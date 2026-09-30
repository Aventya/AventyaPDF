<#
    construir_lanzador.ps1 — Compila AventyaPDF.exe, el lanzador (r109)
    ---------------------------------------------------------------------
    Visual C++ x64, CRT estático (no depende de ningún redistribuible), con el
    icono y los datos de versión. Lo llama empaquetado\construir.ps1:
        .\empaquetado\lanzador\construir_lanzador.ps1 -Version 1.3.0 -Salida <carpeta>
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Version,
    [Parameter(Mandatory)][string]$Salida
)

$ErrorActionPreference = 'Stop'
function Comprobar([string]$que) { if ($LASTEXITCODE -ne 0) { throw "$que falló (código $LASTEXITCODE)." } }

$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path $vswhere)) { throw 'Falta Visual Studio (o Build Tools) con C++.' }
$vs = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vs) { throw 'Falta el componente de C++ de Visual Studio (VC.Tools.x86.x64).' }
$vcvars = Join-Path $vs 'VC\Auxiliary\Build\vcvars64.bat'

New-Item -ItemType Directory -Force $Salida | Out-Null
$trabajo = Join-Path $env:TEMP 'aventyapdf-lanzador'
Remove-Item -Recurse -Force $trabajo -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $trabajo | Out-Null

$coma = (($Version.Split('.') + @('0', '0', '0', '0'))[0..3]) -join ','
$cpp = Join-Path $PSScriptRoot 'AventyaPDF.cpp'
$rc  = Join-Path $PSScriptRoot 'AventyaPDF.rc'
$res = Join-Path $trabajo 'AventyaPDF.res'
$exe = Join-Path $Salida 'AventyaPDF.exe'
$orden = "set `"PATH=$(Split-Path $vswhere);%PATH%`" && `"$vcvars`" >nul && " +
         "rc /nologo /c65001 /dVERSION_COMA=$coma /dVERSION_TEXTO=\`"$Version\`" /fo `"$res`" `"$rc`" && " +
         "cl /nologo /EHsc /O2 /MT /std:c++17 /W3 /DUNICODE /D_UNICODE /Fo`"$trabajo\\`" `"$cpp`" `"$res`" " +
         "/link /SUBSYSTEM:WINDOWS /OUT:`"$exe`" user32.lib"
cmd /c $orden
Comprobar 'Compilar el lanzador AventyaPDF.exe'
Remove-Item -Recurse -Force $trabajo -ErrorAction SilentlyContinue
