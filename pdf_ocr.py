"""
OCR de alta precisión: capa de texto invisible sobre la página ORIGINAL.

Por qué así (lo que hacen Acrobat y OCRmyPDF), frente al método anterior que
solo trataba páginas sin ningún texto y las sustituía por imagen + texto:

1. Todas las páginas: el texto que aparece en imágenes, escaneos o convertido en
   dibujo se reconoce aunque la página ya tenga texto seleccionable.
2. Orientación: «tesseract --psm 0» (OSD) dice cuánto hay que girar la página
   para que el texto quede derecho; el OCR se hace en esa orientación y la
   rotación original se restaura (la capa queda alineada igualmente).
   (r60) El OSD se equivoca con frecuencia (180° en fotos de documentos): su
   propuesta se comprueba reconociendo en las dos orientaciones.
3. Imagen para Tesseract: gris a 400 ppp, con el texto que ya es seleccionable
   tapado en blanco (no se duplica). La capa de un OCR anterior (texto
   invisible) no cuenta como texto real: se sustituye (r60).
4. (r60) Enderezado si la página está torcida ≥ 1°, umbralizado Sauvola y
   tesseract.exe directamente (el motor de MuPDF no deja elegir nada de esto).
   Medido con un banco de 45 escaneos simulados: F1 de palabras 0,759 → 0,922.
5. Modelos «tessdata_best» (los más precisos), ver tesseract_setup.
6. Tesseract devuelve solo la capa de texto invisible (textonly_pdf) y se
   superpone con show_pdf_page: la página conserva imagen, vectores,
   anotaciones, formularios y cifrado, y el cambio se puede deshacer.
"""
import csv
import math
import os
import re
import subprocess
import tempfile

import cv2
import fitz
import numpy as np

import tesseract_setup

DPI = 400
OSD_DPI = 150
MIN_OSD_CONFIDENCE = 0.3
# Límites de render: muchos escáneres guardan la página con tamaño en puntos =
# píxeles (p. ej. 2480 × 3508 pt); a 400 ppp eran ~270 MP y MuPDF abortaba al
# convertir a RGB («Overly large image»). Tesseract admite como máximo 32767 px
# por lado.
MAX_PIXELS = 36_000_000
MAX_SIDE = 32_000
MIN_DPI = 20
# (r60) Comprobación de la orientación: el OSD de Tesseract se equivoca con
# fotos de documentos (OCR.PDF: «girar 180°» con confianza 0,79 estando
# derecha, y el OCR salió entero boca abajo). Si propone girar, se reconoce un
# poco a media resolución en las dos orientaciones y solo se gira si la
# propuesta gana en confianza media por este margen (en OCR.PDF: 94 frente a 35).
VERIFY_MARGIN = 10.0
# Modo de pintado 3 = texto invisible: la capa de un OCR anterior.
INVISIBLE = 3
# (r60) Umbralizado de Tesseract: 2 = Sauvola (adaptativo, por zonas). Mejor
# que el Otsu global por defecto con fondos grises, sombras o viñeteado.
THRESHOLDING = 2
# (r60) Enderezado: solo si la página está torcida al menos MIN_SKEW grados.
# Por debajo, Tesseract ya lo resuelve, y en fotos con perspectiva un giro
# global empeoraba (OCR.PDF, 0,8°: un importe total pasaba a leerse con dos cifras cambiadas).
MIN_SKEW = 1.0
MAX_SKEW = 6.0


def page_has_text(page: fitz.Page) -> bool:
    return bool(page.get_text("text").strip())


def render_dpi(page: fitz.Page, dpi: int = DPI) -> int:
    """ppp de render sin pasar de MAX_PIXELS ni de MAX_SIDE por lado."""
    w_in, h_in = page.rect.width / 72, page.rect.height / 72
    if w_in <= 0 or h_in <= 0:
        return dpi
    limit = min((MAX_PIXELS / (w_in * h_in)) ** 0.5, MAX_SIDE / max(w_in, h_in))
    return max(MIN_DPI, int(min(dpi, limit)))


def _tesseract(args: list, timeout: int = 300):
    """Ejecuta tesseract.exe con los idiomas de la app. None si no se pudo."""
    exe = tesseract_setup.find_tesseract()
    if not exe:
        return None
    try:
        return subprocess.run(
            [exe, *args], capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout,
            env=dict(os.environ, TESSDATA_PREFIX=tesseract_setup.TESSDATA_DIR),
            creationflags=0x08000000 if os.name == "nt" else 0)
    except (OSError, subprocess.SubprocessError):
        return None


