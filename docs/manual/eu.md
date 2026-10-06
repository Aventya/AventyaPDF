---
titulo: AventyaPDF eskuliburua
subtitulo: Ikusi, iruzkindu, antolatu, babestu, bihurtu eta sinatu PDF dokumentuak
version: {version} bertsioa
indice: Aurkibidea
meses: urtarrila|otsaila|martxoa|apirila|maiatza|ekaina|uztaila|abuztua|iraila|urria|azaroa|abendua
fecha: {anio}ko {mes}
cabecera: AventyaPDF-ren eskuliburua
consejo: Aholkua
importante: Garrantzitsua
atajos_tecla: Tekla
atajos_accion: Ekintza
muestra_titulo: Adibide-dokumentua — {n}. orrialdea
muestra_texto: Hau adibide-dokumentu bat da, eskuliburuan AventyaPDF-ren tresnak erakusteko soilik sortua. Ez dauka benetako daturik, ezta inongo bezeroaren daturik ere.\n\nAventyaPDF Windows-erako mahaigaineko aplikazio bat da: PDF dokumentuak ikusi, iruzkindu, antolatu, babestu, bihurtu eta digitalki sinatzeko balio du.\n\nParagrafo honek iruzkintzeko tresnak probatzeko balio du: testua nabarmendu, azpimarratu, marratu, hautatu eta kopiatu, edo ohar itsaskorrak gehitu ondoan.
buscar: dokumentu
resaltar: iruzkintzeko tresnak
texto_anotacion: Orrialdearen gainean gehitutako testua
nota_texto: Berrikusi paragrafo hau bidali aurretik.
formulario_titulo: Adibide-eskabidea
campo_nombre: Izen-abizenak
campo_fecha: Data
campo_importe: Zenbatekoa
casilla: Baldintzak onartzen ditut
firmante: Adibide Pertsona
motivo: Adostasuna
lugar: Hiria
contacto: posta@adibidea.eus
certificado_ejemplo: Adibide-ziurtagiria
nombre_doc1: Kontratua.pdf
nombre_doc2: Faktura.pdf
nombre_doc3: Txostena.pdf
nombre_formulario: Eskabidea.pdf
nombre_firmado: Kontratu sinatua.pdf
explorador_opciones: Ireki|Ireki honekin|Partekatu
---

# Lehen urratsak

## Zer da AventyaPDF

AventyaPDF Windows-erako aplikazio bat da, eta programa bakarrean biltzen du PDF dokumentuekin egunero egiten dena: irakurri, iruzkindu, inprimakiak bete, testua aldatu, orrialdeak antolatu, dokumentuak konbinatu, pasahitzarekin babestu, eskaneatutako dokumentuetako testua ezagutu eta ziurtagiri digitalarekin sinatu.

Banaketa librekoa da, eta haren kodea GitHub-en argitaratuta dago. Ez ditu zure dokumentuak inora bidaltzen: dena zure ordenagailuan egiten da.

![ventana] AventyaPDF-ren leihoa, hiru dokumentu irekita dituela.

## Instalatu eta eguneratu

Instalatzaileak hizkuntza galdetzen du lehenik (Windows-ena proposatzen du): hizkuntza horretan instalatzen eta irekitzen da AventyaPDF. Instalazioan zehar, Python, haren osagaiak eta letra-tipoak deskargatzen dira beren webgune ofizialetatik; beraz, Interneteko konexioa behar da. Bitartean, instalatzaileak aplikazioaren tresnak erakusten ditu.

Amaitzean, AventyaPDF Hasiera menuan agertzen da (eta, markatu baduzu, mahaigainean), baita PDF fitxategien **Ireki honekin** aukeran ere. Windows-ek ez dio uzten programa bati bere kabuz ikustaile lehenetsi bihurtzen: PDFak beti AventyaPDF-rekin irekitzea nahi baduzu, aukeratu **Ireki honekin › Aukeratu beste aplikazio bat** aukeran, eta markatu «Erabili beti aplikazio hau».

