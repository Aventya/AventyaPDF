# Publicar AventyaPDF en la Microsoft Store

(r119) La Microsoft Store **firma gratis** con el certificado de Microsoft los
paquetes MSIX que publica: instalada desde la Store, AventyaPDF **no muestra
el aviso de Windows SmartScreen**, se actualiza sola y también se puede
instalar con `winget`. La cuenta de desarrollador es gratuita, también para
empresas (verificado en la documentación de Microsoft, 2026).

El instalador de GitHub (ligero, que descarga los componentes) se mantiene
igual; la Store es un canal más, con un paquete propio.

## Qué lleva el paquete

`empaquetado\construir_store.ps1` (con `store\preparar_store.py`) monta el
paquete MSIX a partir de la copia completa ya probada de la instalación:
lanzador, Python y sus paquetes (recortados y precompilados), fuentes y
código, más:

* **Tesseract OCR dentro** (`tesseract\`, solo las DLL que usa, modelos
  «best» de español, inglés y orientación, su licencia Apache 2.0). Las
  políticas de la Store no permiten que una aplicación instale otros
  programas; la app usa el incluido antes que ninguno
  (`tesseract_setup._incluido`).
* **El manual** y los logotipos de la Store, generados de `ICONO.png`.
* **Manifiesto** (`store\AppxManifest.xml`): «Abrir con» de los `.pdf`, el
  menú contextual de Windows 11 (la misma extensión `AventyaPDFShell.dll`, aquí
  sin certificado propio ni permiso de administrador) y el alias de consola
  `aventyapdf`.

Dentro del paquete (`dependencias.en_paquete_msix()`) la aplicación **no
avisa de actualizaciones de GitHub** —las instala la Store— y no fija su
propia identidad de la barra de tareas (la da el paquete).

Unos 190 MB el paquete, unos 510 MB instalado (Tesseract incluido).

## Pasos (los que tiene que hacer Ricardo están marcados ★)

1. ★ **Crear la cuenta**: entrar en **storedeveloper.microsoft.com** (es la
   única entrada sin cuota de registro) → «Get started for free» → **Company**
   (a nombre de Aventya Asesoría Integral SL) → verificación de identidad con
   DNI y selfie.
2. ★ En **Partner Center › Apps and games › New product › MSIX or PWA app**,
   **reservar el nombre** «AventyaPDF».
3. ★ En el producto, **Product management › Product identity**: copiar
   `Package/Identity/Name`, `Package/Identity/Publisher` y
   `Package/Properties/PublisherDisplayName`, y pasármelos (o ejecutar el paso
   4 con ellos).
4. **Generar el paquete para la Store** (después de `.\empaquetado\construir.ps1`):

   ```powershell
   .\empaquetado\construir_store.ps1 -ParaStore -Name '<Name>' -Publisher '<Publisher>' -PublisherName '<PublisherDisplayName>'
   ```

   Deja `empaquetado\salida\AventyaPDF-<versión>-store.msix` (sin firmar: lo
   firma la Store). Antes conviene la prueba en el propio equipo, que lo firma
   con el certificado del menú contextual, lo instala, le pasa el
   autodiagnóstico desde dentro del paquete y lo desinstala:

   ```powershell
   .\empaquetado\construir_store.ps1 -Probar
   ```

   Opcional, con permiso de administrador: el kit de certificación de
   aplicaciones de Windows (las mismas pruebas técnicas que hace la Store):

   ```powershell
   & "${env:ProgramFiles(x86)}\Windows Kits\10\App Certification Kit\appcert.exe" test -appxpackagepath .\empaquetado\salida\AventyaPDF-<versión>.msix -reportoutputpath $env:TEMP\wack.xml
   ```

5. ★ **Envío (Submission)** en Partner Center:
   * **Pricing and availability**: gratis, todos los mercados (o los que se
     quieran).
   * **Properties**: categoría *Productivity*; política de privacidad:
     `https://github.com/Aventya/AventyaPDF/blob/main/docs/privacidad.md`;
     web y soporte: `https://github.com/Aventya/AventyaPDF`.
   * **Age ratings**: el cuestionario (sin contenido sensible).
   * **Packages**: subir el `.msix`.
   * **Store listings** (español): descripción (la del README), capturas
     (`docs\capturas\*.png`; mínimo una de 1366×768 o más), logotipo.
   * **Restricted capabilities**: explicar `runFullTrust` — *«AventyaPDF es
     una aplicación de escritorio Win32 (Python + Qt) empaquetada como MSIX;
     necesita confianza total para abrir y guardar documentos PDF en
     cualquier carpeta del usuario, usar el almacén de certificados de Windows
     para la firma digital y ejecutar su motor de OCR (Tesseract, incluido en
     el paquete).»*
6. La certificación tarda de horas a pocos días. Para cada versión nueva:
   subir `APP_VERSION`, `construir.ps1`, `construir_store.ps1 -ParaStore …` y
   un envío nuevo con el `.msix`.

## Pruebas

`construir_store.ps1 -Probar` (r119): paquete de 192 MB, instalado en
`C:\Program Files\WindowsApps\Aventya.AventyaPDF_…`, autodiagnóstico 9/9
desde dentro del paquete (`paquete_store: True`, Tesseract el incluido),
desinstalado. El kit de certificación necesita administrador y no se pasó.

Trampa encontrada: `makeappx` rechaza los nombres con corchetes
(«0x8007007b»): python-docx trae una carpeta de plantilla con
`[Content_Types].xml` que no usa (abre `default.docx`); ahora no se
descomprime ni en el instalador ni en el paquete (`componentes._sobrantes`).
