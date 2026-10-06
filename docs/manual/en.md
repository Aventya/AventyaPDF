---
titulo: AventyaPDF manual
subtitulo: View, comment, organise, protect, convert and sign PDF documents
version: Version {version}
indice: Contents
meses: January|February|March|April|May|June|July|August|September|October|November|December
fecha: {mes} {anio}
cabecera: AventyaPDF manual
consejo: Tip
importante: Important
atajos_tecla: Key
atajos_accion: Action
muestra_titulo: Sample document — page {n}
muestra_texto: This is a sample document created solely to show the AventyaPDF tools in the manual. It contains no real data and no client data.\n\nAventyaPDF is a desktop application for Windows that lets you view, comment, organise, protect, convert and digitally sign PDF documents.\n\nThis paragraph is for trying out the commenting tools: highlight text, underline it, strike it through, select it and copy it, or add sticky notes next to it.
buscar: document
resaltar: commenting tools
texto_anotacion: Text added on the page
nota_texto: Review this paragraph before sending it.
formulario_titulo: Sample application form
campo_nombre: Full name
campo_fecha: Date
campo_importe: Amount
casilla: I accept the terms and conditions
firmante: Jane Example
motivo: Agreement
lugar: City
contacto: email@example.com
certificado_ejemplo: Sample certificate
nombre_doc1: Contract.pdf
nombre_doc2: Invoice.pdf
nombre_doc3: Report.pdf
nombre_formulario: Application.pdf
nombre_firmado: Signed contract.pdf
explorador_opciones: Open|Open with|Share
---

# Getting started

## What AventyaPDF is

AventyaPDF is a Windows application that brings together in a single program everything you do every day with PDF documents: read them, comment on them, fill in forms, change their text, organise their pages, combine them, protect them with a password, recognise the text of scans and sign them with a digital certificate.

It is freely distributed and its source code is published on GitHub. It doesn't send your documents anywhere: everything happens on your computer.

![ventana] The AventyaPDF window with three documents open.

## Installing and updating

The installer first asks for the language (it suggests the Windows language): AventyaPDF is installed and opens in that language. During installation, Python, its components and the fonts are downloaded from their official sites, so you need an Internet connection. Meanwhile, the installer shows you the application's tools.

When it finishes, AventyaPDF appears in the Start menu (and on the desktop, if you selected that option) and under **Open with** for PDF files. Windows doesn't let a program make itself the default viewer: if you want PDFs to always open with AventyaPDF, select it in **Open with › Choose another app** and tick “Always use this app to open .pdf files”.

When a new version is available, AventyaPDF tells you at startup. You can also check in **Help › Check for updates…**: the new installer is downloaded to your Downloads folder and you just have to open it. Your settings, your certificate and your language are kept.

> **Important:** text recognition (OCR) uses Tesseract OCR, which isn't included in the installer. AventyaPDF downloads and installs it the first time you use it; it may ask for administrator permission.

## The window

- **Menu bar**: all the features, arranged in File, Edit, View, Comment, Organise, Tools, Protect, Sign and Help.
- **Toolbar**: open, save, print and compress; undo and redo; the current page; the zoom setting; the commenting and editing tools; the signature; the page operations and, on the right, the magnifying glass for finding text.
- **Side panel** (on the left, opened and closed with **F4**): page thumbnails, bookmarks, comments and digital signatures. The options of the tool you're using appear at the top of the panel.
- **Status bar** (at the bottom): application messages and, on the right, the zoom.

## Tour, help and language

The first time you open AventyaPDF, a tour summarises its features. Tick “Don't show at startup” if you don't want to see it again; you can always reopen it from **Help › AventyaPDF tour**.

![presentacion] The startup tour.

The **Help** menu also contains this manual (**Help › AventyaPDF manual**), the list of keyboard shortcuts (**F1**) and the application language (**Help › Language**). AventyaPDF is available in Spanish, English, French, Italian, Catalan, Galician and Basque; the new language is applied the next time you open the application.

