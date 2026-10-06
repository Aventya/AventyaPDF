; Instalador de AventyaPDF (Inno Setup 6). No se compila a mano: lo usa
; empaquetado\construir.ps1, que pasa la versión con /DAppVersion=x.y.z.
;
; Decisiones (r62, de Ricardo):
;  * Solo para el usuario actual, sin permisos de administrador:
;    %LOCALAPPDATA%\Programs\AventyaPDF. Todo el registro va a HKCU.
;  * (r109, petición de Ricardo: «el instalador no lleve partes que se
;    mantengan fuera de este proyecto») El instalador solo lleva lo propio:
;    el lanzador AventyaPDF.exe, el código (app\), la lista de confianza, los
;    iconos, el menú contextual y el manual. Python oficial, los paquetes de
;    Python (la versión exacta probada) y las fuentes Noto/Fluent se
;    descargan al instalar, de su origen, comprobando su SHA-256: las
;    entradas las genera componentes.py en componentes.iss. Sin Internet no
;    se puede instalar. Hasta r108 iba todo dentro (PyInstaller).
;  * (r102) Tesseract OCR NO va dentro: se descarga (con permiso de
;    administrador la primera vez, si hiciera falta) la primera vez que se
;    usa «Reconocer texto», no al instalar — antes iba en {app}\tesseract
;    (153 MB); [InstallDelete] lo quita si una versión anterior lo dejó.
;  * (r109) /DPrueba compila una variante para construir.ps1
;    -ProbarInstalacion: otro AppId y solo archivos (sin accesos directos,
;    registro, menú contextual ni «Abrir AventyaPDF» al acabar).
;  * (r138) Manual en PDF del idioma elegido (docs\manual\MANUAL_<código>.pdf,
;    en {app}\manual) y, mientras instala, diapositivas con las herramientas
;    de la aplicación: imagen (empaquetado\diapositivas, de
;    docs\manual\crear_manual.py) y texto de la presentación de inicio
;    (mensajes.iss). Ver [Code] «Diapositivas».
;  * Integración con Windows: acceso directo en el menú Inicio (siempre) y en el
;    escritorio (casilla), y AventyaPDF en «Abrir con» de los PDF. Windows 11
;    no deja que un programa se imponga como predeterminado: queda registrado
;    y el usuario lo elige en «Abrir con» o en Aplicaciones predeterminadas.
;  * (r86) Menú contextual del Explorador, submenú «AventyaPDF» con Firmar
;    digitalmente / Combinar en un PDF / Convertir a PDF (ver [Code]):
;      - Menú PRINCIPAL de Windows 11: paquete MSIX disperso firmado con la
;        DLL de shell\, registrado con -ExternalLocation {app} por
;        menu-contextual\AventyaPDF-MenuContextual.exe (r127: sin PowerShell,
;        que hacía que los antivirus lo marcaran). Windows solo
;        lo acepta si el equipo confía en el certificado del paquete: la
;        primera vez se añade a «Personas de confianza» del equipo, lo único
;        que pide permiso de administrador (una sola vez por equipo y
;        certificado). Si se deniega, queda el menú clásico.
;      - Menú clásico («Mostrar más opciones», y el único en Windows 10):
;        claves en HKCU\Software\Classes\SystemFileAssociations.
;
; El AppId NO debe cambiar nunca: es lo que reconoce una instalación anterior
; para actualizarla en su sitio y lo que usa el desinstalador.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif
; Lo propio que lleva el instalador (construir.ps1 lo deja fuera del proyecto).
#ifndef DistDir
  #define DistDir "dist\AventyaPDF"
#endif
#define AppName "AventyaPDF"
#define AppExe "AventyaPDF.exe"
#define ProgId "AventyaPDF.Document"

; Descargas de terceros ([Files] y el tamaño que ocupan): componentes.py.
#include "componentes.iss"

