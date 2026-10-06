"""
menu_contextual.py — Llegada de los archivos desde el menú contextual del
Explorador de Windows (r86) y, desde r87, de cualquier apertura normal
(«Abrir con…», doble clic, arrastrar varios PDF, otra aplicación).

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

(r87, aviso de Ricardo: «al abrir varios PDF se abre una ventana por cada
uno; deben abrirse en pestañas de la misma ventana») La apertura NORMAL de
uno o varios PDF (sin acción del menú contextual) tiene el mismo problema de
fondo por partida doble: la asociación de archivo del instalador usa "%1"
(un proceso por archivo al seleccionar varios y pulsar Intro), y aunque solo
se abra uno, cada doble clic lanza un AventyaPDF.exe distinto, con ventana
propia, aunque ya hubiera uno abierto. `es_instancia_secundaria` (mutex
único, sin acción) es la solución general: el primer proceso en arrancar se
queda con el mutex y sigue como siempre; cualquier otro deja sus rutas en
`entrantes\\` y termina sin abrir ventana. La instancia que sigue corriendo
las recoge con `recoger_entrantes()` (temporizador en `MainWindow`, mientras
la ventana esté abierta) y abre cada una en su pestaña, con la ventana al
frente — sirve tanto para varios PDF a la vez como para uno que llega más
tarde desde otra aplicación. Es un mecanismo aparte de `agrupar_invocaciones`
porque ese necesita ESPERAR a que lleguen todos los archivos de una ráfaga
para combinarlos de una vez; abrir pestañas no necesita esperar a nadie.

Todo con la biblioteca estándar: se ejecuta al principio de main.py, antes de
importar Qt, para que los procesos que solo entregan sus rutas terminen cuanto
antes.
"""
import os
import re
import sys
import time
from idioma import tr

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


# ── (r87) Instancia única para la apertura normal ───────────────────────── #

_CARPETA_ENTRANTES = os.path.join(_CARPETA, "entrantes")
_MUTEX_INSTANCIA = "Local\\AventyaPDF-instancia"
# Referencia viva: si se pierde (y Python la recolecta), Windows liberaría el
# mutex y esta dejaría de ser «la» instancia sin que nadie lo pidiera.
_mutex_vivo = None


