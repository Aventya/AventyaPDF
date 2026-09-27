"""
menu_contextual.py — Llegada de los archivos desde el menú contextual del
Explorador de Windows (r86).

Dos caminos llevan hasta aquí, los dos con la misma línea de órdenes
`AventyaPDF.exe <acción> <archivo> <archivo>…`:

* Menú principal de Windows 11 (extensión nativa `shell/AventyaPDFShell.dll`,
  registrada con el paquete MSIX que instala el instalador): la extensión
  recibe TODOS los archivos seleccionados de una vez y lanza la aplicación
  una sola vez. Si la línea de órdenes fuese demasiado larga para Windows
  (unos 32 000 caracteres), escribe las rutas en un archivo temporal y pasa
  `<acción> --lista <archivo>` (ver `expandir_lista`).

* Menú clásico («Mostrar más opciones», claves de SystemFileAssociations):
  con una orden de línea de comandos, el Explorador lanza UN PROCESO POR
  ARCHIVO seleccionado, cada uno con un solo archivo, aunque la entrada diga
  MultiSelectModel=Player. Para que «Combinar en un PDF» combine de verdad,
  `agrupar_invocaciones` reúne esos procesos: el primero (dueño de un mutex
  con nombre por acción) espera a que dejen de llegar los demás, que solo
  dejan sus rutas en una carpeta de intercambio y se cierran sin abrir
  ventana. El Explorador no garantiza el orden de lanzamiento, así que en
  ese camino el orden final es el natural por nombre de archivo.

Todo con la biblioteca estándar: se ejecuta al principio de main.py, antes de
importar Qt, para que los procesos que solo entregan sus rutas terminen cuanto
antes.
"""
import os
import re
import sys
import time

# Acciones del menú contextual (ver main.procesar_argumentos).
ARG_FIRMAR = "--firmar"
ARG_COMBINAR = "--combinar"
ARG_CONVERTIR = "--convertir"
# (r55) Nombres anteriores, aún aceptados.
ARG_COMBINAR_PDF = "--combinar-pdf"
ARG_IMAGENES_UN_PDF = "--imagenes-a-pdf"
ARG_IMAGENES_VARIOS_PDF = "--imagenes-a-pdfs-separados"
ACCIONES = (ARG_FIRMAR, ARG_COMBINAR, ARG_CONVERTIR,
            ARG_COMBINAR_PDF, ARG_IMAGENES_UN_PDF, ARG_IMAGENES_VARIOS_PDF)

ARG_LISTA = "--lista"

# Espera del proceso principal: se da por terminada la ráfaga de procesos
# cuando pasa QUIETUD sin que llegue ninguno nuevo, y nunca más de ESPERA_MAX.
QUIETUD = 1.0
ESPERA_MAX = 20.0

_CARPETA = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
                        "aventyapdf", "menu-contextual")


def expandir_lista(argv: list[str]) -> list[str]:
    """`<acción> --lista <archivo>` → `<acción> <ruta> <ruta>…`: lee las rutas
    (una por línea, UTF-8) y borra el archivo temporal que dejó la extensión."""
    if len(argv) >= 3 and argv[0] in ACCIONES and argv[1] == ARG_LISTA:
        lista = argv[2]
        try:
            with open(lista, encoding="utf-8-sig") as f:
                rutas = [l.strip() for l in f if l.strip()]
        except OSError:
            rutas = []
        try:
            os.remove(lista)
        except OSError:
            pass
        return [argv[0]] + rutas + argv[3:]
    return argv


def _orden_natural(ruta: str):
    nombre = os.path.basename(ruta).lower()
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", nombre)]


def agrupar_invocaciones(argv: list[str]) -> list[str]:
    """Devuelve la lista de argumentos con la que debe seguir este proceso.
    Si es uno de los procesos «secundarios» de una misma acción del menú
    clásico, deja sus rutas para el principal y termina aquí mismo
    (`sys.exit`). En cualquier otro caso devuelve `argv`, ya reunido."""
    argv = expandir_lista(list(argv))
    if sys.platform != "win32" or not argv or argv[0] not in ACCIONES:
        return argv
    try:
        return _agrupar_windows(argv)
    except SystemExit:
        raise
    except Exception:
        return argv          # ante cualquier imprevisto, como si no hubiera agrupación


def _agrupar_windows(argv: list[str]) -> list[str]:
    import ctypes
    from ctypes import wintypes

    accion, rutas = argv[0], argv[1:]
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateMutexW.restype = wintypes.HANDLE
    k32.CreateMutexW.argtypes = (ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR)
    k32.CloseHandle.argtypes = (wintypes.HANDLE,)
    ERROR_ALREADY_EXISTS = 183

    carpeta = os.path.join(_CARPETA, accion.lstrip("-"))
    os.makedirs(carpeta, exist_ok=True)
    mutex = k32.CreateMutexW(None, False, "Local\\AventyaPDF-menu" + accion)
    secundario = ctypes.get_last_error() == ERROR_ALREADY_EXISTS

    if secundario:
        k32.CloseHandle(mutex)
        nombre = f"{time.time_ns()}-{os.getpid()}"
        tmp = os.path.join(carpeta, nombre + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write("\n".join(rutas))
        os.replace(tmp, os.path.join(carpeta, nombre + ".txt"))
        sys.exit(0)

    # Principal. Fuera los restos de alguna ráfaga anterior que se cortara.
    for n in os.listdir(carpeta):
        try:
            p = os.path.join(carpeta, n)
            if time.time() - os.path.getmtime(p) > 60:
                os.remove(p)
        except OSError:
            pass

    recibidas: list[str] = []

    def recoger() -> bool:
        nuevo = False
        for n in sorted(os.listdir(carpeta)):
            if not n.endswith(".txt"):
                continue
            p = os.path.join(carpeta, n)
            try:
                with open(p, encoding="utf-8") as f:
                    recibidas.extend(l for l in f.read().splitlines() if l)
                os.remove(p)
                nuevo = True
            except OSError:
                pass
        return nuevo

    inicio = ultima = time.monotonic()
    while True:
        time.sleep(0.1)
        if recoger():
            ultima = time.monotonic()
        ahora = time.monotonic()
        if ahora - ultima >= QUIETUD or ahora - inicio >= ESPERA_MAX:
            break
    k32.CloseHandle(mutex)
    time.sleep(0.2)          # algún rezagado que ya había visto el mutex
    recoger()

    if not recibidas:
        return argv          # un solo archivo o una sola invocación con todos
    todas = list(dict.fromkeys(rutas + recibidas))
    todas.sort(key=_orden_natural)
    return [accion] + todas
