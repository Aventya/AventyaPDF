# Plan de migración: AventyaPDF nativa de Windows 11 (WinUI 3 + XAML + C++/WinRT)

> Estado: **plan, sin empezar** (r63, 2026-09-23). Parte de la versión r62
> (Python + PyQt6, 13.600 líneas de código, 160 pruebas, 59 invariantes en
> `MEMORIA_EVOLUTIVA.md` §4). Objetivo: la misma aplicación, con **paridad
> funcional exacta**, escrita en C++20 con interfaz WinUI 3 (Windows App SDK) y
> XAML, usando C++/WinRT.

---

## 1. Principios

1. **Paridad antes que novedades.** Cada función y cada invariante de la memoria
   se migra tal cual; las mejoras van después, en otra fase.
2. **La app de Python es el oráculo.** Mientras dure la migración, la versión
   Python sigue siendo la de uso diario y sirve para generar resultados de
   referencia (PDF, textos, informes de firma) contra los que se compara la
   versión C++.
3. **Núcleo sin interfaz.** Toda la lógica de PDF, OCR y firma va en una
   biblioteca C++ sin dependencias de UI, probada por su cuenta. La app WinUI 3
   solo presenta y llama al núcleo (lo mismo que hoy separan `pdf_edit`,
   `pdf_ocr`, `signer_backend`… de las ventanas Qt).
4. **Mismos motores cuando se pueda.** MuPDF y Tesseract son C/C++: se usan
   directamente, así se conservan el comportamiento, los trucos y los
   resultados medidos (p. ej. el banco de OCR de r60).

## 2. Arquitectura destino

```
AventyaPDF.sln
├── Core/            biblioteca estática C++20, sin UI
│   ├── Documento    abrir desde bytes, guardar (completo / incremental), cifrado, deshacer
│   ├── Render       páginas y miniaturas a mapa de bits (MuPDF)
│   ├── Texto        extracción, búsqueda, selección por palabras, copiar
│   ├── Anotaciones  texto, notas, marcado, mano alzada, rectángulo, emoji, borrador
│   ├── Edición      editar texto e imágenes reales (port de pdf_edit)
│   ├── Formularios  campos, JavaScript (mujs de MuPDF)
│   ├── Páginas      girar, insertar, extraer, reordenar, combinar, dividir
│   ├── Herramientas marca de agua, encabezado/pie/Bates, compresión, exportar
│   ├── Ocr          libtesseract + enderezado + orientación verificada
│   └── Firma        firmar, sellar, validar, quitar la última (interfaz abstracta)
├── Plataforma/      lo específico de Windows, detrás de interfaces del núcleo
│   ├── CertStore    almacén MY, PFX, claves NO exportables (CNG / NCrypt)
│   ├── Cms          CMS/PAdES con CryptMsg, sellado de tiempo con CryptRetrieveTimeStamp
│   ├── Confianza    CertGetCertificateChain + anclas de la TSL de España
│   └── Credenciales Administrador de credenciales (CredWrite/CredRead)
├── App/             WinUI 3 + XAML + C++/WinRT (MVVM)
│   ├── MainWindow   barra de título propia, Mica, barra de herramientas
│   ├── Visor        control propio: tiles renderizados, zoom, selección, herramientas
│   ├── Panel        miniaturas (GridView reordenable), marcadores, comentarios, firmas
│   ├── Diálogos     ContentDialog: opciones de firma, seguridad, OCR, marca de agua…
│   └── ViewModels   runtime classes (.idl) con INotifyPropertyChanged
├── Tests/           GoogleTest para Core y Plataforma; pruebas de UI aparte
└── Herramientas/    (se quedan en Python) TSL, índice de emojis, icono, fondo del sello
```

Los generadores de datos (`create_trust_list.py`, `create_emoji_index.py`,
`create_app_icon.py`, `create_signature_background.py`) **no se migran**: se
ejecutan al preparar una versión y producen archivos (`es_tsl.pem`,
`emojis.json`, `.ico`, `signature_background.pdf`) que la app C++ lee igual.

## 3. Qué sustituye a cada pieza

