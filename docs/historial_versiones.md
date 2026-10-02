# Historial de versiones de AventyaPDF

**Solo se mantiene la última versión**, la de [Releases](https://github.com/Aventya/AventyaPDF/releases/latest). Las anteriores se desechan: su publicación, su etiqueta y su instalador se han retirado de GitHub, porque pueden tener fallos ya corregidos. Aquí queda solo la mención de lo que trajo cada una, con el commit del que salió (el código sigue en el historial de la rama `desarrollo`).

Las publicadas como 1.0.0-1.3.0 se renumeraron 0.9.6-0.9.6.7 al publicarse la 0.9.7, y las 2.0.3-2.0.5 como 0.9.3-0.9.5 al publicarse la que fue 1.0.0: la **1.0.0** queda reservada para la primera versión con el instalador firmado.

## 0.9.9 — 2026-10-01

Commit `9ad46de`.

Un PDF que cambia en otra aplicación se actualiza solo, y el instalador va firmado con Sigstore.

#### Novedades respecto a la 0.9.8
- **PDF cambiado desde otra aplicación**: si otro programa modifica el PDF que tienes abierto, AventyaPDF lo vuelve a leer solo, en la misma pestaña y página: al volver a su ventana, mientras está a la vista sin foco, al cambiar de pestaña o al abrir otra vez el mismo archivo. Si tienes cambios sin guardar, pregunta antes. Volver a guardar el mismo contenido no recarga nada.
- **Instalador firmado con Sigstore**: cualquiera puede comprobar que es exactamente el publicado, sin modificaciones.

203 pruebas automáticas OK. Autodiagnóstico 9/9, también en una instalación real de prueba descargándolo todo de Internet.

## 0.9.8 — 2026-09-30

Commit `9024536`.

Correcciones del instalador.

#### Novedades respecto a la 0.9.7
- **Tamaño correcto en Configuración › Aplicaciones**: la 0.9.7 registraba unos 494 MB porque contaba también los archivos descargados, que se borran al terminar. Ahora muestra lo que ocupa de verdad (unos 336 MB).
- **El diálogo «Abrir» ya no muestra un «prueba.pdf»** en los equipos donde se compila AventyaPDF: la comprobación automática que se hace al generar el instalador ya no toca la configuración del usuario (recientes y última carpeta), y limpia lo que dejaron las anteriores.

203 pruebas automáticas OK. Autodiagnóstico 9/9, también en una instalación real de prueba descargándolo todo de Internet.

## 0.9.7 — 2026-09-30

Commit `0b9d64a`.

Última versión antes de firmar el instalador con certificado (que será la **1.0.0**). Instala solo lo que la aplicación usa.

#### Novedades respecto a la 0.9.6.7
- **Instala solo lo que se usa**: de los componentes descargados ya no se instalan las partes que AventyaPDF no utiliza (por ejemplo, los módulos de Qt para 3D, multimedia o QML y el códec de vídeo de OpenCV). Ocupa unos **336 MB** en lugar de más de 500 (Configuración › Aplicaciones muestra por error unos 494 MB: el instalador de esta versión calcula mal el tamaño que registra; se corrige en la siguiente). La lista se calcula a partir de lo que la aplicación carga de verdad, y cada versión se comprueba con una instalación real antes de publicarse.
- Nuevas comprobaciones automáticas de impresión, formatos de imagen e iconos antes de publicar.

Incluye todo lo de la 0.9.6.7: firma con certificados de Windows cuya clave no se puede exportar e instalador ligero que descarga los componentes al instalar.

202 pruebas automáticas OK. Autodiagnóstico: 9/9, también en una instalación real de prueba descargándolo todo de Internet.

## 0.9.6.7 — 2026-09-30 (publicada como 1.3.0)

Commit `66b074a`.

Firma con certificados de Windows cuya clave no se puede exportar, e instalador mucho más ligero que descarga los componentes de su origen oficial.

#### Novedades
- **Firma digital con certificados no exportables**: los certificados del almacén de Windows cuya clave privada se instaló como no exportable daban «Error de exportación… Clave no válida para utilizar en el estado especificado». Ahora es Windows quien firma con la clave donde está, sin sacarla del almacén ni escribirla en ningún archivo temporal. Esto también abre la puerta a tarjetas criptográficas y DNIe (Windows pide el PIN), aunque aún no se ha probado con una tarjeta real.
- **Instalador de 4,4 MB en lugar de 82 MB**: ya no incluye piezas que se mantienen fuera del proyecto. Python, los paquetes (en la versión exacta probada) y las fuentes se descargan al instalar. Instalado ocupa más que antes (unos 510 MB), porque los paquetes van completos, tal como se publican.
- Noto Emoji actualizada a la versión 3.006.

202 pruebas automáticas OK. Autodiagnóstico: 8/8, también en una instalación real de prueba descargándolo todo de Internet.

## 0.9.6.6 — 2026-09-29 (publicada como 1.2.2)

Commit `2d3e079`.

Correcciones del recorte de páginas y de las páginas giradas.

#### Novedades
- **Recortar ya no es solo visual**: además de lo que se ve, cambia el tamaño real de la página (MediaBox) y ajusta a él las cajas de impresión, así que ningún programa ve ya la página original.
- **Firma digital en páginas recortadas**: el sello aparecía desplazado respecto al recuadro dibujado. Ahora queda exactamente donde se dibuja.
- **Páginas giradas**: rectángulo, texto, notas, resaltado, mano alzada, emojis, firma manuscrita y firma digital quedan donde se dibujan y se leen derechos. También se pueden seleccionar y mover, y la búsqueda, la selección de texto y los campos de formulario se marcan en su sitio.
- **Resaltar, subrayar y tachar en páginas giradas** siguen el renglón (uno por línea), en vez de un recuadro cruzado por cada palabra.
- **OCR en páginas giradas**: ya no vuelve a reconocer (y duplicar) el texto que la página ya tenía.

200 pruebas automáticas OK. Autodiagnóstico del empaquetado: 7/7.

## 0.9.6.5 — 2026-09-29 (publicada como 1.2.1)

Commit `da3593b`.

#### Novedades

- El manual (`MANUAL.pdf`) aparece ya seleccionado al abrir el diálogo de «Abrir PDF» por primera vez, sin tener que navegar hasta él.
- Corregido el aspecto de los selectores del modo de compresión (panel «Comprimir PDF»): eran botones de radio de verdad, pero un fallo en su estilo los pintaba como un cuadrado azul en vez de un círculo cuando estaban marcados.

## 0.9.6.4 — 2026-09-29 (publicada como 1.2.0)

Commit `2a72775`.

Nueva herramienta de recorte de página, el instalador pesa mucho menos, y manual ilustrado.

#### Novedades
- **Recortar página**: nuevo icono en «Operaciones de página» — dibuja un recuadro con tiradores en las cuatro esquinas y los cuatro lados sobre la página mostrada, cada uno cambia su propio margen. Dos botones flotantes, centrados en el recuadro, aplican o cancelan el recorte.
- **Zoom siempre visible en la barra de estado**: campo de porcentaje editable, botones de acercar/alejar y barra deslizante, alineados con el ancho real de la barra de desplazamiento del visor. El botón de ajustar ancho/alto gana una tercera opción: escala original (100 %).
- **Aviso de formulario/cifrado centrado en la barra de estado**, en vez de una barra aparte sobre el visor.
- **Ctrl + rueda del ratón** hace zoom también sobre la zona gris que rodea la página, y ya no da saltos con ratones de alta resolución.
- **Buscador más estrecho**, sin tapar los botones de la barra principal.

#### El instalador pesa mucho menos
Tesseract OCR ya no va incluido dentro del instalador: se descarga solo la primera vez que se usa «Reconocer texto (OCR)» (necesita internet y, si no estuviera ya instalado, permiso de administrador una sola vez). El resto de la aplicación sigue funcionando sin conexión. El instalador baja de ~131 MB a **~81 MB**.

#### Manual con capturas
Nuevo manual ilustrado, con una captura de cada herramienta: [docs/MANUAL.pdf](https://github.com/Aventya/AventyaPDF/blob/main/docs/MANUAL.pdf).

190+ pruebas automáticas OK. Autodiagnóstico del empaquetado: 7/7.

## 0.9.6.3 — 2026-09-28 (publicada como 1.1.2)

Commit `928aa25`.

Rediseño de la herramienta de Zoom.

#### Cambios respecto a la 0.9.6.2
- **Zoom siempre visible, en la barra de estado.** El botón «Zoom» de la barra principal y su panel lateral desaparecen; ahora la herramienta está siempre a la derecha de la barra de estado, del mismo alto que ella: campo con el porcentaje (editable — escribe un valor y pulsa Intro, o simplemente haz clic fuera), botón de alejar, barra deslizante y botón de acercar.
- **Porcentaje a mano.** El campo del zoom se puede editar directamente escribiendo el número que quieras.
- **Tope de zoom: 400%** (antes 800%).
- **Tercera opción en el botón de ajuste.** El botón que alterna entre ajustar al ancho y ajustar al alto gana una tercera posición: escala original (100%).

190 pruebas automáticas OK (5 omitidas por dependencias opcionales). Autodiagnóstico del empaquetado: 7/7.

## 0.9.6.2 — 2026-09-28 (publicada como 1.1.1)

Commit `823c306`.

Corrección de cuatro fallos detectados en la 0.9.6.1.

#### Cambios respecto a la 0.9.6.1
- **Varios PDF, una sola ventana con pestañas.** Al abrir varios PDF a la vez desde el Explorador, otra aplicación o el menú contextual, ya no se abre una ventana por archivo: todos se abren en la misma ventana, cada uno en su pestaña. Si AventyaPDF ya está abierto y llega un PDF nuevo (otro doble clic, otra app), se añade como pestaña a la ventana existente y esta pasa al frente.
- **Rueda del ratón.** Al llegar al final o al principio de una página que cabe entera en el visor, una sola vuelta de rueda pasa a la página siguiente o anterior (antes, en ese caso, hacían falta dos vueltas seguidas y podía sentirse como que no respondía).
- **Zoom al 100% real.** Con la herramienta de Zoom activa, pulsar otra vez el mismo botón fuerza la vista a 1:1 (100% del tamaño original), no solo a apagar el modo.
- **El icono de los PDF ya no cambia.** Al instalar o actualizar AventyaPDF, los archivos .pdf del Explorador conservan su icono habitual (el del lector que tuvieras antes); solo cambia la aplicación que se abre al hacer doble clic.

190 pruebas automáticas OK (5 omitidas por dependencias opcionales). Autodiagnóstico del empaquetado: 7/7.

## 0.9.6.1 — 2026-09-27 (publicada como 1.1.0)

Commit `1c297b4`.

#### Cambios respecto a la 0.9.6

- **Menú del botón derecho en el Explorador de Windows**: nuevo submenú **«AventyaPDF»** con su icono al pulsar con el botón derecho sobre archivos:
  - **Firmar digitalmente**, sobre PDF: abre el documento con la herramienta Firma lista.
  - **Combinar en un PDF**, sobre dos o más PDF, imágenes o documentos de Word, mezclados: un único PDF con todo, en orden.
  - **Convertir a PDF**, sobre imágenes (PNG, JPG, BMP, GIF, TIFF, WEBP) o documentos de Word (DOC, DOCX): un PDF por archivo.
  
  El resultado se abre en AventyaPDF sin guardar, para revisarlo y guardarlo donde quieras; los archivos originales no se tocan. En Windows 11 aparece en el menú principal y también en «Mostrar más opciones». Al desinstalar AventyaPDF desaparece.
- **Word a PDF**: los documentos de Word se convierten con Microsoft Word y, si no lo tienes, con LibreOffice. Hace falta uno de los dos.

## 0.9.6 — 2026-09-27 (publicada como 1.0.0)

Commit `f85b6ef`.

**Primera versión completa** de AventyaPDF, el visor, editor y firmador de PDF para Windows de **Aventya Asesoría Integral SL**: aplicación de libre distribución con licencia **GNU AGPL-3.0**.

#### Cambios respecto a la 0.9.5

- **Interfaz uniforme**: todos los botones y campos de formulario miden 32 px de alto, y los botones de icono 32×32. La barra principal y el panel lateral se adaptan a ese tamaño.

- **Búsqueda**: se superpone a la barra de herramientas en lugar de empujarla o ensanchar la ventana. La «X» de cerrar queda en el sitio exacto del botón de la lupa y vuelve a dejar ver todas las herramientas.

- **Colores**: la paleta se abre como un menú en la posición del cursor, no en una ventana aparte. Tiene 19 colores en círculos, en columnas de 4, con dos grises nuevos (claro y oscuro). Un clic elige el color; Esc o un clic fuera la cierran.

- **Firma**: el aviso de dibujar el área de la firma va arriba, enmarcado, y debajo están el certificado y la firma manuscrita, cada uno con su botón a la derecha.

- **Opciones de firma**: el sello de tiempo cualificado sale marcado de entrada; solo tú decides quitarlo.

- **Texto de la firma visible**: ahora en letra sans (Noto Sans, incrustada en el PDF) en lugar de Courier.

- **Actualizaciones**: al iniciar, AventyaPDF comprueba en segundo plano si hay una versión nueva y, si la hay, te avisa con el enlace directo para descargar su instalador (se desactiva en «Ayuda › Avisar de actualizaciones al iniciar»). También puedes comprobarlo cuando quieras en «Ayuda › Buscar actualizaciones…».

## 0.9.5 — 2026-09-25 (publicada como 2.0.5)

Commit `8b3dc11`.

AventyaPDF de **Aventya Asesoría Integral SL**: aplicación de libre distribución con licencia **GNU AGPL-3.0**.

#### Cambios en la 0.9.5

- El aviso de «documento firmado» ya no aparece sobre el visor: vive en el panel lateral **Firmas Certificadas** (icono de certificado), que se abre siempre que el PDF tenga alguna firma dentro.

- **Firma** y **Comprimir** pasan del visor al panel lateral, como el resto de herramientas:

  - Firma: el certificado seleccionado arriba y, debajo, solo dos iconos (elegir certificado, firma manuscrita).

  - Comprimir: el nivel se elige con tres selectores circulares y frases cortas («Buena calidad, imágenes 100ppp»…), y la acción es «Guardar copia comprimida» con el icono de la herramienta.

- La **búsqueda** ya no es una barra aparte encima del visor: ocupa el sitio de su propio botón en la barra principal.

- Arreglado un fallo visual al **arrastrar una miniatura** para reordenar páginas (podía verse un rectángulo negro).

Novedades de la 0.9.4: [v0.9.4](https://github.com/Aventya/AventyaPDF/releases/tag/v0.9.4).

## 0.9.4 — 2026-09-24 (publicada como 2.0.4)

Commit `6c2f8f4`.

AventyaPDF de **Aventya Asesoría Integral SL**: aplicación de libre distribución con licencia **GNU AGPL-3.0**.

#### Cambios en la 0.9.4

- Las opciones de todas las herramientas (Texto, Nota, Resaltar, Rectángulo, Emoji, Editar contenido, Zoom y Páginas) aparecen siempre **en la parte superior del panel lateral**. Antes, con el panel cerrado, salían centradas en vertical.

- El selector «Tipo de letra» ya no se sale del panel por la derecha.

Novedades de la 0.9.3: [v0.9.3](https://github.com/Aventya/AventyaPDF/releases/tag/v0.9.3).

## 0.9.3 — 2026-09-24 (publicada como 2.0.3)

Commit `e0142d9`.

Primera versión publicada de **AventyaPDF**, el visor, editor y firmador de PDF para Windows de **Aventya Asesoría Integral SL**. Es de libre distribución, con licencia **GNU AGPL-3.0**.

#### Novedades de la 0.9.3

- **Firma manuscrita**: nuevo botón de la plumilla en la barra de Firma. Dibuja tu firma con el ratón, con trazo de estilográfica (grosor variable y tinta que se oscurece donde se cruza) y el color y grosor que elijas, o carga la imagen de tu firma escaneada, que se limpia del fondo blanco.

- **Herramienta Texto**: se escribe directamente con la fuente, el tamaño y el estilo elegidos, y el selector muestra cada fuente con su propia tipografía. Se retira la alineación justificada.

- **Presentación inicial** que explica las características, con la opción «No volver a mostrar al iniciar» (se vuelve a abrir desde Ayuda).

- Titular, licencia libre y enlace al código en «Acerca de» y en la presentación.

#### Qué incluye

Comentarios y marcado de texto · edición del texto y las imágenes del PDF · formularios · organización de páginas · marca de agua, encabezado, pie y Bates · OCR · cifrado AES-256 · firma PAdES con sellado de tiempo y verificación con la lista de confianza de España · exportación a Word, imágenes y texto.
