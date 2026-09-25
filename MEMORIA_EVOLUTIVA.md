# MEMORIA EVOLUTIVA — AventyaPDF

> **Documento vivo.** Es la fuente única de verdad sobre la composición y el
> comportamiento real del proyecto. Se lee ANTES de tocar código y se actualiza
> DESPUÉS de cada edición. Protocolo de actualización en la sección 9.

| Campo | Valor |
| :-- | :-- |
| Revisión de la memoria | **r83** |
| Fecha de la revisión | 2026-09-25 |
| Versión de la app | **2.0.5** (r73-r79: aviso de firma, paneles Firma/Comprimir, Firmas Certificadas, búsqueda en la barra principal; r80/r81/r82: tres intentos sucesivos de arreglar el fantasma negro al arrastrar una miniatura (`devicePixelRatio` → alfa premultiplicado → **sin alfa, opaco**) — **sin confirmar aún en la pantalla real de Ricardo**. Reempaquetada y publicada en r83 pese a eso, a petición suya. `window_menus.APP_VERSION`, `APP_OWNER`, `APP_REPO`) |
| Raíz del proyecto | `C:\Users\Aventya\Proyectos\AVENTYAPDF` (✅ ya renombrada, comprobado en r71; antes `ANTIGRAVITY-PDF`, ver r56) (hasta r5: `A:\CARPETA IA\RICARDO\ANTIGRAVITY-PDF`, carpeta compartida por varios equipos) |
| Control de versiones | ✅ **git** desde r71, repositorio **público** https://github.com/Aventya/AventyaPDF (cuenta de GitHub `Aventya`, rama `main`). Licencia **AGPL-3.0** (`LICENSE`). Titular: **Aventya Asesoría Integral SL**. |
| Estado | ✅ **Pruebas automáticas: 169/169** (r82, r81, r80, r79, r78, r77, r76, r75, r74, r73, r72; r71: 168; r70, 5 omitidas; r69: 167; r68: 166; r62: instalador `AventyaPDF-Setup-2.0.1.exe` generado y probado; r61: r59: 152; r58: 144; r57: 143; r56: con el nombre de código y rutas de `%LOCALAPPDATA%` ya cambiados a AventyaPDF). ⚠️ **La carpeta del proyecto sigue llamándose `ANTIGRAVITY-PDF`** — el renombrado a `AVENTYAPDF` está pendiente, bloqueado porque esta misma sesión la mantiene abierta (ver r56). ⚠️ La interfaz real aún no se ha abierto ni probado a mano (ver §7.0). El menú contextual de `Install-ContextMenu.ps1` **no se ha instalado de verdad** en el registro real: solo se comprobó contra una rama de pruebas (`-Raiz`), ver r55/r56. |
| Líneas de código Python | ~11.000 en 29 módulos + 2 de pruebas (r38: fuera el visor XFA y pdf.js) |

---

## 1. Qué es

Aplicación de escritorio **Windows** (PyQt6) para **ver, comentar, organizar,
proteger, convertir y firmar digitalmente PDF**. Objetivo declarado por Ricardo
(2026-09-14): convertirla en un rival digno de Adobe Acrobat Pro.

Funciones principales (r4): menús completos con atajos; panel lateral
(miniaturas, marcadores, comentarios, firmas); búsqueda; selección y copia de
texto; resaltado/subrayado/tachado de texto real; notas adhesivas; cuadros de
texto, marcador, rectángulos, emojis; relleno de formularios; deshacer/rehacer;
organización de páginas (girar, extraer, dividir, insertar, duplicar);
**edición del texto y las imágenes que ya están en el PDF** (r21);
marca de agua, encabezado/pie y numeración Bates; OCR
(Tesseract); cifrado AES-256 y permisos; propiedades; exportar a imágenes,
texto y Word; crear PDF desde imágenes; firma PAdES visible con sellado de
tiempo y certificación; validación de firmas. Desde r5: registro de errores
sin cierre de la app y pruebas automáticas.

Estética: Adobe Acrobat / Windows 11 Fluent. Toda la UI está en español.
Especificación original: [PLAN_DE_IMPLEMENTACION.md](PLAN_DE_IMPLEMENTACION.md);
memoria narrativa: [docs/](docs/indice.md).

## 2. Composición del proyecto

### 2.1 Código fuente