| Hoy (Python) | Destino nativo | Notas |
| :-- | :-- | :-- |
| PyQt6 (ventanas, estilos) | **WinUI 3 + XAML** | Estilos de `STYLESHEET` → `ResourceDictionary`. Iconos: seguir con **Fluent UI System Icons** incluida (`FontIcon` con la fuente del paquete), no Segoe (decisión r58). |
| QScrollArea + QLabel del visor | Control propio sobre **`SwapChainPanel` + Direct2D** (o Win2D `CanvasVirtualControl`) | Tiles por página a la resolución del zoom; es la pieza de UI más grande. |
| Miniaturas con arrastre (r51/r52) | `GridView` con `CanReorderItems` | El arrastre nativo sustituye la solución híbrida con OLE. |
| PyMuPDF | **MuPDF (API C)** | Mismo motor: anotaciones, redacción, `TextWriter`, `show_pdf_page`, formularios, subconjuntos de fuentes, cifrado. Licencia AGPL o comercial (ver §8). |
| pyHanko (firma) | MuPDF `pdf_sign_signature` con un **firmante propio** (`pdf_pkcs7_signer`) respaldado por CNG + CryptMsg | Firma incremental como hoy. **Mejora**: claves no exportables (DNIe, tarjetas, tokens) sin pasar por PFX (hoy `cert_manager` exporta con PowerShell y falla con ellas). |
| pyHanko (sello visual) | Apariencia construida con MuPDF | Recuadro redondeado, logotipo MOSCA de fondo, texto ajustado al ancho (invariante 45). |
| pyHanko (sellado de tiempo) | `CryptRetrieveTimeStamp` (RFC 3161) | Mismos presets de TSA. |
| pyHanko (validación) | MuPDF (`pdf_check_digest`, cambios desde la firma) + `CertGetCertificateChain` con anclas de la TSL | **La pieza más difícil**: el análisis de modificaciones permitidas (DocMDP) de pyHanko no tiene equivalente directo (§8). |
| `remove_last_signature` (r61) | Mismo método: truncar a la revisión anterior + campo vacío incremental | MuPDF expone las revisiones y el guardado incremental. |
| tesseract.exe (r60) | **libtesseract** (API C++) + `TessPDFRenderer` solo texto | Sin procesos externos ni `pdf.ttf` en carpetas; se conservan Sauvola, enderezado ≥ 1° y la orientación verificada. |
| OpenCV (Python) | OpenCV C++ (o el perfil de proyección propio, ~60 líneas) | Solo se usa para enderezar. |
| pdf2docx | Escritor **DOCX de MuPDF** (biblioteca *extract*) | Comparar la calidad con pdf2docx antes de decidir (§8). |
| keyring | Administrador de credenciales de Windows | |
| QSettings | `ApplicationData::LocalSettings` (empaquetada) o JSON en `%LOCALAPPDATA%` | Migrar los ajustes existentes la primera vez. |
| `color_picker` | Control `ColorPicker` de WinUI | Conservar la paleta común (r42) y la transparencia. |
| Noto / Noto Emoji | Mismas fuentes incluidas; en pantalla con DirectWrite | En el PDF se siguen escribiendo con MuPDF. |
| PyInstaller + Inno Setup (r62) | Windows App SDK **autocontenido** + Inno Setup (o MSIX, §8) | Mismas decisiones: por usuario, Inicio + escritorio, «Abrir con». |

## 4. Preparar el entorno (una vez)

1. **Control de versiones**: el proyecto no es un repositorio git. Crear uno
   (`git init`) y trabajar la versión C++ en una carpeta o rama propia.
2. **Visual Studio 2022 (17.x) o posterior** con las cargas de trabajo
   «Desarrollo de escritorio con C++» y «Desarrollo de aplicaciones de Windows»
   con las plantillas de C++ de WinUI (Windows App SDK). Comprobar en ese
   momento la **última versión estable del Windows App SDK** y del Windows SDK.
3. **vcpkg** en modo manifiesto (`vcpkg.json`) para `mupdf`, `tesseract`,
   `leptonica`, `opencv` (solo `core` e `imgproc`) y `gtest`; comprobar que los
   *ports* traen las opciones necesarias (JavaScript de MuPDF, escritor DOCX).
4. **Proyecto base**: plantilla «WinUI Blank App (Packaged/Unpackaged)» en C++,
   y al lado una biblioteca estática `Core` y un proyecto de pruebas GoogleTest.
5. **Integración continua mínima** (aunque sea local): un script que compile en
   Release y pase todas las pruebas, como hoy `run.ps1 -Pruebas`.

