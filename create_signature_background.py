"""
Genera signature_background.pdf, el fondo del sello de firma, a partir de
MOSCA.svg (o del SVG que se pase como argumento):

    python create_signature_background.py [ruta.svg]

La conversión SVG → PDF vectorial la hace Microsoft Edge (o Google Chrome) en
modo headless, porque MuPDF no soporta máscaras, degradados con transparencia
ni opacidad de grupo, y el logotipo usa las tres cosas. Solo hace falta el
navegador para GENERAR el PDF; firmar usa el PDF ya generado.

Se trabaja sobre una copia temporal del SVG: el original no se modifica.
"""
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

import fitz

RAIZ = os.path.dirname(os.path.abspath(__file__))
SVG_POR_DEFECTO = os.path.join(RAIZ, "MOSCA.svg")
DESTINO = os.path.join(RAIZ, "signature_background.pdf")


def _buscar_navegador() -> str:
    candidatos = [
        os.path.join(os.environ.get("ProgramFiles(x86)", ""), r"Microsoft\Edge\Application\msedge.exe"),
        os.path.join(os.environ.get("ProgramFiles", ""), r"Microsoft\Edge\Application\msedge.exe"),
        os.path.join(os.environ.get("ProgramFiles", ""), r"Google\Chrome\Application\chrome.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", ""), r"Google\Chrome\Application\chrome.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Google\Chrome\Application\chrome.exe"),
    ]
    for ruta in candidatos:
        if os.path.isfile(ruta):
            return ruta
    for nombre in ("msedge", "chrome", "chromium"):
        ruta = shutil.which(nombre)
        if ruta:
            return ruta
    raise SystemExit("No se encontró Microsoft Edge ni Google Chrome para convertir el SVG.")


def _mascaras_sin_recorte(svg: str) -> str:
    """Inkscape (donde se diseñó el logotipo) no recorta las máscaras sin región
    explícita; los navegadores sí, a -10 %…120 % del lienzo, y el degradado
    salía cortado en ángulo recto. Se da a cada <mask> una región amplia."""
    def ampliar(m: re.Match) -> str:
        etiqueta = m.group(0)
        if re.search(r"\s(x|y|width|height)\s*=", etiqueta):
            return etiqueta
        return etiqueta[:-1] + ' x="-100000" y="-100000" width="200000" height="200000">'
    return re.sub(r"<mask\b[^>]*>", ampliar, svg)


def _propiedades(elemento: str) -> dict:
    """fill / fill-opacity / opacity de un elemento (style tiene prioridad)."""
    props = {}
    m = re.search(r'\sstyle\s*=\s*"([^"]*)"', elemento)
    if m:
        for decl in m.group(1).split(";"):
            if ":" in decl:
                k, v = decl.split(":", 1)
                props[k.strip()] = v.strip()
    for k in ("fill", "fill-opacity", "opacity"):
        m = re.search(r'\s' + k + r'\s*=\s*"([^"]*)"', elemento)
        if m and k not in props:
            props[k] = m.group(1).strip()
    return props


