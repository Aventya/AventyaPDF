"""
componentes.py — Qué lleva el instalador y qué descarga (r109)
===============================================================

Petición de Ricardo: «el instalador no lleve partes que se mantengan fuera de
este proyecto». El instalador solo lleva lo propio (lanzador, código, lista de
confianza, iconos, menú contextual, manual); lo de terceros lo descarga Inno
Setup durante la instalación, de su origen oficial y comprobando el SHA-256 de
cada archivo:

* Python oficial «embeddable» de python.org → {app}\\runtime
* cada paquete de Python (wheel de PyPI, la versión EXACTA del entorno ya
  probado) → descomprimido en {app}\\runtime\\Lib\\site-packages. Un wheel es
  un zip: instalarlo es descomprimirlo, no hace falta pip.
* las fuentes Noto y Fluent (GitHub / Google Fonts, a una versión fija) →
  {app}\\app\\vendor\\fonts. Tienen que ser idénticas a las del repositorio
  (con las que se prueba): si no, se detiene la compilación.

Lo usa empaquetado\\construir.ps1 con el Python del entorno de la aplicación:

    python componentes.py --versiones versiones.txt --propios <dir>
                          --completo <dir> --iss <componentes.iss>

--propios   se rellena con app\\ y runtime\\python3XX._pth (lo que empaqueta
            Inno Setup; el lanzador y el menú contextual los pone construir.ps1)
--completo  copia idéntica a la instalación (descargas + propios), para el
            autodiagnóstico antes de crear el instalador
--iss       entradas [Files] de las descargas, para AventyaPDF.iss
"""
import argparse
import ast
import hashlib
import json
import os
import platform
import re
import shutil
import struct
import sys
import urllib.request
import zipfile

from pip._vendor.packaging.tags import sys_tags
from pip._vendor.packaging.utils import parse_wheel_filename

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CACHE = os.path.join(os.environ["LOCALAPPDATA"], "aventyapdf", "build-cache")

# Fuentes: (subcarpeta de vendor/fonts, archivo, URL de origen a versión fija).
_NOTO = "https://raw.githubusercontent.com/notofonts/notofonts.github.io/025970232f4f8ff349310d9785431e87d20ed27c/fonts"
_FLUENT = "https://raw.githubusercontent.com/microsoft/fluentui-system-icons/9cf8af0f95a555918a60b8147a2f33a6a1248442"
FUENTES = [
    ("noto", f"{f}.ttf", f"{_NOTO}/{f.split('-')[0]}/hinted/ttf/{f}.ttf")
    for f in ("NotoSans-Regular", "NotoSans-Bold", "NotoSans-Italic", "NotoSans-BoldItalic",
              "NotoSerif-Regular", "NotoSerif-Bold", "NotoSerif-Italic", "NotoSerif-BoldItalic",
              "NotoSansMono-Regular", "NotoSansMono-Bold")
] + [
    ("noto", "OFL.txt", "https://raw.githubusercontent.com/notofonts/latin-greek-cyrillic/"
                        "4bc63d7ebca1faed49c6c685f380ba0abc2c1941/OFL.txt"),
    # Google Fonts sirve los estáticos de Noto Emoji en URL versionadas (v65 = 3.006).
    ("noto-emoji", "NotoEmoji-Regular.ttf",
     "https://fonts.gstatic.com/s/notoemoji/v65/bMrnmSyK7YY-MEu6aWjPDs-ar6uWaGWuob-r0jwv.ttf"),
    ("noto-emoji", "NotoEmoji-Bold.ttf",
     "https://fonts.gstatic.com/s/notoemoji/v65/bMrnmSyK7YY-MEu6aWjPDs-ar6uWaGWuob9M1Twv.ttf"),
    ("noto-emoji", "OFL.txt", "https://raw.githubusercontent.com/google/fonts/"
                              "a73b9ab0a5df191bcfed817159a903911ea7958a/ofl/notoemoji/OFL.txt"),
    ("fluent-icons", "FluentSystemIcons-Regular.ttf", f"{_FLUENT}/fonts/FluentSystemIcons-Regular.ttf"),
    ("fluent-icons", "FluentSystemIcons-Regular.json", f"{_FLUENT}/fonts/FluentSystemIcons-Regular.json"),
    ("fluent-icons", "LICENSE", f"{_FLUENT}/LICENSE"),
]

