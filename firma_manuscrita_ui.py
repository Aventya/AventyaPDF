"""
Diálogo de la firma manuscrita (r68): pestaña «Dibujar» (a mano alzada con el
ratón, con color y grosor de la tinta) y pestaña «Imagen» (una firma escaneada
o fotografiada, quitando el fondo blanco). Devuelve una
`firma_manuscrita.HandSignature`; la ventana principal la coloca en la página.

La última firma dibujada, su color y su grosor se recuerdan en QSettings
(`firma/…`), como el certificado: se vuelve a firmar sin redibujarla.
"""
from __future__ import annotations

import json
import time

from PyQt6.QtCore import QBuffer, QIODevice, QPointF, QSettings, Qt
from PyQt6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout, QLabel,
    QPushButton, QSpinBox, QTabWidget, QVBoxLayout, QWidget,
)

import firma_manuscrita as fm
from dialogs import ColorButton

_SETTINGS = ("aventyapdf", "config")
IMAGE_FILTER = "Imágenes (*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff *.webp)"
MAX_IMAGE_SIDE = 1600          # px: una firma no necesita más
BG_OPAQUE, BG_CLEAR = 170, 235  # luminancia: ≤ opaca, ≥ fondo transparente


# ── Pintar la tinta con Qt (misma geometría que el PDF) ──────────────────── #

def piece_path(pz) -> QPainterPath:
    circulos, poligonos = fm.piece_shapes(pz)
    path = QPainterPath()
    path.setFillRule(Qt.FillRule.WindingFill)
    for c in circulos:
        seg = fm.circle_segments(*c)
        path.moveTo(*seg[0])
        for c1, c2, e in seg[1:]:
            path.cubicTo(QPointF(*c1), QPointF(*c2), QPointF(*e))
        path.closeSubpath()
    for poly in poligonos:
        path.moveTo(*poly[0])
        for x, y in poly[1:]:
            path.lineTo(x, y)
        path.closeSubpath()
    return path


def paint_ink(p: QPainter, pieces, color, alpha: float = fm.INK_ALPHA) -> None:
    """Cada pieza, un relleno translúcido: los cruces se oscurecen."""
    r, g, b = (int(round(max(0.0, min(1.0, c)) * 255)) for c in color[:3])
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(r, g, b, int(round(alpha * 255))))
    for pz in pieces:
        p.drawPath(piece_path(pz))
    p.restore()


