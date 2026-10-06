---
titulo: Manual de AventyaPDF
subtitulo: Ver, comentar, organizar, proteger, convertir y firmar documentos PDF
version: Versión {version}
indice: Índice
meses: enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre
fecha: {mes} de {anio}
cabecera: Manual de AventyaPDF
consejo: Consejo
importante: Importante
atajos_tecla: Tecla
atajos_accion: Acción
muestra_titulo: Documento de muestra — página {n}
muestra_texto: Este es un documento de muestra creado únicamente para enseñar las herramientas de AventyaPDF en el manual. No contiene ningún dato real ni de ningún cliente.\n\nAventyaPDF es una aplicación de escritorio para Windows que permite ver, comentar, organizar, proteger, convertir y firmar digitalmente documentos PDF.\n\nEste párrafo sirve para probar las herramientas de comentario: resaltar texto, subrayarlo, tacharlo, seleccionarlo y copiarlo, o añadir notas adhesivas junto a él.
buscar: documento
resaltar: herramientas de comentario
texto_anotacion: Texto añadido sobre la página
nota_texto: Revisar este párrafo antes de enviarlo.
formulario_titulo: Solicitud de muestra
campo_nombre: Nombre y apellidos
campo_fecha: Fecha
campo_importe: Importe
casilla: Acepto las condiciones
firmante: Persona de Ejemplo
motivo: Conformidad
lugar: Ciudad
contacto: correo@ejemplo.com
certificado_ejemplo: Certificado de ejemplo
nombre_doc1: Contrato.pdf
nombre_doc2: Factura.pdf
nombre_doc3: Informe.pdf
nombre_formulario: Solicitud.pdf
nombre_firmado: Contrato firmado.pdf
explorador_opciones: Abrir|Abrir con|Compartir
---

# Primeros pasos

## Qué es AventyaPDF

AventyaPDF es una aplicación para Windows que reúne en un solo programa lo que se hace a diario con los documentos PDF: leerlos, comentarlos, rellenar formularios, cambiar su texto, organizar sus páginas, combinarlos, protegerlos con contraseña, reconocer el texto de los escaneos y firmarlos con certificado digital.

Es de libre distribución y su código está publicado en GitHub. No envía tus documentos a ningún sitio: todo se hace en tu equipo.

![ventana] La ventana de AventyaPDF con tres documentos abiertos.

## Instalar y actualizar

El instalador pregunta primero el idioma (propone el de Windows): con ese idioma se instala y se abre AventyaPDF. Durante la instalación se descargan de sus webs oficiales Python, sus componentes y las fuentes de letra, así que hace falta conexión a Internet. Mientras tanto, el instalador va enseñando las herramientas de la aplicación.

Al terminar, AventyaPDF aparece en el menú Inicio (y, si lo marcaste, en el escritorio) y en **Abrir con** de los archivos PDF. Windows no deja que un programa se ponga solo como visor predeterminado: si quieres que los PDF se abran siempre con AventyaPDF, elígelo en **Abrir con › Elegir otra aplicación** y marca «Usar siempre esta aplicación».

Cuando hay una versión nueva, AventyaPDF lo avisa al iniciar. También puedes comprobarlo en **Ayuda › Buscar actualizaciones…**: el instalador nuevo se descarga en tu carpeta Descargas y solo tienes que abrirlo. Tus ajustes, tu certificado y tu idioma se mantienen.

> **Importante:** el reconocimiento de texto (OCR) usa Tesseract OCR, que no va dentro del instalador. AventyaPDF lo descarga e instala la primera vez que lo usas; puede pedir permiso de administrador.

## La ventana

- **Barra de menús**: todas las funciones, ordenadas en Archivo, Edición, Ver, Comentar, Organizar, Herramientas, Proteger, Firmar y Ayuda.
- **Barra de herramientas**: abrir, guardar, imprimir y comprimir; deshacer y rehacer; la página actual; el ajuste del zoom; las herramientas de comentario y de edición; la firma; las operaciones de página y, a la derecha, la lupa para buscar.
- **Panel lateral** (a la izquierda, se abre y se cierra con **F4**): miniaturas de página, marcadores, comentarios y firmas certificadas. Arriba del panel aparecen las opciones de la herramienta que estés usando.
- **Barra de estado** (abajo): mensajes de la aplicación y, a la derecha, el zoom.

