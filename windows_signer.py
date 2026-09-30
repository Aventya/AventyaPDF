"""
windows_signer.py
Firmante de pyHanko que firma con la clave del almacén Personal de Windows
SIN exportarla (r108): Windows hace la operación de firma y la clave nunca
sale del almacén. Así funcionan los certificados con la clave marcada como
no exportable y los de tarjeta criptográfica o token (DNIe), en los que es
Windows —o el controlador de la tarjeta— quien pide el PIN.

CNG (NCrypt) primero; CryptoAPI de respaldo para las claves guardadas con un
proveedor antiguo (CSP) que CNG no sepa abrir.
"""
import ctypes
import hashlib
from ctypes import wintypes

from asn1crypto import algos, x509 as asn1_x509
from pyhanko.sign import signers
from pyhanko_certvalidator.registry import SimpleCertificateStore

_crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
_ncrypt = ctypes.WinDLL("ncrypt")
_advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)

_CERT_STORE_PROV_SYSTEM_W = 10
_CERT_SYSTEM_STORE_CURRENT_USER = 0x00010000
_CERT_STORE_READONLY_FLAG = 0x00008000
_CERT_STORE_OPEN_EXISTING_FLAG = 0x00004000
_ENCODING = 0x00010001                    # X509_ASN_ENCODING | PKCS_7_ASN_ENCODING
_CERT_FIND_SHA1_HASH = 0x00010000
_CRYPT_ACQUIRE_PREFER_NCRYPT_KEY_FLAG = 0x00020000
_CERT_NCRYPT_KEY_SPEC = 0xFFFFFFFF
_BCRYPT_PAD_PKCS1 = 0x00000002
_HP_HASHVAL = 0x0002
_CALG = {"sha256": 0x800C, "sha384": 0x800D, "sha512": 0x800E}
_CANCELLED = {0x8010006E, 0x800704C7, 0x80090036}   # SCARD_W_CANCELLED_BY_USER, ERROR_CANCELLED, NTE_USER_CANCELLED


class _Blob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


class _CertContext(ctypes.Structure):
    _fields_ = [("dwCertEncodingType", wintypes.DWORD),
                ("pbCertEncoded", ctypes.POINTER(ctypes.c_ubyte)),
                ("cbCertEncoded", wintypes.DWORD),
                ("pCertInfo", ctypes.c_void_p),
                ("hCertStore", ctypes.c_void_p)]


class _Pkcs1PaddingInfo(ctypes.Structure):
    _fields_ = [("pszAlgId", wintypes.LPCWSTR)]


_PCtx = ctypes.POINTER(_CertContext)
_crypt32.CertOpenStore.restype = ctypes.c_void_p
_crypt32.CertOpenStore.argtypes = [ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p,
                                   wintypes.DWORD, wintypes.LPCWSTR]
_crypt32.CertFindCertificateInStore.restype = _PCtx
_crypt32.CertFindCertificateInStore.argtypes = [ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
                                                wintypes.DWORD, ctypes.c_void_p, _PCtx]
_crypt32.CryptAcquireCertificatePrivateKey.argtypes = [
    _PCtx, wintypes.DWORD, ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t),
    ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.BOOL)]
_crypt32.CertFreeCertificateContext.argtypes = [_PCtx]
_crypt32.CertCloseStore.argtypes = [ctypes.c_void_p, wintypes.DWORD]
_ncrypt.NCryptSignHash.restype = ctypes.c_long
_ncrypt.NCryptSignHash.argtypes = [ctypes.c_size_t, ctypes.c_void_p, ctypes.c_char_p, wintypes.DWORD,
                                   ctypes.c_char_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD),
                                   wintypes.DWORD]
_ncrypt.NCryptFreeObject.argtypes = [ctypes.c_size_t]
_advapi32.CryptCreateHash.argtypes = [ctypes.c_size_t, wintypes.DWORD, ctypes.c_size_t,
                                      wintypes.DWORD, ctypes.POINTER(ctypes.c_size_t)]
_advapi32.CryptSetHashParam.argtypes = [ctypes.c_size_t, wintypes.DWORD, ctypes.c_char_p, wintypes.DWORD]
_advapi32.CryptSignHashW.argtypes = [ctypes.c_size_t, wintypes.DWORD, wintypes.LPCWSTR, wintypes.DWORD,
                                     ctypes.c_char_p, ctypes.POINTER(wintypes.DWORD)]
