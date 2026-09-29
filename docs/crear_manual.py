# -*- coding: utf-8 -*-
"""
Genera docs/MANUAL.pdf a partir de las capturas de docs/capturas/ (ver antes
crear_capturas.py). Se ejecuta con el entorno de la aplicación:

    %LOCALAPPDATA%\\aventyapdf\\venv\\Scripts\\python.exe docs\\crear_manual.py
"""
import datetime
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
import fitz

CAP = os.path.join(RAIZ, "docs", "capturas")
OUT = os.path.join(RAIZ, "docs", "MANUAL.pdf")

W, H = 595, 842   # A4
MARGEN = 48
AZUL = (0.0, 0.47, 0.83)
GRIS = (0.38, 0.38, 0.38)
NEGRO = (0.13, 0.12, 0.11)
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
        "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

SECCIONES = [
    ("Vista general",
     "AventyaPDF abre varios documentos a la vez, cada uno en su pestaña. El panel "
     "lateral izquierdo muestra miniaturas de página, marcadores, comentarios y firmas "
     "certificadas; se abre y se cierra con el icono de arriba a la izquierda o con F4.",
     ["01_vista_general.png"]),
    ("Añadir texto",
     "La herramienta «Texto» (T) escribe directamente sobre la página, con la fuente, "
     "el tamaño, el color y la alineación que se elijan en el panel lateral.",
     ["02_texto.png"]),
    ("Notas adhesivas",
     "La herramienta «Nota» (N) añade un comentario junto a la página, como una nota "
     "adhesiva: se ve un icono y el texto aparece al pasar el ratón por encima.",
     ["03_nota.png"]),
    ("Resaltar, subrayar y tachar",
     "Sobre texto ya seleccionable, resalta, subraya o tacha automáticamente; sobre una "
     "imagen o un escaneo, dibuja la marca a mano alzada con el ratón.",
     ["04_resaltar.png"]),
    ("Rectángulos y formas",
     "Remarca cualquier zona de la página con un rectángulo de esquinas redondeadas, "
     "con el color y el grosor de línea que se elijan.",
     ["05_rectangulo.png"]),
    ("Emojis",
     "Más de 1.300 emojis, con buscador, para insertar en la página con el tamaño, el "
     "color y la opacidad que se quieran.",
     ["06_emoji.png"]),
    ("Editar el contenido del PDF",
     "La herramienta «Editar» (C) permite corregir directamente el texto por párrafos "
     "y mover o sustituir las imágenes que ya están en el documento, con su misma "
     "fuente cuando es posible.",
     ["07_editar_contenido.png"]),
    ("Rellenar formularios",
     "Los formularios se rellenan haciendo clic en el propio campo: texto, casillas, "
     "botones de opción, listas, cálculos y validaciones, igual que en Acrobat. Un "
     "aviso en la barra de estado avisa si el documento tiene campos sin rellenar.",
     ["10_formulario.png"]),
    ("Operaciones de página",
     "En el panel lateral: girar, duplicar, eliminar, insertar página en blanco, "
     "insertar otro PDF, extraer y reordenar arrastrando las miniaturas, todo con "
     "deshacer (Ctrl+Z).",
     ["08_operaciones_pagina.png"]),
    ("Recortar una página",
     "El icono «Recortar» dibuja un recuadro con tiradores en las cuatro esquinas y "
     "los cuatro lados sobre la página mostrada: cada uno cambia su propio margen. Los "
     "botones que aparecen centrados en el recuadro aplican o cancelan el recorte.",
     ["09_recortar.png"]),
    ("Buscar en el documento",
     "La lupa de la barra principal abre un buscador con resultados en vivo, resaltados "
     "en la página y contados («1 de 4»); las flechas van al resultado siguiente o "
     "anterior.",
     ["11_buscar.png"]),
    ("Zoom",
     "Siempre visible en la barra de estado: acercar y alejar paso a paso, arrastrar la "
     "barra o escribir un porcentaje exacto (hasta el 400 %). El botón de la barra "
     "principal alterna entre ajustar al ancho, ajustar a la página y la escala "
     "original (100 %).",
     ["12_zoom.png"]),
    ("Proteger con contraseña",
     "Cifrado AES de 256 bits: una contraseña para abrir el documento y, aparte, una "
     "contraseña de permisos que restringe imprimir, copiar, modificar o comentar.",
     ["13_proteger.png"]),
    ("Marca de agua",
     "Texto en diagonal (u otro ángulo) sobre las páginas que se elijan, con el "
     "tamaño, el color y la opacidad que se quieran.",
     ["14_marca_de_agua.png"]),
    ("Encabezado, pie y numeración Bates",
     "Hasta tres textos por línea (izquierda, centro, derecha) en la cabecera y en el "
     "pie, con variables para el número de página, el total, la fecha o un número "
     "Bates correlativo.",
     ["15_encabezado_pie.png"]),
    ("Reconocer texto (OCR)",
     "Convierte en texto seleccionable y buscable el de las páginas escaneadas o las "
     "imágenes, con Tesseract OCR: elige el idioma, si son todas las páginas o solo las "
     "que no tienen texto, y si se corrige la orientación de cada una.",
     ["16_ocr.png"]),
    ("Firma digital",
     "La herramienta «Firma» dibuja el área donde irá la firma visible; el certificado "
     "activo (de Windows o de un archivo .pfx/.p12) se ve arriba, en el panel lateral.",
     ["18_firma_digital.png"]),
    ("Opciones de firma",
     "Motivo, lugar y contacto de la firma; sello de tiempo cualificado (PAdES-B-T); y "
     "la opción de certificar el documento, que después de firmarlo solo permitirá "
     "rellenar formularios y añadir más firmas.",
     ["17_opciones_firma.png"]),
    ("Firma manuscrita",
     "Se dibuja con el ratón, con trazo de estilográfica según la velocidad, o se carga "
     "desde una imagen; luego se coloca en la página con un clic o arrastrando un "
     "recuadro.",
     ["19_firma_manuscrita.png"]),
]