def _osd_rotation(page: fitz.Page) -> int:
    """Lo que propone Tesseract OSD (0, 90, 180, 270), sin comprobar."""
    pix = page.get_pixmap(dpi=render_dpi(page, OSD_DPI), alpha=False, annots=False)
    if pix.is_unicolor:
        return 0
    with tempfile.TemporaryDirectory(prefix="agpdf_osd_") as tmp:
        png = os.path.join(tmp, "pagina.png")
        pix.save(png)
        cp = _tesseract([png, "stdout", "--psm", "0"], timeout=60)
    if cp is None:
        return 0
    out = cp.stdout + cp.stderr
    rotate = re.search(r"Rotate:\s*(\d+)", out)
    confidence = re.search(r"Orientation confidence:\s*([\d.]+)", out)
    if not rotate or (confidence and float(confidence.group(1)) < MIN_OSD_CONFIDENCE):
        return 0
    value = int(rotate.group(1)) % 360
    return value if value in (0, 90, 180, 270) else 0


def _mean_confidence(page: fitz.Page, extra: int, language: str) -> float:
    """Confianza media (0-100) de las palabras de 3 o más letras que Tesseract
    reconoce con la página girada `extra` grados, a media resolución.

    Las palabras que salen en vertical (más altas que anchas) cuentan como 0:
    Tesseract 5 lee solo las líneas verticales con buena confianza, así que con
    la página de lado la confianza sin más no distinguía 0° de 90°/270°."""
    original = page.rotation
    try:
        page.set_rotation((original + extra) % 360)
        pix = page.get_pixmap(dpi=max(MIN_DPI, render_dpi(page) // 2),
                              colorspace=fitz.csGRAY, alpha=False, annots=False)
    finally:
        page.set_rotation(original)
    with tempfile.TemporaryDirectory(prefix="agpdf_orient_") as tmp:
        png, out = os.path.join(tmp, "p.png"), os.path.join(tmp, "o")
        pix.save(png)
        cp = _tesseract([png, out, "-l", language, "--psm", "3",
                         "-c", "tessedit_create_tsv=1"])
        try:
            with open(out + ".tsv", encoding="utf-8", errors="replace") as fh:
                filas = list(csv.DictReader(fh, delimiter="\t", quoting=csv.QUOTE_NONE))
        except OSError:
            return 0.0
    confs = []
    for fila in filas:
        texto = (fila.get("text") or "").strip()
        try:
            c = float(fila.get("conf") or -1)
            ancho, alto = int(fila.get("width") or 0), int(fila.get("height") or 0)
        except ValueError:
            continue
        if c >= 0 and len(texto) >= 3:
            confs.append(c if ancho >= alto else 0.0)
    return sum(confs) / len(confs) if confs else 0.0


def detect_rotation(page: fitz.Page, language: str = "spa") -> int:
    """Grados (0, 90, 180, 270) que hay que añadir a la rotación de la página
    para que su texto quede derecho. 0 si no se sabe.

    (r60) Lo propone Tesseract OSD, pero no se le cree sin más: se comprueba
    reconociendo en las dos orientaciones (`_mean_confidence`) y solo se gira
    si la propuesta gana por VERIFY_MARGIN puntos de confianza."""
    if not tesseract_setup.find_tesseract():
        return 0
    propuesta = _osd_rotation(page)
    if not propuesta:
        return 0
    actual = _mean_confidence(page, 0, language)
    girada = _mean_confidence(page, propuesta, language)
    return propuesta if girada >= actual + VERIFY_MARGIN else 0


def remove_previous_ocr(page: fitz.Page) -> int:
    """(r60) Quita la capa de un OCR anterior (texto invisible, modo 3) para
    reconocer de nuevo. Antes se trataba como texto real: se tapaba en blanco
    «para no duplicarlo» y un OCR malo (p. ej. leído boca abajo) no se podía
    corregir repitiendo el OCR. Devuelve cuántos fragmentos se quitaron."""
    cajas = [fitz.Rect(t["bbox"]) for t in page.get_texttrace()
             if t.get("type") == INVISIBLE and not fitz.Rect(t["bbox"]).is_empty]
    if not cajas:
        return 0
    import pdf_edit                  # aquí: pdf_edit importa módulos pesados
    pdf_edit._erase(page, cajas, images=fitz.PDF_REDACT_IMAGE_NONE)
    return len(cajas)


def skew_angle(gray: np.ndarray) -> float:
    """(r60) Inclinación (grados) de las líneas de texto por perfil de
    proyección: el ángulo que hace más «picudas» las sumas por filas. Se busca
    entre ±MAX_SKEW en dos pasadas (0,5° y 0,1°) sobre una copia pequeña."""
    h, w = gray.shape
    f = 1000 / max(h, w)
    small = cv2.resize(gray, (max(1, int(w * f)), max(1, int(h * f))),
                       interpolation=cv2.INTER_AREA) if f < 1 else gray
    _, bw = cv2.threshold(small, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    if bw.mean() < 0.5:                                  # página casi en blanco
        return 0.0
    centro = (bw.shape[1] / 2, bw.shape[0] / 2)

    def nitidez(angulo):
        m = cv2.getRotationMatrix2D(centro, angulo, 1.0)
        r = cv2.warpAffine(bw, m, (bw.shape[1], bw.shape[0]), flags=cv2.INTER_NEAREST)
        filas = r.sum(axis=1, dtype=np.float64)
        return float(np.sum(np.diff(filas) ** 2))
    mejor = max(np.arange(-MAX_SKEW, MAX_SKEW + 0.01, 0.5), key=nitidez)
    mejor = max(np.arange(mejor - 0.5, mejor + 0.51, 0.1), key=nitidez)
    return round(float(mejor), 2)


def _unrotate_matrix(angle: float, width: float, height: float) -> str:
    """Operador `cm` que devuelve la capa de texto reconocida sobre la imagen
    enderezada (girada `angle` grados en sentido antihorario alrededor del
    centro) a la posición de la imagen original."""
    a = math.radians(-angle)
    c, s_ = math.cos(a), math.sin(a)
    cx, cy = width / 2, height / 2
    e = cx - (c * cx - s_ * cy)
    f = cy - (s_ * cx + c * cy)
    return f"{c:.6f} {s_:.6f} {-s_:.6f} {c:.6f} {e:.4f} {f:.4f} cm"


def _text_layer(gray: np.ndarray, dpi: int, language: str,
                angle: float = 0.0) -> tuple[fitz.Document | None, int]:
    """(r60) Capa de texto invisible de Tesseract (tesseract.exe, no el motor de
    MuPDF: este no deja elegir el umbralizado). Sauvola (thresholding_method=2)
    y solo texto (textonly_pdf=1), así que no arrastra ninguna imagen (r35).
    Si la imagen se enderezó `angle` grados, la capa se gira de vuelta."""
    tesseract_setup.ensure_pdf_font()
    with tempfile.TemporaryDirectory(prefix="agpdf_ocr_") as tmp:
        png, base = os.path.join(tmp, "pagina.png"), os.path.join(tmp, "capa")
        cv2.imwrite(png, gray)
        cp = _tesseract([png, base, "-l", language, "--psm", "3", "--dpi", str(dpi),
                         "-c", f"thresholding_method={THRESHOLDING}",
                         "-c", "tessedit_create_pdf=1", "-c", "textonly_pdf=1"],
                        timeout=900)
        if cp is None or not os.path.isfile(base + ".pdf"):
            detalle = (cp.stderr.strip()[-400:] if cp is not None else "no se pudo ejecutar")
            raise RuntimeError(f"Tesseract no generó la capa de texto: {detalle}")
        with open(base + ".pdf", "rb") as fh:
            ocr = fitz.open("pdf", fh.read())
    page = ocr[0]
    words = len(page.get_text("words"))
    if not words:
        ocr.close()
        return None, 0
    contents = page.get_contents()
    stream = b"\n".join(ocr.xref_stream(x) or b"" for x in contents)
    for name in {img[7] for img in page.get_images(full=True)}:   # por si acaso
        stream = re.sub(rb"/" + re.escape(name.encode()) + rb"\s+Do\b", b"", stream)
    if angle:
        r = page.rect
        stream = (b"q " + _unrotate_matrix(angle, r.width, r.height).encode()
                  + b"\n" + stream + b"\nQ")
    ocr.update_stream(contents[0], stream)
    for x in contents[1:]:
        ocr.update_stream(x, b"")
    ocr.xref_set_key(page.xref, "Resources/XObject", "null")
    return ocr, words


def ocr_page(page: fitz.Page, language: str = "spa", dpi: int = DPI,
             detect_orientation: bool = True) -> int:
    """Añade a `page` la capa de texto invisible de lo que Tesseract reconozca
    fuera del texto ya seleccionable (el visible: la capa de un OCR anterior se
    sustituye, r60). Devuelve el número de palabras añadidas."""
    remove_previous_ocr(page)
    original = page.rotation
    extra = detect_rotation(page, language) if detect_orientation else 0
    try:
        if extra:
            page.set_rotation((original + extra) % 360)
        dpi = render_dpi(page, dpi)
        scale = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=scale, colorspace=fitz.csGRAY, alpha=False, annots=False)
        for word in page.get_text("words"):                  # no duplicar texto real
            box = (fitz.Rect(word[:4]) * scale).irect
            box = fitz.IRect(box.x0 - 2, box.y0 - 2, box.x1 + 2, box.y1 + 2) & pix.irect
            if not box.is_empty:
                pix.set_rect(box, (255,))
        if pix.is_unicolor:
            return 0
        gray = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.stride)[:, :pix.width]
        angle = skew_angle(gray)
        if abs(angle) >= MIN_SKEW:
            m = cv2.getRotationMatrix2D((pix.width / 2, pix.height / 2), angle, 1.0)
            gray = cv2.warpAffine(gray, m, (pix.width, pix.height), borderValue=255,
                                  flags=cv2.INTER_CUBIC)
        else:
            angle = 0.0
        layer, words = _text_layer(np.ascontiguousarray(gray), dpi, language, angle)
        if layer is None:
            return 0
        page.show_pdf_page(page.rect, layer, 0, overlay=True)
        layer.close()
        return words
    finally:
        if page.rotation != original:
            page.set_rotation(original)
