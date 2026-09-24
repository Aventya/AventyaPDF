"""
Tesseract OCR: parte obligatoria de AventyaPDF.

El OCR de PyMuPDF (Pixmap.pdfocr_tobytes) usa el motor de Tesseract que MuPDF
lleva dentro, pero necesita los datos de idioma («tessdata») y los busca en
TESSDATA_PREFIX o preguntando a «tesseract --list-langs», que falla porque el
instalador de Windows no añade Tesseract al PATH. Por eso:

* Tesseract (UB Mannheim; paquete de winget UB-Mannheim.TesseractOCR) se
  comprueba al lanzar/instalar (run.ps1) y al iniciar la aplicación (main.py).
  Si falta se instala a la fuerza: winget en silencio y, si no hay winget o
  falla, el instalador oficial con /S. Los dos piden permiso de administrador.
* Los idiomas viven en %LOCALAPPDATA%\\aventyapdf\\tessdata (sin permisos
  de administrador): español, inglés y osd siempre; el resto cuando se eligen
  en «Reconocer texto». Se descargan de github.com/tesseract-ocr/tessdata_best
  (los modelos más precisos); los que no llevan la marca «.best» se sustituyen.
* configure_environment() fija TESSDATA_PREFIX y añade Tesseract al PATH del
  proceso.
* (r62) En la aplicación instalada (AventyaPDF.exe, PyInstaller) Tesseract va
  DENTRO, en {app}\tesseract, con los idiomas «best» de español, inglés y osd
  en su tessdata: se usa ese antes que ninguno y los idiomas se copian de ahí en
  vez de descargarse. El OCR funciona nada más instalar, sin internet ni
  permisos de administrador.

Desde consola (run.ps1):   python tesseract_setup.py
"""
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from dataclasses import dataclass, field

WINGET_ID = "UB-Mannheim.TesseractOCR"
INSTALLER_URL = ("https://github.com/UB-Mannheim/tesseract/releases/download/"
                 "v5.4.0.20240606/tesseract-ocr-w64-setup-5.4.0.20240606.exe")
# Modelos «best» (LSTM de coma flotante): los más precisos. Los de la instalación
# de UB Mannheim son «fast» y los estándar tampoco llegan a su precisión.
TESSDATA_URL = "https://github.com/tesseract-ocr/tessdata_best/raw/main/{lang}.traineddata"
MODEL_MARKER = ".best"          # junto a cada modelo: «spa.traineddata.best»
TESSDATA_DIR = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
                            "aventyapdf", "tessdata")
CORE_LANGS = ("spa", "eng", "osd")
# (r62) Tesseract incluido en la aplicación instalada (junto a AventyaPDF.exe).
# Desde el código fuente no existe y todo sigue como siempre.
APP_DIR = (os.path.dirname(sys.executable) if getattr(sys, "frozen", False)
           else os.path.dirname(os.path.abspath(__file__)))
BUNDLED_EXE = os.path.join(APP_DIR, "tesseract", "tesseract.exe")
BUNDLED_TESSDATA = os.path.join(APP_DIR, "tesseract", "tessdata")
PDF_FONT = "pdf.ttf"            # letra invisible de la capa de texto de Tesseract
INSTALL_TIMEOUT = 30 * 60
_CREATE_NO_WINDOW = 0x08000000


class TesseractSetupError(RuntimeError):
    pass


@dataclass
class Status:
    exe: str | None
    missing_langs: list = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return self.exe is not None and not self.missing_langs


# ── Detección ──────────────────────────────────────────────────────────── #

def _candidates():
    for base in (os.environ.get("ProgramFiles"), os.environ.get("ProgramW6432"),
                 os.environ.get("ProgramFiles(x86)"),
                 os.path.join(os.environ["LOCALAPPDATA"], "Programs")
                 if os.environ.get("LOCALAPPDATA") else None):
        if base:
            yield os.path.join(base, "Tesseract-OCR", "tesseract.exe")
    try:
        import winreg
    except ImportError:
        return
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        for sub in (r"SOFTWARE\Tesseract-OCR", r"SOFTWARE\WOW6432Node\Tesseract-OCR"):
            try:
                with winreg.OpenKey(hive, sub) as key:
                    yield os.path.join(winreg.QueryValueEx(key, "InstallDir")[0], "tesseract.exe")
            except OSError:
                continue


