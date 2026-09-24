# Edición y Manipulación de PDF

Este documento explica las capacidades de edición de contenido y manipulación estructural de archivos PDF provistas por el proyecto, centrándose en las clases de utilidades en `utils.py` y las operaciones de página del panel lateral.

## Índice del Documento
1. [Inyección de Anotaciones (utils.py)](#inyección-de-anotaciones-utilspy)
2. [Operaciones de página en el panel lateral](#operaciones-de-página-en-el-panel-lateral)
3. [Edición del contenido real del PDF (pdf_edit.py)](#edición-del-contenido-real-del-pdf-pdf_editpy)
4. [Operaciones Rápidas de Página](#operaciones-rápidas-de-página)
5. [Motor de Compresión](#motor-de-compresión)
6. [Relación con otros Documentos](#relación-con-otros-documentos)

---

## Inyección de Anotaciones (utils.py)

> Desde r23 el texto de estas anotaciones **se escribe sobre la propia página**,
> no en un diálogo: ver `interfaz_grafica.md`. Lo que sigue describe cómo se
> inyecta en el PDF una vez confirmado.

La clase estática [PDFUtils](file:///a:/CARPETA%20IA/RICARDO/AVENTYAPDF/utils.py#L4) agrupa los métodos de inserción de marcas y objetos gráficos en el documento PDF original mediante la API de **PyMuPDF (`fitz`)**:

### 1. Inserción de Texto Libre (rich text)
* **Método**: `add_text_annotation(doc, page_num, rect, text, fontsize, text_color, bold, italic, align, font_css)`
* **Mecanismo**: Inyecta una anotación `FreeText` en modo **rich text** (`add_freetext_annot(..., richtext=True)`). El estilo (negrita, cursiva, familia tipográfica, tamaño y color) se aplica envolviendo el texto en un `<span style="...">`, porque el generador de apariencia de PyMuPDF **ignora** negrita/cursiva cuando se usan los nombres de fuente base-14 (`hebo`, `tiit`, …) — todos colapsan a la fuente regular. El color sólo se respeta cuando va dentro del `<span>` (no en el `/DS`).
* **Familias tipográficas** (r36): **Noto Sans**, **Noto Serif** y **Noto Sans Mono**, incluidas en la app (`vendor/fonts/noto`, licencia OFL). Son la **fuente base** del programa: también las usan la marca de agua, el encabezado, el pie y la numeración Bates (`doc_tools.BASE_FONT`), el editor de campos de formulario y el número de las miniaturas. En la anotación se guarda la familia CSS genérica (`sans-serif`, `serif`, `monospace`). La opción **Documento** se resuelve con `detect_doc_font_css(page)`, que clasifica la fuente dominante de la página en una de las tres.
* **Apariencia con Noto** (`apply_text_appearance`): el generador de texto enriquecido de MuPDF **ignora la familia pedida** y escribe siempre con Charis SIL o Nimbus. Tras cada `annot.update()` (crear, reeditar, mover, redimensionar, cambiar estilo) se sustituye el flujo `/AP /N` por uno propio: el texto repartido con `pdf_edit.wrap` en el ancho del cuadro (margen de 2 pt), con alineación, color, negrita y cursiva, y la Noto incrustada con `page.insert_font` (Type 0, CID = glifo, así que el texto se sigue pudiendo extraer).
* **Tamaño**: cada variante de Noto se incrusta entera (~350 KB comprimida). Al guardar, `doc_tools.bytes_with_subset_fonts` la reduce a los caracteres usados **en una copia** (si se recortase el documento abierto, el siguiente texto con esa fuente reutilizaría el subconjunto y le faltarían letras). No se hace en formularios; el cifrado se conserva.
* **Alineación**: el parámetro `align` (0=izq, 1=centro, 2=der, 3=justificado) se traslada al quadding `/Q`.
* **Callout**: las anotaciones rich text de PyMuPDF añaden siempre una línea de llamada (`/CL`); se elimina con `xref_set_key(xref, "CL", "null")`.
* **Metadatos de estilo**: como `annot.set_info()` **regenera la apariencia desde el texto plano** (destruyendo el rich text), los metadatos se escriben directamente con `xref_set_key` sobre `/T` (tamaño), `/Contents` (texto plano para reedición) y `/Subj` (token compacto `TXT|b..|i..|a..|f..|c..`). `decode_text_style` recupera todo el estilo al reseleccionar.
* **Reedición y cambios de estilo**: `rebuild_text_annotation(...)` reescribe el `/RC` y el `/Q` de una anotación existente preservando los atributos no modificados (leídos del token de estilo).

### 1.b Emojis: fuente Noto Emoji (r40)
* **Fuente**: **Noto Emoji** (monocroma y vectorial, licencia OFL) en `vendor/fonts/noto-emoji`. Se eligió la monocroma en lugar de NotoColorEmoji porque así el emoji se escribe **con el color y la transparencia que elija el usuario**, como cualquier texto; NotoColorEmoji dibuja mapas de bits a todo color, admite transparencia pero no cambiar el color.
* **Índice** (`vendor/emoji/emojis.json`, `create_emoji_index.py`): los 1391 emojis que la fuente sabe dibujar, en el orden oficial de Unicode (emoji-test.txt), con su grupo y sus nombres en español (Unicode CLDR). Solo emojis de **un carácter**: las banderas de países, las combinaciones con ZWJ y los tonos de piel son secuencias y necesitan ligaduras que no se pueden componer escribiendo un glifo suelto.
* **Método**: `emoji_font.add_emoji_annot(doc, page_num, point, text, fontsize, color, opacity)`. La apariencia de la anotación es `q /AGEa gs  r g b rg  BT /AGE <tamaño> Tf 0 <base> Td <glifo> Tj ET Q`, con la fuente incrustada (`insert_font`) y un `/ExtGState` con `ca`/`CA` para la transparencia. Queda **vectorial y sin imágenes**, y al guardar la fuente se recorta a los emojis usados.
* **Caja**: el avance del glifo por el alto de la fuente (ascendente + descendente) al tamaño elegido.
* **Anotación**: un `Stamp` con `/Subj` «EmojiNoto|c#RRGGBB|a0.40» (`style_token` / `parse_style`: al seleccionarlo, el panel recupera color y transparencia), `/T` tamaño, `/Contents` emoji y `/Name /AGEmoji`. **Nunca `set_rect()` ni `update()`**: MuPDF lo sustituiría por un sello «APPROVED» de proporción 3,8:1; el `/Rect` se escribe con `emoji_font.write_rect()`.
* **Buscar**: `emoji_font.search(texto, grupo)` busca en nombre y palabras clave en español e inglés, sin mayúsculas ni tildes.
* **Emojis antiguos**: `EmojiFluent` (Fluent Emoji, r36-r39), `EmojiFont` (Segoe UI Emoji, r13-r35), `EmojiImg` y `EmojiStamp` se siguen viendo y moviendo; al cambiarles el emoji, el tamaño, el color o la transparencia se recrean con la fuente actual.

### 2. Resaltar, subrayar o tachar a mano alzada (Ink Annotations, r59)
* **Método**: `window_document.add_freehand_markup(points, kind, color, opacity, width)`.
* **Cuándo**: la herramienta «Resaltar, subrayar o tachar» (H) marca el **texto real** si el gesto empieza sobre él (holgura de 3 pt, `viewer.MARKUP_TEXT_MARGIN`); si empieza fuera (imagen, dibujo, escaneo sin OCR) dibuja **a mano alzada**. Sustituye al antiguo «Marcador a mano alzada» (modo `HIGHLIGHT`, tecla M), que se eliminó; su icono (`highlight`) pasó a esta herramienta.
* **Anotación**: `Ink` con `/Subj` = `MANO|<tipo>` (`doc_tools.FREEHAND_PREFIX`), para que al seleccionarla el panel recupere el tipo; las `Ink` antiguas sin ese prefijo se tratan como resaltado. El **resaltado** se funde en modo **Multiply** (`set_blendmode`): tiñe la imagen sin taparla (lo negro sigue negro), igual que un resaltado de texto, así que ya no hace falta la opacidad del 45 % del marcador antiguo. Subrayar y tachar son una línea fina; el ondulado es un zigzag que sigue el trazo (`viewer.squiggle`).
* **Grosor**: en puntos PDF, uno por tipo (`viewer.FREEHAND_WIDTHS`: resaltar 12, líneas 2), en «Grosor del trazo» del panel. No depende del zoom.
* **Trazos rectos** (`viewer.straighten_stroke`): un gesto **rápido** (≤ 0,35 s o ≥ 900 px de pantalla por segundo) que no se separa más del 18 % de la recta inicio→fin se convierte en esa recta; uno **lento** solo se endereza si ya es prácticamente recto (≤ 2 pt o 4 %: el temblor del pulso). Si la recta queda a menos de 8° de la horizontal o la vertical, se ajusta al eje. Un gesto rápido pero claramente curvo (un círculo) se respeta.

### 3. Rectángulos de Atención con Esquinas Redondeadas
* **Método**: `add_rectangle_annotation(doc, page_num, rect, color, width, corner_radius)`
* **Radio por defecto**: `corner_radius=6` puntos PDF, que coincide con el `border-radius` de 4-6px del estilo del propio editor.
* **Consistencia visual**: El visor almacena `rect_corner_radius` (por defecto `6`) en el `PDFViewerWidget`. La vista previa mientras se dibuja usa `radius_px = rect_corner_radius * scale_factor` para que el radio en pantalla sea proporcional al zoom. Al confirmar el trazo, se pasa el mismo valor a `add_rectangle_annotation`, garantizando que el PDF generado tenga exactamente las mismas esquinas que la previsualización.
* **Mecanismo PDF (appearance stream)**: El array `Border [H V W]` del estándar PDF se ignora por la mayoría de visores (incluido el render de PyMuPDF), por lo que **no** produce esquinas redondeadas reales. En su lugar, se **reescribe el flujo de apariencia** (`/N` appearance stream) de la anotación `Square` dibujando el contorno con líneas y curvas Bézier:
  * `PDFUtils._rounded_rect_path(x, y, w, h, radius)` genera la trayectoria PDF (operadores `m`/`l`/`c`/`h`) de un rectángulo redondeado en coordenadas nativas del PDF (eje Y hacia arriba). Las esquinas usan el factor de control Bézier `k = 0.5523·r` para aproximar un cuarto de círculo.
  * `PDFUtils.apply_rounded_corners(annot, corner_radius)` lee la apariencia generada (`annot._getAP()`), localiza el operador `re` (rectángulo recto que PyMuPDF dibuja por defecto) y lo sustituye por la trayectoria redondeada mediante `annot._setAP(...)`.
* **Persistencia tras cada `update()`**: PyMuPDF regenera un `re` recto en **cada** llamada a `annot.update()`. Por ello `apply_rounded_corners` debe re-aplicarse después de **crear, mover, redimensionar y cambiar color o grosor** del rectángulo. Esto se hace en `add_rectangle_annotation` (utils.py) y en los manejadores de `main_window.py` (`mouseReleaseEvent` de resize/drag, `_on_rect_color`, `_on_rect_width`), todos comprobando `annot.type[1] == 'Square'`.

### 4. Estampado de Emojis
* Ver **1.b**. El antiguo `add_emoji_stamp` (FreeText con `subject="EmojiStamp"`, usado para ★) se retiró en r13. Las anotaciones `EmojiStamp` existentes se siguen moviendo y redimensionando (recalculando `fontsize` en `/T`).

---

## Operaciones de página en el panel lateral

Desde la revisión r27 de la memoria **no hay ventana de organizar** (`organize_dialog.py` se eliminó). El botón **Operaciones de página** (o Organizar › Organizar páginas en el panel lateral) activa un modo del panel lateral:

* Se abren las **miniaturas** (`sidebar.ThumbnailsPanel`) en modo organizar (`set_organizing`): **arrastrar** una miniatura (o varias seleccionadas) reordena el documento (`move_selection_to` → `MainWindow.move_pages`, con `doc.select`) y **Supr** elimina las seleccionadas (con confirmación).
* Las miniaturas forman una **cuadrícula** que se adapta al ancho del panel: al estirarlo hacia la derecha caben más columnas, ordenadas de izquierda a derecha y luego por filas. El hueco donde cae lo soltado lo calcula la app (`_ThumbList.drop_row`) porque en esa vista Qt no reordena la lista por sí solo.
* **(r51) El destino del arrastre no sale de `dropEvent`** (informado por Ricardo: «al soltar no hace nada»): en Windows, `QDrag.exec()` negocia por OLE, fuera de la cola de eventos de Qt, y ese `dropEvent` no llegaba a dispararse nunca con el panel dentro del `QSplitter`/`QStackedWidget` anidado de la app; las pruebas no lo detectaban porque llamaban a `move_selection_to` directamente, sin pasar por ningún gesto de ratón.
* **(r52, petición de Ricardo: «solución híbrida») La parte visual SÍ es `QDrag.exec()` real** (el fantasma semitransparente de la miniatura y el cursor de «permitido/prohibido» los pinta Windows, con más fidelidad que cualquier cosa hecha a mano), **pero el destino no depende de que Qt dispare `dropEvent`.** `_ThumbList` guarda dónde se pulsó (`mousePressEvent`) y, en cuanto el ratón se mueve más de `QApplication.startDragDistance()` (`mouseMoveEvent`), arranca un `QDrag` con el recorte de la miniatura como fantasma y lo lanza con `exec()` — que bloquea, pero **siempre** devuelve el control al soltar el botón, se haya aceptado el drop o no. Al volver, `_run_drag` lee la posición real del cursor con `QCursor.pos()` (la da el sistema operativo, no depende de Qt) y hace lo mismo que antes de r52: `drop_row()` + `move_selection_to()`. `dropEvent` se ignora a propósito, sin fiarse de que llegue. Solo activo con `organizing=True`; fuera de ese modo el clic se comporta como siempre (selecciona y navega).
* Encima, en la zona de opciones de herramienta, el panel **Operaciones de página** con el recuento de la selección y una fila de **iconos de Fluent UI System Icons** (lo que hace cada uno está en su tooltip): girar a la izquierda, girar a la derecha, duplicar (`duplicate_pages`, con `fullcopy_page` para que las copias sean independientes), eliminar, insertar página en blanco, insertar otro PDF (`insert_pdf_after`) y extraer a un PDF nuevo. Sin selección se usa la página actual.
* Todo se aplica **al momento sobre el documento abierto** y cada acción es un paso de **deshacer**; ya no se trabaja sobre una copia que luego se «aplica». La selección se conserva al reconstruir las miniaturas.
* Se sale con el mismo botón, con Esc, eligiendo otra herramienta, el zoom o la compresión, o cambiando de panel lateral. Si el panel lateral estaba cerrado, se vuelve a cerrar.

---

## Edición del contenido real del PDF (pdf_edit.py)

Todo lo anterior **añade** objetos encima de la página. Esto es lo contrario:
cambiar el texto y las imágenes que **ya forman parte** del PDF, como el «Editar
PDF» de Acrobat. La lógica vive en [pdf_edit.py](../pdf_edit.py) (sin Qt) y la
interacción en [edit_ui.py](../edit_ui.py); se activa con la herramienta
«Editar contenido» (tecla **C**).

### Cómo se quita el texto viejo

No se tapa: se **borra del flujo de contenido**, que es lo único que MuPDF sabe
hacer de verdad, mediante una anotación de redacción sobre la caja de la línea:

```python
page.add_redact_annot(rect, fill=False)          # fill=False: no pinta recuadro
page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE,
                      graphics=fitz.PDF_REDACT_LINE_ART_NONE,
                      text=fitz.PDF_REDACT_TEXT_REMOVE)
```

`IMAGE_NONE` y `LINE_ART_NONE` son imprescindibles: sin ellos la redacción se
lleva por delante el arte vectorial y las imágenes que hay debajo del texto.
MuPDF decide carácter a carácter **por su centro**, así que la caja de una línea
no se come las vecinas aunque se toquen.

* **Trampa**: `apply_redactions()` aplica **todas** las marcas de la página. Las
  que ya trajera el PDF (de otra aplicación; esta ya no tiene herramienta
  propia de redactar) se apartan antes (`_stash_redactions`) y se reponen
  después; si no, editar una palabra ejecutaría sin avisar una redacción
  irreversible.

### Cómo se escribe el texto nuevo: reajustado al cuadro

La unidad es el **párrafo** (el bloque que ya agrupa MuPDF), no la línea. El
texto se reparte con `wrap` en tantas líneas como quepan en el ancho del cuadro
y se escribe con `TextWriter` en la posición de la **primera línea base
original**, con el **interlineado medido** entre las líneas base del párrafo, su
alineación detectada y el ángulo de la propia línea (para que en páginas giradas
quede como las demás). Estirar una esquina del cuadro cambia ese ancho y ese
alto, y el texto se vuelve a repartir.

* **Cuándo un salto de línea es «de reajuste»**: al leer el párrafo hay que
  decidir qué saltos los puso el ancho y cuáles el autor (una lista, un verso,
  una dirección). Hacen falta **dos** señales a la vez: que el párrafo **llene la
  columna** (el bloque de texto más ancho de la página) y que la primera palabra
  de la línea siguiente **no hubiera cabido** al final de esta (se mide con las
  cajas de sus propios caracteres, sin cargar ninguna fuente). Con solo la
  segunda, una lista corta se convertía en un párrafo seguido: su ítem más largo
  define el borde del bloque y parece llegar siempre al margen.
  **(r32)** La primera señal también se da si **todas las líneas menos la última
  están llenas**, aunque el párrafo sea más estrecho que la columna (una caja
  estrecha, una columna lateral o un texto que la propia app ha repartido en un
  cuadro estrecho). Sin esto, al ensanchar el cuadro el texto seguía cortado al
  ancho anterior. Una línea que empieza por viñeta o número («-», «•», «1.»,
  «a)») nunca se une a la anterior. «No cabía» se mide por el borde derecho y
  por el ancho de la línea a la vez, para que valgan la sangría de primera
  línea y el texto centrado.
* **Si cabe o no** se mide con el descendente del **propio párrafo**
  (`last_descent`), no con el de la fuente: la caja de un bloque es el recuadro
  ajustado a sus glifos, más baja que ascendente+descendente, y con el de la
  fuente un párrafo de una sola línea avisaba siempre de que no cabía sin haber
  tocado nada. El cuadro **no crece solo**: se avisa y el usuario lo estira.
* El cuadro nunca puede salirse de la página (`clamp_box`); si no, el texto se
  escribiría donde no se ve ni se puede volver a seleccionar.

* **La fuente incrustada del PDF no se puede usar.** Los subconjuntos que
  generan Word y Acrobat vienen **sin tabla `cmap`**: `fitz.Font(fontbuffer=…)`
  devuelve el glifo 0 para todos los caracteres y la línea saldría **en blanco,
  sin ningún error**. (r40) **La fuente del documento no cambia**: `resolve_font`
  traduce el nombre base del PDF («BCDEEE+Calibri» → Calibri) al archivo de esa
  misma fuente en `%WINDIR%\Fonts`; si no está instalada usa **la más parecida
  del sistema** (sans → Arial, serif → Times New Roman, mono → Courier New) y,
  solo si tampoco está, la Noto correspondiente (la fuente base de la app).
  Negrita y cursiva se conservan. Si a la fuente le faltan glifos se prueban
  otras y, si tampoco, se avisa por nombre de los caracteres. El editor en
  pantalla usa la misma familia (`pdf_edit.family_for`) y la barra secundaria
  dice cuál es.
* Un párrafo con varios estilos se reescribe entero con el del tramo que tenga
  más caracteres (se avisa antes), así que las negritas sueltas dentro de una
  frase se pierden.

### Imágenes: por aparición, no por xref

`Page.replace_image` y `Page.delete_image` actúan sobre el objeto y cambian
**todas** las copias de esa imagen en todo el documento. Para tocar solo la que
señala el usuario se redacta su rectángulo con `PDF_REDACT_IMAGE_REMOVE`, y
mover o sustituir es quitar la aparición y volver a insertarla (queda encima del
resto: el orden de dibujo original no se puede conservar). Se descartan las
entradas sin xref: imágenes en línea (`BI…ID…EI`) y las que MuPDF reconstruye
cuando no puede emparejarlas — un PDF firmado declara ocho así, del sello — que
no se pueden extraer ni sustituir.

### Lo que NO se ofrece como editable

`get_text` y `get_image_info` incluyen la **apariencia de las anotaciones**: el
texto de un FreeText de la herramienta Texto, el valor de un campo de formulario
o el glifo de un emoji. Redactarlos no borraría nada (viven en su `/AP`) y encima
se escribiría un duplicado, así que se apartan comparando por el centro de la
línea. Highlight, Underline o Square sí se dejan pasar: no pintan texto y sus
rectángulos cubren texto real que debe poder editarse.

Detalle completo y el resto de trampas en
[MEMORIA_EVOLUTIVA.md](../MEMORIA_EVOLUTIVA.md) §4, invariantes 31–36.

---

## Operaciones Rápidas de Página

El botón **Operaciones de página** de la barra superior activa el modo de páginas del panel lateral (sección anterior); no usa la barra secundaria.

Los accesos rápidos sobre la página actual están en el menú **Organizar** de [window_menus.py](../window_menus.py):
* **Duplicar página actual (`copy_page()`)**: Clona la página activa insertándola a continuación.
* **Insertar página en blanco (`insert_blank_after()`)**, **Insertar PDF tras la página actual…** y **Añadir PDF al final… (`merge_pdf()`)**.
* **Eliminar / Extraer / Girar páginas…**: diálogos con rango de páginas.

---

## Motor de Compresión

Comprime como Adobe Acrobat («Reducir tamaño del archivo» / «Optimizar PDF») y como iLovePDF («Comprimir PDF»). Toda la lógica está en [pdf_compression.py](../pdf_compression.py), sin Qt. `MainWindow.compress_pdf()` solo pide la ruta, avisa si el PDF está firmado y muestra el informe.

* **Niveles** (combo del panel, nombres de iLovePDF y criterios de imagen de Acrobat):

  | Nivel | Imágenes color/gris | JPEG | Imágenes sin pérdida |
  | :-- | :-- | :-- | :-- |
  | Baja compresión | 150 ppp | calidad 85 | siguen sin pérdida (Flate) |
  | Recomendada (por defecto) | 100 ppp | calidad 70 | pasan a JPEG |
  | Extrema | 75 ppp en A4 | calidad 50 | pasan a JPEG |

* **Reducción de resolución**: cada imagen dibujada en las páginas se mide en todas sus colocaciones (ppp con que se dibuja). Solo se reduce si supera en **1,5 veces** la resolución necesaria, como Acrobat («reducir a X ppp las imágenes por encima de 1,5·X»), y el tamaño nuevo se redondea al alza. Si no hace falta reducirla, solo se recomprime si ahorra al menos un 10 %.
* **Límite de impresión**: **ninguna imagen baja de 75 ppp al imprimir su página ajustada a una hoja DIN A4**, en la orientación que mejor encaje. Una página menor que A4 se amplía al imprimirse y exige más ppp en el PDF (A5: 107 ppp). Las imágenes que ya estaban por debajo no se amplían.
* **Legibilidad del texto** (r36): la app es para documentos que lee una persona. Las imágenes que parecen texto de documento (`looks_like_text`: al menos la mitad de papel claro, algo de tinta oscura y pocos grises intermedios; una foto está llena de medios tonos) **nunca bajan de 150 ppp ni de calidad JPEG 75**, sea cual sea el nivel (`TEXT_MIN_PPI`, `TEXT_MIN_JPEG_QUALITY`). Medido con OCR sobre un escaneo con letra de 6 a 12 pt: con «Extrema» (75 ppp, JPEG 50) solo se reconocía el 44-89 % del texto de 6-10 pt y «Recomendada» fallaba a 6 pt; con el suelo, el 100 % en los tres niveles. Las fotos se siguen reduciendo según el nivel. El informe dice cuántas imágenes con texto se han protegido.
* **Resto de optimizaciones (Acrobat)**: subconjunto de fuentes incrustadas (salvo en formularios), descarte de miniaturas de página y guardado con `garbage=4`, `deflate` con `compression_effort=100`, flujos de objetos (`use_objstms`) y `clean`. Se conserva el cifrado.
* **Capa de texto de OCR** (r35): los formularios con solo texto invisible (`3 Tr`) se compactan con `compact_ocr_text`: posiciones a 0,1 pt, redondeando la posición acumulada porque los `Td` son relativos, y cuerpo a 0,01. Ocupa un ~23 % menos sin cambiar el texto ni su sitio (≤0,04 pt). Como `clean` reescribe los números en coma flotante de precisión simple y anula el ahorro, con capa de OCR se guarda dos veces: limpiando y, tras compactar, sin limpiar. Además `clean` quita la imagen oculta que dejaban los PDF con OCR hechos antes de r35.
* **Por qué no `Document.rewrite_images`**: la función de MuPDF reconstruye los recursos de todos los formularios que recorre y **pierde los `/Pattern` de los grupos con máscara suave**. Estropeaba el fondo de la mosca de las firmas y los emojis de la paleta («cannot find Pattern resource 'P4'»). El reescritor propio solo toca los objetos imagen, en su mismo xref: decodifica con `Pixmap`, escala con MuPDF, codifica y ajusta `/Width`, `/Height`, `/ColorSpace` y el filtro, y escala la `/SMask` igual.
* **No se tocan**: imágenes de 1 bit, máscaras (`/ImageMask`, `/Mask`, `/Matte`), JPX con `SMaskInData`, imágenes en línea y las que solo aparecen en apariencias de anotaciones o firmas.
* **Imágenes dañadas**: si el `/ColorSpace` de una imagen no es válido, como en `Doc2.pdf`, se sustituye por el espacio Device equivalente y la imagen queda reparada. `get_image_info(xrefs=True)` falla con una sola imagen así, por eso se usa `_image_infos`.
* **Red de seguridad**: se pinta el original y el resultado. Si aparecen avisos de MuPDF nuevos, se repite sin tocar imágenes (y, si hace falta, sin recortar fuentes) y el informe lo explica.
* **Resultado**: si la copia no es más pequeña que el original, no se guarda. Si lo es, se escribe de forma atómica y se informa del tamaño antes y después, del porcentaje, de las imágenes reducidas o recomprimidas y del ppp mínimo en A4.

---

## Relación con otros Documentos

Este fichero se relaciona directamente con:
* **[Arquitectura General (arquitectura.md)](arquitectura.md)**: Estructura del motor de procesamiento PyMuPDF.
* **[Interfaz Gráfica y Visor (interfaz_grafica.md)](interfaz_grafica.md)**: Eventos de ratón que desencadenan la inyección de anotaciones en el visor.
