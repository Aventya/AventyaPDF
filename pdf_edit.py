"""
pdf_edit.py
Edición del contenido REAL de la página: el texto y las imágenes que forman
parte del PDF, no anotaciones puestas encima.

Hasta ahora la aplicación solo sabía *añadir* cosas sobre la página (texto como
anotación FreeText, sellos, marcas). Esto es lo que hace Acrobat en «Editar
PDF»: cambiar lo que ya está escrito.

Cómo se hace (y por qué así):

1. **Quitar el texto viejo = redacción.** Es la única forma con MuPDF de borrar
   de verdad caracteres del flujo de contenido. Se aplica con
   `images=PDF_REDACT_IMAGE_NONE` y `graphics=PDF_REDACT_LINE_ART_NONE` para que
   no se lleve por delante las imágenes ni el arte vectorial que hay debajo, y
   la anotación se crea con `fill=False` para que no pinte ningún recuadro.
2. **Las marcas de redacción pendientes que ya traiga el PDF se apartan y se
   reponen.** `apply_redactions()` aplica *todas* las de la página, así que
   editar una línea habría ejecutado sin avisar marcas de redacción puestas
   por otra aplicación antes de abrirlo (la app ya no tiene herramienta propia
   de redactar; invariante 31).
3. **Escribir el texto nuevo = `TextWriter`** en la línea base original
   (`span["origin"]`), con el tamaño y el color originales.
4. **La fuente incrustada NO sirve para escribir.** Los subconjuntos que generan
   Word y Acrobat suelen venir sin tabla `cmap`: `fitz.Font(fontbuffer=…)`
   devuelve glifo 0 para todos los caracteres y el texto saldría en blanco. Se
   escribe con la familia **Noto** incluida en la app (r36): Noto Sans, Noto
   Serif o Noto Sans Mono según el tipo de letra original (invariante 32).
5. **Páginas giradas**: se trabaja con la rotación a 0 y se compensa el ángulo
   de la propia línea (`line["dir"]`), así la línea nueva queda como las demás.
6. **Imágenes: por aparición, no por xref.** `Page.replace_image` y
   `Page.delete_image` actúan sobre el objeto y cambian *todas* las copias de esa
   imagen en todo el documento. Para tocar solo la que señala el usuario se
   redacta su rectángulo con `PDF_REDACT_IMAGE_REMOVE` (invariante 33).

Nada de este módulo toca Qt.
"""
import math
import os
import re

import fitz

import icons
import pdf_compression

# Bits de `span["flags"]` de PyMuPDF.
FLAG_SUPERSCRIPT = 1
FLAG_ITALIC = 2
FLAG_SERIF = 4
FLAG_MONO = 8
FLAG_BOLD = 16

# Prefijo de subconjunto que anteponen Word, LibreOffice y Acrobat: "BCDEEE+Calibri".
_SUBSET = re.compile(r"^[A-Z]{6}\+")
# Sufijos de estilo pegados al nombre: "Arial,Bold", "TimesNewRomanPS-BoldMT".
_STYLE_WORDS = ("bolditalic", "boldoblique", "semibold", "bold", "black", "heavy",
                "italic", "oblique", "light", "regular", "roman", "medium", "mt", "ps")

