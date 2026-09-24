"""
Iconos y fuentes incorporadas a la aplicación (r36; fuentes base en r40).

* **Iconos de TODAS las herramientas y botones: Fluent UI System Icons**
  (Microsoft, licencia MIT), variante Regular, en vendor/fonts/fluent-icons.
  Es la ÚNICA fuente de iconos de la aplicación —ningún icono sale de Segoe
  Fluent Icons, de MDL2 ni de imágenes—, y así está documentado en
  docs/interfaz_grafica.md y docs/arquitectura.md. Los códigos de cada icono
  salen de FluentSystemIcons-Regular.json **por nombre**, así que no hay números
  mágicos en el código: `glyph("folder_open")`. Un icono nuevo = una entrada en
  ICONS con el nombre de Fluent (si no existe, falla al arrancar).
* **Fuente base del programa**: familia **Noto** (Sans, Serif y Sans Mono;
  licencia OFL) en vendor/fonts/noto. Es la que escribe la app en el PDF cuando
  el texto lo pone ella (herramienta Texto, marca de agua, encabezado, pie,
  numeración Bates) y la de esos dos sitios de la interfaz donde el texto imita
  al del PDF (editor de campos y número de las miniaturas). `noto_path` da el
  archivo para escribir en el PDF y `load_fonts` las registra en Qt.
  OJO: el texto que YA está en el documento se reescribe con la fuente del
  propio documento, no con Noto (pdf_edit.resolve_font, invariante 32).
* **Emojis**: Noto Emoji (vendor/fonts/noto-emoji), ver emoji_font.py.
* **Icono de la aplicación** (ventana, barra de tareas, menú contextual):
  vendor/icono/aventyapdf.ico, generado desde ICONO.png con
  create_app_icon.py (r57).

Las fuentes van dentro del proyecto: no hay nada que instalar en Windows.
"""
import functools
import json
import os
import re

RAIZ = os.path.dirname(os.path.abspath(__file__))
ICON_DIR = os.path.join(RAIZ, "vendor", "fonts", "fluent-icons")
ICON_TTF = os.path.join(ICON_DIR, "FluentSystemIcons-Regular.ttf")
ICON_JSON = os.path.join(ICON_DIR, "FluentSystemIcons-Regular.json")
ICON_FAMILY = "FluentSystemIcons-Regular"
NOTO_DIR = os.path.join(RAIZ, "vendor", "fonts", "noto")
EMOJI_DIR = os.path.join(RAIZ, "vendor", "fonts", "noto-emoji")
APP_ICON = os.path.join(RAIZ, "vendor", "icono", "aventyapdf.ico")
# Identidad propia en la barra de tareas: sin ella Windows agrupa la ventana
# con python.exe y muestra el icono de Python en vez del de la aplicación.
APP_USER_MODEL_ID = "Aventya.AventyaPDF"

# Nombre de la app → nombre del icono en Fluent UI System Icons.
ICONS = {
    # Barra principal
    "open": "folder_open",
    "save": "save",
    "compress": "folder_zip",
    "print": "print",
    "prev": "chevron_left",
    "next": "chevron_right",
    "zoom100": "zoom_in",
    "type": "auto_fit_width",          # (r48) icono cuando el clic ajustaría al ANCHO
    "type_height": "auto_fit_height",  # (r48) icono cuando el clic ajustaría al ALTO
    "text": "text_add_t",
    "rect": "rectangle_landscape",
    "emoji": "emoji",
    "eraser": "eraser",
    "sign": "signature",
    "pages": "document_multiple",
    "undo": "arrow_undo",
    "redo": "arrow_redo",
    "note": "note",
    "markup": "highlight",             # (r59) el del antiguo «Marcador a mano alzada»
    "edit": "edit",
    "search": "search",
    "sidebar": "panel_left",
    # Indicadores y opciones
    "opt_size": "text_font",
    "opt_color": "paint_brush",
    "opt_weight": "pen",
    "opt_font": "text_font",
    "align_left": "text_align_left",
    "align_center": "text_align_center",
    "align_right": "text_align_right",
    "align_justify": "text_align_justify",
    "bold": "text_bold",               # (r58) antes letra «N» en Segoe UI
    "italic": "text_italic",           # (r58) antes letra «I» en Segoe UI
    "opt_cert": "certificate",
    "handsign": "calligraphy_pen",     # (r68) firma manuscrita (Fluent no trae sello de caucho)
    "opt_compress": "folder_zip",
    # Acciones
    "rotate_left": "arrow_rotate_counterclockwise",
    "rotate_right": "arrow_rotate_clockwise",
    "duplicate": "copy",
    "delete": "delete",
    "page_blank": "document_add",
    "insert_pdf": "document_pdf",
    "extract": "document_arrow_right",
    "cert_change": "arrow_swap",
    "save_copy": "save_copy",
    "find_text": "document_search",
    "apply": "checkmark",
    "minus": "subtract",
    "plus": "add",
    "rename": "rename",
    "refresh": "arrow_clockwise",
    "close": "dismiss",
    "find_prev": "chevron_up",
    "find_next": "chevron_down",
    # Panel lateral y pestañas
    "panel_thumbs": "grid",
    "panel_bookmarks": "bookmark_multiple",
    "panel_comments": "comment_multiple",
    "panel_signatures": "signature",
    "doc_pdf": "document_pdf",
    "doc_new": "document",
    # Aviso superior
    "view_normal": "document",
    "view_form": "form",
}

