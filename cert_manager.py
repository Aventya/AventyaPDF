"""
cert_manager.py
Gestión de certificados de firma: almacén de Windows y archivos PKCS#12.
"""
import os
import re
import secrets
import ssl
import string
import subprocess
import tempfile
from datetime import datetime, timezone
from typing import Optional

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.x509.oid import NameOID

from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QFrame,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QTabWidget,
    QVBoxLayout, QWidget,
)
from PyQt6.QtCore import Qt, QSettings

try:
    import keyring
    _KEYRING_OK = True
except ImportError:
    _KEYRING_OK = False

_APP = "aventyapdf"
_KR_SERVICE = "aventyapdf-signing"
_K_TYPE = "signing/cert_type"      # "windows" | "file"
_K_THUMB = "signing/cert_thumb"    # Thumbprint SHA-1 (almacén Windows)
_K_NAME = "signing/cert_name"      # Nombre para mostrar
_K_PATH = "signing/cert_path"      # Ruta al .pfx (archivo)


# ── Helpers ───────────────────────────────────────────────────────────────── #

def _clean_id(value: str) -> str:
    """Elimina prefijos de país (IDCES-, VATES-, …) de campos de identidad."""
    m = re.match(r'^[A-Z]{2,6}-(.+)$', value)
    return m.group(1) if m else value


def _cert_expiry(cert: x509.Certificate) -> Optional[datetime]:
    try:
        return cert.not_valid_after_utc          # cryptography >= 42
    except AttributeError:
        return cert.not_valid_after.replace(tzinfo=timezone.utc)


# ── Almacén de Windows ────────────────────────────────────────────────────── #

def list_windows_certs() -> list[dict]:
    """
    Enumera los certificados de firma del almacén Personal (MY) del usuario
    de Windows. Filtra caducados y los que no tienen uso de firma digital.
    """
    results: list[dict] = []
    try:
        raw = ssl.enum_certificates("MY")
    except Exception:
        return results

    now = datetime.now(timezone.utc)
    for cert_bytes, encoding, _ in raw:
        if encoding != "x509_asn":
            continue
        try:
            cert = x509.load_der_x509_certificate(cert_bytes)
        except Exception:
            continue

        # Descartar caducados
        expiry = _cert_expiry(cert)
        if expiry and expiry < now:
            continue

        # Solo excluir certificados claramente no orientados a firma
        # (p. ej. solo cifrado sin ningún bit de firma). Si no hay extensión
        # KeyUsage, se incluye siempre — es el caso de muchos certs FNMT/ACCV.
        try:
            ku = cert.extensions.get_extension_for_class(x509.KeyUsage).value
            # Excluir únicamente si key_encipherment Y data_encipherment están
            # activos pero digital_signature Y content_commitment NO lo están.
            if (ku.key_encipherment or ku.data_encipherment) and \
               not ku.digital_signature and not ku.content_commitment:
                continue
        except x509.ExtensionNotFound:
            pass

        # Thumbprint SHA-1 sin separadores, mayúsculas (igual que PowerShell)
        thumbprint = cert.fingerprint(hashes.SHA1()).hex().upper()

        def _get(oid, fallback=""):
            try:
                return cert.subject.get_attributes_for_oid(oid)[0].value
            except Exception:
                return fallback

        name = _get(NameOID.COMMON_NAME) or _get(NameOID.ORGANIZATION_NAME, "Sin nombre")
        nif = _clean_id(_get(NameOID.SERIAL_NUMBER, ""))
        org = _get(NameOID.ORGANIZATION_NAME, "")

        results.append({
            "thumbprint": thumbprint,
            "name": name,
            "nif": nif,
            "org": org,
            "expiry": expiry,
        })

    return results


def export_windows_cert_to_pfx(thumbprint: str) -> tuple[str, str]:
    """
    Exporta un certificado del almacén Personal de Windows a un PKCS#12 temporal.
    Usa la clase .NET X509Store directamente (no requiere la unidad Cert: de
    PowerShell ni el módulo PKI). Devuelve (ruta_pfx, contraseña_temporal).

    Lanza RuntimeError si la clave privada no es exportable o no se encuentra.
    """
    alphabet = string.ascii_letters + string.digits
    temp_pass = "".join(secrets.choice(alphabet) for _ in range(24))
    pfx_path = os.path.join(tempfile.gettempdir(), f"_agpdf_{thumbprint[:12]}.pfx")

    if os.path.exists(pfx_path):
        try:
            os.remove(pfx_path)
        except Exception:
            pass

    # Escapar comillas simples en la ruta (poco probable pero seguro)
    safe_path = pfx_path.replace("'", "''")
    thumb_upper = thumbprint.upper()

    # Usamos X509Store/.NET puro: no depende de la unidad Cert: ni del módulo PKI.
    # $c.Export([X509ContentType]::Pfx, password) exporta cert + clave privada.
    ps = f"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Security
