"""
Selector de color único de la aplicación (r41).

Todos los colores (texto, nota, marcado, marcador, rectángulo, emoji, marca de
agua…) se eligen en esta misma tabla de 19 colores, y las herramientas que
admiten transparencia enseñan además su control de opacidad en el mismo cuadro.
Antes cada botón abría el selector de Windows (`QColorDialog`), con millones de
colores y sin transparencia.

La tabla es fija —los 19 colores de la paleta de Ricardo, con sus nombres— y se
dibuja con círculos de `SWATCH` píxeles, en columnas de `ROWS` colores (el
botón que la abre sigue siendo un cuadrado).

(petición de Ricardo) No es una ventana aparte: se abre como un menú emergente
en la posición del cursor, al pulsar el selector de color. Un clic en un color
lo elige y cierra el menú (con la opacidad que marque su control, si lo hay);
Esc o un clic fuera lo cierran sin cambiar nada.
"""
from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QColor, QCursor, QGuiApplication
from PyQt6.QtWidgets import (
    QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QSlider, QVBoxLayout,
)

import icons
from idioma import tr

# Los 17 colores de la paleta de Ricardo («Paleta Cromática de Transición de
# Luces»), en su mismo orden, más (petición de Ricardo) dos grises junto al
# gris: uno claro a mitad de camino del blanco ((255 + 170) / 2 = 212,5 → D5)
# y otro oscuro a mitad de camino del negro (170 / 2 = 85 → 55), de más claro
# a más oscuro. Se leen por columnas de 4. Esta lista es la única fuente de
# verdad: la tabla original en HTML de la que salieron ya no está en el proyecto.
PALETTE = [                                  # una línea = una columna
    "#FFFFFF", "#D5D5D5", "#AAAAAA", "#555555",
    "#000000", "#AA0000", "#FF0000", "#FFAA00",
    "#FFFF00", "#FFFFAA", "#AAFF00", "#00FF00",
    "#00FFAA", "#AAFFFF", "#00AAFF", "#0000FF",
    "#AA00FF", "#FF00FF", "#FFAAFF",
]
ROWS = 4             # (petición de Ricardo) colores por columna
SWATCH = icons.CONTROL   # lado del recuadro de color: 32 px, como todo botón

# Nombre de cada color, tal y como los bautizó Ricardo (sale en la ayuda del
# recuadro). El último era otro «Magenta puro» en la tabla original; aquí se
# llama «Magenta claro» para no repetir nombre.
_NOMBRES = {
    "#FFFFFF": tr("Blanco puro"), "#D5D5D5": tr("Gris claro"), "#AAAAAA": tr("Gris"),
    "#555555": tr("Gris oscuro"), "#000000": tr("Negro absoluto"),
    "#AA0000": tr("Rojo oscuro"), "#FF0000": tr("Rojo puro"), "#FFAA00": tr("Ámbar brillante"),
    "#FFFF00": tr("Amarillo puro"), "#FFFFAA": tr("Amarillo claro"), "#AAFF00": tr("Verde lima"),
    "#00FF00": tr("Verde puro"), "#00FFAA": tr("Turquesa brillante"), "#AAFFFF": tr("Cian claro"),
    "#00AAFF": tr("Azul eléctrico"), "#0000FF": tr("Azul puro"), "#AA00FF": tr("Púrpura vibrante"),
    "#FF00FF": tr("Magenta puro"), "#FFAAFF": tr("Magenta claro"),
}


def to_rgb(hex_color: str) -> tuple:
    c = QColor(hex_color)
    return (c.redF(), c.greenF(), c.blueF())


def nearest(color) -> str:
    """El color de la tabla más parecido a `color` (RGB 0-1), para marcarlo."""
    r, g, b = (max(0.0, min(1.0, c)) * 255 for c in color[:3])
    return min(PALETTE, key=lambda h: sum((a - b) ** 2 for a, b in zip(
        (QColor(h).red(), QColor(h).green(), QColor(h).blue()), (r, g, b))))


