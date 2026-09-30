"""
window_menus.py
Mixin de MainWindow: barra de menús con atajos, barra de búsqueda, aviso
superior del documento y las herramientas de documento que se lanzan desde
los menús (marca de agua, encabezados/Bates, redacción, OCR, seguridad,
exportación, división…).

Patrón para cambios de documento: `_run_doc_change(etiqueta, fn)` crea el
punto de deshacer, ejecuta, y si algo falla restaura el estado anterior.
"""
import datetime
import os
import tempfile
import traceback

import fitz
from PyQt6.QtCore import QObject, Qt, QSettings, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QAction, QDesktopServices, QIcon, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QFileDialog, QFrame, QHBoxLayout, QInputDialog, QLabel,
    QLineEdit, QMessageBox, QProgressDialog, QPushButton, QWidget,
)

import actualizaciones
import conversion_office
import dialogs
import doc_tools
import icons
import pdf_ocr
import tesseract_setup
import tesseract_ui
from signer_backend import TSA_PRESETS

SETTINGS = ("aventyapdf", "config")
APP_VERSION = "1.3.0"
# (r71) Titular y repositorio público (AGPL-3.0, libre distribución).
APP_OWNER = "Aventya Asesoría Integral SL"
APP_REPO = "https://github.com/Aventya/AventyaPDF"
# (petición de Ricardo) Aviso automático de versiones nuevas al iniciar.
_KEY_AUTO_UPDATE = "updates/check_on_start"
_KEY_SKIP_VERSION = "updates/skip_version"
OCR_LANGS = ["spa", "spa+eng", "eng", "cat", "glg", "eus", "por", "fra", "deu", "ita"]


class _UpdateNotifier(QObject):
    """Consulta la última versión en un hilo aparte (sin frenar la ventana)
    y, si responde, la entrega en el hilo de la interfaz con `found`. Los
    errores (sin conexión…) se callan: el aviso automático no molesta."""
    found = pyqtSignal(dict)

    def start(self) -> None:
        import threading
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        try:
            info = actualizaciones.fetch_latest()
        except actualizaciones.UpdateError:
            return
        self.found.emit(info)