Bertsio berri bat dagoenean, AventyaPDF-k abisatu egiten du abiaraztean. **Laguntza › Bilatu eguneratzeak…** aukeran ere egiazta dezakezu: instalatzaile berria zure Deskargak karpetan deskargatzen da, eta ireki besterik ez duzu egin behar. Zure ezarpenak, ziurtagiria eta hizkuntza mantendu egiten dira.

> **Garrantzitsua:** testu-ezagutzak (OCR) Tesseract OCR erabiltzen du, eta hori ez dator instalatzailearen barruan. AventyaPDF-k lehen aldiz erabiltzen duzunean deskargatu eta instalatzen du; administratzaile-baimena eska dezake.

## Leihoa

- **Menu-barra**: funtzio guztiak, menu hauetan antolatuta: Fitxategia, Editatu, Ikusi, Iruzkindu, Antolatu, Tresnak, Babestu, Sinatu eta Laguntza.
- **Tresna-barra**: ireki, gorde, inprimatu eta konprimitu; desegin eta berregin; uneko orrialdea; zoomaren doikuntza; iruzkintzeko eta editatzeko tresnak; sinadura; orrialde-eragiketak eta, eskuinean, lupa bilatzeko.
- **Alboko panela** (ezkerrean; **F4** sakatuta irekitzen eta ixten da): orrialdeen koadro txikiak, laster-markak, iruzkinak eta ziurtagiridun sinadurak. Panelaren goialdean, erabiltzen ari zaren tresnaren aukerak agertzen dira.
- **Egoera-barra** (behean): aplikazioaren mezuak eta, eskuinean, zooma.

## Aurkezpena, laguntza eta hizkuntza

AventyaPDF lehen aldiz irekitzean, funtzioak laburbiltzen dituen aurkezpen bat agertzen da. Markatu «Ez erakutsi berriro abiaraztean» gehiago ikusi nahi ez baduzu; nahi duzunean ireki dezakezu berriro **Laguntza › AventyaPDF-ren aurkezpena** aukeratik.

![presentacion] Hasierako aurkezpena.

**Laguntza** menuan daude, halaber, eskuliburu hau (**Laguntza › AventyaPDF-ren eskuliburua**), lasterbideen zerrenda (**F1**) eta aplikazioaren hizkuntza (**Laguntza › Hizkuntza**). AventyaPDF gaztelaniaz, ingelesez, frantsesez, italieraz, katalanez, galizieraz eta euskaraz dago; hizkuntza berria aplikazioa irekitzen duzun hurrengo aldian aplikatzen da.

![idioma] Laguntza › Hizkuntza.

# Ireki, gorde eta dokumentuan mugitu

## Ireki dokumentuak

Hainbat modutara ireki daitezke dokumentuak:

- **Fitxategia › Ireki…** (`Ctrl+O`): hainbat fitxategi aukera ditzakezu batera, `Ctrl` edo `Maius` sakatuta.
- Fitxategi-arakatzailetik leihora arrastatuta.
- **Fitxategia › Ireki azkenak**, azken aldian erabilitako dokumentuekin.
- PDF batean klik bikoitza eginda, AventyaPDF zure PDF ikustailea bada.

PDFez gain, AventyaPDF-k irudiak (PNG, JPG, BMP, GIF, TIFF eta WebP) eta Word dokumentuak (.doc eta .docx) irekitzen ditu: bakoitza PDF berri bihurtzen da, gorde gabe, bere fitxan. Jatorrizkoa ez da ukitzen. Word dokumentuak bihurtzeko, Microsoft Word edo LibreOffice instalatuta izan behar da.

PDFa pasahitzez babestuta badago, AventyaPDF-k pasahitza eskatzen du ireki aurretik.

## Hainbat dokumentu batera

Irekitako dokumentu bakoitzak bere fitxa du alboko panelean, panelen ikonoen azpian. Sagua gainetik pasatzean, haren izena eta karpeta ikusten dira, eta «●» puntuak adierazten du gorde gabeko aldaketak dituela.

![pestanas] Irekitako dokumentuen fitxak, alboko panelean.

- Egin klik fitxa batean dokumentu horretara joateko, edo erabili `Ctrl+Tab` eta `Ctrl+Maius+Tab`.
- Arrastatu fitxa bat gora edo behera ordena aldatzeko.
- Fitxa baten gainean eskuineko botoiarekin, dokumentu hori itxi dezakezu (edo erabili `Ctrl+W`).

