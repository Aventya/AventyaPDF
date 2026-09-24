"""
Compresión de PDF al estilo de Adobe Acrobat («Reducir tamaño del archivo» /
«Optimizar PDF») y de iLovePDF («Comprimir PDF»: extrema, recomendada, baja).

Trabaja sobre una copia en bytes; el documento abierto no se toca. Pasos:

1. Imágenes (lo que más pesa). Para cada imagen dibujada en las páginas se mira
   cada colocación (ppp con que se dibuja) y se reduce su resolución solo si
   supera en 1,5 veces la necesaria (criterio de Acrobat), recomprimiendo a
   JPEG (o sin pérdida en «Baja compresión» si ya era sin pérdida). Si no hace
   falta reducirla, se recomprime solo cuando ahorra al menos un 10 %.
   NO se usa Document.rewrite_images (MuPDF): reconstruye los recursos de todos
   los formularios que recorre y pierde los /Pattern de los grupos con máscara
   suave, lo que estropeaba el sello de las firmas y los emojis de la paleta.
   Aquí solo se reescriben los objetos imagen, en su mismo xref.
1b. (r36) Legibilidad: la app es para documentos que lee una persona. Una
   imagen que parece texto de documento (fondo claro, tinta oscura y pocos
   grises intermedios, `looks_like_text`) nunca baja de TEXT_MIN_PPI ni de
   calidad JPEG TEXT_MIN_JPEG_QUALITY, sea cual sea el nivel. Medido con OCR y a
   ojo: a 75 ppp / JPEG 50 («Extrema») el texto de 6-10 pt dejaba de leerse.
2. Límite de impresión: ninguna colocación baja de 75 ppp al imprimir su página
   ajustada a DIN A4 (en la orientación que mejor encaje). Una página menor que
   A4 se amplía al imprimirla y exige más ppp en el PDF. Las imágenes que ya
   estaban por debajo no se tocan (nunca se amplían).
3. Fuentes: subconjunto de las fuentes incrustadas, salvo en formularios.
4. Se descartan las miniaturas de página incrustadas.
5. Limpieza: objetos duplicados y sin uso (garbage=4), flujos con esfuerzo
   máximo de compresión, flujos de objetos, contenido de página normalizado.
6. Red de seguridad: se pinta el original y el resultado; si aparecen avisos de
   MuPDF nuevos, se repite sin tocar imágenes (y, si hace falta, sin recortar
   fuentes) y se indica en Result.note.

No se tocan: imágenes de 1 bit, máscaras (/ImageMask, /Mask, /Matte), JPX con
SMaskInData, imágenes en línea ni las que solo aparecen en apariencias de
anotaciones o firmas. El cifrado se conserva; las firmas digitales dejan de ser
válidas (el PDF se reescribe).
"""
import math
import re
from dataclasses import dataclass

import fitz

A4 = (595.276, 841.89)
MIN_PRINT_PPI = 75
DOWNSAMPLE_ABOVE = 1.5        # reducir solo si hay 1,5 veces la resolución necesaria
RECOMPRESS_MIN_BYTES = 32 * 1024
RECOMPRESS_MIN_SAVING = 0.10
# (r36) Suelo para imágenes con texto: por debajo, las letras pequeñas se emborronan.
TEXT_MIN_PPI = 150
TEXT_MIN_JPEG_QUALITY = 75


@dataclass(frozen=True)
class Level:
    key: str
    label: str
    description: str
    color_ppi: int          # color y escala de grises
    jpeg_quality: int
    lossless_as_jpeg: bool  # imágenes sin pérdida (PNG, escaneos Flate…) → JPEG


LEVELS = (
    Level("baja", "Baja compresión",
          "Alta calidad, menor reducción: imágenes a 150 ppp, JPEG de calidad alta", 150, 85, False),
    Level("recomendada", "Recomendada",
          "Buena calidad y buena reducción: imágenes a 100 ppp, JPEG de calidad media", 100, 70, True),
    Level("extrema", "Extrema",
          "Máxima reducción, menor calidad: imágenes a 75 ppp en A4, JPEG de calidad baja",
          MIN_PRINT_PPI, 50, True),
)
LEVELS_BY_KEY = {lvl.key: lvl for lvl in LEVELS}
DEFAULT_LEVEL = "recomendada"


