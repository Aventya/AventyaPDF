---
titulo: Manuale di AventyaPDF
subtitulo: Visualizzare, commentare, organizzare, proteggere, convertire e firmare documenti PDF
version: Versione {version}
indice: Indice
meses: gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre
fecha: {mes} {anio}
cabecera: Manuale di AventyaPDF
consejo: Suggerimento
importante: Importante
atajos_tecla: Tasto
atajos_accion: Azione
muestra_titulo: Documento di esempio — pagina {n}
muestra_texto: Questo è un documento di esempio creato unicamente per mostrare gli strumenti di AventyaPDF nel manuale. Non contiene alcun dato reale né riferito a clienti.\n\nAventyaPDF è un'applicazione desktop per Windows che consente di visualizzare, commentare, organizzare, proteggere, convertire e firmare digitalmente documenti PDF.\n\nQuesto paragrafo serve a provare gli strumenti di commento: evidenziare il testo, sottolinearlo, barrarlo, selezionarlo e copiarlo, oppure aggiungere note adesive accanto a esso.
buscar: documento
resaltar: strumenti di commento
texto_anotacion: Testo aggiunto sulla pagina
nota_texto: Rivedere questo paragrafo prima di inviarlo.
formulario_titulo: Richiesta di esempio
campo_nombre: Nome e cognome
campo_fecha: Data
campo_importe: Importo
casilla: Accetto le condizioni
firmante: Mario Rossi
motivo: Conformità
lugar: Roma
contacto: nome@esempio.it
certificado_ejemplo: Certificato di esempio
nombre_doc1: Contratto.pdf
nombre_doc2: Fattura.pdf
nombre_doc3: Relazione.pdf
nombre_formulario: Richiesta.pdf
nombre_firmado: Contratto firmato.pdf
explorador_opciones: Apri|Apri con|Condividi
---

# Primi passi

## Che cos'è AventyaPDF

AventyaPDF è un'applicazione per Windows che riunisce in un unico programma tutto ciò che si fa ogni giorno con i documenti PDF: leggerli, commentarli, compilare moduli, modificarne il testo, organizzarne le pagine, combinarli, proteggerli con password, riconoscere il testo delle scansioni e firmarli con un certificato digitale.

È a distribuzione libera e il suo codice è pubblicato su GitHub. Non invia i tuoi documenti da nessuna parte: tutto avviene nel tuo computer.

![ventana] La finestra di AventyaPDF con tre documenti aperti.

## Installare e aggiornare

Il programma di installazione chiede per prima cosa la lingua (propone quella di Windows): AventyaPDF viene installato e si apre in quella lingua. Durante l'installazione vengono scaricati dai rispettivi siti ufficiali Python, i suoi componenti e i tipi di carattere, quindi serve una connessione a Internet. Nel frattempo il programma di installazione presenta gli strumenti dell'applicazione.

