import os
import fitz

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QScrollArea, QStackedWidget, QFileDialog,
    QMessageBox, QFrame, QLineEdit, QSplitter,
    QAbstractSpinBox, QSpinBox, QComboBox, QSlider,
    QGridLayout, QSizePolicy, QStyle, QStyledItemDelegate,
)
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QFont
from PyQt6.QtCore import Qt, QTimer, QRectF, QSize

# (r36) Iconos: Fluent UI System Icons (icons.py). Mismas claves que antes.
import icons  # noqa: E402
_G = {k: icons.glyph(k) for k in icons.ICONS}

from utils import PDFUtils, TOOLTIP_QSS
from cert_manager import load_saved_cert, forget_cert, CertPickerDialog
import doc_tools
import emoji_font
import pdf_edit
import pdf_compression
import color_picker
import firma_manuscrita
from emoji_picker import EmojiPicker
from sidebar import SidePanel
from viewer import FREEHAND_WIDTHS, AnnotSelection, PDFViewerWidget
from window_document import DocumentMixin
from window_menus import MenusMixin


# ─────────────────────────────────────────────────────────────────────────────
# Color swatch button
# ─────────────────────────────────────────────────────────────────────────────

def _make_color_btn(color: QColor, parent=None) -> QPushButton:
    btn = QPushButton(parent)
    btn.setObjectName("color_swatch")
    btn.setFixedSize(24, 24)
    _set_color_btn(btn, color)
    return btn


def _set_color_btn(btn: QPushButton, color: QColor):
    r, g, b = color.red(), color.green(), color.blue()
    # Use typed selector so it overrides the global QPushButton min-height/padding rules
    btn.setStyleSheet(
        f"QPushButton#color_swatch {{ background:rgb({r},{g},{b}); }}"
    )




class _FontPreviewDelegate(QStyledItemDelegate):
    """(r69) Lista del combo de fuentes: cada opción escrita con su propia
    tipografía. Se pinta a mano porque, con hoja de estilos, Qt dibuja la
    lista con QComboMenuDelegate y la fuente de la regla QWidget global pisa
    la de Qt.FontRole."""

    FAMILY_ROLE = Qt.ItemDataRole.UserRole + 1

    def paint(self, painter, option, index):
        painter.save()
        sel = bool(option.state & (QStyle.StateFlag.State_Selected
                                   | QStyle.StateFlag.State_MouseOver))
        painter.fillRect(option.rect, QColor("#0078D4") if sel else QColor("#FFFFFF"))
        f = QFont(option.font)
        # «Documento» no es un tipo de letra: va con la fuente de la interfaz.
        f.setFamilies([index.data(self.FAMILY_ROLE)] if index.data(self.FAMILY_ROLE)
                      else ["Segoe UI Variable", "Segoe UI"])
        f.setPixelSize(14)
        painter.setFont(f)
        painter.setPen(QColor("#FFFFFF") if sel else QColor("#201F1E"))
        painter.drawText(option.rect.adjusted(8, 0, -4, 0),
                         Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                         index.data(Qt.ItemDataRole.DisplayRole) or "")
        painter.restore()

    def sizeHint(self, option, index):
        sh = super().sizeHint(option, index)
        return QSize(sh.width() + 24, max(26, sh.height()))


# ─────────────────────────────────────────────────────────────────────────────
# Main window
# ─────────────────────────────────────────────────────────────────────────────

