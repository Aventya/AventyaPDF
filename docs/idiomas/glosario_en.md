# Glosario español → inglés (AventyaPDF)

Archivos: `idiomas/en.json` (841 textos) y `empaquetado/idiomas/instalador_en.json` (15 textos).

## Convenciones generales

| Aspecto | Decisión | Motivo |
|---|---|---|
| Variante | **Inglés británico (en-GB)**: *colour, grey, organise, recognise, optimise, centre, cancelled* | Es la variante de Microsoft para Europa y la del texto inglés de eIDAS. No mezclar con ortografía estadounidense. |
| Mayúsculas | Mayúscula solo al principio de la frase (*Save as*, *Document properties*), no en cada palabra | Norma actual de Windows 11 y Office |
| Contracciones | *Couldn't, can't, isn't, don't* en avisos y errores | Guía de estilo de Microsoft (tono cercano) |
| Errores | «No se pudo X» → **Couldn't X** | Coherencia en todos los avisos de error |
| Tratamiento | *you* + imperativo (*Select a certificate…*) | Como Windows |
| Comillas | « » → **“ ”** (comillas curvas) | Norma del inglés |
| Porcentajes | «100 %» → **100%** (sin espacio) | Norma del inglés |
| Puntos suspensivos | Se mantiene «…» en los comandos que abren un diálogo | Convención de Windows |
| Plural | Se usa el plural (*{n} pages*) cuando el texto solo aparece con varios elementos; cuando el código ya distingue el singular, también se traduce el singular (*1 emoji*, *image*) | |

## Barra de menús (letra del atajo)

| Español | Inglés |
|---|---|
| &Archivo | &File |
| &Edición | &Edit |
| &Ver | &View |
| &Comentar | &Comment |
| &Organizar | &Organise |
| &Herramientas | &Tools |
| &Proteger | &Protect |
| &Firmar | &Sign |
| A&yuda | &Help |

Las letras F, E, V, C, O, T, P, S y H no se repiten.

## Teclas

| Español | Inglés |
|---|---|
| Ctrl | Ctrl |
| Mayús | Shift |
| Supr | Del |
| AvPág / RePág | PgDn / PgUp |
| Inicio / Fin | Home / End |
| Intro | Enter |
| Esc | Esc |
| Rueda (del ratón) | Wheel / Mouse wheel |

## Windows y Office (terminología oficial de Microsoft)

| Español | Inglés |
|---|---|
| Explorador (de archivos) | File Explorer |
| Mostrar más opciones | Show more options |
| menú del botón derecho / menú contextual | right-click menu / context menu |
| Personas de confianza | Trusted People |
| Administrador de credenciales | Credential Manager |
| Administrar certificados de equipo | Manage computer certificates |
| almacén (de certificados) personal de Windows | Windows personal certificate store |
| Descargas (carpeta) | Downloads |
| equipo | computer |
| permiso de administrador | administrator permission |
| acceso directo / escritorio | shortcut / desktop |
| Buscar (en el documento) | Find |
| Buscar actualizaciones | Check for updates |
| Guardar como | Save as |
| Salir | Exit |
| Examinar… | Browse… |
| Aceptar / Cancelar | OK / Cancel |
| Acercar / Alejar | Zoom in / Zoom out |
| Tamaño real | Actual size |
| Ajustar al ancho / a la página | Fit width / Fit page |
| Negrita / Cursiva | Bold / Italic |
| Tipo de letra | Font |
| ppp (puntos por pulgada) | dpi |

## Firma electrónica (eIDAS y Adobe Acrobat)

| Español | Inglés | Motivo |
|---|---|---|
| firma digital | digital signature | Acrobat. Se usa en la interfaz para la firma con certificado. |
| firma electrónica avanzada | advanced electronic signature | eIDAS, art. 26 |
| certificado (cualificado) | (qualified) certificate | eIDAS |
| certificado de firma | signing certificate | Acrobat |
| firmar digitalmente | sign digitally | |
| sello de tiempo | time stamp | eIDAS usa *electronic time stamp* (dos palabras) |
| sello de tiempo cualificado | qualified time stamp | eIDAS (*qualified electronic time stamp*), abreviado por espacio |
| sellado de tiempo | time stamping | |
| autoridad de sellado de tiempo (TSA) | time-stamping authority (TSA) | Término de RFC 3161 / ETSI; Acrobat dice *Timestamp Authority* |
| certificar el documento / certificación | certify the document / certification | Acrobat (*certifying signature*) |
| firma manuscrita (dibujada) | handwritten signature (drawn) | |
| plumilla (de estilográfica) | (fountain pen) nib | |
| validar / validación | validate / validation | |
| verificar las firmas | verify the signatures | |
| documento alterado | document altered | |
| firma íntegra | signature intact | Acrobat: *the document has not been modified* |
| identidad no verificada | identity not verified | |
| de confianza | trusted | |
| lista de confianza (de España) | (Spanish) trusted list | eIDAS, art. 22 |
| datos de validación (LTV) | validation data (LTV) | |
| firmante | signer | Acrobat |
| recuadro de firma | signature box | Se prefirió a *signature field* para distinguirlo de «campo» (*field*), que también aparece en el mismo texto |
| clave privada | private key | |
| resumen (hash) para firmar | digest | Término criptográfico estándar |
| huella SHA-256 | SHA-256 hash | |
| proveedor criptográfico | cryptographic provider | Microsoft (CSP) |
| tarjeta (criptográfica) | smart card | |
| Firmas Certificadas (panel) | **Digital signatures** | *Certified signatures* se confundiría con la «certificación del documento» de Acrobat, que es otra cosa |