# Recursos propios que van dentro del instalador (además del código).
PROPIOS = ["vendor/icono", "vendor/trust", "vendor/emoji", "signature_background.pdf"]
# Plugins de Qt que se conservan (r110). Qt los carga por su cuenta, no por
# importación: ventana (windows; offscreen para el autodiagnóstico), estilo,
# formatos de imagen, iconos SVG, entrada de texto, red/TLS. El resto (QML,
# multimedia, 3D, SQL, sensores…) no lo usa una aplicación de QtWidgets.
PLUGINS_QT = {"platforms", "styles", "imageformats", "iconengines", "platforminputcontexts",
              "generic", "tls", "networkinformation"}
ENTRADAS = ["main.py", "autodiagnostico.py"]


def _sha256(ruta: str) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as fh:
        for bloque in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def _bajar(url: str, nombre: str, sha256: str | None = None) -> str:
    """Descarga a la caché (una sola vez) y comprueba el hash si se conoce."""
    os.makedirs(CACHE, exist_ok=True)
    ruta = os.path.join(CACHE, nombre)
    if not (os.path.isfile(ruta) and (sha256 is None or _sha256(ruta) == sha256)):
        print(f"  descargando {nombre}")
        req = urllib.request.Request(url, headers={"User-Agent": "AventyaPDF-construir"})
        with urllib.request.urlopen(req, timeout=120) as r, open(ruta + ".part", "wb") as fh:
            shutil.copyfileobj(r, fh)
        os.replace(ruta + ".part", ruta)
    if sha256 and _sha256(ruta) != sha256:
        raise SystemExit(f"El SHA-256 de {nombre} no coincide con el publicado.")
    return ruta


def _modulos() -> list[str]:
    """Módulos del proyecto que importa la aplicación (a partir de main.py y
    autodiagnostico.py, también los importados dentro de funciones)."""
    propios = {f[:-3] for f in os.listdir(RAIZ) if f.endswith(".py")}
    vistos, pendientes = set(), [e[:-3] for e in ENTRADAS]
    while pendientes:
        m = pendientes.pop()
        if m in vistos:
            continue
        vistos.add(m)
        with open(os.path.join(RAIZ, m + ".py"), encoding="utf-8") as fh:
            arbol = ast.parse(fh.read())
        for nodo in ast.walk(arbol):
            nombres = ([a.name for a in nodo.names] if isinstance(nodo, ast.Import) else
                       [nodo.module] if isinstance(nodo, ast.ImportFrom) and nodo.module and not nodo.level
                       else [])
            pendientes += [n.split(".")[0] for n in nombres if n.split(".")[0] in propios]
    return sorted(m + ".py" for m in vistos)


def _qt_usados(modulos: list[str]) -> set[str]:
    """Módulos de PyQt6 que importa el código (QtCore, QtGui…)."""
    usados = set()
    for m in modulos:
        with open(os.path.join(RAIZ, m), encoding="utf-8") as fh:
            for nodo in ast.walk(ast.parse(fh.read())):
                nombres = ([a.name for a in nodo.names] if isinstance(nodo, ast.Import) else
                           [nodo.module] if isinstance(nodo, ast.ImportFrom) and nodo.module else [])
                usados |= {n.split(".")[1] for n in nombres if n.startswith("PyQt6.")}
    return usados


