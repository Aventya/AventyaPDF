---
titulo: Manual d'AventyaPDF
subtitulo: Visualitzar, comentar, organitzar, protegir, convertir i signar documents PDF
version: Versió {version}
indice: Índex
meses: gener|febrer|març|abril|maig|juny|juliol|agost|setembre|octubre|novembre|desembre
fecha: {mes} de {anio}
cabecera: Manual d'AventyaPDF
consejo: Consell
importante: Important
atajos_tecla: Tecla
atajos_accion: Acció
muestra_titulo: Document de mostra — pàgina {n}
muestra_texto: Aquest és un document de mostra creat únicament per mostrar les eines d'AventyaPDF al manual. No conté cap dada real ni de cap client.\n\nAventyaPDF és una aplicació d'escriptori per a Windows que permet visualitzar, comentar, organitzar, protegir, convertir i signar digitalment documents PDF.\n\nAquest paràgraf serveix per provar les eines de comentari: ressaltar text, subratllar-lo, ratllar-lo, seleccionar-lo i copiar-lo, o afegir-hi notes adhesives al costat.
buscar: document
resaltar: eines de comentari
texto_anotacion: Text afegit sobre la pàgina
nota_texto: Reviseu aquest paràgraf abans d'enviar-lo.
formulario_titulo: Sol·licitud de mostra
campo_nombre: Nom i cognoms
campo_fecha: Data
campo_importe: Import
casilla: Accepto les condicions
firmante: Persona d'Exemple
motivo: Conformitat
lugar: Ciutat
contacto: correu@exemple.cat
certificado_ejemplo: Certificat d'exemple
nombre_doc1: Contracte.pdf
nombre_doc2: Factura.pdf
nombre_doc3: Informe.pdf
nombre_formulario: Sol·licitud.pdf
nombre_firmado: Contracte signat.pdf
explorador_opciones: Obre|Obre amb|Comparteix
---

# Primers passos

## Què és AventyaPDF

AventyaPDF és una aplicació per a Windows que reuneix en un sol programa el que es fa cada dia amb els documents PDF: llegir-los, comentar-los, emplenar formularis, canviar-ne el text, organitzar-ne les pàgines, combinar-los, protegir-los amb contrasenya, reconèixer el text dels documents escanejats i signar-los amb certificat digital.

És de lliure distribució i el seu codi està publicat a GitHub. No envia els vostres documents enlloc: tot es fa al vostre ordinador.

![ventana] La finestra d'AventyaPDF amb tres documents oberts.

## Instal·lar i actualitzar

L'instal·lador pregunta primer l'idioma (proposa el de Windows): AventyaPDF s'instal·la i s'obre en aquest idioma. Durant la instal·lació es baixen dels seus llocs web oficials Python, els seus components i els tipus de lletra, de manera que cal connexió a Internet. Mentrestant, l'instal·lador va mostrant les eines de l'aplicació.

