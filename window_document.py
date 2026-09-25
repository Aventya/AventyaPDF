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
import os
import traceback

import fitz
from PyQt6.QtCore import Qt, QSettings, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QInputDialog, QLineEdit, QMessageBox,
    QProgressDialog,
)

import dialogs
import doc_tools
import icons
from cert_manager import CertPickerDialog, export_windows_cert_to_pfx, load_saved_cert
from history import Snapshot, UndoStack
from signer_backend import PAdESSigner, SigningError, TSA_PRESETS, remove_last_signature

SETTINGS = ("aventyapdf", "config")
MAX_RECENT = 10
USER_NAME = os.environ.get("USERNAME") or os.environ.get("USER") or ""

MARKUP_COLORS = doc_tools.MARKUP_COLORS
FREEHAND_PREFIX = doc_tools.FREEHAND_PREFIX
MARKUP_LABELS = {"highlight": "Resaltar", "underline": "Subrayar",
                 "strike": "Tachar", "squiggly": "Subrayado ondulado"}
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
                  "_pending_bytes")


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
            name = os.path.basename(self.pdf_path) if self.pdf_path else "Sin título"
            modified = self._modified
            self.setWindowTitle(f"{'● ' if modified else ''}{name} — AventyaPDF")
        self._refresh_doc_tabs()

    def _update_actions(self):
        has = self.doc is not None
        for a in getattr(self, "_doc_actions", []):
            a.setEnabled(has)
        if hasattr(self, "_act_ocr"):          # OCR: además hace falta Tesseract
            self._act_ocr.setEnabled(has and getattr(self, "ocr_available", True))
        can_u = has and self._history.can_undo()
        can_r = has and self._history.can_redo()
        if hasattr(self, "_act_undo"):
            lu, lr = self._history.undo_label(), self._history.redo_label()
            self._act_undo.setEnabled(can_u)
            self._act_undo.setText(f"Deshacer «{lu}»" if can_u and lu else "Deshacer")
            self._act_redo.setEnabled(can_r)
            self._act_redo.setText(f"Rehacer «{lr}»" if can_r and lr else "Rehacer")
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
            self.statusBar().showMessage("Espera a que termine la firma en curso")
            return
        self._stash_active()
        self._restore_session(index)

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
        self._update_banner()
        self._update_actions()
        self._update_title()
        h, y = s.get("_scroll_pos", (0, 0))
        QTimer.singleShot(0, lambda: (self._scroll.horizontalScrollBar().setValue(h),
                                      self._scroll.verticalScrollBar().setValue(y)))
        name = os.path.basename(self.pdf_path) if self.pdf_path else "Sin título"
        self.statusBar().showMessage(f"Documento: {name}")

    def next_document(self, step: int = 1):
        if len(self._sessions) > 1:
            self.switch_document((self._active + step) % len(self._sessions))

    def close_document_at(self, index: int):
        self.switch_document(index)
        if index == self._active:
            self.close_document()

    def _refresh_doc_tabs(self):
        if not hasattr(self, "sidebar"):
            return
        items = []
        for i in range(len(self._sessions)):
            s = self._session(i)
            path = s.get("pdf_path") or ""
            items.append((os.path.basename(path) if path else "Sin título", path,
                          self._session_dirty(i)))
        self.sidebar.set_documents(items, self._active)

    # ── abrir / cerrar ─────────────────────────────────────────────────── #

    def open_pdf(self):
        start =QSettings(*SETTINGS).value("recent/dir", "")
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir PDF", start, "Archivos PDF (*.pdf);;Todos los archivos (*)")
        if path:
            self.open_path(path, confirmed=True)

    def open_path(self, path: str, confirmed: bool = False) -> bool:
        # (r20) Cada PDF se abre en su propia pestaña; `confirmed` ya no se usa.
        already = self._session_index_for(path)
        if already is not None:                 # ya estaba abierto: se pasa a su pestaña
            self.switch_document(already)
            return True
        name = os.path.basename(path)
        try:
            with open(path, "rb") as f:
                data = f.read()
            doc = fitz.open("pdf", data)
        except Exception as e:
            QMessageBox.warning(self, "No se pudo abrir",
                                f"«{name}» no es un PDF válido o está dañado.\n\n{e}")
            return False
        password = ""
        if doc.needs_pass:
            while True:
                pw, ok = QInputDialog.getText(
                    self, "Documento protegido",
                    f"«{name}» está protegido con contraseña.\nContraseña:",
                    QLineEdit.EchoMode.Password)
                if not ok:
                    doc.close()
                    return False
                if doc.authenticate(pw):
                    password = pw
                    break
                QMessageBox.warning(self, "Documento protegido", "Contraseña incorrecta.")
        if len(doc) == 0:
            doc.close()
            QMessageBox.warning(self, "No se pudo abrir", f"«{name}» no contiene páginas.")
            return False
        self._begin_new_session()
        self._set_document(doc, path, data, password)
        self._add_recent(path)
        self.statusBar().showMessage(f"Abierto: {name}  ·  {len(doc)} páginas")
        return True

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
        # Firmas Certificadas se abre siempre que el documento esté firmado,
        # aunque el panel ya mostrara otra cosa.
        if doc_tools.signed_count(doc):
            self.sidebar.show_panel("signatures")
        elif (not self.sidebar.stack.isVisible()
                and QSettings(*SETTINGS).value("view/sidebar", "true") == "true"):
            self.sidebar.show_panel("thumbs")
        self._update_banner()
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
            self.statusBar().showMessage("Documento cerrado")
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
        self._update_banner()
        self._update_actions()
        self._update_title()
        self.statusBar().showMessage("Documento cerrado")

    def _confirm_discard(self) -> bool:
        if self.doc is None or not self._modified:
            return True
        name = os.path.basename(self.pdf_path) if self.pdf_path else "Sin título"
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("Cambios sin guardar")
        box.setText(f"¿Quieres guardar los cambios de «{name}»?")
        b_save = box.addButton("Guardar", QMessageBox.ButtonRole.AcceptRole)
        b_discard = box.addButton("No guardar", QMessageBox.ButtonRole.DestructiveRole)
        box.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
        box.exec()
        clicked = box.clickedButton()
        if clicked is b_save:
            return self.save_pdf()
        return clicked is b_discard

    def closeEvent(self, event):
        if self._sign_worker is not None and self._sign_worker.isRunning():
            self.statusBar().showMessage("Espera a que termine la firma en curso")
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
        if pdfs:
            QTimer.singleShot(0, lambda: self.open_path(pdfs[0]))
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
            m.addAction("(vacío)").setEnabled(False)
        else:
            m.addSeparator()
            m.addAction("Borrar lista").triggered.connect(
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
        path, _ = QFileDialog.getSaveFileName(self, "Guardar como", suggested,
                                              "Archivos PDF (*.pdf)")
        if not path:
            return False
        if not path.lower().endswith(".pdf"):
            path += ".pdf"
        return self._write_to(path)

    def _write_to(self, path: str) -> bool:
        exactos = self._pending_bytes is not None and not self._encrypt_opts
        if self._modified and not exactos and doc_tools.has_signatures(self.doc):
            r = QMessageBox.warning(
                self, "Documento firmado",
                "Este documento contiene firmas digitales.\n\n"
                "Guardar los cambios reescribe el archivo y las firmas existentes "
                "dejarán de ser válidas. Para conservarlas, firma sin modificar "
                "antes el documento.\n\n¿Guardar de todos modos?",
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
            QMessageBox.critical(self, "Error al guardar",
                                 f"No se pudo guardar el archivo:\n{e}")
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
        self._add_recent(path)
        self._update_title()
        self.statusBar().showMessage(f"Guardado: {os.path.basename(path)}")
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
        self._update_banner()

    def undo(self):
        self._step_history(self._history.undo, "Deshecho")

    def redo(self):
        self._step_history(self._history.redo, "Rehecho")

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
            QMessageBox.critical(self, verb, f"No se pudo restaurar el estado:\n{e}")
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
        self._update_banner()
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
                self._find_count.setText("Sin resultados")
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
        self._find_count.setText(f"{self._find_idx + 1} de {len(self._find_hits)}")
        sr = self.viewer._to_screen_rect(r)
        QTimer.singleShot(0, lambda: self._scroll.ensureVisible(
            sr.center().x(), sr.center().y(), 80, 160))

    # ── navegación y zoom ──────────────────────────────────────────────── #

    def go_to_page(self, pno: int):
        if self.doc is None:
            return
        pno = max(0, min(int(pno), len(self.doc) - 1))
        if pno != self.current_page:
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
        n, ok = QInputDialog.getInt(self, "Ir a página", f"Página (1–{len(self.doc)}):",
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
        self._set_custom_zoom(int(max(10, min(800, round(new)))))

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
        self._zoom_btns["100"].setChecked(True)
        self._update_zoom_type_icon()      # (r48) icono según la acción libre
        sl = self._zoom_slider
        sl.blockSignals(True)
        if pct < sl.minimum():
            sl.setMinimum(max(10, pct))
        sl.setValue(pct)
        sl.blockSignals(False)
        self._lbl_zoom_pct.setText(f"{pct} %")
        self.render_page(keep_selection=True)
        self.statusBar().showMessage(f"Zoom {pct} %")

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
        r = fitz.Rect(a.rect)
        self.viewer._sel = AnnotSelection(idx, r, fitz.Rect(r), a.type[1])
        self._show_annot_opts(a)
        self.viewer.update()

    def rotate_pages(self, pages: list[int], delta: int):
        if self.doc is None or not pages:
            return
        self.checkpoint("Girar páginas")
        doc_tools.rotate_pages(self.doc, pages, delta)
        self.mark_modified(structure=True)
        self.render_page()

    def rotate_current(self, delta: int):
        self.rotate_pages([self.current_page], delta)

    def delete_pages(self, pages: list[int]):
        if self.doc is None or not pages:
            return
        if len(set(pages)) >= len(self.doc):
            QMessageBox.warning(self, "No posible", "El PDF debe conservar al menos una página.")
            return
        what = f"la página {pages[0] + 1}" if len(pages) == 1 else f"{len(pages)} páginas"
        r = QMessageBox.question(self, "Eliminar páginas", f"¿Eliminar {what}?",
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r != QMessageBox.StandardButton.Yes:
            return
        self.checkpoint("Eliminar páginas")
        self.doc.delete_pages(sorted(set(pages)))
        self.current_page = min(self.current_page, len(self.doc) - 1)
        self.mark_modified(structure=True)
        self.render_page()

    def extract_pages(self, pages: list[int]):
        if self.doc is None or not pages:
            return
        base = os.path.splitext(self.pdf_path)[0] if self.pdf_path else "documento"
        path, _ = QFileDialog.getSaveFileName(self, "Guardar páginas extraídas",
                                              base + "_extracto.pdf", "Archivos PDF (*.pdf)")
        if not path:
            return
        new = doc_tools.extract_pages(self.doc, pages)
        try:
            new.save(path, garbage=3, deflate=True)
            self.statusBar().showMessage(f"{len(pages)} páginas extraídas a {os.path.basename(path)}")
        except Exception as e:
            QMessageBox.critical(self, "Extraer páginas", f"No se pudo guardar:\n{e}")
        finally:
            new.close()

    def duplicate_pages(self, pages: list[int]):
        """Una copia independiente detrás de cada página (r27). Se recorre de
        atrás adelante para que los índices no se muevan; `fullcopy_page` y no
        `select` con repetidos, que compartiría la página (invariante 22)."""
        if self.doc is None or not pages:
            return
        pages = sorted(set(pages))
        self.checkpoint("Duplicar páginas")
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
        self.checkpoint("Mover páginas")
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
        self.checkpoint("Insertar página en blanco")
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
            return False, "Espera a que termine la firma en curso"
        if self._modified and self._pending_bytes is None:
            return False, ("Guarda o descarta antes los cambios sin guardar: quitar una "
                           "firma parte de la versión del archivo")
        if self._pending_bytes is None and self._clean_bytes is None:
            return False, "Guarda antes el documento"
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
                QMessageBox.information(self, "Quitar firma", motivo)
            return False
        r = QMessageBox.question(
            self, "Quitar firma",
            f"¿Quitar la firma «{field_name}»?\n\n"
            "Su recuadro quedará vacío en el mismo sitio: haz clic en él para firmar "
            "de nuevo, con otro certificado si quieres. Las demás firmas no se tocan.\n\n"
            "El cambio no se guarda en el archivo hasta que guardes el documento.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if r != QMessageBox.StandardButton.Yes:
            return False
        origen = self._pending_bytes if self._pending_bytes is not None else self._clean_bytes
        try:
            nuevo = remove_last_signature(origen, field_name, self._password)
            doc = self._open_bytes(nuevo)
        except (SigningError, Exception) as e:  # noqa: BLE001
            traceback.print_exc()
            QMessageBox.critical(self, "Quitar firma", f"No se pudo quitar la firma:\n{e}")
            return False
        page = min(self.current_page, len(doc) - 1)
        self._set_document(doc, self.pdf_path, self._clean_bytes, self._password,
                           modified=True, pending=nuevo)
        self.go_to_page(page)
        self.statusBar().showMessage(
            f"Firma «{field_name}» quitada — sin guardar. Haz clic en su recuadro para firmar de nuevo")
        return True

    # ── anotaciones creadas desde el visor ─────────────────────────────── #

    def add_text_markup(self, rects: list, kind: str, color: tuple | None = None,
                        opacity: float = 1.0):
        if self.doc is None or not rects:
            return
        page = self.doc[self.current_page]
        fn = {"highlight": page.add_highlight_annot, "underline": page.add_underline_annot,
              "strike": page.add_strikeout_annot, "squiggly": page.add_squiggly_annot}.get(kind)
        if fn is None:
            return
        self.checkpoint(MARKUP_LABELS.get(kind, "Marcar texto"))
        annot = fn([fitz.Rect(r) for r in rects])
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
        self.checkpoint(f"{MARKUP_LABELS.get(kind, 'Marcar')} a mano alzada")
        annot = page.add_ink_annot([[(p.x, p.y) for p in points]])
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
        self.checkpoint("Nota")
        annot = page.add_text_annot(pt, text, icon="Comment")
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
            self.statusBar().showMessage(f"Copiados {len(text)} caracteres")

    # ── aviso superior ─────────────────────────────────────────────────── #

    def _update_banner(self):
        # (petición de Ricardo) El aviso de firma ya no se muestra sobre el
        # visor: esa información vive solo en el panel lateral de Firmas
        # Certificadas (rail o menú), que _set_document abre siempre que el
        # documento está firmado (r77).
        msgs = []
        if self.doc is not None:
            if self.doc.is_form_pdf and not doc_tools.signed_count(self.doc):
                msgs.append(("form", "Este documento contiene campos de formulario: "
                                     "haz clic en ellos para rellenarlos."))
            if self._orig_encrypted:
                msgs.append(("lock", "Documento protegido con cifrado."))
        if not msgs:
            self._banner.hide()
            return
        self._banner_lbl.setText("   ·   ".join(m for _k, m in msgs))
        self._banner.show()

    # ── firma digital ──────────────────────────────────────────────────── #

    def sign_in_field(self, field: dict) -> None:
        """(r38) Firmar en un campo de firma vacío del formulario: la firma va
        dentro de ese campo (con su nombre y su recuadro), como en Acrobat.

        (r39) Pide **siempre** el certificado: aquí no está la barra de la
        herramienta Firma, que enseña cuál se va a usar, así que si no se
        preguntase se firmaría en silencio con el de la sesión anterior."""
        self.statusBar().showMessage(f"Firmando en el campo «{field['name']}»…")
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
            QMessageBox.critical(self, "Error inesperado", f"Error al preparar la firma:\n{e}")
            self._finish_action()

    def _do_signature(self, rect, field_name: str = "", choose_cert: bool = False):
        if rect.width < 20 or rect.height < 10:
            self.statusBar().showMessage("Dibuja un área más grande para la firma")
            return
        has_sigs = doc_tools.has_signatures(self.doc)
        if has_sigs and self._modified and self._pending_bytes is None:
            r = QMessageBox.warning(
                self, "Firmar documento",
                "El documento ya contiene firmas y tiene cambios sin guardar.\n"
                "Si firmas ahora, esos cambios se incluirán y las firmas anteriores "
                "dejarán de ser válidas.\n\n¿Continuar?",
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

        # Invariante 1: único volteo a coordenadas PDF nativas (origen abajo).
        page_h = self.doc[self.current_page].rect.height
        box = (rect.x0, page_h - rect.y1, rect.x1, page_h - rect.y0)
        page = self.current_page

        base = (os.path.splitext(self.pdf_path)[0] if self.pdf_path else
                os.path.join(QSettings(*SETTINGS).value("recent/dir", ""), "documento"))
        out_path, _ = QFileDialog.getSaveFileName(
            self, "Guardar documento firmado", base + "_firmado.pdf", "Archivos PDF (*.pdf)")
        if not out_path:
            self._finish_action()
            return
        if not out_path.lower().endswith(".pdf"):
            out_path += ".pdf"

        temp_pfx = None
        if cert["type"] == "windows":
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                pfx_path, pfx_pass = export_windows_cert_to_pfx(cert["thumbprint"])
                temp_pfx = pfx_path
            except RuntimeError as e:
                QApplication.restoreOverrideCursor()
                QMessageBox.critical(self, "Error de exportación", str(e))
                self._finish_action()
                return
            QApplication.restoreOverrideCursor()
        else:
            pfx_path, pfx_pass = cert["path"], cert["password"]

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

        progress = QProgressDialog("Firmando el documento…", "Cancelar", 0, 0, self)
        progress.setCancelButton(None)
        progress.setWindowTitle("Firma digital")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.show()

        worker = SignWorker(dict(
            pdf_bytes=data, pfx_path=pfx_path, pfx_password=pfx_pass,
            page_num=page, box=box, reason=opts["reason"], location=opts["location"],
            contact=opts["contact"], tsa_url=opts["tsa_url"], certify=opts["certify"],
            doc_password=self._password, field_name=field_name), self)
        self._sign_worker = worker
        password = self._password

        def _cleanup():
            progress.close()
            if temp_pfx and os.path.exists(temp_pfx):
                try:
                    os.remove(temp_pfx)
                except Exception:
                    pass

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
                QMessageBox.critical(self, "Error al guardar",
                                     f"El documento se firmó pero no se pudo guardar:\n{e}")
                return
            doc = fitz.open("pdf", signed)
            if doc.needs_pass and password:
                doc.authenticate(password)
            self._set_document(doc, out_path, signed, password)
            self.go_to_page(page)
            self._add_recent(out_path)
            self.sidebar.show_panel("signatures")
            extra = "\nIncluye sello de tiempo." if opts["tsa_url"] else ""
            QMessageBox.information(self, "Firmado",
                                    f"Documento firmado y guardado en:\n{out_path}{extra}")
            self.statusBar().showMessage(f"Firmado: {os.path.basename(out_path)}")

        def _fail(msg: str):
            _cleanup()
            QMessageBox.critical(
                self, "Error al firmar",
                f"No se pudo firmar el PDF.\n\n{msg}\n\n"
                "• Verifica que el certificado sea válido y no esté caducado.\n"
                "• Si usas un archivo .pfx, comprueba la contraseña.")
            self.statusBar().showMessage("Error al firmar")

        worker.succeeded.connect(_ok)
        worker.failed.connect(_fail)
        worker.finished.connect(_finished)
        self._finish_action()
        self.statusBar().showMessage("Firmando… por favor espera")
        worker.start()
