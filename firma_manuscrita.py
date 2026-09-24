"""
Firma manuscrita (r68): la firma «a mano» que se estampa en la página, sin
valor criptográfico (eso es la firma digital PAdES de signer_backend). Sale del
botón de la plumilla en la barra de Firma: o se dibuja con el ratón o se carga
una imagen escaneada (firma_manuscrita_ui).

Este módulo no usa Qt: guarda la geometría del trazo y escribe la anotación.

**Aspecto de estilográfica.** Cada trazo se dibuja como una plumilla biselada
(`NIB_ANGLE`): los trazos perpendiculares al bisel salen gruesos y los paralelos
finos, y la velocidad adelgaza la línea (lento = más tinta). La tinta es
translúcida (`INK_ALPHA`) y **cada trazo se rellena por separado**, así que
donde dos trazos se cruzan la tinta se superpone y oscurece, como en el papel.
Dentro de un mismo trazo la unión es un único relleno (regla de «winding» no
nula con todas las piezas orientadas igual) y no se oscurece; salvo cuando el
trazo **se corta a sí mismo** (bucles de la «l», la «e»…): ahí se parte en
piezas (`_split_at_crossings`) para que también se note la tinta doble.

**En el PDF** la firma es una anotación Stamp con apariencia propia, como los
emojis (invariante 3): vectorial para la dibujada y con la imagen para la
cargada. Moverla o redimensionarla escribe /Rect por xref
(`emoji_font.write_rect`), nunca con set_rect()/update(). /Subj empieza por
`SUBJECT`, que está en `emoji_font.STAMP_SUBJECTS` por eso mismo.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import fitz

SUBJECT = "FirmaManuscrita"
AP_MARKER = b"% AG-FIRMA"

NIB_ANGLE = math.radians(40)      # bisel de la plumilla: de abajo-izquierda a arriba-derecha
INK_ALPHA = 0.75                  # opacidad de la tinta: los cruces se oscurecen
DEFAULT_COLOR = (0.0, 0.0, 1.0)   # «Azul puro» de la paleta: tinta de estilográfica
DEFAULT_WIDTH = 4                 # grosor de la plumilla en píxeles del lienzo
WIDTHS = (1, 12)                  # límites del grosor
DEFAULT_PLACE_WIDTH = 160.0       # ancho (pt) al colocarla con un clic
PAD = 2.0                         # margen alrededor de la tinta (px del lienzo)

Point = tuple[float, float, float]            # x, y, t (segundos)


@dataclass
class HandSignature:
    """Firma lista para estampar: trazos (dibujada) o PNG (imagen)."""
    strokes: list[list[Point]] = field(default_factory=list)
    width: float = DEFAULT_WIDTH
    color: tuple = DEFAULT_COLOR
    png: bytes = b""
    png_size: tuple[int, int] = (0, 0)

    @property
    def is_image(self) -> bool:
        return bool(self.png)

    def is_empty(self) -> bool:
        return not self.png and not any(self.strokes)

    def pieces(self) -> list[list[tuple[float, float, float]]]:
        return ink_pieces(self.strokes, self.width)

    def bounds(self) -> fitz.Rect:
        """Caja de la tinta, en píxeles del lienzo (o de la imagen)."""
        if self.is_image:
            return fitz.Rect(0, 0, *self.png_size)
        return pieces_bounds(self.pieces())

    def aspect(self) -> float:
        b = self.bounds()
        return b.width / b.height if b.height > 0 else 1.0


# ── Geometría de la plumilla ─────────────────────────────────────────────── #

def _dedupe(pts: list[Point], min_dist: float = 0.5) -> list[Point]:
    out: list[Point] = []
    for p in pts:
        if not out or math.hypot(p[0] - out[-1][0], p[1] - out[-1][1]) >= min_dist:
            out.append(p)
    if len(out) == 1 and len(pts) > 1:
        out.append(pts[-1])
    return out


def _smooth(pts: list[Point]) -> list[Point]:
    """Media móvil de 3 (el ratón tiembla); los extremos se quedan."""
    if len(pts) < 3:
        return list(pts)
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        a, b, c = pts[i - 1], pts[i], pts[i + 1]
        out.append(((a[0] + 2 * b[0] + c[0]) / 4, (a[1] + 2 * b[1] + c[1]) / 4, b[2]))
    out.append(pts[-1])
    return out


def _resample(pts: list[Point], step: float) -> tuple[list[Point], list[int]]:
    """Catmull-Rom entre los puntos del ratón, cada `step` px como mucho.
    Devuelve los puntos densos y, por cada punto original, su índice denso."""
    if len(pts) < 2:
        return list(pts), list(range(len(pts)))
    dense: list[Point] = []
    index: list[int] = []
    n = len(pts)
    for i in range(n - 1):
        p0, p1, p2 = pts[max(0, i - 1)], pts[i], pts[i + 1]
        p3 = pts[min(n - 1, i + 2)]
        index.append(len(dense))
        k = max(1, math.ceil(math.hypot(p2[0] - p1[0], p2[1] - p1[1]) / step))
        for j in range(k):
            s = j / k
            s2, s3 = s * s, s * s * s
            x = 0.5 * (2 * p1[0] + (-p0[0] + p2[0]) * s
                       + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * s2
                       + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * s3)
            y = 0.5 * (2 * p1[1] + (-p0[1] + p2[1]) * s
                       + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * s2
                       + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * s3)
            dense.append((x, y, p1[2] + (p2[2] - p1[2]) * s))
    index.append(len(dense))
    dense.append(pts[-1])
    return dense, index


def _radii(dense: list[Point], width: float) -> list[float]:
    """Radio de la tinta en cada punto: dirección respecto al bisel, velocidad
    y un poco más de tinta al apoyar la plumilla."""
    n = len(dense)
    half = width / 2
    if n == 1:
        return [half * 0.9]
    nx, ny = math.cos(NIB_ANGLE), -math.sin(NIB_ANGLE)
    raw = []
    for i in range(n):
        a, b = dense[max(0, i - 1)], dense[min(n - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        d = math.hypot(dx, dy) or 1.0
        cruz = abs(dx / d * ny - dy / d * nx)       # 0 = paralelo al bisel
        f_dir = 0.28 + 0.72 * cruz
        dt = b[2] - a[2]
        v = d / dt if dt > 1e-4 else 600.0           # px/s
        f_vel = min(1.15, max(0.72, 1.18 - v / 3200))
        raw.append(half * f_dir * f_vel)
    # Suavizado en los dos sentidos: el grosor cambia sin escalones.
    for i in range(1, n):
        raw[i] = raw[i - 1] + (raw[i] - raw[i - 1]) * 0.22
    for i in range(n - 2, -1, -1):
        raw[i] = raw[i + 1] + (raw[i] - raw[i + 1]) * 0.22
    # Gota de tinta al apoyar la plumilla (primeros ~1,5 grosores).
    recorrido = 0.0
    for i in range(1, n):
        recorrido += math.hypot(dense[i][0] - dense[i - 1][0], dense[i][1] - dense[i - 1][1])
        if recorrido > width * 1.5:
            break
        raw[i] *= 1.0 + 0.18 * (1 - recorrido / (width * 1.5))
    raw[0] *= 1.18
    minimo = max(0.3, half * 0.16)
    return [max(minimo, r) for r in raw]


def _seg_cross(a, b, c, d) -> bool:
    """¿Se cortan los segmentos ab y cd (sin contar los extremos)?"""
    def orient(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    o1, o2 = orient(a, b, c), orient(a, b, d)
    o3, o4 = orient(c, d, a), orient(c, d, b)
    return o1 * o2 < 0 and o3 * o4 < 0


def _split_at_crossings(pts: list[Point]) -> list[int]:
    """Índices (de `pts`) donde empieza una pieza nueva: cada vez que el trazo
    corta una parte anterior de la pieza en curso."""
    cortes = []
    inicio = 0
    for j in range(2, len(pts) - 1):
        c, d = pts[j], pts[j + 1]
        x0, x1 = min(c[0], d[0]), max(c[0], d[0])
        y0, y1 = min(c[1], d[1]), max(c[1], d[1])
        for i in range(inicio, j - 1):
            a, b = pts[i], pts[i + 1]
            if (max(a[0], b[0]) < x0 or min(a[0], b[0]) > x1
                    or max(a[1], b[1]) < y0 or min(a[1], b[1]) > y1):
                continue
            if _seg_cross(a, b, c, d):
                cortes.append(j)
                inicio = j
                break
    return cortes


def ink_pieces(strokes: list[list[Point]], width: float) -> list[list[tuple]]:
    """Piezas de tinta [(x, y, radio), …]. Cada pieza se rellena por separado
    con tinta translúcida: donde dos piezas se solapan, se oscurece."""
    step = max(0.8, width * 0.4)
    piezas = []
    for stroke in strokes:
        pts = _smooth(_dedupe(stroke))
        if not pts:
            continue
        dense, index = _resample(pts, step)
        radios = _radii(dense, width)
        puntos = [(p[0], p[1], r) for p, r in zip(dense, radios)]
        inicio = 0
        for c in _split_at_crossings(pts):
            k = index[c]
            if k > inicio:
                piezas.append(puntos[inicio:k + 1])
                inicio = k
        piezas.append(puntos[inicio:])
    return piezas


def pieces_bounds(pieces) -> fitz.Rect:
    xs0 = [x - r for pz in pieces for x, _y, r in pz]
    if not xs0:
        return fitz.Rect(0, 0, 1, 1)
    r = fitz.Rect(min(xs0), min(y - r for pz in pieces for _x, y, r in pz),
                  max(x + r for pz in pieces for x, _y, r in pz),
                  max(y + r for pz in pieces for _x, y, r in pz))
    return r + (-PAD, -PAD, PAD, PAD)


# Contorno de cada pieza: dos bordes paralelos al trazo (a un radio de cada
# lado, con la normal promediada para que los tramos casen sin dientes) y
# círculos en las puntas y en los giros cerrados. Todo con la misma orientación
# (área de Gauss positiva), para que el relleno no nulo sea la unión sin
# huecos. Lo usan el PDF y la vista previa de Qt.

_K = 0.5523


def circle_segments(x, y, r):
    """Círculo como 4 curvas de Bézier: [(inicio), (c1, c2, fin)×4]."""
    k = _K * r
    return [(x + r, y),
            ((x + r, y + k), (x + k, y + r), (x, y + r)),
            ((x - k, y + r), (x - r, y + k), (x - r, y)),
            ((x - r, y - k), (x - k, y - r), (x, y - r)),
            ((x + k, y - r), (x + r, y - k), (x + r, y))]


def _area(poly) -> float:
    return sum(poly[i - 1][0] * poly[i][1] - poly[i][0] * poly[i - 1][1]
               for i in range(len(poly))) * 0.5


def piece_shapes(pz) -> tuple[list[tuple], list[list[tuple]]]:
    """(círculos, polígonos) de una pieza de tinta [(x, y, r), …]."""
    n = len(pz)
    if n == 1:
        return [pz[0]], []
    izq, der = [], []
    for i in range(n):
        a, b = pz[max(0, i - 1)], pz[min(n - 1, i + 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        d = math.hypot(dx, dy) or 1.0
        ox, oy = -dy / d * pz[i][2], dx / d * pz[i][2]
        izq.append((pz[i][0] + ox, pz[i][1] + oy))
        der.append((pz[i][0] - ox, pz[i][1] - oy))
    circulos = {0, n - 1}
    signos = []
    for i in range(n - 1):
        q = (izq[i], izq[i + 1], der[i + 1], der[i])
        # Cuadrilátero retorcido (giro más cerrado que el radio): lo cubren
        # los círculos de sus dos extremos.
        if _seg_cross(q[0], q[1], q[2], q[3]) or _seg_cross(q[1], q[2], q[3], q[0]):
            signos.append(0)
            circulos.update((i, i + 1))
            continue
        area = _area(q)
        signos.append(0 if abs(area) < 1e-9 else (1 if area > 0 else -1))
    for i in range(1, n - 1):
        a, b, c = pz[i - 1], pz[i], pz[i + 1]
        ux, uy, vx, vy = b[0] - a[0], b[1] - a[1], c[0] - b[0], c[1] - b[1]
        if ux * vx + uy * vy < 0.3 * math.hypot(ux, uy) * math.hypot(vx, vy):
            circulos.add(i)                        # esquina de más de ~70°
    # Tramos seguidos con la misma orientación = un solo polígono.
    poligonos = []
    i = 0
    while i < n - 1:
        if signos[i] == 0:
            i += 1
            continue
        j = i
        while j + 1 < n - 1 and signos[j + 1] == signos[i]:
            j += 1
        poly = izq[i:j + 2] + der[i:j + 2][::-1]
        poligonos.append(poly if signos[i] > 0 else poly[::-1])
        i = j + 1
    return [pz[k] for k in sorted(circulos)], poligonos


def pdf_ops(pieces, color, alpha: float = INK_ALPHA) -> tuple[bytes, fitz.Rect]:
    """Flujo de contenido de la apariencia y la caja (px del lienzo) que ocupa."""
    caja = pieces_bounds(pieces)
    r, g, b = (max(0.0, min(1.0, c)) for c in color[:3])
    out = [AP_MARKER.decode(),
           f"q /AGFa gs {r:.4f} {g:.4f} {b:.4f} rg",
           f"1 0 0 -1 {-caja.x0:.3f} {caja.y1:.3f} cm"]

    def f(v):
        return f"{round(v, 2):g}"

    for pz in pieces:
        circulos, poligonos = piece_shapes(pz)
        ops = []
        for c in circulos:
            seg = circle_segments(*c)
            ops.append(f"{f(seg[0][0])} {f(seg[0][1])} m")
            for c1, c2, e in seg[1:]:
                ops.append(f"{f(c1[0])} {f(c1[1])} {f(c2[0])} {f(c2[1])} {f(e[0])} {f(e[1])} c")
            ops.append("h")
        for poly in poligonos:
            ops.append(f"{f(poly[0][0])} {f(poly[0][1])} m\n"
                       + "\n".join(f"{f(x)} {f(y)} l" for x, y in poly[1:]) + "\nh")
        out.append("\n".join(ops))
        out.append("f")                      # una pieza = un relleno
    out.append("Q")
    return "\n".join(out).encode("latin-1"), caja


# ── Anotación ────────────────────────────────────────────────────────────── #

def is_hand_signature(subject: str) -> bool:
    return (subject or "").split("|")[0] == SUBJECT


def fit_rect(sig: HandSignature, center: fitz.Point | None = None,
             box: fitz.Rect | None = None) -> fitz.Rect:
    """Rectángulo en la página: dentro de `box` conservando la proporción, o
    de `DEFAULT_PLACE_WIDTH` de ancho centrado en `center`."""
    asp = sig.aspect()
    if box is not None and box.width > 1 and box.height > 1:
        w = min(box.width, box.height * asp)
        h = w / asp
        cx, cy = (box.x0 + box.x1) / 2, (box.y0 + box.y1) / 2
    else:
        w = DEFAULT_PLACE_WIDTH
        h = w / asp
        cx, cy = center.x, center.y
    return fitz.Rect(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


def add_hand_signature(doc: fitz.Document, page_num: int, rect: fitz.Rect,
                       sig: HandSignature) -> fitz.Annot:
    """Estampa la firma en `rect` (coordenadas de página de PyMuPDF)."""
    import emoji_font                      # write_rect: /Rect sin regenerar la apariencia
    page = doc[page_num]
    if sig.is_image:
        annot = page.add_stamp_annot(rect, stamp=sig.png)
        emoji_font.write_rect(page, annot, rect)
        tipo = "img"
    else:
        ops, caja = pdf_ops(sig.pieces(), sig.color)
        annot = page.add_stamp_annot(rect)
        emoji_font.write_rect(page, annot, rect)
        annot._setAP(ops)
        ap_x = int(doc.xref_get_key(annot.xref, "AP/N")[1].split()[0])
        doc.xref_set_key(ap_x, "Resources",
                         f"<</ExtGState<</AGFa<</Type/ExtGState/ca {INK_ALPHA:.2f}>>>>>>")
        doc.xref_set_key(ap_x, "BBox", f"[0 0 {caja.width:.3f} {caja.height:.3f}]")
        doc.xref_set_key(ap_x, "Matrix", "[1 0 0 1 0 0]")
        doc.xref_set_key(annot.xref, "Name", "/AGFirma")
        tipo = "trazo"
    # Metadatos por xref: set_info() regeneraría la apariencia (invariante 6).
    doc.xref_set_key(annot.xref, "Contents", fitz.get_pdf_str("Firma manuscrita"))
    doc.xref_set_key(annot.xref, "Subj", fitz.get_pdf_str(f"{SUBJECT}|{tipo}"))
    return annot