def es_instancia_secundaria(argv: list[str]) -> bool:
    """True si ya hay una instancia de AventyaPDF corriendo: deja `argv`
    (aunque esté vacío — sirve para que la instancia principal se traiga al
    frente aun sin archivos, p. ej. al pulsar otra vez el acceso directo) y
    devuelve True — quien llama debe salir sin más (no crear ventana). False
    si esta es la primera instancia (debe seguir arrancando con
    normalidad); en ese caso el mutex queda vivo mientras dure el proceso,
    para que el siguiente lanzamiento lo detecte."""
    global _mutex_vivo
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.WinDLL("kernel32", use_last_error=True)
        k32.CreateMutexW.restype = wintypes.HANDLE
        k32.CreateMutexW.argtypes = (ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR)
        ERROR_ALREADY_EXISTS = 183
        mutex = k32.CreateMutexW(None, False, _MUTEX_INSTANCIA)
        if not mutex:
            return False                       # no se pudo crear: sigue como si fuera la única
        if ctypes.get_last_error() != ERROR_ALREADY_EXISTS:
            _mutex_vivo = mutex                # primera instancia: mutex vivo todo el proceso
            return False
        k32.CloseHandle(mutex)
    except Exception:
        return False                           # ante cualquier imprevisto, arranca como siempre
    try:
        os.makedirs(_CARPETA_ENTRANTES, exist_ok=True)
        nombre = f"{time.time_ns()}-{os.getpid()}"
        tmp = os.path.join(_CARPETA_ENTRANTES, nombre + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write("\n".join(argv))
        os.replace(tmp, os.path.join(_CARPETA_ENTRANTES, nombre + ".txt"))
    except OSError:
        return False        # no se pudo avisar a la instancia principal: abre esta ventana
    return True


def recoger_entrantes() -> list[list[str]]:
    """[argv, argv…] dejados por otros procesos mientras esta instancia (la
    única) seguía abierta — uno por cada apertura que se le cedió, `[]`
    incluida (solo pide traer la ventana al frente). Se llama periódicamente
    desde la ventana principal (ver `main._start_instance_watch`)."""
    if not os.path.isdir(_CARPETA_ENTRANTES):
        return []
    resultado = []
    for nombre in sorted(os.listdir(_CARPETA_ENTRANTES)):
        if not nombre.endswith(".txt"):
            continue
        ruta = os.path.join(_CARPETA_ENTRANTES, nombre)
        try:
            with open(ruta, encoding="utf-8") as f:
                argv = [l for l in f.read().splitlines() if l]
            os.remove(ruta)
        except OSError:
            continue
        resultado.append(argv)
    return resultado


# ── (r121) Reparar el menú principal de Windows 11 ─────────────────────── #
# Petición de Ricardo: «quiero que se instale con permisos de administrador
# para que el menú del ratón en el explorador de Windows se ejecute
# correctamente en lugar de tener que entrar en "mostrar más opciones"». El
# submenú del menú PRINCIPAL de Windows 11 es un paquete MSIX disperso
# (menu-contextual\); Windows solo lo acepta si el equipo confía en su
# certificado, y añadirlo a «Personas de confianza» del equipo pide
# administrador. El registro del paquete, en cambio, es POR USUARIO: se hace
# sin elevar, como el propio usuario (si lo hiciera un administrador, quedaría
# registrado para él y no para quien usa el equipo).
# (r127, petición de Ricardo: «la aplicación está usando PowerShell y debería
# dejar de usarlo») Todo lo hace menu-contextual\AventyaPDF-MenuContextual.exe
# (shell\MenuContextual.cpp, el mismo que usa el instalador) con las API de
# Windows; el permiso de administrador se pide con elevar.py (ShellExecuteExW).

_CREATE_NO_WINDOW = 0x08000000


def _archivos_menu() -> tuple[str, str, str, str] | None:
    import dependencias
    base = dependencias.carpeta_instalada()
    if not base or dependencias.en_paquete_msix():
        return None
    carpeta = os.path.join(base, "menu-contextual")
    cer = os.path.join(carpeta, "AventyaPDF-MenuContextual.cer")
    msix = os.path.join(carpeta, "AventyaPDF-MenuContextual.msix")
    exe = os.path.join(carpeta, "AventyaPDF-MenuContextual.exe")
    return (base, cer, msix, exe) if all(map(os.path.isfile, (cer, msix, exe))) else None


def puede_reparar() -> bool:
    """Instalación de GitHub en Windows 11 (el menú principal no existe en
    Windows 10, y en la versión de la Store va dentro de su paquete)."""
    return sys.platform == "win32" and sys.getwindowsversion().build >= 22000 \
        and _archivos_menu() is not None


def _ayudante(exe: str, *args: str) -> tuple[int, str]:
    """Ejecuta el ayudante sin elevar: (código de salida, motivo si falla)."""
    import subprocess
    r = subprocess.run([exe, *args], capture_output=True, creationflags=_CREATE_NO_WINDOW)
    return r.returncode, r.stderr.decode("utf-8", "replace").strip()


def reparar() -> tuple[bool, str]:
    """Confía en el certificado del paquete (pidiendo administrador si hace
    falta) y registra el submenú para el usuario actual. (ok, mensaje)."""
    import elevar
    archivos = _archivos_menu()
    if archivos is None:
        return False, tr("Esta instalación no tiene el menú contextual de Windows 11.")
    base, cer, msix, exe = archivos
    if _ayudante(exe, "comprobar", cer)[0] != 0:
        try:
            elevar.ejecutar_como_administrador(exe, ["confiar", cer], timeout=120)
        except (OSError, TimeoutError):
            pass                                # se comprueba abajo
        if _ayudante(exe, "comprobar", cer)[0] != 0:
            return False, tr(("No se ha dado el permiso de administrador: el submenú «AventyaPDF» "
                           "sigue en «Mostrar más opciones». Vuelve a intentarlo y acepta el "
                           "aviso de Windows."))
    codigo, motivo = _ayudante(exe, "registrar", msix, base)
    if codigo != 0:
        return False, (tr("Windows no aceptó el paquete del menú contextual.")
                       + (f"\n\n{motivo}" if motivo else ""))
    return True, tr(("Listo: el submenú «AventyaPDF» está en el menú principal del botón derecho "
                  "del Explorador (si no aparece aún, cierra y vuelve a abrir la ventana del "
                  "Explorador)."))
