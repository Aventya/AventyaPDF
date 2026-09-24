"""
Selector de color único de la aplicación (r41).

Todos los colores (texto, nota, marcado, marcador, rectángulo, emoji, marca de
agua…) se eligen en esta misma tabla de 17 colores, y las herramientas que
admiten transparencia enseñan además su control de opacidad en el mismo cuadro.
Antes cada botón abría el selector de Windows (`QColorDialog`), con millones de
colores y sin transparencia.

La tabla es fija —los 17 colores de la paleta de Ricardo, con sus nombres— y se
dibuja con recuadros de `SWATCH` píxeles, en dos filas de 9.
"""
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QDialog, QDialogButtonBox, QGridLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QVBoxLayout,
)

# Los 17 colores de la paleta de Ricardo («Paleta Cromática de Transición de
# Luces»), en su mismo orden: dos filas de 9. Esta lista es la única fuente de
# verdad: la tabla original en HTML de la que salieron ya no está en el proyecto.
PALETTE = [
    "#FFFFFF", "#AAAAAA", "#000000", "#AA0000", "#FF0000", "#FFAA00", "#FFFF00",
    "#FFFFAA", "#AAFF00", "#00FF00", "#00FFAA", "#AAFFFF", "#00AAFF", "#0000FF",
    "#AA00FF", "#FF00FF", "#FFAAFF",
]
COLUMNS = 9
SWATCH = 16          # lado del recuadro de color, en píxeles

# Nombre de cada color, tal y como los bautizó Ricardo (sale en la ayuda del
# recuadro). El último era otro «Magenta puro» en la tabla original; aquí se
# llama «Magenta claro» para no repetir nombre.
_NOMBRES = {
    "#FFFFFF": "Blanco puro", "#AAAAAA": "Gris", "#000000": "Negro absoluto",
    "#AA0000": "Rojo oscuro", "#FF0000": "Rojo puro", "#FFAA00": "Ámbar brillante",
    "#FFFF00": "Amarillo puro", "#FFFFAA": "Amarillo claro", "#AAFF00": "Verde lima",
    "#00FF00": "Verde puro", "#00FFAA": "Turquesa brillante", "#AAFFFF": "Cian claro",
    "#00AAFF": "Azul eléctrico", "#0000FF": "Azul puro", "#AA00FF": "Púrpura vibrante",
    "#FF00FF": "Magenta puro", "#FFAAFF": "Magenta claro",
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
    """Tabla de colores y, si la herramienta lo admite, opacidad."""

    def __init__(self, parent, color=(0, 0, 0), opacity: float | None = None,
                 title: str = "Color"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self._color = to_rgb(nearest(color))
        self._opacity = opacity
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)

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
            b.setStyleSheet(
                f"QPushButton#swatch {{ background: {hex_color}; border: 1px solid #8A8886;"
                " border-radius: 2px; min-width: 0; min-height: 0; padding: 0; }"
                "QPushButton#swatch:checked { border: 2px solid #0078D4; }")
            b.clicked.connect(lambda _c=False, h=hex_color: self._pick(h))
            rejilla.addWidget(b, i // COLUMNS, i % COLUMNS)
            self._botones[hex_color] = b
        lay.addLayout(rejilla)

        if opacity is not None:
            fila = QHBoxLayout()
            fila.addWidget(QLabel("Opacidad"))
            self._slider = QSlider(Qt.Orientation.Horizontal)
            self._slider.setRange(5, 100)
            self._slider.setValue(int(round(max(0.05, min(1.0, opacity)) * 100)))
            self._lbl = QLabel(f"{self._slider.value()} %")
            self._lbl.setMinimumWidth(40)
            self._slider.valueChanged.connect(lambda v: self._lbl.setText(f"{v} %"))
            fila.addWidget(self._slider, 1)
            fila.addWidget(self._lbl)
            lay.addLayout(fila)

        botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel)
        botones.button(QDialogButtonBox.StandardButton.Ok).setText("Aceptar")
        botones.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        botones.accepted.connect(self.accept)
        botones.rejected.connect(self.reject)
        lay.addWidget(botones)

    def _pick(self, hex_color: str) -> None:
        self._color = to_rgb(hex_color)
        for h, b in self._botones.items():
            b.setChecked(h == hex_color)
        if self._opacity is None:          # sin opacidad, un clic basta
            self.accept()

    def values(self) -> tuple:
        """(color RGB 0-1, opacidad 0-1 o None)."""
        op = None if self._opacity is None else self._slider.value() / 100
        return self._color, op


def choose(parent, color=(0, 0, 0), opacity: float | None = None,
           title: str = "Color") -> tuple | None:
    """Abre la tabla; devuelve (color, opacidad) o None si se cancela."""
    dlg = ColorDialog(parent, color, opacity, title)
    if not dlg.exec():
        return None
    return dlg.values()