Dokumentu bakoitzak bere orrialdea, aldaketak eta desegiteko historia gordetzen ditu. Irekita zegoen fitxategi bat irekitzen baduzu, AventyaPDF haren fitxara aldatzen da, besterik gabe.

## Orrialdeetan mugitu eta zooma

- `Orria behera` eta `Orria gora` teklek orrialdez aldatzen dute; `Hasiera` eta `Amaiera` teklek lehen eta azken orrialdera eramaten dute. Saguaren gurpilak ere orrialdez aldatzen du ertzera iristean.
- Idatzi zenbaki bat tresna-barrako orrialde-koadroan, edo erabili **Ikusi › Joan orrialdera…** (`Ctrl+G`).
- Egin klik alboko paneleko koadro txiki batean orrialde horretara joateko. Laster-marken panelak dokumentuaren aurkibidea erakusten du, baldin badu.

Zooma beti dago behean eskuinean: luparen botoiek handiagotu eta txikiagotu egiten dute, barra arrastatu egin daiteke, eta koadroan ehuneko zehatza idatz daiteke (% 400 arte). `Ctrl+gurpila`, `Ctrl++` eta `Ctrl+-` ere erabil daitezke. Tresna-barrako doikuntza-botoiak txandaka aldatzen du zabalerara doitzearen (`Ctrl+1`), orrialdera doitzearen (`Ctrl+2`) eta benetako tamainaren (`Ctrl+0`) artean.

![zoom] Zooma, egoera-barran.

## Bilatu eta kopiatu testua

Sakatu `Ctrl+F` edo tresna-barrako lupa, eta idatzi bilatzen duzuna: bat-etortzeak orrialdean nabarmentzen dira idatzi ahala, eta zenbatu egiten dira («1 / 12»). Geziekin, `F3` eta `Maius+F3` teklekin hurrengora eta aurrekora joaten zara; `Esc` teklak bilaketa ixten du.

![buscar] Bilatu dokumentuan.

Kopiatzeko, arrastatu sagua testuaren gainean hautapen-tresnarekin eta sakatu `Ctrl+C`. Paragrafo bakoitza lerro bakarrean itsasten da, PDFko lerro-jauzirik gabe; OCR bidez ezagututako testua ere bai.

## Gorde, inprimatu eta propietateak

- **Fitxategia › Gorde** (`Ctrl+S`) aukerak fitxategi berean gordetzen du; **Gorde honela…** (`Ctrl+Maius+S`) aukerak, beste izen batekin. Leihoaren izenburuak «●» darama gorde gabeko aldaketak dauden bitartean, eta ixtean gorde nahi dituzun galdetzen da.
- **Fitxategia › Inprimatu…** (`Ctrl+P`) aukerak Windows-en inprimatzeko leihoa irekitzen du.
- **Fitxategia › Dokumentuaren propietateak…** (`Ctrl+D`) aukerak izenburua, egilea, gaia eta gako-hitzak erakusten ditu eta aldatzen uzten du, eta Informazioa fitxan, datu hauek: orrialde kopurua, tamaina edo sinadurarik duen, besteak beste.

![propiedades] Dokumentuaren propietateak.

## Desegin eta berregin

Dokumentu batean egiten duzun ia guztia desegin daiteke `Ctrl+Z` sakatuta, eta berregin `Ctrl+Y` sakatuta: iruzkinak, testu-aldaketak, orrialde-eragiketak, ur-markak, OCR… Dokumentu bakoitzak bere historia du.

# Iruzkindu

Iruzkintzeko tresnak **Iruzkindu** menuan eta tresna-barran daude. Bakoitzak letra bat du azkar aukeratzeko; `V` edo `Esc` sakatuta hautapen-tresnara itzultzen zara. Tresnaren aukerak (kolorea, tamaina, lodiera…) alboko panelaren goialdean agertzen dira.

## Gehitu testua