## 5. Fases

Cada fase termina con **criterios de aceptación medibles**; no se empieza la
siguiente sin cumplirlos.

### Fase 0 — Oráculo y lista de paridad (antes de escribir C++)

* Convertir la tabla de funciones de `herramientas_profesionales.md` y las 59
  invariantes de la memoria en una **lista de comprobación de paridad**.
* Montar un **corpus de referencia**: los PDF de las pruebas, `OCR.PDF`,
  `Factura Honorarios.pdf`, `Formulario.pdf`, `Notificacion.PDF`, los 45
  escaneos del banco de OCR de r60 y, para cada uno, lo que produce hoy la app
  Python (texto extraído, resultados de búsqueda, PDF tras cada operación,
  informes de validación de firmas).
* **Aceptación**: el corpus se regenera con un solo comando desde la app Python.

### Fase 1 — Núcleo de documento

Abrir **siempre desde bytes** (el archivo no queda bloqueado), guardar completo e
incremental, `_clean_bytes`/`_pending_bytes`, cifrado AES-256 y permisos,
deshacer por instantáneas, render de página y miniaturas, texto, búsqueda y
selección por palabras con la unión de renglones al copiar (r34).
* **Aceptación**: pruebas GoogleTest equivalentes a las del núcleo actual;
  textos y búsquedas idénticos a los del corpus.

### Fase 2 — Esqueleto WinUI 3

Ventana con barra de título propia y Mica, barra de herramientas con iconos
Fluent UI System Icons, visor con zoom (Ctrl+rueda, 100 %, ancho/alto con el
icono de la acción libre, r48), campo de página de 4 dígitos (r53), búsqueda
dinámica (r50), pestañas de documentos, panel lateral con miniaturas y
marcadores, arrastrar y soltar, recientes, «Abrir con».
* **Aceptación**: abrir, navegar, buscar y cambiar de documento con la misma
  fluidez que la versión Python en los PDF del corpus; icono propio en la barra
  de tareas (r57).

### Fase 3 — Comentar

Texto enriquecido (Noto, negrita/cursiva, alineación), notas, resaltar /
subrayar / tachar / ondulado sobre texto y **a mano alzada con enderezado por
velocidad** (r59), rectángulo, emojis (Noto Emoji con color y transparencia),
borrador, seleccionar, mover y redimensionar, selector de color común.
* **Aceptación**: las anotaciones creadas por la versión C++ se ven igual en la
  versión Python y en Acrobat, y viceversa.

### Fase 4 — Editar, organizar y herramientas

Editar contenido real (port de `pdf_edit`: redacción con marcas ajenas
apartadas, fuente del documento, imágenes por aparición; invariantes 31-33),
formularios con JavaScript, operaciones de página con reordenar arrastrando,
marca de agua, encabezado/pie/Bates, compresión (niveles de r-compresión),
exportar a imágenes, texto y Word, propiedades, aplanar.
* **Aceptación**: los PDF resultantes coinciden con el corpus (mismo texto,
  mismas páginas; comparación visual por píxeles con tolerancia).

### Fase 5 — OCR

libtesseract con los modelos «best», orientación verificada, sustitución de la
capa anterior, Sauvola y enderezado ≥ 1° (r60).
* **Aceptación**: con el banco de r60, **F1 ≥ 0,922** de media y **≥ 0,957**
  en `OCR.PDF`, y cada palabra sobre su tinta.

### Fase 6 — Firma digital

Selector de certificados del almacén de Windows y PFX, firmar con claves no
exportables, opciones (motivo, lugar, contacto, certificación), sellado de
tiempo, sello visual, firma en un recuadro de formulario vacío (r38), firmas
múltiples incrementales, validación con la TSL de España, panel verificado
automáticamente y papelera en la última firma (r61).
* **Aceptación**: los PDF firmados por la versión C++ **validan con pyHanko y
  con Acrobat**; los informes de validación de la versión C++ coinciden con los
  de pyHanko sobre todo el corpus firmado; firmar con un DNIe/tarjeta funciona.

### Fase 7 — Integración con Windows y distribución

Instalador por usuario (Inicio, escritorio, «Abrir con»), autodiagnóstico
(`--autodiagnostico`, r62), registro de errores, opcionalmente el menú
contextual de r55 con `IExplorerCommand`, accesibilidad (Narrador, teclado,
contraste alto) y tema oscuro.
* **Aceptación**: el ciclo instalar → usar → desinstalar deja el equipo limpio,
  como en r62.

