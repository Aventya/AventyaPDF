<#
    Install-ContextMenu.ps1 — Menú contextual de Windows para AventyaPDF
    ------------------------------------------------------------------
    Añade (o quita, con -Quitar) entradas en el menú contextual del
    Explorador de Windows, solo para el usuario actual (HKEY_CURRENT_USER,
    sin permisos de administrador ni instalador):

      • Sobre uno o varios archivos .pdf seleccionados:
          «Combinar con AventyaPDF» — los une, en el orden en que
          Windows los pasa (normalmente el de selección), en un PDF nuevo
          SIN GUARDAR, abierto en la aplicación para revisarlo y guardarlo
          donde se quiera. No toca ni sobrescribe los archivos originales.

      • Sobre uno o varios archivos de imagen seleccionados (mismas
        extensiones que IMAGE_EXTS en window_document.py: .png .jpg .jpeg
        .bmp .gif .tif .tiff .webp), submenú «AventyaPDF» con:
          «Convertir a un PDF»                       — todas juntas, un PDF.
          «Convertir a varios PDF (uno por imagen)»  — un PDF por imagen.
        Igual que al combinar PDF: cada PDF resultante se abre sin guardar,
        en su propia pestaña, para revisar y guardar donde se quiera.

    Todas las entradas usan MultiSelectModel=Player: Windows invoca el
    comando UNA sola vez con todos los archivos seleccionados como
    argumentos (en vez de un proceso por archivo). El comando reenvía esos
    argumentos a main.py a través de run.ps1 (que ya sabe encontrar/crear el
    entorno virtual), precedidos del indicador que main.procesar_argumentos()
    reconoce (--combinar-pdf, --imagenes-a-pdf, --imagenes-a-pdfs-separados).

    Uso:
        .\Install-ContextMenu.ps1            # instala en el menú contextual real
        .\Install-ContextMenu.ps1 -Quitar    # quita las entradas instaladas

    El parámetro -Raiz (uso interno, pruebas) permite apuntar a una rama de
    registro distinta de la real, para comprobar el resultado sin tocar el
    menú contextual de verdad.
#>

[CmdletBinding()]
param(
    [switch]$Quitar,
    [string]$Raiz = 'HKCU:\Software\Classes\SystemFileAssociations'
)

$ErrorActionPreference = 'Stop'

$ProyectoDir = $PSScriptRoot
$RunPs1      = Join-Path $ProyectoDir 'run.ps1'
# (r57) Icono de la aplicación junto a cada entrada del menú (create_app_icon.py).
$IconoApp    = Join-Path $ProyectoDir 'vendor\icono\aventyapdf.ico'
if (-not $Quitar -and -not (Test-Path $RunPs1)) {
    throw "No se encuentra run.ps1 en $ProyectoDir"
}

$PowerShellExe = (Get-Command powershell.exe).Source

# Mismo conjunto que IMAGE_EXTS en window_document.py — si se amplía allí,
# hay que ampliarlo aquí también.
$ExtensionesImagen = @('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tif', '.tiff', '.webp')


function Comando([string]$Indicador) {
    # %1 lo repite Windows una vez por archivo seleccionado (MultiSelectModel
    # Player), cada uno ya entrecomillado por el propio Explorador.
    return ('"{0}" -NoProfile -ExecutionPolicy Bypass -File "{1}" {2} %1' -f
            $PowerShellExe, $RunPs1, $Indicador)
}

function Quitar-Verbo([string]$Extension, [string]$Verbo) {
    $ruta = Join-Path $Raiz "$Extension\shell\$Verbo"
    if (Test-Path $ruta) {
        Remove-Item -Recurse -Force $ruta
        Write-Host "  Quitado: $Extension -> $Verbo" -ForegroundColor Yellow
    }
}

function Instalar-VerboDirecto([string]$Extension, [string]$Verbo, [string]$Etiqueta, [string]$Indicador) {
    $ruta = Join-Path $Raiz "$Extension\shell\$Verbo"
    New-Item -Path $ruta -Force | Out-Null
    Set-ItemProperty -Path $ruta -Name '(Default)' -Value $Etiqueta
    Set-ItemProperty -Path $ruta -Name 'MultiSelectModel' -Value 'Player'
    Set-ItemProperty -Path $ruta -Name 'Icon' -Value $IconoApp
    $rutaCmd = Join-Path $ruta 'command'
    New-Item -Path $rutaCmd -Force | Out-Null
    Set-ItemProperty -Path $rutaCmd -Name '(Default)' -Value (Comando $Indicador)
    Write-Host "  Instalado: $Extension -> $Etiqueta" -ForegroundColor Cyan
}

function Instalar-Submenu([string]$Extension, [array]$Hijos) {
    $ruta = Join-Path $Raiz "$Extension\shell\AventyaPDF"
    New-Item -Path $ruta -Force | Out-Null
    Set-ItemProperty -Path $ruta -Name '(Default)' -Value 'AventyaPDF'
    Set-ItemProperty -Path $ruta -Name 'MUIVerb' -Value 'AventyaPDF'
    Set-ItemProperty -Path $ruta -Name 'subcommands' -Value ''
    Set-ItemProperty -Path $ruta -Name 'Icon' -Value $IconoApp
    foreach ($hijo in $Hijos) {
        $rutaHijo = Join-Path $ruta "shell\$($hijo.Verbo)"
        New-Item -Path $rutaHijo -Force | Out-Null
        Set-ItemProperty -Path $rutaHijo -Name '(Default)' -Value $hijo.Etiqueta
        Set-ItemProperty -Path $rutaHijo -Name 'MultiSelectModel' -Value 'Player'
        $rutaCmd = Join-Path $rutaHijo 'command'
        New-Item -Path $rutaCmd -Force | Out-Null
        Set-ItemProperty -Path $rutaCmd -Name '(Default)' -Value (Comando $hijo.Indicador)
    }
    Write-Host "  Instalado: $Extension -> AventyaPDF (submenú, $($Hijos.Count) opciones)" -ForegroundColor Cyan
}


if ($Quitar) {
    Write-Host 'Quitando el menú contextual de AventyaPDF…' -ForegroundColor Cyan
    Quitar-Verbo '.pdf' 'AventyaPDF.Combinar'
    foreach ($ext in $ExtensionesImagen) { Quitar-Verbo $ext 'AventyaPDF' }
    Write-Host 'Hecho.' -ForegroundColor Green
}
else {
    Write-Host 'Instalando el menú contextual de AventyaPDF…' -ForegroundColor Cyan
    Instalar-VerboDirecto '.pdf' 'AventyaPDF.Combinar' 'Combinar con AventyaPDF' '--combinar-pdf'
    foreach ($ext in $ExtensionesImagen) {
        Instalar-Submenu $ext @(
            @{ Verbo = '01Combinado'; Etiqueta = 'Convertir a un PDF'; Indicador = '--imagenes-a-pdf' },
            @{ Verbo = '02Separado';  Etiqueta = 'Convertir a varios PDF (uno por imagen)'; Indicador = '--imagenes-a-pdfs-separados' }
        )
    }
    Write-Host 'Hecho. Clic derecho sobre uno o varios PDF, o imágenes, para verlo.' -ForegroundColor Green
}
