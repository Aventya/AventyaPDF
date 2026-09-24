<#
    run.ps1 — Lanzador de AventyaPDF
    ------------------------------------------------------------------
    La carpeta del proyecto es compartida por varios equipos, y un entorno
    virtual NO es portable (guarda rutas absolutas del intérprete que lo creó).
    Por eso este script mantiene el entorno FUERA de la carpeta compartida, en
    %LOCALAPPDATA%\aventyapdf\venv, que es local a cada equipo y usuario.

    Todos los complementos son obligatorios y se instalan a la fuerza si faltan
    (r33): Python (winget o el instalador oficial de python.org, para el
    usuario, sin permisos de administrador), los paquetes de requirements.txt
    (dependencias.py, en cada arranque) y Tesseract OCR (tesseract_setup.py).
    Un entorno roto (por ejemplo, porque se desinstaló el Python con el que se
    creó) se vuelve a crear solo.

    Uso:
        .\run.ps1                # arranca (creando el entorno si hace falta)
        .\run.ps1 -Reinstalar    # recrea el entorno desde cero
        .\run.ps1 -Actualizar    # reinstala/actualiza requirements.txt sin borrar el entorno
        .\run.ps1 -Pruebas       # ejecuta las pruebas automáticas (sin abrir ventanas)

    Cualquier otro argumento (r55: lo usa el menú contextual del Explorador,
    ver Install-ContextMenu.ps1) se reenvía tal cual a main.py, por ejemplo:
        .\run.ps1 --combinar-pdf "a.pdf" "b.pdf"
#>

[CmdletBinding()]
param(
    [switch]$Reinstalar,
    [switch]$Actualizar,
    [switch]$Pruebas,
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ArgumentosApp = @()
)

$ErrorActionPreference = 'Stop'

$ProyectoDir  = $PSScriptRoot
$EntradaApp   = Join-Path $ProyectoDir 'main.py'
$Requisitos   = Join-Path $ProyectoDir 'requirements.txt'
$EntornoDir   = Join-Path $env:LOCALAPPDATA 'aventyapdf\venv'
$EntornoPy    = Join-Path $EntornoDir 'Scripts\python.exe'
$Dependencias = Join-Path $ProyectoDir 'dependencias.py'

# Versiones soportadas, de preferente a menos preferente.
# Se excluye 3.14: las ruedas precompiladas de PyMuPDF suelen fallar ahí.
$VersionesOk = @('3.13', '3.12', '3.11')
# Python que se instala si no hay ninguno compatible.
$PythonWinget    = 'Python.Python.3.13'
$PythonInstalador = 'https://www.python.org/ftp/python/3.13.13/python-3.13.13-amd64.exe'


function Buscar-Interprete {
    <#  Devuelve la ruta de un python.exe adecuado del sistema, o $null.
        Prefiere el lanzador `py` (permite elegir versión); si no existe,
        cae al `python` del PATH comprobando que su versión sea soportada. #>

    if (Get-Command py -ErrorAction SilentlyContinue) {
        foreach ($v in $VersionesOk) {
            $ruta = & py "-$v" -c "import sys; print(sys.executable)" 2>$null
            if ($LASTEXITCODE -eq 0 -and $ruta) { return $ruta.Trim() }
        }
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        $mm = & $python.Source -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
        if ($LASTEXITCODE -eq 0 -and $mm -and $VersionesOk -contains $mm.Trim()) {
            return $python.Source
        }
    }

    # Recién instalado, el PATH de esta consola aún no lo ve: rutas habituales.
    foreach ($v in $VersionesOk) {
        $d = $v -replace '\.', ''
        foreach ($ruta in @(
                (Join-Path $env:LOCALAPPDATA "Programs\Python\Python$d\python.exe"),
                (Join-Path $env:ProgramFiles "Python$d\python.exe"))) {
            if (Test-Path $ruta) {
                & $ruta -c "import sys" 2>$null
                if ($LASTEXITCODE -eq 0) { return $ruta }
            }
        }
    }

    return $null
}


