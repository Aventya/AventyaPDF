// AventyaPDF-MenuContextual.exe — Registra el submenú «AventyaPDF» del menú
// principal de Windows 11 sin PowerShell (r127).
//
// Petición de Ricardo: «la aplicación está usando PowerShell y debería dejar
// de usarlo» (Microsoft Defender marcaba el instalador). Hasta r125 el
// instalador y «Ayuda › Reparar el menú contextual» lanzaban PowerShell oculto
// (Import-Certificate, Add-AppxPackage), justo lo que los antivirus asocian
// con programas maliciosos. Este programa hace lo mismo con las API de
// Windows: CryptoAPI para el certificado y PackageManager (WinRT) para el
// paquete disperso.
//
//   comprobar <cer>                    0 si el equipo ya confía en el certificado
//   confiar   <cer>                    lo añade a «Personas de confianza» del
//                                      equipo (hay que lanzarlo con «runas»)
//   registrar <msix> <carpeta> [<log>] registra el paquete disperso para el
//                                      usuario actual (sin elevar)
//   quitar                             quita el paquete del usuario actual
//
// Devuelve 0 si todo fue bien; 1 si no (el motivo, en <log> o en la salida de
// error); 2 si los argumentos no son válidos. Sin ventana (subsistema
// Windows). Compilación: shell\construir_shell.ps1.

#include <windows.h>
#include <wincrypt.h>
#include <winrt/Windows.Foundation.h>
#include <winrt/Windows.Foundation.Collections.h>
#include <winrt/Windows.ApplicationModel.h>
#include <winrt/Windows.Management.Deployment.h>
#include <fstream>
#include <iterator>
#include <string>
#include <vector>

#pragma comment(lib, "crypt32.lib")
#pragma comment(lib, "windowsapp.lib")

using namespace winrt;
using namespace winrt::Windows::Foundation;
using namespace winrt::Windows::Management::Deployment;

// Mismo nombre que la Identity de shell\AppxManifest.xml.
static const wchar_t* const kPaquete = L"Aventya.AventyaPDF.MenuContextual";

static std::wstring g_log;

static void Informar(const std::wstring& texto)
{
    const int n = WideCharToMultiByte(CP_UTF8, 0, texto.c_str(), -1, nullptr, 0, nullptr, nullptr);
    std::string utf8(n > 1 ? n - 1 : 0, '\0');
    if (n > 1)
        WideCharToMultiByte(CP_UTF8, 0, texto.c_str(), -1, utf8.data(), n, nullptr, nullptr);
    if (!g_log.empty())
        std::ofstream(g_log, std::ios::binary) << utf8 << "\r\n";
    DWORD escrito = 0;
    HANDLE err = GetStdHandle(STD_ERROR_HANDLE);
    if (err && err != INVALID_HANDLE_VALUE)
        WriteFile(err, utf8.data(), static_cast<DWORD>(utf8.size()), &escrito, nullptr);
}

// ── Certificado ─────────────────────────────────────────────────────────── //

static PCCERT_CONTEXT LeerCertificado(const wchar_t* ruta)
{
    std::ifstream f(ruta, std::ios::binary);
    std::vector<BYTE> datos((std::istreambuf_iterator<char>(f)), std::istreambuf_iterator<char>());
    if (datos.empty()) {
        Informar(std::wstring(L"No se pudo leer el certificado: ") + ruta);
        return nullptr;
    }
    PCCERT_CONTEXT c = CertCreateCertificateContext(X509_ASN_ENCODING | PKCS_7_ASN_ENCODING,
                                                    datos.data(), static_cast<DWORD>(datos.size()));
    if (!c)
        Informar(std::wstring(L"El archivo no es un certificado válido: ") + ruta);
    return c;
}

static HCERTSTORE AbrirPersonasDeConfianza(bool soloLectura)
{
    DWORD flags = CERT_SYSTEM_STORE_LOCAL_MACHINE;
    if (soloLectura)
        flags |= CERT_STORE_READONLY_FLAG | CERT_STORE_OPEN_EXISTING_FLAG;
    return CertOpenStore(CERT_STORE_PROV_SYSTEM_W, 0, 0, flags, L"TrustedPeople");
}

