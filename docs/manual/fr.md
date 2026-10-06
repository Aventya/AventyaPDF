---
titulo: Manuel d'AventyaPDF
subtitulo: Afficher, commenter, organiser, protéger, convertir et signer des documents PDF
version: Version {version}
indice: Sommaire
meses: janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre
fecha: {mes} {anio}
cabecera: Manuel d'AventyaPDF
consejo: Conseil
importante: Important
atajos_tecla: Touche
atajos_accion: Action
muestra_titulo: Document d'exemple — page {n}
muestra_texto: Ceci est un document d'exemple créé uniquement pour présenter les outils d'AventyaPDF dans le manuel. Il ne contient aucune donnée réelle ni aucune donnée client.\n\nAventyaPDF est une application de bureau pour Windows qui permet d'afficher, de commenter, d'organiser, de protéger, de convertir et de signer numériquement des documents PDF.\n\nCe paragraphe sert à essayer les outils de commentaire : surligner du texte, le souligner, le barrer, le sélectionner et le copier, ou ajouter des notes autocollantes à côté.
buscar: document
resaltar: outils de commentaire
texto_anotacion: Texte ajouté sur la page
nota_texto: Relire ce paragraphe avant de l'envoyer.
formulario_titulo: Exemple de demande
campo_nombre: Nom et prénom
campo_fecha: Date
campo_importe: Montant
casilla: J'accepte les conditions
firmante: Camille Martin
motivo: Accord
lugar: Lyon
contacto: contact@exemple.fr
certificado_ejemplo: Certificat d'exemple
nombre_doc1: Contrat.pdf
nombre_doc2: Facture.pdf
nombre_doc3: Rapport.pdf
nombre_formulario: Demande.pdf
nombre_firmado: Contrat signé.pdf
explorador_opciones: Ouvrir|Ouvrir avec|Partager
---

# Premiers pas

## Qu'est-ce qu'AventyaPDF ?

AventyaPDF est une application pour Windows qui réunit dans un seul programme ce que l'on fait tous les jours avec les documents PDF : les lire, les commenter, remplir des formulaires, modifier leur texte, organiser leurs pages, les combiner, les protéger par mot de passe, reconnaître le texte des numérisations et les signer avec un certificat numérique.

Elle est en libre diffusion et son code source est publié sur GitHub. Elle n'envoie vos documents nulle part : tout se fait sur votre ordinateur.

![ventana] La fenêtre d'AventyaPDF avec trois documents ouverts.

## Installer et mettre à jour

Le programme d'installation demande d'abord la langue (il propose celle de Windows) : AventyaPDF est installé et s'ouvre dans cette langue. Pendant l'installation, Python, ses composants et les polices de caractères sont téléchargés depuis leurs sites officiels : une connexion Internet est donc nécessaire. En attendant, le programme d'installation présente les outils de l'application.

Une fois l'installation terminée, AventyaPDF apparaît dans le menu Démarrer (et, si vous avez coché l'option, sur le Bureau) ainsi que dans **Ouvrir avec** pour les fichiers PDF. Windows ne permet pas à un programme de se définir lui-même comme visionneuse par défaut : si vous voulez que les PDF s'ouvrent toujours avec AventyaPDF, choisissez-le dans **Ouvrir avec › Choisir une autre application** et cochez « Toujours utiliser cette application ».

Lorsqu'une nouvelle version est disponible, AventyaPDF vous en informe au démarrage. Vous pouvez aussi le vérifier dans **Aide › Rechercher des mises à jour…** : le nouveau programme d'installation est téléchargé dans votre dossier Téléchargements et il vous suffit de l'ouvrir. Vos réglages, votre certificat et votre langue sont conservés.

> **Important :** la reconnaissance de texte (OCR) utilise Tesseract OCR, qui n'est pas inclus dans le programme d'installation. AventyaPDF le télécharge et l'installe la première fois que vous l'utilisez ; une autorisation d'administrateur peut être demandée.

