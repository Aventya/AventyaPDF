---
titulo: Manual de AventyaPDF
subtitulo: Ver, comentar, organizar, protexer, converter e asinar documentos PDF
version: Versión {version}
indice: Índice
meses: xaneiro|febreiro|marzo|abril|maio|xuño|xullo|agosto|setembro|outubro|novembro|decembro
fecha: {mes} de {anio}
cabecera: Manual de AventyaPDF
consejo: Consello
importante: Importante
atajos_tecla: Tecla
atajos_accion: Acción
muestra_titulo: Documento de mostra — páxina {n}
muestra_texto: Este é un documento de mostra creado unicamente para ensinar as ferramentas de AventyaPDF no manual. Non contén ningún dato real nin de ningún cliente.\n\nAventyaPDF é unha aplicación de escritorio para Windows que permite ver, comentar, organizar, protexer, converter e asinar dixitalmente documentos PDF.\n\nEste parágrafo serve para probar as ferramentas de comentario: realzar texto, subliñalo, riscalo, seleccionalo e copialo, ou engadir notas adhesivas xunto a el.
buscar: documento
resaltar: ferramentas de comentario
texto_anotacion: Texto engadido sobre a páxina
nota_texto: Revisar este parágrafo antes de envialo.
formulario_titulo: Solicitude de mostra
campo_nombre: Nome e apelidos
campo_fecha: Data
campo_importe: Importe
casilla: Acepto as condicións
firmante: Persoa de Exemplo
motivo: Conformidade
lugar: Cidade
contacto: correo@exemplo.gal
certificado_ejemplo: Certificado de exemplo
nombre_doc1: Contrato.pdf
nombre_doc2: Factura.pdf
nombre_doc3: Informe.pdf
nombre_formulario: Solicitude.pdf
nombre_firmado: Contrato asinado.pdf
explorador_opciones: Abrir|Abrir con|Compartir
---

# Primeiros pasos

## Que é AventyaPDF

AventyaPDF é unha aplicación para Windows que reúne nun só programa o que se fai a diario cos documentos PDF: lelos, comentalos, encher formularios, cambiar o seu texto, organizar as súas páxinas, combinalos, protexelos con contrasinal, recoñecer o texto das dixitalizacións e asinalos con certificado dixital.

É de libre distribución e o seu código está publicado en GitHub. Non envía os teus documentos a ningures: todo se fai no teu equipo.

![ventana] A xanela de AventyaPDF con tres documentos abertos.

## Instalar e actualizar

O instalador pregunta primeiro o idioma (propón o de Windows): con ese idioma instálase e ábrese AventyaPDF. Durante a instalación descárganse dos seus sitios web oficiais Python, os seus compoñentes e as fontes de letra, así que cómpre ter conexión a Internet. Mentres tanto, o instalador vai ensinando as ferramentas da aplicación.

Ao rematar, AventyaPDF aparece no menú Inicio (e, se o marcaches, no escritorio) e en **Abrir con** dos ficheiros PDF. Windows non deixa que un programa se poña el mesmo como visor predeterminado: se queres que os PDF se abran sempre con AventyaPDF, escólleo en **Abrir con › Escoller outra aplicación** e marca «Usar sempre esta aplicación».

Cando hai unha versión nova, AventyaPDF avísao ao iniciar. Tamén podes comprobalo en **Axuda › Buscar actualizacións…**: o instalador novo descárgase no teu cartafol Descargas e só tes que abrilo. A túa configuración, o teu certificado e o teu idioma mantéñense.

> **Importante:** o recoñecemento de texto (OCR) usa Tesseract OCR, que non vai dentro do instalador. AventyaPDF descárgao e instálao a primeira vez que o usas; pode pedir permiso de administrador.

## A xanela

- **Barra de menús**: todas as funcións, ordenadas en Ficheiro, Edición, Ver, Comentar, Organizar, Ferramentas, Protexer, Asinar e Axuda.
- **Barra de ferramentas**: abrir, gardar, imprimir e comprimir; desfacer e refacer; a páxina actual; o axuste do zoom; as ferramentas de comentario e de edición; a sinatura; as operacións de páxina e, á dereita, a lupa para buscar.
- **Panel lateral** (á esquerda, ábrese e péchase con **F4**): miniaturas de páxina, marcadores, comentarios e sinaturas certificadas. Na parte superior do panel aparecen as opcións da ferramenta que esteas a usar.
- **Barra de estado** (abaixo): mensaxes da aplicación e, á dereita, o zoom.