[Setup]
#ifdef Prueba
AppId={{5C0B3F49-6D0E-4C47-9A51-0B7D1D2B3E61}
AppName={#AppName} (prueba)
#else
AppId={{7AE55FB3-3E78-4243-9BEE-CA4E080DFFC2}
AppName={#AppName}
#endif
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
; (r109) Si la aplicación está abierta, que se cierre antes de sustituir su
; Python (el mutex de instancia única de menu_contextual.py).
; La variante de prueba se instala aparte: no debe pararse porque la
; aplicación real esté abierta en el equipo que compila.
#ifndef Prueba
AppMutex=Local\AventyaPDF-instancia
#endif
; Descomprimir el .zip de Python y los wheels (que también son zip).
ArchiveExtraction=full
ExtraDiskSpaceRequired={#ComponentesBytes}
#ifdef TamanoInstalado
; (r112) Lo que se ve en Configuración › Aplicaciones. Sin esto, Inno suma los
; archivos descargados (que se borran tras descomprimirlos) a lo instalado.
; Lo mide construir.ps1 sobre la copia completa ya precompilada.
UninstallDisplaySize={#TamanoInstalado}
#endif

; (r136) El instalador pregunta el idioma al empezar (preselecciona el de
; Windows) y la aplicación arranca en ese idioma (GuardarIdioma, en [Code]).
; Gallego y euskera no vienen con Inno Setup: sus mensajes están en
; empaquetado\idiomas (traducciones no oficiales de Inno Setup).
[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "fr"; MessagesFile: "compiler:Languages\French.isl"
Name: "it"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "ca"; MessagesFile: "compiler:Languages\Catalan.isl"
Name: "gl"; MessagesFile: "idiomas\Galician.isl"
Name: "eu"; MessagesFile: "idiomas\Basque.isl"

; Textos propios del instalador en cada idioma: los genera
; «python herramientas_idioma.py instalador» desde empaquetado\idiomas\*.json.
#include "idiomas\mensajes.iss"

#ifndef Prueba
[Tasks]
Name: "escritorio"; Description: "{cm:TareaEscritorio}"; GroupDescription: "{cm:GrupoAccesos}"
#endif

[Files]
; Lo propio va DESPUÉS de las descargas (componentes.iss): así su
; runtime\python3XX._pth sustituye al que trae el Python descargado.
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; (r103, petición de Ricardo) El manual, fuera de app\: así se ve nada más
; abrir el diálogo «Abrir PDF» la primera vez, antes de que haya una carpeta
; reciente — ver window_document.open_pdf. (r138) Uno por idioma, solo el del
; idioma elegido; Ayuda › Manual ofrece el de la web si se cambia de idioma.
Source: "..\docs\manual\MANUAL_es.pdf"; DestDir: "{app}\manual"; Languages: es; Flags: ignoreversion
Source: "..\docs\manual\MANUAL_en.pdf"; DestDir: "{app}\manual"; Languages: en; Flags: ignoreversion
Source: "..\docs\manual\MANUAL_fr.pdf"; DestDir: "{app}\manual"; Languages: fr; Flags: ignoreversion
Source: "..\docs\manual\MANUAL_it.pdf"; DestDir: "{app}\manual"; Languages: it; Flags: ignoreversion
Source: "..\docs\manual\MANUAL_ca.pdf"; DestDir: "{app}\manual"; Languages: ca; Flags: ignoreversion
Source: "..\docs\manual\MANUAL_gl.pdf"; DestDir: "{app}\manual"; Languages: gl; Flags: ignoreversion
Source: "..\docs\manual\MANUAL_eu.pdf"; DestDir: "{app}\manual"; Languages: eu; Flags: ignoreversion
#ifndef Prueba
; (r127) Para quitar el menú de la versión anterior antes de copiar nada
; (PrepareToInstall, con ExtractTemporaryFile): las anteriores no lo tenían.
Source: "{#DistDir}\menu-contextual\AventyaPDF-MenuContextual.exe"; Flags: dontcopy
; (r138) Imágenes de las diapositivas (<código>_NN.png): solo se extraen las
; del idioma elegido, a {tmp}.
Source: "diapositivas\*.png"; Flags: dontcopy
#endif

[InstallDelete]
; Al actualizar, fuera los restos de la versión anterior (bibliotecas que ya no se usan).
Type: filesandordirs; Name: "{app}\_internal"
; (r102) Tesseract ya no va incluido: si una versión anterior lo dejó aquí
; (153 MB), se quita — se descargará solo la primera vez que haga falta.
Type: filesandordirs; Name: "{app}\tesseract"
; (r109) Python, paquetes y código: siempre desde cero, sin restos de la versión anterior.
Type: filesandordirs; Name: "{app}\runtime"
Type: filesandordirs; Name: "{app}\app"
; (r138) El manual ya no va suelto junto al .exe sino en manual\, uno por
; idioma: fuera el de antes y el del idioma de la instalación anterior.
Type: files; Name: "{app}\MANUAL.pdf"
Type: filesandordirs; Name: "{app}\manual"

[Run]
; (r109) Precompila el código de Python ahora y no en el primer arranque, que
; si no tardaría bastante más. Algunos paquetes traen archivos de prueba que
; no compilan: no importa, por eso no se mira el código de salida.
Filename: "{app}\runtime\python.exe"; Parameters: "-m compileall -q -j 0 ""{app}\app"" ""{app}\runtime\Lib\site-packages"""; StatusMsg: "{cm:PreparandoArranque}"; Flags: runhidden

#ifndef Prueba
[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; AppUserModelID: "Aventya.AventyaPDF"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; AppUserModelID: "Aventya.AventyaPDF"; Tasks: escritorio

[Registry]
; Tipo de documento propio y «Abrir con» de los .pdf
; (r87, petición de Ricardo: «el icono de los PDF no debe cambiar») SIN
; DefaultIcon aquí a propósito: [Code] lo escribe copiando el que ya
; tuvieran los .pdf (Acrobat, Edge…) para que elegir AventyaPDF cambie el
; visor, no el dibujo del archivo en el Explorador — ver CopiarIconoDePdf.
Root: HKA; Subkey: "Software\Classes\{#ProgId}"; ValueType: string; ValueName: ""; ValueData: "{cm:TipoDocumento}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\{#ProgId}"; ValueType: string; ValueName: "AppUserModelID"; ValueData: "Aventya.AventyaPDF"
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
Root: HKA; Subkey: "Software\Aventya\{#AppName}\Capabilities"; ValueType: string; ValueName: "ApplicationDescription"; ValueData: "{cm:DescripcionApp}"
Root: HKA; Subkey: "Software\Aventya\{#AppName}\Capabilities\FileAssociations"; ValueType: string; ValueName: ".pdf"; ValueData: "{#ProgId}"
Root: HKA; Subkey: "Software\RegisteredApplications"; ValueType: string; ValueName: "{#AppName}"; ValueData: "Software\Aventya\{#AppName}\Capabilities"; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:AbrirApp,{#AppName}}"; Flags: nowait postinstall skipifsilent
; (r121) Actualización desde la propia aplicación (/SILENT /REINICIAR): al acabar, se vuelve a abrir.
; (r127) Desde la 0.9.12 la aplicación ya no lanza el instalador (lo deja en Descargas y lo
; instala el usuario), pero la 0.9.11 aún actualiza así: no quitar mientras pueda haberla instalada.
Filename: "{app}\{#AppExe}"; Flags: nowait; Check: Reiniciar
#endif

[UninstallDelete]
Type: files; Name: "{app}\menu-contextual\registro.txt"
; (r109) Lo que crea Python al funcionar (__pycache__ y .pyc de compileall).
Type: filesandordirs; Name: "{app}\runtime"
Type: filesandordirs; Name: "{app}\app"
#ifndef Prueba
; (r130, petición de Ricardo: «que el desinstalador de AventyaPDF deje el
; sistema tan limpio como lo acabas de hacer tú… que se eliminen todos los
; ajustes y los certificados de AventyaPDF») Lo que la aplicación crea en
; %LOCALAPPDATA%\aventyapdf: idiomas de OCR, colas del menú contextual y
; registros de errores. Uno a uno y no la carpeta entera: en los equipos de
; desarrollo ahí viven también venv\ y build-*\ (run.ps1, construir.ps1), que
; no son de la aplicación instalada; la carpeta se quita si queda vacía (en
; el equipo de un usuario, siempre). Fuera de la variante de prueba: la
; instalación de prueba de construir.ps1 no debe borrar nada de esto.
; Si la aplicación empieza a guardar algo nuevo ahí, añadirlo aquí.
Type: filesandordirs; Name: "{localappdata}\aventyapdf\tessdata"
Type: filesandordirs; Name: "{localappdata}\aventyapdf\menu-contextual"
Type: files; Name: "{localappdata}\aventyapdf\*.log"
Type: dirifempty; Name: "{localappdata}\aventyapdf"
; Restos de la actualización de las versiones hasta la 0.9.11.
Type: filesandordirs; Name: "{%TEMP}\aventyapdf-actualizacion"
#endif

#ifndef Prueba
[Code]
// ── (r86) Menú contextual del Explorador ─────────────────────────────────── //
const
  ClaveClasica = 'Software\Classes\SystemFileAssociations\';
  // Mismas extensiones que shell\AventyaPDFShell.cpp y conversion_office.py.
  ExtImagenWord = '.png .jpg .jpeg .bmp .gif .tif .tiff .webp .doc .docx';

// (r127, petición de Ricardo: «la aplicación está usando PowerShell y
// debería dejar de usarlo») Todo lo del menú de Windows 11 lo hace
// AventyaPDF-MenuContextual.exe (shell\MenuContextual.cpp) con las API de
// Windows; hasta r125 se lanzaba PowerShell oculto y elevado, que es lo que
// hacía que Microsoft Defender marcara el instalador.
// Devuelve su código de salida (-1 si no llegó a ejecutarse, p. ej. si se
// rechaza el permiso de administrador).
function Ayudante(const Exe, Params: String; Elevado: Boolean): Integer;
var
  Codigo: Integer;
begin
  if Elevado then begin
    if not ShellExec('runas', Exe, Params, '', SW_HIDE, ewWaitUntilTerminated, Codigo) then
      Codigo := -1;
  end else if not Exec(Exe, Params, '', SW_HIDE, ewWaitUntilTerminated, Codigo) then
    Codigo := -1;
  Result := Codigo;
end;

function AyudanteInstalado: String;
begin
  Result := ExpandConstant('{app}\menu-contextual\AventyaPDF-MenuContextual.exe');
end;

// (r121) Sin mensajes en modo /VERYSILENT (pruebas, despliegues), pero sí
// con /SILENT, que es como actualizaba la propia aplicación hasta la 0.9.11.
function Silencioso: Boolean;
begin
  Result := WizardSilent and (Pos('/VERYSILENT', Uppercase(GetCmdTail)) > 0);
end;

// (r121) /REINICIAR: la aplicación se cerró para actualizarse; se vuelve a abrir.
function Reiniciar: Boolean;
begin
  Result := Pos('/REINICIAR', Uppercase(GetCmdTail)) > 0;
end;

function EsWindows11: Boolean;
var
  V: TWindowsVersion;
begin
  GetWindowsVersionEx(V);
  Result := (V.Major > 10) or ((V.Major = 10) and (V.Build >= 22000));
end;

// (r136) Texto propio del instalador en el idioma elegido (mensajes.iss),
// con «%n» convertido en salto de línea.
function Msg(const Clave: String): String;
begin
  Result := CustomMessage(Clave);
  StringChangeEx(Result, '%n', #13#10, True);
end;

procedure Aviso(const Texto: String);
begin
  if not WizardSilent then
    MsgBox(Texto, mbInformation, MB_OK);
end;

procedure QuitarMenuModerno(const Exe: String);
begin
  if FileExists(Exe) then
    Ayudante(Exe, 'quitar', False);
end;

procedure InstalarMenuModerno;
var
  Carpeta, Cer, Msix, Registro, Exe: String;
begin
  if not EsWindows11 then
    exit;
  Carpeta := ExpandConstant('{app}\menu-contextual');
  Cer := Carpeta + '\AventyaPDF-MenuContextual.cer';
  Msix := Carpeta + '\AventyaPDF-MenuContextual.msix';
  Registro := Carpeta + '\registro.txt';
  DeleteFile(Registro);
  Exe := AyudanteInstalado;
  // ¿El equipo ya confía en el certificado del paquete?
  if Ayudante(Exe, 'comprobar "' + Cer + '"', False) <> 0 then begin
    // (r121, petición de Ricardo: «siempre se debe forzar la instalación como
    // administrador, o dar la opción a ello para que el menú del ratón se pueda
    // recuperar bien») El permiso de administrador se pide aunque la
    // instalación sea silenciosa (actualización desde la app), y si se
    // cancela se ofrece reintentarlo antes de quedarse sin el menú principal.
    // Solo este paso se eleva: el resto, y el registro del paquete, son del
    // usuario que instala (el registro del paquete es por usuario).
    if not Silencioso then
      MsgBox(Msg('MenuConfianza'), mbInformation, MB_OK);
    while Ayudante(Exe, 'confiar "' + Cer + '"', True) <> 0 do begin
      if Silencioso or (MsgBox(Msg('MenuSinPermiso'), mbConfirmation, MB_YESNO) <> IDYES) then
        exit;
    end;
  end;
  if Ayudante(Exe, 'registrar "' + Msix + '" "' + ExpandConstant('{app}') + '" "' + Registro + '"',
              False) <> 0 then
    Aviso(Msg('MenuFallo') + #13#10 + Registro);
end;

procedure OpcionClasica(const Raiz, Verbo, Titulo, Accion: String);
var
  Clave: String;
begin
  Clave := Raiz + '\shell\' + Verbo;
  RegWriteStringValue(HKCU, Clave, '', Titulo);
  RegWriteStringValue(HKCU, Clave, 'MultiSelectModel', 'Player');
  RegWriteStringValue(HKCU, Clave + '\command', '',
    '"' + ExpandConstant('{app}\{#AppExe}') + '" ' + Accion + ' "%1"');
end;

function RaizClasica(const Ext: String): String;
begin
  Result := ClaveClasica + Ext + '\shell\AventyaPDF';
  RegWriteStringValue(HKCU, Result, 'MUIVerb', 'AventyaPDF');
  RegWriteStringValue(HKCU, Result, 'Icon', ExpandConstant('{app}\{#AppExe},0'));
  RegWriteStringValue(HKCU, Result, 'SubCommands', '');
end;

// Lista de extensiones separadas por espacios → una a una.
function SiguienteExt(var Lista: String): String;
var
  P: Integer;
begin
  Lista := Trim(Lista);
  P := Pos(' ', Lista);
  if P = 0 then begin
    Result := Lista;
    Lista := '';
  end else begin
    Result := Copy(Lista, 1, P - 1);
    Delete(Lista, 1, P);
  end;
end;

procedure InstalarMenuClasico;
var
  Raiz, Lista, Ext: String;
begin
  Raiz := RaizClasica('.pdf');
  OpcionClasica(Raiz, '01Firmar', Msg('MenuFirmar'), '--firmar');
  OpcionClasica(Raiz, '02Combinar', Msg('MenuCombinar'), '--combinar');
  Lista := ExtImagenWord;
  while Lista <> '' do begin
    Ext := SiguienteExt(Lista);
    Raiz := RaizClasica(Ext);
    OpcionClasica(Raiz, '01Combinar', Msg('MenuCombinar'), '--combinar');
    OpcionClasica(Raiz, '02Convertir', Msg('MenuConvertir'), '--convertir');
  end;
end;

procedure QuitarMenuClasico;
var
  Lista: String;
begin
  Lista := '.pdf ' + ExtImagenWord;
  while Lista <> '' do
    RegDeleteKeyIncludingSubkeys(HKCU, ClaveClasica + SiguienteExt(Lista) + '\shell\AventyaPDF');
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  // Al actualizar: fuera el paquete anterior antes de sustituir su DLL.
  ExtractTemporaryFile('AventyaPDF-MenuContextual.exe');
  QuitarMenuModerno(ExpandConstant('{tmp}\AventyaPDF-MenuContextual.exe'));
  Result := '';
end;

// ── (r87) El icono de los .pdf no debe cambiar ──────────────────────────── //
// Petición de Ricardo: «el icono de los ficheros PDF del sistema no deben
// cambiar, deben seguir siendo los originales de Windows 11... lo único que
// cambia es que el visor es ahora AventyaPDF». En Windows, el icono que
// enseña el Explorador para un tipo de archivo es el de `DefaultIcon` del
// ProgID que lo abre (Acrobat, Edge, el que sea) — no hay un "icono nativo
// de Windows" aparte que copiar. Así que, antes de que AventyaPDF.Document
// sea ese ProgID, se copia el `DefaultIcon` que YA tuvieran los .pdf, para
// que asociar AventyaPDF no les cambie el dibujo, solo la app que los abre.

// ProgID que abre hoy los .pdf: primero el elegido por el usuario
// (Configuración › Aplicaciones predeterminadas, que manda sobre el
// asociado por la extensión), si no el de la extensión misma.
function ProgIdActualDePdf: String;
var
  Valor: String;
begin
  Result := '';
  if RegQueryStringValue(HKCU,
       'Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\.pdf\UserChoice',
       'ProgId', Valor) and (Valor <> '') then begin
    Result := Valor;
    exit;
  end;
  if RegQueryStringValue(HKCR, '.pdf', '', Valor) and (Valor <> '') then
    Result := Valor;
end;

procedure CopiarIconoDePdfSiHaceFalta;
var
  ProgId, Icono: String;
begin
  ProgId := ProgIdActualDePdf;
  // Vacío (ningún lector de PDF instalado) o ya es el nuestro (instalación
  // anterior, o esta misma actualización): no hay de dónde copiar, y de
  // haberlo copiado ya una vez no hace falta —ni conviene— repetirlo.
  if (ProgId = '') or (ProgId = '{#ProgId}') then
    exit;
  if not RegQueryStringValue(HKCR, ProgId + '\DefaultIcon', '', Icono) then
    exit;
  if Icono = '' then
    exit;
  RegWriteStringValue(HKA, 'Software\Classes\{#ProgId}\DefaultIcon', '', Icono);
end;

// ── (r136) Idioma de la aplicación ─────────────────────────────────────── //
// AventyaPDF arranca en el idioma de su ajuste «ui/idioma» (idioma.py), en
// el registro del usuario. Se escribe el elegido en el instalador cuando no
// hay ninguno o cuando se ha elegido uno distinto del de la instalación
// anterior; si es el mismo, se respeta el que se haya puesto después desde
// Ayuda › Idioma (al actualizar, el instalador propone el idioma anterior).
const
  ClaveIdioma = 'Software\aventyapdf\config\ui';

procedure RegisterPreviousData(PreviousDataKey: Integer);
begin
  SetPreviousData(PreviousDataKey, 'Idioma', ActiveLanguage);
end;

procedure GuardarIdioma;
var
  Actual: String;
begin
  if (GetPreviousData('Idioma', '') <> ActiveLanguage) or
     not RegQueryStringValue(HKCU, ClaveIdioma, 'idioma', Actual) then
    RegWriteStringValue(HKCU, ClaveIdioma, 'idioma', ActiveLanguage);
end;

// ── (r138) Diapositivas mientras instala ──────────────────────────────── //
// Petición de Ricardo: «en el instalador deben ir apareciendo las
// descripciones de las herramientas de la aplicación usando texto e
// imágenes; los textos pueden obtenerse de la pantalla de inicio». Debajo de
// la barra de progreso: la imagen a la izquierda y el título y el texto de la
// diapositiva a la derecha; cambia cada 7 s con un temporizador de Windows
// (SetTimer + CreateCallback, como el ejemplo CodeDll.iss de Inno Setup).
// Las imágenes se extraen todas al empezar: el temporizador salta mientras
// Inno descomprime los archivos y no debe volver a descomprimir nada.
// Necesita Inno Setup 6.5.2 o posterior (PngImage).
const
  DiapoMs = 7000;

var
  DiapoImagen: TBitmapImage;
  DiapoTitulo, DiapoTexto: TNewStaticText;
  DiapoActual: Integer;
  DiapoTimer: UINT_PTR;

function SetTimer(hWnd: HWND; nIDEvent: UINT_PTR; uElapse: UINT; lpTimerFunc: NativeInt): UINT_PTR;
external 'SetTimer@user32.dll stdcall';

function KillTimer(hWnd: HWND; nIDEvent: UINT_PTR): BOOL;
external 'KillTimer@user32.dll stdcall';

function NombreDiapositiva(N: Integer): String;
begin
  Result := ActiveLanguage + '_' + Format('%.2d', [N]) + '.png';
end;

procedure MostrarDiapositiva(N: Integer);
begin
  try
    DiapoImagen.PngImage.LoadFromFile(ExpandConstant('{tmp}\') + NombreDiapositiva(N));
  except
    // Sin imagen la diapositiva sigue saliendo con su texto.
  end;
  DiapoTitulo.Caption := CustomMessage(Format('Diapo%.2dTitulo', [N]));
  DiapoTexto.Caption := CustomMessage(Format('Diapo%.2dTexto', [N]));
end;

procedure SiguienteDiapositiva(Arg1: HWND; Arg2: UINT; Arg3: UINT_PTR; Arg4: DWORD);
begin
  DiapoActual := DiapoActual mod {#NumDiapositivas} + 1;
  MostrarDiapositiva(DiapoActual);
end;

procedure PararDiapositivas;
begin
  if DiapoTimer <> 0 then
    KillTimer(0, DiapoTimer);
  DiapoTimer := 0;
end;

procedure CrearDiapositivas;
var
  Pagina: TNewNotebookPage;
  Arriba, Ancho, Alto, AnchoImg, AltoImg, Hueco, I: Integer;
begin
  for I := 1 to {#NumDiapositivas} do
    try
      ExtractTemporaryFile(NombreDiapositiva(I));
    except
    end;
  Pagina := WizardForm.InstallingPage;
  Arriba := WizardForm.ProgressGauge.Top + WizardForm.ProgressGauge.Height + ScaleY(20);
  Ancho := WizardForm.ProgressGauge.Width;
  Alto := Pagina.ClientHeight - Arriba - ScaleY(4);
  Hueco := ScaleX(14);
  // Imagen 420 × 260 (proporción 1,615), a lo sumo el 55 % del ancho.
  AltoImg := Alto;
  AnchoImg := AltoImg * 420 div 260;
  if AnchoImg > Ancho * 55 div 100 then begin
    AnchoImg := Ancho * 55 div 100;
    AltoImg := AnchoImg * 260 div 420;
  end;
  DiapoImagen := TBitmapImage.Create(WizardForm);
  DiapoImagen.Parent := Pagina;
  DiapoImagen.SetBounds(WizardForm.ProgressGauge.Left, Arriba, AnchoImg, AltoImg);
  DiapoImagen.Stretch := True;
  DiapoTitulo := TNewStaticText.Create(WizardForm);
  DiapoTitulo.Parent := Pagina;
  DiapoTitulo.AutoSize := False;
  DiapoTitulo.WordWrap := True;
  DiapoTitulo.Font.Style := [fsBold];
  DiapoTitulo.Font.Size := DiapoTitulo.Font.Size + 2;
  DiapoTitulo.SetBounds(DiapoImagen.Left + AnchoImg + Hueco, Arriba,
                        Ancho - AnchoImg - Hueco, ScaleY(40));
  DiapoTexto := TNewStaticText.Create(WizardForm);
  DiapoTexto.Parent := Pagina;
  DiapoTexto.AutoSize := False;
  DiapoTexto.WordWrap := True;
  DiapoTexto.SetBounds(DiapoTitulo.Left, Arriba + ScaleY(44), DiapoTitulo.Width,
                       Alto - ScaleY(44));
  DiapoActual := 1;
  MostrarDiapositiva(DiapoActual);
end;

procedure InitializeWizard;
begin
  CrearDiapositivas;
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if (CurPageID = wpInstalling) and (DiapoTimer = 0) then
    DiapoTimer := SetTimer(0, 0, DiapoMs, CreateCallback(@SiguienteDiapositiva))
  else if CurPageID <> wpInstalling then
    PararDiapositivas;
end;

procedure DeinitializeSetup;
begin
  PararDiapositivas;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then begin
    GuardarIdioma;
    CopiarIconoDePdfSiHaceFalta;
    InstalarMenuClasico;
    InstalarMenuModerno;
  end;
end;

// ── (r130) Desinstalar sin dejar rastro ────────────────────────────────── //
// Los ajustes (QSettings("aventyapdf", "config")) viven en el registro del
// usuario; las contraseñas de certificados que se guardaron, en el
// Administrador de credenciales (keyring); el certificado del menú, en
// «Personas de confianza» del EQUIPO (quitarlo pide administrador, como
// añadirlo). Ojo: si otro usuario de este equipo tiene AventyaPDF instalado,
// su submenú de Windows 11 deja de poder registrarse hasta que vuelva a
// instalar o use Ayuda › Reparar el menú contextual.
procedure QuitarCertificados(const Exe: String);
begin
  if not FileExists(Exe) or (Ayudante(Exe, 'confiados', False) <> 0) then
    exit;
  if not UninstallSilent then
    MsgBox(Msg('CertQuitar'), mbInformation, MB_OK);
  if (Ayudante(Exe, 'desconfiar', True) <> 0) and not UninstallSilent then
    MsgBox(Msg('CertNoQuitado'), mbInformation, MB_OK);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then begin
    QuitarMenuModerno(AyudanteInstalado);
    QuitarMenuClasico;
    if FileExists(AyudanteInstalado) then
      Ayudante(AyudanteInstalado, 'olvidar-claves', False);
    QuitarCertificados(AyudanteInstalado);
    RegDeleteKeyIncludingSubkeys(HKCU, 'Software\aventyapdf');
  end;
end;
#endif
