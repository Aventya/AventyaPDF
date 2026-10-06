# Memoria del Proyecto: AventyaPDF Editor & Signer

Bienvenido al índice principal de la documentación del proyecto **AventyaPDF**. Este conjunto de documentos ofrece una memoria técnica detallada y distribuida de la aplicación, analizando su arquitectura, componentes de interfaz de usuario, capacidades de edición y sistema criptográfico de firma digital.

## Índice General

La documentación está distribuida en los siguientes archivos temáticos interrelacionados:

1. **[Arquitectura General (arquitectura.md)](arquitectura.md)**
   * Describe la estructura modular del proyecto, el flujo de datos y las dependencias principales.
2. **[Interfaz Gráfica y Visor (interfaz_grafica.md)](interfaz_grafica.md)**
   * Detalla la interfaz principal (`main.py` y `main_window.py`), el visor interactivo de PDF y la gestión de eventos de usuario (ratón/teclado).
3. **[Edición y Manipulación de PDF (edicion_pdf.md)](edicion_pdf.md)**
   * Explica los mecanismos de inyección de anotaciones (textos, resaltados, rectángulos, emojis) y el diálogo de organización visual de páginas.
4. **[Gestión de Certificados Digitales (gestion_certificados.md)](gestion_certificados.md)**
   * Describe la integración con el almacén personal de certificados de Windows, archivos PKCS#12, el uso de `keyring` y el selector interactivo.
5. **[Firma Digital PAdES (firma_digital.md)](firma_digital.md)**
   * Detalla la implementación criptográfica basada en `pyHanko` para la firma visible e incremental compatible con eIDAS.
6. **[Herramientas profesionales — versión 2.0 (herramientas_profesionales.md)](herramientas_profesionales.md)**
   * Mapa de las funciones tipo Acrobat Pro añadidas en la 2.0 (panel lateral, búsqueda, marcado de texto, deshacer, OCR, cifrado, sellado de tiempo, validación de firmas), decisiones de diseño, pruebas automáticas (`.\run.ps1 -Pruebas`), registro de errores y plan de pruebas manual.
7. **[Historial de versiones (historial_versiones.md)](historial_versiones.md)**
   * (r114) Solo se mantiene la última versión publicada; aquí queda la mención de las anteriores (ya retiradas de GitHub) y de su commit.
8. **[Comprobar que el instalador es auténtico (verificar_instalador.md)](verificar_instalador.md)**
   * (r116) Firma con Sigstore de cada instalador publicado: cómo se comprueba (sigstore o cosign), qué demuestra y qué no (no quita el aviso de SmartScreen).
9. **[Publicar en la Microsoft Store (microsoft_store.md)](microsoft_store.md)**
   * (r119) Paquete MSIX con todo dentro (Tesseract incluido) que la Store firma gratis: sin aviso de SmartScreen. Pasos de Partner Center y pruebas.
10. **[Política de privacidad (privacidad.md)](privacidad.md)**
   * (r119) Qué conexiones hace la app y qué guarda; la enlaza la ficha de la Store.
11. **[Empaquetado e instalador (empaquetado.md)](empaquetado.md)**
   * (r62, r102, r109) Cómo se genera `AventyaPDF-Setup-<versión>.exe` (lanzador propio + Inno Setup: el instalador solo lleva el código propio y descarga al instalar Python, los paquetes y las fuentes, con SHA-256; Tesseract, bajo demanda), qué instala, el autodiagnóstico, la instalación de prueba y lo pendiente (firma de código, tamaño/OpenCV).
12. **[Plan de migración a WinUI 3 + C++/WinRT (plan_migracion_winui3.md)](plan_migracion_winui3.md)**
   * (r63) Plan, sin empezar: arquitectura destino, qué sustituye a cada biblioteca, fases con criterios de aceptación, pruebas, esfuerzo y decisiones pendientes.
13. **[Informe: proyectos similares y otras formas de hacerlo (informe_alternativas.md)](informe_alternativas.md)**
   * (r135) Comparación con Stirling-PDF, BentoPDF, SumatraPDF, PDF Arranger, PDFsam y PDF4QT; viabilidad de React (Electron/Tauri) y de una app nativa, con el consumo de memoria de cada opción (2026-10-06).
14. **[Idiomas de la aplicación (idiomas.md)](idiomas.md)**
   * (r136) Siete idiomas: cómo se elige, dónde están los textos, cómo corregir una traducción y reglas para programar textos nuevos.

> Los documentos 1–5 describen la versión 1 (antes de la división de `main_window.py` en módulos). La composición actual de archivos está en [MEMORIA_EVOLUTIVA.md](../MEMORIA_EVOLUTIVA.md) §2.

---

## Archivos Fuente del Proyecto

Para facilitar la navegación directa al código, a continuación se listan los archivos fuente del proyecto vinculados con su ruta absoluta en el workspace:

* 🚀 **Punto de Entrada**: [main.py](file:///a:/CARPETA%20IA/RICARDO/AVENTYAPDF/main.py)
* 🖥️ **Ventana Principal**: [main_window.py](file:///a:/CARPETA%20IA/RICARDO/AVENTYAPDF/main_window.py)
* 📑 **Panel lateral y operaciones de página**: [sidebar.py](../sidebar.py)
* 🔐 **Gestión de Certificados**: [cert_manager.py](file:///a:/CARPETA%20IA/RICARDO/AVENTYAPDF/cert_manager.py)
* ✍️ **Backend de Firma**: [signer_backend.py](file:///a:/CARPETA%20IA/RICARDO/AVENTYAPDF/signer_backend.py)
* 🛠️ **Utilidades de PDF**: [utils.py](file:///a:/CARPETA%20IA/RICARDO/AVENTYAPDF/utils.py)
* 🔑 **Certificado de Pruebas**: [create_test_cert.py](file:///a:/CARPETA%20IA/RICARDO/AVENTYAPDF/create_test_cert.py)

---

## Relación de Documentos

Este fichero se relaciona directamente con:
* [Arquitectura General](arquitectura.md)
* [Interfaz Gráfica y Visor](interfaz_grafica.md)
* [Edición y Manipulación de PDF](edicion_pdf.md)
* [Gestión de Certificados Digitales](gestion_certificados.md)
* [Firma Digital PAdES](firma_digital.md)