## Presentación, axuda e idioma

Ao abrir AventyaPDF por primeira vez sae unha presentación que resume as funcións. Marca «Non volver mostrar ao iniciar» se non queres vela máis; sempre podes volver abrila desde **Axuda › Presentación de AventyaPDF**.

![presentacion] A presentación de inicio.

No menú **Axuda** tes tamén este manual (**Axuda › Manual de AventyaPDF**), a lista de atallos de teclado (**F1**) e o idioma da aplicación (**Axuda › Idioma**). AventyaPDF está en español, inglés, francés, italiano, catalán, galego e éuscaro; o idioma novo aplícase a próxima vez que abras a aplicación.

![idioma] Axuda › Idioma.

# Abrir, gardar e moverse polo documento

## Abrir documentos

Hai varias formas de abrir documentos:

- **Ficheiro › Abrir…** (`Ctrl+O`): podes escoller varios ficheiros á vez con `Ctrl` ou `Maiús`.
- Arrastralos desde o Explorador de ficheiros á xanela.
- **Ficheiro › Abrir recente**, cos últimos documentos usados.
- Facer dobre clic nun PDF, se AventyaPDF é o teu visor de PDF.

Ademais de PDF, AventyaPDF abre imaxes (PNG, JPG, BMP, GIF, TIFF e WebP) e documentos de Word (.doc e .docx): cada un convértese nun PDF novo, sen gardar, na súa propia lapela. O orixinal non se toca. Para converter documentos de Word cómpre ter instalado Microsoft Word ou LibreOffice.

Se o PDF está protexido con contrasinal, AventyaPDF pídeo antes de abrilo.

## Varios documentos á vez

Cada documento aberto ten a súa lapela no panel lateral, debaixo das iconas dos paneis. Ao pasar o rato por riba vese o seu nome e o seu cartafol, e un punto «●» indica que ten cambios sen gardar.

![pestanas] As lapelas dos documentos abertos, no panel lateral.

- Fai clic nunha lapela para ir a ese documento, ou usa `Ctrl+Tab` e `Ctrl+Maiús+Tab`.
- Arrastra unha lapela cara arriba ou cara abaixo para cambiar a orde.
- Co botón dereito sobre unha lapela podes pechar ese documento (ou usa `Ctrl+W`).

Cada documento conserva a súa páxina, os seus cambios e o seu historial de desfacer. Se abres un ficheiro que xa estaba aberto, AventyaPDF só cambia á súa lapela.

## Moverse polas páxinas e o zoom

- `AvPáx` e `RePáx` pasan de páxina; `Inicio` e `Fin` van á primeira e á última. A roda do rato tamén pasa de páxina ao chegar ao bordo.
- Escribe un número na caixa de páxina da barra de ferramentas, ou usa **Ver › Ir á páxina…** (`Ctrl+G`).
- Fai clic nunha miniatura do panel lateral para ir a esa páxina. O panel de marcadores mostra o índice do documento, se o ten.

O zoom está sempre abaixo á dereita: os botóns de lupa amplían e reducen, a barra arrástrase e na caixa pódese escribir a porcentaxe exacta (ata o 400 %). Tamén funcionan `Ctrl+roda`, `Ctrl++` e `Ctrl+-`. O botón de axuste da barra de ferramentas alterna entre axustar á largura (`Ctrl+1`), axustar á páxina (`Ctrl+2`) e o tamaño real (`Ctrl+0`).

![zoom] O zoom, na barra de estado.

## Buscar e copiar texto

Preme `Ctrl+F` ou a lupa da barra de ferramentas e escribe o que buscas: as coincidencias aparecen realzadas na páxina segundo escribes e cóntanse («1 de 12»). As frechas, `F3` e `Maiús+F3` van á seguinte e á anterior; `Esc` pecha a busca.

![buscar] Buscar no documento.

Para copiar, arrastra o rato sobre o texto coa ferramenta de selección e preme `Ctrl+C`. Cada parágrafo pégase nunha soa liña, sen os saltos de liña do PDF; tamén o texto recoñecido con OCR.

## Gardar, imprimir e propiedades

