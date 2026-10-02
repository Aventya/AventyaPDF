"""
Comprobación de actualizaciones (petición de Ricardo).

«Ayuda › Buscar actualizaciones…» pregunta a GitHub, donde se publica
AventyaPDF, cuál es la última versión y ofrece el **enlace directo** a su
instalador. El enlace no está escrito en el programa: sale de la publicación
más reciente cada vez que se consulta, así que siempre apunta al último
instalador subido. Las versiones previas (0.9.x, marcadas como «Pre-release»)
no cuentan: la API `releases/latest` solo devuelve la última versión estable.

Sin Qt: la ventana (window_menus.check_updates) solo pinta el resultado.
"""
import hashlib
import json
import os
import re
import subprocess
import tempfile
import urllib.error
import urllib.request

# Repositorio donde se publica todo (código y versiones).
OWNER, REPO = "Aventya", "AventyaPDF"
RELEASES_URL = f"https://github.com/{OWNER}/{REPO}/releases"
LATEST_API = f"https://api.github.com/repos/{OWNER}/{REPO}/releases/latest"
TIMEOUT = 10          # segundos


class UpdateError(Exception):
    """No se pudo consultar la última versión (sin conexión, GitHub caído…)."""


def parse_version(text: str) -> tuple[int, ...]:
    """«v1.2.3» o «1.2.3» → (1, 2, 3). Lo que no sea número se ignora."""
    nums = re.findall(r"\d+", text or "")
    return tuple(int(n) for n in nums[:3]) or (0,)


def is_newer(remote: str, local: str) -> bool:
    """¿La versión `remote` es posterior a `local`? (1.0.10 > 1.0.9)"""
    r, l = parse_version(remote), parse_version(local)
    width = max(len(r), len(l))
    return r + (0,) * (width - len(r)) > l + (0,) * (width - len(l))


def release_info(data: dict) -> dict:
    """De la respuesta de la API de GitHub, lo que necesita la ventana:
    versión, página de la publicación y enlace directo al instalador (el
    primer `.exe` adjunto; si no hubiera, la página de la publicación)."""
    tag = data.get("tag_name", "")
    page = data.get("html_url") or RELEASES_URL
    installer = next((a for a in data.get("assets", [])
                      if a.get("name", "").lower().endswith(".exe")), None)
    return {
        "version": ".".join(str(n) for n in parse_version(tag)),
        "tag": tag,
        "page_url": page,
        "installer_name": installer["name"] if installer else "",
        "installer_url": installer["browser_download_url"] if installer else page,
        # (r121) Huella que publica GitHub de cada archivo («sha256:…»).
        "installer_sha256": ((installer or {}).get("digest") or "").removeprefix("sha256:"),
        "installer_size": (installer or {}).get("size") or 0,
    }


def fetch_latest(timeout: float = TIMEOUT) -> dict:
    """Consulta a GitHub la última versión publicada (ver `release_info`)."""
    req = urllib.request.Request(LATEST_API, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{REPO}-actualizaciones",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        raise UpdateError(f"GitHub respondió con el error {e.code}.") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        motivo = getattr(e, "reason", e)
        raise UpdateError(f"No hay conexión con GitHub ({motivo}).") from e
    except ValueError as e:
        raise UpdateError("GitHub devolvió una respuesta que no se entiende.") from e
    return release_info(data)


# ── Descargar e instalar sin pasar por el navegador (r121) ──────────────── #
# Petición de Ricardo: «el descargar de la actualización sí que quiero que se
# haga por detrás, sin acceso al navegador». Descargado así (urllib), el
# archivo no lleva la marca «descargado de Internet» que ponen los
# navegadores, y Windows SmartScreen no avisa al ejecutarlo.

def download_installer(info: dict, progress=None, timeout: float = 60) -> str:
    """Descarga el instalador de `info` a una carpeta temporal y comprueba su
    SHA-256 con el que publica GitHub. `progress(bytes, total)` opcional.
    Devuelve la ruta; lanza UpdateError si algo falla."""
    if not info.get("installer_name"):
        raise UpdateError("La publicación no tiene instalador.")
    carpeta = os.path.join(tempfile.gettempdir(), "aventyapdf-actualizacion")
    os.makedirs(carpeta, exist_ok=True)
    destino = os.path.join(carpeta, info["installer_name"])
    req = urllib.request.Request(info["installer_url"], headers={"User-Agent": f"{REPO}-actualizaciones"})
    h = hashlib.sha256()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp, open(destino + ".part", "wb") as fh:
            total = int(resp.headers.get("Content-Length") or info.get("installer_size") or 0)
            hecho = 0
            while True:
                bloque = resp.read(1 << 16)
                if not bloque:
                    break
                fh.write(bloque)
                h.update(bloque)
                hecho += len(bloque)
                if progress:
                    progress(hecho, total)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise UpdateError(f"No se pudo descargar el instalador ({getattr(e, 'reason', e)}).") from e
    esperado = info.get("installer_sha256", "")
    if esperado and h.hexdigest() != esperado.lower():
        os.remove(destino + ".part")
        raise UpdateError("El instalador descargado no coincide con el publicado (huella SHA-256): "
                          "no se instala.")
    os.replace(destino + ".part", destino)
    return destino


def launch_installer_after_exit(installer: str, pid: int) -> None:
    """Cuando termine el proceso `pid` (esta aplicación, que se cierra para
    dejar sustituir sus archivos), ejecuta el instalador en modo silencioso
    con su barra de progreso; al acabar vuelve a abrir AventyaPDF
    (/REINICIAR, ver [Run] de AventyaPDF.iss)."""
    ps = (f"Wait-Process -Id {int(pid)} -Timeout 120 -ErrorAction SilentlyContinue; "
          f"Start-Process -FilePath '{installer.replace(chr(39), chr(39) * 2)}' "
          "-ArgumentList '/SILENT','/NOCANCEL','/NORESTART','/REINICIAR'")
    # Solo CREATE_NO_WINDOW: con DETACHED_PROCESS powershell.exe se queda sin
    # consola y se cierra sin ejecutar nada. Así sigue vivo al cerrarse la app.
    subprocess.Popen(["powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden",
                      "-Command", ps], creationflags=0x08000000)   # CREATE_NO_WINDOW
