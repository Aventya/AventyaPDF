# Herramientas profesionales (versión 2.0)

Este documento resume las funciones añadidas en la versión 2.0 para acercar
AventyaPDF a Adobe Acrobat Pro. Explica qué hace cada una, qué módulo la
implementa y cómo comprobarla a mano. Los detalles técnicos y las trampas
están en [MEMORIA_EVOLUTIVA.md](../MEMORIA_EVOLUTIVA.md) §4.

## Mapa de funciones

| Área | Función | Dónde | Módulo |
| :-- | :-- | :-- | :-- |
| Archivo | Nuevo PDF en blanco, crear desde imágenes, abrir recientes, arrastrar y soltar, abrir desde el Explorador | Archivo | `window_document`, `window_menus`, `main.py` |
| Archivo | Menú contextual del Explorador de Windows: combinar varios PDF en uno, convertir imágenes a un PDF o a varios (uno por imagen) — sin tener que abrir antes la aplicación | Clic derecho en el Explorador | `Install-ContextMenu.ps1`, `main.procesar_argumentos`, `window_menus.combine_pdfs_from_paths` / `create_separate_pdfs_from_images`, `doc_tools.merge_pdfs` |
| Archivo | Guardar (Ctrl+S) sobre el mismo archivo, aviso de cambios sin guardar | Archivo | `window_document` |
| Archivo | Exportar a imágenes, texto y Word; propiedades del documento | Archivo › Exportar / Propiedades | `window_menus`, `doc_tools`, `dialogs` |
| Edición | Deshacer / rehacer con etiqueta de la acción | Edición, barra superior | `history`, `window_document` |
| Edición | Buscar con resaltado de coincidencias (F3 / Mayús+F3) | Ctrl+F | `window_document`, `viewer` |
| Edición | Seleccionar y copiar texto (r34: cada párrafo se pega en una sola línea, también el texto de OCR) | Arrastrar en modo selección | `viewer`, `doc_tools.word_selection` |
| Ver | Panel lateral: miniaturas, marcadores, comentarios, firmas | F4 / rail izquierdo | `sidebar` |
| Ver | Varios PDF abiertos a la vez, como pestañas: un botón por documento bajo un separador del rail (nombre y ruta al pasar el ratón, «●» con cambios, clic derecho para cerrar); cada uno conserva página, deshacer y formulario XFA | Rail izquierdo (con 2 o más documentos) · Ctrl+Tab / Ctrl+Mayús+Tab | `window_document` (`_sessions`, `switch_document`) + `sidebar.set_documents` |
| Ver | Zoom con Ctrl+rueda, 100 %, ajustar ancho/página, página editable, Ctrl+G | Ver | `window_document`, `main_window` |
| Comentar | Resaltar, subrayar, tachar y ondular texto real y, fuera del texto, a mano alzada con trazos rápidos enderezados (r59) | Herramienta H o clic derecho sobre selección | `viewer`, `window_document` |
| Comentar | Notas adhesivas con aviso al pasar el ratón | Herramienta N | `viewer`, `window_document` |
| Comentar | Rellenar formularios como Acrobat: campos resaltados, edición en el propio campo con Tab, casillas, radios, listas, **botones con JavaScript** (cálculos, validación, avisos, restablecer, enlaces, imprimir, navegar) | Clic en el campo · Ver › Resaltar campos de formulario | `form_ui.FormController` + `pdf_forms` (JavaScript de MuPDF) |
| Comentar | Aplanar anotaciones y formularios | Comentar | `doc_tools.flatten` |
| Organizar | Operaciones de página en el panel lateral: girar, duplicar, eliminar, insertar, extraer y reordenar arrastrando, con deshacer | Organizar | `sidebar`, `main_window._set_pages_mode` |
| Organizar | Girar, extraer, eliminar por rangos; dividir; insertar PDF en posición | Organizar, menú contextual de miniaturas | `window_menus`, `doc_tools` |
| Herramientas | Marca de agua (texto, color, opacidad, ángulo, páginas) | Herramientas | `doc_tools.add_watermark` |
| Herramientas | Encabezado, pie, numeración «Página n de N» y Bates | Herramientas | `doc_tools.add_header_footer` |
| Herramientas | Reconocer texto (OCR) en escaneos, imágenes y texto convertido en dibujo, también en páginas que ya tienen texto | Herramientas | `pdf_ocr.ocr_page`: capa de texto invisible sobre la página original, orientación automática, 400 ppp, contraste, modelos `tessdata_best`. **Tesseract es obligatorio**: `tesseract_setup` / `tesseract_ui` lo comprueban al lanzar (`run.ps1`) y al iniciar la app y lo instalan a la fuerza si falta (winget o el instalador oficial), con los idiomas en `%LOCALAPPDATA%\aventyapdf\tessdata`. |
| Proteger | Cifrado AES-256 con contraseña de apertura y permisos | Proteger | `dialogs.SecurityDialog`, `_write_to` |
| Firmar | Motivo, lugar, contacto, sellado de tiempo (PAdES-B-T), certificación | Firmar › Opciones | `signer_backend`, `dialogs.SignOptionsDialog` |
| Firmar | Firma en segundo plano, sin sobrescribir el original, firmas múltiples | Herramienta de firma | `window_document.SignWorker` |
| Firmar | Validación de firmas (integridad, confianza, modificaciones, sello de tiempo) | Panel Firmas | `signature_validation` |

