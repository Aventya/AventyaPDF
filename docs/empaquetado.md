# Empaquetado e instalador de AventyaPDF

Desde r62 AventyaPDF se distribuye como una aplicación de Windows normal: un
instalador `AventyaPDF-Setup-<versión>.exe` que no necesita permisos de
administrador.

(r109, petición de Ricardo: «el instalador no lleve partes que se mantengan
fuera de este proyecto») **El instalador solo lleva lo propio** —unos pocos
MB—: el lanzador `AventyaPDF.exe`, el código de la aplicación, la lista de
confianza, los iconos, el menú contextual y el manual. Todo lo de terceros
(Python, los paquetes de Python y las fuentes tipográficas) lo **descarga el
propio instalador al instalar**, de su origen oficial y comprobando el SHA-256
de cada archivo. Por eso **instalar necesita conexión a Internet**. Hasta r108
iba todo dentro de un ejecutable de PyInstaller (instalador de ~82 MB).

## Qué instala

| | |
| :-- | :-- |
| **Dónde** | `%LOCALAPPDATA%\Programs\AventyaPDF`, solo para el usuario actual (sin administrador). Todo el registro va a `HKEY_CURRENT_USER`. |
| **Programa** | `AventyaPDF.exe`: un lanzador de C++ propio (`empaquetado\lanzador\`, ~200 KB, sin dependencias) que arranca `runtime\pythonw.exe app\main.py` con los mismos argumentos y devuelve su código de salida. Conserva el nombre porque lo usan los accesos directos, «Abrir con», el menú contextual y su paquete MSIX. `app\`: el código de la aplicación. |
| **Descargado al instalar** | `runtime\`: Python **embeddable** oficial de python.org (la misma versión que el entorno probado, hoy 3.13.13) y en `runtime\Lib\site-packages` cada paquete de Python en su **versión exacta** probada, como wheel de PyPI descomprimido (un wheel es un zip: no hace falta pip). `app\vendor\fonts\`: Noto Sans/Serif/Sans Mono (repositorio oficial de Noto, a un commit fijo), Noto Emoji (Google Fonts, URL versionada v65) y Fluent UI System Icons (repositorio de Microsoft, a un commit fijo), con sus licencias. En total, ~200 MB de descarga, ~510 MB instalados. |
| **OCR** | (r102) Tesseract OCR **no** va dentro: `tesseract_ui.ensure_at_startup`/`ensure_languages` lo descargan e instalan solos —con permiso de administrador la primera vez, si hiciera falta— la primera vez que se usa «Reconocer texto», igual que desde el código fuente. |
| **Accesos directos** | Menú Inicio (siempre) y escritorio (casilla del asistente). |
| **«Abrir con»** | AventyaPDF aparece en «Abrir con» de los `.pdf` y en Configuración › Aplicaciones predeterminadas. Windows 11 no deja que un programa se imponga como predeterminado: lo elige el usuario. |
| **Menú contextual** | (r86) Submenú «AventyaPDF» con su icono al pulsar con el botón derecho sobre PDF, imágenes o documentos de Word: **Firmar digitalmente**, **Combinar en un PDF**, **Convertir a PDF**. En Windows 11 sale en el menú **principal** gracias a un paquete MSIX disperso firmado (`menu-contextual\`) con la extensión `AventyaPDFShell.dll`; la primera vez el instalador pide permiso de administrador para que el equipo confíe en su certificado. También está en «Mostrar más opciones» (claves de `HKCU`). Ver `shell\` y la sección [Code] de `AventyaPDF.iss`. |

Al terminar de copiar, el instalador precompila el código de Python
(`python -m compileall`) para que el primer arranque no sea lento.

El Python embeddable funciona en modo `._pth` (`runtime\python313._pth`, propio,
sustituye al que trae la descarga): solo ve su propia biblioteca,
`site-packages` y `app\`, e ignora `PYTHONPATH` y los paquetes del usuario, así
que otro Python instalado en el equipo no interfiere.

Al actualizar, `runtime\` y `app\` se borran y se vuelven a descargar enteros
(también el `_internal\` de las versiones con PyInstaller). Si AventyaPDF está
abierto, el instalador pide cerrarlo (`AppMutex`, el mutex de instancia única).

El desinstalador (Configuración › Aplicaciones) quita el programa, lo
descargado, los accesos directos y todas las claves del registro. **No** borra
`%LOCALAPPDATA%\aventyapdf` (configuración, idiomas de OCR descargados y
`errores.log`): son datos del usuario y los comparte con la versión de
desarrollo.

## Cómo se genera

```powershell
.\empaquetado\construir.ps1                     # autodiagnóstico + instalador
.\empaquetado\construir.ps1 -ProbarInstalacion  # además, instalación de prueba real
.\empaquetado\construir.ps1 -SinInstalador      # solo hasta el autodiagnóstico
```

Resultado: `empaquetado\salida\AventyaPDF-Setup-<versión>.exe`. La versión sale
de `APP_VERSION` en `window_menus.py`.

Pasos de `construir.ps1`:

1. **Lanzador** (`empaquetado\lanzador\construir_lanzador.ps1`: Visual C++,
   CRT estático, icono y datos de versión) y **menú contextual**
   (`shell\construir_shell.ps1`), en `%LOCALAPPDATA%\aventyapdf\build-dist\AventyaPDF`
   —lo propio, lo único que empaqueta Inno Setup—, **fuera del proyecto**.
2. **`empaquetado\componentes.py`**, con el Python del entorno de la app y su
   `pip freeze` (lo que ya pasó las pruebas):
   * copia a `app\` los módulos que importa la aplicación (a partir de
     `main.py` y `autodiagnostico.py`) y los recursos propios de `vendor\`;
   * busca en PyPI el wheel de cada paquete para este Windows/Python y toma su
     URL, SHA-256 y tamaño publicados; comprueba que cada fuente descargable es
     **idéntica** a la del repositorio (si no, se para: hay que actualizar el
     archivo o la URL y volver a probar);
   * escribe `empaquetado\componentes.iss` (no se sube: se genera) con una
     entrada `[Files]` por descarga (`external download [extractarchive]`,
     `Hash:` SHA-256);
   * monta en `build-dist\AventyaPDF-completo` una copia idéntica a la
     instalación, con las descargas guardadas en
     `%LOCALAPPDATA%\aventyapdf\build-cache` (solo se bajan una vez).
3. **Autodiagnóstico** de esa copia a través del lanzador
   (`AventyaPDF.exe --autodiagnostico informe.json cert.pfx clave`, ver
   `autodiagnostico.py`): archivos, ventana, OCR (con el Tesseract que ya
   tenga el equipo que compila), exportar a Word/OpenCV, sellado de tiempo,
   acceso al almacén de certificados de Windows y firma (firmar, verificar y
   quitar la última firma con un certificado de pruebas). Si algo falla,
   **no se crea el instalador**.
4. **Inno Setup 6.5 o posterior** con `empaquetado\AventyaPDF.iss`
   (`ArchiveExtraction=full` para descomprimir los zip). El icono del
   instalador es el de la app y las imágenes del asistente
   (`empaquetado\imagenes\*.bmp`) salen del mismo `ICONO.png`: si cambia el
   icono, `python create_app_icon.py` antes de construir (r64).
5. Con **`-ProbarInstalacion`**: compila una variante (`/DPrueba`: otro
   `AppId`, sin accesos directos, registro ni menú contextual), la instala de
   verdad en `%TEMP%` —descargando todo de Internet, como un usuario—, le pasa
   el autodiagnóstico y la desinstala comprobando que no quede nada. Conviene
   hacerlo antes de cada publicación: es lo único que prueba las URL, los
   hashes y la descompresión de Inno Setup.

Herramientas necesarias (una vez): el entorno de la app (`.\run.ps1`),
Tesseract (la app lo instala), Inno Setup 6
(`winget install JRSoftware.InnoSetup --scope user`, sin administrador) y
Visual Studio con C++ y el Windows SDK.

## Cambios en la aplicación para funcionar instalada

* `dependencias.carpeta_instalada()` reconoce la instalación (carpeta con
  `AventyaPDF.exe` y `runtime\` por encima de `app\`); ahí
  `asegurar_o_salir()` no hace nada —el instalador ya puso las versiones
  exactas y su Python no lleva pip— y `open_pdf` busca `MANUAL.pdf` junto al
  lanzador.
* Los módulos calculan sus rutas con `__file__`: en la instalación, `app\`
  tiene el mismo árbol que el proyecto.

## Pendiente

* **Firma de código**: solicitud enviada a SignPath Foundation (código
  abierto, gratuita — ver [CODE_SIGNING_POLICY.md](../CODE_SIGNING_POLICY.md))
  para que el instalador no dispare el aviso de Windows SmartScreen. Mientras
  no esté aprobada y conectada a un sistema de compilación de confianza (los
  runners de GitHub Actions, no un equipo personal — requisito del programa
  gratuito), SmartScreen seguirá avisando («Windows protegió su PC» → «Más
  información» → «Ejecutar de todas formas»).
* **Tamaño instalado** (r109): los paquetes van completos, tal como los publica
  PyPI (~510 MB instalados, frente a ~280 MB con PyInstaller, que dejaba fuera
  lo que no se usaba: por ejemplo el códec de vídeo de OpenCV, ~30 MB, o
  módulos de Qt sin usar). Lo más pesado sigue siendo **OpenCV**, que solo se
  usa para enderezar páginas de OCR torcidas (`pdf_ocr.py`); sustituirlo toca
  la precisión del OCR, con pruebas dedicadas, y merece su propia sesión.
* El `AppId` del `.iss` no debe cambiar nunca: es lo que permite actualizar
  encima de una versión anterior. Para publicar una versión nueva, subir
  `APP_VERSION` y volver a ejecutar `construir.ps1`.