**Gehitu testua** tresnarekin (`T`), egin klik orrialdean (edo arrastatu koadro bat) eta idatzi zuzenean gainean, leihorik gabe: koadroa handitu egiten da idatzi ahala. Alboko panelean tamaina, kolorea, letra lodia eta etzana, lerrokadura eta letra-tipoa aukeratzen dituzu, eta aldaketak berehala ikusten dira.

![texto] Orrialdearen gainean zuzenean idatzitako testua.

`Sartu` teklak lerro berri bat irekitzen du, `Ctrl+Sartu` konbinazioak berresten du eta `Esc` teklak bertan behera uzten du. Beste leku batean klik eginda ere berresten da. Lehendik jarritako testu bat aldatzeko, egin klik bikoitza haren gainean.

## Ohar itsaskorrak

**Ohar itsaskorra** tresnak (`N`) iruzkin bat uzten du orrialdearen ondoan: egin klik utzi nahi duzun lekuan eta idatzi. Orrialdean ikono txiki bat ikusten da, eta testua sagua gainetik pasatzean agertzen da. Oharraren kolorea alboko panelean aukeratzen da.

![nota] Ohar itsaskor bat testuaren ondoan.

## Nabarmendu, azpimarratu eta marratu

**Nabarmendu, azpimarratu edo marratu** tresnarekin (`H`), aukeratu marka mota eta haren kolorea alboko panelean, eta arrastatu testuaren gainean. Testua hautatu ezin bada (irudi bat edo eskaneatutako dokumentu bat), marka eskuz marrazten da; trazu azkar bat zuzen ateratzen da.

![resaltar] Testu nabarmendua.

> **Aholkua:** testua hautapen-tresnarekin hauta dezakezu, eta eskuineko botoia sakatu, nabarmentzeko, azpimarratzeko edo marratzeko.

## Laukizuzenak eta emojiak

**Laukizuzena** tresnak (`R`) orrialdeko eremu bat inguratzen du ertz biribildutako lauki batekin: arrastatu marrazteko, alboko paneleko kolorearekin eta lodierarekin.

![rectangulo] Laukizuzen bat izenburuaren inguruan.

**Emojia** tresnak (`E`) 1.300 emoji baino gehiagotatik edozein txertatzen du, bilatzailearekin eta taldeka, nahi duzun tamaina, kolore eta opakutasunarekin: aukeratu bat eta egin klik joango den lekuan.

![emoji] Aukeratu emoji bat.

## Mugitu, aldatu eta ezabatu iruzkinak

Hautapen-tresnarekin, egin klik iruzkin batean hautatzeko: arrastatuta mugi daiteke, heldulekuekin tamainaz alda daiteke, eta `Ezab` teklarekin ezaba daiteke. **Oharpenen borragoma** tresnak iruzkinak kentzen ditu klik batekin.

Alboko paneleko **Iruzkinak** panelak dokumentuko iruzkin guztiak zerrendatzen ditu, bakoitza bere orrialdearekin; bat sakatzean, orrialdea hartara joaten da, eta hautatuta geratzen da.

![comentarios] Iruzkinak panela.

## Lautu

**Iruzkindu › Lautu oharpenak eta inprimakiak…** aukerak iruzkinak eta inprimaki-eremuak orrialdeko edukiaren parte bihurtzen ditu: berdin ikusten dira, baina ezin dira gehiago mugitu ez editatu. Erabilgarria da behin betiko bertsio bat bidali aurretik.

# Editatu PDFaren edukia

**Editatu PDFko testua eta irudiak** tresnak (`C`, Tresnak menuan) dokumentuaren parte diren testua eta irudiak aldatzen ditu, ez gaineko iruzkinak. Tresna hori aukeratzean, paragrafo bakoitza urdinez markoztatzen da, eta irudi bakoitza berdez.

![editar] Paragrafo eta irudi editagarriak, markoztatuta.

**Testua.** Egin klik paragrafo batean eta idatzi: testua behar adina lerrotan banatzen da bere koadroaren barruan, ahal den guztietan letra-tipo, tamaina eta kolore berarekin. Alboko panelean tamaina, kolorea eta letra lodia edo etzana alda ditzakezu. Testua sartzen ez bada, koadroa gorri jartzen da: tiratu haren izkinetako bati handiagoa egiteko. `Ctrl+Sartu` konbinazioak berresten du, `Esc` teklak bertan behera uzten du eta `Tab` teklak hurrengo paragrafora eramaten du. Paragrafo bat hutsik utzita, ezabatu egiten da.

