// AventyaPDFShell.dll — Submenú «AventyaPDF» del menú contextual PRINCIPAL del
// Explorador de Windows 11 (r86).
//
// Windows 11 solo muestra en su menú nuevo las extensiones IExplorerCommand
// de aplicaciones con identidad de paquete. Esta DLL se registra con un
// paquete MSIX «disperso» (shell\AppxManifest.xml, instalado por el
// instalador con Add-AppxPackage -ExternalLocation <carpeta de la app>), y
// se carga en un proceso sustituto (dllhost.exe), no dentro del Explorador.
//
// Opciones, según lo que haya seleccionado:
//   · Firmar digitalmente   — solo PDF.
//   · Combinar en un PDF    — dos o más archivos PDF, imágenes o Word.
//   · Convertir a PDF       — imágenes o Word, sin PDF: uno por archivo.
// Cada opción lanza AventyaPDF.exe (junto a esta DLL) UNA sola vez con todos
// los archivos, en el orden del Explorador, precedidos de la acción que
// entiende menu_contextual.py (--firmar, --combinar, --convertir).
//
// Compilación: shell\construir_shell.ps1 (lo llama empaquetado\construir.ps1).

#include <windows.h>
#include <shobjidl_core.h>
#include <shlwapi.h>
#include <wrl/module.h>
#include <wrl/implements.h>
#include <wrl/client.h>
#include <string>
#include <vector>

#pragma comment(lib, "shlwapi.lib")
#pragma comment(lib, "user32.lib")
#pragma comment(lib, "runtimeobject.lib")

using namespace Microsoft::WRL;

static HMODULE g_modulo = nullptr;

// ── Selección ────────────────────────────────────────────────────────────── //

// Mismas extensiones que conversion_office.py (IMAGE_EXTS, WORD_EXTS) y que
// shell\AppxManifest.xml: si se amplían, en los tres sitios.
static const wchar_t* const EXT_IMAGEN[] = {
    L".png", L".jpg", L".jpeg", L".bmp", L".gif", L".tif", L".tiff", L".webp"};
static const wchar_t* const EXT_WORD[] = {L".doc", L".docx"};

enum class Tipo { Otro, Pdf, Imagen, Word };

static bool EnLista(const wchar_t* ext, const wchar_t* const* lista, size_t n) {
    for (size_t i = 0; i < n; ++i)
        if (_wcsicmp(ext, lista[i]) == 0) return true;
    return false;
}

static Tipo TipoDe(const std::wstring& ruta) {
    const wchar_t* ext = PathFindExtensionW(ruta.c_str());
    if (_wcsicmp(ext, L".pdf") == 0) return Tipo::Pdf;
    if (EnLista(ext, EXT_IMAGEN, ARRAYSIZE(EXT_IMAGEN))) return Tipo::Imagen;
    if (EnLista(ext, EXT_WORD, ARRAYSIZE(EXT_WORD))) return Tipo::Word;
    return Tipo::Otro;
}

struct Seleccion {
    std::vector<std::wstring> rutas;
    int pdf = 0, imagen = 0, word = 0, otro = 0;
    int Total() const { return pdf + imagen + word + otro; }
};

static Seleccion LeerSeleccion(IShellItemArray* items) {
    Seleccion s;
    DWORD n = 0;
    if (!items || FAILED(items->GetCount(&n))) return s;
    for (DWORD i = 0; i < n; ++i) {
        ComPtr<IShellItem> item;
        PWSTR ruta = nullptr;
        if (FAILED(items->GetItemAt(i, &item)) ||
            FAILED(item->GetDisplayName(SIGDN_FILESYSPATH, &ruta))) {
            ++s.otro;                  // elemento virtual, sin ruta en disco
            continue;
        }
        std::wstring r(ruta);
        CoTaskMemFree(ruta);
        DWORD attr = GetFileAttributesW(r.c_str());
        switch (attr != INVALID_FILE_ATTRIBUTES && !(attr & FILE_ATTRIBUTE_DIRECTORY)
                    ? TipoDe(r) : Tipo::Otro) {
            case Tipo::Pdf:    ++s.pdf; break;
            case Tipo::Imagen: ++s.imagen; break;
            case Tipo::Word:   ++s.word; break;
            default:           ++s.otro; break;
        }
        s.rutas.push_back(std::move(r));
    }
    return s;
}

// ── Acciones ─────────────────────────────────────────────────────────────── //

enum class Accion { Firmar, Combinar, Convertir };

struct DatosAccion { const wchar_t* titulo; const wchar_t* argumento; };

