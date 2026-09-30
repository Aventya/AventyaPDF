<#
    construir.ps1 — Crea el instalador de AventyaPDF (r62; r109 sin PyInstaller)
    ---------------------------------------------------------------------------
    (r109, petición de Ricardo: «el instalador no lleve partes que se mantengan
    fuera de este proyecto») El instalador solo lleva lo propio; Python, los
    paquetes y las fuentes los descarga él mismo al instalar, de su origen
    oficial y comprobando el SHA-256 (ver componentes.py).

    1. Lanzador AventyaPDF.exe (lanzador\) y extensión del menú contextual de
       Windows 11 (shell\) → carpeta de lo propio
       (%LOCALAPPDATA%\aventyapdf\build-dist\AventyaPDF).
    2. componentes.py, con las versiones EXACTAS del entorno de la aplicación
       (lo ya probado): copia el código a app\, escribe las descargas para Inno
       Setup (componentes.iss) y monta en build-dist\AventyaPDF-completo una
       copia idéntica a la instalación.
    3. Autodiagnóstico de esa copia a través del lanzador (ventana, archivos,
       OCR con el Tesseract del equipo que compila, firma con un certificado de
       pruebas). Si algo falla, no se crea el instalador.
    4. Inno Setup → empaquetado\salida\AventyaPDF-Setup-<versión>.exe
    5. (-ProbarInstalacion) Instala de verdad una variante de prueba (otro
       AppId, en %TEMP%, sin accesos directos, registro ni menú contextual),
       que descarga todo de Internet, le pasa el autodiagnóstico y la
       desinstala. Comprueba las URL, los hashes y la descompresión.

    Uso:
        .\empaquetado\construir.ps1
        .\empaquetado\construir.ps1 -ProbarInstalacion
        .\empaquetado\construir.ps1 -SinInstalador     # solo hasta el autodiagnóstico

    Requisitos: el entorno de la aplicación (.\run.ps1 una vez), Tesseract
    instalado (la app lo instala; el autodiagnóstico lo necesita para probar
    el OCR), Inno Setup 6.5 o posterior (winget install JRSoftware.InnoSetup)
    y Visual Studio con C++ y el Windows SDK.
#>
[CmdletBinding()]
param([switch]$SinInstalador, [switch]$ProbarInstalacion)

$ErrorActionPreference = 'Stop'
$Raiz     = Split-Path $PSScriptRoot -Parent
$Base     = Join-Path $env:LOCALAPPDATA 'aventyapdf'
$AppPy    = Join-Path $Base 'venv\Scripts\python.exe'
$Propios  = Join-Path $Base 'build-dist\AventyaPDF'
$Completo = Join-Path $Base 'build-dist\AventyaPDF-completo'
$Salida   = Join-Path $PSScriptRoot 'salida'
$Iss      = Join-Path $PSScriptRoot 'AventyaPDF.iss'

function Paso([string]$t) { Write-Host "`n── $t" -ForegroundColor Cyan }
function Comprobar([string]$que) { if ($LASTEXITCODE -ne 0) { throw "$que falló (código $LASTEXITCODE)." } }

if (-not (Test-Path $AppPy)) { throw "No existe el entorno de la aplicación: ejecuta antes .\run.ps1" }
$Version = (Select-String -Path (Join-Path $Raiz 'window_menus.py') -Pattern 'APP_VERSION = "(.+?)"').Matches[0].Groups[1].Value
if (-not $Version) { throw 'No se encuentra APP_VERSION en window_menus.py' }

function Autodiagnostico([string]$exe) {
    $pfx = Join-Path $env:TEMP 'aventyapdf-diagnostico.pfx'
    $informe = Join-Path $env:TEMP 'aventyapdf-diagnostico.json'
    Remove-Item $informe -ErrorAction SilentlyContinue
    Push-Location $Raiz
    try { & $AppPy -c "from create_test_cert import build_test_pfx; open(r'$pfx','wb').write(build_test_pfx(b'1234'))" }
    finally { Pop-Location }
    Comprobar 'Crear el certificado de pruebas'
    $p = Start-Process -FilePath $exe -Wait -PassThru `
            -ArgumentList @('--autodiagnostico', "`"$informe`"", "`"$pfx`"", '1234')
    Remove-Item $pfx -ErrorAction SilentlyContinue
    if (-not (Test-Path $informe)) { throw "La aplicación no llegó a escribir el autodiagnóstico (código $($p.ExitCode))." }
    $diag = Get-Content $informe -Raw -Encoding utf8 | ConvertFrom-Json
    foreach ($c in $diag.comprobaciones) {
        $marca = if ($c.ok) { 'OK   ' } else { 'FALLO' }
        $color = if ($c.ok) { 'Green' } else { 'Red' }
        Write-Host ("  {0} {1} ({2} s)" -f $marca, $c.nombre, $c.segundos) -ForegroundColor $color
        if (-not $c.ok) { Write-Host $c.detalle -ForegroundColor Red }
    }
    if (-not $diag.ok) { throw "El autodiagnóstico de $exe ha fallado: no se crea el instalador." }
}