### Sello visible de la firma

| Español | Inglés | Motivo |
|---|---|---|
| Motivo: | Reason: | Acrobat |
| Lugar: | Location: | Acrobat |
| Firmado: %(ts)s | Signed: %(ts)s | |
| NIF: | Tax ID: | Equivalente funcional comprensible para un lector extranjero |
| Repr.: (NIF de la entidad representada) | On behalf of: | Indica la persona jurídica en cuyo nombre firma el representante |
| Fecha declarada | Claimed signing time | Hora del equipo del firmante, no verificada (frente al sello de tiempo) |
| Aprobación / Conformidad | Approval / Agreement | Motivos de firma predefinidos |
| He revisado este documento / Soy el autor de este documento | I have reviewed this document / I am the author of this document | Frases de Acrobat |

## Comentarios y anotaciones (Acrobat)

| Español | Inglés |
|---|---|
| anotación | annotation |
| comentario | comment |
| nota adhesiva | sticky note |
| resaltar / subrayar / tachar | highlight / underline / strike through |
| resaltado / subrayado / tachado (tipos) | Highlight / Underline / Strikethrough |
| ondulado / subrayado ondulado | Squiggly / Squiggly underline |
| a mano alzada | freehand |
| marca a mano alzada | freehand drawing |
| remarcar con rectángulo | outline with a rectangle |
| inserción (anotación) | text insertion |
| borrador | eraser |
| aplanar | flatten |
| marcador | bookmark |
| miniaturas | thumbnails |
| panel lateral | side panel |

## Páginas y documentos

| Español | Inglés | Motivo |
|---|---|---|
| combinar (archivos en un PDF) | combine | Acrobat (*Combine files*) |
| unir / añadir al final | append | Para la operación de añadir archivos al final del documento abierto |
| dividir | split | |
| extraer | extract | |
| girar | rotate | |
| recortar | crop | |
| duplicar | duplicate | |
| comprimir / optimizar | compress / optimise | |
| reducir la resolución (imágenes) | downsample | Término de Acrobat |
| marca de agua | watermark | |
| encabezado / pie | header / footer | |
| numeración Bates | Bates numbering | |
| reconocer texto (OCR) | recognise text (OCR) | Microsoft en-GB |
| contraseña de apertura | document open password | Acrobat |
| contraseña de permisos | permissions password | Acrobat |
| cifrado | encryption | |
| rellenar formularios | fill in forms | |
| presentación (de bienvenida) | tour | |
| publicación (en GitHub) | release | |

Los marcadores que escribe el usuario en encabezado y pie se dejan como en el programa: `{n}`, `{total}`, `{fecha}`, `{bates}`.

## Erratas del original

No se han encontrado erratas en el texto español. Observación (no es errata): «Firmas Certificadas» lleva mayúscula en la segunda palabra, a diferencia del resto de la interfaz; en inglés se ha puesto *Digital signatures* (ver arriba).

## Añadidos con el manual (r138)

| Español | Inglés | Motivo |
|---|---|---|
| Manual de AventyaPDF | AventyaPDF manual | Mismo patrón que *AventyaPDF tour* (sentence case) |
| Quitar seguridad | Remove security | Acrobat (*Remove Security*) |
| Quitar firma | Remove signature | |
| libre distribución | freely distributed | |
| firmador (de PDF) | signing tool | *Signer* es la persona que firma (ver «firmante») |
| Moverse (por el documento) | navigate | |
| Consejo / Importante (recuadros) | Tip / Important | Microsoft |
| Tecla / Acción (tabla de atajos) | Key / Action | |
| Inicio (menú de Windows) | Start menu | Microsoft |
| Abrir con › Elegir otra aplicación | Open with › Choose another app | Windows 11 |
| Usar siempre esta aplicación | Always use this app to open .pdf files | Windows 10/11 |
| Abrir \| Abrir con \| Compartir (menú del botón derecho) | Open \| Open with \| Share | Windows 11 |
| Ctrl+rueda | Ctrl+Wheel | Como en la tabla de atajos |
| herramientas de comentario | commenting tools | Acrobat |
| prestadores cualificados (de servicios de confianza) | qualified trust service providers | eIDAS, art. 3 |
| papelera (icono) | bin | en-GB |
| documentos de la Administración | government forms | |
| DNIe | DNIe (Spanish electronic ID card) | Se explica la primera vez en el manual |
| CONFIDENCIAL (marca de agua por defecto) | CONFIDENTIAL | |
| _firmado (sufijo del archivo firmado) | _signed | «Contract.pdf» → «Contract_signed.pdf» |
