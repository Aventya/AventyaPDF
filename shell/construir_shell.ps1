<#
    construir_shell.ps1 — Extensión del menú contextual de Windows 11 (r86)
    ----------------------------------------------------------------------
    Deja en -Salida los tres archivos que el instalador necesita:
      AventyaPDFShell.dll              (junto a AventyaPDF.exe)
      AventyaPDF-MenuContextual.msix   paquete disperso firmado
      AventyaPDF-MenuContextual.cer    certificado público con el que se firmó

    1. Compila AventyaPDFShell.cpp con Visual C++ (x64, CRT estático: no
       depende de ningún redistribuible).
    2. Certificado de firma de paquetes: se busca en Cert:\CurrentUser\My del
       equipo que compila y, si no existe, se crea (autofirmado, 10 años). La
       clave privada NUNCA sale de ese almacén ni entra en el proyecto; el
       instalador solo lleva la parte pública (.cer) y la añade a «Personas de
       confianza» del equipo (una vez, con permiso de administrador).
       ⚠ Si se pierde ese certificado, se crea otro: los equipos que ya
       tenían AventyaPDF confiarán en el nuevo en la siguiente instalación
       (el instalador lo comprueba cada vez), pero pedirán administrador otra vez.
    3. makeappx + signtool (Windows SDK).

    Uso (lo llama empaquetado\construir.ps1):
        .\shell\construir_shell.ps1 -Version 1.1.0 -Salida <carpeta>
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Version,
    [Parameter(Mandatory)][string]$Salida
)

$ErrorActionPreference = 'Stop'
# Tiene que coincidir con Publisher de AppxManifest.xml (se sustituye abajo).
$Sujeto = 'CN=Aventya Asesoria Integral SL'
$Nombre = 'AventyaPDF-MenuContextual'

function Comprobar([string]$que) { if ($LASTEXITCODE -ne 0) { throw "$que falló (código $LASTEXITCODE)." } }

New-Item -ItemType Directory -Force $Salida | Out-Null
$trabajo = Join-Path $env:TEMP 'aventyapdf-shell'
Remove-Item -Recurse -Force $trabajo -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $trabajo | Out-Null

# ── 1. DLL ────────────────────────────────────────────────────────────────── #
$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path $vswhere)) { throw 'Falta Visual Studio (o Build Tools) con C++.' }
$vs = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vs) { throw 'Falta el componente de C++ de Visual Studio (VC.Tools.x86.x64).' }
$vcvars = Join-Path $vs 'VC\Auxiliary\Build\vcvars64.bat'
$dll = Join-Path $Salida 'AventyaPDFShell.dll'
$cpp = Join-Path $PSScriptRoot 'AventyaPDFShell.cpp'
$def = Join-Path $PSScriptRoot 'AventyaPDFShell.def'
$orden = "set `"PATH=$(Split-Path $vswhere);%PATH%`" && `"$vcvars`" >nul && cl /nologo /EHsc /O2 /MT /std:c++17 /W3 /DUNICODE /D_UNICODE " +
         "/Fo`"$trabajo\\`" /LD `"$cpp`" /link /DEF:`"$def`" /OUT:`"$dll`" /IMPLIB:`"$trabajo\AventyaPDFShell.lib`""
cmd /c $orden
Comprobar 'Compilar AventyaPDFShell.dll'

# ── 2. Certificado ────────────────────────────────────────────────────────── #
$cert = Get-ChildItem Cert:\CurrentUser\My |
        Where-Object { $_.Subject -eq $Sujeto -and $_.HasPrivateKey -and $_.NotAfter -gt (Get-Date).AddDays(30) } |
        Sort-Object NotAfter -Descending | Select-Object -First 1
if (-not $cert) {
    Write-Host "  Creando el certificado de firma de paquetes ($Sujeto)…" -ForegroundColor Yellow
    $cert = New-SelfSignedCertificate -Type Custom -Subject $Sujeto `
        -FriendlyName 'AventyaPDF — firma del paquete del menú contextual' `
        -KeyUsage DigitalSignature -KeyAlgorithm RSA -KeyLength 3072 `
        -CertStoreLocation Cert:\CurrentUser\My -NotAfter (Get-Date).AddYears(10) `
        -TextExtension @('2.5.29.37={text}1.3.6.1.5.5.7.3.3', '2.5.29.19={text}')
}
Export-Certificate -Cert $cert -FilePath (Join-Path $Salida "$Nombre.cer") -Type CERT | Out-Null

# ── 3. Paquete ────────────────────────────────────────────────────────────── #
$sdk = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin\10.*\x64\makeappx.exe" -ErrorAction SilentlyContinue |
       Sort-Object FullName -Descending | Select-Object -First 1
if (-not $sdk) { throw 'Falta el Windows SDK (makeappx.exe / signtool.exe).' }
$makeappx = $sdk.FullName
$signtool = Join-Path $sdk.DirectoryName 'signtool.exe'

$v4 = (($Version.Split('.') + @('0', '0', '0', '0'))[0..2] -join '.') + '.0'
$paquete = Join-Path $trabajo 'paquete'
New-Item -ItemType Directory -Force $paquete | Out-Null
Copy-Item -Recurse (Join-Path $PSScriptRoot 'imagenes') $paquete
(Get-Content (Join-Path $PSScriptRoot 'AppxManifest.xml') -Raw -Encoding utf8).
    Replace('@VERSION@', $v4).Replace('@PUBLISHER@', $Sujeto) |
    Set-Content (Join-Path $paquete 'AppxManifest.xml') -Encoding utf8
$msix = Join-Path $Salida "$Nombre.msix"
& $makeappx pack /o /nv /d $paquete /p $msix | Out-Null
Comprobar 'makeappx'
& $signtool sign /q /fd SHA256 /s My /sha1 $cert.Thumbprint $msix
Comprobar 'signtool'
Remove-Item -Recurse -Force $trabajo -ErrorAction SilentlyContinue
Write-Host "  Menú contextual de Windows 11: $Nombre.msix $v4 (certificado $($cert.Thumbprint))" -ForegroundColor Green