## Presentación, ayuda e idioma

Al abrir AventyaPDF por primera vez sale una presentación que resume las funciones. Marca «No volver a mostrar al iniciar» si no quieres verla más; siempre puedes volver a abrirla desde **Ayuda › Presentación de AventyaPDF**.

![presentacion] La presentación de inicio.

En el menú **Ayuda** tienes también este manual (**Ayuda › Manual de AventyaPDF**), la lista de atajos de teclado (**F1**) y el idioma de la aplicación (**Ayuda › Idioma**). AventyaPDF está en español, inglés, francés, italiano, catalán, gallego y euskera; el idioma nuevo se aplica la próxima vez que abras la aplicación.

![idioma] Ayuda › Idioma.

# Abrir, guardar y moverse por el documento

## Abrir documentos

Hay varias formas de abrir documentos:

- **Archivo › Abrir…** (`Ctrl+O`): puedes elegir varios archivos a la vez con `Ctrl` o `Mayús`.
- Arrastrarlos desde el Explorador de Windows a la ventana.
- **Archivo › Abrir reciente**, con los últimos documentos usados.
- Hacer doble clic en un PDF, si AventyaPDF es tu visor de PDF.

Además de PDF, AventyaPDF abre imágenes (PNG, JPG, BMP, GIF, TIFF y WebP) y documentos de Word (.doc y .docx): cada uno se convierte en un PDF nuevo, sin guardar, en su propia pestaña. El original no se toca. Para convertir documentos de Word hace falta tener instalado Microsoft Word o LibreOffice.

Si el PDF está protegido con contraseña, AventyaPDF la pide antes de abrirlo.

## Varios documentos a la vez

Cada documento abierto tiene su pestaña en el panel lateral, debajo de los iconos de los paneles. Al pasar el ratón por encima se ve su nombre y su carpeta, y un punto «●» indica que tiene cambios sin guardar.

![pestanas] Las pestañas de los documentos abiertos, en el panel lateral.

- Haz clic en una pestaña para ir a ese documento, o usa `Ctrl+Tab` y `Ctrl+Mayús+Tab`.
- Arrastra una pestaña arriba o abajo para cambiar el orden.
- Con el botón derecho sobre una pestaña puedes cerrar ese documento (o usa `Ctrl+W`).

Cada documento conserva su página, sus cambios y su historial de deshacer. Si abres un archivo que ya estaba abierto, AventyaPDF solo cambia a su pestaña.

## Moverse por las páginas y el zoom

- `AvPág` y `RePág` pasan de página; `Inicio` y `Fin` van a la primera y a la última. La rueda del ratón también pasa de página al llegar al borde.
- Escribe un número en el cuadro de página de la barra de herramientas, o usa **Ver › Ir a página…** (`Ctrl+G`).
- Haz clic en una miniatura del panel lateral para ir a esa página. El panel de marcadores muestra el índice del documento, si lo tiene.

El zoom está siempre abajo a la derecha: los botones de lupa acercan y alejan, la barra se arrastra y en el cuadro se puede escribir el porcentaje exacto (hasta el 400 %). También funcionan `Ctrl+rueda`, `Ctrl++` y `Ctrl+-`. El botón de ajuste de la barra de herramientas alterna entre ajustar al ancho (`Ctrl+1`), ajustar a la página (`Ctrl+2`) y el tamaño real (`Ctrl+0`).

![zoom] El zoom, en la barra de estado.

## Buscar y copiar texto

Pulsa `Ctrl+F` o la lupa de la barra de herramientas y escribe lo que buscas: las coincidencias se resaltan en la página según escribes y se cuentan («1 de 12»). Las flechas, `F3` y `Mayús+F3` van a la siguiente y a la anterior; `Esc` cierra la búsqueda.

![buscar] Buscar en el documento.

Para copiar, arrastra el ratón sobre el texto con la herramienta de selección y pulsa `Ctrl+C`. Cada párrafo se pega en una sola línea, sin los cortes de línea del PDF; también el texto reconocido con OCR.

## Guardar, imprimir y propiedades