# ── 1. Lanzador y menú contextual ─────────────────────────────────────────── #
Paso "Lanzador y menú contextual — AventyaPDF $Version"
if (Test-Path $Propios) { Remove-Item $Propios -Recurse -Force }
& (Join-Path $PSScriptRoot 'lanzador\construir_lanzador.ps1') -Version $Version -Salida $Propios
& (Join-Path $Raiz 'shell\construir_shell.ps1') -Version $Version -Salida (Join-Path $Propios 'menu-contextual')
Move-Item -Force (Join-Path $Propios 'menu-contextual\AventyaPDFShell.dll') $Propios

# ── 2. Código y componentes descargables ──────────────────────────────────── #
Paso 'Código de la aplicación y componentes que se descargan al instalar'
$versiones = Join-Path $env:TEMP 'aventyapdf-versiones.txt'
& $AppPy -m pip freeze --disable-pip-version-check | Set-Content -Encoding utf8 $versiones
Comprobar 'Leer las versiones del entorno de la aplicación'
$env:PYTHONIOENCODING = 'utf-8'
& $AppPy (Join-Path $PSScriptRoot 'componentes.py') --versiones $versiones `
    --propios $Propios --completo $Completo --iss (Join-Path $PSScriptRoot 'componentes.iss')
Comprobar 'componentes.py'

# ── 3. Autodiagnóstico ────────────────────────────────────────────────────── #
Paso 'Autodiagnóstico (copia idéntica a la instalación)'
Autodiagnostico (Join-Path $Completo 'AventyaPDF.exe')
$mb = [math]::Round((Get-ChildItem $Propios -Recurse | Measure-Object Length -Sum).Sum / 1MB, 1)
Write-Host "  Lo propio, lo único que va dentro del instalador: $mb MB" -ForegroundColor Green
if ($SinInstalador) { exit 0 }

# ── 4. Instalador ─────────────────────────────────────────────────────────── #
Paso 'Instalador (Inno Setup)'
$iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
          "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
          "$env:ProgramFiles\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw 'Falta Inno Setup 6: winget install JRSoftware.InnoSetup --scope user' }
& $iscc /Qp "/DAppVersion=$Version" "/DDistDir=$Propios" $Iss
Comprobar 'Inno Setup'
$setup = Join-Path $Salida "AventyaPDF-Setup-$Version.exe"
$mb = [math]::Round((Get-Item $setup).Length / 1MB, 1)
Write-Host "`nInstalador listo: $setup ($mb MB)" -ForegroundColor Green
if (-not $ProbarInstalacion) { exit 0 }

# ── 5. Instalación de prueba ──────────────────────────────────────────────── #
Paso 'Instalación de prueba (descarga todo de Internet)'
$pruebaSalida = Join-Path $env:TEMP 'aventyapdf-prueba-setup'
$destino = Join-Path $env:TEMP 'aventyapdf-prueba-instalacion'
$log = Join-Path $env:TEMP 'aventyapdf-prueba-instalacion.log'
& $iscc /Qp "/DAppVersion=$Version" "/DDistDir=$Propios" '/DPrueba' "/O$pruebaSalida" $Iss
Comprobar 'Inno Setup (variante de prueba)'
if (Test-Path $destino) { Remove-Item $destino -Recurse -Force }
$t = Get-Date
$p = Start-Process (Join-Path $pruebaSalida "AventyaPDF-Setup-$Version.exe") -Wait -PassThru `
        -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', "/DIR=`"$destino`"", "/LOG=`"$log`"")
if ($p.ExitCode -ne 0) { throw "La instalación de prueba falló (código $($p.ExitCode)); registro: $log" }
Write-Host ("  Instalada en {0:N0} s en $destino" -f ((Get-Date) - $t).TotalSeconds) -ForegroundColor Green
try { Autodiagnostico (Join-Path $destino 'AventyaPDF.exe') }
finally {
    $unins = Join-Path $destino 'unins000.exe'
    if (Test-Path $unins) { Start-Process $unins -Wait -ArgumentList @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART') }
    Remove-Item -Recurse -Force $pruebaSalida -ErrorAction SilentlyContinue
}
$quedan = if (Test-Path $destino) { @(Get-ChildItem $destino -Recurse -File).Count } else { 0 }
if ($quedan) { throw "La desinstalación de prueba dejó $quedan archivos en $destino" }
Write-Host '  Desinstalada sin dejar archivos.' -ForegroundColor Green