## La fenêtre

- **Barre de menus** : toutes les fonctions, classées dans Fichier, Édition, Affichage, Commenter, Organiser, Outils, Protéger, Signer et Aide.
- **Barre d'outils** : ouvrir, enregistrer, imprimer et compresser ; annuler et rétablir ; la page active ; l'ajustement du zoom ; les outils de commentaire et de modification ; la signature ; les opérations sur les pages et, à droite, la loupe de recherche.
- **Volet latéral** (à gauche, il s'ouvre et se ferme avec **F4**) : miniatures des pages, signets, commentaires et signatures certifiées. En haut du volet apparaissent les options de l'outil que vous utilisez.
- **Barre d'état** (en bas) : messages de l'application et, à droite, le zoom.

## Présentation, aide et langue

À la première ouverture d'AventyaPDF, une présentation résume les fonctions. Cochez « Ne plus afficher au démarrage » si vous ne voulez plus la voir ; vous pouvez toujours la rouvrir depuis **Aide › Présentation d'AventyaPDF**.

![presentacion] La présentation de démarrage.

Le menu **Aide** contient aussi ce manuel (**Aide › Manuel d'AventyaPDF**), la liste des raccourcis clavier (**F1**) et la langue de l'application (**Aide › Langue**). AventyaPDF existe en espagnol, anglais, français, italien, catalan, galicien et basque ; la nouvelle langue s'applique à la prochaine ouverture de l'application.

![idioma] Aide › Langue.

# Ouvrir, enregistrer et parcourir le document

## Ouvrir des documents

Il existe plusieurs façons d'ouvrir des documents :

- **Fichier › Ouvrir…** (`Ctrl+O`) : vous pouvez sélectionner plusieurs fichiers à la fois avec `Ctrl` ou `Maj`.
- Les faire glisser depuis l'Explorateur Windows dans la fenêtre.
- **Fichier › Ouvrir un fichier récent**, avec les derniers documents utilisés.
- Double-cliquer sur un PDF, si AventyaPDF est votre visionneuse PDF.

Outre les PDF, AventyaPDF ouvre les images (PNG, JPG, BMP, GIF, TIFF et WebP) et les documents Word (.doc et .docx) : chacun est converti en un nouveau PDF, non enregistré, dans son propre onglet. L'original n'est pas modifié. Pour convertir des documents Word, Microsoft Word ou LibreOffice doit être installé.

Si le PDF est protégé par mot de passe, AventyaPDF le demande avant de l'ouvrir.

## Plusieurs documents à la fois

Chaque document ouvert a son onglet dans le volet latéral, sous les icônes des volets. En passant la souris dessus, vous voyez son nom et son dossier ; un point « ● » indique qu'il contient des modifications non enregistrées.

![pestanas] Les onglets des documents ouverts, dans le volet latéral.

- Cliquez sur un onglet pour passer à ce document, ou utilisez `Ctrl+Tab` et `Ctrl+Maj+Tab`.
- Faites glisser un onglet vers le haut ou le bas pour changer l'ordre.
- Un clic droit sur un onglet permet de fermer ce document (ou utilisez `Ctrl+W`).

Chaque document conserve sa page, ses modifications et son historique d'annulation. Si vous ouvrez un fichier déjà ouvert, AventyaPDF se contente d'afficher son onglet.

## Parcourir les pages et zoomer

- `Pg.Suiv` et `Pg.Préc` changent de page ; `Début` et `Fin` vont à la première et à la dernière. La molette de la souris change aussi de page en arrivant au bord.
- Tapez un numéro dans la zone de page de la barre d'outils, ou utilisez **Affichage › Atteindre la page…** (`Ctrl+G`).
- Cliquez sur une miniature du volet latéral pour aller à cette page. Le volet des signets affiche la table des matières du document, s'il en a une.

Le zoom se trouve toujours en bas à droite : les boutons loupe font un zoom avant ou arrière, le curseur se fait glisser et la zone permet de taper le pourcentage exact (jusqu'à 400 %). `Ctrl+molette`, `Ctrl++` et `Ctrl+-` fonctionnent aussi. Le bouton d'ajustement de la barre d'outils alterne entre l'ajustement à la largeur (`Ctrl+1`), l'ajustement à la page (`Ctrl+2`) et la taille réelle (`Ctrl+0`).

![zoom] Le zoom, dans la barre d'état.

## Rechercher et copier du texte

Appuyez sur `Ctrl+F` ou cliquez sur la loupe de la barre d'outils et tapez ce que vous cherchez : les occurrences sont surlignées sur la page au fur et à mesure de la saisie et comptées (« 1 sur 12 »). Les flèches, `F3` et `Maj+F3` passent à la suivante et à la précédente ; `Échap` ferme la recherche.

![buscar] Rechercher dans le document.

Pour copier, faites glisser la souris sur le texte avec l'outil de sélection et appuyez sur `Ctrl+C`. Chaque paragraphe est collé sur une seule ligne, sans les retours à la ligne du PDF ; cela vaut aussi pour le texte reconnu par OCR.

## Enregistrer, imprimer et propriétés

- **Fichier › Enregistrer** (`Ctrl+S`) enregistre dans le même fichier ; **Enregistrer sous…** (`Ctrl+Maj+S`), sous un autre nom. Le titre de la fenêtre affiche « ● » tant qu'il reste des modifications non enregistrées, et à la fermeture l'application vous demande si vous voulez les enregistrer.
- **Fichier › Imprimer…** (`Ctrl+P`) ouvre la boîte de dialogue d'impression de Windows.
- **Fichier › Propriétés du document…** (`Ctrl+D`) affiche et permet de modifier le titre, l'auteur, l'objet et les mots clés, et, dans l'onglet Informations, des données comme le nombre de pages, la taille ou la présence de signatures.

![propiedades] Propriétés du document.

## Annuler et rétablir

Presque tout ce que vous faites dans un document peut être annulé avec `Ctrl+Z` et rétabli avec `Ctrl+Y` : commentaires, modifications de texte, opérations sur les pages, filigranes, OCR… Chaque document a son propre historique.

# Commenter

Les outils de commentaire se trouvent dans le menu **Commenter** et dans la barre d'outils. Chacun a une lettre pour le choisir rapidement ; `V` ou `Échap` reviennent à l'outil de sélection. Les options de l'outil (couleur, taille, épaisseur…) apparaissent en haut du volet latéral.

## Ajouter du texte

Avec l'outil **Ajouter du texte** (`T`), cliquez sur la page (ou faites glisser un cadre) et tapez directement dessus, sans fenêtre : le cadre s'agrandit au fur et à mesure de la saisie. Dans le volet latéral, vous choisissez la taille, la couleur, le gras et l'italique, l'alignement et la police, et les modifications s'affichent immédiatement.

![texto] Texte saisi directement sur la page.

`Entrée` ouvre une nouvelle ligne, `Ctrl+Entrée` valide et `Échap` annule. Cliquer ailleurs valide également. Pour modifier un texte déjà placé, double-cliquez dessus.

## Notes autocollantes

La **Note autocollante** (`N`) laisse un commentaire sur la page : cliquez à l'endroit voulu et tapez. Une petite icône s'affiche sur la page, et le texte apparaît quand vous passez la souris dessus. La couleur de la note se choisit dans le volet latéral.

![nota] Une note autocollante à côté du texte.

## Surligner, souligner et barrer

Avec **Surligner, souligner ou barrer** (`H`), choisissez le type de marque et sa couleur dans le volet latéral, puis faites glisser sur le texte. Si le texte ne peut pas être sélectionné (une image ou une numérisation), la marque est tracée à main levée ; un trait rapide est redressé.

![resaltar] Texte surligné.

> **Conseil :** vous pouvez aussi sélectionner du texte avec l'outil de sélection et faire un clic droit pour le surligner, le souligner ou le barrer.

## Rectangles et emojis

Le **Rectangle** (`R`) encadre une zone de la page d'un cadre aux coins arrondis : faites glisser pour le dessiner, avec la couleur et l'épaisseur du volet latéral.

![rectangulo] Un rectangle autour du titre.

L'outil **Emoji** (`E`) insère l'un des plus de 1 300 emojis, avec recherche et catégories, dans la taille, la couleur et l'opacité de votre choix : choisissez-en un et cliquez à l'endroit où le placer.

![emoji] Choisir un emoji.

## Déplacer, modifier et supprimer des commentaires

Avec l'outil de sélection, cliquez sur un commentaire pour le sélectionner : vous pouvez le déplacer en le faisant glisser, le redimensionner avec ses poignées et le supprimer avec `Suppr`. La **Gomme d'annotations** efface les commentaires d'un clic.

Le volet **Commentaires** du volet latéral répertorie tous les commentaires du document avec leur page ; un clic sur l'un d'eux affiche la page correspondante et le sélectionne.

![comentarios] Le volet Commentaires.

## Aplatir

**Commenter › Aplatir les annotations et les formulaires…** intègre les commentaires et les champs de formulaire au contenu de la page : leur aspect ne change pas, mais ils ne peuvent plus être déplacés ni modifiés. C'est utile avant d'envoyer une version définitive.

# Modifier le contenu du PDF

L'outil **Modifier le texte et les images du PDF** (`C`, dans le menu Outils) modifie le texte et les images qui font déjà partie du document, et non des commentaires ajoutés par-dessus. Lorsque vous le choisissez, chaque paragraphe est encadré en bleu et chaque image en vert.

![editar] Les paragraphes et les images modifiables, encadrés.

**Texte.** Cliquez sur un paragraphe et tapez : le texte se répartit sur autant de lignes que nécessaire dans son cadre, avec la même police, la même taille et la même couleur chaque fois que possible. Dans le volet latéral, vous pouvez changer la taille, la couleur, le gras ou l'italique. Si le texte ne tient pas, le cadre devient rouge : étirez l'un de ses coins pour l'agrandir. `Ctrl+Entrée` valide, `Échap` annule et `Tab` passe au paragraphe suivant. Un paragraphe laissé vide est supprimé.

**Images.** Cliquez sur une image pour la sélectionner : faites-la glisser pour la déplacer, étirez un coin pour la redimensionner (sans la déformer) ou appuyez sur `Suppr` pour la supprimer. Un clic droit permet de la remplacer par une autre image ou de l'enregistrer dans un fichier.

> **Important :** si le document utilise une police qui n'est pas disponible, AventyaPDF utilise la plus proche et le signale dans la barre d'état. Vérifiez le résultat avant d'enregistrer.

# Remplir des formulaires

Les champs des formulaires sont mis en évidence en bleu (vous pouvez désactiver cette option dans **Affichage › Mettre en évidence les champs de formulaire**). Aucun outil particulier n'est nécessaire :

- Cliquez sur un champ de texte et tapez ; `Tab` passe au champ suivant et `Maj+Tab` au précédent.
- Les cases à cocher et les boutons d'option se cochent d'un clic ; les listes déroulent leurs valeurs.
- Les calculs, les validations et les boutons du formulaire fonctionnent comme dans Adobe Acrobat.

![formulario] Un formulaire avec ses champs mis en évidence.

Si le formulaire contient un cadre de signature vide, cliquez dessus pour signer à l'intérieur (voir le chapitre sur la signature).

# Organiser les pages

## Opérations sur les pages

Le bouton **Opérations sur les pages** de la barre d'outils (ou **Organiser › Organiser les pages dans le volet latéral**) affiche les miniatures en mode organisation, avec une rangée de boutons au-dessus.

![organizar] Les opérations sur les pages dans le volet latéral.

- **Réordonner** : faites glisser une miniature vers sa nouvelle position.
- **Sélectionner plusieurs pages** : avec `Ctrl` ou `Maj` en cliquant. Sans sélection, les boutons agissent sur la page active.
- **Boutons** : faire pivoter à gauche et à droite, dupliquer, supprimer, insérer une page vierge, insérer un autre PDF, extraire les pages dans un nouveau PDF et rogner.

Tout s'applique immédiatement et peut être annulé.

## Rogner une page

Le bouton **Rogner** affiche sur la page un cadre avec des poignées aux coins et sur les côtés : faites glisser chacune jusqu'à la marge voulue. Les boutons au centre du cadre appliquent ou annulent le rognage.

![recortar] Rogner une page.

## Le menu Organiser

Le menu **Organiser** propose aussi :

- **Insérer une page vierge**, **Insérer un PDF après la page active…** et **Ajouter un PDF à la fin…**
- **Dupliquer la page active**, **Supprimer des pages…** et **Extraire des pages…**, avec des plages comme « 1-3, 5, 8- ».
- **Fractionner le document…** : enregistre le document en parties d'un nombre fixe de pages.
- **Faire pivoter la page à droite** (`Ctrl+Maj+R`), **à gauche** (`Ctrl+Maj+L`) et **Faire pivoter des pages…** par plages.

## Combiner des documents

**Organiser › Combiner des PDF…** propose deux options :

- **Combiner les documents ouverts** : réunit tous les documents ouverts, dans l'ordre de leurs onglets et avec leurs modifications, dans un nouveau PDF.
- **Combiner des fichiers…** : vous choisissez plusieurs fichiers (PDF, images ou Word, mélangés), qui sont combinés par ordre alphabétique de nom.

![combinar] Organiser › Combiner des PDF.

Le résultat reste ouvert sans être enregistré ; enregistrez-le avec `Ctrl+S`. Les fichiers d'origine ne changent pas.

# Créer, convertir et exporter

## Créer des documents

- **Fichier › Nouveau PDF vierge** (`Ctrl+N`) crée un document avec une page vide.
- **Fichier › Créer un PDF à partir d'images…** réunit plusieurs images dans un PDF, une par page.
- Ouvrir une image ou un document Word le convertit en PDF (voir « Ouvrir des documents »).

## Exporter

Dans **Fichier › Exporter**, vous pouvez extraire le contenu du document :

- **Pages en images…** : PNG ou JPG, à la résolution de votre choix.
- **Texte (.txt)…** : tout le texte du document.
- **Document Word (.docx)…** : un document modifiable dans Word.
- **Extraire des pages vers un PDF…** : uniquement les pages indiquées.

![exportar] Exporter des pages en images.

## Depuis l'Explorateur Windows

Sans ouvrir l'application, sélectionnez des fichiers dans l'Explorateur Windows et faites un clic droit : le sous-menu **AventyaPDF** propose :

- **Signer numériquement** (PDF uniquement) : ouvre les documents avec l'outil de signature prêt à l'emploi.
- **Combiner en un PDF** (deux fichiers ou plus) : PDF, images et Word, mélangés, dans un seul PDF.
- **Convertir en PDF** (images et Word) : un PDF par fichier.

![explorador] Le sous-menu AventyaPDF du clic droit.

Sous Windows 11, le sous-menu se trouve dans le menu principal du clic droit ; sous Windows 10, et sous Windows 11 dans **Afficher plus d'options**, il se trouve dans le menu classique.

> **Conseil :** si le sous-menu disparaît (par exemple après une mise à jour de Windows), utilisez **Aide › Réparer le menu contextuel de l'Explorateur…**

# Outils

## Filigrane

**Outils › Filigrane…** écrit un texte sur les pages de votre choix, avec la taille, la couleur, l'opacité et l'angle voulus (par exemple « CONFIDENTIEL » en diagonale).

![marca_agua] Filigrane.

## En-tête, pied de page et numérotation Bates

**Outils › En-tête, pied de page et numérotation Bates…** ajoute jusqu'à trois textes dans l'en-tête et trois dans le pied de page (à gauche, au centre et à droite). Vous pouvez utiliser des variables :

- `{n}` : le numéro de page ; `{total}` : le nombre total de pages.
- `{fecha}` : la date du jour.
- `{bates}` : un numéro Bates séquentiel, avec préfixe, numéro de départ et nombre de chiffres.

![encabezado] En-tête, pied de page et numérotation Bates.

## Reconnaître le texte (OCR)

**Outils › Reconnaître le texte (OCR)…** transforme en texte sélectionnable et consultable par recherche celui des pages numérisées, des photos et des images. Choisissez la langue du document, s'il faut reconnaître toutes les pages ou seulement celles sans texte, et s'il faut corriger l'orientation de chaque page.

![ocr] Reconnaître le texte (OCR).

Le texte est ajouté sous forme de calque invisible : l'aspect de la page ne change pas, mais il devient possible de rechercher, sélectionner et copier le texte. Si vous choisissez une nouvelle langue, AventyaPDF télécharge d'abord ses données.

## Optimiser et compresser

Le bouton **Compresser le PDF** de la barre d'outils (ou **Outils › Optimiser et compresser…**) réduit la taille du fichier, surtout lorsqu'il contient des images. Choisissez le niveau (haute qualité, bonne qualité ou réduction maximale) et enregistrez la copie compressée ; l'original ne change pas.

![comprimir] Les options de compression.

# Protéger par mot de passe

**Protéger › Protéger par mot de passe…** chiffre le document en AES 256 bits :

- **Mot de passe d'ouverture du document** : sans lui, le document ne peut pas être ouvert.
- **Mot de passe des autorisations** : restreint l'impression, la copie, la modification ou les commentaires, même si le document peut être ouvert sans mot de passe.

![proteger] Protéger par mot de passe.

La protection s'applique à l'enregistrement. **Protéger › Supprimer la sécurité** supprime le mot de passe et les autorisations d'un document que vous avez ouvert avec son mot de passe.

> **Important :** si vous oubliez le mot de passe d'ouverture, il est impossible de récupérer le document. Conservez-le en lieu sûr.

# Signer

AventyaPDF signe avec une signature électronique avancée PAdES, celle utilisée dans les documents officiels européens, avec des certificats qualifiés comme ceux de la FNMT ou du DNIe espagnols.

## Le certificat

Dans **Signer › Certificat de signature…**, vous choisissez le certificat utilisé pour signer :

- **Magasin Windows** : les certificats installés sur votre ordinateur, y compris ceux des cartes à puce et du DNIe. La clé ne quitte jamais le magasin ; si un code PIN est nécessaire, c'est Windows qui le demande.
- **Fichier .pfx / .p12** : un certificat enregistré dans un fichier. Le mot de passe peut être enregistré dans le Gestionnaire d'identification Windows pour ne pas avoir à le saisir à chaque fois.

Le certificat choisi est mémorisé pour les signatures suivantes.

## Signer un document

Choisissez l'outil **Signature** (ou **Signer › Signer le document (dessiner la zone)**) et dessinez sur la page le cadre où placer la signature visible. Le volet latéral affiche le certificat actif, que vous pouvez changer.

![firmar] L'outil de signature, avec le certificat actif.

Viennent ensuite les **options de signature**, puis AventyaPDF vous demande où enregistrer le document signé (il propose le même nom terminé par « _signé »). L'original n'est pas modifié.

![opciones_firma] Options de signature.

- **Motif, lieu et contact** : ils figurent dans la signature visible et dans les données de la signature. La signature visible s'affiche dans la langue de l'application.
- **Ajouter un horodatage qualifié (PAdES-B-T)** : une autorité d'horodatage certifie la date et l'heure de la signature. Nécessite Internet.
- **Certifier le document** : après la signature, seuls le remplissage des formulaires et l'ajout de nouvelles signatures seront possibles ; toute autre modification invalidera la certification.
- **Ne plus demander** : signe directement avec ces options (modifiable dans **Signer › Options de signature…**).

Un document peut être signé plusieurs fois : chaque nouvelle signature s'ajoute sans invalider les précédentes, à condition qu'aucune modification n'ait été faite entre elles.

## Signer dans le cadre d'un formulaire

Si le document contient un cadre de signature vide (comme de nombreux formulaires administratifs), cliquez dessus : AventyaPDF demande le certificat et signe dans ce cadre.

## Signature manuscrite

**Signer › Insérer une signature manuscrite (dessinée ou image)…**, ou la plume du volet de signature, ouvre une zone de dessin où tracer votre signature à la souris, avec un trait de stylo plume et la couleur et l'épaisseur de votre choix. Vous pouvez aussi charger l'image numérisée de votre signature (le fond blanc du papier est supprimé).

![manuscrita] Dessiner la signature manuscrite.

Cliquez ensuite sur la page pour la placer, ou faites glisser un cadre pour définir sa taille. Elle se comporte comme un commentaire : elle se déplace, se redimensionne et se supprime.

> **Important :** la signature manuscrite n'est qu'une image. Elle n'a pas la valeur d'une signature électronique ; pour cela, signez avec un certificat.

## Vérifier les signatures

Le volet **Signatures certifiées** du volet latéral (ou **Signer › Afficher les signatures (vérifiées)**) vérifie automatiquement chaque signature du document :

- si le document a été modifié après la signature ;
- si le certificat est approuvé, selon le magasin Windows et la liste de confiance officielle de l'Espagne (FNMT, DNIe, Colegio de Registradores, Izenpe, ACCV et les autres prestataires qualifiés) ;
- la date déclarée, l'horodatage et la présence de modifications ultérieures.

![firmas] Le volet Signatures certifiées.

La signature la plus récente comporte une corbeille qui la retire et laisse son cadre vide pour signer à nouveau (par exemple avec un autre certificat). La modification s'applique à l'enregistrement.

# Raccourcis clavier

**Aide › Raccourcis clavier** (`F1`) affiche cette même liste dans l'application.

[[atajos]]

# En cas de problème

## L'OCR n'est pas disponible

Tesseract OCR s'installe la première fois que vous reconnaissez du texte et nécessite Internet (et parfois une autorisation d'administrateur). Si l'autorisation a été refusée ou s'il n'y avait pas de connexion, AventyaPDF réessaie à la prochaine ouverture.

## Le sous-menu AventyaPDF n'apparaît pas dans l'Explorateur

Utilisez **Aide › Réparer le menu contextuel de l'Explorateur…**. Sous Windows 11, pour que le sous-menu figure dans le menu principal, le programme d'installation demande une fois l'autorisation d'administrateur ; si elle a été refusée, le sous-menu se trouve dans **Afficher plus d'options**.

## Un document Word n'est pas converti

Microsoft Word ou LibreOffice doit être installé. Si les deux échouent, AventyaPDF en indique la raison.

## Une signature apparaît comme « identité non vérifiée »

La signature n'a pas été modifiée, mais son certificat ne figure ni dans le magasin Windows ni dans la liste de confiance de l'Espagne (par exemple, un certificat de test ou d'un autre pays). Vérifiez auprès du signataire l'origine de son certificat.

## Signaler un problème

Si une fenêtre « Erreur inattendue » apparaît, l'application reste ouverte et le détail est enregistré dans le dossier `%LOCALAPPDATA%\aventyapdf` (fichiers `errores.log` et `fallos_graves.log`). Envoyez ces fichiers avec une description de ce que vous faisiez sur github.com/Aventya/AventyaPDF/issues.