def find_tesseract() -> str | None:
    if os.path.isfile(BUNDLED_EXE):          # (r62) el incluido, antes que ninguno
        return BUNDLED_EXE
    exe = shutil.which("tesseract")
    if exe:
        return exe
    for candidate in _candidates():
        if candidate and os.path.isfile(candidate):
            return candidate
    return None


def normalize_langs(langs) -> list[str]:
    """«spa+eng» o ["spa", "eng"] → ["spa", "eng"] (sin repetidos)."""
    items = langs.split("+") if isinstance(langs, str) else list(langs)
    out = []
    for lang in (l.strip() for l in items):
        if lang and lang not in out:
            out.append(lang)
    return out


def missing_langs(langs, tessdata: str | None = None) -> list[str]:
    """Idiomas sin modelo «best» (un modelo sin marca, estándar o fast, cuenta
    como que falta y se sustituye)."""
    folder = tessdata or TESSDATA_DIR
    return [l for l in normalize_langs(langs)
            if not (os.path.isfile(os.path.join(folder, f"{l}.traineddata"))
                    and os.path.isfile(os.path.join(folder, f"{l}.traineddata{MODEL_MARKER}")))]


def status(langs=CORE_LANGS) -> Status:
    return Status(find_tesseract(), missing_langs(langs))


def configure_environment() -> None:
    """TESSDATA_PREFIX → nuestra carpeta de idiomas; Tesseract en el PATH."""
    os.environ["TESSDATA_PREFIX"] = TESSDATA_DIR
    exe = find_tesseract()
    if exe:
        folder = os.path.dirname(exe)
        path = os.environ.get("PATH", "")
        if folder.lower() not in (p.lower() for p in path.split(os.pathsep)):
            os.environ["PATH"] = folder + os.pathsep + path


# ── Instalación ────────────────────────────────────────────────────────── #

def _run(cmd: list[str], timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout,
                          creationflags=_CREATE_NO_WINDOW if os.name == "nt" else 0)


def _download(url: str, dest: str, report, label: str) -> None:
    tmp = dest + ".part"
    with urllib.request.urlopen(url, timeout=60) as resp, open(tmp, "wb") as fh:
        total = int(resp.headers.get("Content-Length") or 0)
        done, last = 0, -1
        while chunk := resp.read(256 * 1024):
            fh.write(chunk)
            done += len(chunk)
            pct = done * 100 // total if total else -1
            if pct != last and (pct < 0 or pct % 5 == 0):
                report(f"Descargando {label}… {pct} %" if pct >= 0 else f"Descargando {label}…")
                last = pct
    os.replace(tmp, dest)


def _install_with_winget(report) -> str:
    winget = shutil.which("winget")
    if not winget:
        return "winget no está disponible en este equipo"
    report("Instalando Tesseract OCR con winget…\n(Windows pedirá permiso de administrador)")
    cp = _run([winget, "install", "--id", WINGET_ID, "--exact", "--silent",
               "--accept-package-agreements", "--accept-source-agreements",
               "--disable-interactivity"], INSTALL_TIMEOUT)
    if cp.returncode != 0:
        detail = (cp.stdout + cp.stderr).strip().splitlines()[-1:] or [""]
        return f"winget terminó con el código {cp.returncode} {detail[0]}".strip()
    return ""


def _install_with_installer(report) -> str:
    folder = tempfile.mkdtemp(prefix="agpdf_tesseract_")
    try:
        exe = os.path.join(folder, "tesseract-ocr-setup.exe")
        _download(INSTALLER_URL, exe, report, "el instalador de Tesseract OCR")
        report("Instalando Tesseract OCR…\n(Windows pedirá permiso de administrador)")
        script = (f"$p = Start-Process -FilePath '{exe}' -ArgumentList '/S' "
                  "-Verb RunAs -Wait -PassThru; exit $p.ExitCode")
        cp = _run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                  INSTALL_TIMEOUT)
        if cp.returncode != 0:
            return f"el instalador oficial terminó con el código {cp.returncode}"
        return ""
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def install_tesseract(report=None) -> str:
    """Instala Tesseract a la fuerza. Devuelve la ruta de tesseract.exe."""
    report = report or (lambda _msg: None)
    errors = []
    for label, installer in (("winget", _install_with_winget),
                             ("instalador oficial", _install_with_installer)):
        try:
            error = installer(report)
        except Exception as e:  # noqa: BLE001 — sin red, permiso denegado…
            error = f"{label}: {e}"
        exe = find_tesseract()
        if exe:
            return exe
        if error:
            errors.append(error)
    raise TesseractSetupError("No se pudo instalar Tesseract OCR:\n- " + "\n- ".join(errors))


