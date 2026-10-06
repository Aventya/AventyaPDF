"""
window_document.py
Mixin de MainWindow con el ciclo de vida del documento:
abrir / guardar / cerrar, deshacer y rehacer, estado «modificado»,
búsqueda, navegación, zoom por pasos, API del panel lateral, creación de
notas / marcado de texto / redacciones y firma digital en segundo plano.

Modelo de documento (ver MEMORIA_EVOLUTIVA §4):
  · El PDF se abre SIEMPRE desde bytes (`fitz.open("pdf", data)`), nunca desde
    la ruta: así no queda el archivo bloqueado en Windows y se puede guardar
    encima de él (escritura a temporal + os.replace).
  · `_clean_bytes` son los bytes tal cual están en disco. Mientras no haya
    cambios, guardar y firmar usan esos bytes sin reescribir el PDF, lo que
    conserva la validez de las firmas existentes.
  · (r61) `_pending_bytes`: una versión exacta aún sin guardar (quitar la
    última firma). Guardar y firmar la usan tal cual, sin reescribir; cualquier
    otra edición (mark_modified) la descarta y se vuelve a lo normal.
"""
import hashlib
import os
import traceback

import fitz
from PyQt6.QtCore import Qt, QSettings, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QInputDialog, QLineEdit, QMessageBox,
    QProgressDialog,
)

import conversion_office
import dependencias
import dialogs
import doc_tools
import icons
from cert_manager import CertPickerDialog, load_saved_cert
from history import Snapshot, UndoStack
from tsa import TSA_PRESETS
import idioma
from idioma import tr

SETTINGS = ("aventyapdf", "config")
MAX_RECENT = 10
USER_NAME = os.environ.get("USERNAME") or os.environ.get("USER") or ""

MARKUP_COLORS = doc_tools.MARKUP_COLORS
FREEHAND_PREFIX = doc_tools.FREEHAND_PREFIX
MARKUP_LABELS = {"highlight": tr("Resaltar"), "underline": tr("Subrayar"),
                 "strike": tr("Tachar"), "squiggly": tr("Subrayado ondulado")}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp"}


class SignWorker(QThread):
    """Ejecuta la firma fuera del hilo de interfaz (el sellado de tiempo hace
    una petición de red y la firma con claves grandes tarda)."""
    succeeded = pyqtSignal(bytes)
    failed = pyqtSignal(str)

    def __init__(self, kwargs: dict, parent=None):
        super().__init__(parent)
        self._kwargs = kwargs

    def run(self):
        # (r131) pyHanko se carga al firmar, no al arrancar la aplicación.
        from signer_backend import PAdESSigner, SigningError
        try:
            self.succeeded.emit(PAdESSigner.sign_pdf_bytes(**self._kwargs))
        except SigningError as e:
            self.failed.emit(str(e))
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            self.failed.emit(str(e) or e.__class__.__name__)


class ValidateWorker(QThread):
    """(r61) Verifica las firmas en segundo plano: el panel Firmas muestra el
    resultado solo, sin botón, y la comprobación de confianza puede tardar."""
    done = pyqtSignal(object, int)          # (lista de SignatureReport | str de error, turno)

    def __init__(self, data: bytes, password: str, turn: int, parent=None):
        super().__init__(parent)
        self._data, self._password, self._turn = data, password, turn

    def run(self):
        try:
            from signature_validation import validate_signatures
            self.done.emit(validate_signatures(self._data, self._password), self._turn)
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            self.done.emit(str(e) or e.__class__.__name__, self._turn)


# Estado de cada documento abierto (pestañas). El activo vive en los atributos
# de la ventana; los demás, en MainWindow._sessions. El zoom es de la ventana.
_SESSION_ATTRS = ("doc", "pdf_path", "current_page", "_history", "_modified",
                  "_password", "_orig_encrypted", "_encrypt_opts", "_clean_bytes",
                  "_pending_bytes", "_disk_stat", "_disk_ignored")


def _file_stat(path: str) -> tuple | None:
    try:
        st = os.stat(path)
    except OSError:
        return None
    return (st.st_size, st.st_mtime_ns)