- **Ficheiro › Gardar** (`Ctrl+S`) garda sobre o mesmo ficheiro; **Gardar como…** (`Ctrl+Maiús+S`), con outro nome. O título da xanela leva «●» mentres haxa cambios sen gardar, e ao pechar pregúntase se queres gardalos.
- **Ficheiro › Imprimir…** (`Ctrl+P`) abre o diálogo de impresión de Windows.
- **Ficheiro › Propiedades do documento…** (`Ctrl+D`) mostra e permite cambiar o título, o autor, o asunto e as palabras clave, e na lapela Información, datos como o número de páxinas, o tamaño ou se ten sinaturas.

![propiedades] Propiedades do documento.

## Desfacer e refacer

Case todo o que fas nun documento pódese desfacer con `Ctrl+Z` e refacer con `Ctrl+Y`: comentarios, cambios de texto, operacións de páxina, marcas de auga, OCR… Cada documento ten o seu propio historial.

# Comentar

As ferramentas de comentario están no menú **Comentar** e na barra de ferramentas. Cada unha ten unha letra para escollela rapidamente; `V` ou `Esc` volven á ferramenta de selección. As opcións da ferramenta (cor, tamaño, grosor…) aparecen na parte superior do panel lateral.

## Engadir texto

Coa ferramenta **Engadir texto** (`T`) fai clic na páxina (ou arrastra unha caixa) e escribe directamente enriba, sen xanelas: a caixa medra segundo escribes. No panel lateral escolles o tamaño, a cor, a negra e a cursiva, o aliñamento e o tipo de letra, e os cambios vense ao momento.

![texto] Texto escrito directamente sobre a páxina.

`Intro` abre unha liña nova, `Ctrl+Intro` confirma e `Esc` cancela. Facer clic noutro sitio tamén confirma. Para cambiar un texto xa posto, fai dobre clic sobre el.

## Notas adhesivas

A **Nota adhesiva** (`N`) deixa un comentario xunto á páxina: fai clic onde queiras deixala e escribe. Na páxina vese unha pequena icona, e o texto aparece ao pasar o rato por riba. A cor da nota escóllese no panel lateral.

![nota] Unha nota adhesiva xunto ao texto.

## Realzar, subliñar e riscar

Con **Realzar, subliñar ou riscar** (`H`) escolle o tipo de marca e a súa cor no panel lateral e arrastra sobre o texto. Se o texto non se pode seleccionar (unha imaxe ou unha dixitalización), a marca debúxase a man alzada; un trazo rápido sae recto.

![resaltar] Texto realzado.

> **Consello:** tamén podes seleccionar texto coa ferramenta de selección e premer o botón dereito para realzalo, subliñalo ou riscalo.

## Rectángulos e emojis

O **Rectángulo** (`R`) remarca unha zona da páxina cun recadro de esquinas redondeadas: arrastra para debuxalo, coa cor e o grosor do panel lateral.

![rectangulo] Un rectángulo arredor do título.

A ferramenta **Emoji** (`E`) insire calquera dos máis de 1.300 emojis, con buscador e grupos, no tamaño, a cor e a opacidade que queiras: escolle un e fai clic onde irá.

![emoji] Escoller un emoji.

## Mover, cambiar e borrar comentarios

Coa ferramenta de selección, fai clic nun comentario para seleccionalo: pódese mover arrastrándoo, cambiar de tamaño cos seus tiradores e borrar con `Supr`. O **Borrador de anotacións** quita os comentarios cun clic.

O panel **Comentarios** do panel lateral lista todos os comentarios do documento coa súa páxina; ao premer nun, a páxina vai a el e queda seleccionado.

![comentarios] O panel Comentarios.

## Aplanar

**Comentar › Aplanar anotacións e formularios…** converte os comentarios e os campos de formulario en parte do contido da páxina: vense igual, pero xa non se poden mover nin editar. É útil antes de enviar unha versión definitiva.

# Editar o contido do PDF

A ferramenta **Editar texto e imaxes do PDF** (`C`, no menú Ferramentas) cambia o texto e as imaxes que xa forman parte do documento, non comentarios por riba. Ao escollela, cada parágrafo enmárcase en azul e cada imaxe en verde.

![editar] Os parágrafos e as imaxes editables, enmarcados.