**Irudiak.** Egin klik irudi batean hautatzeko: arrastatu mugitzeko, tiratu izkina batetik tamaina aldatzeko (deformatu gabe) edo sakatu `Ezab` ezabatzeko. Eskuineko botoiarekin, beste irudi batez ordez dezakezu edo fitxategi batean gorde.

> **Garrantzitsua:** dokumentuak erabilgarri ez dagoen letra-tipo bat erabiltzen badu, AventyaPDF-k antzekoena erabiltzen du, eta egoera-barran abisatzen du. Berrikusi emaitza gorde aurretik.

# Bete inprimakiak

Inprimakietako eremuak urdinez nabarmentzen dira (**Ikusi › Nabarmendu inprimaki-eremuak** aukeran ken dezakezu). Ez da tresna berezirik behar:

- Egin klik testu-eremu batean eta idatzi; `Tab` teklak hurrengo eremura eramaten du, eta `Maius+Tab` konbinazioak aurrekora.
- Kontrol-laukiak eta aukera-botoiak klik batekin markatzen dira; zerrendek beren balioak zabaltzen dituzte.
- Inprimakiaren kalkuluek, baliozkotzeek eta botoiek Adobe Acrobat-en bezala funtzionatzen dute.

![formulario] Inprimaki bat, eremuak nabarmenduta.

Inprimakiak sinadura-lauki huts bat badu, egin klik haren gainean barruan sinatzeko (sinadurari buruzko kapituluan ikusiko duzu).

# Antolatu orrialdeak

## Orrialde-eragiketak

Tresna-barrako **Orrialde-eragiketak** botoiak (edo **Antolatu › Antolatu orrialdeak alboko panelean** aukerak) koadro txikiak antolatzeko moduan irekitzen ditu, botoi-errenkada bat gainean dutela.

![organizar] Orrialde-eragiketak alboko panelean.

- **Ordenatu**: arrastatu koadro txiki bat bere posizio berrira.
- **Hautatu hainbat**: `Ctrl` edo `Maius` sakatuta klik egitean. Hautapenik ez badago, botoiek uneko orrialdean eragiten dute.
- **Botoiak**: biratu ezkerrera eta eskuinera, bikoiztu, ezabatu, txertatu orrialde zuri bat, txertatu beste PDF bat, atera orrialdeak PDF berri batera eta moztu.

Dena berehala aplikatzen da, eta desegin egin daiteke.

## Moztu orrialde bat

**Moztu** botoiak lauki bat marrazten du orrialdearen gainean, izkinetan eta alboetan heldulekuak dituela: arrastatu bakoitza nahi duzun marjinaraino. Laukiaren erdiko botoiek moztea aplikatzen edo bertan behera uzten dute.

![recortar] Moztu orrialde bat.

## Antolatu menua

**Antolatu** menuan hauek ere badaude:

- **Txertatu orrialde zuria**, **Txertatu PDFa uneko orrialdearen ondoren…** eta **Gehitu PDFa amaieran…**
- **Bikoiztu uneko orrialdea**, **Ezabatu orrialdeak…** eta **Atera orrialdeak…**, «1-3, 5, 8-» bezalako barrutiekin.
- **Zatitu dokumentua…**: dokumentua orrialde kopuru finkoko zatitan gordetzen du.
- **Biratu orrialdea eskuinera** (`Ctrl+Maius+R`), **Biratu orrialdea ezkerrera** (`Ctrl+Maius+L`) eta **Biratu orrialdeak…**, barrutika.

## Konbinatu dokumentuak

**Antolatu › Konbinatu PDFak…** aukerak bi aukera ditu:

- **Konbinatu irekiak**: irekitako dokumentu guztiak PDF berri batean biltzen ditu, fitxen ordenan eta beren aldaketekin.
- **Konbinatu fitxategiak…**: hainbat fitxategi aukeratzen dituzu (PDFak, irudiak edo Word dokumentuak, nahasian), eta izenen ordena alfabetikoan konbinatzen dira.

