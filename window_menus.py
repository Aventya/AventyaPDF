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
from PyQt6.QtGui import QAction, QActionGroup, QDesktopServices, QIcon, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication, QCheckBox, QFileDialog, QFrame, QHBoxLayout, QInputDialog, QLabel,
    QLineEdit, QMessageBox, QProgressDialog, QPushButton, QWidget,
)

import actualizaciones
import conversion_office
import menu_contextual
import dependencias
import dialogs
import doc_tools
import icons
import pdf_ocr
import tesseract_setup
import tesseract_ui
from tsa import TSA_PRESETS
import idioma
from idioma import tr

SETTINGS = ("aventyapdf", "config")
APP_VERSION = "0.9.14"
# (r71) Titular y repositorio público (AGPL-3.0, libre distribución).
APP_OWNER = tr("Aventya Asesoría Integral SL")
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


class _InstallerDownload(QObject):
    """(r121) Descarga el instalador en un hilo aparte (sin navegador)."""
    progreso = pyqtSignal(int, int)
    listo = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, info: dict):
        super().__init__()
        self._info = info

    def start(self) -> None:
        import threading
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self) -> None:
        try:
            ruta = actualizaciones.download_installer(
                self._info, progress=lambda h, t: self.progreso.emit(h, t))
        except actualizaciones.UpdateError as e:
            self.error.emit(str(e))
            return
        self.listo.emit(ruta)


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

    def choose_language(self, codigo: str):
        """(r136) Ayuda › Idioma: se guarda y se aplica al volver a abrir. El
        aviso sale ya en el idioma elegido."""
        if codigo == idioma.ACTUAL:
            return
        idioma.guardar(codigo)
        QMessageBox.information(
            self, idioma.tr_en(codigo, "Idioma"),
            idioma.tr_en(codigo, "AventyaPDF se mostrará en {idioma} la próxima vez que "
                                 "lo abras.").format(idioma=idioma.IDIOMAS[codigo]))

    def _build_menus(self):
        self._doc_actions = []
        A = self._action
        mb = self.menuBar()

        m = mb.addMenu(tr("&Archivo"))
        A(m, tr("Nuevo PDF en blanco"), self.new_blank_document, "Ctrl+N", needs_doc=False)
        A(m, tr("Crear PDF desde imágenes…"), self.create_from_images, needs_doc=False)
        A(m, tr("Abrir…"), self.open_pdf, "Ctrl+O", needs_doc=False)
        self._menu_recent = m.addMenu(tr("Abrir reciente"))
        self._menu_recent.aboutToShow.connect(self._fill_recent_menu)
        m.addSeparator()
        A(m, tr("Guardar"), self.save_pdf, "Ctrl+S")
        A(m, tr("Guardar como…"), self.save_pdf_as, "Ctrl+Shift+S")
        exp = m.addMenu(tr("Exportar"))
        A(exp, tr("Páginas como imágenes…"), self.export_images)
        A(exp, tr("Texto (.txt)…"), self.export_text)
        A(exp, tr("Documento de Word (.docx)…"), self.export_word)
        A(exp, tr("Extraer páginas a PDF…"), self.extract_pages_dialog)
        m.addSeparator()
        A(m, tr("Imprimir…"), self.print_pdf, "Ctrl+P")
        A(m, tr("Propiedades del documento…"), self.show_properties, "Ctrl+D")
        m.addSeparator()
        A(m, tr("Cerrar documento"), self.close_document, "Ctrl+W")
        A(m, tr("Salir"), self.close, "Ctrl+Q", needs_doc=False)

        m = mb.addMenu(tr("&Edición"))
        self._act_undo = A(m, tr("Deshacer"), self.undo, "Ctrl+Z")
        self._act_redo = A(m, tr("Rehacer"), self.redo, ["Ctrl+Y", "Ctrl+Shift+Z"])
        m.addSeparator()
        A(m, tr("Copiar texto seleccionado"), self.copy_selected_text, "Ctrl+C")
        m.addSeparator()
        A(m, tr("Buscar…"), self.show_find, "Ctrl+F")
        A(m, tr("Buscar siguiente"), self.find_next, "F3")
        A(m, tr("Buscar anterior"), self.find_prev, "Shift+F3")

        m = mb.addMenu(tr("&Ver"))
        A(m, tr("Mostrar u ocultar panel lateral"), self.sidebar_toggle, "F4", needs_doc=False)
        A(m, tr("Miniaturas de página"), lambda: self.sidebar.show_panel("thumbs"), needs_doc=False)
        A(m, tr("Marcadores"), lambda: self.sidebar.show_panel("bookmarks"), needs_doc=False)
        A(m, tr("Comentarios"), lambda: self.sidebar.show_panel("comments"), needs_doc=False)
        A(m, tr("Firmas certificadas"), lambda: self.sidebar.show_panel("signatures"), needs_doc=False)
        self._act_highlight_fields = A(m, tr("Resaltar campos de formulario"),
                                       self.toggle_highlight_fields, needs_doc=False)
        self._act_highlight_fields.setCheckable(True)
        self._act_highlight_fields.setChecked(
            QSettings(*SETTINGS).value("view/highlight_fields", True, type=bool))
        m.addSeparator()
        A(m, tr("Acercar"), lambda: self.zoom_step(1), ["Ctrl++", "Ctrl+="])
        A(m, tr("Alejar"), lambda: self.zoom_step(-1), "Ctrl+-")
        A(m, tr("Tamaño real (100 %)"), self.zoom_actual, "Ctrl+0")
        A(m, tr("Ajustar al ancho"), self.zoom_fit_width, "Ctrl+1")
        A(m, tr("Ajustar a la página"), self.zoom_fit_page, "Ctrl+2")
        m.addSeparator()
        A(m, tr("Primera página"), self.first_page, "Home")
        A(m, tr("Página anterior"), self.prev_page, "PgUp")
        A(m, tr("Página siguiente"), self.next_page, "PgDown")
        A(m, tr("Última página"), self.last_page, "End")
        A(m, tr("Ir a página…"), self.ask_go_to_page, "Ctrl+G")
        m.addSeparator()
        A(m, tr("Documento siguiente"), self.next_document, "Ctrl+Tab", needs_doc=False)
        A(m, tr("Documento anterior"), lambda: self.next_document(-1), "Ctrl+Shift+Tab",
          needs_doc=False)

        m = mb.addMenu(tr("&Comentar"))
        for text, mode, key in [
            (tr("Herramienta de selección"), "NONE", "V"),
            (tr("Añadir texto"), "TEXT", "T"),
            (tr("Nota adhesiva"), "NOTE", "N"),
            (tr("Resaltar, subrayar o tachar"), "MARKUP", "H"),
            (tr("Rectángulo"), "RECT", "R"),
            ("Emoji", "EMOJI", "E"),
            (tr("Borrador de anotaciones"), "ERASE", None),
        ]:
            A(m, text, lambda md=mode: self._select_tool(md), key)
        m.addSeparator()
        A(m, tr("Aplanar anotaciones y formularios…"), self.flatten_document)

        m = mb.addMenu(tr("&Organizar"))
        A(m, tr("Organizar páginas en el panel lateral"), self.organize_pages)
        m.addSeparator()
        A(m, tr("Insertar página en blanco"), lambda: self.insert_blank_after(self.current_page))
        A(m, tr("Insertar PDF tras la página actual…"), self.insert_pdf_after_current)
        A(m, tr("Añadir PDF al final…"), self.merge_pdf)
        sub = m.addMenu(tr("Combinar PDF…"))
        self._act_combine_open = A(sub, tr("Combinar abiertos"), self.combine_open_documents,
                                   needs_doc=False)
        A(sub, tr("Combinar archivos…"), self.combine_files_dialog, needs_doc=False)
        sub.aboutToShow.connect(
            lambda: self._act_combine_open.setEnabled(len(self._sessions) >= 2))
        A(m, tr("Duplicar página actual"), self.copy_page)
        A(m, tr("Eliminar páginas…"), self.delete_pages_dialog)
        A(m, tr("Extraer páginas…"), self.extract_pages_dialog)
        A(m, tr("Dividir documento…"), self.split_document)
        m.addSeparator()
        A(m, tr("Girar página a la derecha"), lambda: self.rotate_current(90), "Ctrl+Shift+R")
        A(m, tr("Girar página a la izquierda"), lambda: self.rotate_current(-90), "Ctrl+Shift+L")
        A(m, tr("Girar páginas…"), self.rotate_pages_dialog)

        m = mb.addMenu(tr("&Herramientas"))
        A(m, tr("Editar texto e imágenes del PDF"), lambda: self._select_tool("EDIT"), "C")
        m.addSeparator()
        A(m, tr("Marca de agua…"), self.add_watermark)
        A(m, tr("Encabezado, pie y numeración Bates…"), self.add_header_footer)
        self._act_ocr = A(m, tr("Reconocer texto (OCR)…"), self.run_ocr)
        A(m, tr("Optimizar y comprimir…"), self.compress_dialog)

        m = mb.addMenu(tr("&Proteger"))
        A(m, tr("Proteger con contraseña…"), self.protect_document)
        A(m, "Quitar seguridad", self.remove_security)

        m = mb.addMenu(tr("&Firmar"))
        A(m, tr("Firmar documento (dibujar área)"), lambda: self._select_tool("SIGN"))
        A(m, tr("Insertar firma manuscrita (dibujada o imagen)…"), self._menu_hand_signature)
        A(m, tr("Opciones de firma…"), self.sign_options, needs_doc=False)
        A(m, tr("Certificado de firma…"), self._change_cert, needs_doc=False)
        m.addSeparator()
        A(m, tr("Ver las firmas (verificadas)"), self.show_signatures)

        m = mb.addMenu(tr("A&yuda"))
        A(m, tr("Atajos de teclado"), lambda: dialogs.show_shortcuts(self), "F1", needs_doc=False)
        A(m, tr("Presentación de AventyaPDF"), self.show_welcome, needs_doc=False)
        # (r136) Idioma de la aplicación: cada idioma con su propio nombre.
        lang = m.addMenu(tr("Idioma"))
        grupo = QActionGroup(self)
        for codigo, nombre in idioma.IDIOMAS.items():
            act = lang.addAction(nombre)
            act.setCheckable(True)
            act.setChecked(codigo == idioma.ACTUAL)
            grupo.addAction(act)
            act.triggered.connect(lambda _c=False, c=codigo: self.choose_language(c))
        m.addSeparator()
        if not dependencias.en_paquete_msix():
            # (r119) En la versión de la Microsoft Store las actualizaciones
            # las instala la propia Store: ni menú ni aviso al iniciar.
            A(m, tr("Buscar actualizaciones…"), self.check_updates, needs_doc=False)
            # (petición de Ricardo) Aviso automático al iniciar, activado de entrada.
            self._act_auto_update = QAction(tr("Avisar de actualizaciones al iniciar"), self)
            self._act_auto_update.setCheckable(True)
            self._act_auto_update.setChecked(self._auto_update_enabled())
            self._act_auto_update.toggled.connect(self._set_auto_update)
            m.addAction(self._act_auto_update)
        if menu_contextual.puede_reparar():
            A(m, tr("Reparar el menú contextual del Explorador…"),
              self.repair_context_menu, needs_doc=False)
        A(m, tr("Acerca de AventyaPDF"), self.show_about, needs_doc=False)

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
        self._find_edit.setPlaceholderText(tr("Buscar…"))
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
        for key, tip, fn in [("find_prev", tr("Anterior (Mayús+F3)"), self.find_prev),
                             ("find_next", tr("Siguiente (F3)"), self.find_next)]:
            b = self._glyph_btn(key, tip)
            b.clicked.connect(lambda _c=False, f=fn: f())
            lay.addWidget(b)
        close = self._glyph_btn("close", tr("Cerrar (Esc)"))
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
            QMessageBox.critical(self, label, tr("No se pudo completar la operación:\n{e}").format(e=e))
            return None, False
        QApplication.restoreOverrideCursor()
        self.mark_modified(structure=structure)
        self.render_page()
        self.statusBar().showMessage(tr("{label}: hecho").format(label=label))
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
        self.statusBar().showMessage(tr("Nuevo documento en blanco (A4)"))

    def create_from_images(self, paths=None):
        if not paths:
            paths, _ = QFileDialog.getOpenFileNames(
                self, tr("Crear PDF desde imágenes"), self._start_dir(), doc_tools.IMAGE_FILTER)
            if not paths:
                return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            doc = doc_tools.images_to_pdf(list(paths))
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, tr("Crear PDF"), tr("No se pudieron convertir las imágenes:\n{e}").format(e=e))
            return
        QApplication.restoreOverrideCursor()
        self._begin_new_session()              # en una pestaña nueva
        self._set_document(doc, "", None, modified=True)
        self.statusBar().showMessage(tr("PDF creado a partir de {n} imágenes — sin guardar").format(n=len(paths)))

    def combine_pdfs_from_paths(self, paths):
        """(r55) Menú contextual del Explorador de Windows: combina varios PDF
        elegidos en el Explorador (sin necesidad de abrir ninguno antes) en un
        documento nuevo sin guardar, en una pestaña nueva. A diferencia de
        `merge_pdf()`, que añade un único PDF al final del documento ya
        abierto, aquí no hay documento previo: se parte de cero."""
        paths = [p for p in paths if p.lower().endswith(".pdf")]
        if len(paths) < 2:
            QMessageBox.warning(self, tr("Combinar PDF"),
                                tr("Hacen falta al menos dos archivos PDF para combinarlos."))
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            doc = doc_tools.merge_pdfs(paths)
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, tr("Combinar PDF"), tr("No se pudieron combinar los archivos:\n{e}").format(e=e))
            return
        QApplication.restoreOverrideCursor()
        self._begin_new_session()
        self._set_document(doc, "", None, modified=True)
        self.statusBar().showMessage(tr("PDF combinado a partir de {n} archivos — sin guardar").format(n=len(paths)))

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
            QMessageBox.critical(self, tr("Convertir imágenes"), tr("No se pudieron convertir las imágenes:\n{e}").format(e=e))
            return
        QApplication.restoreOverrideCursor()
        for doc in docs:
            self._begin_new_session()
            self._set_document(doc, "", None, modified=True)
        self.statusBar().showMessage(tr("{n} PDF creados a partir de imágenes — sin guardar").format(n=len(docs)))

    def combine_files_to_pdf(self, paths):
        """(r86) Menú contextual del Explorador, «Combinar en un PDF»: PDF,
        imágenes y documentos de Word mezclados, en el orden recibido, en un
        único documento nuevo sin guardar."""
        paths = [p for p in paths if conversion_office.tipo_de(p)]
        if len(paths) < 2:
            QMessageBox.warning(self, tr("Combinar en un PDF"),
                                tr("Hacen falta al menos dos archivos (PDF, imágenes o Word) para combinarlos."))
            return
        doc = self._convert_paths(paths, tr("Combinar en un PDF"), conversion_office.combinar_archivos)
        if doc is None:
            return
        self._begin_new_session()
        self._set_document(doc, "", None, modified=True)
        self.statusBar().showMessage(tr("PDF combinado a partir de {n} archivos — sin guardar").format(n=len(paths)))

    def convert_files_to_pdfs(self, paths):
        """(r86) Menú contextual del Explorador, «Convertir a PDF»: cada imagen
        o documento de Word en su propio PDF, cada uno en una pestaña nueva sin
        guardar."""
        paths = [p for p in paths if conversion_office.tipo_de(p) in ("img", "word")]
        if not paths:
            return
        docs = self._convert_paths(paths, tr("Convertir a PDF"))
        if docs is None:
            return
        for doc in docs:
            self._begin_new_session()
            self._set_document(doc, "", None, modified=True)
        self.statusBar().showMessage(tr("{n} PDF creados — sin guardar").format(n=len(docs)))

    def sign_files(self, paths):
        """(r86) Menú contextual del Explorador, «Firmar digitalmente»: abre
        los PDF y deja puesta la herramienta Firma en el último."""
        abiertos = [p for p in paths if p.lower().endswith(".pdf") and self.open_path(p)]
        if abiertos:
            self._select_tool("SIGN")

    def combine_files_dialog(self):
        """(r123) Organizar › Combinar PDF › Combinar archivos…: elige varios
        archivos (PDF, imágenes o Word) y los combina en un PDF nuevo sin
        guardar, en una pestaña nueva. Se combinan en el orden natural de sus
        nombres (el diálogo de Windows no devuelve el orden en que se pulsaron);
        después se pueden reordenar las páginas en el panel lateral."""
        paths, _ = QFileDialog.getOpenFileNames(
            self, tr("Combinar archivos en un PDF"), self._start_dir(),
            conversion_office.FILTRO_ABRIR)
        if not paths:
            return
        if len(paths) < 2:
            QMessageBox.warning(self, tr("Combinar archivos"),
                                tr("Selecciona al menos dos archivos para combinarlos "
                                "(con Ctrl o Mayús pulsada)."))
            return
        self.combine_files_to_pdf(sorted(paths, key=menu_contextual._orden_natural))

    def combine_open_documents(self):
        """(r123) Organizar › Combinar PDF › Combinar abiertos: todas las
        pestañas, en su orden, en un único PDF nuevo sin guardar. Se cierran
        todas y queda solo la del resultado. Entra el contenido tal como se ve
        (también los cambios aún sin guardar); los archivos del disco no se tocan."""
        n = len(self._sessions)
        if n < 2:
            QMessageBox.information(self, tr("Combinar abiertos"),
                                    tr("Hacen falta al menos dos documentos abiertos para combinarlos."))
            return
        if self._sign_worker is not None and self._sign_worker.isRunning():
            self.statusBar().showMessage(tr("Espera a que termine la firma en curso"))
            return
        dirty = [i for i in range(n) if self._session_dirty(i)]
        text = tr("Se combinarán los {n} documentos abiertos, en el orden de sus pestañas, " \
               "en un PDF nuevo sin guardar, y se cerrarán sus pestañas.").format(n=n)
        if dirty:
            text += tr(("\n\n{n} de ellos tienen cambios sin guardar: los cambios "
                     "entran en el PDF combinado, pero no se guardarán en sus archivos.")).format(n=len(dirty))
        r = QMessageBox.question(self, tr("Combinar abiertos"), text + tr("\n\n¿Continuar?"),
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                 QMessageBox.StandardButton.Yes)
        if r != QMessageBox.StandardButton.Yes:
            return
        self._stash_active()
        docs = [s["doc"] for s in self._sessions]
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            out = conversion_office.combinar(docs)
        except Exception as e:
            QApplication.restoreOverrideCursor()
            self._restore_session(self._active)
            QMessageBox.critical(self, tr("Combinar abiertos"), tr("No se pudieron combinar:\n{e}").format(e=e))
            return
        QApplication.restoreOverrideCursor()
        for d in docs:
            try:
                d.close()
            except Exception:
                pass
        self._sessions = []
        self._active = -1
        self._reset_document_fields()
        self._set_document(out, "", None, modified=True)
        self.statusBar().showMessage(
            tr("PDF combinado a partir de {n} documentos abiertos — sin guardar").format(n=n))

    def _convert_paths(self, paths, titulo, fn=conversion_office.archivos_a_pdfs):
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        if any(conversion_office.tipo_de(p) == "word" for p in paths):
            self.statusBar().showMessage(tr("Convirtiendo documentos de Word…"))
            QApplication.processEvents()
        try:
            return fn(paths)
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, titulo, tr("No se pudieron convertir los archivos:\n{e}").format(e=e))
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
        self._run_doc_change(tr("Propiedades del documento"),
                             lambda: self.doc.set_metadata(meta), structure=False)

    def export_images(self):
        if self.doc is None:
            return
        dlg = dialogs.ExportImagesDialog(self, len(self.doc), self.current_page)
        if not dlg.exec():
            return
        v = dlg.values()
        folder = QFileDialog.getExistingDirectory(self, tr("Carpeta de destino"), self._start_dir())
        if not folder:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            files = doc_tools.export_images(self.doc, v["pages"], folder, self._base_name(),
                                            v["dpi"], v["fmt"])
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, tr("Exportar imágenes"), tr("No se pudo exportar:\n{e}").format(e=e))
            return
        QApplication.restoreOverrideCursor()
        QMessageBox.information(self, tr("Exportar imágenes"),
                                tr("{n} imágenes guardadas en:\n{folder}").format(n=len(files), folder=folder))

    def export_text(self):
        if self.doc is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("Exportar texto"), os.path.join(self._start_dir(), self._base_name() + ".txt"),
            tr("Texto (*.txt)"))
        if not path:
            return
        try:
            doc_tools.export_text(self.doc, path)
            self.statusBar().showMessage(tr("Texto exportado a {nombre}").format(nombre=os.path.basename(path)))
        except Exception as e:
            QMessageBox.critical(self, tr("Exportar texto"), tr("No se pudo exportar:\n{e}").format(e=e))

    def export_word(self):
        if self.doc is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, tr("Exportar a Word"), os.path.join(self._start_dir(), self._base_name() + ".docx"),
            tr("Documento de Word (*.docx)"))
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
            ok, msg = True, tr("Documento de Word guardado en:\n{path}").format(path=path)
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
            QMessageBox.information(self, tr("Exportar a Word"), msg)
        else:
            QMessageBox.warning(self, tr("Exportar a Word"), msg)

    # ── organizar ──────────────────────────────────────────────────────── #

    def insert_pdf_after_current(self):
        if self.doc is not None:
            self.insert_pdf_after(self.current_page)

    def insert_pdf_after(self, pno: int):
        if self.doc is None:
            return
        path, _ = QFileDialog.getOpenFileName(self, tr("Insertar PDF"), self._start_dir(),
                                              tr("Archivos PDF (*.pdf)"))
        if not path:
            return
        try:
            src = fitz.open(path)
        except Exception as e:
            QMessageBox.warning(self, tr("Insertar PDF"), tr("No se pudo abrir:\n{e}").format(e=e))
            return
        if src.needs_pass:
            src.close()
            QMessageBox.warning(self, tr("Insertar PDF"), tr("El PDF a insertar está protegido con contraseña."))
            return
        pos = pno + 1
        n, ok = self._run_doc_change(
            tr("Insertar PDF"), lambda: doc_tools.insert_pdf_at(self.doc, src, pos))
        src.close()
        if ok:
            self.sidebar.thumbs.select_after_rebuild(list(range(pos, pos + n)))
            self.go_to_page(pos)
            self.statusBar().showMessage(tr("{n} páginas insertadas tras la página {pos}").format(n=n, pos=pos))

    def delete_pages_dialog(self):
        if self.doc is None:
            return
        pages = dialogs.ask_page_range(self, tr("Eliminar páginas"), len(self.doc),
                                       str(self.current_page + 1))
        if pages:
            self.delete_pages(pages)

    def extract_pages_dialog(self):
        if self.doc is None:
            return
        pages = dialogs.ask_page_range(self, tr("Extraer páginas"), len(self.doc),
                                       str(self.current_page + 1))
        if pages:
            self.extract_pages(pages)

    def rotate_pages_dialog(self):
        if self.doc is None:
            return
        pages = dialogs.ask_page_range(self, tr("Girar páginas"), len(self.doc), "")
        if not pages:
            return
        items = [tr("90° a la derecha"), tr("90° a la izquierda"), "180°"]
        choice, ok = QInputDialog.getItem(self, tr("Girar páginas"), tr("Sentido:"), items, 0, False)
        if ok:
            self.rotate_pages(pages, {items[0]: 90, items[1]: -90, items[2]: 180}[choice])

    def split_document(self):
        if self.doc is None:
            return
        n, ok = QInputDialog.getInt(self, tr("Dividir documento"), tr("Páginas por archivo:"),
                                    1, 1, max(1, len(self.doc)))
        if not ok:
            return
        folder = QFileDialog.getExistingDirectory(self, tr("Carpeta de destino"), self._start_dir())
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
            QMessageBox.critical(self, tr("Dividir documento"), tr("No se pudo dividir:\n{e}").format(e=e))
            return
        QApplication.restoreOverrideCursor()
        QMessageBox.information(self, tr("Dividir documento"), tr("{count} archivos creados en:\n{folder}").format(count=count, folder=folder))

    # ── herramientas ───────────────────────────────────────────────────── #

    def add_watermark(self):
        if self.doc is None:
            return
        dlg = dialogs.WatermarkDialog(self, len(self.doc))
        if not dlg.exec():
            return
        v = dlg.values()
        self._run_doc_change(tr("Marca de agua"), lambda: doc_tools.add_watermark(
            self.doc, v["pages"], v["text"], v["fontsize"], v["color"], v["opacity"], v["angle"]))

    def add_header_footer(self):
        if self.doc is None:
            return
        dlg = dialogs.HeaderFooterDialog(self, len(self.doc))
        if not dlg.exec():
            return
        v = dlg.values()
        self._run_doc_change(tr("Encabezado y pie"),
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
            act.setText(tr("Reconocer texto (OCR)…") if available
                        else tr("Reconocer texto (OCR) — Tesseract no instalado"))
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
            QMessageBox.information(self, tr("Reconocer texto (OCR)"),
                                    tr("Todas las páginas ya contienen texto seleccionable."))
            return
        # Tesseract es obligatorio: si falta él o el idioma elegido, se instala ahora.
        if not tesseract_ui.ensure_languages(self, v["lang"]):
            return
        progress = QProgressDialog(tr("Reconociendo texto…"), tr("Cancelar"), 0, len(pages), self)
        progress.setWindowTitle(tr("Reconocer texto (OCR)"))
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        # La capa de texto se añade sobre las páginas originales (pdf_ocr): un solo
        # paso de deshacer para todo el documento.
        self.checkpoint(tr("Reconocer texto (OCR)"))
        words = changed = 0
        try:
            for n, i in enumerate(pages):
                progress.setValue(n)
                progress.setLabelText(tr("Página {valor} de {total}…").format(valor=i + 1, total=total))
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
                self, tr("Reconocer texto (OCR)"),
                tr("No se pudo reconocer el texto.\n\n"
                "Tesseract: {valor}\n"
                "Idiomas: {TESSDATA_DIR}\n\n"
                "Detalle: {e}").format(valor=tesseract_setup.find_tesseract() or tr('no encontrado'), TESSDATA_DIR=tesseract_setup.TESSDATA_DIR, e=e))
            return
        progress.close()
        if not words:
            self._rollback_last()          # no dejar un paso de deshacer vacío
            self.render_page()
            QMessageBox.information(self, tr("Reconocer texto (OCR)"),
                                    tr("No se ha encontrado texto nuevo que reconocer."))
            return
        self.mark_modified(structure=False)
        self.render_page()
        QMessageBox.information(self, tr("Reconocer texto (OCR)"),
                                tr("Se han reconocido {words} palabras en {changed} de "
                                "{n} páginas. Ya puedes buscar y seleccionar ese texto.").format(words=words, changed=changed, n=len(pages)))

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
            self, tr("Aplanar"),
            tr("Las anotaciones y los campos de formulario pasarán a formar parte del "
            "contenido y ya no se podrán editar. ¿Continuar?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            self._run_doc_change(tr("Aplanar"), lambda: doc_tools.flatten(self.doc))

    # ── proteger ───────────────────────────────────────────────────────── #

    def protect_document(self):
        if self.doc is None:
            return
        dlg = dialogs.SecurityDialog(self)
        if dlg.exec():
            self._encrypt_opts = dlg.values()
            self.mark_modified()
            QMessageBox.information(self, tr("Proteger con contraseña"),
                                    tr("La protección se aplicará al guardar el documento (Ctrl+S)."))

    def remove_security(self):
        if self.doc is None:
            return
        protected = self._orig_encrypted or (
            self._encrypt_opts and self._encrypt_opts.get("encryption") != fitz.PDF_ENCRYPT_NONE)
        if not protected:
            QMessageBox.information(self, "Quitar seguridad", tr("El documento no está protegido."))
            return
        self._encrypt_opts = {"encryption": fitz.PDF_ENCRYPT_NONE}
        self.mark_modified()
        QMessageBox.information(self, "Quitar seguridad",
                                tr("El cifrado se eliminará al guardar el documento (Ctrl+S)."))

    # ── firmar ─────────────────────────────────────────────────────────── #

    def sign_options(self):
        has_sigs = self.doc is not None and doc_tools.has_signatures(self.doc)
        dialogs.SignOptionsDialog(self, has_sigs, TSA_PRESETS, ok_text=tr("Guardar")).exec()

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
            caja = QMessageBox(QMessageBox.Icon.Warning, tr("Buscar actualizaciones"),
                               "", parent=self)
            caja.setText(
                tr("<p>No se pudo comprobar si hay una versión nueva.</p><p>{e}</p>"
                "<p>Puedes consultarlas en <a href='{RELEASES_URL}'>"
                "{RELEASES_URL}</a></p>").format(e=e, RELEASES_URL=actualizaciones.RELEASES_URL))
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
        nombre = info["installer_name"] or tr("la página de la versión")
        enlace = (f"<p>Enlace directo de descarga:<br>"
                  f"<a href='{info['installer_url']}'>{nombre}</a></p>"
                  f"<p style='color:#605E5C'>Novedades: <a href='{info['page_url']}'>"
                  f"AventyaPDF {info['version']}</a></p>")
        caja = QMessageBox(self)
        caja.setWindowTitle(tr("Actualización disponible") if automatic else tr("Buscar actualizaciones"))
        caja.setIconPixmap(QIcon(icons.APP_ICON).pixmap(64, 64))
        omitir = None
        descargado = actualizaciones.instalador_descargado(info) if nueva else None
        if descargado:
            # (r127) Ya está en Descargas, esperando a que el usuario la instale.
            caja.setText(
                tr("<h3>Hay una versión nueva: AventyaPDF {info}</h3>"
                "<p>Tienes la {APP_VERSION}. La nueva <b>ya está descargada</b> y comprobada "
                "en tu carpeta Descargas, esperando a que la instales:</p>"
                "<p><b>{nombre}</b></p>"
                "<p>Para instalarla, cierra AventyaPDF y ejecuta ese archivo.</p>").format(info=info['version'], APP_VERSION=APP_VERSION, nombre=os.path.basename(descargado)) + enlace)
            descargar = caja.addButton(tr("Mostrar en Descargas"), QMessageBox.ButtonRole.AcceptRole)
            caja.addButton(tr("Ahora no") if automatic else tr("Cerrar"), QMessageBox.ButtonRole.RejectRole)
            caja.setDefaultButton(descargar)
            if automatic:
                omitir = QCheckBox(tr("No volver a avisar de esta versión"))
                caja.setCheckBox(omitir)
        elif nueva:
            caja.setText(
                tr("<h3>Hay una versión nueva: AventyaPDF {info}</h3>"
                "<p>Tienes la {APP_VERSION}. Se descarga en tu carpeta Descargas; "
                "después cierras AventyaPDF y la instalas ejecutando el archivo "
                "descargado.</p>").format(info=info['version'], APP_VERSION=APP_VERSION) + enlace)
            descargar = caja.addButton(tr("Descargar"), QMessageBox.ButtonRole.AcceptRole)
            caja.addButton(tr("Ahora no") if automatic else tr("Cerrar"), QMessageBox.ButtonRole.RejectRole)
            caja.setDefaultButton(descargar)
            if automatic:
                omitir = QCheckBox(tr("No volver a avisar de esta versión"))
                caja.setCheckBox(omitir)
        else:
            caja.setText(
                tr("<h3>Tienes la última versión: AventyaPDF {APP_VERSION}</h3>").format(APP_VERSION=APP_VERSION) + enlace)
            descargar = None
            caja.addButton(tr("Cerrar"), QMessageBox.ButtonRole.RejectRole)
        caja.setTextFormat(Qt.TextFormat.RichText)
        caja.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        caja.exec()
        if omitir is not None and omitir.isChecked():
            s = QSettings(*SETTINGS)
            s.setValue(_KEY_SKIP_VERSION, info["version"])
            s.sync()
        if descargar is not None and caja.clickedButton() is descargar:
            if descargado:
                actualizaciones.mostrar_en_carpeta(descargado)
            elif info.get("installer_name"):
                self._download_update(info)
            else:       # publicación sin instalador: su página
                QDesktopServices.openUrl(QUrl(info["installer_url"]))

    def _download_update(self, info: dict) -> None:
        """(r121, r127) Descarga el instalador en segundo plano, sin navegador,
        a la carpeta Descargas, y comprueba su huella SHA-256 con la que
        publica GitHub. No lo ejecuta: (r127, petición de Ricardo: «que se
        quedase en la carpeta Descargas y se indique que la actualización
        está allí esperando a que la instale el usuario, para que la
        aplicación no utilice PowerShell») avisa de dónde está y lo instala
        el usuario. Hasta r125 la aplicación se cerraba y lo lanzaba con
        PowerShell, y eso hacía que Microsoft Defender la marcara."""
        progreso = QProgressDialog(tr("Descargando AventyaPDF {info}…").format(info=info['version']), "", 0, 100, self)
        progreso.setCancelButton(None)
        progreso.setWindowTitle(tr("Actualizar AventyaPDF"))
        progreso.setWindowModality(Qt.WindowModality.WindowModal)
        progreso.setMinimumDuration(0)
        progreso.setValue(0)
        tarea = _InstallerDownload(info)
        self._installer_download = tarea

        def avance(hecho: int, total: int) -> None:
            if total:
                progreso.setValue(min(100, hecho * 100 // total))

        def fallo(texto: str) -> None:
            progreso.close()
            QMessageBox.warning(self, tr("Actualizar AventyaPDF"),
                                tr("{texto}\n\nPuedes descargarla a mano desde {info}").format(texto=texto, info=info['page_url']))

        def listo(ruta: str) -> None:
            progreso.close()
            caja = QMessageBox(QMessageBox.Icon.Information, tr("Actualizar AventyaPDF"), "", parent=self)
            caja.setText(
                tr("<p>AventyaPDF {info} está descargada y comprobada en tu carpeta "
                "Descargas, esperando a que la instales:</p>"
                "<p><b>{nombre}</b></p>"
                "<p>Para instalarla, cierra AventyaPDF y ejecuta ese archivo. Mientras no "
                "la instales, AventyaPDF te recordará que está ahí.</p>").format(info=info['version'], nombre=os.path.basename(ruta)))
            caja.setTextFormat(Qt.TextFormat.RichText)
            mostrar = caja.addButton(tr("Mostrar en Descargas"), QMessageBox.ButtonRole.AcceptRole)
            caja.addButton(tr("Aceptar"), QMessageBox.ButtonRole.RejectRole)
            caja.setDefaultButton(mostrar)
            caja.exec()
            if caja.clickedButton() is mostrar:
                actualizaciones.mostrar_en_carpeta(ruta)

        tarea.progreso.connect(avance)
        tarea.error.connect(fallo)
        tarea.listo.connect(listo)
        tarea.start()

    def repair_context_menu(self) -> None:
        """(r121) Ayuda › Reparar el menú contextual del Explorador…: vuelve a
        confiar en el certificado del paquete (con permiso de administrador) y
        registra el submenú «AventyaPDF» en el menú principal de Windows 11."""
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            ok, texto = menu_contextual.reparar()
        finally:
            QApplication.restoreOverrideCursor()
        (QMessageBox.information if ok else QMessageBox.warning)(
            self, tr("Menú contextual del Explorador"), texto)

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
        if dependencias.en_paquete_msix():
            return False
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
        caja.setWindowTitle(tr("Acerca de AventyaPDF"))
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
