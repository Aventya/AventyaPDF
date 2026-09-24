"""
signature_validation.py
Validación de firmas existentes (panel «Firmas», equivalente al de Acrobat).

Comprueba con pyHanko, para cada firma incrustada:
  · integridad criptográfica (el contenido firmado no ha cambiado),
  · confianza de la cadena contra el almacén raíz de Windows **y** la lista de
    confianza de España (vendor/trust/es_tsl.pem, r43; sin consultas de red:
    no se descargan CRL/OCSP, la revocación queda «no comprobada»),
  · cobertura y nivel de modificaciones posteriores a la firma,
  · sello de tiempo, si lo hay.

**(r45) Un campo de firma puede contener una firma normal (`/Sig`) o un sello
de tiempo de documento (`/DocTimeStamp`)** — un campo de firma aparte, sin
firmante, que solo certifica una fecha sobre el PDF ya firmado (lo añaden
Acrobat y otros al re-sellar un documento firmado). pyHanko valida cada tipo
con una función distinta (`validate_pdf_signature` / `validate_pdf_timestamp`)
y **exige el tipo correcto**: pasarle un `/DocTimeStamp` a la primera lanza
«Signature object type must be /Sig», y antes de r45 eso se veía como «No se
pudo validar» aunque el sello fuera perfectamente válido (visto con dos firmas
en un mismo PDF, donde la segunda era en realidad este tipo de sello).

Todo el acceso a atributos de pyHanko va protegido con getattr porque la API
de estado ha cambiado entre versiones.
"""
import functools
import os
import ssl
from dataclasses import dataclass
from io import BytesIO

TRUST_LIST = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "vendor", "trust", "es_tsl.pem")


@dataclass
class SignatureReport:
    field_name: str
    signer: str = ""
    signed_at: str = ""
    timestamp: str = ""
    intact: bool = False
    valid: bool = False
    trusted: bool = False
    coverage: str = ""
    modification: str = ""
    error: str = ""
    is_timestamp: bool = False          # (r45) /DocTimeStamp, no /Sig
    revision: int = -1                  # (r61) revisión del PDF en que se firmó

    @property
    def verdict(self) -> str:
        if self.error:
            return "error"
        if self.intact and self.valid and self.trusted:
            return "ok"
        if self.intact and self.valid:
            return "untrusted"
        return "invalid"

    @property
    def verdict_text(self) -> str:
        return _VERDICT_TEXT[self.is_timestamp][self.verdict]


_VERDICT_TEXT = {
    False: {
        "ok": "Firma válida y de confianza",
        "untrusted": "Firma íntegra, identidad no verificada",
        "invalid": "Firma NO válida (documento alterado o firma dañada)",
        "error": "No se pudo validar",
    },
    True: {
        "ok": "Sello de tiempo válido y de confianza",
        "untrusted": "Sello de tiempo íntegro, identidad no verificada",
        "invalid": "Sello de tiempo NO válido (documento alterado o sello dañado)",
        "error": "No se pudo validar",
    },
}


_COVERAGE = {
    "ENTIRE_FILE": "Todo el documento",
    "ENTIRE_REVISION": "Revisión completa (hay cambios posteriores)",
    "CONTIGUOUS_BLOCK_FROM_START": "Parcial",
    "UNCLEAR": "No determinada",
}
_MODIFICATION = {
    "NONE": "Sin cambios posteriores",
    "LTA_UPDATES": "Solo datos de validación (LTV)",
    "FORM_FILLING": "Relleno de formularios / firmas posteriores",
    "ANNOTATIONS": "Comentarios añadidos después",
    "OTHER": "Cambios no permitidos después de firmar",
}


def _windows_trust_material():
    from asn1crypto import x509 as ax
    roots, others = [], []
    for store, target in (("ROOT", roots), ("CA", others)):
        try:
            for der, enc, _ in ssl.enum_certificates(store):
                if enc != "x509_asn":
                    continue
                try:
                    target.append(ax.Certificate.load(der))
                except Exception:
                    pass
        except Exception:
            pass
    return roots, others


@functools.lru_cache(maxsize=1)
def _bundled_trust_anchors() -> tuple:
    """Anclas de confianza de la TSL de España (r43), generadas con
    `create_trust_list.py`.

    Adobe da por buenas las firmas de las entidades cualificadas (FNMT,
    Registradores, Policía…) porque usa la lista de confianza europea, no el
    almacén de Windows, donde muchas no están. La TSL lista como punto de
    confianza la CA que emite, que suele ser una **intermedia** (p. ej. la «AC
    Interna» de los Registradores), y pyHanko acepta una intermedia como ancla.
    Sin el archivo devuelve vacío y se valida solo contra Windows."""
    from asn1crypto import pem, x509
    try:
        with open(TRUST_LIST, "rb") as f:
            data = f.read()
        bloques = list(pem.unarmor(data, multiple=True))
    except (OSError, ValueError):
        return ()
    anclas = []
    for _tipo, _cabeceras, der in bloques:
        try:
            anclas.append(x509.Certificate.load(der))
        except Exception:
            pass
    return tuple(anclas)