class MainWindow(DocumentMixin, MenusMixin, QMainWindow):
    """Ventana principal. El ciclo de vida del documento (abrir, guardar,
    deshacer, búsqueda, firma) vive en `DocumentMixin` y los menús y
    herramientas de documento en `MenusMixin`; aquí quedan la construcción de
    barras, los paneles contextuales, el zoom y las operaciones de página."""

    def __init__(self):
        super().__init__()
        icons.load_fonts()          # (r36) iconos Fluent y Noto, incluidos en vendor/fonts
        self.setWindowTitle("AventyaPDF")
        self.resize(1360, 900)
        self.setAcceptDrops(True)

        self.doc = None
        self.current_page = 0
        self.pdf_path = ""
        self.zoom_mode = "100"         # "100" | "width" | "height"
        self.custom_zoom_pct = 100     # zoom efectivo cuando mode == "100"

        self._init_document_state()
        self._setup_ui()

    # ── UI construction ────────────────────────────────────────────────── #

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._build_menus()
        root.addWidget(self._build_topbar())

        self.sidebar = SidePanel(self)
        self._build_side_tool_panels()
        # (r26, ampliado en r46 al aviso y a la barra de búsqueda) Ninguna
        # barra secundaria, de búsqueda ni de notificación externa a la
        # columna del panel empuja el panel lateral hacia abajo: la búsqueda,
        # el aviso y la barra de Firma/Comprimir solo desplazan el visor. Ni
        # una sola de esas barras queda ya por encima del `QSplitter` que
        # reparte panel lateral y visor. (r50) Dentro del propio panel, las
        # opciones de la herramienta activa sí empujan `stack` hacia abajo
        # (vuelta al comportamiento de r26): así la herramienta y lo que ya se
        # veía en el panel están disponibles a la vez.
        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(0)
        right_lay.addWidget(self._build_find_bar())
        right_lay.addWidget(self._build_banner())
        right_lay.addWidget(self._build_options_row())
        right_lay.addWidget(self._build_viewer(), 1)
        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.setChildrenCollapsible(False)
        self._splitter.addWidget(self.sidebar)
        self._splitter.addWidget(right)
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 1)
        root.addWidget(self._splitter, 1)

        self._refresh_opt_row()
        self._update_actions()
        self._update_title()

        self.statusBar().showMessage(
            "Listo  —  Abre un PDF (Ctrl+O) o arrástralo a la ventana  ·  F1: atajos de teclado")

    @staticmethod
    def _glyph_btn(glyph_key: str, tip: str, checkable: bool = False,
                   obj_name: str = "tbr_btn") -> QPushButton:
        # Font is applied via stylesheet (#tbr_btn / #nav_btn), not inline
        btn = QPushButton(_G.get(glyph_key, "?"))
        btn.setObjectName(obj_name)
        btn.setToolTip(tip)
        btn.setCheckable(checkable)
        return btn

    def _build_topbar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("topbar")
        bar.setFixedHeight(50)
        self._topbar = bar

        lay = QHBoxLayout(bar)
        lay.setContentsMargins(10, 7, 10, 7)
        lay.setSpacing(2)

        # ── File operations ──────────────────────────────────────────────
        b_side = self._glyph_btn("sidebar", "Panel lateral  (F4)")
        b_side.clicked.connect(lambda _c=False: self.sidebar_toggle())
        lay.addWidget(b_side)
        lay.addWidget(self._vline())

        for key, tip, handler in [
            ("open",  "Abrir PDF  (Ctrl+O)",   self.open_pdf),
            ("save",  "Guardar  (Ctrl+S)", self.save_pdf),
            ("print", "Imprimir  (Ctrl+P)", self.print_pdf),
        ]:
            b = self._glyph_btn(key, tip)
            b.clicked.connect(lambda _c=False, h=handler: h())
            lay.addWidget(b)

        self._btn_compress = self._glyph_btn(
            "compress", "Comprimir PDF  ·  muestra barra de nivel", checkable=True)
        self._btn_compress.clicked.connect(self._toggle_compress_panel)
        lay.addWidget(self._btn_compress)

        self._btn_undo = self._glyph_btn("undo", "Deshacer  (Ctrl+Z)")
        self._btn_undo.clicked.connect(lambda _c=False: self.undo())
        lay.addWidget(self._btn_undo)
        self._btn_redo = self._glyph_btn("redo", "Rehacer  (Ctrl+Y)")
        self._btn_redo.clicked.connect(lambda _c=False: self.redo())
        lay.addWidget(self._btn_redo)

        lay.addWidget(self._vline())

        # ── Page navigation ──────────────────────────────────────────────
        btn_prev = self._glyph_btn("prev", "Página anterior  (RePág)", obj_name="nav_btn")
        btn_prev.clicked.connect(self.prev_page)

        self._page_edit = QLineEdit("")
        self._page_edit.setFixedWidth(44)
        # (r53, petición de Ricardo) Máximo 4 dígitos (hasta 9999 páginas) y
        # texto alineado a la derecha, como cualquier campo numérico.
        self._page_edit.setMaxLength(4)
        self._page_edit.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._page_edit.setToolTip("Escribe un número de página y pulsa Intro  (Ctrl+G)")
        self._page_edit.returnPressed.connect(self._on_page_edit)

        self._lbl_page = QLabel("/ —")
        self._lbl_page.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self._lbl_page.setMinimumWidth(40)
        self._lbl_page.setStyleSheet("font-size:13px; color:#605E5C; background:transparent;")

        btn_next = self._glyph_btn("next", "Página siguiente  (AvPág)", obj_name="nav_btn")
        btn_next.clicked.connect(self.next_page)

        lay.addWidget(btn_prev)
        lay.addWidget(self._page_edit)
        lay.addWidget(self._lbl_page)
        lay.addWidget(btn_next)

        lay.addWidget(self._vline())

        # ── Zoom: 100% con barra + Type (ancho/alto toggle) ─────────────
        self._zoom_btns: dict[str, QPushButton] = {}

        b100 = self._glyph_btn("zoom100", "Zoom", checkable=True)
        b100.clicked.connect(self._on_zoom100_btn)
        self._zoom_btns["100"] = b100
        lay.addWidget(b100)

        # (r51, petición de Ricardo) No es «checkable»: el icono ya dice qué
        # va a hacer el próximo clic (r48), así que el botón nunca debe quedar
        # marcado como seleccionado tras pulsarlo.
        btype = self._glyph_btn("type", "Ajustar al ancho / al alto  (alterna al pulsar)")
        btype.clicked.connect(self._toggle_type_zoom)
        self._zoom_btns["type"] = btype
        self._update_zoom_type_icon()      # (r48) icono según la acción libre, no fijo
        lay.addWidget(btype)

        lay.addWidget(self._vline())

        # ── Annotation tools (exclusivos) ────────────────────────────────
        self._tool_btns: dict[str, QPushButton] = {}
        for key, mode, tip in [
            ("text",      "TEXT",      "Añadir texto  (T)"),
            ("note",      "NOTE",      "Nota adhesiva  (N)"),
            ("markup",    "MARKUP",    "Resaltar, subrayar o tachar — sobre el texto o a mano alzada  (H)"),
            ("rect",      "RECT",      "Remarcar con rectángulo  (R)"),
            ("emoji",     "EMOJI",     "Insertar emoji  (E)"),
            ("eraser",    "ERASE",     "Borrador — mantén pulsado y arrastra sobre anotaciones"),
            ("edit",      "EDIT",      "Editar el texto y las imágenes del PDF  (C)"),
        ]:
            b = self._glyph_btn(key, tip, checkable=True)
            b.clicked.connect(lambda _c, m=mode: self._toggle_tool(m))
            self._tool_btns[mode] = b
            lay.addWidget(b)

        lay.addWidget(self._vline())

        # ── Firma + Operaciones de página ────────────────────────────────
        b_sign = self._glyph_btn("sign", "Firma digital PAdES", checkable=True)
        b_sign.clicked.connect(lambda _c: self._toggle_tool("SIGN"))
        self._tool_btns["SIGN"] = b_sign
        lay.addWidget(b_sign)

        # (r27) Sin ventana: miniaturas y acciones en el panel lateral.
        self._btn_pages = self._glyph_btn(
            "pages", "Operaciones de página: miniaturas y acciones en el panel lateral",
            checkable=True)
        self._btn_pages.clicked.connect(lambda _c=False: self._set_pages_mode(not self._pages_mode))
        lay.addWidget(self._btn_pages)

        lay.addStretch()

        b_find = self._glyph_btn("search", "Buscar  (Ctrl+F)  ·  pulsar de nuevo la cierra")
        b_find.clicked.connect(lambda _c=False: self._toggle_find_bar())
        lay.addWidget(b_find)
        return bar

    def _toggle_find_bar(self) -> None:
        """(r50, petición de Ricardo) El botón de la barra principal alterna:
        la segunda pulsación oculta la barra de búsqueda. Ctrl+F y el menú
        Edición › Buscar siguen abriendo/enfocando sin cerrarla."""
        if self._find_bar.isVisible():
            self.hide_find()
        else:
            self.show_find()

    def _build_options_row(self) -> QFrame:
        """Barra secundaria horizontal, solo encima del visor (r26): opciones de
        Firma y Comprimir. Las del resto de herramientas van en el
        panel lateral (`_build_side_tool_panels`)."""
        row = QFrame()
        row.setObjectName("options_row")
        row.setFixedHeight(50)
        row.setVisible(False)
        self._opt_row = row

        lay = QHBoxLayout(row)
        lay.setContentsMargins(12, 6, 12, 6)
        lay.setSpacing(6)

        _TP = "* { background: transparent; }" + TOOLTIP_QSS   # shorthand para todos los panels

        # ── Panel: Firma ─────────────────────────────────────────────────
        self._sign_panel = QFrame()
        self._sign_panel.setStyleSheet(_TP)
        self._sign_panel.setVisible(False)
        sl = QHBoxLayout(self._sign_panel)
        sl.setContentsMargins(0, 0, 0, 0); sl.setSpacing(4)
        sl.addWidget(self._opt_glyph("opt_cert"))
        self._sign_cert_lbl = QLabel("Sin certificado")
        self._sign_cert_lbl.setObjectName("opt_lbl")
        self._sign_cert_lbl.setFixedHeight(28)
        sl.addWidget(self._sign_cert_lbl)
        sl.addWidget(self._opt_sep())
        btn_change_cert = self._opt_icon_btn("cert_change", "Cambiar de certificado digital…")
        btn_change_cert.clicked.connect(self._change_cert)
        sl.addWidget(btn_change_cert)
        btn_forget_cert = self._opt_icon_btn("delete", "Olvidar el certificado recordado")
        btn_forget_cert.clicked.connect(self._forget_cert)
        sl.addWidget(btn_forget_cert)
        # (r68) Firma manuscrita: dibujada con el ratón o desde una imagen.
        sl.addWidget(self._opt_sep())
        self._btn_handsign = self._opt_icon_btn(
            "handsign", "Firma manuscrita: dibújala con el ratón (plumilla de "
            "estilográfica) o carga la imagen de tu firma, y colócala en la página")
        self._btn_handsign.setCheckable(True)
        self._btn_handsign.setStyleSheet(
            "QPushButton#opt_btn:checked { background:#CCE4F7; border-color:#0078D4; }")
        self._btn_handsign.clicked.connect(lambda _c=False: self._on_hand_signature())
        sl.addWidget(self._btn_handsign)

        # ── Panel: Compresión ────────────────────────────────────────────
        self._compress_panel = QFrame()
        self._compress_panel.setStyleSheet(_TP)
        self._compress_panel.setVisible(False)
        cl = QHBoxLayout(self._compress_panel)
        cl.setContentsMargins(0, 0, 0, 0); cl.setSpacing(4)
        cl.addWidget(self._opt_glyph("opt_compress"))
        cl.addWidget(self._opt_lbl("Nivel:"))
        # Niveles de iLovePDF con los criterios de imagen de Acrobat (pdf_compression).
        self._compress_level_cb = QComboBox()
        for i, lvl in enumerate(pdf_compression.LEVELS):
            self._compress_level_cb.addItem(lvl.label, lvl.key)
            self._compress_level_cb.setItemData(i, lvl.description, Qt.ItemDataRole.ToolTipRole)
        self._compress_level_cb.setCurrentIndex(
            self._compress_level_cb.findData(pdf_compression.DEFAULT_LEVEL))
        self._compress_level_cb.currentIndexChanged.connect(self._on_compress_level)
        cl.addWidget(self._compress_level_cb)
        self._lbl_compress_lvl = QLabel()
        self._lbl_compress_lvl.setObjectName("opt_lbl")
        cl.addWidget(self._lbl_compress_lvl)
        self._on_compress_level()
        cl.addWidget(self._opt_sep())
        btn_do_compress = self._opt_icon_btn("save_copy", "Comprimir y guardar una copia del PDF…")
        btn_do_compress.clicked.connect(self.compress_pdf)
        cl.addWidget(btn_do_compress)

        lay.addStretch()
        lay.addWidget(self._sign_panel)
        lay.addWidget(self._compress_panel)
        lay.addStretch()
        return row

    def _side_form(self, title: str) -> tuple[QFrame, QGridLayout]:
        """Panel de opciones para la columna lateral: título y filas de
        «etiqueta explícita · control», cada una en una sola línea."""
        panel = QFrame()
        panel.setObjectName("side_tool_panel")
        panel.setVisible(False)
        grid = QGridLayout(panel)
        grid.setContentsMargins(10, 6, 10, 10)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        grid.setColumnStretch(1, 1)
        head = QLabel(title)
        head.setObjectName("side_title")
        grid.addWidget(head, 0, 0, 1, 2)
        self.sidebar.add_tool_panel(panel)
        return panel, grid

    @staticmethod
    def _side_row(grid: QGridLayout, label: str, *widgets: QWidget) -> None:
        r = grid.rowCount()
        lbl = QLabel(label)
        lbl.setObjectName("side_lbl")
        grid.addWidget(lbl, r, 0)
        box = QHBoxLayout()
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(4)
        for w in widgets:
            box.addWidget(w)
        box.addStretch()
        grid.addLayout(box, r, 1)

    @staticmethod
    def _side_hint(grid: QGridLayout, text: str) -> QLabel:
        """Texto de ayuda a lo ancho del panel. Si un texto variable no cabe se
        corta (no ensancha el panel) y se lee entero en su tooltip."""
        lbl = QLabel(text)
        lbl.setObjectName("side_hint")
        lbl.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        grid.addWidget(lbl, grid.rowCount(), 0, 1, 2)
        return lbl

    def _build_side_tool_panels(self) -> None:
        """(r26; superposición de r46 revertida en r50) Opciones de las
        herramientas de zoom y anotación, arriba del panel lateral: ocupan su
        ancho y lo empujan hacia abajo, para que la herramienta y lo que ya
        se veía en el panel estén disponibles a la vez."""
        # ── Panel: Zoom (modo 100%) ──────────────────────────────────────
        self._zoom_panel, g = self._side_form("Zoom")
        self._lbl_zoom_pct = QLabel("100 %")
        self._lbl_zoom_pct.setObjectName("side_lbl")
        self._side_row(g, "Ampliación de la página", self._lbl_zoom_pct)
        self._zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self._zoom_slider.setRange(10, 800)
        self._zoom_slider.setValue(100)
        self._zoom_slider.valueChanged.connect(self._on_zoom_slider)
        g.addWidget(self._zoom_slider, g.rowCount(), 0, 1, 2)

        # ── Panel: Operaciones de página (r27, sustituye al organizador) ─
        self._pages_panel, g = self._side_form("Operaciones de página")
        self._lbl_pages_sel = self._side_hint(g, "")
        self._pages_btns = []
        # (r31) Una sola fila de iconos; qué hace cada uno, en su tooltip.
        icons = QHBoxLayout()
        icons.setContentsMargins(0, 0, 0, 0)
        icons.setSpacing(0)
        for glyph, tip, op in [
            ("rotate_left", "Girar 90° a la izquierda las páginas seleccionadas", "left"),
            ("rotate_right", "Girar 90° a la derecha las páginas seleccionadas", "right"),
            ("duplicate", "Duplicar: poner una copia detrás de cada página seleccionada", "dup"),
            ("delete", "Eliminar las páginas seleccionadas  (Supr)", "del"),
            ("page_blank", "Insertar una página en blanco detrás de la selección", "blank"),
            ("insert_pdf", "Insertar las páginas de otro PDF detrás de la selección…", "pdf"),
            ("extract", "Extraer las páginas seleccionadas a un PDF nuevo…", "extract"),
        ]:
            b = self._opt_icon_btn(glyph, tip)
            b.setObjectName("side_icon_btn")
            b.clicked.connect(lambda _c=False, o=op: self._pages_op(o))
            icons.addWidget(b)
            self._pages_btns.append(b)
        icons.addStretch()
        g.addLayout(icons, g.rowCount(), 0, 1, 2)
        self._side_hint(g, "Arrastra una miniatura para moverla")
        self._side_hint(g, "Ctrl o Mayús para elegir varias")

        # ── Panel: Texto ─────────────────────────────────────────────────
        self._txt_panel, g = self._side_form("Añadir texto")
        self._txt_size_spin = self._make_spin(6, 96, 12, self._on_txt_size)
        self._side_row(g, "Tamaño de letra", self._txt_size_spin)
        self._txt_color_btn = _make_color_btn(QColor(0, 0, 0))
        self._txt_color_btn.clicked.connect(self._on_txt_color)
        self._side_row(g, "Color del texto", self._txt_color_btn)
        self._txt_bold_btn = self._make_style_btn("bold", "Negrita", self._on_txt_bold)
        self._txt_italic_btn = self._make_style_btn("italic", "Cursiva", self._on_txt_italic)
        self._side_row(g, "Negrita y cursiva", self._txt_bold_btn, self._txt_italic_btn)
        # Alineación cíclica (izquierda → centro → derecha). (r69) Sin
        # justificado: MuPDF no lo sabe pintar en el texto enriquecido.
        self._txt_align_btn = self._opt_icon_btn(
            "align_left", "Alineación: izquierda → centro → derecha")
        self._txt_align_btn.clicked.connect(self._on_txt_align_cycle)
        self._side_row(g, "Alineación", self._txt_align_btn)
        self._cb_font = QComboBox()
        self._cb_font.addItems(list(PDFUtils.FONT_LABELS))      # Documento + Noto (r36)
        # (r69) Cada tipo de letra se ve escrito con su propia fuente, en la
        # lista y en el propio combo (ver _show_font_in_combo).
        for i, label in enumerate(PDFUtils.FONT_LABELS):
            fam = self._font_label_family(label)
            if fam:
                self._cb_font.setItemData(i, fam, _FontPreviewDelegate.FAMILY_ROLE)
            else:
                self._cb_font.setItemData(
                    i, "La del propio documento (se imita con la Noto más parecida)",
                    Qt.ItemDataRole.ToolTipRole)
        self._cb_font.setItemDelegate(_FontPreviewDelegate(self._cb_font))
        self._cb_font.setCurrentText("Noto Sans")
        self._cb_font.setFixedSize(160, 28)          # (r69) cabe «Noto Sans Mono» en su letra
        self._cb_font.currentTextChanged.connect(self._show_font_in_combo)
        self._cb_font.currentTextChanged.connect(self._on_txt_font)
        self._show_font_in_combo(self._cb_font.currentText())
        self._side_row(g, "Tipo de letra", self._cb_font)
        self._side_hint(g, "Haz clic en la página y escribe")

        # ── Panel: Nota adhesiva ─────────────────────────────────────────
        self._note_panel, g = self._side_form("Nota adhesiva")
        self._note_color_btn = _make_color_btn(QColor(255, 209, 0))
        self._note_color_btn.clicked.connect(self._on_note_color)
        self._side_row(g, "Color de la nota", self._note_color_btn)
        self._side_hint(g, "Haz clic donde irá la nota")

        # ── Panel: Marcado de texto ──────────────────────────────────────
        self._markup_panel, g = self._side_form("Resaltar, subrayar o tachar")
        self._cb_markup = QComboBox()
        self._cb_markup.addItem("Resaltar", "highlight")
        self._cb_markup.addItem("Subrayar", "underline")
        self._cb_markup.addItem("Tachar", "strike")
        self._cb_markup.addItem("Ondulado", "squiggly")
        self._cb_markup.setFixedSize(104, 28)
        self._cb_markup.currentIndexChanged.connect(self._on_markup_kind)
        self._side_row(g, "Tipo de marca", self._cb_markup)
        self._markup_color_btn = _make_color_btn(QColor(255, 235, 0))
        self._markup_color_btn.clicked.connect(self._on_markup_color)
        self._side_row(g, "Color de la marca", self._markup_color_btn)
        # (r59) Fuera del texto se marca a mano alzada: grosor de ese trazo.
        self._markup_width_spin = self._make_spin(
            1, 60, int(FREEHAND_WIDTHS["highlight"]), self._on_markup_width)
        self._side_row(g, "Grosor del trazo", self._markup_width_spin)
        self._side_hint(g, "Fuera del texto: a mano alzada")

        # ── Panel: Rectángulo ────────────────────────────────────────────
        self._rect_panel, g = self._side_form("Remarcar con rectángulo")
        self._rect_width_spin = self._make_spin(1, 20, 2, self._on_rect_width)
        self._side_row(g, "Grosor del borde", self._rect_width_spin)
        self._rect_color_btn = _make_color_btn(QColor(0xD1, 0x34, 0x38))
        self._rect_color_btn.clicked.connect(self._on_rect_color)
        self._side_row(g, "Color del borde", self._rect_color_btn)
        self._side_hint(g, "Arrastra para dibujar el rectángulo")

        # ── Panel: Emoji ─────────────────────────────────────────────────
        self._emoji_panel, g = self._side_form("Insertar emoji")
        self._emoji_size_spin = self._make_spin(8, 96, 24, self._on_emoji_size)
        self._side_row(g, "Tamaño del emoji", self._emoji_size_spin)
        # (r40) Noto Emoji es monocroma: el emoji se escribe con el color y la
        # transparencia que se elijan aquí, como cualquier otro texto.
        self._emoji_color_btn = _make_color_btn(
            QColor(*[int(c * 255) for c in emoji_font.DEFAULT_COLOR]))
        self._emoji_color_btn.clicked.connect(self._on_emoji_color)
        self._side_row(g, "Color y opacidad", self._emoji_color_btn)
        # (r36) Todos los emojis del índice, con buscador y grupos.
        self._emoji_picker = EmojiPicker()
        self._emoji_picker.emojiChosen.connect(self._on_emoji_glyph)
        g.addWidget(self._emoji_picker, g.rowCount(), 0, 1, 2)
        self._side_hint(g, "Elige un emoji y haz clic donde irá")

        # ── Panel: Editar contenido ──────────────────────────────────────
        self._edit_panel, g = self._side_form("Editar texto e imágenes")
        self._edit_size_spin = self._make_spin(4, 96, 11, self._on_edit_size)
        self._side_row(g, "Tamaño de letra", self._edit_size_spin)
        self._edit_color_btn = _make_color_btn(QColor(0, 0, 0))
        self._edit_color_btn.clicked.connect(self._on_edit_color)
        self._side_row(g, "Color del texto", self._edit_color_btn)
        self._edit_bold_btn = self._make_style_btn("bold", "Negrita", self._on_edit_bold)
        self._edit_italic_btn = self._make_style_btn("italic", "Cursiva", self._on_edit_italic)
        self._side_row(g, "Negrita y cursiva", self._edit_bold_btn, self._edit_italic_btn)
        self._lbl_edit_hint = self._side_hint(g, "Haz clic en un párrafo o imagen")
        self._lbl_edit_mixed = self._side_hint(g, "Estilos mezclados: se unifican")
        self._lbl_edit_mixed.setStyleSheet("color:#C42B1C;")
        self._lbl_edit_mixed.setToolTip(
            "El párrafo mezcla estilos: se reescribirá entero con uno solo")
        self._lbl_edit_mixed.hide()
        self._lbl_edit_fit = self._side_hint(g, "")
        self._lbl_edit_fit.hide()
        # Ninguno de estos controles debe robarle el foco al editor en línea:
        # un FocusOut lo cierra y el cambio de estilo se perdería.
        for wdg in self._edit_panel.findChildren(QWidget):
            wdg.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def _build_viewer(self) -> QStackedWidget:
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(False)
        self._scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._scroll.viewport().setStyleSheet("* { background: #D0D4D8; }" + TOOLTIP_QSS)

        self.viewer = PDFViewerWidget()
        self.viewer.main_window = self
        self._scroll.setWidget(self.viewer)
        # Zona central del documento (una pila por si algún día hay más vistas).
        self._center = QStackedWidget()
        self._center.addWidget(self._scroll)
        return self._center

    # ── Static helpers ─────────────────────────────────────────────────── #

    @staticmethod
    def _vline() -> QFrame:
        f = QFrame()
        f.setObjectName("vline")
        f.setFrameShape(QFrame.Shape.VLine)
        f.setFixedWidth(1)
        f.setFixedHeight(32)
        return f

    @staticmethod
    def _opt_lbl(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("opt_lbl")
        return lbl

    @staticmethod
    def _make_spin(lo: int, hi: int, default: int, callback) -> QFrame:
        container = QFrame()
        container.setFixedHeight(24)
        lay = QHBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        sb = QSpinBox()
        sb.setRange(lo, hi)
        sb.setValue(default)
        sb.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        sb.setObjectName("opt_spin_field")
        sb.setFixedSize(36, 22)
        sb.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        sb.valueChanged.connect(callback)
        btn_m = QPushButton(_G["minus"])
        btn_m.setObjectName("opt_spin_btn")
        btn_m.setFixedSize(22, 22)
        btn_m.setFlat(False)
        btn_m.clicked.connect(sb.stepDown)
        btn_p = QPushButton(_G["plus"])
        btn_p.setObjectName("opt_spin_btn")
        btn_p.setFixedSize(22, 22)
        btn_p.setFlat(False)
        btn_p.clicked.connect(sb.stepUp)
        lay.addWidget(btn_m)
        lay.addWidget(sb)
        lay.addWidget(btn_p)
        return container

    @staticmethod
    def _opt_glyph(glyph_key: str) -> QLabel:
        lbl = QLabel(_G.get(glyph_key, ""))
        lbl.setObjectName("opt_glyph")
        lbl.setFixedSize(20, 28)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return lbl

    @staticmethod
    def _opt_sep() -> QFrame:
        f = QFrame()
        f.setFrameShape(QFrame.Shape.VLine)
        f.setFixedSize(1, 20)
        f.setStyleSheet("background:#D2D0CE;")
        return f

    @staticmethod
    def _opt_icon_btn(glyph_key: str, tip: str) -> QPushButton:
        btn = QPushButton(_G.get(glyph_key, "?"))
        btn.setObjectName("opt_btn")
        btn.setToolTip(tip)
        return btn

    @staticmethod
    def _make_style_btn(glyph_key: str, tip: str, callback) -> QPushButton:
        """Checkable toggle (Bold / Italic). (r58) Drawn with the Fluent UI
        System Icons glyph like every other option button, not with a
        Segoe UI letter."""
        btn = QPushButton(_G[glyph_key])
        btn.setObjectName("opt_btn")
        btn.setCheckable(True)
        btn.setToolTip(tip)
        btn.setFixedSize(28, 28)
        btn.setStyleSheet(
            "QPushButton#opt_btn:checked { background:#CCE4F7;"
            " border-color:#0078D4; }")
        btn.clicked.connect(callback)
        return btn

    # ── Paneles contextuales ───────────────────────────────────────────── #

    def _show_only_tool_panel(self, mode: str | None) -> None:
        """Muestra el panel contextual de la herramienta `mode` y oculta el
        resto de paneles de herramienta (None = ninguno)."""
        panels = {
            "TEXT": self._txt_panel, "NOTE": self._note_panel,
            "MARKUP": self._markup_panel,
            "RECT": self._rect_panel, "EMOJI": self._emoji_panel,
            "SIGN": self._sign_panel,
            "EDIT": self._edit_panel,
        }
        for m, panel in panels.items():
            panel.setVisible(m == mode)

    # ── Operaciones de página (panel lateral) ──────────────────────────── #

    _pages_mode = False
    _pages_closes_sidebar = False

    def _set_pages_mode(self, on: bool) -> None:
        """(r27) Botón «Operaciones de página»: las miniaturas del panel
        lateral pasan a organizarse (arrastrar reordena, Supr elimina) y encima
        aparecen las acciones. Sin ventana aparte. Se sale con el mismo botón,
        con Esc, eligiendo otra herramienta, zoom o compresión, o cambiando de
        panel lateral. Si el panel estaba cerrado, se vuelve a cerrar."""
        if on and self.doc is None:
            self._btn_pages.setChecked(False)
            return
        if on == self._pages_mode:
            self._btn_pages.setChecked(on)
            return
        if on:
            self._finish_action()
            self._zoom_btns["100"].setChecked(False)
            self._zoom_panel.setVisible(False)
            self._pages_closes_sidebar = self.sidebar.stack.isHidden()
            self._pages_mode = True
            self.sidebar.show_panel("thumbs")
        else:
            self._pages_mode = False       # antes de cerrar el panel (evita reentrar)
            if self._pages_closes_sidebar and not self.sidebar.stack.isHidden():
                self.sidebar.collapse()
            self._pages_closes_sidebar = False
        self._btn_pages.setChecked(on)
        self.sidebar.thumbs.set_organizing(on)
        self._pages_panel.setVisible(on)
        self._update_pages_panel()
        self._refresh_opt_row()

    def _on_sidebar_panel(self, key: str) -> None:
        """El panel lateral cambió (otro panel o cerrado): fuera del modo páginas."""
        if self._pages_mode and key != "thumbs":
            self._pages_closes_sidebar = False
            self._set_pages_mode(False)

    def _update_pages_panel(self) -> None:
        if not hasattr(self, "_lbl_pages_sel"):
            return
        n = len(self.doc) if self.doc is not None else 0
        sel = len(self.sidebar.thumbs._selected())
        if sel:
            self._lbl_pages_sel.setText(f"Seleccionadas: {sel} de {n}")
        else:
            self._lbl_pages_sel.setText(f"Sin selección: se usa la {self.current_page + 1} de {n}")
        for b in self._pages_btns:
            b.setEnabled(n > 0)

    def _pages_op(self, op: str) -> None:
        if self.doc is None:
            return
        th = self.sidebar.thumbs
        rows = th.selected_pages()
        if op == "left":
            th.select_after_rebuild(rows)
            self.rotate_pages(rows, -90)
        elif op == "right":
            th.select_after_rebuild(rows)
            self.rotate_pages(rows, 90)
        elif op == "dup":
            self.duplicate_pages(rows)
        elif op == "del":
            self.delete_pages(rows)
        elif op == "blank":
            th.select_after_rebuild([rows[-1] + 1])
            self.insert_blank_after(rows[-1])
        elif op == "pdf":
            self.insert_pdf_after(rows[-1])
        elif op == "extract":
            self.extract_pages(rows)

    def _finish_action(self) -> None:
        for b in self._tool_btns.values():
            b.setChecked(False)
        self._btn_compress.setChecked(False)
        self._compress_panel.setVisible(False)
        self._activate_tool("NONE")

    def _show_annot_opts(self, annot) -> None:
        """Show the options panel for the selected annotation type (mode stays NONE)."""
        atype = annot.type[1]
        subject = annot.info.get('subject', '')

        if atype == 'FreeText':
            mode = 'EMOJI' if subject == 'EmojiStamp' else 'TEXT'
        elif atype == 'Text':
            mode = 'NOTE'
        elif atype in ('Highlight', 'Underline', 'StrikeOut', 'Squiggly'):
            mode = 'MARKUP'
        elif atype == 'Stamp' and firma_manuscrita.is_hand_signature(subject):
            return  # (r68) firma manuscrita: se mueve y redimensiona, sin opciones
        elif atype == 'Stamp':
            mode = 'EMOJI'  # true-colour emoji image
        elif atype == 'Ink':
            mode = 'MARKUP'         # (r59) marca a mano alzada
        elif atype == 'Square':
            mode = 'RECT'
        else:
            return  # Widget (firma) u otro tipo — sin panel editable

        self._sync_panel_to_annot(annot, mode)
        self._set_pages_mode(False)

        # Remember whether the secondary bar is about to appear, so we can
        # compensate the resulting layout shift and keep the annotation under
        # the cursor (it grows the viewer downward by _opt_row.height()).
        opt_was_visible = self._opt_row.isVisible()

        for m, b in self._tool_btns.items():
            b.setChecked(m == mode)
        self._show_only_tool_panel(mode)
        self._compress_panel.setVisible(False)
        self._btn_compress.setChecked(False)
        self._refresh_opt_row()
        # If the secondary bar just appeared, the viewer is pushed down by its
        # height. Defer until Qt processes the layout, then scroll the content
        # by the same amount so the selected annotation keeps its screen
        # position (no visual displacement). Fall back to ensureVisible.
        if not opt_was_visible and self._opt_row.isVisible():
            shift = self._opt_row.height()
            QTimer.singleShot(0, lambda: self._compensate_opt_shift(shift))
        else:
            QTimer.singleShot(0, self._scroll_to_selection)

    def _hide_annot_opts(self) -> None:
        """Hide the annotation options panel when nothing is selected (mode stays NONE)."""
        if self.viewer.mode != 'NONE':
            return
        for b in self._tool_btns.values():
            b.setChecked(False)
        self._show_only_tool_panel(None)
        self._refresh_opt_row()

    def _toggle_compress_panel(self) -> None:
        showing = self._btn_compress.isChecked()
        if showing:
            self._set_pages_mode(False)
            for m, b in self._tool_btns.items():
                b.setChecked(False)
            self._zoom_btns["100"].setChecked(False)
            self._zoom_panel.setVisible(False)
            self._show_only_tool_panel(None)
            self.viewer.mode = "NONE"
            self.viewer._sel = None
            self.viewer.update()
        self._compress_panel.setVisible(showing)
        self._refresh_opt_row()

    def _on_compress_level(self, _index: int = 0) -> None:
        lvl = pdf_compression.LEVELS_BY_KEY[self._compress_level_cb.currentData()]
        self._lbl_compress_lvl.setText(lvl.description)

    # ── Tool selection ─────────────────────────────────────────────────── #

    def _toggle_tool(self, mode: str):
        if self.viewer.mode == mode:
            self._tool_btns[mode].setChecked(False)
            self._activate_tool("NONE")
        else:
            for m, b in self._tool_btns.items():
                b.setChecked(m == mode)
            self._activate_tool(mode)

    def _activate_tool(self, mode: str):
        if mode != "NONE" and self._pages_mode:
            self._set_pages_mode(False)
        self.viewer.mode = mode
        self.viewer.set_hand_signature(None)
        self._btn_handsign.setChecked(False)
        self.viewer._sel = None
        self.viewer._stroke_pts = []
        self.viewer.start_pos = None
        self.viewer.current_rect = None
        self.viewer.clear_text_selection()
        self.viewer.close_text_editor(commit=True)
        # Los recuadros de «Editar contenido» solo se calculan con la herramienta puesta.
        self.viewer.content.clear()
        if mode == "EDIT":
            self.viewer.content.refresh()
        self.viewer.update()

        self._show_only_tool_panel(mode)

        # When a tool is active, zoom buttons must appear deselected
        if mode != "NONE":
            self._zoom_btns["100"].setChecked(False)
            self._zoom_panel.setVisible(False)

        self._refresh_opt_row()
        if mode == "SIGN":
            self._refresh_cert_label()

        cursors = {
            "SIGN":      Qt.CursorShape.CrossCursor,
            "RECT":      Qt.CursorShape.CrossCursor,
            "MARKUP":    Qt.CursorShape.IBeamCursor,
            "TEXT":      Qt.CursorShape.IBeamCursor,
            "NOTE":      Qt.CursorShape.PointingHandCursor,
            "EMOJI":     Qt.CursorShape.PointingHandCursor,
            "ERASE":     Qt.CursorShape.PointingHandCursor,
            "EDIT":      Qt.CursorShape.ArrowCursor,
        }
        self.viewer.setCursor(cursors.get(mode, Qt.CursorShape.ArrowCursor))

        hints = {
            "TEXT":      ("Texto — haz clic (o arrastra un cuadro) y escribe sobre la "
                          "página  ·  Ctrl+Intro confirma  ·  Esc cancela"),
            "NOTE":      ("Nota — haz clic donde quieras dejar el comentario y escríbelo "
                          "sobre la página  ·  Ctrl+Intro confirma  ·  Esc cancela"),
            "MARKUP":    "Marcar — arrastra sobre el texto, o fuera de él a mano alzada"
                         "  ·  Esc para terminar",
            "RECT":      "Remarcar — dibuja un rectángulo",
            "EMOJI":     "Emoji — haz clic para insertar",
            "SIGN":      "Firma — dibuja el área donde irá la firma",
            "ERASE":     "Borrador — mantén pulsado y arrastra sobre anotaciones para borrarlas",
            "EDIT":       ("Editar contenido — clic en un párrafo para reescribirlo "
                           "(Ctrl+Intro confirma)  ·  estira una esquina para que el texto "
                           "se reajuste  ·  clic en una imagen para moverla, cambiarla o "
                           "borrarla  ·  Esc para terminar"),
            "NONE":      "Selección — clic en una anotación · arrastra sobre el texto para seleccionarlo · Supr borra",
        }
        self.statusBar().showMessage(hints.get(mode, ""))

    # ── Apply to selection ─────────────────────────────────────────────── #

    def _apply_to_selection(self, fn) -> None:
        """Call fn(annot) on the selected annotation and re-render. No-op when nothing selected."""
        if self.viewer.mode != "NONE" or not self.viewer._sel:
            return
        if self.viewer._sel.is_signature:
            return
        a = self.viewer._annot_by_idx(self.viewer._sel.idx)
        if a:
            if firma_manuscrita.is_hand_signature(a.info.get("subject", "")):
                return
            self.checkpoint("Cambiar estilo")
            fn(a)
            self.mark_modified()
            self.render_page(keep_selection=True)

    # ── Text styling (rich text: size/color/bold/italic/align/font) ──────── #

    # (r69) Sin justificado en la herramienta Texto (invariante 55).
    _ALIGN_GLYPHS = ["align_left", "align_center", "align_right"]

    @staticmethod
    def _font_label_family(label: str) -> str:
        """Familia de Qt de una etiqueta del combo de fuentes ("" = Documento)."""
        kind = PDFUtils.FONT_LABELS.get(label, "doc")
        return "" if kind == "doc" else icons.noto_family(kind)

    def _show_font_in_combo(self, label: str) -> None:
        """El combo cerrado también enseña el nombre con su tipografía. Va por
        hoja de estilos: la global (regla QWidget) manda sobre setFont()."""
        fam = self._font_label_family(label)
        self._cb_font.setStyleSheet(f"QComboBox {{ font-family:'{fam}'; }}" if fam else "")

    def _text_font_css(self) -> str:
        """Resolve the current font choice to a CSS family for the rich text."""
        choice = self.viewer.text_font
        if choice == "doc":
            if self.doc:
                return PDFUtils.detect_doc_font_css(self.doc[self.current_page])
            return "sans-serif"
        return PDFUtils.FONT_CSS.get(choice, "sans-serif")

    def _apply_text_change(self, **ov) -> None:
        """Update the tool defaults and, if a FreeText annotation is selected,
        rebuild its rich text with the changed attribute(s) preserved."""
        if "fontsize" in ov: self.viewer.text_font_size = ov["fontsize"]
        if "bold" in ov:     self.viewer.text_bold = ov["bold"]
        if "italic" in ov:   self.viewer.text_italic = ov["italic"]
        if "align" in ov:    self.viewer.text_align = ov["align"]
        if "color" in ov:    self.viewer.text_color = ov["color"]
        # Si se está escribiendo sobre la página, el cambio se ve al momento.
        self.viewer.restyle_text_editor()

        def _fn(a):
            if a.type[1] != "FreeText":
                return
            if a.info.get("subject", "").startswith("EmojiStamp"):
                return  # star emoji is not stylable text
            st = PDFUtils.decode_text_style(a.info.get("subject", ""))
            try:
                fs = int(float(a.info.get("title") or self.viewer.text_font_size))
            except (TypeError, ValueError):
                fs = self.viewer.text_font_size
            PDFUtils.rebuild_text_annotation(
                self.doc, a, a.info.get("content", ""),
                ov.get("fontsize", fs), ov.get("color", st["color"]),
                ov.get("bold", st["bold"]), ov.get("italic", st["italic"]),
                ov.get("align", st["align"]), ov.get("font_css", st["font_css"]))
        self._apply_to_selection(_fn)

    def _on_txt_size(self, v: int) -> None:
        self._apply_text_change(fontsize=v)

    def _on_txt_bold(self) -> None:
        self._apply_text_change(bold=self._txt_bold_btn.isChecked())

    def _on_txt_italic(self) -> None:
        self._apply_text_change(italic=self._txt_italic_btn.isChecked())

    def _on_txt_align_cycle(self) -> None:
        nxt = (min(self.viewer.text_align, 2) + 1) % 3
        self._set_align_icon(nxt)
        self._apply_text_change(align=nxt)

    def _set_align_icon(self, align: int) -> None:
        self._txt_align_btn.setText(_G.get(self._ALIGN_GLYPHS[align if 0 <= align <= 2 else 0], ""))

    def _on_txt_font(self, label: str) -> None:
        self.viewer.text_font = PDFUtils.FONT_LABELS.get(label, "sans")
        self._apply_text_change(font_css=self._text_font_css())

    def _edit_text_annot(self, a, text: str) -> None:
        """Re-apply edited text content keeping the annotation's current style."""
        if a.type[1] == "Text":          # nota adhesiva: texto plano en /Contents
            a.set_info(content=text)
            a.update()
            return
        if a.info.get("subject", "").startswith("EmojiStamp"):
            a.set_info(content=text)
            a.update()
            return
        st = PDFUtils.decode_text_style(a.info.get("subject", ""))
        try:
            fs = int(float(a.info.get("title") or self.viewer.text_font_size))
        except (TypeError, ValueError):
            fs = self.viewer.text_font_size
        PDFUtils.rebuild_text_annotation(
            self.doc, a, text, fs, st["color"], st["bold"],
            st["italic"], st["align"], st["font_css"])

    def _on_markup_width(self, v: int) -> None:
        """(r59) Grosor del trazo a mano alzada (pt) del tipo de marca actual;
        si hay una marca a mano alzada seleccionada, se le aplica."""
        self.viewer.markup_widths[self.viewer.markup_kind] = float(v)
        def _apply(a):
            if a.type[1] == "Ink":
                a.set_border(width=float(v))
                a.update()
        self._apply_to_selection(_apply)

    def _on_rect_width(self, v: int) -> None:
        self.viewer.rect_line_width = v
        cr = self.viewer.rect_corner_radius
        def _apply(a):
            a.set_border(width=v)
            a.update()
            PDFUtils.apply_rounded_corners(a, cr)
        self._apply_to_selection(_apply)

    # ── Emoji (Fluent Emoji, ver emoji_font) ────────────────────────────── #

    def _insert_emoji(self, pt, emoji: str, fontsize: int, color=None,
                      opacity: float | None = None) -> None:
        try:
            emoji_font.add_emoji_annot(
                self.doc, self.current_page, pt, emoji, fontsize,
                self.viewer.emoji_color if color is None else color,
                self.viewer.emoji_opacity if opacity is None else opacity)
        except emoji_font.EmojiFontError as e:
            QMessageBox.warning(self, "Emoji", str(e))

    def _recreate_emoji_selection(self) -> None:
        """Cambiar el glifo o el tamaño de un emoji seleccionado lo recrea en su
        sitio (y convierte los emojis antiguos, imagen o FreeText, al actual)."""
        sel = self.viewer._sel
        if self.viewer.mode != "NONE" or not sel:
            return
        a = self.viewer._annot_by_idx(sel.idx)
        if not a or not emoji_font.is_emoji(a.info.get("subject", "")):
            return
        r = fitz.Rect(a.rect)
        self.checkpoint("Cambiar emoji")
        self.viewer.pdf_page.delete_annot(a)
        self._insert_emoji(fitz.Point(r.x0, r.y0),
                           self.viewer.selected_emoji, self.viewer.emoji_font_size)
        self.mark_modified()
        # Insertar un emoji de la paleta recarga las páginas: viewer.pdf_page ya
        # no es válida hasta el siguiente render_page (invariante 15).
        # La página en una variable: una Annot solo guarda una referencia débil a ella.
        page = self.doc[self.current_page]
        annots = list(page.annots())
        if annots:
            na = annots[-1]
            nr = fitz.Rect(na.rect)
            self.viewer._sel = AnnotSelection(
                len(annots) - 1, nr, fitz.Rect(nr), na.type[1])
        self.render_page(keep_selection=True)

    def _on_emoji_size(self, v: int) -> None:
        self.viewer.emoji_font_size = v
        self._recreate_emoji_selection()

    def _on_emoji_glyph(self, text: str) -> None:
        self.viewer.selected_emoji = text
        self._recreate_emoji_selection()

    def _on_emoji_color(self) -> None:
        elegido = color_picker.choose(self, self.viewer.emoji_color,
                                      self.viewer.emoji_opacity, "Color del emoji")
        if elegido:
            color, opacidad = elegido
            self.viewer.emoji_color = color
            self.viewer.emoji_opacity = opacidad
            _set_color_btn(self._emoji_color_btn, QColor(*[int(x * 255) for x in color]))
            self._emoji_picker.set_color(color)
            self._recreate_emoji_selection()

    # ── Herramienta «Editar contenido» ─────────────────────────────────── #

    def _show_edit_opts(self, block) -> None:
        """Pone en la barra secundaria el estilo del párrafo que se está
        editando. Lo llama edit_ui al abrir el editor."""
        sb = self._edit_size_spin.findChild(QSpinBox)
        if sb:
            sb.blockSignals(True)
            sb.setValue(max(sb.minimum(), min(sb.maximum(), int(round(block.size)))))
            sb.blockSignals(False)
        _set_color_btn(self._edit_color_btn, QColor(*[int(c * 255) for c in block.color]))
        for btn, val in ((self._edit_bold_btn, block.bold),
                         (self._edit_italic_btn, block.italic)):
            btn.blockSignals(True)
            btn.setChecked(val)
            btn.blockSignals(False)
        familia = pdf_edit.family_for(block.font, block.flags, block.bold, block.italic)
        self._lbl_edit_hint.setText(f"Letra: {familia} {block.size:g} pt")
        self._lbl_edit_hint.setToolTip(
            f"Fuente del documento: {block.font}\nSe reescribe con {familia}")
        self._lbl_edit_mixed.setVisible(block.mixed)

    def _set_edit_fit(self, lineas: int, alto: float, caja: float) -> None:
        """Indicador en vivo: cuántas líneas ocupa el texto y si cabe en el
        cuadro. Lo llama edit_ui al escribir y al estirar una esquina."""
        cabe = alto <= caja + 0.5
        plural = "línea" if lineas == 1 else "líneas"
        self._lbl_edit_fit.setText(
            f"Ocupa {lineas} {plural} y cabe" if cabe else "NO cabe: estira una esquina")
        self._lbl_edit_fit.setToolTip(
            f"Ocupa {lineas} {plural}: {alto:.0f} de {caja:.0f} pt de alto")
        self._lbl_edit_fit.setStyleSheet("" if cabe else "color:#C42B1C; font-weight:600;")
        self._lbl_edit_fit.show()

    def _on_edit_size(self, v: int) -> None:
        self.viewer.content.apply_style(size=float(v))

    def _on_edit_color(self) -> None:
        # El diálogo es modal y cierra el editor en línea: se guarda antes qué
        # línea se estaba editando y con qué texto.
        cont = self.viewer.content
        block = cont._editing
        texto = cont.editor.toPlainText() if cont.editor is not None else None
        actual = block.color if block else (0, 0, 0)
        elegido = color_picker.choose(self, actual, title="Color del texto")
        if elegido:
            color, _ = elegido
            _set_color_btn(self._edit_color_btn, QColor(*[int(x * 255) for x in color]))
            cont.apply_style(block=block, text=texto, color=color)

    def _on_edit_bold(self, checked: bool) -> None:
        self.viewer.content.apply_style(bold=checked)

    def _on_edit_italic(self, checked: bool) -> None:
        self.viewer.content.apply_style(italic=checked)

    def _sync_panel_to_annot(self, annot, mode: str) -> None:
        """Read annotation properties and update the options panel controls (no signals)."""
        def _set_spin(container, v):
            sb = container.findChild(QSpinBox)
            if sb:
                sb.blockSignals(True)
                sb.setValue(max(sb.minimum(), min(sb.maximum(), int(v))))
                sb.blockSignals(False)

        try:
            colors = annot.colors
            border = annot.border
            info   = annot.info

            if mode == 'TEXT':
                stored = info.get('title', '')
                if stored:
                    _set_spin(self._txt_size_spin, float(stored))
                    self.viewer.text_font_size = int(float(stored))
                st = PDFUtils.decode_text_style(info.get('subject', ''))
                self.viewer.text_bold = st['bold']
                self.viewer.text_italic = st['italic']
                # (r69) Un texto antiguo justificado sigue a la izquierda.
                self.viewer.text_align = st['align'] if st['align'] in (0, 1, 2) else 0
                self.viewer.text_color = st['color']
                self._txt_bold_btn.blockSignals(True)
                self._txt_bold_btn.setChecked(st['bold'])
                self._txt_bold_btn.blockSignals(False)
                self._txt_italic_btn.blockSignals(True)
                self._txt_italic_btn.setChecked(st['italic'])
                self._txt_italic_btn.blockSignals(False)
                self._set_align_icon(self.viewer.text_align)
                _set_color_btn(self._txt_color_btn, QColor(
                    int(st['color'][0]*255), int(st['color'][1]*255),
                    int(st['color'][2]*255)))
                css_to_label = PDFUtils.CSS_LABELS
                self._cb_font.blockSignals(True)
                self._cb_font.setCurrentText(
                    css_to_label.get(st['font_css'], "Noto Sans"))
                self._cb_font.blockSignals(False)

            elif mode == 'RECT':
                pdf_w = border.get('width') or 0
                if pdf_w:
                    _set_spin(self._rect_width_spin, max(1, round(pdf_w)))
                    self.viewer.rect_line_width = max(1, round(pdf_w))
                stroke = colors.get('stroke')
                if stroke is not None:
                    self.viewer.rect_color = tuple(stroke)
                    _set_color_btn(self._rect_color_btn,
                        QColor(int(stroke[0]*255), int(stroke[1]*255), int(stroke[2]*255)))

            elif mode in ('NOTE', 'MARKUP'):
                stroke = colors.get('stroke')
                if stroke is not None:
                    qc = QColor(int(stroke[0]*255), int(stroke[1]*255), int(stroke[2]*255))
                    if mode == 'NOTE':
                        self.viewer.note_color = tuple(stroke)
                        _set_color_btn(self._note_color_btn, qc)
                    else:
                        self.viewer.markup_color = tuple(stroke)
                        _set_color_btn(self._markup_color_btn, qc)
                if mode == 'MARKUP' and annot.type[1] == 'Ink':
                    # (r59) A mano alzada: el tipo va en /Subj; las Ink sin él
                    # (antiguo «Marcador a mano alzada») son resaltados.
                    subj = info.get('subject', '')
                    kind = (subj[len(doc_tools.FREEHAND_PREFIX):]
                            if subj.startswith(doc_tools.FREEHAND_PREFIX) else 'highlight')
                    if kind not in doc_tools.MARKUP_COLORS:
                        kind = 'highlight'
                    pdf_w = border.get('width') or 0
                    if pdf_w:
                        self.viewer.markup_widths[kind] = float(pdf_w)
                elif mode == 'MARKUP':
                    kind = {'Highlight': 'highlight', 'Underline': 'underline',
                            'StrikeOut': 'strike', 'Squiggly': 'squiggly'}.get(annot.type[1])
                if mode == 'MARKUP':
                    idx = self._cb_markup.findData(kind)
                    if idx >= 0:
                        self._cb_markup.blockSignals(True)
                        self._cb_markup.setCurrentIndex(idx)
                        self._cb_markup.blockSignals(False)
                        self.viewer.markup_kind = kind
                        _set_spin(self._markup_width_spin, self.viewer.markup_widths[kind])

            elif mode == 'EMOJI':
                stored = info.get('title', '')
                if stored:
                    _set_spin(self._emoji_size_spin, float(stored))
                    self.viewer.emoji_font_size = int(float(stored))
                content = info.get('content', '')
                if content:
                    self.viewer.selected_emoji = content
                    self._emoji_picker.set_current(content)
                # (r40) color y transparencia guardados en la propia anotación
                color, opacidad = emoji_font.parse_style(info.get('subject', ''))
                self.viewer.emoji_color = color
                self.viewer.emoji_opacity = opacidad
                _set_color_btn(self._emoji_color_btn,
                               QColor(*[int(c * 255) for c in color]))
                self._emoji_picker.set_color(color)
        except Exception:
            pass

    def _compensate_opt_shift(self, shift: int) -> None:
        """Scroll the viewer down by `shift` px to cancel the downward layout
        displacement caused by the secondary options bar appearing, so the
        selected annotation stays exactly where the user clicked it."""
        bar = self._scroll.verticalScrollBar()
        bar.setValue(bar.value() + shift)

    def _scroll_to_selection(self) -> None:
        """After layout settles, scroll so the selected annotation stays visible."""
        if not self.viewer._sel:
            return
        sr = self.viewer._to_screen_rect(self.viewer._sel.rect)
        self._scroll.ensureVisible(
            sr.center().x(), sr.center().y(),
            sr.width() // 2 + 30, sr.height() // 2 + 30)

    # ── Options callbacks ──────────────────────────────────────────────── #

    def _on_txt_color(self):
        elegido = color_picker.choose(self, self.viewer.text_color, title="Color del texto")
        if elegido:
            color, _ = elegido
            _set_color_btn(self._txt_color_btn, QColor(*[int(x * 255) for x in color]))
            self._apply_text_change(color=color)

    def _on_rect_color(self):
        elegido = color_picker.choose(self, self.viewer.rect_color, title="Color del rectángulo")
        if elegido:
            color, _ = elegido
            self.viewer.rect_color = color
            _set_color_btn(self._rect_color_btn, QColor(*[int(x * 255) for x in color]))
            def _rect_apply(a):
                a.set_colors(stroke=color)
                a.update()
                PDFUtils.apply_rounded_corners(a, self.viewer.rect_corner_radius)
            self._apply_to_selection(_rect_apply)

    def _on_note_color(self):
        elegido = color_picker.choose(self, self.viewer.note_color, title="Color de la nota")
        if elegido:
            color, _ = elegido
            self.viewer.note_color = color
            _set_color_btn(self._note_color_btn, QColor(*[int(x * 255) for x in color]))
            def _note_apply(a):
                if a.type[1] == "Text":
                    a.set_colors(stroke=color)
                    a.update()
            self._apply_to_selection(_note_apply)

    def _on_markup_kind(self, _index: int):
        kind = self._cb_markup.currentData()
        self.viewer.markup_kind = kind
        self.viewer.markup_color = doc_tools.MARKUP_COLORS.get(kind, self.viewer.markup_color)
        r, g, b = self.viewer.markup_color
        _set_color_btn(self._markup_color_btn, QColor(int(r*255), int(g*255), int(b*255)))
        spin = self._markup_width_spin.findChild(QSpinBox)
        spin.blockSignals(True)
        spin.setValue(int(round(self.viewer.markup_widths.get(kind, 2.0))))
        spin.blockSignals(False)

    def _on_markup_color(self):
        elegido = color_picker.choose(self, self.viewer.markup_color,
                                      self.viewer.markup_opacity, "Color del marcado")
        if elegido:
            color, opacidad = elegido
            self.viewer.markup_color = color
            self.viewer.markup_opacity = opacidad
            _set_color_btn(self._markup_color_btn, QColor(*[int(x * 255) for x in color]))
            def _markup_apply(a):
                if a.type[1] in ("Highlight", "Underline", "StrikeOut", "Squiggly", "Ink"):
                    a.set_colors(stroke=color)
                    a.set_opacity(opacidad)
                    a.update()
            self._apply_to_selection(_markup_apply)

    # ── File operations ────────────────────────────────────────────────── #

    def print_pdf(self):
        if not self._require_open():
            return
        try:
            from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
        except ImportError:
            QMessageBox.warning(self, "Sin soporte de impresión",
                                "El módulo QtPrintSupport no está disponible.")
            return

        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dlg = QPrintDialog(printer, self)
        if dlg.exec() != QPrintDialog.DialogCode.Accepted:
            return

        painter = QPainter()
        if not painter.begin(printer):
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            first = max(printer.fromPage() - 1, 0)
            last = (printer.toPage() - 1) if printer.toPage() > 0 else len(self.doc) - 1
            last = min(last, len(self.doc) - 1)
            pr = printer.pageRect(QPrinter.Unit.DevicePixel)
            # A la resolución nativa (600–1200 ppp) un A4 ocupa cientos de MB.
            dpi = min(printer.resolution(), 300)

            for i, pn in enumerate(range(first, last + 1)):
                if i > 0:
                    printer.newPage()
                pix = self.doc[pn].get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72))
                img = QImage(pix.samples, pix.width, pix.height,
                             pix.stride, QImage.Format.Format_RGB888)
                # El origen del pintor es el área imprimible; se centra la
                # página conservando su proporción.
                k = min(pr.width() / pix.width, pr.height() / pix.height)
                w, h = pix.width * k, pix.height * k
                painter.drawImage(QRectF((pr.width() - w) / 2, (pr.height() - h) / 2, w, h), img)
                QApplication.processEvents()
        finally:
            painter.end()
            QApplication.restoreOverrideCursor()
        self.statusBar().showMessage("Impresión enviada")

    # ── Zoom ───────────────────────────────────────────────────────────── #

    def _compute_scale(self) -> float:
        if not self.doc:
            return 1.5
        page = self.doc[self.current_page]
        pw, ph = page.rect.width, page.rect.height
        if self.zoom_mode == "100":
            return max(0.01, self.custom_zoom_pct / 100.0)
        vp = self._scroll.viewport()
        if self.zoom_mode == "width":
            return max(0.1, (vp.width() - 4) / pw)
        if self.zoom_mode == "height":
            # «Ajustar a la página»: cabe entera, a lo alto y a lo ancho.
            return max(0.1, min((vp.height() - 4) / ph, (vp.width() - 4) / pw))
        return 1.5

    def _toggle_type_zoom(self) -> None:
        if self.zoom_mode == "width":
            self._zoom_mode_changed("height")
        else:
            self._zoom_mode_changed("width")

    def _update_zoom_type_icon(self) -> None:
        """(r48) El icono del botón «ancho/alto» no es fijo: muestra la acción
        que el clic va a ejecutar (la que está libre), no la que ya está
        activa — igual que decide `_toggle_type_zoom`. Con zoom 100 % no hay
        ninguna de las dos activa todavía y el próximo clic ajusta al ancho."""
        self._zoom_btns["type"].setText(
            _G["type_height"] if self.zoom_mode == "width" else _G["type"])

    def _on_zoom100_btn(self, checked: bool) -> None:
        if checked:
            self._zoom_mode_changed("100")
        else:
            self._zoom_panel.setVisible(False)
            self._refresh_opt_row()

    def _zoom_mode_changed(self, mode: str) -> None:
        if mode == "100":
            self._set_pages_mode(False)
        if self.viewer.mode != "NONE":
            for b in self._tool_btns.values():
                b.setChecked(False)
            self.viewer.mode = "NONE"
            self.viewer._sel = None
            self.viewer._stroke_pts = []
            self.viewer.clear_text_selection()
            self._show_only_tool_panel(None)
        self._btn_compress.setChecked(False)
        self._compress_panel.setVisible(False)

        self.zoom_mode = mode
        self._zoom_btns["100"].setChecked(mode == "100")
        self._update_zoom_type_icon()
        if mode == "100":
            self.custom_zoom_pct = 100
            self._update_zoom_slider_range()
        self._zoom_panel.setVisible(mode == "100")
        self._refresh_opt_row()
        self.render_page()

    def _update_zoom_slider_range(self) -> None:
        if not self.doc:
            self._zoom_slider.setRange(10, 800)
            return
        page = self.doc[self.current_page]
        pw, ph = page.rect.width, page.rect.height
        vp = self._scroll.viewport()
        pct_w = max(1, int(100 * (vp.width()  - 4) / pw))
        pct_h = max(1, int(100 * (vp.height() - 4) / ph))
        min_pct = min(pct_w, pct_h)
        cur = self._zoom_slider.value()
        self._zoom_slider.setRange(min(min_pct, self.custom_zoom_pct), 800)
        self._zoom_slider.setValue(max(min_pct, cur))

    def _on_zoom_slider(self, value: int) -> None:
        self.custom_zoom_pct = value
        self._lbl_zoom_pct.setText(f"{value} %")
        if self.zoom_mode == "100":
            self.render_page()

    def _refresh_opt_row(self) -> None:
        # isHidden() not isVisible() — avoids dependency on parent visibility
        self._opt_row.setVisible(any(
            not w.isHidden() for w in (self._sign_panel, self._compress_panel)))
        self.sidebar.set_tools_visible(any(
            not w.isHidden() for w in (
                self._txt_panel, self._note_panel, self._markup_panel,
                self._rect_panel, self._emoji_panel,
                self._edit_panel, self._zoom_panel, self._pages_panel,
            )))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.doc:
            if self.zoom_mode in ("width", "height"):
                self.render_page()
            elif self.zoom_mode == "100":
                self._update_zoom_slider_range()

    # ── Render & navigation ────────────────────────────────────────────── #

    def render_page(self, keep_selection: bool = False):
        # Un campo en edición se confirma antes de volver a pintar (zoom, deshacer…).
        self.viewer.forms.close_editor(commit=True)
        self.viewer.content.close_editor(commit=True)
        self.viewer.close_text_editor(commit=True)
        if not self.doc:
            self.viewer.forms.fields = []
            self.viewer.content.clear()
            return
        self._page_edit.setText(str(self.current_page + 1))
        self._lbl_page.setText(f"/ {len(self.doc)}")
        page = self.doc[self.current_page]
        try:
            same_page = (self.viewer.pdf_page is not None
                         and self.viewer.pdf_page.number == page.number)
        except Exception:        # página de un documento ya cerrado (deshacer)
            same_page = False
        if not same_page:
            self.viewer._words = None
        self.viewer.pdf_page = page
        self.viewer.scale_factor = self._compute_scale()
        self.viewer.forms.refresh()
        self.viewer.content.refresh()
        mat = fitz.Matrix(self.viewer.scale_factor, self.viewer.scale_factor)
        pix = page.get_pixmap(matrix=mat)
        img = QImage(pix.samples, pix.width, pix.height, pix.stride,
                     QImage.Format.Format_RGB888)
        self.viewer.setPixmap(QPixmap.fromImage(img))
        self.viewer.resize(pix.width, pix.height)
        if not keep_selection:
            self.viewer._sel = None
            self.viewer.clear_text_selection()
            self._hide_annot_opts()
        self.viewer.update()
        self.sidebar.set_current_page(self.current_page)

    def prev_page(self):
        if self.doc and self.current_page > 0:
            self.current_page -= 1
            self.render_page()

    def next_page(self):
        if self.doc and self.current_page < len(self.doc) - 1:
            self.current_page += 1
            self.render_page()

    # ── Page operations ────────────────────────────────────────────────── #

    def organize_pages(self):
        """Menú Organizar › Organizar páginas: el modo del panel lateral."""
        if not self._require_open():
            return
        self._set_pages_mode(True)

    def copy_page(self):
        if not self._require_open():
            return
        self.checkpoint("Duplicar página")
        # fullcopy_page crea una página independiente; copy_page comparte el
        # objeto página, y anotar una copia modificaría también la otra.
        # `to` debe estar en -1..n-1: tras la última página se usa -1 (al final).
        cur = self.current_page
        to = cur + 1 if cur + 1 < len(self.doc) else -1
        if hasattr(self.doc, "fullcopy_page"):
            self.doc.fullcopy_page(cur, to)
        else:
            self.doc.copy_page(cur, to)
        self.current_page += 1
        self.mark_modified(structure=True)
        self.render_page()
        self._finish_action()

    def merge_pdf(self):
        if not self._require_open():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar PDF para unir", "", "Archivos PDF (*.pdf)")
        if path:
            try:
                src = fitz.open(path)
            except Exception as e:
                QMessageBox.warning(self, "Error al unir", str(e))
                return
            if src.needs_pass:
                src.close()
                QMessageBox.warning(self, "Error al unir", "El PDF está protegido con contraseña.")
                return
            n, ok = self._run_doc_change("Unir PDF", lambda: self.doc.insert_pdf(src))
            src.close()
            if ok:
                self.statusBar().showMessage(f"«{os.path.basename(path)}» añadido al final")
                self._finish_action()

    def compress_pdf(self):
        """Guarda una copia comprimida (Acrobat/iLovePDF, ver pdf_compression).
        Nunca reduce imágenes por debajo de 75 ppp al imprimir en DIN A4."""
        if not self._require_open():
            return
        level = pdf_compression.LEVELS_BY_KEY[self._compress_level_cb.currentData()]
        if doc_tools.has_signatures(self.doc):
            r = QMessageBox.warning(
                self, "Comprimir PDF",
                "El documento está firmado digitalmente. La copia comprimida se "
                "reescribe entera y sus firmas dejarán de ser válidas (el original "
                "no cambia).\n\n¿Continuar?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if r != QMessageBox.StandardButton.Yes:
                return
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar PDF comprimido",
            os.path.join(self._start_dir(), self._base_name() + "_comprimido.pdf"),
            "Archivos PDF (*.pdf)")
        if not path:
            return
        if not path.lower().endswith(".pdf"):
            path += ".pdf"

        # Sin cambios se parte del archivo tal como está en disco (y se compara con él).
        if not self._modified and self._clean_bytes is not None:
            data = self._clean_bytes
        else:
            data = self._doc_bytes()
        # La copia conserva la protección del documento (o la pendiente de aplicar).
        encryption = dict(self._encrypt_opts) if self._encrypt_opts else None

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            res = pdf_compression.compress(data, level.key, self._password, encryption)
            if res.smaller:
                tmp = path + ".agtmp"
                with open(tmp, "wb") as f:
                    f.write(res.data)
                os.replace(tmp, path)
        except Exception as e:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, "Error", f"No se pudo comprimir el PDF:\n{e}")
            return
        QApplication.restoreOverrideCursor()

        fmt = pdf_compression.format_size
        if not res.smaller:
            QMessageBox.information(
                self, "Comprimir PDF",
                f"Este PDF ya está optimizado: con el nivel «{level.label}» no se reduce "
                f"({fmt(res.original_size)} → {fmt(res.size)}).\n\nNo se ha guardado ninguna copia.")
            self._finish_action()
            return
        lineas = [
            f"PDF comprimido (nivel «{level.label}») guardado en:\n{path}", "",
            f"{fmt(res.original_size)} → {fmt(res.size)}   (−{res.saved_percent:.0f} %)",
            f"Imágenes: {res.images_resampled} con resolución reducida (hasta "
            f"{res.color_ppi} ppp) y {res.images_recompressed} recomprimidas; ninguna por "
            f"debajo de {pdf_compression.MIN_PRINT_PPI} ppp al imprimir en DIN A4.",
        ]
        if res.text_images:
            lineas.append(
                f"{res.text_images} {'imagen' if res.text_images == 1 else 'imágenes'} con texto: "
                f"como mínimo {pdf_compression.TEXT_MIN_PPI} ppp y calidad "
                f"{pdf_compression.TEXT_MIN_JPEG_QUALITY} para que se lea bien.")
        if res.min_print_ppi is not None:
            nota = ""
            if res.original_min_print_ppi is not None and \
                    res.original_min_print_ppi < pdf_compression.MIN_PRINT_PPI:
                nota = " (el original ya tenía imágenes por debajo; no se amplían)"
            lineas.append(f"Resolución mínima al imprimir en A4: {res.min_print_ppi:.0f} ppp{nota}.")
        if res.note:
            lineas += ["", res.note]
        QMessageBox.information(self, "Comprimir PDF", "\n".join(lineas))
        self._finish_action()

    # ── Signature (la firma en sí vive en window_document.DocumentMixin) ── #

    def _refresh_cert_label(self) -> None:
        cert = load_saved_cert()
        if cert["type"] == "windows":
            label = cert.get("name") or "Certificado de Windows"
            self._sign_cert_lbl.setText(f"🖥️  {label}")
            self._sign_cert_lbl.setStyleSheet("color: #107C10; font-weight: 600;")
        elif cert["type"] == "file":
            label = os.path.basename(cert["path"])
            self._sign_cert_lbl.setText(f"📁  {label}")
            self._sign_cert_lbl.setStyleSheet("color: #107C10; font-weight: 600;")
        else:
            self._sign_cert_lbl.setText("Sin certificado seleccionado")
            self._sign_cert_lbl.setStyleSheet("color: #605E5C;")

    def _on_hand_signature(self) -> None:
        """(r68) Botón de la plumilla: pide la firma (dibujada o imagen) y deja
        la herramienta Firma lista para colocarla con un clic o un recuadro."""
        import firma_manuscrita_ui
        if self.viewer.hand_signature is not None:        # segunda pulsación: se suelta
            self.viewer.set_hand_signature(None)
            self._btn_handsign.setChecked(False)
            self._activate_tool_hint()
            return
        self._btn_handsign.setChecked(False)
        if not self._require_open():
            return
        sig = firma_manuscrita_ui.ask_hand_signature(self)
        if sig is None or self.viewer.mode != "SIGN":
            return
        self.viewer.set_hand_signature(sig, firma_manuscrita_ui.preview_image(sig))
        self._btn_handsign.setChecked(True)
        self.statusBar().showMessage(
            "Firma manuscrita — haz clic donde irá (o arrastra un recuadro para darle "
            "tamaño)  ·  Esc cancela")

    def _activate_tool_hint(self) -> None:
        self.statusBar().showMessage("Firma — dibuja el área donde irá la firma")

    def place_hand_signature(self, center=None, box=None) -> None:
        """Estampa la firma manuscrita preparada: centrada en `center` con el
        ancho por defecto, o encajada en `box` sin deformarla."""
        sig = self.viewer.hand_signature
        if sig is None or self.doc is None:
            return
        page = self.doc[self.current_page]
        rect = firma_manuscrita.fit_rect(sig, center=center, box=box)
        # Que no se salga de la página (se desplaza; si no cabe, se reduce).
        pr = page.rect
        if rect.width > pr.width or rect.height > pr.height:
            f = min(pr.width / rect.width, pr.height / rect.height) * 0.95
            c = fitz.Point((rect.x0 + rect.x1) / 2, (rect.y0 + rect.y1) / 2)
            rect = fitz.Rect(c.x - rect.width * f / 2, c.y - rect.height * f / 2,
                             c.x + rect.width * f / 2, c.y + rect.height * f / 2)
        dx = max(pr.x0 - rect.x0, 0) or min(pr.x1 - rect.x1, 0)
        dy = max(pr.y0 - rect.y0, 0) or min(pr.y1 - rect.y1, 0)
        rect = rect + (dx, dy, dx, dy)
        self.checkpoint("Firma manuscrita")
        firma_manuscrita.add_hand_signature(self.doc, self.current_page, rect, sig)
        self.mark_modified()
        self.render_page()
        self._finish_action()
        self.statusBar().showMessage(
            "Firma manuscrita colocada  ·  selecciónala para moverla o cambiarle el tamaño")

    def _change_cert(self) -> None:
        dlg = CertPickerDialog(self, saved_cert=load_saved_cert())
        if dlg.exec():
            self._refresh_cert_label()

    def _forget_cert(self) -> None:
        forget_cert()
        self._refresh_cert_label()

    # ── Helper ─────────────────────────────────────────────────────────── #

    def _require_open(self) -> bool:
        if not self.doc:
            QMessageBox.warning(self, "Sin archivo", "Abre un PDF primero.")
            return False
        return True