def download_langs(langs, report=None) -> None:
    report = report or (lambda _msg: None)
    os.makedirs(TESSDATA_DIR, exist_ok=True)
    for lang in missing_langs(langs):
        dest = os.path.join(TESSDATA_DIR, f"{lang}.traineddata")
        incluido = os.path.join(BUNDLED_TESSDATA, f"{lang}.traineddata")
        if os.path.isfile(incluido) and os.path.isfile(incluido + MODEL_MARKER):
            # (r62) El instalador lo trae: se copia, sin descargar nada.
            report(f"Preparando el idioma «{lang}»…")
            shutil.copyfile(incluido, dest)
            shutil.copyfile(incluido + MODEL_MARKER, dest + MODEL_MARKER)
            continue
        # Siempre «best» (no se copian los de la instalación, que son «fast»).
        _download(TESSDATA_URL.format(lang=lang), dest, report, f"el idioma «{lang}» (máxima precisión)")
        with open(dest + MODEL_MARKER, "w", encoding="utf-8") as fh:
            fh.write(TESSDATA_URL.format(lang=lang))


def ensure_pdf_font() -> str:
    """(r60) El OCR llama a tesseract.exe para generar la capa de texto en PDF
    (pdf_ocr) y Tesseract busca su letra invisible «pdf.ttf» en la carpeta de
    idiomas: se copia la de la instalación a TESSDATA_DIR. Devuelve la ruta."""
    dest = os.path.join(TESSDATA_DIR, PDF_FONT)
    if os.path.isfile(dest):
        return dest
    exe = find_tesseract()
    origen = os.path.join(os.path.dirname(exe), "tessdata", PDF_FONT) if exe else ""
    if not os.path.isfile(origen):
        raise TesseractSetupError(
            f"Falta «{PDF_FONT}» en la instalación de Tesseract ({origen or 'no encontrada'}).")
    os.makedirs(TESSDATA_DIR, exist_ok=True)
    shutil.copyfile(origen, dest)
    return dest


def ensure(langs=CORE_LANGS, report=None) -> Status:
    """Deja Tesseract y los idiomas listos (instalando lo que falte) o lanza
    TesseractSetupError con un mensaje legible."""
    report = report or (lambda _msg: None)
    if not find_tesseract():
        install_tesseract(report)
    missing = missing_langs(langs)
    if missing:
        try:
            download_langs(missing, report)
        except Exception as e:  # noqa: BLE001
            raise TesseractSetupError(
                f"No se pudieron descargar los idiomas de OCR ({', '.join(missing)}): {e}") from e
    configure_environment()
    try:
        ensure_pdf_font()
    except TesseractSetupError as e:     # el OCR lo volverá a pedir, con este mensaje
        report(str(e))
    st = status(langs)
    if not st.ready:
        raise TesseractSetupError(
            "Tesseract OCR no quedó listo: "
            + ("no se encuentra tesseract.exe" if not st.exe
               else f"faltan los idiomas {', '.join(st.missing_langs)}"))
    return st


def verify_ocr(lang: str = "spa") -> None:
    """Reconoce un texto de prueba por el mismo camino que la aplicación
    (pdf_ocr: tesseract.exe; r60, antes el motor de PyMuPDF)."""
    import fitz
    import pdf_ocr
    doc = fitz.open()
    page = doc.new_page(width=320, height=90)
    page.insert_image(page.rect, pixmap=_imagen_de_prueba(fitz))
    try:
        pdf_ocr.ocr_page(page, lang, detect_orientation=False)
        text = page.get_text()
    except Exception as e:  # noqa: BLE001
        raise TesseractSetupError(f"El OCR no funciona: {e}") from e
    if "Hola" not in text:
        raise TesseractSetupError(f"El OCR no reconoce el texto de prueba (obtenido: {text!r}).")


def _imagen_de_prueba(fitz):
    """«Hola 2026» como imagen (el OCR no toca el texto que ya es seleccionable)."""
    tmp = fitz.open()
    p = tmp.new_page(width=320, height=90)
    p.insert_text((20, 58), "Hola 2026", fontsize=36)
    return p.get_pixmap(dpi=200)


def main() -> int:
    try:
        st = ensure(CORE_LANGS, lambda msg: print(msg.replace("\n", " "), flush=True))
        verify_ocr("spa")
    except TesseractSetupError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    print(f"Tesseract OCR listo: {st.exe}  ·  idiomas en {TESSDATA_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
