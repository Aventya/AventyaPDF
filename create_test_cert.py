"""
create_test_cert.py
Genera `test_certificate.pfx` (contraseña 1234): certificado autofirmado para
probar la firma PAdES. Las pruebas automáticas reutilizan `build_test_pfx`
para no depender de un certificado que pueda haber caducado.
"""
import datetime
import os

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

PFX_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_certificate.pfx")


def build_test_pfx(password: bytes = b"1234",
                   common_name: str = "Usuario de Pruebas Aventya",
                   days: int = 3 * 365) -> bytes:
    """Devuelve un PKCS#12 con clave RSA 2048 y certificado autofirmado."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "ES"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Madrid"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Madrid"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Aventya Software S.L."),
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
    ])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=5))
        .not_valid_after(now + datetime.timedelta(days=days))
        # Firma digital + no repudio: lo que pyHanko espera de un certificado de firma.
        .add_extension(x509.KeyUsage(
            digital_signature=True, content_commitment=True, key_encipherment=False,
            data_encipherment=False, key_agreement=False, key_cert_sign=False,
            crl_sign=False, encipher_only=False, decipher_only=False), critical=True)
        .sign(private_key, hashes.SHA256())
    )
    return pkcs12.serialize_key_and_certificates(
        name=b"test_cert", key=private_key, cert=cert, cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(password))


def generate_test_pfx():
    with open(PFX_PATH, "wb") as f:
        f.write(build_test_pfx())
    print(f"Certificado de pruebas creado: {PFX_PATH} (contraseña: 1234)")


if __name__ == "__main__":
    generate_test_pfx()