@dataclass
class Result:
    data: bytes
    original_size: int
    level: Level
    color_ppi: int                       # objetivo máximo aplicado (con el mínimo A4)
    images_resampled: int
    images_recompressed: int
    min_print_ppi: float | None          # ppp mínimo en A4 tras comprimir
    original_min_print_ppi: float | None
    note: str = ""
    text_images: int = 0                 # (r36) imágenes con texto protegidas

    @property
    def size(self) -> int:
        return len(self.data)

    @property
    def smaller(self) -> bool:
        return self.size < self.original_size

    @property
    def saved_percent(self) -> float:
        return 100.0 * (1 - self.size / self.original_size) if self.original_size else 0.0


def format_size(n: int) -> str:
    if n >= 1024 * 1024:
        return f"{n / (1024 * 1024):.1f} MB".replace(".", ",")
    return f"{n / 1024:.0f} KB"


def a4_fit_factor(rect: fitz.Rect) -> float:
    """Escala con que se imprime la página ajustada a A4 (<1 reduce, >1 amplía)."""
    w, h = rect.width, rect.height
    if w <= 0 or h <= 0:
        return 1.0
    return max(min(A4[0] / w, A4[1] / h), min(A4[1] / w, A4[0] / h))


def print_floor_ppi(doc: fitz.Document) -> int:
    """ppp que necesita en el PDF una imagen de la página con imágenes más
    pequeña para no bajar de 75 ppp en A4 (para informar)."""
    factors = [a4_fit_factor(p.rect) for p in doc if p.get_images()]
    return math.ceil(MIN_PRINT_PPI * max(factors, default=1.0))


def _load_pixmap(doc: fitz.Document, xref: int) -> fitz.Pixmap | None:
    """Pixmap de la imagen. Si su perfil ICC está roto (MuPDF: «invalid ICC
    colorspace», p. ej. /ColorSpace apuntando a un objeto que no es un perfil),
    se sustituye por el espacio Device equivalente según /N (RGB si no se sabe)
    y se reintenta: es lo mismo que hace MuPDF al pintarla, y la deja reparada."""
    try:
        return fitz.Pixmap(doc, xref)
    except Exception:  # noqa: BLE001
        pass
    kind, value = _key(doc, xref, "ColorSpace")
    text = value
    if kind == "xref":
        try:
            text = doc.xref_object(_xref_of((kind, value)), compressed=True)
        except Exception:  # noqa: BLE001
            text = ""
    components = 3
    m = re.search(r"/ICCBased\s+(\d+)\s+0\s+R", text)
    if m:
        try:
            components = int(_key(doc, int(m.group(1)), "N")[1])
        except (TypeError, ValueError):
            components = 3
    device = {1: "/DeviceGray", 4: "/DeviceCMYK"}.get(components, "/DeviceRGB")
    doc.xref_set_key(xref, "ColorSpace", device)
    try:
        return fitz.Pixmap(doc, xref)
    except Exception:  # noqa: BLE001
        doc.xref_set_key(xref, "ColorSpace", value if kind != "xref" else value)
        return None


def _image_infos(page: fitz.Page) -> list[dict]:
    """get_image_info(xrefs=True), tolerando imágenes que no se pueden decodificar:
    PyMuPDF decodifica todas las de la página para emparejarlas por huella MD5 y
    una sola dañada hacía fallar la página entera."""
    try:
        return page.get_image_info(xrefs=True)
    except Exception:  # noqa: BLE001
        pass
    infos = page.get_image_info(hashes=True)
    digests = {}
    for item in page.get_images(full=True):
        pix = _load_pixmap(page.parent, item[0])
        if pix is not None:
            digests[pix.digest] = item[0]
    for info in infos:
        info["xref"] = digests.get(info.get("digest"), 0)
    return infos


