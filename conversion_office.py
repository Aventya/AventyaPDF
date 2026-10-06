"""
conversion_office.py — Documentos de Word (.doc, .docx) a PDF (r86).

AventyaPDF no lee Word por sí misma: delega en lo que haya instalado.
1. Microsoft Word, por automatización COM (word_com.py, con comtypes, en un
   proceso aparte; hasta r125, desde PowerShell). Es la conversión más fiel.
2. Si no hay Word o falla: LibreOffice en modo sin ventana (`soffice
   --headless --convert-to pdf`).
Si no hay ninguno de los dos, `ConversionError` lo explica.

`archivos_a_pdfs` es la puerta común del menú contextual: convierte una lista
mezclada de PDF, imágenes y documentos de Word en documentos fitz, en el mismo
orden, sin escribir nada junto a los originales (todo pasa por una carpeta
temporal que se borra).
"""
import os
import shutil
import subprocess
import sys
import tempfile

import fitz

import doc_tools
from idioma import tr

WORD_EXTS = {".doc", ".docx"}
# Mismo conjunto que window_document.IMAGE_EXTS (y que la extensión del
# Explorador, shell/AventyaPDFShell.cpp): si se amplía, en los tres sitios.
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp"}

# (r123) Diálogos de abrir varios archivos: todo lo que la aplicación sabe
# mostrar (PDF, y también imágenes y Word, que se convierten a PDF).
_PATRON = " ".join("*" + e for e in sorted(IMAGE_EXTS))
FILTRO_ABRIR = tr(("Todos los admitidos (*.pdf {_PATRON} *.doc *.docx);;"
                "Archivos PDF (*.pdf);;"
                "Imágenes ({_PATRON});;"
                "Documentos de Word (*.doc *.docx)")).format(_PATRON=_PATRON)

_SIN_VENTANA = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_TIEMPO_MAX = 300          # segundos para toda una tanda de documentos

class ConversionError(RuntimeError):
    pass


def _soffice() -> str | None:
    for p in (shutil.which("soffice"),
              os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"),
                           "LibreOffice", "program", "soffice.exe"),
              os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
                           "LibreOffice", "program", "soffice.exe")):
        if p and os.path.isfile(p):
            return p
    return None


def _con_word(pares: list[tuple[str, str]], tmp: str) -> str:
    """Convierte con Word; devuelve "" si todo fue bien o el error."""
    lista = os.path.join(tmp, "lista.txt")
    with open(lista, "w", encoding="utf-8") as f:
        for origen, destino in pares:
            f.write(f"{origen}\n{destino}\n")
    # (r127) Sin PowerShell: word_com.py habla con Word por COM (comtypes),
    # en otro proceso para poder cortarlo si Word se queda colgado.
    import word_com
    try:
        r = subprocess.run(
            [sys.executable, os.path.abspath(word_com.__file__), lista],
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=_TIEMPO_MAX, creationflags=_SIN_VENTANA)
    except (OSError, subprocess.TimeoutExpired) as e:
        return str(e)
    return "" if r.returncode == 0 else (r.stderr or r.stdout or tr("código {codigo}").format(codigo=r.returncode)).strip()


def _con_libreoffice(soffice: str, origen: str, destino: str, tmp: str) -> str:
    salida = tempfile.mkdtemp(dir=tmp)
    try:
        r = subprocess.run(
            [soffice, "--headless", "--norestore", "--nolockcheck",
             "--convert-to", "pdf", "--outdir", salida, origen],
            capture_output=True, text=True, timeout=_TIEMPO_MAX, creationflags=_SIN_VENTANA)
    except (OSError, subprocess.TimeoutExpired) as e:
        return str(e)
    hecho = os.path.join(salida, os.path.splitext(os.path.basename(origen))[0] + ".pdf")
    if not os.path.isfile(hecho):
        return (r.stderr or r.stdout or tr("LibreOffice no generó el PDF")).strip()
    os.replace(hecho, destino)
    return ""