# (r40) **La fuente del documento no se cambia**: al reescribir un párrafo se
# usa la MISMA fuente instalada en Windows y, si no está, la más parecida. Las
# Noto incluidas en la app son la fuente base: solo se usan cuando el sistema no
# tiene nada mejor (y para el texto que añade la app).
# Familias conocidas → (tipo, archivos en %WINDIR%\Fonts: normal, negrita,
# cursiva, negrita cursiva).
_FAMILIES = {
    "calibri":       ("sans", ("calibri.ttf", "calibrib.ttf", "calibrii.ttf", "calibriz.ttf")),
    "arial":         ("sans", ("arial.ttf", "arialbd.ttf", "ariali.ttf", "arialbi.ttf")),
    "helvetica":     ("sans", ("arial.ttf", "arialbd.ttf", "ariali.ttf", "arialbi.ttf")),
    "segoeui":       ("sans", ("segoeui.ttf", "segoeuib.ttf", "segoeuii.ttf", "segoeuiz.ttf")),
    "verdana":       ("sans", ("verdana.ttf", "verdanab.ttf", "verdanai.ttf", "verdanaz.ttf")),
    "tahoma":        ("sans", ("tahoma.ttf", "tahomabd.ttf", "tahoma.ttf", "tahomabd.ttf")),
    "trebuchetms":   ("sans", ("trebuc.ttf", "trebucbd.ttf", "trebucit.ttf", "trebucbi.ttf")),
    "comicsansms":   ("sans", ("comic.ttf", "comicbd.ttf", "comici.ttf", "comicz.ttf")),
    "impact":        ("sans", ("impact.ttf",) * 4),
    "aptos":         ("sans", ("aptos.ttf", "aptos-bold.ttf", "aptos-italic.ttf",
                               "aptos-bold-italic.ttf")),
    "cambria":       ("serif", ("cambria.ttc", "cambriab.ttf", "cambriai.ttf", "cambriaz.ttf")),
    "timesnewroman": ("serif", ("times.ttf", "timesbd.ttf", "timesi.ttf", "timesbi.ttf")),
    "times":         ("serif", ("times.ttf", "timesbd.ttf", "timesi.ttf", "timesbi.ttf")),
    "georgia":       ("serif", ("georgia.ttf", "georgiab.ttf", "georgiai.ttf", "georgiaz.ttf")),
    "palatinolinotype": ("serif", ("pala.ttf", "palab.ttf", "palai.ttf", "palabi.ttf")),
    "bookantiqua":   ("serif", ("pala.ttf", "palab.ttf", "palai.ttf", "palabi.ttf")),
    "garamond":      ("serif", ("gara.ttf", "garabd.ttf", "garait.ttf", "garabd.ttf")),
    "couriernew":    ("mono", ("cour.ttf", "courbd.ttf", "couri.ttf", "courbi.ttf")),
    "courier":       ("mono", ("cour.ttf", "courbd.ttf", "couri.ttf", "courbi.ttf")),
    "consolas":      ("mono", ("consola.ttf", "consolab.ttf", "consolai.ttf", "consolaz.ttf")),
    "lucidaconsole": ("mono", ("lucon.ttf",) * 4),
    # Familias de otros sistemas: no están en Windows, pero dicen su tipo.
    "notosans": ("sans", ()), "liberationsans": ("sans", ()), "opensans": ("sans", ()),
    "roboto": ("sans", ()), "dejavusans": ("sans", ()), "carlito": ("sans", ()),
    "notoserif": ("serif", ()), "liberationserif": ("serif", ()), "dejavuserif": ("serif", ()),
    "caladea": ("serif", ()), "centuryschoolbook": ("serif", ()),
    "notosansmono": ("mono", ()), "liberationmono": ("mono", ()),
    "dejavusansmono": ("mono", ()),
}
# La más parecida del sistema cuando no se conoce la fuente del documento.
_PARECIDAS = {"sans": "arial", "serif": "timesnewroman", "mono": "couriernew"}
_NOMBRE_NOTO = {"sans": "Noto Sans", "serif": "Noto Serif", "mono": "Noto Sans Mono"}
# Base-14 de MuPDF, solo por si faltase el archivo de Noto.
_BASE14 = {
    "serif": ("tiro", "tibo", "tiit", "tibi"),
    "mono":  ("cour", "cobo", "coit", "cobi"),
    "sans":  ("helv", "hebo", "heit", "hebi"),
}
# Si la fuente elegida no tiene algún carácter se prueban estas, por orden.
_FALLBACKS = ("sans", "serif", "mono")


def _fonts_dir() -> str:
    return os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")


def _system_font(key: str, bold: bool, italic: bool):
    """La fuente de Windows de esa familia, o None si no está instalada."""
    tipo_archivos = _FAMILIES.get(key)
    if not tipo_archivos or not tipo_archivos[1]:
        return None
    archivo = tipo_archivos[1][_variant(bold, italic)]
    return _load(os.path.join(_fonts_dir(), archivo))

_font_cache: dict = {}


# ── Fuentes ────────────────────────────────────────────────────────────────── #

def family_key(name: str) -> str:
    """«BCDEEE+TimesNewRomanPS-BoldMT» → «timesnewroman»."""
    n = _SUBSET.sub("", name or "")
    n = re.split(r"[,\-]", n)[0]
    n = re.sub(r"[^A-Za-z]", "", n).lower()
    # Se van quitando los sufijos de estilo, pero en cuanto queda una familia
    # conocida se para: si no, «timesnewromanpsmt» acabaría en «timesnew»
    # porque «roman» también es un sufijo de estilo.
    while n not in _FAMILIES:
        for w in _STYLE_WORDS:
            if n.endswith(w) and len(n) > len(w):
                n = n[: -len(w)]
                break
        else:
            break
    return n


def display_name(name: str) -> str:
    """Nombre de la fuente tal y como se le enseña al usuario. Las Type 3 no
    tienen nombre: MuPDF devuelve su referencia («Type3 (6 0 R)»)."""
    n = _SUBSET.sub("", name or "")
    return "Type 3 (del documento)" if n.startswith("Type3") else n


def style_from_name(name: str) -> tuple[bool, bool]:
    """Negrita y cursiva deducidas del propio nombre de la fuente."""
    low = (name or "").lower()
    bold = "bold" in low or "black" in low or "heavy" in low
    italic = "italic" in low or "oblique" in low
    return bold, italic


def _variant(bold: bool, italic: bool) -> int:
    return (1 if bold else 0) + (2 if italic else 0)


def _load(path: str):
    if path not in _font_cache:
        try:
            _font_cache[path] = fitz.Font(fontfile=path)
        except Exception:
            _font_cache[path] = None
    return _font_cache[path]


def _base14(flags: int, bold: bool, italic: bool) -> fitz.Font:
    return fitz.Font(_BASE14[_kind(flags)][_variant(bold, italic)])