class ColorDialog(QDialog):
    """Tabla de colores y, si la herramienta lo admite, opacidad; se muestra
    como menú emergente (`Qt.WindowType.Popup`), sin barra de título."""

    def __init__(self, parent, color=(0, 0, 0), opacity: float | None = None,
                 title: str | None = None):
        title = title or tr("Color")
        super().__init__(parent, Qt.WindowType.Popup)
        self.setWindowTitle(title)           # no se ve; lo usan los lectores de pantalla
        self.setAccessibleName(title)
        self._color = to_rgb(nearest(color))
        self._opacity = opacity
        fuera = QVBoxLayout(self)
        fuera.setContentsMargins(0, 0, 0, 0)
        # Marco con borde y fondo de menú (#color_popup en main.STYLESHEET).
        marco = QFrame()
        marco.setObjectName("color_popup")
        fuera.addWidget(marco)
        lay = QVBoxLayout(marco)
        lay.setContentsMargins(8, 8, 8, 8)
        lay.setSpacing(8)

        rejilla = QGridLayout()
        rejilla.setSpacing(3)
        elegido = nearest(color)
        self._botones = {}
        for i, hex_color in enumerate(PALETTE):
            b = QPushButton()
            b.setObjectName("swatch")
            b.setFixedSize(SWATCH, SWATCH)
            b.setCheckable(True)
            b.setChecked(hex_color == elegido)
            b.setToolTip(f"{_NOMBRES.get(hex_color, '')}  {hex_color}".strip())
            # min/max son el contenido: SWATCH menos el borde (1 px, o 2 px
            # cuando está marcado), para que el recuadro mida siempre SWATCH.
            # (petición de Ricardo) Círculos: radio = medio lado.
            b.setStyleSheet(
                f"QPushButton#swatch {{ background: {hex_color}; border: 1px solid #8A8886;"
                f" border-radius: {SWATCH // 2}px; padding: 0; min-width: {SWATCH - 2}px;"
                f" max-width: {SWATCH - 2}px; min-height: {SWATCH - 2}px;"
                f" max-height: {SWATCH - 2}px; }}"
                f"QPushButton#swatch:checked {{ border: 2px solid #0078D4;"
                f" min-width: {SWATCH - 4}px; max-width: {SWATCH - 4}px;"
                f" min-height: {SWATCH - 4}px; max-height: {SWATCH - 4}px; }}")
            b.clicked.connect(lambda _c=False, h=hex_color: self._pick(h))
            rejilla.addWidget(b, i % ROWS, i // ROWS)     # por columnas
            self._botones[hex_color] = b
        lay.addLayout(rejilla)
        # Centrada: si la fila de opacidad pide algo más de ancho, el margen
        # sobrante queda repartido a los dos lados.
        lay.setAlignment(rejilla, Qt.AlignmentFlag.AlignHCenter)

        if opacity is not None:
            fila = QHBoxLayout()
            fila.addWidget(QLabel(tr("Opacidad")))
            self._slider = QSlider(Qt.Orientation.Horizontal)
            self._slider.setRange(5, 100)
            # Que se estreche hasta el ancho de la paleta, sin ensanchar el menú.
            self._slider.setSizePolicy(QSizePolicy.Policy.Ignored,
                                       self._slider.sizePolicy().verticalPolicy())
            self._slider.setMinimumWidth(24)
            self._slider.setValue(int(round(max(0.05, min(1.0, opacity)) * 100)))
            self._lbl = QLabel(f"{self._slider.value()} %")
            self._lbl.setMinimumWidth(36)
            self._lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._slider.valueChanged.connect(lambda v: self._lbl.setText(f"{v} %"))
            fila.addWidget(self._slider, 1)
            fila.addWidget(self._lbl)
            lay.addLayout(fila)

    def _pick(self, hex_color: str) -> None:
        """Como en un menú: el clic elige el color y cierra. Para cambiar solo
        la opacidad, se mueve su control y se pulsa el color ya marcado."""
        self._color = to_rgb(hex_color)
        for h, b in self._botones.items():
            b.setChecked(h == hex_color)
        self.accept()

    def popup_at(self, pos: QPoint) -> None:
        """Coloca el menú con su esquina superior izquierda en `pos` (el
        cursor), metiéndolo dentro de la pantalla si no cabe, como un menú."""
        self.adjustSize()
        size = self.sizeHint()
        screen = QGuiApplication.screenAt(pos) or QGuiApplication.primaryScreen()
        area = screen.availableGeometry()
        x, y = pos.x(), pos.y()
        if x + size.width() > area.right() + 1:      # no cabe: a la izquierda
            x -= size.width()
        if y + size.height() > area.bottom() + 1:    # no cabe: hacia arriba
            y -= size.height()
        x = max(area.left(), min(x, area.right() + 1 - size.width()))
        y = max(area.top(), min(y, area.bottom() + 1 - size.height()))
        self.move(x, y)

    def values(self) -> tuple:
        """(color RGB 0-1, opacidad 0-1 o None)."""
        op = None if self._opacity is None else self._slider.value() / 100
        return self._color, op


def choose(parent, color=(0, 0, 0), opacity: float | None = None,
           title: str | None = None) -> tuple | None:
    """Abre la tabla en el cursor; devuelve (color, opacidad) o None si se
    cierra sin elegir."""
    dlg = ColorDialog(parent, color, opacity, title)
    dlg.popup_at(QCursor.pos())
    if not dlg.exec():
        return None
    return dlg.values()
