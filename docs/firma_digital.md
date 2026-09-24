# Firma Digital PAdES

Este documento expone en detalle la implementación del sistema criptográfico de firma digital de la aplicación, implementado en [signer_backend.py](file:///a:/CARPETA%20IA/RICARDO/AVENTYAPDF/signer_backend.py).

## Índice del Documento
1. [El Estándar PAdES e incrementalidad](#el-estándar-pades-e-incrementalidad)
2. [Estructura del Backend (signer_backend.py)](#estructura-del-backend-signer_backendpy)
3. [El Sello de Firma Personalizado](#el-sello-de-firma-personalizado)
4. [Extracción de Metadatos de Identidad](#extracción-de-metadatos-de-identidad)
5. [Relación con otros Documentos](#relación-con-otros-documentos)

---

## El Estándar PAdES e incrementalidad

La aplicación genera firmas electrónicas conformes con la especificación **PAdES (PDF Advanced Electronic Signatures)**, alineadas con el reglamento europeo eIDAS. 

Una firma digital PAdES requiere preservar el documento original sin modificaciones destructivas. Para lograr esto, el motor utiliza la firma **incremental**:
* En lugar de reescribir el PDF (lo cual invalidaría cualquier firma previa en el archivo), se añade una sección al final del documento (un "incremental update") que contiene el objeto de firma digital (`/Sig`) y el diccionario del campo de firma.
* La firma se aplica sobre el hash de todo el archivo excepto los bytes correspondientes al valor de la propia firma (marcado mediante el array `/ByteRange`).

---

## Estructura del Backend (signer_backend.py)

El backend de firmado está encapsulado en la clase estática [PAdESSigner](file:///a:/CARPETA%20IA/RICARDO/AVENTYAPDF/signer_backend.py#L163) y su método principal:

```python
def sign_pdf_visible_with_widget(
    input_pdf_path: str,
    output_pdf_path: str,
    pfx_path: str,
    pfx_password: str,
    page_num: int,
    box: tuple,
    reason: str = "Firma PAdES",
    location: str = "ES",
) -> bool:
```

### Proceso de Firmado:
1. **Extracción de Identidad**: Invoca `extract_cert_info` para recuperar los datos legibles del firmante.
2. **Carga de Claves**: Carga la clave privada y el certificado digital desde el archivo PKCS#12 (PFX) usando `SimpleSigner.load_pkcs12`.
3. **Configuración de Metadatos**: Crea un objeto `PdfSignatureMetadata` asignando el subfiltro de firma a `SigSeedSubFilter.PADES` e indicando la razón, localización y nombre del firmante.
4. **Especificación del Campo**: Define la ubicación geométrica (`SigFieldSpec`) indicando la página (`page_num`) y la caja de coordenadas `box: (x1, y1, x2, y2)`.
5. **Estilo del Sello**: Configura la apariencia del sello visible instanciando la clase personalizada `_SpanishCertStampStyle` y vinculando el texto formateado.
6. **Ejecución Incremental**: Instancia un `PdfSigner`, abre el PDF de origen mediante `IncrementalPdfFileWriter` y escribe el PDF firmado resultante de forma incremental.

**Firmar en el campo de firma de un formulario** (r38): si el PDF ya trae un recuadro de firma vacío (`/FT /Sig` sin `/V`), al hacer clic en él la app **pide primero el certificado** (r39: `choose_cert=True`, con el guardado preseleccionado; cancelar no firma) y firma **dentro de ese campo**, con su nombre y su recuadro, en vez de crear uno nuevo: `form_ui` → `MainWindow.sign_in_field` → `trigger_signature(rect, field_name)` → `PAdESSigner.sign_pdf_bytes(field_name=…)`, que lo detecta con `_empty_sig_field` y firma sin `new_field_spec`. Los campos de firma salen de `pdf_forms.field_boxes` (antes se descartaban, y por eso el recuadro no hacía nada); `signed` indica si ya tienen firma.

**PDF que pyHanko rechaza en modo estricto**: los de **referencias cruzadas híbridas** (tabla xref clásica con `/XRefStm`, habitual en documentos de Word o Acrobat; «hybrid xrefs are disabled») y, desde r37, los que dan cualquier `PdfReadError` al abrirlos, como una tabla xref que declara un objeto más de los que anuncia el tráiler («Xref table size mismatch», notificaciones del Colegio de Registradores). Los visores los abren sin protestar. `_tolerant_writer` los trata así:
* **Sin firmas previas**: se reescriben con PyMuPDF (xref clásica, conservando el cifrado) y se firma el resultado. No se pierde nada, porque no hay firmas que invalidar.
* **Con firmas previas**: se firma de forma incremental con el lector en modo no estricto, para no invalidarlas.
* La validación (`signature_validation._open_reader`) reabre estos archivos con `PdfFileReader(strict=False)`; como las firmas se leen en diferido, se recorren dentro del `try`. La comprobación criptográfica es la misma: si el archivo estuviese alterado, la firma saldría no válida.
* **«Identidad no verificada» no es un fallo del archivo**: significa que la cadena del firmante no acaba en ningún ancla de confianza conocida. Adobe usa su propia lista de confianza europea (EUTL/AATL), no el almacén de Windows, y por eso daba por buena una firma que aquí salía sin verificar.

### Confianza de las firmas: Windows y la lista de España (r43)

**(r61) Panel Firmas.** Las firmas se ven **siempre verificadas**: al mostrarse el panel se comprueban solas, en segundo plano, sin botón. La firma **más reciente** lleva una **papelera** que la quita y deja su recuadro vacío en el mismo sitio, para hacer clic y firmar de nuevo (con otro certificado si se quiere). Solo la más reciente, porque cada firma protege todo lo firmado antes que ella: quitar una anterior invalidaría las posteriores. Para no romper las demás, no se edita el campo y se reescribe el PDF (eso invalidaría todas): se vuelve a la versión exacta del archivo de antes de esa firma, que sigue dentro del propio PDF, y se le añade un campo de firma vacío (`signer_backend.remove_last_signature`). Queda como cambio sin guardar: al guardar se escriben esos bytes tal cual; para arrepentirse, cerrar sin guardar (no pasa por deshacer). Con otros cambios sin guardar la papelera está desactivada.

La validación (`signature_validation.validate_signatures`) acepta como ancla de confianza **lo que haya en el almacén de Windows (ROOT y CA) y, además, la lista de confianza de España (TSL)**, incluida en la aplicación en `vendor/trust/es_tsl.pem`. Así salen «Firma válida y de confianza» las firmas de las entidades cualificadas —FNMT (incluida «AC Sector Público», la de las administraciones públicas), Dirección General de la Policía (DNIe), Colegio de Registradores, ACCV, Izenpe, AOC, Defensa, Camerfirma y el resto de la lista— sin instalar nada en Windows ni pedir permisos de administrador.

* **Es una lista, no todo lo que traiga el PDF.** Se confía solo en lo que está en la TSL oficial, contrastado por huella. Un certificado raíz que viaje dentro del PDF **no** se toma como ancla: si lo fuera, cualquiera podría fabricar un PDF con una raíz falsa y salir «verificado». Ejemplo: la raíz autofirmada de los Registradores va dentro de sus PDF y no está en la TSL; la ancla es su «AC Interna», que sí está.
* **La TSL lista la CA que emite, a menudo una intermedia**, y no siempre su raíz; por eso se aceptan intermedias como ancla.
* **Qué entra** (`create_trust_list.py`): servicios de certificados cualificados (`CA/QC`) y de sellos de tiempo (`TSA/QTST`) con estado «concedido» y sin caducar. Se excluyen los declarados expresamente para sitios web (`QCForWSA` sin firma ni sello) y los servicios OCSP. Sin propósito declarado se toma la firma por defecto (los de la FNMT para el sector público solo declaran `QCQSCDManagedOnBehalf`).
* **Cómo se genera, con la firma comprobada de verdad** (`python create_trust_list.py`, necesita `pip install signxml` aparte, solo para generar):
  1. Descarga la LOTL (lista de la UE) y comprueba su firma XAdES contra `vendor/trust/oj_signers.pem` (los certificados de la Comisión Europea; ver ese archivo para su procedencia exacta). Si no valida, se aborta sin escribir nada.
  2. De la LOTL, ya de confianza, toma el puntero a España **y los certificados que la propia LOTL declara que deben firmar la TSL española** (no los que traiga el archivo descargado).
  3. Descarga la TSL de España y comprueba su firma contra esos certificados. Si no valida, se aborta.
  4. Solo entonces selecciona los servicios y escribe `vendor/trust/es_tsl.pem`, con la cabecera «Próxima actualización».
  Solo hace falta Internet para generarla; la aplicación usa el archivo y no necesita `signxml`.
* **Procedencia de `vendor/trust/oj_signers.pem`**: no es la lectura literal de la tabla del Diario Oficial (EUR-Lex es una aplicación JavaScript que no se pudo leer con las herramientas disponibles); son los certificados del propio `keystore.p12` del proyecto **DSS** (Digital Signature Service), la implementación de referencia de la Comisión Europea para eIDAS, tal cual los usa su validador (`ec.europa.eu/digital-building-blocks/DSS`). Contrastado (21-22/09/2026): la configuración de ese DSS declara `current.oj.url = https://eur-lex.europa.eu/eli/C/2026/1944/oj`, que coincide exactamente con el `SchemeInformationURI` que la LOTL en vivo declara como su propia publicación oficial; con esos certificados la firma de la LOTL y la de la TSL de España validaron. Es un almacén de raíces: no se regenera solo (`python create_trust_list.py --reanclar` lo vuelve a extraer a un archivo `.nuevo` aparte, para revisar el cambio a mano).
* **Hay que regenerar `es_tsl.pem`** antes de la fecha de «Próxima actualización» (la prueba `test_la_lista_incluida_esta_cargada_y_vigente` falla cuando pasa, a propósito). Sin regenerar, las CA nuevas saldrían «no verificadas».
* **Límites**: solo se usa el estado actual de cada servicio (una CA retirada después de firmar deja de ser de confianza aunque la firma fuera buena en su día); sin comprobación de revocación en línea; `oj_signers.pem` puede quedar desactualizado si la Comisión rota sus firmantes (la generación fallaría en voz alta, no en silencio).

### Un campo de firma puede ser una firma o un sello de tiempo de documento (r45)

Un PDF firmado puede llevar, además de la firma, un **sello de tiempo de documento** (`/DocTimeStamp`) añadido después: un campo de firma sin firmante que solo certifica una fecha sobre el PDF ya firmado (Acrobat y otras herramientas lo añaden al re-sellar). Es distinto de una firma normal (`/Sig`) y pyHanko exige la función de validación que toca a cada uno: `validate_pdf_signature` para `/Sig`, `validate_pdf_timestamp` para `/DocTimeStamp`. Antes de r45, `signature_validation` llamaba siempre a la primera, así que un `/DocTimeStamp` salía **«No se pudo validar» («Signature object type must be /Sig»)** aunque el sello fuera perfectamente válido — visto con `Factura Honorarios.pdf`, que lleva la firma del Colegio de Registradores y, detrás, un sello de tiempo suyo como segundo campo.

Ahora `emb.sig_object_type` decide qué función llamar, y `SignatureReport.is_timestamp` cambia el texto del veredicto («Sello de tiempo válido y de confianza» en vez de «Firma válida…») y qué campos se rellenan: la fecha del sello va en `timestamp`, no en `signed_at` (un sello no tiene «fecha declarada por el firmante» aparte de la suya propia). El panel Firmas (`sidebar.py`) muestra «Autoridad de sellado» en vez de «Firmante» para estas entradas.
* **Diagnóstico**: `python inspect_signature.py [archivo.pdf]` muestra el veredicto, la cadena del certificado y qué ancla (Windows o TSL) la respalda.

---

## El Sello de Firma Personalizado

Para ajustarse a los requisitos estéticos y de claridad exigidos en España y la Unión Europea, el backend implementa un sello gráfico personalizado a través de las clases privadas `_SpanishCertTextStamp` y `_SpanishCertStampStyle`:

### 1. Logotipo de fondo (`_draw_background`)
* Orden de dibujo: recuadro de color → logotipo → texto. Sin borde.
* **Recuadro de color** (`_draw_panel`): ocupa todo el recuadro de la firma, color #D1CCBD con un 75 % de transparencia (opacidad 0,25, ExtGState `/SigPanelGS`) y esquinas redondeadas de 14 pt. Se configura con `PANEL_RGB`, `PANEL_ALPHA` y `PANEL_RADIUS`; en recuadros muy pequeños el radio se limita a la mitad del lado menor.
* El logotipo es [MOSCA.svg](../MOSCA.svg) convertido a PDF vectorial en [signature_background.pdf](../signature_background.pdf) (`BACKGROUND_PDF`). Se importa con `writer.import_page_as_xobject` como XObject de formulario, así que conserva sus degradados y transparencias.
* Escala proporcional **siempre por el alto del recuadro** y **pegado al lado derecho** del recuadro. Si el recuadro es más estrecho que el logotipo, lo que sobresale se recorta con el mismo contorno redondeado del recuadro de color.
* Si falta `signature_background.pdf`, la firma se crea igualmente, sin fondo (aviso por consola).

### 1 bis. Regenerar el fondo
* `python create_signature_background.py [ruta.svg]` (usa `MOSCA.svg` por defecto). Requiere Microsoft Edge o Google Chrome, **solo para generar**: MuPDF no soporta máscaras, degradados con transparencia ni opacidad de grupo.
* Trabaja sobre una copia del SVG y da a cada `<mask>` una región amplia: los navegadores recortan por especificación las máscaras sin región a −10 %…120 % del lienzo e Inkscape no, y el degradado salía cortado en ángulo recto.
* Antes de eso convierte cada `<mask>` hecha solo de formas de un mismo color sólido en un `<clipPath>` y pone en el elemento enmascarado una opacidad igual a la luminancia de ese color (`_mascaras_solidas_a_clip`). Motivo: Edge/Chrome exportan las máscaras como una **imagen rasterizada** usada de máscara suave, y en el borde de esa imagen se colaba 1 px del contenido enmascarado. El sello mostraba una línea fina en el perímetro del lienzo del logotipo a zoom de pantalla. Los recortes se exportan como vector.
* Las pruebas `TestFondoFirma` comprueban que el PDF generado no tiene imágenes y que las esquinas y los bordes del lienzo salen en blanco puro a varios zooms.

### 2. Texto con el ancho del recuadro (`_text_layout`, `_arrange_lines`, `_render_inner_content`)
* El texto (Courier) se compone a 100 pt sin márgenes y se escala con `cm` para que **la línea más larga vaya exactamente de margen a margen del recuadro**; se centra en vertical dentro de los márgenes.
* **Margen interno** (`_text_area`): el 10 % del alto del recuadro, y nunca menos de 7 pt, en los cuatro lados (`TEXT_MARGIN_MIN`, `TEXT_MARGIN_RATIO`). Solo en recuadros diminutos se reduce para que quede sitio para el texto. El logotipo de fondo, en cambio, se escala por el **alto**.
* En recuadros anchos y bajos se unen líneas seguidas con « · » (se prueban todas las agrupaciones y se elige la que da la letra más grande), para que el alto no impida llegar al ancho.
* Si aun así no cabe en alto, se reduce **solo el alto** de las letras: el ancho sigue siendo el del recuadro y ninguna línea queda recortada.

### 3. Texto del Sello (`_build_stamp_text`)
El texto inyectado en el sello incluye la siguiente información estructurada:
```
[Nombre del Firmante]
NIF: [NIF del Firmante]
Repr.: [NIF de la Entidad Representada] (si existe)
Firmado: DD/MM/AAAA HH:MM:SS
```

---

## Extracción de Metadatos de Identidad

El método helper `extract_cert_info(pfx_path, pfx_password)` lee la estructura ASN.1 del certificado X.509 utilizando la biblioteca `cryptography`:
* **Nombre** (primera línea del sello): **solo nombre y apellidos**, calculado por `_signer_display_name`:
  * Si el certificado trae *givenName* y *surname* (`NameOID.GIVEN_NAME`, `NameOID.SURNAME`), se usan juntos: es lo más fiable y da los dos apellidos.
  * Si no, se limpia el *Common Name*: los certificados de representante de la FNMT lo traen como `DNI NOMBRE APELLIDO1 (R: CIF)` y los de persona física como `APELLIDOS NOMBRE - NIF DNI`. Se quitan el DNI/NIE inicial, el `(R: …)` final y el `- NIF …` final.
* **NIF del Firmante**: Extraído del atributo *SerialNumber* (`NameOID.SERIAL_NUMBER`). Si este contiene prefijos de países (por ejemplo, `IDCES-12345678A`), el método helper `_clean_id` limpia el prefijo para mostrar solo el NIF limpio.
* **NIF de la Entidad Representada**: Se extrae mediante el identificador de objeto específico (**OID 2.5.4.97** - *organizationIdentifier*), que almacena el código fiscal de la empresa u organismo representado en certificados de representación de personas jurídicas.

---

## Firma manuscrita (r68)

Además de la firma digital, la barra de Firma tiene el botón de la **plumilla**
para estampar una firma **manuscrita**: dibujada con el ratón o cargada desde
una imagen escaneada. Es solo la imagen de la firma, **sin valor
criptográfico**; si hace falta validez legal, se firma además digitalmente.

* **Dibujada** (`firma_manuscrita.py`): se imita una estilográfica. La plumilla
  está biselada a 40°, así que los trazos que la cruzan salen gruesos y los que
  van en su dirección, finos; ir despacio deja más tinta que ir deprisa, y al
  apoyar sale una pequeña gota. La tinta es translúcida y **cada trazo se pinta
  por separado**, de modo que donde dos trazos se cruzan la tinta se superpone y
  se oscurece, como en el papel (también en los bucles de un mismo trazo). Se
  eligen el color (la paleta de la aplicación) y el grosor de la plumilla.
* **Imagen** (`firma_manuscrita_ui.py`): PNG, JPG, BMP, GIF, TIFF o WebP. Por
  defecto el papel blanco se vuelve transparente y se recorta el margen.
* En el PDF es una anotación *Stamp* con apariencia propia (vectorial si se
  dibujó), igual que los emojis: se mueve, se redimensiona sin deformarse, se
  borra y se deshace. La última firma dibujada, su color y su grosor se
  recuerdan para la próxima vez.

## Relación con otros Documentos

Este fichero se relaciona directamente con:
* **[Arquitectura General (arquitectura.md)](arquitectura.md)**: Vista general del motor `pyHanko` y flujo criptográfico.
* **[Gestión de Certificados Digitales (gestion_certificados.md)](gestion_certificados.md)**: Origen de los datos del certificado PFX/P12 y la contraseña segura.
* **[Interfaz Gráfica y Visor (interfaz_grafica.md)](interfaz_grafica.md)**: El visor interactivo donde el usuario dibuja la caja de firma visible.