# Tamaños de diseño preferidos: 20 px es el de la interfaz; si no existe, el más cercano.
_SIZES = (20, 24, 16, 28, 32, 48, 12)


@functools.lru_cache(maxsize=1)
def _codepoints() -> dict[str, dict[int, int]]:
    with open(ICON_JSON, encoding="utf-8") as fh:
        raw = json.load(fh)
    out: dict[str, dict[int, int]] = {}
    for key, code in raw.items():
        m = re.match(r"^ic_fluent_(.+)_(\d+)_regular$", key)
        if m:
            out.setdefault(m.group(1), {})[int(m.group(2))] = code
    return out


def glyph(key: str) -> str:
    """Carácter del icono `key` (clave de ICONS o nombre de Fluent)."""
    nombre = ICONS.get(key, key)
    tallas = _codepoints().get(nombre)
    if not tallas:
        raise KeyError(f"Icono desconocido en Fluent UI System Icons: {nombre!r}")
    for s in _SIZES:
        if s in tallas:
            return chr(tallas[s])
    return chr(tallas[min(tallas)])


# ── Noto ─────────────────────────────────────────────────────────────────── #

NOTO_FAMILIES = {           # clave de estilo → (familia de Qt, prefijo del archivo)
    "sans": ("Noto Sans", "NotoSans"),
    "serif": ("Noto Serif", "NotoSerif"),
    "mono": ("Noto Sans Mono", "NotoSansMono"),
}
# font_css de las anotaciones de texto → clave de estilo
CSS_TO_NOTO = {"sans-serif": "sans", "serif": "serif", "monospace": "mono"}


def noto_path(kind: str, bold: bool = False, italic: bool = False) -> str:
    """Archivo TTF de Noto. Noto Sans Mono no tiene cursiva: se usa la recta."""
    _fam, prefijo = NOTO_FAMILIES.get(kind, NOTO_FAMILIES["sans"])
    estilo = ("Bold" if bold else "") + ("Italic" if italic else "")
    ruta = os.path.join(NOTO_DIR, f"{prefijo}-{estilo or 'Regular'}.ttf")
    if not os.path.isfile(ruta) and italic:
        ruta = os.path.join(NOTO_DIR, f"{prefijo}-{'Bold' if bold else 'Regular'}.ttf")
    return ruta


def noto_family(kind: str) -> str:
    return NOTO_FAMILIES.get(kind, NOTO_FAMILIES["sans"])[0]


def load_fonts() -> None:
    """Registra en Qt la fuente de iconos, las Noto y Noto Emoji (hace falta
    una QApplication). Se puede llamar varias veces."""
    from PyQt6.QtGui import QFontDatabase
    if getattr(load_fonts, "_hecho", False):
        return
    rutas = [ICON_TTF]
    for carpeta in (NOTO_DIR, EMOJI_DIR):
        rutas += [os.path.join(carpeta, f) for f in sorted(os.listdir(carpeta))
                  if f.lower().endswith(".ttf")]
    for ruta in rutas:
        QFontDatabase.addApplicationFont(ruta)
    load_fonts._hecho = True