def _importa(ruta: str) -> list[str]:
    """DLL que importa un binario PE (tabla de importación y de carga diferida)."""
    with open(ruta, "rb") as fh:
        d = fh.read()
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    nsec, optsz = struct.unpack_from("<H", d, pe + 6)[0], struct.unpack_from("<H", d, pe + 20)[0]
    opt = pe + 24
    ddir = opt + (112 if struct.unpack_from("<H", d, opt)[0] == 0x20B else 96)
    secciones = []
    for i in range(nsec):
        o = opt + optsz + 40 * i
        vsize, va, rawsize, raw = struct.unpack_from("<IIII", d, o + 8)
        secciones.append((va, max(vsize, rawsize), raw))

    def desp(rva):
        return next(rva - va + raw for va, tam, raw in secciones if va <= rva < va + tam)
    out = []
    for idx, paso, campo in ((1, 20, 12), (13, 32, 4)):
        rva = struct.unpack_from("<I", d, ddir + 8 * idx)[0]
        if not rva:
            continue
        p = desp(rva)
        while (n := struct.unpack_from("<I", d, p + campo)[0]):
            s = desp(n)
            out.append(d[s:d.index(b"\0", s)].decode("ascii").lower())
            p += paso
    return out


def _sobrantes(site: str, qt_usados: set[str]) -> tuple[set[str], set[str]]:
    """(r110) Lo que la aplicación no usa dentro de los paquetes: (carpetas,
    archivos), rutas relativas a site-packages con «/». Los paquetes se
    descargan enteros (su SHA-256 es del archivo completo) pero esto no se
    descomprime. Se calcula, no se escribe a mano: los módulos de PyQt6 que
    importa el código y, de las DLL de Qt, solo las que esos módulos y los
    plugins que se conservan importan (directa o indirectamente)."""
    qt = os.path.join(site, "PyQt6")
    carpetas = {"PyQt6/bindings/", "PyQt6/Qt6/qml/", "PyQt6/Qt6/qsci/", "PyQt6/Qt6/translations/"}
    archivos = set()
    raices = []
    for f in os.listdir(qt):
        m = re.match(r"^(Qt\w+)\.pyd$", f)
        if m and m.group(1) not in qt_usados:
            archivos.add(f"PyQt6/{f}")
        elif f.endswith(".pyd"):
            raices.append(os.path.join(qt, f))
    plugins = os.path.join(qt, "Qt6", "plugins")
    for sub in os.listdir(plugins):
        if sub in PLUGINS_QT:
            raices += [os.path.join(plugins, sub, f) for f in os.listdir(os.path.join(plugins, sub))]
        else:
            carpetas.add(f"PyQt6/Qt6/plugins/{sub}/")
    binqt = os.path.join(qt, "Qt6", "bin")
    dlls = {f.lower(): f for f in os.listdir(binqt) if f.lower().endswith(".dll")}
    necesarias, pendientes = set(), list(raices)
    while pendientes:
        for dll in _importa(pendientes.pop()):
            if dll in dlls and dll not in necesarias:
                necesarias.add(dll)
                pendientes.append(os.path.join(binqt, dlls[dll]))
    archivos |= {f"PyQt6/Qt6/bin/{dlls[k]}" for k in set(dlls) - necesarias}
    # (r119) Plantilla de python-docx en carpeta: no se usa (abre default.docx)
    # y su «[Content_Types].xml» no puede ir en un paquete MSIX (corchetes).
    carpetas.add("docx/templates/default-docx-template/")
    cv2 = os.path.join(site, "cv2")
    archivos |= {f"cv2/{f}" for f in os.listdir(cv2) if f.startswith("opencv_videoio_ffmpeg")}
    return carpetas, archivos


def _wheel(nombre: str, version: str) -> dict:
    """El wheel de PyPI de esa versión exacta que mejor encaja con este Python."""
    url = f"https://pypi.org/pypi/{nombre}/{version}/json"
    with urllib.request.urlopen(url, timeout=60) as r:
        datos = json.load(r)
    prioridad = {str(t): i for i, t in enumerate(sys_tags())}
    mejor = None
    for f in datos["urls"]:
        if f["packagetype"] != "bdist_wheel" or f.get("yanked"):
            continue
        tags = parse_wheel_filename(f["filename"])[3]
        p = min((prioridad[str(t)] for t in tags if str(t) in prioridad), default=None)
        if p is not None and (mejor is None or p < mejor[0]):
            mejor = (p, f)
    if mejor is None:
        raise SystemExit(f"PyPI no tiene un wheel de {nombre}=={version} para este Windows/Python.")
    f = mejor[1]
    return dict(url=f["url"], nombre=f["filename"], sha256=f["digests"]["sha256"], tam=f["size"])


