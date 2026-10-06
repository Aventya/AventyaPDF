# Informe: AventyaPDF frente a proyectos similares y otras formas de hacerlo

> 2026-10-06 · Petición de Ricardo: «revisa toda la documentación accesible de
> proyectos similares de GitHub y crea un informe comparativo, además revisa la
> viabilidad de realizar este proyecto de otra forma (como por ejemplo usando
> React) y que se mantenga con un consumo de memoria pequeño».
>
> Las cifras de otros proyectos salen de sus páginas de GitHub y de mediciones
> publicadas por terceros (enlaces al final). Las de AventyaPDF se midieron en
> la nube (Linux, sin pantalla), así que en Windows serán algo distintas. Las
> estrellas de GitHub son las de hoy y sirven solo como idea de popularidad.
> Las cifras de AventyaPDF en Windows son las medidas en el equipo de Ricardo
> en r67 (`docs/plan_migracion_winui3.md` §10).

## 1. Conclusión en pocas líneas

- **Rehacerlo con React no reduciría la memoria; la aumentaría o la dejaría
  igual.** Una aplicación React de escritorio corre dentro de un navegador
  Chromium (Electron) o del navegador de Windows (WebView2, con Tauri). Solo esa
  base ya ocupa lo mismo o más que AventyaPDF entero hoy (unos 120-160 MB en
  Windows con un PDF abierto).