static DatosAccion Datos(Accion a) {
    switch (a) {
        case Accion::Firmar:   return {L"Firmar digitalmente", L"--firmar"};
        case Accion::Combinar: return {L"Combinar en un PDF", L"--combinar"};
        default:               return {L"Convertir a PDF", L"--convertir"};
    }
}

static bool Aplicable(Accion a, const Seleccion& s) {
    if (s.otro > 0 || s.Total() == 0) return false;
    switch (a) {
        case Accion::Firmar:   return s.pdf > 0 && s.imagen + s.word == 0;
        case Accion::Combinar: return s.Total() >= 2;
        default:               return s.pdf == 0;
    }
}

static std::wstring CarpetaDeLaDll() {
    wchar_t ruta[MAX_PATH * 4];
    DWORD n = GetModuleFileNameW(g_modulo, ruta, ARRAYSIZE(ruta));
    if (n == 0 || n >= ARRAYSIZE(ruta)) return L"";
    PathRemoveFileSpecW(ruta);
    return ruta;
}

static std::wstring Entrecomillar(const std::wstring& s) { return L"\"" + s + L"\""; }

static HRESULT Lanzar(Accion a, const Seleccion& s) {
    const std::wstring carpeta = CarpetaDeLaDll();
    const std::wstring exe = carpeta + L"\\AventyaPDF.exe";
    std::wstring linea = Entrecomillar(exe) + L" " + Datos(a).argumento;
    for (const auto& r : s.rutas) linea += L" " + Entrecomillar(r);

    // CreateProcess admite 32 767 caracteres: con selecciones enormes, las
    // rutas van en un archivo temporal (menu_contextual.expandir_lista).
    if (linea.size() > 30000) {
        wchar_t tmp[MAX_PATH + 1], archivo[MAX_PATH + 1];
        if (!GetTempPathW(ARRAYSIZE(tmp), tmp) ||
            !GetTempFileNameW(tmp, L"apd", 0, archivo)) return E_FAIL;
        std::string utf8;
        for (const auto& r : s.rutas) {
            int n = WideCharToMultiByte(CP_UTF8, 0, r.c_str(), (int)r.size(), nullptr, 0, nullptr, nullptr);
            std::string parte(n, '\0');
            WideCharToMultiByte(CP_UTF8, 0, r.c_str(), (int)r.size(), parte.data(), n, nullptr, nullptr);
            utf8 += parte + "\n";
        }
        HANDLE h = CreateFileW(archivo, GENERIC_WRITE, 0, nullptr, CREATE_ALWAYS,
                               FILE_ATTRIBUTE_NORMAL, nullptr);
        if (h == INVALID_HANDLE_VALUE) return HRESULT_FROM_WIN32(GetLastError());
        DWORD escritos = 0;
        WriteFile(h, utf8.data(), (DWORD)utf8.size(), &escritos, nullptr);
        CloseHandle(h);
        linea = Entrecomillar(exe) + L" " + Datos(a).argumento + L" --lista " + Entrecomillar(archivo);
    }

    STARTUPINFOW si = {sizeof(si)};
    PROCESS_INFORMATION pi = {};
    std::vector<wchar_t> buf(linea.begin(), linea.end());
    buf.push_back(L'\0');
    if (!CreateProcessW(exe.c_str(), buf.data(), nullptr, nullptr, FALSE, 0, nullptr,
                        carpeta.c_str(), &si, &pi))
        return HRESULT_FROM_WIN32(GetLastError());
    AllowSetForegroundWindow(pi.dwProcessId);   // que la ventana salga delante
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    return S_OK;
}

// ── Opciones del submenú ─────────────────────────────────────────────────── //

class Opcion : public RuntimeClass<RuntimeClassFlags<ClassicCom>, IExplorerCommand> {
public:
    explicit Opcion(Accion a) : accion_(a) {}

    IFACEMETHODIMP GetTitle(IShellItemArray*, PWSTR* nombre) override {
        return SHStrDupW(Datos(accion_).titulo, nombre);
    }
    IFACEMETHODIMP GetIcon(IShellItemArray*, PWSTR* icono) override { *icono = nullptr; return E_NOTIMPL; }
    IFACEMETHODIMP GetToolTip(IShellItemArray*, PWSTR* tip) override { *tip = nullptr; return E_NOTIMPL; }
    IFACEMETHODIMP GetCanonicalName(GUID* guid) override { *guid = GUID_NULL; return E_NOTIMPL; }
    IFACEMETHODIMP GetState(IShellItemArray* items, BOOL, EXPCMDSTATE* estado) override {
        *estado = Aplicable(accion_, LeerSeleccion(items)) ? ECS_ENABLED : ECS_HIDDEN;
        return S_OK;
    }
    IFACEMETHODIMP Invoke(IShellItemArray* items, IBindCtx*) override {
        Seleccion s = LeerSeleccion(items);
        return Aplicable(accion_, s) ? Lanzar(accion_, s) : S_OK;
    }
    IFACEMETHODIMP GetFlags(EXPCMDFLAGS* flags) override { *flags = ECF_DEFAULT; return S_OK; }
    IFACEMETHODIMP EnumSubCommands(IEnumExplorerCommand** e) override { *e = nullptr; return E_NOTIMPL; }

private:
    Accion accion_;
};