### Fase 8 — Certificación de paridad y relevo

Recorrer la lista de la fase 0 entera con las dos versiones en paralelo durante
un periodo de uso real. Solo entonces la versión C++ sustituye a la de Python.

## 6. Pruebas

* **Núcleo y plataforma**: GoogleTest, portando las 160 pruebas actuales (las de
  interfaz se convierten en pruebas de ViewModel siempre que se pueda).
* **Oráculo**: comparación automática con el corpus de la fase 0.
* **Firma**: validar cada PDF firmado por la versión C++ con pyHanko (el
  Python se queda como herramienta de verificación).
* **OCR**: el banco de r60, tal cual.
* **Interfaz**: pruebas de UI con UI Automation (Appium/WinAppDriver u
  otra herramienta equivalente; comprobar cuál está mantenida al empezar).

## 7. Esfuerzo orientativo

13.600 líneas de Python suelen convertirse en varias veces más de C++ (sin
contar XAML). Solo como orden de magnitud, para **una persona con experiencia en
C++ y WinUI 3**: del orden de **9 a 14 meses** hasta la paridad completa, con
la firma (fase 6) y el visor (fase 2) como partes más largas. La cifra depende
sobre todo de las decisiones de §8.

## 8. Riesgos y decisiones pendientes (de Ricardo)

| Tema | Por qué importa | Opciones |
| :-- | :-- | :-- |
| **Licencia de MuPDF** | MuPDF (y PyMuPDF, hoy) es **AGPL**: distribuir la app obliga a publicar su código bajo AGPL, salvo licencia comercial de Artifex. | Mantener AGPL · licencia comercial · PDFium (BSD) para ver + otro motor para editar (mucho más trabajo y sin paridad con los trucos actuales). |
| **Validación de modificaciones (DocMDP)** | pyHanko distingue cambios permitidos tras firmar («Relleno de formularios / firmas posteriores»); no hay biblioteca C++ equivalente. | Implementarlo sobre MuPDF (grande) · versión simplificada (íntegra / cambiada después) · seguir validando con pyHanko incluido. |
| **Exportar a Word** | pdf2docx y el escritor DOCX de MuPDF no dan el mismo resultado. | Medir con el corpus y decidir. |
| **C++/WinRT** | Sin diseñador visual de XAML para C++; comprobar al empezar su estado de mantenimiento y el soporte de Recarga activa. | Seguir con C++/WinRT (lo pedido) · núcleo en C++ con la interfaz en C# (más productivo, deja de ser «todo C++»). |
| **Distribución** | MSIX da asociaciones y desinstalación limpias pero **exige firma de código**; autocontenido + Inno Setup funciona sin certificado (como r62). | Autocontenido + Inno Setup (recomendado al principio) · MSIX (con certificado o Microsoft Store). |
| **OCR** | `Windows.Media.Ocr` viene con Windows y no ocupa espacio, pero no se ha medido. | Pasarlo por el banco de r60 y comparar con Tesseract. |
| **Solo Windows 11** | WinUI 3 funciona también en Windows 10 1809+, pero Mica y algunos controles son de Windows 11. | Fijar Windows 11 como mínimo (lo pedido) o admitir Windows 10. |

## 9. Primeros pasos concretos

1. Decidir los puntos de §8 (sobre todo licencia de MuPDF y validación DocMDP).
2. `git init` y primer commit de la versión r62 tal cual.
3. Fase 0: script que genera el corpus de referencia desde la app Python.
4. Instalar Visual Studio con las cargas de trabajo, vcpkg y el Windows App SDK;
   crear la solución vacía (App + Core + Tests) y comprobar que compila una
   ventana WinUI 3 que abre un PDF con MuPDF y lo pinta.
5. Con eso funcionando, empezar la fase 1.

## 10. Alternativa en Python: pruebas de concepto (r66)

Ricardo preguntó si se podía llegar a una app nativa de Windows 11 **sin
reescribir en C++**: mantener el núcleo Python (PyMuPDF, pyHanko, Tesseract) y
cambiar solo la interfaz. Se hacen dos pruebas en su equipo.

### Prueba 1 — Estilo `windows11` de Qt (hecha el 2026-09-24)