$store = [System.Security.Cryptography.X509Certificates.X509Store]::new(
    [System.Security.Cryptography.X509Certificates.StoreName]::My,
    [System.Security.Cryptography.X509Certificates.StoreLocation]::CurrentUser)
$store.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadOnly)
$cert = ($store.Certificates | Where-Object {{ $_.Thumbprint -eq '{thumb_upper}' }}) | Select-Object -First 1
$store.Close()
if (-not $cert) {{ throw "Certificado no encontrado: {thumb_upper}" }}
$bytes = $cert.Export(
    [System.Security.Cryptography.X509Certificates.X509ContentType]::Pfx,
    '{temp_pass}')
[System.IO.File]::WriteAllBytes('{safe_path}', $bytes)
"""

    result = subprocess.run(
        ["powershell", "-Command", ps],
        capture_output=True, text=True, timeout=30,
    )

    if result.returncode != 0 or not os.path.exists(pfx_path):
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(
            "No se pudo exportar el certificado del almacén de Windows.\n\n"
            "Causas habituales:\n"
            "• La clave privada no está marcada como exportable.\n"
            "• El certificado usa una tarjeta criptográfica o token USB (DNIe).\n\n"
            + (detail or "Sin detalles adicionales.")
        )

    return pfx_path, temp_pass


# ── Persistencia de certificado activo ───────────────────────────────────── #

def load_saved_cert() -> dict:
    """
    Devuelve el certificado guardado:
      {'type': 'windows', 'thumbprint': '…', 'name': '…'}
      {'type': 'file',    'path': '…', 'password': '…'}
      {'type': ''}  →  nada guardado
    """
    s = QSettings(_APP, "config")
    ctype = s.value(_K_TYPE, "")

    if ctype == "windows":
        thumb = s.value(_K_THUMB, "")
        name = s.value(_K_NAME, "")
        return {"type": "windows", "thumbprint": thumb, "name": name} if thumb else {"type": ""}

    if ctype == "file":
        path = s.value(_K_PATH, "")
        if not path or not os.path.exists(path):
            return {"type": ""}
        if _KEYRING_OK:
            pwd = keyring.get_password(_KR_SERVICE, path) or ""
        else:
            pwd = s.value("signing/cert_pass", "")
        return {"type": "file", "path": path, "password": pwd}

    return {"type": ""}


def save_cert(cert: dict) -> None:
    """Persiste la configuración del certificado activo."""
    s = QSettings(_APP, "config")
    s.setValue(_K_TYPE, cert.get("type", ""))
    if cert.get("type") == "windows":
        s.setValue(_K_THUMB, cert.get("thumbprint", ""))
        s.setValue(_K_NAME, cert.get("name", ""))
    elif cert.get("type") == "file":
        path = cert["path"]
        s.setValue(_K_PATH, path)
        pwd = cert.get("password", "")
        if _KEYRING_OK:
            keyring.set_password(_KR_SERVICE, path, pwd)
        else:
            s.setValue("signing/cert_pass", pwd)
    s.sync()  # forzar escritura a disco inmediatamente


def forget_cert() -> None:
    """Elimina el certificado recordado de la configuración."""
    s = QSettings(_APP, "config")
    old_path = s.value(_K_PATH, "")
    for k in (_K_TYPE, _K_THUMB, _K_NAME, _K_PATH, "signing/cert_pass"):
        s.remove(k)
    if _KEYRING_OK and old_path:
        try:
            keyring.delete_password(_KR_SERVICE, old_path)
        except Exception:
            pass


# ── Diálogo selector de certificado ──────────────────────────────────────── #

class _WinCertTab(QWidget):
    """Pestaña con la lista de certificados del almacén de Windows."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._certs: list[dict] = []
        self._build_ui()
        self._populate()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 8, 0, 0)

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Titular / Nombre", "NIF", "Válido hasta"])
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        lay.addWidget(self._table)

        self._empty = QLabel(
            "No se encontraron certificados de firma en el almacén personal de Windows.\n"
            "Instala tu certificado (FNMT, ACCV, Camerfirma…) y vuelve a intentarlo."
        )
        self._empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty.setWordWrap(True)
        self._empty.setStyleSheet("color:#888; padding:20px;")
        self._empty.hide()
        lay.addWidget(self._empty)

    def _populate(self):
        self._certs = list_windows_certs()
        self._table.setRowCount(len(self._certs))
        if not self._certs:
            self._table.hide()
            self._empty.show()
            return
        for i, c in enumerate(self._certs):
            self._table.setItem(i, 0, QTableWidgetItem(c["name"]))
            self._table.setItem(i, 1, QTableWidgetItem(c["nif"] or c["org"] or "—"))
            exp = c["expiry"].strftime("%d/%m/%Y") if c.get("expiry") else "—"
            self._table.setItem(i, 2, QTableWidgetItem(exp))
        self._table.selectRow(0)

    def selected(self) -> Optional[dict]:
        row = self._table.currentRow()
        return self._certs[row] if 0 <= row < len(self._certs) else None