class DocumentMixin:

    # ── estado ─────────────────────────────────────────────────────────── #

    def _init_document_state(self):
        self._history = UndoStack()
        self._modified = False
        self._password = ""
        self._orig_encrypted = False
        self._encrypt_opts: dict | None = None
        self._clean_bytes: bytes | None = None
        self._pending_bytes: bytes | None = None
        # (r115) Cambios del archivo hechos desde otra aplicación: tamaño y
        # fecha del disco la última vez que se miró, y el resumen de una
        # versión del disco que el usuario ya decidió no cargar.
        self._disk_stat: tuple | None = None
        self._disk_ignored: str | None = None
        self._checking_disk = False
        QApplication.instance().applicationStateChanged.connect(self._on_app_state)
        # Con la ventana a la vista pero sin foco (al lado de la otra
        # aplicación), se mira cada poco sin pedirle nada al usuario.
        self._disk_timer = QTimer(self)
        self._disk_timer.setInterval(1500)
        self._disk_timer.timeout.connect(self._poll_disk)
        self._disk_timer.start()
        self._find_hits: list = []
        self._find_idx = -1
        self._find_text = ""
        # (r50) Búsqueda dinámica: no hace falta pulsar Intro. Un pequeño
        # retardo evita relanzar la búsqueda en cada pulsación al escribir rápido.
        self._find_live_timer = QTimer(self)
        self._find_live_timer.setSingleShot(True)
        self._find_live_timer.setInterval(250)
        self._find_live_timer.timeout.connect(lambda: self._find_step(0))
        self._sign_worker: SignWorker | None = None
        self._sessions: list[dict] = []    # un estado por documento abierto (_SESSION_ATTRS)
        self._active = -1                  # índice del documento activo en _sessions

    def _update_title(self):
        if self.doc is None:
            self.setWindowTitle("AventyaPDF")
        else:
            name = os.path.basename(self.pdf_path) if self.pdf_path else tr("Sin título")
            modified = self._modified
            self.setWindowTitle(tr("{valor}{name} — AventyaPDF").format(valor='● ' if modified else '', name=name))
        self._refresh_doc_tabs()

    def _update_actions(self):
        has = self.doc is not None
        for a in getattr(self, "_doc_actions", []):
            a.setEnabled(has)
        if hasattr(self, "_zoom_status_box"):
            self._zoom_status_box.setEnabled(has)
        if hasattr(self, "_act_ocr"):          # OCR: además hace falta Tesseract
            self._act_ocr.setEnabled(has and getattr(self, "ocr_available", True))
        can_u = has and self._history.can_undo()
        can_r = has and self._history.can_redo()
        if hasattr(self, "_act_undo"):
            lu, lr = self._history.undo_label(), self._history.redo_label()
            self._act_undo.setEnabled(can_u)
            self._act_undo.setText(tr("Deshacer «{lu}»").format(lu=lu) if can_u and lu else tr("Deshacer"))
            self._act_redo.setEnabled(can_r)
            self._act_redo.setText(tr("Rehacer «{lr}»").format(lr=lr) if can_r and lr else tr("Rehacer"))
        if hasattr(self, "_btn_undo"):
            self._btn_undo.setEnabled(can_u)
            self._btn_redo.setEnabled(can_r)

    # ── varios documentos (pestañas del panel lateral) ─────────────────── #

    def _reset_document_fields(self):
        self.doc = None
        self.pdf_path = ""
        self.current_page = 0
        self._history = UndoStack()
        self._modified = False
        self._password = ""
        self._orig_encrypted = False
        self._encrypt_opts = None
        self._clean_bytes = None
        self._pending_bytes = None
        self._disk_stat = None
        self._disk_ignored = None

    def _session(self, index: int) -> dict:
        """Estado del documento `index` (el activo, leído en vivo)."""
        if index != self._active:
            return self._sessions[index]
        s = {k: getattr(self, k) for k in _SESSION_ATTRS}
        s["_scroll_pos"] = (self._scroll.horizontalScrollBar().value(),
                            self._scroll.verticalScrollBar().value())
        return s

    def _session_dirty(self, index: int) -> bool:
        return bool(self._session(index).get("_modified"))

    def _session_index_for(self, path: str) -> int | None:
        key = os.path.normcase(os.path.abspath(path))
        for i in range(len(self._sessions)):
            p = self._session(i).get("pdf_path")
            if p and os.path.normcase(os.path.abspath(p)) == key:
                return i
        return None

    def _stash_active(self):
        """Guarda el documento activo en su pestaña y libera la vista."""
        self.viewer.forms.close_editor(commit=True)
        self.viewer.close_text_editor(commit=True)
        self.viewer.content.clear()
        self._finish_action()
        self._find_bar.hide()
        self._btn_find.show()
        self._clear_find()
        self._sessions[self._active] = self._session(self._active)

    def _begin_new_session(self):
        """Antes de cargar otro documento: el actual sigue abierto en su pestaña."""
        if self.doc is None:
            return
        self._stash_active()
        self._reset_document_fields()
        self._active = -1                       # _set_document registra la pestaña nueva

    def switch_document(self, index: int):
        if not 0 <= index < len(self._sessions) or index == self._active:
            return
        if self._sign_worker is not None and self._sign_worker.isRunning():
            self.statusBar().showMessage(tr("Espera a que termine la firma en curso"))
            return
        self._stash_active()
        self._restore_session(index)
        self.check_disk_changes()

    def _restore_session(self, index: int):
        s = self._sessions[index]
        for k in _SESSION_ATTRS:
            setattr(self, k, s[k])
        self._active = index
        v = self.viewer
        v._sel = None
        v._words = None
        v.pdf_page = None
        v.clear_text_selection()
        self._hide_annot_opts()
        self.render_page()
        self.sidebar.set_document()
        self._update_doc_notice()
        self._update_actions()
        self._update_title()
        h, y = s.get("_scroll_pos", (0, 0))
        QTimer.singleShot(0, lambda: (self._scroll.horizontalScrollBar().setValue(h),
                                      self._scroll.verticalScrollBar().setValue(y)))
        name = os.path.basename(self.pdf_path) if self.pdf_path else tr("Sin título")
        self.statusBar().showMessage(tr("Documento: {name}").format(name=name))

    def next_document(self, step: int = 1):
        if len(self._sessions) > 1:
            self.switch_document((self._active + step) % len(self._sessions))

    def close_document_at(self, index: int):
        self.switch_document(index)
        if index == self._active:
            self.close_document()

    def move_document(self, src: int, dst: int):
        """(r123) Pestaña `src` arrastrada con el ratón a la posición `dst`.
        Solo cambia el orden: el documento activo sigue siendo el mismo."""
        n = len(self._sessions)
        if not (0 <= src < n and 0 <= dst < n) or src == dst:
            return
        order = list(range(n))
        order.insert(dst, order.pop(src))
        self._sessions = [self._sessions[i] for i in order]
        if self._active >= 0:
            self._active = order.index(self._active)
        self._refresh_doc_tabs()

    def _refresh_doc_tabs(self):
        if not hasattr(self, "sidebar"):
            return
        items = []
        for i in range(len(self._sessions)):
            s = self._session(i)
            path = s.get("pdf_path") or ""
            items.append((os.path.basename(path) if path else tr("Sin título"), path,
                          self._session_dirty(i)))
        self.sidebar.set_documents(items, self._active)

    # ── abrir / cerrar ─────────────────────────────────────────────────── #

    def open_pdf(self):
        start = QSettings(*SETTINGS).value("recent/dir", "")
        instalada = dependencias.carpeta_instalada()
        if not start and instalada:
            # (r103, petición de Ricardo) Antes de haber abierto nunca nada
            # —sin carpeta reciente todavía—, que el manual salga ya
            # seleccionado en el propio diálogo, no solo en su carpeta:
            # pasarle la ruta del archivo, no solo la de la carpeta, hace
            # que Qt lo abra ahí y lo deje resaltado.
            # (r138) Uno por idioma, en la carpeta manual\.
            manual = dependencias.ruta_manual(idioma.ACTUAL)
            if manual:
                start = manual
        # (r123, petición de Ricardo) Siempre se pueden elegir varios archivos,
        # de todo lo que la aplicación sabe mostrar: cada PDF en su pestaña, y
        # cada imagen o documento de Word convertido a PDF en la suya (sin guardar).
        paths, _ = QFileDialog.getOpenFileNames(
            self, tr("Abrir"), start, conversion_office.FILTRO_ABRIR)
        self.open_paths(paths)

    def open_paths(self, paths: list[str]):
        """Abre cada PDF en su pestaña; las imágenes y los Word, convertidos."""
        otros = []
        for p in paths:
            tipo = conversion_office.tipo_de(p)
            if tipo == "pdf":
                self.open_path(p, confirmed=True)
            elif tipo:
                otros.append(p)
        if otros:
            self.convert_files_to_pdfs(otros)

    def open_path(self, path: str, confirmed: bool = False) -> bool:
        # (r20) Cada PDF se abre en su propia pestaña; `confirmed` ya no se usa.
        already = self._session_index_for(path)
        if already is not None:                 # ya estaba abierto: se pasa a su pestaña
            self.switch_document(already)
            # (r115) …y si el archivo cambió desde otra aplicación, se lee de nuevo.
            self.check_disk_changes(force=True)
            return True
        name = os.path.basename(path)
        try:
            with open(path, "rb") as f:
                data = f.read()
            doc = fitz.open("pdf", data)
        except Exception as e:
            QMessageBox.warning(self, tr("No se pudo abrir"),
                                tr("«{name}» no es un PDF válido o está dañado.\n\n{e}").format(name=name, e=e))
            return False
        password = self._ask_password(doc, name)
        if password is None:
            doc.close()
            return False
        if len(doc) == 0:
            doc.close()
            QMessageBox.warning(self, tr("No se pudo abrir"), tr("«{name}» no contiene páginas.").format(name=name))
            return False
        self._begin_new_session()
        self._set_document(doc, path, data, password)
        self._disk_stat = _file_stat(path)
        self._add_recent(path)
        self.statusBar().showMessage(tr("Abierto: {name}  ·  {n} páginas").format(name=name, n=len(doc)))
        return True

    def _ask_password(self, doc, name: str, known: str = "") -> str | None:
        """Contraseña del PDF («» si no tiene); None si el usuario cancela."""
        if not doc.needs_pass:
            return ""
        if known and doc.authenticate(known):
            return known
        while True:
            pw, ok = QInputDialog.getText(
                self, tr("Documento protegido"),
                tr("«{name}» está protegido con contraseña.\nContraseña:").format(name=name),
                QLineEdit.EchoMode.Password)
            if not ok:
                return None
            if doc.authenticate(pw):
                return pw
            QMessageBox.warning(self, tr("Documento protegido"), tr("Contraseña incorrecta."))

    # ── cambios del archivo desde otra aplicación (r115) ───────────────── #

    def _on_app_state(self, state):
        if state == Qt.ApplicationState.ApplicationActive:
            QTimer.singleShot(0, self.check_disk_changes)

    def _poll_disk(self):
        if QApplication.applicationState() != Qt.ApplicationState.ApplicationActive:
            self.check_disk_changes(ask=False)

    def check_disk_changes(self, force: bool = False, ask: bool = True):
        """(r115, petición de Ricardo: «cuando se tiene un PDF abierto y se
        modifica desde otra aplicación… ni te actualiza la vista… debe leer
        que tiene otros bytes») Si el archivo del documento activo tiene en el
        disco otros bytes que los que se leyeron, se vuelve a leer en la misma
        pestaña; con cambios sin guardar, se pregunta antes. Se mira al volver
        a la ventana, al cambiar de pestaña y al abrir otra vez el mismo
        archivo. El tamaño y la fecha evitan leerlo entero cada vez: si no han
        cambiado (y no es `force`), no se lee. Sin `ask` (mientras se usa otra
        aplicación) solo se recarga lo que no necesita preguntar nada: con
        cambios sin guardar se espera a que se vuelva a la ventana."""
        if not ask and (self._modified or self._pending_bytes is not None):
            return
        if (self._checking_disk or self.doc is None or not self.pdf_path
                or self._clean_bytes is None
                or (self._sign_worker is not None and self._sign_worker.isRunning())):
            return
        st = _file_stat(self.pdf_path)
        if st is None or (st == self._disk_stat and not force):
            return
        try:
            with open(self.pdf_path, "rb") as f:
                data = f.read()
        except OSError:
            return
        self._disk_stat = st
        firma = hashlib.sha256(data).hexdigest()
        if data == self._clean_bytes or firma == self._disk_ignored:
            return
        self._checking_disk = True
        try:
            self._reload_changed(data, firma, ask)
        finally:
            self._checking_disk = False

    def _reload_changed(self, data: bytes, firma: str, ask: bool = True):
        name = os.path.basename(self.pdf_path)
        # Lo que se esté escribiendo en un campo o en un cuadro de texto
        # cuenta como cambio sin guardar.
        self.viewer.forms.close_editor(commit=True)
        self.viewer.close_text_editor(commit=True)
        if (self._modified or self._pending_bytes is not None) \
                and not self._ask_reload_over_changes(name):
            self._disk_ignored = firma
            self.statusBar().showMessage(
                tr("«{name}» ha cambiado en otra aplicación: se mantienen tus cambios").format(name=name))
            return
        try:
            doc = fitz.open("pdf", data)
        except Exception:
            # A medio escribir por la otra aplicación: se reintenta la próxima vez.
            self._disk_stat = None
            return
        if not ask and doc.needs_pass and not doc.authenticate(self._password):
            doc.close()                         # ya se pedirá la contraseña al volver
            self._disk_stat = None
            return
        password = self._ask_password(doc, name, self._password)
        if password is None or len(doc) == 0:
            doc.close()
            self._disk_ignored = firma
            return
        page = self.current_page
        stat = self._disk_stat
        self._set_document(doc, self.pdf_path, data, password)
        self._disk_stat = stat
        self.go_to_page(min(page, len(doc) - 1))
        self.statusBar().showMessage(
            tr("«{name}» ha cambiado en otra aplicación: se muestra la versión nueva").format(name=name))

    def _ask_reload_over_changes(self, name: str) -> bool:
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle(tr("El archivo ha cambiado"))
        box.setText(tr("«{name}» se ha modificado en otra aplicación, y aquí tiene "
                    "cambios sin guardar.").format(name=name))
        box.setInformativeText(tr("¿Cargar la versión nueva del archivo? Se perderán tus cambios."))
        b_load = box.addButton(tr("Cargar la versión nueva"), QMessageBox.ButtonRole.DestructiveRole)
        box.addButton(tr("Mantener mis cambios"), QMessageBox.ButtonRole.RejectRole)
        box.exec()
        return box.clickedButton() is b_load

    def _set_document(self, doc, path: str, clean_bytes: bytes | None,
                      password: str = "", modified: bool = False,
                      pending: bytes | None = None):
        if self._active < 0:                    # primer documento o pestaña nueva
            self._sessions.append({})
            self._active = len(self._sessions) - 1
        old = self.doc
        self.doc = doc
        if old is not None and old is not doc:
            try:
                old.close()
            except Exception:
                pass
        self.pdf_path = path or ""
        self._clean_bytes = clean_bytes
        self._pending_bytes = pending
        self._disk_stat = None
        self._disk_ignored = None
        self._password = password
        self._orig_encrypted = bool((doc.metadata or {}).get("encryption"))
        self._encrypt_opts = None
        self._history.clear()
        self._modified = modified
        self.current_page = 0
        self._clear_find()
        v = self.viewer
        v._sel = None
        v._words = None
        v.clear_text_selection()
        self._finish_action()
        self.render_page()
        self.sidebar.set_document()
        # (r77, petición de Ricardo: «este visor de firmas certificadas
        # siempre se debe mostrar abierto en cuanto se abra un PDF que
        # traiga una firma certificada en su interior») A diferencia de
        # «thumbs» (que solo se abre si el panel lateral estaba cerrado),
        # Firmas certificadas se abre siempre que el documento esté firmado,
        # aunque el panel ya mostrara otra cosa.
        if doc_tools.signed_count(doc):
            self.sidebar.show_panel("signatures")
        elif (not self.sidebar.stack.isVisible()
                and QSettings(*SETTINGS).value("view/sidebar", "true") == "true"):
            self.sidebar.show_panel("thumbs")
        self._update_doc_notice()
        self._update_actions()
        self._update_title()

    def close_document(self):
        if self.doc is None or not self._confirm_discard():
            return
        self.doc.close()
        self._reset_document_fields()
        index = self._active
        if 0 <= index < len(self._sessions):
            del self._sessions[index]
        self._active = -1
        if self._sessions:                      # quedan documentos: se pasa al contiguo
            self._restore_session(min(index, len(self._sessions) - 1))
            self.statusBar().showMessage(tr("Documento cerrado"))
            return
        self._clear_find()
        v = self.viewer
        v._sel = None
        v.pdf_page = None
        v._words = None
        v.clear_text_selection()
        v.setPixmap(QPixmap())
        v.resize(0, 0)
        self._page_edit.setText("")
        self._lbl_page.setText("/ —")
        self._finish_action()
        self.sidebar.set_document()
        self._update_doc_notice()
        self._update_actions()
        self._update_title()
        self.statusBar().showMessage(tr("Documento cerrado"))

    def _confirm_discard(self) -> bool:
        if self.doc is None or not self._modified:
            return True
        name = os.path.basename(self.pdf_path) if self.pdf_path else tr("Sin título")
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle(tr("Cambios sin guardar"))
        box.setText(tr("¿Quieres guardar los cambios de «{name}»?").format(name=name))
        b_save = box.addButton(tr("Guardar"), QMessageBox.ButtonRole.AcceptRole)
        b_discard = box.addButton(tr("No guardar"), QMessageBox.ButtonRole.DestructiveRole)
        box.addButton(tr("Cancelar"), QMessageBox.ButtonRole.RejectRole)
        box.exec()
        clicked = box.clickedButton()
        if clicked is b_save:
            return self.save_pdf()
        return clicked is b_discard

    def closeEvent(self, event):
        if self._sign_worker is not None and self._sign_worker.isRunning():
            self.statusBar().showMessage(tr("Espera a que termine la firma en curso"))
            event.ignore()
            return
        # Cada documento con cambios pregunta, mostrando antes su pestaña.
        dirty = [i for i in range(len(self._sessions)) if self._session_dirty(i)]
        for i in dirty:
            self.switch_document(i)
            if not self._confirm_discard():
                event.ignore()
                return
        event.accept()

    # ── arrastrar y soltar ─────────────────────────────────────────────── #

    @staticmethod
    def _drop_kind(path: str) -> str:
        ext = os.path.splitext(path)[1].lower()
        return "pdf" if ext == ".pdf" else "img" if ext in IMAGE_EXTS else ""

    def dragEnterEvent(self, event):
        md = event.mimeData()
        if md.hasUrls() and any(self._drop_kind(u.toLocalFile()) for u in md.urls()):
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = [u.toLocalFile() for u in event.mimeData().urls()]
        pdfs = [p for p in paths if self._drop_kind(p) == "pdf"]
        imgs = [p for p in paths if self._drop_kind(p) == "img"]
        event.acceptProposedAction()
        if pdfs:                                # (r123) todos, no solo el primero
            QTimer.singleShot(0, lambda: [self.open_path(p) for p in pdfs])
        elif imgs:
            QTimer.singleShot(0, lambda: self.create_from_images(imgs))

    # ── recientes ──────────────────────────────────────────────────────── #

    def _recent(self) -> list[str]:
        v = QSettings(*SETTINGS).value("recent/files", [])
        if isinstance(v, str):
            v = [v]
        return [p for p in (v or []) if isinstance(p, str) and p]

    def _add_recent(self, path: str):
        path = os.path.abspath(path)
        files = [p for p in self._recent() if os.path.normcase(p) != os.path.normcase(path)]
        files.insert(0, path)
        s = QSettings(*SETTINGS)
        s.setValue("recent/files", files[:MAX_RECENT])
        s.setValue("recent/dir", os.path.dirname(path))

    def _fill_recent_menu(self):
        m = self._menu_recent
        m.clear()
        files = self._recent()
        for p in files:
            act = m.addAction(os.path.basename(p))
            act.setToolTip(p)
            act.setStatusTip(p)
            act.setEnabled(os.path.exists(p))
            act.triggered.connect(lambda _c=False, x=p: self.open_path(x))
        if not files:
            m.addAction(tr("(vacío)")).setEnabled(False)
        else:
            m.addSeparator()
            m.addAction(tr("Borrar lista")).triggered.connect(
                lambda: QSettings(*SETTINGS).setValue("recent/files", []))

    # ── guardar ────────────────────────────────────────────────────────── #

    def save_pdf(self) -> bool:
        if self.doc is None:
            return False
        if not self.pdf_path:
            return self.save_pdf_as()
        return self._write_to(self.pdf_path)

    def save_pdf_as(self) -> bool:
        if self.doc is None:
            return False
        suggested = self.pdf_path or os.path.join(
            QSettings(*SETTINGS).value("recent/dir", ""), "documento.pdf")
        path, _ = QFileDialog.getSaveFileName(self, tr("Guardar como"), suggested,
                                              tr("Archivos PDF (*.pdf)"))
        if not path:
            return False
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        return self._write_to(path)

    def _write_to(self, path: str) -> bool:
        exactos = self._pending_bytes is not None and not self._encrypt_opts
        if self._modified and not exactos and doc_tools.has_signatures(self.doc):
            r = QMessageBox.warning(
                self, tr("Documento firmado"),
                tr("Este documento contiene firmas digitales.\n\n"
                "Guardar los cambios reescribe el archivo y las firmas existentes "
                "dejarán de ser válidas. Para conservarlas, firma sin modificar "
                "antes el documento.\n\n¿Guardar de todos modos?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if r != QMessageBox.StandardButton.Yes:
                return False
        tmp = path + ".agtmp"
        try:
            if exactos:                  # (r61) versión exacta: sin reescribir
                data = self._pending_bytes
            elif not self._modified and self._clean_bytes is not None and not self._encrypt_opts:
                data = self._clean_bytes
            else:
                kw = dict(garbage=3, deflate=True)
                if self._encrypt_opts:
                    kw.update(self._encrypt_opts)
                elif self._orig_encrypted:
                    kw["encryption"] = fitz.PDF_ENCRYPT_KEEP
                data = doc_tools.bytes_with_subset_fonts(self.doc, kw, self._password)
            with open(tmp, "wb") as f:
                f.write(data)
            os.replace(tmp, path)
        except Exception as e:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:
                pass
            QMessageBox.critical(self, tr("Error al guardar"),
                                 tr("No se pudo guardar el archivo:\n{e}").format(e=e))
            return False

        if self._encrypt_opts:
            # La seguridad nueva se ha aplicado al escribir: se reabre lo
            # guardado para que el estado en memoria coincida con el disco.
            opts = self._encrypt_opts
            pw = opts.get("owner_pw") or opts.get("user_pw") or ""
            page = self.current_page
            doc = fitz.open("pdf", data)
            if doc.needs_pass:
                doc.authenticate(pw)
            self._set_document(doc, path, data, pw)
            self.go_to_page(page)
        else:
            self.pdf_path = path
            self._clean_bytes = data
            self._pending_bytes = None
            self._modified = False
            self._disk_stat = _file_stat(path)
        self._add_recent(path)
        self._update_title()
        self.statusBar().showMessage(tr("Guardado: {nombre}").format(nombre=os.path.basename(path)))
        return True

    # ── deshacer / rehacer ─────────────────────────────────────────────── #

    def _doc_bytes(self) -> bytes:
        if self._orig_encrypted and not self._encrypt_opts:
            return self.doc.tobytes(encryption=fitz.PDF_ENCRYPT_KEEP)
        return self.doc.tobytes()

    def _open_bytes(self, data: bytes):
        doc = fitz.open("pdf", data)
        if doc.needs_pass and self._password:
            doc.authenticate(self._password)
        return doc

    def checkpoint(self, label: str = ""):
        """Llamar ANTES de modificar el documento."""
        if self.doc is None:
            return
        try:
            self._history.push(Snapshot(self._doc_bytes(), self.current_page, label))
        except Exception as e:
            print(f"[deshacer] no se pudo guardar el estado: {e}")
        self._update_actions()

    def mark_modified(self, structure: bool = False):
        """Llamar DESPUÉS de modificar el documento."""
        self._modified = True
        self._pending_bytes = None      # (r61) ya no es la versión exacta
        self._find_text = ""          # la próxima búsqueda se recalcula
        if structure:
            self._find_hits = []
            self._find_idx = -1
        self.viewer._words = None
        self.sidebar.doc_changed(structure)
        self._update_title()
        self._update_actions()

    def replace_document(self, data: bytes, label: str, page: int | None = None):
        """Sustituye el documento por otra versión (organizar, OCR…) con deshacer."""
        new = self._open_bytes(data)
        self.checkpoint(label)
        old = self.doc
        self.doc = new
        old.close()
        self.current_page = max(0, min(self.current_page if page is None else page, len(new) - 1))
        self.viewer._sel = None
        self.mark_modified(structure=True)
        self.render_page()
        self.sidebar.set_document()
        self._update_doc_notice()

    def undo(self):
        self._step_history(self._history.undo, tr("Deshecho"))

    def redo(self):
        self._step_history(self._history.redo, tr("Rehecho"))

    def _step_history(self, step, verb: str):
        if self.doc is None:
            return
        if self._sign_worker is not None and self._sign_worker.isRunning():
            return
        snap = step(Snapshot(self._doc_bytes(), self.current_page, ""))
        if snap is None:
            return
        try:
            new = self._open_bytes(snap.data)
        except Exception as e:
            QMessageBox.critical(self, verb, tr("No se pudo restaurar el estado:\n{e}").format(e=e))
            return
        old = self.doc
        self.doc = new
        old.close()
        self.current_page = max(0, min(snap.page, len(new) - 1))
        v = self.viewer
        v._sel = None
        v._words = None
        v.clear_text_selection()
        self._hide_annot_opts()
        self._modified = True
        self._clear_find()
        self.render_page()
        self.sidebar.set_document()
        self._update_doc_notice()
        self._update_actions()
        self._update_title()
        self.statusBar().showMessage(f"{verb}: {snap.label}" if snap.label else verb)

    # ── búsqueda ───────────────────────────────────────────────────────── #

    def show_find(self):
        if self.doc is None:
            return
        # (r78, petición de Ricardo) El botón de búsqueda y la herramienta
        # ocupan el mismo sitio en la barra principal: nunca se ven los dos.
        self._btn_find.hide()
        self._find_bar.show()
        self._place_find_bar()          # flota sobre la barra, en la lupa
        self._find_edit.setFocus()
        self._find_edit.selectAll()

    def hide_find(self):
        self._find_bar.hide()
        self._btn_find.show()
        self._clear_find()
        self.viewer.update()
        self.viewer.setFocus()

    def _clear_find(self):
        self._find_live_timer.stop()
        self._find_hits = []
        self._find_idx = -1
        self._find_text = ""
        if hasattr(self, "_find_count"):
            self._find_count.setText("")

    def _on_find_text_changed(self, text: str) -> None:
        """(r50) Búsqueda dinámica: cada pulsación reprograma el temporizador
        (`_find_live_timer`), que al disparar llama a `_find_step(0)` — la
        misma ruta que ya usaba Intro, así que el resto de la lógica
        (recalcular, resaltar la primera coincidencia, contador) no cambia."""
        if not text.strip():
            self._clear_find()
            self.viewer.update()
            return
        self._find_live_timer.start()

    def find_next(self):
        self._find_step(+1)

    def find_prev(self):
        self._find_step(-1)

    def _find_step(self, direction: int):
        if self.doc is None:
            return
        if not self._find_bar.isVisible():
            self.show_find()
        text = self._find_edit.text().strip()
        if not text:
            return
        if text != self._find_text:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                self._find_hits = doc_tools.search_document(self.doc, text)
            finally:
                QApplication.restoreOverrideCursor()
            self._find_text = text
            if not self._find_hits:
                self._find_idx = -1
                self._find_count.setText(tr("Sin resultados"))
                self.viewer.update()
                return
            after = [i for i, (p, _r) in enumerate(self._find_hits) if p >= self.current_page]
            self._find_idx = after[0] if after else 0
        elif self._find_hits:
            self._find_idx = (self._find_idx + direction) % len(self._find_hits)
        else:
            return
        self._show_find_hit()

    def _show_find_hit(self):
        pno, r = self._find_hits[self._find_idx]
        if pno != self.current_page:
            self.go_to_page(pno)
        self.viewer.update()
        self._find_count.setText(tr("{valor} de {n}").format(valor=self._find_idx + 1, n=len(self._find_hits)))
        sr = self.viewer._to_screen_rect(r)
        QTimer.singleShot(0, lambda: self._scroll.ensureVisible(
            sr.center().x(), sr.center().y(), 80, 160))

    # ── navegación y zoom ──────────────────────────────────────────────── #

    def go_to_page(self, pno: int):
        if self.doc is None:
            return
        pno = max(0, min(int(pno), len(self.doc) - 1))
        if pno != self.current_page:
            self._cancel_crop()    # (r99) el recuadro es de la página que se deja
            self.current_page = pno
            self.render_page()

    def first_page(self):
        self.go_to_page(0)

    def last_page(self):
        if self.doc is not None:
            self.go_to_page(len(self.doc) - 1)

    def ask_go_to_page(self):
        if self.doc is None:
            return
        n, ok = QInputDialog.getInt(self, tr("Ir a página"), tr("Página (1–{n}):").format(n=len(self.doc)),
                                    self.current_page + 1, 1, len(self.doc))
        if ok:
            self.go_to_page(n - 1)

    def _on_page_edit(self):
        if self.doc is None:
            return
        try:
            n = int(self._page_edit.text().strip())
        except ValueError:
            n = self.current_page + 1
        self.go_to_page(n - 1)
        self._page_edit.setText(str(self.current_page + 1))
        self.viewer.setFocus()

    def zoom_step(self, direction: int):
        if self.doc is None:
            return
        pct = self.viewer.scale_factor * 100
        new = pct * 1.2 if direction > 0 else pct / 1.2
        self._set_custom_zoom(int(max(10, min(400, round(new)))))

    def zoom_actual(self):
        self._set_custom_zoom(100)

    def zoom_fit_width(self):
        self._zoom_mode_changed("width")

    def zoom_fit_page(self):
        self._zoom_mode_changed("height")

    def _set_custom_zoom(self, pct: int):
        if self.doc is None:
            return
        self.zoom_mode = "100"
        self.custom_zoom_pct = pct
        self._update_zoom_type_icon()      # (r48) icono según la acción libre
        sl = self._zoom_slider
        sl.blockSignals(True)
        if pct < sl.minimum():
            sl.setMinimum(max(10, pct))
        sl.setValue(pct)
        sl.setToolTip(tr("Zoom: {pct} %").format(pct=pct))
        sl.blockSignals(False)
        self.render_page(keep_selection=True)
        self.statusBar().showMessage(tr("Zoom {pct} %").format(pct=pct))
        self.statusBar().showMessage(tr("Zoom {pct} %").format(pct=pct))

    # ── API para el panel lateral ──────────────────────────────────────── #

    def _sync_splitter(self):
        # El ancho depende de la columna (panel u opciones de herramienta); la
        # preferencia guardada, solo de si el panel está abierto.
        visible = not self.sidebar.stack.isHidden()
        total = max(300, sum(self._splitter.sizes()))
        from sidebar import COLUMN_MIN
        side = self.sidebar.rail.maximumWidth() + (COLUMN_MIN if self.sidebar.is_open() else 0)
        self._splitter.setSizes([side, total - side])
        QSettings(*SETTINGS).setValue("view/sidebar", "true" if visible else "false")
        if self.doc is not None and self.zoom_mode in ("width", "height"):
            QTimer.singleShot(0, lambda: self.render_page(keep_selection=True))

    def select_annotation(self, pno: int, idx: int):
        if self.doc is None:
            return
        from viewer import AnnotSelection
        self._finish_action()
        self.go_to_page(pno)
        a = self.viewer._annot_by_idx(idx)
        if a is None:
            return
        r = self.viewer.annot_rect(a)
        self.viewer._sel = AnnotSelection(idx, r, fitz.Rect(r), a.type[1])
        self._show_annot_opts(a)
        self.viewer.update()

    def rotate_pages(self, pages: list[int], delta: int):
        if self.doc is None or not pages:
            return
        self.checkpoint(tr("Girar páginas"))
        doc_tools.rotate_pages(self.doc, pages, delta)
        self.mark_modified(structure=True)
        self.render_page()

    def rotate_current(self, delta: int):
        self.rotate_pages([self.current_page], delta)

    def crop_page(self, pno: int, rect: fitz.Rect):
        if self.doc is None:
            return
        self.checkpoint(tr("Recortar página"))
        doc_tools.crop_page(self.doc, pno, rect)
        self.mark_modified(structure=True)
        self.render_page()

    def delete_pages(self, pages: list[int]):
        if self.doc is None or not pages:
            return
        if len(set(pages)) >= len(self.doc):
            QMessageBox.warning(self, tr("No posible"), tr("El PDF debe conservar al menos una página."))
            return
        what = tr("la página {valor}").format(valor=pages[0] + 1) if len(pages) == 1 else tr("{n} páginas").format(n=len(pages))
        r = QMessageBox.question(self, tr("Eliminar páginas"), tr("¿Eliminar {what}?").format(what=what),
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r != QMessageBox.StandardButton.Yes:
            return
        self.checkpoint(tr("Eliminar páginas"))
        self.doc.delete_pages(sorted(set(pages)))
        self.current_page = min(self.current_page, len(self.doc) - 1)
        self.mark_modified(structure=True)
        self.render_page()

    def extract_pages(self, pages: list[int]):
        if self.doc is None or not pages:
            return
        base = os.path.splitext(self.pdf_path)[0] if self.pdf_path else "documento"
        path, _ = QFileDialog.getSaveFileName(self, tr("Guardar páginas extraídas"),
                                              base + "_extracto.pdf", tr("Archivos PDF (*.pdf)"))
        if not path:
            return
        new = doc_tools.extract_pages(self.doc, pages)
        try:
            new.save(path, garbage=3, deflate=True)
            self.statusBar().showMessage(tr("{n} páginas extraídas a {nombre}").format(n=len(pages), nombre=os.path.basename(path)))
        except Exception as e:
            QMessageBox.critical(self, tr("Extraer páginas"), tr("No se pudo guardar:\n{e}").format(e=e))
        finally:
            new.close()

    def duplicate_pages(self, pages: list[int]):
        """Una copia independiente detrás de cada página (r27). Se recorre de
        atrás adelante para que los índices no se muevan; `fullcopy_page` y no
        `select` con repetidos, que compartiría la página (invariante 22)."""
        if self.doc is None or not pages:
            return
        pages = sorted(set(pages))
        self.checkpoint(tr("Duplicar páginas"))
        for p in reversed(pages):
            to = p + 1 if p + 1 < len(self.doc) else -1
            if hasattr(self.doc, "fullcopy_page"):
                self.doc.fullcopy_page(p, to)
            else:
                self.doc.copy_page(p, to)
        copies = [p + i + 1 for i, p in enumerate(pages)]
        self.sidebar.thumbs.select_after_rebuild(copies)
        self.current_page = copies[0]
        self.mark_modified(structure=True)
        self.render_page()

    def move_pages(self, order: list[int], selected: list[int] | None = None):
        """Reordena el documento: `order[i]` es la página que queda en la
        posición i (arrastre de miniaturas, r27)."""
        if self.doc is None or sorted(order) != list(range(len(self.doc))):
            return
        if order == list(range(len(order))):
            return
        self.checkpoint(tr("Mover páginas"))
        self.doc.select(order)
        self.current_page = order.index(self.current_page)
        if selected is not None:
            self.sidebar.thumbs.select_after_rebuild(selected)
        self.mark_modified(structure=True)
        self.render_page()

    def insert_blank_after(self, pno: int):
        if self.doc is None:
            return
        ref = self.doc[pno].rect
        self.checkpoint(tr("Insertar página en blanco"))
        self.doc.new_page(pno + 1, width=ref.width, height=ref.height)
        self.current_page = pno + 1
        self.mark_modified(structure=True)
        self.render_page()

    def signature_bytes(self) -> bytes | None:
        """(r61) Bytes cuyas firmas se verifican: la versión exacta pendiente de
        guardar o la de disco (con otros cambios sin guardar, el panel avisa de
        que guardar reescribirá el archivo). Sin archivo aún, la de memoria."""
        if self.doc is None:
            return None
        if self._pending_bytes is not None:
            return self._pending_bytes
        if self._clean_bytes is not None:
            return self._clean_bytes
        return self._doc_bytes()

    def unsaved_rewrite(self) -> bool:
        """(r61) ¿Hay cambios que al guardar reescribirán el archivo (y
        dejarán de ser válidas las firmas)?"""
        return self._modified and self._pending_bytes is None

    def can_remove_signature(self) -> tuple[bool, str]:
        """(r61) ¿Se puede quitar la última firma ahora? (y por qué no)."""
        if self.doc is None:
            return False, ""
        if self._sign_worker is not None and self._sign_worker.isRunning():
            return False, tr("Espera a que termine la firma en curso")
        if self._modified and self._pending_bytes is None:
            return False, tr(("Guarda o descarta antes los cambios sin guardar: quitar una "
                           "firma parte de la versión del archivo"))
        if self._pending_bytes is None and self._clean_bytes is None:
            return False, tr("Guarda antes el documento")
        return True, ""

    def remove_last_signature(self, field_name: str) -> bool:
        """(r61) Quita la firma más reciente y deja su recuadro vacío para firmar
        de nuevo (signer_backend.remove_last_signature). El resultado queda como
        cambio sin guardar; al guardar se escriben esos bytes tal cual, así que
        las demás firmas siguen válidas. No pasa por deshacer: sus instantáneas
        son copias reescritas. Para arrepentirse, cerrar sin guardar."""
        ok, motivo = self.can_remove_signature()
        if not ok:
            if motivo:
                QMessageBox.information(self, tr("Quitar firma"), motivo)
            return False
        r = QMessageBox.question(
            self, tr("Quitar firma"),
            tr("¿Quitar la firma «{field_name}»?\n\n"
            "Su recuadro quedará vacío en el mismo sitio: haz clic en él para firmar "
            "de nuevo, con otro certificado si quieres. Las demás firmas no se tocan.\n\n"
            "El cambio no se guarda en el archivo hasta que guardes el documento.").format(field_name=field_name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if r != QMessageBox.StandardButton.Yes:
            return False
        origen = self._pending_bytes if self._pending_bytes is not None else self._clean_bytes
        from signer_backend import SigningError, remove_last_signature   # (r131) al usarse
        try:
            nuevo = remove_last_signature(origen, field_name, self._password)
            doc = self._open_bytes(nuevo)
        except (SigningError, Exception) as e:  # noqa: BLE001
            traceback.print_exc()
            QMessageBox.critical(self, tr("Quitar firma"), tr("No se pudo quitar la firma:\n{e}").format(e=e))
            return False
        page = min(self.current_page, len(doc) - 1)
        self._set_document(doc, self.pdf_path, self._clean_bytes, self._password,
                           modified=True, pending=nuevo)
        self.go_to_page(page)
        self.statusBar().showMessage(
            tr("Firma «{field_name}» quitada — sin guardar. Haz clic en su recuadro para firmar de nuevo").format(field_name=field_name))
        return True

    # ── anotaciones creadas desde el visor ─────────────────────────────── #

    def add_text_markup(self, rects: list, kind: str, color: tuple | None = None,
                        opacity: float = 1.0, quads: list | None = None):
        if self.doc is None or not rects:
            return
        page = self.doc[self.current_page]
        fn = {"highlight": page.add_highlight_annot, "underline": page.add_underline_annot,
              "strike": page.add_strikeout_annot, "squiggly": page.add_squiggly_annot}.get(kind)
        if fn is None:
            return
        self.checkpoint(MARKUP_LABELS.get(kind, tr("Marcar texto")))
        # (r105) `rects` como se ve la página. Se pasan como cuadriláteros sin
        # girar que conservan qué lado es «abajo» en la vista: el subrayado
        # va bajo el texto tal como se lee, también con la página girada.
        # `quads` (del visor, ya sin girar y en el sentido del renglón) manda.
        annot = fn(quads or [fitz.Rect(r).quad * page.derotation_matrix if page.rotation
                             else fitz.Rect(r) for r in rects])
        if annot is None:
            return
        annot.set_colors(stroke=color or MARKUP_COLORS[kind])
        annot.set_opacity(max(0.05, min(1.0, opacity)))        # (r41)
        if USER_NAME:
            annot.set_info(title=USER_NAME)
        annot.update()
        self.mark_modified()
        self.render_page()

    def add_freehand_markup(self, points: list, kind: str, color: tuple | None = None,
                            opacity: float = 1.0, width: float = 2.0):
        """(r59) Resaltar/subrayar/tachar/ondulado a mano alzada, sobre imágenes
        y demás objetos que no son texto: anotación Ink. El resaltado se funde
        en modo Multiply, como un rotulador: tiñe lo de debajo sin taparlo.
        El tipo queda en /Subj (FREEHAND_PREFIX + tipo) para que al
        seleccionarla el panel muestre el tipo con que se hizo."""
        if self.doc is None or len(points) < 2:
            return
        page = self.doc[self.current_page]
        self.checkpoint(tr("{get} a mano alzada").format(get=MARKUP_LABELS.get(kind, tr('Marcar'))))
        m = page.derotation_matrix                  # (r105) visto → sin girar
        annot = page.add_ink_annot([[tuple(fitz.Point(p) * m) for p in points]])
        annot.set_colors(stroke=color or MARKUP_COLORS.get(kind, (1.0, 0.92, 0.0)))
        annot.set_border(width=width)
        annot.set_opacity(max(0.05, min(1.0, opacity)))
        if kind == "highlight":
            annot.set_blendmode(fitz.PDF_BM_Multiply)
        annot.set_info(subject=FREEHAND_PREFIX + kind, title=USER_NAME or "")
        annot.update()
        self.mark_modified()
        self.render_page()

    def add_note(self, pt, text: str):
        if self.doc is None:
            return
        page = self.doc[self.current_page]
        self.checkpoint(tr("Nota"))
        annot = page.add_text_annot(doc_tools.unrotated_point(page, pt), text, icon="Comment")
        if page.rotation:
            # (r105) Icono derecho en una página girada: NoRotate lo deja sin
            # girar, anclado a su esquina superior izquierda.
            annot.set_flags(annot.flags | fitz.PDF_ANNOT_IS_NO_ROTATE)
        annot.set_colors(stroke=self.viewer.note_color)
        if USER_NAME:
            annot.set_info(title=USER_NAME)
        annot.update()
        self.mark_modified()
        self.render_page()

    def copy_selected_text(self):
        text = self.viewer._tsel_text
        if text:
            QApplication.clipboard().setText(text)
            self.statusBar().showMessage(tr("Copiados {n} caracteres").format(n=len(text)))

    # ── aviso del documento ───────────────────────────────────────────── #

    def _update_doc_notice(self):
        """(r101, petición de Ricardo: «cualquier aviso que esté preparado
        para abrir una barra de notificaciones debe visualizarse centrado
        en la barra de tareas») Formulario sin firmar y/o cifrado, centrado
        en la barra de estado (`_notice_box`) — sustituye al aviso superior
        (`_build_banner`, r46, retirado por no usarlo ya nada). El de firma
        no se anuncia aquí: vive en el panel lateral de Firmas certificadas
        (rail o menú), que `_set_document` abre siempre que el documento
        está firmado (r77)."""
        msgs = []
        if self.doc is not None:
            if self.doc.is_form_pdf and not doc_tools.signed_count(self.doc):
                msgs.append(tr("Este documento contiene campos de formulario: "
                            "haz clic en ellos para rellenarlos."))
            if self._orig_encrypted:
                msgs.append(tr("Documento protegido con cifrado."))
        self._notice_lbl.setText("   ·   ".join(msgs))
        self._notice_box.setVisible(bool(msgs))

    # ── firma digital ──────────────────────────────────────────────────── #

    def sign_in_field(self, field: dict) -> None:
        """(r38) Firmar en un campo de firma vacío del formulario: la firma va
        dentro de ese campo (con su nombre y su recuadro), como en Acrobat.

        (r39) Pide **siempre** el certificado: aquí no está la barra de la
        herramienta Firma, que enseña cuál se va a usar, así que si no se
        preguntase se firmaría en silencio con el de la sesión anterior."""
        self.statusBar().showMessage(tr("Firmando en el campo «{field}»…").format(field=field['name']))
        self.trigger_signature(fitz.Rect(field["rect"]), field_name=field["name"],
                               choose_cert=True)

    def trigger_signature(self, rect, field_name: str = "", choose_cert: bool = False):
        if self.doc is None:
            return
        if self._sign_worker is not None and self._sign_worker.isRunning():
            return
        try:
            self._do_signature(rect, field_name, choose_cert)
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, tr("Error inesperado"), tr("Error al preparar la firma:\n{e}").format(e=e))
            self._finish_action()

    def _do_signature(self, rect, field_name: str = "", choose_cert: bool = False):
        if rect.width < 20 or rect.height < 10:
            self.statusBar().showMessage(tr("Dibuja un área más grande para la firma"))
            return
        has_sigs = doc_tools.has_signatures(self.doc)
        if has_sigs and self._modified and self._pending_bytes is None:
            r = QMessageBox.warning(
                self, tr("Firmar documento"),
                tr("El documento ya contiene firmas y tiene cambios sin guardar.\n"
                "Si firmas ahora, esos cambios se incluirán y las firmas anteriores "
                "dejarán de ser válidas.\n\n¿Continuar?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if r != QMessageBox.StandardButton.Yes:
                self._finish_action()
                return

        # El certificado, lo primero: con `choose_cert` se pregunta siempre
        # (r39, recuadro de firma del PDF) y, si no, solo cuando no hay ninguno.
        cert = load_saved_cert()
        if choose_cert or not cert["type"]:
            picker = CertPickerDialog(self, saved_cert=cert)
            if not picker.exec():
                self._finish_action()
                return
            cert = picker.cert_info
            self._refresh_cert_label()

        if dialogs.SignOptionsDialog.skip_requested():
            opts = dialogs.SignOptionsDialog.saved()
        else:
            dlg = dialogs.SignOptionsDialog(self, has_sigs, TSA_PRESETS)
            if not dlg.exec():
                self._finish_action()
                return
            opts = dlg.values()

        # Invariante 1: único volteo a coordenadas PDF nativas (origen abajo),
        # con el giro y el origen de la CropBox (r104: páginas recortadas).
        page = self.current_page
        box = doc_tools.page_rect_to_pdf(self.doc[page], rect)

        base = (os.path.splitext(self.pdf_path)[0] if self.pdf_path else
                os.path.join(QSettings(*SETTINGS).value("recent/dir", ""), "documento"))
        out_path, _ = QFileDialog.getSaveFileName(
            self, tr("Guardar documento firmado"), base + tr("_firmado") + ".pdf", tr("Archivos PDF (*.pdf)"))
        if not out_path:
            self._finish_action()
            return
        if not out_path.lower().endswith(".pdf"):
            out_path += ".pdf"

        # (r108) Del almacén de Windows se firma con la clave donde está, sin
        # exportarla: vale también si no es exportable o está en un DNIe.
        if cert["type"] == "windows":
            pfx_path, pfx_pass, thumb = "", "", cert["thumbprint"]
        else:
            pfx_path, pfx_pass, thumb = cert["path"], cert["password"], ""

        # Sin cambios: se firman los bytes de disco (firma incremental pura,
        # conserva las firmas previas). (r61) Con una versión exacta pendiente
        # (firma quitada), esa. Con cambios: se serializa la memoria.
        if self._pending_bytes is not None:
            data = self._pending_bytes
        elif not self._modified and self._clean_bytes is not None:
            data = self._clean_bytes
        else:
            kw = {"encryption": fitz.PDF_ENCRYPT_KEEP} if self._orig_encrypted else {}
            data = self.doc.tobytes(garbage=1, deflate=True, **kw)

        progress = QProgressDialog(tr("Firmando el documento…"), tr("Cancelar"), 0, 0, self)
        progress.setCancelButton(None)
        progress.setWindowTitle(tr("Firma digital"))
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.show()

        worker = SignWorker(dict(
            pdf_bytes=data, pfx_path=pfx_path, pfx_password=pfx_pass,
            page_num=page, box=box, reason=opts["reason"], location=opts["location"],
            contact=opts["contact"], tsa_url=opts["tsa_url"], certify=opts["certify"],
            doc_password=self._password, field_name=field_name,
            windows_thumbprint=thumb), self)
        self._sign_worker = worker
        password = self._password

        def _cleanup():
            progress.close()

        def _finished():
            # Las señales succeeded/failed se emiten DENTRO de run(): el hilo
            # sigue vivo cuando llegan. Destruirlo ahí podía abortar con
            # «QThread: Destroyed while thread is still running».
            if self._sign_worker is worker:
                self._sign_worker = None
            worker.deleteLater()

        def _ok(signed: bytes):
            _cleanup()
            tmp = out_path + ".agtmp"
            try:
                with open(tmp, "wb") as f:
                    f.write(signed)
                os.replace(tmp, out_path)
            except Exception as e:
                QMessageBox.critical(self, tr("Error al guardar"),
                                     tr("El documento se firmó pero no se pudo guardar:\n{e}").format(e=e))
                return
            doc = fitz.open("pdf", signed)
            if doc.needs_pass and password:
                doc.authenticate(password)
            self._set_document(doc, out_path, signed, password)
            self.go_to_page(page)
            self._add_recent(out_path)
            self.sidebar.show_panel("signatures")
            extra = tr("\nIncluye sello de tiempo.") if opts["tsa_url"] else ""
            QMessageBox.information(self, tr("Firmado"),
                                    tr("Documento firmado y guardado en:\n{out_path}{extra}").format(out_path=out_path, extra=extra))
            self.statusBar().showMessage(tr("Firmado: {nombre}").format(nombre=os.path.basename(out_path)))

        def _fail(msg: str):
            _cleanup()
            QMessageBox.critical(
                self, tr("Error al firmar"),
                tr("No se pudo firmar el PDF.\n\n{msg}\n\n"
                "• Verifica que el certificado sea válido y no esté caducado.\n"
                "• Si usas un archivo .pfx, comprueba la contraseña.").format(msg=msg))
            self.statusBar().showMessage(tr("Error al firmar"))

        worker.succeeded.connect(_ok)
        worker.failed.connect(_fail)
        worker.finished.connect(_finished)
        self._finish_action()
        self.statusBar().showMessage(tr("Firmando… por favor espera"))
        worker.start()
