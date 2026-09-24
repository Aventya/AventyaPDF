# Plan de Implementación: Acrobat PAdES Signer & Editor (eIDAS & PAdES Compatible)

Este documento detalla la arquitectura, el diseño de la interfaz de usuario, y el motor criptográfico para el prototipo funcional de un software de PDF avanzado con visualización, firma digital visible, edición básica de contenido (texto, resaltado), organización de páginas, compresión de archivos e inserción de marcas de atención estilo emoji/iconos.

## Requisitos y Control Criptográfico

> [!IMPORTANT]
> **Compatibilidad de Criptografía (pyHanko)**:
> Se utilizará la biblioteca `pyHanko` en combinación con `PyMuPDF` (fitz). `pyHanko` gestiona firmas PAdES de nivel empresarial en la estructura incremental de PDFs sin romper firmas previas.
>
> Para la firma visible, capturaremos las coordenadas exactas de PyQt6 y las traduciremos al sistema de coordenadas de la página PDF de PyMuPDF/pyHanko (teniendo en cuenta la resolución DPI, el zoom y que el origen del PDF (0,0) está en la esquina inferior izquierda, a diferencia de la UI donde está en la esquina superior izquierda).

> [!IMPORTANT]
> **Edición y Marcado de Emojis/Iconos**:
> * **Emojis de Atención**: En la barra de herramientas añadiremos un selector de Emojis (ej. 📌, ⚠️, 💡, ✅, ❌, 🔍) o sellos rápidos de atención.
> * El usuario selecciona el emoji de la barra de herramientas, hace clic en el visor y el emoji se dibuja en el PDF en las coordenadas exactas seleccionadas.
> * **Manipulación de Páginas**: Diálogo de organización con cuadrícula interactiva. Mover, borrar, insertar en blanco e importar desde otro PDF.
> * **Compresión**: Optimización y guardado comprimido nativo mediante PyMuPDF.

---

## Estructura de Directorios

Crearemos una arquitectura modular y limpia en el directorio raíz `a:\CARPETA IA\RICARDO\ANTIGRAVITY-PDF`:

```
antigravity-pdf/
│
├── requirements.txt            # Dependencias del proyecto (PyQt6, PyMuPDF, pyHanko, etc.)
├── main.py                     # Punto de entrada de la aplicación
├── main_window.py              # Interfaz de usuario principal (PyQt6)
├── organize_dialog.py          # Diálogo para ordenar, borrar e insertar páginas
├── signer_backend.py           # Backend criptográfico (pyHanko)
└── utils.py                    # Utilidades de conversión de coordenadas y manejo de PDF (Compresión y Edición)
```

---

## Componentes y Cambios Propuestos

### 1. Dependencias (`requirements.txt`)
Instalaremos las dependencias necesarias:
* `PyQt6`: Para la interfaz de usuario de alta calidad.
* `pymupdf` (fitz): Para renderizado ultra rápido, edición de texto, estampado de emojis como sellos visuales vectoriales o anotaciones, organización y compresión de PDFs.
* `pyHanko`: Para inyectar firmas digitales conformes con PAdES.
* `cryptography`: Backend criptográfico estándar.

### 2. Visor e Interfaz de Usuario (`main_window.py`)
* Estética Adobe Acrobat Premium:
  * **Barra de herramientas**:
    * Abrir / Guardar.
    * Selector de Zoom e Indicador de Páginas.
    * **Herramientas de Edición**: Botón "Añadir Texto" (clic para insertar texto libre), "Resaltar" e "Dibujar Rectángulo".
    * **Herramientas de Emojis/Marcas**: Botón "Insertar Marca/Emoji" que abre un menú desplegable rápido con emojis premium de atención (📌 Chincheta, ⚠️ Advertencia, 💡 Idea, ✅ Aprobado, ❌ Error, 🔍 Revisar).
    * **Herramientas de Páginas**: Botón "Organizar Páginas" (abre el diálogo para reordenar, borrar e insertar).
    * **Herramientas de Documento**: Botón "Optimizar / Comprimir PDF" (reduce el tamaño del archivo con un clic).
    * **Firma Digital**: Botón "Firmar digitalmente".
  * **Visor central**: Lienzo interactivo para renderizado y marcado visual (rectángulo azul transparente).

### 3. Diálogo de Organización de Páginas (`organize_dialog.py`)
* Ventana emergente tipo cuadrícula (grid) mostrando las miniaturas de todas las páginas del PDF.
* Funciones de arrastrar/soltar, borrar e insertar en blanco o desde otro archivo PDF.

### 4. Backend de Compresión, Edición y Estampado (`utils.py`)
* **Edición**: Inserción de textos, rectángulos y resaltados mediante anotaciones nativas de PyMuPDF.
* **Estampado de Emojis**: Inyección de emojis como anotaciones de texto especial con fuentes compatibles en la posición seleccionada mediante el evento de clic en el visor.
* **Compresión**: Guardado óptimo con compresión nativa en PyMuPDF (`garbage=4`, `deflate=True`).

### 5. Backend de Firma Digital (`signer_backend.py`)
* Firma digital PAdES utilizando `pyHanko`.

---

## Plan de Verificación

### Pruebas Manuales
1. Abrir un PDF, seleccionar un emoji de atención (ej. 📌 o ⚠️), hacer clic en el visor y ver cómo se estampa en el PDF en tiempo real.
2. Probar las utilidades de edición de texto, organización de páginas, compresión de PDF y la firma digital PAdES visible.
