"""
viewer.py
Visor interactivo de una página (`PDFViewerWidget`) y estado de selección de
anotaciones (`AnnotSelection`).

Modos (`viewer.mode`):
  NONE      selección: mover/redimensionar anotaciones, seleccionar y copiar
            texto, rellenar campos de formulario
  TEXT      cuadro de texto (FreeText rich-text)
  NOTE      nota adhesiva (Text)
  MARKUP    resaltar / subrayar / tachar / ondular: sobre el texto real si se
            empieza encima de él; si no, a mano alzada (Ink) sobre imágenes y
            demás objetos, enderezando los trazos rápidos (r59; sustituye al
            antiguo modo HIGHLIGHT, «Marcador a mano alzada»)
  RECT      rectángulo de esquinas redondeadas (Square)
  EMOJI     emoji de Noto Emoji con color y transparencia (Stamp)
  ERASE     borrador de anotaciones
  EDIT      editar el texto y las imágenes REALES de la página (edit_ui/pdf_edit)
  SIGN      dibujar el área de la firma PAdES

Regla de deshacer: toda modificación del documento va precedida de
`main_window.checkpoint(etiqueta)` y seguida de `main_window.mark_modified()`.
"""
import math
import statistics
import time
from dataclasses import dataclass

import fitz
from PyQt6.QtCore import Qt, QPoint, QRect, QRectF, QTimer
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QLabel, QMenu, QToolTip

import doc_tools
import icons
import edit_ui
import inplace_editor
import emoji_font
import firma_manuscrita as fm
import form_ui
from utils import PDFUtils

_MARKUP_TYPES = ('Highlight', 'Underline', 'StrikeOut', 'Squiggly')


def _keep_aspect(r: fitz.Rect, o: fitz.Rect, corner: str) -> fitz.Rect:
    """Ajusta `r` (arrastrado desde la esquina `corner`) a la proporción de `o`,
    dejando fija la esquina opuesta. Para emojis: nunca se deforman."""
    if o.width <= 0 or o.height <= 0:
        return r
    s = max(r.width / o.width, r.height / o.height)
    w, h = o.width * s, o.height * s
    if corner == "TL":
        return fitz.Rect(o.x1 - w, o.y1 - h, o.x1, o.y1)
    if corner == "TR":
        return fitz.Rect(o.x0, o.y1 - h, o.x0 + w, o.y1)
    if corner == "BL":
        return fitz.Rect(o.x1 - w, o.y0, o.x1, o.y0 + h)
    return fitz.Rect(o.x0, o.y0, o.x0 + w, o.y0 + h)
_FIELD_READ_ONLY = getattr(fitz, "PDF_FIELD_IS_READ_ONLY", 1)
_TX_MULTILINE = getattr(fitz, "PDF_TX_FIELD_IS_MULTILINE", 4096)


# ─────────────────────────────────────────────────────────────────────────────
# Annotation selection state
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AnnotSelection:
    idx: int
    rect: fitz.Rect
    orig_rect: fitz.Rect
    annot_type: str

    @property
    def is_signature(self):
        return self.annot_type == 'Widget'

    @property
    def is_text(self):
        return self.annot_type in ('FreeText', 'Text')

    @property
    def is_note(self):
        return self.annot_type == 'Text'

    @property
    def is_fixed(self):
        """Marcado de texto: está anclado al texto, no se mueve ni redimensiona."""
        return self.annot_type in _MARKUP_TYPES or self.annot_type == 'Widget'


# ─────────────────────────────────────────────────────────────────────────────
# PDF viewer widget
# ─────────────────────────────────────────────────────────────────────────────

