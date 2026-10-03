"""
Ejecutar un programa con permiso de administrador, sin PowerShell (r127).

Petición de Ricardo: «la aplicación está usando PowerShell y debería dejar de
usarlo» (Microsoft Defender marcaba AventyaPDF). Hasta r125 se pedía el
permiso con `powershell Start-Process -Verb RunAs`, oculto; ahora se llama
directamente a `ShellExecuteExW` con el verbo «runas», que es lo mismo que
hace el Explorador con «Ejecutar como administrador»: Windows muestra su
aviso de Control de cuentas de usuario y, si se acepta, arranca el programa.

Solo la biblioteca estándar (ctypes).
"""
import ctypes
import subprocess
import sys
from ctypes import wintypes

_SEE_MASK_NOCLOSEPROCESS = 0x00000040
_SEE_MASK_NOASYNC = 0x00000100
_SW_HIDE = 0
_WAIT_TIMEOUT = 0x00000102
_ERROR_CANCELLED = 1223


class _SHELLEXECUTEINFOW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("fMask", ctypes.c_ulong),
        ("hwnd", wintypes.HWND),
        ("lpVerb", wintypes.LPCWSTR),
        ("lpFile", wintypes.LPCWSTR),
        ("lpParameters", wintypes.LPCWSTR),
        ("lpDirectory", wintypes.LPCWSTR),
        ("nShow", ctypes.c_int),
        ("hInstApp", wintypes.HINSTANCE),
        ("lpIDList", ctypes.c_void_p),
        ("lpClass", wintypes.LPCWSTR),
        ("hkeyClass", wintypes.HKEY),
        ("dwHotKey", wintypes.DWORD),
        ("hIconOrMonitor", wintypes.HANDLE),
        ("hProcess", wintypes.HANDLE),
    ]


class Cancelado(OSError):
    """El usuario no dio el permiso de administrador."""


def ejecutar_como_administrador(exe: str, args: list[str], timeout: float | None = None) -> int:
    """Lanza `exe args` elevado y sin ventana, espera a que termine y devuelve
    su código de salida. Lanza `Cancelado` si no se da el permiso y
    `TimeoutError` si no termina en `timeout` segundos (sigue ejecutándose)."""
    if sys.platform != "win32":
        raise OSError("Solo en Windows.")
    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    shell32.ShellExecuteExW.argtypes = [ctypes.POINTER(_SHELLEXECUTEINFOW)]
    shell32.ShellExecuteExW.restype = wintypes.BOOL
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

    info = _SHELLEXECUTEINFOW()
    info.cbSize = ctypes.sizeof(info)
    info.fMask = _SEE_MASK_NOCLOSEPROCESS | _SEE_MASK_NOASYNC
    info.lpVerb = "runas"
    info.lpFile = exe
    info.lpParameters = subprocess.list2cmdline(args)
    info.nShow = _SW_HIDE
    if not shell32.ShellExecuteExW(ctypes.byref(info)):
        err = ctypes.get_last_error()
        if err == _ERROR_CANCELLED:
            raise Cancelado("No se dio el permiso de administrador.")
        raise ctypes.WinError(err)
    if not info.hProcess:
        raise OSError("Windows no devolvió el proceso lanzado.")
    try:
        espera = 0xFFFFFFFF if timeout is None else int(timeout * 1000)
        if kernel32.WaitForSingleObject(info.hProcess, espera) == _WAIT_TIMEOUT:
            raise TimeoutError(f"«{exe}» no terminó en {timeout} s.")
        codigo = wintypes.DWORD()
        kernel32.GetExitCodeProcess(info.hProcess, ctypes.byref(codigo))
        return codigo.value
    finally:
        kernel32.CloseHandle(info.hProcess)