def _kind(flags: int, key: str = "") -> str:
    """sans · serif · mono: por la familia conocida o, si no, por los flags."""
    conocida = _FAMILIES.get(key)
    return (conocida[0] if conocida else
            ("mono" if flags & FLAG_MONO else "serif" if flags & FLAG_SERIF else "sans"))


_RE_ESTILO_FIN = re.compile(r"\s+(Regular|Bold|Italic|Oblique|BoldItalic|Medium|Light)$", re.I)


def _qt_family(font_name: str) -> str:
    """«Times New Roman Italic» → «Times New Roman» (lo que entiende Qt)."""
    nombre = font_name or ""
    anterior = None
    while nombre != anterior:
        anterior, nombre = nombre, _RE_ESTILO_FIN.sub("", nombre).strip()
    return nombre


def family_for(name: str, flags: int = 0, bold: bool = False, italic: bool = False) -> str:
    """(r40) Familia con la que se reescribirá un texto de fuente `name`: la
    misma del documento si está en Windows, si no la más parecida, y si tampoco
    la Noto correspondiente. El editor en pantalla la usa para que lo que se
    teclea se vea igual que lo que quedará en el PDF."""
    key = family_key(name)
    tipo = _kind(flags, key)
    f = _system_font(key, bold, italic) or _system_font(_PARECIDAS[tipo], bold, italic)
    return _qt_family(f.name) if f is not None else icons.noto_family(tipo)


def _noto(kind: str, bold: bool, italic: bool):
    return _load(icons.noto_path(kind, bold, italic))


def _noto_label(kind: str, bold: bool, italic: bool) -> str:
    estilo = ("negrita " if bold else "") + ("cursiva" if italic and kind != "mono" else "")
    return f"{_NOMBRE_NOTO[kind]} {estilo}".strip()


def resolve_font(name: str, flags: int = 0, bold: bool | None = None,
                 italic: bool | None = None) -> tuple[fitz.Font, str]:
    """Devuelve (fuente utilizable para escribir, nombre legible de lo que se usó).

    La fuente incrustada del PDF no se puede usar: los subconjuntos vienen sin
    `cmap` y todos los caracteres darían el glifo 0 (invariante 32)."""
    n_bold, n_italic = style_from_name(name)
    bold = (flags & FLAG_BOLD != 0 or n_bold) if bold is None else bold
    italic = (flags & FLAG_ITALIC != 0 or n_italic) if italic is None else italic
    key = family_key(name)
    kind = _kind(flags, key)
    # 1) la MISMA fuente del documento, si está instalada en Windows
    f = _system_font(key, bold, italic)
    if f is not None:
        return f, f"{_qt_family(f.name)} (la del documento)"
    # 2) la más parecida del sistema
    f = _system_font(_PARECIDAS[kind], bold, italic)
    if f is not None:
        return f, f"{_qt_family(f.name)} (la más parecida del sistema)"
    # 3) la fuente base de la app
    f = _noto(kind, bold, italic)
    if f is not None:
        return f, _noto_label(kind, bold, italic)
    return _base14(flags, bold, italic), "fuente base del PDF"


def _covering_font(text: str, font: fitz.Font, flags: int,
                   bold: bool, italic: bool) -> tuple[fitz.Font, str, str]:
    """Si `font` no tiene todos los caracteres, busca una que sí.
    Devuelve (fuente, nombre, caracteres que siguen faltando)."""
    def missing(f: fitz.Font) -> str:
        return "".join(dict.fromkeys(
            c for c in text if c not in "\r\n\t" and not f.has_glyph(ord(c))))

    falta = missing(font)
    if not falta:
        return font, "", ""
    for kind in _FALLBACKS:
        alt = _noto(kind, bold, italic)
        if alt is not None and alt is not font and not missing(alt):
            return alt, _noto_label(kind, bold, italic), ""
    alt = _base14(flags, bold, italic)
    if not missing(alt):
        return alt, "fuente base del PDF", ""
    return font, "", falta


# ── Lectura de la página ───────────────────────────────────────────────────── #

class TextBlock:
    """Un párrafo editable de la página: la unidad con la que trabaja la
    herramienta, porque al cambiarle el texto este se **reajusta** a la caja y
    la caja se puede estirar para que quepan más líneas.

    `bbox` va en coordenadas de la página tal y como se ve (con su rotación),
    que son las que usa el visor. `base_*` y `angle` son el mismo dato en la
    página sin girar y solo los usa este módulo para escribir."""

    __slots__ = ("page", "index", "text", "bbox", "base_bbox", "line_rects",
                 "size", "color", "font", "flags", "bold", "italic", "mono",
                 "serif", "mixed", "angle", "line_height", "first_baseline",
                 "last_descent", "align")

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw.get(k))

    def __repr__(self):
        return (f"<TextBlock {self.index} {self.text[:30]!r} {self.font} "
                f"{self.size:.1f} {len(self.line_rects)} líneas>")


def _dominant(spans: list[dict]) -> dict:
    """El tramo con más caracteres: su estilo es el del párrafo."""
    return max(spans, key=lambda s: len(s["chars"]))