![idioma] Help › Language.

# Opening, saving and navigating the document

## Opening documents

There are several ways to open documents:

- **File › Open…** (`Ctrl+O`): you can select several files at once with `Ctrl` or `Shift`.
- Drag them from File Explorer onto the window.
- **File › Open recent**, with the most recently used documents.
- Double-click a PDF, if AventyaPDF is your PDF viewer.

As well as PDFs, AventyaPDF opens images (PNG, JPG, BMP, GIF, TIFF and WebP) and Word documents (.doc and .docx): each one is converted into a new, unsaved PDF in its own tab. The original isn't changed. To convert Word documents, Microsoft Word or LibreOffice must be installed.

If the PDF is password-protected, AventyaPDF asks for the password before opening it.

## Several documents at once

Each open document has its own tab in the side panel, below the panel icons. Hover the mouse over a tab to see the document's name and folder; a “●” dot means it has unsaved changes.

![pestanas] The tabs of the open documents, in the side panel.

- Click a tab to go to that document, or use `Ctrl+Tab` and `Ctrl+Shift+Tab`.
- Drag a tab up or down to change the order.
- Right-click a tab to close that document (or use `Ctrl+W`).

Each document keeps its own page, changes and undo history. If you open a file that is already open, AventyaPDF simply switches to its tab.

## Moving through pages and zooming

- `PgDn` and `PgUp` turn the page; `Home` and `End` go to the first and last page. The mouse wheel also turns the page when you reach the edge.
- Type a number in the page box on the toolbar, or use **View › Go to page…** (`Ctrl+G`).
- Click a thumbnail in the side panel to go to that page. The bookmarks panel shows the document's table of contents, if it has one.

The zoom is always at the bottom right: the magnifying glass buttons zoom in and out, you can drag the slider, and you can type the exact percentage in the box (up to 400%). `Ctrl+Wheel`, `Ctrl++` and `Ctrl+-` also work. The fit button on the toolbar toggles between fit width (`Ctrl+1`), fit page (`Ctrl+2`) and actual size (`Ctrl+0`).

![zoom] The zoom, in the status bar.

## Finding and copying text

Press `Ctrl+F` or click the magnifying glass on the toolbar and type what you're looking for: matches are highlighted on the page as you type and counted (“1 of 12”). The arrows, `F3` and `Shift+F3` go to the next and previous match; `Esc` closes the search.

![buscar] Finding text in the document.

To copy, drag the mouse over the text with the selection tool and press `Ctrl+C`. Each paragraph is pasted as a single line, without the PDF's line breaks; this also applies to text recognised with OCR.

## Saving, printing and properties

- **File › Save** (`Ctrl+S`) saves over the same file; **Save as…** (`Ctrl+Shift+S`) saves it under another name. The window title shows “●” while there are unsaved changes, and when you close the document you're asked whether you want to save them.
- **File › Print…** (`Ctrl+P`) opens the Windows print dialog.
- **File › Document properties…** (`Ctrl+D`) shows the title, author, subject and keywords and lets you change them; the Information tab shows details such as the number of pages, the size or whether the document has signatures.

![propiedades] Document properties.

## Undo and redo

Almost everything you do in a document can be undone with `Ctrl+Z` and redone with `Ctrl+Y`: comments, text changes, page operations, watermarks, OCR… Each document has its own history.

# Commenting

The commenting tools are in the **Comment** menu and on the toolbar. Each one has a letter so you can select it quickly; `V` or `Esc` go back to the selection tool. The tool's options (colour, size, width…) appear at the top of the side panel.

## Adding text

With the **Add text** tool (`T`), click the page (or drag a box) and type directly on it, with no dialog boxes: the box grows as you type. In the side panel you choose the size, colour, bold and italic, alignment and font, and the changes are visible straight away.

![texto] Text typed directly on the page.