class PDFViewerWidget(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.setMouseTracking(True)   # cursores y avisos al pasar por encima

        self.mode = "NONE"
        self.start_pos: QPoint | None = None
        self.current_rect: QRect | None = None
        self.pdf_page = None
        self.scale_factor = 1.5
        self.main_window = None

        # Text options
        self.text_font_size: int = 12
        self.text_color: tuple = (0.0, 0.0, 0.0)
        self.text_bold: bool = False
        self.text_italic: bool = False
        self.text_align: int = 0          # 0=left 1=center 2=right 3=justify
        self.text_font: str = "sans"      # sans | serif | mono | doc  (Noto, r36)

        # Emoji options
        self.emoji_font_size: int = 24
        self.selected_emoji: str = emoji_font.DEFAULT
        self.emoji_color: tuple = emoji_font.DEFAULT_COLOR      # (r40) color y…
        self.emoji_opacity: float = emoji_font.DEFAULT_OPACITY  # … transparencia

        # Trazo a mano alzada de MARKUP (r59)
        self._stroke_pts: list[QPoint] = []
        self._stroking: bool = False
        self._stroke_t0: float = 0.0

        # Rectangle tool options
        self.rect_color: tuple = (0.82, 0.20, 0.22)
        self.rect_line_width: int = 2
        self.rect_corner_radius: int = 6  # PDF points — matches app border-radius

        # Notas y marcado de texto
        self.note_color: tuple = (1.0, 0.82, 0.0)
        self.markup_kind: str = "highlight"   # highlight | underline | strike | squiggly
        self.markup_color: tuple = doc_tools.MARKUP_COLORS["highlight"]
        self.markup_opacity: float = 1.0        # (r41) transparencia del marcado
        # (r59) Grosor del trazo a mano alzada, en puntos PDF, por tipo de marca.
        self.markup_widths: dict = dict(FREEHAND_WIDTHS)

        # Selection / drag
        self._sel: AnnotSelection | None = None
        self._dragging: bool = False
        self._drag_start: fitz.Point | None = None

        # Resize handles
        self._resizing: str | None = None
        self._resize_orig_rect = None
        self._resize_keep_aspect = False
        # Formularios: resaltado, edición en línea, botones (form_ui / pdf_forms).
        self.forms = form_ui.FormController(self)
        # Herramienta «Editar contenido» (edit_ui / pdf_edit).
        self.content = edit_ui.ContentEditor(self)
        # Escritura sobre la propia página: herramienta Texto, notas y edición
        # de anotaciones. Nunca se abre una ventana para escribir (r23).
        self.text_editor: inplace_editor.InPlaceEditor | None = None
        self._text_target: tuple | None = None
        self._text_box: fitz.Rect | None = None
        self._text_busy = False
        self._swallow_release = False

        # Selección de texto (modo NONE y herramienta MARKUP)
        self._words = None                      # caché de page.get_text("words")
        self._tsel_start: fitz.Point | None = None
        self._tsel_press = QPoint()
        self._tsel_rects: list = []
        self._tsel_text: str = ""

        self._erase_checkpointed = False
        self._wheel_accum = 0

        # (r68) Firma manuscrita preparada para colocar (herramienta SIGN).
        self.hand_signature = None
        self._hand_preview = None            # QImage con transparencia
        self._hover_pos: QPoint | None = None

    def set_hand_signature(self, sig, preview=None) -> None:
        """Con firma, la herramienta Firma estampa la firma manuscrita en vez
        de dibujar el recuadro de la firma digital."""
        self.hand_signature = sig
        self._hand_preview = preview
        self._hover_pos = None
        self.update()

    # ── coordinates ───────────────────────────────────────────────────── #

    def _to_pdf_pt(self, pos: QPoint) -> fitz.Point:
        s = self.scale_factor
        return fitz.Point(pos.x() / s, pos.y() / s)

    def _to_pdf_rect(self, qr: QRect) -> fitz.Rect:
        s = self.scale_factor
        return fitz.Rect(qr.left()/s, qr.top()/s, qr.right()/s, qr.bottom()/s)

    def _to_screen_rect(self, fr: fitz.Rect) -> QRect:
        s = self.scale_factor
        return QRect(int(fr.x0*s), int(fr.y0*s),
                     int((fr.x1-fr.x0)*s), int((fr.y1-fr.y0)*s))

    # ── annotation lookup ─────────────────────────────────────────────── #

    def _annot_at(self, pdf_pt):
        if not self.pdf_page:
            return None
        for i, a in enumerate(self.pdf_page.annots()):
            if a.rect.contains(pdf_pt):
                return i, a
        return None

    def _annot_by_idx(self, idx):
        if not self.pdf_page:
            return None
        lst = list(self.pdf_page.annots())
        return lst[idx] if 0 <= idx < len(lst) else None

    def _select_hit(self, hit) -> None:
        idx, a = hit
        r = fitz.Rect(a.rect)
        self._sel = AnnotSelection(idx, fitz.Rect(r), fitz.Rect(r), a.type[1])
        self.main_window._show_annot_opts(a)

    def _delete_selected(self) -> None:
        mw = self.main_window
        a = self._annot_by_idx(self._sel.idx) if self._sel else None
        if a is None or self._sel.is_signature:
            return
        mw.checkpoint("Eliminar anotación")
        self.pdf_page.delete_annot(a)
        self._sel = None
        mw._hide_annot_opts()
        mw.mark_modified()
        mw.render_page()

    # ── selección de texto ────────────────────────────────────────────── #

    def _page_words(self) -> list:
        if self._words is None and self.pdf_page is not None:
            try:
                self._words = self.pdf_page.get_text("words")
            except Exception:
                self._words = []
        return self._words or []

    def _word_at(self, pdf_pt: fitz.Point, margin: float = 1) -> bool:
        """¿Hay texto seleccionable bajo el punto? (cursor de texto)."""
        x, y = pdf_pt.x, pdf_pt.y
        return any(w[0] - margin <= x <= w[2] + margin and w[1] - margin <= y <= w[3] + margin
                   for w in self._page_words())

    def _markup_on_text(self, pdf_pt: fitz.Point) -> bool:
        """(r59) MARKUP marca texto si el gesto empieza sobre él (con un poco de
        holgura, para poder arrancar justo antes de la primera letra); si no,
        dibuja a mano alzada."""
        return self._word_at(pdf_pt, MARKUP_TEXT_MARGIN)

    def _update_text_selection(self, pdf_pt: fitz.Point) -> None:
        if self._tsel_start is None:
            return
        words = self._page_words()
        self._tsel_rects, self._tsel_text = doc_tools.word_selection(
            self.pdf_page, self._tsel_start, pdf_pt, words)
        self.update()

    def clear_text_selection(self) -> None:
        had = bool(self._tsel_rects)
        self._tsel_rects = []
        self._tsel_text = ""
        self._tsel_start = None
        if had:
            self.update()

    # ── mouse ─────────────────────────────────────────────────────────── #

    def _get_resize_corner(self, pos: QPoint) -> str | None:
        if not self._sel or self._sel.is_fixed or self._sel.is_note:
            return None
        sr = self._to_screen_rect(self._sel.rect)
        H = 8   # visual handle size (matches paintEvent)
        hit = 12  # slightly larger hit area for usability
        corners = {
            "TL": (sr.left(),        sr.top()),
            "TR": (sr.right() - H,   sr.top()),
            "BL": (sr.left(),        sr.bottom() - H),
            "BR": (sr.right() - H,   sr.bottom() - H),
        }
        for name, (hx, hy) in corners.items():
            if QRect(hx - 2, hy - 2, hit, hit).contains(pos):
                return name
        return None

    def _erase_at(self, screen_pos: QPoint) -> None:
        if not self.pdf_page:
            return
        hit = self._annot_at(self._to_pdf_pt(screen_pos))
        if not hit:
            return
        _, annot = hit
        if annot.type[1] == "Widget":
            return
        if not self._erase_checkpointed:          # un solo paso por arrastre
            self.main_window.checkpoint("Borrador")
            self._erase_checkpointed = True
        self.pdf_page.delete_annot(annot)
        self.main_window.mark_modified()
        self.main_window.render_page()

    def mousePressEvent(self, event):
        mw = self.main_window
        if not self.pdf_page or event.button() != Qt.MouseButton.LeftButton:
            return
        # Pulsar en la página confirma lo que se estuviera escribiendo: el visor
        # no le quita el foco al editor (no llama a super()), así que hay que
        # cerrarlo a mano.
        if self.text_editor is not None:
            self.close_text_editor(commit=True)
            # Ese clic solo confirma: si se dejara pasar, al soltar se abriría
            # otro cuadro de escritura en el mismo sitio.
            self._swallow_release = True
            self.start_pos = None
            return
        pos = event.pos()
        if self.mode == "NONE":
            corner = self._get_resize_corner(pos)
            if corner and self._sel:
                self._resizing = corner
                self._resize_orig_rect = fitz.Rect(self._sel.rect)
                self._sel.orig_rect = fitz.Rect(self._sel.rect)
                a = self._annot_by_idx(self._sel.idx)
                self._resize_keep_aspect = bool(a) and (
                    emoji_font.is_stamp(a.info.get("subject", "")))
                return
            pdf_pt = self._to_pdf_pt(pos)
            self.clear_text_selection()
            hit = self._annot_at(pdf_pt)
            if hit:
                self._select_hit(hit)
                self._dragging = not self._sel.is_fixed
                self._drag_start = pdf_pt
            else:
                self._sel = None
                self._dragging = False
                mw._hide_annot_opts()
                field = self.forms.field_at(pdf_pt)
                if field is not None:
                    self.update()
                    self.forms.click(field)
                    return
                self._tsel_start = pdf_pt
                self._tsel_press = QPoint(pos)
            self.update()
        elif self.mode == "EDIT":
            self.content.press(pos, self._to_pdf_pt(pos))
        elif self.mode in ("SIGN", "RECT"):
            self.start_pos = pos
            self.current_rect = QRect(pos, pos)
            self.update()
        elif self.mode == "MARKUP":
            self.clear_text_selection()
            if self._markup_on_text(self._to_pdf_pt(pos)):
                self._tsel_start = self._to_pdf_pt(pos)
                self._tsel_press = QPoint(pos)
            else:                                   # (r59) a mano alzada
                self._stroke_pts = [pos]
                self._stroking = True
                self._stroke_t0 = time.monotonic()
        elif self.mode in ("TEXT", "EMOJI", "NOTE"):
            self.start_pos = pos
        elif self.mode == "ERASE":
            self._erase_checkpointed = False
            self._erase_at(pos)

    def mouseMoveEvent(self, event):
        pos = event.pos()
        left = bool(event.buttons() & Qt.MouseButton.LeftButton)

        if self._tsel_start is not None and left and self.mode in ("NONE", "MARKUP"):
            if (pos - self._tsel_press).manhattanLength() >= 4:
                self._update_text_selection(self._to_pdf_pt(pos))
            return

        if self.mode == "EDIT":
            self.content.move(pos, self._to_pdf_pt(pos), left)
            self.setCursor(self.content.cursor_at(pos, self._to_pdf_pt(pos)))
            return

        if self.mode == "MARKUP":
            if self._stroking:
                self._stroke_pts.append(pos)
                self.update()
            elif not left and self.pdf_page is not None:
                self.setCursor(Qt.CursorShape.IBeamCursor
                               if self._markup_on_text(self._to_pdf_pt(pos))
                               else Qt.CursorShape.CrossCursor)
            return

        if self.mode == "ERASE":
            if left:
                self._erase_at(pos)
            return

        if self.mode == "NONE":
            if self._resizing and self._sel and self._resize_orig_rect:
                pt = self._to_pdf_pt(pos)
                o = self._resize_orig_rect
                MIN = 10  # minimum annotation size in PDF points
                if self._resizing == "TL":
                    self._sel.rect = fitz.Rect(min(pt.x, o.x1 - MIN), min(pt.y, o.y1 - MIN), o.x1, o.y1)
                elif self._resizing == "TR":
                    self._sel.rect = fitz.Rect(o.x0, min(pt.y, o.y1 - MIN), max(pt.x, o.x0 + MIN), o.y1)
                elif self._resizing == "BL":
                    self._sel.rect = fitz.Rect(min(pt.x, o.x1 - MIN), o.y0, o.x1, max(pt.y, o.y0 + MIN))
                elif self._resizing == "BR":
                    self._sel.rect = fitz.Rect(o.x0, o.y0, max(pt.x, o.x0 + MIN), max(pt.y, o.y0 + MIN))
                if self._resize_keep_aspect:
                    self._sel.rect = _keep_aspect(self._sel.rect, o, self._resizing)
                self.update()
            elif self._dragging and self._sel and self._drag_start and left:
                pt = self._to_pdf_pt(pos)
                dx = pt.x - self._drag_start.x
                dy = pt.y - self._drag_start.y
                o = self._sel.orig_rect
                self._sel.rect = fitz.Rect(o.x0+dx, o.y0+dy, o.x1+dx, o.y1+dy)
                self.update()
            elif not left and self.pdf_page is not None:
                _diag_cursors = {
                    "TL": Qt.CursorShape.SizeFDiagCursor,
                    "BR": Qt.CursorShape.SizeFDiagCursor,
                    "TR": Qt.CursorShape.SizeBDiagCursor,
                    "BL": Qt.CursorShape.SizeBDiagCursor,
                }
                corner = self._get_resize_corner(pos)
                if corner:
                    self.setCursor(_diag_cursors[corner])
                    return
                pdf_pt = self._to_pdf_pt(pos)
                hit = self._annot_at(pdf_pt)
                field = None if hit else self.forms.field_at(pdf_pt)
                if hit:
                    atype = hit[1].type[1]
                    if atype == 'Text':
                        QToolTip.showText(event.globalPosition().toPoint(),
                                          hit[1].info.get('content', '') or 'Nota', self)
                    self.setCursor(Qt.CursorShape.PointingHandCursor if atype in _MARKUP_TYPES
                                   else Qt.CursorShape.SizeAllCursor)
                elif field is not None:
                    self.setCursor(self.forms.cursor_for(field))
                    if field["tooltip"]:
                        QToolTip.showText(event.globalPosition().toPoint(), field["tooltip"], self)
                elif self._word_at(pdf_pt):
                    self.setCursor(Qt.CursorShape.IBeamCursor)      # texto seleccionable
                else:
                    self.setCursor(Qt.CursorShape.ArrowCursor)
            return

        if self.mode in ("SIGN", "RECT") and self.start_pos:
            self.current_rect = QRect(self.start_pos, pos).normalized()
            self.update()
        elif self.mode == "SIGN" and self.hand_signature is not None:
            self._hover_pos = QPoint(pos)       # vista previa bajo el cursor
            self.update()

    def leaveEvent(self, event):
        if self._hover_pos is not None:          # (r68) sin cursor, sin vista previa
            self._hover_pos = None
            self.update()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event):
        mw = self.main_window
        if event.button() != Qt.MouseButton.LeftButton:
            return

        if self.mode == "EDIT":
            self.content.release(event.pos())
            return

        if self.mode == "MARKUP" and self._stroking:
            self._stroking = False
            self._stroke_pts.append(event.pos())
            duracion = time.monotonic() - self._stroke_t0
            pdf_pts = [self._to_pdf_pt(p) for p in self._stroke_pts]
            self._stroke_pts = []
            self.update()
            if len(pdf_pts) >= 2 and _path_length(pdf_pts) * self.scale_factor >= 4:
                kind = self.markup_kind
                ancho = self.markup_widths[kind]
                pdf_pts = straighten_stroke(pdf_pts, duracion, self.scale_factor)
                if kind == "squiggly":
                    pdf_pts = squiggle(pdf_pts, ancho)
                mw.add_freehand_markup(pdf_pts, kind, self.markup_color,
                                       self.markup_opacity, ancho)
            return   # la herramienta sigue activa, como con el texto

        if self.mode == "MARKUP":
            if self._tsel_start is not None:
                moved = (event.pos() - self._tsel_press).manhattanLength() >= 4
                if moved:
                    self._update_text_selection(self._to_pdf_pt(event.pos()))
                rects = list(self._tsel_rects) if moved else []
                self.clear_text_selection()
                if rects:
                    mw.add_text_markup(rects, self.markup_kind, self.markup_color,
                                       self.markup_opacity)
            return   # la herramienta sigue activa, como en Acrobat

        if self.mode == "NONE":
            if self._tsel_start is not None:
                self._tsel_start = None
                if self._tsel_text:
                    mw.statusBar().showMessage(
                        f"{len(self._tsel_text)} caracteres seleccionados  ·  Ctrl+C copia"
                        "  ·  clic derecho para resaltar, subrayar o tachar")
                return
            if self._resizing and self._sel:
                a = self._annot_by_idx(self._sel.idx)
                if a:
                    nr = fitz.Rect(self._sel.rect)
                    mw.checkpoint("Redimensionar")
                    subj = a.info.get('subject', '')
                    if emoji_font.is_stamp(subj):
                        # Su apariencia escala con /Rect. Sin set_rect() ni update(),
                        # que la sustituirían por un sello estándar (invariante 3).
                        emoji_font.write_rect(self.pdf_page, a, nr)
                        if emoji_font.is_sized(subj) and self._resize_orig_rect:
                            try:
                                fs = float(a.info.get('title') or self.emoji_font_size)
                                fs *= nr.height / max(1.0, self._resize_orig_rect.height)
                                PDFUtils._set_info_keys(mw.doc, a, title=f"{fs:.1f}")
                            except (TypeError, ValueError):
                                pass
                    elif subj == 'EmojiStamp' and self._resize_orig_rect:
                        a.set_rect(nr)
                        orig_h = max(1.0, self._resize_orig_rect.y1 - self._resize_orig_rect.y0)
                        new_h = max(1.0, nr.y1 - nr.y0)
                        stored_fs = a.info.get('title', '')
                        try:
                            new_fs = max(6.0, float(stored_fs) * new_h / orig_h) if stored_fs else 24.0
                            a.update(fontsize=new_fs)
                            a.set_info(title=str(new_fs))
                        except (ValueError, TypeError):
                            a.update()
                    else:
                        a.set_rect(nr)
                        a.update()
                        if a.type[1] == 'Square':
                            PDFUtils.apply_rounded_corners(a, self.rect_corner_radius)
                        elif a.type[1] == 'FreeText':
                            PDFUtils.apply_text_appearance(mw.doc, a)
                    mw.mark_modified()
                    self._sel.orig_rect = fitz.Rect(nr)
                    mw.render_page(keep_selection=True)
                else:
                    self._sel = None
                self._resizing = None
                self._resize_orig_rect = None
                self._resize_keep_aspect = False
                return
            if self._dragging and self._sel and self._drag_start:
                pt = self._to_pdf_pt(event.pos())
                dx = pt.x - self._drag_start.x
                dy = pt.y - self._drag_start.y
                if abs(dx) > 1 or abs(dy) > 1:
                    a = self._annot_by_idx(self._sel.idx)
                    if a:
                        o = self._sel.orig_rect
                        nr = fitz.Rect(o.x0+dx, o.y0+dy, o.x1+dx, o.y1+dy)
                        mw.checkpoint("Mover")
                        if emoji_font.is_stamp(a.info.get('subject', '')):
                            # Sin set_rect(): MuPDF regeneraría la apariencia (invariante 3).
                            emoji_font.write_rect(self.pdf_page, a, nr)
                        else:
                            a.set_rect(nr)
                            a.update()
                            if a.type[1] == 'Square':
                                PDFUtils.apply_rounded_corners(a, self.rect_corner_radius)
                            elif a.type[1] == 'FreeText':
                                PDFUtils.apply_text_appearance(mw.doc, a)
                        mw.mark_modified()
                        self._sel.orig_rect = fitz.Rect(nr)
                        self._sel.rect = fitz.Rect(nr)
                        mw.render_page(keep_selection=True)
                    else:
                        self._sel = None
                else:
                    self._sel.rect = fitz.Rect(self._sel.orig_rect)
            self._dragging = False
            return

        if not self.pdf_page:
            return

        if self._swallow_release:
            self._swallow_release = False
            return

        end = event.pos()

        if self.mode in ("SIGN", "RECT") and self.start_pos:
            qr = QRect(self.start_pos, end).normalized()
            self.start_pos = None
            self.current_rect = None
            self.update()
            if self.mode == "SIGN" and self.hand_signature is not None:
                # (r68) Clic = tamaño por defecto; recuadro = encajada en él.
                if qr.width() < 8 or qr.height() < 8:
                    mw.place_hand_signature(center=self._to_pdf_pt(end))
                else:
                    mw.place_hand_signature(box=self._to_pdf_rect(qr))
                return
            if qr.width() < 4 or qr.height() < 4:
                return      # clic accidental
            pdf_r = self._to_pdf_rect(qr)
            if self.mode == "SIGN":
                mw.trigger_signature(pdf_r)
            else:
                mw.checkpoint("Rectángulo")
                PDFUtils.add_rectangle_annotation(
                    mw.doc, mw.current_page, pdf_r,
                    color=self.rect_color, width=self.rect_line_width,
                    corner_radius=self.rect_corner_radius)
                mw.mark_modified()
                mw.render_page()
                mw._finish_action()

        elif self.mode == "TEXT":
            caja = self._text_rect(end)
            self.start_pos = None
            self.begin_text(caja)

        elif self.mode == "NOTE":
            self.start_pos = None
            self.begin_note(self._to_pdf_pt(end))

        elif self.mode == "EMOJI":
            mw.checkpoint("Emoji")
            mw._insert_emoji(self._to_pdf_pt(end), self.selected_emoji,
                             self.emoji_font_size, self.emoji_color, self.emoji_opacity)
            mw.mark_modified()
            mw.render_page()
            mw._finish_action()

    def mouseDoubleClickEvent(self, event):
        if self.mode == "NONE" and self._sel and self._sel.is_text:
            self._edit_selected_text()

    def _edit_selected_text(self) -> None:
        """Edita la anotación seleccionada SOBRE la página, sin ventana."""
        a = self._annot_by_idx(self._sel.idx) if self._sel else None
        if a is None:
            return
        es_nota = a.type[1] == "Text"
        st = PDFUtils.decode_text_style(a.info.get("subject", ""))
        try:
            fs = float(a.info.get("title") or self.text_font_size)
        except (TypeError, ValueError):
            fs = self.text_font_size
        caja = fitz.Rect(a.rect)
        if es_nota:
            # El icono de la nota es diminuto: el cuadro se abre a su lado.
            caja = fitz.Rect(caja.x1 + 4, caja.y0, caja.x1 + 4 + 190, caja.y0 + 70)
            fs = self.text_font_size
        editor = self._open_text_editor(
            caja, a.info.get("content", ""),
            family=self._family_for(st["font_css"]), size=fs,
            bold=st["bold"], italic=st["italic"],
            color=(1.0, 0.98, 0.85) if es_nota else st["color"],
            align=st["align"], nota=es_nota)
        if es_nota:                      # el texto de la nota siempre se ve negro
            editor.apply_style(family="Segoe UI", pixel_size=12 * self.scale_factor,
                               color=(0.1, 0.1, 0.1))
        self._text_target = ("annot", self._sel.idx,
                             "Editar nota" if es_nota else "Editar texto")

    # ── escritura sobre la página (r23) ───────────────────────────────── #

    def _family_for(self, font_css: str) -> str:
        """Familia Noto con que se verá el texto en el PDF (r36)."""
        return icons.noto_family(icons.CSS_TO_NOTO.get(font_css, "sans"))

    def _text_rect(self, end: QPoint) -> fitz.Rect:
        """Dónde va el cuadro de la herramienta Texto: el que se haya arrastrado
        o, si fue un clic, uno de ancho cómodo que no se sale de la página."""
        pagina = self.pdf_page.rect
        if self.start_pos is not None:
            r = QRect(self.start_pos, end).normalized()
            if r.width() >= 24 and r.height() >= 18:
                return self._to_pdf_rect(r) & pagina
        pt = self._to_pdf_pt(end)
        fs = self.text_font_size
        ancho = min(280.0, max(90.0, pagina.x1 - pt.x - 6))
        return fitz.Rect(pt.x, pt.y, pt.x + ancho, pt.y + fs * 1.7 + 6) & pagina

    def _open_text_editor(self, caja: fitz.Rect, texto: str, *, family, size,
                          bold=False, italic=False, color=(0, 0, 0), align=0,
                          nota=False):
        """Crea el cuadro de escritura sobre la página y lo deja con el foco."""
        self.close_text_editor(commit=True)
        editor = inplace_editor.InPlaceEditor(
            self, self._to_screen_rect(caja),
            border=(0.85, 0.65, 0.0) if nota else (0.0, 0.47, 0.83),
            background=(1.0, 0.98, 0.85) if nota else (1.0, 1.0, 1.0))
        editor.apply_style(family=family, pixel_size=size * self.scale_factor,
                           bold=bold, italic=italic,
                           color=(0.1, 0.1, 0.1) if nota else color, align=align)
        editor.setPlainText(texto)
        editor.selectAll()
        editor.committed.connect(self._on_text_committed)
        editor.cancelled.connect(lambda: self.close_text_editor(commit=False))
        editor.moved.connect(lambda _d: editor.commit())
        # El cuadro crece al escribir: si no, el texto se recorta en cuanto pasa
        # de una línea y se estaría escribiendo a ciegas.
        editor.enable_autogrow(int(self.pdf_page.rect.y1 * self.scale_factor))
        self.text_editor = editor
        self._text_box = fitz.Rect(caja)
        editor.show()
        editor.setFocus()
        self.update()
        return editor

    def begin_text(self, caja: fitz.Rect) -> None:
        """Herramienta Texto: se escribe directamente donde se ha hecho clic."""
        mw = self.main_window
        self._open_text_editor(
            caja, "", family=self._family_for(mw._text_font_css()),
            size=self.text_font_size, bold=self.text_bold, italic=self.text_italic,
            color=self.text_color, align=self.text_align)
        self._text_target = ("new_text", None, "Texto")
        mw.statusBar().showMessage(
            "Escribe el texto  ·  Ctrl+Intro confirma  ·  Esc cancela")

    def begin_note(self, punto: fitz.Point) -> None:
        """Nota adhesiva: el comentario se escribe en un cuadro amarillo sobre
        la página, no en una ventana."""
        pagina = self.pdf_page.rect
        caja = fitz.Rect(punto.x, punto.y, punto.x + 190, punto.y + 70) & pagina
        self._open_text_editor(caja, "", family="Segoe UI", size=12, nota=True)
        self._text_target = ("new_note", fitz.Point(punto), "Nota")
        self.main_window.statusBar().showMessage(
            "Escribe el comentario  ·  Ctrl+Intro confirma  ·  Esc cancela")

    def restyle_text_editor(self) -> None:
        """La barra secundaria ha cambiado el estilo: se refleja al momento en
        lo que se está escribiendo."""
        editor = self.text_editor
        if editor is None or not self._text_target or self._text_target[0] != "new_text":
            return
        mw = self.main_window
        editor.apply_style(family=self._family_for(mw._text_font_css()),
                           pixel_size=self.text_font_size * self.scale_factor,
                           bold=self.text_bold, italic=self.text_italic,
                           color=self.text_color, align=self.text_align)

    def _on_text_committed(self, texto: str) -> None:
        self.close_text_editor(commit=True, texto=texto)

    def close_text_editor(self, commit: bool = True, texto: str | None = None) -> None:
        """Cierra el cuadro de escritura, aplicando o descartando lo escrito."""
        editor = self.text_editor
        if editor is None or self._text_busy:
            return
        self._text_busy = True
        destino = self._text_target
        caja = self._text_box
        alto_px = float(editor.height())
        # Líneas ya repartidas por el editor (en QPlainTextEdit el alto de
        # documentSize viene en líneas, no en píxeles).
        lineas = max(1, int(round(
            editor.document().documentLayout().documentSize().height())))
        if texto is None:
            texto = editor.toPlainText()
        self.text_editor = self._text_target = self._text_box = None
        editor.finish()
        try:
            if commit:
                self._commit_text(destino, caja, texto, alto_px, lineas)
        finally:
            self._text_busy = False
        self.update()

    def _commit_text(self, destino, caja, texto: str, alto_px: float,
                     lineas: int = 1) -> None:
        mw = self.main_window
        if not destino or mw is None or mw.doc is None:
            return
        clase, dato, etiqueta = destino
        texto = texto.rstrip()
        if clase == "new_text":
            if not texto.strip():
                return
            # La caja crece hasta lo que ocupa el texto: lo que se ve escrito es
            # lo que queda, sin recortes. Se toma la mayor de las dos medidas
            # porque el reparto de Qt y el del rich-text de MuPDF no coinciden
            # exactamente, y quedarse corto recorta el texto.
            fs = self.text_font_size
            alto = max(caja.height,
                       alto_px / max(self.scale_factor, 0.01),
                       fs * 1.45 * lineas + fs * 0.6)
            r = fitz.Rect(caja.x0, caja.y0, caja.x1, caja.y0 + alto) & self.pdf_page.rect
            mw.checkpoint(etiqueta)
            PDFUtils.add_text_annotation(
                mw.doc, mw.current_page, r, texto, fs,
                self.text_color, bold=self.text_bold, italic=self.text_italic,
                align=self.text_align, font_css=mw._text_font_css())
            mw.mark_modified()
            mw.render_page()
            mw._finish_action()
        elif clase == "new_note":
            if not texto.strip():
                return
            mw.add_note(dato, texto)
            mw._finish_action()
        elif clase == "annot":
            a = self._annot_by_idx(dato)
            if a is None or a.info.get("content", "") == texto:
                return
            mw.checkpoint(etiqueta)
            mw._edit_text_annot(a, texto)
            mw.mark_modified()
            mw.render_page(keep_selection=True)

    def contextMenuEvent(self, event):
        if not self.pdf_page:
            return
        if self.mode == "EDIT":
            self.content.context_menu(event.pos(), event.globalPos(),
                                      self._to_pdf_pt(event.pos()))
            return
        if self.mode != "NONE":
            return
        if self._tsel_rects:
            self._text_selection_menu(event.globalPos())
            return
        hit = self._annot_at(self._to_pdf_pt(event.pos()))
        if hit and (self._sel is None or self._sel.idx != hit[0]):
            self._select_hit(hit)
            self.update()
        if not self._sel:
            return
        a = self._annot_by_idx(self._sel.idx)
        if not a:
            return
        menu = QMenu(self)
        act_edit = menu.addAction("Editar texto…") if self._sel.is_text else None
        act_del = None
        if self._sel.is_signature:
            menu.addAction("Firma — no se puede eliminar").setEnabled(False)
        else:
            act_del = menu.addAction("Eliminar anotación")
        chosen = menu.exec(event.globalPos())
        if act_edit is not None and chosen == act_edit:
            self._edit_selected_text()
        elif act_del is not None and chosen == act_del:
            self._delete_selected()

    def _text_selection_menu(self, global_pos) -> None:
        mw = self.main_window
        menu = QMenu(self)
        a_copy = menu.addAction("Copiar texto")
        menu.addSeparator()
        kinds = {}
        for kind, label in (("highlight", "Resaltar"), ("underline", "Subrayar"),
                            ("strike", "Tachar"), ("squiggly", "Subrayado ondulado")):
            kinds[menu.addAction(label)] = kind
        chosen = menu.exec(global_pos)
        if chosen is None:
            return
        rects = list(self._tsel_rects)
        if chosen == a_copy:
            mw.copy_selected_text()
        elif chosen in kinds:
            kind = kinds[chosen]
            color = self.markup_color if kind == self.markup_kind else doc_tools.MARKUP_COLORS[kind]
            self.clear_text_selection()
            mw.add_text_markup(rects, kind, color)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            if self.mode == "EDIT" and self.content.delete_selected():
                return
            if self._sel and not self._sel.is_signature and self.mode == "NONE":
                self._delete_selected()
                return
        super().keyPressEvent(event)

    def wheelEvent(self, event):
        mw = self.main_window
        dy = event.angleDelta().y()
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if dy:
                mw.zoom_step(1 if dy > 0 else -1)
            event.accept()
            return
        if mw is not None and mw.doc is not None and dy:
            bar = mw._scroll.verticalScrollBar()
            at_bottom = bar.value() >= bar.maximum()
            at_top = bar.value() <= bar.minimum()
            if (dy < 0 and at_bottom) or (dy > 0 and at_top):
                # En el borde de la página, dos «muescas» pasan de página.
                self._wheel_accum += dy
                if abs(self._wheel_accum) >= 240:
                    self._wheel_accum = 0
                    if dy < 0 and mw.current_page < len(mw.doc) - 1:
                        mw.go_to_page(mw.current_page + 1)
                        QTimer.singleShot(0, lambda: bar.setValue(bar.minimum()))
                    elif dy > 0 and mw.current_page > 0:
                        mw.go_to_page(mw.current_page - 1)
                        QTimer.singleShot(0, lambda: bar.setValue(bar.maximum()))
                event.accept()
                return
        self._wheel_accum = 0
        event.ignore()   # el QScrollArea desplaza la página

    # ── paint ─────────────────────────────────────────────────────────── #

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        mw = self.main_window

        # Campos de formulario (resaltado y campo en edición)
        self.forms.paint(p)

        # Herramienta «Editar contenido»: recuadros del texto y las imágenes
        self.content.paint(p)

        # Coincidencias de búsqueda en la página actual
        if mw is not None and mw._find_hits:
            for i, (pno, r) in enumerate(mw._find_hits):
                if pno != mw.current_page:
                    continue
                cur = i == mw._find_idx
                p.fillRect(self._to_screen_rect(r),
                           QColor(255, 140, 0, 120) if cur else QColor(255, 225, 0, 90))

        # Selección de texto / vista previa de marcado
        if self._tsel_rects:
            if self.mode == "MARKUP":
                r, g, b = self.markup_color
                col = QColor(int(r * 255), int(g * 255), int(b * 255), 110)
            else:
                col = QColor(0, 120, 212, 70)
            for tr in self._tsel_rects:
                p.fillRect(self._to_screen_rect(tr), col)

        if self._sel and self.mode == "NONE":
            sr = self._to_screen_rect(self._sel.rect)
            col = QColor(0xD1, 0x34, 0x38) if self._sel.is_signature \
                  else QColor(0x00, 0x78, 0xD4)
            p.setPen(QPen(col, 2, Qt.PenStyle.DashLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(sr)
            if not (self._sel.is_fixed or self._sel.is_note):
                h = 8
                for hx, hy in [(sr.left(), sr.top()), (sr.right()-h, sr.top()),
                               (sr.left(), sr.bottom()-h), (sr.right()-h, sr.bottom()-h)]:
                    p.fillRect(hx, hy, h, h, col)

        if self._stroking and len(self._stroke_pts) > 1:
            # (r59) Mismo aspecto que tendrá la anotación: el resaltado tiñe
            # (multiplica) lo de debajo; subrayar/tachar/ondulado, línea fina.
            mr, mg, mb = self.markup_color
            qc = QColor(int(mr*255), int(mg*255), int(mb*255),
                        int(self.markup_opacity * 255))
            ancho = max(1.0, self.markup_widths[self.markup_kind] * self.scale_factor)
            pen = QPen(qc, ancho, Qt.PenStyle.SolidLine,
                       Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            p.save()
            if self.markup_kind == "highlight":
                p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Multiply)
            p.setPen(pen)
            for i in range(1, len(self._stroke_pts)):
                p.drawLine(self._stroke_pts[i-1], self._stroke_pts[i])
            p.restore()

        if self.mode == "SIGN" and self._hand_preview is not None:
            self._paint_hand_preview(p)
        elif self.current_rect and self.mode in ("SIGN", "RECT"):
            if self.mode == "SIGN":
                p.fillRect(self.current_rect, QColor(0, 120, 212, 40))
                p.setPen(QPen(QColor(0, 120, 212), 2, Qt.PenStyle.DashLine))
                p.drawRect(self.current_rect)
            else:
                r, g, b = self.rect_color
                col = QColor(int(r*255), int(g*255), int(b*255))
                pen = QPen(col, self.rect_line_width)
                pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                p.setPen(pen)
                p.setBrush(Qt.BrushStyle.NoBrush)
                radius_px = self.rect_corner_radius * self.scale_factor
                p.drawRoundedRect(self.current_rect, radius_px, radius_px)
        p.end()

    def _paint_hand_preview(self, p: QPainter) -> None:
        """(r68) La firma manuscrita, translúcida, donde va a quedar: en el
        recuadro que se arrastra o, si no, con el tamaño de un clic."""
        sig = self.hand_signature
        if self.current_rect is not None and self.current_rect.width() >= 8                 and self.current_rect.height() >= 8:
            p.setPen(QPen(QColor(0, 120, 212), 1, Qt.PenStyle.DashLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(self.current_rect)
            r = fm.fit_rect(sig, box=self._to_pdf_rect(self.current_rect))
        elif self._hover_pos is not None:
            r = fm.fit_rect(sig, center=self._to_pdf_pt(self._hover_pos))
        else:
            return
        p.save()
        p.setOpacity(0.6)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.drawImage(QRectF(self._to_screen_rect(r)), self._hand_preview)
        p.restore()


# ─────────────────────────────────────────────────────────────────────────────
# Stroke straightening
# ─────────────────────────────────────────────────────────────────────────────

# ── Trazos a mano alzada de «Resaltar, subrayar o tachar» (r59) ────────── #

# Grosor por defecto (puntos PDF): resaltado ancho como un rotulador; las
# líneas, finas como las de subrayar/tachar texto.
FREEHAND_WIDTHS = {"highlight": 12.0, "underline": 2.0, "strike": 2.0, "squiggly": 2.0}
# Holgura (pt) para decidir si el gesto empieza sobre el texto.
MARKUP_TEXT_MARGIN = 3.0
# Un trazo es «rápido» si dura menos de esto o va a más velocidad (en píxeles
# de pantalla por segundo, para que no dependa del zoom).
FAST_STROKE_SECONDS = 0.35
FAST_STROKE_SPEED = 900.0
# Un trazo rápido se endereza si no se separa de la recta inicio→fin más que
# esta fracción de su longitud (un gesto rápido y torcido sigue a mano alzada).
FAST_STROKE_DEVIATION = 0.18
# Un trazo lento solo se endereza si ya es prácticamente una recta (temblor
# del pulso): desviación máxima de SLOW_STROKE_TOLERANCE pt o de esta fracción.
SLOW_STROKE_TOLERANCE = 2.0
SLOW_STROKE_DEVIATION = 0.04
# Ángulo (grados) bajo el cual una recta se ajusta a horizontal o vertical.
AXIS_SNAP_DEGREES = 8.0


def _path_length(pts: list[fitz.Point]) -> float:
    return sum(math.hypot(b.x - a.x, b.y - a.y) for a, b in zip(pts, pts[1:]))


def _max_deviation(pts: list[fitz.Point]) -> float:
    """Distancia máxima de los puntos a la recta que une el primero y el último."""
    a, b = pts[0], pts[-1]
    dx, dy = b.x - a.x, b.y - a.y
    largo = math.hypot(dx, dy)
    if largo == 0:
        return max(math.hypot(p.x - a.x, p.y - a.y) for p in pts)
    return max(abs(dy * (p.x - a.x) - dx * (p.y - a.y)) / largo for p in pts)


def _snap_to_axis(a: fitz.Point, b: fitz.Point) -> list[fitz.Point]:
    angulo = abs(math.degrees(math.atan2(b.y - a.y, b.x - a.x))) % 180
    if min(angulo, 180 - angulo) <= AXIS_SNAP_DEGREES:
        y = (a.y + b.y) / 2
        return [fitz.Point(a.x, y), fitz.Point(b.x, y)]
    if abs(angulo - 90) <= AXIS_SNAP_DEGREES:
        x = (a.x + b.x) / 2
        return [fitz.Point(x, a.y), fitz.Point(x, b.y)]
    return [fitz.Point(a), fitz.Point(b)]


def straighten_stroke(pts: list[fitz.Point], seconds: float,
                      scale: float = 1.0) -> list[fitz.Point]:
    """(r59) Endereza un trazo a mano alzada.

    Un movimiento **rápido** y más o menos recto se convierte en una recta del
    punto inicial al final, y si está casi horizontal o vertical se ajusta al
    eje: al pasar deprisa el ratón la mano tiembla y el trazo sale ondulado,
    pero lo que se quería era una línea. Un trazo lento (o rápido pero
    claramente curvo, como un círculo) se respeta tal cual, salvo que ya sea
    prácticamente una recta (solo el temblor del pulso).
    `pts` en puntos PDF; `scale` = píxeles de pantalla por punto PDF."""
    if len(pts) < 2:
        return pts
    a, b = pts[0], pts[-1]
    cuerda = math.hypot(b.x - a.x, b.y - a.y)
    if cuerda > 0:
        velocidad = _path_length(pts) * scale / max(seconds, 1e-3)
        rapido = seconds <= FAST_STROKE_SECONDS or velocidad >= FAST_STROKE_SPEED
        desvio = _max_deviation(pts)
        if rapido and desvio <= FAST_STROKE_DEVIATION * cuerda:
            return _snap_to_axis(a, b)
        if desvio <= max(SLOW_STROKE_TOLERANCE, SLOW_STROKE_DEVIATION * cuerda):
            return _snap_to_axis(a, b)
    return pts


def squiggle(pts: list[fitz.Point], width: float) -> list[fitz.Point]:
    """(r59) Línea ondulada que sigue el trazo: zigzag perpendicular cada medio
    periodo, con amplitud y periodo proporcionales al grosor."""
    amp = max(1.0, width * 0.9)
    paso = max(2.0, width * 2.0)
    total = _path_length(pts)
    if total < paso:
        return pts
    out: list[fitz.Point] = []
    tramo, recorrido, signo = 0, 0.0, 1
    d = 0.0
    while d <= total:
        while tramo < len(pts) - 2 and recorrido + math.hypot(
                pts[tramo + 1].x - pts[tramo].x, pts[tramo + 1].y - pts[tramo].y) < d:
            recorrido += math.hypot(pts[tramo + 1].x - pts[tramo].x,
                                    pts[tramo + 1].y - pts[tramo].y)
            tramo += 1
        a, b = pts[tramo], pts[tramo + 1]
        largo = math.hypot(b.x - a.x, b.y - a.y) or 1.0
        t = min(1.0, max(0.0, (d - recorrido) / largo))
        ux, uy = (b.x - a.x) / largo, (b.y - a.y) / largo
        out.append(fitz.Point(a.x + ux * t * largo - uy * amp * signo,
                              a.y + uy * t * largo + ux * amp * signo))
        signo = -signo
        d += paso
    return out
    xs = [p.x for p in pts]
    ys = [p.y for p in pts]
    rx = max(xs) - min(xs)
    ry = max(ys) - min(ys)
    total = rx + ry
    if total < 2:
        return pts
    sx = statistics.pstdev(xs)
    sy = statistics.pstdev(ys)
    threshold = 0.12
    start, end = pts[0], pts[-1]
    if sx < total * threshold:
        mx = (start.x + end.x) / 2
        return [fitz.Point(mx, start.y), fitz.Point(mx, end.y)]
    if sy < total * threshold:
        my = (start.y + end.y) / 2
        return [fitz.Point(start.x, my), fitz.Point(end.x, my)]
    return pts
