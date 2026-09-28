import datetime
import faulthandler
import os
import sys
import traceback

# (r67) OpenBLAS (la biblioteca matemática de numpy, que importa el OCR con
# OpenCV) reserva al importarse un búfer por cada núcleo del procesador:
# ~100 MB de memoria privada que la app no usa (numpy solo hace operaciones
# sencillas). Con un hilo: 259 → 161 MB con un PDF abierto. Tiene que fijarse
# ANTES de que nada importe numpy. setdefault: quien lo fije a mano manda.
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

# (r86, r87) Antes de importar nada pesado: el menú contextual clásico lanza
# un proceso por archivo seleccionado (los de una misma acción se reúnen en
# uno solo, ver menu_contextual.py), y CUALQUIER apertura normal —doble
# clic, «Abrir con…», varios PDF a la vez, otra aplicación— debe acabar en
# la ÚNICA instancia abierta, no en una ventana nueva por archivo. Solo al
# ejecutarse como programa, no al importarse.
if __name__ == "__main__":
    import menu_contextual
    _argv = sys.argv[1:]
    if _argv and _argv[0] in menu_contextual.ACCIONES:
        sys.argv[1:] = menu_contextual.agrupar_invocaciones(_argv)
    elif _argv[:1] == ["--autodiagnostico"]:
        pass                 # invocación especial (construir.ps1): nunca se cede
    elif menu_contextual.es_instancia_secundaria(_argv):
        sys.exit(0)          # otra instancia ya recogerá esto (archivos, o solo activarse)

# Todos los complementos son obligatorios: antes de importar nada de fuera se
# instala a la fuerza lo que falte de requirements.txt (dependencias.py).
import dependencias
dependencias.asegurar_o_salir()

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMessageBox
import icons
from main_window import MainWindow
from utils import TOOLTIP_QSS
import presentacion
import tesseract_ui

# Registro de errores: local a cada equipo (la carpeta del proyecto es compartida).
LOG_DIR = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
                       "aventyapdf")
LOG_PATH = os.path.join(LOG_DIR, "errores.log")
_fault_log = None   # referencia viva: faulthandler escribe en él si Python se cuelga