def _placements(doc: fitz.Document) -> dict[int, list[tuple[float, float]]]:
    """xref de imagen → [(ppp de la colocación, factor A4 de su página)]."""
    out: dict[int, list[tuple[float, float]]] = {}
    for page in doc:
        s = a4_fit_factor(page.rect)
        for info in _image_infos(page):
            xref = info.get("xref") or 0
            a, b, c, d, _e, _f = info["transform"]
            dw, dh = math.hypot(a, b), math.hypot(c, d)
            if dw <= 0 or dh <= 0 or not info.get("width") or not info.get("height"):
                continue
            ppi = min(info["width"] / (dw / 72), info["height"] / (dh / 72))
            out.setdefault(xref, []).append((ppi, s))
    return out


def min_print_ppi(doc: fitz.Document) -> float | None:
    """ppp de la imagen peor resuelta al imprimir cada página ajustada a A4."""
    values = [ppi / s for uses in _placements(doc).values() for ppi, s in uses]
    return min(values) if values else None


def _key(doc: fitz.Document, xref: int, key: str) -> tuple[str, str]:
    try:
        return doc.xref_get_key(xref, key)
    except Exception:  # noqa: BLE001
        return ("null", "null")


def _xref_of(value: tuple[str, str]) -> int:
    return int(value[1].split()[0]) if value[0] == "xref" else 0


_CLASES = bytes(ord("D") if v <= 100 else ord("L") if v >= 200 else ord("M") for v in range(256))


