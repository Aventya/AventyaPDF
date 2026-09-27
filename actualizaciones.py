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
import json
import re
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