![combinar] Antolatu › Konbinatu PDFak.

Emaitza irekita geratzen da, gorde gabe; gorde ezazu `Ctrl+S` sakatuta. Jatorrizko fitxategiak ez dira aldatzen.

# Sortu, bihurtu eta esportatu

## Sortu dokumentuak

- **Fitxategia › PDF zuri berria** (`Ctrl+N`) aukerak orrialde huts bat duen dokumentu bat sortzen du.
- **Fitxategia › Sortu PDFa irudietatik…** aukerak hainbat irudi biltzen ditu PDF batean, bat orrialde bakoitzeko.
- Irudi bat edo Word dokumentu bat irekitzean, PDF bihurtzen da (ikus «Ireki dokumentuak»).

## Esportatu

**Fitxategia › Esportatu** aukeran, dokumentuaren edukia atera dezakezu:

- **Orrialdeak irudi gisa…**: PNG edo JPG, aukeratzen duzun bereizmenean.
- **Testua (.txt)…**: dokumentuko testu guztia.
- **Word dokumentua (.docx)…**: Word-en editatzeko moduko dokumentu bat.
- **Atera orrialdeak PDFra…**: adierazten dituzun orrialdeak soilik.

![exportar] Esportatu orrialdeak irudi gisa.

## Fitxategi-arakatzailetik

Aplikazioa aurretik ireki gabe, hautatu fitxategiak Windows-en Fitxategi-arakatzailean eta sakatu eskuineko botoia: **AventyaPDF** azpimenuan hauek dituzu:

- **Sinatu digitalki** (PDFak soilik): dokumentuak irekitzen ditu, sinatzeko tresna prest dagoela.
- **Konbinatu PDF bakarrean** (bi fitxategi edo gehiago): PDFak, irudiak eta Word dokumentuak, nahasian, PDF bakar batean.
- **Bihurtu PDF** (irudiak eta Word): PDF bat fitxategi bakoitzeko.

![explorador] Eskuineko botoiaren AventyaPDF azpimenua.

Windows 11n, azpimenua eskuineko botoiaren menu nagusian dago; Windows 10en, eta Windows 11n **Erakutsi aukera gehiago** aukeraren barruan, menu klasikoan dago.

> **Aholkua:** azpimenua desagertzen bada (adibidez, Windows-en eguneratze baten ondoren), erabili **Laguntza › Konpondu Fitxategi-arakatzailearen laster-menua…**

# Tresnak

## Ur-marka

**Tresnak › Ur-marka…** aukerak testu bat idazten du aukeratzen dituzun orrialdeen gainean, nahi duzun tamaina, kolore, opakutasun eta angeluarekin (adibidez, «KONFIDENTZIALA» diagonalean).

![marca_agua] Ur-marka.

## Goiburua, orri-oina eta Bates zenbakitzea

**Tresnak › Goiburua, orri-oina eta Bates zenbakitzea…** aukerak hiru testu arte gehitzen ditu goiburuan eta beste hiru orri-oinean (ezkerrean, erdian eta eskuinean). Aldagaiak erabil ditzakezu:

- `{n}`: orrialde-zenbakia; `{total}`: orrialdeen guztizko kopurua.
- `{fecha}`: gaurko data.
- `{bates}`: Bates zenbaki korrelatibo bat, aurrizkiarekin, hasierako zenbakiarekin eta zifra kopuruarekin.

![encabezado] Goiburua, orri-oina eta Bates zenbakitzea.

## Ezagutu testua (OCR)

**Tresnak › Ezagutu testua (OCR)…** aukerak eskaneatutako orrialdeetako, argazkietako eta irudietako testua hautatzeko eta bilatzeko moduko testu bihurtzen du. Aukeratu dokumentuaren hizkuntza, orrialde guztiak ezagutu behar diren edo testurik ez dutenak soilik, eta orrialde bakoitzaren orientazioa zuzendu behar den.

![ocr] Ezagutu testua (OCR).

