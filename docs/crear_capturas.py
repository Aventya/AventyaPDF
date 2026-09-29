# -*- coding: utf-8 -*-
"""
Genera las capturas de pantalla de docs/capturas/, usadas por el README y por
crear_manual.py. Se ejecutan con el entorno de la aplicación:

    %LOCALAPPDATA%\\aventyapdf\\venv\\Scripts\\python.exe docs\\crear_capturas.py

Solo usa contenido de muestra inventado (nunca abre un documento real): esos
PDF de muestra se crean aparte, en un directorio temporal, y no se guardan en
el proyecto.

(r102) ⚠️ Ricardo, IMPORTANTE si vuelves a ejecutar esto: el panel «Firma»
(`_sign_cert_lbl`) y el selector de certificado (`cert_manager.CertPickerDialog`,
pestaña «Almacén de Windows») leen datos REALES de este equipo — el
certificado de firma guardado y el almacén de certificados de Windows, que
puede tener clientes reales. Por eso aquí el nombre del certificado se
sustituye por uno de ejemplo antes de capturar, y el selector de certificado
NO se captura en absoluto. Revisa cualquier captura nueva relacionada con
firma antes de darla por buena — ver la memoria del asistente,
«capturas-firma-datos-reales».

Para medir anchos de texto a pixel (no es el caso aquí) haría falta
QT_QPA_PLATFORM=windows, no offscreen — ver «offscreen no mide texto bien».
Aun con la plataforma real, la ventana se coloca fuera del escritorio
visible (move(-5000, -5000)): no toca la pantalla ni el ratón mientras se
generan las capturas.
"""
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "windows")
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

import fitz
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QPoint, QRect  # noqa: F401 (QRect: por si se amplía)

import dialogs
import doc_tools
import firma_manuscrita_ui
import main_window
import utils
from window_menus import OCR_LANGS, TSA_PRESETS

CAP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "capturas")
TMP = tempfile.mkdtemp(prefix="agpdf_capturas_")
os.makedirs(CAP, exist_ok=True)

LOREM = (
    "Este es un documento de muestra creado únicamente para mostrar las "
    "herramientas de AventyaPDF en las capturas de pantalla del manual y "
    "del repositorio. No contiene ningún dato real ni de ningún cliente.\n\n"
    "AventyaPDF es una aplicación de escritorio para Windows que permite ver, "
    "comentar, organizar, proteger, convertir y firmar digitalmente "
    "documentos PDF, con toda su interfaz en español.\n\n"
    "Este párrafo sirve para probar las herramientas de comentario: "
    "resaltar texto, subrayarlo, tacharlo, seleccionarlo y copiarlo, o "
    "añadir notas adhesivas junto a él. También se puede dibujar "
    "directamente sobre la página con texto libre, rectángulos o emojis."
)


def crear_pdf_general() -> str:
    doc = fitz.open()
    for i in range(4):
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 90), f"Documento de muestra — página {i + 1}", fontsize=18)
        page.draw_line(fitz.Point(72, 105), fitz.Point(523, 105), color=(0.2, 0.2, 0.2), width=1)
        page.insert_textbox(fitz.Rect(72, 130, 523, 500), LOREM, fontsize=12, lineheight=1.4)
    ruta = os.path.join(TMP, "muestra_general.pdf")
    doc.save(ruta)
    doc.close()
    return ruta