**Texto.** Fai clic nun parágrafo e escribe: o texto repártese nas liñas que fagan falta dentro da súa caixa, coa mesma fonte, tamaño e cor sempre que é posible. No panel lateral podes cambiar o tamaño, a cor e a negra ou cursiva. Se o texto non cabe, a caixa ponse vermella: estira unha das súas esquinas para facela máis grande. `Ctrl+Intro` confirma, `Esc` cancela e `Tab` pasa ao parágrafo seguinte. Deixar un parágrafo baleiro bórrao.

**Imaxes.** Fai clic nunha imaxe para seleccionala: arrástraa para movela, estira unha esquina para cambiar o seu tamaño (sen deformala) ou preme `Supr` para borrala. Co botón dereito podes substituíla por outra imaxe ou gardala nun ficheiro.

> **Importante:** se o documento usa unha fonte que non está dispoñible, AventyaPDF usa a máis parecida e avísao na barra de estado. Revisa o resultado antes de gardar.

# Encher formularios

Os campos dos formularios aparecen realzados en azul (podes quitalo en **Ver › Realzar campos de formulario**). Non fai falta ningunha ferramenta especial:

- Fai clic nun campo de texto e escribe; `Tab` pasa ao campo seguinte e `Maiús+Tab` ao anterior.
- As caixas de verificación e os botóns de opción márcanse cun clic; as listas despregan os seus valores.
- Os cálculos, as validacións e os botóns do formulario funcionan como en Adobe Acrobat.

![formulario] Un formulario cos seus campos realzados.

Se o formulario ten un recadro de sinatura baleiro, fai clic nel para asinar dentro (verás como no capítulo de sinatura).

# Organizar páxinas

## Operacións de páxina

O botón **Operacións de páxina** da barra de ferramentas (ou **Organizar › Organizar páxinas no panel lateral**) abre as miniaturas en modo organizar, cunha fila de botóns enriba.

![organizar] As operacións de páxina no panel lateral.

- **Reordenar**: arrastra unha miniatura á súa nova posición.
- **Seleccionar varias**: con `Ctrl` ou `Maiús` ao facer clic. Sen selección, os botóns actúan sobre a páxina actual.
- **Botóns**: xirar á esquerda e á dereita, duplicar, eliminar, inserir unha páxina en branco, inserir outro PDF, extraer as páxinas a un PDF novo e recortar.

Todo se aplica ao momento e pódese desfacer.

## Recortar unha páxina

O botón **Recortar** debuxa sobre a páxina un recadro con tiradores nas esquinas e nos lados: arrastra cada un ata a marxe que queiras. Os botóns do centro do recadro aplican ou cancelan o recorte.

![recortar] Recortar unha páxina.

## O menú Organizar

No menú **Organizar** están tamén:

- **Inserir páxina en branco**, **Inserir PDF despois da páxina actual…** e **Engadir PDF ao final…**
- **Duplicar páxina actual**, **Eliminar páxinas…** e **Extraer páxinas…**, con intervalos como «1-3, 5, 8-».
- **Dividir documento…**: garda o documento en partes dun número fixo de páxinas.
- **Xirar páxina á dereita** (`Ctrl+Maiús+R`), **á esquerda** (`Ctrl+Maiús+L`) e **Xirar páxinas…** por intervalos.

## Combinar documentos

**Organizar › Combinar PDF…** ten dúas opcións:

- **Combinar abertos**: xunta todos os documentos abertos, na orde das súas lapelas e cos seus cambios, nun PDF novo.
- **Combinar ficheiros…**: escolles varios ficheiros (PDF, imaxes ou Word, mesturados) e combínanse por orde alfabética do nome.

![combinar] Organizar › Combinar PDF.

O resultado queda aberto sen gardar; gárdao con `Ctrl+S`. Os ficheiros orixinais non cambian.

# Crear, converter e exportar

## Crear documentos

- **Ficheiro › Novo PDF en branco** (`Ctrl+N`) crea un documento cunha páxina baleira.
- **Ficheiro › Crear PDF desde imaxes…** xunta varias imaxes nun PDF, unha por páxina.
- Abrir unha imaxe ou un documento de Word convérteo a PDF (consulta «Abrir documentos»).

## Exportar

En **Ficheiro › Exportar** podes sacar o contido do documento:

- **Páxinas como imaxes…**: PNG ou JPG, coa resolución que escollas.
- **Texto (.txt)…**: todo o texto do documento.
- **Documento de Word (.docx)…**: un documento editable en Word.
- **Extraer páxinas a PDF…**: só as páxinas que indiques.