Testua geruza ikusezin gisa gehitzen da: orrialdearen itxura ez da aldatzen, baina testua bilatu, hautatu eta kopiatu egin daiteke jada. Hizkuntza berri bat aukeratzen baduzu, AventyaPDF-k haren datuak deskargatzen ditu lehenik.

## Optimizatu eta konprimitu

Tresna-barrako **Konprimitu PDFa** botoiak (edo **Tresnak › Optimizatu eta konprimitu…** aukerak) fitxategiaren tamaina txikitzen du, batez ere irudiak dituenean. Aukeratu maila (kalitate handia, kalitate ona edo txikitze handiena) eta gorde kopia konprimitua; jatorrizkoa ez da aldatzen.

![comprimir] Konpresio-aukerak.

# Babestu pasahitzarekin

**Babestu › Babestu pasahitzarekin…** aukerak dokumentua 256 biteko AES bidez zifratzen du:

- **Dokumentua irekitzeko pasahitza**: hori gabe ezin da ireki.
- **Baimen-pasahitza**: inprimatzea, kopiatzea, aldatzea edo iruzkintzea mugatzen du, nahiz eta pasahitzik gabe ireki daitekeen.

![proteger] Babestu pasahitzarekin.

Babesa gordetzean aplikatzen da. **Babestu › Kendu segurtasuna** aukerak pasahitza eta baimenak kentzen ditu, haren pasahitzarekin ireki duzun dokumentu batetik.

> **Garrantzitsua:** irekitzeko pasahitza ahazten baduzu, ez dago dokumentua berreskuratzeko modurik. Gorde ezazu leku seguru batean.

# Sinatu

AventyaPDF-k PAdES sinadura elektroniko aurreratuarekin sinatzen du —Europako dokumentu ofizialetan erabiltzen dena—, FNMTrenak edo DNIe-a bezalako ziurtagiri kualifikatuekin.

## Ziurtagiria

**Sinatu › Sinadura-ziurtagiria…** aukeran, zein ziurtagirirekin sinatuko den aukeratzen duzu:

- **Windows-en biltegia**: zure ordenagailuan instalatutako ziurtagiriak, txarteletakoak eta DNIe-koak barne. Gakoa ez da inoiz biltegitik ateratzen; PIN bat behar bada, Windows-ek eskatzen du.
- **.pfx / .p12 fitxategia**: fitxategi batean gordetako ziurtagiri bat. Pasahitza Windows-en Kredentzial-kudeatzailean gorde daiteke, aldi bakoitzean idatzi behar ez izateko.

Aukeratutako ziurtagiria gogoratu egiten da hurrengo sinaduretarako.

## Sinatu dokumentu bat

Aukeratu **Sinadura** tresna (edo **Sinatu › Sinatu dokumentua (marraztu eremua)**) eta marraztu orrialdean sinadura ikusgaia joango den laukia. Alboko panelean ziurtagiri aktiboa ikusten da, eta alda daiteke.

![firmar] Sinatzeko tresna, ziurtagiri aktiboarekin.

Ondoren, **sinaduraren aukerak** agertzen dira, eta azkenik AventyaPDF-k galdetzen du non gorde sinatutako dokumentua (izen bera proposatzen du, «_sinatua» amaierarekin). Jatorrizkoa ez da aldatzen.

![opciones_firma] Sinaduraren aukerak.

- **Arrazoia, lekua eta kontaktua**: zigilu ikusgaian eta sinaduraren datuetan agertzen dira. Zigilua aplikazioaren hizkuntzan ateratzen da.
- **Gehitu denbora-zigilu kualifikatua (PAdES-B-T)**: zigilatze-agintaritza batek sinaduraren data eta ordua ziurtatzen ditu. Internet behar du.
- **Ziurtatu dokumentua**: sinatu ondoren, inprimakiak bete eta sinadura gehiago gehitu ahal izango dira soilik; beste edozein aldaketak ziurtapena baliogabetuko du.
- **Ez galdetu berriro**: aukera hauekin zuzenean sinatzen du (**Sinatu › Sinaduraren aukerak…** aukeran aldatzen da).

Dokumentu bat hainbat aldiz sinatu daiteke: sinadura berri bakoitza aurrekoak baliogabetu gabe gehitzen da, betiere haien artean aldaketarik egin ez bada.