def _luminancia(color: str) -> float | None:
    color = color.strip().lower()
    if re.fullmatch(r"#[0-9a-f]{3}", color):
        color = "#" + "".join(c * 2 for c in color[1:])
    if not re.fullmatch(r"#[0-9a-f]{6}", color):
        return None
    r, g, b = (int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2125 * r + 0.7154 * g + 0.0721 * b


def _mascaras_solidas_a_clip(svg: str) -> str:
    """Skia (Edge/Chrome) exporta cada <mask> como una IMAGEN rasterizada usada
    de máscara suave, y en el borde de esa imagen se cuela 1 px del contenido
    enmascarado: aparecía una línea fina en el perímetro del lienzo del logotipo.
    Una máscara formada solo por formas de un mismo color sólido equivale a un
    <clipPath> (que Skia exporta como vector) más una opacidad igual a su
    luminancia. Las máscaras que no cumplan eso se dejan como están."""
    for m in list(re.finditer(r"<mask\b([^>]*)>(.*?)</mask>", svg, re.DOTALL)):
        atributos, cuerpo = m.group(1), m.group(2)
        ident = re.search(r'\sid\s*=\s*"([^"]+)"', atributos)
        if not ident or "maskContentUnits" in atributos:
            continue
        ident = ident.group(1)
        if re.search(r"mask\s*:\s*url\(\s*#" + re.escape(ident) + r"\s*\)", svg):
            continue                      # referenciada desde style: no se toca
        formas = re.findall(r"<(?:ellipse|circle|rect|path|polygon)\b[^>]*>", cuerpo)
        resto = cuerpo
        for f in formas:
            resto = resto.replace(f, "", 1)
        if not formas or "<" in resto:
            continue                      # hay grupos, degradados, texto…
        alfas = []
        for f in formas:
            p = _propiedades(f)
            lum = _luminancia(p.get("fill", "#000000"))
            try:
                alfa = lum * float(p.get("fill-opacity", 1)) * float(p.get("opacity", 1))
            except (TypeError, ValueError):
                alfa = None
            alfas.append(alfa)
        if None in alfas or max(alfas) - min(alfas) > 1e-3:
            continue
        alfa = alfas[0]
        clip = f'<clipPath id="{ident}" clipPathUnits="userSpaceOnUse">{"".join(formas)}</clipPath>'
        svg = svg[:m.start()] + clip + svg[m.end():]

        def referencia(r: re.Match) -> str:
            etiqueta = r.group(0).replace(r.group(1), f'clip-path="url(#{ident})"', 1)
            if alfa >= 0.999:
                return etiqueta
            estilo = re.search(r'\sstyle\s*=\s*"([^"]*)"', etiqueta)
            if estilo and re.search(r"(^|;)\s*opacity\s*:", estilo.group(1)):
                def mult(o: re.Match) -> str:
                    return f"{o.group(1)}opacity:{float(o.group(2)) * alfa:.6g}"
                nuevo = re.sub(r"(^|;)\s*opacity\s*:\s*([\d.]+)", mult, estilo.group(1))
                return etiqueta.replace(estilo.group(1), nuevo, 1)
            op = re.search(r'\sopacity\s*=\s*"([\d.]+)"', etiqueta)
            if op:
                return etiqueta.replace(op.group(0), f' opacity="{float(op.group(1)) * alfa:.6g}"', 1)
            return etiqueta[:-1] + f' opacity="{alfa:.6g}">'

        svg = re.sub(r'<[a-zA-Z][^>]*?(mask\s*=\s*"url\(#' + re.escape(ident) + r'\)")[^>]*>',
                     referencia, svg)
    return svg


def _tamano_viewbox(svg: str) -> tuple[float, float]:
    m = re.search(r'viewBox\s*=\s*"\s*[-\d.eE+]+[\s,]+[-\d.eE+]+[\s,]+([\d.eE+]+)[\s,]+([\d.eE+]+)', svg)
    if not m:
        raise SystemExit("El SVG no tiene viewBox: no se puede calcular su proporción.")
    return float(m.group(1)), float(m.group(2))


def generar(svg_path: str = SVG_POR_DEFECTO, destino: str = DESTINO) -> str:
    with open(svg_path, encoding="utf-8") as fh:
        svg = fh.read()
    ancho, alto = _tamano_viewbox(svg)
    navegador = _buscar_navegador()

    with tempfile.TemporaryDirectory(prefix="agpdf_fondo_") as tmp:
        svg_tmp = os.path.join(tmp, "fondo.svg")
        with open(svg_tmp, "w", encoding="utf-8") as fh:
            fh.write(_mascaras_sin_recorte(_mascaras_solidas_a_clip(svg)))
        # 1 unidad del viewBox = 1 mm: solo importa la proporción, el sello escala.
        html = os.path.join(tmp, "fondo.html")
        with open(html, "w", encoding="utf-8") as fh:
            fh.write(
                "<!doctype html><html><head><meta charset='utf-8'><style>"
                f"@page {{ size: {ancho}mm {alto}mm; margin: 0; }}"
                "html, body { margin: 0; padding: 0; background: transparent; overflow: hidden; }"
                f"img {{ display: block; width: {ancho}mm; height: {alto}mm; }}"
                f"</style></head><body><img src='{pathlib.Path(svg_tmp).as_uri()}'></body></html>"
            )
        pdf_tmp = os.path.join(tmp, "fondo.pdf")
        subprocess.run(
            [navegador, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
             f"--user-data-dir={os.path.join(tmp, 'perfil')}",
             f"--print-to-pdf={pdf_tmp}", pathlib.Path(html).as_uri()],
            check=True, timeout=120,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        if not os.path.isfile(pdf_tmp):
            raise SystemExit("El navegador no generó el PDF.")

        doc = fitz.open(pdf_tmp)
        if len(doc) > 1:                 # redondeos del navegador: sobra una página
            doc.select([0])
        pr = doc[0].rect
        if abs(pr.width / pr.height - ancho / alto) > 0.01:
            raise SystemExit(f"Proporción inesperada del PDF generado: {pr}")
        doc.save(destino, garbage=3, deflate=True)
        doc.close()
    return destino


if __name__ == "__main__":
    ruta = generar(sys.argv[1] if len(sys.argv) > 1 else SVG_POR_DEFECTO)
    print(f"Fondo del sello generado: {ruta}")
