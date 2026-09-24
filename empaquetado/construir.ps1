<#
    construir.ps1 — Empaqueta AventyaPDF y crea su instalador (r62)
    ----------------------------------------------------------------
    1. Entorno de compilación en %LOCALAPPDATA%\aventyapdf\build-venv, con las
       MISMAS versiones que el entorno de la aplicación (lo ya probado) más
       PyInstaller. Se crea solo si falta.
    2. PyInstaller → carpeta con AventyaPDF.exe (fuera del proyecto, que es una
       carpeta compartida: %LOCALAPPDATA%\aventyapdf\build-dist).
    3. Tesseract OCR dentro, en <app>\tesseract (preparar_tesseract.py).
    4. Autodiagnóstico del EJECUTABLE ya empaquetado (ventana, archivos, OCR
       con el Tesseract incluido, firma con un certificado de pruebas). Si algo
       falla, no se crea el instalador.
    5. Inno Setup → empaquetado\salida\AventyaPDF-Setup-<versión>.exe

    Uso:
        .\empaquetado\construir.ps1
        .\empaquetado\construir.ps1 -SinInstalador     # solo la carpeta de la app

    Requisitos: el entorno de la aplicación (.\run.ps1 una vez), Tesseract
    instalado (la app lo instala) e Inno Setup 6 (winget install JRSoftware.InnoSetup).
#>
[CmdletBinding()]
param([switch]$SinInstalador)

$ErrorActionPreference = 'Stop'
$Raiz      = Split-Path $PSScriptRoot -Parent
$Base      = Join-Path $env:LOCALAPPDATA 'aventyapdf'
$AppPy     = Join-Path $Base 'venv\Scripts\python.exe'
$BuildVenv = Join-Path $Base 'build-venv'
$BuildPy   = Join-Path $BuildVenv 'Scripts\python.exe'
$Dist      = Join-Path $Base 'build-dist'
$Work      = Join-Path $Base 'build-work'
$App       = Join-Path $Dist 'AventyaPDF'
$Salida    = Join-Path $PSScriptRoot 'salida'

function Paso([string]$t) { Write-Host "`n── $t" -ForegroundColor Cyan }
function Comprobar([string]$que) { if ($LASTEXITCODE -ne 0) { throw "$que falló (código $LASTEXITCODE)." } }

if (-not (Test-Path $AppPy)) { throw "No existe el entorno de la aplicación: ejecuta antes .\run.ps1" }

# ── 1. Entorno de compilación ─────────────────────────────────────────────── #
Paso 'Entorno de compilación'
$congelado = Join-Path $env:TEMP 'aventyapdf-versiones.txt'
& $AppPy -m pip freeze --disable-pip-version-check | Set-Content -Encoding utf8 $congelado
Comprobar 'Leer las versiones del entorno de la aplicación'
if (-not (Test-Path $BuildPy)) {
    $pyBase = & $AppPy -c "import sys; print(sys._base_executable)"
    & $pyBase -m venv $BuildVenv
    Comprobar 'Crear el entorno de compilación'
}
& $BuildPy -m pip install --disable-pip-version-check -q -r $congelado pyinstaller
Comprobar 'Instalar los paquetes de compilación'

