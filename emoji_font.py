"""
Emojis de la aplicación: fuente **Noto Emoji** (monocroma y vectorial, licencia
OFL), en vendor/fonts/noto-emoji.

Por qué monocroma y no NotoColorEmoji (r40, decisión de Ricardo): al ser de un
solo color el emoji se puede escribir con **el color y la transparencia que
elija el usuario**, como cualquier otro texto, y queda vectorial y ligero
(NotoColorEmoji dibuja mapas de bits a todo color: se puede cambiar la
transparencia, pero no el color).

El emoji se escribe como texto con la fuente incrustada, dentro de la apariencia
de una anotación Stamp:

    q /AGEa gs  r g b rg  BT /AGE <tamaño> Tf 0 <base> Td <glifo> Tj ET Q

`vendor/emoji/emojis.json` (create_emoji_index.py) trae los emojis que la fuente
sabe dibujar, en el orden de Unicode y con sus nombres en español (CLDR). Solo
emojis de un carácter: las secuencias (banderas de países, ZWJ, tonos de piel)
necesitan ligaduras que no se pueden componer escribiendo un glifo suelto.

La anotación es un Stamp con apariencia propia. Su /Rect se escribe
DIRECTAMENTE en el objeto (write_rect): Annot.set_rect() y update() la marcan
como modificada y, al volver a pintar, MuPDF la sustituye por un sello
«APPROVED» de proporción 3,8:1 (invariante 3).
"""
import functools
import json
import os
import re
import unicodedata

import fitz

RAIZ = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(RAIZ, "vendor", "fonts", "noto-emoji", "NotoEmoji-Regular.ttf")
FONT_NAME = "Noto Emoji"
EMOJI_JSON = os.path.join(RAIZ, "vendor", "emoji", "emojis.json")

SUBJECT = "EmojiNoto"
# Emojis de versiones anteriores: EmojiFluent (r36-r39, dibujo de Fluent Emoji),
# EmojiFont (Segoe UI Emoji, r13-r35), EmojiImg (PNG) y EmojiStamp (FreeText).
# Ya no se crean, pero se siguen viendo, moviendo y, al cambiarles el emoji, el
# tamaño, el color o la transparencia, se recrean con la fuente actual.
LEGACY_SUBJECTS = ("EmojiFluent", "EmojiFont", "EmojiImg", "EmojiStamp")
# Stamps con apariencia propia: moverlos o redimensionarlos con write_rect().
# (r68) «FirmaManuscrita» = firma_manuscrita.SUBJECT (literal para no importar
# ese módulo desde aquí).
STAMP_SUBJECTS = (SUBJECT, "EmojiFluent", "EmojiFont", "EmojiImg", "FirmaManuscrita")
# Los que guardan su tamaño en /T (se actualiza al redimensionar).
SIZED_SUBJECTS = (SUBJECT, "EmojiFluent", "EmojiFont")

DEFAULT = "📌"
DEFAULT_COLOR = (0.85, 0.25, 0.10)
DEFAULT_OPACITY = 1.0
AP_MARKER = b"% AG-EMOJI"
_IGNORED = {0xFE0E, 0xFE0F}          # selectores de variación (p. ej. «⚠️»)

GROUPS_ES = {
    "Smileys & Emotion": "Caras y emociones",
    "People & Body": "Personas y cuerpo",
    "Animals & Nature": "Animales y naturaleza",
    "Food & Drink": "Comida y bebida",
    "Travel & Places": "Viajes y lugares",
    "Activities": "Actividades",
    "Objects": "Objetos",
    "Symbols": "Símbolos",
    "Flags": "Banderas",
}


class EmojiFontError(RuntimeError):
    pass


def emoji_key(text: str) -> str:
    """El emoji sin selectores de variación («⚠️» y «⚠» son el mismo dibujo)."""
    return "".join(c for c in (text or "") if ord(c) not in _IGNORED)


def _plain(text: str) -> str:
    """Minúsculas y sin tildes, para buscar «corazon» y encontrar «corazón»."""
    t = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(c for c in t if not unicodedata.combining(c))


@functools.lru_cache(maxsize=1)
def font() -> fitz.Font:
    if not os.path.isfile(FONT_PATH):
        raise EmojiFontError(f"Falta la fuente de emojis: {FONT_PATH}")
    return fitz.Font(fontfile=FONT_PATH)


@functools.lru_cache(maxsize=1)
def catalog() -> tuple[dict, ...]:
    """Todos los emojis disponibles, en el orden de Unicode."""
    if not os.path.isfile(EMOJI_JSON):
        raise EmojiFontError(
            "Falta el índice de emojis (vendor/emoji/emojis.json). "
            "Genéralo con: python create_emoji_index.py")
    with open(EMOJI_JSON, encoding="utf-8") as fh:
        items = json.load(fh)
    for e in items:
        e["key"] = emoji_key(e["emoji"])
        e["label"] = (e.get("name") or "").capitalize()
        e["search"] = _plain(" ".join([e["emoji"], e.get("name", "")]
                                      + e.get("keywords", []) + e.get("es", [])))
    return tuple(items)


@functools.lru_cache(maxsize=1)
def _by_key() -> dict[str, dict]:
    return {e["key"]: e for e in catalog()}


def find(text: str) -> dict | None:
    return _by_key().get(emoji_key(text))


def available(text: str) -> bool:
    try:
        return find(text) is not None
    except EmojiFontError:
        return False


def groups() -> list[tuple[str, str]]:
    """[(grupo, nombre en español)] en el orden del catálogo."""
    vistos = dict.fromkeys(e["group"] for e in catalog())
    return [(g, GROUPS_ES.get(g, g)) for g in vistos]


