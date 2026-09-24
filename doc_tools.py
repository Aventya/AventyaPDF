"""
doc_tools.py
Operaciones de documento independientes de la interfaz (solo PyMuPDF):
rangos de páginas, rotación, extracción, división, marcas de agua,
encabezados/pies/Bates, redacción, búsqueda, selección de texto, conversión
desde imágenes, exportación, OCR y metadatos.

Nada de este módulo toca Qt: recibe y devuelve objetos `fitz`, lo que permite
reutilizarlo y probarlo sin arrancar la aplicación.
"""
import functools
import os
import re
from datetime import datetime

import fitz

import icons

# (r40) Fuente base de la app para el texto que añade ella misma (marcas de
# agua, encabezados, pies y numeración Bates): Noto Sans, incluida en vendor/.
BASE_FONT = icons.noto_path("sans")

# (r59) /Subj de las marcas a mano alzada (Ink) de «Resaltar, subrayar o
# tachar»: prefijo + tipo (highlight | underline | strike | squiggly).
FREEHAND_PREFIX = "MANO|"

# Colores por defecto del marcado de texto (RGB 0–1).
MARKUP_COLORS = {
    "highlight": (1.0, 0.92, 0.0),
    "underline": (0.0, 0.47, 0.84),
    "strike":    (0.82, 0.20, 0.22),
    "squiggly":  (0.82, 0.20, 0.22),
}


# ── Rangos de páginas ──────────────────────────────────────────────────────── #

def parse_page_range(text: str, page_count: int) -> list[int]:
    """Convierte "1-3, 5, 8-" en índices base 0. Vacío o "todas" → todas.
    Lanza ValueError con un mensaje legible si el rango no es válido."""
    t = (text or "").strip().lower()
    if t in ("", "todas", "todo", "all", "*"):
        return list(range(page_count))
    out: list[int] = []
    for part in re.split(r"[,;\s]+", t):
        if not part:
            continue
        m = re.fullmatch(r"(\d*)-(\d*)", part)
        if m:
            a = int(m.group(1)) if m.group(1) else 1
            b = int(m.group(2)) if m.group(2) else page_count
        elif part.isdigit():
            a = b = int(part)
        else:
            raise ValueError(f"Rango no válido: «{part}»")
        if a < 1 or b > page_count or a > b:
            raise ValueError(f"Rango fuera del documento (1–{page_count}): «{part}»")
        for i in range(a - 1, b):
            if i not in out:
                out.append(i)
    if not out:
        raise ValueError("El rango no contiene ninguna página")
    return out


# ── Páginas ────────────────────────────────────────────────────────────────── #

def rotate_pages(doc: fitz.Document, pages: list[int], delta: int) -> None:
    for pno in pages:
        page = doc[pno]
        page.set_rotation((page.rotation + delta) % 360)


def extract_pages(doc: fitz.Document, pages: list[int]) -> fitz.Document:
    new = fitz.open()
    for pno in pages:
        new.insert_pdf(doc, from_page=pno, to_page=pno)
    return new


def split_every(doc: fitz.Document, n: int) -> list[fitz.Document]:
    n = max(1, int(n))
    parts = []
    for start in range(0, len(doc), n):
        part = fitz.open()
        part.insert_pdf(doc, from_page=start, to_page=min(start + n, len(doc)) - 1)
        parts.append(part)
    return parts


def insert_pdf_at(doc: fitz.Document, src: fitz.Document, position: int) -> int:
    """Inserta todas las páginas de `src` antes del índice `position`.
    Devuelve el número de páginas insertadas."""
    position = max(0, min(position, len(doc)))
    doc.insert_pdf(src, start_at=position)
    return len(src)


# ── Texto sobre páginas (con soporte de páginas giradas) ───────────────────── #

def _visible_to_unrotated(page: fitz.Page, pt: fitz.Point) -> fitz.Point:
    """Las inserciones de contenido trabajan en coordenadas de la página sin
    girar; los usuarios piensan en la página tal como se ve."""
    return pt * page.derotation_matrix


