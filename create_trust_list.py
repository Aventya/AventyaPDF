"""
Genera la lista de confianza para validar firmas:

    python create_trust_list.py

Resultado: vendor/trust/es_tsl.pem — los certificados de los servicios de
confianza **cualificados y en vigor** de la Lista de Confianza de España (TSL),
que es la fuente que usan Adobe Acrobat y el resto de validadores europeos
(EUTL), no el almacén de Windows. Ahí están las autoridades de las
administraciones públicas y las demás entidades cualificadas (FNMT, Dirección
General de la Policía, Colegio de Registradores, ACCV, Izenpe, AOC, Defensa…).

De la TSL entran, con estado «granted» (concedido) y sin caducar:
  · los servicios de certificados cualificados (CA/QC) y de sellos de tiempo
    (TSA/QTST);
  · pero **no** los declarados expresamente para sitios web (qualifier
    QCForWSA sin QCForESig ni QCForESeal), que no tienen que ver con firmar un
    PDF. Sin propósito declarado el uso por defecto es la firma (los de la
    FNMT para el sector público solo declaran QCQSCDManagedOnBehalf).

Ojo: la TSL lista como punto de confianza la CA que emite (a menudo una
**intermedia**, p. ej. «AC Interna» de los Registradores) y no siempre su raíz,
así que la validación tiene que aceptar intermedias como ancla.

## La cadena se verifica de verdad, no solo por HTTPS (r43)

1. Se descarga la LOTL (lista de la UE) y se comprueba su firma XAdES contra
   `vendor/trust/oj_signers.pem` (los certificados de la Comisión, ver ese
   archivo para su procedencia). Si no valida, se aborta: no se lee nada de un
   documento que dice ser la LOTL pero no está firmado por quien debería.
2. De la LOTL (ya de confianza) se toma el puntero a la TSL de España **y los
   certificados que la propia LOTL declara que deben firmarla**
   (`ServiceDigitalIdentity` del `OtherTSLPointer`). Es la LOTL quien dice qué
   certificado vale para España, no el archivo de España que se va a descargar.
3. Se descarga la TSL de España y se comprueba su firma XAdES contra
   **esos** certificados (los que dijo la LOTL, no otros). Si no valida, se
   aborta.
4. Solo entonces se seleccionan los servicios (`seleccionar`).

Necesita `signxml` además de lo del entorno normal de la app (solo para
generar; la aplicación no lo necesita para validar firmas de PDF):
`pip install signxml`.

La lista caduca (campo «Próxima actualización» de la cabecera del archivo):
volver a ejecutar este script antes de esa fecha.

Solo hace falta Internet para GENERAR la lista; la aplicación usa el archivo.
"""
import base64
import datetime
import hashlib
import os
import sys
import urllib.request
import xml.etree.ElementTree as ET

from asn1crypto import pem, x509

RAIZ = os.path.dirname(os.path.abspath(__file__))
DESTINO = os.path.join(RAIZ, "vendor", "trust", "es_tsl.pem")
ANCLAS_OJ = os.path.join(RAIZ, "vendor", "trust", "oj_signers.pem")
LOTL = "https://ec.europa.eu/tools/lotl/eu-lotl.xml"
DSS_KEYSTORE = ("https://raw.githubusercontent.com/esig/dss-demonstrations/master/"
                "dss-demo-webapp/src/main/resources/keystore.p12")
DSS_KEYSTORE_PASSWORD = "dss-password"          # pública, del propio repositorio de DSS
NS = "{http://uri.etsi.org/02231/v2#}"
NS_ADICIONAL = "{http://uri.etsi.org/02231/v2/additionaltypes#}"
TIPOS = ("CA/QC", "TSA/QTST")                # …/Svctype/CA/QC y …/Svctype/TSA/QTST
SOLO_WEB = "QCForWSA"
PARA_FIRMA = ("QCForESig", "QCForESeal")


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "aventyapdf"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def _sufijo(url: str) -> str:
    return (url or "").rstrip("/").rsplit("/", 1)[-1]


class FirmaNoValida(RuntimeError):
    """La firma XAdES de la LOTL o de la TSL no valida contra las anclas."""


