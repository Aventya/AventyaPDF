# Empaquetado e instalador de AventyaPDF

Desde r62 AventyaPDF se distribuye como una aplicación de Windows normal: un
instalador `AventyaPDF-Setup-<versión>.exe` que no necesita Python, ni internet,
ni permisos de administrador.

## Qué instala

| | |
| :-- | :-- |
| **Dónde** | `%LOCALAPPDATA%\Programs\AventyaPDF`, solo para el usuario actual (sin administrador). Todo el registro va a `HKEY_CURRENT_USER`. |
| **Programa** | `AventyaPDF.exe` y su carpeta `_internal` (PyInstaller, modo carpeta: arranca rápido). |
| **OCR** | Tesseract OCR dentro, en `tesseract\` (motor, las DLL que necesita y los modelos «best» de español, inglés y orientación). El OCR funciona nada más instalar. |
| **Accesos directos** | Menú Inicio (siempre) y escritorio (casilla del asistente). |
| **«Abrir con»** | AventyaPDF aparece en «Abrir con» de los `.pdf` y en Configuración › Aplicaciones predeterminadas. Windows 11 no deja que un programa se imponga como predeterminado: lo elige el usuario. |
| **No incluye** | El menú contextual del Explorador (r55); se puede seguir instalando desde el código con `Install-ContextMenu.ps1`. |

El desinstalador (Configuración › Aplicaciones) quita el programa, los accesos
directos y todas las claves del registro. **No** borra
`%LOCALAPPDATA%\aventyapdf` (configuración, idiomas de OCR descargados y
`errores.log`): son datos del usuario y los comparte con la versión de
desarrollo.

## Cómo se genera

```powershell
.\empaquetado\construir.ps1                 # app + autodiagnóstico + instalador
.\empaquetado\construir.ps1 -SinInstalador  # solo la carpeta de la app
```

Resultado: `empaquetado\salida\AventyaPDF-Setup-<versión>.exe` (~130 MB). La
versión sale de `APP_VERSION` en `window_menus.py`.

Pasos de `construir.ps1`:

1. **Entorno de compilación** `%LOCALAPPDATA%\aventyapdf\build-venv`, con las
   **mismas versiones** de paquetes que el entorno de la app (`pip freeze`), más
   PyInstaller. Así el ejecutable lleva exactamente lo que ya pasó las pruebas.
2. **PyInstaller** con `empaquetado\AventyaPDF.spec`. La carpeta resultante
   (~430 MB) y los intermedios van a `%LOCALAPPDATA%\aventyapdf\build-dist` y
   `build-work`, **fuera del proyecto** (carpeta compartida).
3. **Tesseract** (`preparar_tesseract.py`): copia `tesseract.exe` y **solo las
   DLL que importa** (se siguen sus importaciones con `pefile`; la instalación de
   UB Mannheim trae ~160 MB de DLL de herramientas de entrenamiento que no
   hacen falta), los modelos «best», `pdf.ttf` y la licencia (Apache 2.0).
4. **Autodiagnóstico del ejecutable ya empaquetado**
   (`AventyaPDF.exe --autodiagnostico informe.json cert.pfx clave`, ver
   `autodiagnostico.py`): archivos incluidos, ventana, OCR con el Tesseract
   incluido, exportar a Word, sellado de tiempo y firma (firmar, verificar y
   quitar la última firma con un certificado de pruebas). Si algo falla, **no se
   crea el instalador**. Existe porque una aplicación sin consola no enseña sus
   errores.
5. **Inno Setup 6** con `empaquetado\AventyaPDF.iss`. El icono del instalador
   es el de la app y las imágenes del asistente (`empaquetado\imagenes\*.bmp`,
   una por escala de pantalla) salen del mismo `ICONO.png`: si cambia el
   icono, `python create_app_icon.py` antes de construir (r64).

Herramientas necesarias (una vez): el entorno de la app (`.\run.ps1`),
Tesseract (la app lo instala) e Inno Setup 6
(`winget install JRSoftware.InnoSetup --scope user`, sin administrador).

## Cambios en la aplicación para funcionar empaquetada

* `dependencias.asegurar_o_salir()` no hace nada en el ejecutable
  (`sys.frozen`): los paquetes van dentro y no hay pip.
* `tesseract_setup`: usa primero el Tesseract incluido (`BUNDLED_EXE`, junto al
  ejecutable) y copia sus idiomas a `%LOCALAPPDATA%\aventyapdf\tessdata` en vez
  de descargarlos. Desde el código fuente todo sigue igual.
* Los módulos calculan sus rutas con `__file__`; en el ejecutable apunta a
  `_internal`, así que `vendor\` y `signature_background.pdf` se incluyen ahí con
  el mismo árbol.
* Se excluye el códec de vídeo de OpenCV (~30 MB): no se usa.

## Pendiente

* **Firma de código**: el instalador y el ejecutable no están firmados con un
  certificado de firma de código, así que Windows SmartScreen avisará
  («Windows protegió su PC» → «Más información» → «Ejecutar de todas formas»)
  hasta que se firmen o ganen reputación.
* El `AppId` del `.iss` no debe cambiar nunca: es lo que permite actualizar
  encima de una versión anterior. Para publicar una versión nueva, subir
  `APP_VERSION` y volver a ejecutar `construir.ps1`.