def _span_text(span: dict) -> str:
    # MuPDF devuelve U+00A0 donde el PDF separa palabras por posición; al
    # reescribir queremos espacios normales.
    return "".join(c["c"] for c in span["chars"]).replace("\xa0", " ")


def _first_word_width(line: dict) -> float:
    """Ancho de la primera palabra de la línea, medido con las cajas de sus
    propios caracteres: así no hace falta cargar ninguna fuente."""
    ancho = 0.0
    for span in line["spans"]:
        for ch in span["chars"]:
            if ch["c"].isspace():
                return ancho
            ancho += ch["bbox"][2] - ch["bbox"][0]
    return ancho


def _join_lines(lineas: list[dict], textos: list[str], cajas: list[fitz.Rect],
                derecha: float, columna: float) -> str:
    """Une las líneas del párrafo en un texto reajustable.

    Un salto se sustituye por un espacio (para que el texto pueda volver a
    repartirse) solo si **el párrafo llena la columna** y la primera palabra de
    la línea siguiente no habría cabido al final de esta. Si cabía, el salto era
    intencionado —lista, verso, dirección— y se conserva.

    Las dos condiciones hacen falta. Mirar solo si la línea «llega al margen» no
    vale, porque el borde derecho de un párrafo es irregular; y mirar solo si la
    palabra cabía tampoco, porque en una lista corta el ítem más largo define el
    borde del bloque y parece llegar siempre al margen. La referencia buena es
    el bloque de texto más ancho de la página, que es el ancho de columna.

    (r32) Un párrafo más estrecho que la columna (una caja de texto estrecha,
    una columna lateral, o el propio texto que la app ha repartido en un cuadro
    estrecho) también es reajustable si **todas** sus líneas menos la última
    están llenas: si no, al ensanchar el cuadro el texto seguía cortado al ancho
    anterior. Las líneas que empiezan por viñeta o número nunca se unen a la
    anterior. «Cabía» exige caber por el borde derecho (así una sangría de
    primera línea no rompe el párrafo) y por el ancho (así vale también con
    texto centrado)."""
    izquierda = min(c.x0 for c in cajas)
    ancho = derecha - izquierda
    llenas = []
    for i in range(len(textos) - 1):
        hueco = 0.25 * (cajas[i].height or 1.0)          # un espacio, aproximado
        palabra = hueco + _first_word_width(lineas[i + 1])
        # Por el borde derecho (sangría de primera línea) y por el ancho (centrado).
        cabia = (cajas[i].x1 + palabra <= derecha + 2
                 and cajas[i].width + palabra <= ancho + 2)
        llenas.append(not cabia and not _RE_LIST_ITEM.match(textos[i + 1]))
    fluye = len(cajas) > 1 and (ancho >= 0.6 * columna or all(llenas))
    out: list[str] = []
    for i, t in enumerate(textos):
        out.append(t.strip())
        if i < len(llenas):
            out.append(" " if (fluye and llenas[i]) else "\n")
    return "".join(out)


# Comienzo de un elemento de lista: viñeta, «1.», «2)», «a)».
_RE_LIST_ITEM = re.compile(r"\s*(?:[-–—•·▪◦‣*]|\d{1,3}[.)]|[A-Za-z][.)])\s")


def _detect_align(cajas: list[fitz.Rect], caja: fitz.Rect) -> str:
    """izquierda · centro · derecha, mirando cómo se apilan las líneas."""
    if len(cajas) < 2:
        return "left"
    izq = max(abs(c.x0 - caja.x0) for c in cajas)
    der = max(abs(c.x1 - caja.x1) for c in cajas)
    centros = [abs((c.x0 + c.x1) / 2 - (caja.x0 + caja.x1) / 2) for c in cajas]
    if izq <= 1.0:
        return "left"
    if der <= 1.0:
        return "right"
    return "center" if max(centros) <= 2.0 else "left"


