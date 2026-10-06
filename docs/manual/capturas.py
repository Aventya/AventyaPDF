# -*- coding: utf-8 -*-
"""
(r138) Capturas de pantalla del manual y de las diapositivas del instalador,
en el idioma con el que arranque este proceso (variable AVENTYAPDF_IDIOMA;
crear_manual.py lanza un proceso por idioma).

Solo usa contenido de muestra inventado, con los textos de la cabecera del
manual de cada idioma (`muestras`): nunca abre un documento real. Los PDF de
muestra y el certificado de pruebas se crean en una carpeta temporal.

Privacidad (r102): los ajustes de la aplicación se leen de un archivo
temporal (`aislar_ajustes`), no de los del equipo, así que ni el certificado
guardado, ni el lugar o el contacto de la firma, ni los archivos recientes
de quien lo ejecute pueden salir en una captura. El selector de certificado
(pestaña «Almacén de Windows») NO se captura: lee el almacén real.

Funciona con la plataforma «offscreen» de Qt (sin pantalla), en Linux y en
Windows.
"""
from __future__ import annotations

import os
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Ancho × alto de la ventana en las capturas y zona que se recorta para las
# herramientas (barra, panel lateral y la parte de arriba de la página).
VENTANA = (1280, 800)
ZONA = (0, 0, 1280, 600)


def aislar_ajustes(carpeta: str) -> None:
    """Ajustes de Qt en un .ini temporal en vez de los del usuario (en
    Windows, el registro). Hay que llamarlo antes de importar ningún módulo
    de la aplicación: `QSettings("aventyapdf", "config")` siempre usa el
    formato nativo, así que se sustituye la clase por una que fuerza el .ini."""
    from PyQt6 import QtCore
    base = QtCore.QSettings
    if getattr(base, "_aislado", False):
        return
    base.setPath(base.Format.IniFormat, base.Scope.UserScope, carpeta)

    class Aislado(base):
        _aislado = True

        def __init__(self, *args, **kwargs):
            if len(args) == 2 and all(isinstance(x, str) for x in args):
                super().__init__(base.Format.IniFormat, base.Scope.UserScope, *args)
            else:
                super().__init__(*args, **kwargs)

    QtCore.QSettings = Aislado


def _pdf_general(m: dict, ruta: str, paginas: int = 4) -> None:
    import fitz
    doc = fitz.open()
    fuente = os.path.join(RAIZ, "vendor", "fonts", "noto", "NotoSans-Regular.ttf")
    for i in range(paginas):
        page = doc.new_page(width=595, height=842)
        page.insert_font(fontname="noto", fontfile=fuente)
        page.insert_text((72, 90), m["muestra_titulo"].format(n=i + 1), fontsize=18,
                         fontname="noto")
        page.draw_line(fitz.Point(72, 105), fitz.Point(523, 105), color=(0.2, 0.2, 0.2), width=1)
        page.insert_textbox(fitz.Rect(72, 130, 523, 560), m["muestra_texto"].replace("\\n", "\n"),
                            fontsize=12, lineheight=1.4, fontname="noto")
    doc.set_metadata({"title": m["muestra_titulo"].format(n=1).split("—")[0].strip(),
                      "author": m["firmante"]})
    doc.save(ruta)
    doc.close()


