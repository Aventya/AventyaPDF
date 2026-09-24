"""
Diagnóstico de la validación de firmas de un PDF (misma ruta que el panel Firmas):

    python inspect_signature.py [archivo.pdf]

Sin argumento usa Notificacion.PDF. Enseña el veredicto y la cadena del
certificado, y de dónde sale la confianza: almacén de Windows o lista de
confianza de España (vendor/trust/es_tsl.pem).
"""
import hashlib
import os
import pathlib
import ssl
import sys

import signature_validation as sv

RAIZ = os.path.dirname(os.path.abspath(__file__))
pdf = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, "Notificacion.PDF")
data = pathlib.Path(pdf).read_bytes()

for r in sv.validate_signatures(data):
    print(f"\n--- Informe de {'sello de tiempo' if r.is_timestamp else 'firma'} ---")
    print(f"Campo: {r.field_name}")
    print(f"Veredicto interno: {r.verdict}  →  {r.verdict_text}")
    print(f"Íntegra: {r.intact} · válida: {r.valid} · de confianza: {r.trusted}")
    print(f"Firmante: {r.signer}")
    print(f"Firmada: {r.signed_at} · sello de tiempo: {r.timestamp or '—'}")
    print(f"Cobertura: {r.coverage} · {r.modification}")
    if r.error:
        print(f"Error: {r.error}")

# Cadena de certificados de cada firma y qué ancla la respalda. Se abre con el
# lector tolerante de la app: el estricto rechaza PDF con la xref irregular.
windows = {hashlib.sha256(der).hexdigest()
           for store in ("ROOT", "CA") for der, enc, _ in ssl.enum_certificates(store)
           if enc == "x509_asn"}
tsl = {hashlib.sha256(c.dump()).hexdigest() for c in sv._bundled_trust_anchors()}
for emb in sv._open_reader(data).embedded_signatures:
    print(f"\n--- Cadena de {emb.field_name} ---")
    for c in [emb.signer_cert, *emb.other_embedded_certs]:
        huella = hashlib.sha256(c.dump()).hexdigest()
        donde = [n for n, s in (("Windows", windows), ("TSL de España", tsl)) if huella in s]
        auto = " (autofirmado)" if c.subject == c.issuer else ""
        print(f"  {c.subject.native.get('common_name', c.subject.human_friendly)}{auto}")
        print(f"     emisor: {c.issuer.native.get('common_name', c.issuer.human_friendly)}"
              f" · SHA-256 {huella[:16]}… · ancla en: {', '.join(donde) or 'ninguna'}")