static int Comprobar(const wchar_t* cer)
{
    PCCERT_CONTEXT c = LeerCertificado(cer);
    if (!c)
        return 1;
    int codigo = 1;
    if (HCERTSTORE almacen = AbrirPersonasDeConfianza(true)) {
        if (PCCERT_CONTEXT hallado = CertFindCertificateInStore(
                almacen, X509_ASN_ENCODING | PKCS_7_ASN_ENCODING, 0, CERT_FIND_EXISTING, c, nullptr)) {
            CertFreeCertificateContext(hallado);
            codigo = 0;
        }
        CertCloseStore(almacen, 0);
    }
    CertFreeCertificateContext(c);
    return codigo;
}

static int Confiar(const wchar_t* cer)
{
    PCCERT_CONTEXT c = LeerCertificado(cer);
    if (!c)
        return 1;
    int codigo = 1;
    HCERTSTORE almacen = AbrirPersonasDeConfianza(false);
    if (!almacen) {
        Informar(L"No se pudo abrir «Personas de confianza» del equipo (¿sin permiso de administrador?).");
    } else {
        if (CertAddCertificateContextToStore(almacen, c, CERT_STORE_ADD_REPLACE_EXISTING, nullptr))
            codigo = 0;
        else
            Informar(L"Windows no dejó añadir el certificado (error " + std::to_wstring(GetLastError()) + L").");
        CertCloseStore(almacen, 0);
    }
    CertFreeCertificateContext(c);
    return codigo;
}

// ── Paquete disperso ────────────────────────────────────────────────────── //

static Uri UriDeArchivo(std::wstring ruta)
{
    for (auto& ch : ruta)
        if (ch == L'\\')
            ch = L'/';
    return Uri(L"file:///" + ruta);
}

static void QuitarPaquete(PackageManager const& pm)
{
    for (auto const& p : pm.FindPackagesForUser(L"")) {
        if (p.Id().Name() == kPaquete)
            pm.RemovePackageAsync(p.Id().FullName()).get();
    }
}

static int Registrar(const wchar_t* msix, const wchar_t* carpeta)
{
    PackageManager pm;
    try {
        QuitarPaquete(pm);
    } catch (...) {
        // Si no se puede quitar el anterior, ForceUpdateFromAnyVersion lo sustituye.
    }
    AddPackageOptions opciones;
    opciones.ExternalLocationUri(UriDeArchivo(carpeta));
    opciones.ForceUpdateFromAnyVersion(true);
    auto r = pm.AddPackageByUriAsync(UriDeArchivo(msix), opciones).get();
    if (r.ExtendedErrorCode() != hresult(0)) {
        wchar_t hex[16];
        swprintf_s(hex, L"%08X", static_cast<uint32_t>(r.ExtendedErrorCode().value));
        Informar(std::wstring(r.ErrorText()) + L" (0x" + hex + L")");
        return 1;
    }
    return 0;
}

int wmain(int argc, wchar_t** argv)
{
    if (argc < 2)
        return 2;
    const std::wstring orden = argv[1];
    try {
        init_apartment();
        if (orden == L"comprobar" && argc == 3)
            return Comprobar(argv[2]);
        if (orden == L"confiar" && argc == 3)
            return Confiar(argv[2]);
        if (orden == L"registrar" && (argc == 4 || argc == 5)) {
            if (argc == 5)
                g_log = argv[4];
            return Registrar(argv[2], argv[3]);
        }
        if (orden == L"quitar" && argc == 2) {
            QuitarPaquete(PackageManager());
            return 0;
        }
    } catch (hresult_error const& e) {
        Informar(std::wstring(e.message()));
        return 1;
    } catch (...) {
        Informar(L"Error inesperado.");
        return 1;
    }
    return 2;
}