STYLESHEET = """
/* ── Base ── */
QMainWindow, QDialog, QWidget {
    background-color: #F3F3F3;
    color: #201F1E;
    font-family: 'Segoe UI Variable', 'Segoe UI', sans-serif;
    font-size: 13px;
}

/* ── Main toolbar (white) ── */
QFrame#topbar {
    background-color: #FFFFFF;
    border-bottom: 1px solid #E0E0E0;
}

/* (petición de Ricardo) TODOS los botones y campos de formulario de la
   aplicación miden 32 px de alto (y los botones de icono, 32×32). En Qt,
   min/max-height es la altura del contenido: sin borde se pone 32 y con
   borde de 1 px, 30 (30 + 1 + 1 = 32). Ver icons.CONTROL.               */

/* ── Botones de icono ──────────────────────────────────────────────────────
   TODOS los iconos de la aplicación son de **Fluent UI System Icons** (fuente
   incluida en vendor/fonts/fluent-icons, licencia MIT). Los glifos se piden por
   nombre con icons.glyph(); no se usa ninguna otra fuente de iconos.          */
QPushButton#tbr_btn {
    background: transparent;
    border: none;
    border-radius: 6px;
    font-family: "FluentSystemIcons-Regular";
    font-size: 20px;
    min-width: 32px;  max-width: 32px;
    min-height: 32px; max-height: 32px;
    padding: 0;
}
QPushButton#tbr_btn:hover   { background: #F0F0F0; }
QPushButton#tbr_btn:pressed { background: #E0E0E0; }
QPushButton#tbr_btn:checked { background: #CCE4F7; border: 1px solid #0078D4; }
QPushButton#tbr_btn:disabled { opacity: 0.4; }

/* ── Page nav buttons ── */
QPushButton#nav_btn {
    background: transparent;
    border: none;
    border-radius: 6px;
    font-family: "FluentSystemIcons-Regular";
    font-size: 20px;
    min-width: 32px;  max-width: 32px;
    min-height: 32px; max-height: 32px;
    padding: 0;
}
QPushButton#nav_btn:hover   { background: #F0F0F0; }
QPushButton#nav_btn:pressed { background: #E0E0E0; }

/* ── Options row — etiquetas de texto ── */
QLabel#opt_lbl {
    font-size: 12px; color: #605E5C; background: transparent;
}

/* ── Options row — iconos indicadores (no interactivos) ── */
QLabel#opt_glyph {
    font-family: "FluentSystemIcons-Regular";
    font-size: 18px; color: #605E5C; background: transparent;
}

/* ── Options row — botones de icono cuadrados (páginas, etc.) ── */
QPushButton#opt_btn {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 4px;
    font-family: "FluentSystemIcons-Regular";
    font-size: 18px;
    min-width: 30px;  max-width: 30px;
    min-height: 30px; max-height: 30px;
    padding: 0;
}
QPushButton#opt_btn:hover   { background: #EBEBEB; border-color: #D2D0CE; }
QPushButton#opt_btn:disabled { color: #C8C6C4; }
QPushButton#opt_btn:pressed { background: #D8D8D8; }

/* ── Color swatch buttons (secondary toolbar) ── */
QPushButton#color_swatch {
    min-width: 30px;  max-width: 30px;
    min-height: 30px; max-height: 30px;
    padding: 0;
    border: 1px solid #8A8886;
    border-radius: 3px;
}
QPushButton#color_swatch:hover { border-color: #605E5C; }
/* (petición de Ricardo) Paleta de colores: menú emergente en el cursor,
   con el mismo aspecto que QMenu. */
QFrame#color_popup { background: #FFFFFF; border: 1px solid #D2D0CE; }
QFrame#color_popup QLabel { background: transparent; }

/* ── Options row — botones +/− del spin personalizado ── */
QPushButton#opt_spin_btn {
    background: #F5F5F5;
    border: 1px solid #AEACAB;
    border-radius: 3px;
    font-family: "FluentSystemIcons-Regular";
    font-size: 14px; color: #201F1E;
    padding: 0;
    margin: 0;
    min-width: 30px; max-width: 30px;
    min-height: 30px; max-height: 30px;
}
QPushButton#opt_spin_btn:hover   { background: #E5E5E5; border-color: #8A8886; }
QPushButton#opt_spin_btn:pressed { background: #D8D8D8; }

QSpinBox#opt_spin_field {
    border: 1px solid #AEACAB;
    border-radius: 0;
    background: #FFFFFF; color: #201F1E;
    min-width: 34px; max-width: 40px;
    min-height: 30px; max-height: 30px;
    padding: 0;
    selection-background-color: #0078D4;
}


/* ── SpinBox estandarizado ── */
QSpinBox {
    background: #FFFFFF; color: #201F1E;
    border: 1px solid #8A8886; border-radius: 4px;
    padding: 0 4px;
    min-height: 30px; max-height: 30px;
    selection-background-color: #0078D4;
}
QSpinBox:focus { border-color: #0078D4; }
QSpinBox::up-button {
    subcontrol-origin: border; subcontrol-position: top right;
    width: 16px; border-left: 1px solid #AEACAB; border-top-right-radius: 3px;
}
QSpinBox::down-button {
    subcontrol-origin: border; subcontrol-position: bottom right;
    width: 16px; border-left: 1px solid #AEACAB; border-bottom-right-radius: 3px;
}
QSpinBox::up-button:hover, QSpinBox::down-button:hover { background: #E0E0E0; }

/* ── ComboBox estandarizado ── */
QComboBox {
    background: #FFFFFF; color: #201F1E;
    border: 1px solid #8A8886; border-radius: 4px;
    padding: 0 6px;
    min-height: 30px; max-height: 30px;
}
QComboBox:hover { border-color: #605E5C; }
QComboBox::drop-down { border: none; padding-right: 4px; }
QComboBox QAbstractItemView {
    background: #FFFFFF; color: #201F1E;
    border: 1px solid #8A8886;
    selection-background-color: #0078D4;
    selection-color: #FFFFFF;
}

/* ── Sliders (zoom, compresión) ── */
/* (petición de Ricardo) Fondo transparente: se ve el de su contenedor (el
   blanco del menú de colores, el del panel lateral…) y no el gris de la regla
   general `QWidget`. */
QSlider { background: transparent; }
QSlider::groove:horizontal {
    height: 4px; background: #D2D0CE; border-radius: 2px; margin: 0;
}
QSlider::handle:horizontal {
    background: #0078D4; border: none;
    width: 14px; height: 14px; border-radius: 7px;
    margin: -5px 0;
}
QSlider::handle:horizontal:hover { background: #106EBE; }
QSlider::sub-page:horizontal { background: #0078D4; border-radius: 2px; }

/* ── Viewer area (darker than toolbar) ── */
QScrollArea {
    background-color: #D0D4D8;
    border: none;
}

QScrollBar:vertical {
    background: #D0D4D8; width: 12px; border: none;
}
QScrollBar::handle:vertical {
    background: #A0A4A8; border-radius: 5px; min-height: 30px; margin: 2px;
}
QScrollBar::handle:vertical:hover { background: #808488; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background: #D0D4D8; height: 12px; border: none;
}
QScrollBar::handle:horizontal {
    background: #A0A4A8; border-radius: 5px; min-width: 30px; margin: 2px;
}
QScrollBar::handle:horizontal:hover { background: #808488; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ── Status bar ── */
QStatusBar {
    background: #F3F3F3; color: #605E5C;
    border-top: 1px solid #E0E0E0;
    padding: 2px 8px; font-size: 12px;
}

/* ── Herramienta de zoom de la barra de estado (petición de Ricardo: del
   mismo alto que la barra original — los controles se adaptan a ella, no
   al revés, así que su tamaño se fija aquí y no con icons.CONTROL) ── */
QPushButton#status_zoom_btn {
    background: transparent;
    border: none;
    border-radius: 3px;
    font-family: "FluentSystemIcons-Regular";
    font-size: 12px;
    min-width: 16px;  max-width: 16px;
    min-height: 16px; max-height: 16px;
    padding: 0;
}
QPushButton#status_zoom_btn:hover    { background: #E4E4E4; }
QPushButton#status_zoom_btn:pressed  { background: #D0D0D0; }
QPushButton#status_zoom_btn:disabled { color: #C8C6C4; }

QLineEdit#status_zoom_pct {
    background: #FFFFFF; color: #201F1E;
    border: 1px solid #C8C6C4; border-radius: 3px;
    padding: 0 3px;
    font-size: 11px;
    min-width: 52px; max-width: 52px;
    min-height: 16px; max-height: 16px;
    selection-background-color: #0078D4; selection-color: #FFFFFF;
}
QLineEdit#status_zoom_pct:focus    { border-color: #0078D4; }
QLineEdit#status_zoom_pct:disabled { background: #F3F3F3; color: #C8C6C4; }

/* ── Separator line ── */
QFrame#vline { background: #E0E0E0; max-width: 1px; }

/* ── Dialogs / misc ── */
QLineEdit {
    background: #FFFFFF; color: #201F1E;
    border: 1px solid #8A8886; border-radius: 4px;
    padding: 0 6px; min-height: 30px; max-height: 30px;
    selection-background-color: #0078D4; selection-color: #FFFFFF;
}
QLineEdit:focus { border-color: #0078D4; }

QPushButton {
    background: #FBFBFB; color: #201F1E;
    border: 1px solid #8A8886; border-radius: 4px;
    padding: 0 12px; min-height: 30px; max-height: 30px;
}
QPushButton:hover   { background: #F0F0F0; border-color: #605E5C; }
QPushButton:pressed { background: #E5E5E5; }
QPushButton:disabled { background: #F3F3F3; color: #A19F9D; border-color: #D2D0CE; }

QInputDialog, QMessageBox, QDialog { background: #FFFFFF; }
QLabel { background: transparent; }

QListWidget { background: #FFFFFF; color: #201F1E; border: 1px solid #E0E0E0; }
QListWidget::item:selected { background: #CCE4F7; color: #201F1E; }
QListWidget::item:hover    { background: #F0F0F0; }

/* ── Barra de menús y menús ── */
QMenuBar { background: #FFFFFF; color: #201F1E; border-bottom: 1px solid #EDEBE9; padding: 2px 4px; }
QMenuBar::item { background: transparent; padding: 4px 10px; border-radius: 4px; }
QMenuBar::item:selected { background: #F0F0F0; }
QMenu { background: #FFFFFF; color: #201F1E; border: 1px solid #D2D0CE; padding: 4px; }
QMenu::item { padding: 6px 28px 6px 24px; border-radius: 4px; }
QMenu::item:selected { background: #E5F1FB; color: #201F1E; }
QMenu::item:disabled { color: #A19F9D; }
QMenu::separator { height: 1px; background: #EDEBE9; margin: 4px 8px; }

/* ── Panel lateral (rail de iconos + paneles) ── */
QFrame#rail { background: #FFFFFF; border-right: 1px solid #E0E0E0; }
QPushButton#rail_btn {
    background: transparent; border: none; border-radius: 6px;
    font-family: "FluentSystemIcons-Regular"; font-size: 20px;
    min-width: 32px; max-width: 32px; min-height: 32px; max-height: 32px; padding: 0;
}
QPushButton#rail_btn:hover   { background: #F0F0F0; }
QPushButton#rail_btn:checked { background: #CCE4F7; border-left: 3px solid #0078D4; }
QPushButton#rail_btn:disabled { color: #C8C6C4; }
QFrame#rail_sep { background: #D2D0CE; border: none; margin: 2px 6px; }
QScrollArea#rail_docs, QWidget#rail_docs_holder { background: transparent; border: none; }
QPushButton#rail_doc {
    background: transparent; border: none; border-radius: 6px; color: #A4262C;
    font-family: "FluentSystemIcons-Regular"; font-size: 20px;
    min-width: 32px; max-width: 32px; min-height: 32px; max-height: 32px; padding: 0;
}
QPushButton#rail_doc:hover   { background: #F0F0F0; }
QPushButton#rail_doc:checked { background: #CCE4F7; border-left: 3px solid #0078D4; }
QWidget#side_column { background: #FAFAFA; border-right: 1px solid #E0E0E0; }
QStackedWidget#side_stack { background: #FAFAFA; }
/* (r26) Opciones de herramienta encima del panel lateral */
QFrame#side_tools { background: #FAFAFA; border-bottom: 1px solid #E0E0E0; }
QFrame#side_tool_panel, QFrame#side_tool_panel QLabel { background: #FAFAFA; }
QLabel#side_lbl { font-size: 12px; color: #201F1E; }
QLabel#side_hint { font-size: 12px; color: #605E5C; }
/* (petición de Ricardo) Aviso enmarcado dentro de un panel (p. ej. Firma):
   con marco y fondo propios, para que se lea como aviso y no como control.
   Dos ids en el selector: si no, gana el fondo de `#side_tool_panel QLabel`. */
QFrame#side_tool_panel QLabel#side_notice {
    background: #E5F1FB; color: #004578; font-size: 12px;
    border: 1px solid #C7E0F4; border-radius: 4px; padding: 6px 8px;
}
QStackedWidget#side_stack QListWidget, QStackedWidget#side_stack QTreeWidget {
    background: #FAFAFA; border: none;
}
QLabel#side_title { font-weight: 600; font-size: 13px; padding: 4px 2px 6px 2px; }
QPushButton#side_icon_btn {
    background: transparent; border: 1px solid transparent; border-radius: 4px;
    font-family: "FluentSystemIcons-Regular"; font-size: 20px;
    min-width: 30px; max-width: 30px; min-height: 30px; max-height: 30px; padding: 0;
}
QPushButton#side_icon_btn:hover   { background: #EBEBEB; border-color: #D2D0CE; }
QPushButton#side_icon_btn:pressed { background: #D8D8D8; }
QPushButton#side_icon_btn:disabled { color: #C8C6C4; }
/* (petición de Ricardo) Selectores circulares (nivel de Comprimir), en vez
   de un desplegable o de botones de texto */
QRadioButton#side_radio {
    background: transparent; font-size: 12px; color: #201F1E; spacing: 6px;
    padding: 3px 0;
}
QRadioButton#side_radio::indicator {
    width: 15px; height: 15px; border-radius: 8px; border: 1px solid #8A8886;
    background: #FFFFFF;
}
QRadioButton#side_radio::indicator:hover    { border-color: #0078D4; }
QRadioButton#side_radio::indicator:checked  {
    border: 5px solid #0078D4; background: #FFFFFF;
}
QTreeWidget { background: #FFFFFF; color: #201F1E; border: 1px solid #E0E0E0; }
QTreeWidget::item { padding: 3px 0; }
QTreeWidget::item:selected { background: #CCE4F7; color: #201F1E; }
QSplitter::handle { background: #E0E0E0; width: 1px; }

/* ── Búsqueda (r78: en línea en la barra principal) ── */
/* (r79, petición de Ricardo) Sin el gris de la regla general `QWidget`:
   el blanco de `#topbar`. (Petición de Ricardo) Opaco, porque flota encima
   de la barra y tapa las herramientas que queden debajo. */
QWidget#find_bar { background: #FFFFFF; }
QWidget#find_bar QLabel { background: transparent; }
QLabel#find_count { color: #605E5C; font-size: 12px; }

/* ── Aviso de documento (firmas, formularios, protección) ── */
QFrame#doc_banner { background: #E5F1FB; border-bottom: 1px solid #C7E0F4; }
QFrame#doc_banner QLabel { color: #004578; }

/* ── Pestañas ── */
QTabWidget::pane { border: 1px solid #E0E0E0; border-radius: 4px; top: -1px; background: #FFFFFF; }
QTabBar::tab { background: transparent; padding: 6px 14px; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { border-bottom: 2px solid #0078D4; font-weight: 600; }
QTabBar::tab:hover { background: #F0F0F0; }
QGroupBox { border: 1px solid #E0E0E0; border-radius: 6px; margin-top: 12px; padding: 10px 8px 8px 8px; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; color: #605E5C; }
QPlainTextEdit { background: #FFFFFF; border: 1px solid #8A8886; border-radius: 4px; }
"""