def add_watermark(doc: fitz.Document, pages: list[int], text: str,
                  fontsize: float = 60, color: tuple = (0.6, 0.6, 0.6),
                  opacity: float = 0.25, angle: float = 45,
                  fontfile: str = "") -> None:
    font = fitz.Font(fontfile=fontfile or BASE_FONT)
    for pno in pages:
        page = doc[pno]
        vis = page.rect
        center = _visible_to_unrotated(page, fitz.Point(vis.width / 2, vis.height / 2))
        width = font.text_length(text, fontsize=fontsize)
        pos = fitz.Point(center.x - width / 2, center.y + fontsize * 0.35)
        tw = fitz.TextWriter(page.rect)
        tw.append(pos, text, font=font, fontsize=fontsize)
        # Matrix(θ) gira en sentido horario en coordenadas con y hacia abajo;
        # se compensa además el giro de visualización de la página.
        tw.write_text(page, color=color, opacity=opacity, overlay=True,
                      morph=(center, fitz.Matrix(-(angle + page.rotation))))


@functools.lru_cache(maxsize=1)
def _base_font() -> fitz.Font:
    return fitz.Font(fontfile=BASE_FONT)


def _expand_tokens(template: str, n: int, total: int, bates: str) -> str:
    return (template.replace("{n}", str(n))
                    .replace("{total}", str(total))
                    .replace("{fecha}", datetime.now().strftime("%d/%m/%Y"))
                    .replace("{bates}", bates))


def add_header_footer(doc: fitz.Document, pages: list[int], spec: dict) -> None:
    """spec: hl, hc, hr, fl, fc, fr (plantillas con {n} {total} {fecha} {bates}),
    fontsize, color, margin, bates_prefix, bates_start, bates_digits."""
    fs = float(spec.get("fontsize", 10))
    color = spec.get("color", (0, 0, 0))
    margin = float(spec.get("margin", 28))
    prefix = spec.get("bates_prefix", "")
    start = int(spec.get("bates_start", 1))
    digits = int(spec.get("bates_digits", 6))
    total = len(doc)
    for k, pno in enumerate(pages):
        page = doc[pno]
        vis = page.rect
        bates = f"{prefix}{start + k:0{digits}d}"
        slots = {
            "hl": ("l", margin + fs), "hc": ("c", margin + fs), "hr": ("r", margin + fs),
            "fl": ("l", vis.height - margin), "fc": ("c", vis.height - margin),
            "fr": ("r", vis.height - margin),
        }
        for key, (align, y) in slots.items():
            tpl = spec.get(key, "")
            if not tpl:
                continue
            s = _expand_tokens(tpl, pno + 1, total, bates)
            w = _base_font().text_length(s, fs)
            if align == "l":
                x = margin
            elif align == "c":
                x = (vis.width - w) / 2
            else:
                x = vis.width - margin - w
            pt = _visible_to_unrotated(page, fitz.Point(x, y))
            page.insert_text(pt, s, fontsize=fs, fontname="AGBase", fontfile=BASE_FONT,
                             color=color, rotate=page.rotation)


# ── Búsqueda y selección de texto ──────────────────────────────────────────── #

def bytes_with_subset_fonts(doc: fitz.Document, kw: dict, password: str = "") -> bytes:
    """`doc.tobytes(**kw)`, pero con las fuentes Noto que ha incrustado la app
    reducidas a los caracteres usados (r36).

    La herramienta Texto y «Editar contenido» incrustan la fuente Noto entera
    (~350 KB comprimida por variante). Se recorta en una COPIA: si se recortase
    el documento abierto, el siguiente texto escrito con esa fuente reutilizaría
    el subconjunto y le faltarían letras. No se hace en formularios (los campos
    necesitan la fuente completa para escribir), igual que la compresión."""
    data = doc.tobytes(**kw)
    try:
        if doc.is_form_pdf or not any(
                "Noto" in (f[3] or "") and "+" not in (f[3] or "")
                for page in doc for f in page.get_fonts(full=True)):
            return data
        copia = fitz.open("pdf", data)
        if copia.needs_pass and not (password and copia.authenticate(password)):
            return data
        copia.subset_fonts()
        final = dict(kw)
        if "encryption" in final and final["encryption"] not in (fitz.PDF_ENCRYPT_KEEP,
                                                                  fitz.PDF_ENCRYPT_NONE):
            pass                                  # cifrado nuevo: se vuelve a aplicar
        elif copia.is_encrypted or kw.get("encryption") == fitz.PDF_ENCRYPT_KEEP:
            final["encryption"] = fitz.PDF_ENCRYPT_KEEP
        out = copia.tobytes(**final)
        copia.close()
        return out if len(out) < len(data) else data
    except Exception:  # noqa: BLE001 — ante cualquier duda, el guardado normal
        return data


