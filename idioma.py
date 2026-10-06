"""
idioma.py — Textos de la aplicación en varios idiomas (r136).

Todo texto que ve el usuario pasa por `tr("texto en español")`. El español es
el idioma de referencia: la clave de cada texto es el propio texto en español.
`idiomas/<código>.json` tiene, para cada idioma, `{"texto en español":
"traducción"}`; `idiomas/es.json` es el catálogo completo (cada texto se
traduce a sí mismo) y sirve de lista de lo que hay que traducir. Un texto que
falte en un idioma sale en español.

Los textos con datos llevan marcadores con nombre, que la traducción conserva
tal cual: `tr("Abierto: {nombre}").format(nombre=…)`.

El idioma se elige así, en este orden:
1. la variable de entorno `AVENTYAPDF_IDIOMA` (pruebas y sesiones en la nube);
2. el ajuste `ui/idioma` de la configuración (lo escribe el instalador con el
   idioma elegido al instalar y el menú Ayuda › Idioma);
3. el idioma de Windows, si es uno de los disponibles;
4. si no, inglés.

Se lee sin Qt (registro de Windows o archivo .conf de Qt en Linux) porque este
módulo se importa en procesos que deben terminar enseguida (menu_contextual) y
porque las constantes con texto de los módulos se traducen al importarlos. El
cambio de idioma se aplica al volver a abrir la aplicación.
"""
import json
import os
import sys

IDIOMAS = {
    "es": "Español",
    "en": "English",
    "fr": "Français",
    "it": "Italiano",
    "ca": "Català",
    "gl": "Galego",
    "eu": "Euskara",
}
REFERENCIA = "es"
SIN_PREFERENCIA = "en"           # idioma de Windows que no está en IDIOMAS
CLAVE = "ui/idioma"              # en QSettings("aventyapdf", "config")

CARPETA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "idiomas")

# Identificador principal de idioma de Windows (LANGID & 0x3FF) → código.
_WINDOWS = {0x0A: "es", 0x09: "en", 0x0C: "fr", 0x10: "it", 0x03: "ca",
            0x56: "gl", 0x2D: "eu"}


def _ajuste_guardado() -> str:
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\aventyapdf\config\ui") as k:
                valor, _tipo = winreg.QueryValueEx(k, "idioma")
                return str(valor)
        except OSError:
            return ""
    import configparser
    ruta = os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"),
                        "aventyapdf", "config.conf")
    cp = configparser.ConfigParser(interpolation=None)
    try:
        cp.read(ruta, encoding="utf-8")
        return cp.get("ui", "idioma", fallback="")
    except (configparser.Error, OSError):
        return ""


def idioma_del_sistema() -> str:
    """Código del idioma de Windows (o del entorno, fuera de Windows), si es
    uno de los disponibles; si no, SIN_PREFERENCIA."""
    if sys.platform == "win32":
        try:
            import ctypes
            langid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            return _WINDOWS.get(langid & 0x3FF, SIN_PREFERENCIA)
        except Exception:
            return SIN_PREFERENCIA
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        codigo = (os.environ.get(var) or "").split("_")[0].split(".")[0].lower()
        if codigo:
            return codigo if codigo in IDIOMAS else SIN_PREFERENCIA
    return SIN_PREFERENCIA


def elegido() -> str:
    """Idioma con el que arranca la aplicación (ver la cabecera)."""
    for codigo in (os.environ.get("AVENTYAPDF_IDIOMA", ""), _ajuste_guardado()):
        if codigo in IDIOMAS:
            return codigo
    return idioma_del_sistema()


def cargar_textos(codigo: str) -> dict[str, str]:
    """Traducciones de un idioma ({} para el español o si falta el archivo)."""
    if codigo == REFERENCIA:
        return {}
    try:
        with open(os.path.join(CARPETA, codigo + ".json"), encoding="utf-8") as f:
            datos = json.load(f)
    except (OSError, ValueError):
        return {}
    return {k: v for k, v in datos.items() if isinstance(v, str) and v}


ACTUAL = elegido()
_TEXTOS = cargar_textos(ACTUAL)


def tr(texto: str) -> str:
    """El texto en el idioma de la aplicación (en español si no hay traducción)."""
    return _TEXTOS.get(texto, texto)


def tr_en(codigo: str, texto: str) -> str:
    """El texto en otro idioma: para avisar en el idioma recién elegido."""
    return cargar_textos(codigo).get(texto, texto)


def guardar(codigo: str) -> None:
    """Idioma para la próxima vez que se abra la aplicación."""
    from PyQt6.QtCore import QSettings
    s = QSettings("aventyapdf", "config")
    s.setValue(CLAVE, codigo)
    s.sync()