## Sinatu inprimaki bateko laukian

Dokumentuak sinadura-lauki huts bat badu (Administrazioaren inprimaki askok bezala), egin klik haren gainean: AventyaPDF-k ziurtagiria eskatzen du eta lauki horren barruan sinatzen du.

## Eskuzko sinadura

**Sinatu › Txertatu eskuzko sinadura (marraztua edo irudia)…** aukerak, edo sinadura-paneleko lumak, oihal bat irekitzen du zure sinadura saguarekin marrazteko, luma estilografikoaren trazuarekin eta nahi duzun kolore eta lodierarekin. Zure sinadura eskaneatuaren irudia ere karga dezakezu (paperaren atzealde zuria kendu egiten da).

![manuscrita] Marraztu eskuzko sinadura.

Ondoren, egin klik orrialdean kokatzeko, edo arrastatu lauki bat tamaina emateko. Beste iruzkin bat bezala geratzen da: mugitu, tamainaz aldatu eta ezabatu egin daiteke.

> **Garrantzitsua:** eskuzko sinadura irudi bat besterik ez da. Ez du sinadura elektronikoaren baliorik; horretarako, sinatu ziurtagiriarekin.

## Egiaztatu sinadurak

Alboko paneleko **Ziurtagiridun sinadurak** panelak (edo **Sinatu › Ikusi sinadurak (egiaztatuta)** aukerak) dokumentuko sinadura bakoitza automatikoki egiaztatzen du:

- dokumentua sinatu ondoren aldatu den;
- ziurtagiria fidagarria den, Windows-en biltegiaren eta Espainiako konfiantza-zerrenda ofizialaren arabera (FNMT, DNIe, Colegio de Registradores, Izenpe, ACCV eta gainerako zerbitzu-emaile kualifikatuak);
- adierazitako data, denbora-zigilua eta geroko aldaketarik dagoen.

![firmas] Ziurtagiridun sinadurak panela.

Sinadurarik berrienak zakarrontzi bat du: sinadura kentzen du eta haren laukia hutsik uzten du berriro sinatzeko (adibidez, beste ziurtagiri batekin). Aldaketa gordetzean aplikatzen da.

# Lasterbideak

**Laguntza › Lasterbideak** (`F1`) aukerak zerrenda hau bera erakusten du aplikazioaren barruan.

[[atajos]]

# Zerbaitek ez badu funtzionatzen

## OCR ez dago erabilgarri

Tesseract OCR testua lehen aldiz ezagutzen duzunean instalatzen da, eta Internet behar du (eta, batzuetan, administratzaile-baimena). Baimena ukatu bazen edo konexiorik ez bazegoen, AventyaPDF-k berriro saiatuko da ireki duzun hurrengo aldian.

## AventyaPDF azpimenua ez da agertzen Fitxategi-arakatzailean

Erabili **Laguntza › Konpondu Fitxategi-arakatzailearen laster-menua…**. Windows 11n, azpimenua menu nagusian egon dadin, instalatzaileak behin eskatzen du administratzaile-baimena; ukatu bazen, azpimenua **Erakutsi aukera gehiago** aukeran dago.

## Word dokumentu bat ez da bihurtzen

Microsoft Word edo LibreOffice instalatuta izan behar da. Biek huts egiten badute, AventyaPDF-k arrazoia erakusten du.

## Sinadura bat «identitatea egiaztatu gabe» ateratzen da

Sinadura ez da aldatu, baina haren ziurtagiria ez dago Windows-en biltegian ezta Espainiako konfiantza-zerrendan ere (adibidez, proba-ziurtagiri bat edo beste herrialde batekoa). Egiaztatu sinatzailearekin nongoa den haren ziurtagiria.

## Jakinarazi akats bat

«Ustekabeko errorea» leihoa agertzen bada, aplikazioak irekita jarraitzen du, eta xehetasunak `%LOCALAPPDATA%\aventyapdf` karpetan gordetzen dira (`errores.log` eta `fallos_graves.log` fitxategiak). Bidali fitxategi horiek, egiten ari zinenaren azalpen batekin, helbide honetara: github.com/Aventya/AventyaPDF/issues.
