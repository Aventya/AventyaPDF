"""
word_com.py — Convierte documentos de Word a PDF con Microsoft Word (r127).

Lo lanza conversion_office._con_word en un proceso aparte (así un Word
colgado no bloquea la aplicación y se le puede poner un tiempo máximo):

    python word_com.py <lista>

<lista>: archivo UTF-8 con una línea de origen y otra de destino por
documento. Devuelve 0 si todo fue bien; si no, el error en la salida de error.

(r127, petición de Ricardo: «la aplicación está usando PowerShell y debería
dejar de usarlo») Hasta r125 esto era un script de PowerShell
(New-Object -ComObject Word.Application); ahora habla con Word por COM desde
Python con comtypes, con la misma secuencia de llamadas.
"""
import sys

_FORMATO_PDF = 17                   # wdExportFormatPDF
_NO_GUARDAR = 0                     # wdDoNotSaveChanges
# Contraseña ficticia: un documento protegido FALLA en vez de quedarse
# esperando a que alguien la escriba en un diálogo invisible.
_CONTRASENA = "§AventyaPDF§"


def _motivo(e: Exception) -> str:
    """Texto legible de un error COM: (hresult, texto, (descripción, …))."""
    args = getattr(e, "args", ())
    if len(args) == 3 and isinstance(args[0], int):
        detalle = args[2] if isinstance(args[2], tuple) else ()
        texto = (detalle[0] if detalle and detalle[0] else None) or args[1]
        return f"{texto or 'error'} (0x{args[0] & 0xFFFFFFFF:08X})"
    return str(e)


def convertir(pares: list[tuple[str, str]]) -> None:
    import comtypes
    import comtypes.client
    comtypes.CoInitialize()
    try:
        w = comtypes.client.CreateObject("Word.Application", dynamic=True)
        try:
            w.Visible = False
            w.DisplayAlerts = 0
            for origen, destino in pares:
                # Open(FileName, ConfirmConversions, ReadOnly, AddToRecentFiles, PasswordDocument)
                try:
                    d = w.Documents.Open(origen, False, True, False, _CONTRASENA)
                    try:
                        d.ExportAsFixedFormat(destino, _FORMATO_PDF)
                    finally:
                        d.Close(_NO_GUARDAR)
                except Exception as e:  # noqa: BLE001
                    raise RuntimeError(f"Word no pudo convertir «{origen}»: {_motivo(e)}") from e
        finally:
            w.Quit()
            del w
    finally:
        comtypes.CoUninitialize()


def main(argv: list[str]) -> int:
    with open(argv[1], encoding="utf-8") as f:
        lineas = f.read().splitlines()
    pares = list(zip(lineas[0::2], lineas[1::2]))
    try:
        convertir(pares)
    except Exception as e:  # noqa: BLE001 — el motivo, a quien lo lanzó
        if sys.stderr:
            sys.stderr.write(f"{e}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
