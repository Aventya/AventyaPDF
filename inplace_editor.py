"""
inplace_editor.py
Editor de texto que se dibuja **sobre la propia página**, en el sitio exacto
donde va a quedar el texto.

Regla del proyecto (petición de Ricardo, r23): **ninguna entrada de texto que
acabe dentro del PDF abre una ventana aparte**. Lo usan la herramienta Texto,
las notas adhesivas, la edición de una anotación existente y «Editar contenido».

Teclas, iguales en todos los sitios:
  Intro        línea nueva
  Ctrl+Intro   confirmar
  Esc          cancelar
  Tab / Mayús+Tab   confirmar y pasar al siguiente / anterior

Aviso: el `QShortcut` de Esc de la ventana principal se queda la tecla **antes**
de que llegue aquí (los atajos se procesan antes que los eventos de teclado), así
que `MainWindow._on_escape` tiene que cancelar el editor abierto él mismo
(invariante 41).
"""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QTextOption
from PyQt6.QtWidgets import QPlainTextEdit

# Alineación de `PDFUtils` (0=izquierda 1=centro 2=derecha 3=justificado).
_ALIGN = {
    0: Qt.AlignmentFlag.AlignLeft,
    1: Qt.AlignmentFlag.AlignHCenter,
    2: Qt.AlignmentFlag.AlignRight,
    3: Qt.AlignmentFlag.AlignJustify,
}
ALIGN_INDEX = {"left": 0, "center": 1, "right": 2, "justify": 3}

MARGIN = 2          # margen interior del documento, en píxeles
BORDER = 1          # grosor del borde, en píxeles


def _hex(color) -> str:
    r, g, b = (max(0, min(255, int(round(c * 255)))) for c in color[:3])
    return f"#{r:02X}{g:02X}{b:02X}"


class InPlaceEditor(QPlainTextEdit):
    """Cuadro de escritura colocado encima de la página.

    Emite `committed(texto)` al confirmar, `cancelled()` al cancelar y
    `moved(+1/-1)` con Tab. Quien lo crea decide qué hacer con el texto."""

    committed = pyqtSignal(str)
    cancelled = pyqtSignal()
    moved = pyqtSignal(int)

    def __init__(self, parent, rect, *, border=(0.0, 0.47, 0.83),
                 background=(1.0, 1.0, 1.0)):
        super().__init__(parent)
        self._done = False
        self._border, self._background = _hex(border), _hex(background)
        self._color = "#201F1E"
        self._font_css = ""
        self.document().setDocumentMargin(MARGIN)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setGeometry(rect)
        self._restyle()

    # ── aspecto ────────────────────────────────────────────────────────── #

    def apply_style(self, *, family="Arial", pixel_size=14, bold=False,
                    italic=False, color=(0, 0, 0), align=0) -> None:
        """Deja el editor con la pinta que tendrá el texto en el PDF, para que
        lo que se escribe sea lo que se ve."""
        f = QFont(family)
        f.setPixelSize(max(8, int(round(pixel_size))))
        f.setBold(bool(bold))
        f.setItalic(bool(italic))
        self.setFont(f)
        # (r69) La hoja de estilos global (main.STYLESHEET, regla QWidget) fija
        # familia y tamaño y manda sobre setFont(): sin repetirlos aquí se
        # escribía con Segoe UI a 13 px y la fuente elegida solo aparecía al
        # confirmar. Invariante 55.
        self._font_css = (f"font-family:'{family}'; font-size:{f.pixelSize()}px;"
                          f" font-weight:{700 if bold else 400};"
                          f" font-style:{'italic' if italic else 'normal'};")
        opt = QTextOption(_ALIGN.get(align, _ALIGN[0]))
        opt.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        self.document().setDefaultTextOption(opt)
        self._color = _hex(color)
        self._restyle()

    def _restyle(self) -> None:
        self.setStyleSheet(
            f"QPlainTextEdit {{ background:{self._background}; color:{self._color};"
            f" {self._font_css}"
            f" border:{BORDER}px solid {self._border}; border-radius:0; padding:0; }}")

    def needed_height(self) -> float:
        """Alto en píxeles que necesita el texto tal y como está repartido.

        Ojo: en `QPlainTextEdit` el alto de `documentSize()` viene en **líneas**,
        no en píxeles (al revés que en `QTextEdit`), y solo cuenta bien una vez
        que el widget está realizado y sabe su ancho. Tomarlo por píxeles hacía
        que el cuadro no creciera y se escribiera a ciegas."""
        lineas = max(1.0, self.document().documentLayout().documentSize().height())
        return lineas * self.fontMetrics().lineSpacing() + 2 * MARGIN + 2 * BORDER + 2

    def enable_autogrow(self, max_bottom: int) -> None:
        """El cuadro crece (y mengua) al escribir, sin pasar de `max_bottom`.

        Sin esto el texto se recorta en cuanto pasa de una línea y se escribe a
        ciegas. No lo usa «Editar contenido»: allí el alto lo manda el usuario
        estirando la esquina."""
        self._min_height = self.height()
        self._max_bottom = int(max_bottom)
        self.textChanged.connect(self._grow)
        self._grow()

    def _grow(self) -> None:
        g = self.geometry()
        tope = max(self._min_height, self._max_bottom - g.top())
        alto = max(self._min_height, min(int(round(self.needed_height())), tope))
        if alto != g.height():
            self.setGeometry(g.x(), g.y(), g.width(), alto)

    # ── teclado y foco ─────────────────────────────────────────────────── #

    def keyPressEvent(self, event):
        key = event.key()
        mods = event.modifiers()
        if key == Qt.Key.Key_Escape:
            self.cancel()
            return
        if key in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
            atras = key == Qt.Key.Key_Backtab or bool(
                mods & Qt.KeyboardModifier.ShiftModifier)
            self.moved.emit(-1 if atras else 1)
            return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and \
                mods & Qt.KeyboardModifier.ControlModifier:
            self.commit()
            return
        super().keyPressEvent(event)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        self.commit()

    # ── fin ────────────────────────────────────────────────────────────── #

    def commit(self) -> None:
        if self._done:
            return
        self._done = True
        self.committed.emit(self.toPlainText())

    def cancel(self) -> None:
        if self._done:
            return
        self._done = True
        self.cancelled.emit()

    def finish(self) -> None:
        """Lo retira quien lo creó, sin disparar nada más."""
        self._done = True
        self.hide()
        self.deleteLater()
