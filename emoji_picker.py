"""
Selector de emojis del panel «Insertar emoji» (r36; fuente Noto Emoji desde r40).

Buscador (en español o en inglés, sin importar tildes), filtro por grupo y una
cuadrícula con cada emoji dibujado con la propia fuente Noto Emoji, en el color
elegido, tal y como quedará en el PDF. Los dibujos se generan poco a poco con un
temporizador (hay ~1.400), empezando por los visibles, y se guardan en caché.

La cuadrícula no se rellena hasta que el panel se muestra por primera vez:
rellenada mientras estaba oculta, Qt no la distribuía y salía en blanco.
"""
from PyQt6.QtCore import QRectF, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon, QImage, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView, QComboBox, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QSizePolicy, QVBoxLayout, QWidget,
)

import emoji_font
import icons

ICON_PX = 28
_ROLE = Qt.ItemDataRole.UserRole


class EmojiPicker(QWidget):
    emojiChosen = pyqtSignal(str)
    BATCH = 60

    def __init__(self, parent=None):
        super().__init__(parent)
        icons.load_fonts()
        # El selector no debe ensanchar el panel lateral: sus etiquetas fijas se
        # cortarían (invariante 46). Se adapta al ancho que le den.
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar emoji…")
        self.search.setClearButtonEnabled(True)
        self.search.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.search.textChanged.connect(lambda _t: self._refill())
        lay.addWidget(self.search)
        self.group = QComboBox()
        self.group.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.group.addItem("Todos los grupos", "")
        self.list = QListWidget()
        self.list.setObjectName("emoji_grid")
        self.list.setViewMode(QListWidget.ViewMode.IconMode)
        self.list.setFlow(QListWidget.Flow.LeftToRight)
        self.list.setWrapping(True)
        self.list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.list.setMovement(QListWidget.Movement.Static)
        self.list.setUniformItemSizes(True)
        self.list.setIconSize(QSize(ICON_PX, ICON_PX))
        self.list.setGridSize(QSize(ICON_PX + 8, ICON_PX + 8))
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.setMinimumHeight(220)
        self.list.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self.list.itemClicked.connect(self._clicked)
        self.list.verticalScrollBar().valueChanged.connect(lambda _v: self._prioritize())
        self._count = QLabel("")
        self._count.setObjectName("side_hint")
        self._count.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self._icons: dict[str, QIcon] = {}
        self._pending: list[QListWidgetItem] = []
        self._timer = QTimer(self)
        self._timer.setInterval(10)           # sin acaparar la CPU mientras se dibujan
        self._timer.timeout.connect(self._render_batch)
        self._current = emoji_font.DEFAULT
        self._color = QColor(*[int(c * 255) for c in emoji_font.DEFAULT_COLOR])
        self.error = ""
        try:
            for g, nombre in emoji_font.groups():
                self.group.addItem(nombre, g)
        except emoji_font.EmojiFontError as e:
            self.error = str(e)
        self.group.currentIndexChanged.connect(lambda _i: self._refill())
        lay.addWidget(self.group)
        lay.addWidget(self.list, 1)
        lay.addWidget(self._count)
        self._filled = False
        # Icono provisional del mismo tamaño: con setUniformItemSizes Qt mide el
        # primer elemento, y sin icono toda la cuadrícula se distribuía a tamaño 0.
        vacio = QPixmap(ICON_PX, ICON_PX)
        vacio.fill(Qt.GlobalColor.transparent)
        self._placeholder = QIcon(vacio)

    def showEvent(self, event):
        super().showEvent(event)
        if not self._filled:
            self._filled = True
            QTimer.singleShot(0, self._refill)

    # ── contenido ─────────────────────────────────────────────────────── #

    def set_color(self, color) -> None:
        """Color con el que se dibujan los emojis de la cuadrícula: el mismo con
        el que se insertan (r40)."""
        nuevo = QColor(*[int(max(0.0, min(1.0, c)) * 255) for c in color[:3]])
        if nuevo == self._color:
            return
        self._color = nuevo
        self._icons.clear()
        if self._filled:
            self._refill()

    def _refill(self) -> None:
        self._filled = True
        self._timer.stop()
        self.list.clear()
        self._pending = []
        if self.error:
            self._count.setText(self.error)
            return
        items = emoji_font.search(self.search.text(), self.group.currentData() or "")
        for e in items:
            it = QListWidgetItem()
            it.setData(_ROLE, e["emoji"])
            it.setToolTip(f"{e['emoji']}  {e['label']}")
            icono = self._icons.get(e["key"])
            if icono is not None:
                it.setIcon(icono)
            else:
                it.setIcon(self._placeholder)
                self._pending.append(it)
            self.list.addItem(it)
            if e["key"] == emoji_font.emoji_key(self._current):
                it.setSelected(True)
        n = len(items)
        self._count.setText(f"{n} emoji{'s' if n != 1 else ''}" if n else "Ningún emoji coincide")
        if self._pending:
            self._timer.start()

    def _prioritize(self) -> None:
        """Lo que se ve en la cuadrícula se dibuja primero."""
        if not self._pending:
            return
        vista = self.list.viewport().rect()
        visibles = [it for it in self._pending
                    if self.list.visualItemRect(it).intersects(vista)]
        if visibles:
            resto = [it for it in self._pending if it not in visibles]
            self._pending = visibles + resto

    def _render_batch(self) -> None:
        self._prioritize()
        for _ in range(self.BATCH):
            if not self._pending:
                self._timer.stop()
                return
            it = self._pending.pop(0)
            try:
                texto = it.data(_ROLE)
            except RuntimeError:          # el elemento ya no existe (nueva búsqueda)
                continue
            key = emoji_font.emoji_key(texto)
            icono = self._icons.get(key)
            if icono is None:
                icono = QIcon(self._qpixmap(texto))
                self._icons[key] = icono
            it.setIcon(icono)

    def _qpixmap(self, texto: str) -> QPixmap:
        """El glifo de Noto Emoji en el color elegido."""
        ratio = max(1.0, self.devicePixelRatioF())
        px = int(round(ICON_PX * ratio))
        img = QImage(px, px, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(0)
        painter = QPainter(img)
        f = QFont(emoji_font.FONT_NAME)
        # Sin esto Qt sustituye los emojis por la fuente de color del sistema
        # (Segoe UI Emoji) y la cuadrícula no se parecería a lo que va al PDF.
        f.setStyleStrategy(QFont.StyleStrategy.NoFontMerging)
        f.setPixelSize(int(px * 0.82))
        painter.setFont(f)
        painter.setPen(self._color)
        painter.drawText(QRectF(0, 0, px, px), int(Qt.AlignmentFlag.AlignCenter),
                         emoji_font.emoji_key(texto))
        painter.end()
        qp = QPixmap.fromImage(img)
        qp.setDevicePixelRatio(ratio)
        return qp

    # ── selección ─────────────────────────────────────────────────────── #

    def _clicked(self, item: QListWidgetItem) -> None:
        texto = item.data(_ROLE)
        if texto:
            self._current = texto
            self.emojiChosen.emit(texto)

    def current(self) -> str:
        return self._current

    def set_current(self, texto: str) -> None:
        """Marca el emoji (sin emitir la señal)."""
        self._current = texto
        key = emoji_font.emoji_key(texto)
        self.list.clearSelection()
        for i in range(self.list.count()):
            it = self.list.item(i)
            if emoji_font.emoji_key(it.data(_ROLE)) == key:
                it.setSelected(True)
                self.list.scrollToItem(it)
                break
