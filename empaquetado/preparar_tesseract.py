"""
Copia Tesseract OCR dentro de la aplicación empaquetada (r62; lo usa
construir.ps1):

    python preparar_tesseract.py <carpeta de la app>

Deja en <app>\\tesseract:
* tesseract.exe y SOLO las DLL que necesita, siguiendo sus importaciones (con
  pefile, que viene con PyInstaller). La instalación de UB Mannheim trae
  ~160 MB de DLL, casi todas de las herramientas de entrenamiento (ICU, cairo,
  pango para text2image).
* tessdata: los modelos «best» de español, inglés y orientación de
  %LOCALAPPDATA%\\aventyapdf\\tessdata (con su marca .best, para que
  tesseract_setup los copie en vez de descargarlos) y pdf.ttf.
* doc: LICENSE, AUTHORS y README de Tesseract (licencia Apache 2.0: se puede
  redistribuir incluyendo la licencia).
"""
import os
import shutil
import sys

import pefile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
import tesseract_setup  # noqa: E402

# DLL del propio Windows: nunca se copian.
_SISTEMA = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32")


def dependencias(exe: str, carpeta: str) -> list[str]:
    """DLL de `carpeta` que `exe` necesita, directa o indirectamente."""
    vistas: set[str] = set()
    pendientes = [exe]
    while pendientes:
        ruta = pendientes.pop()
        pe = pefile.PE(ruta, fast_load=True)
        pe.parse_data_directories(directories=[
            pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"],
            pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT"]])
        nombres = [e.dll.decode() for e in getattr(pe, "DIRECTORY_ENTRY_IMPORT", [])]
        nombres += [e.dll.decode() for e in getattr(pe, "DIRECTORY_ENTRY_DELAY_IMPORT", [])]
        pe.close()
        for n in nombres:
            local = os.path.join(carpeta, n)
            if n.lower() in vistas or not os.path.isfile(local):
                continue            # del sistema (kernel32, msvcrt…) o ya vista
            vistas.add(n.lower())
            pendientes.append(local)
    return sorted(vistas)


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    app = sys.argv[1]
    exe = tesseract_setup.find_tesseract()
    if not exe or os.path.normcase(os.path.dirname(exe)).startswith(os.path.normcase(app)):
        print("No se encuentra una instalación de Tesseract de la que copiar.", file=sys.stderr)
        return 1
    origen = os.path.dirname(exe)
    destino = os.path.join(app, "tesseract")
    if os.path.isdir(destino):
        shutil.rmtree(destino)
    os.makedirs(os.path.join(destino, "tessdata"))
    os.makedirs(os.path.join(destino, "doc"))

    shutil.copy2(exe, os.path.join(destino, "tesseract.exe"))
    dlls = dependencias(exe, origen)
    for n in dlls:
        shutil.copy2(os.path.join(origen, n), destino)

    # Idiomas: los «best» de la app (se preparan si faltan).
    tesseract_setup.ensure(tesseract_setup.CORE_LANGS, report=print)
    for lang in tesseract_setup.CORE_LANGS:
        for extra in ("", tesseract_setup.MODEL_MARKER):
            shutil.copy2(os.path.join(tesseract_setup.TESSDATA_DIR, f"{lang}.traineddata{extra}"),
                         os.path.join(destino, "tessdata"))
    shutil.copy2(os.path.join(origen, "tessdata", tesseract_setup.PDF_FONT),
                 os.path.join(destino, "tessdata"))
    for doc in ("LICENSE", "AUTHORS", "README.md"):
        ruta = os.path.join(origen, "doc", doc)
        if os.path.isfile(ruta):
            shutil.copy2(ruta, os.path.join(destino, "doc"))

    total = sum(os.path.getsize(os.path.join(r, f)) for r, _d, fs in os.walk(destino) for f in fs)
    print(f"Tesseract incluido: {len(dlls)} DLL, {total / 1e6:.0f} MB en {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