def _line_height(origenes: list[tuple], size: float) -> float:
    """Interlineado real del párrafo, medido entre líneas base."""
    saltos = sorted(abs(origenes[i + 1][1] - origenes[i][1])
                    for i in range(len(origenes) - 1))
    if not saltos:
        return round(size * 1.2, 2)
    medio = saltos[len(saltos) // 2]
    return round(medio if medio > 0.1 else size * 1.2, 2)


def text_blocks(page: fitz.Page) -> list[TextBlock]:
    """Párrafos de texto reales de la página, en orden de extracción."""
    ajenos = _painted_by_annots(page)          # en la página SIN girar
    rot = page.rotation
    if rot:
        page.set_rotation(0)
    try:
        raw = page.get_text("rawdict")
    finally:
        if rot:
            page.set_rotation(rot)

    m = page.rotation_matrix
    out: list[TextBlock] = []
    crudos: list[tuple] = []
    for block in raw["blocks"]:
        if block["type"] != 0:
            continue
        lineas, textos, cajas, origenes, todos = [], [], [], [], []
        for line in block["lines"]:
            spans = [s for s in line["spans"] if s["chars"]]
            texto = "".join(_span_text(s) for s in spans)
            if not spans or not texto.strip() or _from_annot(line["bbox"], ajenos):
                continue
            lineas.append(line)
            textos.append(texto)
            cajas.append(fitz.Rect(line["bbox"]))
            origenes.append(tuple(_dominant(spans)["origin"]))
            todos.extend(spans)
        if not lineas:
            continue

        caja = fitz.Rect(cajas[0])
        for c in cajas[1:]:
            caja |= c
        crudos.append((lineas, textos, cajas, origenes, todos, caja))

    # Segunda pasada: el bloque de texto más ancho de la página es el ancho de
    # columna, y con él se sabe qué saltos de línea eran solo de reajuste.
    columna = max((c[5].width for c in crudos), default=0.0)
    for lineas, textos, cajas, origenes, todos, caja in crudos:
        dom = _dominant(todos)
        flags = dom["flags"]
        n_bold, n_italic = style_from_name(dom["font"])
        d = lineas[0]["dir"]
        size = round(dom["size"], 2)
        out.append(TextBlock(
            page=page.number,
            index=len(out),
            text=_join_lines(lineas, textos, cajas, caja.x1, columna),
            bbox=tuple(caja * m),
            base_bbox=tuple(caja),
            line_rects=[tuple(c) for c in cajas],
            angle=math.degrees(math.atan2(-d[1], d[0])),
            size=size,
            color=_rgb(dom["color"]),
            font=display_name(dom["font"]),
            flags=flags,
            bold=bool(flags & FLAG_BOLD) or n_bold,
            italic=bool(flags & FLAG_ITALIC) or n_italic,
            mono=bool(flags & FLAG_MONO),
            serif=bool(flags & FLAG_SERIF),
            mixed=len({(s["font"], round(s["size"], 1), s["color"]) for s in todos}) > 1,
            line_height=_line_height(origenes, size),
            first_baseline=round(origenes[0][1] - caja.y0, 2),
            last_descent=round(max(0.0, caja.y1 - origenes[-1][1]), 2),
            align=_detect_align(cajas, caja),
        ))
    return out


def _painted_by_annots(page: fitz.Page) -> list[fitz.Rect]:
    """Rectángulos de las anotaciones que dibujan texto o imágenes propias.

    `get_text` y `get_image_info` incluyen la apariencia de las anotaciones: el
    texto de un FreeText de la herramienta Texto, el valor de un campo de
    formulario o el glifo de un emoji saldrían como contenido editable, y
    redactarlos no borraría nada (están en su /AP, no en el flujo de la página)
    mientras se escribía un duplicado encima. Invariante 34.

    No se apartan Highlight, Underline, Square… : esos no pintan texto y sus
    rectángulos cubren texto real de la página, que sí debe poder editarse."""
    # Ojo: estos rectángulos van SIEMPRE en la página sin girar, aunque
    # `get_text` devuelva el texto en la página vista (invariante 35).
    rects = [fitz.Rect(w.rect) for w in page.widgets()]
    rects += [fitz.Rect(a.rect) for a in page.annots(types=[
        fitz.PDF_ANNOT_FREE_TEXT, fitz.PDF_ANNOT_STAMP, fitz.PDF_ANNOT_CARET,
        fitz.PDF_ANNOT_FILE_ATTACHMENT])]
    return rects


def _from_annot(bbox, rects: list[fitz.Rect]) -> bool:
    """Se compara por el CENTRO, no por contención: la apariencia se sale del
    rectángulo de su anotación (las mayúsculas de un FreeText suben por encima,
    el valor de un campo es más alto que el campo) y exigir que quepa dentro
    dejaba pasar justo los casos que hay que apartar."""
    r = fitz.Rect(bbox)
    if r.get_area() <= 0:
        return False
    # fitz.Rect no tiene .center en PyMuPDF 1.28 (invariante 23).
    centro = fitz.Point((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2)
    return any(fitz.Rect(o + (-2, -2, 2, 2)).contains(centro) for o in rects)


def _rgb(color: int) -> tuple[float, float, float]:
    return ((color >> 16 & 255) / 255, (color >> 8 & 255) / 255, (color & 255) / 255)


def block_at(blocks: list[TextBlock], point) -> TextBlock | None:
    """El párrafo bajo un punto en coordenadas de la página vista. Si varios se
    solapan gana el más pequeño, que es el que el usuario ha señalado."""
    p = fitz.Point(point)
    dentro = [b for b in blocks if fitz.Rect(b.bbox).contains(p)]
    if not dentro:
        return None
    return min(dentro, key=lambda b: fitz.Rect(b.bbox).get_area())


# ── Redacciones pendientes ya presentes en el PDF ────────────────────────────── #

def _stash_redactions(page: fitz.Page) -> list[dict]:
    """Aparta las marcas de redacción que ya traiga la página (de otra
    aplicación: esta app no tiene herramienta propia de redactar) para que
    `apply_redactions` no las ejecute de paso (invariante 31)."""
    marcas = []
    for a in list(page.annots(types=[fitz.PDF_ANNOT_REDACT])):
        marcas.append({"rect": fitz.Rect(a.rect),
                       "fill": (a.colors or {}).get("fill"),
                       "text": (a.info or {}).get("content") or None})
        page.delete_annot(a)
    return marcas


def _restore_redactions(page: fitz.Page, marcas: list[dict]) -> None:
    for m in marcas:
        page.add_redact_annot(m["rect"], text=m["text"],
                              fill=m["fill"] if m["fill"] else (0, 0, 0))


def _erase(page: fitz.Page, rects: list, *, images: int) -> None:
    """Borra del flujo de contenido lo que cubren `rects`, conservando las
    marcas de redacción que ya trajera el PDF y (según `images`) las imágenes."""
    marcas = _stash_redactions(page)
    try:
        for r in rects:
            page.add_redact_annot(fitz.Rect(r), fill=False)
        page.apply_redactions(
            images=images,
            graphics=fitz.PDF_REDACT_LINE_ART_NONE,
            text=(fitz.PDF_REDACT_TEXT_REMOVE if images == fitz.PDF_REDACT_IMAGE_NONE
                  else fitz.PDF_REDACT_TEXT_NONE))
    finally:
        _restore_redactions(page, marcas)


# ── Edición de texto: reajuste al cuadro ───────────────────────────────────── #

MIN_BOX = 8.0          # ningún cuadro puede quedar más pequeño que esto, en puntos


class EditResult:
    """Qué ha pasado al reescribir un párrafo. Lo que importa para la interfaz
    es si el texto **cabe** en el cuadro: si no, hay que estirarlo."""

    def __init__(self, room=0.0, warnings=None):
        self.room = room            # alto del cuadro, en puntos
        self.needed = 0.0           # alto que pide el texto ya repartido
        self.width = 0.0            # ancho de la línea más larga
        self.lines: list[str] = []  # el texto tal y como ha quedado repartido
        self.box = None             # cuadro final, en coordenadas de la página vista
        self.warnings = warnings or []

    @property
    def overflows(self) -> bool:
        return self.needed > self.room + 0.5

    def __repr__(self):
        return (f"<EditResult {len(self.lines)} líneas, {self.needed:.0f}/{self.room:.0f} pt"
                f"{', SE SALE' if self.overflows else ''}>")


def wrap(text: str, font: fitz.Font, size: float, width: float) -> list[str]:
    """Reparte `text` en las líneas que quepan en `width`.

    Los saltos de línea que haya escrito el usuario se respetan; dentro de cada
    párrafo se corta por palabras. Una palabra más ancha que la caja se deja
    entera y sobresale: partirla sería peor (se avisa aparte)."""
    if width <= 0:
        return [text]
    out: list[str] = []
    for parrafo in text.split("\n"):
        palabras = parrafo.split()
        if not palabras:
            out.append("")
            continue
        linea = palabras[0]
        for palabra in palabras[1:]:
            prueba = f"{linea} {palabra}"
            if font.text_length(prueba, size) <= width:
                linea = prueba
            else:
                out.append(linea)
                linea = palabra
        out.append(linea)
    return out


def needed_height(n_lineas: int, block: TextBlock, font: fitz.Font,
                  size: float) -> float:
    """Alto que pide el texto ya repartido, desde el borde de arriba del cuadro.

    El descendente es el del **propio párrafo** (`last_descent`), no el de la
    fuente: la caja de un bloque es el recuadro ajustado a sus glifos, más baja
    que ascendente+descendente, así que con el de la fuente un párrafo de una
    sola línea salía siempre como «no cabe» sin haber tocado nada. Medido así,
    un texto con las mismas líneas ocupa exactamente el alto de su cuadro."""
    escala = (size / block.size) if block.size else 1.0
    primera = (block.first_baseline if block.first_baseline > 0 else size) * escala
    salto = (block.line_height if block.line_height > 0 else size * 1.2) * escala
    baja = block.last_descent * escala if block.last_descent > 0 else abs(font.descender) * size
    return primera + max(0, n_lineas - 1) * salto + baja


def clamp_box(caja, limite) -> fitz.Rect:
    """Deja el cuadro dentro de `limite` y nunca más pequeño que MIN_BOX.

    Sin esto, al arrastrar un tirador fuera de la hoja el texto se escribía
    fuera de la página: invisible y ya no se podía volver a seleccionar para
    arreglarlo."""
    c, l = fitz.Rect(caja).normalize(), fitz.Rect(limite)
    x0 = min(max(c.x0, l.x0), l.x1 - MIN_BOX)
    y0 = min(max(c.y0, l.y0), l.y1 - MIN_BOX)
    x1 = max(min(c.x1, l.x1), x0 + MIN_BOX)
    y1 = max(min(c.y1, l.y1), y0 + MIN_BOX)
    return fitz.Rect(x0, y0, x1, y1)


def _x_for(align: str, caja: fitz.Rect, ancho: float) -> float:
    if align == "center":
        return caja.x0 + (caja.width - ancho) / 2
    if align == "right":
        return caja.x1 - ancho
    return caja.x0


def delete_block(page: fitz.Page, block: TextBlock) -> None:
    """Borra el párrafo del PDF (no lo tapa: lo quita del flujo de contenido).
    Se borra línea a línea, no por la caja entera, para no llevarse por delante
    texto de al lado que caiga dentro del rectángulo del párrafo."""
    rot = page.rotation
    if rot:
        page.set_rotation(0)
    try:
        _erase(page, block.line_rects, images=fitz.PDF_REDACT_IMAGE_NONE)
    finally:
        if rot:
            page.set_rotation(rot)


def replace_block(page: fitz.Page, block: TextBlock, new_text: str, *,
                  rect=None, size: float | None = None, color=None,
                  bold: bool | None = None, italic: bool | None = None,
                  align: str | None = None,
                  font_name: str | None = None) -> EditResult:
    """Sustituye el párrafo por `new_text`, **reajustándolo** a su cuadro.

    `rect` (en coordenadas de la página vista) permite dar un cuadro nuevo: es
    lo que hace el visor al estirar una esquina, y el texto se reparte en tantas
    líneas como haga falta. Si no cabe, el `EditResult` lo dice (`overflows` y
    `needed`) para que la interfaz avise y el usuario estire más."""
    new_text = (new_text or "").replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")
    avisos: list[str] = []

    size = float(size if size is not None else block.size)
    color = tuple(color) if color is not None else block.color
    bold = block.bold if bold is None else bold
    italic = block.italic if italic is None else italic
    align = align or block.align
    nombre = font_name or block.font

    font, usada = resolve_font(nombre, block.flags, bold, italic)
    font, alt, faltan = _covering_font(new_text, font, block.flags, bold, italic)
    if alt:
        avisos.append(f"«{nombre}» no tiene algunos caracteres; se han escrito con {alt}.")
    elif family_key(nombre) not in _FAMILIES:
        avisos.append(f"«{nombre}» no es una familia conocida; se ha usado {usada}.")
    if faltan:
        avisos.append("No hay ningún glifo para estos caracteres y saldrán en blanco: "
                      + " ".join(faltan))
    if block.mixed:
        avisos.append(f"El párrafo mezclaba varios estilos; se ha reescrito entero "
                      f"con {usada} de {size:g} pt.")

    # Las matrices se piden ANTES de poner la rotación a 0: después son la
    # identidad, y el cuadro que manda el visor se quedaba sin convertir (el
    # texto se repartía en un cuadro girado y aterrizaba donde no era).
    derot, rotm = page.derotation_matrix, page.rotation_matrix
    rot = page.rotation
    if rot:
        page.set_rotation(0)
    try:
        caja = fitz.Rect(rect) * derot if rect is not None else fitz.Rect(block.base_bbox)
        caja = clamp_box(caja, page.rect)
        _erase(page, block.line_rects, images=fitz.PDF_REDACT_IMAGE_NONE)

        lineas = wrap(new_text, font, size, caja.width) if new_text.strip() else []
        res = EditResult(room=caja.height)
        res.lines = lineas
        res.needed = needed_height(len(lineas), block, font, size) if lineas else 0.0
        res.box = tuple(caja * rotm)
        if lineas:
            escala = (size / block.size) if block.size else 1.0
            primera = (block.first_baseline if block.first_baseline > 0 else size) * escala
            salto = (block.line_height if block.line_height > 0 else size * 1.2) * escala
            tw = fitz.TextWriter(page.rect)
            ancho_max = 0.0
            for i, linea in enumerate(lineas):
                if not linea:
                    continue
                ancho = font.text_length(linea, size)
                ancho_max = max(ancho_max, ancho)
                punto = fitz.Point(_x_for(align, caja, ancho), caja.y0 + primera + i * salto)
                tw.append(punto, linea, font=font, fontsize=size)
            res.width = ancho_max
            morph = (fitz.Point(caja.x0, caja.y0), fitz.Matrix(-block.angle))                 if abs(block.angle) > 0.01 else None
            tw.write_text(page, color=color, overlay=True, morph=morph)
    finally:
        if rot:
            page.set_rotation(rot)

    if res.overflows:
        avisos.append(f"El texto necesita {res.needed:.0f} pt de alto y el cuadro tiene "
                      f"{res.room:.0f} pt: estira una esquina hacia abajo para que quepa.")
    if res.width > caja.width + 0.5:
        avisos.append("Hay una palabra más ancha que el cuadro y se sale por el lado.")
    res.warnings = avisos
    return res


# ── Imágenes ───────────────────────────────────────────────────────────────── #

class ImageBox:
    """Una aparición concreta de una imagen en la página.

    `xref` puede repetirse: la misma imagen colocada varias veces comparte
    objeto. Por eso las operaciones de este módulo son por aparición. Si está
    repetida o no lo dice `is_shared`, que recorre el documento entero y por eso
    NO se calcula al leer la página (se leen en cada render)."""

    __slots__ = ("page", "index", "xref", "bbox", "base_bbox", "width", "height",
                 "rotation")

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw.get(k))

    def __repr__(self):
        return f"<ImageBox {self.index} xref={self.xref} {self.width}×{self.height}>"


def _placement_rotation(t) -> int:
    """0/90/180/270 si la imagen está colocada recta; -1 si lleva sesgo."""
    m = fitz.Matrix(t)
    for deg, (a, b, c, d) in ((0, (1, 0, 0, 1)), (90, (0, 1, -1, 0)),
                              (180, (-1, 0, 0, -1)), (270, (0, -1, 1, 0))):
        if (abs(m.a) > 1e-6 or a == 0) and (abs(m.d) > 1e-6 or d == 0):
            sx = math.hypot(m.a, m.b) or 1
            sy = math.hypot(m.c, m.d) or 1
            if (abs(m.a / sx - a) < 1e-3 and abs(m.b / sx - b) < 1e-3
                    and abs(m.c / sy - c) < 1e-3 and abs(m.d / sy - d) < 1e-3):
                return deg
    return -1


def images(page: fitz.Page) -> list[ImageBox]:
    """Imágenes colocadas en la página, una entrada por aparición."""
    ajenos = _painted_by_annots(page)
    rot = page.rotation
    if rot:
        page.set_rotation(0)
    try:
        # _image_infos y no get_image_info: un /ColorSpace roto hace que MuPDF
        # lance al decodificar la página entera (invariante 25).
        info = pdf_compression._image_infos(page)
    finally:
        if rot:
            page.set_rotation(rot)

    m = page.rotation_matrix
    out: list[ImageBox] = []
    for i in info:
        xref = i.get("xref", 0)
        # Sin xref no hay objeto imagen que extraer ni sustituir: son imágenes
        # «en línea» (BI…ID…EI) y las entradas que MuPDF reconstruye al no poder
        # emparejarlas, entre ellas las del sello de una firma, que además llegan
        # con caja vacía. Ofrecerlas sería ofrecer operaciones que fallan
        # (invariante 33).
        if xref <= 0 or fitz.Rect(i["bbox"]).get_area() <= 0:
            continue
        if _from_annot(i["bbox"], ajenos):   # sellos de emoji y apariencias (invariante 34)
            continue
        caja = fitz.Rect(i["bbox"]) * m
        out.append(ImageBox(
            page=page.number, index=len(out), xref=xref,
            bbox=tuple(caja),
            base_bbox=tuple(i["bbox"]),
            width=i.get("width", 0), height=i.get("height", 0),
            rotation=_placement_rotation(i.get("transform", fitz.Identity)),
        ))
    return out


def is_shared(page: fitz.Page, box: ImageBox) -> bool:
    """¿La misma imagen está colocada en más sitios del documento? Recorre todas
    las páginas, así que solo se pregunta cuando hace falta (al enseñar el menú),
    nunca al leer la página."""
    doc = page.parent
    veces = 0
    for pno in range(doc.page_count):
        veces += sum(1 for im in doc.get_page_images(pno) if im[0] == box.xref)
        if veces > 1:
            return True
    return False


def image_at(boxes: list[ImageBox], point) -> ImageBox | None:
    """La imagen bajo un punto; la más pequeña si hay varias superpuestas."""
    p = fitz.Point(point)
    dentro = [b for b in boxes if fitz.Rect(b.bbox).contains(p)]
    if not dentro:
        return None
    return min(dentro, key=lambda b: fitz.Rect(b.bbox).get_area())


def image_bytes(page: fitz.Page, box: ImageBox) -> tuple[str, bytes]:
    """(extensión, datos) de la imagen, para guardarla o reinsertarla."""
    d = page.parent.extract_image(box.xref)
    return d["ext"], d["image"]


def delete_image(page: fitz.Page, box: ImageBox) -> None:
    """Quita ESTA aparición. Las demás copias del mismo xref siguen intactas."""
    rot = page.rotation
    if rot:
        page.set_rotation(0)
    try:
        _erase(page, [box.base_bbox], images=fitz.PDF_REDACT_IMAGE_REMOVE)
    finally:
        if rot:
            page.set_rotation(rot)


def place_image(page: fitz.Page, box: ImageBox, data: bytes | None = None,
                rect=None) -> None:
    """Sustituye o recoloca esta aparición.

    `data` = imagen nueva (None = la misma); `rect` = sitio nuevo en coordenadas
    de la página vista (None = el mismo). Se quita la aparición vieja y se pone
    la nueva **encima del resto del contenido**: el orden de dibujo original no
    se puede conservar."""
    if data is None:
        data = image_bytes(page, box)[1]
    destino = fitz.Rect(rect) * page.derotation_matrix if rect is not None \
        else fitz.Rect(box.base_bbox)
    giro = box.rotation if box.rotation > 0 else 0

    rot = page.rotation
    if rot:
        page.set_rotation(0)
    try:
        _erase(page, [box.base_bbox], images=fitz.PDF_REDACT_IMAGE_REMOVE)
        page.insert_image(destino, stream=data, rotate=giro, overlay=True)
    finally:
        if rot:
            page.set_rotation(rot)