def _fmt_dt(dt) -> str:
    try:
        return dt.astimezone().strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        return str(dt) if dt else ""


def _build_context(roots, others):
    from pyhanko_certvalidator import ValidationContext
    try:
        return ValidationContext(trust_roots=roots, other_certs=others,
                                 allow_fetching=False, revocation_mode="soft-fail")
    except TypeError:
        return ValidationContext(trust_roots=roots)


def _open_reader(data: bytes):
    """Lector de pyHanko, tolerante con los PDF algo irregulares (r37).

    En modo estricto pyHanko se niega a leer archivos con referencias cruzadas
    híbridas (Word, Acrobat…) y también otros defectos que los visores aceptan
    sin más, como que la tabla xref declare un objeto más de los que anuncia el
    tráiler («Xref table size mismatch», visto en las notificaciones del Colegio
    de Registradores). Eso impedía **validar** la firma, aunque fuese correcta.
    En modo tolerante se lee igual que en cualquier visor y la firma se
    comprueba criptográficamente igual: si el archivo estuviese alterado, la
    validación lo diría."""
    from pyhanko.pdf_utils.misc import PdfReadError
    from pyhanko.pdf_utils.reader import PdfFileReader

    try:
        reader = PdfFileReader(BytesIO(data))
        if reader.xrefs.hybrid_xrefs_present:
            reader = PdfFileReader(BytesIO(data), strict=False)
        list(reader.embedded_signatures)         # las firmas se leen en diferido
        return reader
    except PdfReadError:
        return PdfFileReader(BytesIO(data), strict=False)


def validate_signatures(data: bytes, password: str = "") -> list[SignatureReport]:
    from pyhanko.sign.validation import validate_pdf_signature, validate_pdf_timestamp

    reader = _open_reader(data)
    if getattr(reader, "encrypted", False) and password:
        try:
            reader.decrypt(password)
        except Exception:
            pass

    roots, others = _windows_trust_material()
    roots = roots + list(_bundled_trust_anchors())
    reports: list[SignatureReport] = []
    for emb in reader.embedded_signatures:
        # (r45) Un campo de firma puede ser una firma normal (/Sig) o un sello
        # de tiempo de documento (/DocTimeStamp, sin firmante): cada uno se
        # valida con su función de pyHanko; la que no toca lanza «Signature
        # object type must be /Sig» (o «…/DocTimeStamp»), no un fallo real.
        es_sello = getattr(emb, "sig_object_type", "/Sig") == "/DocTimeStamp"
        rep = SignatureReport(field_name=getattr(emb, "field_name", "") or "",
                              is_timestamp=es_sello,
                              revision=getattr(emb, "signed_revision", -1))
        try:
            if es_sello:
                status = validate_pdf_timestamp(emb, _build_context(roots, others))
            else:
                status = validate_pdf_signature(emb, _build_context(roots, others))
            rep.intact = bool(getattr(status, "intact", False))
            rep.valid = bool(getattr(status, "valid", False))
            rep.trusted = bool(getattr(status, "trusted", False))
            cert = getattr(status, "signing_cert", None)
            if cert is not None:
                try:
                    rep.signer = cert.subject.native.get("common_name") or cert.subject.human_friendly
                except Exception:
                    rep.signer = str(cert.subject)
            if es_sello:
                # El propio objeto ES el sello: su fecha va en «timestamp», no
                # hay una fecha aparte «declarada por el firmante».
                rep.timestamp = _fmt_dt(getattr(status, "timestamp", None))
            else:
                rep.signed_at = _fmt_dt(getattr(status, "signer_reported_dt", None))
                ts = getattr(status, "timestamp_validity", None)
                if ts is not None:
                    rep.timestamp = _fmt_dt(getattr(ts, "timestamp", None))
            cov = getattr(status, "coverage", None)
            if cov is not None:
                rep.coverage = _COVERAGE.get(getattr(cov, "name", ""), str(cov))
            mod = getattr(status, "modification_level", None)
            if mod is not None:
                rep.modification = _MODIFICATION.get(getattr(mod, "name", ""), str(mod))
        except Exception as e:  # noqa: BLE001 — se muestra al usuario
            rep.error = str(e) or e.__class__.__name__
        reports.append(rep)
    return reports