PyQt6 6.11 trae el estilo `windows11` (`QStyleFactory.keys()` →
`windows11, windowsvista, Windows, Fusion`). Se lanzó la app sin tocar su código
(script aparte) en cuatro variantes, con `Formulario.pdf` abierto, y se
capturó la ventana y el menú Archivo:

| Variante | Resultado |
| :-- | :-- |
| `Fusion` + hoja de estilos (lo actual) | Referencia. |
| `windows11` + hoja de estilos actual | **Casi idéntica**: la hoja de estilos manda en casi todo. Cambian solo los menús (esquinas redondeadas, sombra y flecha «›» de Windows 11) y el subrayado de las teclas de acceso, que pasa a verse solo al pulsar Alt (como en Windows). **Empeora** algo: la miniatura seleccionada pierde el velo azul (habría que devolvérselo en la hoja de estilos). |
| `windows11` sin hoja de estilos | **Inservible tal cual**: los botones de icono de la barra se convierten en botones anchos con marco, los iconos quedan diminutos y el panel lateral pierde su aspecto. |
| `windows11` sin hoja + Mica (`DwmSetWindowAttribute(38, 2)`, devuelve OK) | **Mica no se ve**: los widgets de Qt pintan fondos opacos encima. Para verlo habría que dejar transparentes a mano las zonas de fondo; Qt no lo soporta oficialmente para widgets. |

**Conclusión**: el estilo `windows11` de Qt es un **retoque cosmético** (menús
y ventanas emergentes), no una app nativa: los controles siguen siendo de Qt,
sin Mica, sin la barra de título integrada ni los controles de WinUI 3.
Adoptarlo costaría poco (cambiar `app.setStyle` y arreglar la selección de
miniaturas), pero no acerca a lo que pide Ricardo.

### Prueba 2 — WinUI 3 desde Python con PyWinRT (hecha el 2026-09-24)

Código: [prototipos/winui3/visor_poc.py](../prototipos/winui3/visor_poc.py) y su
receta de PyInstaller `visor_poc.spec`. Entorno aparte (no el de la app):
`%LOCALAPPDATA%ventyapdfenv-winui3` con `winui3-Microsoft.UI.Xaml*` 3.2.1
(Windows App SDK **1.7**), `winrt-runtime` 3.2.1, PyMuPDF y PyInstaller.

| Objetivo | Resultado |
| :-- | :-- |
| Ventana WinUI 3 con XAML cargado en tiempo de ejecución (`XamlReader.load`) | ✅ Aparece en ~1,5 s. |
| Aspecto de Windows 11 | ✅ Fondo **Mica**, barra de título propia (`ExtendsContentIntoTitleBar` + `SetTitleBar`) con el icono de la app, `CommandBar` y botones nativos de WinUI. |
| Barra con Fluent UI System Icons (la fuente de `vendor/`) | ✅ **Solo empaquetado**: WinUI 3 carga fuentes propias únicamente con `ms-appx:///`, que en una app sin MSIX es la carpeta del `.exe` (con PyInstaller, `_internal/vendor/...`). Con `python.exe` apunta a la carpeta de Python y salen cuadrados; `file:///` y la ruta absoluta **no** funcionan. |
| Página del PDF con PyMuPDF | ✅ `get_pixmap` → `WriteableBitmap` (RGBA→BGRA copiando al `pixel_buffer` con `memoryview`), renderizada a la escala real de la pantalla: nítida. |
| Zoom con Ctrl + rueda, desplazamiento con la rueda | ✅ Probado con ratón real: 100 % → 133 % en 3 pasos, volviendo a renderizar. |
| Clic → coordenadas de la página | ✅ `PointerPressed` + `GetCurrentPoint(imagen)` / zoom → puntos de PyMuPDF. |
| Empaquetado con PyInstaller | ✅ `VisorWinUI3.exe`, 89 MB (casi todo PyMuPDF), `collect_all("winui3")` y `collect_all("winrt")` meten la DLL de arranque del runtime. |

**Trampas encontradas** (anotarlas antes de seguir por aquí):

* Los paquetes `winrt-Microsoft.*` 2.x (SDK 1.6) **están abandonados**; los
  buenos son `winui3-Microsoft.*` 3.x y el espacio de nombres `winui3.*`
  (ejemplo oficial: `pywinrt/samples/winui3/hello_app.py`).