def _install_error_handler():
    """PyQt6 aborta la aplicación ante cualquier excepción no capturada en un
    slot (qFatal) si `sys.excepthook` es el predeterminado. Este gancho la
    registra en `errores.log`, la muestra en un diálogo y deja seguir."""
    global _fault_log
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        _fault_log = open(os.path.join(LOG_DIR, "fallos_graves.log"), "a", encoding="utf-8")
        faulthandler.enable(_fault_log)
    except Exception:
        pass

    showing = [False]

    def hook(exc_type, exc, tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc, tb)
            return
        text = "".join(traceback.format_exception(exc_type, exc, tb))
        if sys.stderr is not None:
            print(text, file=sys.stderr)
        try:
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"──── {datetime.datetime.now():%Y-%m-%d %H:%M:%S} ────\n{text}\n")
        except Exception:
            pass
        app = QApplication.instance()
        if app is None or showing[0]:
            return
        showing[0] = True
        try:
            while QApplication.overrideCursor() is not None:
                QApplication.restoreOverrideCursor()
            box = QMessageBox(QMessageBox.Icon.Critical, "Error inesperado",
                              "Se ha producido un error y la operación no se completó.\n\n"
                              f"{exc_type.__name__}: {exc}\n\n"
                              f"El detalle se ha guardado en:\n{LOG_PATH}",
                              parent=app.activeWindow())
            box.setDetailedText(text)
            box.exec()
        finally:
            showing[0] = False

    sys.excepthook = hook