Al termine, AventyaPDF compare nel menu Start (e, se l'hai selezionato, sul desktop) e in **Apri con** dei file PDF. Windows non consente a un programma di impostarsi da solo come visualizzatore predefinito: se vuoi che i PDF si aprano sempre con AventyaPDF, sceglilo in **Apri con › Scegli un'altra app** e seleziona «Usa sempre questa app».

Quando è disponibile una nuova versione, AventyaPDF lo segnala all'avvio. Puoi anche verificarlo in **Guida › Verifica disponibilità aggiornamenti…**: il nuovo programma di installazione viene scaricato nella cartella Download e devi solo aprirlo. Le tue impostazioni, il tuo certificato e la tua lingua vengono mantenuti.

> **Importante:** il riconoscimento del testo (OCR) usa Tesseract OCR, che non è incluso nel programma di installazione. AventyaPDF lo scarica e lo installa la prima volta che lo usi; potrebbe chiedere l'autorizzazione di amministratore.

## La finestra

- **Barra dei menu**: tutte le funzioni, ordinate in File, Modifica, Visualizza, Commenta, Organizza, Strumenti, Proteggi, Firma e Guida.
- **Barra degli strumenti**: aprire, salvare, stampare e comprimere; annullare e ripristinare; la pagina corrente; l'adattamento dello zoom; gli strumenti di commento e di modifica; la firma; le operazioni sulle pagine e, a destra, la lente per cercare.
- **Riquadro laterale** (a sinistra, si apre e si chiude con **F4**): miniature delle pagine, segnalibri, commenti e firme certificate. Nella parte superiore del riquadro compaiono le opzioni dello strumento che stai usando.
- **Barra di stato** (in basso): messaggi dell'applicazione e, a destra, lo zoom.

## Presentazione, guida e lingua

La prima volta che apri AventyaPDF compare una presentazione che riassume le funzioni. Seleziona «Non mostrare più all'avvio» se non vuoi più vederla; puoi sempre riaprirla da **Guida › Presentazione di AventyaPDF**.

![presentacion] La presentazione iniziale.

Nel menu **Guida** trovi anche questo manuale (**Guida › Manuale di AventyaPDF**), l'elenco dei tasti di scelta rapida (**F1**) e la lingua dell'applicazione (**Guida › Lingua**). AventyaPDF è disponibile in spagnolo, inglese, francese, italiano, catalano, galiziano e basco; la nuova lingua si applica la prossima volta che apri l'applicazione.

![idioma] Guida › Lingua.

# Aprire, salvare e spostarsi nel documento

## Aprire documenti

Ci sono diversi modi per aprire documenti:

- **File › Apri…** (`Ctrl+O`): puoi scegliere più file contemporaneamente con `Ctrl` o `Maiusc`.
- Trascinarli da Esplora file nella finestra.
- **File › Apri recenti**, con gli ultimi documenti usati.
- Fare doppio clic su un PDF, se AventyaPDF è il tuo visualizzatore PDF.

Oltre ai PDF, AventyaPDF apre immagini (PNG, JPG, BMP, GIF, TIFF e WebP) e documenti di Word (.doc e .docx): ognuno viene convertito in un nuovo PDF, non salvato, nella propria scheda. L'originale non viene modificato. Per convertire documenti di Word è necessario avere installato Microsoft Word o LibreOffice.

Se il PDF è protetto da password, AventyaPDF la chiede prima di aprirlo.

## Più documenti insieme

Ogni documento aperto ha la sua scheda nel riquadro laterale, sotto le icone dei riquadri. Passando il mouse sopra si vedono il nome e la cartella, e un punto «●» indica che ci sono modifiche non salvate.

![pestanas] Le schede dei documenti aperti, nel riquadro laterale.

- Fai clic su una scheda per passare a quel documento, oppure usa `Ctrl+Tab` e `Ctrl+Maiusc+Tab`.
- Trascina una scheda in alto o in basso per cambiarne l'ordine.
- Con il clic destro su una scheda puoi chiudere quel documento (oppure usa `Ctrl+W`).

Ogni documento conserva la sua pagina, le sue modifiche e la sua cronologia di annullamento. Se apri un file già aperto, AventyaPDF passa semplicemente alla sua scheda.

## Spostarsi tra le pagine e zoom

- `PgGiù` e `PgSu` cambiano pagina; `Home` e `Fine` vanno alla prima e all'ultima. Anche la rotellina del mouse cambia pagina quando arriva al bordo.
- Scrivi un numero nella casella della pagina della barra degli strumenti, oppure usa **Visualizza › Vai alla pagina…** (`Ctrl+G`).
- Fai clic su una miniatura del riquadro laterale per andare a quella pagina. Il riquadro dei segnalibri mostra l'indice del documento, se presente.

Lo zoom si trova sempre in basso a destra: i pulsanti con la lente ingrandiscono e riducono, il dispositivo di scorrimento si trascina e nella casella si può scrivere la percentuale esatta (fino al 400%). Funzionano anche `Ctrl+rotellina`, `Ctrl++` e `Ctrl+-`. Il pulsante di adattamento della barra degli strumenti alterna tra adatta alla larghezza (`Ctrl+1`), adatta alla pagina (`Ctrl+2`) e dimensioni effettive (`Ctrl+0`).

![zoom] Lo zoom, nella barra di stato.

## Cercare e copiare testo

Premi `Ctrl+F` o la lente della barra degli strumenti e scrivi ciò che cerchi: le occorrenze vengono evidenziate nella pagina mentre scrivi e vengono contate («1 di 12»). Le frecce, `F3` e `Maiusc+F3` passano alla successiva e alla precedente; `Esc` chiude la ricerca.

![buscar] Cercare nel documento.

Per copiare, trascina il mouse sul testo con lo strumento di selezione e premi `Ctrl+C`. Ogni paragrafo viene incollato su una sola riga, senza le interruzioni di riga del PDF; anche il testo riconosciuto con l'OCR.

## Salvare, stampare e proprietà

- **File › Salva** (`Ctrl+S`) salva sullo stesso file; **Salva con nome…** (`Ctrl+Maiusc+S`), con un altro nome. Il titolo della finestra mostra «●» finché ci sono modifiche non salvate e, alla chiusura, ti viene chiesto se vuoi salvarle.
- **File › Stampa…** (`Ctrl+P`) apre la finestra di stampa di Windows.
- **File › Proprietà del documento…** (`Ctrl+D`) mostra e consente di modificare titolo, autore, oggetto e parole chiave e, nella scheda Informazioni, dati come il numero di pagine, le dimensioni o la presenza di firme.

![propiedades] Proprietà del documento.

## Annullare e ripristinare

Quasi tutto ciò che fai in un documento si può annullare con `Ctrl+Z` e ripristinare con `Ctrl+Y`: commenti, modifiche al testo, operazioni sulle pagine, filigrane, OCR… Ogni documento ha la propria cronologia.

# Commentare

Gli strumenti di commento si trovano nel menu **Commenta** e nella barra degli strumenti. Ognuno ha una lettera per sceglierlo rapidamente; `V` o `Esc` tornano allo strumento di selezione. Le opzioni dello strumento (colore, dimensione, spessore…) compaiono nella parte superiore del riquadro laterale.

## Aggiungere testo

Con lo strumento **Aggiungi testo** (`T`) fai clic sulla pagina (o trascina un riquadro) e scrivi direttamente sopra, senza finestre: il riquadro si allarga mentre scrivi. Nel riquadro laterale scegli dimensione, colore, grassetto e corsivo, allineamento e tipo di carattere, e le modifiche si vedono subito.

![texto] Testo scritto direttamente sulla pagina.

`Invio` inizia una nuova riga, `Ctrl+Invio` conferma ed `Esc` annulla. Anche fare clic altrove conferma. Per modificare un testo già inserito, fai doppio clic su di esso.

## Note adesive

La **Nota adesiva** (`N`) lascia un commento accanto alla pagina: fai clic dove vuoi lasciarla e scrivi. Sulla pagina si vede una piccola icona e il testo compare passandoci sopra con il mouse. Il colore della nota si sceglie nel riquadro laterale.

![nota] Una nota adesiva accanto al testo.

## Evidenziare, sottolineare e barrare

Con **Evidenzia, sottolinea o barra** (`H`) scegli il tipo di segno e il suo colore nel riquadro laterale e trascina sul testo. Se il testo non si può selezionare (un'immagine o una scansione), il segno viene disegnato a mano libera; un tratto rapido risulta diritto.

![resaltar] Testo evidenziato.

> **Suggerimento:** puoi anche selezionare il testo con lo strumento di selezione e fare clic destro per evidenziarlo, sottolinearlo o barrarlo.

## Rettangoli ed emoji

Il **Rettangolo** (`R`) riquadra una zona della pagina con un riquadro ad angoli arrotondati: trascina per disegnarlo, con il colore e lo spessore del riquadro laterale.

![rectangulo] Un rettangolo intorno al titolo.

Lo strumento **Emoji** (`E`) inserisce una qualsiasi delle oltre 1.300 emoji, con ricerca e gruppi, nella dimensione, nel colore e con l'opacità che preferisci: scegline una e fai clic dove andrà.

![emoji] Scegliere un'emoji.

## Spostare, modificare ed eliminare commenti

Con lo strumento di selezione, fai clic su un commento per selezionarlo: si può spostare trascinandolo, ridimensionare con le sue maniglie ed eliminare con `Canc`. La **Gomma per annotazioni** rimuove i commenti con un clic.

Il riquadro **Commenti** del riquadro laterale elenca tutti i commenti del documento con la relativa pagina; facendo clic su uno, la vista si sposta su di esso e rimane selezionato.

![comentarios] Il riquadro Commenti.

## Appiattire

**Commenta › Appiattisci annotazioni e moduli…** trasforma i commenti e i campi modulo in parte del contenuto della pagina: si vedono uguali, ma non si possono più spostare né modificare. È utile prima di inviare una versione definitiva.

# Modificare il contenuto del PDF

Lo strumento **Modifica testo e immagini del PDF** (`C`, nel menu Strumenti) modifica il testo e le immagini che fanno già parte del documento, non commenti sovrapposti. Quando lo scegli, ogni paragrafo viene incorniciato in blu e ogni immagine in verde.

![editar] I paragrafi e le immagini modificabili, incorniciati.

**Testo.** Fai clic su un paragrafo e scrivi: il testo si distribuisce sulle righe necessarie all'interno del suo riquadro, con lo stesso tipo di carattere, dimensione e colore quando possibile. Nel riquadro laterale puoi cambiare dimensione, colore, grassetto o corsivo. Se il testo non ci sta, il riquadro diventa rosso: trascina uno dei suoi angoli per ingrandirlo. `Ctrl+Invio` conferma, `Esc` annulla e `Tab` passa al paragrafo successivo. Lasciare vuoto un paragrafo lo elimina.

**Immagini.** Fai clic su un'immagine per selezionarla: trascinala per spostarla, trascina un angolo per ridimensionarla (senza deformarla) o premi `Canc` per eliminarla. Con il clic destro puoi sostituirla con un'altra immagine o salvarla in un file.

> **Importante:** se il documento usa un tipo di carattere non disponibile, AventyaPDF usa quello più simile e lo segnala nella barra di stato. Controlla il risultato prima di salvare.

# Compilare moduli

I campi dei moduli sono evidenziati in blu (puoi disattivarlo in **Visualizza › Evidenzia campi modulo**). Non serve alcuno strumento speciale:

- Fai clic su un campo di testo e scrivi; `Tab` passa al campo successivo e `Maiusc+Tab` a quello precedente.
- Le caselle di controllo e i pulsanti di opzione si selezionano con un clic; gli elenchi mostrano i loro valori.
- I calcoli, le convalide e i pulsanti del modulo funzionano come in Adobe Acrobat.

![formulario] Un modulo con i campi evidenziati.

Se il modulo ha un riquadro di firma vuoto, fai clic su di esso per firmare al suo interno (lo vedrai nel capitolo sulla firma).

# Organizzare le pagine

## Operazioni sulle pagine

Il pulsante **Operazioni sulle pagine** della barra degli strumenti (o **Organizza › Organizza pagine nel riquadro laterale**) apre le miniature in modalità organizzazione, con una fila di pulsanti in alto.

![organizar] Le operazioni sulle pagine nel riquadro laterale.

- **Riordinare**: trascina una miniatura nella nuova posizione.
- **Selezionarne più di una**: con `Ctrl` o `Maiusc` mentre fai clic. Senza selezione, i pulsanti agiscono sulla pagina corrente.
- **Pulsanti**: ruota a sinistra e a destra, duplica, elimina, inserisci una pagina vuota, inserisci un altro PDF, estrai le pagine in un nuovo PDF e ritaglia.

Tutto si applica subito e si può annullare.

## Ritagliare una pagina

Il pulsante **Ritaglia** disegna sulla pagina un riquadro con maniglie sugli angoli e sui lati: trascina ciascuna fino al margine che desideri. I pulsanti al centro del riquadro applicano o annullano il ritaglio.

![recortar] Ritagliare una pagina.

## Il menu Organizza

Nel menu **Organizza** si trovano anche:

- **Inserisci pagina vuota**, **Inserisci PDF dopo la pagina corrente…** e **Aggiungi PDF alla fine…**
- **Duplica pagina corrente**, **Elimina pagine…** ed **Estrai pagine…**, con intervalli come «1-3, 5, 8-».
- **Dividi documento…**: salva il documento in parti con un numero fisso di pagine.
- **Ruota pagina a destra** (`Ctrl+Maiusc+R`), **a sinistra** (`Ctrl+Maiusc+L`) e **Ruota pagine…** per intervalli.

## Combinare documenti

**Organizza › Combina PDF…** offre due opzioni:

- **Combina aperti**: unisce tutti i documenti aperti, nell'ordine delle schede e con le loro modifiche, in un nuovo PDF.
- **Combina file…**: scegli più file (PDF, immagini o Word, anche misti), che vengono combinati in ordine alfabetico di nome.

![combinar] Organizza › Combina PDF.

Il risultato rimane aperto e non salvato; salvalo con `Ctrl+S`. I file originali non cambiano.

# Creare, convertire ed esportare

## Creare documenti

- **File › Nuovo PDF vuoto** (`Ctrl+N`) crea un documento con una pagina vuota.
- **File › Crea PDF da immagini…** unisce più immagini in un PDF, una per pagina.
- Aprire un'immagine o un documento di Word lo converte in PDF (vedi «Aprire documenti»).

## Esportare

In **File › Esporta** puoi estrarre il contenuto del documento:

- **Pagine come immagini…**: PNG o JPG, alla risoluzione che scegli.
- **Testo (.txt)…**: tutto il testo del documento.
- **Documento di Word (.docx)…**: un documento modificabile in Word.
- **Estrai pagine in PDF…**: solo le pagine che indichi.

![exportar] Esportare le pagine come immagini.

## Da Esplora file

Senza aprire prima l'applicazione, seleziona i file in Esplora file e fai clic destro: nel sottomenu **AventyaPDF** trovi:

- **Firma digitalmente** (solo PDF): apre i documenti con lo strumento di firma pronto.
- **Combina in un PDF** (due o più file): PDF, immagini e Word, anche misti, in un unico PDF.
- **Converti in PDF** (immagini e Word): un PDF per ogni file.

![explorador] Il sottomenu AventyaPDF del clic destro.

In Windows 11 il sottomenu si trova nel menu principale del clic destro; in Windows 10, e in Windows 11 all'interno di **Mostra altre opzioni**, si trova nel menu classico.

> **Suggerimento:** se il sottomenu scompare (per esempio dopo un aggiornamento di Windows), usa **Guida › Ripara il menu contestuale di Esplora file…**

# Strumenti

## Filigrana

**Strumenti › Filigrana…** scrive un testo sulle pagine che scegli, con la dimensione, il colore, l'opacità e l'angolo che preferisci (per esempio «RISERVATO» in diagonale).

![marca_agua] Filigrana.

## Intestazione, piè di pagina e numerazione Bates

**Strumenti › Intestazione, piè di pagina e numerazione Bates…** aggiunge fino a tre testi nell'intestazione e tre nel piè di pagina (a sinistra, al centro e a destra). Puoi usare delle variabili:

- `{n}`: il numero di pagina; `{total}`: il numero totale di pagine.
- `{fecha}`: la data odierna.
- `{bates}`: un numero progressivo Bates, con prefisso, numero iniziale e cifre.

![encabezado] Intestazione, piè di pagina e numerazione Bates.

## Riconoscere il testo (OCR)

**Strumenti › Riconosci testo (OCR)…** trasforma in testo selezionabile e ricercabile quello delle pagine scansionate, delle foto e delle immagini. Scegli la lingua del documento, se riconoscere tutte le pagine o solo quelle senza testo, e se correggere l'orientamento di ogni pagina.

![ocr] Riconoscere il testo (OCR).

Il testo viene aggiunto come livello invisibile: l'aspetto della pagina non cambia, ma il testo si può già cercare, selezionare e copiare. Se scegli una nuova lingua, AventyaPDF ne scarica prima i dati.

## Ottimizzare e comprimere

Il pulsante **Comprimi PDF** della barra degli strumenti (o **Strumenti › Ottimizza e comprimi…**) riduce le dimensioni del file, soprattutto quando contiene immagini. Scegli il livello (alta qualità, buona qualità o massima riduzione) e salva la copia compressa; l'originale non cambia.

![comprimir] Le opzioni di compressione.

# Proteggere con password

**Proteggi › Proteggi con password…** crittografa il documento con AES a 256 bit:

- **Password di apertura del documento**: senza di essa il documento non si può aprire.
- **Password delle autorizzazioni**: limita stampa, copia, modifica o commenti, anche se il documento si può aprire senza password.

![proteger] Proteggere con password.

La protezione si applica al salvataggio. **Proteggi › Rimuovi protezione** elimina la password e le autorizzazioni di un documento che hai aperto con la sua password.

> **Importante:** se dimentichi la password di apertura, non c'è modo di recuperare il documento. Conservala in un luogo sicuro.

# Firmare

AventyaPDF firma con firma elettronica avanzata PAdES, quella usata nei documenti ufficiali europei, con certificati qualificati come quelli della FNMT spagnola o del DNIe (la carta d'identità elettronica spagnola).

## Il certificato

In **Firma › Certificato di firma…** scegli con quale certificato firmare:

- **Archivio di Windows**: i certificati installati nel tuo computer, compresi quelli su smart card e del DNIe. La chiave non esce mai dall'archivio; se serve un PIN, lo chiede Windows.
- **File .pfx / .p12**: un certificato in un file .pfx o .p12. La password può essere salvata in Gestione credenziali di Windows per non doverla digitare ogni volta.

Il certificato scelto viene ricordato per le firme successive.

## Firmare un documento

Scegli lo strumento **Firma** (o **Firma › Firma documento (disegna area)**) e disegna sulla pagina il riquadro in cui andrà la firma visibile. Nel riquadro laterale si vede il certificato attivo e lo si può cambiare.

![firmar] Lo strumento di firma, con il certificato attivo.

Poi compaiono le **Opzioni di firma** e infine AventyaPDF chiede dove salvare il documento firmato (propone lo stesso nome con la desinenza «_firmato»). L'originale non viene modificato.

![opciones_firma] Opzioni di firma.

- **Motivo, luogo e contatto**: compaiono nel timbro visibile e nei dati della firma. Il timbro appare nella lingua dell'applicazione.
- **Aggiungi marca temporale qualificata (PAdES-B-T)**: un'autorità di marcatura temporale certifica la data e l'ora della firma. Richiede Internet.
- **Certifica il documento**: dopo la firma si potranno solo compilare moduli e aggiungere altre firme; qualsiasi altra modifica invaliderà la certificazione.
- **Non chiedere più**: firma direttamente con queste opzioni (si modifica in **Firma › Opzioni di firma…**).

Un documento si può firmare più volte: ogni nuova firma si aggiunge senza invalidare le precedenti, purché tra l'una e l'altra non siano state fatte modifiche.

## Firmare nel riquadro di un modulo

Se il documento ha un riquadro di firma vuoto (come molti moduli della Pubblica Amministrazione), fai clic su di esso: AventyaPDF chiede il certificato e firma all'interno di quel riquadro.

## Firma autografa

**Firma › Inserisci firma autografa (disegnata o immagine)…**, o il pennino del riquadro di firma, apre un'area di disegno in cui tracciare la tua firma con il mouse, con tratto stilografico e il colore e lo spessore che preferisci. Puoi anche caricare l'immagine della tua firma scansionata (lo sfondo bianco della carta viene rimosso).

![manuscrita] Disegnare la firma autografa.

Poi fai clic sulla pagina per posizionarla, oppure trascina un riquadro per definirne le dimensioni. Diventa un commento come gli altri: si sposta, si ridimensiona e si elimina.

> **Importante:** la firma autografa è solo un'immagine. Non ha valore di firma elettronica; per questo, firma con un certificato.

## Verificare le firme

Il riquadro **Firme certificate** del riquadro laterale (o **Firma › Visualizza le firme (verificate)**) verifica automaticamente ogni firma del documento:

- se il documento è stato alterato dopo la firma;
- se il certificato è attendibile, secondo l'archivio di Windows e l'elenco di fiducia ufficiale della Spagna (FNMT, DNIe, Colegio de Registradores, Izenpe, ACCV e gli altri prestatori qualificati);
- la data dichiarata, la marca temporale e l'eventuale presenza di modifiche successive.

![firmas] Il riquadro Firme certificate.

La firma più recente ha un cestino che la rimuove e lascia vuoto il suo riquadro per firmare di nuovo (per esempio con un altro certificato). La modifica si applica al salvataggio.

# Tasti di scelta rapida

**Guida › Tasti di scelta rapida** (`F1`) mostra questo stesso elenco all'interno dell'applicazione.

[[atajos]]

# Se qualcosa non funziona

## L'OCR non è disponibile

Tesseract OCR viene installato la prima volta che riconosci un testo e richiede Internet (e, a volte, l'autorizzazione di amministratore). Se l'autorizzazione è stata negata o non c'era connessione, AventyaPDF riprova la volta successiva che lo apri.

## Il sottomenu AventyaPDF non compare in Esplora file

Usa **Guida › Ripara il menu contestuale di Esplora file…**. In Windows 11, perché il sottomenu sia nel menu principale, il programma di installazione chiede una sola volta l'autorizzazione di amministratore; se è stata negata, il sottomenu si trova in **Mostra altre opzioni**.

## Un documento di Word non viene convertito

Serve Microsoft Word o LibreOffice installato. Se entrambi non riescono, AventyaPDF ne mostra il motivo.

## Una firma risulta come «identità non verificata»

La firma non è stata alterata, ma il suo certificato non è nell'archivio di Windows né nell'elenco di fiducia della Spagna (per esempio un certificato di prova o di un altro paese). Verifica con il firmatario la provenienza del suo certificato.

## Segnalare un errore

Se compare una finestra di «Errore imprevisto», l'applicazione rimane aperta e il dettaglio viene salvato nella cartella `%LOCALAPPDATA%\aventyapdf` (file `errores.log` e `fallos_graves.log`). Invia questi file, con una descrizione di ciò che stavi facendo, su github.com/Aventya/AventyaPDF/issues.
