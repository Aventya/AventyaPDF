"""
Presentación inicial de AventyaPDF (r70).

Ventana sin marco que sale al arrancar y va explicando las características de
la aplicación, una tras otra, con el aspecto de la maqueta de Ricardo
(`popup_temp.png`): fondo en degradado turquesa → blanco → salmón, el icono,
el nombre en azul marino, una barra de progreso redondeada rematada con la
plumilla y el texto debajo. Aquí la barra no mide una carga: avanza sola por
las diapositivas (se para mientras el ratón está encima, para leer con calma)
y se puede ir adelante y atrás con los botones o con ← →.

«No volver a mostrar» guarda `inicio/presentacion = false` en QSettings; se
puede volver a ver (y reactivar) desde Ayuda › «Presentación de AventyaPDF».
El degradado se pinta en código: la PNG de la maqueta traía textos fijos
(«© 2024…») y pesaba 260 KB. (r71) El pie nombra al titular, Aventya Asesoría
Integral SL, y enlaza el repositorio público de GitHub (libre distribución).
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass

from PyQt6.QtCore import QPointF, QRectF, QSettings, Qt, QTimer
from PyQt6.QtGui import (
    QColor, QFont, QIcon, QLinearGradient, QPainter, QPainterPath, QPen,
    QRadialGradient,
)
from PyQt6.QtWidgets import (
    QCheckBox, QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

import icons

_SETTINGS = ("aventyapdf", "config")
KEY_SHOW = "inicio/presentacion"

SLIDE_MS = 7000          # tiempo de cada diapositiva
TICK_MS = 30
NAVY = "#17355E"
TEXT = "#4A5560"
W, H = 640, 510


@dataclass(frozen=True)
class Slide:
    icon: str            # nombre de Fluent UI System Icons (icons.glyph)
    title: str
    text: str


SLIDES: tuple[Slide, ...] = (
    Slide("document_pdf", "Bienvenido a AventyaPDF",
          "Ver, comentar, organizar, proteger, convertir y firmar PDF en una sola "
          "aplicación de libre distribución, con su código abierto en GitHub. Esta "
          "presentación te enseña lo principal en un minuto."),
    Slide("folder_open", "Abrir y moverse por el documento",
          "Abre varios PDF a la vez (Ctrl+O o arrastrándolos a la ventana) y pasa de "
          "uno a otro con Ctrl+Tab. Panel lateral con miniaturas, marcadores, comentarios "
          "y firmas (F4), búsqueda con Ctrl+F y zoom al ancho o a la página."),
    Slide("text_add_t", "Comentar sobre la página",
          "Texto que se escribe directamente donde va a quedar, notas adhesivas, "
          "resaltar, subrayar o tachar (sobre el texto o a mano alzada), rectángulos, "
          "emojis y borrador. Todo se deshace con Ctrl+Z."),
    Slide("edit", "Editar el contenido del PDF",
          "Cambia el texto y las imágenes que ya están en el documento: el párrafo se "
          "reajusta a su cuadro y las imágenes se mueven, se sustituyen o se borran "
          "(tecla C)."),
    Slide("form", "Rellenar formularios",
          "Los campos se resaltan en azul; se escriben en el propio campo, las casillas "
          "se marcan con un clic y los cálculos y validaciones funcionan como en Acrobat."),
    Slide("document_multiple", "Organizar páginas",
          "Arrastra miniaturas para reordenar y gira, duplica, elimina, inserta o extrae "
          "páginas. Combina varios PDF, divide uno en partes o crea un PDF desde imágenes, "
          "también desde el menú contextual del Explorador."),
    Slide("certificate", "Firma digital PAdES",
          "Firma con los certificados de Windows o con un archivo .pfx, con sellado de "
          "tiempo y certificación. Las firmas del documento se verifican solas contra el "
          "almacén de Windows y la lista de confianza de España."),
    Slide("calligraphy_pen", "Firma manuscrita",
          "Desde la barra de Firma, la plumilla: dibuja tu firma con el ratón, con trazo "
          "de estilográfica y el color y grosor que quieras, o carga la imagen de tu "
          "firma escaneada."),
    Slide("document_search", "Reconocimiento de texto (OCR)",
          "Convierte los escaneos y las fotos en PDF con texto que se puede buscar y "
          "copiar. Endereza la página y corrige la orientación antes de leerla."),
    Slide("lock_closed", "Proteger y preparar",
          "Contraseña AES-256 y permisos, marca de agua, encabezado y pie, numeración "
          "Bates, compresión y exportación a Word, imágenes o texto."),
    Slide("keyboard", "Listo para empezar",
          "F1 muestra todos los atajos de teclado. Puedes volver a ver esta presentación "
          "cuando quieras desde Ayuda › Presentación de AventyaPDF."),
)


def should_show() -> bool:
    return QSettings(*_SETTINGS).value(KEY_SHOW, True, type=bool)


def set_show(show: bool) -> None:
    s = QSettings(*_SETTINGS)
    s.setValue(KEY_SHOW, bool(show))
    s.sync()


class _Progress(QWidget):
    """Barra redondeada de la maqueta: cápsula clara con relleno azul y la
    plumilla al final. `value` va de 0 a 1."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = 0.0
        self.setFixedHeight(30)

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pluma = 34
        r = QRectF(2, 7, self.width() - pluma - 6, 16)
        p.setPen(QPen(QColor(23, 53, 94, 150), 1.2))
        p.setBrush(QColor(255, 255, 255, 120))
        p.drawRoundedRect(r, 8, 8)
        if self.value > 0:
            dentro = r.adjusted(2.5, 2.5, -2.5, -2.5)
            ancho = max(dentro.height(), dentro.width() * min(1.0, self.value))
            relleno = QRectF(dentro.left(), dentro.top(), ancho, dentro.height())
            g = QLinearGradient(relleno.topLeft(), relleno.topRight())
            g.setColorAt(0, QColor("#4F798B"))
            g.setColorAt(1, QColor("#24374B"))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(g)
            p.drawRoundedRect(relleno, dentro.height() / 2, dentro.height() / 2)
        f = QFont(icons.ICON_FAMILY)
        f.setPixelSize(24)
        p.setFont(f)
        p.setPen(QColor("#24374B"))
        p.drawText(QRectF(self.width() - pluma, 0, pluma, self.height()),
                   Qt.AlignmentFlag.AlignCenter, icons.glyph("signature"))
        p.end()


