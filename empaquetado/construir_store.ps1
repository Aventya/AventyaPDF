<#
    construir_store.ps1 — Paquete MSIX de AventyaPDF para la Microsoft Store (r119)
    ------------------------------------------------------------------------------
    La Microsoft Store firma gratis con el certificado de Microsoft los paquetes
    MSIX que publica, y así no sale el aviso de Windows SmartScreen. El paquete
    lleva todo dentro (store\preparar_store.py): la copia completa ya probada
    que monta construir.ps1, más Tesseract OCR y el manual.

    Antes: .\empaquetado\construir.ps1 (deja build-dist\AventyaPDF-completo).

    Uso:
      # Prueba en este equipo: paquete firmado con el certificado propio del
      # menú contextual (CN=Aventya Asesoria Integral SL), se instala, se le pasa
      # el autodiagnóstico desde dentro del paquete y se desinstala.
      .\empaquetado\construir_store.ps1 -Probar

      # Para subir a Partner Center: con la identidad que da Partner Center
      # (Producto › Identidad del producto). Sin firmar: la Store lo firma.
      .\empaquetado\construir_store.ps1 -ParaStore -Name '<Package/Identity/Name>' `
          -Publisher '<Package/Identity/Publisher>' -PublisherName '<PublisherDisplayName>'

    Resultado: empaquetado\salida\AventyaPDF-<versión>.msix (o -store.msix).
#>
[CmdletBinding()]
param(
    [string]$Name = 'Aventya.AventyaPDF',
    [string]$Publisher = 'CN=Aventya Asesoria Integral SL',
    [string]$PublisherName = 'Aventya Asesoría Integral SL',
    [switch]$ParaStore,
    [switch]$Probar
)

$ErrorActionPreference = 'Stop'
$Raiz     = Split-Path $PSScriptRoot -Parent
$Base     = Join-Path $env:LOCALAPPDATA 'aventyapdf'
$AppPy    = Join-Path $Base 'venv\Scripts\python.exe'
$Completo = Join-Path $Base 'build-dist\AventyaPDF-completo'
$Stage    = Join-Path $Base 'build-dist\AventyaPDF-store'
$Salida   = Join-Path $PSScriptRoot 'salida'

function Paso([string]$t) { Write-Host "`n── $t" -ForegroundColor Cyan }
function Comprobar([string]$que) { if ($LASTEXITCODE -ne 0) { throw "$que falló (código $LASTEXITCODE)." } }

$Version = (Select-String -Path (Join-Path $Raiz 'window_menus.py') -Pattern 'APP_VERSION = "(.+?)"').Matches[0].Groups[1].Value
$lanzador = Join-Path $Completo 'AventyaPDF.exe'
if (-not (Test-Path $lanzador) -or (Get-Item $lanzador).VersionInfo.ProductVersion -ne $Version) {
    throw "Falta la copia completa de la versión ${Version}: ejecuta antes .\empaquetado\construir.ps1"
}
if ($ParaStore -and $Publisher -notmatch '^CN=') { throw 'Publisher tiene que ser el de Partner Center (CN=…).' }

# ── 1. Contenido ──────────────────────────────────────────────────────────── #
Paso "Contenido del paquete — AventyaPDF $Version"
$env:PYTHONIOENCODING = 'utf-8'
& $AppPy (Join-Path $PSScriptRoot 'store\preparar_store.py') --completo $Completo --destino $Stage `
    --version $Version --name $Name --publisher $Publisher --publisher-name $PublisherName
Comprobar 'preparar_store.py'

# ── 2. Paquete ────────────────────────────────────────────────────────────── #
Paso 'MSIX (makeappx)'
$sdk = Get-ChildItem "${env:ProgramFiles(x86)}\Windows Kits\10\bin\10.*\x64\makeappx.exe" -ErrorAction SilentlyContinue |
       Sort-Object FullName -Descending | Select-Object -First 1
if (-not $sdk) { throw 'Falta el Windows SDK (makeappx.exe / signtool.exe).' }
$makeappx = $sdk.FullName
$signtool = Join-Path $sdk.DirectoryName 'signtool.exe'
New-Item -ItemType Directory -Force $Salida | Out-Null
$msix = Join-Path $Salida ("AventyaPDF-$Version" + $(if ($ParaStore) { '-store' } else { '' }) + '.msix')
& $makeappx pack /o /h SHA256 /d $Stage /p $msix | Out-Null
Comprobar 'makeappx'
if (-not $ParaStore) {
    $cert = Get-ChildItem Cert:\CurrentUser\My |
            Where-Object { $_.Subject -eq $Publisher -and $_.HasPrivateKey } |
            Sort-Object NotAfter -Descending | Select-Object -First 1
    if (-not $cert) { throw "No hay certificado «$Publisher» con clave en Cert:\CurrentUser\My (lo crea shell\construir_shell.ps1)." }
    & $signtool sign /q /fd SHA256 /sha1 $cert.Thumbprint $msix
    Comprobar 'signtool'
}
$mb = [math]::Round((Get-Item $msix).Length / 1MB)
Write-Host "  Paquete: $msix ($mb MB)" -ForegroundColor Green
if (-not $Probar) { exit 0 }

# ── 3. Prueba en este equipo ──────────────────────────────────────────────── #
Paso 'Instalación de prueba del paquete'
if ($ParaStore) { throw 'Para probarlo en este equipo, sin -ParaStore (tiene que ir firmado).' }
Get-AppxPackage -Name $Name | Remove-AppxPackage
Add-AppxPackage -Path $msix
$pkg = Get-AppxPackage -Name $Name
Write-Host "  Instalado: $($pkg.PackageFullName)" -ForegroundColor Green
try {
    $pfx = Join-Path $env:TEMP 'aventyapdf-diagnostico.pfx'
    $informe = Join-Path $env:TEMP 'aventyapdf-diagnostico-store.json'
    Remove-Item $informe -ErrorAction SilentlyContinue
    Push-Location $Raiz
    try { & $AppPy -c "from create_test_cert import build_test_pfx; open(r'$pfx','wb').write(build_test_pfx(b'1234'))" }
    finally { Pop-Location }
    # Por su alias: así se ejecuta DENTRO del paquete, con su identidad.
    $alias = Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps\aventyapdf.exe'
    $p = Start-Process -FilePath $alias -Wait -PassThru `
            -ArgumentList @('--autodiagnostico', "`"$informe`"", "`"$pfx`"", '1234')
    Remove-Item $pfx -ErrorAction SilentlyContinue
    if (-not (Test-Path $informe)) { throw "El paquete no llegó a escribir el autodiagnóstico (código $($p.ExitCode))." }
    $diag = Get-Content $informe -Raw -Encoding utf8 | ConvertFrom-Json
    foreach ($c in $diag.comprobaciones) {
        $color = if ($c.ok) { 'Green' } else { 'Red' }
        Write-Host ("  {0} {1} ({2} s)" -f $(if ($c.ok) { 'OK   ' } else { 'FALLO' }), $c.nombre, $c.segundos) -ForegroundColor $color
        if (-not $c.ok -or $c.nombre -like 'Entorno*' -or $c.nombre -like 'OCR*') { Write-Host "        $($c.detalle)" }
    }
    if (-not $diag.ok) { throw 'El autodiagnóstico del paquete ha fallado.' }
}
finally {
    Get-AppxPackage -Name $Name | Remove-AppxPackage
    Write-Host '  Paquete de prueba desinstalado.' -ForegroundColor Green
}