![exportar] Exportar páxinas como imaxes.

## Desde o Explorador de ficheiros

Sen abrir antes a aplicación, selecciona ficheiros no Explorador de ficheiros e preme o botón dereito: no submenú **AventyaPDF** tes:

- **Asinar dixitalmente** (só PDF): abre os documentos coa ferramenta de sinatura preparada.
- **Combinar nun PDF** (dous ou máis ficheiros): PDF, imaxes e Word, mesturados, nun só PDF.
- **Converter a PDF** (imaxes e Word): un PDF por ficheiro.

![explorador] O submenú AventyaPDF do botón dereito.

En Windows 11, o submenú está no menú principal do botón dereito; en Windows 10, e en Windows 11 dentro de **Mostrar máis opcións**, está no menú clásico.

> **Consello:** se o submenú desaparece (por exemplo, despois dunha actualización de Windows), usa **Axuda › Reparar o menú contextual do Explorador de ficheiros…**

# Ferramentas

## Marca de auga

**Ferramentas › Marca de auga…** escribe un texto sobre as páxinas que escollas, co tamaño, a cor, a opacidade e o ángulo que queiras (por exemplo, «CONFIDENCIAL» en diagonal).

![marca_agua] Marca de auga.

## Cabeceira, pé e numeración Bates

**Ferramentas › Cabeceira, pé e numeración Bates…** engade ata tres textos na cabeceira e tres no pé (esquerda, centro e dereita). Podes usar variables:

- `{n}`: o número de páxina; `{total}`: o número total de páxinas.
- `{fecha}`: a data de hoxe.
- `{bates}`: un número correlativo Bates, con prefixo, número inicial e díxitos.

![encabezado] Cabeceira, pé e numeración Bates.

## Recoñecer texto (OCR)

**Ferramentas › Recoñecer texto (OCR)…** converte en texto seleccionable e que se pode buscar o das páxinas dixitalizadas, as fotos e as imaxes. Escolle o idioma do documento, se se recoñecen todas as páxinas ou só as que non teñen texto, e se se corrixe a orientación de cada páxina.

![ocr] Recoñecer texto (OCR).

O texto engádese como unha capa invisible: a páxina non cambia de aspecto, pero xa se pode buscar, seleccionar e copiar. Se escolles un idioma novo, AventyaPDF descarga antes os seus datos.

## Optimizar e comprimir

O botón **Comprimir PDF** da barra de ferramentas (ou **Ferramentas › Optimizar e comprimir…**) reduce o tamaño do ficheiro, sobre todo cando ten imaxes. Escolle o nivel (alta calidade, boa calidade ou máxima redución) e garda a copia comprimida; o orixinal non cambia.

![comprimir] As opcións de compresión.

# Protexer con contrasinal

**Protexer › Protexer con contrasinal…** cifra o documento con AES de 256 bits:

- **Contrasinal para abrir o documento**: sen el non se pode abrir.
- **Contrasinal de permisos**: restrinxe imprimir, copiar, modificar ou comentar, aínda que se poida abrir sen contrasinal.

![proteger] Protexer con contrasinal.

A protección aplícase ao gardar. **Protexer › Quitar seguridade** quita o contrasinal e os permisos dun documento que abriches co seu contrasinal.

> **Importante:** se esqueces o contrasinal para abrir, non hai forma de recuperar o documento. Gárdao nun lugar seguro.

# Asinar

AventyaPDF asina con sinatura electrónica avanzada PAdES, a que se usa nos documentos oficiais europeos, con certificados cualificados como os da FNMT ou o DNIe.

## O certificado

En **Asinar › Certificado de sinatura…** escolles con que certificado se asina:

- **Almacén de Windows**: os certificados instalados no teu equipo, tamén os de tarxetas e do DNIe. A clave nunca sae do almacén; se fai falta un PIN, pídeo Windows.
- **Ficheiro .pfx / .p12**: un certificado gardado nun ficheiro. O contrasinal pódese gardar no Administrador de credenciais de Windows para non escribilo cada vez.

O certificado escollido lémbrase para as sinaturas seguintes.

## Asinar un documento

Escolle a ferramenta **Sinatura** (ou **Asinar › Asinar documento (debuxar área)**) e debuxa na páxina o recadro onde irá a sinatura visible. No panel lateral vese o certificado activo e pódese cambiar.