_advapi32.CryptDestroyHash.argtypes = [ctypes.c_size_t]
_advapi32.CryptReleaseContext.argtypes = [ctypes.c_size_t, wintypes.DWORD]


class WindowsStoreError(Exception):
    pass


def _cancelled(code: int) -> bool:
    return (code & 0xFFFFFFFF) in _CANCELLED


class _StoreCert:
    """Contexto de un certificado del almacén MY, buscado por su huella SHA-1."""

    def __init__(self, thumbprint: str):
        self._store = _crypt32.CertOpenStore(
            _CERT_STORE_PROV_SYSTEM_W, 0, None,
            _CERT_SYSTEM_STORE_CURRENT_USER | _CERT_STORE_READONLY_FLAG
            | _CERT_STORE_OPEN_EXISTING_FLAG, "MY")
        if not self._store:
            raise WindowsStoreError("No se pudo abrir el almacén personal de Windows.")
        raw = bytes.fromhex(thumbprint)
        buf = (ctypes.c_ubyte * len(raw)).from_buffer_copy(raw)
        blob = _Blob(len(raw), buf)
        self.ctx = _crypt32.CertFindCertificateInStore(
            self._store, _ENCODING, 0, _CERT_FIND_SHA1_HASH, ctypes.byref(blob), None)
        if not self.ctx:
            self.close()
            raise WindowsStoreError(
                "El certificado ya no está en el almacén de Windows. Elige otro.")

    def der(self) -> bytes:
        c = self.ctx.contents
        return ctypes.string_at(c.pbCertEncoded, c.cbCertEncoded)

    def close(self):
        if getattr(self, "ctx", None):
            _crypt32.CertFreeCertificateContext(self.ctx)
            self.ctx = None
        if self._store:
            _crypt32.CertCloseStore(self._store, 0)
            self._store = None


def _chain(leaf: asn1_x509.Certificate) -> list:
    """Intermedias del emisor, del almacén de Windows (no la raíz): el
    validador del lector las necesita si no las tiene él."""
    import ssl
    pool = []
    for store in ("CA", "ROOT"):
        try:
            pool += [asn1_x509.Certificate.load(d) for d, enc, _ in ssl.enum_certificates(store)
                     if enc == "x509_asn"]
        except Exception:
            pass
    out, cur = [], leaf
    for _ in range(6):
        if cur.self_signed != "no":
            break
        issuer = next((c for c in pool if c.subject == cur.issuer and c.dump() != cur.dump()), None)
        if issuer is None or issuer.self_signed != "no":
            break
        out.append(issuer)
        cur = issuer
    return out


