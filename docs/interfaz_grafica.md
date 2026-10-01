# Interfaz Gráfica y Visor Interactivo

Este documento describe detalladamente el diseño, componentes y lógica interactiva de la interfaz de usuario de **AventyaPDF**, implementada a través de `main.py` y `main_window.py`.


> **Presentación inicial (r70).** Al abrir la aplicación sale una ventana sin
> marco con el diseño de la maqueta `popup_temp.png` (degradado turquesa y
> salmón, icono, nombre y barra con la plumilla) que va explicando las
> características en 11 pasos: avanza sola cada 7 segundos (se detiene con el
> ratón encima) y se recorre con Anterior / Siguiente o con ← →. La casilla «No
> volver a mostrar al iniciar» la desactiva; Ayuda › «Presentación de
> AventyaPDF» la vuelve a abrir y permite reactivarla (`presentacion.py`).

## Índice del Documento
1. [Inicialización y Estilos (main.py)](#inicialización-y-estilos-mainpy)
2. [Estructura de la Ventana Principal (MainWindow)](#estructura-de-la-ventana-principal-mainwindow)
3. [El Visor Interactivo (PDFViewerWidget)](#el-visor-interactivo-pdfviewerwidget)
4. [Control de Zoom](#control-de-zoom)
5. [Gestión de Eventos y Estados](#gestión-de-eventos-y-estados)
6. [Relación con otros Documentos](#relación-con-otros-documentos)

---

## Inicialización y Estilos (main.py)

El archivo [main.py](file:///a:/CARPETA%20IA/RICARDO/AVENTYAPDF/main.py) sirve como punto de entrada de la aplicación. Configura la aplicación PyQt6 utilizando el estilo "Fusion" de Qt y carga una hoja de estilos CSS personalizada (`STYLESHEET`).

### Características del Diseño Visual (CSS)
* **Estética Moderna (Windows 11 / Acrobat)**: Paleta de colores armoniosa, con fondos grises claros (`#F3F3F3`) para el área principal y blanco puro (`#FFFFFF`) para la barra de herramientas principal.
* **Tipografía**: los textos de la ventana usan `Segoe UI Variable` / `Segoe UI`, salvo el editor de campos de formulario y el número de las miniaturas, que usan la fuente base de la app (r40). El texto que **añade** la app al PDF usa **Noto Sans, Noto Serif y Noto Sans Mono** (`vendor/fonts/noto`); al **editar** un texto que ya está en el documento se respeta su fuente (ver `edicion_pdf.md`).
* **Iconografía**: **solo Fluent UI System Icons** (Microsoft, MIT; r36) (Microsoft, MIT), variante Regular, incluida en `vendor/fonts/fluent-icons` y registrada al crear la ventana (`icons.load_fonts`). `icons.ICONS` traduce cada clave de la app («open», «rotate_left»…) al nombre del icono y `icons.glyph()` saca el código de `FluentSystemIcons-Regular.json` (tamaño de diseño 20 px). El diccionario `_G` de `main_window.py` se construye desde ahí. Los botones de icono usan letra de 20 px (18 px los `#opt_btn` sueltos dentro de un panel de herramienta, como la alineación de Texto).
* **Icono de la aplicación** (r57, nuevo en r64): `vendor/icono/aventyapdf.ico` (generado desde `ICONO.png` con `create_app_icon.py`, 14 tamaños de 16 a 256 px, con el margen de Windows 11 desde 24 px y enfoque suave hasta 48 px). «Ayuda › Acerca de AventyaPDF» lo muestra a 64 px, igual que **«Ayuda › Buscar actualizaciones…»** (petición de Ricardo; `check_updates` en `window_menus.py`, lógica en `actualizaciones.py`): pregunta a la API de GitHub por la última versión estable (`releases/latest`, que no devuelve las versiones previas), la compara con `APP_VERSION` y muestra el **enlace directo al instalador** que va adjunto a esa publicación (con «Descargar ahora» si es más nueva; si ya es la última, lo dice y deja el enlace igualmente). El enlace no está escrito en el programa: sale de la publicación más reciente en cada consulta. Sin conexión, lo explica y enlaza a la página de versiones. **Aviso automático al iniciar** (petición de Ricardo): `main.py` llama a `start_update_check()`, que a los 4 s consulta GitHub en un hilo aparte (`_UpdateNotifier`, señal `found` hacia el hilo de la interfaz) sin frenar el arranque. Solo avisa si hay una versión más nueva (sin conexión o al día, calla), con la misma ventana titulada «Actualización disponible», botones «Descargar ahora»/«Ahora no» y la casilla «No volver a avisar de esta versión» (`updates/skip_version`; una versión posterior vuelve a avisar). Si hay otra ventana modal abierta (la presentación inicial, un diálogo), espera a que se cierre. Se desactiva con «Ayuda › Avisar de actualizaciones al iniciar» (marcable, activada de entrada; `updates/check_on_start`). Lo usan la ventana y los diálogos (`QApplication.setWindowIcon`), la barra de tareas (identidad propia con `SetCurrentProcessExplicitAppUserModelID`, para no aparecer como Python) y las entradas del menú contextual del Explorador.
* **Interactividad Visual**: Botones con transiciones suaves, efectos hover de realce, y bordes redondeados estándar de 4-6px. El visor utiliza un área de scroll con fondo gris azulado oscuro (`#D0D4D8`) para resaltar el lienzo blanco del PDF.

---

## Estructura de la Ventana Principal (MainWindow)

La clase [MainWindow](file:///a:/CARPETA%20IA/RICARDO/AVENTYAPDF/main_window.py#L517) hereda de `QMainWindow` y orquesta la UI en tres secciones principales apiladas verticalmente mediante `QVBoxLayout`:

1. **Barra de Herramientas Superior (`_build_topbar()`)**:
   * Operaciones de archivo (Abrir, Guardar, Imprimir).
   * Panel de compresión (alternable).
   * Navegación de páginas (Anterior, Siguiente e indicador actual: campo editable de hasta **4 dígitos**, texto alineado a la **derecha**, r53).
   * Herramientas de Zoom (Zoom 100% y Ajuste de pantalla).
   * Herramientas exclusivas de marcado (Texto, Resaltador, Rectángulo, Emoji, Borrador).
   * Activadores de Firma PAdES y panel de edición de páginas.

> **Escribir nunca abre una ventana** (r23). Todo el texto que acaba dentro
> del PDF se teclea sobre la propia página con `inplace_editor.InPlaceEditor`:
> la herramienta Texto, la nota adhesiva, la edición de una anotación (doble
> clic) y «Editar contenido». El cuadro sale donde se hace clic, con el tipo,
> tamaño, color y alineación que tendrá el texto, y **crece según se escribe**.
> Intro abre línea, **Ctrl+Intro** confirma, Esc cancela, Tab pasa al siguiente,
> y pulsar en otro sitio de la página también confirma. Dos cosas no obvias: el
> `QShortcut` de Esc de la ventana se queda la tecla antes que el editor (lo
> cancela `_on_escape`), y en `QPlainTextEdit` el alto de `documentSize()` viene
> en **líneas**, no en píxeles. Ver MEMORIA_EVOLUTIVA.md §4, invariantes 41-43.

2. **Opciones de cada herramienta: todas en el panel lateral** (r26; r74/r75 —petición de Ricardo— se retiró la barra secundaria `_opt_row`, que hasta entonces reservaban Firma y Comprimir):
   * **Zoom, Texto, Nota, Resaltar/subrayar/tachar, Marcador, Rectángulo, Emoji, Editar contenido, (r74) Firma y (r75) Comprimir** ponen sus opciones **arriba del panel lateral** (`_build_side_tool_panels()`, `SidePanel.tools`), en el mismo `QVBoxLayout` que `SidePanel.stack` (miniaturas/marcadores/comentarios/firmas): **lo empujan hacia abajo** (r26; r46 probó a superponerlas en vez de empujar, pero r50 —petición de Ricardo: la herramienta y lo que ya se veía en el panel deben estar disponibles a la vez— volvió al empuje; con scroll, lo que se veía antes sigue alcanzable). Cada panel es un título y filas de **«etiqueta explícita · control»** en **una sola línea** («Tamaño de letra», «Color del texto», «Negrita y cursiva», «Grosor del trazo»…), más una línea de ayuda. Sin iconos indicadores sueltos. Si el panel lateral estaba cerrado, se abre la columna solo con las opciones. (r72) Siempre **en la parte superior** de la columna, nunca centradas, aunque no haya panel debajo.
   * **(r74) Firma**: primero el certificado seleccionado (`_sign_cert_lbl`, en rojo/verde según haya uno o no; (r76) con ajuste de línea, porque el nombre de un certificado real del almacén de Windows puede ser mucho más largo que los de prueba); debajo, **solo dos iconos** — elegir un certificado nuevo (`_change_cert`, icono del certificado digital, antes «cambiar»+«olvidar») y firma manuscrita (`_btn_handsign`). El botón «olvidar el certificado recordado» se retiró: para cambiar de certificado siempre se usa el selector completo. (r74) **Los iconos de «Firma» (botón de la barra principal, `_tool_btns["SIGN"]`) y de «firma manuscrita» (`_btn_handsign`) están intercambiados** entre sí (`"handsign"`/`"sign"` en `icons.ICONS`), y la herramienta ya no se llama «Firma digital PAdES» sino **«Firma»**. **(Petición de Ricardo) Disposición más visual**: arriba, un **aviso enmarcado** (`QLabel#side_notice`, fondo `#E5F1FB` y borde `#C7E0F4`, como el aviso del documento) con «Antes de firmar digitalmente, dibuja en la página el área donde irá la firma.», para que se lea como aviso y no como control; debajo, **dos filas con el texto a la izquierda y su botón a la derecha**, los dos botones en la misma columna: el certificado seleccionado + el botón para cambiarlo, y «Firma manuscrita» + `_btn_handsign` (la etiqueta es corta para caber en una línea con `COLUMN_MIN`; lo de dibujarla o cargar la imagen va en el tooltip). La línea de ayuda final «Dibuja el área donde irá la firma» desaparece: la sustituye el aviso.
   * **(r77, petición de Ricardo) La pestaña del panel lateral se llama «Firmas Certificadas»** (antes «Firmas», en `SidePanel.PANELS` y en el título de `SignaturesPanel`, `sidebar._panel_header`) y usa el icono del certificado (`"opt_cert"`; en r76 había pasado a la estilográfica de Firma, pero Ricardo pidió el del certificado). **Se abre sola** en cuanto se abre un PDF con alguna firma dentro: a diferencia de «thumbs» (que solo se abre si el panel lateral estaba cerrado), `_set_document` la abre **siempre**, aunque el panel ya mostrara otra cosa (`doc_tools.signed_count(doc)`).
   * **(r75; r77 petición de Ricardo: «sigue siendo un caos», con selectores circulares y frases cortas) Comprimir**: tres `QRadioButton` (`_compress_level_btns`, estilo `#side_radio`, `QButtonGroup` exclusivo — sustituyen al `QComboBox` r72 y a los botones de texto r76) con una frase corta cada uno («Buena calidad, imágenes 100ppp», con el ppp real de `Level.color_ppi`); sin la palabra «Nivel» ni una línea de descripción aparte. Debajo, la acción es la frase **«Guardar copia comprimida»** seguida del icono de la herramienta (`compress_pdf`, mismo icono que «Comprimir PDF» en la barra principal: `"compress"` → `folder_zip`); sin la línea de ayuda final que hubo en r75/r76.
   * **(r46; r73 petición de Ricardo: quitar el aviso de firma) El aviso superior** (`_build_banner()`) ya solo avisa de «con formulario / cifrado»: el de «documento firmado» se quitó del visor y vive solo en el panel lateral de Firmas Certificadas (`_set_document()` lo abre siempre que el documento está firmado, r77). Va en la misma columna que el visor, encima de él: solo desplaza la página, nunca el panel lateral. No queda ya por encima del `QSplitter` que reparte panel lateral y visor, salvo la barra superior fija (`#topbar`, siempre presente, 46 px: controles de 32 px más 7 px arriba y abajo; todos los botones y campos de la aplicación miden 32 px de alto, y los botones de icono 32×32, ver `icons.CONTROL`); solo las opciones **dentro** del panel lateral lo desplazan, y a propósito (r50).
   * **(r78, petición de Ricardo: «la barra secundaria debe desaparecer… en su lugar, al pulsar el botón de búsqueda, este se oculta y en su lugar aparece toda la herramienta de búsqueda… y si se pulsa la "X" vuelve a la posición original») La búsqueda ya no es una barra aparte que empuja el visor** (como hasta r46/r48): `_build_find_bar()` (`window_menus.py`) construye ahora un `QWidget` sin borde propio que vive **dentro de la barra principal** (`_topbar`), en el mismo sitio que el botón de la lupa (`_btn_find`). `show_find()` oculta `_btn_find` y muestra el widget de búsqueda (contador, campo, anterior/siguiente, cerrar); `hide_find()` hace lo contrario. Nunca se ven los dos a la vez, y como la barra principal tiene altura fija, activar o cerrar la búsqueda **no desplaza ni el visor ni el panel lateral**. (r79, petición de Ricardo: «debe tener el mismo color que el resto de la barra... o ser transparente») La regla general `QWidget { background-color: #F3F3F3 }` (gris) le pintaba un fondo que desentonaba con el blanco de `#topbar`: `QWidget#find_bar, QWidget#find_bar QLabel { background: transparent; }` en `main.py` lo deja transparente (el campo de texto sigue blanco, con su propio fondo de `QLineEdit`). **(Petición de Ricardo) El buscador flota sobre la barra**: ya no está en su layout, sino que es hijo de `_topbar` y `_place_find_bar()` lo coloca con su borde derecho en el de la lupa (que, oculta, conserva su sitio con `setRetainSizeWhenHidden`), centrado en su altura y por encima de todo. Así **tapa las herramientas que queden debajo** en lugar de empujarlas u obligar a ensanchar la ventana (antes, con el buscador abierto, la barra exigía 1223 px); una herramienta que quedaría tapada a medias se tapa entera. Por eso su fondo pasa a ser opaco (`QWidget#find_bar { background: #FFFFFF; }`). Se recoloca al redimensionar la barra (`eventFilter`), y la X (en el sitio exacto de la lupa) lo cierra y deja ver otra vez todas las herramientas.
   * **(r50, petición de Ricardo) Búsqueda**: el botón de la barra principal **alterna** mostrar/ocultar (`_toggle_find_bar`; Ctrl+F y el menú siguen abriendo/enfocando sin cerrar). Escribir busca **sola**, sin pulsar Intro (`_find_edit.textChanged` → `_on_find_text_changed`, retardo de 250 ms con `_find_live_timer` para no relanzar en cada pulsación); Intro/F3 siguen sirviendo para saltar a la siguiente coincidencia. **Ya no hay icono de lupa**: en su sitio va el contador de coincidencias, con **ancho fijo** (96 px) para que el resto de la barra no se desplace al crecer el número o pasar a «Sin resultados».
   * Controles de cada herramienta:
     * **Zoom**: porcentaje y control deslizante.
     * **Texto**: Selector de tamaño de fuente (`QSpinBox`), botón de color, botón de **negrita** (icono Fluent `text_bold`), botón de **cursiva** (icono Fluent `text_italic`), botón de **alineación cíclica** (izquierda → centro → derecha, cuyo icono cambia en cada pulsación; (r69) **sin justificado**, que MuPDF no sabe pintar en este texto) y un combo de **tipografía** (`Documento`, `Noto Sans`, `Noto Serif`, `Noto Sans Mono`) en el que (r69) cada nombre se ve escrito con su propia letra. Mientras se escribe sobre la página, el cuadro usa ya la fuente, el tamaño, la negrita y la cursiva elegidos, y cambiarlos se ve al momento (antes la hoja de estilos global lo impedía).
     * **Resaltar, subrayar o tachar** (r59): tipo de marca, color (con transparencia) y **grosor del trazo** a mano alzada. Sobre el texto lo marca; fuera del texto (imágenes, dibujos) marca a mano alzada, enderezando los trazos rápidos. Sustituye al antiguo «Marcador a mano alzada».
     * **Rectángulo**: Selector de ancho de línea y color del borde.
     * **Emoji** (r40): **tamaño, color y opacidad** del emoji, y **selector con los 1391 emojis** de la fuente Noto Emoji (`emoji_picker.EmojiPicker`): buscador en español o en inglés (sin importar tildes), filtro por grupo y cuadrícula donde cada emoji se dibuja **con esa misma fuente y en el color elegido**. Dos detalles: la fuente se pide con `NoFontMerging`, porque si no Qt sustituye los emojis por Segoe UI Emoji (a color); y la cuadrícula se rellena la primera vez que se muestra, con un icono transparente provisional (con `setUniformItemSizes`, un primer elemento sin icono dejaba toda la cuadrícula a tamaño 0 y en blanco). Los dibujos se generan poco a poco, primero los visibles, y se guardan en caché. Ver `edicion_pdf.md` §1.b.
     * **Texto**: las opciones de letra son Documento, Noto Sans, Noto Serif y Noto Sans Mono (r36).
     * **Editar contenido**: tamaño, color, negrita y cursiva **del párrafo que se está editando**, una línea con su fuente, otra que avisa si mezcla estilos y un **indicador en vivo** «Ocupa N líneas y cabe» / «NO cabe: estira una esquina» (`_set_edit_fit`, en rojo cuando no cabe; el alto exacto va en su tooltip). Cambiar cualquier control reescribe el párrafo en el acto. Los controles llevan `NoFocus`: si le robaran el foco al editor, este se cerraría y el cambio se perdería.
     * **Firma**: Visualiza el nombre del certificado activo y dos iconos: cambiarlo (Switch) y olvidarlo (Delete), y (r68) tras un separador la **plumilla** de la firma manuscrita: abre el diálogo para dibujarla con el ratón (estilográfica: color, grosor, tinta que se superpone en los cruces) o cargar su imagen, y luego un clic en la página la estampa (arrastrar le da tamaño). Ver [firma_digital.md](firma_digital.md#firma-manuscrita-r68).
     * **Páginas**: panel «Operaciones de página» encima de las miniaturas, con una fila de iconos (ver `edicion_pdf.md`).
     * **Compresión**: combo de nivel como iLovePDF (**Baja compresión**, **Recomendada**, **Extrema**), con la descripción del nivel al lado, y un icono de guardar como que guarda una copia optimizada (ver `edicion_pdf.md`, «Motor de Compresión»).
   * **(r41, paleta de r42) Un único selector de color.** Todos los botones de color (texto, nota, marcado, marcador, rectángulo, emoji, editar contenido y marca de agua) abren la misma tabla de **19 colores** —la «Paleta Cromática de Transición de Luces» de Ricardo más dos grises junto al gris (petición de Ricardo): Gris claro `#D5D5D5`, a mitad de camino del blanco, y Gris oscuro `#555555`, a mitad de camino del negro— en **círculos** de 32 px dispuestos en **columnas de 4** leídas de arriba abajo (`color_picker.py`; el botón que la abre sigue siendo cuadrado), en lugar del selector de Windows. Cada círculo enseña en su ayuda el nombre del color (Blanco puro, Ámbar brillante, Azul eléctrico…). Las herramientas con transparencia —marcado, marcador y emoji, y la marca de agua— enseñan además la **opacidad** en ese mismo cuadro, así que el color y la transparencia se eligen juntos. (Petición de Ricardo) No es una ventana aparte: se abre como un **menú emergente en la posición del cursor** al pulsar el selector (sin barra de título ni botones Aceptar/Cancelar), y se recoloca si no cabe en la pantalla. Un clic en un color lo elige y cierra el menú, con la opacidad que marque su control; Esc o un clic fuera lo cierran sin cambiar nada. Al abrirlo queda marcado el color de la tabla más parecido al actual.
   * **(r31) Botones de acción solo con icono.** Toda acción que tiene un icono reconocible en Fluent UI System Icons (desde r36; antes Segoe Fluent Icons) se muestra solo con el glifo y su descripción va en el tooltip: operaciones de página, marcadores, actualizar comentarios, validar firmas, certificado, comprimir, el botón del aviso superior y los +/− de los selectores numéricos. Desde r58 también la negrita y la cursiva (Texto y Editar contenido) usan los glifos de Fluent (`text_bold`, `text_italic`) en vez de las letras **N** / *I* en Segoe UI, aunque el de negrita sea la «B» inglesa (decisión de Ricardo: ningún botón de icono sale de Segoe UI). Solo siguen con texto los botones de los diálogos.

3. **Área de Visualización del PDF (`_build_viewer()`)**:
   * Contenedor `QScrollArea` que alberga el widget [PDFViewerWidget](file:///a:/CARPETA%20IA/RICARDO/AVENTYAPDF/main_window.py#L100).

---

## El Visor Interactivo (PDFViewerWidget)

La clase [PDFViewerWidget](file:///a:/CARPETA%20IA/RICARDO/AVENTYAPDF/main_window.py#L100) es el lienzo interactivo donde se pinta el PDF y se gestionan todas las acciones de edición manual.

### 1. Conversión de Coordenadas
Para pintar y colocar las anotaciones en el lugar físico correcto, se implementa una traducción bidireccional entre la escala de pantalla (píxeles PyQt6 basados en el zoom) y las coordenadas de la página PDF original (puntos tipográficos, 72 DPI):
* `_to_pdf_pt(pos: QPoint) -> fitz.Point`: Convierte una posición del ratón en pantalla a un punto en coordenadas PDF dividiendo por el factor de escala (`scale_factor`).
* `_to_pdf_rect(qr: QRect) -> fitz.Rect`: Convierte un rectángulo dibujado en pantalla a un rectángulo PDF.
* `_to_screen_rect(fr: fitz.Rect) -> QRect`: Traduce un área rectangular del PDF original a píxeles de pantalla para pintar las cajas de selección y redimensionamiento.

### 2. Pintado del PDF y Anotaciones (`paintEvent`)
Dibuja el fondo del PDF renderizado. Si hay una anotación seleccionada (`_sel: AnnotSelection`) en modo selección (`mode == "NONE"`), dibuja:
* Una línea discontinua de color azul (`#0078D4`) o rojo para firmas (`#D13438`) bordeando el área de la anotación.
* Cuatro tiradores cuadrados pequeños en las esquinas (Top-Left, Top-Right, Bottom-Left, Bottom-Right) para permitir el redimensionamiento.
* Dibuja trazos provisionales mientras el usuario marca a mano alzada (el resaltado en modo Multiply, como quedará) o despliega un rectángulo elástico.

### 3. Redimensionamiento y Arrastre de Anotaciones
Cuando el visor está en modo selección (`NONE`):
* **Arrastre (Drag)**: Si el ratón hace clic dentro de los límites de una anotación (`_annot_at()`), se activa el estado `_dragging` y se desplaza la anotación siguiendo el movimiento del ratón.
* **Redimensionamiento (Resize)**: Si el ratón hace clic sobre alguno de los tiradores de las esquinas (`_get_resize_corner()`), se inicia el redimensionamiento en la dirección correspondiente, recalculando el rectángulo físico de la anotación y forzando un tamaño mínimo (`MIN = 10` puntos PDF) para evitar el colapso del objeto.
* **Actualización**: Al soltar el ratón, se actualizan las propiedades de la anotación mediante PyMuPDF (`a.set_rect()`, `a.update()`) y se vuelve a renderizar la página.

### 4. Menú Contextual y Teclado
* El visor responde a clics secundarios (`contextMenuEvent`) sobre anotaciones mostrando la opción de editar su texto o eliminarla (a excepción de las firmas digitales que no pueden modificarse).
* Permite borrar la anotación seleccionada presionando las teclas `Suprimir` o `Retroceso` (`keyPressEvent`).
* La tecla `Escape` deselecciona cualquier anotación activa.

---

## Control de Zoom

La visualización admite tres modos de escala controlados por `MainWindow.zoom_mode`:
* **Zoom 100% (`"100"`)**: El factor de escala se ajusta numéricamente. La barra de herramientas permite regular el valor.
* **Ajustar al Ancho (`"width"`)**: Escala la página del PDF para que ocupe exactamente el ancho disponible en la ventana (descontando el espacio de barras de scroll).
* **Ajustar al Alto (`"height"`)**: Escala la página del PDF para que se ajuste verticalmente a la altura del visor.

El método `update_zoom()` calcula el factor de escala apropiado y redibuja la página activa preservando las anotaciones y selecciones actuales.

**(r48) El botón «ancho/alto» no lleva un icono fijo**: muestra la acción que el clic va a ejecutar (la que está libre), no la que ya está activa — petición de Ricardo. `_update_zoom_type_icon()` decide entre `icons.glyph("type")` (ancho) y `icons.glyph("type_height")` (alto) según `zoom_mode`: con `"width"` activo el próximo clic ajusta al alto → icono de alto; con `"height"` o `"100"` activo (o cualquier zoom numérico) el próximo clic ajusta al ancho → icono de ancho, igual que decide `_toggle_type_zoom`. Se llama tras cada cambio de `zoom_mode` (`_zoom_mode_changed`, `_set_custom_zoom`) y al construir el botón. **(r51) Tampoco es «checkable»**: con el icono cambiando de sitio para decir qué va a pasar, dejarlo además marcado como seleccionado (resaltado) era contradictorio — petición de Ricardo. Al no ser «checkable», `.setChecked()` no tiene ya nada que hacer sobre este botón: se quitaron las llamadas que quedaban (`_set_pages_mode`, `_toggle_compress_panel`, `_activate_tool`, `_set_custom_zoom`).

---

## Gestión de Eventos y Estados

La aplicación funciona como una máquina de estados controlada por `mode`:
* `NONE`: Modo selección estándar. El usuario puede mover, redimensionar, editar o borrar anotaciones existentes.
* `EDIT`: Editar contenido (tecla **C**). No manipula anotaciones, sino el texto y las imágenes **del propio PDF**: `viewer.content` (`edit_ui.ContentEditor`) dibuja los recuadros, abre un editor multilínea sobre el cuadro del **párrafo** y aplica los cambios con `pdf_edit`. Los tiradores de las esquinas estiran el cuadro y el texto se reajusta; van dibujados **fuera** del cuadro porque el editor lo tapa entero, y funcionan porque `mousePressEvent` del visor no llama a `super()` y por tanto no le quita el foco al editor. Ver `edicion_pdf.md`, «Edición del contenido real del PDF».
* `TEXT` / `EMOJI`: Al hacer clic en el lienzo, solicita confirmación e inyecta la anotación en el PDF.
* `MARKUP` (Resaltar, subrayar o tachar): sobre el texto lo selecciona y lo marca; fuera del texto dibuja a mano alzada (r59; sustituye al antiguo `HIGHLIGHT`). El cursor cambia a I sobre texto y a cruz fuera.
* `RECT` / `SIGN`: El cursor cambia a cruz y permite arrastrar un rectángulo elástico de selección de área.

### Auto-selección de herramienta al seleccionar una anotación
Cuando el usuario hace clic sobre una anotación existente en modo `NONE`, se invocan dos métodos de `MainWindow`:

* **`_show_annot_opts(annot)`**: Identifica el tipo de anotación (`FreeText`→`TEXT`/`EMOJI`, `Ink`→`MARKUP` (r59), `Square`→`RECT`) y:
  1. Llama a `_sync_panel_to_annot` para leer las propiedades reales de la anotación (color, grosor, tamaño de fuente) y actualizar los controles del panel sin disparar señales (`blockSignals`).
  2. Muestra el panel de opciones correspondiente sin cambiar el `mode` del visor (permanece `NONE`).
  3. Activa visualmente el botón de herramienta en la barra superior.
  4. Programa `_scroll_to_selection` vía `QTimer.singleShot(0, ...)`. (r74/r75: ya no existe la barra secundaria `_opt_row` que antes podía empujar el visor hacia abajo al aparecer, así que se retiró la compensación de desplazamiento — `_compensate_opt_shift` — que antes hacía falta para esos casos.)

* **`_hide_annot_opts()`**: Al deseleccionar (clic en espacio vacío, Suprimir, Escape, navegación de páginas), apaga el botón de herramienta y oculta los paneles de opciones. Solo actúa si `mode == "NONE"` para no interferir con operaciones activas.

* **`_apply_to_selection(fn)`**: Función central que aplica `fn(annot)` sobre la anotación actualmente seleccionada y re-renderiza la página. Todos los cambios de color, tamaño y grosor pasan por aquí cuando hay una selección activa en modo `NONE`.

* **`_scroll_to_selection()`**: Llama a `QScrollArea.ensureVisible` sobre el centro del rectángulo de la anotación seleccionada para garantizar que siga a la vista tras el cambio de panel.

### Estilado de texto (negrita / cursiva / alineación / tipografía)
Todos los cambios de estilo de una anotación de texto pasan por **`_apply_text_change(**ov)`**, que actualiza los valores por defecto del visor (`text_bold`, `text_italic`, `text_align`, `text_color`, `text_font`) y, si hay una anotación `FreeText` seleccionada, la **reconstruye** vía `PDFUtils.rebuild_text_annotation` preservando los atributos no modificados (leídos del token `/Subj`). Los manejadores son `_on_txt_size`, `_on_txt_color`, `_on_txt_bold`, `_on_txt_italic`, `_on_txt_align_cycle` (cicla 0→1→2→3→0 y actualiza el icono con `_set_align_icon`) y `_on_txt_font` (mapea `Documento`/`Arial`/`Times`/`Courier` a una familia CSS mediante `_text_font_css`). La reedición de texto (doble clic / menú contextual) usa `_edit_text_annot`, que mantiene el estilo guardado.

### Emojis a color e identificación al seleccionar
* **`_insert_emoji(pt, emoji, fontsize, color, opacity)`**: llama a `emoji_font.add_emoji_annot`. El emoji (Noto Emoji, r40) queda con la esquina superior izquierda en el punto clicado, con el color y la transparencia del panel. Si no lo trae la fuente (banderas de países, secuencias con ZWJ), se avisa con un `QMessageBox`.
* **`_recreate_emoji_selection()`**: cambiar el glifo o el tamaño de un emoji seleccionado lo **recrea en su posición** (borra el anterior, inserta el nuevo y reselecciona). Así también se convierten al formato actual los emojis antiguos (`EmojiImg`, `EmojiStamp`).
* **Mover y redimensionar** (`viewer.py`): para los Stamp de emoji (`emoji_font.STAMP_SUBJECTS`) se usa `emoji_font.write_rect()` en lugar de `set_rect()`/`update()`. Al redimensionar, `_keep_aspect` mantiene la proporción desde cualquier esquina y el tamaño guardado en `/T` se reescala con el alto.
* **`_show_annot_opts`** mapea `Stamp` → modo `EMOJI` (y `FreeText`+`EmojiStamp` de versiones antiguas). El tamaño y el glifo se recuperan de `/T` y `/Contents`.

### Metadatos de estilo en anotaciones de texto
`add_text_annotation` (utils.py) ya **no** usa `annot.set_info()` (que regeneraría la apariencia rich text desde texto plano). Escribe `/T` (tamaño), `/Contents` (texto plano) y `/Subj` (token de estilo) directamente con `xref_set_key`, y `_sync_panel_to_annot` los recupera con `PDFUtils.decode_text_style` para sincronizar todos los controles del panel (tamaño, color, negrita, cursiva, alineación y tipografía) sin disparar señales.

### Trazos rectos a mano alzada (`straighten_stroke()`, r59)
Al marcar a mano alzada, un gesto **rápido** y más o menos recto sale como una recta (y se ajusta a horizontal o vertical si está a menos de 8°); un gesto lento se respeta tal cual salvo el temblor del pulso. Sustituye a `_maybe_straighten`, que enderezaba cualquier trazo casi horizontal aunque fuera lento. Detalle y umbrales en `edicion_pdf.md` §2.

### Archivo cambiado desde otra aplicación (`check_disk_changes()`, r115)
La app lee el PDF entero a memoria al abrirlo (no bloquea el archivo), así que otra aplicación puede reescribirlo. Si en el disco hay **otros bytes** que los que se leyeron (`_clean_bytes`), el documento se vuelve a leer **en la misma pestaña**, en la misma página, con un aviso en la barra de estado. Se comprueba:
* al volver a la ventana (`applicationStateChanged` → activa);
* cada 1,5 s mientras la ventana está sin foco —p. ej., a la vista junto a la otra aplicación— (`_poll_disk`), pero solo si no hay cambios sin guardar y sin mostrar ningún diálogo;
* al cambiar de pestaña, y al abrir otra vez un archivo que ya está abierto (antes solo se cambiaba a su pestaña, aunque hubiera cambiado).

Para no leer el archivo entero cada vez se guarda su tamaño y fecha (`_disk_stat`): solo si cambian se leen y comparan los bytes (volver a guardar el mismo contenido no recarga nada). Con **cambios sin guardar** (o un campo/cuadro de texto a medio escribir, que se confirma antes) se pregunta «Cargar la versión nueva» / «Mantener mis cambios»; si se mantienen, esa versión del disco (`_disk_ignored`, su SHA-256) no se vuelve a ofrecer. Si el archivo está a medio escribir y no se puede leer como PDF, se reintenta en la siguiente comprobación. Los guardados de la propia app actualizan `_disk_stat` y no cuentan como cambio externo.

---

## Relación con otros Documentos

Este fichero se relaciona directamente con:
* **[Arquitectura General (arquitectura.md)](arquitectura.md)**: Flujo de eventos y componentes UI.
* **[Edición y Manipulación de PDF (edicion_pdf.md)](edicion_pdf.md)**: Cómo se aplican las anotaciones en la estructura interna de PyMuPDF.
* **[Gestión de Certificados Digitales (gestion_certificados.md)](gestion_certificados.md)**: Interfaz de selección de certificado (`CertPickerDialog`).