def word_a_pdfs(paths: list[str]) -> list[fitz.Document]:
    """Un documento fitz (en memoria) por cada documento de Word, en orden."""
    if not paths:
        return []
    with tempfile.TemporaryDirectory(prefix="aventyapdf_word_") as tmp:
        pares = [(os.path.abspath(p), os.path.join(tmp, f"{i:04d}.pdf"))
                 for i, p in enumerate(paths)]
        error_word = _con_word(pares, tmp)
        pendientes = [(o, d) for o, d in pares if not os.path.isfile(d)]
        if pendientes:
            soffice = _soffice()
            errores = []
            for origen, destino in pendientes:
                e = (_con_libreoffice(soffice, origen, destino, tmp) if soffice
                     else tr("no está instalado LibreOffice"))
                if e:
                    errores.append(f"«{os.path.basename(origen)}»: {e}")
            if errores:
                raise ConversionError(
                    tr("No se pudo convertir a PDF:\n") + "\n".join(errores)
                    + (tr("\n\nMicrosoft Word: ") + error_word.splitlines()[-1] if error_word else "")
                    + tr("\n\nHace falta Microsoft Word o LibreOffice instalado."))
        docs = []
        for _o, destino in pares:
            with open(destino, "rb") as f:
                docs.append(fitz.open("pdf", f.read()))
        return docs


def tipo_de(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return "pdf"
    if ext in IMAGE_EXTS:
        return "img"
    if ext in WORD_EXTS:
        return "word"
    return ""


def archivos_a_pdfs(paths: list[str]) -> list[fitz.Document]:
    """PDF, imágenes y documentos de Word mezclados → un documento fitz por
    archivo, en el mismo orden. Los de Word se convierten todos de una vez
    (abrir Word es lo lento). Los tipos no admitidos se ignoran."""
    paths = [p for p in paths if tipo_de(p)]
    word = [p for p in paths if tipo_de(p) == "word"]
    convertidos = dict(zip(word, word_a_pdfs(word)))
    docs = []
    for p in paths:
        t = tipo_de(p)
        if t == "pdf":
            src = fitz.open(p)
            if src.needs_pass:
                src.close()
                raise ValueError(tr("«{nombre}» está protegido con contraseña.").format(nombre=os.path.basename(p)))
            docs.append(src)
        elif t == "img":
            docs.append(doc_tools.images_to_pdf([p]))
        else:
            docs.append(convertidos[p])
    return docs


def combinar(docs: list[fitz.Document]) -> fitz.Document:
    out = fitz.open()
    for d in docs:
        out.insert_pdf(d)
    return out


def combinar_archivos(paths: list[str]) -> fitz.Document:
    """(r123) PDF, imágenes y Word mezclados → un único documento nuevo, en el
    orden dado. A diferencia de `archivos_a_pdfs` + `combinar`, cada archivo
    se lee, se copia al resultado y se suelta antes de pasar al siguiente, y
    los PDF se leen a memoria (no quedan abiertos en disco): en Windows no se
    pueden tener más de unos 500 archivos abiertos a la vez, y combinar más
    PDF que eso fallaba entero. Ahora el único límite es la memoria."""
    paths = [p for p in paths if tipo_de(p)]
    word = [p for p in paths if tipo_de(p) == "word"]
    convertidos = dict(zip(word, word_a_pdfs(word)))
    out = fitz.open()
    try:
        for p in paths:
            t = tipo_de(p)
            if t == "pdf":
                with open(p, "rb") as f:
                    src = fitz.open("pdf", f.read())
                if src.needs_pass:
                    src.close()
                    raise ValueError(tr("«{nombre}» está protegido con contraseña.").format(nombre=os.path.basename(p)))
            elif t == "img":
                src = doc_tools.images_to_pdf([p])
            else:
                src = convertidos.pop(p)
            try:
                out.insert_pdf(src)
            finally:
                src.close()
    except Exception:
        out.close()
        for d in convertidos.values():
            d.close()
        raise
    return out