def _anclas_de_confianza():
    """Certificados de `vendor/trust/oj_signers.pem` como objetos `cryptography`
    (lo que exige `signxml`, a diferencia del resto del módulo que usa
    `asn1crypto`)."""
    from cryptography.x509 import load_pem_x509_certificate

    with open(ANCLAS_OJ, "rb") as f:
        data = f.read()
    bloques = data.split(b"-----BEGIN CERTIFICATE-----")[1:]
    return [load_pem_x509_certificate(b"-----BEGIN CERTIFICATE-----" + b)
            for b in bloques]


def verificar_firma(xml: bytes, anclas, refs: int = 2):
    """Certificado de `anclas` que firma `xml` con XAdES/XMLDSig, o
    `FirmaNoValida` si ninguno lo hace. `refs=2` es la firma envolvente con
    XAdES-BES normal (una referencia al documento y otra a `SignedProperties`);
    se exige ese número exacto para no aceptar una firma con menos partes de
    las que debería llevar."""
    from signxml import SignatureConfiguration, XMLVerifier

    cfg = SignatureConfiguration(expect_references=refs)
    errores = []
    for cert in anclas:
        try:
            XMLVerifier().verify(xml, x509_cert=cert, expect_config=cfg)
            return cert
        except Exception as e:                              # noqa: BLE001
            errores.append(f"{cert.subject.rfc4514_string()}: {e}")
    raise FirmaNoValida("Ninguna ancla valida la firma:\n  " + "\n  ".join(errores))


def puntero_es(lotl_xml: bytes):
    """(url de la TSL de España, [certificados DER] que la LOTL declara que
    deben firmarla) leyendo el puntero de tipo XML (no el PDF)."""
    raiz = ET.fromstring(lotl_xml)
    for p in raiz.iter(NS + "OtherTSLPointer"):
        territorio = p.findtext(f".//{NS_ADICIONAL}MimeType")
        pais = "".join(t.text or "" for t in p.iter(NS + "SchemeTerritory"))
        if pais == "ES" and territorio == "application/vnd.etsi.tsl+xml":
            url = p.findtext(NS + "TSLLocation")
            certs = [base64.b64decode(b64.text) for b64 in p.iter(NS + "X509Certificate")]
            if not certs:
                raise RuntimeError("La LOTL no declara certificado para firmar la TSL de ES")
            return url, certs
    raise RuntimeError("La LOTL no trae un puntero XML para ES")


def _tipo(uri: str) -> str:
    """`…/TrstSvc/Svctype/CA/QC` → `CA/QC`. Con solo el último tramo, `QC` también
    sería el de los servicios OCSP (`Certstatus/OCSP/QC`), que no son CA."""
    return (uri or "").split("Svctype/")[-1]


def _es_de_firma(servicio) -> bool:
    """False solo si el servicio se declara **expresamente** para sitios web
    (QCForWSA) y no para firma ni sello. Sin propósito explícito el uso por defecto
    es la firma: los servicios de la FNMT para el sector público declaran solo
    `QCQSCDManagedOnBehalf` y son justo los que interesan."""
    q = [_sufijo(e.get("uri", "")) for e in servicio.iter() if e.tag.endswith("Qualifier")]
    return SOLO_WEB not in q or any(x in PARA_FIRMA for x in q)


def seleccionar(xml: bytes, ahora=None):
    """(cabecera, [(huella, nombre, proveedor, certificado)]) de la TSL."""
    ahora = ahora or datetime.datetime.now(datetime.timezone.utc)
    raiz = ET.fromstring(xml)
    cab = {
        "emision": raiz.findtext(f".//{NS}TSLSequenceNumber"),
        "fecha": raiz.findtext(f".//{NS}ListIssueDateTime"),
        "proxima": raiz.findtext(f".//{NS}NextUpdate/{NS}dateTime"),
    }
    elegidos: dict[str, tuple] = {}
    for tsp in raiz.iter(NS + "TrustServiceProvider"):
        proveedor = tsp.findtext(f"{NS}TSPInformation/{NS}TSPName/{NS}Name") or ""
        for info in tsp.iter(NS + "ServiceInformation"):
            tipo = _tipo(info.findtext(NS + "ServiceTypeIdentifier"))
            estado = _sufijo(info.findtext(NS + "ServiceStatus"))
            if tipo not in TIPOS or estado != "granted" or not _es_de_firma(info):
                continue
            nombre = info.findtext(f"{NS}ServiceName/{NS}Name") or ""
            for b64 in info.iter(NS + "X509Certificate"):
                der = base64.b64decode(b64.text)
                cert = x509.Certificate.load(der)
                if cert["tbs_certificate"]["validity"]["not_after"].native <= ahora:
                    continue
                elegidos.setdefault(hashlib.sha256(der).hexdigest(),
                                    (nombre, proveedor, cert))
    filas = [(h, n, p, c) for h, (n, p, c) in elegidos.items()]
    filas.sort(key=lambda f: (f[2].lower(), f[3].subject.human_friendly, f[0]))
    return cab, filas


