# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller de la prueba WinUI 3 (r66). Desde el entorno venv-winui3:

    python -m PyInstaller prototipos/winui3/visor_poc.spec --distpath <fuera> --workpath <fuera>

Necesita el runtime del Windows App SDK 1.7 instalado en el equipo (lo que
haría el instalador real).
"""
import os

from PyInstaller.utils.hooks import collect_all

RAIZ = os.path.abspath(os.path.join(SPECPATH, "..", ".."))
datas = [
    (os.path.join(RAIZ, "vendor", "fonts", "fluent-icons"), os.path.join("vendor", "fonts", "fluent-icons")),
    (os.path.join(RAIZ, "vendor", "icono"), os.path.join("vendor", "icono")),
    (os.path.join(RAIZ, "Formulario.pdf"), "."),
]
binaries, hiddenimports = [], []
for paquete in ("winui3", "winrt"):
    d, b, h = collect_all(paquete)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis([os.path.join(SPECPATH, "visor_poc.py")], pathex=[RAIZ], datas=datas,
             binaries=binaries, hiddenimports=hiddenimports, noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="VisorWinUI3",
          icon=os.path.join(RAIZ, "vendor", "icono", "aventyapdf.ico"), console=False, upx=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="VisorWinUI3")