class WindowsStoreSigner(signers.Signer):
    def __init__(self, thumbprint: str):
        self.thumbprint = thumbprint.upper()
        sc = _StoreCert(self.thumbprint)
        try:
            der = sc.der()
        finally:
            sc.close()
        cert = asn1_x509.Certificate.load(der)
        self.cert_der = der
        algo = cert.public_key.algorithm
        if algo not in ("rsa", "ec"):
            raise WindowsStoreError(f"Tipo de clave no admitido para firmar: {algo}.")
        self._algo = algo
        super().__init__(
            signing_cert=cert,
            cert_registry=SimpleCertificateStore.from_certs([cert] + _chain(cert)),
            embed_roots=False,
            signature_mechanism=algos.SignedDigestAlgorithm(
                {"algorithm": "sha256_rsa" if algo == "rsa" else "sha256_ecdsa"}),
        )

    def _dummy(self) -> bytes:
        n = self.signing_cert.public_key.bit_size
        if self._algo == "rsa":
            return bytes((n + 7) // 8)
        big = (1 << (((n + 7) // 8) * 8)) - 1
        return algos.DSASignature({"r": big, "s": big}).dump()

    async def async_sign_raw(self, data: bytes, digest_algorithm: str, dry_run=False) -> bytes:
        if dry_run:
            return self._dummy()
        digest_algorithm = digest_algorithm.lower()
        if digest_algorithm not in _CALG:
            raise WindowsStoreError(f"Algoritmo de resumen no admitido: {digest_algorithm}.")
        digest = hashlib.new(digest_algorithm, data).digest()
        sc = _StoreCert(self.thumbprint)
        try:
            handle, spec, free = ctypes.c_size_t(), wintypes.DWORD(), wintypes.BOOL()
            if not _crypt32.CryptAcquireCertificatePrivateKey(
                    sc.ctx, _CRYPT_ACQUIRE_PREFER_NCRYPT_KEY_FLAG, None,
                    ctypes.byref(handle), ctypes.byref(spec), ctypes.byref(free)):
                err = ctypes.get_last_error()
                if _cancelled(err):
                    raise WindowsStoreError("Firma cancelada.")
                raise WindowsStoreError(
                    "Windows no da acceso a la clave privada de este certificado "
                    f"(código 0x{err & 0xFFFFFFFF:08X}).\n\n"
                    "Si es de una tarjeta o un DNIe, comprueba que está insertado.")
            try:
                if spec.value == _CERT_NCRYPT_KEY_SPEC:
                    sig = self._sign_ncrypt(handle.value, digest, digest_algorithm)
                else:
                    sig = self._sign_capi(handle.value, spec.value, digest, digest_algorithm)
            finally:
                if free.value:
                    if spec.value == _CERT_NCRYPT_KEY_SPEC:
                        _ncrypt.NCryptFreeObject(handle.value)
                    else:
                        _advapi32.CryptReleaseContext(handle.value, 0)
        finally:
            sc.close()
        return sig

    def _sign_ncrypt(self, key, digest: bytes, digest_algorithm: str) -> bytes:
        if self._algo == "rsa":
            pad = _Pkcs1PaddingInfo(digest_algorithm.upper())
            pad_ptr, flags = ctypes.byref(pad), _BCRYPT_PAD_PKCS1
        else:
            pad_ptr, flags = None, 0
        size = wintypes.DWORD()
        st = _ncrypt.NCryptSignHash(key, pad_ptr, digest, len(digest), None, 0,
                                    ctypes.byref(size), flags)
        if st == 0:
            out = ctypes.create_string_buffer(size.value)
            st = _ncrypt.NCryptSignHash(key, pad_ptr, digest, len(digest), out, size,
                                        ctypes.byref(size), flags)
        if st != 0:
            if _cancelled(st):
                raise WindowsStoreError("Firma cancelada.")
            raise WindowsStoreError(
                f"Windows no pudo firmar con la clave del certificado (código 0x{st & 0xFFFFFFFF:08X}).")
        sig = out.raw[:size.value]
        if self._algo == "ec":   # CNG devuelve r‖s en crudo; CMS lo quiere en DER
            h = len(sig) // 2
            sig = algos.DSASignature({"r": int.from_bytes(sig[:h], "big"),
                                      "s": int.from_bytes(sig[h:], "big")}).dump()
        return sig

    def _sign_capi(self, prov, spec: int, digest: bytes, digest_algorithm: str) -> bytes:
        if self._algo != "rsa":
            raise WindowsStoreError("Clave de curva elíptica en un proveedor antiguo: no admitida.")
        h = ctypes.c_size_t()
        if not _advapi32.CryptCreateHash(prov, _CALG[digest_algorithm], 0, 0, ctypes.byref(h)):
            raise WindowsStoreError(
                "El proveedor criptográfico del certificado no admite SHA-2 "
                f"(código 0x{ctypes.get_last_error() & 0xFFFFFFFF:08X}).")
        try:
            if not _advapi32.CryptSetHashParam(h.value, _HP_HASHVAL, digest, 0):
                raise WindowsStoreError("No se pudo preparar el resumen para firmar.")
            size = wintypes.DWORD()
            ok = _advapi32.CryptSignHashW(h.value, spec, None, 0, None, ctypes.byref(size))
            out = ctypes.create_string_buffer(size.value) if ok else None
            if ok:
                ok = _advapi32.CryptSignHashW(h.value, spec, None, 0, out, ctypes.byref(size))
            if not ok:
                err = ctypes.get_last_error()
                if _cancelled(err):
                    raise WindowsStoreError("Firma cancelada.")
                raise WindowsStoreError(
                    f"Windows no pudo firmar con la clave del certificado (código 0x{err & 0xFFFFFFFF:08X}).")
        finally:
            _advapi32.CryptDestroyHash(h.value)
        return out.raw[:size.value][::-1]   # CryptoAPI la da en little-endian