def escribir(cab: dict, filas: list, url: str, destino: str = DESTINO) -> None:
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    partes = [
        "# Lista de confianza de España (TSL) — generada con create_trust_list.py\n"
        f"# Origen: {url}\n"
        "# Firma XAdES comprobada contra los certificados que la LOTL declara para\n"
        "# España (create_trust_list.verificar_firma; ver vendor/trust/oj_signers.pem).\n"
        f"# Emisión nº {cab['emision']} · publicada {cab['fecha']} · "
        f"Próxima actualización: {cab['proxima']}\n"
        f"# Servicios: {len(filas)} (cualificados, concedidos y sin caducar)\n"
    ]
    for huella, nombre, proveedor, cert in filas:
        cn = cert.subject.native.get("common_name") or cert.subject.human_friendly
        partes.append(f"\n# {cn}\n# Proveedor: {proveedor}\n# SHA-256: {huella}\n")
        partes.append(pem.armor("CERTIFICATE", cert.dump()).decode("ascii"))
    with open(destino, "w", encoding="utf-8", newline="\n") as f:
        f.write("".join(partes))


def reanclar(destino: str = ANCLAS_OJ) -> int:
    """Vuelve a extraer los certificados de la Comisión desde el `keystore.p12`
    del proyecto DSS (ver la cabecera de `vendor/trust/oj_signers.pem`) y los
    escribe **en un archivo aparte** (`.nuevo`) para revisar el cambio a mano:
    esto fija un ancla de confianza y no debe sobrescribirse solo."""
    from cryptography.hazmat.primitives.serialization import Encoding, pkcs12

    ks = pkcs12.load_key_and_certificates(_get(DSS_KEYSTORE), DSS_KEYSTORE_PASSWORD.encode())
    anclas = sorted(([ks[1]] if ks[1] else []) + list(ks[2] or []),
                     key=lambda c: c.subject.rfc4514_string())
    salida = destino + ".nuevo"
    with open(salida, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"# Reanclado {datetime.date.today()} desde {DSS_KEYSTORE}\n")
        for c in anclas:
            huella = hashlib.sha256(c.public_bytes(Encoding.DER)).hexdigest()
            f.write(f"\n# {c.subject.rfc4514_string()}\n"
                    f"# Válido hasta: {c.not_valid_after_utc:%Y-%m-%d}\n"
                    f"# SHA-256: {huella}\n")
            f.write(c.public_bytes(Encoding.PEM).decode("ascii"))
    print(f"{len(anclas)} certificados → {salida}")
    print("Revisa el cambio (diff contra oj_signers.pem) y compara al menos una\n"
          "huella contra otra fuente antes de sustituirlo. No se sobrescribe solo.")
    return 0


def generar() -> int:
    anclas_oj = _anclas_de_confianza()
    lotl_xml = _get(LOTL)
    firmante = verificar_firma(lotl_xml, anclas_oj)
    print("LOTL firmada por:", firmante.subject.rfc4514_string())

    url, certs_es_der = puntero_es(lotl_xml)
    print("TSL de España:", url)
    from cryptography.x509 import load_der_x509_certificate
    anclas_es = [load_der_x509_certificate(d) for d in certs_es_der]

    tsl_xml = _get(url)
    firmante_es = verificar_firma(tsl_xml, anclas_es)
    print("TSL de España firmada por:", firmante_es.subject.rfc4514_string())

    cab, filas = seleccionar(tsl_xml)
    if len(filas) < 50:                                 # una TSL vacía no se guarda
        print(f"Solo {len(filas)} servicios: se descarta, algo ha cambiado en la TSL.")
        return 1
    escribir(cab, filas, url)
    print(f"{len(filas)} certificados → {DESTINO}")
    print(f"Emisión {cab['emision']}, próxima actualización {cab['proxima']}")
    return 0


if __name__ == "__main__":
    if "--reanclar" in sys.argv:
        sys.exit(reanclar())
    try:
        sys.exit(generar())
    except FirmaNoValida as e:
        print("ABORTADO —", e)
        sys.exit(1)