# ── 2. PyInstaller ────────────────────────────────────────────────────────── #
$Version = (Select-String -Path (Join-Path $Raiz 'window_menus.py') -Pattern 'APP_VERSION = "(.+?)"').Matches[0].Groups[1].Value
if (-not $Version) { throw 'No se encuentra APP_VERSION en window_menus.py' }
Paso "PyInstaller — AventyaPDF $Version"
$v = ($Version.Split('.') + @('0', '0', '0', '0'))[0..3] -join ', '
@"
VSVersionInfo(
  ffi=FixedFileInfo(filevers=($v), prodvers=($v)),
  kids=[StringFileInfo([StringTable('0C0A04B0', [
    StringStruct('CompanyName', 'Aventya Asesoría Integral SL'),
    StringStruct('LegalCopyright', 'Aventya Asesoría Integral SL · AGPL-3.0'),
    StringStruct('FileDescription', 'AventyaPDF'),
    StringStruct('FileVersion', '$Version'),
    StringStruct('InternalName', 'AventyaPDF'),
    StringStruct('OriginalFilename', 'AventyaPDF.exe'),
    StringStruct('ProductName', 'AventyaPDF'),
    StringStruct('ProductVersion', '$Version')])]),
    VarFileInfo([VarStruct('Translation', [0x0C0A, 1200])])]
)
"@ | Set-Content -Encoding utf8 (Join-Path $PSScriptRoot 'version_info.txt')
$env:AVENTYAPDF_VERSION = $Version
& $BuildPy -m PyInstaller --noconfirm --clean --log-level WARN `
    --distpath $Dist --workpath $Work (Join-Path $PSScriptRoot 'AventyaPDF.spec')
Comprobar 'PyInstaller'

# ── 3. Tesseract dentro ───────────────────────────────────────────────────── #
Paso 'Tesseract OCR incluido'
& $BuildPy (Join-Path $PSScriptRoot 'preparar_tesseract.py') $App
Comprobar 'Preparar Tesseract'

# ── 4. Autodiagnóstico del ejecutable ─────────────────────────────────────── #
Paso 'Autodiagnóstico del ejecutable empaquetado'
$pfx = Join-Path $env:TEMP 'aventyapdf-diagnostico.pfx'
$informe = Join-Path $env:TEMP 'aventyapdf-diagnostico.json'
Remove-Item $informe -ErrorAction SilentlyContinue
Push-Location $Raiz
try { & $BuildPy -c "from create_test_cert import build_test_pfx; open(r'$pfx','wb').write(build_test_pfx(b'1234'))" }
finally { Pop-Location }
Comprobar 'Crear el certificado de pruebas'
$p = Start-Process -FilePath (Join-Path $App 'AventyaPDF.exe') -Wait -PassThru `
        -ArgumentList @('--autodiagnostico', "`"$informe`"", "`"$pfx`"", '1234')
Remove-Item $pfx -ErrorAction SilentlyContinue
if (-not (Test-Path $informe)) { throw "El ejecutable no llegó a escribir el autodiagnóstico (código $($p.ExitCode))." }
$diag = Get-Content $informe -Raw -Encoding utf8 | ConvertFrom-Json
foreach ($c in $diag.comprobaciones) {
    $marca = if ($c.ok) { 'OK   ' } else { 'FALLO' }
    $color = if ($c.ok) { 'Green' } else { 'Red' }
    Write-Host ("  {0} {1} ({2} s)" -f $marca, $c.nombre, $c.segundos) -ForegroundColor $color
    if (-not $c.ok) { Write-Host $c.detalle -ForegroundColor Red }
}
if (-not $diag.ok) { throw 'El autodiagnóstico del ejecutable ha fallado: no se crea el instalador.' }
$mb = [math]::Round((Get-ChildItem $App -Recurse | Measure-Object Length -Sum).Sum / 1MB)
Write-Host "  Aplicación: $App ($mb MB)" -ForegroundColor Green
if ($SinInstalador) { exit 0 }

# ── 5. Instalador ─────────────────────────────────────────────────────────── #
Paso 'Instalador (Inno Setup)'
$iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
          "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
          "$env:ProgramFiles\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw 'Falta Inno Setup 6: winget install JRSoftware.InnoSetup --scope user' }
& $iscc /Qp "/DAppVersion=$Version" "/DDistDir=$App" (Join-Path $PSScriptRoot 'AventyaPDF.iss')
Comprobar 'Inno Setup'
$setup = Join-Path $Salida "AventyaPDF-Setup-$Version.exe"
$mb = [math]::Round((Get-Item $setup).Length / 1MB)
Write-Host "`nInstalador listo: $setup ($mb MB)" -ForegroundColor Green