## Decisiones de diseño

- **Documento siempre en memoria.** Se abre desde bytes y solo se escribe al
  guardar. Así ninguna operación destruye el original y deshacer es trivial:
  restaurar una instantánea.
- **Firmas previas preservadas.** Mientras el documento no se haya modificado,
  firmar parte de los bytes exactos del disco, y pyHanko añade la nueva firma
  de forma incremental. Si hay cambios, la aplicación avisa de que las firmas
  anteriores quedarán invalidadas.
- **Operaciones puras separadas de la interfaz.** `doc_tools`, `history` y
  `signature_validation` no importan Qt, para poder probarlos sin la app.

## Pruebas automáticas (desde 2.0.1)

```powershell
.\run.ps1 -Pruebas
```

Ejecuta `tests/` con `unittest`, sin abrir ventanas (`QT_QPA_PLATFORM=offscreen`)
y sin red:

- `tests/test_nucleo.py` — rangos de páginas, deshacer, girar/extraer/dividir/
  insertar, duplicar la última página, búsqueda y selección de texto, marca de
  agua y encabezados (también en página girada), comentarios,
  formularios y aplanado, imágenes→PDF y exportaciones, cifrado AES-256, y
  **firma PAdES doble e incremental + validación** con un certificado generado
  al vuelo (`create_test_cert.build_test_pfx`).
- `tests/test_interfaz.py` — construye la ventana principal y recorre abrir,
  zoom, navegación, operaciones de página, deshacer/rehacer, marcado, notas,
  búsqueda, panel lateral, cambio de herramienta, guardar y guardar
  con contraseña. Los `QMessageBox` responden «Sí» automáticamente y se
  restaura la configuración del usuario que toca. Desde r20 abre varios
  documentos y recorre las pestañas: estado propio de cada uno (páginas,
  cambios, deshacer), archivo ya abierto, documento nuevo y cierre en cadena.

Lo que no cubren (diálogos modales, impresión, OCR, sellado de tiempo por red,
certificados de Windows) sigue en el plan manual.

## Menú contextual del Explorador de Windows (r55)

`Install-ContextMenu.ps1` añade, solo para el usuario actual (`HKEY_CURRENT_USER`,
sin permisos de administrador ni instalador — igual de reversible que
`run.ps1 -Reinstalar`), entradas en el menú contextual del Explorador:

