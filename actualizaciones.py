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
import urllib.error
import urllib.request
from idioma import tr

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
        raise UpdateError(tr("GitHub respondió con el error {code}.").format(code=e.code)) from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        motivo = getattr(e, "reason", e)
        raise UpdateError(tr("No hay conexión con GitHub ({motivo}).").format(motivo=motivo)) from e
    except ValueError as e:
        raise UpdateError(tr("GitHub devolvió una respuesta que no se entiende.")) from e
    return release_info(data)


# ── Descargar sin pasar por el navegador (r121, r127) ───────────────────── #
# Petición de Ricardo (r121): «el descargar de la actualización sí que quiero
# que se haga por detrás, sin acceso al navegador». (r127) «Lo que me gustaría
# es que la descarga de las actualizaciones sea directa desde la propia
# aplicación pero que se quedase en la carpeta Descargas y se indique que la
# actualización está allí esperando a que la instale el usuario, para que la
# aplicación no utilice PowerShell»: hasta r125 la aplicación se cerraba y
# lanzaba el instalador con PowerShell oculto, una de las cosas por las que
# Microsoft Defender la marcaba. Ahora solo descarga; instala el usuario.

_FOLDERID_DOWNLOADS = "{374DE290-123F-4565-9164-39C4925E467B}"


def carpeta_descargas() -> str:
    """La carpeta Descargas del usuario (la de verdad, aunque la haya movido a
    otra unidad o a OneDrive); si Windows no la da, ~/Downloads."""
    if os.name == "nt":
        try:
            import ctypes
            import uuid
            from ctypes import wintypes
            guid = (ctypes.c_byte * 16).from_buffer_copy(uuid.UUID(_FOLDERID_DOWNLOADS).bytes_le)
            ruta = ctypes.c_wchar_p()
            shell32, ole32 = ctypes.windll.shell32, ctypes.windll.ole32
            shell32.SHGetKnownFolderPath.argtypes = [ctypes.c_void_p, wintypes.DWORD, wintypes.HANDLE,
                                                     ctypes.POINTER(ctypes.c_wchar_p)]
            if shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(ruta)) == 0:
                try:
                    if ruta.value and os.path.isdir(ruta.value):
                        return ruta.value
                finally:
                    ole32.CoTaskMemFree(ruta)
        except (OSError, AttributeError, ValueError):
            pass
    return os.path.join(os.path.expanduser("~"), "Downloads")


def _sha256(ruta: str) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as fh:
        for bloque in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def instalador_descargado(info: dict, carpeta: str | None = None) -> str | None:
    """Ruta del instalador de `info` si ya está en Descargas y es el
    publicado (misma huella SHA-256 o, si GitHub no la diera, mismo tamaño):
    la actualización que espera a que el usuario la instale."""
    if not info.get("installer_name"):
        return None
    ruta = os.path.join(carpeta or carpeta_descargas(), info["installer_name"])
    if not os.path.isfile(ruta):
        return None
    esperado = (info.get("installer_sha256") or "").lower()
    try:
        if esperado:
            return ruta if _sha256(ruta) == esperado else None
        tam = info.get("installer_size") or 0
        return ruta if tam and os.path.getsize(ruta) == tam else None
    except OSError:
        return None


def download_installer(info: dict, progress=None, timeout: float = 60,
                       carpeta: str | None = None) -> str:
    """Descarga el instalador de `info` a la carpeta Descargas (o a `carpeta`)
    y comprueba su SHA-256 con el que publica GitHub; si ya estaba allí y es
    el mismo, no lo vuelve a bajar. `progress(bytes, total)` opcional.
    Devuelve la ruta; lanza UpdateError si algo falla."""
    if not info.get("installer_name"):
        raise UpdateError(tr("La publicación no tiene instalador."))
    carpeta = carpeta or carpeta_descargas()
    hecho = instalador_descargado(info, carpeta)
    if hecho:
        return hecho
    destino = os.path.join(carpeta, info["installer_name"])
    req = urllib.request.Request(info["installer_url"], headers={"User-Agent": f"{REPO}-actualizaciones"})
    h = hashlib.sha256()
    try:
        os.makedirs(carpeta, exist_ok=True)
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
        raise UpdateError(tr("No se pudo descargar el instalador ({getattr}).").format(getattr=getattr(e, 'reason', e))) from e
    esperado = info.get("installer_sha256", "")
    if esperado and h.hexdigest() != esperado.lower():
        os.remove(destino + ".part")
        raise UpdateError(tr("El instalador descargado no coincide con el publicado (huella SHA-256): "
                          "se ha borrado."))
    os.replace(destino + ".part", destino)
    return destino


