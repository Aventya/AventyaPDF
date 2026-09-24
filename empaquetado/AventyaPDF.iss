; Instalador de AventyaPDF (Inno Setup 6). No se compila a mano: lo usa
; empaquetado\construir.ps1, que pasa la versión con /DAppVersion=x.y.z.
;
; Decisiones (r62, de Ricardo):
;  * Solo para el usuario actual, sin permisos de administrador:
;    %LOCALAPPDATA%\Programs\AventyaPDF. Todo el registro va a HKCU.
;  * Tesseract OCR va dentro ({app}\tesseract): el OCR funciona nada más
;    instalar, sin internet.
;  * Integración con Windows: acceso directo en el menú Inicio (siempre) y en el
;    escritorio (casilla), y AventyaPDF en «Abrir con» de los PDF. Windows 11
;    no deja que un programa se imponga como predeterminado: queda registrado
;    y el usuario lo elige en «Abrir con» o en Aplicaciones predeterminadas.
;  * Sin menú contextual del Explorador (r55 sigue disponible con
;    Install-ContextMenu.ps1 para quien lo quiera desde el código fuente).
;
; El AppId NO debe cambiar nunca: es lo que reconoce una instalación anterior
; para actualizarla en su sitio y lo que usa el desinstalador.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
; Carpeta de la aplicación ya compilada (construir.ps1 la deja fuera del
; proyecto, que es una carpeta compartida: son unos 400 MB).
#ifndef DistDir
  #define DistDir "dist\AventyaPDF"
#endif
#define AppName "AventyaPDF"
#define AppExe "AventyaPDF.exe"
#define ProgId "AventyaPDF.Document"

[Setup]
AppId={{7AE55FB3-3E78-4243-9BEE-CA4E080DFFC2}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Aventya Asesoría Integral SL
AppPublisherURL=https://github.com/Aventya/AventyaPDF
AppSupportURL=https://github.com/Aventya/AventyaPDF/issues
VersionInfoVersion={#AppVersion}
VersionInfoCompany=Aventya Asesoría Integral SL
VersionInfoDescription=Instalador de {#AppName}
PrivilegesRequired=lowest
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=salida
OutputBaseFilename=AventyaPDF-Setup-{#AppVersion}
; (r64) Icono y las dos imágenes del asistente: todo sale de ICONO.png con
; create_app_icon.py. Una imagen por escala de pantalla; Inno elige la mejor.
SetupIconFile=..\vendor\icono\aventyapdf.ico
WizardSmallImageFile=imagenes\asistente_pequena_100.bmp,imagenes\asistente_pequena_150.bmp,imagenes\asistente_pequena_200.bmp,imagenes\asistente_pequena_250.bmp
WizardImageFile=imagenes\asistente_grande_100.bmp,imagenes\asistente_grande_150.bmp,imagenes\asistente_grande_200.bmp,imagenes\asistente_grande_250.bmp
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ChangesAssociations=yes
; Si la aplicación está abierta al actualizar o desinstalar, se ofrece cerrarla.
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "escritorio"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"

[Files]
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
; Al actualizar, fuera los restos de la versión anterior (bibliotecas que ya no se usan).
Type: filesandordirs; Name: "{app}\_internal"

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; AppUserModelID: "Aventya.AventyaPDF"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; AppUserModelID: "Aventya.AventyaPDF"; Tasks: escritorio

[Registry]
; Tipo de documento propio y «Abrir con» de los .pdf
Root: HKA; Subkey: "Software\Classes\{#ProgId}"; ValueType: string; ValueName: ""; ValueData: "Documento PDF"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\{#ProgId}"; ValueType: string; ValueName: "AppUserModelID"; ValueData: "Aventya.AventyaPDF"
Root: HKA; Subkey: "Software\Classes\{#ProgId}\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExe},0"
Root: HKA; Subkey: "Software\Classes\{#ProgId}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""
Root: HKA; Subkey: "Software\Classes\.pdf\OpenWithProgids"; ValueType: string; ValueName: "{#ProgId}"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}"; ValueType: string; ValueName: "FriendlyAppName"; ValueData: "{#AppName}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}\SupportedTypes"; ValueType: string; ValueName: ".pdf"; ValueData: ""
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""
; Para que aparezca en Configuración › Aplicaciones predeterminadas
; (las dos primeras solo para que el desinstalador no deje claves vacías)
Root: HKA; Subkey: "Software\Aventya"; Flags: uninsdeletekeyifempty
Root: HKA; Subkey: "Software\Aventya\{#AppName}"; Flags: uninsdeletekeyifempty
Root: HKA; Subkey: "Software\Aventya\{#AppName}\Capabilities"; ValueType: string; ValueName: "ApplicationName"; ValueData: "{#AppName}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Aventya\{#AppName}\Capabilities"; ValueType: string; ValueName: "ApplicationDescription"; ValueData: "Visor y editor de PDF con firma digital y OCR"
Root: HKA; Subkey: "Software\Aventya\{#AppName}\Capabilities\FileAssociations"; ValueType: string; ValueName: ".pdf"; ValueData: "{#ProgId}"
Root: HKA; Subkey: "Software\RegisteredApplications"; ValueType: string; ValueName: "{#AppName}"; ValueData: "Software\Aventya\{#AppName}\Capabilities"; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#AppExe}"; Description: "Abrir {#AppName}"; Flags: nowait postinstall skipifsilent