- Sobre uno o varios **.pdf** seleccionados: **«Combinar con AventyaPDF»**
  — los une, en el orden en que Windows los pasa, en un PDF nuevo **sin
  guardar**, en una pestaña nueva, para revisarlo y guardarlo donde se quiera.
  Con un solo archivo no hace nada (hacen falta al menos dos).
- Sobre una o varias **imágenes** seleccionadas (mismas extensiones que
  `IMAGE_EXTS` de `window_document.py`: png, jpg/jpeg, bmp, gif, tif/tiff,
  webp), submenú **«AventyaPDF»** con:
  - **«Convertir a un PDF»** — todas juntas, como `create_from_images()`.
  - **«Convertir a varios PDF (uno por imagen)»** — un PDF de una página por
    cada imagen, cada uno en su propia pestaña, todos sin guardar.

Ningún archivo original se toca ni se sobrescribe: el resultado siempre queda
sin guardar dentro de la aplicación, igual que «Nuevo PDF en blanco» o «Crear
PDF desde imágenes».

**Mecánica**: cada entrada usa `MultiSelectModel=Player`, para que Windows
invoque el comando **una sola vez** con todos los archivos seleccionados como
argumentos (y no un proceso por archivo). El comando registrado llama a
`run.ps1` (que ya sabe encontrar o crear el entorno virtual) con uno de los
indicadores `--combinar-pdf` / `--imagenes-a-pdf` / `--imagenes-a-pdfs-separados`,
seguido de las rutas; `run.ps1` los reenvía tal cual a `main.py`, que los
interpreta en `procesar_argumentos()` y llama al método correspondiente de
`MainWindow` (los mismos que usaría el menú normal, no hay lógica duplicada).
Sin ninguno de esos indicadores, `procesar_argumentos()` se comporta como
siempre: abre el primer `.pdf` de la lista (el «Abrir con…» de toda la vida).

Instalar o quitar el menú:

```powershell
.\Install-ContextMenu.ps1            # instala
.\Install-ContextMenu.ps1 -Quitar    # quita las entradas
```

## Registro de errores

Desde 2.0.1, `main.py` instala un `sys.excepthook`: cualquier excepción no
controlada se muestra en un diálogo con el detalle y se añade a
`%LOCALAPPDATA%\aventyapdf\errores.log`, en lugar de cerrar la aplicación
(PyQt6 aborta con `qFatal` si no hay gancho). Los cierres a nivel nativo quedan
en `fallos_graves.log` (módulo `faulthandler`). Son los dos archivos que hay que
enviar al informar de un fallo.

## Plan de pruebas

Checklist manual para validar la versión 2.0 tras `.\run.ps1`:

1. **Arranque**: la ventana abre sin trazas en consola; F1 muestra los atajos.
2. **Abrir**: Ctrl+O, arrastrar un PDF a la ventana y `Abrir reciente`. Un PDF
   cifrado pide contraseña; una contraseña errónea vuelve a preguntar.
3. **Navegación**: AvPág/RePág, rueda en el borde, número de página editable,
   Ctrl+G, miniaturas (clic y menú contextual).
4. **Zoom**: Ctrl+rueda, Ctrl+0/1/2, slider; con el panel lateral abierto y
   cerrado en modo «ajustar».
5. **Texto**: arrastrar sobre texto, Ctrl+C y pegar en el Bloc de notas; clic
   derecho → Resaltar. Herramienta H: subrayar y tachar varias líneas.
6. **Escribir sobre la página**: con la herramienta Texto (T), hacer clic y
   escribir **encima del PDF**, sin que se abra ninguna ventana; el cuadro debe
   crecer según se escribe y cambiar tamaño, color, negrita y alineación desde
   la barra secundaria debe verse al momento. Ctrl+Intro confirma (Intro abre
   línea), Esc cancela **de verdad** (no debe limitarse a salir de la
   herramienta) y pulsar en otro sitio confirma sin abrir otro cuadro. Igual con
   la nota (N), que sale en amarillo, y con el doble clic sobre un texto ya
   puesto. Comprobar que un texto largo **no se recorta** al confirmarlo.