| Archivo | Líneas | Responsabilidad |
| :-- | --: | :-- |
| [main.py](main.py) | ~415 | Entrada. `QApplication` Fusion + `STYLESHEET` global (toda la apariencia). **`_install_error_handler()`** (r5): `sys.excepthook` → diálogo + `errores.log`; `faulthandler` → `fallos_graves.log`. (r55) **`procesar_argumentos(window, argv)`**: función aparte (probable sin arrancar `QApplication` de verdad), interpreta `--combinar-pdf` / `--imagenes-a-pdf` / `--imagenes-a-pdfs-separados` del menú contextual del Explorador (`Install-ContextMenu.ps1`) o, sin indicador, abre el primer `.pdf` de la lista como siempre («Abrir con…»). |
| [main_window.py](main_window.py) | ~1.520 | `MainWindow(DocumentMixin, MenusMixin, QMainWindow)`: glifos `_G`, barra superior, barra secundaria encima del visor con Firma y Comprimir (r49: fuera Redactar), y (r26) paneles de opciones de Zoom y anotación en el panel lateral (`_build_side_tool_panels`) (sin panel de páginas desde r7; r21: `_edit_panel` y `_show_edit_opts`), zoom, render de página, estilos de anotación, operaciones de página simples, impresión, compresión, emojis, etiqueta de certificado. |
| [viewer.py](viewer.py) | ~960 | `AnnotSelection` y `PDFViewerWidget`: ratón/teclado/rueda/pintado de los 11 modos (r21: `EDIT`), selección de texto, relleno de formularios, (r59) `straighten_stroke`/`squiggle` (marcas a mano alzada). `self.content` = `edit_ui.ContentEditor`. (r23) `self.text_editor`: escritura sobre la página para la herramienta Texto (`begin_text`), las notas (`begin_note`) y la edición de anotaciones (`_edit_selected_text`), con `restyle_text_editor` y `close_text_editor`. |
| [window_document.py](window_document.py) | ~790 | `DocumentMixin`: abrir/guardar/cerrar, **varios documentos** (r20: `_sessions`, `_active`, `switch_document`, `_stash_active`/`_restore_session`, `_begin_new_session`, `close_document_at`, `next_document`), recientes, arrastrar-soltar, deshacer/rehacer, búsqueda, navegación, zoom por pasos, API del panel lateral, notas/marcado, aviso superior y **firma en hilo** (`SignWorker`). |
| [window_menus.py](window_menus.py) | ~737 | `MenusMixin`: barra de menús y atajos (r54: 9 menús — `Editar contenido` ya no tiene el suyo propio, su acción abre Herramientas), barra de búsqueda, aviso, y herramientas de documento (marca de agua, Bates, OCR, seguridad, propiedades, exportar, dividir…). `_run_doc_change` = checkpoint + ejecutar + revertir si falla. (r55) `combine_pdfs_from_paths(paths)` y `create_separate_pdfs_from_images(paths)`, junto a `create_from_images` ya existente: los tres parten de cero (sin documento previo) y dejan el resultado sin guardar en una o varias pestañas nuevas — las usa el menú contextual del Explorador. |
| [sidebar.py](sidebar.py) | ~540 | `SidePanel`: rail de iconos + paneles Miniaturas (render perezoso por lotes), Marcadores (editar TOC), Comentarios, Firmas ((r61) verificadas solas en segundo plano con `ValidateWorker`, sin botón; papelera en la más reciente; recuadros vacíos listados). (r20) Bajo un separador, **pestañas de documentos abiertos** (`set_documents`: botón por documento con glifo PDF U+EA90, o Document U+E8A5 si no tiene ruta; tooltip «● nombre» + ruta; menú «Cerrar documento»; solo con 2 o más). `set_panels_enabled` (modo XFA). `tools` (opciones de herramienta) va arriba de `stack` en un `QVBoxLayout` normal y lo empuja hacia abajo (r26; probado sin empujar con `_ToolOverlay` en r46, retirado en r50 — invariante 53). (r51, híbrido con `QDrag` real en r52) `_ThumbList` arrastra las miniaturas con `mousePressEvent`/`mouseMoveEvent` de toda la vida decidiendo cuándo hay arrastre, pero con un `QDrag.exec()` real para el fantasma y el cursor de OLE; el destino sale de `QCursor.pos()` al volver de `exec()`, no de `dropEvent` (invariante 48). |
| [doc_tools.py](doc_tools.py) | ~472 | Operaciones puras PyMuPDF, sin Qt: rangos de páginas, rotar/extraer/dividir/insertar, marca de agua, encabezado/pie/Bates, búsqueda, `word_selection`, imágenes→PDF, exportaciones, OCR, firmas, aplanar, resumen de comentarios, `MARKUP_COLORS`. (r55) `merge_pdfs(paths)`: combina varios PDF completos en un `fitz.Document` nuevo (a diferencia de `merge_pdf()` de `main_window.py`, que añade uno solo al final del documento ya abierto); avisa con `ValueError` claro si alguno está protegido con contraseña. |
| [color_picker.py](color_picker.py) | ~130 | (r41, paleta de r42) **El selector de color de toda la app**: tabla fija de 17 colores, la paleta de Ricardo con sus nombres (recuadros de 16 px, dos filas de 9) y, si la herramienta la admite, opacidad en el mismo cuadro. `PALETTE` y `_NOMBRES` son la única fuente de verdad de la paleta. `choose()` devuelve (color, opacidad) o None; `nearest()` marca el más parecido al actual. |
| [dialogs.py](dialogs.py) | ~455 | Diálogos: rango de páginas, marca de agua, encabezado/pie, seguridad, propiedades, opciones de firma (QSettings), exportar imágenes, atajos. |
| [history.py](history.py) | ~85 | `UndoStack` de instantáneas en bytes (máx. 40 pasos / 400 MB). |
| [signature_validation.py](signature_validation.py) | ~190 | Validación pyHanko contra el almacén ROOT/CA de Windows **y la lista de confianza de España** (r43, `_bundled_trust_anchors` lee `vendor/trust/es_tsl.pem`), sin red. (r37) `_open_reader` abre en modo tolerante los PDF que pyHanko rechaza en estricto (invariante 24). (r61) `SignatureReport.revision` (revisión del PDF en que se firmó: la mayor es la más reciente). |
| [create_trust_list.py](create_trust_list.py) | ~220 | (r43, **firma XAdES comprobada de verdad en r44**) Genera `vendor/trust/es_tsl.pem`: LOTL de la UE → **verificar su firma contra `vendor/trust/oj_signers.pem`** (`verificar_firma`, aborta con `FirmaNoValida` si no cuadra) → puntero de España **y el certificado que la LOTL declara que debe firmarlo** (`puntero_es`) → TSL → **verificar su firma contra ese certificado** → servicios `CA/QC` y `TSA/QTST` concedidos, sin caducar y no exclusivos de web (`seleccionar`, `escribir`). La biblioteca estándar, `asn1crypto` y, **solo para generar** (no la usa la app), `signxml` (`pip install signxml`). `--reanclar` vuelve a extraer `oj_signers.pem` a un `.nuevo` para revisar a mano (no se sobrescribe solo). Hay que **volver a ejecutarlo antes de la «Próxima actualización»** de la cabecera del PEM (2027-02-02 a 21/09/2026). |
| [inspect_signature.py](inspect_signature.py) | ~55 | (r43) Diagnóstico por consola: `python inspect_signature.py [pdf]` enseña el veredicto de cada firma y su cadena con el ancla que la respalda (Windows o TSL). Usa `_open_reader`, así que abre también los PDF con xref irregular. |
| [signer_backend.py](signer_backend.py) | ~420 | `PAdESSigner.sign_pdf_bytes` (bytes→bytes, TSA, certificación, campo único) + sello visual `_SpanishCertTextStamp`. (r61) `remove_last_signature`: vuelve a la versión del archivo anterior a la última firma (`_revision_end`) y deja su recuadro vacío (invariante 27, g). Mantiene `sign_pdf_visible_with_widget` por compatibilidad. |
| [create_signature_background.py](create_signature_background.py) | ~130 | (r9) Genera `signature_background.pdf` desde `MOSCA.svg` (o el SVG pasado) con Edge/Chrome headless `--print-to-pdf`. En una copia temporal convierte las `<mask>` de color sólido en `<clipPath>` + opacidad (r12) y amplía la región de las demás. Solo se usa al cambiar el logotipo. |
| [utils.py](utils.py) | ~200 | `PDFUtils`: FreeText rich-text, Ink, Square redondeado, codificación de estilo. (r13: fuera `add_image_stamp` y `add_emoji_stamp`.) (r24) `TOOLTIP_QSS`: estilo único de los tooltips (crema #FFF8DC). |
| [emoji_font.py](emoji_font.py) | ~260 | (r40) **Noto Emoji** (monocroma, vectorial) en un Stamp (`/Subj EmojiNoto|c#RRGGBB|aX`): el glifo se escribe con la fuente incrustada, en el color y la transparencia elegidos (`style_token`, `parse_style`). `catalog()` (1391 emojis de `vendor/emoji/emojis.json`), `search(texto, grupo)` sin tildes en español e inglés, `groups()`, `find`, `box_size` (avance × alto de la fuente), `write_rect()`, `is_emoji`/`is_stamp`/`is_sized`. `LEGACY_SUBJECTS` / `STAMP_SUBJECTS` / `SIZED_SUBJECTS` para los antiguos. |
| [firma_manuscrita.py](firma_manuscrita.py) | ~370 | (r68) **Firma manuscrita** sin Qt: `HandSignature` (trazos `(x, y, t)` + grosor + color, o PNG), geometría de estilográfica (`ink_pieces`: suavizado, Catmull-Rom, radio por **ángulo del bisel** `NIB_ANGLE` y **velocidad**, gota al apoyar, y corte en piezas donde el trazo se cruza a sí mismo), `piece_shapes` (bordes + círculos, misma orientación), `pdf_ops` (una pieza = un relleno `f` con `/ca INK_ALPHA`), `fit_rect` y `add_hand_signature` (Stamp `/Subj FirmaManuscrita|trazo` o `|img`). |
| [firma_manuscrita_ui.py](firma_manuscrita_ui.py) | ~360 | (r68) Diálogo «Firma manuscrita»: pestaña **Dibujar** (`SignatureCanvas` 640 × 220 con línea de firma, color con `dialogs.ColorButton`/`color_picker`, grosor 1–12 px, deshacer trazo, borrar) y pestaña **Imagen** (`load_signature_image`: reduce a 1600 px, vuelve transparente el papel con rampa de luminancia 170→235 y recorta; numpy importado dentro). `paint_ink`/`preview_image` pintan con la misma geometría que el PDF. Recuerda `firma/color`, `firma/grosor`, `firma/trazos` y `firma/pestana` en QSettings. |
| [presentacion.py](presentacion.py) | ~330 | (r70) **Presentación inicial** (`WelcomeDialog`, sin marco, 640 × 510): réplica en código de la maqueta `popup_temp.png` (degradado turquesa → luz central → salmón, icono, «AventyaPDF» en #17355E, barra-cápsula con la plumilla `signature`, copyright con el año actual). `SLIDES` (11 diapositivas: icono Fluent, título, texto) avanzan solas cada `SLIDE_MS` = 7 s con la barra llenándose de forma continua; se paran con el ratón encima; ‹ Anterior / Siguiente › / Empezar, ← →, Esc, arrastrable. `should_show`/`set_show` (`inicio/presentacion` en QSettings). `show_welcome(parent, only_if_enabled)` la abre con `open()` (no bloquea `procesar_argumentos`). |
| [emoji_picker.py](emoji_picker.py) | ~150 | (r36) `EmojiPicker`: buscador, grupo y cuadrícula `IconMode` con todos los emojis, dibujados con Noto Emoji en el color elegido (`set_color`; `NoFontMerging` o Qt los sustituye por Segoe UI Emoji). Iconos por lotes (primero los visibles) y en caché; no impone ancho al panel. |
| [icons.py](icons.py) | ~180 | (r36) Iconos **Fluent UI System Icons** (`ICONS` clave→nombre, `glyph()` desde el JSON) y fuentes **Noto** (`noto_path`, `noto_family`, `CSS_TO_NOTO`); `load_fonts()` las registra en Qt (lo llama `MainWindow`). |
| [pdf_compression.py](pdf_compression.py) | ~200 | (r15) Compresión tipo **Acrobat + iLovePDF**, sin Qt. `LEVELS`: baja (150 ppp, JPEG 85, sin pérdida se mantiene), recomendada (100 ppp, JPEG 70), extrema (75 ppp, JPEG 50); blanco y negro en FAX a 300/200/150. `compress(data, nivel, password, encryption)`: **reescritor de imágenes propio** (no `rewrite_images`, invariante 25) que reduce cada imagen si supera 1,5 veces la resolución necesaria, calculada por colocación: `max(nivel, 75 ppp × factor A4)`, así que **ninguna baja de 75 ppp en DIN A4**. Además `subset_fonts` (salvo formularios), `scrub` solo de miniaturas y guardado con `garbage=4`, `use_objstms` y `compression_effort=100`. (r35) Capa de texto de OCR compactada (`compact_ocr_text`, `_ocr_forms`) en un segundo guardado sin `clean`. Red de seguridad por avisos de MuPDF. Devuelve `Result` con tamaños, contadores, `min_print_ppi` y `note`. (Sin «blanco y negro»: las imágenes de 1 bit no se tocan.) |
| [tesseract_setup.py](tesseract_setup.py) | ~250 | (r16) **Tesseract OCR obligatorio**, sin Qt. `find_tesseract` (PATH, rutas típicas, registro `InstallDir`). `ensure(langs, report)` instala a la fuerza (`winget install UB-Mannheim.TesseractOCR --silent` y, si falla, el instalador oficial con `/S` como administrador) y descarga los modelos **`tessdata_best`** (r17; marca `<lang>.traineddata.best`, los que no la llevan se sustituyen) a `TESSDATA_DIR` (`CORE_LANGS` = spa, eng, osd). `configure_environment` fija `TESSDATA_PREFIX` y el PATH; (r60) `ensure_pdf_font` copia `pdf.ttf` (letra invisible de la capa de texto) de la instalación a `TESSDATA_DIR`; `verify_ocr` reconoce un texto de prueba por el mismo camino que la app (`pdf_ocr`). En consola (`python tesseract_setup.py`, lo usa `run.ps1`) sale con código 0 o 1. |
| [pdf_ocr.py](pdf_ocr.py) | ~330 | (r17) **OCR de alta precisión**, sin Qt. `ocr_page(page, lang)`: (r60) quita la capa de un OCR anterior (`remove_previous_ocr`, texto invisible), orientación con `tesseract --psm 0` **comprobada** (`detect_rotation` → `_osd_rotation` + `_mean_confidence`), página en gris a 400 ppp con el texto ya seleccionable tapado en blanco, enderezado si está torcida ≥ 1° (`skew_angle`), y **`tesseract.exe` directo** con Sauvola y `textonly_pdf` (`_text_layer`; antes `pdfocr_tobytes` de MuPDF con contraste estirado y conversión a RGB). Después se quita la imagen de la página de Tesseract (el `Do` **y**, desde r35, la entrada de `/Resources`: si no, `show_pdf_page` copiaba una imagen oculta a 400 ppp por página) y se superpone solo su capa de texto invisible sobre la **página original** (`show_pdf_page(overlay=True)`); la rotación se restaura. Devuelve las palabras añadidas. (r18) `render_dpi` limita la resolución en páginas enormes (36 Mpx, 32.000 px por lado, mínimo 20 ppp). |
| [pdf_edit.py](pdf_edit.py) | ~700 | (r21, **párrafos en r22**) **Edición del contenido real de la página**, sin Qt. `text_blocks(page)` e `images(page)` devuelven lo editable (**párrafos** con fuente, tamaño, color, negrita, «mezcla de estilos», interlineado real, primera línea base, descendente y alineación; y una entrada **por aparición** de cada imagen), `block_at`/`image_at` lo buscan por un punto. `replace_block(page, block, texto, rect=…)` borra el párrafo por **redacción** línea a línea (`fill=False`, `IMAGE_NONE` + `LINE_ART_NONE`) y lo reescribe **reajustado al cuadro** (`wrap`, `needed_height`, `clamp_box`); `delete_block`; `delete_image`, `place_image` (sustituir, mover, redimensionar) e `image_bytes`. `resolve_font` traduce el nombre de la fuente del PDF a una de Windows (la incrustada no vale, invariante 32) con su tabla `_FAMILIES`, variantes de negrita/cursiva y respaldo base-14; `_covering_font` busca otra si faltan glifos. `EditResult` lleva los avisos y si el texto se sale. `is_shared` (recorre el documento, solo bajo demanda). |
| [inplace_editor.py](inplace_editor.py) | ~150 | (r23) **Cuadro de escritura sobre la propia página**, compartido por toda la app: herramienta Texto, notas, edición de anotaciones y «Editar contenido». `InPlaceEditor(QPlainTextEdit)` con `apply_style` (familia, tamaño, negrita, cursiva, color y alineación, para que lo que se escribe sea lo que se ve), `needed_height`, `enable_autogrow` (crece y mengua al escribir sin pasar del borde de la página) y las señales `committed` / `cancelled` / `moved`. Teclas iguales en todos los sitios: Intro línea nueva, **Ctrl+Intro** confirma, Esc cancela, Tab / Mayús+Tab van al siguiente o anterior. |

| [edit_ui.py](edit_ui.py) | ~500 | (r21, **párrafos en r22**) `ContentEditor` del visor: recuadros discontinuos sobre cada párrafo e imagen, resalte al pasar, cursores (I, mover, redimensionar), **editor multilínea sobre el cuadro** (Intro abre línea, Ctrl+Intro confirma, Esc cancela, Tab/Mayús+Tab por orden visual), **tiradores que estiran el cuadro y reajustan el texto** (`_resized`, `_handle_points` fuera del cuadro), marco rojo y recuadro hasta donde llega el texto cuando no cabe, menú contextual (editar/eliminar texto; sustituir/guardar/eliminar imagen, avisando si está repetida), arrastrar y redimensionar imágenes sin deformarlas, y `apply_style` desde la barra secundaria. Un paso de deshacer por cambio (`_apply`) y los avisos a la barra de estado. |
| [pdf_forms.py](pdf_forms.py) | ~300 | (r17) **Formularios con el JavaScript de MuPDF**, sin Qt. `enable_js`, `set_text` / `choose` (con eventos: formato, validación, cálculos), `toggle` (casillas y radios, con apagado de hermanos sin `/Parent`), `press` (botones). Devuelve `FormEvent` (alert, url, print, mail, submit, named, goto, launch…). Además `values()` y `field_boxes(page)` para la interfaz. Captura los avisos envolviendo el JavaScript en `with(__agpdf.scope)` (invariante 28). |
| [form_ui.py](form_ui.py) | ~260 | (r17) `FormController` del visor: caché de campos (`refresh` desde `render_page`), resaltado, cursor, **editor en línea** (`QLineEdit`/`QPlainTextEdit` sobre el campo; Intro, Esc, Tab/Mayús+Tab), menú para listas, botones y `handle_events` (mensajes, abrir URL con confirmación, imprimir, navegar; no envía formularios ni abre archivos). `_apply` crea un paso de deshacer y lo descarta (`UndoStack.discard_last`) si no cambia ningún valor. |
| [tesseract_ui.py](tesseract_ui.py) | ~95 | (r16) Parte Qt: instalación en un `QThread` con `QProgressDialog` modal sin cancelar. `ensure_at_startup()` (main.py) devuelve `(disponible, motivo)` y, si falla, avisa y la app sigue con el OCR desactivado. `ensure_languages()` (antes de reconocer) instala lo que falte del idioma elegido. |
| [create_emoji_index.py](create_emoji_index.py) | ~100 | (r40) Genera `vendor/emoji/emojis.json`: los emojis que dibuja Noto Emoji (uno por carácter), en el orden de emoji-test.txt, con grupo y nombres en español de CLDR. |
| [create_app_icon.py](create_app_icon.py) | ~110 | (r57, r64) Desde `ICONO.png` genera `vendor/icono/aventyapdf.ico` con los 14 tamaños oficiales de Windows (16, 20, 24, 30, 32, 36, 40, 48, 60, 64, 72, 80, 96 y 256 px), cada uno reducido por separado desde el original con Lanczos; desde 24 px deja el margen de Windows 11 (1/16 del lado) y hasta 48 px enfoca el color (no el alfa: halo). (r64) También genera las imágenes del asistente de Inno Setup en `empaquetado/imagenes/` (pequeña y lateral, a 100/150/200/250 %). Necesita Pillow **solo para generar** (importado dentro de las funciones, para que las pruebas lean `TAMANOS` y las tablas sin Pillow); la app lee el `.ico` con Qt. |
| [cert_manager.py](cert_manager.py) | 441 | Identidad: almacén Windows `MY`, exportación a PFX temporal, persistencia (`QSettings` + `keyring`), `CertPickerDialog`. Sin cambios desde r3. |
| [create_test_cert.py](create_test_cert.py) | ~70 | `build_test_pfx()` (r5: API con zona horaria, `KeyUsage` firma + no repudio, 3 años) y `generate_test_pfx()` → `test_certificate.pfx` (contraseña `1234`) junto al script. |
| [run.ps1](run.ps1) | ~215 | Lanzador: entorno en `%LOCALAPPDATA%\aventyapdf\venv`. (r33) Si no hay Python compatible **lo instala** (winget y, si falla, python.org, para el usuario); recrea un entorno roto; en cada arranque `dependencias.py` instala lo que falte; luego Tesseract. **`-Pruebas`** ejecuta `tests/` en modo offscreen. (r55) Cualquier argumento que no sea uno de sus `switch` propios (`-ArgumentosApp`, `ValueFromRemainingArguments`) se reenvía tal cual a `main.py`: lo usa `Install-ContextMenu.ps1`. |
| [Install-ContextMenu.ps1](Install-ContextMenu.ps1) | ~120 | (r55) Instala/quita (`-Quitar`) el menú contextual del Explorador, solo `HKEY_CURRENT_USER` (sin administrador): sobre `.pdf`, verbo directo «Combinar con AventyaPDF»; sobre imágenes (`IMAGE_EXTS` de `window_document.py`), submenú «AventyaPDF» con «Convertir a un PDF» / «Convertir a varios PDF». Todas las entradas con `MultiSelectModel=Player` (una sola invocación con todos los archivos seleccionados) que llama a `run.ps1` con `--combinar-pdf` / `--imagenes-a-pdf` / `--imagenes-a-pdfs-separados`. Parámetro `-Raiz` (uso interno, pruebas) para no tocar el menú contextual real. |
| [autodiagnostico.py](autodiagnostico.py) | ~150 | (r62) `AventyaPDF.exe --autodiagnostico informe.json [cert.pfx clave]` (lo intercepta `main.main()`): comprueba sin ventana archivos incluidos, ventana, OCR, exportar a Word, sellado de tiempo y firma, y escribe el JSON. Lo usa `construir.ps1` sobre el ejecutable empaquetado. |
| [empaquetado/](empaquetado/) | — | (r62) `construir.ps1` (todo el proceso), `AventyaPDF.spec` (PyInstaller), `preparar_tesseract.py` (Tesseract dentro, solo las DLL que importa), `AventyaPDF.iss` (Inno Setup; `AppId` fijo, no cambiarlo), `version_info.txt` (lo genera `construir.ps1`), `salida/` (el instalador). Ver `docs/empaquetado.md`. |
| [prototipos/winui3/](prototipos/winui3/) | — | (r66) Prueba de concepto de interfaz WinUI 3 desde Python (PyWinRT): `visor_poc.py` y `visor_poc.spec`. **No es parte de la app** ni la importa nada; usa su propio entorno (`%LOCALAPPDATA%ventyapdfenv-winui3`). Ver `docs/plan_migracion_winui3.md` §10. |
| [dependencias.py](dependencias.py) | ~150 | (r33) Sin dependencias externas. `faltan()` compara `requirements.txt` (solo `nombre>=x.y`) con `importlib.metadata`; `asegurar()` instala con pip lo que falte y lanza `DependenciasError` si sigue faltando; `asegurar_o_salir()` lo usa `main.py` antes de importar PyQt6. |
| [tests/test_nucleo.py](tests/test_nucleo.py) | ~2.020 | Pruebas sin Qt: `doc_tools`, `history`, cifrado, **firma PAdES doble + validación** con certificado generado al vuelo, lista de confianza (r43), XAdES (r44). (r55) `TestConversion.test_combinar_varios_pdf_en_uno` / `test_combinar_pdf_protegido_da_error_claro` para `doc_tools.merge_pdfs`. |
| [tests/test_interfaz.py](tests/test_interfaz.py) | ~1.720 | Prueba de humo de `MainWindow` offscreen con `QMessageBox` simulados; restaura las claves de QSettings que toca. (r55) Pruebas de `combine_pdfs_from_paths`, `create_separate_pdfs_from_images` y `main.procesar_argumentos` (los cuatro indicadores, incluido el «abrir con» normal sin indicador). |

### 2.2 Recursos y artefactos

| Ruta | Nota |
| :-- | :-- |
| [requirements.txt](requirements.txt) | PyQt6 ≥6.5, PyQt6-WebEngine, **PyMuPDF ≥1.24** (`fullcopy_page`, `bake`, `Font.text_length`), pyHanko ≥0.20, pyhanko-certvalidator, cryptography ≥41, keyring ≥24, (r33) **pdf2docx ≥0.5.6** (ya no es opcional; `requirements-opcional.txt` se borró). Todo obligatorio. |
| `%LOCALAPPDATA%\aventyapdf\tessdata` | (r16) Idiomas de OCR (`*.traineddata`, modelos estándar de github.com/tesseract-ocr/tessdata), sin permisos de administrador. `TESSDATA_PREFIX` apunta aquí. |
| `%LOCALAPPDATA%\aventyapdf\venv` | Entorno real del equipo de Ricardo (visto en r5): **Python 3.13.13, PyMuPDF 1.28.0, pyHanko 0.36.2, pyhanko-certvalidator 0.31.4, PyQt6 6.11.0, cryptography 49.0, keyring 25.7**. (r33) Instalado `pdf2docx` 0.5.13 (con numpy, opencv-python-headless, python-docx); `requirements.sha256` ya no se usa. Ejecutable desde las herramientas. (r56) Movida de `%LOCALAPPDATA%\antigravity-pdf` a `%LOCALAPPDATA%\aventyapdf` sin reinstalar nada. |
| `%LOCALAPPDATA%\aventyapdf\errores.log`, `fallos_graves.log` | Registro de errores (r5). Lo primero que hay que pedir si algo falla. |
| `.venv/` | ⚠️ Inservible (de otro equipo). No usarlo. Ver §8. |
| `__pycache__/` | `.pyc` de varios intérpretes; prescindible. |
| `test_certificate.pfx` | Certificado de pruebas (`1234`). Regenerable con `create_test_cert.py`. |
| `vendor/fonts/` | (r36) `fluent-icons/` (FluentSystemIcons-Regular.ttf + .json + LICENSE, MIT): **la única fuente de iconos de la app**. `noto/` (Noto Sans, Serif: 4 estilos; Sans Mono: normal y negrita; OFL.txt): fuente **base** del PDF y de la app. (r40) `noto-emoji/` (NotoEmoji-Regular/Bold + OFL.txt): los emojis. |
| `vendor/trust/es_tsl.pem` | (r43) **Lista de confianza de España (TSL)**: 202 certificados de servicios cualificados (a 21/09/2026, emisión nº 188), con nombre, proveedor y SHA-256 en comentarios sobre cada bloque. La lee `signature_validation`. **Generado** con `create_trust_list.py` (r44: solo tras comprobar su firma XAdES); no editar a mano. |
| `vendor/trust/oj_signers.pem` | (r44) **Ancla de confianza de la Comisión Europea** (6 certificados) para comprobar la firma de la LOTL antes de creerse su contenido. Procedencia en la cabecera del propio archivo: extraídos del `keystore.p12` del proyecto **DSS** (implementación de referencia de la Comisión para eIDAS), contrastado porque la URL del Diario Oficial que ese DSS tiene configurada coincide exactamente con la que la LOTL en vivo declara como la suya. **No** es la lectura literal de la tabla del DOUE (EUR-Lex no se pudo leer, es una SPA). Es un almacén de raíces: no se regenera solo, `create_trust_list.py --reanclar` escribe un `.nuevo` aparte para revisar a mano. |
| `vendor/emoji/` | (r40) `emojis.json`: 1391 emojis con grupo y nombres en español. Generado con `create_emoji_index.py`. |
| `vendor/icono/` | (r57) `aventyapdf.ico`: icono de la aplicación (ventana, barra de tareas, «Acerca de», menú contextual del Explorador, ejecutable, instalador y desinstalador). Origen: `ICONO.png` de la raíz, aportado por Ricardo (r64: icono nuevo); se regenera con `create_app_icon.py`. `ICONO.svg` **no** sirve de origen: no es vectorial, solo envuelve el mismo PNG de 596 px. |
| `MOSCA.svg` | (r9, **nuevas versiones en r28 y r65**) Logotipo de fondo del sello, aportado por Ricardo. Desde r28 viene de Affinity (viewBox 596×596, trazos turquesa de huella + «A» blanca, sin máscaras ni imágenes). (r65) Añade detrás un degradado radial salmón que se desvanece a transparente (`<radialGradient>` con alfa). La versión de r9 era de Inkscape con máscaras y degradados con alfa. **No modificarlo desde el código.** |
| `signature_background.pdf` | (r9) **Generado** con `create_signature_background.py`: MOSCA.svg en PDF vectorial (1 página, 1688,88 pt² desde r28 —el tamaño no importa, el sello escala por el alto—, sin imágenes, fondo transparente). (r65) ~14,6 KB: Edge exporta el degradado con alfa como sombreado radial con máscara suave de luminosidad (`/SMask /S /Luminosity`, grupo de formulario **vectorial**, no imagen: no reaparece la línea de r12). Lo lee `signer_backend.BACKGROUND_PDF` en cada firma. Regenerar si cambia el SVG. |
| `Compartimentar.odt` | Documento ajeno al código. |

### 2.3 Arquitectura en capas

```
main.py (QSS, excepthook)
  └─ MainWindow ──┬─ DocumentMixin (window_document) ── history, doc_tools, signer_backend, cert_manager
                  ├─ MenusMixin    (window_menus)    ── dialogs, doc_tools
                  ├─ PDFViewerWidget (viewer)        ── utils.PDFUtils, doc_tools, dialogs
                  ├─ SidePanel (sidebar)             ── doc_tools, signature_validation (vía MainWindow); miniaturas propias
                  └─ CertPickerDialog
doc_tools / history / signature_validation / signer_backend: sin Qt (probados en tests/test_nucleo.py)
```

Acoplamiento deliberado: `viewer.main_window` y `sidebar.mw` apuntan a la
ventana; ambos llaman a su API pública (`checkpoint`, `mark_modified`,
`render_page`, `go_to_page`, `add_text_markup`…). Los mixins no tienen
`__init__`: el estado se crea en `_init_document_state()` y los widgets en
`_setup_ui()` (orden: menús → barras → búsqueda → aviso → splitter[sidebar, visor]).

## 3. Modelo de interacción (UI)

- **Menús**: Archivo · Edición · Ver · Comentar · Organizar · Herramientas ·
  Proteger · Firmar · Ayuda (r54: «Editar contenido» ya no tiene menú propio,
  pasó a Herramientas › «Editar texto e imágenes del PDF»). Las acciones que
  necesitan documento están en `_doc_actions` y se (des)habilitan en
  `_update_actions()`. Atajos: ver `dialogs.SHORTCUTS` (F1). Letras sueltas
  V/T/N/H/M/R/E seleccionan herramienta (r49: fuera X, era Redactar).
  `Esc` es un `QShortcut` de ventana (`_on_escape`): cierra búsqueda → sale de
  la herramienta → quita selección.
- **Escribir en el PDF nunca abre una ventana** (r23, `inplace_editor`): el
  texto se teclea **sobre la propia página**, en el sitio donde va a quedar y
  con la pinta que va a tener. Vale para la herramienta **Texto** (clic, o
  arrastrar un cuadro, y a escribir; el cuadro crece solo según se escribe y la
  barra secundaria cambia tamaño, color, negrita, cursiva y alineación **en
  vivo**), la **nota adhesiva** (cuadro amarillo donde se hace clic), **editar
  una anotación** (doble clic sobre ella) y «Editar contenido». Teclas iguales
  en todos los sitios: **Intro** abre línea, **Ctrl+Intro** confirma, **Esc**
  cancela, **Tab / Mayús+Tab** pasan al siguiente o anterior. Pulsar en otro
  sitio de la página también confirma. Ya no existe el diálogo de texto.

- **Barra superior** (`#topbar`): panel lateral │ abrir · guardar · imprimir ·
  comprimir · deshacer · rehacer │ ◀ [nº página editable] / N ▶ │ zoom · ajustar │
  texto · nota · resaltar/subrayar/tachar · rectángulo · emoji · borrador ·
  **editar contenido** │ firma · páginas … buscar. (r49: fuera «redactar»,
  la app ya no tiene herramienta de redacción.)
- **Botón «Operaciones de página»** (r27): **no hay ventana de organizar**.
  Es conmutable (`_set_pages_mode`): abre el panel de miniaturas en modo
  organizar (arrastrar reordena, Supr elimina, Ctrl/Mayús seleccionan varias)
  y, arriba, `_pages_panel` con el recuento y siete botones (girar izquierda /
  derecha, duplicar, eliminar, insertar en blanco, insertar otro PDF, extraer).
  Sin selección actúa sobre la página actual. Todo al momento y con deshacer.
  Sale con el botón, Esc, otra herramienta, zoom 100 %, compresión, seleccionar
  una anotación o cambiar/cerrar el panel; si abrió el panel, lo vuelve a
  cerrar. Menú Organizar › «Organizar páginas en el panel lateral».
- **Opciones de herramienta** (r26, petición de Ricardo): `_zoom`, `_txt`,
  `_note`, `_markup`, `_mrk`, `_rect`, `_emoji` y `_edit` van **arriba del panel
  lateral** (`SidePanel.tools`, dentro de `SidePanel.column`, mismo `QVBoxLayout`
  que `stack`): ocupan su ancho y **lo empujan hacia abajo** (r26; r46 probó a
  superponerlas con `_ToolOverlay` para no desplazar nada, pero r50 —petición
  de Ricardo: la herramienta y lo que ya se veía en el panel deben estar
  disponibles a la vez— deshizo la superposición y volvió al empuje; con scroll,
  lo que se veía antes sigue alcanzable); filas «etiqueta explícita · control»
  de una línea, sin iconos sueltos. Si el panel estaba cerrado se abre la
  columna solo con las opciones (la preferencia `view/sidebar` sigue
  dependiendo solo del `stack`). **Barra secundaria** (`#options_row`): solo
  `_sign` y `_compress` (r49: fuera `_redact`), en la columna derecha del
  divisor **encima del visor**, y esa sí sin desplazar el panel lateral (r46).
  `_show_only_tool_panel(mode)` gobierna ambos grupos y `_refresh_opt_row()`
  (con `isHidden()`) decide qué se ve.
- **Modos del visor**: `NONE` · `TEXT` · `NOTE` · `MARKUP` ·
  `RECT` · `EMOJI` · `ERASE` · `SIGN` · `EDIT` (r49: fuera `REDACT`; r59: fuera `HIGHLIGHT`, absorbido por `MARKUP`). `MARKUP`
  queda activo tras cada uso (como Acrobat); el resto vuelve a `NONE`.
- **Modo NONE**: clic en anotación = seleccionar/mover/redimensionar; arrastrar
  sobre texto = seleccionar texto (Ctrl+C, clic derecho → resaltar/subrayar/
  tachar/ondulado); pasar sobre una nota muestra su contenido.
  **Cursor** (r17): «I» sobre texto seleccionable (`viewer._word_at`, también el
  texto de OCR), «I» sobre campos de texto, mano sobre casillas, listas y botones,
  flecha sobre campos de solo lectura.
- **Editar contenido** (r21, **por párrafos desde r22**; `edit_ui`, tecla **C**,
  menú Herramientas › «Editar texto e imágenes del PDF», r54: antes tenía su
  propio menú «Editar contenido» en la barra): cambia el texto y las imágenes
  que **ya están en el PDF**, no anotaciones encima. Con la herramienta
  puesta, cada **párrafo** lleva
  un recuadro discontinuo azul y cada imagen uno verde, y lo que hay bajo el
  cursor se resalta. **Texto**: clic = editor de varias líneas sobre el propio
  cuadro del párrafo; **el texto se reajusta al cuadro** (se reparte en tantas
  líneas como quepan en su ancho, respetando el interlineado, la alineación y la
  primera línea base originales) y **estirando una esquina** se hace más alto o
  más ancho y el texto se vuelve a repartir. Intro abre línea nueva,
  **Ctrl+Intro** confirma, Esc cancela y Tab / Mayús+Tab van al párrafo
  siguiente o anterior **por orden visual**. La barra secundaria enseña la
  fuente, el tamaño, el color y la negrita/cursiva, y **en vivo** cuántas líneas
  ocupa y si cabe; si no cabe, el cuadro y sus tiradores se pintan en **rojo** y
  un recuadro discontinuo enseña hasta dónde llega el texto. Dejarlo vacío borra
  el párrafo; el menú contextual también. **Imágenes**: clic la selecciona
  (borde y cuatro tiradores), se arrastra, se redimensiona **sin deformarla**,
  Supr la borra y el menú contextual la sustituye por un archivo o la guarda,
  avisando si esa imagen está colocada en más sitios. Ningún cuadro puede
  salirse de la página (`clamp_box`). Cada cambio es un paso de deshacer y los
  avisos (fuente sustituida, caracteres sin glifo, texto que no cabe, estilos
  mezclados) salen en la barra de estado. **No se ofrecen** el texto de las
  anotaciones ni de los campos, ni las imágenes sin xref (invariantes 33 y 34).
- **Formularios** (r17, `form_ui`): campos resaltados en azul (Ver › Resaltar
  campos de formulario, `view/highlight_fields`); clic en campo de texto = editor
  en el propio campo (Intro confirma, Esc cancela, Tab/Mayús+Tab pasa al
  siguiente o anterior); casillas y radios con un clic; listas con menú (y
  «Escribir otro valor…» si es editable); botones ejecutan su JavaScript y sus
  acciones (mensajes, abrir enlace con confirmación, imprimir, página
  siguiente…). Calcula y valida como Acrobat.
- **Firma manuscrita** (r68, petición de Ricardo): en la barra de Firma, tras el
  certificado, el botón de la **plumilla** (`_btn_handsign`, icono Fluent
  `calligraphy_pen`: la fuente de iconos incluida no tiene sello de caucho).
  Abre el diálogo (dibujar con el ratón o cargar imagen); al aceptar, el botón
  queda marcado y la herramienta Firma **estampa la firma manuscrita** en vez
  de pedir el recuadro de la firma digital: un **clic** la centra a 160 pt de
  ancho, **arrastrar** la encaja en el recuadro sin deformarla, y mientras
  tanto se ve translúcida bajo el cursor. Nunca se sale de la página. Esc, la
  segunda pulsación o cambiar de herramienta la sueltan. Después es una
  anotación más: se selecciona, se mueve y se redimensiona (con proporción),
  se borra y se deshace; no abre panel de opciones. También en el menú
  Firmar › «Insertar firma manuscrita (dibujada o imagen)…». **No es una firma
  digital**: no tiene valor criptográfico.
- **Presentación inicial** (r70, petición de Ricardo, diseño de `popup_temp.png`):
  al arrancar (`main.main`, 250 ms después de `window.show()`) sale la
  presentación que va explicando las características; la casilla «No volver a
  mostrar al iniciar» la desactiva (`inicio/presentacion = false`, se guarda al
  cerrarla de cualquier forma). Ayuda › «Presentación de AventyaPDF» la vuelve a
  abrir siempre, con la casilla como esté: desmarcarla la reactiva. Las pruebas
  crean `MainWindow` directamente y no la ven salir.
- **Campo de firma del formulario** (r38): el recuadro de firma vacío se pulsa
  como cualquier otro campo y arranca la firma **dentro de él**
  (`form_ui` → `sign_in_field` → `signer_backend.sign_pdf_bytes(field_name=…)`);
  si ya está firmado, lo dice la barra de estado. (r39) Ahí se pide **siempre**
  el certificado (`choose_cert=True`), antes que el diálogo de opciones: en ese
  camino no hay barra que enseñe cuál se usaría y, si no, firmaría con el de la
  sesión anterior. Con la herramienta Firma solo se pregunta si no hay ninguno
  guardado, porque su panel lo muestra y permite cambiarlo.
- (r38) **Ya no hay formularios XFA**: se retiraron el visor (pdf.js en Qt
  WebEngine) y todo su modo de ventana. Un XFA dinámico se ve como lo pinta
  MuPDF («Please wait…»).
- **Rueda**: Ctrl+rueda = zoom; en el borde superior/inferior dos «muescas»
  pasan de página.
- **Panel lateral** (F4): colapsado muestra solo el rail (44 px). Se abre solo
  al cargar un documento si `view/sidebar` = true.
- **Varios documentos** (r20): abrir, arrastrar, «Nuevo PDF en blanco» y «Crear
  PDF desde imágenes» abren una pestaña nueva (ya no preguntan por descartar);
  abrir un archivo ya abierto solo cambia a su pestaña. Con dos o más, el rail
  muestra un separador y un botón por documento (tooltip con nombre y ruta, «●»
  si tiene cambios; clic derecho › Cerrar documento). Ctrl+Tab / Ctrl+Mayús+Tab
  cambian de documento. Cada uno conserva página, desplazamiento, deshacer,
  cambios y contraseña; el zoom es de la ventana. Cerrar
  pasa a la pestaña contigua; salir pregunta por cada documento con cambios.
- **Aviso superior** (`#doc_banner`): documento firmado / formulario / cifrado.
  El botón (`_banner_action`) abre el panel de firmas.
- **Zoom**: `"100"` (slider 10–800 %), `"width"`, `"height"` = **ajustar
  página entera** (min(ancho, alto)).
- **Errores inesperados** (r5): diálogo «Error inesperado» con el traceback en
  «Mostrar detalles»; la aplicación sigue abierta.

## 4. Invariantes técnicos — NO ROMPER

1. **Coordenadas.** El visor usa coordenadas de página PyMuPDF (origen
   arriba-izquierda) escaladas por `scale_factor`. **El único volteo a PDF
   nativo ocurre en `DocumentMixin._do_signature`**:
   `box = (x0, page_h - y1, x1, page_h - y0)`.
2. **Esquinas redondeadas de `Square`.** Re-aplicar
   `PDFUtils.apply_rounded_corners()` tras **cada** `annot.update()`.
3. **(r13) Emojis = Stamp con apariencia propia (`EmojiFluent` desde r36;
   antes `EmojiFont` y `EmojiImg`). Ni `annot.update()` ni `annot.set_rect()`**: ambos marcan la
   anotación como modificada y, al pintar, MuPDF regenera un sello estándar
   «APPROVED» con `/Rect` a proporción 3,8:1 (esa era la causa de los emojis
   aplastados). Mover y redimensionar con `emoji_font.write_rect()`, que escribe
   `/Rect` con `xref_set_key`; los metadatos también por xref. Al redimensionar,
   el visor fija la proporción (`viewer._keep_aspect`) y reescala `/T`.
   **(r14)** Insertar un emoji crea y **borra una página auxiliar**
   (`emoji_font._appearance`, r36): PyMuPDF recarga las páginas y los `Page` abiertos
   (p. ej. `viewer.pdf_page`) quedan huérfanos hasta `render_page`. Además una
   `Annot` solo guarda una **referencia débil** a su página: nunca
   `list(doc[n].annots())` y luego usar las anotaciones; guardar antes la página
   en una variable (si no, `ReferenceError` o incluso un acceso inválido en memoria).
4. **Emoji glifo antiguo (`EmojiStamp`).** FreeText de versiones anteriores (★);
   ya no se crea. Al redimensionar se recalcula `fontsize` en `/T`.
5. **Estilo de texto en `/Subj`** con `TXT|b|i|a|f|c`; tamaño en `/T`; texto en
   `/Contents`. Los saltos de línea se convierten en `<br/>` en el rich-text
   (`_text_richtext`).
6. **`_set_info_keys` vs `annot.set_info`** (set_info regenera la apariencia).
7. **FreeText rich-text** nace con línea de llamada → `CL null`.
8. **Trazos a mano alzada** (r59, `MARKUP` fuera del texto): se enderezan por **velocidad** (`viewer.straighten_stroke`: rápido y ≤ 18 % de desviación → recta; lento solo si ≤ 2 pt / 4 %), no por la forma sola como el antiguo `_maybe_straighten` (retirado: enderezaba también trazos lentos). Grosor en **puntos PDF** (`FREEHAND_WIDTHS`), ya no en píxeles divididos por `scale_factor`. Tipo en `/Subj` = `MANO|tipo`; el resaltado va con `/BM /Multiply`.
9. **Firmas intocables** (`AnnotSelection.is_signature`). Nota r5: en PyMuPDF
   1.28 `page.annots()` **ya excluye** Link, Popup y Widget, así que los
   índices de anotación nunca cuentan campos de formulario ni firmas.
10. **Índices de anotación volátiles** (`AnnotSelection.idx` posicional sobre
    `page.annots()`). Tras cualquier deshacer se limpia la selección.
11. **El documento se abre SIEMPRE desde bytes** (`fitz.open("pdf", data)`),
    nunca por ruta. Así Windows no bloquea el archivo y guardar encima funciona
    (temporal `*.agtmp` + `os.replace`). No volver a `fitz.open(path)` para el
    documento principal.
12. **`_clean_bytes` = bytes tal cual están en disco.** Si `_modified` es falso,
    *Guardar* y *Firmar* usan esos bytes sin reescribir. Es lo que mantiene
    válidas las firmas previas al añadir otra firma (firma incremental pura).
    Cualquier `doc.tobytes()/save()` sobre un PDF firmado **invalida sus firmas**:
    por eso se avisa antes de guardar o firmar con cambios.
13. **Regla de deshacer**: `checkpoint(etiqueta)` ANTES de mutar,
    `mark_modified(structure)` DESPUÉS. `structure=True` si cambian páginas
    (recalcula miniaturas/marcadores y descarta resultados de búsqueda). En el
    borrador el checkpoint es uno por arrastre (`_erase_checkpointed`). Las
    herramientas de menú usan `_run_doc_change`, que revierte con
    `_rollback_last()` si la operación lanza.
14. **Documentos cifrados**: al abrir se guarda la contraseña en `_password` y
    `_orig_encrypted`. Instantáneas, guardado y compresión usan
    `PDF_ENCRYPT_KEEP` y se reautentican al reabrir (`_open_bytes`).
    **`Document.tobytes()/save()` sin `encryption` DESCIFRA** (el valor por
    defecto es 1 = `PDF_ENCRYPT_NONE`): pasar siempre KEEP u opciones
    explícitas. `_encrypt_opts` (Proteger/Quitar seguridad) solo se aplica al
    guardar; tras guardar se reabre lo escrito (`_set_document`, que vacía el
    historial).
15. **Páginas de documentos cerrados**: tras deshacer/reemplazar, `viewer.pdf_page`
    apunta a una página huérfana hasta el siguiente `render_page`; no leer sus
    atributos sin `try` (ver `render_page`).
16. **Marcado de texto** (`Highlight/Underline/StrikeOut/Squiggly`) es
    `is_fixed`: no se arrastra ni redimensiona. Las notas (`Text`) se mueven
    pero no se redimensionan. `_apply_text_change` solo toca `FreeText`;
    `_edit_text_annot` trata `Text` como texto plano.
17. **Selección de texto**: `doc_tools.word_selection` usa el orden de
    extracción de `get_text("words")` (bloque, línea, palabra) y no selecciona
    nada si el punto inicial está a > 24 pt de cualquier palabra. La caché
    `viewer._words` se invalida en `mark_modified` y al cambiar de página.
18. **Organizador**: `QListWidget` en **ListMode + LeftToRight + wrapping**, no
    IconMode (en IconMode arrastrar solo recoloca y el orden se perdía). El
    número de página va pintado dentro del icono. `_sync_order()` aplica
    `doc.select(orden)` antes de cada operación y al aceptar.
19. **Panel lateral en QSplitter**: colapsado fija `maximumWidth` = ancho del
    rail; si no, el splitter deja un hueco. `_sync_splitter()` recoloca y
    re-renderiza en zoom ajustado.
20. **Firma en hilo**: `SignWorker(QThread)` solo ejecuta pyHanko; todo lo de
    Qt (guardar, reabrir, diálogos) ocurre en los *slots* del hilo principal.
    `closeEvent` y deshacer se bloquean mientras firma. Campo de firma único
    por firma (`Firma1`, `Firma2`…): reutilizar nombre hacía fallar la segunda
    firma. **(r5)** `succeeded`/`failed` se emiten *dentro* de `run()`: el hilo
    sigue vivo en esos slots. `deleteLater()` y `_sign_worker = None` van en
    el slot de **`finished`**, nunca antes.
21. **(r5) `sys.excepthook` es obligatorio.** Sin gancho propio, PyQt6 llama a
    `qFatal()` ante cualquier excepción no capturada en un slot y la app se
    cierra sin aviso. `main._install_error_handler()` debe instalarse antes de
    crear la `QApplication`; no sustituirlo por `sys.__excepthook__`.
22. **(r5) Rangos de PyMuPDF**: `fullcopy_page/copy_page(pno, to)` exigen
    `to ∈ [-1, n-1]` (tras la última página se pasa `-1`); `insert_pdf(start_at)`
    y `new_page(pno)` sí aceptan `n` (lo recortan / añaden al final).
23. **(r6) `fitz.Rect` no tiene `.center`** en PyMuPDF 1.28 (lanza
    `AttributeError`). El centro se calcula a mano:
    `fitz.Point((x0 + x1) / 2, (y0 + y1) / 2)`. `QRect.center()` de Qt sí existe.
24. **(r10) PDF que pyHanko rechaza en modo estricto.** Los de **referencias
    cruzadas híbridas** (tabla clásica + `/XRefStm`, habitual en Word/Acrobat;
    detección: `reader.xrefs.hybrid_xrefs_present`) y **(r37) los que dan
    `PdfReadError` al abrirlos**, como una tabla xref que declara un objeto más
    de los que anuncia el tráiler («Xref table size mismatch», notificaciones
    del Colegio de Registradores). Los visores los abren sin protestar, así que
    la app los lee en modo tolerante; lo criptográfico se comprueba igual.
    - Firmar (`signer_backend._tolerant_writer`): **sin firmas previas**
      se reescribe con PyMuPDF (`tobytes(..., encryption=KEEP)`, xref clásica) y
      se firma en estricto — es la única excepción a la invariante 12, y es
      segura porque no hay firmas que invalidar; **con firmas previas** se firma
      incremental con `IncrementalPdfFileWriter(..., strict=False)`.
    - Validar (`signature_validation._open_reader`): se reabre con
      `PdfFileReader(strict=False)`. Ojo: las firmas se leen **en diferido**, así
      que hay que recorrer `embedded_signatures` dentro del `try` para que el
      error salte a tiempo.
    - Pruebas: `tests/test_nucleo.pdf_hibrido()` fabrica una xref híbrida y
      `test_valida_y_firma_pdf_con_xref_irregular` baja el `/Size` del tráiler.
25. **(r15) No usar `Document.rewrite_images` de MuPDF.** Reconstruye los
    recursos de todos los formularios que recorre y pierde los `/Pattern` de los
    grupos con máscara suave. Rompía el sello de las firmas (fondo de Edge), los
    emojis de la paleta y cualquier PDF con esa estructura («cannot find Pattern
    resource 'P4'»), aunque no tocase ninguna imagen. `pdf_compression` reescribe
    solo los objetos imagen, en su xref. También: `page.get_image_info(xrefs=True)`
    decodifica todas las imágenes de la página y **lanza** si una tiene el
    `/ColorSpace` roto: usar `pdf_compression._image_infos`.
26. **(r16) Tesseract es obligatorio.** Se comprueba en `run.ps1` (salvo
    `-Pruebas`) y en `main.py` antes de crear la ventana, y se instala a la
    fuerza si falta. Si no se puede, `window.set_ocr_available(False, motivo)`:
    la acción `_act_ocr` queda desactivada aunque haya documento (lo respeta
    `_update_actions`) y se reintenta en el siguiente inicio. PyMuPDF lleva el
    motor de Tesseract dentro, pero los idiomas los busca en `TESSDATA_PREFIX` o
    con `tesseract --list-langs`, y el instalador no añade Tesseract al PATH: la
    app **debe** llamar a `tesseract_setup.configure_environment()`, y los
    idiomas van en nuestra carpeta, no en Archivos de programa.
    **(r33)** La misma regla vale para **todos** los complementos: Python
    (`run.ps1`) y los paquetes de `requirements.txt` (`dependencias.py`, desde
    `run.ps1` y lo primero de `main.py`). Un paquete nuevo se añade a
    `requirements.txt` y se instala solo en cada equipo. No se fuerzan
    Edge/Chrome (solo desarrollo). **(r36)** Iconos (Fluent UI System Icons),
    fuentes de texto (Noto) y emojis (Fluent Emoji) van dentro de `vendor/`, con
    su licencia: no dependen de Windows. Un icono nuevo = una entrada en
    `icons.ICONS` con el nombre de Fluent (falla al arrancar si no existe).
50. **(r36) El texto enriquecido de MuPDF ignora `font-family`.** Pida la
    familia que pida, el `/AP` de un FreeText sale con Charis SIL o Nimbus. Para
    escribir con Noto, `PDFUtils.apply_text_appearance` reescribe el `/AP /N`
    **después de cada `annot.update()`** de un FreeText de la herramienta Texto
    (crear, reeditar, mover, redimensionar, estilo). Si se añade otro sitio que
    llame a `update()` sobre un FreeText, hay que llamar también a esa función.
    Las fuentes incrustadas con `insert_font` son completas: se recortan al
    guardar sobre una copia (`bytes_with_subset_fonts`), nunca en el documento
    abierto (`insert_font` reutiliza el objeto y al siguiente texto le faltarían
    letras).
51. **(r36) Compresión: el texto escaneado nunca baja de 150 ppp / JPEG 75.**
    `looks_like_text` decide por histograma; si se cambian los umbrales, medir
    con OCR sobre texto de 6-8 pt en los tres niveles antes de darlo por bueno.
52. **(r45) Un campo de firma puede ser `/Sig` o `/DocTimeStamp`** (sello de
    tiempo de documento, sin firmante). `emb.sig_object_type` dice cuál es;
    pyHanko exige la función que toca (`validate_pdf_signature` para `/Sig`,
    `validate_pdf_timestamp` para `/DocTimeStamp`) y lanza si se le pasa el
    tipo equivocado («Signature object type must be /Sig», u opuesto). No
    asumir que todo lo que devuelve `reader.embedded_signatures` es `/Sig`.
53. **(r46, retirado en r50) `sidebar._ToolOverlay` ya no existe.** Colocaba
    `tools` encima de `stack` con `setGeometry()` a mano para que las opciones
    de herramienta no empujaran el panel; Ricardo pidió lo contrario (que sí lo
    empujen, para que la herramienta y lo que ya se veía en el panel estén
    disponibles a la vez), así que `tools` y `stack` volvieron a un
    `QVBoxLayout` normal (r26). Queda anotado por si alguien reintenta la
    superposición: la dificultad entonces era que un cambio de tamaño de
    `tools` no dispara su propio `resizeEvent`, hace falta escuchar
    `QEvent.Type.LayoutRequest`.
27. **(r17) OCR (`pdf_ocr`).** (a) **MuPDF solo reconoce texto en píxeles RGB**:
    `pdfocr_tobytes` sobre un Pixmap en gris devuelve 0 palabras sin error. Se
    preprocesa en gris y se convierte a RGB justo antes. (b) Nunca sustituir
    páginas: la capa de texto se superpone a la original (se conservan vectores,
    anotaciones, formularios y cifrado; un paso de deshacer). (c) Las palabras de
    `get_text("words")` van en coordenadas de la página **girada** (las mismas
    del Pixmap), así que para taparlas basta `Rect * Matrix(dpi/72)`. (d) Para
    orientar, `set_rotation(orig + Rotate de OSD)`, renderizar, superponer y
    restaurar la rotación en un `finally`: la capa queda alineada. (e) Se aplica
    a **todas** las páginas por defecto: el método anterior solo trataba páginas
    sin texto y se dejaba las imágenes de páginas mixtas. (f) (r18) **Nunca
    renderizar a DPI fijo sin límite**: una página de escáner enorme a 400 ppp
    lanza `FzErrorLimit: Overly large image`; usar siempre `render_dpi(page, dpi)`.
    (g) (r60) **No fiarse del OSD**: propone 180° con la página derecha (fotos de
    documentos; `OCR.PDF` y `Factura Honorarios` p. 2 salían enteros boca abajo).
    Se comprueba reconociendo a media resolución en las dos orientaciones; la
    confianza cuenta como 0 en las palabras verticales, porque Tesseract 5 lee
    bien las líneas verticales y sin eso no distinguía 0° de 90°/270°. (h) (r60)
    El texto **invisible** (modo 3) es la capa de un OCR anterior, no texto real:
    se borra y se reconoce de nuevo (antes se tapaba en blanco y un OCR malo no
    se podía corregir). (i) (r60) Enderezar solo a partir de 1°: con 0,8° en una
    foto con perspectiva, el total de una minuta pasaba a leerse mal; la capa se
    devuelve girada con un `cm` para que cada palabra caiga sobre su tinta.
    (j) (r60) `tesseract.exe` escribe mal las tildes por la salida estándar en
    Windows: leer siempre sus salidas desde archivo (`o.txt`, `.tsv`, `.pdf`).
28. **(r17) JavaScript de formularios (`pdf_forms`).** `app.alert`,
    `app.launchURL`, `this.print`… son nativos de MuPDF, **no configurables ni
    escribibles** (`defineProperty` los ignora en silencio), no avisan a nadie
    (el callback de eventos exige un puntero C) y, si no existen, el script se
    corta. Durante cada evento de usuario se escribe en la acción
    `with (__agpdf.scope) { …JS original… }` (`_captured`) y se restaura el valor
    exacto (referencia `n 0 R` o cadena); `__agpdf.scope.app` hereda del `app`
    nativo con `Object.defineProperty`. El puntero JS es `pdf.m_internal.js` y se
    usa con `mupdf.ll_pdf_js_execute` (la versión «class-aware» no lo acepta);
    su resultado es un literal JS, así que hay que decodificarlo con `json.loads`.
    MuPDF ejecuta él mismo el JavaScript y `ResetForm`; URI/Named/GoTo/Submit/Launch
    los ejecuta la app. Nunca se ejecuta JavaScript al abrir el documento.
    Tras deshacer, el documento se reabre y el JS se reactiva solo (`enable_js`
    es idempotente).
29. **(r18/r36) Qt WebEngine (Chromium).** (a) `from PyQt6 import QtWebEngineWidgets`
    **antes** de crear la `QApplication` (main.py y las pruebas). (b) La
    `QApplication` necesita un argv **no vacío** (`QApplication([])` aborta el
    proceso al cargarlo). (c) Toda `QWebEnginePage` debe destruirse antes que el
    perfil o hay violación de acceso al salir (`emoji_font._convert_svg_to_pdf`
    la borra con `sip.delete`). (d) Pruebas sin pantalla:
    `QTWEBENGINE_CHROMIUM_FLAGS="--disable-gpu --no-sandbox"` y
    `QTWEBENGINE_DISABLE_SANDBOX=1`. (r38) Ya solo se usa para convertir los
    emojis de Fluent Emoji; el visor XFA se retiró.
30. **(r20) Varios documentos (`_sessions`).** (a) El documento activo vive en
    los atributos de la ventana (`_SESSION_ATTRS`); `_sessions[_active]` está
    **desactualizado** mientras es el activo: leer siempre con `_session(i)`.
    Todo estado nuevo propio de un documento debe añadirse a `_SESSION_ATTRS`
    y a `_reset_document_fields`, o se mezclará entre pestañas. (b) Cargar un
    documento nuevo = `_begin_new_session()` **antes** de `_set_document`;
    `_set_document` a secas sustituye el documento de la pestaña activa (guardar
    con cifrado, firmar). (c) `_stash_active` confirma antes el editor de campo
    abierto (modifica el documento). (d) La firma en curso es modal y además
    bloquea `switch_document`.

31. **(r21) Editar contenido borra por redacción, y `apply_redactions()`
    aplica TODAS las de la página.** Antes de quitar una línea o una imagen,
    `pdf_edit._erase` **aparta las marcas de redacción que ya trajera el PDF**
    (`_stash_redactions`) y las repone después: si no, editar una palabra
    ejecutaba sin avisar una marca de redacción puesta por otra aplicación
    antes de abrirlo (r49: la app ya no tiene herramienta propia de redactar,
    pero un PDF puede llegar con marcas de otra), que es
    irreversible. Se aplica siempre con `fill=False` (no pinta recuadro),
    `PDF_REDACT_LINE_ART_NONE` y `PDF_REDACT_IMAGE_NONE` para texto (o
    `PDF_REDACT_IMAGE_REMOVE` + `TEXT_NONE` para imágenes), así no se lleva por
    delante el arte vectorial ni las imágenes de debajo. Comprobado: MuPDF
    decide por el **centro** del carácter, así que la caja de una línea no se
    come las vecinas aunque se toquen.
32. **(r21) La fuente incrustada del PDF NO sirve para escribir.** Los
    subconjuntos que generan Word y Acrobat vienen **sin tabla `cmap`**:
    `fitz.Font(fontbuffer=doc.extract_font(xref)[3])` devuelve glifo **0 para
    todos los caracteres** y el texto saldría en blanco, sin ningún error
    (comprobado con el Calibri de `Doc1.pdf`: 272 KB, 7.048 glifos, 0 accesibles).
    `pdf_edit.resolve_font` traduce el nombre base — quitando el prefijo
    `BCDEEE+` y los sufijos de estilo, pero **parando en cuanto queda una
    familia conocida** (si no, «timesnewromanpsmt» acaba en «timesnew») — al
    archivo de `%WINDIR%\Fonts` de **esa misma fuente**. (r40) La fuente del
    documento **no se cambia**: si no está instalada se usa la más parecida del
    sistema (sans → Arial, serif → Times New Roman, mono → Courier New) y, solo
    si tampoco está, la Noto de la app (fuente base), con respaldo base-14. Si faltan glifos se prueba
    otra fuente y, si tampoco, se avisa por nombre de los caracteres.
33. **(r21) Las imágenes se tocan por APARICIÓN, no por xref.**
    `Page.replace_image` y `Page.delete_image` actúan sobre el objeto y cambian
    **todas** las copias de esa imagen en todo el documento (comprobado). Para
    tocar solo la que señala el usuario se redacta su rectángulo con
    `PDF_REDACT_IMAGE_REMOVE`. Mover o sustituir = quitar la aparición y
    `insert_image` en el sitio nuevo, que queda **encima** del resto (el orden
    de dibujo original no se puede conservar). Las entradas con `xref <= 0` o
    caja vacía no se ofrecen: son imágenes en línea (`BI…ID…EI`) y las que MuPDF
    reconstruye cuando no puede emparejarlas — un PDF firmado da ocho así, del
    sello — y no se pueden extraer ni sustituir. `is_shared` recorre el
    documento entero: **solo bajo demanda**, nunca al leer la página.
34. **(r21) `get_text` y `get_image_info` incluyen la apariencia de las
    anotaciones.** El texto de un FreeText de la herramienta Texto, el valor de
    un campo de formulario o el glifo de un emoji salen como si fueran contenido
    de la página, y no hay ninguna bandera para excluirlos. Redactarlos **no
    borraría nada** (viven en su `/AP`) y encima se escribiría un duplicado. Por
    eso `pdf_edit._painted_by_annots` aparta Widget, FreeText, Stamp, Caret y
    FileAttachment, comparando por el **centro** de la línea (la apariencia se
    sale de su propio rectángulo: las mayúsculas suben por encima y el valor de
    un campo es más alto que el campo). **No** se apartan Highlight, Underline,
    Square…: no pintan texto y sus rectángulos cubren texto real que sí debe
    poder editarse.
35. **(r21) `Annot.rect` y `Widget.rect` NO siguen la rotación de la página**,
    aunque `get_text` sí devuelva el texto en la página vista. Con `/Rotate 90`
    el rectángulo de un campo llega en coordenadas sin girar y puede caer
    incluso fuera de `page.rect`. Cualquier comparación entre anotaciones y
    texto se hace en la página **sin girar**; mezclarlos hacía que la herramienta
    de edición tapara una línea y dejara pasar un campo. Ver también la
    invariante 27c.
36. **(r21) Reescribir una línea cambia el orden de extracción.** El contenido
    nuevo se añade al final del flujo, así que `text_lines()` la devuelve en otra
    posición: buscarla luego por su índice señala **otra línea** (es la trampa de
    la invariante 10 otra vez, y aquí llegaba a reescribir el texto equivocado).
    La identidad estable es la **línea base** (`base_origin`), que la reescritura
    respeta: `edit_ui._same`. Para Tab se ordena por geometría
    (`_reading_order`), no por extracción.

37. **(r22) La unidad de edición es el PÁRRAFO y el texto se reajusta a su
    cuadro.** `text_blocks` usa los bloques de MuPDF (que ya agrupa por párrafo)
    y `replace_block` reparte el texto con `wrap` en las líneas que quepan en el
    ancho del cuadro, en la posición de la primera línea base, con el
    interlineado medido entre líneas base y la alineación detectada. Dos
    trampas medidas:
    - **Al unir las líneas de un párrafo** hay que distinguir el salto que puso
      el reajuste del que puso el autor (lista, verso, dirección). Hacen falta
      **dos** señales a la vez: que el párrafo **llene la columna** (el bloque de
      texto más ancho de la página) y que la primera palabra de la línea
      siguiente **no hubiera cabido** al final de esta (medida con las cajas de
      sus propios caracteres, sin cargar la fuente). Solo con la segunda, una
      lista corta se convertía en un churro: su ítem más largo define el borde
      del bloque y parece llegar siempre al margen.
      **(r32)** «Llenar la columna» (≥ 60 % del bloque más ancho) **no basta
      como única vía**: un párrafo estrecho —caja de texto, columna lateral, o
      el texto que la app acaba de repartir en un cuadro estrecho— quedaba con
      todos sus saltos como del autor, y al ensanchar el cuadro el texto seguía
      cortado al ancho anterior. Ahora también es reajustable si **todas** sus
      líneas menos la última están llenas; las líneas que empiezan por viñeta o
      número (`_RE_LIST_ITEM`) nunca se unen. «Cabía» exige caber por el borde
      derecho **y** por el ancho de la línea (sangría de primera línea y texto
      centrado).
    - **El alto que pide el texto se mide con el descendente del propio párrafo**
      (`last_descent`), no con el de la fuente: la caja de un bloque es el
      recuadro ajustado a sus glifos, más baja que ascendente+descendente, y con
      el de la fuente un párrafo de una sola línea salía siempre como «no cabe»
      sin haber tocado nada.
38. **(r22) Las matrices de rotación se piden ANTES de poner la rotación a 0.**
    El cuadro que manda el visor viene en coordenadas de la página **vista**;
    dentro de `replace_block` se trabaja con `set_rotation(0)` y, a partir de ahí,
    `page.derotation_matrix` y `page.rotation_matrix` son la **identidad**. Pedirlas
    después dejaba el cuadro sin convertir: con `/Rotate 90` el texto se repartía
    en un cuadro girado y aterrizaba donde no era. (`place_image` ya lo hacía bien.)
39. **(r22) Ningún cuadro puede salirse de la página** (`clamp_box`, también en
    `edit_ui._resized`): el texto se escribiría fuera, no se vería y ya no se
    podría volver a seleccionar para arreglarlo. Acota además al mínimo `MIN_BOX`
    y endereza los rectángulos arrastrados «al revés».
40. **(r22) Los tiradores del cuadro van FUERA de él** (`_OUT` = 6 px): mientras
    se edita, el `QPlainTextEdit` tapa el cuadro entero y, si cayesen dentro, los
    clics no llegarían al visor y no se podría estirar. Funciona porque
    `PDFViewerWidget.mousePressEvent` **no llama a `super()`**: pulsar en el visor
    no le quita el foco al editor, así que estirar una esquina no lo cierra
    (comprobado). Si algún día se añade ese `super()`, el editor se cerrará en
    cuanto se toque un tirador.

41. **(r23) El `QShortcut` de Esc de la ventana se queda la tecla antes que
    el editor.** Los atajos de Qt se procesan **antes** que los eventos de
    teclado, así que Esc **nunca llega** al cuadro que haya abierto sobre la
    página, por mucho que tenga el foco (comprobado). `MenusMixin._on_escape`
    cancela él mismo, primero `viewer.text_editor` y luego
    `viewer.content.editor`, y solo después hace lo de siempre. Ojo con las
    pruebas: `QTest.keyClick(editor, Esc)` va directo al widget y **se salta el
    atajo**, así que pasaba aunque en la app real no funcionara; hay una prueba
    que dispara `_esc_shortcut` para recorrer el camino de verdad.
42. **(r23) El visor no le quita el foco al editor** porque
    `PDFViewerWidget.mousePressEvent` **no llama a `super()`**. De eso dependen
    dos cosas: estirar una esquina sin cerrar el editor (invariante 40) y que
    haya que cerrar el cuadro a mano al pulsar en la página. Ese clic de
    confirmación **se traga también el release** (`_swallow_release`): si no, al
    soltar se abría otro cuadro de escritura en el mismo sitio.
43. **(r23) En `QPlainTextEdit`, el alto de `documentSize()` viene en LÍNEAS,
    no en píxeles** (al revés que en `QTextEdit`), y solo cuenta bien cuando el
    widget ya está realizado y sabe su ancho. Tomarlo por píxeles hacía que el
    cuadro no creciera y se escribiera a ciegas. Para la caja que queda en el
    PDF se toma **la mayor** de dos medidas —la del editor de Qt y
    `fontsize × 1,45 × líneas + fontsize × 0,6`—: los repartos de Qt y del
    rich-text de MuPDF no coinciden, y quedarse corto **recorta el texto**.
44. **(r24) Los tooltips son amarillo crema (`utils.TOOLTIP_QSS`) y un
    `setStyleSheet` local sin selector los pisa.** Qt envuelve «background: …;»
    en `* { }`, y el tooltip hereda la hoja del widget que lo muestra: los de
    los paneles de la barra secundaria (`_TP`) salían **transparentes** y los
    del visor, **grises** (viewport #D0D4D8). Todo estilo local que tenga hijos
    con tooltip debe escribirse `"* { … }" + TOOLTIP_QSS` (declaraciones
    sueltas y reglas no se pueden mezclar). La prueba
    `test_tooltips_con_fondo_amarillo_crema` muestra el tooltip de cada widget
    y mira el píxel.
45. **(r25) Texto del sello al ancho del recuadro.** pyHanko escribe `Tf`/`TL`
    como **enteros** y redondea el ancho de cada línea, y su `TextBox` pone 10 pt
    de margen por lado si no se le da `box_layout_rule`; además su maquetación
    por defecto solo **encoge**. Por eso `_text_layout` compone a 100 pt con
    márgenes 0 (y ¼ de cuerpo abajo para los descendentes) y
    `_render_inner_content` pone su propia `cm`: `sx = ancho/ancho_texto`,
    `sy = min(sx, alto/alto_texto)`. Courier es monoespaciada, así que medir por
    número de caracteres es exacto. `_arrange_lines` une líneas con « · » en
    recuadros anchos y bajos para que `sy` se aleje poco de `sx`.
    **(r30)** Todo eso se calcula sobre el hueco interior de `_text_area`:
    margen = máx(7 pt, 10 % del alto) por los cuatro lados (`TEXT_MARGIN_MIN`,
    `TEXT_MARGIN_RATIO`); solo en recuadros diminutos se reduce para dejar 1 pt.
46. **(r26) Panel lateral = rail + `column` (opciones `tools` arriba, `stack`
    abajo).** El ancho del divisor lo decide `sidebar.is_open()` (columna), no
    `stack.isVisible()`; la preferencia guardada sí es del `stack`. Las
    etiquetas fijas no deben cortarse (la prueba compara `width()` con
    `sizeHint()`); las variables (`_side_hint`) tienen política `Ignored`
    para no ensanchar el panel y llevan el texto completo en el tooltip. En
    las pruebas, abrir antes un panel (`show_panel`) salvo que se quiera probar
    la columna sin panel. **(r72)** `tools` va con `AlignTop` en el layout de la
    columna: con el `stack` oculto era el único elemento y el layout lo centraba
    en vertical (Texto a 236 px de 698). **`COLUMN_MIN` = 310** desde r72: el
    combo de fuentes de 160 px (r69) dejó el panel «Añadir texto» en 306 px y
    con 290 se cortaba por la derecha. Al abrir la columna con el
    panel cerrado el visor se estrecha 240 px y la página se recoloca en
    horizontal (no se compensa).
47. **(r27) Modo páginas: la selección de miniaturas es de las acciones.**
    `render_page` → `sidebar.set_current_page` → `thumbs.set_current`; con
    `setCurrentRow` la selección se reducía a la página actual y la acción
    siguiente caía en otra página. Organizando se usa
    `selectionModel().setCurrentIndex(…, NoUpdate)`. Las operaciones que
    cambian la estructura piden la selección nueva con
    `thumbs.select_after_rebuild` (la reconstrucción llega con el temporizador
    de 350 ms). El reordenado por arrastre se aplica en diferido
    (`QTimer.singleShot(0)`): reconstruir la lista dentro del propio evento
    de soltar la rompería. Duplicar usa `fullcopy_page` de atrás adelante, nunca
    `select` con índices repetidos (compartiría la página).
48. **(r31; arrastre reescrito en r51; híbrido con `QDrag` real en r52)
    Miniaturas en cuadrícula: el soltar lo calcula la app, no `dropEvent`.**
    La lista es `IconMode` + `LeftToRight` + `setWrapping` + `ResizeMode.
    Adjust`, así que al ensanchar el panel caben más columnas; `drop_row`
    calcula el hueco de destino por orden de lectura (sin cambios desde r31).
    **(r51, aviso de Ricardo: «al soltar no hace nada»)** Hasta r51 el destino
    salía de `_ThumbList.dropEvent` sobre el `dragDropMode=InternalMove`
    nativo de Qt — y **nunca llegaba a completarse con el ratón de verdad**:
    en Windows, `QDrag.exec()` negocia por OLE (`DoDragDrop`), que lee los
    mensajes del ratón directamente del sistema operativo, no de la cola de
    eventos de Qt, y con el panel dentro del `QSplitter`/`QStackedWidget`
    anidado de la app esa negociación no se completaba, así que `dropEvent`
    no se disparaba nunca. Nadie lo había visto: la prueba de r31 llamaba a
    `move_selection_to` **directamente**, sin pasar por ningún gesto de ratón.
    **(r52, petición de Ricardo: «solución híbrida — funcionalidad de toda
    la vida (pulsar, mover, soltar) pero que visualmente siga apoyándose en
    OLE»)** `_run_drag` SÍ arranca un `QDrag.exec()` real en cuanto
    `mouseMoveEvent` supera `QApplication.startDragDistance()` — así el
    fantasma semitransparente de la miniatura y el cursor de «permitido/
    prohibido» los sigue pintando Windows —, pero **el destino ya no sale de
    `dropEvent`** (`dropEvent` se ignora a propósito: no hay que fiarse de que
    llegue). En su lugar, en cuanto `exec()` devuelve el control —**siempre**
    lo devuelve al soltar el botón, con o sin drop aceptado, así que no hay
    riesgo de bloqueo— se lee `QCursor.pos()` (la da el sistema operativo, no
    la cola de Qt) y con esa posición se hace exactamente lo mismo que en r51:
    `drop_row()` + `move_selection_to()`, solo si el punto cae dentro del
    `viewport`. **Trampa al escribir la prueba**: bajo `offscreen`,
    `QTest.mousePress` sí mueve `QCursor.pos()` a la posición de la pulsación,
    pero `QTest.mouseMove` **no** lo mueve a ningún sitio (comprobado a mano);
    la prueba tiene que llamar a `QCursor.setPos()` ella misma **después** de
    `mousePress` (si no, `mousePress` lo pisa) y **antes** de `mouseMove`, con
    la posición global de destino. Esto **sí se puede probar en offscreen**:
    `QDrag.exec()` no cuelga ahí (vuelve enseguida con `IgnoreAction`, no hay
    compositor real que negocie el drop, pero el valor de retorno no se usa
    para nada) y el resto son eventos de ratón normales. La prueba ensancha el
    panel (como en la de Operaciones de página) para que la 4.ª miniatura
    quepa sin necesitar scroll, ya que `_run_drag` descarta un destino fuera
    del `viewport` visible.
49. **(r34) El texto copiado no sigue las líneas de MuPDF.** `(bloque, línea)`
    de `get_text("words")` no es una línea visual: en la capa de OCR de un
    escaneo torcido MuPDF la trocea a alturas algo distintas. `word_selection`
    rehace las líneas por solape vertical con la palabra anterior
    (`_visual_lines`) y `_lines_to_text` une los renglones de cada párrafo. El
    margen derecho y el interlineado se miden **sobre toda la selección** (el
    renglón más largo con el mismo arranque; el cuartil bajo de los saltos): con
    el margen del propio párrafo, la primera línea de cada párrafo nuevo era su
    propio borde y se pegaba con lo que venía detrás. La selección sigue siendo
    el tramo de palabras en orden de extracción entre las dos más cercanas.
54. **(r68) Firma manuscrita = Stamp con apariencia propia, como los emojis.**
    (a) `FirmaManuscrita` está en `emoji_font.STAMP_SUBJECTS` (como literal, para
    no importar `firma_manuscrita` desde ahí): moverla y redimensionarla va por
    `write_rect` y con proporción fija (invariante 3); nada de `set_rect()`,
    `update()` ni `set_info()`. `is_emoji` sigue siendo falso para ella, y
    `_show_annot_opts` la atiende **antes** que la rama `Stamp → EMOJI`.
    (b) **La superposición de tinta sale de rellenar cada pieza por separado**
    con `/ca` < 1: dentro de un relleno la unión no se oscurece (regla no nula
    con todas las formas en la misma orientación: si una pieza tuviera una
    forma al revés, abriría un hueco). Por eso los cuadriláteros retorcidos se
    descartan y los tapan círculos, y los trazos que se cortan a sí mismos se
    parten en `_split_at_crossings`. (c) Los bordes usan la normal
    **promediada** en cada punto: con un cuadrilátero por segmento y su propia
    normal, el contorno salía dentado a 400 ppp. (d) Una firma de ~300 puntos
    ocupa ~10 KB comprimida; con un círculo en cada punto eran ~100 KB.
    (e) La imagen va con `add_stamp_annot(rect, stamp=png)`: MuPDF conserva la
    transparencia como `/SMask` de 8 bits (comprobado con un degradado).
    (f) `Pixmap.clear_with(0)` en PyMuPDF 1.28 deja el alfa a 255: para una
    imagen transparente en pruebas, construir el `Pixmap` desde las muestras.
55. **(r69) La hoja de estilos global pisa `setFont()`.** `main.STYLESHEET`
    tiene una regla `QWidget { font-family; font-size }` y, con hoja de estilos,
    Qt manda la fuente de la regla sobre la del widget. (a) `InPlaceEditor`
    repite familia, tamaño, grosor y estilo en su propia hoja (`_font_css`):
    antes se escribía siempre con la fuente de la interfaz a 13 px, y el tipo
    de letra y el tamaño elegidos solo aparecían al confirmar (vale también para
    las notas y «Editar contenido»). (b) El combo de fuentes enseña la elegida
    con `setStyleSheet` en el propio combo, y su lista la pinta
    `main_window._FontPreviewDelegate` a mano: con hoja de estilos la lista usa
    `QComboMenuDelegate` y la regla global también pisa `Qt.FontRole` (probado:
    ni `setFamilies` lo arregla). (c) En pruebas, para ver este fallo hay que
    poner `main.STYLESHEET` en la `QApplication`: sin ella todo parecía ir bien.
    (d) **La herramienta Texto no justifica** (`_ALIGN_GLYPHS` de 3; ciclo
    izquierda → centro → derecha): MuPDF no reparte bien el justificado en el
    texto enriquecido. Un texto antiguo con `a3` se muestra a la izquierda al
    seleccionarlo y conserva su valor si no se toca la alineación. «Editar
    contenido» sí conserva el justificado de los párrafos del PDF
    (`inplace_editor._ALIGN[3]` sigue existiendo por eso). (e) (r70) La
    presentación inicial pone todas sus fuentes en su propia hoja de estilos
    por lo mismo: con `setFont()` el título salía a 13 px.
56. **(r71) Repositorio público: nada de clientes.** `.gitignore` excluye
    todos los `*.pdf`/`*.PDF` salvo `signature_background.pdf`, los `.odt`/`.doc*`/
    `.xls*`, los certificados (`*.pfx`, `*.p12`, `*.key`; el de pruebas lo genera
    `create_test_cert.py`), los `*.log`, `empaquetado/salida/` y
    `empaquetado/version_info.txt`. Los documentos de prueba de Ricardo
    (`Factura Honorarios.pdf`, `Notificacion.PDF`, `OCR.pdf`, `Formulario.pdf`,
    `Compartimentar.odt`) siguen en su carpeta pero **no** se suben; las pruebas
    que los usan se saltan si faltan. En docs y memoria **no escribir datos
    reales de clientes** (entidades, importes, IBAN, DNI): r71 anonimizó la
    minuta de IBERAVAL (entidad, total e IBAN en `docs/herramientas_profesionales.md`,
    en esta memoria y en un comentario de `pdf_ocr.py`). Los identificadores de
    las pruebas son ficticios (`12345678Z`, `B12345678`). Antes de cada `git add`
    nuevo, revisar `git status` por si aparece un documento que no debe ir.
    **Licencia**: AGPL-3.0 es la única compatible con PyMuPDF (AGPL) y PyQt6
    (GPL) sin licencias comerciales; `.iss` en UTF-8 **con BOM** para que Inno
    Setup lea bien «Asesoría».

## 5. Operaciones que escriben en disco

**Ningún flujo sobrescribe el original sin que el usuario guarde**:

- *Guardar* / *Guardar como*: escritura atómica (`.agtmp` + `os.replace`),
  `garbage=3, deflate=True` si hay cambios; bytes de disco si no los hay.
- *Firmar*: pide ruta de salida (por defecto `<nombre>_firmado.pdf`), escribe
  ahí y abre el firmado. El original queda intacto.
- *Organizar páginas*: en memoria (con deshacer). No toca disco.
- *Comprimir* (r15, `pdf_compression`): copia a una ruta elegida (por defecto
  `<nombre>_comprimido.pdf`) con escritura atómica. Parte de los bytes de disco
  si no hay cambios y, si no, del estado actual. Tres niveles (combo del panel).
  **Nunca reduce imágenes por debajo de 75 ppp al imprimir la página ajustada a
  DIN A4**: el objetivo mínimo es `ceil(75 × factor A4 de la página con imágenes
  más pequeña) + 1`, y MuPDF usa la colocación de menor resolución de cada imagen.
  Las imágenes que ya estaban por debajo no se amplían. Si el resultado no es
  menor que el original, **no guarda nada** y lo dice. Conserva el cifrado (KEEP
  o la protección pendiente). Avisa antes si el PDF está firmado (la copia
  pierde las firmas; el original no cambia). Informa del tamaño antes y
  después, del porcentaje y del ppp mínimo en A4. **Red de seguridad**: si al
  pintar el resultado aparecen avisos de MuPDF que el original no tenía, repite
  sin tocar imágenes (y después sin recortar fuentes) y lo explica en `note`.
- *Extraer / Dividir / Exportar*: siempre a archivos nuevos elegidos por el usuario.
- Temporales: PFX exportado de Windows (`%TEMP%\_agpdf_*.pfx`, se borra al
  terminar la firma) y PDF temporal para `pdf2docx`.
- Registro: `errores.log` y `fallos_graves.log` en `%LOCALAPPDATA%\aventyapdf`.
- Pruebas: todo en carpetas `%TEMP%\agpdf_test_*` / `agpdf_ui_*` que se borran;
  la prueba de interfaz toca `recent/*` y `view/sidebar` de QSettings y los restaura.
- *Menú contextual del Explorador* (r55): combinar PDF y convertir imágenes
  desde el Explorador **no escriben ningún archivo por su cuenta** — el
  resultado queda sin guardar dentro de la app, como «Nuevo PDF en blanco»;
  el usuario decide después dónde guardarlo. Lo único que sí escribe algo
  fuera del propio proyecto es `Install-ContextMenu.ps1`, y no es un archivo:
  son claves de `HKEY_CURRENT_USER\...\SystemFileAssociations` (sin
  administrador), reversibles con `-Quitar`.

## 6. Firma digital PAdES

**Selección de identidad** (`cert_manager`, sin cambios): almacén `MY` con
`ssl.enum_certificates`, exportación a PFX temporal vía PowerShell/.NET
(falla con claves no exportables: DNIe, tokens), persistencia `QSettings` + `keyring`.

**Flujo** (`DocumentMixin._do_signature`): área dibujada (mín. 20×10 pt) →
`SignOptionsDialog` (motivo, lugar, contacto, TSA, certificar; recordado en
`QSettings signing/*`; «no volver a preguntar» con `signing/skip_dialog`) →
certificado → ruta de salida → `SignWorker` → guardar → abrir firmado → panel Firmas.

**Firma** (`PAdESSigner.sign_pdf_bytes`): `IncrementalPdfFileWriter` sobre
bytes; `SimpleSigner.load_pkcs12` **devuelve None en vez de lanzar** (se
comprueba); campo único `_unique_field_name` (`enumerate_sig_fields` produce
`(nombre, valor, ref)`); `SigSeedSubFilter.PADES`; opcional
`HTTPTimeStamper(tsa_url)` → PAdES-B-T (presets en `TSA_PRESETS`); opcional
`certify=True` + `MDPPerm.FILL_FORMS`; documentos cifrados con
`w.encrypt(password)`. Errores → `SigningError` con mensaje legible.
PDF con xref híbridas: normalizar o firmar en modo tolerante según haya firmas
previas (invariante 24).
Sello visual `_SpanishCertTextStamp`: sobrescribe `render()` y
`_text_layout()` de `TextStamp` (API verificada en pyHanko 0.36.2: si una
versión futura cambia esos métodos privados, el sello es lo primero que
romperá). Líneas `Motivo:`/`Lugar:` con `%` escapado.

**Aspecto del sello (r9, petición de Ricardo)** — orden de dibujo en `render()`:
0. **(r29) Recuadro de color** (`_draw_panel`): todo el recuadro de la firma
   relleno de #D1CCBD con opacidad 0,25 («75 % de transparencia», ExtGState
   `/SigPanelGS` con `/ca`) y esquinas redondeadas de 14 pt (`PANEL_RGB`,
   `PANEL_ALPHA`, `PANEL_RADIUS`; el radio se limita a la mitad del lado
   menor). Contorno en `_rounded_box_path` (Bézier k = 0,552285).
1. **Logotipo `MOSCA.svg` de fondo** (`_draw_background`): la página de
   `signature_background.pdf` importada con `writer.import_page_as_xobject` y
   dibujada con `cm`. Escala proporcional **siempre por el alto** del recuadro,
   (r30) **pegado al lado derecho** y ocupando todo el alto; en recuadros estrechos lo que sobresale se recorta
   (r29) con el mismo contorno redondeado (`W n`), para que no asome por las esquinas. Sin el PDF, se firma sin fondo (aviso por consola, no falla).
2. Texto opaco (negro por defecto de pyHanko). **(r25) Con el ancho exacto del
   recuadro** menos el margen interno de r30 (la línea más larga de borde a borde) y centrado en vertical;
   el fondo va por el alto y el texto por el ancho (invariante 45).

**Sin** borde ni huella (r9 retiró lo de r8; r29 recuperó un recuadro
redondeado, ahora semitransparente y de otro color). Ojo: MuPDF reescribe `/ca 0.25`
como `/ca .25`. Trampas del logotipo:
- **MuPDF no sirve para convertir el SVG** (`fitz.open(svg)` lo pinta negro: no
  soporta máscaras, degradados con alfa ni opacidad de grupo). Qt `QSvgRenderer`
  lo pinta parecido, pero se usa Edge por fidelidad y salida vectorial.
- **Máscaras sin región**: los navegadores recortan a −10 %…120 % (especificación)
  e Inkscape no. Por eso el generador amplía cada `<mask>` en la copia temporal.
- **(r12) Skia rasteriza las `<mask>`**: las exporta como imagen (2479 px) usada de
  máscara suave, y en el borde de la imagen se cuela 1 px del contenido
  enmascarado. En pantalla salía una **línea de 1 px en el perímetro del lienzo**
  del logotipo, invisible al ampliar mucho. Solución: `_mascaras_solidas_a_clip`
  (máscara de formas de un solo color sólido = `<clipPath>` + opacidad igual a su
  luminancia, 0,9546 para #F5F3F3). Para buscar este tipo de fallos, renderizar
  a zoom 0,25–1,5 y ampliar sin suavizar; con zoom alto no se ve.
  `TestFondoFirma` vigila que no haya imágenes y que el perímetro salga blanco.
- La `cm` usa 6 decimales: con 4, el alto se desviaba 0,02 pt.

Comprobación visual: firmar y renderizar con `get_pixmap` (PyMuPDF dibuja la
apariencia del widget de firma); para ver la transparencia, pintar antes un
fondo de color en la página.

**Nombre del firmante** (r11, primera línea del sello y `/Name` de la firma):
**solo nombre y apellidos** (`_signer_display_name`). El CN de los certificados
de representante de la FNMT es `DNI NOMBRE APELLIDO1 (R: CIF)` (¡un solo
apellido!), así que se prefiere `givenName` + `surname`; si faltan, se limpia el
CN (DNI/NIE inicial, `(R: …)` y `- NIF …` finales). NIF y «Repr.» siguen en sus
líneas. Ojo: el panel Firmas (`signature_validation`, `rep.signer`) y el
selector de certificados siguen mostrando el CN completo.

**Validación** (`signature_validation.validate_signatures`): pyHanko con
`ValidationContext(trust_roots=ROOT de Windows + TSL de España (r43), other_certs=CA,
allow_fetching=False, revocation_mode="soft-fail")`. **(r43) La TSL da anclas
que suelen ser CA intermedias** (la «AC Interna» de los Registradores, no su raíz
autofirmada) y pyHanko las acepta como ancla; la raíz que trae el PDF **no** se
usa como ancla (si no, cualquier PDF con una raíz falsa saldría «verificado»).
`vendor/trust/es_tsl.pem` caduca con la TSL (regenerar con `create_trust_list.py`;
una prueba falla a propósito al pasar la fecha). **(r44) La firma XAdES de la LOTL
y de la TSL de España sí se comprueba**, en tiempo de generación (`create_trust_list
.verificar_firma`, con `signxml`), no al validar un PDF: `es_tsl.pem` solo se genera
si ambas firmas cuadran contra `vendor/trust/oj_signers.pem` y contra el
certificado que la propia LOTL declara para España. Límites: `oj_signers.pem` es un
ancla fijada a mano (no se regenera sola) y solo cuenta el estado actual de cada
servicio, no el histórico. `trusted` y `modification_level` son
**propiedades** de `PdfSignatureStatus` (verificado r5). Veredictos: `ok` ·
`untrusted` (íntegra, cadena no de confianza) · `invalid` · `error`. Se valida
`_clean_bytes` (lo que hay en disco); si tiene xref híbridas se lee con
`strict=False` (invariante 24). **Sin LTV / PAdES-LTA ni comprobación de
revocación en línea.**

**(r45) Un campo de firma puede ser `/Sig` (firma normal) o `/DocTimeStamp`**
(sello de tiempo de documento, sin firmante: certifica solo una fecha sobre un
PDF ya firmado; lo añaden Acrobat y otros TSA al re-sellar). pyHanko exige la
función correcta para cada uno (`validate_pdf_signature` / `validate_pdf_
timestamp`, invariante 50): la que no toca lanza «Signature object type must
be /Sig» (o «…/DocTimeStamp»). Antes de r45 siempre se llamaba a la primera,
así que un `/DocTimeStamp` salía **«No se pudo validar»** aunque fuese
perfectamente válido — visto con `Factura Honorarios.pdf` (Ricardo: «cuando
tiene más de una firma de certificado parece que no verifica el segundo
certificado»), donde la segunda «firma» era en realidad este tipo de sello, de
los Registradores. `signature_validation` distingue por `emb.sig_object_type`
y `SignatureReport.is_timestamp` cambia el texto del veredicto («Sello de
tiempo válido…») y qué campos rellena: `timestamp` con la fecha del propio
sello, `signed_at` vacío (no hay «fecha declarada» aparte de la del sello).

## 7. Deuda técnica y observaciones abiertas

### 7.0 ⚠️ Verificación pendiente
**r6: primera ejecución real.** Con el proyecto en `C:` la consola funciona.
`.\run.ps1 -Pruebas` → **18/18 OK** tras corregir dos pruebas que usaban
`fitz.Rect.center` (invariante 23; el código de la app no lo usaba). En las
pruebas de firma salen trazas de pyHanko «self-signed»: es lo esperado, porque
el certificado de pruebas es autofirmado (veredicto `untrusted`), y no son fallos.

**Pendiente:** abrir la app (`.\run.ps1`) y seguir el plan manual de
[docs/herramientas_profesionales.md](docs/herramientas_profesionales.md#plan-de-pruebas)
(diálogos modales, impresión, OCR, TSA y certificados de Windows no tienen
pruebas automáticas). Ante cualquier fallo, pedir `errores.log`.

Antecedente: r4 y r5 no pudieron ejecutar Python (la unidad `A:` hacía fallar
las consolas) y verificaron las APIs de riesgo leyendo el código fuente de las
versiones instaladas. Quedaron confirmadas: `add_*_annot(quads=[Rect…])`,
`TextWriter.write_text(morph=…)` (compensa rotación y CropBox),
`insert_text(rotate=…)`, `Widget.on_state()`, `pdfocr_tobytes`, `bake`,
`fullcopy_page`, constantes `PDF_*`, `enumerate_sig_fields`, `load_pkcs12`,
campos de `PdfSignatureMetadata`, `PdfSigner`, atributos de estado de
validación, `ValidationContext`, `IncrementalPdfFileWriter.encrypt`,
`QDialog.DialogCode` (IntEnum en PyQt6 6.11).

### 7.1 Errores o límites conocidos
- Guardar cambios en un PDF firmado reescribe el archivo (no hay guardado
  incremental con PyMuPDF desde bytes) → las firmas previas se invalidan; se avisa.
- Páginas giradas: marcas de agua/encabezados compensan la rotación, pero la
  interacción de anotaciones, el resaltado de búsqueda y el volteo de la firma
  no se han revisado para `/Rotate ≠ 0` ni CropBox desplazado.
- ~~OCR reconstruye las páginas como imagen + texto invisible y pierde
  anotaciones y cifrado~~ → **resuelto en r17** (capa superpuesta, invariante 27).
- (r38) Los **XFA dinámicos** (LiveCycle/AEM) ya no se pueden rellenar: la app
  muestra lo que pinta MuPDF, normalmente solo «Please wait…».
- (r17) Formularios AcroForm: no se envían formularios por
  Internet (SubmitForm solo informa); `app.response` no puede pedir datos al
  usuario (devuelve null); los avisos de funciones JavaScript definidas a nivel
  de documento (fuera de la acción disparada) no se capturan. Los cálculos
  (`AA/C`) que avisan tampoco muestran su mensaje.
- (r21, **al día en r22**) **Editar contenido**: la unidad es el **párrafo** y el
  texto se reajusta a su cuadro, pero **el cuadro no crece solo**: si el texto no
  cabe se avisa (marco rojo, indicador en vivo) y hay que estirar una esquina. El
  texto que se sale se escribe igualmente, para no perderlo. Los párrafos los
  agrupa MuPDF: en una tabla o en un texto a dos columnas puede juntar cosas que
  el autor no ve como un párrafo. Un párrafo con **varios estilos** se reescribe
  entero con el del tramo que tenga más caracteres (se avisa antes, en la barra
  secundaria); las negritas sueltas dentro de una frase se pierden.
  La fuente es una de Windows parecida, no la incrustada (invariante 32), así
  que el ancho de los caracteres puede variar un poco. No se editan las
  imágenes en línea ni el texto de las anotaciones (invariantes 33 y 34), ni el
  texto que forme parte de un dibujo vectorial o de un escaneo (para eso, OCR).
  Al mover o sustituir una imagen queda **encima** del resto del contenido.
  Editar un PDF firmado invalida sus firmas, como cualquier otro cambio.
- Deshacer por instantáneas: con PDF de cientos de MB cada paso cuesta memoria
  y tiempo (`tobytes`).
- `AnnotSelection.idx` sigue siendo posicional (invariante 10).
- Atajos de una letra pueden dispararse con el foco en un `QSpinBox` de la barra secundaria.
- La impresión rasteriza a ≤ 300 ppp (r5); no hay N-up ni folleto.
- (r13) Los emojis creados **antes de r13** (`EmojiImg`, PNG) siguen en esos PDF
  tal cual: aplastados y, en algunos, con referencias de perfil ICC rotas que
  hacen protestar a MuPDF («cmsOpenProfileFromMem failed / invalid ICC
  colorspace»; en `Doc2.pdf` una imagen apuntaba como `/ColorSpace` a la
  apariencia de otra anotación). Se arreglan seleccionándolos y cambiando
  tamaño o glifo: `_recreate_emoji_selection` los recrea como `EmojiFont`.
- (r36) Emojis: solo el tono de piel por defecto; los 1595 de Fluent Emoji
  (con secuencias ZWJ). La búsqueda en español depende de CLDR (1595 con
  nombre). Sin banderas de países (Fluent Emoji no las tiene). La primera
  inserción de cada emoji tarda hasta 1 s (conversión) y cada emoji añade
  20-90 KB al PDF (sus desenfoques van como imágenes pequeñas). El texto escrito con Noto puede ocupar más ancho que el original (p. ej.
  Calibri) y repartirse en más líneas.
- (r36) El sello de la firma sigue en Courier (base-14 de pyHanko): no es texto
  editable y su maquetación depende de que sea monoespaciada.

### 7.2 Higiene
- (r42) Borrados de la carpeta: `Noto_Emoji/` y `Noto_Emoji.zip` (la fuente está
  en `vendor/fonts/noto-emoji`), `Noto_Color_Emoji.zip` y
  `material-symbols-outlined.zip` (no se usan), `colores.html` (la paleta vive en
  `color_picker.PALETTE`), las capturas `error1-6.png` y `herramientas_corregir.png`
  y los `__pycache__/`. Quedan `Compartimentar.odt` y `PLAN_DE_IMPLEMENTACION.md`
  (documentos de Ricardo) y `Formulario.pdf` y `Notificacion.PDF` (sus PDF de prueba).
- Quedan `except Exception: pass` en `_sync_panel_to_annot` y `apply_rounded_corners`.
- Las pruebas no cubren diálogos modales, impresión, OCR, TSA ni certificados de Windows.
- (r23) **Trampas del arnés de pruebas**, las dos tumban el proceso con
  0xC0000409 y **sin traza**: `QTest.keyClicks` con cualquier carácter **no
  ASCII** (las tildes se ponen con `setPlainText`), y parchear un método C++ de
  Qt como `QDialog.exec` con `mock.patch.object`. Y la de siempre: iterar
  `doc[n].annots()` sin guardar la página en una variable (invariante 3).

### 7.3 Funcionalidad ausente frente a Acrobat Pro
- Vista continua multipágina y vista a doble página.
- Edición del texto con **reflujo de párrafo** y por caracteres sueltos, y
  edición con la fuente incrustada del propio PDF (r21 edita por líneas y con
  fuentes del sistema; ver §7.1).
- LTV / PAdES-LTA, revocación en línea, firma con DNIe/tarjeta (PKCS#11).
- Creación de formularios (solo relleno), JavaScript de formularios.
- Comparar documentos, preflight/PDF/A, accesibilidad (etiquetado).
- Exportar a Excel/PowerPoint; imprimir con opciones avanzadas (N-up, folleto).
- Tema oscuro.

## 8. Cómo ejecutar

**Un entorno por equipo fuera de la carpeta del proyecto**, gestionado por [run.ps1](run.ps1):

```powershell
cd "C:\Users\Aventya\Proyectos\ANTIGRAVITY-PDF"   # (r56) pendiente de pasar a AVENTYAPDF, ver cabecera
.\run.ps1                # instala Python y el entorno si faltan; instala los paquetes que falten
.\run.ps1 -Pruebas       # pruebas automáticas (sin ventanas, sin red)
.\run.ps1 -Actualizar    # reinstala y actualiza requirements.txt
.\run.ps1 -Reinstalar    # borra el entorno y lo rehace
```

Entorno: `%LOCALAPPDATA%\aventyapdf\venv` (Python 3.13 → 3.12 → 3.11; se
excluye 3.14). (r33) No hay componentes opcionales: todo se instala solo.
Arrancar con `python.exe` (la consola muestra
trazas de firma, validación y OCR). Política de scripts:
`powershell -ExecutionPolicy Bypass -File .\run.ps1`.

Certificado de pruebas: `python create_test_cert.py` → `test_certificate.pfx` (`1234`).

**(r62) Instalador**: `.\empaquetado\construir.ps1` → `empaquetado\salida\AventyaPDF-Setup-<versión>.exe`
(`-SinInstalador`: solo la app). Compila fuera del proyecto
(`%LOCALAPPDATA%\aventyapdf\build-venv`, `build-work`, `build-dist`) y no crea el
instalador si falla el autodiagnóstico del ejecutable. Detalle en
[docs/empaquetado.md](docs/empaquetado.md).

Tesseract OCR (r16): `.\run.ps1` lo comprueba antes de arrancar y, si falta, lo
instala solo (pedirá permiso de administrador) con los idiomas español, inglés y
osd. A mano: `python tesseract_setup.py` con el Python del entorno.

> Nota operativa: desde `C:\Users\Aventya\Proyectos\ANTIGRAVITY-PDF` (r56:
> pendiente de pasar a `...\AVENTYAPDF`, ver cabecera; hasta r5:
> `A:\CARPETA IA\RICARDO\ANTIGRAVITY-PDF`) las consolas de las herramientas
> funcionan y pueden lanzar `run.ps1 -Pruebas`.
> (r21) Eso sí, invocar `powershell -File .\run.ps1` **desde la herramienta
> Bash** falla con «Get-FileHash no se reconoce»: hay que usar la herramienta
> PowerShell, o el intérprete del entorno directamente
> (`%LOCALAPPDATA%\aventyapdf\venv\Scripts\python.exe -m unittest discover -s tests`).
> Desde la antigua ruta en `A:` fallaban siempre; si el proyecto vuelve ahí,
> habrá que pedirle a Ricardo que ejecute.

## 9. Protocolo de actualización de esta memoria

**Regla:** ninguna edición se considera terminada hasta que esta memoria refleja el nuevo estado.

1. **Leer** este archivo antes de empezar (sobre todo §4).
2. **Actualizar** las secciones afectadas: archivos → §2 · UI/modos/atajos → §3 ·
   trucos no obvios → **§4** · escritura en disco → §5 · firma → §6 ·
   errores → §7 (mover a §10 al resolverse).
3. **Subir la revisión** `rN` y la fecha.
4. **Añadir una línea en §10**: `rN · fecha · qué cambió · por qué`.
5. Si el cambio es conceptual, propagarlo a [docs/](docs/indice.md).

Criterio: aquí va lo que **no se deduce leyendo el código** — decisiones,
motivos, invariantes, trampas y estado.

## 10. Historial de revisiones

| Rev | Fecha | Cambio |
| :-- | :-- | :-- |
| r83 | 2026-09-25 | **Reempaquetado del instalador y publicación de la versión 2.0.5 en GitHub.** Se ejecuta `empaquetado/construir.ps1`, superando las 7 pruebas de autodiagnóstico del ejecutable y generando `AventyaPDF-Setup-2.0.5.exe`. Se crea y publica la Release v2.0.5 en GitHub junto al instalador. |
| r82 | 2026-09-25 | **Probado el arrastre de verdad (agente, con permiso de Ricardo: «te dejo la pantalla libre, haz la prueba tu mismo») y sin alfa en el fantasma tras nueva confirmación de Ricardo de que seguía en negro.** Lanzada la build de desarrollo (r72-r81 sin reempaquetar) con un intérprete de Python distinto al venv habitual, dependencias instaladas aparte para no tocar el entorno real; arrastre simulado con eventos de ratón reales (`SetCursorPos`/`mouse_event`, no Qt), captura de pantalla completa **con el cursor superpuesto** (`GetCursorInfo`/`DrawIcon`, que una captura normal no incluye) justo antes de soltar. Resultado de esa prueba: fantasma gris claro, sin negro, arrastre funcional (la página se reordenó). **Pero Ricardo, tras probarlo él en su pantalla real, seguía viéndolo negro** — y aquí el dato clave: ni mi captura con cursor ni su propia grabación con la Herramienta Recortes de Windows lo recogen. El negro es real en la composición **en pantalla** (lo ve en vivo) pero no está en el mapa de bits que ninguna herramienta de captura o grabación lee — apunta a un fallo de composición del canal alfa de la ventana en capas que usa Windows para esta imagen de arrastre, no a nada que una captura pueda enseñar. Revisado `HKCU\Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers` (vacío, sin capa de compatibilidad para ningún exe) y `HKCU\...\Themes\Personalize\EnableTransparency` (=1, no desactivada): no es ninguna de las dos causas per-usuario más obvias. **Arreglo**: `_run_drag` deja de usar canal alfa por completo — `QImage.Format.Format_RGB32` (opaco) en vez de `Format_ARGB32_Premultiplied`, relleno celeste claro `#EAF3FC` con borde azul, sin `setOpacity()`. Sin alfa que la composición pueda mezclar mal, no hay semitransparencia que falle; a cambio el fantasma deja de ser semitransparente. 169/169 OK (5 omitidas). **Pendiente de que Ricardo confirme en su pantalla real** — si sigue en negro incluso sin alfa, el siguiente paso sería descartar una causa de sesión (reiniciar `explorer.exe`/DWM, o comprobar si el `AventyaPDF.exe` instalado sin ningún cambio de esta sesión también lo muestra ahora mismo, para separar «algo cambió en el código» de «algo cambió en el equipo desde ayer», que es la sospecha de Ricardo). Sin reempaquetar. Propagado a [docs/edicion_pdf.md](docs/edicion_pdf.md). |
| r81 | 2026-09-25 | **El fantasma del arrastre de miniaturas ya no es la miniatura real, sino un rectángulo liso, y se construye con alfa premultiplicado** (el negro de r80 seguía saliendo; petición de Ricardo: «El problema persiste, si el problema es la miniatura, se puede cambiar por un rectángulo en blanco del mismo tamaño en lugar de ser una miniatura real. Piensa que antes ese problema no existía, mira las modificaciones que hiciste sobre estas herramientas»). **Revisadas las modificaciones de esta sesión** (`git diff` desde el último commit): lo único tocado en `_run_drag`/`_ThumbList` en toda la conversación era el propio ajuste de r80; nada más de lo cambiado (paneles de Firma/Comprimir, pestaña Firmas Certificadas, la búsqueda en la barra principal) toca el arrastre de miniaturas. El ajuste de tamaño físico por `devicePixelRatio` de r80 era correcto pero insuficiente: `QPixmap(size)` construye un pixmap de formato **ambiguo** (normalmente sin alfa premultiplicado), y la composición de imágenes de arrastre de Windows (`IDragSourceHelper`, vía OLE, no Qt) espera alfa **premultiplicado** — con alfa sin premultiplicar es típico que pinte en negro donde debería verse transparente, sea cual sea el contenido. **Arreglo doble**: (1) el fantasma se construye ahora con `QImage(size, QImage.Format.Format_ARGB32_Premultiplied)` en vez de `QPixmap(size)`, y se convierte con `QPixmap.fromImage()` al final; (2) ya no recorta `viewport().grab(rect)` (la miniatura real): es un rectángulo liso blanco con borde azul del mismo tamaño, más simple de componer y sin depender del contenido pintado de la lista en ese instante. Comprobado fuera de pantalla (offscreen): `QImage.format()` es `Format_ARGB32_Premultiplied`, la esquina fuera del rectángulo tiene alfa 0 (transparente de verdad) y el relleno alfa ≈216 (0,85 de opacidad); la mecánica del arrastre (`test_arrastrar_una_miniatura_la_traslada_de_verdad`) sigue funcionando → **169/169 OK** (5 omitidas). **Sigue sin poder comprobarse el color en un monitor real con escalado** (offscreen da `devicePixelRatioF()` = 1, y no hay forma de capturar la pantalla real de Ricardo mientras trabaja): pendiente de que él confirme si el negro ha desaparecido del todo. Sin reempaquetar (pendiente). Propagado a [docs/edicion_pdf.md](docs/edicion_pdf.md). |
| r80 | 2026-09-25 | **Arrastrar una miniatura ya no pinta de negro la parte inferior de la pantalla** (petición de Ricardo: «En las operaciones de páginas existe un pequeño error visual, cuando se arrastra una página para colocarla en otro lugar la parte inferior de la pantalla del PC hasta la miniatura que se está moviendo se rellena de color negro. este detalle hay que repararlo si no la herramienta deja de ser funcional»). **Causa** (`sidebar._ThumbList._run_drag`, r51/r52): el «fantasma» semitransparente que sigue al cursor durante el arrastre (`QDrag.setPixmap`, compuesto por el propio Windows vía OLE, no por Qt) se creaba con `QPixmap(rect.size())` — tamaño en píxeles **lógicos**, sin decirle su `devicePixelRatio`. Con el escalado de pantalla de Windows (125 %, 150 %…, lo habitual en portátiles, y Qt6 lo activa por defecto), el mapa de bits físico resultante era más pequeño de lo que el sistema esperaba para esa imagen de arrastre nativa, y quedaba mal dimensionada: el resto del área, sin pintar, se veía negro (no es un fallo de Qt en pantalla, sino de la composición nativa de Windows con un bitmap del tamaño equivocado). **Arreglo**: el fantasma se crea ahora en píxeles físicos (`rect.size() × devicePixelRatioF()`) y se le fija ese `devicePixelRatio` con `setDevicePixelRatio()`, igual que ya trae de serie `viewport().grab()` (la fuente del recorte que se pinta encima) — así físico y lógico quedan consistentes, como espera el compositor de arrastre de Windows. Comprobado fuera de pantalla (offscreen) que el pixmap resultante conserva el tamaño lógico correcto, un canal alfa real (no negro opaco) y el `devicePixelRatio` fijado; la mecánica de arrastre en sí (probada por `test_arrastrar_una_miniatura_la_traslada_de_verdad`, que si dispara `_run_drag` de verdad) no cambia → **169/169 OK** (5 omitidas). No se pudo verificar el color en una pantalla real con escalado (offscreen siempre da `devicePixelRatioF()` = 1). Sin reempaquetar (pendiente). Propagado a [docs/edicion_pdf.md](docs/edicion_pdf.md). |
| r79 | 2026-09-25 | **Fondo gris de la herramienta de búsqueda en la barra principal → transparente** (petición de Ricardo: «LA HERRAMIENTA DE BÚSQUEDA DEBE TENER EL MISMO COLOR QUE EL RESTO DE LA BARRA DE HERRAMIENTAS O SER TRANSPARENTE»). **Causa**: al mudar la búsqueda a `_topbar` en r78 quité la regla `QFrame#find_bar { background: #FFFFFF; ... }` pensando que ya no hacía falta por vivir «dentro» de la barra blanca — pero la regla general de `main.STYLESHEET`, `QWidget { background-color: #F3F3F3 }` (gris, la de fondo de toda la ventana), se aplica a **cada widget por separado**, no se hereda visualmente del padre: el nuevo `QWidget#find_bar` y el `QLabel` del contador (`_find_count`) se pintaban grises, desentonando con el blanco de `#topbar`. Arreglo en `main.py`: `QWidget#find_bar, QWidget#find_bar QLabel { background: transparent; }` (el campo `_find_edit` no se toca: su fondo blanco con borde es a propósito, como cualquier `QLineEdit`). Comprobado con una captura fuera de pantalla (offscreen) del `_topbar` real, comparando el color de un píxel junto al contador contra el resto de la barra: **`#ffffff` en los dos sitios** (antes del arreglo habría sido `#f3f3f3` junto al contador). 169/169 OK (5 omitidas). Sin reempaquetar (pendiente). Propagado a [docs/interfaz_grafica.md](docs/interfaz_grafica.md). |
| r78 | 2026-09-25 | **La búsqueda deja de ser una barra aparte: ocupa el sitio del botón en la barra principal** (petición de Ricardo: «La barra secundaria de la herramienta debe desaparecer, en su lugar, cuando pulses sobre el botón de búsqueda, este botón se oculta y en su lugar aparece toda la herramienta de búsqueda que antes aparecía en una barra secundaria y si se pulsa la "X" de cerrar, vuelve a la posición original... con el botón para activarla visible de nuevo»). `_build_find_bar()` (`window_menus.py`) construía un `QFrame` con altura y fondo propios, añadido a la columna del visor **encima de él** (`right_lay`, entre el aviso y `_build_viewer()`), centrado con `addStretch()` a los dos lados: al mostrarse empujaba la página hacia abajo (igual que el aviso). Ahora construye un `QWidget` sin fondo ni altura propia que se añade **dentro de `_build_topbar()`**, justo después del botón de búsqueda (`_btn_find`, antes variable local `b_find`, ahora atributo para poder ocultarlo). `show_find()`/`hide_find()` alternan la visibilidad de `_btn_find` y del widget de búsqueda (nunca los dos a la vez); `_stash_active` (cambio de documento) también restaura el botón. Como la barra principal tiene altura fija (50 px), activar o cerrar la búsqueda ya no desplaza ni el visor ni el panel lateral. Quitada la regla CSS `QFrame#find_bar` (ya no aplica: no es `QFrame` ni tiene fondo propio) y el campo se estrechó de 280 a 220 px (compite por sitio con el resto de la barra principal, que antes no tenía). Reescritas `test_boton_de_busqueda_alterna_y_busqueda_dinamica` (botón y herramienta nunca visibles a la vez, la «X» también devuelve el botón) y la parte de búsqueda de `test_opciones_de_herramienta_en_el_panel_lateral` (ya no se comprueba que empuje el visor, sino que no desplaza nada y que `_find_bar` cuelga de `_topbar`, no de la columna del visor) → **169/169 OK** (5 omitidas). Comprobado también fuera de pantalla (offscreen): con un PDF abierto, `show_find()` oculta el botón y muestra la herramienta sin cambiar la altura de la barra principal; `hide_find()` la revierte. Sin reempaquetar (pendiente). Propagado a [docs/interfaz_grafica.md](docs/interfaz_grafica.md). |
| r77 | 2026-09-25 | **«Firmas Certificadas» con icono de certificado y apertura siempre que el PDF esté firmado; Comprimir rediseñado con círculos** (dos peticiones de Ricardo: 1) «El icono del panel lateral del visor de "Firmas" debería ser el icono del certificado y cambiar el nombre... a "Firmas Certificadas"... este visor de firmas certificadas siempre se debe mostrar abierto en cuanto se abra un PDF que traiga una firma certificada»; 2) «el menú de Comprimir PDF sigue siendo un caos. Primero quita la palabra nivel y en lugar de botones, utiliza una lista de selectores tipo círculo, las frases explicativas deben ser más cortas... para guardar el PDF... pones la frase "Guardar copia comprimida" y seguidamente el icono de la herramienta..., borrando la última frase»). (1) `SidePanel.PANELS` y el título de `SignaturesPanel` pasan de «Firmas» (icono r76 de la estilográfica) a **«Firmas Certificadas»** con el icono del certificado (`"opt_cert"`); el menú «Ver» se renombra igual. `_set_document` ya no exige que el panel lateral estuviera cerrado para abrir Firmas Certificadas: si `doc_tools.signed_count(doc)`, se abre siempre (antes solo competía con «thumbs» cuando el panel estaba cerrado). (2) El panel Comprimir (r75/r76) se rehace entero: los tres `QPushButton#side_seg_btn` se sustituyen por `QRadioButton#side_radio` (círculos nativos, nuevo estilo en `main.py`) sin la etiqueta «Nivel»; cada uno lleva una frase corta («Alta calidad, imágenes 150ppp»…, con el ppp real de `Level.color_ppi`, no un texto suelto) en vez del nombre del nivel + una descripción larga aparte (`_lbl_compress_lvl` desaparece). La fila de acción cambia de icono-solo a **«Guardar copia comprimida» + icono** (mismo `"compress"`/`folder_zip` que ya tenía desde r76), y se quita la línea de ayuda final. `_on_compress_level(key)` se simplifica (ya no actualiza ninguna etiqueta). Actualizada `test_comprimir_pdf_desde_la_interfaz` (sigue usando `_compress_level_btns`, ahora `QRadioButton`, mismo `.click()`/`.isChecked()`) → **169/169 OK** (5 omitidas). Comprobado también fuera de pantalla (offscreen): abrir un PDF firmado con el panel en «Comentarios» lo cambia a Firmas Certificadas; los tres textos y el icono de acción del panel Comprimir son los esperados. Sin reempaquetar (pendiente). Propagado a [docs/interfaz_grafica.md](docs/interfaz_grafica.md). |
| r76 | 2026-09-25 | **Comprimir con selectores en vez de desplegable, icono de acción igual al de la herramienta, y bug real de la pestaña Firmas** (dos peticiones de Ricardo: 1) «cambia el icono de las herramientas laterales correspondiente a "Firmas" por el de la estilográfica de la herramienta "Firma"»; 2) «La herramienta de compresión al abrirse en el panel lateral queda horrible, mejor utiliza selectores en lugar de un desplegable y el botón de acción debe tener el mismo icono de la carpeta comprimida del de la herramienta»). (1) `SidePanel.PANELS` usa `icons.glyph("handsign")` para «Firmas» en vez de `"panel_signatures"` — de paso se vio que `_banner_btn`/`_banner_action` (`window_menus._build_banner`, `window_document._update_banner`) habían quedado muertos desde r73 (quitar el aviso de firma dejó `_banner_action` siempre a `None`, el botón nunca podía mostrarse): se retiraron. (2) El `QComboBox` `_compress_level_cb` se sustituye por `_compress_level_btns` (r75), tres `QPushButton` de texto («Baja», «Recomendada», «Extrema») checkables en un `QButtonGroup` exclusivo, estilo nuevo `#side_seg_btn` en `main.py`; el nivel activo se guarda en `_compress_level_key` (antes se leía `_compress_level_cb.currentData()`). El icono del botón de acción pasa de `"save_copy"` a `"compress"` (`folder_zip`), el mismo que `_btn_compress` en la barra principal. **Bug real encontrado al verificar** (no causado por este cambio, sino por r74): con un certificado real del almacén de Windows ya recordado en el registro de este equipo, `_sign_cert_lbl` desbordaba la columna porque no tenía ajuste de línea — los nombres de prueba son cortos y nunca lo habían disparado. Arreglado con `setWordWrap(True)`; el test genérico de «una sola línea por etiqueta» (`test_opciones_de_herramienta_en_el_panel_lateral`) ahora excluye las etiquetas que ajustan línea a propósito en vez de forzarlas todas a una línea. Actualizada `test_comprimir_pdf_desde_la_interfaz` para los botones nuevos → **169/169 OK** (5 omitidas). Comprobado también fuera de pantalla (offscreen) que el icono de acción coincide exactamente con el de la barra principal. Sin reempaquetar (pendiente). Propagado a [docs/interfaz_grafica.md](docs/interfaz_grafica.md). |
| r75 | 2026-09-25 | **Comprimir se muda al panel lateral, como Firma, y se retira `_opt_row`** (petición de Ricardo: «Haz el mismo trabajo de traspaso al panel lateral y reorganización de la herramienta de compresión de PDF», aclarando después que se refería a la barra secundaria que aparecía al pulsar el icono de comprimir). `_compress_panel` deja la barra horizontal `_opt_row` y pasa a construirse con `_side_form("Comprimir PDF")` en `_build_side_tool_panels`, igual que Firma en r74. Reorganizado: fila «Nivel» con el combo, debajo la descripción del nivel como línea de ayuda (antes una etiqueta en la misma fila que el combo) y, por último, el único icono de acción — comprimir y guardar copia (`compress_pdf`) — con otra línea de ayuda. Se activa igual que antes con `_btn_compress`/`_toggle_compress_panel` (botón e interruptor propios, no `_toggle_tool`), pero ahora empuja `SidePanel.tools` en vez de aparecer encima del visor. **Como ya no queda ninguna herramienta en `_opt_row`, se retiró entera**: `_build_options_row()`, el atributo `_opt_row`, la fila que la añadía al layout, `_refresh_opt_row()` (renombrado `_refresh_side_tools()`, ahora también cuenta a `_compress_panel`), la compensación de desplazamiento del visor en `_show_annot_opts` (`_compensate_opt_shift`, que ya no podía dispararse) y los helpers `_opt_glyph`/`_opt_sep`/`_opt_lbl` que solo usaba Comprimir; también las reglas CSS `#options_row` en `main.py`. Actualizada `test_opciones_de_herramienta_en_el_panel_lateral` (Comprimir probado igual que el resto) y corregida `test_operaciones_de_pagina_en_el_panel_lateral` (comprobaba `_opt_row.isHidden()`, ahora `_sign_panel.isHidden()`) → **169/169 OK** (5 omitidas). Comprobado también fuera de pantalla (offscreen) que el panel se abre, con qué texto e icono. Sin reempaquetar (pendiente). Propagado a [docs/interfaz_grafica.md](docs/interfaz_grafica.md) y [docs/arquitectura.md](docs/arquitectura.md). |
| r74 | 2026-09-25 | **La barra de Firma se muda al panel lateral y se simplifica** (petición de Ricardo: «quiero que la barra de herramientas de la firma de documentos se abra en el panel lateral, para ello organiza mejor los botones de uso. Primero se debe mostrar el certificado selecciona[do] y debajo sólo 2 opciones seleccionar nuevo certificado usando el icono del certificado digital y firma manuscrita. Además debes intercambiar los iconos de los botones de firma digital y firma manuscrita. Por cierto la herramienta "Firma digital" debe cambiar su nombre por "Firma"»). `_sign_panel` deja `_opt_row` (que ahora solo sirve a Comprimir) y pasa a construirse con `_side_form("Firma")` como el resto de herramientas (`_build_side_tool_panels`), empujando el panel lateral igual que Texto, Nota, etc. (r72). Debajo del certificado seleccionado (`_sign_cert_lbl`) quedan solo dos iconos: elegir certificado (`_change_cert`, con el icono `opt_cert`, el del certificado digital) y firma manuscrita (`_btn_handsign`); se retiró el botón «olvidar el certificado recordado» (sin sustituto en la interfaz: para cambiar de certificado se usa siempre el selector completo, que también sirve para reemplazarlo). Iconos intercambiados entre el botón «Firma» de la barra principal y el de firma manuscrita (`"handsign"`/`"sign"` en `icons.ICONS`), y el primero se renombra de «Firma digital PAdES» a «Firma». `_refresh_opt_row()` ajustado (Firma ya no cuenta para `_opt_row`, sí para `sidebar.set_tools_visible`). Actualizada `test_opciones_de_herramienta_en_el_panel_lateral` para probar Firma junto al resto de herramientas → **169/169 OK** (5 omitidas). Sin reempaquetar (pendiente). Propagado a [docs/interfaz_grafica.md](docs/interfaz_grafica.md). |
| r73 | 2026-09-25 | **El aviso de firma desaparece del visor y vive en el panel lateral** (petición de Ricardo: «quiero que la barra de notificación o aviso de que un PDF está firmado con certificado, desaparezca del visor de PDF y simplemente aparezca en el panel lateral»). `_update_banner()` ya no añade el mensaje «Este documento está firmado digitalmente…» (el aviso superior solo queda para formulario/cifrado); `_set_document()` abre el panel lateral de **Firmas** en vez de Miniaturas cuando se abre un documento firmado con el panel cerrado, igual que ya hacía tras firmar uno. Sin cambios en el resto del aviso ni en `SignaturesPanel`, que ya mostraba el detalle completo (firmante, fecha, verificación) al abrirlo. 54/54 pruebas de interfaz OK. Sin reempaquetar (pendiente). Propagado a [docs/interfaz_grafica.md](docs/interfaz_grafica.md). |
| r72 | 2026-09-24 | **Las opciones de todas las herramientas salen arriba del panel lateral** (petición de Ricardo: «todas las herramientas que se abren dentro del panel lateral deben aparecer en la parte superior del mismo, no en el centro… tras cambiarlo vuelve a empaquetar y a subir el repositorio»). **Causa medida**: con el panel cerrado, `SidePanel.tools` era lo único visible en la columna y el `QVBoxLayout` lo centraba (Texto a y = 236 de 698; Emoji, 128; Zoom, 305). Arreglo: `AlignTop` (invariante 46). De paso, **fallo mío de r69** visto en la captura: el combo «Tipo de letra» de 160 px se salía de la columna (panel 306 px, columna 290) → `COLUMN_MIN` = 310. Nueva prueba `test_opciones_de_herramienta_arriba_del_panel_lateral` (con el panel abierto y cerrado, las seis herramientas; comprobado que falla sin el arreglo) → **169/169 OK** (5 omitidas). Versión **2.0.4**, reempaquetada y publicada (Release `v2.0.4`). |
| r71 | 2026-09-24 | **Titular, licencia libre y repositorio público en GitHub** (petición de Ricardo: «quita lo de Aventya Technologies y todo lo de derechos reservados, la empresa se llama Aventya Asesoría Integral SL y la aplicación es de libre distribución con el enlace al repositorio en GITHUB… lo tienes que hacer tú»). **Decisiones de Ricardo** (preguntadas antes): repositorio **público** `Aventya/AventyaPDF`, licencia **AGPL-3.0**, excluir documentos de clientes y **anonimizar** docs y memoria, y **reempaquetar y publicar el instalador como Release**. Pie de la presentación: «© año Aventya Asesoría Integral SL · Libre distribución · GitHub» (enlace); «Acerca de» con titular, licencia y enlace; primera diapositiva menciona la libre distribución. Versión **2.0.3**; `AppPublisher`/`CompanyName` = Aventya Asesoría Integral SL (+ `AppPublisherURL`, `LegalCopyright`). Nuevos `LICENSE` (texto oficial de gnu.org), `README.md` (con las licencias de terceros comprobadas en los metadatos instalados: pdf2docx es MIT) y `.gitignore` (invariante 56). `git init`, primer commit y `gh repo create --public`; temas del repositorio añadidos y licencia reconocida por GitHub. Instalador **`AventyaPDF-Setup-2.0.3.exe`** regenerado con `empaquetado/construir.ps1` (autodiagnóstico del ejecutable: todo OK; `CompanyName` comprobado) y publicado como **Release `v2.0.3`** (etiqueta git `v2.0.3`; descarga comprobada sin sesión). El instalador **no está firmado** con certificado de editor: SmartScreen avisa (lo dicen las notas de la Release). → **168/168 OK** (5 omitidas). |
| r70 | 2026-09-24 | **Presentación inicial de la aplicación** (petición de Ricardo: «usando como base popup_tmp.png desarrolles y pongas en marcha un popup inicial… que vaya explicando todas sus características… la oportunidad de quitar este popup y que no vuelva a salir»; el archivo real se llama `popup_temp.png`). Nuevo `presentacion.py`: la maqueta reproducida en código (no se incrusta la PNG: traía «© 2024…» fijo), 11 diapositivas que avanzan solas (7 s, pausa con el ratón encima) y navegación manual; «No volver a mostrar al iniciar» y Ayuda › «Presentación de AventyaPDF» para volver a verla o reactivarla. Arranque comprobado fuera de pantalla con `main.main()` (salen `MainWindow` y `WelcomeDialog`). Nueva prueba `test_presentacion_inicial_y_no_volver_a_mostrar` (guarda y restaura la preferencia real) → **168/168 OK** (5 omitidas). Revisado en PNG. `popup_temp.png` se queda en la raíz como maqueta de referencia. Propagado a [docs/interfaz_grafica.md](docs/interfaz_grafica.md). |
| r69 | 2026-09-24 | **Herramienta Texto: se escribe con la fuente elegida, el combo enseña cada fuente con su letra y fuera el justificado** (petición de Ricardo: «la selección de fuentes además de su nombre deben mostrar su tipo de fuente… al escribir debe visualizarse dinámicamente su tipografía… la alineación… nunca puede ser justificado»; confirmó además que la prueba de la plumilla de r68 fue satisfactoria). **Causa medida**: la regla `QWidget` de `main.STYLESHEET` anulaba `setFont()` del editor sobre la página (salía la fuente de la interfaz a 13 px, **también el tamaño estaba mal** mientras se escribía). Arreglado en `inplace_editor.apply_style` (invariante 55). Combo: `_FontPreviewDelegate` + hoja de estilos del combo cerrado; ancho 140 → 160 px para que quepa «Noto Sans Mono». Alineación en ciclo de 3. Nueva prueba `test_texto_se_escribe_con_la_fuente_elegida_y_sin_justificar` (con la hoja de estilos real) → **167/167 OK** (5 omitidas). Revisado en PNG el combo abierto y cerrado. Propagado a [docs/interfaz_grafica.md](docs/interfaz_grafica.md). |
| r68 | 2026-09-24 | **Firma manuscrita con aspecto de estilográfica** (petición de Ricardo: «en la sub barra de la herramienta de firmas debe existir un icono de sello que permita la inserción o bien de una imagen de una firma, o bien crear la firma a mano alzada con el ratón… color del trazo, su grosor… que su estilo recuerde a una estilográfica, es decir que la tinta se superponga entre sí»). Nuevos `firma_manuscrita.py` (geometría y anotación) y `firma_manuscrita_ui.py` (diálogo Dibujar / Imagen). Botón de la plumilla en la barra de Firma (Fluent no trae icono de sello de caucho: se usó `calligraphy_pen`) y entrada en el menú Firmar. Plumilla biselada a 40° + velocidad; tinta translúcida al 75 % con **cada trazo rellenado aparte** para que los cruces se oscurezcan, también en los bucles de un mismo trazo. Vectorial en el PDF (Stamp, invariante 54). Imagen: quita el papel blanco y recorta. Nuevas pruebas `TestFirmaManuscrita` (4) y `test_firma_manuscrita_desde_la_barra_de_firma` → **166/166 OK** (5 omitidas). Revisado en PNG a 400 ppp y el diálogo renderizado fuera de pantalla. Ricardo lo probó a mano con el ratón: satisfactorio (r69). Falta reempaquetar el instalador. Propagado a [docs/firma_digital.md](docs/firma_digital.md) e [docs/interfaz_grafica.md](docs/interfaz_grafica.md). |
| r67 | 2026-09-24 | **La app ocupa ~100 MB menos abierta** (Ricardo: «lo que estamos buscando es que la aplicación pese menos estando abierta»). Medido antes de migrar: a igualdad de funciones WinUI 3 gasta **más** que Qt (94 frente a 64 MB privados), así que migrar la interfaz no ahorra memoria. Lo que pesaba era **numpy (+102 MB al importarse)**: OpenBLAS reserva un búfer por núcleo. `main.py` fija `OPENBLAS_NUM_THREADS=1` (con `setdefault`) antes de cualquier importación → app empaquetada con un PDF abierto **259 → 161 MB** privados; OCR igual de rápido (2 páginas: 77 → 71 s); 161 pruebas OK. Tabla completa y peso de cada biblioteca en `docs/plan_migracion_winui3.md` §10. Pendiente posible: importar pyHanko, OpenCV/numpy y pdf2docx solo cuando se usan (~35 MB más). **Versión 2.0.2** (icono r64, sello r65, memoria r67): `construir.ps1` → autodiagnóstico 7/7 OK → `empaquetado/salida/AventyaPDF-Setup-2.0.2.exe` (130 MB); el ejecutable nuevo ocupa 149-162 MB privados con un PDF abierto sin fijar la variable desde fuera (antes 259). |
| r66 | 2026-09-24 | **Las dos pruebas de concepto para una app nativa de Windows 11** (pendientes de r63; Ricardo: «mañana haces las dos pruebas»). **1. Estilo `windows11` de Qt**: casi idéntico con la hoja de estilos actual (solo cambian los menús) y roto sin ella; Mica no se ve → retoque cosmético, descartado como vía a «nativa». **2. WinUI 3 desde Python (PyWinRT)**: `prototipos/winui3/visor_poc.py` (+ `visor_poc.spec`), fuera de la app y con entorno propio `%LOCALAPPDATA%ventyapdfenv-winui3` (`winui3-*` 3.2.1, SDK 1.7). Funciona: XAML en tiempo de ejecución, Mica, barra de título propia con el icono, `CommandBar` con Fluent UI System Icons, página de PyMuPDF nítida en `WriteableBitmap`, Ctrl+rueda = zoom, clic → coordenadas de página, empaquetado con PyInstaller (89 MB). Trampas: fuentes propias solo con `ms-appx:///` (solo empaquetado), runtime del SDK completo obligatorio, `Application` sin argumentos en el constructor. Para arrancar se instaló con winget el runtime 1.6 completo (al final no hacía falta: se pasó a los paquetes 1.7). Resultados y conclusión en `docs/plan_migracion_winui3.md` §10. **Decisión pendiente de Ricardo**: vía Python + WinUI 3 o reescritura en C++. |
| r65 | 2026-09-24 | **Sello de firma con el `MOSCA.svg` nuevo** (petición de Ricardo: «utiliza la nueva imagen MOSCA.svg para las firmas con certificado»). SVG vectorial con degradado radial salmón detrás de la huella; `python create_signature_background.py` sin cambios de código → `signature_background.pdf` nuevo (sin imágenes; el degradado queda como sombreado + máscara suave vectorial). Comprobado firmando un PDF de prueba con un sello ancho y otro casi cuadrado (texto legible sobre el degradado, logotipo pegado a la derecha y recortado por las esquinas redondeadas) y con las 161 pruebas OK. |
| r64 | 2026-09-24 | **Icono nuevo** (petición de Ricardo: «Prepara el nuevo icono… es el icono de una aplicación para Windows 11 y también debe servir como icono de Ayuda y del instalador»). Origen `ICONO.png` (596 px); se descartó `ICONO.svg` porque solo incrusta ese mismo PNG. `create_app_icon.py` añade el margen de Windows 11 (1/16 desde 24 px), enfoque suave hasta 48 px y genera las imágenes del asistente de Inno Setup (`empaquetado/imagenes/*.bmp`, fondo liso: Inno no mezcla bien la transparencia), que el `.iss` usa con `WizardSmallImageFile`/`WizardImageFile`, una por escala. «Acerca de» muestra el icono a 64 px con `setIconPixmap` (`QMessageBox.about` lo dejaba en 32). Nueva prueba `test_imagenes_del_instalador_generadas_y_usadas`; 161 pruebas OK; el `.iss` compila con ISCC (probado con una carpeta de relleno). Falta verlo en el instalador real y en la barra de tareas con `construir.ps1`. |
| r63 | 2026-09-23 | **Plan de migración a una app nativa de Windows 11 con WinUI 3, XAML y C++/WinRT** (petición de Ricardo: «Prepara los pasos para que toda la aplicación sea nativa de windows 11 con WinUI 3 y XAML además de ser en C++»). Solo el plan, sin código: `docs/plan_migracion_winui3.md` (arquitectura Core/Plataforma/App, sustituto de cada biblioteca —MuPDF C, libtesseract, CNG/CryptMsg/CryptRetrieveTimeStamp, WinUI 3—, fases 0-8 con criterios de aceptación medibles, la app Python como oráculo, esfuerzo orientativo y 7 decisiones pendientes: licencia AGPL de MuPDF, validación DocMDP sin equivalente de pyHanko, exportar a Word, estado de C++/WinRT, MSIX frente a Inno Setup, Windows.Media.Ocr, solo Windows 11). Enlazado desde `docs/indice.md`. |
| r62 | 2026-09-23 | **Aplicación empaquetada con instalador** (petición de Ricardo: «¿puedes empaquetar y crear la aplicación con su instalador?»). **Decisiones de Ricardo** (preguntadas antes): instalar PyInstaller e Inno Setup en el equipo; **Tesseract incluido** en el instalador; **solo el usuario actual** (sin administrador); integración: **menú Inicio + escritorio** y **«Abrir con» para PDF**, sin menú contextual. **Herramientas**: PyInstaller 6.22.3 en `%LOCALAPPDATA%\aventyapdf\build-venv` con las mismas versiones que el entorno de la app (`pip freeze`); Inno Setup 6.7.3 con `winget --scope user`. **Cambios en la app**: `dependencias.asegurar_o_salir` no hace nada con `sys.frozen`; `tesseract_setup` usa primero el Tesseract incluido (`BUNDLED_EXE`) y copia sus idiomas en vez de descargarlos; `autodiagnostico.py` nuevo + interceptado en `main.main()`. **Empaquetado** (`empaquetado/`, ver `docs/empaquetado.md`): PyInstaller en modo carpeta (arranque rápido), datos en `_internal` porque los módulos calculan sus rutas con `__file__`; fuera el códec de vídeo de OpenCV (29 MB); Tesseract con **solo las DLL que importa** (`pefile`; 26 DLL, 161 MB, casi todo `libtesseract-5.dll`, 97 MB) + modelos «best» + licencia; compilación fuera del proyecto (carpeta compartida). **Verificado de verdad**: autodiagnóstico del **ejecutable empaquetado** 7/7 (con el OCR usando el Tesseract incluido y la firma con certificado de pruebas: firmar, verificar y quitar la última); instalador **130 MB**; instalación silenciosa en carpeta de prueba → programa, Tesseract, acceso del menú Inicio, `AventyaPDF.Document` + `.pdf\OpenWithProgids` + `Applications\AventyaPDF.exe` + `RegisteredApplications`, entrada en Aplicaciones instaladas (2.0.1); la **app instalada** pasa su autodiagnóstico y, lanzada con un PDF como hace «Abrir con», abre «Formulario.pdf — AventyaPDF» en 5,7 s en frío; **desinstalación** silenciosa → no queda nada (la primera vez quedó la clave vacía `HKCU\Software\Aventya`: añadido `uninsdeletekeyifempty`, borrada la que dejó la prueba tras comprobar que estaba vacía, y repetido el ciclo limpio). La desinstalación **no** borra `%LOCALAPPDATA%\aventyapdf` (datos del usuario, compartidos con desarrollo). **Pendiente**: el instalador no está firmado con certificado de firma de código → SmartScreen avisará. 160/160 pruebas del código fuente siguen OK. |
| r61 | 2026-09-23 | **Firmas verificadas siempre y papelera para quitar la última** (petición de Ricardo: «los certificados del panel lateral siempre se deben visualizar con la verificación realizada, no debe hacerse una verificación manual… el botón… debe cambiarse por un icono de basura y debe permitir eliminar la firma… dejando el recuadro de firma para poder clicar y usar otro certificado»). **Preguntado antes** (cambiaban el diseño): papelera **por firma** (no una en la cabecera) y **solo en la más reciente** (quitar una anterior invalidaría las posteriores). **Panel**: `SignaturesPanel` verifica solo al mostrarse, en segundo plano (`window_document.ValidateWorker`, con turno para descartar resultados obsoletos), con «Verificando las firmas…»; lista también los recuadros de firma vacíos («haz clic en él para firmar») y, con otros cambios sin guardar, avisa de que guardar reescribirá el archivo. Fuera el botón del escudo y el icono `validate`; el menú Firmar › «Validar todas las firmas» pasa a «Ver las firmas (verificadas)». **Quitar la firma sin romper las demás** (`signer_backend.remove_last_signature`): editar el campo y guardar reescribiría el PDF e invalidaría todas; en cambio, como cada firma es una actualización incremental, se trunca el archivo al final de la revisión anterior (`_revision_end`, con `xrefs.get_startxref_for_revision`; comprobado que coincide **byte a byte** con el archivo de antes de esa firma) y, si el campo no existía vacío en esa versión, se añade uno vacío con el mismo nombre y recuadro (`append_signature_field`, incremental). Las firmas anteriores conservan su veredicto (probado: «Relleno de formularios / firmas posteriores», nivel permitido). El resultado queda como **cambio sin guardar** en `_pending_bytes` (nuevo en `_SESSION_ATTRS`): guardar y firmar usan esos bytes tal cual; cualquier otra edición (`mark_modified`) lo descarta. **No pasa por deshacer** (sus instantáneas son copias reescritas); para arrepentirse, cerrar sin guardar. Con otros cambios sin guardar la papelera sale desactivada con el motivo en el tooltip. **De paso**: el aviso superior decía «firmado digitalmente (n firmas)» contando recuadros vacíos, y `has_signatures` avisaba de firmas invalidadas con solo un recuadro vacío: nuevo `doc_tools.signed_count` (campos con `/V`). **Pruebas**: `test_quitar_la_ultima_firma_conserva_las_anteriores_y_el_recuadro` (y refirmar dentro), `test_solo_se_puede_quitar_la_firma_mas_reciente`, `test_quitar_la_firma_de_un_recuadro_del_formulario` (vuelve exactamente al PDF original) y, en la interfaz, `test_panel_de_firmas_verificado_solo_y_papelera_en_la_ultima` (verificado sin botón, papelera solo en la última, quitar → recuadro vacío listado, guardar → Firma1 sigue válida, papelera desactivada con otros cambios). **Comprobado visualmente** (captura offscreen): panel con las dos firmas verificadas y la papelera en Firma2; tras quitarla, Firma1 con la papelera y «Recuadro de firma vacío» de Firma2, y el recuadro vacío en la página. → **160/160 OK** (incluye r60). Propagado a `docs/firma_digital.md` y `docs/herramientas_profesionales.md`. |
| r60 | 2026-09-23 | **OCR mucho más preciso** (petición de Ricardo: «el ocr no es tan preciso como esperaba, debe ser mucho mejor»; probado con su `OCR.PDF`, la foto de una minuta de una entidad financiera de 3000 × 4000 pt con una imagen de 6000 × 8000 px). **Diagnóstico medido, no supuesto**: la capa de texto que traía el archivo se había reconocido **boca abajo** (el IBAN de la minuta salía como letras sin sentido: era el texto girado 180°), y el OCR de la app lo reproducía: el OSD de Tesseract decía «girar 180°» (confianza 0,79) con la página derecha. Con la orientación buena Tesseract leía la minuta casi perfecta. **Banco de pruebas** (en el scratchpad, no en el proyecto): 45 escaneos simulados (páginas reales de Factura/Formulario/Notificación + páginas sintéticas con NIF, importes y tildes; limpio 300 ppp, JPEG 200 ppp, torcido 2,2°, ruido y fondo gris, «malo» = todo junto) medidos con F1 de palabras. **Resultados**: app actual 0,759 (la p. 2 de la factura, 0,035: boca abajo en las 5 versiones); sin el giro erróneo 0,876; `tesseract.exe` directo 0,906; Sauvola 0,912; enderezado 0,918; **enderezado + Sauvola 0,922** (malo 0,746 → 0,938; ruido 0,636 → 0,827). Descartados con datos: `psm 4` (0,891, aunque en `OCR.PDF` ayudaba), `spa+eng` (pierde tildes: COMISION), quitar ruido y reescalar la letra (empeoran). **Cambios** (`pdf_ocr`): orientación comprobada (invariante 27 g), capa anterior sustituida (h), enderezado ≥ 1° con la capa devuelta girada (i), `tesseract.exe` con `thresholding_method=2` y `textonly_pdf=1` en vez de `pdfocr_tobytes` (que no deja elegir nada), `pdf.ttf` copiada a `TESSDATA_DIR`, `numpy`/`opencv-python-headless` explícitos en `requirements.txt` (ya venían con `pdf2docx`). **`OCR.PDF` de principio a fin**: capa basura fuera, orientación bien, F1 ≈ 0 → **0,957**, importes, cuenta y NIF correctos y cada palabra sobre su tinta (comprobado dibujando las cajas); 125 s frente a 176 s. Quedan fallos menores: «2º» → «22», «@» → «O», el título «Minuta» y el lema del logotipo. **Tropiezos**: la primera versión de la verificación de orientación rechazaba el giro bueno en páginas de lado (Tesseract 5 lee bien las líneas verticales: 96,5 de confianza a 0° y a 270°) → las palabras verticales cuentan como 0; y exigir `pdf.ttf` en `ensure()` rompía las pruebas de instalación simulada → solo se avisa. Una comparación sobre pasar `--dpi` o dejar que Tesseract lo estime quedó **sin terminar** (el sistema paró el proceso por falta de memoria al lanzar 7 reconocimientos en paralelo): pendiente, podría arreglar palabras partidas en páginas gigantes como `OCR.PDF`. Pruebas nuevas en `TestOCR`: orientación propuesta comprobada, capa anterior sustituida, estimación de la inclinación y página torcida con la capa sobre la tinta. Propagado a `docs/herramientas_profesionales.md`. |
| r59 | 2026-09-23 | **«Resaltar, subrayar o tachar» también a mano alzada; fuera «Marcador a mano alzada»** (petición de Ricardo: si no se puede seleccionar texto, que se pueda aplicar por encima de imágenes y demás objetos a mano alzada, «procurando que las líneas salgan rectas cuando se hace un movimiento rápido»; la herramienta toma el icono del marcador, que se elimina). **Cómo decide**: al pulsar, si hay una palabra bajo el puntero (holgura de 3 pt, `MARKUP_TEXT_MARGIN`, para poder arrancar justo antes de la primera letra) marca el texto como siempre; si no, trazo a mano alzada. El cursor lo anuncia (I sobre texto, cruz fuera). **Trazo**: `window_document.add_freehand_markup` → `Ink` con `/Subj MANO|tipo` (`doc_tools.FREEHAND_PREFIX`); resaltar = trazo ancho (12 pt) en modo **Multiply** (tiñe la imagen sin taparla; comprobado con una captura: lo negro de la imagen sigue negro), subrayar/tachar = línea de 2 pt, ondulado = zigzag (`viewer.squiggle`). Grosor por tipo en «Grosor del trazo» del panel, en pt. La herramienta sigue activa tras cada trazo, como con el texto. **Enderezado por velocidad** (`viewer.straighten_stroke`): la duración se mide con `time.monotonic()` entre pulsar y soltar y la velocidad en píxeles de pantalla (no depende del zoom); rápido (≤ 0,35 s o ≥ 900 px/s) y a ≤ 18 % de la recta inicio→fin → recta, ajustada a horizontal/vertical si está a < 8°; lento → se respeta salvo el temblor del pulso (≤ 2 pt o 4 %). **Tropiezo destapado por la comprobación visual**: la primera versión conservó como respaldo la regla del marcador antiguo (`_maybe_straighten`, desviación típica < 12 %), y un trazo lento y ondulado salía igualmente recto — contradice «a mano alzada»; se retiró esa regla. **Eliminado**: modo `HIGHLIGHT`, su botón, su panel (`_mrk_panel`, `_on_mrk_size`, `_on_mrk_color`), el menú Comentar › «Marcador a mano alzada», la tecla **M**, `viewer.marker_*`, `PDFUtils.add_ink_annotation` y `_maybe_straighten`. Las `Ink` que ya estén en un PDF (del marcador antiguo o de otra aplicación) se seleccionan con el panel de esta herramienta y se tratan como resaltado. **Icono**: `icons.ICONS["markup"]` pasa de `text_underline` a `highlight`. **Pruebas**: `TestTrazoAManoAlzada` (núcleo: rápido casi horizontal → recta horizontal; rápido diagonal → recta sin forzar el eje; la velocidad cuenta en píxeles de pantalla; lento y curvo se respeta; lento pero recto pierde el temblor; ondulado alterna) y `test_marcar_a_mano_alzada_fuera_del_texto` (gesto real con `QMouseEvent` y `time.monotonic` simulado: texto → Highlight, imagen → Ink recta con Multiply, tachar → Ink fina, deshacer, y el panel recupera tipo y grosor al seleccionarla — esta última destapó que el combo no se sincronizaba para las Ink, corregido); ajustadas las que listaban `HIGHLIGHT`/`_mrk_panel`/`marker_opacity`. La etiqueta y la ayuda del panel se acortaron («Grosor del trazo», «Fuera del texto: a mano alzada») porque `test_opciones_de_herramienta_en_el_panel_lateral` exige una sola línea. → **152/152 OK**. Propagado a `docs/edicion_pdf.md` (§2 reescrito), `docs/interfaz_grafica.md` y `docs/herramientas_profesionales.md`. |
| r58 | 2026-09-23 | **Negrita y cursiva con iconos Fluent, no con letras en Segoe UI** (petición de Ricardo: «Deja de usar Segoe UI Variable / Segoe UI como fuente de iconos para los botones, en su lugar debes usar Fluent UI System Icons»). Inventario: el **único** botón que se dibujaba con Segoe UI era `main_window._make_style_btn` —negrita «N» y cursiva «I» de los paneles Texto y Editar contenido—, que sobrescribía con su propia hoja de estilos la fuente Fluent de `#opt_btn`. Ahora recibe una clave de icono (`"bold"` → `text_bold`, `"italic"` → `text_italic`, nuevas en `icons.ICONS`) y su hoja local solo conserva el resaltado de `:checked`. **Consecuencia aceptada**: Fluent solo trae el glifo de negrita con «B» inglesa (no hay variante «N»); r31 había mantenido las letras por eso, y ahora se prioriza que todos los botones de icono salgan de Fluent. **Lo que NO se tocó**: Segoe UI sigue siendo la letra de los *textos* de la interfaz (hoja global de `main.py`) y del editor de notas (`viewer.py`), que no son iconos. Prueba nueva `test_negrita_y_cursiva_con_iconos_fluent` (aplica `main.STYLESHEET` a la app durante la prueba, porque la batería no la carga y sin ella todos los botones salen en «Sans Serif») → **144/144 OK**. **Comprobado visualmente** con una captura offscreen del panel Texto: la B y la I de Fluent, con la negrita marcada en azul. Propagado a `docs/interfaz_grafica.md`. |
| r57 | 2026-09-23 | **Icono propio de la aplicación** (petición de Ricardo: «convierte el fichero "icono.png" en un icono de windows para todos los tamaños oficiales necesarios y úsalo como icono de la aplicación»). El archivo real es `ICONO.png` (596×596, RGBA). Nuevo `create_app_icon.py` → `vendor/icono/aventyapdf.ico` con los **14 tamaños** de la guía de Microsoft para iconos de aplicación (16, 20, 24, 30, 32, 36, 40, 48, 60, 64, 72, 80, 96, 256), cada uno reducido desde el original con Lanczos (no en cadena). **Dónde se usa**: (1) `main.py` → `app.setWindowIcon(QIcon(icons.APP_ICON))`, que vale para la ventana principal y todos los diálogos; (2) `_set_app_user_model_id()` llama a `SetCurrentProcessExplicitAppUserModelID("Aventya.AventyaPDF")` **antes** de crear la ventana: sin eso Windows agrupa la ventana con `python.exe` y la barra de tareas enseña el icono de Python en vez del nuestro; (3) `Install-ContextMenu.ps1` pone el valor `Icon` en el verbo «Combinar con AventyaPDF» y en el submenú «AventyaPDF» de las imágenes. **Límites que quedan**: la ventana de consola de `run.ps1` (a propósito `python.exe`, no `pythonw`) sigue con el icono de PowerShell/Python; y el menú contextual ya instalado no cambia hasta volver a ejecutar `Install-ContextMenu.ps1`. A 16 px el rótulo «PDF» del dibujo ya no se lee (solo la «A»), propio del diseño. **Comprobado**: el `.ico` trae los 14 tamaños (Pillow y `QIcon.availableSizes()`), renderizado a 16/32/48/256 px con Qt; el menú contextual se instaló en una rama de registro de prueba (`-Raiz`) y el valor `Icon` apunta a un archivo que existe, luego se borró esa rama (el menú real no se ha tocado). Prueba nueva `test_icono_de_la_aplicacion_con_todos_los_tamanos` → **143/143 OK**. De paso, la cabecera de esta memoria seguía en r55 aunque ya existía r56: corregida. |
| r56 | 2026-09-22 | **La aplicación pasa a llamarse «AventyaPDF»** (petición de Ricardo, a mitad de decidir si instalar de verdad el menú contextual de r55: «Quiero que cambies el nombre del programa y del proyecto, ahora debe llamarse "AventyaPDF"»). **Dos aclaraciones antes de tocar nada** (afectaban a rutas del sistema, no solo a texto): forma exacta del nombre visible → **«AventyaPDF», una sola palabra**, tal cual; alcance → **todo**, incluidas la carpeta del proyecto y `%LOCALAPPDATA%` (no solo el texto visible). **Inventario primero** (`grep` recursivo insensible a mayúsculas: una búsqueda sensible a mayúsculas se había dejado fuera los enlaces `file:///…/ANTIGRAVITY-PDF/…` en mayúsculas de los docs 1-5, corregido antes de tocar nada). **Reemplazo mecánico ordenado** (para no corromper coincidencias parciales: las cadenas más largas y específicas antes que las cortas) en **27 archivos** (todo el código, `Install-ContextMenu.ps1`, `requirements.txt` y los `docs/*.md`, salvo `PLAN_DE_IMPLEMENTACION.md` y `Compartimentar.odt`, documentos propios de Ricardo que no se tocan, como ya se decidió en r42): `"Antigravity PDF"` → `"AventyaPDF"` (nombre visible: título de ventana, «Acerca de», diálogos, prosa de los docs); `"antigravity-pdf"` → `"aventyapdf"` (identificadores: organización de `QSettings`/`cert_manager._APP`, carpeta de `%LOCALAPPDATA%`, tipo MIME interno del arrastre de miniaturas en `sidebar.py`, cabecera `User-Agent` de las descargas de la TSL/LOTL); `"ANTIGRAVITY-PDF"` → `"AVENTYAPDF"` (menciones de la carpeta del proyecto); `"Antigravity Software S.L."` / `"Usuario de Pruebas Antigravity"` (datos ficticios del certificado de pruebas, `create_test_cert.py`) → `"Aventya Software S.L."` / `"Usuario de Pruebas Aventya"` (esta última también reutilizada como texto de muestra en `test_nombre_del_firmante_sin_identificadores`, de `test_nucleo.py`, sin relación con el certificado: solo comprueba que un nombre sin NIF ni comas pasa tal cual; actualizada a juego); los nombres de los verbos del registro en `Install-ContextMenu.ps1` (`AntigravityPDF.Combinar`, `AntigravityPDF`) → `AventyaPDF.Combinar` / `AventyaPDF` (antes solo se había cambiado el texto que ve el usuario en el menú, no la clave interna). `MEMORIA_EVOLUTIVA.md` se editó aparte, **a mano, no con el reemplazo automático**: las filas del historial (r1-r55) describen lo que era cierto **en su momento**, bajo el nombre antiguo, y no se reescriben (mismo criterio que ya se sigue con las rutas antiguas de la unidad `A:` en r5); solo se actualizaron los campos de estado actual (cabecera, tabla de módulos, §5, §8) y el título del propio documento. **Comprobado sin sorpresas**: `.\run.ps1 -Pruebas` completo tras el reemplazo → **142/142 OK** (las mismas pruebas de siempre; el renombrado no añade ni quita ninguna). **`%LOCALAPPDATA%`**: al apuntar ya `run.ps1` a `aventyapdf\venv`, esa misma tanda de pruebas **creó sola** un entorno nuevo ahí (491 MB, limpio, sin caché de pip — la prueba de que el entorno se crea bien de cero, gratis) mientras el antiguo `antigravity-pdf` seguía intacto; en vez de tirarlo, se migraron `tessdata` (idiomas de OCR: evita volver a descargarlos) y `errores.log` (no existía: nunca ha saltado un error real, se deja así) a la carpeta nueva, comprobado que `emoji_pdf` no lo referencia ya ningún archivo `.py` (resto huérfano de la función de emojis con WebEngine que se quitó en r40) y se dejó fuera de la migración, y se borró la carpeta antigua entera. **Aviso para Ricardo** (efecto colateral real, no solo cosmético): `cert_manager._KR_SERVICE` pasa de `"antigravity-pdf-signing"` a `"aventyapdf-signing"` — si alguna vez se guardó la contraseña de un `.pfx` en el Administrador de credenciales de Windows bajo el nombre antiguo, queda huérfana (no se borra ni se pierde el certificado, solo hay que volver a escribir la contraseña una vez; no se ha comprobado que hubiera ninguna guardada). **Lo único que queda pendiente, y por qué**: la carpeta del proyecto en disco **sigue llamándose `ANTIGRAVITY-PDF`**. Se intentó renombrarla dos veces con `Rename-Item` (la segunda tras mover explícitamente el directorio de trabajo del intérprete al padre con `Set-Location` primero, por si el propio proceso la tenía tomada) y las dos veces Windows devolvió *«The process cannot access the file because it is being used by another process»*; además, tras cada intento, el propio directorio de trabajo de las herramientas de esta sesión **vuelve solo** a `...\ANTIGRAVITY-PDF` aunque el comando termine en otra carpeta — indicio bastante claro de que es **esta misma sesión** (su seguimiento de archivos, el que genera los avisos de «cambiado en disco» de este mismo historial) la que mantiene la carpeta abierta, no un proceso ajeno que se pudiera cerrar. No se ha intentado forzar matando procesos a ciegas: es una carpeta que la propia sesión necesita para seguir funcionando, y un cierre a la fuerza es justo el tipo de acción irreversible/de sistema que hay que confirmar antes, no adivinar. **Pendiente para Ricardo, fuera de esta sesión** (cerrar Claude Code o abrir una consola aparte, y luego): `Rename-Item "C:\Users\Aventya\Proyectos\ANTIGRAVITY-PDF" "AVENTYAPDF"`; después, reabrir el proyecto ya desde la carpeta nueva. **No hace falta tocar nada de contenido tras el renombrado de la carpeta**: `Install-ContextMenu.ps1` resuelve la ruta del proyecto con `$PSScriptRoot` en el momento de ejecutarse, no con una ruta escrita a mano, así que ya apuntará bien sin más cambios. Sigue sin instalarse de verdad el menú contextual de r55 en el registro real (esa decisión se interrumpió por esta petición); se retoma en cuanto la carpeta tenga su nombre definitivo. No propagado a `docs/*.md` más allá del reemplazo mecánico del nombre (no hay ningún concepto nuevo que documentar, es un renombrado). |
| r55 | 2026-09-22 | **Menú contextual del Explorador de Windows: combinar PDF y convertir imágenes** (petición de Ricardo: «crear menú derecho del cursor en Windows para combinar varios PDF en uno usando esta aplicación y para convertir los archivos seleccionados en un PDF combinado o en varios PDF»). **Tres piezas nuevas, sin duplicar lógica**: (1) `doc_tools.merge_pdfs(paths)` — combina varios PDF completos en un `fitz.Document` nuevo, distinto de `main_window.merge_pdf()` (que solo añade un PDF al final del documento ya abierto); avisa con `ValueError` claro si alguno está protegido con contraseña, en vez de fallar con el error críptico de PyMuPDF. (2) `window_menus.combine_pdfs_from_paths(paths)` y `.create_separate_pdfs_from_images(paths)`, junto a `create_from_images()` que ya existía: los tres parten de cero (sin documento previo, a diferencia de `merge_pdf()`) y dejan el resultado **sin guardar**, en una pestaña nueva cada uno — mismo criterio que «Nuevo PDF en blanco»: ningún archivo original se toca, el usuario decide después dónde guardar. `create_separate_pdfs_from_images` abre tantas pestañas como imágenes, cada una con un PDF de una sola página. (3) `main.py`: `procesar_argumentos(window, argv)` — separado de `main()` para poder probarlo sin depender de `sys.argv` real ni de un bucle de eventos — reconoce `--combinar-pdf` / `--imagenes-a-pdf` / `--imagenes-a-pdfs-separados` (los indicadores que pasará el menú contextual) y llama al método correspondiente; sin ninguno de ellos, sigue abriendo el primer `.pdf` de la lista, el «Abrir con…» de toda la vida (comportamiento sin cambios). **Menú contextual real**: nuevo `Install-ContextMenu.ps1` (instala/`-Quitar`), solo `HKEY_CURRENT_USER\...\SystemFileAssociations` (sin administrador, tan reversible como `run.ps1 -Reinstalar`): verbo directo «Combinar con Antigravity PDF» sobre `.pdf`, y submenú «Antigravity PDF» sobre imágenes (mismo conjunto que `IMAGE_EXTS` de `window_document.py`) con «Convertir a un PDF» / «Convertir a varios PDF (uno por imagen)». Todas las entradas con `MultiSelectModel=Player`: Windows invoca el comando **una sola vez** con todos los archivos seleccionados como argumentos (no un proceso por archivo), lo que evita abrir tantas ventanas de la aplicación como archivos elegidos. El comando llama a `run.ps1` (ya sabe encontrar o crear el entorno virtual; se le añadió `-ArgumentosApp` con `ValueFromRemainingArguments` para reenviar lo que no sea uno de sus `switch` propios directamente a `main.py`). **Decisión de diseño clave**: nada de esto escribe archivos por su cuenta — se apoya en el mismo patrón ya usado por «Nuevo PDF en blanco»/«Crear PDF desde imágenes» (documento en memoria, sin guardar, en pestaña nueva) en vez de escribir directamente al lado del archivo original, así ninguna operación es sorprendente ni irreversible y no hace falta preguntar dónde guardar antes de saber si el resultado es el que se quería. **Verificación del registro sin tocar el menú contextual real**: el script acepta `-Raiz` (por defecto la ruta real) para poder instalar/comprobar/desinstalar contra una rama de prueba de `HKEY_CURRENT_USER` inventada; se instaló ahí de verdad, se leyeron con `Get-ItemProperty` los valores exactos de cada clave (`MultiSelectModel=Player`, `subcommands=""`, `MUIVerb`, y la línea de comando completa con la ruta real de `powershell.exe` y de `run.ps1`), se comprobó que las 8 extensiones de imagen quedan cubiertas, se desinstaló con `-Quitar` y se comprobó que no queda nada — sin escribir nunca en el menú contextual real del equipo (pendiente de que Ricardo confirme antes de ejecutarlo ahí, ver §7.0/cabecera). **Pruebas**: `TestConversion.test_combinar_varios_pdf_en_uno` / `.test_combinar_pdf_protegido_da_error_claro` (núcleo, sin Qt); en la interfaz, `test_combinar_pdf_desde_menu_contextual`, `test_combinar_pdf_con_un_solo_archivo_avisa_y_no_hace_nada`, `test_convertir_imagenes_a_un_solo_pdf_desde_menu_contextual`, `test_convertir_imagenes_a_varios_pdf_desde_menu_contextual` y los cuatro casos de `main.procesar_argumentos` (los tres indicadores más el «abrir con» normal sin indicador) → **142/142 OK** (132 + 10 pruebas nuevas). **Comprobado visualmente** con una ventana real offscreen (`QWidget.grab()`): PDF combinado de 2 archivos → 5 páginas en orden (A luego B), barra de estado «PDF combinado a partir de 2 archivos — sin guardar»; combinar con 1 solo archivo no cambia nada y muestra el aviso (interceptado en el guion, que si no se queda colgado esperando un clic que nunca llega bajo `offscreen` — fallo del propio guion de comprobación, no de la app, igual que `tests/test_interfaz.py` ya simula `QMessageBox` por el mismo motivo); imágenes a un PDF → 1 pestaña con 3 páginas; imágenes a varios PDF → 3 pestañas nuevas de 1 página cada una, con las 5 pestañas visibles a la vez en el rail izquierdo; los cuatro casos de `procesar_argumentos` reproducidos con una `MainWindow` nueva cada uno, tal como los lanzaría de verdad el menú contextual. Propagado a `docs/herramientas_profesionales.md` (tabla de funciones, sección nueva, plan de pruebas manual punto 21). |
| r54 | 2026-09-22 | **«Editar contenido» pierde su menú propio: pasa a Herramientas** (petición de Ricardo: «que desaparezca como un menú directo»). `_build_menus()` (`window_menus.py`) tenía `mb.addMenu("&Editar contenido")` con una sola acción («Editar texto e imágenes del PDF», tecla **C**) entre Comentar y Organizar; se quitó ese menú y la acción se movió a la cabeza de `&Herramientas` (antes de Marca de agua/Bates/OCR/Comprimir, con un separador detrás), sin tocar el atajo ni el método (`self._select_tool("EDIT")`). La barra de menús pasa de 10 a **9 menús**: Archivo · Edición · Ver · Comentar · Organizar · Herramientas · Proteger · Firmar · Ayuda. Prueba nueva `test_editar_contenido_vive_en_herramientas_sin_menu_propio` (comprueba la lista exacta de menús de la barra y que la acción es la primera de Herramientas) → 132/132 OK. **Comprobado**: `w.menuBar().actions()` y el contenido real del menú Herramientas ya desplegado (`QMenu.popup()`), además de una revisión completa de toda la documentación y la propia memoria en busca de menciones a la ruta de menú antigua (solo hacía falta corregir una en MEMORIA_EVOLUTIVA.md; el resto de menciones a «Editar contenido» en los docs son del nombre de la herramienta, no de su menú, y se dejaron como estaban). De paso, corregida una frase de la propia memoria que se quedó desactualizada en r49 (la letra «X» de Redactar seguía listada entre los atajos de una sola letra). Propagado a `docs/interfaz_grafica.md`. |
| r53 | 2026-09-22 | **Campo del número de página: máximo 4 dígitos, alineado a la derecha** (petición de Ricardo). `main_window._page_edit` pasa de `setAlignment(AlignCenter)` sin límite a `setMaxLength(4)` + `setAlignment(AlignRight | AlignVCenter)` — hasta 9999 páginas, más que suficiente (un valor mayor lo recortaría igual `go_to_page`, que ya acota al rango real del documento). Comprobado que `setMaxLength` trunca tanto al escribir con teclas reales (`QTest.keyClicks`) como al asignar el texto por código (`setText`), así que un intento de escribir «123456» se queda en «1234». Prueba nueva `test_campo_de_pagina_maximo_4_digitos_alineado_a_la_derecha` → 131/131 OK. **Comprobado visualmente**: con la página 1 el campo muestra «1» pegado al borde derecho del cuadro, no centrado. Propagado a `docs/interfaz_grafica.md`. |
| r52 | 2026-09-22 | **Arrastre de miniaturas: solución híbrida** (petición de Ricardo: «que la funcionalidad sea la de toda la vida (pulsar, mover, soltar) pero que visualmente siga apoyándose en OLE para mostrar ese desplazamiento interactivo»). El arreglo de r51 había quitado `QDrag` del todo (mousePress/Move/Release a mano, sin ningún rastro visual más que el cursor de mano cerrada); Ricardo pidió recuperar el fantasma semitransparente y el cursor de «permitido/prohibido» que solo da un `QDrag.exec()` de verdad, sin volver a depender de `dropEvent` para el destino (que es justo lo que fallaba en r51). **Diseño**: `_run_drag` arranca `QDrag.exec()` en cuanto `mouseMoveEvent` detecta arrastre (con el recorte de la miniatura al 70 % de opacidad como fantasma, y `setHotSpot` para que se agarre por donde se pulsó); `dropEvent`/`dragEnterEvent`/`dragMoveEvent` solo sirven para que Windows pinte el cursor de «permitido» mientras se está encima de la cuadrícula — `dropEvent` se ignora a propósito. El destino real se calcula al volver de `exec()` (que **siempre** devuelve el control al soltar el botón, se acepte o no el drop, así que no hay riesgo de bloqueo) leyendo `QCursor.pos()` —la da el sistema operativo, no la cola de eventos de Qt, así que no hereda el problema de r51— y aplicando exactamente lo mismo que antes: `drop_row()` + `move_selection_to()`, solo si el punto cae dentro del `viewport`. **Lo que costó averiguar** (todo en la propia prueba, no en la app): comprobado a mano que bajo `offscreen`, `QDrag.exec()` **no cuelga** (vuelve enseguida con `IgnoreAction`, sin compositor real que negocie nada) — importante, porque si se hubiera bloqueado habría colgado toda la batería; y que `QTest.mousePress` **sí** mueve `QCursor.pos()` a la pulsación pero `QTest.mouseMove` **no** lo mueve a ningún sitio, así que la prueba tiene que fijar `QCursor.setPos()` ella misma **después** de `mousePress` (si no, lo pisa) y antes de `mouseMove` — el primer intento lo puso antes de `mousePress` y la reordenación nunca se disparaba porque `QCursor.pos()` seguía en la pulsación. Segundo tropiezo: con el panel a su ancho por defecto la 4.ª miniatura queda fuera del `viewport` visible (haría falta scroll) y `_run_drag` descarta a propósito un destino fuera de él, así que la prueba ensancha el panel primero (como ya hacía la de Operaciones de página). Prueba reescrita con estos dos ajustes, más un caso nuevo (soltar fuera de la cuadrícula no reordena nada) → 130/130 OK. **Comprobado visualmente** con capturas reales: la cuadrícula ensanchada en una sola fila, con la página que era la 1.ª trasladada de verdad al final tras el gesto. Propagado a `docs/edicion_pdf.md`. |
| r51 | 2026-09-22 | **El botón ancho/alto ya no queda marcado, y el arrastre de miniaturas para reordenar páginas por fin funciona con el ratón de verdad** (dos peticiones de Ricardo). **(1)** El botón «ancho/alto» (`_zoom_btns["type"]`) deja de ser `checkable`: con el icono ya diciendo qué va a pasar en el próximo clic (r48), quedar además resaltado como «seleccionado» era contradictorio. Se quitaron las cinco llamadas a `.setChecked()` sobre ese botón que ya no hacían nada (`_set_pages_mode`, `_toggle_compress_panel`, `_activate_tool` en `main_window.py`, `_set_custom_zoom` en `window_document.py`, y la que fijaba el estado en `_zoom_mode_changed`). **(2)** «Durante las operaciones con páginas el visor de miniaturas se vuelve interactivo… la página que se tiene pulsada se traslada a esta nueva posición»: **preguntado a Ricardo qué pasaba exactamente**, confirmó «no hace nada al soltar». La función ya existía desde r31 (`_ThumbList.dropEvent` sobre `dragDropMode=InternalMove`, `QDrag` nativo de Qt) y estaba cubierta por pruebas — pero esas pruebas llamaban a `move_selection_to` **directamente**, sin pasar por ningún gesto de ratón, así que nunca habían comprobado el camino real. Causa real: en Windows, `QDrag.exec()` negocia por OLE (`DoDragDrop`), que lee los mensajes del ratón **directamente del sistema operativo**, no de la cola de eventos de Qt; con el panel de miniaturas dentro del `QSplitter`/`QStackedWidget` anidado de la app, esa negociación no se completaba nunca y `dropEvent` no llegaba a dispararse (invariante 48, reescrita). **Solución**: quitar `QDrag` del todo. `_ThumbList` maneja `mousePressEvent`/`mouseMoveEvent`/`mouseReleaseEvent` a mano — guarda dónde se pulsó, decide que hay arrastre en cuanto se supera `QApplication.startDragDistance()` (cursor de mano cerrada; a partir de ahí deja de delegar en Qt) y al soltar calcula el hueco con `drop_row()` (sin tocar, ya estaba bien) y llama a `move_selection_to()`. `set_organizing()` ya no toca `dragDropMode`/`setDropIndicatorShown`: solo pone la bandera `organizing` que activan esos tres métodos. **Esto sí se puede probar en offscreen** (son eventos de ratón normales, no una negociación OLE): nueva `test_arrastrar_una_miniatura_la_traslada_de_verdad`, que reproduce el gesto con `QTest.mousePress/mouseMove/mouseRelease` sobre el *viewport* de la lista y comprueba que la página cambia de sitio de verdad (y que un clic sin apenas moverse no reordena nada, y que fuera de «Operaciones de página» el mismo gesto no hace nada) — el hueco de cobertura que dejó pasar el fallo original queda cerrado. `test_icono_ajustar_ancho_alto_muestra_la_accion_libre` ampliada con `assertFalse(btn.isChecked())` en cada paso. 130/130 OK. **Comprobado visualmente** con capturas reales (`QWidget.grab()`): el botón sin resaltar tras pulsarlo, y la miniatura 1 trasladada de verdad al final de la cuadrícula tras el arrastre. Propagado a `docs/edicion_pdf.md` y `docs/interfaz_grafica.md`. |
| r50 | 2026-09-22 | **Búsqueda dinámica y centrada, y el panel lateral vuelve a dejarse empujar por las opciones de herramienta** (petición de Ricardo, cuatro cambios). **(1) Botón de búsqueda que alterna**: la segunda pulsación del botón de la barra principal oculta la barra (`_toggle_find_bar`, `main_window.py`); Ctrl+F y el menú Edición › Buscar siguen abriendo/enfocando sin cerrar. **(2) Búsqueda dinámica**: ya no hace falta pulsar Intro. `_find_edit.textChanged` → `_on_find_text_changed` (`window_menus.py`/`window_document.py`) arranca `_find_live_timer` (`QTimer` de 250 ms, creado una vez en `_init_document_state`) que al disparar llama a `_find_step(0)` — la misma ruta que ya usaba Intro, así que el resto de la lógica (recalcular solo si el texto cambió, resaltar la primera coincidencia, contador) no se tocó; con el campo vacío se limpia todo (`_clear_find`, que ahora también para el temporizador) sin esperar. Intro/F3 se conservan para saltar a la siguiente coincidencia. **(3) La lupa desaparece; en su sitio va el contador**, con **ancho fijo (96 px)** para que el resto de la barra no se desplace al crecer el número de coincidencias o pasar a «Sin resultados» (antes tenía ancho variable y, al estar la barra centrada entre dos `addStretch()` desde r48, cualquier cambio de ancho desplazaba también el botón de cerrar). **(4) El panel lateral vuelve a dejarse empujar por las opciones de herramienta**: revierte la superposición de r46 (`sidebar._ToolOverlay`, invariante 53, retirada) porque tapaba parte del panel (p. ej. la miniatura 1 quedaba oculta tras «Editar contenido») y Ricardo pidió lo contrario — que la herramienta seleccionada y lo que ya se veía en el panel estén **disponibles a la vez** (con scroll si hace falta) —; `tools` y `stack` vuelven al `QVBoxLayout` simple de r26. Las barras que sí se dejaron fuera de la columna del panel en r46 (aviso, búsqueda, `_opt_row`) siguen sin empujarlo: ese cambio no se ha tocado. **Pruebas**: `test_opciones_de_herramienta_en_el_panel_lateral` reescrita para comprobar el empuje (vuelta a la forma de r26, con el conjunto de herramientas de r49 sin Redactar); nueva `test_boton_de_busqueda_alterna_y_busqueda_dinamica` (alterna con clics reales, `QTest.keyClicks` sin Intro con `QTest.qWait(400)` para el retardo real, sin icono de lupa, ancho fijo del contador comprobado con la posición x del campo de texto antes y después de crecer el contador, y que vaciar el campo para el temporizador) → 129/129 OK. **Comprobado visualmente** con el guion offscreen habitual (`QWidget.grab()`): capturas de la barra sin lupa con el contador «1 de 4» tras escribir sin pulsar Intro, del segundo clic cerrando la barra, y del panel de miniaturas con la página 1 visible (empujada, no tapada) bajo el panel «Editar contenido». Propagado a `docs/interfaz_grafica.md`. |
| r49 | 2026-09-22 | **Eliminada del todo la herramienta «Redactar»** (petición de Ricardo: «eliminar el botón y función "redactar" así como todas las referencias a dicha función»). Se quitó de raíz, no se ocultó: botón de la barra superior y modo `REDACT` del visor (dibujar rectángulo → `add_redaction`), panel «Redacción» de `_opt_row` (marcar texto / aplicar), el botón a juego de la barra de búsqueda (`redact_find_results`), el menú Proteger › «Redactar área» / «Marcar texto para redactar…» / «Aplicar redacciones…», el atajo **X**, el menú contextual «Marcar para redactar» sobre texto seleccionado, y `doc_tools.mark_text_for_redaction` / `count_redactions` / `apply_redactions`. Con ello cayeron `main_window._redact_panel` y sus entradas en `_show_only_tool_panel`/cursores/pistas de la barra de estado/`_refresh_opt_row`, `window_document.add_redaction` y `.redact_find_results`, `window_menus.mark_text_for_redaction` y `.apply_redactions`, el icono `redact` (`eye_off`) de `icons.ICONS`, la letra «X» del atajo en `dialogs.SHORTCUTS`, y la entrada «Redact» del diccionario de etiquetas de `doc_tools.annotation_summary` (un PDF con esa anotación de otra herramienta ahora se etiqueta con su nombre en inglés, sin caer). **Lo que NO se tocó, a propósito**: `pdf_edit.py` usa la redacción de MuPDF como *técnica interna* para borrar texto e imágenes al editar contenido (`_erase`, `_stash_redactions`/`_restore_redactions`, invariante 31) — es un mecanismo distinto que sigue haciendo falta para «Editar contenido» aunque no exista ya la herramienta del usuario; solo se reescribieron los comentarios que citaban la ruta de menú retirada («Proteger › Redactar área» → «marcas que ya trajera el PDF, de otra aplicación»). Tampoco se tocó `pdf_compression.doc.scrub(redactions=False, …)`, un parámetro de la propia API de MuPDF sin relación. **Pruebas**: borrada `test_redaccion_elimina_el_texto` (la única dedicada a la API pública retirada); en `test_recorrido_completo` se quitaron `add_redaction`/`count_redactions`/`apply_redactions` y se ajustaron los recuentos que dependían de esa anotación (comentarios: 3 → 2; tipos de anotación: sin `"Redact"`); en `test_operaciones_de_pagina_en_el_panel_lateral` y `test_opciones_de_herramienta_en_el_panel_lateral` se sustituyó `REDACT` por `SIGN` (la única herramienta que queda en `_opt_row`) para conservar lo que de verdad probaban. Las pruebas que fabrican un PDF con una anotación `/Redact` **ya puesta, como si viniera de otra aplicación** (`pdf_editable()`, invariante 31) se dejaron intactas: siguen comprobando el mecanismo interno. 128/128 OK (129 − 1 prueba retirada). **Comprobado visualmente** con el guion offscreen de r46-r48 (`QWidget.grab()`): sin botón Redactar en la barra, sin su panel, con Firma como única opción de `_opt_row`, y sin el botón a juego en la barra de búsqueda. Propagado a `docs/edicion_pdf.md`, `docs/herramientas_profesionales.md` (tabla de funciones, decisiones de diseño, ambas listas de pruebas automáticas, y el plan manual renumerado del 11 al 20) y `docs/indice.md`. |
| r48 | 2026-09-22 | **Dos peticiones sueltas de Ricardo sobre la barra superior y la de búsqueda.** (1) «el botón de ajustar entre ancho y alto alternativamente también debe cambiar su icono según el estado que pueda ejecutar»: el botón `_zoom_btns["type"]` llevaba siempre el mismo glifo (`auto_fit_width`); ahora `_update_zoom_type_icon()` (`main_window.py`) elige entre `icons.glyph("type")` (ancho) y el nuevo `icons.glyph("type_height")` (`auto_fit_height`, añadido a `icons.ICONS`) según cuál sea la acción que el clic va a ejecutar — la contraria a `zoom_mode`, con la misma condición que ya usaba `_toggle_type_zoom` para decidir a qué modo saltar. Se llama al construir el botón y tras cada cambio de modo (`_zoom_mode_changed`, `_set_custom_zoom`). (2) «la barra de búsqueda debe hacer que las herramientas de dicha barra se queden centradas… no ponerlas en un lateral»: `_build_find_bar()` (`window_menus.py`) tenía un `addStretch()` a mitad de camino (entre el contador de resultados y los botones de redactar/cerrar), así que el grupo de la izquierda quedaba pegado al borde izquierdo y el de la derecha al derecho; ahora es un solo grupo con `addStretch()` a los dos lados, el mismo recurso que ya centraba `_opt_row`. Prueba nueva `test_icono_ajustar_ancho_alto_muestra_la_accion_libre` (zoom 100 → icono ancho; ajustar ancho → icono alto; ajustar alto → icono ancho; clic real sobre el botón; volver a un zoom numérico) → 129/129 OK. **Comprobado visualmente** con el mismo guion de r46/r47 (ventana real offscreen + `QWidget.grab()`): el icono cambia de verdad entre el glifo de doble flecha horizontal y el de doble flecha vertical al alternar, y la barra de búsqueda aparece como un solo bloque centrado en el visor, ya no pegada al borde. Propagado a `docs/interfaz_grafica.md`. |
| r47 | 2026-09-22 | **La barra de búsqueda tampoco empuja ya el panel lateral** (aviso de Ricardo tras revisar r46: «la barra del buscador sigue desplazando el panel lateral y he especificado que ninguna barra puede desplazar el panel lateral izquierdo hacia abajo»). Se me había escapado en r46: excluí la barra de búsqueda por no encajar literalmente en «de herramientas o de notificación», un criterio demasiado estrecho — la regla es **ninguna barra**, sin excepción. `_build_find_bar()` pasa de `root` (por encima de todo, panel lateral incluido) a `right_lay` (la columna del visor, junto al aviso y `_opt_row`): ya no queda ninguna barra por encima del `QSplitter` que reparte panel lateral y visor, solo la barra superior fija. Prueba `test_opciones_de_herramienta_en_el_panel_lateral` ampliada con el mismo bloque que ya tenía el aviso, para la búsqueda. **Comprobado visualmente de verdad** (no solo con la suite): ventana real renderizada offscreen con `QWidget.grab()`, con el estilo completo de `main.py`, herramientas alternadas una a una, aviso mostrado con `Formulario.pdf` (resultó estar firmado: «Este documento está firmado digitalmente») y `Notificacion.PDF`, y ahora la barra de búsqueda — capturas guardadas y leídas, más las coordenadas exactas en cada paso (techo del panel siempre en el mismo píxel). **Lo que costó averiguar** (del propio guion de comprobación, no de la app): la primera medida «antes» de mostrar la búsqueda leyó `114` en vez de `80` porque Qt no recalcula el layout hasta el siguiente `processEvents()` — sin llamarlo antes de tomar la base, la comparación arrastraba el alto del aviso del documento anterior; con `processEvents()` antes de medir, la diferencia coincidió exactamente con `find_bar.height()` (42 px). 128/128 OK (misma cuenta: se amplió una prueba existente). Propagado a `docs/interfaz_grafica.md`. |
| r46 | 2026-09-22 | **Ninguna barra secundaria empuja ya el panel lateral hacia abajo** (petición de Ricardo: «haz que todas las barras secundarias de herramientas o de notificación jamás desplacen hacia abajo el panel lateral izquierdo»). Hasta ahora había dos focos, ambos documentados como intencionados en su momento (r26): (1) las opciones de herramienta (Zoom, Texto, Nota, Marcar, Marcador, Rectángulo, Emoji, Editar contenido) iban **arriba** de las miniaturas/marcadores/comentarios/firmas en el mismo `QVBoxLayout` de `SidePanel.column`, así que al elegir una herramienta el panel se desplazaba (su comentario decía literalmente «empujan el panel hacia abajo»); (2) el aviso superior (documento firmado/con formulario/cifrado, `#doc_banner`) iba en `root`, por encima de **todo** —panel lateral y visor—, así que su aparición también movía el panel. **(1)**: nuevo `sidebar._ToolOverlay` (invariante 53): dentro de la columna, `stack` ocupa siempre el hueco completo con `setGeometry()`, y `tools` se dibuja **encima**, a su alto natural, sin alterar la posición ni el scroll de `stack`; un `QVBoxLayout` no sirve porque reserva espacio para cada hijo, así que la colocación es manual (`_reflow()`, disparado por `Show`/`Hide`/`LayoutRequest` de `tools`). **(2)**: `_build_banner()` pasa de `root` a `right_lay` (la columna del visor), igual que ya estaban Redactar/Firma/Comprimir desde r26: ahora solo empuja el visor. Prueba `test_opciones_de_herramienta_en_el_panel_lateral` (r26) reescrita: en vez de comprobar que las opciones quedan por encima del panel (el empujón), comprueba que el techo de `stack` **no cambia** al activar o quitar cada herramienta, y añadido un bloque para el aviso (misma comprobación que ya existía para Redactar/Firma: el panel lateral no se mueve, el visor baja el alto del aviso) → 128/128 OK (misma cuenta: se reescribió una prueba existente, no se añadieron). Propagado a `docs/interfaz_grafica.md`. |
| r45 | 2026-09-22 | **Un sello de tiempo de documento ya no sale como firma no válida** (Ricardo: «cuando tiene más de una firma de certificado parece que no verifica el segundo certificado», con `Factura Honorarios.pdf` como ejemplo). **Diagnóstico**: la «Firma2» era en realidad un campo `/DocTimeStamp` (sello de tiempo de documento de los Registradores, sin firmante, añadido tras la firma de contenido) y `signature_validation.validate_signatures` llamaba siempre a `pyhanko.sign.validation.validate_pdf_signature`, que exige `/Sig` y lanza «Signature object type must be /Sig» con cualquier otro tipo; el error se guardaba en el informe como «No se pudo validar», aunque el sello fuera correcto. **Arreglo**: se mira `emb.sig_object_type` y se llama a `validate_pdf_timestamp` para `/DocTimeStamp` (invariante 52); `SignatureReport.is_timestamp` distingue el caso para el texto del veredicto (`_VERDICT_TEXT`, «Sello de tiempo válido y de confianza») y qué campos rellenar (`timestamp` con la fecha del sello, `signed_at` vacío: un sello no declara una fecha aparte de la suya). `sidebar.py` muestra «Autoridad de sellado» en vez de «Firmante» para esas entradas; `inspect_signature.py` rotula «Informe de sello de tiempo». Comprobado con `Factura Honorarios.pdf`: las dos entradas pasan a `ok` (antes la segunda era `error`). Prueba nueva de núcleo que reproduce el caso de verdad: firma con `PAdESSigner` y luego sella con `pyhanko.sign.signers.pdf_signer.PdfTimeStamper` + `DummyTimeStamper` (con la clave del PFX de pruebas cargada vía `SimpleSigner.load_pkcs12`, en formato `asn1crypto` que exige `DummyTimeStamper`), comprueba que las dos entradas validan sin error y que la de tipo sello lleva `is_timestamp=True` con `timestamp` relleno y `signed_at` vacío → 128/128 OK. Propagado a `docs/firma_digital.md`. |
| r44 | 2026-09-22 | **La lista de confianza de España ya no se fía solo del HTTPS: se comprueba la firma XAdES de verdad** (Ricardo, tras revisar r43, pidió expresamente implementar el punto pendiente «sin verificar la firma XAdES de la TSL»). **Investigación** (sin acceso de navegador, con `WebSearch`/`WebFetch`): EUR-Lex es una aplicación JavaScript que no se pudo leer con las herramientas disponibles, así que no hay forma de copiar la tabla de huellas tal como la imprime el Diario Oficial. Se encontró en su lugar el `keystore.p12` del proyecto **DSS** (`esig/dss-demonstrations` en GitHub), la implementación de referencia de la Comisión Europea para eIDAS, con la que funciona su propio validador oficial; se contrastó que la URL del Diario Oficial que ese DSS tiene configurada (`current.oj.url`) coincide **exactamente** con el `SchemeInformationURI` que la LOTL en vivo declara como su propia publicación — no es la misma fuente primaria, pero es un cruce independiente razonable, documentado como tal (ni más ni menos) en la cabecera de `vendor/trust/oj_signers.pem`. **Verificado de extremo a extremo con `signxml`** (nueva dependencia, solo para generar): la firma de la LOTL descargada hoy valida contra el certificado `EUROPEAN COMMISSION <digit-dmo@ec.europa.eu>` de ese almacén, y la firma de la TSL de España valida contra el certificado `SPANISH TRUST SCHEME OPERATOR` que la propia LOTL —ya de confianza en ese punto— declara para España (no el que trajera el archivo descargado). `create_trust_list.py` reescrito: `verificar_firma` (`expect_references=2`, la forma normal de una firma XAdES-BES: documento + `SignedProperties`; con menos referencias de las debidas, no vale aunque el certificado sea el correcto), `puntero_es` (toma del puntero de España tanto la URL como el certificado declarado, y solo el puntero de tipo XML, no el PDF), y `FirmaNoValida` aborta sin escribir nada si algún nivel no cuadra. `--reanclar` deja los certificados de la Comisión en un `.nuevo` aparte para revisar a mano: es un almacén de raíces y no debe regenerarse solo. **Lo que costó averiguar**: `signxml.XMLSigner.sign(cert=…)` exige una **lista**, no un certificado suelto (`'Certificate' object is not iterable`); y mi primer intento de verificar la LOTL fallaba con «Expected to find 1 references, but found 2» — esperable en XAdES, no un fallo de la firma; hubo que pasar `expect_config=SignatureConfiguration(expect_references=2)`. 5 pruebas nuevas sin red (`TestFirmaXml`: firma válida, documento manipulado, certificado ajeno, número de referencias exigido, y que el puntero a España toma solo el de tipo XML) más el arreglo de una prueba de r43 que solo leía las 3 primeras líneas del PEM (dejó de bastar al añadir una línea a la cabecera) → 127/127 OK. `signxml` **no** entra en `requirements.txt` (la app no lo necesita para validar firmas de PDF; solo hace falta para generar `vendor/trust/`, igual que Edge/Chrome para el fondo del sello, r33). Propagado a `docs/firma_digital.md`. |
| r43 | 2026-09-21 | **Las firmas de las administraciones públicas y demás entidades cualificadas salen «verificadas»** (petición de Ricardo: «que los certificados de las administraciones públicas también aparezcan en los PDF que están firmados como verificados correctamente»). **Diagnóstico** con `Notificacion.PDF`: la cadena era firmante → «AC Interna» → «Raíz de los Registradores» (autofirmada, dentro del PDF) y Windows tenía 0 certificados de Registradores, así que salía «identidad no verificada» aunque Adobe la diera por buena (usa la lista europea, no Windows). **Se revisó primero el trabajo en curso** (otra sesión había dejado `Install-TrustedRoots.ps1`, sin memoria) y **no servía**: apuntaba a FNMT y ACCV, que Windows ya tiene (7 y 1), las 4 URLs dan 404, mandaba casi todo al almacén CA por comparar «ROOT» en español, no comprobaba huellas e instalaba raíces para todo el sistema. **Solución**: la TSL oficial de España (LOTL → `tsl.digital.gob.es/TSL.xml`) empaquetada en `vendor/trust/es_tsl.pem` (202 certificados, emisión nº 188) con `create_trust_list.py`, y `signature_validation._bundled_trust_anchors` la suma a las raíces de Windows; sin instalar nada ni pedir administrador. Contraste independiente: la «AC Interna» del PDF es **idéntica byte a byte** a la de la TSL (SHA-256 `f67a0c98…`); la raíz autofirmada del PDF **no** se usa como ancla. `Notificacion.PDF`: `untrusted` → **`ok`** (cobertura total, sin cambios posteriores). **Lo que costó averiguar**: (1) la TSL lista como ancla la CA que emite (intermedia), no la raíz; (2) el sufijo de tipo `QC` también lo llevan los servicios OCSP (`Certstatus/OCSP/QC`): hay que comparar `CA/QC` y `TSA/QTST` enteros; (3) **mi primer filtro excluía «AC Sector Público G2» de la FNMT**, la de las administraciones, porque solo declara `QCQSCDManagedOnBehalf` y yo exigía `QCForESig`; sin propósito declarado el uso por defecto es firma, así que solo se excluye lo declarado expresamente para web (`QCForWSA`) sin firma ni sello. Lo cazó una prueba que buscaba ese CN. **Límites**: no se verifica la firma XAdES de la TSL; solo cuenta el estado actual del servicio; la lista caduca el 2027-02-02 (regenerar; una prueba falla a propósito al pasar la fecha). `inspect_signature.py` reescrito: fallaba con su propio PDF de ejemplo (`PdfStrictReadError`, abría en modo estricto); ahora usa `_open_reader` y enseña la cadena y el ancla. 4 pruebas nuevas (ancla → `ok`, selección de la TSL con FNMT/web/OCSP/caducados, lista incluida cargada y vigente, `Notificacion.PDF` → `ok`) → 122/122 OK. `Install-TrustedRoots.ps1` borrado en r44 (el primer intento lo denegó el sistema; a la petición expresa de Ricardo sí se pudo). Propagado a `docs/firma_digital.md`. |
| r42 | 2026-09-18 | **La paleta pasa a ser la de Ricardo y se limpia la carpeta** (petición: «cambiar los colores por los que aparecen en `colores.html` y borrar luego todo lo que no se use»). `color_picker.PALETTE` deja los 26 colores CSS de r41 y toma los **17** de la «Paleta Cromática de Transición de Luces», en su mismo orden: `#FFFFFF #AAAAAA #000000 #AA0000 #FF0000 #FFAA00 #FFFF00 #FFFFAA #AAFF00 #00FF00 #00FFAA #AAFFFF #00AAFF #0000FF #AA00FF #FF00FF #FFAAFF`. `COLUMNS` pasa de 13 a **9** (dos filas de 9) y `_NOMBRES` guarda el nombre de cada color para la ayuda del recuadro; los recuadros siguen siendo de 16 px y el cuadro mide **200×109** (225×136 con opacidad). Ojo: en el HTML original `#FF00FF` y `#FFAAFF` se llamaban los dos «Magenta puro»; el segundo queda aquí como **«Magenta claro»** para no repetir. **Limpieza (−49,5 MB)**: borrados `Noto_Emoji/` y `Noto_Emoji.zip` (la fuente vive en `vendor/fonts/noto-emoji`), `Noto_Color_Emoji.zip` y `material-symbols-outlined.zip` (no se usan desde r40), `colores.html` (la paleta ya está en el código, que pasa a ser su única fuente de verdad), las capturas `error1-6.png` y `herramientas_corregir.png`, y los `__pycache__/`. **Se quedan** `Compartimentar.odt` y `PLAN_DE_IMPLEMENTACION.md` (documentos de Ricardo) y `Formulario.pdf` y `Notificacion.PDF` (sus PDF de prueba). `test_todos_los_colores_usan_la_misma_tabla` comprueba ahora la lista exacta, que todo color tenga nombre y que el recuadro no pase de 24 px → 118/118 OK. Propagado a `docs/interfaz_grafica.md`. |
| r41 | 2026-09-18 | **Un único selector de color, con transparencia donde toca** (petición de Ricardo, que dio los 26 colores en CSS: «que todos los selectores de colores muestren una misma tabla con grado de transparencia en caso de que la herramienta tenga transparencia… recuadros de no más de 24px, supongo que con 16px sería suficiente»). Nuevo `color_picker.py`: `PALETTE` (26 colores fijos), `ColorDialog` con la tabla en dos filas de 13 recuadros de **16 px** (comprobado: el cuadro mide 268×109, y 268×136 con opacidad) y, solo si la herramienta la admite, un control de opacidad en el mismo cuadro; `choose(parent, color, opacity, title)` devuelve (color, opacidad) o None. Sin opacidad, un clic en el color elige y cierra; con opacidad hay que aceptar. `nearest()` marca el color de la tabla más parecido al actual. Sustituye a `QColorDialog` en texto, nota, marcado, marcador, rectángulo, emoji, editar contenido y marca de agua. **Con transparencia**: marcado (nuevo `viewer.markup_opacity`, se aplica con `annot.set_opacity` al crear y al cambiar), marcador (ya tenía 0,45) y emoji (r40; su fila «Opacidad (%)» del panel desaparece: ahora va en la tabla, «Color y opacidad»). La marca de agua pierde su slider propio y usa el del selector. Prueba nueva `test_todos_los_colores_usan_la_misma_tabla` (26 recuadros de ≤24 px, qué herramientas piden opacidad y que el marcado se escribe con ella) → 118/118 OK. Propagado a `docs/`. |
| r40 | 2026-09-18 | **La fuente del documento no cambia, Noto como fuente base y emojis con Noto Emoji en color y transparencia** (petición de Ricardo: «la fuente de cada documento debe ser inmutable… la misma o la más parecida dentro del sistema», «las fuentes noto… que fueran las fuentes base del PDF y que sustituyera a la Arial así como en el número de cada miniatura», «que los emojis usen… NotoColorEmoji… se pueda elegir su color y transparencia», «que los iconos de los botones usen Fluent UI System Icons y quede indicado en la documentación y el código»). **Editar contenido**: `resolve_font` vuelve a escribir con la fuente del documento instalada en Windows (tabla `_FAMILIES` con los archivos de %WINDIR%\\Fonts) → si no está, la más parecida del sistema (`_PARECIDAS`) → y solo entonces la Noto de la app; `family_for` (antes `noto_family_for`) da la familia para el editor en pantalla y la barra dice cuál se usa. **Noto = fuente base**: marca de agua, encabezado, pie y Bates la incrustan (`doc_tools.BASE_FONT`, antes las base-14 de MuPDF); en la interfaz sustituye a Arial en el editor de campos y a Segoe UI en el número de las miniaturas. **Emojis**: elegido «solo Noto Emoji monocromo» (NotoColorEmoji dibuja mapas de bits: admite transparencia pero no color). Nuevo índice `vendor/emoji/emojis.json` (1391 emojis, `create_emoji_index.py` desde emoji-test.txt y CLDR) y fuente en `vendor/fonts/noto-emoji` (del Noto_Emoji.zip que ya estaba en la carpeta). `emoji_font` escribe el glifo con la fuente incrustada, con color y `/ca` de transparencia, y guarda ambos en `/Subj` («EmojiNoto|c#RRGGBB|a0.40», `parse_style`); panel con color y opacidad. Borrados el paquete Fluent Emoji (6,5 MB de SVG), `create_fluent_emoji.py` y la conversión con Chromium: **PyQt6-WebEngine deja de ser necesario** (XFA se fue en r38) y sale de `requirements.txt`. **Dos trampas**: Qt sustituía los emojis por Segoe UI Emoji en la cuadrícula (se corrige con `NoFontMerging`), y el selector, al pedir ancho, estaba tapando que el panel de opciones más ancho («Añadir texto», 286 px) no cabía en 240: `sidebar.COLUMN_MIN` pasa a 290 y el selector ya no impone ancho. **Iconos**: siguen siendo Fluent UI System Icons, ahora dicho en `icons.py`, en la hoja de estilo, en `docs/interfaz_grafica.md` y en `docs/arquitectura.md`. Pruebas de emojis y de fuentes reescritas → 117/117 OK. Revisado en capturas (panel, cuadrícula y PDF con emojis de colores, marca de agua y encabezado). |
| r39 | 2026-09-18 | **Al firmar en el recuadro del PDF se pide siempre el certificado** (petición de Ricardo: «primero debe aparecer un selector del certificado a utilizar… si no siempre firmará con el anteriormente seleccionado en la sesión anterior»). `sign_in_field` pasa `choose_cert=True` a `trigger_signature` / `_do_signature`, que abre `CertPickerDialog` con el guardado preseleccionado; cancelar no firma. Además el certificado se pregunta **antes** que el diálogo de opciones (motivo, lugar, sellado de tiempo), que es el orden que se ve. La herramienta Firma de la barra sigue igual: su panel enseña el certificado activo y tiene el icono de cambiarlo, así que no vuelve a preguntar. Prueba ampliada `test_clic_en_el_recuadro_de_firma_inicia_la_firma` (el selector recibe el certificado guardado, las opciones no se abren antes y cancelar deja el campo sin firmar) → 117/117 OK. Propagado a `docs/firma_digital.md`. |
| r38 | 2026-09-18 | **Fuera los formularios XFA y el recuadro de firma del formulario ya firma** (petición de Ricardo: «quita todo lo relacionado con los ficheros de formularios XFA» y «en Formulario.pdf el recuadro programado para firmar no activa la firma»). **XFA**: borrados `xfa_viewer.py` y `vendor/pdfjs` (296 archivos, 8,3 MB), `doc_tools.xfa_info`, el modo XFA de la ventana (`_xfa`, `_xfa_view`, `_xfa_actions`, `_apply_xfa_mode`, `_close_xfa_view`, `_dispose_xfa_views`, `_save_xfa_to`, `open_xfa_form`, Ctrl+Mayús+F), `sidebar.set_panels_enabled` y sus pruebas. **Qt WebEngine sigue siendo obligatorio**: ahora lo usan los emojis (r36), así que `requirements.txt` no cambia. El `QStackedWidget` central se queda por si vuelve a haber otra vista. **Firma en el campo del formulario**: `pdf_forms.field_boxes` **descartaba los campos de firma**, así que el recuadro «FIRMA» de `Formulario.pdf` no respondía al clic; ahora salen en la lista (`signed` dice si ya está firmado), `form_ui` los pulsa → `sign_in_field` → `trigger_signature(rect, field_name)` y `signer_backend.sign_pdf_bytes(field_name=…)` firma **dentro del campo existente** (`_empty_sig_field`, sin `new_field_spec`) en vez de crear otro. Comprobado con `Formulario.pdf`: queda un solo campo «FIRMA», el sello se dibuja en su recuadro y la firma cubre todo el documento. **Al quitar XFA me llevé por delante** los ayudantes `pdf_editable`, `PARRAFO` y `_fuente_windows` de las pruebas (el `.pyc` ya estaba regenerado): reconstruidos a partir de lo que exigen las pruebas (cuatro párrafos con Calibri, uno con estilos mezclados, la misma imagen dos veces, arte vectorial, resaltado, redacción pendiente y un campo de texto). 2 pruebas nuevas (núcleo y clic en la interfaz) y 3 borradas (XFA) → 117/117 OK. Propagado a `docs/`. |
| r37 | 2026-09-18 | **El panel Firmas ya valida los PDF con la tabla xref algo irregular** (informado por Ricardo con `Notificacion.PDF`, una notificación del Colegio de Registradores: «No se pudo validar: Xref table size mismatch: table allocated object with id 28, but according to the trailer 27 is the maximal allowed object id»). Causa: `PdfFileReader` en modo estricto **rechaza abrir** el archivo (su tabla xref declara un objeto más de los que anuncia el tráiler; los visores lo aceptan sin más) y eso pasaba antes de mirar ninguna firma, así que el error salía como si la firma fuese ilegible. Lo mismo impedía **firmar encima**. Ahora `signature_validation._open_reader` y `signer_backend` reabren en modo tolerante ante cualquier `PdfReadError`, con la misma regla que ya había para las xref híbridas (invariante 24); `_writer_for_hybrid_xrefs` pasa a llamarse `_tolerant_writer`. Las firmas se siguen comprobando igual de estrictas en lo criptográfico. Comprobado con el PDF de Ricardo: firma **íntegra, cubre todo el documento y sin cambios posteriores**; sale «identidad no verificada» porque la «Autoridad de Certificación Raíz de los Registradores» no está en el almacén de Windows de este equipo (comprobado en CurrentUser y LocalMachine), no por el archivo; Adobe la da por buena porque usa su propia lista de confianza (EUTL/AATL), no la de Windows. Firmar encima también funciona y conserva la firma previa. Prueba nueva `test_valida_y_firma_pdf_con_xref_irregular`, que fabrica el defecto bajando el `/Size` del tráiler → 118/118 OK. Propagado a `docs/firma_digital.md`. |
| r36 | 2026-09-17 | **Compresión legible, iconos Fluent UI System Icons, Fluent Emoji completo y fuentes Noto** (petición de Ricardo: «la compresión actual… difumina demasiado los textos… los caracteres deben quedar siempre bien legibles»; «para los iconos… solo… Fluent UI System Icons y para los emojis Fluent Emoji»; «la herramienta de emojis debe permitir seleccionar cualquier emoji»; «las fuentes editables… familia Noto… serif, sans y mono»). **Compresión**: medido con OCR sobre un escaneo de 6-12 pt: «Extrema» (75 ppp/JPEG 50) solo reconocía el 44-89 % del texto de 6-10 pt y «Recomendada» fallaba a 6 pt. `looks_like_text` (histograma: ≥50 % claro, algo de tinta, pocos medios tonos) y suelo `TEXT_MIN_PPI`=150 / `TEXT_MIN_JPEG_QUALITY`=75 para esas imágenes → 100 % en los tres niveles, en gris y color; fotos igual que antes; `Result.text_images` en el informe. **Iconos**: nuevo `icons.py` con `vendor/fonts/fluent-icons` (Regular, MIT): `ICONS` clave→nombre y `glyph()` lee los códigos del JSON (tamaño 20); sustituidos todos los `chr(0x…)` de Segoe; letra de 20 px en los botones. **Noto** (`vendor/fonts/noto`, OFL, 10 TTF): `pdf_edit.resolve_font` clasifica la fuente original en sans/serif/mono y escribe con Noto (antes la de Windows del mismo nombre); editor en pantalla con la misma (`noto_family_for`); herramienta Texto con Documento / Noto Sans / Serif / Sans Mono. **Trampa**: el texto enriquecido de MuPDF ignora `font-family` (siempre Charis SIL o Nimbus), así que `PDFUtils.apply_text_appearance` sustituye el `/AP /N` tras cada `update()` (crear, reeditar, mover, redimensionar) con la Noto incrustada (`insert_font`, CID = glifo, texto extraíble). Cada variante entera pesa ~350 KB: `doc_tools.bytes_with_subset_fonts` la recorta **en una copia** al guardar (384 → 26 KB; en el documento abierto dejaría sin letras al siguiente texto), salvo formularios y conservando el cifrado. **Emojis**: Fluent Emoji no existe como fuente; `create_fluent_emoji.py` baja los SVG Color (tono por defecto), los nombres en español de CLDR y el orden de Unicode → `vendor/fluent-emoji/fluent_emoji_svg.zip` (1595 SVG, 6.1 MB) + `emojis.json` (1595 con nombre en español). **Lo que costó averiguar**: MuPDF pinta negros los degradados; Qt SVG→QPdfWriter rasteriza y pone caras negras; Edge es fiel pero sus desenfoques se vuelven imágenes y todo convertido ocupaba 111 MB (58 MB a media pulgada; y guardarlo con `garbage` 3/4 no terminaba en 10 min, búsqueda de duplicados cuadrática). Solución: se guardan los SVG y cada emoji se convierte al insertarlo con el Chromium de **Qt WebEngine** (`printToPdf`, 0,1-0,8 s, idéntico a Edge), con caché en `%LOCALAPPDATA%`; la página web se destruye con `sip.delete`. En la cuadrícula, `setUniformItemSizes` + primer elemento sin icono = cuadrícula en blanco: icono transparente provisional y relleno al mostrarse. Fluent Emoji **no trae banderas de países**. `emoji_font` reescrito (Stamp `EmojiFluent`, caja cuadrada, `search`, `svg_bytes`, `emoji_pdf`; `EmojiFont` pasa a antiguo); nuevo `emoji_picker.EmojiPicker` (buscador sin tildes, grupos, miniaturas con QSvgRenderer). Borrados `create_emoji_palette.py`, `emoji_palette.pdf` y el código COLRv0 de Segoe. Pruebas: legibilidad por nivel, fuentes Noto, emojis Fluent con selector y paquete; adaptadas las de edición → 117/117 OK. Revisado en capturas (barra, panel de páginas, cuadros de texto Noto, selector). Propagado a `docs/`. |
| r35 | 2026-09-17 | **La capa de texto de OCR ocupa lo mínimo, y el OCR ya no multiplica el tamaño del PDF** (petición de Ricardo: que la compresión «comprima también este texto para que ocupe lo mínimo posible»). Medido antes de tocar nada con 6 páginas escaneadas (1,70 MB): tras el OCR el PDF pesaba **16,9 MB**, pero la capa de texto era solo ~10 KB; el resto era la **imagen a 400 ppp que Tesseract usa por dentro**: `_text_layer` quitaba el `Do` pero dejaba la imagen en `/Resources`, y `show_pdf_page` la copiaba. **Corregido en `pdf_ocr`** (`Resources/XObject` a null): tras el OCR, 1,72 MB. La compresión ya la quitaba (`clean=True` descarta recursos sin uso), así que los PDF viejos se arreglan comprimiéndolos. **Compresión**: `compact_ocr_text` redondea a 0,1 pt la posición **acumulada** de los `Td/TD` (son relativos) y el cuerpo a 0,01; `_ocr_forms` reconoce la capa por tener solo operadores de texto y todo el texto en `3 Tr`, no por el nombre GlyphLessFont (`subset_fonts` puede cambiarlo). **Trampa**: `clean=True` reescribe los números en coma flotante de precisión simple («45.700006») y deshacía el ahorro: con capa de OCR se guarda primero limpiando, se reabre, se compacta y se guarda otra vez sin `clean` (el intermedio conserva el cifrado; el final aplica el pedido). Resultado: capa de texto −23 % (10,3 → 8,0 KB en 6 páginas), mismo texto, cajas a ≤0,04 pt; cifrado conservado y nuevo comprobados. 2 pruebas nuevas (`test_el_ocr_no_guarda_una_copia_oculta_de_la_pagina`, `test_compacta_la_capa_de_texto_del_ocr`) → 116/116 OK. Propagado a `docs/`. |
| r34 | 2026-09-17 | **Copiar texto ya no parte las líneas** (Ricardo: «al copiar texto y llevarlo al bloc de notas, veo que rompe casi todas las líneas»; preguntó si cambiar Tesseract por PaddleOCR y, tras ver el coste, prefirió seguir con Tesseract si se podía arreglar programando). **Descartado PaddleOCR**: instalable en Python 3.13 (paddleocr 3.7, paddlepaddle 3.3.1 de 105 MB, ~50 paquetes, modelos aparte, más lento en CPU) pero choca con `pdf2docx` (`opencv-contrib-python` 4.10 frente a `opencv-python-headless` 5.0, los dos traen `cv2`), y el OCR actual ya no altera la página (capa invisible). **Causa**: `doc_tools.word_selection` ponía un salto por cada línea de MuPDF (bloque, línea): cada renglón de un párrafo acababa en salto y, en la capa de OCR de escaneos torcidos, una línea visual troceada daba saltos en mitad de la frase. **Ahora** (`_visual_lines` + `_lines_to_text`, invariante 49) las líneas se rehacen por geometría y los renglones de un párrafo se unen con espacio (quitando el guion de corte); hay salto si cabía la palabra siguiente, la línea siguiente es viñeta/número o está sangrada, cambia de columna, y línea en blanco si la separación es mayor de la normal. Los rectángulos de selección también son por línea visual. Comprobado con OCR real de escaneos simulados a 0°, 1,2° y 2,5° (5 renglones → 3 líneas: dos párrafos y el hueco); no se reprodujo el troceado con Tesseract aquí, así que se cubre con una prueba que lo fuerza. Los espacios que falten o sobren **dentro** de una palabra (p. ej. «capacidadlegal» a 2,5°) son del reconocimiento y no se tocan. 2 pruebas nuevas → 114/114 OK. Propagado a `docs/`. |
| r33 | 2026-09-17 | **Todos los complementos se instalan a la fuerza si faltan** (petición de Ricardo: «todos los complementos de esta aplicación deben forzarse su instalación si no están instalados en el equipo donde se instale o abra esta aplicación»). Inventario: Python, paquetes de `requirements.txt`, `pdf2docx` (era opcional), Tesseract y sus idiomas (ya forzados desde r16), pdf.js (va en `vendor/`), fuentes de iconos y Edge/Chrome. **Nuevo `dependencias.py`** (solo biblioteca estándar): compara `requirements.txt` con `importlib.metadata` (paquete y versión mínima) y lanza `pip install -r` si falta algo (con `ensurepip` si el intérprete no trae pip); se ejecuta en cada arranque desde `run.ps1` (~0,4 s si todo está) y lo primero de `main.py`, antes de importar PyQt6, por si la app se abre sin `run.ps1` (sin consola, avisa con `MessageBoxW`). `pdf2docx` pasa a `requirements.txt`; borrado `requirements-opcional.txt`. **`run.ps1`**: si no hay Python 3.13/3.12/3.11, lo instala para el usuario (winget `Python.Python.3.13` y, si falla, el instalador de python.org 3.13.13 con `/quiet InstallAllUsers=0`) y lo busca también en las rutas típicas (el PATH de la consola no se refresca); un entorno que no arranca se vuelve a crear; sustituida la huella `requirements.sha256` por `dependencias.py`. **No se fuerzan**: Edge/Chrome (solo para regenerar `signature_background.pdf`, no para usar la app) ni **Segoe Fluent Icons**, cuya licencia (EULA del zip de aka.ms/SegoeFluentIcons) no permite distribuirla ni usarla fuera de diseñar y probar; en Windows 10 se usa Segoe MDL2 Assets, y de los 53 glifos de la app solo faltaba E9A3 (indicador de Comprimir), cambiado a F012 (ZipFolder). Comprobado en este equipo: `dependencias.py` detectó `pdf2docx`, lo instaló y exportar a Word funciona; `.\run.ps1 -Pruebas` pasa por el nuevo recorrido. **No ejecutado de verdad**: instalar Python en un equipo sin él ni recrear un entorno roto. 3 pruebas nuevas `TestDependencias` → 112/112 OK. Propagado a `docs/`. |
| r32 | 2026-09-17 | **Al ensanchar un cuadro de texto, el texto ocupa el ancho nuevo** (informado por Ricardo: «aunque cambiemos el ancho de esas cajas, el texto interno sigue adaptándose al ancho anterior»). Causa: `pdf_edit._join_lines` solo convertía los saltos en espacios si el párrafo medía al menos el 60 % del bloque más ancho de la página; en cajas estrechas todos los saltos se leían como del autor y `wrap` los respetaba. Le pasaba también al texto que la app había reescrito en un cuadro estrecho. Ahora basta con que todas las líneas menos la última estén llenas, protegiendo las líneas que empiezan por viñeta o número (invariante 37). Tamaño y fuente no cambian. Reproducido antes de tocar nada con un párrafo estrecho junto a un título ancho (4 líneas → seguía en 4 al ensanchar; ahora 3, y tras estrechar a 5 vuelve a 3). Prueba nueva `test_ensanchar_un_cuadro_estrecho_reparte_al_ancho_nuevo` (incluye una lista numerada que conserva sus saltos) → 109/109 OK. Propagado a `docs/edicion_pdf.md`. |
| r31 | 2026-09-17 | **Miniaturas en cuadrícula y botones solo con icono** (petición de Ricardo: «si estiras ese panel hacia la derecha, dinámicamente se aproveche el espacio colocando las páginas en columnas… de izquierda a derecha y luego en filas» y «todas las operaciones con botones que puedas identificar con iconos de… Segoe Fluent Icons sean sustituidas por estos iconos»). **Miniaturas**: `sidebar._ThumbList` en `IconMode` con reparto por filas; soltar calcula el hueco (`drop_row`) y mueve la selección (`move_selection_to`), sustituye a `_rows_moved`/`_apply_order` (invariante 48). **Iconos** (glifos comprobados renderizando la fuente entera): Operaciones de página en una fila (girar izq. E777, der. E72C, duplicar E8C8, eliminar E74D, página en blanco E82E, otro PDF EA90, extraer F413); Marcadores (E710, E8AC, E74D); Comentarios, actualizar E72C; Firmas, validar todas E9D5 junto al título; Firma, cambiar certificado E8AB y olvidar E74D; Comprimir y guardar E792; Redactar, marcar texto E721 y aplicar E73E; búsqueda, marcar todo para redactar E8F8; aviso superior E928 / F0E3 / E7C3 según el caso; +/− de los selectores numéricos E710/E738. El texto pasa al tooltip. Estilo nuevo `side_icon_btn`; borrados `_opt_act_btn` y `opt_act`. Se dejan con letra **N/I** (negrita y cursiva, convención en español; la fuente solo trae «B») y los botones de los diálogos. Prueba de páginas ampliada (columnas, `drop_row`, mover hacia delante y atrás) y la del aviso XFA mira el tooltip → 108/108 OK. Revisado en capturas con fuentes reales (panel a 240 y 470 px, barras de Redactar y Firma, Marcadores y Firmas). Propagado a `docs/`. |
| r30 | 2026-09-17 | **Margen interno del texto del sello y logotipo a la derecha** (petición de Ricardo: «margen interno entre el texto y el recuadro de la firma de mínimo 7px y si es posible un 10% de la altura del recuadro, además el dibujo del fondo debe estar colocado en la parte derecha»). Nuevo `_SpanishCertTextStamp._text_area`: margen = máx(7 pt, 10 % del alto) en los cuatro lados; `_arrange_lines` y `_render_inner_content` trabajan sobre ese hueco. `_draw_background`: `tx = w − ancho·s` (antes centrado). Pruebas `test_sello_visual_fondo_mosca` (borde derecho = 200) y `test_texto_del_sello_con_el_ancho_del_recuadro` (texto de margen a margen) actualizadas → 108/108 OK. Revisado en PNG con recuadros 300×100, 120×200 y 400×40. Propagado a `docs/firma_digital.md`. |
| r29 | 2026-09-17 | **Recuadro de color detrás del logotipo del sello** (petición de Ricardo: «el fondo que ahora es transparente, tenga el color #d1ccbd pero con un 75% de transparencia y con esquinas redondeadas de 14 px»). `signer_backend._draw_panel` rellena el recuadro completo con #D1CCBD a opacidad 0,25 y radio 14 pt (= 14 px al 100 %); el logotipo se recorta con el mismo contorno. `test_sello_visual_fondo_mosca` comprueba color, `/ca` y radio → 108/108 OK. Revisado en PNG sobre página azul y blanca, con recuadro ancho (300×100) y estrecho (100×200): sobre blanco sale (243, 242, 238), lo esperado. Propagado a `docs/firma_digital.md`. |
| r28 | 2026-09-17 | **Fondo del sello regenerado con el `MOSCA.svg` mejorado** (petición de Ricardo). SVG nuevo exportado de Affinity, sin `<mask>` ni imágenes; `python create_signature_background.py` sin cambios de código → `signature_background.pdf` vectorial, sin imágenes (de 64 KB a 6,5 KB). Resuelve el aviso de §7.1 (r24): el fondo regenerado el 16-09 traía imágenes y hacía fallar `test_sin_imagenes_rasterizadas` → **108/108 OK**. Revisado firmando un PDF con fondo de color y renderizando a zoom 1 y 3: fondo transparente, logotipo centrado por el alto y sin línea de 1 px en el perímetro. |
| r27 | 2026-09-16 | **Adiós a la ventana «Organizar páginas»: operaciones de página en el panel lateral** (petición de Ricardo). Borrado `organize_dialog.py` (`_thumb_image`/`_labeled_icon` pasan a `sidebar.py`). El botón Operaciones de página es conmutable (`_set_pages_mode`): abre las miniaturas en modo organizar (arrastrar reordena con `move_pages`, Supr elimina) y encima el panel `_pages_panel` con recuento y siete acciones de una línea (girar izq./der., duplicar con `fullcopy_page`, eliminar, insertar en blanco, insertar otro PDF con `insert_pdf_after`, extraer). Todo va directo al documento con deshacer. Se sale con el botón, Esc, otra herramienta, zoom, compresión o cambiando de panel (`_on_sidebar_panel`); si el panel estaba cerrado se vuelve a cerrar. **Lo que costó averiguar:** `render_page` llama a `thumbs.set_current`, que con `setCurrentRow` dejaba seleccionada solo la página actual y la segunda acción se aplicaba a otra página; organizando se usa `setCurrentIndex(…, NoUpdate)` (invariante 47). Prueba nueva `test_operaciones_de_pagina_en_el_panel_lateral` (sustituye a la del organizador) → 107/108 (solo `test_sin_imagenes_rasterizadas`, §7.1). Propagado a `docs/`. |
| r26 | 2026-09-16 | **Opciones de herramienta en el panel lateral** (petición de Ricardo, con capturas `error1-6.png` y `herramientas_corregir.png`). Quitados los iconos indicadores (`opt_glyph`) de Texto, Nota, Resaltar, Marcador, Rectángulo y Emoji. Las opciones de Zoom, Texto, Nota, Resaltar, Marcador, Rectángulo, Emoji y Editar contenido pasan a `SidePanel.tools`, arriba del panel lateral, como filas «etiqueta explícita · control» de una línea (`_build_side_tool_panels`, `_side_form`, `_side_row`, `_side_hint`); la columna del panel (`SidePanel.column`) se abre también solo con opciones. Redactar, Firma y Comprimir siguen en `_opt_row`, que ahora está **dentro de la columna derecha del divisor, encima del visor**, así que no baja el panel lateral. Los textos variables de Editar contenido se partieron en líneas cortas con el detalle en el tooltip. Invariante 46. Prueba nueva `test_opciones_de_herramienta_en_el_panel_lateral` (posiciones reales y etiquetas sin cortar) → 107/108 (solo falla `test_sin_imagenes_rasterizadas`, §7.1). Revisado en capturas sin pantalla. Propagado a `docs/interfaz_grafica.md`. |
| r25 | 2026-09-16 | **El texto del sello mide lo mismo que el recuadro de la firma** (petición de Ricardo: «el texto debe ajustarse al ancho del recuadro de la firma mientras que el fondo… al alto»). Antes `_compute_font_size` estimaba un cuerpo entero entre 5 y 10 pt y pyHanko lo centraba solo encogiendo, así que en recuadros grandes el texto se quedaba pequeño. Ahora el texto se compone a 100 pt sin márgenes y se escala con `cm` al ancho exacto; en recuadros anchos y bajos se unen líneas con « · » y, si aun así no cabe en alto, se aplasta solo el alto (invariante 45). Fondo sin cambios (por el alto). Revisado en PNG con recuadros 120×200, 300×80 y 400×30. Prueba nueva `test_texto_del_sello_con_el_ancho_del_recuadro` → 106/107 (sigue fallando solo `test_sin_imagenes_rasterizadas`, §7.1). Propagado a `docs/firma_digital.md`. |
| r24 | 2026-09-16 | **Todos los tooltips con fondo amarillo crema** (petición de Ricardo: comprobarlo en cada herramienta, icono y botón). Comprobado mostrando de verdad el tooltip de los 58 destinos (botones, campos, listas de los combos, panel lateral y visor) y leyendo el píxel: 42 salían blancos (regla global `QToolTip`), 15 **transparentes** (paneles de la barra secundaria, por el `_TP` sin selector) y el visor **gris**. Nuevo `utils.TOOLTIP_QSS` (#FFF8DC, borde #E3D5A6) en la hoja global y en `_TP` y el viewport, ahora con `* { }` (invariante 44). Prueba nueva `test_tooltips_con_fondo_amarillo_crema` → 105/106: la única falla es `test_sin_imagenes_rasterizadas`, por el fondo de firma regenerado hoy fuera de esta revisión. |
| r23 | 2026-09-16 | **Escribir en el PDF ya no abre ninguna ventana** (petición de Ricardo: «que se realice directamente sobre la ventana de representación»). Nuevo `inplace_editor.InPlaceEditor`, compartido por la herramienta Texto, las notas, la edición de anotaciones y «Editar contenido», con las mismas teclas en todos los sitios (Intro línea, Ctrl+Intro confirma, Esc cancela, Tab siguiente). El cuadro sale donde se hace clic, con el tipo, tamaño, color y alineación que tendrá el texto, y **crece al escribir**; la barra secundaria lo restila en vivo (`restyle_text_editor`). Borrado `dialogs.TextInputDialog`. **Lo que costó averiguar:** el `QShortcut` de Esc de la ventana se queda la tecla antes que el editor, así que Esc **no cancelaba** nada (fallo que venía de r21 y que las pruebas no veían porque mandan la tecla directa al widget, invariante 41); el clic que confirma se tragaba mal el release y abría otro cuadro (invariante 42); y en `QPlainTextEdit` el alto de `documentSize()` viene en **líneas**, no en píxeles, por lo que el cuadro no crecía y además la caja del PDF se quedaba corta y **recortaba el texto** (invariante 43). Además, dos trampas del arnés que tumban el proceso sin traza: `QTest.keyClicks` con caracteres no ASCII y parchear `QDialog.exec` (§7.2). 7 pruebas nuevas de interfaz, una de ellas disparando el atajo de Esc de verdad → **105/105 OK**. Propagado a `docs/`. |
| r22 | 2026-09-16 | **El texto editado se reajusta al cuadro, y el cuadro se estira** (petición de Ricardo: «si tengo un texto demasiado largo, puedo coger el cuadro y estirar su esquina de manera que sea más alto y quepan más líneas»). La unidad de edición pasa de la **línea** al **párrafo**: `TextLine`/`text_lines`/`replace_text`/`line_at` → `TextBlock`/`text_blocks`/`replace_block`/`block_at`, con `wrap`, `needed_height` y `clamp_box`; el editor es un `QPlainTextEdit` sobre el cuadro y los tiradores de esquina lo estiran reajustando el texto (invariante 40: van fuera del cuadro y funcionan porque el visor no roba el foco). Indicador en vivo de líneas y de si cabe, marco rojo y recuadro hasta donde llega el texto cuando no cabe. **Lo que costó averiguar:** unir las líneas de un párrafo necesita **dos** señales —que llene la columna y que la palabra siguiente no cupiera—, porque solo con la segunda una lista corta se convertía en un churro; el alto hay que medirlo con el descendente del **propio párrafo**, porque con el de la fuente un párrafo de una línea avisaba siempre de que no cabía sin haber tocado nada; y las matrices de rotación hay que pedirlas **antes** de poner la rotación a 0, si no el cuadro llegaba sin convertir y con `/Rotate 90` el texto aterrizaba fuera (invariantes 37-39). El cuadro se acota a la página: arrastrando un tirador fuera de la hoja el texto se escribía donde no se ve ni se puede volver a seleccionar. Interlineado, alineación y primera línea base se conservan. 9 pruebas nuevas (7 de núcleo + 2 de interfaz que estiran el tirador de verdad) → **98/98 OK**. Propagado a `docs/edicion_pdf.md`, `interfaz_grafica.md` y el plan manual. |
| r21 | 2026-09-16 | **Edición del texto y las imágenes que ya están en el PDF** (petición de Ricardo; era la carencia más grande de §7.3 frente a Acrobat: hasta ahora la app solo sabía *añadir* cosas encima). Nuevos `pdf_edit.py` (sin Qt) y `edit_ui.py`, herramienta **C** con su botón, su menú y su panel en la barra secundaria. El texto viejo se quita por **redacción** conservando arte vectorial e imágenes, y se reescribe con `TextWriter` en la línea base original. **Lo que costó averiguar:** la fuente incrustada no sirve para escribir (los subconjuntos vienen sin `cmap`: todos los caracteres dan glifo 0 y el texto sale en blanco, invariante 32), `apply_redactions()` habría ejecutado de paso las redacciones pendientes del usuario (invariante 31), `replace_image`/`delete_image` cambian **todas** las copias de la imagen en el documento (invariante 33), `get_text` incluye la apariencia de los FreeText y de los campos —redactarlos no borra nada y duplica el texto— (invariante 34), `Annot.rect` no sigue la rotación de la página aunque `get_text` sí (invariante 35), y reescribir una línea cambia el orden de extracción, así que buscarla luego por su índice reescribía **otra** línea (invariante 36). Un PDF firmado declara ocho «imágenes» sin xref, del sello: descartadas. `is_shared` pasó a calcularse bajo demanda (recorría el documento entero en cada render: 89 ms → 18 ms con 400 páginas). Probado contra `Doc1/Doc2/*_firmado.pdf` y con páginas giradas 90/180/270. 23 pruebas nuevas (17 de núcleo + 5 de interfaz con ratón y teclado reales, + 1 de imágenes en línea) → **89/89 OK**. Propagado a `docs/edicion_pdf.md`. |
| r20 | 2026-09-15 | **Varios PDF abiertos a la vez, como pestañas en el panel lateral** (petición de Ricardo). Estado por documento en `window_document` (`_SESSION_ATTRS`, `_sessions`, `switch_document`, `_begin_new_session`, `close_document_at`, `next_document`; invariante 30). `sidebar.SidePanel.set_documents`: separador + botón por documento (glifo PDF, o Document si no está guardado; comprobados en Segoe Fluent Icons y MDL2), tooltip con nombre, ruta y «●», menú Cerrar; solo con 2 o más. Abrir, nuevo, desde imágenes y arrastrar abren pestaña nueva; archivo ya abierto → cambia de pestaña; cerrar pasa a la contigua; salir pregunta por cada documento con cambios. Ctrl+Tab / Ctrl+Mayús+Tab. Modo XFA: `sidebar.set_panels_enabled` en lugar de desactivar todo el panel (las pestañas siguen); `_dispose_xfa_views` al salir; `XfaView.shutdown` idempotente. Estilos `#rail_sep`, `#rail_doc`. Prueba nueva `test_varios_documentos_como_pestanas` → 66/66 OK. |
| r19 | 2026-09-15 | **Formulario XFA en la misma ventana** (petición de Ricardo, tras preguntar si convenía pasar todo el programa a pdf.js: se descartó porque pdf.js no edita, redacta, cifra, comprime ni hace OCR, es más lento y obligaría a reescribir la interfaz). `xfa_viewer.XfaWindow` → `XfaView` (widget, guardado síncrono, zoom). La zona central es un `QStackedWidget` (`_center`: `_scroll` o el formulario); modo XFA en `window_menus` con acciones y botones limitados (invariante 29g), guardar/guardar como/imprimir/zoom redirigidos, título y cierre con los cambios del formulario, botón del aviso y Herramientas › Ver formulario XFA (Ctrl+Mayús+F) que alternan. Quitados `_xfa_windows` y `_on_xfa_saved`. La prueba de extremo a extremo ahora también escribe con el **teclado real** («Tnh», atajos de herramientas) y vuelve a la vista normal → 65/65 OK. |
| r18 | 2026-09-15 | **Formularios XFA rellenables y arreglo del OCR en páginas enormes** (petición de Ricardo; eligió «Visor XFA integrado», ~126 MB de dependencias). **XFA**: nuevo `xfa_viewer.py` (pdf.js 6.3.289 legacy en `vendor/pdfjs` servido por HTTP local dentro de Qt WebEngine; guardado incremental que actualiza `datasets` y conserva el cifrado) + `doc_tools.xfa_info`. Se abre solo con XFA dinámico, desde el aviso (botón generalizado con `_banner_action`) o Herramientas › Abrir formulario XFA…; al guardar recarga el documento; al cerrar la app pregunta por los cambios del formulario. Probado con IMM5257 (5 páginas, 77 controles, AES) y otros XFA reales. `requirements.txt`: PyQt6-WebEngine; `main.py` importa QtWebEngineWidgets antes de la `QApplication` (invariante 29: legacy, MIME, argv no vacío, destrucción de la página). **OCR**: `FzErrorLimit: Overly large image` en páginas de escáner gigantes → `pdf_ocr.render_dpi` (invariante 27f). Pruebas nuevas: `TestOCRLimites` (2), `TestXfa` (2) y la de extremo a extremo del visor XFA (abre, rellena, guarda, recarga) → 65/65 OK. |
| r17 | 2026-09-15 | **OCR mucho más preciso, cursor de texto y formularios completos** (petición de Ricardo). **OCR**: el método anterior solo trataba páginas sin texto (las imágenes de páginas mixtas: 0 %) y las sustituía por imagen + texto. Nuevo `pdf_ocr.py`: capa invisible sobre la página original, texto existente tapado, contraste, 400 ppp, orientación con OSD (páginas giradas: del 4–12 % a completo) y modelos `tessdata_best` (`tesseract_setup` los descarga y marca; verificado en este equipo). Diálogo `dialogs.OcrDialog` (idioma, todas las páginas o solo sin texto, orientación), un paso de deshacer. Trampa: **MuPDF solo reconoce en RGB** (invariante 27). **Cursor**: «I» sobre texto seleccionable y campos de texto, mano sobre botones. **Formularios**: `pdf_forms.py` (JavaScript de MuPDF: cálculos, validación, botones, ResetForm; avisos capturados envolviendo el JS, invariante 28) y `form_ui.py` (resaltado, editor en línea con Tab, menú de listas, acciones). Quitados `viewer._widget_at` y `_fill_widget` (diálogos) y `doc_tools.ocr_page_into`. `UndoStack.discard_last`. 15 pruebas nuevas → 60/60 OK. |
| r16 | 2026-09-15 | **Tesseract OCR obligatorio** (petición de Ricardo). Antes era un requisito manual: instalarlo y crear `TESSDATA_PREFIX`. Nuevos `tesseract_setup.py` (sin Qt) y `tesseract_ui.py`. Se comprueba en `run.ps1` antes de arrancar y en `main.py` al iniciar. Si falta, **se instala a la fuerza**: `winget install UB-Mannheim.TesseractOCR --silent` y, si falla, el instalador oficial 5.4.0 con `/S` como administrador. Los idiomas spa, eng y osd se copian de la instalación o se descargan de tessdata a `%LOCALAPPDATA%\antigravity-pdf\tessdata`, y la app fija `TESSDATA_PREFIX`. Decisión de Ricardo: si la instalación falla, se avisa y la app abre con el OCR desactivado, reintentándolo en el siguiente inicio (invariante 26). «Reconocer texto» descarga el idioma elegido si falta. Pruebas simuladas (6 núcleo + 2 interfaz) → 45/45 OK. Detección comprobada en este equipo (no instalado); **la instalación real no se ha ejecutado aún** (requiere permiso de administrador en el escritorio de Ricardo). |
| r15 | 2026-09-15 | **Compresión tipo Adobe Acrobat + iLovePDF** (petición de Ricardo). Antes solo `garbage`/`deflate` con un control del 1 al 9, sin tocar imágenes. Nuevo `pdf_compression.py` con 3 niveles (baja 150 ppp/JPEG 85, recomendada 100/70, extrema 75/50): reducción de resolución «por encima de 1,5·X», recorte de fuentes, sin miniaturas, flujos de objetos y esfuerzo máximo. **Nunca por debajo de 75 ppp al imprimir en DIN A4** (por colocación y con el factor A4 de su página). Panel: combo de nivel con descripción. Informe con tamaños, %, imágenes y ppp mínimo; no guarda si no reduce; aviso si hay firmas. **Descartado `rewrite_images` de MuPDF** tras probarlo con PDF reales: perdía los `/Pattern` del sello de firma y de los emojis (invariante 25). Se sustituyó por un reescritor propio y una red de seguridad por avisos. **Corregido**: `get_image_info(xrefs=True)` lanzaba con el `/ColorSpace` roto de `Doc2.pdf`; ahora esas imágenes se reparan y comprimen. Resultados reales: `Doc2` 387→54 KB en extrema, firmados −18/−47 %, sin avisos nuevos. 10 pruebas nuevas → 37/37 OK. Propagado a `docs/edicion_pdf.md` e `interfaz_grafica.md`. |
| r14 | 2026-09-15 | **Emojis con el aspecto de Windows (degradados COLRv1)**, a petición de Ricardo: la chincheta de r13, plana, no se parecía a la de Windows. Qt `QPdfWriter` incrusta la TTF (fuera de Windows saldría monocroma); **Edge/Skia la exporta como Type 3 con degradados y máscaras, sin imágenes**. Nuevo `create_emoji_palette.py` → `emoji_palette.pdf` (una página por emoji, recortada a su caja). `emoji_font` copia esa página a la apariencia mediante una página auxiliar; fuera de la paleta sigue COLRv0. Caja = avance × (`usWinAscent` + `usWinDescent`), porque con el ascendente se cortaban los dibujos. `PALETTE` es la única lista, la usa también el combo. **Corregido de r13**: `_recreate_emoji_selection` usaba anotaciones de una página temporal (referencia débil: `ReferenceError` o acceso inválido en memoria). Pruebas: emojis (paleta + 🍍 + recrear) y `test_paleta_de_emojis_vectorial` → 27/27 OK. Revisado en PNG. |
| r13 | 2026-09-15 | **Emojis como fuente Segoe UI Emoji** (petición de Ricardo, `Doc2.pdf`). Antes: PNG renderizado con Qt dentro de un Stamp. Salían aplastados porque `annot.update()` fijaba el `/Rect` del Stamp a 3,8:1, y a veces MuPDF daba «invalid ICC colorspace» por referencias de color rotas entre imágenes. Ahora: nuevo `emoji_font.py`, una fuente Type 3 a color por emoji (capas COLRv0/CPAL de `seguiemj.ttf`, contornos con `QRawFont`, `ToUnicode`), sin imágenes. Caja con las métricas de la fuente al tamaño elegido. El visor mueve y redimensiona con `write_rect()` (sin `set_rect()`, invariante 3) y fija la proporción. Paleta: ★ → ⭐ (★ no existe en Segoe UI Emoji). Quitados `_render_emoji_png`, `_FONT_EMOJIS`, `add_image_stamp` y `add_emoji_stamp`. Nueva prueba `test_emojis_como_fuente_segoe_ui_emoji` → 26/26 OK; sin avisos de MuPDF y revisado en PNG. |
| r12 | 2026-09-15 | **Corregida la línea de 1 px alrededor de la mosca** (informada por Ricardo). Causa: Edge rasterizaba la `<mask>` del SVG como imagen de máscara suave y en su borde se colaba el rectángulo #94CFE1 enmascarado; se veía en el perímetro del lienzo a zoom de pantalla, no al ampliar. `create_signature_background.py` convierte ahora las máscaras de color sólido en `<clipPath>` + opacidad (luminancia); `signature_background.pdf` regenerado, ya sin imágenes. Diferencia con el fondo anterior: media 0,85/255, así que se ve igual salvo la línea. Nuevas pruebas `TestFondoFirma` (sin imágenes; perímetro blanco a zoom 0,25/0,5/1), que fallaban con el fondo antiguo → 25/25 OK. Revisado con MuPDF a zoom 1 y 1,5 ampliando píxeles. QtPdf/PDFium no pinta la apariencia de los campos de firma, así que no sirve para comprobarlo. Propagado a [docs/firma_digital.md](docs/firma_digital.md). |
| r11 | 2026-09-15 | **Primera línea del sello = solo nombre y apellidos** (petición de Ricardo, visto en un PDF firmado con certificado de representante FNMT, que mostraba `DNI NOMBRE APELLIDO1 (R: CIF)`). `extract_cert_info` usa el nuevo `_signer_display_name`: `givenName` + `surname`, o el CN sin DNI/NIE ni `(R: …)`/`- NIF …`. Comprobado con el certificado real extraído del PDF (sin clave privada): nombre completo con los dos apellidos. Nueva prueba `test_nombre_del_firmante_sin_identificadores` (datos ficticios) → 23/23 OK. Propagado a [docs/firma_digital.md](docs/firma_digital.md). El panel Firmas y el selector de certificados siguen mostrando el CN. |
| r10 | 2026-09-15 | **Corregido: firmar fallaba con «Attempting to sign document with hybrid cross-reference sections while hybrid xrefs are disabled»** (informado por Ricardo al firmar un PDF real sin cambios). No lo causó r9: pyHanko en modo estricto rechaza los PDF con xref híbridas. Sin firmas previas se normaliza con PyMuPDF; con firmas previas se firma en modo no estricto. Además `signature_validation` tampoco validaba esos archivos («Settings do not permit validation of signatures in hybrid-reference files»): ahora reabre en modo tolerante. Invariante 24. Nuevas pruebas `test_firma_pdf_con_xref_hibridas` y `…_y_firma_previa` con el generador `pdf_hibrido` → 22/22 OK. |
| r9 | 2026-09-15 | **Fondo del sello = logotipo `MOSCA.svg`** (petición de Ricardo). Retirados el recuadro #008EA1, las esquinas redondeadas y la huella de r8 (Ricardo eligió quitar también la huella); borrado `signature_fingerprint.py`. Nuevo `create_signature_background.py` → `signature_background.pdf` (SVG → PDF vectorial con Edge headless; MuPDF lo pintaba negro; amplía la región de las `<mask>` porque los navegadores las recortaban). `_draw_background` importa la página como XObject, escala por el alto del recuadro y centra. Prueba renombrada a `test_sello_visual_fondo_mosca` (escala 80 pt, centrado, sin recuadro de color); la `cm` pasa a 6 decimales porque con 4 el alto se desviaba 0,02 pt → 20/20 OK. Revisado en PNG con recuadro ancho y estrecho. Propagado a [docs/firma_digital.md](docs/firma_digital.md). |
| r8 | 2026-09-15 | **Nuevo aspecto del sello de firma** (petición de Ricardo): recuadro redondeado #008EA1 al 50 % (antes azul-verdoso con mezcla Screen al 70 %), huella dactilar blanca opaca centrada con el alto del recuadro −1 % por lado, y texto opaco. Nuevo módulo generado `signature_fingerprint.py` (contorno vectorial del glifo U+E928). Nueva prueba `test_sello_visual_fondo_y_huella` (color, `/ca 0.5`, sin Screen, huella blanca a 98 % del alto; salta los objetos xref libres que deja la firma incremental) → 20/20 OK. Revisado a ojo en PNG con un recuadro ancho y otro estrecho. Propagado a [docs/firma_digital.md](docs/firma_digital.md). |
| r7 | 2026-09-15 | **El botón «Operaciones de página» abre directamente el organizador** (petición de Ricardo): antes desplegaba en la barra secundaria un panel con 5 iconos. Eliminados `_pages_panel`, `_toggle_pages_panel`, los glifos `pg_*` y los métodos que solo usaba ese panel (`cut_page`, `add_blank_page`; el diálogo y el menú Organizar cubren lo mismo). Nuevo `_open_pages_dialog()`, que oculta la barra secundaria **antes** de abrir el diálogo. Nueva prueba `test_boton_paginas_abre_organizador_sin_barra_secundaria` → 19/19 OK. Propagado a [docs/edicion_pdf.md](docs/edicion_pdf.md). |
| r6 | 2026-09-15 | **Primera ejecución real.** El proyecto está ahora en `C:\Users\Aventya\Proyectos\ANTIGRAVITY-PDF` y ya se puede usar la consola. `run.ps1 -Pruebas`: 16/18 al principio; los 2 errores eran de las pruebas (`fitz.Rect.center` no existe en PyMuPDF 1.28, invariante 23) y se corrigieron en `tests/test_nucleo.py` y `tests/test_interfaz.py` → **18/18 OK**. El entorno registró `requirements.sha256`. Queda la prueba manual de la interfaz (§7.0). |
| r5 | 2026-09-15 | **Versión 2.0.1: endurecimiento sin ejecutar.** Revisión estática de los 15 módulos y verificación de APIs contra PyMuPDF 1.28 / pyHanko 0.36 / PyQt6 6.11 instalados (§7.0). **Corregido:** duplicar la última página lanzaba `ValueError` (`fullcopy_page(to=n)`, invariante 22); carrera al destruir `SignWorker` desde `succeeded`/`failed` (invariante 20); impresión deformada (no respetaba proporción) y con riesgo de agotar memoria a 1200 ppp; *Comprimir* perdía el cifrado, no sugería nombre ni añadía `.pdf`. **Nuevo:** `sys.excepthook` + `faulthandler` con `errores.log`/`fallos_graves.log` (invariante 21); `tests/` (núcleo + interfaz offscreen) y `run.ps1 -Pruebas`; `create_test_cert.build_test_pfx` con API moderna y `KeyUsage`. **Descartado tras verificar:** sospecha de que `status.trusted` no existía en pyHanko 0.36 (es propiedad). |
| r4 | 2026-09-14 | **Versión 2.0 «rival de Acrobat Pro»** (sin ejecutar, §7.0). Monolito dividido: `viewer.py`, `window_document.py`, `window_menus.py`, `sidebar.py`, `doc_tools.py`, `dialogs.py`, `history.py`, `signature_validation.py`. Nuevo: menús y atajos, panel lateral, búsqueda, selección/copia de texto, marcado de texto, notas, formularios, deshacer/rehacer, cambios sin guardar, recientes, arrastrar-soltar, contraseña al abrir, marca de agua, Bates, redacción, OCR, cifrado, propiedades, exportaciones, dividir/extraer/girar, firma con TSA/certificación en hilo, validación de firmas. **Resueltos de §7.1 r3**: `insert_pdf(to_page=…)` → `start_at`; mezcla de botones y arrastre en el organizador; `move_page(idx, idx+1)` que no movía; miniaturas `QImage` sin copiar; segunda firma fallaba por nombre de campo repetido; firmar y organizar sobrescribían el PDF original; `replace(".pdf", …)` rompía rutas con «.pdf» en carpetas; `copy_page` compartía la página. `qtawesome` fuera; PyMuPDF ≥1.24; `run.ps1` detecta cambios de requisitos. |
| r3 | 2026-07-30 | Añadido [run.ps1](run.ps1): entorno en `%LOCALAPPDATA%`, forma normal de ejecutar (§8). |
| r2 | 2026-07-30 | Carpeta compartida; `.venv/` del árbol inservible; entorno por equipo. |
| r1 | 2026-07-30 | Creación de la memoria evolutiva. Revisión completa de los 7 módulos, invariantes, flujos destructivos y deuda técnica. |
