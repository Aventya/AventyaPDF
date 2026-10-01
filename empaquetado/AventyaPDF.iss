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
;  * Integración con Windows: acceso directo en el menú Inicio (siempre) y en el
;    escritorio (casilla), y AventyaPDF en «Abrir con» de los PDF. Windows 11
;    no deja que un programa se imponga como predeterminado: queda registrado
;    y el usuario lo elige en «Abrir con» o en Aplicaciones predeterminadas.
;  * (r86) Menú contextual del Explorador, submenú «AventyaPDF» con Firmar
;    digitalmente / Combinar en un PDF / Convertir a PDF (ver [Code]):
;      - Menú PRINCIPAL de Windows 11: paquete MSIX disperso firmado con la
;        DLL de shell\ (Add-AppxPackage -ExternalLocation {app}). Windows solo
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

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Messages]
WelcomeLabel2=Se instalará [name/ver] en este equipo.%n%nDurante la instalación se descargarán de sus sitios oficiales Python, los componentes de Python y las fuentes tipográficas (unos {#ComponentesMB} MB): hace falta conexión a Internet.%n%nSe recomienda cerrar AventyaPDF antes de continuar.

#ifndef Prueba
[Tasks]
Name: "escritorio"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"
#endif

[Files]
; Lo propio va DESPUÉS de las descargas (componentes.iss): así su
; runtime\python3XX._pth sustituye al que trae el Python descargado.
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; (r103, petición de Ricardo) El manual, junto al .exe (no dentro de
; _internal): así se ve nada más abrir el diálogo «Abrir PDF» la primera
; vez, antes de que haya una carpeta reciente — ver window_document.open_pdf.
Source: "..\docs\MANUAL.pdf"; DestDir: "{app}"; Flags: ignoreversion

[InstallDelete]
; Al actualizar, fuera los restos de la versión anterior (bibliotecas que ya no se usan).
Type: filesandordirs; Name: "{app}\_internal"
; (r102) Tesseract ya no va incluido: si una versión anterior lo dejó aquí
; (153 MB), se quita — se descargará solo la primera vez que haga falta.
Type: filesandordirs; Name: "{app}\tesseract"
; (r109) Python, paquetes y código: siempre desde cero, sin restos de la versión anterior.
Type: filesandordirs; Name: "{app}\runtime"
Type: filesandordirs; Name: "{app}\app"

[Run]
; (r109) Precompila el código de Python ahora y no en el primer arranque, que
; si no tardaría bastante más. Algunos paquetes traen archivos de prueba que
; no compilan: no importa, por eso no se mira el código de salida.
Filename: "{app}\runtime\python.exe"; Parameters: "-m compileall -q -j 0 ""{app}\app"" ""{app}\runtime\Lib\site-packages"""; StatusMsg: "Preparando AventyaPDF para el primer arranque…"; Flags: runhidden

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
Root: HKA; Subkey: "Software\Classes\{#ProgId}"; ValueType: string; ValueName: ""; ValueData: "Documento PDF"; Flags: uninsdeletekey
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
Root: HKA; Subkey: "Software\Aventya\{#AppName}\Capabilities"; ValueType: string; ValueName: "ApplicationDescription"; ValueData: "Visor y editor de PDF con firma digital y OCR"
Root: HKA; Subkey: "Software\Aventya\{#AppName}\Capabilities\FileAssociations"; ValueType: string; ValueName: ".pdf"; ValueData: "{#ProgId}"
Root: HKA; Subkey: "Software\RegisteredApplications"; ValueType: string; ValueName: "{#AppName}"; ValueData: "Software\Aventya\{#AppName}\Capabilities"; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#AppExe}"; Description: "Abrir {#AppName}"; Flags: nowait postinstall skipifsilent
#endif

[UninstallDelete]
Type: files; Name: "{app}\menu-contextual\registro.txt"
; (r109) Lo que crea Python al funcionar (__pycache__ y .pyc de compileall).
Type: filesandordirs; Name: "{app}\runtime"
Type: filesandordirs; Name: "{app}\app"

#ifndef Prueba
[Code]
// ── (r86) Menú contextual del Explorador ─────────────────────────────────── //
const
  PaqueteMenu = 'Aventya.AventyaPDF.MenuContextual';
  ClaveClasica = 'Software\Classes\SystemFileAssociations\';
  // Mismas extensiones que shell\AventyaPDFShell.cpp y conversion_office.py.
  ExtImagenWord = '.png .jpg .jpeg .bmp .gif .tif .tiff .webp .doc .docx';

// Texto como literal de PowerShell entre comillas simples.
function Literal(const S: String): String;
var
  T: String;
begin
  T := S;
  StringChangeEx(T, '''', '''''', True);
  Result := '''' + T + '''';
end;

// Ejecuta una orden de PowerShell sin ventana; devuelve su código de salida
// (-1 si no llegó a ejecutarse, p. ej. si se rechaza el permiso).
function PowerShell(const Orden: String; Elevado: Boolean): Integer;
var
  Exe, Params: String;
  Codigo: Integer;
begin
  Exe := ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe');
  Params := '-NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "' + Orden + '"';
  if Elevado then begin
    if not ShellExec('runas', Exe, Params, '', SW_HIDE, ewWaitUntilTerminated, Codigo) then
      Codigo := -1;
  end else if not Exec(Exe, Params, '', SW_HIDE, ewWaitUntilTerminated, Codigo) then
    Codigo := -1;
  Result := Codigo;
end;

function EsWindows11: Boolean;
var
  V: TWindowsVersion;
begin
  GetWindowsVersionEx(V);
  Result := (V.Major > 10) or ((V.Major = 10) and (V.Build >= 22000));
end;

procedure Aviso(const Texto: String);
begin
  if not WizardSilent then
    MsgBox(Texto, mbInformation, MB_OK);
end;

procedure QuitarMenuModerno;
begin
  PowerShell('Get-AppxPackage -Name ' + PaqueteMenu + ' | Remove-AppxPackage', False);
end;

procedure InstalarMenuModerno;
var
  Carpeta, Cer, Msix, Registro: String;
begin
  if not EsWindows11 then
    exit;
  Carpeta := ExpandConstant('{app}\menu-contextual');
  Cer := Carpeta + '\AventyaPDF-MenuContextual.cer';
  Msix := Carpeta + '\AventyaPDF-MenuContextual.msix';
  Registro := Carpeta + '\registro.txt';
  DeleteFile(Registro);
  // ¿El equipo ya confía en el certificado del paquete?
  if PowerShell('$c = New-Object Security.Cryptography.X509Certificates.X509Certificate2 ' + Literal(Cer) +
                '; if (Test-Path (''Cert:\LocalMachine\TrustedPeople\'' + $c.Thumbprint)) { exit 0 } else { exit 1 }',
                False) <> 0 then begin
    Aviso('Para que el submenú «AventyaPDF» aparezca en el menú del botón derecho de Windows 11, ' +
          'Windows tiene que confiar en el certificado de AventyaPDF.' + #13#10#13#10 +
          'A continuación Windows pedirá permiso de administrador (solo esta vez).');
    if PowerShell('Import-Certificate -FilePath ' + Literal(Cer) +
                  ' -CertStoreLocation Cert:\LocalMachine\TrustedPeople | Out-Null', True) <> 0 then begin
      Aviso('No se ha dado el permiso: el submenú «AventyaPDF» estará en «Mostrar más opciones» ' +
            'del menú del botón derecho. Puede volver a ejecutar el instalador para añadirlo al menú principal.');
      exit;
    end;
  end;
  if PowerShell('try { Add-AppxPackage -Path ' + Literal(Msix) + ' -ExternalLocation ' +
                Literal(ExpandConstant('{app}')) + ' -ForceUpdateFromAnyVersion -ErrorAction Stop } ' +
                'catch { $_ | Out-File -Encoding utf8 ' + Literal(Registro) + '; exit 1 }', False) <> 0 then
    Aviso('No se pudo añadir el submenú «AventyaPDF» al menú principal de Windows 11 ' +
          '(sigue en «Mostrar más opciones»). Detalle en:' + #13#10 + Registro);
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
  OpcionClasica(Raiz, '01Firmar', 'Firmar digitalmente', '--firmar');
  OpcionClasica(Raiz, '02Combinar', 'Combinar en un PDF', '--combinar');
  Lista := ExtImagenWord;
  while Lista <> '' do begin
    Ext := SiguienteExt(Lista);
    Raiz := RaizClasica(Ext);
    OpcionClasica(Raiz, '01Combinar', 'Combinar en un PDF', '--combinar');
    OpcionClasica(Raiz, '02Convertir', 'Convertir a PDF', '--convertir');
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
  QuitarMenuModerno;
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

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then begin
    CopiarIconoDePdfSiHaceFalta;
    InstalarMenuClasico;
    InstalarMenuModerno;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then begin
    QuitarMenuModerno;
    QuitarMenuClasico;
  end;
end;
#endif