def preview_image(sig: fm.HandSignature, max_w: int = 480) -> QImage:
    """Imagen con transparencia de la firma, para la vista previa al colocarla."""
    if sig.is_image:
        img = QImage.fromData(sig.png)
        return img.scaledToWidth(min(max_w, img.width()),
                                 Qt.TransformationMode.SmoothTransformation)
    caja = sig.bounds()
    esc = min(2.0, max_w / max(1.0, caja.width))
    img = QImage(max(1, int(caja.width * esc)), max(1, int(caja.height * esc)),
                 QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.scale(esc, esc)
    p.translate(-caja.x0, -caja.y0)
    paint_ink(p, sig.pieces(), sig.color)
    p.end()
    return img


# ── Imagen cargada ───────────────────────────────────────────────────────── #

def _png_bytes(img: QImage) -> bytes:
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    return bytes(buf.data())


def load_signature_image(path: str, remove_background: bool = True) -> QImage:
    """Abre la imagen, la reduce si es enorme y, si se pide, vuelve
    transparente el papel (claro) con un degradado suave hacia la tinta, y
    recorta lo que sobra alrededor. Lanza ValueError si no es una imagen."""
    img = QImage(path)
    if img.isNull():
        raise ValueError("No se pudo leer la imagen (¿formato no admitido?).")
    if max(img.width(), img.height()) > MAX_IMAGE_SIDE:
        img = img.scaled(MAX_IMAGE_SIDE, MAX_IMAGE_SIDE, Qt.AspectRatioMode.KeepAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)
    img = img.convertToFormat(QImage.Format.Format_ARGB32)
    if not remove_background:
        return img
    import numpy as np          # perezoso: numpy pesa en memoria (r67)
    w, h = img.width(), img.height()
    ptr = img.bits()
    ptr.setsize(img.sizeInBytes())
    px = np.frombuffer(ptr, np.uint8).reshape(h, img.bytesPerLine() // 4, 4)[:, :w].copy()
    b, g, r, a = (px[..., i].astype(np.float32) for i in range(4))   # BGRA
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    tinta = np.clip((BG_CLEAR - lum) / (BG_CLEAR - BG_OPAQUE), 0.0, 1.0)
    px[..., 3] = (tinta * a).astype(np.uint8)
    ys, xs = np.nonzero(px[..., 3] > 12)
    if len(xs) == 0:
        raise ValueError("La imagen parece estar en blanco: no se ha encontrado tinta.")
    m = 4
    x0, x1 = max(0, xs.min() - m), min(w, xs.max() + 1 + m)
    y0, y1 = max(0, ys.min() - m), min(h, ys.max() + 1 + m)
    recorte = np.ascontiguousarray(px[y0:y1, x0:x1])
    out = QImage(recorte.data, x1 - x0, y1 - y0, (x1 - x0) * 4, QImage.Format.Format_ARGB32)
    return out.copy()            # copia: `recorte` deja de existir al salir


# ── Lienzo para firmar con el ratón ──────────────────────────────────────── #

class SignatureCanvas(QWidget):
    """Papel en el que se firma. Guarda los trazos con su tiempo (la velocidad
    decide el grosor) y los pinta con la misma geometría que el PDF."""

    W, H = 640, 220

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(self.W, self.H)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.strokes: list[list[tuple]] = []
        self.width = fm.DEFAULT_WIDTH
        self.color = fm.DEFAULT_COLOR
        self._pieces: list = []        # tinta de los trazos terminados
        self._live: list = []          # tinta del trazo en curso
        self._t0 = 0.0
        self._drawing = False
        self.on_change = None

    def set_strokes(self, strokes) -> None:
        self.strokes = [list(map(tuple, s)) for s in strokes]
        self._rebuild()

    def set_pen(self, width: float | None = None, color=None) -> None:
        if width is not None:
            self.width = width
        if color is not None:
            self.color = tuple(color)
        self._rebuild()

    def clear(self) -> None:
        self.strokes = []
        self._rebuild()

    def undo_stroke(self) -> None:
        if self.strokes:
            self.strokes.pop()
            self._rebuild()

    def _rebuild(self) -> None:
        self._pieces = fm.ink_pieces(self.strokes, self.width)
        self._live = []
        self.update()
        if self.on_change:
            self.on_change()

    def _pt(self, event) -> tuple:
        pos = event.position()
        return (pos.x(), pos.y(), time.monotonic() - self._t0)

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if not self.strokes:
            self._t0 = time.monotonic()
        self._drawing = True
        self.strokes.append([self._pt(event)])
        self._live = fm.ink_pieces(self.strokes[-1:], self.width)
        self.update()

    def mouseMoveEvent(self, event):
        if not self._drawing:
            return
        self.strokes[-1].append(self._pt(event))
        self._live = fm.ink_pieces(self.strokes[-1:], self.width)
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or not self._drawing:
            return
        self._drawing = False
        self.strokes[-1].append(self._pt(event))
        self._rebuild()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#FFFFFF"))
        p.setPen(QPen(QColor("#D2D0CE"), 1))
        p.drawRect(self.rect().adjusted(0, 0, -1, -1))
        # Línea de firma, como en un impreso.
        y = int(self.H * 0.72)
        p.setPen(QPen(QColor("#C8C6C4"), 1, Qt.PenStyle.DashLine))
        p.drawLine(28, y, self.W - 28, y)
        p.setPen(QColor("#A19F9D"))
        p.drawText(12, y + 5, "×")
        if not self.strokes:
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       "Firma aquí con el ratón")
        paint_ink(p, self._pieces + self._live, self.color)
        p.end()


# ── Diálogo ──────────────────────────────────────────────────────────────── #

class HandSignatureDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Firma manuscrita")
        self._image: QImage | None = None
        s = QSettings(*_SETTINGS)

        lay = QVBoxLayout(self)
        self._tabs = QTabWidget()
        lay.addWidget(self._tabs)

        # Pestaña Dibujar
        dib = QWidget()
        dl = QVBoxLayout(dib)
        self.canvas = SignatureCanvas()
        dl.addWidget(self.canvas)
        fila = QHBoxLayout()
        fila.addWidget(QLabel("Color de la tinta:"))
        color = s.value("firma/color", "")
        try:
            color = tuple(float(c) for c in json.loads(color)) if color else fm.DEFAULT_COLOR
        except (TypeError, ValueError):
            color = fm.DEFAULT_COLOR
        self._color_btn = ColorButton(color, titulo="Color de la tinta")
        self._color_btn.clicked.connect(self._on_pen)   # después de elegir el color
        fila.addWidget(self._color_btn)
        fila.addSpacing(16)
        fila.addWidget(QLabel("Grosor de la plumilla:"))
        self._width_spin = QSpinBox()
        self._width_spin.setRange(*fm.WIDTHS)
        self._width_spin.setSuffix(" px")
        try:
            self._width_spin.setValue(int(s.value("firma/grosor", fm.DEFAULT_WIDTH)))
        except (TypeError, ValueError):
            self._width_spin.setValue(fm.DEFAULT_WIDTH)
        self._width_spin.valueChanged.connect(self._on_pen)
        fila.addWidget(self._width_spin)
        fila.addStretch()
        b_undo = QPushButton("Deshacer trazo")
        b_undo.clicked.connect(self.canvas.undo_stroke)
        fila.addWidget(b_undo)
        b_clear = QPushButton("Borrar")
        b_clear.clicked.connect(self.canvas.clear)
        fila.addWidget(b_clear)
        dl.addLayout(fila)
        self._tabs.addTab(dib, "Dibujar")

        # Pestaña Imagen
        im = QWidget()
        il = QVBoxLayout(im)
        self._img_lbl = QLabel("Carga la imagen de una firma escaneada o fotografiada")
        self._img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._img_lbl.setFixedSize(SignatureCanvas.W, SignatureCanvas.H)
        self._img_lbl.setStyleSheet("background:#FFFFFF; border:1px solid #D2D0CE; color:#A19F9D;")
        il.addWidget(self._img_lbl)
        fila = QHBoxLayout()
        b_load = QPushButton("Cargar imagen…")
        b_load.clicked.connect(self._load_image)
        fila.addWidget(b_load)
        self._bg_chk = QCheckBox("Quitar el fondo blanco del papel")
        self._bg_chk.setChecked(True)
        self._bg_chk.toggled.connect(self._reload_image)
        fila.addWidget(self._bg_chk)
        fila.addStretch()
        il.addLayout(fila)
        self._tabs.addTab(im, "Imagen")
        self._img_path = ""

        lay.addWidget(QLabel("Al aceptar, haz clic en la página donde irá la firma "
                             "(o arrastra un recuadro para darle tamaño)."))
        self._bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                    | QDialogButtonBox.StandardButton.Cancel)
        self._bb.button(QDialogButtonBox.StandardButton.Ok).setText("Colocar en la página")
        self._bb.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        self._bb.accepted.connect(self.accept)
        self._bb.rejected.connect(self.reject)
        lay.addWidget(self._bb)

        self.canvas.set_pen(self._width_spin.value(), self._color_btn.color)
        try:
            self.canvas.set_strokes(json.loads(s.value("firma/trazos", "") or "[]"))
        except (TypeError, ValueError):
            pass
        self.canvas.on_change = self._update_ok
        self._tabs.setCurrentIndex(1 if s.value("firma/pestana", "") == "imagen" else 0)
        self._tabs.currentChanged.connect(self._update_ok)
        self._update_ok()

    def _on_pen(self, *_):
        self.canvas.set_pen(self._width_spin.value(), self._color_btn.color)

    def _drawing_tab(self) -> bool:
        return self._tabs.currentIndex() == 0

    def _update_ok(self, *_):
        listo = any(self.canvas.strokes) if self._drawing_tab() else self._image is not None
        self._bb.button(QDialogButtonBox.StandardButton.Ok).setEnabled(listo)

    def _load_image(self):
        ruta, _ = QFileDialog.getOpenFileName(self, "Imagen de la firma", "", IMAGE_FILTER)
        if ruta:
            self._img_path = ruta
            self._reload_image()

    def _reload_image(self, *_):
        if not self._img_path:
            return
        try:
            self._image = load_signature_image(self._img_path, self._bg_chk.isChecked())
        except ValueError as e:
            self._image = None
            self._img_lbl.setPixmap(QPixmap())
            self._img_lbl.setText(str(e))
        else:
            vista = self._image.scaled(self._img_lbl.width() - 16, self._img_lbl.height() - 16,
                                       Qt.AspectRatioMode.KeepAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation)
            self._img_lbl.setPixmap(QPixmap.fromImage(vista))
        self._update_ok()

    def signature(self) -> fm.HandSignature:
        if self._drawing_tab():
            return fm.HandSignature(strokes=[list(s) for s in self.canvas.strokes],
                                    width=self.canvas.width, color=self.canvas.color)
        return fm.HandSignature(png=_png_bytes(self._image),
                                png_size=(self._image.width(), self._image.height()))

    def accept(self):
        s = QSettings(*_SETTINGS)
        s.setValue("firma/color", json.dumps(list(self._color_btn.color)))
        s.setValue("firma/grosor", self._width_spin.value())
        s.setValue("firma/pestana", "dibujar" if self._drawing_tab() else "imagen")
        if self._drawing_tab():
            trazos = [[[round(x, 1), round(y, 1), round(t, 3)] for x, y, t in st]
                      for st in self.canvas.strokes]
            s.setValue("firma/trazos", json.dumps(trazos))
        super().accept()


def ask_hand_signature(parent) -> fm.HandSignature | None:
    dlg = HandSignatureDialog(parent)
    if not dlg.exec():
        return None
    sig = dlg.signature()
    return None if sig.is_empty() else sig