def crear_pdf_formulario() -> str:
    doc = fitz.open()
    page = doc.new_page(width=595, height=400)
    page.insert_text((40, 40), "Formulario de muestra", fontsize=18)

    def campo(tipo, nombre, rect, etiqueta, **kw):
        page.insert_text((rect[0], rect[1] - 6), etiqueta, fontsize=10, color=(0.3, 0.3, 0.3))
        w = fitz.Widget()
        w.field_type = tipo
        w.field_name = nombre
        w.rect = fitz.Rect(rect)
        for k, v in kw.items():
            setattr(w, k, v)
        page.add_widget(w)

    campo(fitz.PDF_WIDGET_TYPE_TEXT, "nombre", (40, 90, 300, 114), "Nombre", field_value="")
    campo(fitz.PDF_WIDGET_TYPE_TEXT, "fecha", (320, 90, 500, 114), "Fecha", field_value="")
    campo(fitz.PDF_WIDGET_TYPE_CHECKBOX, "acepto", (40, 150, 60, 170), "Acepto los términos")
    page.insert_text((70, 165), "Acepto los términos", fontsize=11)
    ruta = os.path.join(TMP, "muestra_formulario.pdf")
    doc.save(ruta)
    doc.close()
    return ruta


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    hoja = open(os.path.join(RAIZ, "main.py"), encoding="utf-8").read()
    app.setStyleSheet(hoja.split('STYLESHEET = """')[1].split('"""')[0])

    w = main_window.MainWindow()
    w.move(-5000, -5000)      # fuera del escritorio visible: no toca la pantalla
    w.resize(1360, 900)
    w.show()

    def shot(nombre):
        for _ in range(6):
            app.processEvents()
        w.grab().save(os.path.join(CAP, nombre))
        print("  ->", nombre)

    def shot_dialog(dlg, nombre):
        dlg.move(-4200, -4200)
        dlg.show()
        for _ in range(6):
            app.processEvents()
        dlg.grab().save(os.path.join(CAP, nombre))
        print("  ->", nombre)
        dlg.close()

    general = crear_pdf_general()
    formulario = crear_pdf_formulario()

    print("01 — vista general")
    w.open_path(general)
    w.sidebar.show_panel("thumbs")
    shot("01_vista_general.png")

    print("02 — texto")
    w._toggle_tool("TEXT")
    w.doc[0].add_freetext_annot(fitz.Rect(90, 550, 340, 600),
                                "Texto añadido con la herramienta Texto",
                                fontsize=13, text_color=(0.82, 0.20, 0.22))
    w.mark_modified()
    w.render_page()
    shot("02_texto.png")
    w._toggle_tool("TEXT")

    print("03 — nota")
    w._toggle_tool("NOTE")
    w.add_note(fitz.Point(500, 200), "Recuerda revisar este párrafo antes de enviarlo.")
    shot("03_nota.png")
    w._toggle_tool("NOTE")

    print("04 — resaltar")
    w._toggle_tool("MARKUP")
    hits = doc_tools.search_document(w.doc, "herramientas de comentario")
    rects0 = [r for p, r in hits if p == 0]
    if rects0:
        w.add_text_markup(rects0, "highlight")
    shot("04_resaltar.png")
    w._toggle_tool("MARKUP")

    print("05 — rectángulo")
    w._toggle_tool("RECT")
    utils.PDFUtils.add_rectangle_annotation(w.doc, 0, fitz.Rect(90, 280, 400, 330),
                                            color=(0.82, 0.20, 0.22), width=2, corner_radius=6)
    w.mark_modified()
    w.render_page()
    shot("05_rectangulo.png")
    w._toggle_tool("RECT")

    print("06 — emoji")
    w._toggle_tool("EMOJI")
    shot("06_emoji.png")
    w._toggle_tool("EMOJI")

    print("07 — editar contenido")
    w._toggle_tool("EDIT")
    shot("07_editar_contenido.png")
    w._toggle_tool("EDIT")

    print("08 — operaciones de página")
    w._set_pages_mode(True)
    shot("08_operaciones_pagina.png")

    print("09 — recortar")
    w._pages_op("crop")
    shot("09_recortar.png")
    w._cancel_crop()
    w._set_pages_mode(False)

    print("10 — formulario")
    w.open_path(formulario)
    shot("10_formulario.png")

    print("11 — buscar")
    w.open_path(general)
    w.show_find()
    w._find_edit.setText("comentario")
    w._find_step(0)
    shot("11_buscar.png")
    w.hide_find()

    print("12 — zoom")
    w._set_custom_zoom(150)
    shot("12_zoom.png")
    w._set_custom_zoom(100)

    print("13 — proteger")
    shot_dialog(dialogs.SecurityDialog(w), "13_proteger.png")

    print("14 — marca de agua")
    shot_dialog(dialogs.WatermarkDialog(w, len(w.doc)), "14_marca_de_agua.png")

    print("15 — encabezado y pie")
    shot_dialog(dialogs.HeaderFooterDialog(w, len(w.doc)), "15_encabezado_pie.png")

    print("16 — OCR")
    shot_dialog(dialogs.OcrDialog(w, OCR_LANGS, 0, len(w.doc)), "16_ocr.png")

    print("17 — opciones de firma (con lugar/contacto de ejemplo)")
    dlg = dialogs.SignOptionsDialog(w, False, TSA_PRESETS, ok_text="Firmar")
    dlg._reason.setCurrentText("Conformidad")
    dlg._location.setText("Ciudad")            # nunca el lugar real guardado
    dlg._contact.setText("correo@ejemplo.com")  # nunca el contacto real guardado
    shot_dialog(dlg, "17_opciones_firma.png")

    print("18 — herramienta de firma (con certificado de ejemplo)")
    w._toggle_tool("SIGN")
    # Nunca el nombre real del certificado guardado (puede ser un cliente real).
    w._sign_cert_lbl.setText("🖥️  Certificado de ejemplo")
    w._sign_cert_lbl.setStyleSheet("color: #107C10; font-weight: 600;")
    shot("18_firma_digital.png")
    w._toggle_tool("SIGN")

    print("19 — firma manuscrita (lienzo vacío)")
    dlg = firma_manuscrita_ui.HandSignatureDialog(w)
    dlg.canvas.clear()   # nunca el trazo real guardado
    shot_dialog(dlg, "19_firma_manuscrita.png")

    # (r102) A propósito NO se captura cert_manager.CertPickerDialog en la
    # pestaña «Almacén de Windows»: lee el almacén de certificados real del
    # sistema, que puede contener clientes reales de Ricardo.

    print("listo:", CAP)


if __name__ == "__main__":
    main()