function Instalar-Python {
    <#  Instala Python a la fuerza para el usuario actual: winget en silencio y,
        si no hay winget o falla, el instalador oficial de python.org. #>
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host "Instalando Python con winget ($PythonWinget)…" -ForegroundColor Cyan
        & winget install --id $PythonWinget --exact --scope user --silent `
            --accept-package-agreements --accept-source-agreements --disable-interactivity
        if (Buscar-Interprete) { return }
        Write-Host 'winget no dejó un Python utilizable; se prueba el instalador oficial.' -ForegroundColor Yellow
    }
    $exe = Join-Path $env:TEMP 'aventyapdf-python-setup.exe'
    Write-Host "Descargando Python de python.org…" -ForegroundColor Cyan
    Invoke-WebRequest -Uri $PythonInstalador -OutFile $exe -UseBasicParsing
    Write-Host 'Instalando Python…' -ForegroundColor Cyan
    $p = Start-Process -FilePath $exe -Wait -PassThru -ArgumentList @(
        '/quiet', 'InstallAllUsers=0', 'Include_launcher=0', 'PrependPath=1',
        'Include_test=0', 'Include_doc=0')
    Remove-Item $exe -ErrorAction SilentlyContinue
    if ($p.ExitCode -ne 0) { throw "El instalador de Python terminó con el código $($p.ExitCode)." }
}


function Instalar-Dependencias {
    param([string]$Py)

    Write-Host 'Instalando dependencias…' -ForegroundColor Cyan
    & $Py -m pip install --upgrade pip --quiet
    & $Py -m pip install --upgrade -r $Requisitos
    if ($LASTEXITCODE -ne 0) {
        throw "Falló la instalación de dependencias desde $Requisitos"
    }
}


function Entorno-Sano {
    if (-not (Test-Path $EntornoPy)) { return $false }
    & $EntornoPy -c "import sys" 2>$null
    return ($LASTEXITCODE -eq 0)
}


# ── Validaciones ─────────────────────────────────────────────────────────── #

if (-not (Test-Path $EntradaApp))  { throw "No se encuentra main.py en $ProyectoDir" }
if (-not (Test-Path $Requisitos))  { throw "No se encuentra requirements.txt en $ProyectoDir" }

# ── Entorno virtual ──────────────────────────────────────────────────────── #

if ($Reinstalar -and (Test-Path $EntornoDir)) {
    Write-Host "Eliminando el entorno anterior: $EntornoDir" -ForegroundColor Yellow
    Remove-Item -Recurse -Force $EntornoDir
}

if ((Test-Path $EntornoDir) -and -not (Entorno-Sano)) {
    Write-Host "El entorno de $EntornoDir no funciona: se vuelve a crear." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $EntornoDir
}

if (-not (Test-Path $EntornoPy)) {
    $interprete = Buscar-Interprete
    if (-not $interprete) {
        Write-Host ("No hay un Python compatible ({0}): se instala." -f ($VersionesOk -join ', ')) -ForegroundColor Yellow
        Instalar-Python
        $interprete = Buscar-Interprete
    }
    if (-not $interprete) {
        throw ("No se pudo instalar un Python compatible ({0}).`n" -f ($VersionesOk -join ', ')) +
              "Comprueba la conexión a Internet y vuelve a ejecutar."
    }

    $version = (& $interprete -c "import sys; print(sys.version.split()[0])").Trim()
    Write-Host "Creando el entorno con Python $version" -ForegroundColor Cyan
    Write-Host "  Intérprete: $interprete"
    Write-Host "  Entorno:    $EntornoDir"

    & $interprete -m venv $EntornoDir
    if (-not (Test-Path $EntornoPy)) { throw "No se pudo crear el entorno en $EntornoDir" }

    Instalar-Dependencias -Py $EntornoPy
}
elseif ($Actualizar) {
    Instalar-Dependencias -Py $EntornoPy
}

# En cada arranque: lo que falte de requirements.txt (o esté por debajo de la
# versión mínima) se instala a la fuerza. Si otro equipo añade un paquete en la
# carpeta compartida, se instala aquí solo.
& $EntornoPy $Dependencias
if ($LASTEXITCODE -ne 0) {
    throw 'No se pudieron instalar los componentes de Python (detalle arriba).'
}

# ── Pruebas automáticas ──────────────────────────────────────────────────── #

if ($Pruebas) {
    Write-Host 'Ejecutando las pruebas automáticas…' -ForegroundColor Cyan
    # offscreen: la prueba de interfaz construye la ventana sin mostrarla.
    $env:QT_QPA_PLATFORM = 'offscreen'
    & $EntornoPy -m unittest discover -s (Join-Path $ProyectoDir 'tests') -t $ProyectoDir -v
    $codigo = $LASTEXITCODE
    Remove-Item Env:\QT_QPA_PLATFORM -ErrorAction SilentlyContinue
    if ($codigo -eq 0) { Write-Host 'Todas las pruebas han pasado.' -ForegroundColor Green }
    else { Write-Host 'Hay pruebas que fallan (detalle arriba).' -ForegroundColor Red }
    exit $codigo
}

# ── Tesseract OCR (obligatorio) ──────────────────────────────────────────── #

# Se comprueba en cada arranque (no en -Pruebas). Si falta, se instala a la
# fuerza (winget o el instalador oficial, con permiso de administrador) junto
# con los idiomas español, inglés y osd, y se prueba el OCR. Si no se puede,
# la aplicación arranca con el OCR desactivado y lo vuelve a intentar ella.
Write-Host 'Comprobando Tesseract OCR…' -ForegroundColor Cyan
& $EntornoPy (Join-Path $ProyectoDir 'tesseract_setup.py')
if ($LASTEXITCODE -ne 0) {
    Write-Host 'No se pudo preparar Tesseract OCR (detalle arriba). La aplicación arrancará con el OCR desactivado.' -ForegroundColor Yellow
}

# ── Arranque ─────────────────────────────────────────────────────────────── #

# Se usa python.exe y no pythonw.exe a propósito: la consola es el único canal
# donde aparecen los errores de firma (signer_backend imprime el traceback) y
# los fallos silenciados por los `except Exception: pass` del visor.
Write-Host 'Iniciando AventyaPDF…' -ForegroundColor Green
& $EntornoPy $EntradaApp @ArgumentosApp
exit $LASTEXITCODE
