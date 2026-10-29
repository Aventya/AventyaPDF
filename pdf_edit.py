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
4. **La fuente nunca cambia** (r148). Se escribe con la del documento: la
   instalada en Windows o, si no está, la incrustada en el PDF cuando tiene
   todos los caracteres (muchos subconjuntos vienen sin `cmap` y darían glifo
   0: invariante 32). Si ninguna sirve, `FuenteNoDisponible` y no se toca la
   página. La negrita o cursiva que la familia no tenga se simulan.
5. **Páginas giradas**: se trabaja con la rotación a 0 y se compensa el ángulo
   de la propia línea (`line["dir"]`), así la línea nueva queda como las demás.
6. **Imágenes: por aparición, no por xref.** `Page.replace_image` y
   `Page.delete_image` actúan sobre el objeto y cambian *todas* las copias de esa
   imagen en todo el documento. Para tocar solo la que señala el usuario se
   redacta su rectángulo con `PDF_REDACT_IMAGE_REMOVE` (invariante 33).

Nada de este módulo toca Qt.
"""
import functools
import math
import os
import re
from typing import NamedTuple

import fitz

import icons
import pdf_compression
from idioma import tr

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
# (r148) Las Noto de la app son esas mismas familias: si el documento las usa,
# se reescribe con ellas.
_NOTO_KEYS = {"notosans": "sans", "notoserif": "serif", "notosansmono": "mono"}
# Sufijos con los que Windows nombra cada estilo de una familia («Calibri Bold»).
_SUFIJOS = {(False, False): ("", "regular"), (True, False): ("bold", "semibold"),
            (False, True): ("italic", "oblique"),
            (True, True): ("bolditalic", "boldoblique", "semibolditalic")}
# Inclinación de la cursiva simulada (unos 12°), como la de Word y Acrobat.
_INCLINACION = 0.21


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
    return tr("Type 3 (del documento)") if n.startswith("Type3") else n


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


class FuenteNoDisponible(ValueError):
    """(r148) Reescribir el párrafo obligaría a cambiar su tipografía: la
    fuente del documento no está en el equipo ni sirve la incrustada, o no
    tiene alguno de los caracteres escritos. No se toca nada."""


class Letra(NamedTuple):
    """Con qué se reescribe un párrafo: siempre la fuente del documento."""
    font: fitz.Font
    nombre: str                 # legible, para la barra y los avisos
    negrita: bool = False       # negrita simulada: la familia no trae la suya
    cursiva: bool = False       # cursiva simulada (inclinada)
    incrustada: bool = False    # la del propio PDF, no una instalada


def _sin_estilo_ps(name: str) -> str:
    """«BCDEEE+TimesNewRomanPS-BoldMT» → «timesnewromanbold»: el nombre
    completo, como lo registra Windows («Times New Roman Bold»)."""
    partes = re.split(r"[,\-]", _SUBSET.sub("", name or ""))
    partes = [re.sub(r"(PS)?(MT)?$", "", p) for p in partes]
    return re.sub(r"[^A-Za-z]", "", "".join(partes)).lower()


@functools.lru_cache(maxsize=1)
def _registro() -> dict[str, str]:
    """(r148) Fuentes instaladas en Windows (para todos y del usuario), por su
    nombre completo sin espacios: {"segoeuisemibold": ruta}. Así se encuentra
    cualquier familia, no solo las de `_FAMILIES`."""
    indice: dict[str, str] = {}
    try:
        import winreg
    except ImportError:
        return indice
    clave = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts"
    for raiz in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            k = winreg.OpenKey(raiz, clave)
        except OSError:
            continue
        with k:
            i = 0
            while True:
                try:
                    nombre, archivo, _t = winreg.EnumValue(k, i)
                except OSError:
                    break
                i += 1
                if not isinstance(archivo, str):
                    continue
                ruta = archivo if os.path.isabs(archivo) else os.path.join(_fonts_dir(), archivo)
                # «Cambria & Cambria Math (TrueType)»: de una .ttc solo se lee
                # la primera cara, así que solo vale el primer nombre.
                primero = re.sub(r"\(.*?\)", "", nombre).split("&")[0]
                indice.setdefault(re.sub(r"[^A-Za-z]", "", primero).lower(), ruta)
    return indice


def _instalada(name: str, bold: bool, italic: bool, exacta: bool):
    """La fuente instalada de esa familia con ese estilo (`exacta`) o, si no,
    cualquier otra cara de la MISMA familia (luego se simula el estilo)."""
    key = family_key(name)
    reg = _registro()
    if exacta:
        nombres = [_sin_estilo_ps(name)] if (bold, italic) == style_from_name(name) else []
        nombres += [key + s for s in _SUFIJOS[(bold, italic)]]
    else:
        nombres = [_sin_estilo_ps(name), key, key + "regular"]
    candidatas = [_load(reg[n]) for n in nombres if n in reg]
    if key in _NOTO_KEYS:
        candidatas.append(_load(icons.noto_path(_NOTO_KEYS[key], bold and exacta, italic and exacta)))
    candidatas.append(_system_font(key, bold and exacta, italic and exacta))
    for f in candidatas:
        # `_FAMILIES` repite el archivo normal donde la familia no tiene el
        # estilo (Impact, Noto Sans Mono cursiva): eso no es «exacta».
        if f is not None and (not exacta or (bool(f.is_bold), bool(f.is_italic)) == (bold, italic)):
            return f
    return None


def _incrustada(doc, name: str, bold: bool, italic: bool, texto: str):
    """(r148) La fuente que trae el propio PDF, si sirve para escribir `texto`:
    los subconjuntos solo tienen los caracteres que ya se usaban y muchos
    vienen sin `cmap` (invariante 32), así que se comprueba carácter a carácter.
    Prefiere la cara del estilo pedido entre las de la misma familia."""
    if doc is None:
        return None
    key = family_key(name)
    caras, vistas = [], set()
    for pno in range(len(doc)):
        try:
            fuentes = doc.get_page_fonts(pno, full=True)
        except Exception:  # noqa: BLE001
            continue
        for xref, _ext, tipo, base, *_ in fuentes:
            if xref and xref not in vistas and tipo != "Type3" and family_key(base) == key:
                vistas.add(xref)
                caras.append((xref, base))
    caras.sort(key=lambda c: style_from_name(c[1]) != (bold, italic))
    for xref, base in caras:
        clave = (id(doc), xref, base)
        if clave not in _font_cache:
            try:
                buf = doc.extract_font(xref)[3]
                _font_cache[clave] = fitz.Font(fontbuffer=buf) if buf else None
            except Exception:  # noqa: BLE001
                _font_cache[clave] = None
        f = _font_cache[clave]
        if f is not None and f.has_glyph(32) and not _faltan(f, texto or "a"):
            return f
    return None


def _faltan(font: fitz.Font, texto: str) -> str:
    return "".join(dict.fromkeys(
        c for c in texto if c not in "\r\n\t" and not font.has_glyph(ord(c))))


def letra(name: str, flags: int = 0, bold: bool | None = None,
          italic: bool | None = None, *, doc=None, texto: str = "") -> Letra:
    """(r148, petición de Ricardo: «nunca puede cambiar la fuente, siempre debe
    mantener la misma fuente original del documento PDF») Con qué se reescribe
    un texto de fuente `name`. Solo con ESA fuente, por orden:

    1. instalada en Windows con el estilo pedido (incluidas las del usuario y
       las equivalentes de las estándar del PDF: Helvetica → Arial);
    2. otra cara instalada de la misma familia, simulando la negrita o la
       cursiva que le falten;
    3. la incrustada en el PDF, si tiene todos los caracteres de `texto`.

    Si no hay ninguna, o le faltan caracteres, lanza `FuenteNoDisponible`:
    nunca se sustituye por otra (hasta r147 se usaba la más parecida)."""
    n_bold, n_italic = style_from_name(name)
    bold = (flags & FLAG_BOLD != 0 or n_bold) if bold is None else bold
    italic = (flags & FLAG_ITALIC != 0 or n_italic) if italic is None else italic
    visible = display_name(name)
    f = _instalada(name, bold, italic, exacta=True)
    simulada = f is None
    if simulada:
        f = _instalada(name, bold, italic, exacta=False)
    if f is not None:
        faltan = _faltan(f, texto)
        if faltan:
            raise FuenteNoDisponible(
                tr("La fuente del documento, {fuente}, no tiene estos caracteres: {faltan}. "
                   "Para no cambiar la tipografía no se pueden escribir.").format(
                    fuente=visible, faltan=" ".join(faltan)))
        nb, ni = (bold and not f.is_bold, italic and not f.is_italic) if simulada else (False, False)
        return Letra(f, _qt_family(f.name), nb, ni)
    f = _incrustada(doc, name, bold, italic, texto)
    if f is not None:
        nb, ni = style_from_name(f.name)
        nb, ni = nb or bool(f.is_bold), ni or bool(f.is_italic)
        return Letra(f, tr("{fuente} (la incrustada en el PDF)").format(fuente=visible),
                     bold and not nb, italic and not ni, True)
    raise FuenteNoDisponible(
        tr("La fuente del documento, {fuente}, no está instalada en este equipo y el PDF "
           "solo trae las letras que ya usaba: para no cambiar la tipografía, este texto "
           "no se puede reescribir. Instala la fuente {fuente} para editarlo.").format(fuente=visible))


def family_for(name: str, flags: int = 0, bold: bool = False, italic: bool = False,
               doc=None) -> str:
    """Familia (para Qt) con la que se ve en pantalla lo que se teclea: la del
    documento. Si no está instalada, su nombre: Qt pondrá una parecida solo en
    el cuadro de escritura, nunca en el PDF."""
    try:
        l = letra(name, flags, bold, italic, doc=doc)
    except FuenteNoDisponible:
        return display_name(name)
    return display_name(name) if l.incrustada else l.nombre


def resolve_font(name: str, flags: int = 0, bold: bool | None = None,
                 italic: bool | None = None, doc=None) -> tuple[fitz.Font, str]:
    """(fuente con la que se escribe, nombre legible). Ver `letra`."""
    l = letra(name, flags, bold, italic, doc=doc)
    return l.font, l.nombre


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


def _inclinada(tw: fitz.TextWriter, punto: fitz.Point, giro) -> fitz.Matrix:
    """(r148) Matriz de `write_text` para la cursiva simulada: inclina la línea
    sobre su línea base y después aplica el giro del párrafo. Va en el espacio
    del PDF (y hacia arriba), como la de `morph`."""
    def sobre(q: fitz.Point, m: fitz.Matrix) -> fitz.Matrix:
        q = q * tw.ictm
        return fitz.Matrix(1, 0, 0, 1, -q.x, -q.y) * m * fitz.Matrix(1, 0, 0, 1, q.x, q.y)
    m = sobre(punto, fitz.Matrix(1, 0, _INCLINACION, 1, 0, 0))
    return m * sobre(giro[0], giro[1]) if giro else m


def replace_block(page: fitz.Page, block: TextBlock, new_text: str, *,
                  rect=None, size: float | None = None, color=None,
                  bold: bool | None = None, italic: bool | None = None,
                  align: str | None = None) -> EditResult:
    """Sustituye el párrafo por `new_text`, **reajustándolo** a su cuadro.

    `rect` (en coordenadas de la página vista) permite dar un cuadro nuevo: es
    lo que hace el visor al estirar una esquina, y el texto se reparte en tantas
    líneas como haga falta. Si no cabe, el `EditResult` lo dice (`overflows` y
    `needed`) para que la interfaz avise y el usuario estire más.

    (r148) Se cambian tamaño, color, negrita y cursiva, **nunca la fuente**: si
    la del documento no puede escribir el texto, `FuenteNoDisponible` y la
    página queda intacta (se comprueba antes de borrar nada)."""
    new_text = (new_text or "").replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")
    avisos: list[str] = []

    size = float(size if size is not None else block.size)
    color = tuple(color) if color is not None else block.color
    bold = block.bold if bold is None else bold
    italic = block.italic if italic is None else italic
    align = align or block.align

    le = letra(block.font, block.flags, bold, italic, doc=page.parent, texto=new_text)
    font, usada = le.font, le.nombre
    if le.negrita or le.cursiva:
        avisos.append(tr("{usada} no tiene versión {estilo}: se ha simulado para no cambiar "
                         "la fuente.").format(usada=usada, estilo=" ".join(
                             e for e, si in ((tr("negrita"), le.negrita),
                                             (tr("cursiva"), le.cursiva)) if si)))
    if block.mixed:
        avisos.append(tr("El párrafo mezclaba varios estilos; se ha reescrito entero "
                      "con {usada} de {size:g} pt.").format(usada=usada, size=size))

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
            giro = ((fitz.Point(caja.x0, caja.y0), fitz.Matrix(-block.angle))
                    if abs(block.angle) > 0.01 else None)
            # (r148) Negrita simulada = relleno y contorno (render mode 2).
            modo = 2 if le.negrita else 0
            tw = fitz.TextWriter(page.rect)
            ancho_max = 0.0
            for i, linea in enumerate(lineas):
                if not linea:
                    continue
                ancho = font.text_length(linea, size)
                ancho_max = max(ancho_max, ancho)
                punto = fitz.Point(_x_for(align, caja, ancho), caja.y0 + primera + i * salto)
                if le.cursiva:
                    # Cada línea se inclina sobre su propia línea base.
                    una = fitz.TextWriter(page.rect)
                    una.append(punto, linea, font=font, fontsize=size)
                    una.write_text(page, color=color, overlay=True, render_mode=modo,
                                   matrix=_inclinada(una, punto, giro))
                else:
                    tw.append(punto, linea, font=font, fontsize=size)
            res.width = ancho_max
            if not le.cursiva:
                tw.write_text(page, color=color, overlay=True, morph=giro, render_mode=modo)
    finally:
        if rot:
            page.set_rotation(rot)

    if res.overflows:
        avisos.append(tr("El texto necesita {needed:.0f} pt de alto y el cuadro tiene "
                      "{room:.0f} pt: estira una esquina hacia abajo para que quepa.").format(needed=res.needed, room=res.room))
    if res.width > caja.width + 0.5:
        avisos.append(tr("Hay una palabra más ancha que el cuadro y se sale por el lado."))
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