# (r55, r86) Menú contextual del Explorador de Windows (ver menu_contextual.py):
# los archivos seleccionados llegan como argumentos, precedidos de la acción.
# Se procesan en una función aparte (no dentro de main()) para poder probarlos
# con una MainWindow de pruebas sin depender de sys.argv real.
from menu_contextual import (  # noqa: E402
    ARG_COMBINAR, ARG_COMBINAR_PDF, ARG_CONVERTIR, ARG_FIRMAR,
    ARG_IMAGENES_UN_PDF, ARG_IMAGENES_VARIOS_PDF,
)


def procesar_argumentos(window, argv: list[str]) -> None:
    """Interpreta `argv` (sys.argv[1:]) y actúa sobre `window`: o bien una de
    las acciones del menú contextual del Explorador, o bien el «Abrir con…»
    normal — TODOS los .pdf de la lista, cada uno en su pestaña (r87; antes
    solo abría el primero)."""
    if not argv:
        return
    accion, resto = argv[0], [p for p in argv[1:] if os.path.isfile(p)]
    if accion == ARG_FIRMAR:
        window.sign_files(resto)
        return
    if accion == ARG_COMBINAR:
        window.combine_files_to_pdf(resto)
        return
    if accion == ARG_CONVERTIR:
        window.convert_files_to_pdfs(resto)
        return
    if accion == ARG_COMBINAR_PDF:
        window.combine_pdfs_from_paths(resto)
        return
    if accion == ARG_IMAGENES_UN_PDF:
        window.create_from_images(resto)
        return
    if accion == ARG_IMAGENES_VARIOS_PDF:
        window.create_separate_pdfs_from_images(resto)
        return
    for arg in argv:
        if arg.lower().endswith(".pdf") and os.path.isfile(arg):
            window.open_path(arg)