def _pdf_formulario(m: dict, ruta: str) -> None:
    import fitz
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    fuente = os.path.join(RAIZ, "vendor", "fonts", "noto", "NotoSans-Regular.ttf")
    page.insert_font(fontname="noto", fontfile=fuente)
    page.insert_text((60, 80), m["formulario_titulo"], fontsize=20, fontname="noto")

    def etiqueta(x, y, texto):
        page.insert_text((x, y), texto, fontsize=10, color=(0.3, 0.3, 0.3), fontname="noto")

    def campo(tipo, nombre, rect, **kw):
        w = fitz.Widget()
        w.field_type = tipo
        w.field_name = nombre
        w.rect = fitz.Rect(rect)
        for k, v in kw.items():
            setattr(w, k, v)
        page.add_widget(w)

    etiqueta(60, 124, m["campo_nombre"])
    campo(fitz.PDF_WIDGET_TYPE_TEXT, "nombre", (60, 130, 330, 154), field_value="")
    etiqueta(350, 124, m["campo_fecha"])
    campo(fitz.PDF_WIDGET_TYPE_TEXT, "fecha", (350, 130, 535, 154), field_value="")
    etiqueta(60, 184, m["campo_importe"])
    campo(fitz.PDF_WIDGET_TYPE_TEXT, "importe", (60, 190, 230, 214), field_value="")
    campo(fitz.PDF_WIDGET_TYPE_CHECKBOX, "acepto", (60, 236, 76, 252))
    etiqueta(84, 249, m["casilla"])
    doc.save(ruta)
    doc.close()


def _pdf_firmado(m: dict, ruta_origen: str, ruta: str, carpeta: str) -> None:
    from create_test_cert import build_test_pfx
    from signer_backend import PAdESSigner
    pfx = os.path.join(carpeta, "muestra.pfx")
    with open(pfx, "wb") as fh:
        fh.write(build_test_pfx(b"1234", common_name=m["firmante"]))
    with open(ruta_origen, "rb") as fh:
        datos = fh.read()
    firmado = PAdESSigner.sign_pdf_bytes(datos, pfx, "1234", 0, (300, 372, 530, 442),
                                         reason=m["motivo"], location=m["lugar"])
    with open(ruta, "wb") as fh:
        fh.write(firmado)


