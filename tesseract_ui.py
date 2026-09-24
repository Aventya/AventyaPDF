"""
Parte Qt de tesseract_setup: instalación forzada con diálogo de progreso.

La instalación y las descargas corren en un QThread (pueden tardar minutos);
el diálogo es modal y sin «Cancelar»: Tesseract es obligatorio.
"""
from PyQt6.QtCore import QEventLoop, Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import QMessageBox, QProgressDialog

import tesseract_setup as ts


class _Worker(QThread):
    progress = pyqtSignal(str)

    def __init__(self, fn):
        super().__init__()
        self._fn = fn
        self.result = None
        self.error: BaseException | None = None

    def run(self):
        try:
            self.result = self._fn(self.progress.emit)
        except BaseException as e:  # noqa: BLE001 — se relanza en el hilo principal
            self.error = e


def _run_with_progress(parent, title: str, text: str, fn):
    dlg = QProgressDialog(text, None, 0, 0, parent)
    dlg.setWindowTitle(title)
    dlg.setCancelButton(None)
    dlg.setWindowModality(Qt.WindowModality.ApplicationModal)
    dlg.setMinimumDuration(0)
    dlg.setMinimumWidth(420)
    worker = _Worker(fn)
    worker.progress.connect(dlg.setLabelText)
    loop = QEventLoop()
    worker.finished.connect(loop.quit)
    dlg.show()
    worker.start()
    loop.exec()
    worker.wait()
    dlg.close()
    if worker.error is not None:
        raise worker.error
    return worker.result


def ensure_at_startup(parent=None) -> tuple[bool, str]:
    """Comprueba Tesseract al iniciar y, si falta, lo instala a la fuerza.
    Devuelve (disponible, motivo si no lo está)."""
    ts.configure_environment()
    if ts.status(ts.CORE_LANGS).ready:
        return True, ""
    try:
        _run_with_progress(
            parent, "Tesseract OCR",
            "Tesseract OCR es obligatorio en AventyaPDF y no está instalado.\n"
            "Preparando la instalación…",
            lambda report: ts.ensure(ts.CORE_LANGS, report))
        return True, ""
    except Exception as e:  # noqa: BLE001
        reason = str(e) or type(e).__name__
    QMessageBox.warning(
        parent, "Tesseract OCR",
        "No se pudo instalar Tesseract OCR, necesario para reconocer texto.\n\n"
        f"{reason}\n\n"
        "AventyaPDF se abrirá con «Reconocer texto (OCR)» desactivado y "
        "volverá a instalarlo en el próximo inicio.")
    return False, reason


def ensure_languages(parent, langs) -> bool:
    """Antes de reconocer texto: Tesseract y los idiomas elegidos, instalando lo
    que falte. Devuelve False (tras avisar) si no se pudo."""
    ts.configure_environment()
    st = ts.status(langs)
    if st.ready:
        return True
    what = ("Instalando Tesseract OCR…" if not st.exe
            else f"Descargando idiomas de OCR: {', '.join(st.missing_langs)}…")
    try:
        _run_with_progress(parent, "Reconocer texto (OCR)", what,
                           lambda report: ts.ensure(langs, report))
        return True
    except Exception as e:  # noqa: BLE001
        QMessageBox.warning(parent, "Reconocer texto (OCR)",
                            f"No se pudo preparar el OCR.\n\n{e}")
        return False
