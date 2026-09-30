// AventyaPDF.exe — lanzador de la aplicación instalada (r109).
//
// El instalador ya no lleva un ejecutable de PyInstaller: descarga Python
// oficial (runtime\) y el código de la aplicación va en app\. Este programa
// solo arranca «runtime\pythonw.exe app\main.py» con los mismos argumentos
// (archivos, acciones del menú contextual, --autodiagnostico) y devuelve su
// código de salida. Se mantiene el nombre AventyaPDF.exe porque es lo que
// usan los accesos directos, «Abrir con», el menú contextual y el paquete
// MSIX (AppxManifest.xml).
#include <windows.h>
#include <string>

static std::wstring Carpeta()
{
    wchar_t ruta[MAX_PATH * 4];
    DWORD n = GetModuleFileNameW(nullptr, ruta, ARRAYSIZE(ruta));
    std::wstring s(ruta, n);
    return s.substr(0, s.find_last_of(L'\\'));
}

// Lo que sigue al nombre del programa en la línea de órdenes, tal cual (con
// sus comillas), para no volver a partir ni a entrecomillar los argumentos.
static const wchar_t* Argumentos()
{
    const wchar_t* p = GetCommandLineW();
    if (*p == L'"') {
        for (++p; *p && *p != L'"'; ++p) {}
        if (*p) ++p;
    } else {
        for (; *p && *p != L' ' && *p != L'\t'; ++p) {}
    }
    while (*p == L' ' || *p == L'\t') ++p;
    return p;
}

int WINAPI wWinMain(HINSTANCE, HINSTANCE, PWSTR, int)
{
    const std::wstring base = Carpeta();
    const std::wstring python = base + L"\\runtime\\pythonw.exe";
    const std::wstring script = base + L"\\app\\main.py";
    if (GetFileAttributesW(python.c_str()) == INVALID_FILE_ATTRIBUTES ||
        GetFileAttributesW(script.c_str()) == INVALID_FILE_ATTRIBUTES) {
        MessageBoxW(nullptr,
            L"La instalación de AventyaPDF está incompleta: faltan componentes.\n\n"
            L"Vuelve a ejecutar el instalador (necesita conexión a Internet).",
            L"AventyaPDF", MB_ICONERROR);
        return 1;
    }

    std::wstring orden = L"\"" + python + L"\" \"" + script + L"\"";
    const wchar_t* args = Argumentos();
    if (*args) orden += L" " + std::wstring(args);

    STARTUPINFOW si{};
    si.cb = sizeof(si);
    PROCESS_INFORMATION pi{};
    if (!CreateProcessW(python.c_str(), orden.data(), nullptr, nullptr, FALSE, 0,
                        nullptr, nullptr, &si, &pi)) {
        MessageBoxW(nullptr, L"No se pudo arrancar AventyaPDF.", L"AventyaPDF", MB_ICONERROR);
        return 1;
    }
    CloseHandle(pi.hThread);
    WaitForSingleObject(pi.hProcess, INFINITE);
    DWORD codigo = 1;
    GetExitCodeProcess(pi.hProcess, &codigo);
    CloseHandle(pi.hProcess);
    return static_cast<int>(codigo);
}