6b. **Comentarios**: nota (N), texto multilínea (T), rectángulo, marca a mano
   alzada (H fuera del texto; un trazo rápido debe salir recto),
   emoji; mover, redimensionar, cambiar color; panel Comentarios lista todo y
   al pulsar selecciona la anotación.
7. **Deshacer**: Ctrl+Z/Ctrl+Y sobre cada acción anterior y sobre girar o
   eliminar páginas; el título muestra «●» con cambios sin guardar; cerrar
   pregunta si guardar.
8. **Guardar**: Ctrl+S sobre el archivo abierto (no debe dar error de archivo
   en uso) y reabrir para comprobar que los cambios persisten.
9. **Páginas**: organizar (arrastrar, girar, insertar PDF, extraer), dividir
   cada 2 páginas, eliminar rango «2-3».
10. **Herramientas**: marca de agua a 45°, encabezado/pie con `{n}`/`{total}`
    y Bates; comprobar también en una página girada.
11. **Seguridad**: proteger con contraseña de apertura y permisos, guardar,
    reabrir (pide contraseña); quitar seguridad y guardar.
12. **Formularios**: en un PDF con formulario los campos salen resaltados. Hacer clic en un campo de texto, escribir y pasar con Tab al siguiente; los totales calculados se actualizan. Probar casillas, radios y listas, y pulsar botones: los avisos del documento se muestran, los enlaces piden confirmación, «Restablecer» vacía el formulario y deshacer revierte cada cambio. Pasar el ratón por texto seleccionable muestra el cursor de texto.
13. **Firma**: con `test_certificate.pfx`, firmar con motivo y lugar; firmar
    una segunda vez el resultado sin modificarlo; en el panel Firmas ambas deben
    salir íntegras («identidad no verificada» con el certificado de pruebas).
    Repetir con sello de tiempo activado y con «Certificar documento».
14. **Exportar**: imágenes PNG a 150 ppp, texto, Word y crear PDF desde varias
    imágenes.
15. **OCR**: en un equipo sin Tesseract, `.\run.ps1` (y también la app al iniciar) debe instalarlo, pidiendo permiso de administrador, y descargar español, inglés y osd. Sin internet o denegando el permiso, la app avisa y abre con «Reconocer texto (OCR)» desactivado, y lo reintenta en el siguiente inicio. Con Tesseract, un PDF escaneado debe permitir buscar texto, y elegir otro idioma (p. ej. `cat`) lo descarga antes de reconocer. Con «Todas las páginas», el texto dentro de imágenes de páginas que ya tienen texto también se vuelve buscable, sin duplicar el texto existente. Las páginas escaneadas de lado o boca abajo también se reconocen, y deshacer quita la capa de OCR. (r60) Una página derecha **no** debe salir girada (`OCR.PDF`: la minuta bancaria de prueba: su total y su número de cuenta deben encontrarse con Buscar); repetir el OCR sobre un documento con un OCR anterior malo lo sustituye; una página torcida 2-3° se reconoce y al seleccionar el texto cae sobre las palabras. Una página de escáner enorme (p. ej. un plano) se reconoce sin el error «Overly large image».
16. **Campo de firma de un formulario** (r38): abrir un PDF con un recuadro de
    firma vacío (p. ej. una solicitud de la Administración) y hacer clic en él:
    debe salir **primero el selector de certificado** (r39) y, tras las opciones
    de firma, el sello debe quedar **dentro de ese recuadro**, con un único campo
    de firma. Cancelar el selector no debe firmar. Si el campo ya está firmado,
    la barra de estado lo dice y no vuelve a firmar.