- **Archivo › Guardar** (`Ctrl+S`) guarda sobre el mismo archivo; **Guardar como…** (`Ctrl+Mayús+S`), con otro nombre. El título de la ventana lleva «●» mientras haya cambios sin guardar, y al cerrar se pregunta si quieres guardarlos.
- **Archivo › Imprimir…** (`Ctrl+P`) abre el diálogo de impresión de Windows.
- **Archivo › Propiedades del documento…** (`Ctrl+D`) muestra y permite cambiar el título, el autor, el asunto y las palabras clave, y en la pestaña Información, datos como el número de páginas, el tamaño o si tiene firmas.

![propiedades] Propiedades del documento.

## Deshacer y rehacer

Casi todo lo que haces en un documento se puede deshacer con `Ctrl+Z` y rehacer con `Ctrl+Y`: comentarios, cambios de texto, operaciones de página, marcas de agua, OCR… Cada documento tiene su propio historial.

# Comentar

Las herramientas de comentario están en el menú **Comentar** y en la barra de herramientas. Cada una tiene una letra para elegirla rápido; `V` o `Esc` vuelven a la herramienta de selección. Las opciones de la herramienta (color, tamaño, grosor…) aparecen arriba del panel lateral.

## Añadir texto

Con la herramienta **Añadir texto** (`T`) haz clic en la página (o arrastra un cuadro) y escribe directamente encima, sin ventanas: el cuadro crece según escribes. En el panel lateral eliges el tamaño, el color, la negrita y la cursiva, la alineación y el tipo de letra, y los cambios se ven al momento.

![texto] Texto escrito directamente sobre la página.

`Intro` abre una línea nueva, `Ctrl+Intro` confirma y `Esc` cancela. Hacer clic en otro sitio también confirma. Para cambiar un texto ya puesto, haz doble clic sobre él.

## Notas adhesivas

La **Nota adhesiva** (`N`) deja un comentario junto a la página: haz clic donde quieras dejarla y escribe. En la página se ve un pequeño icono, y el texto aparece al pasar el ratón por encima. El color de la nota se elige en el panel lateral.

![nota] Una nota adhesiva junto al texto.

## Resaltar, subrayar y tachar

Con **Resaltar, subrayar o tachar** (`H`) elige el tipo de marca y su color en el panel lateral y arrastra sobre el texto. Si el texto no se puede seleccionar (una imagen o un escaneo), la marca se dibuja a mano alzada; un trazo rápido sale recto.

![resaltar] Texto resaltado.

> **Consejo:** también puedes seleccionar texto con la herramienta de selección y pulsar el botón derecho para resaltarlo, subrayarlo o tacharlo.

## Rectángulos y emojis

El **Rectángulo** (`R`) remarca una zona de la página con un recuadro de esquinas redondeadas: arrastra para dibujarlo, con el color y el grosor del panel lateral.

![rectangulo] Un rectángulo alrededor del título.

La herramienta **Emoji** (`E`) inserta cualquiera de los más de 1.300 emojis, con buscador y grupos, en el tamaño, el color y la opacidad que quieras: elige uno y haz clic donde irá.

![emoji] Elegir un emoji.

## Mover, cambiar y borrar comentarios

Con la herramienta de selección, haz clic en un comentario para seleccionarlo: se puede mover arrastrándolo, cambiar de tamaño con sus tiradores y borrar con `Supr`. El **Borrador de anotaciones** quita los comentarios con un clic.

El panel **Comentarios** del panel lateral lista todos los comentarios del documento con su página; al pulsar uno, la página va a él y queda seleccionado.

![comentarios] El panel Comentarios.

## Aplanar

**Comentar › Aplanar anotaciones y formularios…** convierte los comentarios y los campos de formulario en parte del contenido de la página: se ven igual, pero ya no se pueden mover ni editar. Es útil antes de enviar una versión definitiva.

# Editar el contenido del PDF

La herramienta **Editar texto e imágenes del PDF** (`C`, en el menú Herramientas) cambia el texto y las imágenes que ya forman parte del documento, no comentarios encima. Al elegirla, cada párrafo se enmarca en azul y cada imagen en verde.

![editar] Los párrafos y las imágenes editables, enmarcados.