En acabar, AventyaPDF apareix al menú Inicia (i, si ho heu marcat, a l'escriptori) i a **Obre amb** dels fitxers PDF. Windows no permet que un programa es defineixi tot sol com a visualitzador predeterminat: si voleu que els PDF s'obrin sempre amb AventyaPDF, trieu-lo a **Obre amb › Tria una altra aplicació** i marqueu «Utilitza sempre aquesta aplicació».

Quan hi ha una versió nova, AventyaPDF ho avisa en iniciar-se. També ho podeu comprovar a **Ajuda › Cerca actualitzacions…**: l'instal·lador nou es baixa a la carpeta Baixades i només l'heu d'obrir. Es mantenen la configuració, el certificat i l'idioma.

> **Important:** el reconeixement de text (OCR) utilitza Tesseract OCR, que no s'inclou a l'instal·lador. AventyaPDF el baixa i l'instal·la la primera vegada que l'utilitzeu; pot demanar permís d'administrador.

## La finestra

- **Barra de menús**: totes les funcions, ordenades a Fitxer, Edita, Visualitza, Comenta, Organitza, Eines, Protegeix, Signa i Ajuda.
- **Barra d'eines**: obrir, desar, imprimir i comprimir; desfer i refer; la pàgina actual; l'ajust del zoom; les eines de comentari i d'edició; la signatura; les operacions de pàgina i, a la dreta, la lupa per cercar.
- **Tauler lateral** (a l'esquerra, s'obre i es tanca amb **F4**): miniatures de pàgina, marcadors, comentaris i signatures certificades. A la part superior del tauler hi apareixen les opcions de l'eina que utilitzeu.
- **Barra d'estat** (a baix): missatges de l'aplicació i, a la dreta, el zoom.

## Presentació, ajuda i idioma

La primera vegada que obriu AventyaPDF apareix una presentació que en resumeix les funcions. Marqueu «No ho tornis a mostrar en iniciar» si no la voleu veure més; sempre la podeu tornar a obrir des d'**Ajuda › Presentació d'AventyaPDF**.

![presentacion] La presentació inicial.

Al menú **Ajuda** també hi teniu aquest manual (**Ajuda › Manual d'AventyaPDF**), la llista de dreceres de teclat (**F1**) i l'idioma de l'aplicació (**Ajuda › Idioma**). AventyaPDF està en castellà, anglès, francès, italià, català, gallec i basc; l'idioma nou s'aplica la propera vegada que obriu l'aplicació.

![idioma] Ajuda › Idioma.

# Obrir, desar i moure's pel document

## Obrir documents

Hi ha diverses maneres d'obrir documents:

- **Fitxer › Obre…** (`Ctrl+O`): podeu triar diversos fitxers alhora amb `Ctrl` o `Maj`.
- Arrossegar-los des de l'Explorador de fitxers fins a la finestra.
- **Fitxer › Obre un fitxer recent**, amb els últims documents utilitzats.
- Fer doble clic en un PDF, si AventyaPDF és el vostre visualitzador de PDF.

A més de PDF, AventyaPDF obre imatges (PNG, JPG, BMP, GIF, TIFF i WebP) i documents de Word (.doc i .docx): cada un es converteix en un PDF nou, sense desar, a la seva pròpia pestanya. L'original no es modifica. Per convertir documents de Word cal tenir instal·lat Microsoft Word o LibreOffice.

Si el PDF està protegit amb contrasenya, AventyaPDF la demana abans d'obrir-lo.

## Diversos documents alhora

Cada document obert té la seva pestanya al tauler lateral, a sota de les icones dels taulers. En passar-hi el ratolí per sobre se'n veu el nom i la carpeta, i un punt «●» indica que té canvis sense desar.

![pestanas] Les pestanyes dels documents oberts, al tauler lateral.

- Feu clic en una pestanya per anar a aquell document, o utilitzeu `Ctrl+Tab` i `Ctrl+Maj+Tab`.
- Arrossegueu una pestanya amunt o avall per canviar-ne l'ordre.
- Amb el botó dret sobre una pestanya podeu tancar aquell document (o utilitzeu `Ctrl+W`).

Cada document conserva la seva pàgina, els seus canvis i el seu historial de desfer. Si obriu un fitxer que ja estava obert, AventyaPDF només canvia a la seva pestanya.

## Moure's per les pàgines i el zoom

- `AvPàg` i `RePàg` canvien de pàgina; `Inici` i `Fi` van a la primera i a l'última. La roda del ratolí també canvia de pàgina en arribar a la vora.
- Escriviu un número al quadre de pàgina de la barra d'eines, o utilitzeu **Visualitza › Ves a la pàgina…** (`Ctrl+G`).
- Feu clic en una miniatura del tauler lateral per anar a aquella pàgina. El tauler de marcadors mostra l'índex del document, si en té.

El zoom sempre és a baix a la dreta: els botons de lupa apropen i allunyen, la barra es pot arrossegar i al quadre es pot escriure el percentatge exacte (fins al 400 %). També funcionen `Ctrl+roda`, `Ctrl++` i `Ctrl+-`. El botó d'ajust de la barra d'eines alterna entre ajustar a l'amplada (`Ctrl+1`), ajustar a la pàgina (`Ctrl+2`) i la mida real (`Ctrl+0`).

![zoom] El zoom, a la barra d'estat.

## Cercar i copiar text

Premeu `Ctrl+F` o la lupa de la barra d'eines i escriviu el que cerqueu: les coincidències es ressalten a la pàgina a mesura que escriviu i es compten («1 de 12»). Les fletxes, `F3` i `Maj+F3` van a la següent i a l'anterior; `Esc` tanca la cerca.

![buscar] Cercar al document.

Per copiar, arrossegueu el ratolí sobre el text amb l'eina de selecció i premeu `Ctrl+C`. Cada paràgraf s'enganxa en una sola línia, sense els salts de línia del PDF; també el text reconegut amb OCR.

## Desar, imprimir i propietats

- **Fitxer › Desa** (`Ctrl+S`) desa sobre el mateix fitxer; **Desa com a…** (`Ctrl+Maj+S`), amb un altre nom. El títol de la finestra porta «●» mentre hi hagi canvis sense desar, i en tancar es pregunta si els voleu desar.
- **Fitxer › Imprimeix…** (`Ctrl+P`) obre el diàleg d'impressió de Windows.
- **Fitxer › Propietats del document…** (`Ctrl+D`) mostra i permet canviar el títol, l'autor, l'assumpte i les paraules clau, i a la pestanya Informació, dades com el nombre de pàgines, la mida o si té signatures.

![propiedades] Propietats del document.

## Desfer i refer

Gairebé tot el que feu en un document es pot desfer amb `Ctrl+Z` i refer amb `Ctrl+Y`: comentaris, canvis de text, operacions de pàgina, marques d'aigua, OCR… Cada document té el seu propi historial.

# Comentar

Les eines de comentari són al menú **Comenta** i a la barra d'eines. Cada una té una lletra per triar-la ràpidament; `V` o `Esc` tornen a l'eina de selecció. Les opcions de l'eina (color, mida, gruix…) apareixen a la part superior del tauler lateral.

## Afegir text

Amb l'eina **Afegeix text** (`T`) feu clic a la pàgina (o arrossegueu un quadre) i escriviu-hi directament a sobre, sense finestres: el quadre creix a mesura que escriviu. Al tauler lateral trieu la mida, el color, la negreta i la cursiva, l'alineació i el tipus de lletra, i els canvis es veuen a l'instant.

![texto] Text escrit directament sobre la pàgina.

`Retorn` obre una línia nova, `Ctrl+Retorn` confirma i `Esc` cancel·la. Fer clic en un altre lloc també confirma. Per canviar un text ja posat, feu-hi doble clic.

## Notes adhesives

La **Nota adhesiva** (`N`) deixa un comentari al costat de la pàgina: feu clic on la vulgueu deixar i escriviu. A la pàgina es veu una icona petita, i el text apareix en passar-hi el ratolí per sobre. El color de la nota es tria al tauler lateral.

![nota] Una nota adhesiva al costat del text.

## Ressaltar, subratllar i ratllar

Amb **Ressalta, subratlla o ratlla** (`H`) trieu el tipus de marca i el color al tauler lateral i arrossegueu sobre el text. Si el text no es pot seleccionar (una imatge o un document escanejat), la marca es dibuixa a mà alçada; un traç ràpid surt recte.

![resaltar] Text ressaltat.

> **Consell:** també podeu seleccionar text amb l'eina de selecció i fer clic amb el botó dret per ressaltar-lo, subratllar-lo o ratllar-lo.

## Rectangles i emojis

El **Rectangle** (`R`) remarca una zona de la pàgina amb un requadre de cantonades arrodonides: arrossegueu per dibuixar-lo, amb el color i el gruix del tauler lateral.

![rectangulo] Un rectangle al voltant del títol.

L'eina **Emoji** (`E`) insereix qualsevol dels més de 1.300 emojis, amb cercador i grups, amb la mida, el color i l'opacitat que vulgueu: trieu-ne un i feu clic on ha d'anar.

![emoji] Triar un emoji.

## Moure, canviar i esborrar comentaris

Amb l'eina de selecció, feu clic en un comentari per seleccionar-lo: es pot moure arrossegant-lo, canviar-ne la mida amb les nanses i esborrar amb `Supr`. L'**Esborrador d'anotacions** treu els comentaris amb un clic.

El tauler **Comentaris** del tauler lateral mostra tots els comentaris del document amb la seva pàgina; en fer-hi clic, la pàgina hi va i queda seleccionat.

![comentarios] El tauler Comentaris.

## Aplanar

**Comenta › Aplana les anotacions i els formularis…** converteix els comentaris i els camps de formulari en part del contingut de la pàgina: es veuen igual, però ja no es poden moure ni editar. És útil abans d'enviar una versió definitiva.

# Editar el contingut del PDF

L'eina **Edita el text i les imatges del PDF** (`C`, al menú Eines) canvia el text i les imatges que ja formen part del document, no pas comentaris a sobre. En triar-la, cada paràgraf s'emmarca en blau i cada imatge en verd.

![editar] Els paràgrafs i les imatges editables, emmarcats.

**Text.** Feu clic en un paràgraf i escriviu: el text es reparteix en les línies que calgui dins del seu quadre, amb el mateix tipus de lletra, mida i color sempre que és possible. Al tauler lateral podeu canviar la mida, el color i la negreta o la cursiva. Si el text no hi cap, el quadre es posa vermell: estireu una de les cantonades per fer-lo més gran. `Ctrl+Retorn` confirma, `Esc` cancel·la i `Tab` passa al paràgraf següent. Si deixeu un paràgraf buit, s'esborra.

**Imatges.** Feu clic en una imatge per seleccionar-la: arrossegueu-la per moure-la, estireu una cantonada per canviar-ne la mida (sense deformar-la) o premeu `Supr` per esborrar-la. Amb el botó dret la podeu substituir per una altra imatge o desar-la en un fitxer.

> **Important:** si el document utilitza un tipus de lletra que no està disponible, AventyaPDF utilitza el més semblant i ho avisa a la barra d'estat. Reviseu el resultat abans de desar.

# Emplenar formularis

Els camps dels formularis es ressalten en blau (ho podeu desactivar a **Visualitza › Ressalta els camps de formulari**). No cal cap eina especial:

- Feu clic en un camp de text i escriviu; `Tab` passa al camp següent i `Maj+Tab` a l'anterior.
- Les caselles i els botons d'opció es marquen amb un clic; les llistes despleguen els seus valors.
- Els càlculs, les validacions i els botons del formulari funcionen com a Adobe Acrobat.

![formulario] Un formulari amb els camps ressaltats.

Si el formulari té un requadre de signatura buit, feu-hi clic per signar-hi a dins (ho veureu al capítol de signatura).

# Organitzar pàgines

## Operacions de pàgina

El botó **Operacions de pàgina** de la barra d'eines (o **Organitza › Organitza les pàgines al tauler lateral**) obre les miniatures en mode d'organització, amb una fila de botons a sobre.

![organizar] Les operacions de pàgina al tauler lateral.

- **Reordenar**: arrossegueu una miniatura a la seva nova posició.
- **Seleccionar-ne diverses**: amb `Ctrl` o `Maj` en fer clic. Sense selecció, els botons actuen sobre la pàgina actual.
- **Botons**: girar a l'esquerra i a la dreta, duplicar, suprimir, inserir una pàgina en blanc, inserir un altre PDF, extreure les pàgines a un PDF nou i retallar.

Tot s'aplica a l'instant i es pot desfer.

## Retallar una pàgina

El botó **Retalla** dibuixa sobre la pàgina un requadre amb nanses a les cantonades i als costats: arrossegueu-les fins al marge que vulgueu. Els botons del centre del requadre apliquen o cancel·len el retall.

![recortar] Retallar una pàgina.

## El menú Organitza

Al menú **Organitza** també hi ha:

- **Insereix una pàgina en blanc**, **Insereix un PDF després de la pàgina actual…** i **Afegeix un PDF al final…**
- **Duplica la pàgina actual**, **Suprimeix pàgines…** i **Extreu pàgines…**, amb intervals com ara «1-3, 5, 8-».
- **Divideix el document…**: desa el document en parts d'un nombre fix de pàgines.
- **Gira la pàgina a la dreta** (`Ctrl+Maj+R`), **a l'esquerra** (`Ctrl+Maj+L`) i **Gira pàgines…** per intervals.

## Combinar documents

**Organitza › Combina PDF…** té dues opcions:

- **Combina els oberts**: ajunta tots els documents oberts, en l'ordre de les pestanyes i amb els seus canvis, en un PDF nou.
- **Combina fitxers…**: trieu diversos fitxers (PDF, imatges o Word, barrejats) i es combinen per ordre alfabètic del nom.

![combinar] Organitza › Combina PDF.

El resultat queda obert sense desar; deseu-lo amb `Ctrl+S`. Els fitxers originals no canvien.

# Crear, convertir i exportar

## Crear documents

- **Fitxer › PDF en blanc nou** (`Ctrl+N`) crea un document amb una pàgina buida.
- **Fitxer › Crea un PDF a partir d'imatges…** ajunta diverses imatges en un PDF, una per pàgina.
- Si obriu una imatge o un document de Word, es converteix a PDF (vegeu «Obrir documents»).

## Exportar

A **Fitxer › Exporta** podeu treure el contingut del document:

- **Pàgines com a imatges…**: PNG o JPG, a la resolució que trieu.
- **Text (.txt)…**: tot el text del document.
- **Document de Word (.docx)…**: un document editable a Word.
- **Extreu pàgines a PDF…**: només les pàgines que indiqueu.

![exportar] Exportar pàgines com a imatges.

## Des de l'Explorador de fitxers

Sense obrir abans l'aplicació, seleccioneu fitxers a l'Explorador de fitxers i feu clic amb el botó dret: al submenú **AventyaPDF** hi teniu:

- **Signa digitalment** (només PDF): obre els documents amb l'eina de signatura preparada.
- **Combina en un PDF** (dos fitxers o més): PDF, imatges i Word, barrejats, en un sol PDF.
- **Converteix a PDF** (imatges i Word): un PDF per fitxer.

![explorador] El submenú AventyaPDF del botó dret.

A Windows 11, el submenú és al menú principal del botó dret; a Windows 10, i a Windows 11 dins de **Mostra més opcions**, és al menú clàssic.

> **Consell:** si el submenú desapareix (per exemple, després d'una actualització de Windows), utilitzeu **Ajuda › Repara el menú contextual de l'Explorador de fitxers…**

# Eines

## Marca d'aigua

**Eines › Marca d'aigua…** escriu un text sobre les pàgines que trieu, amb la mida, el color, l'opacitat i l'angle que vulgueu (per exemple, «CONFIDENCIAL» en diagonal).

![marca_agua] Marca d'aigua.

## Capçalera, peu i numeració Bates

**Eines › Capçalera, peu i numeració Bates…** afegeix fins a tres textos a la capçalera i tres al peu (esquerra, centre i dreta). Podeu utilitzar variables:

- `{n}`: el número de pàgina; `{total}`: el nombre total de pàgines.
- `{fecha}`: la data d'avui.
- `{bates}`: un número correlatiu Bates, amb prefix, número inicial i xifres.

![encabezado] Capçalera, peu i numeració Bates.

## Reconèixer text (OCR)

**Eines › Reconeix el text (OCR)…** converteix en text seleccionable i cercable el de les pàgines escanejades, les fotos i les imatges. Trieu l'idioma del document, si es reconeixen totes les pàgines o només les que no tenen text, i si es corregeix l'orientació de cada pàgina.

![ocr] Reconèixer text (OCR).

El text s'afegeix com una capa invisible: la pàgina no canvia d'aspecte, però ja es pot cercar, seleccionar i copiar. Si trieu un idioma nou, AventyaPDF en baixa abans les dades.

## Optimitzar i comprimir

El botó **Comprimeix el PDF** de la barra d'eines (o **Eines › Optimitza i comprimeix…**) redueix la mida del fitxer, sobretot quan té imatges. Trieu el nivell (alta qualitat, bona qualitat o màxima reducció) i deseu la còpia comprimida; l'original no canvia.

![comprimir] Les opcions de compressió.

# Protegir amb contrasenya

**Protegeix › Protegeix amb contrasenya…** xifra el document amb AES de 256 bits:

- **Contrasenya per obrir el document**: sense aquesta contrasenya no es pot obrir.
- **Contrasenya de permisos**: restringeix imprimir, copiar, modificar o comentar, encara que es pugui obrir sense contrasenya.

![proteger] Protegir amb contrasenya.

La protecció s'aplica en desar. **Protegeix › Treu la seguretat** treu la contrasenya i els permisos d'un document que heu obert amb la seva contrasenya.

> **Important:** si oblideu la contrasenya per obrir, no hi ha manera de recuperar el document. Deseu-la en un lloc segur.

# Signar

AventyaPDF signa amb signatura electrònica avançada PAdES, la que s'utilitza als documents oficials europeus, amb certificats qualificats com els de la FNMT o el DNIe.

## El certificat

A **Signa › Certificat de signatura…** trieu amb quin certificat se signa:

- **Magatzem de Windows**: els certificats instal·lats al vostre ordinador, també els de targetes i del DNIe. La clau no surt mai del magatzem; si cal un PIN, el demana Windows.
- **Fitxer .pfx / .p12**: un certificat desat en un fitxer. La contrasenya es pot desar a l'Administrador de credencials de Windows per no haver-la d'escriure cada vegada.

El certificat triat es recorda per a les signatures següents.

## Signar un document

Trieu l'eina **Signatura** (o **Signa › Signa el document (dibuixa l'àrea)**) i dibuixeu a la pàgina el requadre on anirà la signatura visible. Al tauler lateral es veu el certificat actiu i es pot canviar.

![firmar] L'eina de signatura, amb el certificat actiu.

Després apareixen les **opcions de signatura**, i finalment AventyaPDF demana on voleu desar el document signat (proposa el mateix nom acabat en «_signat»). L'original no es modifica.

![opciones_firma] Opcions de signatura.

- **Motiu, lloc i contacte**: apareixen al segell visible i a les dades de la signatura. El segell surt en l'idioma de l'aplicació.
- **Afegeix un segell de temps qualificat (PAdES-B-T)**: una autoritat de segellament de temps certifica la data i l'hora de la signatura. Necessita Internet.
- **Certifica el document**: després de signar, només es podran emplenar formularis i afegir més signatures; qualsevol altre canvi invalidarà la certificació.
- **No ho tornis a preguntar**: signa directament amb aquestes opcions (es canvia a **Signa › Opcions de signatura…**).

Un document es pot signar diverses vegades: cada signatura nova s'afegeix sense invalidar les anteriors, sempre que no s'hi hagin fet canvis entremig.

## Signar al requadre d'un formulari

Si el document té un requadre de signatura buit (com molts impresos de l'Administració), feu-hi clic: AventyaPDF demana el certificat i signa dins d'aquest requadre.

## Signatura manuscrita

**Signa › Insereix una signatura manuscrita (dibuixada o imatge)…**, o la ploma del tauler de signatura, obre un llenç on podeu dibuixar la vostra signatura amb el ratolí, amb traç d'estilogràfica i el color i el gruix que vulgueu. També podeu carregar la imatge de la vostra signatura escanejada (es treu el fons blanc del paper).

![manuscrita] Dibuixar la signatura manuscrita.

Després feu clic a la pàgina per col·locar-la, o arrossegueu un requadre per donar-li mida. Queda com un comentari més: es mou, se'n canvia la mida i s'esborra.

> **Important:** la signatura manuscrita només és una imatge. No té valor de signatura electrònica; per a això, signeu amb certificat.

## Verificar les signatures

El tauler **Signatures certificades** del tauler lateral (o **Signa › Mostra les signatures (verificades)**) comprova automàticament cada signatura del document:

- si el document s'ha alterat després de signar-lo;
- si el certificat és de confiança, segons el magatzem de Windows i la llista de confiança oficial d'Espanya (FNMT, DNIe, Col·legi de Registradors, Izenpe, ACCV i la resta de prestadors qualificats);
- la data declarada, el segell de temps i si hi ha canvis posteriors.

![firmas] El tauler Signatures certificades.

La signatura més recent té una paperera que la treu i en deixa el requadre buit per tornar a signar (per exemple, amb un altre certificat). El canvi s'aplica en desar.

# Dreceres de teclat

**Ajuda › Dreceres de teclat** (`F1`) mostra aquesta mateixa llista dins de l'aplicació.

[[atajos]]

# Si alguna cosa no funciona

## L'OCR no està disponible

Tesseract OCR s'instal·la la primera vegada que reconeixeu text i necessita Internet (i, de vegades, permís d'administrador). Si s'ha denegat el permís o no hi havia connexió, AventyaPDF ho torna a provar la propera vegada que l'obriu.

## No apareix el submenú AventyaPDF a l'Explorador de fitxers

Utilitzeu **Ajuda › Repara el menú contextual de l'Explorador de fitxers…**. A Windows 11, perquè el submenú sigui al menú principal, l'instal·lador demana una vegada permís d'administrador; si s'ha denegat, el submenú és a **Mostra més opcions**.

## Un document de Word no es converteix

Cal tenir instal·lat Microsoft Word o LibreOffice. Si tots dos fallen, AventyaPDF en mostra el motiu.

## Una signatura surt com a «identitat no verificada»

La signatura no s'ha alterat, però el seu certificat no és al magatzem de Windows ni a la llista de confiança d'Espanya (per exemple, un certificat de proves o d'un altre país). Comproveu amb el signant d'on és el seu certificat.

## Informar d'un error

Si apareix una finestra d'«Error inesperat», l'aplicació continua oberta i el detall es desa a la carpeta `%LOCALAPPDATA%\aventyapdf` (fitxers `errores.log` i `fallos_graves.log`). Envieu aquests fitxers amb una descripció del que fèieu a github.com/Aventya/AventyaPDF/issues.