class WelcomeDialog(QDialog):
    """La presentación. `index` es la diapositiva actual."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("Presentación de AventyaPDF")
        self.setFixedSize(W, H)
        self.index = 0
        self._elapsed = 0
        self._paused = False
        self._drag = None
        # Nada de la hoja de estilos global (fondo gris #F3F3F3 en QWidget).
        self.setStyleSheet(
            # Las fuentes van aquí y no con setFont(): la regla QWidget de la
            # hoja global manda sobre setFont() (invariante 55).
            "QWidget { background: transparent; font-family:'Noto Sans','Segoe UI'; }"
            f"QLabel {{ color:{TEXT}; font-size:15px; }}"
            f"QLabel#titulo {{ color:{NAVY}; font-size:46px; font-weight:700; }}"
            f"QLabel#diapo {{ color:{NAVY}; font-size:20px; font-weight:700; }}"
            f"QLabel#icono {{ color:{NAVY}; font-size:24px; font-family:'{icons.ICON_FAMILY}'; }}"
            "QLabel#contador { color:#5E6A70; font-size:12px; }"
            "QLabel#pie { color:#4E565B; font-size:12px; }"
            "QPushButton { background: rgba(255,255,255,0.72); color:#17355E;"
            " border:1px solid rgba(23,53,94,0.45); border-radius:6px;"
            " padding:4px 14px; font-size:13px; min-height:22px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.95); }"
            "QPushButton:disabled { color: rgba(23,53,94,0.35); }"
            "QPushButton#primario { background:#17355E; color:#FFFFFF; border-color:#17355E; }"
            "QPushButton#primario:hover { background:#24497C; }"
            "QPushButton#cerrar { background: transparent; border:none; font-size:16px;"
            f" font-family:'{icons.ICON_FAMILY}'; padding:0; min-width:28px; }}"
            "QPushButton#cerrar:hover { background: rgba(255,255,255,0.5); }"
            "QCheckBox { color:#2E363C; font-size:13px; spacing:7px; }"
            "QCheckBox::indicator { width:15px; height:15px; border-radius:3px;"
            " border:1px solid rgba(23,53,94,0.7); background: rgba(255,255,255,0.85); }"
            "QCheckBox::indicator:checked { background:#17355E; border-color:#17355E;"
            " image: none; }")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 14, 20, 12)
        lay.setSpacing(0)

        arriba = QHBoxLayout()
        arriba.addStretch()
        self._btn_close = QPushButton(icons.glyph("dismiss"))
        self._btn_close.setObjectName("cerrar")
        self._btn_close.setToolTip("Cerrar la presentación  (Esc)")
        self._btn_close.clicked.connect(self.accept)
        arriba.addWidget(self._btn_close)
        lay.addLayout(arriba)

        logo = QLabel()
        logo.setPixmap(QIcon(icons.APP_ICON).pixmap(112, 112))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(logo)
        lay.addSpacing(6)
        titulo = QLabel("AventyaPDF")
        titulo.setObjectName("titulo")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(titulo)
        lay.addSpacing(14)

        self._progress = _Progress()
        barra = QHBoxLayout()
        barra.setContentsMargins(40, 0, 32, 0)
        barra.addWidget(self._progress)
        lay.addLayout(barra)
        lay.addSpacing(10)

        cab = QHBoxLayout()
        cab.addStretch()
        self._slide_icon = QLabel()
        self._slide_icon.setObjectName("icono")
        cab.addWidget(self._slide_icon)
        cab.addSpacing(6)
        self._slide_title = QLabel()
        self._slide_title.setObjectName("diapo")
        cab.addWidget(self._slide_title)
        cab.addStretch()
        lay.addLayout(cab)
        lay.addSpacing(6)

        self._slide_text = QLabel()
        self._slide_text.setWordWrap(True)
        self._slide_text.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self._slide_text.setFixedHeight(84)
        self._slide_text.setContentsMargins(30, 0, 30, 0)
        lay.addWidget(self._slide_text)

        self._counter = QLabel()
        self._counter.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._counter.setObjectName("contador")
        lay.addSpacing(4)
        lay.addWidget(self._counter)
        lay.addStretch()

        abajo = QHBoxLayout()
        self._chk = QCheckBox("No volver a mostrar al iniciar")
        self._chk.setChecked(not should_show())
        abajo.addWidget(self._chk)
        abajo.addStretch()
        self._btn_prev = QPushButton("‹ Anterior")
        self._btn_prev.clicked.connect(lambda: self.go(self.index - 1))
        abajo.addWidget(self._btn_prev)
        self._btn_next = QPushButton()
        self._btn_next.setObjectName("primario")
        self._btn_next.setDefault(True)
        self._btn_next.clicked.connect(self._on_next)
        abajo.addWidget(self._btn_next)
        lay.addLayout(abajo)
        lay.addSpacing(8)

        # (r71) Titular y licencia libre, con el enlace al repositorio.
        from window_menus import APP_OWNER, APP_REPO
        pie = QLabel(f"© {datetime.date.today().year} {APP_OWNER} · Libre distribución · "
                     f"<a href='{APP_REPO}' style='color:#17355E;'>GitHub</a>")
        pie.setToolTip(APP_REPO)
        pie.setTextFormat(Qt.TextFormat.RichText)
        pie.setOpenExternalLinks(True)
        pie.setObjectName("pie")
        pie.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(pie)

        self._timer = QTimer(self)
        self._timer.setInterval(TICK_MS)
        self._timer.timeout.connect(self._tick)
        self.go(0)
        self._timer.start()

    # ── diapositivas ──────────────────────────────────────────────────── #

    def go(self, index: int) -> None:
        self.index = max(0, min(len(SLIDES) - 1, index))
        self._elapsed = 0
        s = SLIDES[self.index]
        self._slide_icon.setText(icons.glyph(s.icon))
        self._slide_title.setText(s.title)
        self._slide_text.setText(s.text)
        self._counter.setText(f"{self.index + 1} de {len(SLIDES)}")
        ultima = self.index == len(SLIDES) - 1
        self._btn_prev.setEnabled(self.index > 0)
        self._btn_next.setText("Empezar" if ultima else "Siguiente ›")
        self._update_progress()

    def _on_next(self) -> None:
        if self.index == len(SLIDES) - 1:
            self.accept()
        else:
            self.go(self.index + 1)

    def _tick(self) -> None:
        if self._paused or self.index == len(SLIDES) - 1:
            return
        self._elapsed += TICK_MS
        if self._elapsed >= SLIDE_MS:
            self.go(self.index + 1)
        else:
            self._update_progress()

    def _update_progress(self) -> None:
        # La barra entera = toda la presentación; se llena de forma continua.
        n = len(SLIDES) - 1
        parcial = 0.0 if self.index == n else min(1.0, self._elapsed / SLIDE_MS)
        self._progress.value = (self.index + parcial) / n
        self._progress.update()

    # ── ratón y teclado ───────────────────────────────────────────────── #

    def enterEvent(self, e):
        self._paused = True            # leyendo: la presentación espera
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._paused = False
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag is not None and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, e):
        self._drag = None

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Right:
            self.go(self.index + 1)
        elif e.key() == Qt.Key.Key_Left:
            self.go(self.index - 1)
        else:
            super().keyPressEvent(e)        # Esc cierra, Intro = botón por defecto

    def done(self, r):
        self._timer.stop()
        set_show(not self._chk.isChecked())
        super().done(r)

    # ── fondo de la maqueta ───────────────────────────────────────────── #

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        caja = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        forma = QPainterPath()
        forma.addRoundedRect(caja, 14, 14)
        p.setClipPath(forma)
        base = QLinearGradient(caja.topLeft(), caja.bottomLeft())
        base.setColorAt(0, QColor("#1B7B8B"))
        base.setColorAt(1, QColor("#58949D"))
        p.fillRect(caja, base)
        # Resplandor claro en el centro, bajo el título.
        luz = QRadialGradient(QPointF(W * 0.50, H * 0.40), W * 0.62)
        luz.setColorAt(0.0, QColor(242, 245, 244, 255))
        luz.setColorAt(0.45, QColor(214, 229, 231, 225))
        luz.setColorAt(1.0, QColor(214, 229, 231, 0))
        p.fillRect(caja, luz)
        # Salmón en la esquina inferior derecha.
        sal = QRadialGradient(QPointF(W * 1.02, H * 1.02), W * 0.62)
        sal.setColorAt(0.0, QColor(205, 110, 72, 255))
        sal.setColorAt(0.45, QColor(210, 140, 110, 150))
        sal.setColorAt(1.0, QColor(210, 160, 140, 0))
        p.fillRect(caja, sal)
        # Plumilla de adorno, como en la maqueta.
        f = QFont(icons.ICON_FAMILY)
        f.setPixelSize(26)
        p.setFont(f)
        p.setPen(QColor(36, 55, 75, 170))
        p.drawText(QRectF(W - 46, H - 42, 36, 36), Qt.AlignmentFlag.AlignCenter,
                   icons.glyph("signature"))
        p.setClipping(False)
        p.setPen(QPen(QColor(255, 255, 255, 90), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(forma)
        p.end()


def show_welcome(parent, only_if_enabled: bool = False) -> WelcomeDialog | None:
    """Abre la presentación sin bloquear (modal para la ventana). Al arrancar,
    con `only_if_enabled`, no sale si se marcó «No volver a mostrar»."""
    if only_if_enabled and not should_show():
        return None
    dlg = WelcomeDialog(parent)
    dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    if parent is not None:
        g = parent.frameGeometry()
        dlg.move(g.center().x() - W // 2, g.center().y() - H // 2)
    dlg.open()
    dlg.activateWindow()
    return dlg