class Opciones : public RuntimeClass<RuntimeClassFlags<ClassicCom>, IEnumExplorerCommand> {
public:
    Opciones() {
        for (Accion a : {Accion::Firmar, Accion::Combinar, Accion::Convertir})
            opciones_.push_back(Make<Opcion>(a));
    }
    IFACEMETHODIMP Next(ULONG pedidos, IExplorerCommand** salida, ULONG* dados) override {
        ULONG n = 0;
        for (; n < pedidos && pos_ < opciones_.size(); ++n, ++pos_)
            opciones_[pos_].CopyTo(&salida[n]);
        if (dados) *dados = n;
        return n == pedidos ? S_OK : S_FALSE;
    }
    IFACEMETHODIMP Skip(ULONG n) override { pos_ = min(pos_ + n, (ULONG)opciones_.size()); return S_OK; }
    IFACEMETHODIMP Reset() override { pos_ = 0; return S_OK; }
    IFACEMETHODIMP Clone(IEnumExplorerCommand** e) override { *e = nullptr; return E_NOTIMPL; }

private:
    std::vector<ComPtr<IExplorerCommand>> opciones_;
    ULONG pos_ = 0;
};

// ── Entrada raíz «AventyaPDF» (la que registra el paquete) ───────────────── //

class __declspec(uuid("CFCBA067-9C58-4229-95F8-2F5912C3611F")) MenuAventyaPDF
    : public RuntimeClass<RuntimeClassFlags<ClassicCom>, IExplorerCommand> {
public:
    IFACEMETHODIMP GetTitle(IShellItemArray*, PWSTR* nombre) override {
        return SHStrDupW(L"AventyaPDF", nombre);
    }
    IFACEMETHODIMP GetIcon(IShellItemArray*, PWSTR* icono) override {
        std::wstring ruta = CarpetaDeLaDll() + L"\\AventyaPDF.exe,0";
        return SHStrDupW(ruta.c_str(), icono);
    }
    IFACEMETHODIMP GetToolTip(IShellItemArray*, PWSTR* tip) override { *tip = nullptr; return E_NOTIMPL; }
    IFACEMETHODIMP GetCanonicalName(GUID* guid) override { *guid = __uuidof(MenuAventyaPDF); return S_OK; }
    IFACEMETHODIMP GetState(IShellItemArray* items, BOOL, EXPCMDSTATE* estado) override {
        Seleccion s = LeerSeleccion(items);
        bool alguna = false;
        for (Accion a : {Accion::Firmar, Accion::Combinar, Accion::Convertir})
            alguna = alguna || Aplicable(a, s);
        *estado = alguna ? ECS_ENABLED : ECS_HIDDEN;
        return S_OK;
    }
    IFACEMETHODIMP Invoke(IShellItemArray*, IBindCtx*) override { return E_NOTIMPL; }
    IFACEMETHODIMP GetFlags(EXPCMDFLAGS* flags) override { *flags = ECF_HASSUBCOMMANDS; return S_OK; }
    IFACEMETHODIMP EnumSubCommands(IEnumExplorerCommand** e) override {
        return Make<Opciones>().CopyTo(e);
    }
};

CoCreatableClass(MenuAventyaPDF)

// ── Exportaciones COM ────────────────────────────────────────────────────── //

STDAPI DllGetActivationFactory(HSTRING id, IActivationFactory** f) {
    return Module<ModuleType::InProc>::GetModule().GetActivationFactory(id, f);
}

STDAPI DllCanUnloadNow() {
    return Module<InProc>::GetModule().GetObjectCount() == 0 ? S_OK : S_FALSE;
}

STDAPI DllGetClassObject(REFCLSID clsid, REFIID riid, void** obj) {
    return Module<InProc>::GetModule().GetClassObject(clsid, riid, obj);
}

BOOL APIENTRY DllMain(HMODULE modulo, DWORD motivo, LPVOID) {
    if (motivo == DLL_PROCESS_ATTACH) {
        g_modulo = modulo;
        DisableThreadLibraryCalls(modulo);
    }
    return TRUE;
}