def _start_instance_watch(window, interval_ms: int = 500) -> None:
    """(r87, aviso de Ricardo: «al abrir varios PDF se abre una ventana por
    cada uno») Mientras esta ventana esté abierta —la única instancia,
    `menu_contextual.es_instancia_secundaria`—, recoge periódicamente los
    archivos que otros procesos le hayan cedido (otro PDF abierto desde el
    Explorador o desde otra aplicación mientras esta seguía corriendo) y los
    abre cada uno en su pestaña, con la ventana al frente."""
    timer = QTimer(window)

    def recoger():
        entrantes = menu_contextual.recoger_entrantes()
        if not entrantes:
            return
        for argv in entrantes:
            procesar_argumentos(window, argv)
        if window.isMinimized():
            window.showNormal()
        window.raise_()
        window.activateWindow()

    timer.timeout.connect(recoger)
    timer.start(interval_ms)
    window._instance_watch_timer = timer      # referencia viva: si se pierde, el timer para


def _set_app_user_model_id() -> None:
    """(r57) Da a la ventana su propia identidad en la barra de tareas de
    Windows, para que muestre el icono de AventyaPDF y no el de python.exe.
    Tiene que hacerse antes de crear la primera ventana."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(icons.APP_USER_MODEL_ID)
    except Exception:
        pass


def main():
    if sys.argv[1:2] == ["--autodiagnostico"]:     # (r62) ver autodiagnostico.py
        import autodiagnostico
        sys.exit(autodiagnostico.run(sys.argv[2:]))
    _install_error_handler()
    _set_app_user_model_id()
    QApplication.setApplicationName("AventyaPDF")
    QApplication.setOrganizationName("aventyapdf")
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(icons.APP_ICON))      # (r57) todas las ventanas y diálogos
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET + TOOLTIP_QSS)
    # Tesseract OCR es obligatorio: se comprueba al iniciar y, si falta, se
    # instala a la fuerza. Si no se puede, la app sigue con el OCR desactivado.
    ocr_ok, ocr_reason = tesseract_ui.ensure_at_startup()
    window = MainWindow()
    window.set_ocr_available(ocr_ok, ocr_reason)
    window.show()
    procesar_argumentos(window, sys.argv[1:])
    # (r87) Mientras esta ventana siga abierta, recoge los PDF que le cedan
    # otros procesos (otra apertura mientras esta ya corría).
    _start_instance_watch(window)
    # (r70) Presentación inicial, salvo que se marcara «No volver a mostrar».
    QTimer.singleShot(250, lambda: presentacion.show_welcome(window, only_if_enabled=True))
    # (petición de Ricardo) Aviso de versión nueva, en segundo plano; espera
    # a que se cierre la presentación si está abierta.
    window.start_update_check()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
