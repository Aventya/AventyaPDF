"""
preparar_store.py — Contenido del paquete MSIX para la Microsoft Store (r119)
=============================================================================

Lo usa empaquetado\\construir_store.ps1 con el Python del entorno de la app:

    python preparar_store.py --completo <dir> --destino <dir> --version 0.9.9
                             --name <Name> --publisher <CN=…> --publisher-name <texto>

* Copia la copia completa ya probada de la instalación (`--completo`, la que
  monta construir.ps1: lanzador, Python, paquetes ya recortados y precompilados,
  fuentes, código) sin el paquete disperso del menú contextual, que aquí sobra.
* Tesseract OCR dentro (`tesseract\\`): un paquete de la Store no puede instalar
  otros programas. tesseract.exe y solo las DLL que importa (de la instalación
  de Tesseract de este equipo), los modelos «best» de español, inglés y
  orientación, pdf.ttf y su licencia (Apache 2.0).
* (r141: ya sin manual, que se descarga) Las imágenes de la Store (de ICONO.png) y el AppxManifest.xml.
"""
import argparse
import os
import shutil
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", ".."))
sys.path.insert(0, RAIZ)
sys.path.insert(0, os.path.join(RAIZ, "empaquetado"))

import tesseract_setup  # noqa: E402
from componentes import _importa  # noqa: E402

# Mismas extensiones que shell\AventyaPDFShell.cpp y el instalador.
EXTENSIONES = (".pdf .png .jpg .jpeg .bmp .gif .tif .tiff .webp .doc .docx").split()
CLSID = "CFCBA067-9C58-4229-95F8-2F5912C3611F"


def _tesseract(destino: str) -> int:
    exe = tesseract_setup.find_tesseract()
    if not exe:
        raise SystemExit("Hace falta Tesseract instalado en este equipo para incluirlo en el paquete.")
    origen = os.path.dirname(exe)
    t = os.path.join(destino, "tesseract")
    os.makedirs(os.path.join(t, "tessdata"))
    os.makedirs(os.path.join(t, "doc"))
    shutil.copy2(exe, os.path.join(t, "tesseract.exe"))
    dlls, pendientes = set(), [exe]
    locales = {f.lower(): f for f in os.listdir(origen) if f.lower().endswith(".dll")}
    while pendientes:
        for dll in _importa(pendientes.pop()):
            if dll in locales and dll not in dlls:
                dlls.add(dll)
                pendientes.append(os.path.join(origen, locales[dll]))
    for d in dlls:
        shutil.copy2(os.path.join(origen, locales[d]), t)
    tesseract_setup.ensure(tesseract_setup.CORE_LANGS, report=print)
    for lang in tesseract_setup.CORE_LANGS:
        for extra in ("", tesseract_setup.MODEL_MARKER):
            shutil.copy2(os.path.join(tesseract_setup.TESSDATA_DIR, f"{lang}.traineddata{extra}"),
                         os.path.join(t, "tessdata"))
    shutil.copy2(os.path.join(origen, "tessdata", tesseract_setup.PDF_FONT), os.path.join(t, "tessdata"))
    for doc in ("LICENSE", "AUTHORS", "README.md"):
        if os.path.isfile(os.path.join(origen, "doc", doc)):
            shutil.copy2(os.path.join(origen, "doc", doc), os.path.join(t, "doc"))
    return len(dlls)


def _imagenes(destino: str) -> None:
    """Logos de la Store desde ICONO.png, con fondo transparente."""
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QGuiApplication, QImage, QPainter
    QGuiApplication.instance() or QGuiApplication([])
    icono = QImage(os.path.join(RAIZ, "ICONO.png"))
    carpeta = os.path.join(destino, "imagenes-store")
    os.makedirs(carpeta)

    def lienzo(nombre, ancho, alto, lado):
        img = QImage(ancho, alto, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        ic = icono.scaled(lado, lado, Qt.AspectRatioMode.KeepAspectRatio,
                          Qt.TransformationMode.SmoothTransformation)
        p.drawImage((ancho - ic.width()) // 2, (alto - ic.height()) // 2, ic)
        p.end()
        img.save(os.path.join(carpeta, nombre))

    lienzo("Square44x44Logo.png", 44, 44, 40)
    for t in (16, 24, 32, 48, 256):         # barra de tareas y menú Inicio, sin placa
        lienzo(f"Square44x44Logo.targetsize-{t}_altform-unplated.png", t, t, t)
    lienzo("Square71x71Logo.png", 71, 71, 56)
    lienzo("Square150x150Logo.png", 150, 150, 100)
    lienzo("Wide310x150Logo.png", 310, 150, 100)
    lienzo("StoreLogo.png", 50, 50, 50)
    # (r139) Icono de los archivos PDF, pintado desde su dibujo vectorial.
    from PyQt6.QtSvg import QSvgRenderer
    svg = QSvgRenderer(os.path.join(RAIZ, "vendor", "icono", "documento_pdf.svg"))
    for nombre, t in [("DocumentoPDF.png", 44)] + [
            (f"DocumentoPDF.targetsize-{t}.png", t) for t in (16, 24, 32, 48, 256)]:
        img = QImage(t, t, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        svg.render(p)
        p.end()
        img.save(os.path.join(carpeta, nombre))


def _manifiesto(destino: str, a) -> None:
    v = (a.version.split(".") + ["0", "0", "0"])[:3]
    menu = "\n".join(
        f'            <desktop5:ItemType Type="{e}">\n'
        f'              <desktop5:Verb Id="AventyaPDF" Clsid="{CLSID}" />\n'
        f'            </desktop5:ItemType>' for e in EXTENSIONES)
    with open(os.path.join(AQUI, "AppxManifest.xml"), encoding="utf-8") as fh:
        texto = fh.read()
    texto = (texto.replace("@NAME@", a.name).replace("@PUBLISHER@", a.publisher)
             .replace("@PUBLISHERNAME@", a.publisher_name)
             .replace("@VERSION@", ".".join(v) + ".0").replace("@MENU@", menu))
    with open(os.path.join(destino, "AppxManifest.xml"), "w", encoding="utf-8") as fh:
        fh.write(texto)


def main() -> None:
    ap = argparse.ArgumentParser()
    for opcion in ("--completo", "--destino", "--version", "--name", "--publisher",
                   "--publisher-name"):
        ap.add_argument(opcion, required=True)
    a = ap.parse_args()
    shutil.rmtree(a.destino, ignore_errors=True)
    shutil.copytree(a.completo, a.destino,
                    ignore=shutil.ignore_patterns("menu-contextual"))
    n = _tesseract(a.destino)
    _imagenes(a.destino)
    _manifiesto(a.destino, a)
    total = sum(os.path.getsize(os.path.join(r, f)) for r, _d, fs in os.walk(a.destino) for f in fs)
    print(f"  contenido del paquete: {total / 1e6:.0f} MB (Tesseract con {n} DLL)")


if __name__ == "__main__":
    main()