def search_document(doc: fitz.Document, needle: str,
                    max_hits: int = 5000) -> list[tuple[int, fitz.Rect]]:
    hits: list[tuple[int, fitz.Rect]] = []
    if not needle:
        return hits
    for pno in range(len(doc)):
        for r in doc[pno].search_for(needle):
            hits.append((pno, fitz.Rect(r)))
            if len(hits) >= max_hits:
                return hits
    return hits


def _rect_distance(r, pt: fitz.Point) -> float:
    dx = max(r[0] - pt.x, 0, pt.x - r[2])
    dy = max(r[1] - pt.y, 0, pt.y - r[3])
    return dx * dx + 4 * dy * dy   # la distancia vertical pesa más


def word_selection(page: fitz.Page, p1: fitz.Point, p2: fitz.Point,
                   words: list | None = None,
                   max_start_dist: float = 24.0) -> tuple[list[fitz.Rect], str]:
    """Selección de texto «como en un visor»: todas las palabras en orden de
    lectura entre la más cercana a p1 y la más cercana a p2. Devuelve un
    rectángulo por línea y el texto seleccionado. Si p1 está a más de
    `max_start_dist` puntos de cualquier palabra no se selecciona nada (evita
    seleccionar texto lejano al arrastrar desde un margen)."""
    if words is None:
        words = page.get_text("words")
    if not words:
        return [], ""
    i1 = min(range(len(words)), key=lambda i: _rect_distance(words[i], p1))
    if _rect_distance(words[i1], p1) > max_start_dist ** 2:
        return [], ""
    i2 = min(range(len(words)), key=lambda i: _rect_distance(words[i], p2))
    lo, hi = min(i1, i2), max(i1, i2)
    lines = _visual_lines(words[lo:hi + 1])
    rects = [fitz.Rect(l[0][0], min(w[1] for w in l), l[-1][2], max(w[3] for w in l))
             for l in lines]
    return rects, _lines_to_text(lines)


# ── Texto copiado (r34) ────────────────────────────────────────────────────── #
#
# Antes cada línea de MuPDF (bloque, línea) era una línea del texto copiado.
# Con la capa de OCR de un escaneo algo torcido MuPDF parte una misma línea
# visual en varios trozos, y al pegar en el Bloc de notas salían saltos en
# mitad de las frases; además cada renglón de un párrafo acababa en un salto.
# Ahora las líneas se reconstruyen por geometría y los renglones de un mismo
# párrafo se unen con un espacio, como hace Acrobat.

# Comienzo de un elemento de lista: viñeta, «1.», «2)», «a)».
_RE_LIST_ITEM = re.compile(r"(?:[-–—•·▪◦‣*]|\d{1,3}[.)]|[A-Za-z][.)])$")


def _visual_lines(words: list) -> list[list]:
    """Agrupa las palabras (en orden de extracción) en líneas visuales: una
    palabra sigue en la línea si solapa en vertical al menos la mitad con la
    palabra anterior y no vuelve hacia la izquierda."""
    lines: list[list] = []
    for w in words:
        if lines:
            last = lines[-1][-1]
            alto = min(w[3] - w[1], last[3] - last[1]) or 1.0
            solape = min(w[3], last[3]) - max(w[1], last[1])
            if solape >= 0.5 * alto and w[0] >= last[0] - 0.5 * alto:
                lines[-1].append(w)
                continue
        lines.append([w])
    return lines