def pagina_titulo(doc):
    page = doc.new_page(width=W, height=H)
    icono = os.path.join(RAIZ, "ICONO.png")
    if os.path.isfile(icono):
        lado = 120
        x0 = (W - lado) / 2
        page.insert_image(fitz.Rect(x0, 200, x0 + lado, 200 + lado), filename=icono)
    page.insert_textbox(fitz.Rect(0, 350, W, 400), "Manual de AventyaPDF",
                        fontsize=28, fontname="helv", color=NEGRO,
                        align=fitz.TEXT_ALIGN_CENTER)
    page.insert_textbox(fitz.Rect(0, 395, W, 420),
                        "Ver, comentar, organizar, proteger, convertir y firmar documentos PDF",
                        fontsize=13, fontname="helv", color=GRIS,
                        align=fitz.TEXT_ALIGN_CENTER)
    hoy = datetime.date.today()
    fecha = f"{MESES[hoy.month - 1]} de {hoy.year}"
    page.insert_textbox(fitz.Rect(0, 760, W, 800),
                        f"Aventya Asesoría Integral SL  ·  {fecha}\n"
                        "github.com/Aventya/AventyaPDF",
                        fontsize=10, fontname="helv", color=GRIS,
                        align=fitz.TEXT_ALIGN_CENTER)


def pagina_indice(doc):
    page = doc.new_page(width=W, height=H)
    page.insert_textbox(fitz.Rect(MARGEN, 60, W - MARGEN, 100), "Índice",
                        fontsize=22, fontname="helv", color=NEGRO)
    y = 120
    for i, (titulo, _texto, _imgs) in enumerate(SECCIONES, start=1):
        page.insert_textbox(fitz.Rect(MARGEN, y, W - MARGEN, y + 22),
                            f"{i}.  {titulo}", fontsize=12, fontname="helv", color=NEGRO)
        y += 26


def pagina_seccion(doc, numero, titulo, texto, imagenes):
    page = doc.new_page(width=W, height=H)
    page.insert_textbox(fitz.Rect(MARGEN, 40, W - MARGEN, 44), "AventyaPDF — Manual",
                        fontsize=8, fontname="helv", color=GRIS)
    page.draw_line(fitz.Point(MARGEN, 50), fitz.Point(W - MARGEN, 50),
                   color=(0.85, 0.85, 0.85), width=0.7)
    page.insert_textbox(fitz.Rect(MARGEN, 60, W - MARGEN, 95), f"{numero}.  {titulo}",
                        fontsize=19, fontname="helv", color=AZUL)
    y = 100
    if texto:
        page.insert_textbox(fitz.Rect(MARGEN, y, W - MARGEN, y + 90), texto,
                            fontsize=11, fontname="helv", color=NEGRO, lineheight=1.35)
        y += 70 if len(texto) < 160 else 95
    y += 8

    n = len(imagenes)
    disponible = H - 70 - y
    for ruta in imagenes:
        pix = fitz.Pixmap(ruta)
        iw, ih = pix.width, pix.height
        alto_max = disponible / n - 12
        ancho_max = W - 2 * MARGEN
        k = min(ancho_max / iw, alto_max / ih)
        w, h = iw * k, ih * k
        x0 = (W - w) / 2
        page.draw_rect(fitz.Rect(x0 - 1, y - 1, x0 + w + 1, y + h + 1),
                       color=(0.82, 0.82, 0.82), width=0.7)
        page.insert_image(fitz.Rect(x0, y, x0 + w, y + h), filename=ruta)
        y += h + 16
    page.insert_textbox(fitz.Rect(MARGEN, H - 34, W - MARGEN, H - 20), f"{numero}",
                        fontsize=9, fontname="helv", color=GRIS, align=fitz.TEXT_ALIGN_CENTER)


def main():
    doc = fitz.open()
    pagina_titulo(doc)
    pagina_indice(doc)
    for i, (titulo, texto, imgs) in enumerate(SECCIONES, start=1):
        pagina_seccion(doc, i, titulo, texto, [os.path.join(CAP, n) for n in imgs])
    doc.save(OUT, garbage=4, deflate=True)
    doc.close()
    print(f"Manual generado: {OUT} ({len(SECCIONES) + 2} páginas)")


if __name__ == "__main__":
    main()