def generar(m: dict, destino: str) -> list[str]:
    """Hace todas las capturas en `destino` (PNG). Devuelve sus nombres."""
    from PyQt6.QtCore import QPoint, QRect
    from PyQt6.QtGui import QColor, QPainter, QPixmap
    from PyQt6.QtWidgets import QApplication, QMenu

    os.makedirs(destino, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="aventyapdf_capturas_")
    aislar_ajustes(os.path.join(tmp, "ajustes"))

    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyle("Fusion")
    sys.path.insert(0, RAIZ)
    import fitz
    import dialogs
    import doc_tools
    import firma_manuscrita_ui
    import icons
    import main
    import main_window
    import presentacion
    import utils
    from window_menus import OCR_LANGS, TSA_PRESETS

    icons.load_fonts()
    app.setStyleSheet(main.STYLESHEET + main.TOOLTIP_QSS)
    main._install_qt_translation(app)
    presentacion.set_show(False)

    hechas: list[str] = []

    def esperar(n=8, segundos=0.0):
        import time
        fin = time.monotonic() + segundos
        for _ in range(n):
            app.processEvents()
        while time.monotonic() < fin:
            app.processEvents()
            time.sleep(0.02)

    def guardar(pix: QPixmap, nombre: str) -> None:
        pix.save(os.path.join(destino, nombre + ".png"))
        hechas.append(nombre)

    w = main_window.MainWindow()
    w.resize(*VENTANA)
    w.show()

    def shot(nombre: str, zona: tuple | None = ZONA) -> None:
        esperar()
        pix = w.grab()
        if zona:
            pix = pix.copy(QRect(*zona))
        guardar(pix, nombre)

    def shot_widget(widget, nombre: str) -> None:
        widget.show()
        esperar()
        guardar(widget.grab(), nombre)
        widget.close()

    def menus(cadena: list, nombre: str, fondo: QPixmap | None = None) -> None:
        """Captura una cadena de menús abiertos (menú, submenú…), uno al lado
        del otro como los ve el usuario."""
        pixs = []
        for menu, activa in cadena:
            menu.popup(QPoint(0, 0))
            if activa is not None:
                menu.setActiveAction(activa)
            esperar()
            pixs.append((menu.grab(), menu.actionGeometry(activa).top() if activa else 0))
            menu.hide()
        ancho = sum(p.width() for p, _ in pixs) + 4
        alto = 0
        y = 0
        posiciones = []
        x = 0
        for p, desplaz in pixs:
            posiciones.append((x, y))
            alto = max(alto, y + p.height())
            x += p.width() - 4
            y += desplaz
        lienzo = QPixmap(ancho + 8, alto + 8)
        lienzo.fill(QColor("#F3F4F6"))
        pintor = QPainter(lienzo)
        for (p, _), (px, py) in zip(pixs, posiciones):
            pintor.fillRect(px + 3, py + 3, p.width(), p.height(), QColor(0, 0, 0, 40))
            pintor.drawPixmap(px, py, p)
        pintor.end()
        guardar(lienzo, nombre)

    # ── documentos de muestra ─────────────────────────────────────────── #
    docs = []
    for clave in ("nombre_doc1", "nombre_doc2", "nombre_doc3"):
        ruta = os.path.join(tmp, m[clave])
        _pdf_general(m, ruta)
        docs.append(ruta)
    formulario = os.path.join(tmp, m["nombre_formulario"])
    _pdf_formulario(m, formulario)
    firmado = os.path.join(tmp, m["nombre_firmado"])
    _pdf_firmado(m, docs[0], firmado, tmp)

    # ── la ventana ───────────────────────────────────────────────────── #
    for ruta in reversed(docs):
        w.open_path(ruta)
    w.sidebar.show_panel("thumbs")
    shot("ventana", None)
    shot("pestanas", (0, 0, 380, 420))

    w.show_find()
    w._find_edit.setText(m["buscar"])
    w._find_step(0)
    shot("buscar", (300, 0, 980, 560))
    w.hide_find()

    # Zoom: barra de estado (abajo a la derecha).
    w._set_custom_zoom(150)
    shot("zoom", (VENTANA[0] - 520, VENTANA[1] - 40, 520, 40))
    w._set_custom_zoom(100)

    # ── comentar ─────────────────────────────────────────────────────── #
    w._toggle_tool("TEXT")
    w.doc[0].add_freetext_annot(fitz.Rect(250, 24, 560, 62), m["texto_anotacion"],
                                fontsize=16, text_color=(0.82, 0.20, 0.22))
    w.mark_modified()
    w.render_page()
    shot("texto")
    w._toggle_tool("TEXT")

    w._toggle_tool("NOTE")
    w.add_note(fitz.Point(540, 150), m["nota_texto"])
    shot("nota")
    w._toggle_tool("NOTE")

    w._toggle_tool("MARKUP")
    hits = doc_tools.search_document(w.doc, m["resaltar"])
    rects0 = [r for p, r in hits if p == 0]
    if rects0:
        w.add_text_markup(rects0, "highlight")
    shot("resaltar")
    shot("comentar")
    w._toggle_tool("MARKUP")

    w._toggle_tool("RECT")
    utils.PDFUtils.add_rectangle_annotation(w.doc, 0, fitz.Rect(62, 66, 440, 112),
                                            color=(0.82, 0.20, 0.22), width=2, corner_radius=6)
    w.mark_modified()
    w.render_page()
    shot("rectangulo")
    w._toggle_tool("RECT")

    w._toggle_tool("EMOJI")
    esperar(segundos=3)
    shot("emoji")
    w._toggle_tool("EMOJI")

    w.sidebar.show_panel("comments")
    shot("comentarios")
    w.sidebar.show_panel("thumbs")

    # ── editar contenido ─────────────────────────────────────────────── #
    w._toggle_tool("EDIT")
    shot("editar")
    w._toggle_tool("EDIT")

    # ── páginas ──────────────────────────────────────────────────────── #
    w._set_pages_mode(True)
    shot("organizar")
    w._pages_op("crop")
    shot("recortar")
    w._cancel_crop()
    w._set_pages_mode(False)

    # Organizar › Combinar PDF…
    barra = w.menuBar()
    acciones = {a.text(): a for a in barra.actions()}

    def menu_de(texto_menu):
        for a in barra.actions():
            if a.text() == texto_menu:
                return a.menu()
        raise KeyError(texto_menu)

    from idioma import tr
    org = menu_de(tr("&Organizar"))
    sub = next(a for a in org.actions() if a.menu() and a.text() == tr("Combinar PDF…"))
    menus([(org, sub), (sub.menu(), None)], "combinar")

    ayuda = menu_de(tr("A&yuda"))
    sub = next(a for a in ayuda.actions() if a.menu() and a.text() == tr("Idioma"))
    menus([(ayuda, sub), (sub.menu(), None)], "idioma")
    del acciones

    # Menú del botón derecho del Explorador (ilustración con los textos y el
    # icono reales del submenú; el resto del menú es el de Windows).
    from PyQt6.QtGui import QIcon
    import idioma
    textos = __import__("json").load(open(os.path.join(
        RAIZ, "empaquetado", "idiomas",
        "instalador.json" if idioma.ACTUAL == "es" else f"instalador_{idioma.ACTUAL}.json"),
        encoding="utf-8"))
    textos = textos.get("es", textos)
    exp = QMenu()
    for t in m["explorador_opciones"].split("|"):
        exp.addAction(t)
    exp.addSeparator()
    sub_exp = exp.addMenu(QIcon(icons.APP_ICON), "AventyaPDF")
    for clave in ("MenuFirmar", "MenuCombinar", "MenuConvertir"):
        sub_exp.addAction(textos[clave])
    menus([(exp, sub_exp.menuAction()), (sub_exp, None)], "explorador")

    # ── formularios ──────────────────────────────────────────────────── #
    w.open_path(formulario)
    shot("formulario")

    # ── firmar ───────────────────────────────────────────────────────── #
    w.open_path(docs[1])
    w._toggle_tool("SIGN")
    w._sign_cert_lbl.setText("🖥️  " + m["certificado_ejemplo"])
    w._sign_cert_lbl.setStyleSheet("color: #107C10; font-weight: 600;")
    shot("firmar")
    w._toggle_tool("SIGN")

    w.open_path(firmado)
    w.sidebar.show_panel("signatures")
    w.sidebar._panels["signatures"].wait()
    esperar(20)
    shot("firmas")

    dlg = dialogs.SignOptionsDialog(w, False, TSA_PRESETS)
    dlg._reason.setCurrentText(m["motivo"])
    dlg._location.setText(m["lugar"])
    dlg._contact.setText(m["contacto"])
    shot_widget(dlg, "opciones_firma")

    dlg = firma_manuscrita_ui.HandSignatureDialog(w)
    dlg.canvas.clear()
    shot_widget(dlg, "manuscrita")

    # ── herramientas y diálogos ──────────────────────────────────────── #
    w.open_path(docs[1])
    n = len(w.doc)
    shot_widget(dialogs.OcrDialog(w, OCR_LANGS, 0, n), "ocr")
    shot_widget(dialogs.SecurityDialog(w), "proteger")
    shot_widget(dialogs.WatermarkDialog(w, n), "marca_agua")
    shot_widget(dialogs.HeaderFooterDialog(w, n), "encabezado")
    shot_widget(dialogs.ExportImagesDialog(w, n, 0), "exportar")
    shot_widget(dialogs.PropertiesDialog(w, w.doc, w.pdf_path, 0), "propiedades")

    w._btn_compress.setChecked(True)
    w._toggle_compress_panel()
    shot("comprimir")
    w._btn_compress.setChecked(False)
    w._toggle_compress_panel()

    pres = presentacion.WelcomeDialog(w)
    pres._timer.stop()
    shot_widget(pres, "presentacion")

    w.hide()
    return hechas


if __name__ == "__main__":
    import json
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    print(generar(json.loads(sys.argv[1]), sys.argv[2]))