17. **Varios documentos**: abrir tres PDF (Ctrl+O y arrastrando). Con el segundo aparece en el panel lateral, bajo un separador, un botón por documento; al pasar el ratón muestra el nombre y la ruta. Hacer un cambio en uno (título y tooltip con «●»), pasar a otro con su botón o Ctrl+Tab y volver: se conservan página, desplazamiento, cambios y deshacer propios. Abrir otra vez un archivo ya abierto solo cambia a su pestaña. «Nuevo PDF en blanco» añade una pestaña con icono de documento. Con un formulario XFA en una pestaña, cambiar de pestaña y volver lo mantiene relleno. Clic derecho › Cerrar documento pasa a la pestaña contigua; con un solo documento desaparecen las pestañas. Salir con cambios en varios documentos pregunta por cada uno.

18. **Editar contenido** (tecla **C**): cada línea de texto y cada imagen de la página se enmarcan; el texto de las notas, los cuadros de texto y los campos de formulario **no** deben enmarcarse. Clic en un párrafo, reescribirlo y **Ctrl+Intro** (Intro abre línea nueva): el texto viejo desaparece de verdad (búscalo: no debe aparecer) y el nuevo sale con la misma fuente, tamaño, color e interlineado, **repartido en las líneas que hagan falta**, sin estropear recuadros, fondos ni imágenes de debajo. Escribir un texto largo debe marcar el cuadro en **rojo** y decir en la barra secundaria cuántas líneas ocupa y que no cabe; **estirar el tirador de una esquina** hacia abajo o hacia el lado debe reajustar el texto hasta que quepa (y estrecharlo, repartirlo en más líneas). Comprobar que un párrafo de varios renglones se lee como **uno solo** y que una **lista** conserva sus saltos. Arrastrar un tirador fuera de la hoja no debe sacar el texto de la página. Tab pasa al párrafo siguiente y Esc cancela. Cambiar tamaño, color y negrita desde la barra secundaria. Dejar una línea vacía la borra. Probar en una **página girada** y en una con **fondo de color** o tabla. Escribir caracteres raros (漢字) debe avisar en la barra de estado, y un texto muy largo avisar de que se sale. Con **imágenes**: clic la selecciona, arrastrarla y redimensionarla por una esquina (no debe deformarse), clic derecho › Sustituir imagen y › Guardar imagen como, Supr la borra; si la misma imagen está en más sitios el menú lo advierte y solo cambia esa. Deshacer (Ctrl+Z) revierte cada cambio. Comprobar también sobre un PDF con **redacciones pendientes sin aplicar**: editar texto no debe ejecutarlas.
19. **Complementos obligatorios** (r33): en un equipo sin Python, `.\run.ps1`
    debe instalarlo solo (winget o python.org) y crear el entorno. Desinstalar
    un paquete del entorno (p. ej. `pip uninstall pdf2docx`) y abrir la app con
    `.\run.ps1` o directamente con `python main.py`: debe reinstalarlo antes de
    abrir la ventana. Borrar el Python con el que se creó el entorno: el
    siguiente `.\run.ps1` debe recrearlo.
20. **Copiar texto** (r34): en un PDF escaneado con OCR y en uno normal,
    seleccionar varios párrafos y una lista, copiar y pegar en el Bloc de notas.
    Cada párrafo debe salir en una sola línea (sin guiones de corte), con una
    línea en blanco entre párrafos, y cada elemento de la lista en la suya.
21. **Menú contextual del Explorador** (r55): ejecutar `.\Install-ContextMenu.ps1`,
    seleccionar 2 o más PDF en el Explorador y pulsar «Combinar con
    AventyaPDF»: debe abrirse la aplicación con un PDF nuevo sin guardar con todas las
    páginas en orden. Seleccionar varias imágenes y probar «AventyaPDF ›
    Convertir a un PDF» (una sola pestaña con todas) y «› Convertir a varios PDF»
    (una pestaña por imagen). Comprobar que los archivos originales siguen
    intactos. `.\Install-ContextMenu.ps1 -Quitar` debe hacer desaparecer las
    tres entradas del menú contextual.

## Relación de documentos

- [Índice](indice.md)
- [Arquitectura General](arquitectura.md)
- [Firma Digital PAdES](firma_digital.md)
- [Edición y Manipulación de PDF](edicion_pdf.md)