**Texto.** Haz clic en un párrafo y escribe: el texto se reparte en las líneas que hagan falta dentro de su cuadro, con la misma fuente, tamaño y color siempre que es posible. En el panel lateral puedes cambiar el tamaño, el color y la negrita o cursiva. Si el texto no cabe, el cuadro se pone rojo: estira una de sus esquinas para hacerlo más grande. `Ctrl+Intro` confirma, `Esc` cancela y `Tab` pasa al párrafo siguiente. Dejar un párrafo vacío lo borra.

**Imágenes.** Haz clic en una imagen para seleccionarla: arrástrala para moverla, estira una esquina para cambiar su tamaño (sin deformarla) o pulsa `Supr` para borrarla. Con el botón derecho puedes sustituirla por otra imagen o guardarla en un archivo.

> **Importante:** si el documento usa una fuente que no está disponible, AventyaPDF usa la más parecida y lo avisa en la barra de estado. Revisa el resultado antes de guardar.

# Rellenar formularios

Los campos de los formularios se resaltan en azul (puedes quitarlo en **Ver › Resaltar campos de formulario**). No hace falta ninguna herramienta especial:

- Haz clic en un campo de texto y escribe; `Tab` pasa al siguiente campo y `Mayús+Tab` al anterior.
- Las casillas y los botones de opción se marcan con un clic; las listas despliegan sus valores.
- Los cálculos, las validaciones y los botones del formulario funcionan como en Adobe Acrobat.

![formulario] Un formulario con sus campos resaltados.

Si el formulario tiene un recuadro de firma vacío, haz clic en él para firmar dentro (lo verás en el capítulo de firma).

# Organizar páginas

## Operaciones de página

El botón **Operaciones de página** de la barra de herramientas (o **Organizar › Organizar páginas en el panel lateral**) abre las miniaturas en modo organizar, con una fila de botones encima.

![organizar] Las operaciones de página en el panel lateral.

- **Reordenar**: arrastra una miniatura a su nueva posición.
- **Seleccionar varias**: con `Ctrl` o `Mayús` al hacer clic. Sin selección, los botones actúan sobre la página actual.
- **Botones**: girar a la izquierda y a la derecha, duplicar, eliminar, insertar una página en blanco, insertar otro PDF, extraer las páginas a un PDF nuevo y recortar.

Todo se aplica al momento y se puede deshacer.

## Recortar una página

El botón **Recortar** dibuja sobre la página un recuadro con tiradores en las esquinas y en los lados: arrastra cada uno hasta el margen que quieras. Los botones del centro del recuadro aplican o cancelan el recorte.

![recortar] Recortar una página.

## El menú Organizar

En el menú **Organizar** están también:

- **Insertar página en blanco**, **Insertar PDF tras la página actual…** y **Añadir PDF al final…**
- **Duplicar página actual**, **Eliminar páginas…** y **Extraer páginas…**, con rangos como «1-3, 5, 8-».
- **Dividir documento…**: guarda el documento en partes de un número fijo de páginas.
- **Girar página a la derecha** (`Ctrl+Mayús+R`), **a la izquierda** (`Ctrl+Mayús+L`) y **Girar páginas…** por rangos.

## Combinar documentos

**Organizar › Combinar PDF…** tiene dos opciones:

- **Combinar abiertos**: junta todos los documentos abiertos, en el orden de sus pestañas y con sus cambios, en un PDF nuevo.
- **Combinar archivos…**: eliges varios archivos (PDF, imágenes o Word, mezclados) y se combinan en orden alfabético de nombre.

![combinar] Organizar › Combinar PDF.

El resultado queda abierto sin guardar; guárdalo con `Ctrl+S`. Los archivos originales no cambian.

# Crear, convertir y exportar

## Crear documentos

- **Archivo › Nuevo PDF en blanco** (`Ctrl+N`) crea un documento con una página vacía.
- **Archivo › Crear PDF desde imágenes…** junta varias imágenes en un PDF, una por página.
- Abrir una imagen o un documento de Word lo convierte a PDF (ver «Abrir documentos»).

## Exportar

En **Archivo › Exportar** puedes sacar el contenido del documento:

- **Páginas como imágenes…**: PNG o JPG, a la resolución que elijas.
- **Texto (.txt)…**: todo el texto del documento.
- **Documento de Word (.docx)…**: un documento editable en Word.
- **Extraer páginas a PDF…**: solo las páginas que indiques.

![exportar] Exportar páginas como imágenes.

## Desde el Explorador de Windows

Sin abrir antes la aplicación, selecciona archivos en el Explorador de Windows y pulsa el botón derecho: en el submenú **AventyaPDF** tienes:

- **Firmar digitalmente** (solo PDF): abre los documentos con la herramienta de firma preparada.
- **Combinar en un PDF** (dos o más archivos): PDF, imágenes y Word, mezclados, en un solo PDF.
- **Convertir a PDF** (imágenes y Word): un PDF por archivo.

![explorador] El submenú AventyaPDF del botón derecho.

En Windows 11, el submenú está en el menú principal del botón derecho; en Windows 10, y en Windows 11 dentro de **Mostrar más opciones**, está en el menú clásico.

> **Consejo:** si el submenú desaparece (por ejemplo, tras una actualización de Windows), usa **Ayuda › Reparar el menú contextual del Explorador…**

# Herramientas

## Marca de agua

**Herramientas › Marca de agua…** escribe un texto sobre las páginas que elijas, con el tamaño, el color, la opacidad y el ángulo que quieras (por ejemplo, «CONFIDENCIAL» en diagonal).

![marca_agua] Marca de agua.

## Encabezado, pie y numeración Bates

**Herramientas › Encabezado, pie y numeración Bates…** añade hasta tres textos en el encabezado y tres en el pie (izquierda, centro y derecha). Puedes usar variables:

- `{n}`: el número de página; `{total}`: el número total de páginas.
- `{fecha}`: la fecha de hoy.
- `{bates}`: un número correlativo Bates, con prefijo, número inicial y cifras.

![encabezado] Encabezado, pie y numeración Bates.

## Reconocer texto (OCR)

**Herramientas › Reconocer texto (OCR)…** convierte en texto seleccionable y buscable el de las páginas escaneadas, las fotos y las imágenes. Elige el idioma del documento, si se reconocen todas las páginas o solo las que no tienen texto, y si se corrige la orientación de cada página.

![ocr] Reconocer texto (OCR).

El texto se añade como una capa invisible: la página no cambia de aspecto, pero ya se puede buscar, seleccionar y copiar. Si eliges un idioma nuevo, AventyaPDF descarga antes sus datos.

## Optimizar y comprimir

El botón **Comprimir PDF** de la barra de herramientas (o **Herramientas › Optimizar y comprimir…**) reduce el tamaño del archivo, sobre todo cuando tiene imágenes. Elige el nivel (alta calidad, buena calidad o máxima reducción) y guarda la copia comprimida; el original no cambia.

![comprimir] Las opciones de compresión.

# Proteger con contraseña

**Proteger › Proteger con contraseña…** cifra el documento con AES de 256 bits:

- **Contraseña para abrir el documento**: sin ella no se puede abrir.
- **Contraseña de permisos**: restringe imprimir, copiar, modificar o comentar, aunque se pueda abrir sin contraseña.

![proteger] Proteger con contraseña.

La protección se aplica al guardar. **Proteger › Quitar seguridad** quita la contraseña y los permisos de un documento que has abierto con su contraseña.

> **Importante:** si olvidas la contraseña para abrir, no hay forma de recuperar el documento. Guárdala en un lugar seguro.

# Firmar

AventyaPDF firma con firma electrónica avanzada PAdES, la que se usa en los documentos oficiales europeos, con certificados cualificados como los de la FNMT o el DNIe.

## El certificado

En **Firmar › Certificado de firma…** eliges con qué certificado se firma:

- **Almacén de Windows**: los certificados instalados en tu equipo, también los de tarjetas y del DNIe. La clave nunca sale del almacén; si hace falta un PIN, lo pide Windows.
- **Archivo .pfx / .p12**: un certificado guardado en un archivo. La contraseña se puede guardar en el Administrador de credenciales de Windows para no escribirla cada vez.

El certificado elegido se recuerda para las firmas siguientes.

## Firmar un documento