def mostrar_en_carpeta(ruta: str) -> None:
    """Abre la carpeta de `ruta` en el Explorador con el archivo seleccionado
    (SHOpenFolderAndSelectItems, sin lanzar ningún intérprete)."""
    if os.name != "nt":
        return
    import ctypes
    shell32 = ctypes.windll.shell32
    shell32.ILCreateFromPathW.restype = ctypes.c_void_p
    shell32.ILCreateFromPathW.argtypes = [ctypes.c_wchar_p]
    shell32.SHOpenFolderAndSelectItems.argtypes = [ctypes.c_void_p, ctypes.c_uint,
                                                   ctypes.c_void_p, ctypes.c_ulong]
    shell32.ILFree.argtypes = [ctypes.c_void_p]
    pidl = shell32.ILCreateFromPathW(os.path.abspath(ruta))
    if not pidl:
        os.startfile(os.path.dirname(ruta))
        return
    try:
        ctypes.windll.ole32.CoInitialize(None)
        if shell32.SHOpenFolderAndSelectItems(pidl, 0, None, 0) != 0:
            os.startfile(os.path.dirname(ruta))
    finally:
        shell32.ILFree(pidl)


# ── (r141) Manual de AventyaPDF ─────────────────────────────────────────── #
# Petición de Ricardo: «el manual que se empaqueta con la aplicación es un
# error, lo conveniente es tener acceso al PDF subido a GitHub de manera que se
# descargue y se abra automáticamente en la aplicación sin usar PowerShell».
# Se descarga con urllib (como el instalador) a una carpeta propia y se guarda
# la marca (ETag) que da GitHub: la vez siguiente solo se vuelve a bajar si el
# manual ha cambiado, y sin conexión se abre la copia que haya.

MANUAL_URL = ("https://raw.githubusercontent.com/" + OWNER + "/" + REPO
              + "/main/docs/manual/MANUAL_{codigo}.pdf")
CARPETA_MANUAL = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
                              "aventyapdf", "manual")


def descargar_manual(codigo: str, timeout: float = 30, carpeta: str | None = None) -> str:
    """Ruta del manual en el idioma `codigo`, descargado de GitHub o el que ya
    estaba si no ha cambiado. Si ese idioma no está publicado, el español. Sin
    conexión, la copia anterior si la hay; si no, UpdateError."""
    carpeta = carpeta or CARPETA_MANUAL
    os.makedirs(carpeta, exist_ok=True)
    ultimo_error = None
    for c in dict.fromkeys((codigo, "es")):
        destino = os.path.join(carpeta, f"MANUAL_{c}.pdf")
        marca = destino + ".etag"
        cabeceras = {"User-Agent": f"{REPO}-manual"}
        if os.path.isfile(destino) and os.path.isfile(marca):
            with open(marca, encoding="utf-8") as fh:
                cabeceras["If-None-Match"] = fh.read().strip()
        req = urllib.request.Request(MANUAL_URL.format(codigo=c), headers=cabeceras)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                datos = resp.read()
                etag = resp.headers.get("ETag", "")
        except urllib.error.HTTPError as e:
            if e.code == 304:                       # sin cambios: la copia sirve
                return destino
            ultimo_error = e
            if e.code == 404:                       # ese idioma no está: el siguiente
                continue
            break
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            ultimo_error = e
            break
        if not datos.startswith(b"%PDF"):
            ultimo_error = ValueError("no es un PDF")
            break
        with open(destino + ".part", "wb") as fh:
            fh.write(datos)
        os.replace(destino + ".part", destino)
        with open(marca, "w", encoding="utf-8") as fh:
            fh.write(etag)
        return destino
    # Sin conexión (o GitHub sin responder): la copia que haya.
    for c in dict.fromkeys((codigo, "es")):
        destino = os.path.join(carpeta, f"MANUAL_{c}.pdf")
        if os.path.isfile(destino):
            return destino
    razon = getattr(ultimo_error, "reason", ultimo_error)
    raise UpdateError(tr("No se pudo descargar el manual ({razon}).").format(razon=razon))