def _lines_to_text(lines: list[list]) -> str:
    """Une los renglones de un mismo párrafo con un espacio y deja salto solo
    donde el autor lo puso: la línea no llegaba al margen (cabía la palabra
    siguiente), la siguiente empieza por viñeta o número, cambia la sangría,
    o hay más separación de la normal (esto último deja una línea en blanco)."""
    if not lines:
        return ""
    info = []
    for l in lines:
        alturas = sorted(w[3] - w[1] for w in l)
        info.append({
            "text": " ".join(w[4] for w in l),
            "x0": l[0][0], "x1": l[-1][2],
            "yc": sum((w[1] + w[3]) / 2 for w in l) / len(l),
            "h": alturas[len(alturas) // 2] or 1.0,
            "first_w": l[0][2] - l[0][0],
            "first": l[0][4],
        })
    # Interlineado normal: el menor salto habitual entre renglones seguidos.
    saltos = sorted(b["yc"] - a["yc"] for a, b in zip(info, info[1:])
                    if 0.3 * max(a["h"], b["h"]) < b["yc"] - a["yc"] <= 2.6 * max(a["h"], b["h"]))
    salto_normal = saltos[len(saltos) // 4] if saltos else None

    def margen_derecho(linea) -> float:
        """Borde derecho de la columna: el renglón más largo de la selección
        que empieza más o menos a la misma altura horizontal."""
        return max(o["x1"] for o in info if abs(o["x0"] - linea["x0"]) <= 3 * linea["h"])

    out = [info[0]["text"]]
    for prev, cur in zip(info, info[1:]):
        h = max(prev["h"], cur["h"])
        dy = cur["yc"] - prev["yc"]
        guion = (prev["text"].endswith("-") and len(prev["text"]) > 1
                 and prev["text"][-2].isalpha() and cur["first"][:1].islower())
        blanco = dy > 2.6 * h or (salto_normal is not None and dy > 1.45 * salto_normal)
        if dy <= 0.3 * h or blanco:                        # otra columna o hueco grande
            corte = True
        elif _RE_LIST_ITEM.match(cur["first"]):
            corte = True
        elif cur["x0"] - prev["x0"] > 1.5 * h:             # sangría: empieza párrafo
            corte = True
        elif guion:                                        # «obligar-» + «se»
            corte = False
        else:                                              # ¿cabía la palabra siguiente?
            corte = (prev["x1"] + 0.3 * h + cur["first_w"]
                     <= margen_derecho(prev) + 0.25 * h)
        if corte:
            out.append(("\n\n" if blanco and dy > 0.3 * h else "\n") + cur["text"])
        elif guion:
            out[-1] = out[-1][:-1]
            out.append(cur["text"])
        else:
            out.append(" " + cur["text"])
    return "".join(out)


# ── Conversión y exportación ───────────────────────────────────────────────── #

IMAGE_FILTER = "Imágenes (*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff *.webp)"


def images_to_pdf(paths: list[str]) -> fitz.Document:
    out = fitz.open()
    for path in paths:
        img = fitz.open(path)
        pdf_bytes = img.convert_to_pdf()
        img.close()
        img_pdf = fitz.open("pdf", pdf_bytes)
        out.insert_pdf(img_pdf)
        img_pdf.close()
    return out


def merge_pdfs(paths: list[str]) -> fitz.Document:
    """(r55) Combina varios PDF completos, en el orden dado, en un documento
    nuevo. A diferencia de `merge_pdf()` de main_window.py (que añade UN PDF
    al final del documento ya abierto), esta función parte de cero y no toca
    ningún documento existente: la usa el menú contextual del Explorador de
    Windows para combinar los archivos seleccionados sin tener que abrir antes
    ninguno de ellos en la aplicación."""
    out = fitz.open()
    for path in paths:
        src = fitz.open(path)
        if src.needs_pass:
            src.close()
            raise ValueError(f"«{os.path.basename(path)}» está protegido con contraseña.")
        out.insert_pdf(src)
        src.close()
    return out


def export_images(doc: fitz.Document, pages: list[int], folder: str,
                  basename: str, dpi: int = 150, fmt: str = "png") -> list[str]:
    written = []
    for pno in pages:
        pix = doc[pno].get_pixmap(dpi=dpi, alpha=False)
        path = os.path.join(folder, f"{basename}_p{pno + 1:03d}.{fmt}")
        pix.save(path)
        written.append(path)
    return written


def export_text(doc: fitz.Document, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for pno, page in enumerate(doc):
            f.write(f"──────── Página {pno + 1} ────────\n")
            f.write(page.get_text("text", sort=True))
            f.write("\n")


def export_docx(pdf_path: str, docx_path: str) -> None:
    """Usa `pdf2docx` (obligatorio desde r33; lo instala dependencias.py)."""
    try:
        from pdf2docx import Converter
    except ImportError as e:
        raise RuntimeError(
            "La exportación a Word necesita el componente «pdf2docx», que no se ha "
            "podido instalar.\nCierra y vuelve a abrir la aplicación con conexión a "
            "Internet para que se instale solo.") from e
    cv = Converter(pdf_path)
    try:
        cv.convert(docx_path)
    finally:
        cv.close()


# (El OCR vive en pdf_ocr.py: capa de texto invisible sobre la página original.)



# ── Firmas, formularios, metadatos ─────────────────────────────────────────── #

def signature_widgets(doc: fitz.Document) -> list[tuple[int, str, fitz.Rect]]:
    out = []
    try:
        if doc.get_sigflags() < 1:
            return out
    except Exception:
        pass
    for pno, page in enumerate(doc):
        for w in page.widgets():
            if w.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE:
                out.append((pno, w.field_name or "", fitz.Rect(w.rect)))
    return out


def signed_count(doc: fitz.Document) -> int:
    """(r61) Firmas de verdad: campos de firma con valor (/V). Un recuadro de
    firma vacío (de un formulario, o el que queda al quitar una firma) no
    cuenta: antes el aviso decía «firmado digitalmente» por él."""
    n = 0
    for pno, _name, _r in signature_widgets(doc):
        for w in doc[pno].widgets(types=[fitz.PDF_WIDGET_TYPE_SIGNATURE]):
            if doc.xref_get_key(w.xref, "V")[0] not in ("null", "unknown") and w.field_name == _name:
                n += 1
                break
    return n


def has_signatures(doc: fitz.Document) -> bool:
    try:
        return doc.get_sigflags() >= 1 and signed_count(doc) > 0
    except Exception:
        return False


def flatten(doc: fitz.Document) -> None:
    """Integra anotaciones y campos en el contenido (dejan de ser editables)."""
    if not hasattr(doc, "bake"):
        raise RuntimeError("Tu versión de PyMuPDF no permite aplanar (necesita ≥ 1.23.8).")
    doc.bake(annots=True, widgets=True)


METADATA_FIELDS = [
    ("title", "Título"), ("author", "Autor"), ("subject", "Asunto"),
    ("keywords", "Palabras clave"), ("creator", "Aplicación creadora"),
    ("producer", "Productor PDF"),
]


def annotation_summary(doc: fitz.Document) -> list[dict]:
    """Lista plana de comentarios para el panel lateral."""
    names = {
        "FreeText": "Texto", "Text": "Nota", "Ink": "Marca a mano alzada", "Square": "Rectángulo",
        "Stamp": "Sello", "Highlight": "Resaltado", "Underline": "Subrayado",
        "StrikeOut": "Tachado", "Squiggly": "Ondulado",
        "Circle": "Elipse", "Line": "Línea", "Polygon": "Polígono",
        "PolyLine": "Polilínea", "Caret": "Inserción",
    }
    out = []
    for pno, page in enumerate(doc):
        for i, a in enumerate(page.annots()):
            atype = a.type[1]
            if atype in ("Link", "Popup"):
                continue
            info = a.info
            content = info.get("content", "") or ""
            if info.get("subject") in ("EmojiFont", "EmojiImg", "EmojiStamp"):
                atype_label = "Emoji"
            elif (info.get("subject") or "").startswith("FirmaManuscrita"):
                atype_label = "Firma manuscrita"
            else:
                atype_label = names.get(atype, atype)
            out.append({
                "page": pno, "idx": i, "type": atype, "label": atype_label,
                "content": content.strip().replace("\n", " ")[:120],
                "author": info.get("title", "") if atype in ("Text", "Highlight",
                          "Underline", "StrikeOut", "Squiggly") else "",
                "rect": fitz.Rect(a.rect),
            })
    return out
