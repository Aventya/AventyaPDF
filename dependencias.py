"""
Paquetes de Python de AventyaPDF: todos obligatorios.

Cada arranque comprueba que todo lo de requirements.txt esté instalado en el
intérprete que ejecuta la aplicación, con la versión mínima, y si falta algo lo
instala a la fuerza con pip. Lo usan:

* run.ps1, antes de lanzar la aplicación:   python dependencias.py
* main.py, lo primero de todo (antes de importar PyQt6), por si la aplicación
  se abre sin run.ps1 (acceso directo, «Abrir con…», otro entorno).

Solo usa la biblioteca estándar: tiene que funcionar cuando aún no hay nada
instalado. Tesseract OCR no es un paquete de Python; lo gestiona
tesseract_setup.py.
"""
import importlib.metadata as metadata
import os
import re
import subprocess
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
REQUISITOS = os.path.join(RAIZ, "requirements.txt")
_CREATE_NO_WINDOW = 0x08000000


class DependenciasError(RuntimeError):
    pass


def _version(texto: str) -> tuple:
    """«6.5.0» → (6, 5, 0). Los sufijos (rc1, .post1…) no cuentan."""
    partes = []
    for p in texto.split("."):
        m = re.match(r"\d+", p)
        if not m:
            break
        partes.append(int(m.group()))
    return tuple(partes)


def requisitos(ruta: str = REQUISITOS) -> list[tuple[str, tuple]]:
    """[(paquete, versión mínima)] de requirements.txt (solo «nombre>=x.y»)."""
    out = []
    with open(ruta, encoding="utf-8") as fh:
        for linea in fh:
            linea = linea.split("#", 1)[0].strip()
            if not linea:
                continue
            m = re.match(r"([A-Za-z0-9_.\-]+)\s*(?:>=\s*([\w.]+))?", linea)
            if m:
                out.append((m.group(1), _version(m.group(2) or "0")))
    return out


def faltan(ruta: str = REQUISITOS) -> list[str]:
    """Requisitos que no están instalados o tienen una versión menor."""
    out = []
    for nombre, minima in requisitos(ruta):
        try:
            instalada = _version(metadata.version(nombre))
        except metadata.PackageNotFoundError:
            out.append(nombre)
            continue
        if instalada < minima:
            out.append(f"{nombre} (hay {'.'.join(map(str, instalada))})")
    return out


def instalar(ruta: str = REQUISITOS, report=print) -> None:
    """pip install -r requirements.txt en el intérprete actual."""
    report("Instalando los componentes de AventyaPDF (puede tardar unos minutos)…")
    visible = sys.stdout is not None
    import importlib.util
    if importlib.util.find_spec("pip") is None:        # intérprete sin pip
        subprocess.run([sys.executable, "-m", "ensurepip", "--upgrade"],
                       capture_output=True, creationflags=0 if visible else _CREATE_NO_WINDOW)
    cmd = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
           "-r", ruta]
    cp = subprocess.run(
        cmd,
        stdout=None if visible else subprocess.DEVNULL,
        stderr=None if visible else subprocess.PIPE,
        text=True,
        creationflags=0 if visible else _CREATE_NO_WINDOW,
    )
    if cp.returncode != 0:
        detalle = (cp.stderr or "").strip().splitlines()[-1:] if not visible else []
        raise DependenciasError(
            "pip no pudo instalar los componentes (código "
            f"{cp.returncode}). {detalle[0] if detalle else ''}".strip())
    # Paquetes recién instalados: que el proceso actual los vea.
    import importlib
    importlib.invalidate_caches()


def asegurar(ruta: str = REQUISITOS, report=print) -> None:
    """Instala a la fuerza lo que falte; si aun así falta algo, lanza
    DependenciasError con la lista."""
    pendientes = faltan(ruta)
    if not pendientes:
        return
    report("Faltan componentes: " + ", ".join(pendientes))
    instalar(ruta, report)
    pendientes = faltan(ruta)
    if pendientes:
        raise DependenciasError("Siguen faltando componentes: " + ", ".join(pendientes))


def _aviso_grafico(texto: str) -> None:
    """Sin consola (pythonw) no se vería nada: caja de mensaje de Windows."""
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, texto, "AventyaPDF", 0x10)
    except Exception:  # noqa: BLE001
        pass


def asegurar_o_salir() -> None:
    """Para main.py: si no se pueden instalar, avisa y termina (sin PyQt6 ni
    PyMuPDF la aplicación no puede arrancar)."""
    if getattr(sys, "frozen", False):
        # (r62) Aplicación instalada (PyInstaller): los paquetes van dentro del
        # ejecutable y no hay pip ni requirements.txt con los que instalar.
        return
    try:
        asegurar(report=(print if sys.stdout is not None else (lambda _t: None)))
    except (DependenciasError, OSError) as e:
        texto = (f"No se pudieron instalar los componentes necesarios.\n\n{e}\n\n"
                 "Comprueba la conexión a Internet y vuelve a abrir la aplicación.")
        if sys.stderr is not None:
            print(texto, file=sys.stderr)
        else:
            _aviso_grafico(texto)
        raise SystemExit(1)


def main() -> int:
    try:
        asegurar()
    except (DependenciasError, OSError) as e:
        print(e, file=sys.stderr)
        return 1
    print("Componentes de Python: todo instalado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