![firmar] A ferramenta de sinatura, co certificado activo.

Despois saen as **opcións de sinatura**, e por último AventyaPDF pide onde gardar o documento asinado (propón o mesmo nome rematado en «_asinado»). O orixinal non se modifica.

![opciones_firma] Opcións de sinatura.

- **Motivo, lugar e contacto**: aparecen no selo visible e nos datos da sinatura. O selo sae no idioma da aplicación.
- **Engadir selo de tempo cualificado (PAdES-B-T)**: unha autoridade de selado de tempo certifica a data e a hora da sinatura. Necesita Internet.
- **Certificar o documento**: despois de asinar, só se poderán encher formularios e engadir máis sinaturas; calquera outro cambio invalidará a certificación.
- **Non volver preguntar**: asina directamente con estas opcións (pódese cambiar en **Asinar › Opcións de sinatura…**).

Un documento pódese asinar varias veces: cada sinatura nova engádese sen invalidar as anteriores, sempre que non se fixesen cambios entre elas.

## Asinar no recadro dun formulario

Se o documento ten un recadro de sinatura baleiro (como moitos impresos da Administración), fai clic nel: AventyaPDF pide o certificado e asina dentro dese recadro.

## Sinatura manuscrita

**Asinar › Inserir sinatura manuscrita (debuxada ou imaxe)…**, ou a pluma do panel de sinatura, abre un lenzo onde debuxar a túa sinatura co rato, con trazo de estilográfica e a cor e o grosor que queiras. Tamén podes cargar a imaxe da túa sinatura dixitalizada (quítase o fondo branco do papel).

![manuscrita] Debuxar a sinatura manuscrita.

Despois fai clic na páxina para colocala, ou arrastra un recadro para darlle tamaño. Queda como un comentario máis: móvese, cámbiase de tamaño e bórrase.

> **Importante:** a sinatura manuscrita é só unha imaxe. Non ten valor de sinatura electrónica; para iso, asina con certificado.

## Verificar as sinaturas

O panel **Sinaturas certificadas** do panel lateral (ou **Asinar › Ver as sinaturas (verificadas)**) comproba automaticamente cada sinatura do documento:

- se o documento se alterou despois de asinalo;
- se o certificado é de confianza, segundo o almacén de Windows e a lista de confianza oficial de España (FNMT, DNIe, Colexio de Rexistradores, Izenpe, ACCV e o resto de prestadores cualificados);
- a data declarada, o selo de tempo e se hai cambios posteriores.

![firmas] O panel Sinaturas certificadas.

A sinatura máis recente ten unha papeleira que a quita e deixa o seu recadro baleiro para volver asinar (por exemplo, con outro certificado). O cambio aplícase ao gardar.

# Atallos de teclado

**Axuda › Atallos de teclado** (`F1`) mostra esta mesma lista dentro da aplicación.

[[atajos]]

# Se algo non funciona

## O OCR non está dispoñible

Tesseract OCR instálase a primeira vez que recoñeces texto e necesita Internet (e, ás veces, permiso de administrador). Se se denegou o permiso ou non había conexión, AventyaPDF volve intentalo a próxima vez que o abras.

## Non aparece o submenú AventyaPDF no Explorador de ficheiros

Usa **Axuda › Reparar o menú contextual do Explorador de ficheiros…**. En Windows 11, para que o submenú estea no menú principal, o instalador pide unha vez permiso de administrador; se se denegou, o submenú está en **Mostrar máis opcións**.

## Un documento de Word non se converte

Cómpre ter instalado Microsoft Word ou LibreOffice. Se os dous fallan, AventyaPDF mostra o motivo.

## Unha sinatura sae como «identidade non verificada»

A sinatura non se alterou, pero o seu certificado non está no almacén de Windows nin na lista de confianza de España (por exemplo, un certificado de probas ou doutro país). Comproba co asinante de onde é o seu certificado.

## Informar dun fallo

Se aparece unha xanela de «Erro inesperado», a aplicación segue aberta e o detalle gárdase no cartafol `%LOCALAPPDATA%\aventyapdf` (ficheiros `errores.log` e `fallos_graves.log`). Envía eses ficheiros cunha descrición do que estabas a facer en github.com/Aventya/AventyaPDF/issues.
