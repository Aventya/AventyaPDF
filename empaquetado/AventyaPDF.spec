# -*- mode: python ; coding: utf-8 -*-
"""
Receta de PyInstaller para AventyaPDF (r62). No se lanza a mano: la usa
empaquetado/construir.ps1, que además añade Tesseract y crea el instalador.

Carpeta (onedir) y no un solo .exe: arranca mucho más rápido (no hay que
descomprimir 300 MB en cada inicio) y el instalador de Inno Setup la copia tal
cual. Los módulos calculan sus rutas con __file__ (vendor/, el fondo del sello,
la lista de confianza): en el ejecutable, __file__ apunta a _internal, así que
esos datos van ahí con el mismo árbol que en el proyecto.
"""
import os

from PyInstaller.utils.hooks import collect_submodules

RAIZ = os.path.abspath(os.path.join(SPECPATH, ".."))
VERSION = os.environ.get("AVENTYAPDF_VERSION", "0.0.0")

datas = [
    (os.path.join(RAIZ, "vendor"), "vendor"),
    (os.path.join(RAIZ, "signature_background.pdf"), "."),
]
hiddenimports = (
    ["autodiagnostico"]
    # pyHanko carga algunas piezas bajo demanda (sellado de tiempo, validación).
    + collect_submodules("pyhanko.sign")
    + collect_submodules("pyhanko_certvalidator")
    + collect_submodules("keyring.backends")
)

a = Analysis(
    [os.path.join(RAIZ, "main.py")],
    pathex=[RAIZ],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "matplotlib", "IPython", "pytest", "tests"],
    noarchive=False,
)
# El códec de vídeo de OpenCV (~30 MB) sobra: ni el OCR (enderezado) ni
# pdf2docx leen vídeo.
a.binaries = [b for b in a.binaries if "opencv_videoio_ffmpeg" not in b[0].lower()]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AventyaPDF",
    icon=os.path.join(RAIZ, "vendor", "icono", "aventyapdf.ico"),
    version=os.path.join(SPECPATH, "version_info.txt"),
    console=False,          # aplicación de ventanas: sin consola negra detrás
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="AventyaPDF")
