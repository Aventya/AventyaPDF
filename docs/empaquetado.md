# Empaquetado e instalador de AventyaPDF

Desde r62 AventyaPDF se distribuye como una aplicación de Windows normal: un
instalador `AventyaPDF-Setup-<versión>.exe` que no necesita Python, ni internet,
ni permisos de administrador. (r102) El OCR es la única excepción: la primera
vez que se usa necesita internet y, si Tesseract no estuviera ya instalado en
el equipo, permiso de administrador una vez — a cambio, el instalador pesa
mucho menos (ver «Qué instala»).

## Qué instala

| | |
| :-- | :-- |
| **Dónde** | `%LOCALAPPDATA%\Programs\AventyaPDF`, solo para el usuario actual (sin administrador). Todo el registro va a `HKEY_CURRENT_USER`. |
| **Programa** | `AventyaPDF.exe` y su carpeta `_internal` (PyInstaller, modo carpeta: arranca rápido). |
| **OCR** | (r102) Tesseract OCR **no** va dentro: `tesseract_ui.ensure_at_startup`/`ensure_languages` lo descargan e instalan solos —con permiso de administrador la primera vez, si hiciera falta— la primera vez que se usa «Reconocer texto», igual que desde el código fuente. |
| **Accesos directos** | Menú Inicio (siempre) y escritorio (casilla del asistente). |
| **«Abrir con»** | AventyaPDF aparece en «Abrir con» de los `.pdf` y en Configuración › Aplicaciones predeterminadas. Windows 11 no deja que un programa se imponga como predeterminado: lo elige el usuario. |
| **Menú contextual** | (r86) Submenú «AventyaPDF» con su icono al pulsar con el botón derecho sobre PDF, imágenes o documentos de Word: **Firmar digitalmente**, **Combinar en un PDF**, **Convertir a PDF**. En Windows 11 sale en el menú **principal** gracias a un paquete MSIX disperso firmado (`menu-contextual\`) con la extensión `AventyaPDFShell.dll`; la primera vez el instalador pide permiso de administrador para que el equipo confíe en su certificado. También está en «Mostrar más opciones» (claves de `HKCU`). Ver `shell\` y la sección [Code] de `AventyaPDF.iss`. |

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

Resultado: `empaquetado\salida\AventyaPDF-Setup-<versión>.exe` (~81 MB desde
r102, sin Tesseract dentro; antes, ~131 MB). La
versión sale de `APP_VERSION` en `window_menus.py`.

Pasos de `construir.ps1`:

1. **Entorno de compilación** `%LOCALAPPDATA%\aventyapdf\build-venv`, con las
   **mismas versiones** de paquetes que el entorno de la app (`pip freeze`), más
   PyInstaller. Así el ejecutable lleva exactamente lo que ya pasó las pruebas.
2. **PyInstaller** con `empaquetado\AventyaPDF.spec`. La carpeta resultante
   (~280 MB desde r102, sin Tesseract dentro; antes, ~430 MB) y los
   intermedios van a `%LOCALAPPDATA%\aventyapdf\build-dist` y `build-work`,
   **fuera del proyecto** (carpeta compartida).
3. **Autodiagnóstico del ejecutable ya empaquetado**
   (`AventyaPDF.exe --autodiagnostico informe.json cert.pfx clave`, ver
   `autodiagnostico.py`): archivos incluidos, ventana, OCR (con el Tesseract
   que ya tenga instalado el equipo que compila — no comprueba la descarga en
   un equipo limpio), exportar a Word, sellado de tiempo y firma (firmar,
   verificar y quitar la última firma con un certificado de pruebas). Si algo
   falla, **no se crea el instalador**. Existe porque una aplicación sin
   consola no enseña sus errores.
4. **Inno Setup 6** con `empaquetado\AventyaPDF.iss`. El icono del instalador
   es el de la app y las imágenes del asistente (`empaquetado\imagenes\*.bmp`,
   una por escala de pantalla) salen del mismo `ICONO.png`: si cambia el
   icono, `python create_app_icon.py` antes de construir (r64).

Herramientas necesarias (una vez): el entorno de la app (`.\run.ps1`),
Tesseract (la app lo instala) e Inno Setup 6
(`winget install JRSoftware.InnoSetup --scope user`, sin administrador).

## Cambios en la aplicación para funcionar empaquetada

* `dependencias.asegurar_o_salir()` no hace nada en el ejecutable
  (`sys.frozen`): los paquetes van dentro y no hay pip.
* `tesseract_setup`/`tesseract_ui`: **sin cambios** respecto al código fuente
  (r102) — mismo mecanismo de instalación bajo demanda en los dos casos, ver
  «Qué instala» arriba.
* Los módulos calculan sus rutas con `__file__`; en el ejecutable apunta a
  `_internal`, así que `vendor\` y `signature_background.pdf` se incluyen ahí con
  el mismo árbol.
* Se excluye el códec de vídeo de OpenCV (~30 MB): no se usa.

## Pendiente

* **Firma de código**: solicitud enviada a SignPath Foundation (código
  abierto, gratuita — ver [CODE_SIGNING_POLICY.md](../CODE_SIGNING_POLICY.md))
  para que el instalador no dispare el aviso de Windows SmartScreen. Mientras
  no esté aprobada y conectada a un sistema de compilación de confianza (los
  runners de GitHub Actions, no un equipo personal — requisito del programa
  gratuito), SmartScreen seguirá avisando («Windows protegió su PC» → «Más
  información» → «Ejecutar de todas formas»).
* **OpenCV (`cv2`, r102) es de lejos lo que más pesa dentro de `_internal`**:
  82 MB en un único `cv2.pyd`, más que PyQt6 (73 MB). Solo se usa para
  enderezar páginas de OCR torcidas (`pdf_ocr.py`: `resize`, `threshold`
  Otsu, `getRotationMatrix2D` + `warpAffine`, `imwrite`) — un uso muy
  concreto para una dependencia tan grande. Al ser un único binario
  precompilado no hay manera de excluir partes con PyInstaller, como sí se
  hizo con el códec de vídeo de FFmpeg (~30 MB, sin usar). Sustituirlo por
  algo más ligero (o implementar el enderezado a mano con numpy/Pillow) es
  un cambio de riesgo real —toca directamente la precisión del OCR, con
  pruebas dedicadas (`test_estima_la_inclinacion`,
  `test_pagina_torcida_se_endereza_y_la_capa_queda_sobre_el_texto`…)— que
  merece su propia sesión, no colarse en una de empaquetado.
* El `AppId` del `.iss` no debe cambiar nunca: es lo que permite actualizar
  encima de una versión anterior. Para publicar una versión nueva, subir
  `APP_VERSION` y volver a ejecutar `construir.ps1`.