`Enter` starts a new line, `Ctrl+Enter` confirms and `Esc` cancels. Clicking somewhere else also confirms. To change existing text, double-click it.

## Sticky notes

The **Sticky note** (`N`) leaves a comment on the page: click where you want to place it and type. A small icon appears on the page, and the text is shown when you hover the mouse over it. You choose the note colour in the side panel.

![nota] A sticky note next to the text.

## Highlighting, underlining and striking through

With **Highlight, underline or strike through** (`H`), choose the markup type and colour in the side panel and drag over the text. If the text can't be selected (an image or a scan), the markup is drawn freehand; a quick stroke comes out straight.

![resaltar] Highlighted text.

> **Tip:** you can also select text with the selection tool and right-click to highlight, underline or strike it through.

## Rectangles and emojis

The **Rectangle** (`R`) outlines an area of the page with a rounded-corner box: drag to draw it, with the colour and width set in the side panel.

![rectangulo] A rectangle around the title.

The **Emoji** tool (`E`) inserts any of more than 1,300 emojis, with search and groups, in the size, colour and opacity you want: choose one and click where it should go.

![emoji] Choosing an emoji.

## Moving, changing and deleting comments

With the selection tool, click a comment to select it: you can move it by dragging, resize it with its handles and delete it with `Del`. The **Annotation eraser** removes comments with a single click.

The **Comments** panel in the side panel lists all the comments in the document with their page; click one to go to it on the page and select it.

![comentarios] The Comments panel.

## Flattening

**Comment › Flatten annotations and forms…** turns comments and form fields into part of the page content: they look the same, but can no longer be moved or edited. This is useful before sending a final version.

# Editing the PDF content

The **Edit PDF text and images** tool (`C`, in the Tools menu) changes the text and images that are already part of the document, not comments on top of it. When you select it, each paragraph is framed in blue and each image in green.

![editar] The editable paragraphs and images, framed.

**Text.** Click a paragraph and type: the text is spread over as many lines as needed within its box, with the same font, size and colour whenever possible. In the side panel you can change the size, the colour and bold or italic. If the text doesn't fit, the box turns red: drag one of its corners to make it bigger. `Ctrl+Enter` confirms, `Esc` cancels and `Tab` moves to the next paragraph. Leaving a paragraph empty deletes it.

**Images.** Click an image to select it: drag it to move it, drag a corner to resize it (without distorting it) or press `Del` to delete it. Right-click it to replace it with another image or save it to a file.

> **Important:** if the document uses a font that isn't available, AventyaPDF uses the closest match and tells you so in the status bar. Check the result before saving.

# Filling in forms

Form fields are highlighted in blue (you can turn this off in **View › Highlight form fields**). You don't need any special tool:

- Click a text field and type; `Tab` moves to the next field and `Shift+Tab` to the previous one.
- Tick boxes and option buttons are selected with a click; lists drop down their values.
- Calculations, validations and form buttons work as in Adobe Acrobat.

![formulario] A form with its fields highlighted.

If the form has an empty signature box, click it to sign inside it (see the chapter on signing).

# Organising pages

## Page operations

The **Page operations** button on the toolbar (or **Organise › Organise pages in the side panel**) opens the thumbnails in organise mode, with a row of buttons above them.

![organizar] Page operations in the side panel.

- **Reorder**: drag a thumbnail to its new position.
- **Select several**: hold down `Ctrl` or `Shift` while clicking. With no selection, the buttons act on the current page.
- **Buttons**: rotate left and right, duplicate, delete, insert a blank page, insert another PDF, extract the pages to a new PDF and crop.

Everything is applied immediately and can be undone.

## Cropping a page

The **Crop** button draws a box on the page with handles at the corners and on the sides: drag each one to the margin you want. The buttons in the centre of the box apply or cancel the crop.

![recortar] Cropping a page.

## The Organise menu

The **Organise** menu also contains:

- **Insert blank page**, **Insert PDF after current page…** and **Append PDF…**
- **Duplicate current page**, **Delete pages…** and **Extract pages…**, with ranges such as “1-3, 5, 8-”.
- **Split document…**: saves the document in parts with a fixed number of pages.
- **Rotate page right** (`Ctrl+Shift+R`), **Rotate page left** (`Ctrl+Shift+L`) and **Rotate pages…** by range.

## Combining documents

**Organise › Combine PDFs…** has two options:

- **Combine open documents**: puts all the open documents, in the order of their tabs and with their changes, into a new PDF.
- **Combine files…**: you choose several files (PDFs, images or Word documents, mixed) and they are combined in alphabetical order of name.

![combinar] Organise › Combine PDFs.

The result stays open without being saved; save it with `Ctrl+S`. The original files don't change.

# Creating, converting and exporting

## Creating documents

- **File › New blank PDF** (`Ctrl+N`) creates a document with one empty page.
- **File › Create PDF from images…** puts several images into a PDF, one per page.
- Opening an image or a Word document converts it to PDF (see “Opening documents”).

## Exporting

In **File › Export** you can extract the document's content:

- **Pages as images…**: PNG or JPG, at the resolution you choose.
- **Text (.txt)…**: all the text in the document.
- **Word document (.docx)…**: a document you can edit in Word.
- **Extract pages to PDF…**: only the pages you specify.

![exportar] Exporting pages as images.

## From File Explorer

Without opening the application first, select files in File Explorer and right-click: the **AventyaPDF** submenu contains:

- **Sign digitally** (PDFs only): opens the documents with the signing tool ready.
- **Combine into one PDF** (two or more files): PDFs, images and Word documents, mixed, into a single PDF.
- **Convert to PDF** (images and Word): one PDF per file.

![explorador] The AventyaPDF right-click submenu.

In Windows 11, the submenu is in the main right-click menu; in Windows 10, and in Windows 11 under **Show more options**, it's in the classic menu.

> **Tip:** if the submenu disappears (for example, after a Windows update), use **Help › Repair the File Explorer context menu…**

# Tools

## Watermark

**Tools › Watermark…** writes text over the pages you choose, with the size, colour, opacity and angle you want (for example, “CONFIDENTIAL” diagonally).

![marca_agua] Watermark.

## Header, footer and Bates numbering

**Tools › Header, footer and Bates numbering…** adds up to three texts in the header and three in the footer (left, centre and right). You can use variables:

- `{n}`: the page number; `{total}`: the total number of pages.
- `{fecha}`: today's date.
- `{bates}`: a sequential Bates number, with a prefix, start number and number of digits.

![encabezado] Header, footer and Bates numbering.

## Recognising text (OCR)

**Tools › Recognise text (OCR)…** turns the text in scanned pages, photos and images into text that can be selected and searched. Choose the document language, whether to recognise all pages or only those without text, and whether to correct the orientation of each page.

![ocr] Recognise text (OCR).

The text is added as an invisible layer: the page looks the same, but the text can now be searched, selected and copied. If you choose a new language, AventyaPDF first downloads its data.

## Optimising and compressing

The **Compress PDF** button on the toolbar (or **Tools › Optimise and compress…**) reduces the file size, especially when it contains images. Choose the level (high quality, good quality or maximum reduction) and save the compressed copy; the original doesn't change.

![comprimir] The compression options.

# Password protection

**Protect › Protect with password…** encrypts the document with 256-bit AES:

- **Document open password**: without it, the document can't be opened.
- **Permissions password**: restricts printing, copying, changing or commenting, even if the document can be opened without a password.

![proteger] Protect with password.

Protection is applied when you save. **Protect › Remove security** removes the password and permissions from a document you have opened with its password.

> **Important:** if you forget the open password, there's no way to recover the document. Keep it somewhere safe.

# Signing

AventyaPDF signs with a PAdES advanced electronic signature, the type used in official European documents, with qualified certificates such as those issued by the FNMT or the DNIe (Spanish electronic ID card).