def _extraer(zipruta: str, destino: str) -> int:
    """Descomprime y devuelve los bytes descomprimidos."""
    with zipfile.ZipFile(zipruta) as z:
        z.extractall(destino)
        return sum(i.file_size for i in z.infolist())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--versiones", required=True, help="salida de pip freeze del entorno probado")
    ap.add_argument("--propios", required=True)
    ap.add_argument("--completo", required=True)
    ap.add_argument("--iss", required=True)
    a = ap.parse_args()

    pyver = platform.python_version()
    pth = f"python{sys.version_info.major}{sys.version_info.minor}"

    # ── Propios ───────────────────────────────────────────────────────────
    app = os.path.join(a.propios, "app")
    shutil.rmtree(app, ignore_errors=True)
    shutil.rmtree(os.path.join(a.propios, "runtime"), ignore_errors=True)
    os.makedirs(app)
    modulos = _modulos()
    for m in modulos:
        shutil.copy2(os.path.join(RAIZ, m), app)
    for r in PROPIOS:
        src = os.path.join(RAIZ, r)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(app, r))
        else:
            shutil.copy2(src, os.path.join(app, r))
    os.makedirs(os.path.join(a.propios, "runtime"))
    # Sustituye al ._pth del Python embeddable (va DESPUÉS en [Files]): sin él,
    # ese Python no ve site-packages ni la carpeta de la aplicación. En modo
    # ._pth Python además ignora PYTHONPATH y los paquetes del usuario, así que
    # otro Python instalado en el equipo no interfiere.
    with open(os.path.join(a.propios, "runtime", f"{pth}._pth"), "w", encoding="ascii") as fh:
        fh.write(f"{pth}.zip\n.\nLib\\site-packages\n..\\app\nimport site\n")
    print(f"  propios: {len(modulos)} módulos de Python + {', '.join(PROPIOS)}")

    # ── Descargas ─────────────────────────────────────────────────────────
    entradas = []   # (url, nombre, destino, sha256, tamaño, extraer)
    shutil.rmtree(a.completo, ignore_errors=True)
    os.makedirs(a.completo)
    descomprimido = 0

    py_nombre = f"python-{pyver}-embed-amd64.zip"
    py_url = f"https://www.python.org/ftp/python/{pyver}/{py_nombre}"
    py_zip = _bajar(py_url, py_nombre)
    entradas.append((py_url, py_nombre, r"{app}\runtime", _sha256(py_zip), os.path.getsize(py_zip), True, []))
    descomprimido += _extraer(py_zip, os.path.join(a.completo, "runtime"))

    site = os.path.join(a.completo, "runtime", "Lib", "site-packages")
    with open(a.versiones, encoding="utf-8-sig") as fh:
        pins = [l.strip() for l in fh if re.match(r"^[A-Za-z0-9_.\-]+==", l.strip())]
    wheels = []     # (índice en entradas, ruta del wheel)
    for pin in pins:
        nombre, version = pin.split("==", 1)
        w = _wheel(nombre, version)
        ruta = _bajar(w["url"], w["nombre"], w["sha256"])
        with zipfile.ZipFile(ruta) as z:
            data = sorted({"/".join(n.split("/")[:2]) for n in z.namelist()
                           if re.match(r"^[^/]+\.data/(purelib|platlib|scripts|headers)/", n)})
        if data:
            # Código en .data/ necesita que un instalador lo mueva a su sitio:
            # descomprimirlo tal cual no basta. (.data/data/, p. ej. la página
            # de manual de fonttools, no es código y se queda ahí sin molestar.)
            raise SystemExit(f"{w['nombre']} trae {data}: no se puede instalar descomprimiéndolo.")
        # El 7-Zip de Inno Setup elige el formato por la extensión y no conoce
        # «.whl» (que es un zip): el archivo temporal se llama «….whl.zip».
        wheels.append((len(entradas), ruta))
        entradas.append((w["url"], w["nombre"] + ".zip", r"{app}\runtime\Lib\site-packages",
                         w["sha256"], w["tam"], True, []))
        descomprimido += _extraer(ruta, site)

    # (r110) Lo que no se usa de dentro de los paquetes no se descomprime.
    carpetas, archivos = _sobrantes(site, _qt_usados(modulos))
    quitado = 0
    for i, ruta in wheels:
        with zipfile.ZipFile(ruta) as z:
            fuera = [x for x in z.infolist() if not x.is_dir() and
                     (x.filename in archivos or any(x.filename.startswith(c) for c in carpetas))]
        if not fuera:
            continue
        quitado += sum(x.file_size for x in fuera)
        nombres = {x.filename for x in fuera}
        # Inno Setup: «carpeta\*» excluye lo que hay en esa carpeta, pero no en
        # sus subcarpetas: un patrón por cada carpeta con algo que excluir.
        patrones = sorted({n.rsplit("/", 1)[0].replace("/", "\\") + "\\*" for n in nombres - archivos}
                          | {n.replace("/", "\\") for n in nombres & archivos})
        entradas[i][6].extend(patrones)
    for c in carpetas:
        shutil.rmtree(os.path.join(site, c), ignore_errors=True)
    for f in archivos:
        if os.path.isfile(os.path.join(site, f)):
            os.remove(os.path.join(site, f))
    descomprimido -= quitado
    print(f"  no se descomprime lo que no se usa: {quitado / 1e6:.0f} MB "
          f"({len(carpetas)} carpetas y {len(archivos)} archivos)")

    fuentes = os.path.join(a.completo, "app", "vendor", "fonts")
    for sub, archivo, url in FUENTES:
        local = os.path.join(RAIZ, "vendor", "fonts", sub, archivo)
        sha = _sha256(local)
        ruta = _bajar(url, f"{sub}-{archivo}")
        if _sha256(ruta) != sha:
            raise SystemExit(f"{url}\nno es idéntico a vendor/fonts/{sub}/{archivo}: "
                             "actualiza el archivo del repositorio o la URL, y vuelve a probar.")
        os.makedirs(os.path.join(fuentes, sub), exist_ok=True)
        shutil.copy2(ruta, os.path.join(fuentes, sub, archivo))
        entradas.append((url, archivo, rf"{{app}}\app\vendor\fonts\{sub}", sha, os.path.getsize(ruta), False, []))
        descomprimido += os.path.getsize(ruta)

    # Encima, lo propio (como en el instalador, que lo copia después).
    shutil.copytree(a.propios, a.completo, dirs_exist_ok=True)

    # ── Entradas para Inno Setup ──────────────────────────────────────────
    lineas = [
        "; Generado por empaquetado\\componentes.py al compilar: no editar a mano.",
        "; Todo lo de terceros se descarga al instalar, de su origen oficial,",
        "; comprobando el SHA-256 de cada archivo.",
        f"#define ComponentesBytes \"{descomprimido}\"",
        f"#define ComponentesMB \"{round(sum(e[4] for e in entradas) / 1e6)}\"",
        "[Files]",
    ]
    for url, nombre, destino, sha, tam, extraer, excluir in entradas:
        flags = ("external download extractarchive recursesubdirs createallsubdirs ignoreversion"
                 if extraer else "external download ignoreversion")
        linea = (f'Source: "{url}"; DestName: "{nombre}"; DestDir: "{destino}"; '
                 f'Hash: "{sha}"; ExternalSize: {tam}; Flags: {flags}')
        if excluir:
            # Una línea por patrón, unidas con « \» (continuación de Inno Setup).
            linea += '; \\\n  Excludes: "' + ", \\\n    ".join(excluir) + '"'
        lineas.append(linea)
    with open(a.iss, "w", encoding="utf-8-sig") as fh:
        fh.write("\n".join(lineas) + "\n")
    total = sum(e[4] for e in entradas)
    print(f"  descargas al instalar: {len(entradas)} archivos, {total / 1e6:.0f} MB "
          f"({descomprimido / 1e6:.0f} MB descomprimidos); Python {pyver}, {len(pins)} paquetes")


if __name__ == "__main__":
    main()