Elige la herramienta **Firma** (o **Firmar › Firmar documento (dibujar área)**) y dibuja en la página el recuadro donde irá la firma visible. En el panel lateral se ve el certificado activo y se puede cambiar.

![firmar] La herramienta de firma, con el certificado activo.

Después salen las **opciones de firma**, y por último AventyaPDF pide dónde guardar el documento firmado (propone el mismo nombre terminado en «_firmado»). El original no se modifica.

![opciones_firma] Opciones de firma.

- **Motivo, lugar y contacto**: aparecen en el sello visible y en los datos de la firma. El sello sale en el idioma de la aplicación.
- **Añadir sello de tiempo cualificado (PAdES-B-T)**: una autoridad de sellado de tiempo certifica la fecha y la hora de la firma. Necesita Internet.
- **Certificar documento**: después de firmar, solo se podrán rellenar formularios y añadir más firmas; cualquier otro cambio invalidará la certificación.
- **No volver a preguntar**: firma directamente con estas opciones (se cambia en **Firmar › Opciones de firma…**).

Un documento se puede firmar varias veces: cada firma nueva se añade sin invalidar las anteriores, siempre que no se hayan hecho cambios entre ellas.

## Firmar en el recuadro de un formulario

Si el documento tiene un recuadro de firma vacío (como muchos impresos de la Administración), haz clic en él: AventyaPDF pide el certificado y firma dentro de ese recuadro.

## Firma manuscrita

**Firmar › Insertar firma manuscrita (dibujada o imagen)…**, o la plumilla del panel de firma, abre un lienzo donde dibujar tu firma con el ratón, con trazo de estilográfica y el color y grosor que quieras. También puedes cargar la imagen de tu firma escaneada (se quita el fondo blanco del papel).

![manuscrita] Dibujar la firma manuscrita.

Después haz clic en la página para colocarla, o arrastra un recuadro para darle tamaño. Queda como un comentario más: se mueve, se cambia de tamaño y se borra.

> **Importante:** la firma manuscrita es solo una imagen. No tiene valor de firma electrónica; para eso, firma con certificado.

## Verificar las firmas

El panel **Firmas certificadas** del panel lateral (o **Firmar › Ver las firmas (verificadas)**) comprueba automáticamente cada firma del documento:

- si el documento se ha alterado después de firmarlo;
- si el certificado es de confianza, según el almacén de Windows y la lista de confianza oficial de España (FNMT, DNIe, Colegio de Registradores, Izenpe, ACCV y el resto de prestadores cualificados);
- la fecha declarada, el sello de tiempo y si hay cambios posteriores.

![firmas] El panel Firmas certificadas.

La firma más reciente tiene una papelera que la quita y deja su recuadro vacío para volver a firmar (por ejemplo, con otro certificado). El cambio se aplica al guardar.

# Atajos de teclado

**Ayuda › Atajos de teclado** (`F1`) muestra esta misma lista dentro de la aplicación.

[[atajos]]

# Si algo no funciona

## El OCR no está disponible

Tesseract OCR se instala la primera vez que reconoces texto y necesita Internet (y, a veces, permiso de administrador). Si se denegó el permiso o no había conexión, AventyaPDF vuelve a intentarlo la próxima vez que lo abras.

## No aparece el submenú AventyaPDF en el Explorador

Usa **Ayuda › Reparar el menú contextual del Explorador…**. En Windows 11, para que el submenú esté en el menú principal, el instalador pide una vez permiso de administrador; si se denegó, el submenú está en **Mostrar más opciones**.

## Un documento de Word no se convierte

Hace falta tener instalado Microsoft Word o LibreOffice. Si los dos fallan, AventyaPDF muestra el motivo.

## Una firma sale como «identidad no verificada»

La firma no se ha alterado, pero su certificado no está en el almacén de Windows ni en la lista de confianza de España (por ejemplo, un certificado de pruebas o de otro país). Comprueba con el firmante de dónde es su certificado.

## Informar de un fallo

Si aparece una ventana de «Error inesperado», la aplicación sigue abierta y el detalle se guarda en la carpeta `%LOCALAPPDATA%\aventyapdf` (archivos `errores.log` y `fallos_graves.log`). Envía esos archivos con una descripción de lo que hacías en github.com/Aventya/AventyaPDF/issues.