def looks_like_text(pix: fitz.Pixmap) -> bool:
    """¿Es una imagen de documento con texto (escaneo, captura de un texto)?

    Se mira el histograma de grises: mucho papel claro, algo de tinta oscura y
    pocos grises intermedios (los bordes suavizados de las letras son pocos; una
    fotografía está llena de medios tonos)."""
    if pix.width * pix.height < 64 * 64:
        return False
    gray = pix if (pix.n - pix.alpha) == 1 and not pix.alpha else fitz.Pixmap(fitz.csGRAY, pix)
    muestra = bytes(gray.samples_mv[:: max(1, len(gray.samples_mv) // 400_000)])
    clases = muestra.translate(_CLASES)
    total = len(clases) or 1
    claro, oscuro, medio = (clases.count(c) / total for c in (b"L", b"D", b"M"))
    return claro >= 0.5 and oscuro >= 0.002 and medio <= max(0.12, 3 * oscuro)


def _rewrite_image(doc: fitz.Document, xref: int, scale: float, level: Level,
                   text_scale: float | None = None) -> str:
    """Reduce (scale < 1) o recomprime la imagen en su xref. Devuelve
    'resampled', 'recompressed' o '' si no se toca; con «text» delante
    ('text-resampled'…) si la imagen tenía texto y se le aplicó el suelo de
    legibilidad (`text_scale`, nunca menor que `scale`)."""
    if _key(doc, xref, "ImageMask")[1] == "true" or _key(doc, xref, "BitsPerComponent")[1] == "1":
        return ""
    if _key(doc, xref, "Mask")[0] != "null":
        return ""
    smask = _xref_of(_key(doc, xref, "SMask"))
    if smask and _key(doc, smask, "Matte")[0] != "null":
        return ""
    filters = _key(doc, xref, "Filter")[1]
    if "JPX" in filters and _key(doc, xref, "SMaskInData")[1] not in ("null", "0"):
        return ""
    lossy_source = "DCT" in filters or "JPX" in filters
    raw_size = len(doc.xref_stream_raw(xref) or b"")
    if scale >= 1 and (raw_size < RECOMPRESS_MIN_BYTES or not (lossy_source or level.lossless_as_jpeg)):
        return ""

    pix = _load_pixmap(doc, xref)
    if pix is None:
        return ""
    if pix.alpha:
        pix = fitz.Pixmap(pix, 0)
    if pix.colorspace is None or pix.colorspace.n not in (1, 3):
        pix = fitz.Pixmap(fitz.csRGB, pix)
    quality = level.jpeg_quality
    texto = False
    if text_scale is not None and looks_like_text(pix):
        texto = True
        scale = max(scale, text_scale)
        quality = max(quality, TEXT_MIN_JPEG_QUALITY)
    width, height = pix.width, pix.height
    if scale < 1:
        width, height = max(1, math.ceil(pix.width * scale)), max(1, math.ceil(pix.height * scale))
        pix = fitz.Pixmap(pix, width, height, None)

    as_jpeg = lossy_source or level.lossless_as_jpeg
    data = pix.tobytes("jpeg", jpg_quality=quality) if as_jpeg else pix.samples
    if scale >= 1 and len(data) > raw_size * (1 - RECOMPRESS_MIN_SAVING):
        return "text" if texto else ""
    if scale < 1 and as_jpeg and len(data) >= raw_size:
        return "text" if texto else ""

    mask_pix = None
    if smask:
        mask_pix = fitz.Pixmap(doc, smask)
        if mask_pix.alpha or mask_pix.n != 1:
            mask_pix = fitz.Pixmap(fitz.csGRAY, mask_pix)
        if (mask_pix.width, mask_pix.height) != (width, height):
            mask_pix = fitz.Pixmap(mask_pix, width, height, None)

    doc.update_stream(xref, data, compress=not as_jpeg)
    doc.xref_set_key(xref, "Filter", "/DCTDecode" if as_jpeg else "/FlateDecode")
    for key, value in (("Width", str(width)), ("Height", str(height)), ("BitsPerComponent", "8"),
                       ("ColorSpace", "/DeviceGray" if pix.n == 1 else "/DeviceRGB"),
                       ("DecodeParms", "null"), ("Decode", "null"), ("Intent", "null")):
        doc.xref_set_key(xref, key, value)
    if mask_pix is not None:
        doc.update_stream(smask, mask_pix.samples, compress=True)
        doc.xref_set_key(smask, "Filter", "/FlateDecode")
        for key, value in (("Width", str(width)), ("Height", str(height)), ("BitsPerComponent", "8"),
                           ("ColorSpace", "/DeviceGray"), ("DecodeParms", "null"), ("Decode", "null")):
            doc.xref_set_key(smask, key, value)
    hecho = "resampled" if scale < 1 else "recompressed"
    return f"text-{hecho}" if texto else hecho


def _rewrite_images(doc: fitz.Document, level: Level) -> tuple[int, int, int]:
    resampled = recompressed = text = 0

    def escala(ppi_minimo: int, uses) -> float:
        # Escala que deja cada colocación en max(mínimo, 75 ppp en A4).
        need = max(max(ppi_minimo, MIN_PRINT_PPI * s) / ppi for ppi, s in uses)
        return need if need < 1 / DOWNSAMPLE_ABOVE else 1.0

    for xref, uses in _placements(doc).items():
        if xref <= 0:
            continue                          # imagen en línea: no se puede sustituir
        try:
            done = _rewrite_image(doc, xref, escala(level.color_ppi, uses), level,
                                  text_scale=escala(max(level.color_ppi, TEXT_MIN_PPI), uses))
        except Exception:  # noqa: BLE001 — espacios de color raros, datos dañados…
            done = ""
        text += done.startswith("text")
        resampled += done.endswith("resampled")
        recompressed += done.endswith("recompressed")
    return resampled, recompressed, text


# ── Capa de texto de OCR (r35) ─────────────────────────────────────────────── #
#
# Tesseract escribe cada palabra con posiciones de 5-6 decimales («45.719999 0
# TD») y el tamaño con otros tantos. A 0,1 pt nadie lo nota (ni al seleccionar
# ni al buscar) y el flujo, ya comprimido, ocupa un ~30 % menos. Los «TD»/«Td»
# son desplazamientos RELATIVOS: redondear cada uno por separado acumularía el
# error a lo largo de la línea, así que se redondea la posición acumulada.

_OCR_OPS = {b"q", b"Q", b"cm", b"BT", b"ET", b"Td", b"TD", b"Tf", b"Tz", b"Tr",
            b"Tj", b"TJ", b"BDC", b"BMC", b"EMC", b"Tm", b"TL", b"Tc", b"Tw", b"T*"}
_NUM = rb"[-+]?(?:\d+\.?\d*|\.\d+)"
_RE_OCR_TOKENS = re.compile(
    rb"<<.*?>>|<[0-9A-Fa-f\s]*>|\((?:\\.|[^\\)])*\)|/[^\s/<>\[\]()]+|" + _NUM
    + rb"|[A-Za-z*'\"]+|\[|\]", re.DOTALL)
_RE_OCR_POS = re.compile(
    rb"\bBT\b|(?:" + _NUM + rb"\s+){6}Tm\b|(" + _NUM + rb")\s+(" + _NUM + rb")\s+(Td|TD)\b"
    rb"|(/[^\s/<>\[\]()]+)\s+(" + _NUM + rb")\s+Tf\b")


def _fmt(v: float, decimals: int) -> bytes:
    s = f"{v:.{decimals}f}".rstrip("0").rstrip(".")
    return (s if s not in ("-0", "") else "0").encode()


def compact_ocr_text(stream: bytes) -> bytes | None:
    """Flujo de la capa de OCR con las posiciones a 0,1 pt y el tamaño a 0,01,
    o None si el flujo usa operadores que no son de texto (no se toca)."""
    ops = {t for t in _RE_OCR_TOKENS.findall(stream)
           if t[:1].isalpha() or t[:1] in (b"*", b"'", b'"')}
    if not ops or not ops <= _OCR_OPS or b"Tj" not in ops and b"TJ" not in ops:
        return None
    exacta = [0.0, 0.0]            # posición acumulada real dentro del bloque
    escrita = [0.0, 0.0]           # la que suman los valores ya redondeados

    def sustituir(m: re.Match) -> bytes:
        texto = m.group(0)
        if m.group(3):                                    # tx ty Td / TD
            for i, g in enumerate((1, 2)):
                exacta[i] += float(m.group(g))
            d = [round(exacta[i] - escrita[i], 1) for i in range(2)]
            for i in range(2):
                escrita[i] += d[i]
            return _fmt(d[0], 1) + b" " + _fmt(d[1], 1) + b" " + m.group(3)
        if m.group(4):                                    # /F0 12.23999 Tf
            return m.group(4) + b" " + _fmt(float(m.group(5)), 2) + b" Tf"
        exacta[:] = [0.0, 0.0]                            # BT o Tm: nueva referencia
        escrita[:] = [0.0, 0.0]
        return texto

    return _RE_OCR_POS.sub(sustituir, stream)


def _ocr_forms(doc: fitz.Document) -> list[int]:
    """Formularios que son una capa de texto de OCR: solo operadores de texto
    y TODO el texto invisible («3 Tr»). Se reconocen por eso y no por el nombre
    de la fuente (GlyphLessFont en Tesseract), que `subset_fonts` puede cambiar
    y que otros programas de OCR no usan."""
    out = []
    for xref in range(1, doc.xref_length()):
        try:
            if not doc.xref_is_stream(xref):
                continue
            if "/Subtype/Form" not in doc.xref_object(xref, compressed=True):
                continue
            stream = doc.xref_stream(xref) or b""
            modos = re.findall(rb"(?<![\w.])(\d+)\s+Tr\b", stream)
            if modos and all(m == b"3" for m in modos) and compact_ocr_text(stream) is not None:
                out.append(xref)
        except Exception:  # noqa: BLE001
            continue
    return out


def _has_ocr_layer(doc: fitz.Document) -> bool:
    return bool(_ocr_forms(doc))


def _compact_ocr_layers(doc: fitz.Document) -> int:
    """Compacta los formularios de la capa de texto de OCR. Devuelve cuántos."""
    hechos = 0
    for xref in _ocr_forms(doc):
        try:
            original = doc.xref_stream(xref)
            nuevo = compact_ocr_text(original)
            if nuevo is None or len(nuevo) >= len(original):
                continue
            doc.update_stream(xref, nuevo, compress=True)
            hechos += 1
        except Exception:  # noqa: BLE001 — un formulario raro no para la compresión
            continue
    return hechos


def _open(data: bytes, password: str) -> fitz.Document:
    doc = fitz.open("pdf", data)
    if doc.needs_pass and not (password and doc.authenticate(password)):
        doc.close()
        raise ValueError("El documento está protegido con contraseña.")
    return doc


def _render_warnings(data: bytes, password: str) -> set[str]:
    """Avisos de MuPDF al pintar todas las páginas (con anotaciones)."""
    fitz.TOOLS.reset_mupdf_warnings()
    doc = _open(data, password)
    try:
        for page in doc:
            page.get_pixmap(matrix=fitz.Matrix(0.2, 0.2))
    finally:
        doc.close()
    lines = fitz.TOOLS.mupdf_warnings().splitlines()
    fitz.TOOLS.reset_mupdf_warnings()
    return {l.strip() for l in lines if l.strip() and not l.strip().startswith("... repeated")}


def _run(data: bytes, level: Level, password: str, encryption: dict | None,
         images: bool, fonts: bool) -> tuple[bytes, int, int, int]:
    doc = _open(data, password)
    try:
        resampled = recompressed = text = 0
        if images:
            resampled, recompressed, text = _rewrite_images(doc, level)
        if fonts and not doc.is_form_pdf:
            try:
                doc.subset_fonts()
            except Exception:  # noqa: BLE001
                pass
        try:
            doc.scrub(attached_files=False, clean_pages=False, embedded_files=False,
                      hidden_text=False, javascript=False, metadata=False, redactions=False,
                      remove_links=False, reset_fields=False, reset_responses=False,
                      thumbnails=True, xml_metadata=False)
        except Exception:  # noqa: BLE001
            pass
        kw = dict(garbage=4, deflate=True, deflate_images=True, deflate_fonts=True,
                  clean=True, use_objstms=1, compression_effort=100)
        final = encryption if encryption else {"encryption": fitz.PDF_ENCRYPT_KEEP}
        if not _has_ocr_layer(doc):
            return doc.tobytes(**kw, **final), resampled, recompressed, text
        # (r35) `clean=True` reescribe los números de los flujos en coma flotante
        # de precisión simple («45.700006») y deshace el compactado de la capa de
        # OCR: se limpia primero, se compacta sobre el resultado y se guarda otra
        # vez sin limpiar. El paso intermedio conserva el cifrado original (se
        # reabre con la misma contraseña) y el definitivo aplica el pedido.
        intermedio = doc.tobytes(**kw, encryption=fitz.PDF_ENCRYPT_KEEP)
    finally:
        doc.close()
    doc = _open(intermedio, password)
    try:
        _compact_ocr_layers(doc)
        kw["clean"] = False
        return doc.tobytes(**kw, **final), resampled, recompressed, text
    finally:
        doc.close()


def compress(data: bytes, level: str = DEFAULT_LEVEL, password: str = "",
             encryption: dict | None = None, original_size: int | None = None) -> Result:
    """Comprime `data` con el nivel indicado. `encryption`: opciones de cifrado
    para el guardado (por defecto se conserva el del documento)."""
    lvl = LEVELS_BY_KEY[level]
    doc = _open(data, password)
    try:
        original_min = min_print_ppi(doc)
        color_ppi = max(lvl.color_ppi, print_floor_ppi(doc))
    finally:
        doc.close()
    baseline = _render_warnings(data, password)

    note = ""
    attempts = ((True, True, ""),
                (False, True, "Las imágenes no se han recomprimido: el documento tiene una "
                              "estructura que no lo permite sin dañarlo."),
                (False, False, "Solo se ha optimizado la estructura del PDF: el documento no "
                               "admite recomprimir imágenes ni recortar fuentes sin dañarlo."))
    for images, fonts, attempt_note in attempts:
        out, resampled, recompressed, text = _run(data, lvl, password, encryption, images, fonts)
        check_password = password if not encryption else ""
        try:
            new_warnings = _render_warnings(out, check_password) - baseline
        except ValueError:                     # cifrado nuevo: no se puede comprobar
            new_warnings = set()
        if not new_warnings:
            note = attempt_note
            break
    else:
        note = attempts[-1][2]

    check = fitz.open("pdf", out)
    if check.needs_pass and password:
        check.authenticate(password)
    try:
        result_min = min_print_ppi(check) if not check.needs_pass else None
    finally:
        check.close()
    return Result(out, original_size if original_size else len(data), lvl, color_ppi,
                  resampled, recompressed, result_min, original_min, note, text)