def search(query: str = "", group: str = "") -> list[dict]:
    """Emojis del grupo (todos si vacío) cuyo nombre o palabras clave, en
    español o en inglés, contienen todas las palabras de `query`."""
    palabras = _plain(query).split()
    return [e for e in catalog()
            if (not group or e["group"] == group)
            and all(p in e["search"] for p in palabras)]


def box_size(text: str, fontsize: float) -> tuple[float, float]:
    """Caja del emoji a `fontsize` pt: el avance del glifo por el alto de la
    fuente (ascendente + descendente), como cualquier letra."""
    f = font()
    return (f.text_length(emoji_key(text)[:1] or " ", fontsize),
            (f.ascender - f.descender) * fontsize)


# ── Estilo guardado en la anotación ───────────────────────────────────────── #

_RE_STYLE = re.compile(r"c#([0-9A-Fa-f]{6})|a([\d.]+)")


def style_token(color, opacity: float) -> str:
    """/Subj de la anotación: «EmojiNoto|c#RRGGBB|a0.75»."""
    r, g, b = (max(0, min(255, int(round(c * 255)))) for c in color[:3])
    return f"{SUBJECT}|c#{r:02X}{g:02X}{b:02X}|a{max(0.0, min(1.0, opacity)):.2f}"


def parse_style(subject: str) -> tuple[tuple, float]:
    """(color, opacidad) de una anotación de emoji; valores por defecto si no
    los lleva (emojis de versiones anteriores)."""
    color, opacidad = DEFAULT_COLOR, DEFAULT_OPACITY
    for hexcol, alfa in _RE_STYLE.findall(subject or ""):
        if hexcol:
            color = tuple(int(hexcol[i:i + 2], 16) / 255 for i in (0, 2, 4))
        elif alfa:
            try:
                opacidad = max(0.0, min(1.0, float(alfa)))
            except ValueError:
                pass
    return color, opacidad


def is_emoji(subject: str) -> bool:
    s = (subject or "").split("|")[0]
    return s == SUBJECT or s in LEGACY_SUBJECTS


def is_stamp(subject: str) -> bool:
    return (subject or "").split("|")[0] in STAMP_SUBJECTS


def is_sized(subject: str) -> bool:
    return (subject or "").split("|")[0] in SIZED_SUBJECTS


# ── Anotación ──────────────────────────────────────────────────────────── #

def write_rect(page: fitz.Page, annot: fitz.Annot, rect: fitz.Rect) -> None:
    """Escribe /Rect sin marcar la anotación como modificada (ver el docstring
    del módulo). `rect` va en coordenadas de página de PyMuPDF."""
    r = fitz.Rect(rect) * ~page.transformation_matrix
    r.normalize()
    page.parent.xref_set_key(annot.xref, "Rect", f"[{r.x0:.4f} {r.y0:.4f} {r.x1:.4f} {r.y1:.4f}]")


def add_emoji_annot(doc: fitz.Document, page_num: int, point: fitz.Point,
                    text: str, fontsize: float, color=DEFAULT_COLOR,
                    opacity: float = DEFAULT_OPACITY) -> fitz.Annot:
    """Inserta `text` con esquina superior izquierda en `point`, a `fontsize` pt,
    con el color y la transparencia indicados."""
    e = find(text)
    if e is None:
        raise EmojiFontError(
            f"El emoji «{text}» no está en Noto Emoji (las banderas de países y "
            "las combinaciones con ZWJ no se pueden insertar).")
    f = font()
    glifo = f.has_glyph(ord(e["emoji"]))
    w, h = box_size(e["emoji"], fontsize)
    page = doc[page_num]
    fxref = page.insert_font(fontname="AGEmoji", fontfile=FONT_PATH)

    r, g, b = (max(0.0, min(1.0, c)) for c in color[:3])
    alfa = max(0.0, min(1.0, float(opacity)))
    base = -f.descender * fontsize                 # línea base dentro de la caja
    ops = (f"q /AGEa gs {r:.4f} {g:.4f} {b:.4f} rg BT /AGE {fontsize:g} Tf "
           f"0 {base:.4f} Td <{glifo:04x}> Tj ET Q")
    recursos = (f"<</Font<</AGE {fxref} 0 R>>"
                f"/ExtGState<</AGEa<</Type/ExtGState/ca {alfa:.4f}/CA {alfa:.4f}>>>>>>")

    rect = fitz.Rect(point.x, point.y, point.x + w, point.y + h)
    annot = page.add_stamp_annot(rect)
    write_rect(page, annot, rect)
    annot._setAP(AP_MARKER + b"\n" + ops.encode("latin-1"))
    ap_x = int(doc.xref_get_key(annot.xref, "AP/N")[1].split()[0])
    doc.xref_set_key(ap_x, "Resources", recursos)
    doc.xref_set_key(ap_x, "BBox", f"[0 0 {w:.4f} {h:.4f}]")
    doc.xref_set_key(ap_x, "Matrix", "[1 0 0 1 0 0]")
    # Metadatos por xref (set_info regeneraría la apariencia). /Name propio para
    # que ningún visor sustituya el emoji por un sello estándar («Approved»…).
    doc.xref_set_key(annot.xref, "Name", "/AGEmoji")
    doc.xref_set_key(annot.xref, "T", fitz.get_pdf_str(f"{fontsize:g}"))
    doc.xref_set_key(annot.xref, "Contents", fitz.get_pdf_str(e["emoji"]))
    doc.xref_set_key(annot.xref, "Subj", fitz.get_pdf_str(style_token(color, opacity)))
    return annot