- **La única forma de bajar mucho la memoria es una aplicación nativa** (C++ o
  C#), como SumatraPDF. Es el camino del plan WinUI 3 que ya está escrito
  (`docs/plan_migracion_winui3.md`), y es el más caro: rehacerlo todo.
- **React sí tendría sentido para otra cosa: una versión web** que funcione en
  el navegador sin instalar nada, como BentoPDF o Stirling-PDF. Sería un
  producto distinto, no un sustituto ligero de la aplicación de escritorio.
- **Recomendación: seguir con Python.** AventyaPDF está en una franja de
  memoria razonable, usa el mismo motor que los visores más rápidos (MuPDF) y
  tiene funciones que la mayoría de los proyectos parecidos no tienen juntas:
  firma digital con certificados de Windows, OCR, edición del texto real del
  PDF y menú del botón derecho del Explorador.

## 2. AventyaPDF hoy

| Aspecto | Situación |
|---|---|
| Lenguaje e interfaz | Python + PyQt6 (Qt 6) |
| Motor PDF | MuPDF, a través de PyMuPDF |
| Firma digital | pyHanko (PAdES), certificados de Windows y archivos .pfx |
| OCR | Tesseract, con enderezado propio de páginas |
| Licencia | AGPL-3.0 |
| Distribución | Instalador firmado con Sigstore; paquete de la Microsoft Store en preparación |

**Memoria medida en Windows** (equipo de Ricardo, r67, «Memoria» del
Administrador de tareas, con un PDF abierto):

| Medición | Memoria |
|---|---|
| Aplicación antes de r67 | 259 MB |
| Aplicación tras r67 (ajuste de NumPy) | **161 MB** |
| Visor mínimo hecho con Qt (prueba) | 64 MB |
| Visor mínimo hecho con WinUI 3 (prueba, misma función) | 94 MB |

Desde entonces, la 0.9.14 (r131) ya no carga OpenCV, NumPy ni pyHanko al
abrir; r67 calculaba que eso ahorraría unos 35 MB más, así que hoy debería
rondar los **120-130 MB** (sin medir aún en Windows). La prueba de r67 también
mostró que, para lo mismo, **Qt gasta menos que WinUI 3** usado desde Python.

**Memoria medida en Linux** (nube, versión 0.9.14, 2026-10-06):

| Momento | Memoria |
|---|---|
| Python con el motor PDF cargado | 45 MB |
| + Qt (la librería de las ventanas) | 67 MB |
| Ventana de AventyaPDF abierta | 113 MB |
| Con un PDF de 50 páginas abierto | 126 MB |

Las dos mediciones encajan: unos 120-130 MB con un documento abierto.

## 3. Proyectos parecidos en GitHub

| Proyecto | Qué es | Tecnología | Motor PDF | Licencia | Estrellas |
|---|---|---|---|---|---|
| **Stirling-PDF** | Más de 50 herramientas PDF (editar, unir, dividir, firmar, OCR, convertir, ocultar). Se usa en el navegador, montado en un servidor propio, o con un cliente de escritorio. | Java (servidor) + interfaz web | Java (servidor) | Núcleo abierto, con partes de pago | ~93.600 |
| **BentoPDF** | Más de 50 herramientas que funcionan **dentro del navegador**, sin subir los archivos a ningún sitio. | TypeScript + Vite (web) | pdf.js, pdf-lib, EmbedPDF, qpdf, PyMuPDF y Ghostscript compilados para el navegador | AGPL-3.0 o licencia comercial | ~15.800 |
| **SumatraPDF** | Visor muy ligero para Windows (PDF, EPUB, CBZ…). Solo ver, sin editar. | C/C++ | **MuPDF** (el mismo que AventyaPDF) | GPLv3 | ~17.700 |
| **PDF Arranger** | Unir, dividir, girar, recortar y reordenar páginas. | **Python + GTK** | pikepdf | GPL-3.0 | ~6.000 |
| **PDFsam Basic** | Unir, dividir, extraer, mezclar y girar. | Java + JavaFX | Java | AGPL-3.0 | ~4.600 |
| **PDF4QT** | Editor completo: anotaciones, formularios, firma digital, cifrado, comparar documentos. | **C++ + Qt** | Motor propio | MIT | ~1.500 |
| **EmbedPDF** *(librería, no aplicación)* | Visor para React y otros marcos web, con anotaciones, búsqueda y ocultación real de contenido. | TypeScript | **PDFium** (el de Chrome) para el navegador | MIT | — |
| **MuPDF.js** *(librería)* | El motor de AventyaPDF para el navegador: pintar, anotar, editar páginas, ocultar contenido, formularios. | TypeScript | **MuPDF** para el navegador | AGPL-3.0 o licencia comercial | ~600 |

### Qué nos enseñan

- **Nadie hace todo lo que hace AventyaPDF en una aplicación de escritorio
  ligera.** Las más completas (Stirling-PDF, BentoPDF) son **web**; las de
  escritorio, o solo ven (SumatraPDF) o solo organizan páginas (PDF Arranger,
  PDFsam). PDF4QT es la más parecida en ambición, en C++ y con motor propio.
- **PDF Arranger demuestra que Python sirve** para una herramienta PDF de
  escritorio estable y mantenida durante años.
- **SumatraPDF es la referencia de ligereza**: usa nuestro mismo motor (MuPDF)
  pero escrito todo en C++, sin capa de interfaz pesada. Sus usuarios cuentan
  que arranca con 10-20 MB y crece a cientos de megas con documentos pesados:
  **la memoria la ponen sobre todo los documentos, no el lenguaje.**
- **La tendencia web «todo en el navegador»** (BentoPDF) es la que más crece:
  privacidad (nada sale del equipo) y cero instalación.

## 4. ¿Se puede rehacer de otra forma con poca memoria?

### 4.1 Las opciones

| Opción | Memoria esperada en Windows | Esfuerzo | Seguridad | Qué se pierde o complica |
|---|---|---|---|---|
| **Seguir con Python + Qt** (actual) | ~120-130 MB con un PDF (161 MB medidos en Windows antes de r131) | Ninguno | Buena (motor en C) | Nada |
| **React + Electron** | ~160 MB o más **solo la base** (navegador Chromium incluido), más el motor PDF | Rehacerlo todo | Buena si se aísla bien | Firma con certificados de Windows, conversión de Word, menú del Explorador: todo eso necesita piezas nativas aparte |
| **React + Tauri** (usa el navegador de Windows, WebView2) | Las cifras publicadas varían mucho: de ~40-80 MB en pruebas sencillas a cifras **iguales o peores que Electron** con contenido real, porque WebView2 también es Chromium | Rehacerlo todo, más una parte en Rust | Muy buena (Rust) | Lo mismo que Electron |
| **C++ + WinUI 3** (plan ya escrito) | Baja, decenas de MB de base (referencia: SumatraPDF). Ojo: el visor mínimo WinUI 3 de r67, desde Python, gastó más que el de Qt (94 frente a 64 MB); el ahorro solo llega quitando Python del todo | El mayor: rehacerlo todo en C++ | Media (C++ exige mucho cuidado) | Nada, pero es el trabajo más largo |
| **C# (.NET) + WinUI 3** | Baja-media | Rehacerlo todo | Muy alta | Hay que buscar en .NET piezas equivalentes a pyHanko |
| **C++ + Qt** (como PDF4QT) | Baja | Rehacerlo todo | Media | Nada |

### 4.2 Por qué React no ahorra memoria

1. **Una aplicación React de escritorio lleva un navegador dentro.** Con
   Electron, Chromium viene incluido; con Tauri se usa WebView2, que en Windows
   también es Chromium. Una prueba publicada en Windows 10 midió la misma web
   en Tauri y en Electron y Tauri **gastó más** (399 MB frente a 318 MB). Las
   pruebas que dan a Tauri 40-80 MB son de ventanas casi vacías.
2. **El motor PDF va además dentro del navegador** (MuPDF.js, PDFium o pdf.js
   compilados para el navegador), con su propia copia de cada documento.
3. **Lo que hoy hace Python habría que rehacerlo fuera del navegador**: la
   firma con el almacén de certificados de Windows, la conversión de Word, el
   OCR rápido con Tesseract y el menú del botón derecho. Habría que escribir
   esas partes en Rust o C++ y conectarlas: más piezas y más memoria.

Si se hiciera en React, el mejor encaje técnico sería **Tauri + MuPDF.js**:
mismo motor que hoy, licencia AGPL compatible con la de AventyaPDF y la parte
nativa en Rust, que es muy seguro. Aun así, la memoria no bajaría de la actual.

### 4.3 Donde React sí aporta: una versión web

Una **AventyaPDF web** (React + MuPDF.js o EmbedPDF, todo dentro del
navegador, como BentoPDF) permitiría:

- usarla desde cualquier equipo sin instalar nada, también fuera de la oficina;
- que los documentos de los clientes **no salgan del equipo**, porque todo se
  procesa en el navegador;
- reutilizar el mismo motor (MuPDF).

Limitaciones: la firma con certificados instalados en Windows no es posible
desde una web normal (habría que firmar con archivo .pfx), el OCR sería más
lento y la conversión de Word, muy pesada. Sería un complemento, no un
sustituto.

## 5. Recomendación

1. **Mantener AventyaPDF en Python + Qt.** Su memoria está en una franja
   razonable, el motor es el mismo que el de los visores más rápidos y la
   función más valiosa (firma, OCR, edición real, integración con Windows) ya
   está hecha y probada.
2. **Si el objetivo fuera ocupar muy poca memoria**, el único camino real es el
   **plan WinUI 3** (`docs/plan_migracion_winui3.md`), o C# si se prefiere
   seguridad a rendimiento máximo. Es un proyecto de meses, no un ajuste.
3. **Si interesa llegar a equipos sin instalar nada**, estudiar aparte una
   **versión web** con React y MuPDF.js, centrada en lo que funciona bien en el
   navegador: ver, organizar páginas, unir, dividir, anotar y firmar con .pfx.
4. **No rehacer la aplicación de escritorio en React**: no ahorra memoria y
   obliga a rehacer en otro lenguaje justo las partes más delicadas.

## Fuentes

- Stirling-PDF: https://github.com/Stirling-Tools/Stirling-PDF
- BentoPDF: https://github.com/alam00000/bentopdf
- SumatraPDF: https://github.com/sumatrapdfreader/sumatrapdf · https://en.wikipedia.org/wiki/Sumatra_PDF · foro sobre memoria: https://forum.sumatrapdfreader.org/t/sumatra-takes-huge-amount-of-ram/3819
- PDF Arranger: https://github.com/pdfarranger/pdfarranger
- PDFsam Basic: https://github.com/torakiki/pdfsam
- PDF4QT: https://github.com/JakubMelka/PDF4QT
- EmbedPDF: https://www.embedpdf.com/react-pdf-viewer · https://github.com/embedpdf/embed-pdf-viewer
- MuPDF.js: https://github.com/ArtifexSoftware/mupdf.js
- Tauri frente a Electron en Windows (medición con la misma web): https://github.com/tauri-apps/tauri/issues/5889
- Cifras publicadas de Tauri y Electron en reposo: https://tech-insider.org/tauri-vs-electron-2026/ · https://blog.openreplay.com/comparing-electron-tauri-desktop-applications/
- Rendimiento de WebView2 (Microsoft): https://learn.microsoft.com/microsoft-edge/webview2/concepts/performance