## The certificate

In **Sign › Signing certificate…** you choose which certificate to sign with:

- **Windows certificate store**: the certificates installed on your computer, including those on smart cards and the DNIe. The key never leaves the store; if a PIN is needed, Windows asks for it.
- **.pfx / .p12 file**: a certificate saved in a file. The password can be saved in Windows Credential Manager so you don't have to type it every time.

The chosen certificate is remembered for subsequent signatures.

## Signing a document

Choose the **Signature** tool (or **Sign › Sign document (draw area)**) and draw on the page the box where the visible signature will go. The side panel shows the active certificate, and you can change it there.

![firmar] The signing tool, with the active certificate.

Next, the **Signature options** appear, and finally AventyaPDF asks where to save the signed document (it suggests the same name ending in “_signed”). The original isn't modified.

![opciones_firma] Signature options.

- **Reason, location and contact**: these appear in the visible stamp and in the signature details. The stamp appears in the application language.
- **Add qualified time stamp (PAdES-B-T)**: a time-stamping authority certifies the date and time of the signature. Requires an Internet connection.
- **Certify document**: after signing, only form filling and further signatures will be allowed; any other change will invalidate the certification.
- **Don't ask again**: signs directly with these options (you can change this in **Sign › Signature options…**).

A document can be signed several times: each new signature is added without invalidating the earlier ones, as long as no changes have been made between them.

## Signing in a form's signature box

If the document has an empty signature box (like many government forms), click it: AventyaPDF asks for the certificate and signs inside that box.

## Handwritten signature

**Sign › Insert handwritten signature (drawn or image)…**, or the pen nib in the signature panel, opens a canvas where you can draw your signature with the mouse, with a fountain pen stroke in the colour and width you want. You can also load an image of your scanned signature (the white paper background is removed).

![manuscrita] Drawing the handwritten signature.

Then click the page to place it, or drag a box to set its size. It behaves like any other comment: it can be moved, resized and deleted.

> **Important:** the handwritten signature is just an image. It has no value as an electronic signature; for that, sign with a certificate.

## Verifying signatures

The **Digital signatures** panel in the side panel (or **Sign › View signatures (verified)**) automatically checks each signature in the document:

- whether the document has been altered after signing;
- whether the certificate is trusted, according to the Windows certificate store and the official Spanish trusted list (FNMT, DNIe, Colegio de Registradores, Izenpe, ACCV and the other qualified trust service providers);
- the claimed signing time, the time stamp and whether there are later changes.

![firmas] The Digital signatures panel.

The most recent signature has a bin icon that removes it and leaves its box empty so you can sign again (for example, with another certificate). The change is applied when you save.

# Keyboard shortcuts

**Help › Keyboard shortcuts** (`F1`) shows this same list within the application.

[[atajos]]

# Troubleshooting

## OCR isn't available

Tesseract OCR is installed the first time you recognise text and requires an Internet connection (and sometimes administrator permission). If permission was refused or there was no connection, AventyaPDF tries again the next time you open it.

## The AventyaPDF submenu doesn't appear in File Explorer

Use **Help › Repair the File Explorer context menu…**. In Windows 11, for the submenu to be in the main menu, the installer asks once for administrator permission; if it was refused, the submenu is under **Show more options**.

## A Word document isn't converted

Microsoft Word or LibreOffice must be installed. If both fail, AventyaPDF shows the reason.

## A signature shows as “identity not verified”

The signature hasn't been altered, but its certificate isn't in the Windows certificate store or on the Spanish trusted list (for example, a test certificate or one from another country). Check with the signer where their certificate comes from.

## Reporting a problem

If an “Unexpected error” window appears, the application stays open and the details are saved in the `%LOCALAPPDATA%\aventyapdf` folder (files `errores.log` and `fallos_graves.log`). Send those files, with a description of what you were doing, at github.com/Aventya/AventyaPDF/issues.