* El runtime del Windows App SDK de la versión exacta (hoy 1.7) tiene que estar
  **completo** en el equipo (marco + `Main` + `DDLM`). Si falta, `initialize()`
  da «No se pudieron resolver los criterios de dependencia del paquete». El
  instalador real tendría que llevar `WindowsAppRuntimeInstall-x64.exe` de esa
  versión (o `ON_NO_MATCH_SHOW_UI` para que Windows ofrezca instalarlo).
* Una subclase de `Application` **no admite argumentos** en el constructor
  («Invalid parameter count»): los datos van por atributos de clase.
* El `python.exe` de un venv es un lanzador: la ventana es de su proceso hijo
  (otro PID). Solo importa para automatizar pruebas.
* Faltó por probar el selector de archivos: `FileOpenPicker` necesita el HWND
  en una app sin MSIX (`InitializeWithWindow`) o los selectores nuevos del SDK
  1.8.

### Conclusión de las dos pruebas

* **Qt `windows11`**: retoque cosmético, no una app nativa. No vale para lo que
  pide Ricardo.
* **PyWinRT + WinUI 3**: **funciona** para una app de verdad: controles, Mica,
  barra de título e iconos nativos de Windows 11, con el núcleo Python intacto
  (PyMuPDF aquí; pyHanko, Tesseract y el resto no dependen de la interfaz).
  Frente a la reescritura en C++ de §1-§9, solo hay que rehacer la capa de
  interfaz: de las ~13.600 líneas, unas 8.700 están en módulos que usan Qt y
  unas 4.900 son núcleo puro que se queda tal cual (las 160 pruebas del núcleo
  siguen valiendo). Lo más laborioso sería el visor: selección de texto,
  anotaciones, edición en el sitio y formularios pintados sobre la página
  (hoy en `viewer.py`, `inplace_editor.py`, `form_ui.py`), a rehacer con
  `Canvas` y capas encima del `Image`.
* **Riesgos** de la vía Python: PyWinRT lo mantiene la comunidad (no
  Microsoft); no hay diseñador visual de XAML (como en C++/WinRT); hay que
  llevar el runtime del Windows App SDK en el instalador; y el problema de la
  licencia AGPL de MuPDF (§8) sigue igual en las dos vías.

### Medida de memoria (r67): WinUI 3 NO hace la app más ligera

Ricardo aclaró el objetivo: **que la aplicación pese menos estando abierta**.
Medido en su equipo (memoria privada = la columna «Memoria» del Administrador
de tareas; «en uso» = conjunto de trabajo, incluye DLL compartidas), con
`Formulario.pdf` abierto y la app ya asentada:

| Proceso | En uso | Privada |
| :-- | --: | --: |
| App actual empaquetada (Qt) | 231 MB | 259 MB |
| Solo importar los módulos de la app, sin ventana | 103 MB | 183 MB |
| Visor mínimo en **Qt** (lo mismo que el prototipo) | 92 MB | **64 MB** |
| Visor mínimo en **WinUI 3** (el prototipo, empaquetado) | 150 MB | **94 MB** |
| **App actual con `OPENBLAS_NUM_THREADS=1`** (r67) | 230 MB | **161 MB** |

* A igualdad de funciones, **WinUI 3 gasta más que Qt** (94 frente a 64 MB):
  cambiar de interfaz no ahorra memoria.
* Lo que pesaba eran las bibliotecas cargadas al arrancar. Por importación
  (memoria privada): **numpy +102 MB** (OpenBLAS reserva un búfer por núcleo),
  PyMuPDF +38, pyHanko +20, pdf2docx +7, cryptography +4, OpenCV +3, Qt +3.
* Arreglo de r67: `OPENBLAS_NUM_THREADS=1` en `main.py` → **259 → 161 MB**
  (−38 %), sin perder velocidad en el OCR (2 páginas: 77 s → 71 s).
* Siguiente ahorro posible: importar pyHanko, OpenCV/numpy y pdf2docx solo
  cuando se firma, se hace OCR o se exporta a Word (unos 35 MB más).

**Conclusión**: para pesar menos, **no hay que migrar la interfaz** ni a WinUI
3 desde Python ni a C++; hay que cargar menos cosas. La migración queda como
decisión de aspecto (controles nativos de Windows 11), no de memoria.