class MenusMixin:

    # ── construcción ───────────────────────────────────────────────────── #

    def _action(self, menu, text: str, slot, shortcut=None, needs_doc: bool = True):
        act = QAction(text, self)
        if shortcut:
            seqs = shortcut if isinstance(shortcut, (list, tuple)) else [shortcut]
            act.setShortcuts([QKeySequence(s) for s in seqs])
        act.triggered.connect(lambda _checked=False, fn=slot: fn())
        menu.addAction(act)
        if needs_doc:
            self._doc_actions.append(act)
        return act

    def _build_menus(self):
        self._doc_actions = []
        A = self._action
        mb = self.menuBar()

        m = mb.addMenu("&Archivo")
        A(m, "Nuevo PDF en blanco", self.new_blank_document, "Ctrl+N", needs_doc=False)
        A(m, "Crear PDF desde imágenes…", self.create_from_images, needs_doc=False)
        A(m, "Abrir…", self.open_pdf, "Ctrl+O", needs_doc=False)
        self._menu_recent = m.addMenu("Abrir reciente")
        self._menu_recent.aboutToShow.connect(self._fill_recent_menu)
        m.addSeparator()
        A(m, "Guardar", self.save_pdf, "Ctrl+S")
        A(m, "Guardar como…", self.save_pdf_as, "Ctrl+Shift+S")
        exp = m.addMenu("Exportar")
        A(exp, "Páginas como imágenes…", self.export_images)
        A(exp, "Texto (.txt)…", self.export_text)
        A(exp, "Documento de Word (.docx)…", self.export_word)
        A(exp, "Extraer páginas a PDF…", self.extract_pages_dialog)
        m.addSeparator()
        A(m, "Imprimir…", self.print_pdf, "Ctrl+P")
        A(m, "Propiedades del documento…", self.show_properties, "Ctrl+D")
        m.addSeparator()
        A(m, "Cerrar documento", self.close_document, "Ctrl+W")
        A(m, "Salir", self.close, "Ctrl+Q", needs_doc=False)

        m = mb.addMenu("&Edición")
        self._act_undo = A(m, "Deshacer", self.undo, "Ctrl+Z")
        self._act_redo = A(m, "Rehacer", self.redo, ["Ctrl+Y", "Ctrl+Shift+Z"])
        m.addSeparator()
        A(m, "Copiar texto seleccionado", self.copy_selected_text, "Ctrl+C")
        m.addSeparator()
        A(m, "Buscar…", self.show_find, "Ctrl+F")
        A(m, "Buscar siguiente", self.find_next, "F3")
        A(m, "Buscar anterior", self.find_prev, "Shift+F3")

        m = mb.addMenu("&Ver")
        A(m, "Mostrar u ocultar panel lateral", self.sidebar_toggle, "F4", needs_doc=False)
        A(m, "Miniaturas de página", lambda: self.sidebar.show_panel("thumbs"), needs_doc=False)
        A(m, "Marcadores", lambda: self.sidebar.show_panel("bookmarks"), needs_doc=False)
        A(m, "Comentarios", lambda: self.sidebar.show_panel("comments"), needs_doc=False)
        A(m, "Firmas Certificadas", lambda: self.sidebar.show_panel("signatures"), needs_doc=False)
        self._act_highlight_fields = A(m, "Resaltar campos de formulario",
                                       self.toggle_highlight_fields, needs_doc=False)
        self._act_highlight_fields.setCheckable(True)
        self._act_highlight_fields.setChecked(
            QSettings(*SETTINGS).value("view/highlight_fields", True, type=bool))
        m.addSeparator()
        A(m, "Acercar", lambda: self.zoom_step(1), ["Ctrl++", "Ctrl+="])
        A(m, "Alejar", lambda: self.zoom_step(-1), "Ctrl+-")
        A(m, "Tamaño real (100 %)", self.zoom_actual, "Ctrl+0")
        A(m, "Ajustar al ancho", self.zoom_fit_width, "Ctrl+1")
        A(m, "Ajustar a la página", self.zoom_fit_page, "Ctrl+2")
        m.addSeparator()
        A(m, "Primera página", self.first_page, "Home")
        A(m, "Página anterior", self.prev_page, "PgUp")
        A(m, "Página siguiente", self.next_page, "PgDown")
        A(m, "Última página", self.last_page, "End")
        A(m, "Ir a página…", self.ask_go_to_page, "Ctrl+G")
        m.addSeparator()
        A(m, "Documento siguiente", self.next_document, "Ctrl+Tab", needs_doc=False)
        A(m, "Documento anterior", lambda: self.next_document(-1), "Ctrl+Shift+Tab",
          needs_doc=False)

        m = mb.addMenu("&Comentar")
        for text, mode, key in [
            ("Herramienta de selección", "NONE", "V"),
            ("Añadir texto", "TEXT", "T"),
            ("Nota adhesiva", "NOTE", "N"),
            ("Resaltar, subrayar o tachar", "MARKUP", "H"),
            ("Rectángulo", "RECT", "R"),
            ("Emoji", "EMOJI", "E"),
            ("Borrador de anotaciones", "ERASE", None),
        ]:
            A(m, text, lambda md=mode: self._select_tool(md), key)
        m.addSeparator()
        A(m, "Aplanar anotaciones y formularios…", self.flatten_document)

        m = mb.addMenu("&Organizar")
        A(m, "Organizar páginas en el panel lateral", self.organize_pages)
        m.addSeparator()
        A(m, "Insertar página en blanco", lambda: self.insert_blank_after(self.current_page))
        A(m, "Insertar PDF tras la página actual…", self.insert_pdf_after_current)
        A(m, "Añadir PDF al final…", self.merge_pdf)
        A(m, "Duplicar página actual", self.copy_page)
        A(m, "Eliminar páginas…", self.delete_pages_dialog)
        A(m, "Extraer páginas…", self.extract_pages_dialog)
        A(m, "Dividir documento…", self.split_document)
        m.addSeparator()
        A(m, "Girar página a la derecha", lambda: self.rotate_current(90), "Ctrl+Shift+R")
        A(m, "Girar página a la izquierda", lambda: self.rotate_current(-90), "Ctrl+Shift+L")
        A(m, "Girar páginas…", self.rotate_pages_dialog)

        m = mb.addMenu("&Herramientas")
        A(m, "Editar texto e imágenes del PDF", lambda: self._select_tool("EDIT"), "C")
        m.addSeparator()
        A(m, "Marca de agua…", self.add_watermark)
        A(m, "Encabezado, pie y numeración Bates…", self.add_header_footer)
        self._act_ocr = A(m, "Reconocer texto (OCR)…", self.run_ocr)
        A(m, "Optimizar y comprimir…", self.compress_dialog)

        m = mb.addMenu("&Proteger")
        A(m, "Proteger con contraseña…", self.protect_document)
        A(m, "Quitar seguridad", self.remove_security)

        m = mb.addMenu("&Firmar")
        A(m, "Firmar documento (dibujar área)", lambda: self._select_tool("SIGN"))
        A(m, "Insertar firma manuscrita (dibujada o imagen)…", self._menu_hand_signature)
        A(m, "Opciones de firma…", self.sign_options, needs_doc=False)
        A(m, "Certificado de firma…", self._change_cert, needs_doc=False)
        m.addSeparator()
        A(m, "Ver las firmas (verificadas)", self.show_signatures)

        m = mb.addMenu("A&yuda")
        A(m, "Atajos de teclado", lambda: dialogs.show_shortcuts(self), "F1", needs_doc=False)
        A(m, "Presentación de AventyaPDF", self.show_welcome, needs_doc=False)
        m.addSeparator()
        A(m, "Buscar actualizaciones…", self.check_updates, needs_doc=False)
        # (petición de Ricardo) Aviso automático al iniciar, activado de entrada.
        self._act_auto_update = QAction("Avisar de actualizaciones al iniciar", self)
        self._act_auto_update.setCheckable(True)
        self._act_auto_update.setChecked(self._auto_update_enabled())
        self._act_auto_update.toggled.connect(self._set_auto_update)
        m.addAction(self._act_auto_update)
        A(m, "Acerca de AventyaPDF", self.show_about, needs_doc=False)

        self._esc_shortcut = QShortcut(QKeySequence("Escape"), self)
        self._esc_shortcut.activated.connect(self._on_escape)

    def _build_find_bar(self) -> QWidget:
        """(r78, petición de Ricardo) Ya no es una barra aparte encima del
        visor: estos controles ocupan, dentro de la propia barra principal,
        el sitio del botón de búsqueda (`_btn_find`) mientras están
        visibles — nunca se ven los dos a la vez (`show_find`/`hide_find`).

        (petición de Ricardo) No forma parte del layout de la barra: flota
        encima de ella (`_place_find_bar`), con su borde derecho en el de la
        lupa, y tapa las herramientas que queden debajo en vez de empujarlas
        o de obligar a ensanchar la ventana. La X las vuelve a dejar ver."""
        box = QWidget(self._topbar)
        box.setObjectName("find_bar")
        # Fondo opaco (el blanco de la barra) para tapar lo que haya debajo.
        box.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        box.hide()
        lay = QHBoxLayout(box)
        # Un poco de aire a la izquierda: no pegarse a la herramienta tapada.
        lay.setContentsMargins(8, 0, 0, 0)
        lay.addStretch()        # controles a la derecha si se ensancha para tapar
        # (petición de Ricardo) Misma separación que la barra principal.
        lay.setSpacing(self._topbar.layout().spacing())
        # (r50, petición de Ricardo) La lupa desaparece; en su sitio va el
        # contador, con ancho fijo para que no desplace el resto de la barra
        # al crecer el número de coincidencias («Sin resultados» es lo más
        # ancho que puede salir).
        self._find_count = QLabel("")
        self._find_count.setObjectName("find_count")
        self._find_count.setFixedWidth(96)
        self._find_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._find_count)
        self._find_edit = QLineEdit()
        # (r96, petición de Ricardo) 107 px más estrecho que antes (220) y sin
        # « en el documento»: todo el buscador flotante se estrecha con él.
        self._find_edit.setPlaceholderText("Buscar…")
        self._find_edit.setFixedWidth(113)
        # (r50) Dinámica: cada pulsación relanza la búsqueda (con un pequeño
        # retardo, `_find_live_timer`); Intro ya no hace falta, pero sigue
        # sirviendo para saltar a la siguiente coincidencia.
        self._find_edit.textChanged.connect(self._on_find_text_changed)
        self._find_edit.returnPressed.connect(self.find_next)
        sc = QShortcut(QKeySequence("Shift+Return"), self._find_edit)
        sc.setContext(Qt.ShortcutContext.WidgetShortcut)
        sc.activated.connect(self.find_prev)
        lay.addWidget(self._find_edit)
        # (petición de Ricardo) Todos los botones del buscador son del mismo
        # tipo que los de la barra principal (`tbr_btn`, 32×32), no `opt_btn`,
        # que es más pequeño: así la X ocupa exactamente el sitio de la lupa.
        for key, tip, fn in [("find_prev", "Anterior (Mayús+F3)", self.find_prev),
                             ("find_next", "Siguiente (F3)", self.find_next)]:
            b = self._glyph_btn(key, tip)
            b.clicked.connect(lambda _c=False, f=fn: f())
            lay.addWidget(b)
        close = self._glyph_btn("close", "Cerrar (Esc)")
        close.clicked.connect(lambda _c=False: self.hide_find())
        lay.addWidget(close)
        self._find_bar = box
        return box


    # ── utilidades ─────────────────────────────────────────────────────── #

    def sidebar_toggle(self):
        self.sidebar.toggle()

    def _menu_hand_signature(self):
        """(r68) Menú Firmar: pone la herramienta Firma y abre la firma manuscrita."""
        self._select_tool("SIGN")
        if self.viewer.mode == "SIGN":
            self._on_hand_signature()

    def _select_tool(self, mode: str):
        if self.doc is None:
            return
        if mode == "NONE":
            self._finish_action()
        elif self.viewer.mode != mode:
            self._toggle_tool(mode)

    def _on_escape(self):
        # Los QShortcut de ventana se procesan ANTES que los eventos de teclado,
        # así que Esc NO llega al editor que haya abierto sobre la página: hay
        # que cancelarlo aquí (invariante 41).
        v = self.viewer
        if v.text_editor is not None:
            v.close_text_editor(commit=False)
            return
        if v.content.editor is not None:
            v.content.close_editor(commit=False)
            return
        if self._find_bar.isVisible() and self._find_edit.hasFocus():
            self.hide_find()
            return
        if v.mode != "NONE":
            self._finish_action()
            return
        if self._pages_mode:
            self._set_pages_mode(False)
            return
        v.clear_text_selection()
        if v._sel is not None:
            v._sel = None
            self._hide_annot_opts()
            v.update()
        elif self._find_bar.isVisible():
            self.hide_find()

    def _base_name(self) -> str:
        return os.path.splitext(os.path.basename(self.pdf_path))[0] if self.pdf_path else "documento"

    def _start_dir(self) -> str:
        return (os.path.dirname(self.pdf_path) if self.pdf_path
                else QSettings(*SETTINGS).value("recent/dir", ""))

    def _run_doc_change(self, label: str, fn, structure: bool = True):
        self.checkpoint(label)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            result = fn()
        except Exception as e:  # noqa: BLE001
            QApplication.restoreOverrideCursor()
            traceback.print_exc()
            self._rollback_last()
            QMessageBox.critical(self, label, f"No se pudo completar la operación:\n{e}")
            return None, False
        QApplication.restoreOverrideCursor()
        self.mark_modified(structure=structure)
        self.render_page()
        self.statusBar().showMessage(f"{label}: hecho")
        return result, True

    def _rollback_last(self):
        """Restaura el último punto de deshacer sin dejarlo en «rehacer»."""
        was_modified = self._modified
        self.undo()
        self._history.discard_redo()
        self._modified = was_modified
        self._update_actions()
        self._update_title()

    # ── archivo ────────────────────────────────────────────────────────── #

    def new_blank_document(self):
        doc = fitz.open()
        doc.new_page(width=595, height=842)
        self._begin_new_session()              # en una pestaña nueva
        self._set_document(doc, "", None, modified=True)
        self.statusBar().showMessage("Nuevo documento en blanco (A4)")

    def create_from_images(self, paths=None):
        if not paths:
            paths, _ = QFileDialog.getOpenFileNames(
                self, "Crear PDF desde imágenes", self._start_dir(), doc_tools.IMAGE_FILTER)
            if not paths:
                return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            doc = doc_tools.images_to_pdf(list(paths))
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Crear PDF", f"No se pudieron convertir las imágenes:\n{e}")
            return
        QApplication.restoreOverrideCursor()
        self._begin_new_session()              # en una pestaña nueva
        self._set_document(doc, "", None, modified=True)
        self.statusBar().showMessage(f"PDF creado a partir de {len(paths)} imágenes — sin guardar")

    def combine_pdfs_from_paths(self, paths):
        """(r55) Menú contextual del Explorador de Windows: combina varios PDF
        elegidos en el Explorador (sin necesidad de abrir ninguno antes) en un
        documento nuevo sin guardar, en una pestaña nueva. A diferencia de
        `merge_pdf()`, que añade un único PDF al final del documento ya
        abierto, aquí no hay documento previo: se parte de cero."""
        paths = [p for p in paths if p.lower().endswith(".pdf")]
        if len(paths) < 2:
            QMessageBox.warning(self, "Combinar PDF",
                                "Hacen falta al menos dos archivos PDF para combinarlos.")
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            doc = doc_tools.merge_pdfs(paths)
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Combinar PDF", f"No se pudieron combinar los archivos:\n{e}")
            return
        QApplication.restoreOverrideCursor()
        self._begin_new_session()
        self._set_document(doc, "", None, modified=True)
        self.statusBar().showMessage(f"PDF combinado a partir de {len(paths)} archivos — sin guardar")

    def create_separate_pdfs_from_images(self, paths):
        """(r55) Menú contextual del Explorador de Windows: convierte cada
        imagen elegida en su propio PDF de una sola página, cada uno en una
        pestaña nueva sin guardar (a diferencia de `create_from_images()`, que
        las junta todas en un único PDF)."""
        if not paths:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            docs = [doc_tools.images_to_pdf([p]) for p in paths]
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Convertir imágenes", f"No se pudieron convertir las imágenes:\n{e}")
            return
        QApplication.restoreOverrideCursor()
        for doc in docs:
            self._begin_new_session()
            self._set_document(doc, "", None, modified=True)
        self.statusBar().showMessage(f"{len(docs)} PDF creados a partir de imágenes — sin guardar")

    def combine_files_to_pdf(self, paths):
        """(r86) Menú contextual del Explorador, «Combinar en un PDF»: PDF,
        imágenes y documentos de Word mezclados, en el orden recibido, en un
        único documento nuevo sin guardar."""
        paths = [p for p in paths if conversion_office.tipo_de(p)]
        if len(paths) < 2:
            QMessageBox.warning(self, "Combinar en un PDF",
                                "Hacen falta al menos dos archivos (PDF, imágenes o Word) para combinarlos.")
            return
        docs = self._convert_paths(paths, "Combinar en un PDF")
        if docs is None:
            return
        doc = conversion_office.combinar(docs)
        self._begin_new_session()
        self._set_document(doc, "", None, modified=True)
        self.statusBar().showMessage(f"PDF combinado a partir de {len(paths)} archivos — sin guardar")

    def convert_files_to_pdfs(self, paths):
        """(r86) Menú contextual del Explorador, «Convertir a PDF»: cada imagen
        o documento de Word en su propio PDF, cada uno en una pestaña nueva sin
        guardar."""
        paths = [p for p in paths if conversion_office.tipo_de(p) in ("img", "word")]
        if not paths:
            return
        docs = self._convert_paths(paths, "Convertir a PDF")
        if docs is None:
            return
        for doc in docs:
            self._begin_new_session()
            self._set_document(doc, "", None, modified=True)
        self.statusBar().showMessage(f"{len(docs)} PDF creados — sin guardar")

    def sign_files(self, paths):
        """(r86) Menú contextual del Explorador, «Firmar digitalmente»: abre
        los PDF y deja puesta la herramienta Firma en el último."""
        abiertos = [p for p in paths if p.lower().endswith(".pdf") and self.open_path(p)]
        if abiertos:
            self._select_tool("SIGN")

    def _convert_paths(self, paths, titulo):
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        if any(conversion_office.tipo_de(p) == "word" for p in paths):
            self.statusBar().showMessage("Convirtiendo documentos de Word…")
            QApplication.processEvents()
        try:
            return conversion_office.archivos_a_pdfs(paths)
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, titulo, f"No se pudieron convertir los archivos:\n{e}")
            return None
        finally:
            while QApplication.overrideCursor() is not None:
                QApplication.restoreOverrideCursor()

    def show_properties(self):
        if self.doc is None:
            return
        n = len(doc_tools.signature_widgets(self.doc))
        dlg = dialogs.PropertiesDialog(self, self.doc, self.pdf_path, n)
        if not dlg.exec():
            return
        new = dlg.metadata()
        old = self.doc.metadata or {}
        if all((old.get(k) or "") == v for k, v in new.items()):
            return
        meta = {k: (old.get(k) or "") for k, _l in doc_tools.METADATA_FIELDS}
        if old.get("creationDate"):
            meta["creationDate"] = old["creationDate"]
        meta.update(new)
        meta["modDate"] = fitz.get_pdf_now()
        self._run_doc_change("Propiedades del documento",
                             lambda: self.doc.set_metadata(meta), structure=False)

    def export_images(self):
        if self.doc is None:
            return
        dlg = dialogs.ExportImagesDialog(self, len(self.doc), self.current_page)
        if not dlg.exec():
            return
        v = dlg.values()
        folder = QFileDialog.getExistingDirectory(self, "Carpeta de destino", self._start_dir())
        if not folder:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            files = doc_tools.export_images(self.doc, v["pages"], folder, self._base_name(),
                                            v["dpi"], v["fmt"])
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Exportar imágenes", f"No se pudo exportar:\n{e}")
            return
        QApplication.restoreOverrideCursor()
        QMessageBox.information(self, "Exportar imágenes",
                                f"{len(files)} imágenes guardadas en:\n{folder}")

    def export_text(self):
        if self.doc is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar texto", os.path.join(self._start_dir(), self._base_name() + ".txt"),
            "Texto (*.txt)")
        if not path:
            return
        try:
            doc_tools.export_text(self.doc, path)
            self.statusBar().showMessage(f"Texto exportado a {os.path.basename(path)}")
        except Exception as e:
            QMessageBox.critical(self, "Exportar texto", f"No se pudo exportar:\n{e}")

    def export_word(self):
        if self.doc is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar a Word", os.path.join(self._start_dir(), self._base_name() + ".docx"),
            "Documento de Word (*.docx)")
        if not path:
            return
        tmp = None
        src = self.pdf_path
        if self._modified or not src or self._orig_encrypted:
            fd, tmp = tempfile.mkstemp(suffix=".pdf")
            os.close(fd)
            with open(tmp, "wb") as f:
                f.write(self.doc.tobytes())
            src = tmp
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            doc_tools.export_docx(src, path)
            ok, msg = True, f"Documento de Word guardado en:\n{path}"
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            ok, msg = False, str(e)
        finally:
            QApplication.restoreOverrideCursor()
            if tmp and os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except Exception:
                    pass
        if ok:
            QMessageBox.information(self, "Exportar a Word", msg)
        else:
            QMessageBox.warning(self, "Exportar a Word", msg)

    # ── organizar ──────────────────────────────────────────────────────── #

    def insert_pdf_after_current(self):
        if self.doc is not None:
            self.insert_pdf_after(self.current_page)

    def insert_pdf_after(self, pno: int):
        if self.doc is None:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Insertar PDF", self._start_dir(),
                                              "Archivos PDF (*.pdf)")
        if not path:
            return
        try:
            src = fitz.open(path)
        except Exception as e:
            QMessageBox.warning(self, "Insertar PDF", f"No se pudo abrir:\n{e}")
            return
        if src.needs_pass:
            src.close()
            QMessageBox.warning(self, "Insertar PDF", "El PDF a insertar está protegido con contraseña.")
            return
        pos = pno + 1
        n, ok = self._run_doc_change(
            "Insertar PDF", lambda: doc_tools.insert_pdf_at(self.doc, src, pos))
        src.close()
        if ok:
            self.sidebar.thumbs.select_after_rebuild(list(range(pos, pos + n)))
            self.go_to_page(pos)
            self.statusBar().showMessage(f"{n} páginas insertadas tras la página {pos}")

    def delete_pages_dialog(self):
        if self.doc is None:
            return
        pages = dialogs.ask_page_range(self, "Eliminar páginas", len(self.doc),
                                       str(self.current_page + 1))
        if pages:
            self.delete_pages(pages)

    def extract_pages_dialog(self):
        if self.doc is None:
            return
        pages = dialogs.ask_page_range(self, "Extraer páginas", len(self.doc),
                                       str(self.current_page + 1))
        if pages:
            self.extract_pages(pages)

    def rotate_pages_dialog(self):
        if self.doc is None:
            return
        pages = dialogs.ask_page_range(self, "Girar páginas", len(self.doc), "")
        if not pages:
            return
        items = ["90° a la derecha", "90° a la izquierda", "180°"]
        choice, ok = QInputDialog.getItem(self, "Girar páginas", "Sentido:", items, 0, False)
        if ok:
            self.rotate_pages(pages, {items[0]: 90, items[1]: -90, items[2]: 180}[choice])

    def split_document(self):
        if self.doc is None:
            return
        n, ok = QInputDialog.getInt(self, "Dividir documento", "Páginas por archivo:",
                                    1, 1, max(1, len(self.doc)))
        if not ok:
            return
        folder = QFileDialog.getExistingDirectory(self, "Carpeta de destino", self._start_dir())
        if not folder:
            return
        base = self._base_name()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        count = 0
        try:
            for i, part in enumerate(doc_tools.split_every(self.doc, n), 1):
                part.save(os.path.join(folder, f"{base}_parte{i:02d}.pdf"), garbage=3, deflate=True)
                part.close()
                count = i
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Dividir documento", f"No se pudo dividir:\n{e}")
            return
        QApplication.restoreOverrideCursor()
        QMessageBox.information(self, "Dividir documento", f"{count} archivos creados en:\n{folder}")

    # ── herramientas ───────────────────────────────────────────────────── #

    def add_watermark(self):
        if self.doc is None:
            return
        dlg = dialogs.WatermarkDialog(self, len(self.doc))
        if not dlg.exec():
            return
        v = dlg.values()
        self._run_doc_change("Marca de agua", lambda: doc_tools.add_watermark(
            self.doc, v["pages"], v["text"], v["fontsize"], v["color"], v["opacity"], v["angle"]))

    def add_header_footer(self):
        if self.doc is None:
            return
        dlg = dialogs.HeaderFooterDialog(self, len(self.doc))
        if not dlg.exec():
            return
        v = dlg.values()
        self._run_doc_change("Encabezado y pie",
                             lambda: doc_tools.add_header_footer(self.doc, v["pages"], v["spec"]))

    def toggle_highlight_fields(self) -> None:
        QSettings(*SETTINGS).setValue("view/highlight_fields",
                                      self._act_highlight_fields.isChecked())
        self.viewer.update()

    ocr_available = True

    def set_ocr_available(self, available: bool, reason: str = "") -> None:
        """Tesseract es obligatorio: sin él, «Reconocer texto (OCR)» se desactiva
        (main.py vuelve a forzar la instalación en el siguiente inicio)."""
        self.ocr_available = available
        act = getattr(self, "_act_ocr", None)
        if act is not None:
            act.setText("Reconocer texto (OCR)…" if available
                        else "Reconocer texto (OCR) — Tesseract no instalado")
            act.setToolTip(reason)
        self._update_actions()

    def run_ocr(self):
        if self.doc is None:
            return
        total = len(self.doc)
        without_text = [i for i in range(total) if not pdf_ocr.page_has_text(self.doc[i])]
        dlg = dialogs.OcrDialog(self, OCR_LANGS, len(without_text), total)
        if not dlg.exec():
            return
        v = dlg.values()
        pages = list(range(total)) if v["all_pages"] else without_text
        if not pages:
            QMessageBox.information(self, "Reconocer texto (OCR)",
                                    "Todas las páginas ya contienen texto seleccionable.")
            return
        # Tesseract es obligatorio: si falta él o el idioma elegido, se instala ahora.
        if not tesseract_ui.ensure_languages(self, v["lang"]):
            return
        progress = QProgressDialog("Reconociendo texto…", "Cancelar", 0, len(pages), self)
        progress.setWindowTitle("Reconocer texto (OCR)")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        # La capa de texto se añade sobre las páginas originales (pdf_ocr): un solo
        # paso de deshacer para todo el documento.
        self.checkpoint("Reconocer texto (OCR)")
        words = changed = 0
        try:
            for n, i in enumerate(pages):
                progress.setValue(n)
                progress.setLabelText(f"Página {i + 1} de {total}…")
                QApplication.processEvents()
                if progress.wasCanceled():
                    progress.close()
                    self._rollback_last()
                    self.render_page()
                    return
                added = pdf_ocr.ocr_page(self.doc[i], v["lang"],
                                         detect_orientation=v["orientation"])
                words += added
                changed += bool(added)
            progress.setValue(len(pages))
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            progress.close()
            self._rollback_last()
            self.render_page()
            QMessageBox.critical(
                self, "Reconocer texto (OCR)",
                "No se pudo reconocer el texto.\n\n"
                f"Tesseract: {tesseract_setup.find_tesseract() or 'no encontrado'}\n"
                f"Idiomas: {tesseract_setup.TESSDATA_DIR}\n\n"
                f"Detalle: {e}")
            return
        progress.close()
        if not words:
            self._rollback_last()          # no dejar un paso de deshacer vacío
            self.render_page()
            QMessageBox.information(self, "Reconocer texto (OCR)",
                                    "No se ha encontrado texto nuevo que reconocer.")
            return
        self.mark_modified(structure=False)
        self.render_page()
        QMessageBox.information(self, "Reconocer texto (OCR)",
                                f"Se han reconocido {words} palabras en {changed} de "
                                f"{len(pages)} páginas. Ya puedes buscar y seleccionar ese texto.")

    def compress_dialog(self):
        if self.doc is None:
            return
        if not self._btn_compress.isChecked():
            self._btn_compress.setChecked(True)
            self._toggle_compress_panel()

    def flatten_document(self):
        if self.doc is None:
            return
        r = QMessageBox.question(
            self, "Aplanar",
            "Las anotaciones y los campos de formulario pasarán a formar parte del "
            "contenido y ya no se podrán editar. ¿Continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            self._run_doc_change("Aplanar", lambda: doc_tools.flatten(self.doc))

    # ── proteger ───────────────────────────────────────────────────────── #

    def protect_document(self):
        if self.doc is None:
            return
        dlg = dialogs.SecurityDialog(self)
        if dlg.exec():
            self._encrypt_opts = dlg.values()
            self.mark_modified()
            QMessageBox.information(self, "Proteger con contraseña",
                                    "La protección se aplicará al guardar el documento (Ctrl+S).")

    def remove_security(self):
        if self.doc is None:
            return
        protected = self._orig_encrypted or (
            self._encrypt_opts and self._encrypt_opts.get("encryption") != fitz.PDF_ENCRYPT_NONE)
        if not protected:
            QMessageBox.information(self, "Quitar seguridad", "El documento no está protegido.")
            return
        self._encrypt_opts = {"encryption": fitz.PDF_ENCRYPT_NONE}
        self.mark_modified()
        QMessageBox.information(self, "Quitar seguridad",
                                "El cifrado se eliminará al guardar el documento (Ctrl+S).")

    # ── firmar ─────────────────────────────────────────────────────────── #

    def sign_options(self):
        has_sigs = self.doc is not None and doc_tools.has_signatures(self.doc)
        dialogs.SignOptionsDialog(self, has_sigs, TSA_PRESETS, ok_text="Guardar").exec()

    def show_signatures(self):
        """(r61) Abre el panel Firmas, que las verifica solo."""
        if self.doc is None:
            return
        self.sidebar.show_panel("signatures")

    # ── ayuda ──────────────────────────────────────────────────────────── #

    def show_welcome(self):
        """(r70) Vuelve a abrir la presentación inicial; su casilla permite
        reactivarla al arrancar."""
        import presentacion
        return presentacion.show_welcome(self)

    def check_updates(self):
        """(petición de Ricardo) Ayuda › Buscar actualizaciones…: pregunta a
        GitHub por la última versión publicada y da el enlace directo a su
        instalador, que sale de la propia publicación (siempre la última)."""
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            info = actualizaciones.fetch_latest()
        except actualizaciones.UpdateError as e:
            QApplication.restoreOverrideCursor()
            caja = QMessageBox(QMessageBox.Icon.Warning, "Buscar actualizaciones",
                               "", parent=self)
            caja.setText(
                f"<p>No se pudo comprobar si hay una versión nueva.</p><p>{e}</p>"
                f"<p>Puedes consultarlas en <a href='{actualizaciones.RELEASES_URL}'>"
                f"{actualizaciones.RELEASES_URL}</a></p>")
            caja.setTextFormat(Qt.TextFormat.RichText)
            caja.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
            caja.exec()
            return
        QApplication.restoreOverrideCursor()
        self._show_update_dialog(info)

    def _show_update_dialog(self, info: dict, automatic: bool = False) -> None:
        """Ventana de actualizaciones. `automatic`: el aviso al iniciar, que
        solo sale si hay versión nueva y ofrece no volver a avisar de ella."""
        nueva = actualizaciones.is_newer(info["version"], APP_VERSION)
        nombre = info["installer_name"] or "la página de la versión"
        enlace = (f"<p>Enlace directo de descarga:<br>"
                  f"<a href='{info['installer_url']}'>{nombre}</a></p>"
                  f"<p style='color:#605E5C'>Novedades: <a href='{info['page_url']}'>"
                  f"AventyaPDF {info['version']}</a></p>")
        caja = QMessageBox(self)
        caja.setWindowTitle("Actualización disponible" if automatic else "Buscar actualizaciones")
        caja.setIconPixmap(QIcon(icons.APP_ICON).pixmap(64, 64))
        omitir = None
        if nueva:
            caja.setText(
                f"<h3>Hay una versión nueva: AventyaPDF {info['version']}</h3>"
                f"<p>Tienes la {APP_VERSION}. Descarga el instalador y ejecútalo: "
                "se instala encima de la versión actual.</p>" + enlace)
            descargar = caja.addButton("Descargar ahora", QMessageBox.ButtonRole.AcceptRole)
            caja.addButton("Ahora no" if automatic else "Cerrar", QMessageBox.ButtonRole.RejectRole)
            caja.setDefaultButton(descargar)
            if automatic:
                omitir = QCheckBox("No volver a avisar de esta versión")
                caja.setCheckBox(omitir)
        else:
            caja.setText(
                f"<h3>Tienes la última versión: AventyaPDF {APP_VERSION}</h3>" + enlace)
            descargar = None
            caja.addButton("Cerrar", QMessageBox.ButtonRole.RejectRole)
        caja.setTextFormat(Qt.TextFormat.RichText)
        caja.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        caja.exec()
        if omitir is not None and omitir.isChecked():
            s = QSettings(*SETTINGS)
            s.setValue(_KEY_SKIP_VERSION, info["version"])
            s.sync()
        if descargar is not None and caja.clickedButton() is descargar:
            QDesktopServices.openUrl(QUrl(info["installer_url"]))

    # ── aviso automático al iniciar (petición de Ricardo) ─────────────── #

    def start_update_check(self, delay_ms: int = 4000) -> None:
        """Al arrancar (main.py): si está activado, comprueba en segundo plano
        si hay una versión nueva, sin frenar el arranque. Solo avisa si la
        hay; sin conexión o al día, no dice nada."""
        if not self._auto_update_enabled():
            return
        self._update_notifier = _UpdateNotifier()
        self._update_notifier.found.connect(self._on_update_found)
        QTimer.singleShot(delay_ms, self._update_notifier.start)

    def _on_update_found(self, info: dict) -> None:
        if not actualizaciones.is_newer(info["version"], APP_VERSION):
            return
        if QSettings(*SETTINGS).value(_KEY_SKIP_VERSION, "") == info["version"]:
            return                               # el usuario pidió no avisar de esta
        # No encima de otra ventana (la presentación inicial, un diálogo…):
        # se espera a que se cierre.
        if QApplication.activeModalWidget() is not None:
            QTimer.singleShot(2000, lambda: self._on_update_found(info))
            return
        self._show_update_dialog(info, automatic=True)

    @staticmethod
    def _auto_update_enabled() -> bool:
        return QSettings(*SETTINGS).value(_KEY_AUTO_UPDATE, "true") == "true"

    def _set_auto_update(self, on: bool) -> None:
        s = QSettings(*SETTINGS)
        s.setValue(_KEY_AUTO_UPDATE, "true" if on else "false")
        s.sync()

    def show_about(self):
        try:
            import pyhanko
            hanko = pyhanko.__version__
        except Exception:
            hanko = "?"
        caja = QMessageBox(self)
        caja.setWindowTitle("Acerca de AventyaPDF")
        caja.setText(
            f"<h3>AventyaPDF {APP_VERSION}</h3>"
            "<p>Visor, editor y firmador de PDF para Windows.</p>"
            "<p>Comentarios y marcado de texto · formularios · organización de páginas · "
            "marcas de agua, encabezados y Bates · redacción · OCR · cifrado AES-256 · "
            "firma PAdES con sellado de tiempo y validación de firmas.</p>"
            f"<p style='color:#605E5C'>PyMuPDF {fitz.VersionBind} · pyHanko {hanko}</p>"
            f"<p>© {datetime.date.today().year} {APP_OWNER}<br>"
            "Aplicación de libre distribución (licencia AGPL-3.0).<br>"
            f"Código fuente: <a href='{APP_REPO}'>{APP_REPO}</a></p>")
        caja.setTextFormat(Qt.TextFormat.RichText)
        caja.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        # (r64) El icono de la app a 64 px (el .ico trae 64 a 256 para cada
        # escala de pantalla); QMessageBox.about lo dejaba en 32 px.
        caja.setIconPixmap(QIcon(icons.APP_ICON).pixmap(64, 64))
        caja.exec()