class _FileCertTab(QWidget):
    """Pestaña para seleccionar un certificado PKCS#12 desde archivo."""

    def __init__(self, saved_path="", saved_password="", parent=None):
        super().__init__(parent)
        self._path = saved_path
        self._build_ui(saved_path, saved_password)

    def _build_ui(self, saved_path, saved_password):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 8, 0, 0)
        lay.setSpacing(10)

        lay.addWidget(QLabel("Archivo de certificado PKCS#12 (.pfx / .p12):"))

        row = QHBoxLayout()
        self._path_edit = QLineEdit(saved_path)
        self._path_edit.setPlaceholderText("Ruta al archivo .pfx o .p12…")
        self._path_edit.setReadOnly(True)
        row.addWidget(self._path_edit)
        btn = QPushButton("Examinar…")
        btn.setFixedWidth(96)
        btn.clicked.connect(self._browse)
        row.addWidget(btn)
        lay.addLayout(row)

        lay.addWidget(QLabel("Contraseña:"))
        self._pass = QLineEdit(saved_password)
        self._pass.setEchoMode(QLineEdit.EchoMode.Password)
        self._pass.setPlaceholderText("Contraseña del certificado…")
        lay.addWidget(self._pass)

        note = "(Windows Credential Manager)" if _KEYRING_OK else "(configuración de la app)"
        self._remember = QCheckBox(f"Recordar  {note}")
        self._remember.setChecked(bool(saved_path))
        lay.addWidget(self._remember)
        lay.addStretch()

    def _browse(self):
        p, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar certificado", "", "PKCS#12 (*.pfx *.p12)"
        )
        if p:
            self._path = p
            self._path_edit.setText(p)

    @property
    def cert_path(self) -> str:
        return self._path

    @property
    def password(self) -> str:
        return self._pass.text()

    @property
    def remember(self) -> bool:
        return self._remember.isChecked()


class CertPickerDialog(QDialog):
    """
    Selector de certificado digital.
    Pestaña principal: almacén personal de Windows (certificados instalados).
    Pestaña secundaria: archivo PKCS#12 local (.pfx / .p12).
    """

    def __init__(self, parent=None, saved_cert: dict = None):
        super().__init__(parent)
        self.setWindowTitle("Seleccionar certificado de firma")
        self.setMinimumWidth(600)
        self.setMinimumHeight(450)
        self.setModal(True)
        self._result: dict = {}
        self._build_ui(saved_cert or {})

    def _build_ui(self, saved: dict):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)

        info = QLabel(
            "Selecciona un certificado instalado en el sistema o desde un archivo PKCS#12."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color:#605E5C;")
        lay.addWidget(info)

        self._tabs = QTabWidget()

        self._win_tab = _WinCertTab()
        self._tabs.addTab(self._win_tab, "🖥️  Almacén de Windows")

        saved_path = saved.get("path", "") if saved.get("type") == "file" else ""
        saved_pass = saved.get("password", "") if saved.get("type") == "file" else ""
        self._file_tab = _FileCertTab(saved_path, saved_pass)
        self._tabs.addTab(self._file_tab, "📁  Archivo .pfx / .p12")

        if saved.get("type") == "file":
            self._tabs.setCurrentIndex(1)

        lay.addWidget(self._tabs)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        lay.addWidget(sep)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.button(QDialogButtonBox.StandardButton.Ok).setText("Usar este certificado")
        btns.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        btns.accepted.connect(self._on_accept)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

    def _on_accept(self):
        if self._tabs.currentIndex() == 0:
            c = self._win_tab.selected()
            if not c:
                QMessageBox.warning(self, "Selección requerida",
                                    "Selecciona un certificado de la lista.")
                return
            self._result = {
                "type": "windows",
                "thumbprint": c["thumbprint"],
                "name": c["name"],
                "nif": c.get("nif", ""),
            }
            save_cert(self._result)
        else:
            tab = self._file_tab
            if not tab.cert_path or not os.path.exists(tab.cert_path):
                QMessageBox.warning(self, "Certificado requerido",
                                    "Selecciona un archivo de certificado válido.")
                return
            self._result = {
                "type": "file",
                "path": tab.cert_path,
                "password": tab.password,
            }
            if tab.remember:
                save_cert(self._result)
        self.accept()

    @property
    def cert_info(self) -> dict:
        return self._result
