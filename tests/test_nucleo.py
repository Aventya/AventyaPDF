"""
Pruebas de los módulos sin interfaz: doc_tools, history, signer_backend y
signature_validation. No abren ventanas ni necesitan red.

    .\\run.ps1 -Pruebas
"""
import math
import os
import shutil
import struct
import sys
import tempfile
import unittest
from unittest import mock

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import fitz  # noqa: E402

import doc_tools  # noqa: E402
from history import Snapshot, UndoStack  # noqa: E402


def pdf_de_prueba(paginas: int = 3) -> fitz.Document:
    doc = fitz.open()
    for i in range(paginas):
        page = doc.new_page(width=595, height=842)
        page.insert_text((72, 100), f"Hola mundo pagina {i + 1}", fontsize=14)
        page.insert_text((72, 130), "Texto confidencial 12345", fontsize=12)
    return doc


def pdf_hibrido(base: bytes) -> bytes:
    """Añade a `base` una actualización incremental con referencias cruzadas
    híbridas (como las de Word/Acrobat): tabla xref clásica cuyo trailer lleva
    /XRefStm apuntando a un flujo xref que declara un objeto /Info nuevo."""
    doc = fitz.open("pdf", base)
    n = doc.xref_length()
    root = doc.pdf_catalog()
    s0 = int(base.rsplit(b"startxref", 1)[1].split()[0])
    out = bytearray(base)
    if not out.endswith(b"\n"):
        out += b"\n"
    o1 = len(out)
    out += f"{n} 0 obj\n<< /Producer (hibrido) >>\nendobj\n".encode()
    datos = bytes([1]) + struct.pack(">I", o1) + b"\x00\x00"
    o2 = len(out)
    out += (f"{n + 1} 0 obj\n<< /Type /XRef /Size {n + 2} /W [1 4 2] /Index [{n} 1] "
            f"/Length {len(datos)} >>\nstream\n").encode() + datos + b"\nendstream\nendobj\n"
    ox = len(out)
    out += (f"xref\n0 1\n0000000000 65535 f \n{n + 1} 1\n{o2:010d} 00000 n \n"
            f"trailer\n<< /Size {n + 2} /Root {root} 0 R /Prev {s0} /XRefStm {o2} "
            f"/Info {n} 0 R >>\nstartxref\n{ox}\n%%EOF\n").encode()
    return bytes(out)


def xref_hibridas(data: bytes) -> bool:
    from io import BytesIO
    from pyhanko.pdf_utils.reader import PdfFileReader
    return PdfFileReader(BytesIO(data)).xrefs.hybrid_xrefs_present


class _ConCarpeta(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="agpdf_test_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestRangos(unittest.TestCase):
    def test_rangos_validos(self):
        self.assertEqual(doc_tools.parse_page_range("1-3, 5, 8-", 10), [0, 1, 2, 4, 7, 8, 9])
        self.assertEqual(doc_tools.parse_page_range("", 3), [0, 1, 2])
        self.assertEqual(doc_tools.parse_page_range("todas", 2), [0, 1])
        self.assertEqual(doc_tools.parse_page_range("-2", 5), [0, 1])
        self.assertEqual(doc_tools.parse_page_range("2,2,2", 5), [1])

    def test_rangos_invalidos(self):
        for texto in ("0", "4-2", "x", "11", "3-12"):
            with self.subTest(texto=texto):
                with self.assertRaises(ValueError):
                    doc_tools.parse_page_range(texto, 10)


class TestHistorial(unittest.TestCase):
    def test_deshacer_rehacer(self):
        h = UndoStack()
        h.push(Snapshot(b"v1", 0, "uno"))
        h.push(Snapshot(b"v2", 1, "dos"))
        self.assertEqual(h.undo_label(), "dos")
        snap = h.undo(Snapshot(b"v3", 2, ""))
        self.assertEqual((snap.data, snap.page), (b"v2", 1))
        self.assertTrue(h.can_redo())
        self.assertEqual(h.redo_label(), "dos")
        again = h.redo(Snapshot(b"v2", 1, ""))
        self.assertEqual(again.data, b"v3")
        h.undo(Snapshot(b"v3", 2, ""))
        h.push(Snapshot(b"v2b", 1, "otra"))
        self.assertFalse(h.can_redo())

    def test_limites(self):
        h = UndoStack(max_steps=2)
        for i in range(5):
            h.push(Snapshot(bytes([i]), i, str(i)))
        self.assertEqual(len(h._undo), 2)
        h = UndoStack(max_bytes=10)
        for i in range(4):
            h.push(Snapshot(b"x" * 6, i, str(i)))
        self.assertEqual(len(h._undo), 1)     # siempre conserva al menos un paso
        self.assertIsNone(UndoStack().undo(Snapshot(b"", 0, "")))


class TestPaginas(unittest.TestCase):
    def test_girar_extraer_dividir_insertar(self):
        doc = pdf_de_prueba(5)
        doc_tools.rotate_pages(doc, [0, 2], 90)
        doc_tools.rotate_pages(doc, [0], -90)
        self.assertEqual([doc[i].rotation for i in range(3)], [0, 0, 90])

        ext = doc_tools.extract_pages(doc, [4, 0])
        self.assertEqual(len(ext), 2)
        self.assertIn("pagina 5", ext[0].get_text())

        partes = doc_tools.split_every(doc, 2)
        self.assertEqual([len(p) for p in partes], [2, 2, 1])

        otro = pdf_de_prueba(2)
        self.assertEqual(doc_tools.insert_pdf_at(doc, otro, 99), 2)   # 99 → al final
        self.assertEqual(len(doc), 7)
        self.assertEqual(doc_tools.insert_pdf_at(doc, otro, 0), 2)
        self.assertEqual(len(doc), 9)

    def test_duplicar_ultima_pagina(self):
        doc = pdf_de_prueba(2)
        doc.fullcopy_page(1, -1)       # lo que hace «Duplicar página» en la última
        self.assertEqual(len(doc), 3)
        self.assertIn("pagina 2", doc[2].get_text())
        with self.assertRaises(ValueError):
            doc.fullcopy_page(0, len(doc))


class TestTrazoAManoAlzada(unittest.TestCase):
    """(r59) Enderezado de los trazos de «Resaltar, subrayar o tachar» fuera
    del texto (viewer.straighten_stroke / viewer.squiggle)."""

    @staticmethod
    def _tembloroso(x0, y0, x1, y1, amp=3.0, n=30):
        """Recta de (x0, y0) a (x1, y1) con temblor perpendicular de ±amp."""
        largo = math.hypot(x1 - x0, y1 - y0)
        nx, ny = -(y1 - y0) / largo, (x1 - x0) / largo
        return [fitz.Point(x0 + (x1 - x0) * i / n + nx * amp * math.sin(i * 1.7),
                           y0 + (y1 - y0) * i / n + ny * amp * math.sin(i * 1.7))
                for i in range(n + 1)]

    def test_trazo_rapido_casi_horizontal_sale_recto_y_horizontal(self):
        import viewer
        pts = self._tembloroso(100, 300, 400, 310)       # ~2° e irregular
        r = viewer.straighten_stroke(pts, 0.15)
        self.assertEqual(len(r), 2)
        self.assertAlmostEqual(r[0].y, r[1].y)
        self.assertAlmostEqual(r[0].x, pts[0].x)
        self.assertAlmostEqual(r[1].x, pts[-1].x)

    def test_trazo_rapido_en_diagonal_sale_recto_sin_forzar_el_eje(self):
        import viewer
        pts = self._tembloroso(100, 100, 300, 300)
        r = viewer.straighten_stroke(pts, 0.15)
        self.assertEqual([(p.x, p.y) for p in r], [(pts[0].x, pts[0].y), (pts[-1].x, pts[-1].y)])

    def test_la_velocidad_cuenta_en_pixeles_de_pantalla(self):
        """Mismo trazo diagonal y misma duración (1 s): rápido o lento según el
        zoom, porque lo que mueve la mano son píxeles de pantalla."""
        import viewer
        pts = self._tembloroso(100, 100, 400, 400, amp=30)   # ~424 pt, temblor claro
        self.assertEqual(len(viewer.straighten_stroke(pts, 1.0, scale=3.0)), 2)
        self.assertGreater(len(viewer.straighten_stroke(pts, 1.0, scale=0.3)), 2)

    def test_trazo_lento_y_curvo_se_respeta(self):
        """Lento = a mano alzada de verdad, aunque vaya casi en horizontal
        (el marcador antiguo lo enderezaba igualmente: la comprobación
        visual de r59 lo destapó)."""
        import viewer
        for amp in (80, 25):
            pts = [fitz.Point(100 + 6 * i, 330 + amp * math.sin(i / 5)) for i in range(60)]
            self.assertEqual(len(viewer.straighten_stroke(pts, 2.5)), len(pts))

    def test_trazo_lento_pero_recto_pierde_el_temblor(self):
        import viewer
        pts = self._tembloroso(100, 300, 400, 300, amp=1.0)
        r = viewer.straighten_stroke(pts, 3.0)
        self.assertEqual(len(r), 2)
        self.assertAlmostEqual(r[0].y, r[1].y)

    def test_trazo_rapido_pero_claramente_curvo_se_respeta(self):
        import viewer
        pts = [fitz.Point(200 + 50 * math.cos(t / 10), 200 + 50 * math.sin(t / 10))
               for t in range(0, 50)]                    # medio círculo largo
        self.assertEqual(len(viewer.straighten_stroke(pts, 0.1)), len(pts))

    def test_ondulado_alterna_a_cada_lado_del_trazo(self):
        import viewer
        pts = viewer.squiggle([fitz.Point(100, 200), fitz.Point(200, 200)], 2.0)
        self.assertGreater(len(pts), 10)
        lados = {round(p.y - 200, 3) for p in pts}
        self.assertEqual(lados, {-1.8, 1.8})


class TestTexto(unittest.TestCase):
    def test_busqueda(self):
        doc = pdf_de_prueba(3)
        hits = doc_tools.search_document(doc, "confidencial")
        self.assertEqual([p for p, _r in hits], [0, 1, 2])
        self.assertEqual(doc_tools.search_document(doc, ""), [])
        self.assertEqual(len(doc_tools.search_document(doc, "Hola", max_hits=2)), 2)

    def test_seleccion_de_palabras(self):
        doc = pdf_de_prueba(1)
        page = doc[0]
        words = page.get_text("words")
        # PyMuPDF 1.28 no tiene Rect.center.
        centro = lambda w: fitz.Point((w[0] + w[2]) / 2, (w[1] + w[3]) / 2)  # noqa: E731
        rects, texto = doc_tools.word_selection(page, centro(words[0]), centro(words[1]), words)
        self.assertEqual(texto, "Hola mundo")
        self.assertEqual(len(rects), 1)
        # Arrastrar hasta la segunda línea devuelve un rectángulo por línea.
        ultima = words[-1]
        rects, texto = doc_tools.word_selection(page, centro(words[0]), centro(ultima), words)
        self.assertEqual(len(rects), 2)
        self.assertTrue(texto.endswith("12345"))
        # Empezar lejos de cualquier palabra no selecciona nada.
        self.assertEqual(doc_tools.word_selection(page, fitz.Point(500, 800),
                                                  centro(words[0]), words), ([], ""))

    @staticmethod
    def _copiar_todo(page) -> str:
        words = page.get_text("words")
        return doc_tools.word_selection(page, fitz.Point(words[0][0] + 1, words[0][1] + 1),
                                        fitz.Point(words[-1][2] - 1, words[-1][3] - 1), words)[1]

    def test_copiar_une_los_renglones_de_cada_parrafo(self):
        """(r34) Al pegar en el Bloc de notas, un párrafo sale en una sola línea;
        se conservan los saltos del autor (listas, final de párrafo, sangría)."""
        doc = fitz.open()
        page = doc.new_page()
        y = [80]

        def renglones(lineas, x=60):
            for t in lineas:
                page.insert_text((x, y[0]), t, fontsize=11, fontname="helv")
                y[0] += 15

        renglones(["El presente contrato de arrendamiento se celebra entre las partes abajo",
                   "firmantes, que declaran tener capacidad legal suficiente para obligar-",
                   "se en los términos establecidos en las siguientes cláusulas vigentes."])
        y[0] += 12
        renglones(["PRIMERA. Objeto del contrato.", "Lista de documentos:",
                   "1. Copia del DNI", "2. Nómina del último mes", "- Aval bancario"])
        y[0] += 14
        renglones(["      Párrafo con sangría que continúa en la línea de abajo porque es",
                   "largo, y termina aquí.", "Otro párrafo corto seguido."])
        self.assertEqual(self._copiar_todo(page).split("\n"), [
            "El presente contrato de arrendamiento se celebra entre las partes abajo "
            "firmantes, que declaran tener capacidad legal suficiente para obligarse en "
            "los términos establecidos en las siguientes cláusulas vigentes.",
            "",
            "PRIMERA. Objeto del contrato.",
            "Lista de documentos:",
            "1. Copia del DNI",
            "2. Nómina del último mes",
            "- Aval bancario",
            "",
            "Párrafo con sangría que continúa en la línea de abajo porque es largo, y "
            "termina aquí.",
            "Otro párrafo corto seguido.",
        ])

    def test_copiar_no_parte_una_linea_troceada(self):
        """(r34) En la capa de OCR de un escaneo torcido MuPDF parte una línea
        visual en trozos a alturas algo distintas: el texto copiado no debe
        llevar saltos en mitad de la frase."""
        doc = fitz.open()
        page = doc.new_page()
        trozos = ["El arrendador cede", "al arrendatario", "el uso de la vivienda"]
        x = 60.0
        for i, t in enumerate(trozos):
            page.insert_text((x, 100 + i * 1.6), t, fontsize=12, fontname="helv")
            x += fitz.get_text_length(t + " ", fontname="helv", fontsize=12) + 25
        claves = {(w[5], w[6]) for w in page.get_text("words")}
        self.assertGreater(len(claves), 1)          # MuPDF sí lo ve troceado
        self.assertEqual(self._copiar_todo(page),
                         "El arrendador cede al arrendatario el uso de la vivienda")


class TestDependencias(unittest.TestCase):
    """(r33) Todos los paquetes de requirements.txt son obligatorios: lo que
    falte o tenga una versión menor se instala a la fuerza al arrancar."""

    def _requisitos(self, texto: str) -> str:
        fd, ruta = tempfile.mkstemp(suffix=".txt")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(texto)
        self.addCleanup(os.remove, ruta)
        return ruta

    def test_todo_lo_de_requirements_esta_instalado(self):
        import dependencias
        nombres = [n for n, _v in dependencias.requisitos()]
        self.assertIn("pdf2docx", nombres)          # ya no es opcional
        self.assertIn("PyQt6", nombres)
        self.assertEqual(dependencias.faltan(), [])
        self.assertFalse(os.path.exists(os.path.join(RAIZ, "requirements-opcional.txt")))

    def test_detecta_paquetes_ausentes_y_versiones_viejas(self):
        import dependencias
        ruta = self._requisitos("# comentario\nPyMuPDF>=1.0\n"
                                "paquete-que-no-existe-agpdf>=1.0\n"
                                "keyring>=9999.0  # demasiado nuevo\n")
        faltan = dependencias.faltan(ruta)
        self.assertEqual(len(faltan), 2)
        self.assertEqual(faltan[0], "paquete-que-no-existe-agpdf")
        self.assertTrue(faltan[1].startswith("keyring (hay "))

    def test_instala_lo_que_falta_y_avisa_si_no_puede(self):
        import dependencias
        ruta = self._requisitos("paquete-que-no-existe-agpdf>=1.0\n")
        with mock.patch.object(dependencias, "instalar") as instalar:
            with self.assertRaises(dependencias.DependenciasError):
                dependencias.asegurar(ruta, report=lambda _t: None)
            instalar.assert_called_once()
        ruta_ok = self._requisitos("PyMuPDF>=1.0\n")
        with mock.patch.object(dependencias, "instalar") as instalar:
            dependencias.asegurar(ruta_ok, report=lambda _t: None)
            instalar.assert_not_called()


class TestFondoFirma(unittest.TestCase):
    """signature_background.pdf (MOSCA.svg) debe ser vectorial y sin bordes:
    con la máscara rasterizada por Edge se colaba una línea de 1 px en el
    perímetro del lienzo del logotipo."""

    def setUp(self):
        from signer_backend import BACKGROUND_PDF
        self.assertTrue(os.path.isfile(BACKGROUND_PDF), "falta signature_background.pdf")
        self.doc = fitz.open(BACKGROUND_PDF)

    def test_sin_imagenes_rasterizadas(self):
        imagenes = [x for x in range(1, self.doc.xref_length())
                    if "/Subtype/Image" in self.doc.xref_object(x, compressed=True)]
        self.assertEqual(imagenes, [])

    def test_perimetro_del_lienzo_transparente(self):
        src = self.doc
        r = src[0].rect
        for zoom in (0.25, 0.5, 1.0):            # tamaños de sello habituales en pantalla
            with self.subTest(zoom=zoom):
                o = fitz.open()
                p = o.new_page(width=r.width, height=r.height)
                p.draw_rect(p.rect, fill=(1, 1, 1), color=None)
                p.show_pdf_page(p.rect, src, 0)
                pix = p.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
                w, h = pix.width, pix.height
                # Esquinas y bordes junto a ellas: fuera del círculo, blanco puro.
                puntos = [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1),
                          (int(w * 0.08), 0), (0, int(h * 0.08)),
                          (w - 1, int(h * 0.92)), (int(w * 0.92), h - 1)]
                for x, y in puntos:
                    self.assertGreaterEqual(min(pix.pixel(x, y)), 254, f"píxel {x},{y}")


def foto_de_prueba(w: int, h: int) -> fitz.Pixmap:
    """RGB con ruido y bandas: se comprime como una fotografía."""
    datos = bytearray(os.urandom(w * h * 3))
    for y in range(0, h, 5):
        datos[y * 3 * w:(y + 1) * 3 * w:3] = bytes([(y * 255) // h]) * w
    return fitz.Pixmap(fitz.csRGB, w, h, bytes(datos), 0)


def pdf_con_fotos(tamanos=((595.276, 841.89),)) -> bytes:
    """Una página por tamaño, con una foto JPEG a ~400 ppp, un PNG a ~300 ppp,
    texto y una nota."""
    foto = foto_de_prueba(1600, 1067)
    jpeg = foto.tobytes("jpeg", jpg_quality=95)
    doc = fitz.open()
    for w, h in tamanos:
        page = doc.new_page(width=w, height=h)
        page.insert_text((30, 40), "Texto que debe sobrevivir", fontsize=12)
        page.insert_image(fitz.Rect(30, 60, 30 + 288, 60 + 192), stream=jpeg)
        page.insert_image(fitz.Rect(30, 270, 30 + 144, 270 + 96), pixmap=foto_de_prueba(600, 400))
        page.add_text_annot((w - 40, 40), "Nota")
    return doc.tobytes(garbage=3, deflate=True)


class TestCompresion(unittest.TestCase):
    """Compresión tipo Acrobat/iLovePDF con el límite de 75 ppp en DIN A4."""

    @classmethod
    def setUpClass(cls):
        import pdf_compression
        cls.pc = pdf_compression
        cls.a4 = pdf_con_fotos()
        cls.resultados = {lvl.key: pdf_compression.compress(cls.a4, lvl.key)
                          for lvl in pdf_compression.LEVELS}

    @staticmethod
    def _pdf_con_capa_ocr() -> bytes:
        """Página escaneada con una capa invisible «de Tesseract» (fuente
        GlyphLessFont, posiciones de 6 decimales) que además arrastra, sin
        dibujarla, la imagen interna del OCR, como hacía la app hasta r35."""
        capa = fitz.open()
        cp = capa.new_page(width=420, height=300)
        cp.insert_font(fontname="F0", fontbuffer=fitz.Font("helv").buffer)
        font = [f for f in cp.get_fonts(full=True)][0][0]
        capa.xref_set_key(font, "BaseFont", "/ABCDEF+GlyphLessFont")
        oculta = fitz.Pixmap(fitz.csGRAY, fitz.IRect(0, 0, 600, 400), 0)
        oculta.clear_with(200)
        cp.insert_image(fitz.Rect(0, 0, 1, 1), pixmap=oculta)
        partes = []
        y = 250.123456
        for fila in range(12):
            partes.append(f"BT 3 Tr /F0 11.23999 Tf 20.120001 {y - fila * 16.000001:.6f} Td")
            for i, palabra in enumerate(("Factura", "número", f"{fila}2026", "pendiente",
                                         "de", "pago", "Madrid")):
                partes.append(f"{93 + i} Tz ({palabra}) Tj {41.719999 + i * 0.333333:.6f} 0 Td")
            partes.append("ET")
        capa.update_stream(cp.get_contents()[0], " ".join(partes).encode("latin-1"))
        doc = fitz.open()
        page = doc.new_page(width=420, height=300)
        page.insert_image(page.rect, stream=imagen_con_texto("Factura escaneada"))
        page.show_pdf_page(page.rect, capa, 0, overlay=True)
        return doc.tobytes(garbage=3, deflate=True)

    def test_compacta_la_capa_de_texto_del_ocr(self):
        """(r35) La capa de OCR se guarda con posiciones a 0,1 pt (sin acumular
        error en los desplazamientos relativos), sin la imagen oculta y con el
        mismo texto en el mismo sitio."""
        data = self._pdf_con_capa_ocr()
        original = fitz.open("pdf", data)
        with mock.patch.object(self.pc, "_has_ocr_layer", return_value=False):
            sin = self.pc.compress(data, "baja")
        con = self.pc.compress(data, "baja")
        self.assertLess(con.size, sin.size)
        res = fitz.open("pdf", con.data)
        imagenes = [x for x in range(1, res.xref_length())
                    if "/Subtype/Image" in res.xref_object(x, compressed=True)]
        self.assertEqual(len(imagenes), 1, "la imagen oculta del OCR debe desaparecer")
        wa, wb = original[0].get_text("words"), res[0].get_text("words")
        self.assertEqual([w[4] for w in wa], [w[4] for w in wb])
        self.assertLess(max(abs(a[i] - b[i]) for a, b in zip(wa, wb) for i in range(4)), 0.1)
        capa = [x for x in range(1, res.xref_length())
                if "/Subtype/Form" in res.xref_object(x, compressed=True)
                and b"Tj" in (res.xref_stream(x) or b"")]
        self.assertTrue(capa)
        self.assertNotRegex(res.xref_stream(capa[0]), rb"\d\.\d{3,}")
        # Un flujo con operadores que no son de texto no se toca.
        self.assertIsNone(self.pc.compact_ocr_text(b"q 1.123456 0 0 1 0 0 cm /Im0 Do Q"))

    def test_el_texto_escaneado_sigue_legible_en_todos_los_niveles(self):
        """(r36) Una imagen con texto nunca baja de TEXT_MIN_PPI ni de calidad
        TEXT_MIN_JPEG_QUALITY; una foto sí se reduce según el nivel."""
        src = fitz.open()
        p = src.new_page()
        y = 60
        for t in (6, 8, 10, 12) * 6:
            p.insert_text((40, y), "El arrendatario abonará 1.245,50 euros el día 5 de cada mes.",
                          fontsize=t, fontname="tiro")
            y += t * 2.2
        escaneo = p.get_pixmap(dpi=300, colorspace=fitz.csGRAY)
        self.assertTrue(self.pc.looks_like_text(escaneo))
        self.assertFalse(self.pc.looks_like_text(foto_de_prueba(800, 600)))
        doc = fitz.open()
        page = doc.new_page()
        page.insert_image(page.rect, stream=escaneo.tobytes("jpeg", jpg_quality=92))
        data = doc.tobytes(garbage=3, deflate=True)
        for lvl in self.pc.LEVELS:
            with self.subTest(nivel=lvl.key):
                res = self.pc.compress(data, lvl.key)
                self.assertEqual(res.text_images, 1)
                self.assertGreaterEqual(res.min_print_ppi, self.pc.TEXT_MIN_PPI - 1)
                out = fitz.open("pdf", res.data)
                x = out[0].get_images()[0][0]
                calidad = fitz.Pixmap(out, x)
                # Mismo contenido: la diferencia media con el original reducido es pequeña.
                ref = fitz.Pixmap(escaneo, calidad.width, calidad.height, None)
                dif = sum(abs(a - b) for a, b in zip(ref.samples[::97], calidad.samples[::97]))
                self.assertLess(dif / len(ref.samples[::97]), 6)
        # Las fotos siguen bajando al nivel (el suelo solo es para texto).
        self.assertLess(self.resultados["extrema"].min_print_ppi, self.pc.TEXT_MIN_PPI)

    def test_tres_niveles_reducen_y_ordenan(self):
        r = self.resultados
        for key, res in r.items():
            with self.subTest(nivel=key):
                self.assertTrue(res.smaller, f"{key}: {res.size} >= {res.original_size}")
        self.assertLessEqual(r["extrema"].size, r["recomendada"].size)
        self.assertLessEqual(r["recomendada"].size, r["baja"].size)
        self.assertGreater(r["extrema"].saved_percent, 80)

    def test_nunca_por_debajo_de_75_ppp_en_a4(self):
        for key, res in self.resultados.items():
            with self.subTest(nivel=key):
                self.assertGreaterEqual(res.min_print_ppi, self.pc.MIN_PRINT_PPI)
                self.assertLessEqual(res.min_print_ppi, max(res.color_ppi, 76) * 1.5 + 1)
        # Extrema en A4: al mínimo permitido (objetivo 75 + margen de redondeo).
        self.assertLess(self.resultados["extrema"].min_print_ppi, 80)

    def test_pagina_menor_que_a4_exige_mas_ppp(self):
        a5 = pdf_con_fotos(((419.53, 595.276),))
        res = self.pc.compress(a5, "extrema")
        self.assertGreaterEqual(res.color_ppi, math.ceil(75 * 841.89 / 595.276))
        self.assertGreaterEqual(res.min_print_ppi, self.pc.MIN_PRINT_PPI)

    def test_contenido_y_anotaciones_intactos(self):
        with fitz.open("pdf", self.resultados["extrema"].data) as d:
            self.assertIn("Texto que debe sobrevivir", d[0].get_text())
            self.assertEqual(len(list(d[0].annots())), 1)
            self.assertEqual(len(d[0].get_images()), 2)

    def test_conserva_el_cifrado(self):
        cifrado = fitz.open("pdf", self.a4).tobytes(
            encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw="dueño", user_pw="abrir",
            permissions=4095)
        res = self.pc.compress(cifrado, "recomendada", password="abrir")
        self.assertTrue(res.smaller)
        with fitz.open("pdf", res.data) as d:
            self.assertTrue(d.needs_pass)
            self.assertTrue(d.authenticate("abrir"))
            self.assertIn("Texto que debe sobrevivir", d[0].get_text())

    def test_pdf_firmado_no_pierde_recursos_del_sello(self):
        """rewrite_images de MuPDF perdía los /Pattern del fondo de la firma
        («cannot find Pattern resource 'P4'»)."""
        import tempfile
        from create_test_cert import build_test_pfx
        from signer_backend import PAdESSigner
        with tempfile.TemporaryDirectory(prefix="agpdf_test_") as tmp:
            pfx = os.path.join(tmp, "prueba.pfx")
            with open(pfx, "wb") as fh:
                fh.write(build_test_pfx(b"1234"))
            firmado = PAdESSigner.sign_pdf_bytes(self.a4, pfx, "1234", 0, (300, 600, 540, 700))
        antes = self.pc._render_warnings(firmado, "")
        res = self.pc.compress(firmado, "extrema")
        self.assertEqual(self.pc._render_warnings(res.data, "") - antes, set())
        self.assertEqual(res.note, "")
        self.assertGreaterEqual(res.images_resampled, 1)
        self.assertTrue(res.smaller)

    def test_emojis_sobreviven(self):
        import emoji_font
        from PyQt6.QtWidgets import QApplication
        self.app = QApplication.instance() or QApplication(["aventyapdf"])
        doc = fitz.open("pdf", self.a4)
        x = 330
        for e in ("📌", "❤️", "✅"):
            emoji_font.add_emoji_annot(doc, 0, fitz.Point(x, 60), e, 24)
            x += 40
        data = doc.tobytes(garbage=3, deflate=True)
        antes = self.pc._render_warnings(data, "")
        res = self.pc.compress(data, "recomendada")
        self.assertEqual(self.pc._render_warnings(res.data, "") - antes, set())
        self.assertEqual(res.note, "")
        with fitz.open("pdf", res.data) as d:
            pagina = d[0]
            self.assertEqual(len(list(pagina.annots())), 4)       # 3 emojis + la nota

    def test_imagen_con_perfil_icc_roto(self):
        """Como Doc2.pdf: el /ColorSpace de la imagen apunta a un objeto que no es
        un espacio de color (allí, la apariencia de otra anotación).
        get_image_info(xrefs=True) lanzaba «invalid ICC colorspace»."""
        doc = fitz.open("pdf", self.a4)
        roto = doc.get_new_xref()
        doc.update_object(roto, "<</Type/XObject/Subtype/Form/BBox[0 0 10 10]>>")
        doc.update_stream(roto, b"0 0 10 10 re f")
        foto = next(x for x, *_r in doc[0].get_images(full=True)
                    if "DCT" in doc.xref_get_key(x, "Filter")[1])
        doc.xref_set_key(foto, "ColorSpace", f"{roto} 0 R")
        data = doc.tobytes(garbage=1)
        with self.assertRaises(Exception):              # el fallo original
            fitz.open("pdf", data)[0].get_image_info(xrefs=True)
        res = self.pc.compress(data, "extrema")
        self.assertTrue(res.smaller)
        self.assertGreaterEqual(res.images_resampled, 1)
        self.assertGreaterEqual(res.min_print_ppi, self.pc.MIN_PRINT_PPI)
        self.assertEqual(self.pc._render_warnings(res.data, "") -
                         self.pc._render_warnings(data, ""), set())

    def test_contrasena_necesaria(self):
        cifrado = fitz.open("pdf", self.a4).tobytes(
            encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw="d", user_pw="u", permissions=4095)
        with self.assertRaises(ValueError):
            self.pc.compress(cifrado, "baja")


class TestTesseract(unittest.TestCase):
    """Instalación forzada de Tesseract (simulada: no instala ni descarga nada)."""

    EXE = r"C:\Tesseract-OCR\tesseract.exe"

    def setUp(self):
        import tesseract_setup
        self.ts = tesseract_setup
        self.tmp = tempfile.mkdtemp(prefix="agpdf_tess_")
        self.tessdata = os.path.join(self.tmp, "tessdata")
        self._parche = mock.patch.object(tesseract_setup, "TESSDATA_DIR", self.tessdata)
        self._parche.start()
        self._entorno = {k: os.environ.get(k) for k in ("TESSDATA_PREFIX", "PATH")}
        self.descargas = []

    def tearDown(self):
        self._parche.stop()
        for k, v in self._entorno.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _descarga_falsa(self, url, dest, report, label):
        self.descargas.append(url)
        with open(dest, "wb") as fh:
            fh.write(b"datos de idioma")

    def test_idiomas(self):
        ts = self.ts
        self.assertEqual(ts.normalize_langs("spa+eng+spa"), ["spa", "eng"])
        self.assertEqual(ts.missing_langs("spa+eng"), ["spa", "eng"])
        os.makedirs(self.tessdata)
        with open(os.path.join(self.tessdata, "spa.traineddata"), "wb") as fh:
            fh.write(b"x")
        # Sin la marca «best» cuenta como que falta (modelo fast o estándar).
        self.assertEqual(ts.missing_langs(["spa", "eng"]), ["spa", "eng"])
        with open(os.path.join(self.tessdata, "spa.traineddata" + ts.MODEL_MARKER), "w") as fh:
            fh.write("best")
        self.assertEqual(ts.missing_langs(["spa", "eng"]), ["eng"])
        self.assertFalse(ts.Status(None, []).ready)
        self.assertFalse(ts.Status(self.EXE, ["eng"]).ready)
        self.assertTrue(ts.Status(self.EXE, []).ready)

    def test_instalado_solo_prepara_idiomas_y_entorno(self):
        ts = self.ts
        with mock.patch.object(ts, "find_tesseract", return_value=self.EXE), \
                mock.patch.object(ts, "_install_with_winget") as winget, \
                mock.patch.object(ts, "_download", side_effect=self._descarga_falsa):
            st = ts.ensure(ts.CORE_LANGS)
        winget.assert_not_called()
        self.assertTrue(st.ready)
        self.assertEqual(len(self.descargas), 3)
        self.assertEqual(os.environ["TESSDATA_PREFIX"], self.tessdata)
        self.assertIn(r"C:\Tesseract-OCR", os.environ["PATH"])

    def test_si_falta_fuerza_la_instalacion_con_winget(self):
        ts = self.ts
        instalado = []
        with mock.patch.object(ts, "find_tesseract",
                               side_effect=lambda: self.EXE if instalado else None), \
                mock.patch.object(ts, "_install_with_winget",
                                  side_effect=lambda r: instalado.append(1) or "") as winget, \
                mock.patch.object(ts, "_install_with_installer") as oficial, \
                mock.patch.object(ts, "_download", side_effect=self._descarga_falsa):
            st = ts.ensure(ts.CORE_LANGS)
        winget.assert_called_once()
        oficial.assert_not_called()
        self.assertTrue(st.ready)

    def test_si_winget_falla_usa_el_instalador_oficial(self):
        ts = self.ts
        instalado = []
        with mock.patch.object(ts, "find_tesseract",
                               side_effect=lambda: self.EXE if instalado else None), \
                mock.patch.object(ts, "_install_with_winget", return_value="winget: código 1"), \
                mock.patch.object(ts, "_install_with_installer",
                                  side_effect=lambda r: instalado.append(1) or "") as oficial, \
                mock.patch.object(ts, "_download", side_effect=self._descarga_falsa):
            self.assertTrue(ts.ensure(ts.CORE_LANGS).ready)
        oficial.assert_called_once()

    def test_error_legible_si_no_se_puede_instalar(self):
        ts = self.ts
        with mock.patch.object(ts, "find_tesseract", return_value=None), \
                mock.patch.object(ts, "_install_with_winget", return_value="winget no está disponible"), \
                mock.patch.object(ts, "_install_with_installer",
                                  side_effect=OSError("permiso denegado")):
            with self.assertRaises(ts.TesseractSetupError) as cm:
                ts.ensure(ts.CORE_LANGS)
        self.assertIn("winget no está disponible", str(cm.exception))
        self.assertIn("permiso denegado", str(cm.exception))

    def test_sustituye_modelos_que_no_son_best(self):
        """Los de la instalación son «fast» y los ya descargados antes, estándar:
        se descargan los «best» y se marcan."""
        ts = self.ts
        instalacion = os.path.join(self.tmp, "Tesseract-OCR")
        os.makedirs(os.path.join(instalacion, "tessdata"))
        os.makedirs(self.tessdata)
        for carpeta in (os.path.join(instalacion, "tessdata"), self.tessdata):
            for lang in ts.CORE_LANGS:
                with open(os.path.join(carpeta, f"{lang}.traineddata"), "wb") as fh:
                    fh.write(b"modelo antiguo")
        with mock.patch.object(ts, "find_tesseract",
                               return_value=os.path.join(instalacion, "tesseract.exe")), \
                mock.patch.object(ts, "_download", side_effect=self._descarga_falsa):
            st = ts.ensure(ts.CORE_LANGS)
        self.assertTrue(st.ready)
        self.assertEqual(sorted(self.descargas),
                         sorted(ts.TESSDATA_URL.format(lang=l) for l in ts.CORE_LANGS))
        self.assertIn("tessdata_best", ts.TESSDATA_URL)
        for lang in ts.CORE_LANGS:
            self.assertTrue(os.path.isfile(os.path.join(self.tessdata, f"{lang}.traineddata" + ts.MODEL_MARKER)))
        self.assertEqual(ts.missing_langs(ts.CORE_LANGS), [])


def _ocr_disponible() -> bool:
    import tesseract_setup
    return bool(tesseract_setup.find_tesseract()) and os.path.isfile(
        os.path.join(tesseract_setup.TESSDATA_DIR, "spa.traineddata"))


def imagen_con_texto(texto: str, girar: int = 0) -> bytes:
    """PNG en gris a 200 ppp de un párrafo (girado si se pide), como un escaneo."""
    d = fitz.open()
    p = d.new_page(width=420, height=120)
    tw = fitz.TextWriter(p.rect, color=(0.25, 0.25, 0.25))
    tw.fill_textbox(fitz.Rect(10, 10, 410, 110), texto, font=fitz.Font("helv"), fontsize=11)
    tw.write_text(p)
    if girar:
        p.set_rotation(girar)
    return p.get_pixmap(dpi=200, colorspace=fitz.csGRAY).tobytes("png")


class TestOCRLimites(unittest.TestCase):
    """«Overly large image»: página de escáner de 2480 × 3508 pt renderizada a
    400 ppp (~270 MP) al convertir a RGB."""

    def test_resolucion_limitada_en_paginas_enormes(self):
        import pdf_ocr
        doc = fitz.open()
        for w, h in ((2480, 3508), (14400, 14400), (595, 842), (200, 20000)):
            page = doc.new_page(width=w, height=h)
            dpi = pdf_ocr.render_dpi(page)
            px_w, px_h = w / 72 * dpi, h / 72 * dpi
            with self.subTest(pagina=(w, h), dpi=dpi):
                self.assertLessEqual(px_w * px_h, pdf_ocr.MAX_PIXELS * 1.001)
                self.assertLessEqual(max(px_w, px_h), pdf_ocr.MAX_SIDE)
        self.assertEqual(pdf_ocr.render_dpi(doc[2]), pdf_ocr.DPI, "A4 sigue a 400 ppp")

    def test_pagina_enorme_se_renderiza(self):
        import pdf_ocr
        doc = fitz.open()
        page = doc.new_page(width=2480, height=3508)
        page.insert_image(fitz.Rect(100, 100, 2380, 700), stream=imagen_con_texto("Texto grande"))
        dpi = pdf_ocr.render_dpi(page)
        pix = page.get_pixmap(dpi=dpi, colorspace=fitz.csGRAY, alpha=False)
        rgb = fitz.Pixmap(fitz.csRGB, pix)              # antes: FzErrorLimit
        self.assertEqual(rgb.n, 3)


@unittest.skipUnless(_ocr_disponible(), "Tesseract o el idioma español no están instalados")
class TestOCR(unittest.TestCase):
    TEXTO = ("Factura número 2026 con vencimiento en octubre. Dirección de entrega: "
             "Calle Mayor doce, Madrid. Importe pendiente de pago.")

    def test_pagina_mixta_reconoce_la_imagen_sin_duplicar_el_texto(self):
        import pdf_ocr
        doc = fitz.open()
        page = doc.new_page(width=460, height=320)
        page.insert_text((20, 30), "Encabezado real seleccionable", fontsize=13)
        zona = fitz.Rect(20, 50, 440, 170)
        page.insert_image(zona, stream=imagen_con_texto(self.TEXTO))
        page.add_text_annot((440, 300), "Nota")
        self.assertFalse(pdf_ocr.page_has_text(page) is False)     # antes se omitía
        n = pdf_ocr.ocr_page(page, "spa")
        self.assertGreater(n, 8)
        texto = page.get_text()
        self.assertIn("Madrid", texto)
        self.assertEqual(texto.count("Encabezado"), 1, "no debe duplicar el texto real")
        cajas = page.search_for("Madrid")
        self.assertTrue(cajas and all(zona.contains(c) for c in cajas), f"cajas {cajas}")
        self.assertEqual(len(list(page.annots())), 1)

    def test_detecta_la_orientacion(self):
        import pdf_ocr
        doc = fitz.open()
        page = doc.new_page(width=460, height=460)
        page.insert_image(fitz.Rect(20, 20, 440, 440), stream=imagen_con_texto(self.TEXTO, girar=90))
        self.assertIn(pdf_ocr.detect_rotation(page), (90, 270))
        self.assertGreater(pdf_ocr.ocr_page(page, "spa"), 8)
        self.assertIn("Madrid", page.get_text())
        self.assertEqual(page.rotation, 0, "la rotación original se restaura")

    def test_el_ocr_no_guarda_una_copia_oculta_de_la_pagina(self):
        """(r35) La capa de texto no debe arrastrar la imagen a 400 ppp que
        Tesseract usa por dentro: el PDF crecía ~10 veces tras el OCR."""
        import pdf_ocr
        doc = fitz.open()
        page = doc.new_page(width=460, height=320)
        page.insert_image(fitz.Rect(20, 50, 440, 170), stream=imagen_con_texto(self.TEXTO))
        antes = len(doc.tobytes(garbage=3, deflate=True))
        self.assertGreater(pdf_ocr.ocr_page(page, "spa", detect_orientation=False), 8)
        despues = doc.tobytes(garbage=3, deflate=True)
        imagenes = [x for x in range(1, doc.xref_length())
                    if "/Subtype/Image" in doc.xref_object(x, compressed=True)]
        self.assertEqual(len(imagenes), 1, "solo la imagen original")
        self.assertLess(len(despues), antes + 20_000)

    # ── (r60) OCR más preciso ──────────────────────────────────────────── #

    def _pagina_escaneada(self, girar=0, inclinar=0.0):
        """Página con el párrafo de prueba como imagen (escaneo); `inclinar`
        grados de página torcida."""
        import cv2
        import numpy as np
        png = imagen_con_texto(self.TEXTO, girar=girar)
        if inclinar:
            img = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_GRAYSCALE)
            h, w = img.shape
            m = cv2.getRotationMatrix2D((w / 2, h / 2), inclinar, 1.0)
            img = cv2.warpAffine(img, m, (w, h), borderValue=255, flags=cv2.INTER_CUBIC)
            png = cv2.imencode(".png", img)[1].tobytes()
        doc = fitz.open()
        lado = 460 if girar in (90, 270) else None
        page = doc.new_page(width=460, height=lado or 180)
        zona = fitz.Rect(20, 20, 440, (lado or 180) - 20)
        page.insert_image(zona, stream=png)
        return doc, page, zona

    def test_la_orientacion_propuesta_se_comprueba(self):
        """El OSD se equivoca (OCR.PDF: «girar 180°» con la página derecha y
        todo el OCR salía boca abajo): su propuesta se verifica."""
        import pdf_ocr
        _doc, page, _ = self._pagina_escaneada()
        with mock.patch.object(pdf_ocr, "_osd_rotation", return_value=180):
            self.assertEqual(pdf_ocr.detect_rotation(page), 0, "derecha: no se gira")
        _doc, page, _ = self._pagina_escaneada(girar=180)
        with mock.patch.object(pdf_ocr, "_osd_rotation", return_value=180):
            self.assertEqual(pdf_ocr.detect_rotation(page), 180, "boca abajo: sí")
        with mock.patch.object(pdf_ocr, "_osd_rotation", return_value=180):
            self.assertGreater(pdf_ocr.ocr_page(page, "spa"), 8)
        self.assertIn("Madrid", page.get_text())

    def test_una_capa_de_ocr_anterior_se_sustituye(self):
        """Texto invisible de un OCR anterior (malo) no cuenta como texto real:
        antes se tapaba en blanco y repetir el OCR no reconocía nada."""
        import pdf_ocr
        _doc, page, zona = self._pagina_escaneada()
        page.insert_textbox(zona, "dirdaM royaM ellaC (basura al revés) " * 6,
                            fontsize=11, render_mode=3)
        self.assertIn("basura", page.get_text())
        self.assertGreater(pdf_ocr.ocr_page(page, "spa", detect_orientation=False), 8)
        texto = page.get_text()
        self.assertNotIn("basura", texto)
        self.assertIn("Madrid", texto)

    def test_estima_la_inclinacion(self):
        import cv2
        import numpy as np
        import pdf_ocr
        img = cv2.imdecode(np.frombuffer(imagen_con_texto(self.TEXTO), np.uint8),
                           cv2.IMREAD_GRAYSCALE)
        h, w = img.shape
        for grados in (2.5, -1.8):
            m = cv2.getRotationMatrix2D((w / 2, h / 2), grados, 1.0)
            torcida = cv2.warpAffine(img, m, (w, h), borderValue=255)
            with self.subTest(grados=grados):
                self.assertAlmostEqual(pdf_ocr.skew_angle(torcida), -grados, delta=0.25)
        self.assertAlmostEqual(pdf_ocr.skew_angle(img), 0.0, delta=0.25)

    def test_pagina_torcida_se_endereza_y_la_capa_queda_sobre_el_texto(self):
        """Se reconoce sobre la imagen enderezada, pero la capa de texto se
        devuelve girada: cada palabra encontrada cae sobre tinta de la página."""
        import numpy as np
        import pdf_ocr
        doc, page, zona = self._pagina_escaneada(inclinar=3.0)
        self.assertGreater(pdf_ocr.ocr_page(page, "spa", detect_orientation=False), 8)
        self.assertIn("Madrid", page.get_text())
        pix = page.get_pixmap(dpi=144, colorspace=fitz.csGRAY, annots=False)
        img = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.stride)[:, :pix.width]
        for palabra in ("Madrid", "Factura", "entrega"):
            cajas = page.search_for(palabra)
            with self.subTest(palabra=palabra):
                self.assertTrue(cajas)
                r = (cajas[0] * fitz.Matrix(2, 2)).irect
                trozo = img[max(0, r.y0):r.y1, max(0, r.x0):r.x1]
                self.assertGreater((trozo < 128).mean(), 0.05, f"sin tinta bajo {palabra}: {r}")

    def test_pagina_solo_con_texto_no_se_toca(self):
        import pdf_ocr
        doc = fitz.open()
        page = doc.new_page(width=300, height=200)
        page.insert_text((20, 40), "Solo texto real", fontsize=14)
        objetos, contenidos = doc.xref_length(), page.get_contents()
        self.assertEqual(pdf_ocr.ocr_page(page, "spa", detect_orientation=False), 0)
        # (tobytes() no sirve para comparar: PyMuPDF genera un /ID nuevo cada vez)
        self.assertEqual(doc.xref_length(), objetos)
        self.assertEqual(page.get_contents(), contenidos)
        self.assertEqual(page.get_xobjects(), [])


def formulario_de_prueba() -> bytes:
    """Formulario con cálculo, validación, casilla, radios, lista, campo de solo
    lectura y botones (JavaScript con avisos, ResetForm, URI, página siguiente)."""
    doc = fitz.open()
    page = doc.new_page(width=420, height=360)

    def campo(tipo, nombre, rect, **kw):
        w = fitz.Widget()
        w.field_type = tipo
        w.field_name = nombre
        w.rect = fitz.Rect(rect)
        for k, v in kw.items():
            setattr(w, k, v)
        page.add_widget(w)

    T = fitz.PDF_WIDGET_TYPE_TEXT
    campo(T, "a", (20, 20, 120, 40), field_value="")
    campo(T, "b", (140, 20, 240, 40), field_value="")
    campo(T, "total", (260, 20, 360, 40), field_value="",
          script_calc='event.value = Number(this.getField("a").value) + Number(this.getField("b").value);')
    campo(T, "maximo", (20, 300, 120, 320), field_value="",
          script_change='if (Number(event.value) > 10) { app.alert("Máximo 10"); event.rc = false; }')
    campo(T, "fijo", (140, 300, 240, 320), field_value="no tocar",
          field_flags=fitz.PDF_FIELD_IS_READ_ONLY)
    campo(fitz.PDF_WIDGET_TYPE_CHECKBOX, "acepto", (20, 60, 40, 80), field_value=False)
    campo(fitz.PDF_WIDGET_TYPE_RADIOBUTTON, "color", (20, 100, 40, 120), field_value=False)
    campo(fitz.PDF_WIDGET_TYPE_RADIOBUTTON, "color", (60, 100, 80, 120), field_value=False)
    campo(fitz.PDF_WIDGET_TYPE_COMBOBOX, "pais", (20, 140, 160, 160),
          choice_values=["España", "Portugal", "Francia"], field_value="España")
    B = fitz.PDF_WIDGET_TYPE_BUTTON
    campo(B, "btn_js", (20, 200, 140, 225), button_caption="Rellenar",
          script='this.getField("a").value = "5"; this.getField("b").value = "7"; '
                 'app.alert("Datos rellenados"); app.launchURL("https://example.com", true); '
                 'this.print({bUI: true});')
    campo(B, "btn_aviso", (20, 240, 140, 265), button_caption="Aviso", script='app.alert("Solo aviso");')
    campo(B, "btn_reset", (160, 200, 280, 225), button_caption="Borrar")
    campo(B, "btn_uri", (160, 240, 280, 265), button_caption="Web")
    campo(B, "btn_next", (300, 200, 410, 225), button_caption="Siguiente")
    acciones = {"btn_reset": "<</S/ResetForm>>",
                "btn_uri": "<</S/URI/URI(https://example.com)>>",
                "btn_next": "<</S/Named/N/NextPage>>"}
    page = doc.reload_page(page)
    for w in page.widgets():
        if w.field_name in acciones:
            doc.xref_set_key(w.xref, "A", acciones[w.field_name])
    doc.new_page(width=420, height=360)
    return doc.tobytes()


class TestFormularios(unittest.TestCase):
    def setUp(self):
        import pdf_forms
        self.pf = pdf_forms
        self.doc = fitz.open("pdf", formulario_de_prueba())
        self.page = self.doc[0]

    def w(self, nombre, i=0):
        return [x for x in self.page.widgets() if x.field_name == nombre][i]

    def valor(self, nombre, i=0):
        return self.w(nombre, i).field_value

    def test_calculo_al_rellenar(self):
        ok, eventos = self.pf.set_text(self.doc, self.page, self.w("a").xref, "2")
        self.assertTrue(ok)
        self.assertEqual(eventos, [])
        self.pf.set_text(self.doc, self.page, self.w("b").xref, "3")
        self.assertEqual(self.valor("total"), "5")

    def test_boton_javascript_con_avisos_enlace_e_imprimir(self):
        original = self.w("btn_js").script
        eventos = [(e.kind, e.text) for e in self.pf.press(self.doc, self.page, self.w("btn_js").xref)]
        self.assertEqual((self.valor("a"), self.valor("b"), self.valor("total")), ("5", "7", "12"))
        self.assertIn(("alert", "Datos rellenados"), eventos)
        self.assertIn(("url", "https://example.com"), eventos)
        self.assertIn(("print", ""), eventos)
        self.assertEqual(self.w("btn_js").script, original, "el JavaScript se restaura")

    def test_validacion_rechaza_y_avisa(self):
        ok, eventos = self.pf.set_text(self.doc, self.page, self.w("maximo").xref, "50")
        self.assertFalse(ok)
        self.assertIn(("alert", "Máximo 10"), [(e.kind, e.text) for e in eventos])
        self.assertNotEqual(self.valor("maximo"), "50")

    def test_reset_enlace_y_pagina_siguiente(self):
        self.pf.set_text(self.doc, self.page, self.w("a").xref, "9")
        self.pf.press(self.doc, self.page, self.w("btn_reset").xref)
        self.assertEqual(self.valor("a"), "")
        self.assertEqual([(e.kind, e.text) for e in self.pf.press(self.doc, self.page, self.w("btn_uri").xref)],
                         [("url", "https://example.com")])
        self.assertEqual([(e.kind, e.text) for e in self.pf.press(self.doc, self.page, self.w("btn_next").xref)],
                         [("named", "NextPage")])

    def test_casilla_y_radios_excluyentes(self):
        self.pf.toggle(self.doc, self.page, self.w("acepto").xref)
        self.assertNotIn(self.valor("acepto"), (None, False, "", "Off"))
        self.pf.toggle(self.doc, self.page, self.w("acepto").xref)
        self.assertIn(self.valor("acepto"), (None, False, "", "Off"))
        self.pf.toggle(self.doc, self.page, self.w("color", 0).xref)
        self.pf.toggle(self.doc, self.page, self.w("color", 1).xref)
        self.assertIn(self.valor("color", 0), (None, False, "", "Off"))
        self.assertNotIn(self.valor("color", 1), (None, False, "", "Off"))

    def test_lista_y_persistencia(self):
        self.pf.choose(self.doc, self.page, self.w("pais").xref, "Francia")
        self.pf.set_text(self.doc, self.page, self.w("a").xref, "4")
        with fitz.open("pdf", self.doc.tobytes()) as d2:
            vals = {w.field_name: w.field_value for w in d2[0].widgets()}
        self.assertEqual((vals["pais"], vals["a"], vals["total"]), ("Francia", "4", "4"))

    def test_campos_para_la_interfaz(self):
        campos = {c["name"]: c for c in self.pf.field_boxes(self.page)}
        self.assertTrue(campos["fijo"]["readonly"])
        self.assertEqual(campos["btn_js"]["label"], "Rellenar")
        self.assertEqual([e for e, _d in campos["pais"]["choices"]], ["España", "Portugal", "Francia"])


def _fuente_windows(nombre: str) -> str:
    """Ruta de una fuente de %WINDIR%\\Fonts (las pruebas escriben con Calibri,
    como los PDF de Word, para comprobar que la app la reconoce)."""
    return os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", nombre)


# Párrafo de tres renglones que llena la columna: al leerlo se une en uno solo.
_PARRAFO_LINEAS = [
    "Un párrafo largo repartido en tres renglones que se",
    "tiene que poder reajustar al cuadro cuando se escribe",
    "más texto del que cabía en el original.",
]
PARRAFO = " ".join(_PARRAFO_LINEAS)


def pdf_con_campo_de_firma(nombre: str = "FIRMA") -> bytes:
    """PDF con un campo de firma VACÍO, como el recuadro «FIRMA» de los
    formularios de la Administración."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 100), "Formulario de prueba", fontsize=14)
    campo = fitz.Widget()
    campo.field_type = fitz.PDF_WIDGET_TYPE_SIGNATURE
    campo.field_name = nombre
    campo.rect = fitz.Rect(389, 671, 539, 703)
    page.add_widget(campo)
    return doc.tobytes()


def pdf_editable() -> bytes:
    """PDF de prueba de «Editar contenido»: cuatro párrafos escritos con Calibri
    (uno de ellos con estilos mezclados), la misma imagen colocada dos veces,
    arte vectorial, un resaltado, una marca de redacción pendiente y un campo de
    formulario. Con eso se comprueba que editar el texto no se lleva nada por
    delante."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    normal = fitz.Font(fontfile=_fuente_windows("calibri.ttf"))
    negrita = fitz.Font(fontfile=_fuente_windows("calibrib.ttf"))

    tw = fitz.TextWriter(page.rect)
    tw.append(fitz.Point(30, 60), "Importe total: 1.234,56 €", font=normal, fontsize=15)
    tw.write_text(page, color=(0.1, 0.1, 0.5))

    tw = fitz.TextWriter(page.rect)
    tw.append(fitz.Point(30, 100), "Segunda línea que no se toca", font=normal, fontsize=11)
    for i, linea in enumerate(_PARRAFO_LINEAS):
        tw.append(fitz.Point(30, 140 + i * 14), linea, font=normal, fontsize=11)
    tw.append(fitz.Point(30, 240), "Mezcla de ", font=normal, fontsize=11)
    tw.write_text(page, color=(0, 0, 0))

    tw = fitz.TextWriter(page.rect)
    tw.append(fitz.Point(30 + normal.text_length("Mezcla de ", 11), 240), "estilos",
              font=negrita, fontsize=13)
    tw.write_text(page, color=(0, 0, 0))

    # La misma imagen colocada dos veces (invariante 33: se tocan por aparición).
    roja = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 30, 30))
    roja.clear_with(220)
    for i in range(roja.width * roja.height):        # rojo: r alto, g y b bajos
        roja.set_pixel(i % roja.width, i // roja.width, (230, 60, 60))
    png = roja.tobytes("png")
    page.insert_image(fitz.Rect(320, 165, 360, 205), stream=png)
    page.insert_image(fitz.Rect(240, 165, 280, 205), stream=png)

    page.draw_line(fitz.Point(30, 330), fitz.Point(560, 330), color=(0.4, 0.4, 0.4), width=1)

    page.add_highlight_annot(fitz.Rect(30, 90, 250, 104))
    page.add_redact_annot(fitz.Rect(30, 300, 200, 320))

    campo = fitz.Widget()
    campo.field_type = fitz.PDF_WIDGET_TYPE_TEXT
    campo.field_name = "campo"
    campo.field_value = "intacto"
    campo.rect = fitz.Rect(320, 60, 520, 80)
    page.add_widget(campo)
    return doc.tobytes()


class TestEdicionTexto(unittest.TestCase):
    def setUp(self):
        import pdf_edit
        self.E = pdf_edit
        self.doc = fitz.open("pdf", pdf_editable())
        self.page = self.doc[0]

    def tearDown(self):
        self.doc.close()

    def rehacer(self) -> fitz.Page:
        """Reabre desde bytes: así se comprueba lo que quedaría guardado."""
        data = self.doc.tobytes()
        self.doc.close()
        self.doc = fitz.open("pdf", data)
        self.page = self.doc[0]
        return self.page

    def texto(self) -> str:
        return self.page.get_text().replace("\xa0", " ")

    def test_lee_los_parrafos_con_su_estilo(self):
        lineas = self.E.text_blocks(self.page)
        self.assertEqual([l.text for l in lineas],
                         ["Importe total: 1.234,56 €", "Segunda línea que no se toca",
                          PARRAFO, "Mezcla de estilos"])
        primera = lineas[0]
        self.assertEqual(primera.font, "Calibri")
        self.assertEqual(primera.size, 15.0)
        self.assertFalse(primera.bold)
        self.assertFalse(primera.mixed)
        for c, esperado in zip(primera.color, (0.1, 0.1, 0.5)):
            self.assertAlmostEqual(c, esperado, places=1)
        # La tercera mezcla Calibri 11 y Calibri negrita 13: se avisa de ello.
        self.assertTrue(lineas[3].mixed)
        # El párrafo de tres renglones se lee como UNO, con su interlineado.
        parrafo = lineas[2]
        self.assertEqual(len(parrafo.line_rects), 3)
        self.assertEqual(parrafo.line_height, 14.0)
        self.assertGreater(parrafo.first_baseline, 0)
        # block_at encuentra el párrafo por un punto de dentro y nada fuera.
        x0, y0, x1, y1 = primera.bbox
        self.assertIs(self.E.block_at(lineas, ((x0 + x1) / 2, (y0 + y1) / 2)), primera)
        self.assertIsNone(self.E.block_at(lineas, (410, 292)))

    def test_no_ofrece_el_texto_de_anotaciones_ni_de_campos(self):
        # get_text() incluye la apariencia del FreeText y del campo: redactarlos
        # no borraría nada y se escribiría un duplicado encima (invariante 34).
        a = self.page.add_freetext_annot(fitz.Rect(30, 190, 300, 215),
                                         "nota de la herramienta Texto", fontsize=11)
        a.update()
        page = self.rehacer()
        self.assertIn("nota de la herramienta Texto", self.texto())
        self.assertIn("intacto", self.texto())
        textos = [l.text for l in self.E.text_blocks(page)]
        self.assertNotIn("nota de la herramienta Texto", textos)
        self.assertFalse([t for t in textos if "intacto" in t])
        self.assertIn("Importe total: 1.234,56 €", textos)

    def test_resuelve_la_fuente_por_su_nombre(self):
        # La incrustada no vale: los subconjuntos vienen sin cmap (invariante 32).
        self.assertEqual(self.E.family_key("BCDEEE+Calibri"), "calibri")
        self.assertEqual(self.E.family_key("TimesNewRomanPS-BoldMT"), "timesnewroman")
        self.assertEqual(self.E.family_key("Arial,BoldItalic"), "arial")
        self.assertEqual(self.E.style_from_name("Arial-BoldItalic"), (True, True))
        # (r40) La fuente del documento no cambia: se usa la misma de Windows.
        f, usada = self.E.resolve_font("Calibri", self.E.FLAG_BOLD)
        self.assertEqual((f.name, usada), ("Calibri Bold", "Calibri (la del documento)"))
        f, usada = self.E.resolve_font("TimesNewRomanPS-ItalicMT", 0)
        self.assertEqual((f.name, usada),
                         ("Times New Roman Italic", "Times New Roman (la del documento)"))
        self.assertEqual(self.E.family_for("BCDEEE+Calibri", 0, True), "Calibri")
        # Una fuente que no está en Windows: la más parecida, por sus flags.
        f, usada = self.E.resolve_font("NoExisteEstaFuente", self.E.FLAG_MONO)
        self.assertEqual(usada, "Courier New (la más parecida del sistema)")
        self.assertTrue(f.has_glyph(ord("a")))
        self.assertEqual(self.E.family_for("NoExisteEstaFuente", self.E.FLAG_SERIF),
                         "Times New Roman")
        # Sin nada del sistema, la fuente base de la app (Noto).
        with mock.patch.object(self.E, "_system_font", return_value=None):
            f, usada = self.E.resolve_font("Calibri", self.E.FLAG_BOLD)
            self.assertEqual((f.name, usada), ("Noto Sans Bold", "Noto Sans negrita"))
            self.assertEqual(self.E.family_for("Consolas", 0), "Noto Sans Mono")

    def test_sustituir_conserva_todo_lo_demas(self):
        lineas = self.E.text_blocks(self.page)
        antes_dibujos = len(self.page.get_drawings())
        res = self.E.replace_block(self.page, lineas[0], "Importe: 9.999,99 €")
        self.assertEqual(res.warnings, [])
        self.assertFalse(res.overflows)
        self.assertEqual(len(res.lines), 1)
        page = self.rehacer()
        self.assertIn("Importe: 9.999,99 €", self.texto())
        self.assertNotIn("1.234,56", self.texto())
        self.assertIn("Segunda línea que no se toca", self.texto())
        self.assertEqual(len(page.get_drawings()), antes_dibujos)      # arte vectorial
        self.assertEqual(len({i[0] for i in page.get_images()}), 1)    # imagen
        self.assertEqual([a.type[1] for a in page.annots()], ["Highlight", "Redact"])
        self.assertEqual([w.field_value for w in page.widgets()], ["intacto"])

    def test_no_ejecuta_las_redacciones_pendientes(self):
        # apply_redactions() aplica TODAS las de la página: las que ya trajera
        # el PDF se apartan y se reponen (invariante 31).
        lineas = self.E.text_blocks(self.page)
        self.E.replace_block(self.page, lineas[0], "otra cosa")
        self.E.delete_block(self.page, self.E.text_blocks(self.page)[1])
        page = self.rehacer()
        marcas = list(page.annots(types=[fitz.PDF_ANNOT_REDACT]))
        self.assertEqual(len(marcas), 1)
        self.assertAlmostEqual(marcas[0].rect.x0, 30, places=0)

    def test_el_texto_nuevo_se_ve_de_verdad(self):
        # Escribir con la fuente incrustada daría glifo 0 en todos los
        # caracteres: la línea saldría en blanco, sin ningún error.
        tinta = lambda p: sum(1 for i in range(0, len(p.samples), p.n)  # noqa: E731
                              if p.samples[i] < 200)
        linea = self.E.text_blocks(self.page)[1]
        self.E.delete_block(self.page, linea)
        page = self.rehacer()
        self.assertEqual(tinta(page.get_pixmap(clip=fitz.Rect(linea.bbox), dpi=150)), 0)

        self.doc.close()
        self.doc = fitz.open("pdf", pdf_editable())
        self.page = self.doc[0]
        self.E.replace_block(self.page, self.E.text_blocks(self.page)[1],
                            "Línea reescrita ÁÉÍÓÚñ@€")
        page = self.rehacer()
        nueva = [l for l in self.E.text_blocks(page) if "reescrita" in l.text][0]
        self.assertGreater(tinta(page.get_pixmap(clip=fitz.Rect(nueva.bbox), dpi=150)), 50)

    def test_avisa_de_estilos_mezclados_y_de_texto_que_se_sale(self):
        lineas = self.E.text_blocks(self.page)
        res = self.E.replace_block(self.page, lineas[3], "Ahora todo el párrafo igual")
        self.assertTrue(any("mezclaba" in a for a in res.warnings))
        largo = "palabra " * 40
        res = self.E.replace_block(self.page, self.E.text_blocks(self.page)[0], largo)
        self.assertTrue(res.overflows)
        self.assertTrue(any("estira una esquina" in a for a in res.warnings))

    def test_el_texto_se_reajusta_al_cuadro(self):
        parrafo = [b for b in self.E.text_blocks(self.page) if len(b.line_rects) == 3][0]
        caja = fitz.Rect(parrafo.bbox)
        largo = ("Texto mucho más largo que el original, escrito expresamente para "
                 "comprobar que se reparte solo en todas y cada una de las líneas que "
                 "hagan falta, y que avisa cuando ya no cabe en el alto del cuadro.")
        # En el cuadro original no cabe, y lo dice.
        res = self.E.replace_block(self.page, parrafo, largo)
        self.assertGreater(len(res.lines), 3)
        self.assertTrue(res.overflows)
        self.assertGreater(res.needed, res.room)
        self.assertTrue(any("estira una esquina" in a for a in res.warnings))
        # Ninguna línea se pasa del ancho del cuadro.
        font, _ = self.E.resolve_font(parrafo.font, parrafo.flags)
        for linea in res.lines:
            self.assertLessEqual(font.text_length(linea, parrafo.size), caja.width + 0.5)

    def test_estirar_el_cuadro_hace_que_quepa(self):
        parrafo = [b for b in self.E.text_blocks(self.page) if len(b.line_rects) == 3][0]
        caja = fitz.Rect(parrafo.bbox)
        largo = ("Texto mucho más largo que el original, escrito para comprobar que "
                 "se reparte solo en todas las líneas que hagan falta.")
        estirado = fitz.Rect(caja.x0, caja.y0, caja.x1, caja.y0 + 120)
        res = self.E.replace_block(self.page, parrafo, largo, rect=estirado)
        self.assertFalse(res.overflows, res.warnings)
        self.assertEqual(res.warnings, [])
        page = self.rehacer()
        texto = page.get_text().replace("\xa0", " ")
        self.assertNotIn("tres renglones", texto)          # el viejo ya no está
        self.assertIn("Texto mucho más largo", texto)
        self.assertIn("Importe total", texto)              # lo de al lado, intacto
        # Vuelve a leerse como UN párrafo, con el mismo interlineado.
        nuevo = [b for b in self.E.text_blocks(page) if "mucho más largo" in b.text][0]
        self.assertEqual(len(nuevo.line_rects), len(res.lines))
        self.assertAlmostEqual(nuevo.line_height, parrafo.line_height, places=1)

    def test_un_cuadro_mas_estrecho_reparte_en_mas_lineas(self):
        parrafo = [b for b in self.E.text_blocks(self.page) if len(b.line_rects) == 3][0]
        caja = fitz.Rect(parrafo.bbox)
        ancho = self.E.replace_block(self.page, parrafo, PARRAFO, rect=caja)
        self.doc.close()
        self.doc = fitz.open("pdf", pdf_editable())
        self.page = self.doc[0]
        parrafo = [b for b in self.E.text_blocks(self.page) if len(b.line_rects) == 3][0]
        estrecho = fitz.Rect(caja.x0, caja.y0, caja.x0 + caja.width / 2, caja.y1 + 200)
        angosto = self.E.replace_block(self.page, parrafo, PARRAFO, rect=estrecho)
        self.assertGreater(len(angosto.lines), len(ancho.lines))

    def test_respeta_los_saltos_que_escribe_el_usuario(self):
        parrafo = self.E.text_blocks(self.page)[0]
        caja = fitz.Rect(parrafo.bbox)
        alto = fitz.Rect(caja.x0, caja.y0, caja.x1, caja.y0 + 80)
        res = self.E.replace_block(self.page, parrafo, "Uno\nDos\nTres", rect=alto)
        self.assertEqual(res.lines, ["Uno", "Dos", "Tres"])

    def test_una_lista_no_se_convierte_en_parrafo(self):
        # Los saltos de una lista son intencionados: no son de reajuste.
        doc = fitz.open()
        page = doc.new_page(width=420, height=300)
        cal = fitz.Font(fontfile=_fuente_windows("calibri.ttf"))
        tw = fitz.TextWriter(page.rect)
        for i, t in enumerate(["Un párrafo normal que sí llena la columna entera",
                               "y por eso se une al reajustarse sin problema."]):
            tw.append(fitz.Point(30, 50 + i * 14), t, font=cal, fontsize=11)
        for i, t in enumerate(["- Manzanas", "- Peras", "- Uvas"]):
            tw.append(fitz.Point(30, 120 + i * 14), t, font=cal, fontsize=11)
        tw.write_text(page)
        doc = fitz.open("pdf", doc.tobytes())
        bloques = self.E.text_blocks(doc[0])
        parrafo = [b for b in bloques if "columna" in b.text][0]
        lista = [b for b in bloques if "Manzanas" in b.text][0]
        self.assertNotIn("\n", parrafo.text)
        self.assertEqual(lista.text.count("\n"), 2)
        doc.close()

    def test_ensanchar_un_cuadro_estrecho_reparte_al_ancho_nuevo(self):
        """(r32) Un párrafo más estrecho que la columna de la página también es
        reajustable: al ensanchar su cuadro el texto ocupa el ancho nuevo con el
        mismo tamaño, también después de que la app lo haya estrechado."""
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 60), "Título muy largo que ocupa casi todo el ancho de la "
                                   "página de prueba", fontsize=12)
        texto = ("Este es un párrafo de prueba bastante largo que se reparte en varias "
                 "líneas dentro de una caja estrecha para ver cómo se comporta al estirarla.")
        page.insert_textbox(fitz.Rect(72, 100, 262, 300), texto, fontsize=11)
        page.insert_textbox(fitz.Rect(320, 100, 540, 300),
                            "Lista de la compra\n1. Pan de molde integral grande\n"
                            "2. Leche\n- Huevos camperos", fontsize=11)

        def parrafo():
            return [b for b in self.E.text_blocks(page) if "párrafo de prueba" in b.text][0]

        antes = parrafo()
        self.assertNotIn("\n", antes.text)
        lista = [b for b in self.E.text_blocks(page) if "Lista" in b.text][0]
        self.assertEqual(lista.text.count("\n"), 3)
        ancho = self.E.replace_block(page, antes, antes.text, rect=fitz.Rect(72, 100, 400, 300))
        self.assertLess(len(ancho.lines), len(antes.line_rects))
        # Estrechar y volver a ensanchar: el texto escrito por la app sigue fluyendo.
        estrecho = self.E.replace_block(page, parrafo(), parrafo().text,
                                        rect=fitz.Rect(72, 100, 200, 300))
        b = parrafo()
        self.assertNotIn("\n", b.text)
        self.assertEqual(b.size, antes.size)
        otra_vez = self.E.replace_block(page, b, b.text, rect=fitz.Rect(72, 100, 400, 300))
        self.assertLess(len(otra_vez.lines), len(estrecho.lines))
        self.assertEqual(otra_vez.lines, ancho.lines)
        doc.close()

    def test_avisa_de_caracteres_sin_glifo(self):
        lineas = self.E.text_blocks(self.page)
        res = self.E.replace_block(self.page, lineas[0], "Chino 漢字 y emoji")
        self.assertTrue(res.warnings)
        self.assertTrue(any("漢" in a for a in res.warnings))

    def test_borrar_un_parrafo(self):
        lineas = self.E.text_blocks(self.page)
        self.E.delete_block(self.page, lineas[1])
        self.rehacer()
        self.assertNotIn("Segunda línea", self.texto())
        self.assertIn("Importe total", self.texto())

    def test_cambiar_tamano_color_y_negrita(self):
        lineas = self.E.text_blocks(self.page)
        self.E.replace_block(self.page, lineas[1], "Ahora en rojo y negrita",
                            size=18, color=(1, 0, 0), bold=True)
        self.rehacer()
        nueva = [l for l in self.E.text_blocks(self.page) if "rojo" in l.text][0]
        self.assertEqual(nueva.size, 18.0)
        self.assertGreater(nueva.color[0], 0.9)
        self.assertLess(nueva.color[1], 0.1)
        self.assertTrue(nueva.bold)

    def test_paginas_giradas(self):
        for giro in (90, 180, 270):
            with self.subTest(giro=giro):
                doc = fitz.open("pdf", pdf_editable())
                page = doc[0]
                page.set_rotation(giro)
                linea = self.E.text_blocks(page)[0]
                # El bbox que ve el visor cae dentro de la página girada.
                self.assertTrue(fitz.Rect(linea.bbox) in page.rect + (-1, -1, 1, 1))
                self.E.replace_block(page, linea, "Girada y reescrita")
                doc = fitz.open("pdf", doc.tobytes())
                page = doc[0]
                self.assertEqual(page.rotation, giro)
                texto = page.get_text().replace("\xa0", " ")
                self.assertIn("Girada y reescrita", texto)
                self.assertIn("Segunda línea que no se toca", texto)
                # La línea nueva va en la misma dirección que las intactas.
                lineas = self.E.text_blocks(page)
                nueva = [l for l in lineas if "Girada" in l.text][0]
                otra = [l for l in lineas if "Segunda" in l.text][0]
                self.assertAlmostEqual(nueva.angle, otra.angle, places=3)
                doc.close()

    def test_el_cuadro_nunca_se_sale_de_la_pagina(self):
        # Al arrastrar un tirador fuera de la hoja, el texto se escribiría fuera:
        # invisible y sin poder volver a seleccionarlo para arreglarlo.
        pagina = self.page.rect
        acotado = self.E.clamp_box(fitz.Rect(-50, -50, 9000, 9000), pagina)
        self.assertEqual(tuple(acotado), tuple(pagina))
        diminuto = self.E.clamp_box(fitz.Rect(100, 100, 101, 101), pagina)
        self.assertGreaterEqual(diminuto.width, self.E.MIN_BOX)
        self.assertGreaterEqual(diminuto.height, self.E.MIN_BOX)
        # Un rectángulo al revés (arrastrando hacia arriba) se endereza.
        self.assertEqual(tuple(self.E.clamp_box(fitz.Rect(300, 200, 100, 50), pagina)),
                         (100.0, 50.0, 300.0, 200.0))

        parrafo = self.E.text_blocks(self.page)[0]
        caja = fitz.Rect(parrafo.bbox)
        res = self.E.replace_block(self.page, parrafo, "Sigue dentro de la página",
                                   rect=fitz.Rect(caja.x0, caja.y0, caja.x1 + 500,
                                                  caja.y1 + 500))
        self.assertTrue(fitz.Rect(res.box) in pagina + (-1, -1, 1, 1))
        page = self.rehacer()
        self.assertIn("Sigue dentro de la página", page.get_text().replace("\xa0", " "))

    def test_estirar_el_cuadro_en_paginas_giradas(self):
        # El cuadro llega del visor en coordenadas de la página VISTA: hay que
        # convertirlo con la matriz de antes de poner la rotación a 0.
        for giro in (90, 180, 270):
            with self.subTest(giro=giro):
                doc = fitz.open("pdf", pdf_editable())
                page = doc[0]
                page.set_rotation(giro)
                parrafo = [b for b in self.E.text_blocks(page)
                           if len(b.line_rects) == 3][0]
                caja = fitz.Rect(parrafo.bbox)
                res = self.E.replace_block(
                    page, parrafo, "Girada, estirada y reajustada al cuadro nuevo",
                    rect=fitz.Rect(caja.x0, caja.y0, caja.x1 + 40, caja.y1 + 40))
                self.assertTrue(fitz.Rect(res.box) in page.rect + (-1, -1, 1, 1))
                doc = fitz.open("pdf", doc.tobytes())
                texto = doc[0].get_text().replace("\xa0", " ")
                self.assertEqual(doc[0].rotation, giro)
                self.assertIn("Girada, estirada", texto)
                self.assertIn("Importe total", texto)
                doc.close()

    def test_conserva_el_cifrado(self):
        datos = fitz.open("pdf", pdf_editable()).tobytes(
            encryption=fitz.PDF_ENCRYPT_AES_256, owner_pw="jefe", user_pw="clave")
        doc = fitz.open("pdf", datos)
        self.assertTrue(doc.authenticate("clave"))
        self.E.replace_block(doc[0], self.E.text_blocks(doc[0])[0], "Cifrado y editado")
        salida = doc.tobytes(encryption=fitz.PDF_ENCRYPT_KEEP)
        doc.close()
        doc = fitz.open("pdf", salida)
        self.assertTrue(doc.needs_pass)
        self.assertTrue(doc.authenticate("clave"))
        self.assertIn("Cifrado y editado", doc[0].get_text().replace("\xa0", " "))
        doc.close()


class TestEdicionImagenes(unittest.TestCase):
    def setUp(self):
        import pdf_edit
        self.E = pdf_edit
        self.doc = fitz.open("pdf", pdf_editable())
        self.page = self.doc[0]

    def tearDown(self):
        self.doc.close()

    def rehacer(self) -> fitz.Page:
        data = self.doc.tobytes()
        self.doc.close()
        self.doc = fitz.open("pdf", data)
        self.page = self.doc[0]
        return self.page

    def test_lee_una_entrada_por_aparicion(self):
        cajas = self.E.images(self.page)
        self.assertEqual(len(cajas), 2)
        self.assertEqual(len({c.xref for c in cajas}), 1)
        self.assertTrue(all(self.E.is_shared(self.page, c) for c in cajas))
        self.assertTrue(all(c.rotation == 0 for c in cajas))
        self.assertEqual(cajas[0].width, 30)
        caja = self.E.image_at(cajas, (350, 180))
        self.assertAlmostEqual(fitz.Rect(caja.bbox).x0, 320, places=0)
        self.assertIsNone(self.E.image_at(cajas, (10, 10)))

    def test_descarta_lo_que_no_es_un_objeto_imagen(self):
        # Imágenes «en línea» y las entradas que MuPDF reconstruye (el sello de
        # una firma da varias, algunas con caja vacía) llegan con xref 0: no se
        # pueden extraer ni sustituir, así que no se ofrecen (invariante 33).
        doc = fitz.open()
        page = doc.new_page(width=200, height=200)
        page.insert_text((20, 180), "texto normal", fontsize=12)
        xref = page.get_contents()[0]
        doc.update_stream(xref, doc.xref_stream(xref) + (
            b"q 60 0 0 60 20 20 cm BI /W 2 /H 2 /CS /RGB /BPC 8 ID "
            + bytes([255, 0, 0, 0, 255, 0, 0, 0, 255, 255, 255, 0]) + b" EI Q\n"))
        doc = fitz.open("pdf", doc.tobytes())
        page = doc[0]
        self.assertEqual(len(page.get_image_info(xrefs=True)), 1)   # MuPDF sí la ve
        self.assertEqual(self.E.images(page), [])
        self.assertEqual([l.text for l in self.E.text_blocks(page)], ["texto normal"])
        doc.close()

    def test_borrar_solo_afecta_a_esa_aparicion(self):
        # Page.delete_image actúa sobre el xref y borraría las dos (invariante 33).
        cajas = self.E.images(self.page)
        self.E.delete_image(self.page, cajas[0])
        page = self.rehacer()
        quedan = self.E.images(page)
        self.assertEqual(len(quedan), 1)
        self.assertAlmostEqual(fitz.Rect(quedan[0].bbox).x0, 240, places=0)
        self.assertIn("Importe total", page.get_text().replace("\xa0", " "))
        self.assertEqual([a.type[1] for a in page.annots()], ["Highlight", "Redact"])

    def test_sustituir_solo_esa_aparicion(self):
        verde = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 30, 30))
        verde.set_rect(verde.irect, (20, 180, 60))
        cajas = self.E.images(self.page)
        self.E.place_image(self.page, cajas[0], verde.tobytes("png"))
        page = self.rehacer()
        self.assertEqual(len(self.E.images(page)), 2)
        muestra = lambda x: page.get_pixmap(  # noqa: E731
            clip=fitz.Rect(x, 175, x + 6, 181), dpi=72).pixel(0, 0)
        r, g, b = muestra(345)
        self.assertTrue(g > 120 and r < 100, f"la sustituida sigue siendo {(r, g, b)}")
        r, g, b = muestra(265)
        self.assertTrue(r > 200 and g < 180, f"la gemela ha cambiado a {(r, g, b)}")

    def test_mover_y_redimensionar(self):
        cajas = self.E.images(self.page)
        self.E.place_image(self.page, cajas[0], rect=(40, 150, 140, 250))
        page = self.rehacer()
        movida = [c for c in self.E.images(page) if fitz.Rect(c.bbox).x0 < 200
                  and fitz.Rect(c.bbox).y0 > 100][0]
        for v, esperado in zip(fitz.Rect(movida.bbox), (40, 150, 140, 250)):
            self.assertAlmostEqual(v, esperado, places=0)

    def test_extraer_los_bytes(self):
        ext, datos = self.E.image_bytes(self.page, self.E.images(self.page)[0])
        self.assertTrue(ext)
        pix = fitz.Pixmap(datos)
        self.assertEqual((pix.width, pix.height), (30, 30))


class TestHerramientas(unittest.TestCase):
    def test_marca_de_agua_y_encabezado(self):
        doc = pdf_de_prueba(3)
        doc[1].set_rotation(90)
        doc_tools.add_watermark(doc, [0, 1, 2], "BORRADOR", 48, (1, 0, 0), 0.3, 45)
        for i in range(3):
            self.assertIn("BORRADOR", doc[i].get_text(), f"página {i + 1}")
        spec = dict(hl="", hc="", hr="{bates}", fl="", fc="Pagina {n} de {total}", fr="",
                    fontsize=9, color=(0, 0, 0), margin=28,
                    bates_prefix="EXP-", bates_start=7, bates_digits=4)
        doc_tools.add_header_footer(doc, [0, 1, 2], spec)
        self.assertIn("Pagina 1 de 3", doc[0].get_text())
        self.assertIn("EXP-0008", doc[1].get_text())
        self.assertIn("Pagina 3 de 3", doc[2].get_text())

    def test_comentarios_formularios_y_aplanar(self):
        doc = pdf_de_prueba(1)
        page = doc[0]
        page.add_text_annot((300, 300), "Revisar esto")
        page.add_highlight_annot([fitz.Rect(72, 85, 200, 105)])
        w = fitz.Widget()
        w.field_type = fitz.PDF_WIDGET_TYPE_TEXT
        w.field_name = "nombre"
        w.rect = fitz.Rect(72, 400, 272, 420)
        w.field_value = "Ricardo"
        page.add_widget(w)
        resumen = doc_tools.annotation_summary(doc)
        self.assertEqual(sorted(c["label"] for c in resumen), ["Nota", "Resaltado"])
        self.assertTrue(doc.is_form_pdf)
        self.assertFalse(doc_tools.has_signatures(doc))
        doc_tools.flatten(doc)
        self.assertFalse(doc.is_form_pdf)
        self.assertEqual(doc_tools.annotation_summary(doc), [])


class TestConversion(_ConCarpeta):
    def test_imagenes_y_exportaciones(self):
        imgs = []
        for i, color in enumerate((60, 200)):
            pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 40, 30), 0)
            pix.clear_with(color)
            p = os.path.join(self.tmp, f"img{i}.png")
            pix.save(p)
            imgs.append(p)
        creado = doc_tools.images_to_pdf(imgs)
        self.assertEqual(len(creado), 2)

        doc = pdf_de_prueba(2)
        files = doc_tools.export_images(doc, [0, 1], self.tmp, "doc", dpi=50, fmt="png")
        self.assertTrue(all(os.path.getsize(f) > 0 for f in files))
        txt = os.path.join(self.tmp, "doc.txt")
        doc_tools.export_text(doc, txt)
        with open(txt, encoding="utf-8") as f:
            self.assertIn("confidencial", f.read())

    def test_combinar_varios_pdf_en_uno(self):
        # (r55) doc_tools.merge_pdfs(): menú contextual del Explorador.
        rutas = []
        for i, n in enumerate((2, 3)):
            p = os.path.join(self.tmp, f"parte{i}.pdf")
            pdf_de_prueba(n).save(p)
            rutas.append(p)
        combinado = doc_tools.merge_pdfs(rutas)
        self.assertEqual(len(combinado), 5)
        self.assertIn("pagina 1", combinado[0].get_text())
        self.assertIn("pagina 1", combinado[2].get_text())    # empieza el 2º archivo

    def test_combinar_pdf_protegido_da_error_claro(self):
        libre = os.path.join(self.tmp, "libre.pdf")
        pdf_de_prueba(1).save(libre)
        protegido = os.path.join(self.tmp, "protegido.pdf")
        data = pdf_de_prueba(1).tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="1234")
        with open(protegido, "wb") as f:
            f.write(data)
        with self.assertRaises(ValueError) as cm:
            doc_tools.merge_pdfs([libre, protegido])
        self.assertIn("protegido.pdf", str(cm.exception))


class TestCifrado(unittest.TestCase):
    def test_ida_y_vuelta(self):
        doc = pdf_de_prueba(1)
        data = doc.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="abrir",
                           owner_pw="permisos", permissions=fitz.PDF_PERM_PRINT)
        cif = fitz.open("pdf", data)
        self.assertTrue(cif.needs_pass)
        self.assertFalse(cif.authenticate("mala"))
        self.assertTrue(cif.authenticate("abrir"))
        self.assertTrue((cif.metadata or {}).get("encryption"))
        # Instantánea de deshacer: KEEP conserva el cifrado.
        again = fitz.open("pdf", cif.tobytes(encryption=fitz.PDF_ENCRYPT_KEEP))
        self.assertTrue(again.needs_pass)
        # Quitar seguridad.
        plano = fitz.open("pdf", cif.tobytes(encryption=fitz.PDF_ENCRYPT_NONE))
        self.assertFalse(plano.needs_pass)


class TestFirma(_ConCarpeta):
    @classmethod
    def setUpClass(cls):
        from create_test_cert import build_test_pfx
        cls.pfx_data = build_test_pfx(b"1234")

    def setUp(self):
        super().setUp()
        self.pfx = os.path.join(self.tmp, "prueba.pfx")
        with open(self.pfx, "wb") as f:
            f.write(self.pfx_data)

    def test_dos_firmas_incrementales_validas(self):
        from signer_backend import PAdESSigner
        from signature_validation import validate_signatures

        data = pdf_de_prueba(2).tobytes()
        uno = PAdESSigner.sign_pdf_bytes(data, self.pfx, "1234", 0, (72, 600, 272, 680),
                                         reason="Pruebas 100%", location="Madrid")
        self.assertTrue(uno.startswith(data[:8]))
        dos = PAdESSigner.sign_pdf_bytes(uno, self.pfx, "1234", 1, (72, 600, 272, 680))
        self.assertTrue(dos.startswith(uno), "la segunda firma debe ser incremental")

        doc = fitz.open("pdf", dos)
        self.assertTrue(doc_tools.has_signatures(doc))
        self.assertEqual(sorted(n for _p, n, _r in doc_tools.signature_widgets(doc)),
                         ["Firma1", "Firma2"])

        reports = validate_signatures(dos)
        self.assertEqual(len(reports), 2)
        for rep in reports:
            with self.subTest(campo=rep.field_name):
                self.assertEqual(rep.error, "")
                self.assertTrue(rep.intact and rep.valid)
                self.assertIn(rep.verdict, ("ok", "untrusted"))
                self.assertIn("Usuario de Pruebas", rep.signer)

    def test_certificacion(self):
        from signer_backend import PAdESSigner
        from signature_validation import validate_signatures

        data = pdf_de_prueba(1).tobytes()
        firmado = PAdESSigner.sign_pdf_bytes(data, self.pfx, "1234", 0, (72, 600, 272, 680),
                                             certify=True)
        reports = validate_signatures(firmado)
        self.assertEqual(len(reports), 1)
        self.assertTrue(reports[0].intact and reports[0].valid)

    def test_firma_pdf_con_xref_hibridas(self):
        """Antes: «Attempting to sign document with hybrid cross-reference
        sections while hybrid xrefs are disabled»."""
        from signer_backend import PAdESSigner
        from signature_validation import validate_signatures

        hibrido = pdf_hibrido(pdf_de_prueba(1).tobytes())
        self.assertTrue(xref_hibridas(hibrido))
        firmado = PAdESSigner.sign_pdf_bytes(hibrido, self.pfx, "1234", 0, (72, 600, 272, 680))
        self.assertFalse(xref_hibridas(firmado), "sin firmas previas se normaliza la xref")
        reports = validate_signatures(firmado)
        self.assertEqual(len(reports), 1)
        self.assertTrue(reports[0].intact and reports[0].valid)

    def test_firma_pdf_con_xref_hibridas_y_firma_previa(self):
        from signer_backend import PAdESSigner
        from signature_validation import validate_signatures

        uno = PAdESSigner.sign_pdf_bytes(pdf_de_prueba(1).tobytes(), self.pfx, "1234", 0,
                                         (72, 600, 272, 680))
        hibrido = pdf_hibrido(uno)
        self.assertTrue(xref_hibridas(hibrido))
        dos = PAdESSigner.sign_pdf_bytes(hibrido, self.pfx, "1234", 0, (72, 400, 272, 480))
        self.assertTrue(dos.startswith(hibrido), "con firma previa la firma debe ser incremental")
        reports = validate_signatures(dos)
        self.assertEqual(len(reports), 2)
        for rep in reports:
            with self.subTest(campo=rep.field_name):
                self.assertTrue(rep.intact and rep.valid)

    def test_valida_y_firma_pdf_con_xref_irregular(self):
        """(r37) PDF cuya tabla xref declara un objeto más de los que anuncia el
        tráiler (como las notificaciones del Colegio de Registradores). pyHanko
        en modo estricto ni siquiera lo abría: «Xref table size mismatch», y el
        panel Firmas decía «No se pudo validar»."""
        import re
        from io import BytesIO
        from pyhanko.pdf_utils.misc import PdfReadError
        from pyhanko.pdf_utils.reader import PdfFileReader
        from signature_validation import _open_reader, validate_signatures
        from signer_backend import PAdESSigner

        firmado = PAdESSigner.sign_pdf_bytes(pdf_de_prueba(1).tobytes(), self.pfx, "1234", 0,
                                             (72, 600, 272, 680))
        tam = list(re.finditer(rb"/Size\s+(\d+)", firmado))[-1]
        ini, fin = tam.span(1)
        roto = firmado[:ini] + str(int(tam.group(1)) - 1).encode() + firmado[fin:]
        self.assertEqual(len(roto), len(firmado))
        with self.assertRaises(PdfReadError):                 # así lo rechazaba pyHanko
            PdfFileReader(BytesIO(roto))

        # Validar: ya no lanza; el veredicto es del contenido, no del formato.
        reader = _open_reader(roto)
        self.assertEqual(len(list(reader.embedded_signatures)), 1)
        reports = validate_signatures(roto)
        self.assertEqual(len(reports), 1)
        self.assertNotIn("Xref", reports[0].error)
        # Firmar encima también funciona (incremental: no toca la firma previa).
        dos = PAdESSigner.sign_pdf_bytes(roto, self.pfx, "1234", 0, (72, 400, 272, 480))
        self.assertTrue(dos.startswith(roto), "con firma previa la firma debe ser incremental")
        reports = validate_signatures(dos)
        self.assertEqual(len(reports), 2)
        self.assertTrue(reports[-1].intact and reports[-1].valid)

    def test_firma_en_el_campo_de_firma_del_formulario(self):
        """(r38) El recuadro de firma que ya trae el formulario se rellena con
        la firma (antes se creaba un campo nuevo y el recuadro seguía vacío)."""
        import pdf_forms
        from signature_validation import validate_signatures
        from signer_backend import PAdESSigner

        data = pdf_con_campo_de_firma()
        page = fitz.open("pdf", data)[0]
        campo = [c for c in pdf_forms.field_boxes(page) if c["type"] == pdf_forms.SIGNATURE][0]
        self.assertEqual((campo["name"], campo["signed"]), ("FIRMA", False))
        r = fitz.Rect(campo["rect"])
        alto = page.rect.height
        firmado = PAdESSigner.sign_pdf_bytes(
            data, self.pfx, "1234", 0, (r.x0, alto - r.y1, r.x1, alto - r.y0),
            field_name="FIRMA")

        doc = fitz.open("pdf", firmado)
        campos = [w.field_name for p in doc for w in p.widgets()
                  if w.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE]
        self.assertEqual(campos, ["FIRMA"], "no debe crear otro campo de firma")
        reports = validate_signatures(firmado)
        self.assertEqual([x.field_name for x in reports], ["FIRMA"])
        self.assertTrue(reports[0].intact and reports[0].valid)
        # El sello se dibuja dentro del recuadro del formulario.
        pix = doc[0].get_pixmap(clip=r, dpi=150)
        tinta = sum(1 for i in range(0, len(pix.samples), pix.n) if pix.samples[i] < 200)
        self.assertGreater(tinta, 200)
        self.assertFalse(
            [c for c in pdf_forms.field_boxes(doc[0])
             if c["type"] == pdf_forms.SIGNATURE and not c["signed"]],
            "el campo debe quedar como firmado")
        # Sin nombre de campo se sigue creando uno nuevo (herramienta Firma).
        otro = PAdESSigner.sign_pdf_bytes(data, self.pfx, "1234", 0, (72, 100, 272, 160))
        nombres = [x.field_name for x in validate_signatures(otro)]
        self.assertEqual(len(nombres), 1)
        self.assertNotEqual(nombres[0], "FIRMA")

    # ── (r61) Quitar la última firma ──────────────────────────────────── #

    def _dos_firmas(self):
        from signer_backend import PAdESSigner
        data = pdf_de_prueba(2).tobytes()
        uno = PAdESSigner.sign_pdf_bytes(data, self.pfx, "1234", 0, (72, 600, 272, 680))
        dos = PAdESSigner.sign_pdf_bytes(uno, self.pfx, "1234", 1, (72, 600, 272, 680))
        return uno, dos

    def test_quitar_la_ultima_firma_conserva_las_anteriores_y_el_recuadro(self):
        from signature_validation import validate_signatures
        from signer_backend import PAdESSigner, remove_last_signature
        uno, dos = self._dos_firmas()
        antes = {r.field_name: (r.verdict, r.intact) for r in validate_signatures(dos)}
        sin = remove_last_signature(dos, "Firma2")
        self.assertTrue(sin.startswith(uno), "parte de la versión exacta de antes de Firma2")
        reports = validate_signatures(sin)
        self.assertEqual([r.field_name for r in reports], ["Firma1"])
        self.assertEqual((reports[0].verdict, reports[0].intact), antes["Firma1"],
                         "la firma anterior no cambia")
        # El recuadro sigue ahí, vacío, en la misma página y sitio.
        doc = fitz.open("pdf", sin)
        vacios = [(p.number, w.field_name, fitz.Rect(w.rect)) for p in doc for w in p.widgets()
                  if w.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE and w.field_name == "Firma2"]
        self.assertEqual(len(vacios), 1)
        self.assertEqual(vacios[0][0], 1)
        alto = doc[1].rect.height
        self.assertEqual(vacios[0][2], fitz.Rect(72, alto - 680, 272, alto - 600))
        # Y se puede volver a firmar dentro (con otro certificado, en la app).
        otra = PAdESSigner.sign_pdf_bytes(sin, self.pfx, "1234", 1, (72, 600, 272, 680),
                                          field_name="Firma2")
        reports = validate_signatures(otra)
        self.assertEqual([r.field_name for r in reports], ["Firma1", "Firma2"])
        self.assertTrue(all(r.intact and r.valid for r in reports))

    def test_solo_se_puede_quitar_la_firma_mas_reciente(self):
        from signer_backend import SigningError, remove_last_signature
        _uno, dos = self._dos_firmas()
        with self.assertRaises(SigningError) as ctx:
            remove_last_signature(dos, "Firma1")
        self.assertIn("más reciente", str(ctx.exception))

    def test_quitar_la_firma_de_un_recuadro_del_formulario(self):
        """(r38) Si el recuadro ya venía vacío en el formulario, basta volver
        a la versión anterior: queda el mismo campo, sin duplicarlo."""
        from signer_backend import PAdESSigner, remove_last_signature
        data = pdf_con_campo_de_firma()
        alto = fitz.open("pdf", data)[0].rect.height
        firmado = PAdESSigner.sign_pdf_bytes(data, self.pfx, "1234", 0,
                                             (389, alto - 703, 539, alto - 671),
                                             field_name="FIRMA")
        sin = remove_last_signature(firmado, "FIRMA")
        self.assertEqual(sin, data)
        campos = [w.field_name for p in fitz.open("pdf", sin) for w in p.widgets()
                  if w.field_type == fitz.PDF_WIDGET_TYPE_SIGNATURE]
        self.assertEqual(campos, ["FIRMA"])

    def test_sello_visual_fondo_mosca(self):
        from signer_backend import PAdESSigner

        data = pdf_de_prueba(1).tobytes()
        firmado = PAdESSigner.sign_pdf_bytes(data, self.pfx, "1234", 0, (72, 600, 272, 680))
        doc = fitz.open("pdf", firmado)
        flujos, objetos = b"", ""
        for x in range(1, doc.xref_length()):
            try:                     # la firma incremental deja objetos libres
                objetos += " " + doc.xref_object(x, compressed=True)
                if doc.xref_is_stream(x):
                    flujos += doc.xref_stream(x) or b""
            except RuntimeError:
                continue
        import re
        from signer_backend import BACKGROUND_PDF
        self.assertTrue(os.path.isfile(BACKGROUND_PDF), "falta signature_background.pdf")
        self.assertNotIn(b"0.5569 0.6314 rg", flujos)               # sin recuadro de color
        self.assertNotIn("/SigBgGS", objetos)
        # (r29) Recuadro #D1CCBD al 25 % de opacidad con esquinas de 14 pt.
        self.assertRegex(flujos, rb"q /SigPanelGS gs 0\.819608 0\.800000 0\.741176 rg "
                                 rb"14\.0000 0 m 186\.0000 0 l .* f Q")
        self.assertRegex(objetos, r"/SigPanelGS\s*<<[^>]*/ca 0?\.25\b")
        m = re.search(rb"W n ([\d.]+) 0 0 ([\d.]+) ([-\d.]+) ([-\d.]+) cm /SigBackground Do Q", flujos)
        self.assertIsNotNone(m, "el sello debe dibujar el logotipo de fondo")
        s, tx, ty = (float(m.group(i)) for i in (1, 3, 4))
        fondo = fitz.open(BACKGROUND_PDF)[0].rect
        # Recuadro de 200 × 80 pt: alto del logotipo = 80, pegado a la derecha (r30).
        self.assertAlmostEqual(s * fondo.height, 80, delta=0.01)
        self.assertAlmostEqual(tx + s * fondo.width, 200, delta=0.05)
        self.assertAlmostEqual(ty, 0, delta=0.01)

    def test_texto_del_sello_con_el_ancho_del_recuadro(self):
        """El texto va de margen a margen del recuadro en recuadros estrechos,
        proporcionados y anchos y bajos, sin salirse por arriba ni por abajo.
        (r30) Margen interno = máx(7 pt, 10 % del alto)."""
        from signer_backend import PAdESSigner
        for rect in ((72, 500, 192, 700), (72, 600, 372, 680), (72, 600, 472, 630)):
            with self.subTest(rect=rect):
                firmado = PAdESSigner.sign_pdf_bytes(pdf_de_prueba(1).tobytes(), self.pfx, "1234", 0,
                                                     rect, reason="Conformidad", location="Madrid")
                page = fitz.open("pdf", firmado)[0]
                alto = page.rect.height
                margen = max(7, 0.1 * (rect[3] - rect[1]))
                caja = fitz.Rect(rect[0], alto - rect[3], rect[2], alto - rect[1])
                palabras = [p for p in page.get_text("words")      # la página trae texto propio
                            if caja.contains(fitz.Point((p[0] + p[2]) / 2, (p[1] + p[3]) / 2))]
                self.assertTrue(palabras)
                self.assertAlmostEqual(min(p[0] for p in palabras), rect[0] + margen, delta=0.5)
                self.assertAlmostEqual(max(p[2] for p in palabras), rect[2] - margen, delta=0.5)
                self.assertGreaterEqual(min(p[1] for p in palabras), alto - rect[3] + margen - 0.5)
                self.assertLessEqual(max(p[3] for p in palabras), alto - rect[1] - margen + 0.5)

    def test_nombre_del_firmante_sin_identificadores(self):
        from signer_backend import _signer_display_name as nombre
        # Certificado de representante FNMT: givenName + surname (dos apellidos).
        self.assertEqual(nombre("NOMBRE COMPUESTO", "APELLIDO1 APELLIDO2",
                                "12345678Z NOMBRE COMPUESTO APELLIDO1 (R: B12345678)"),
                         "NOMBRE COMPUESTO APELLIDO1 APELLIDO2")
        # Sin givenName/surname: se limpia el CN.
        self.assertEqual(nombre("", "", "12345678Z NOMBRE APELLIDO1 (R: B12345678)"),
                         "NOMBRE APELLIDO1")
        self.assertEqual(nombre("", "", "X1234567L NOMBRE APELLIDO1"), "NOMBRE APELLIDO1")
        self.assertEqual(nombre("", "", "APELLIDO1 APELLIDO2 NOMBRE - NIF 12345678Z"),
                         "APELLIDO1 APELLIDO2 NOMBRE")
        self.assertEqual(nombre("", "", "Usuario de Pruebas Aventya"),
                         "Usuario de Pruebas Aventya")
        self.assertEqual(nombre("", "", ""), "Firmante desconocido")

    def test_contrasena_incorrecta(self):
        from signer_backend import PAdESSigner, SigningError
        with self.assertRaises(SigningError):
            PAdESSigner.sign_pdf_bytes(pdf_de_prueba(1).tobytes(), self.pfx, "mala", 0,
                                       (72, 600, 272, 680))

    def test_sello_de_tiempo_de_documento_se_valida(self):
        """(r45) Un campo de firma puede ser una firma normal (/Sig) o un
        sello de tiempo de documento (/DocTimeStamp, sin firmante: solo
        certifica una fecha sobre el PDF ya firmado). Antes fallaba con
        «Signature object type must be /Sig» porque se validaba siempre con
        la función pensada para firmas normales, aunque el sello fuera
        perfectamente válido (visto en «Factura Honorarios.pdf», con una
        firma y, detrás, un sello de este tipo)."""
        from io import BytesIO

        from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
        from pyhanko.sign.signers.pdf_cms import SimpleSigner
        from pyhanko.sign.signers.pdf_signer import PdfTimeStamper
        from pyhanko.sign.timestamps import DummyTimeStamper
        from signature_validation import validate_signatures
        from signer_backend import PAdESSigner

        firmado = PAdESSigner.sign_pdf_bytes(pdf_de_prueba(1).tobytes(), self.pfx, "1234", 0,
                                             (72, 600, 272, 680))
        tsa = SimpleSigner.load_pkcs12(self.pfx, passphrase=b"1234")
        stamper = PdfTimeStamper(DummyTimeStamper(tsa.signing_cert, tsa.signing_key))
        sellado = stamper.timestamp_pdf(
            IncrementalPdfFileWriter(BytesIO(firmado)), "sha256").getvalue()
        self.assertTrue(sellado.startswith(firmado), "el sello debe ser incremental")

        reports = validate_signatures(sellado)
        self.assertEqual(len(reports), 2)
        firma, sello = reports
        self.assertFalse(firma.is_timestamp)
        self.assertTrue(sello.is_timestamp)
        for rep in reports:
            self.assertEqual(rep.error, "", rep.error)
            self.assertTrue(rep.intact and rep.valid)
            self.assertIn(rep.verdict, ("ok", "untrusted"))
        self.assertIn("Usuario de Pruebas", sello.signer)
        self.assertNotEqual(sello.timestamp, "")
        self.assertEqual(sello.signed_at, "", "un sello no tiene fecha declarada aparte")
        self.assertIn("Sello de tiempo", sello.verdict_text)

    def test_una_ancla_de_la_lista_de_confianza_da_firma_de_confianza(self):
        """(r43) La validación acepta como ancla lo que traiga la lista de
        confianza de España, además del almacén de Windows. El certificado de
        pruebas es autofirmado: sin ancla, `untrusted`; con ella, `ok`."""
        from unittest import mock
        import signature_validation as sv
        from signer_backend import PAdESSigner

        firmado = PAdESSigner.sign_pdf_bytes(pdf_de_prueba(1).tobytes(), self.pfx, "1234", 0,
                                             (72, 600, 272, 680))
        self.assertEqual(sv.validate_signatures(firmado)[0].verdict, "untrusted")
        cert = list(sv._open_reader(firmado).embedded_signatures)[0].signer_cert
        with mock.patch.object(sv, "_bundled_trust_anchors", lambda: (cert,)):
            rep = sv.validate_signatures(firmado)[0]
        self.assertEqual((rep.verdict, rep.trusted), ("ok", True))
        # Si falta el archivo de la lista, se valida solo contra Windows.
        sv._bundled_trust_anchors.cache_clear()
        with mock.patch.object(sv, "TRUST_LIST", os.path.join(self.tmp, "no_existe.pem")):
            self.assertEqual(sv._bundled_trust_anchors(), ())
        sv._bundled_trust_anchors.cache_clear()


def _cert_b64(nombre: str, dias: int) -> str:
    """Certificado autofirmado (DER en base64) que caduca dentro de `dias`."""
    import base64
    import datetime
    from cryptography import x509 as cx
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    clave = ec.generate_private_key(ec.SECP256R1())
    n = cx.Name([cx.NameAttribute(NameOID.COMMON_NAME, nombre)])
    ahora = datetime.datetime.now(datetime.timezone.utc)
    c = (cx.CertificateBuilder().subject_name(n).issuer_name(n)
         .public_key(clave.public_key()).serial_number(cx.random_serial_number())
         .not_valid_before(ahora - datetime.timedelta(days=400))
         .not_valid_after(ahora + datetime.timedelta(days=dias))
         .sign(clave, hashes.SHA256()))
    return base64.b64encode(c.public_bytes(serialization.Encoding.DER)).decode()


def _tsl_de_prueba(servicios) -> bytes:
    """TSL mínima: servicios = [(tipo, estado, nombre, b64, qualifiers)]."""
    ext = ('<ServiceInformationExtensions><Extension><Qualifications xmlns="http://uri.etsi.org/'
           'TrstSvc/SvcInfoExt/eSigDir-1999-93-EC-TrustedList/#"><QualificationElement>'
           '<Qualifiers>{}</Qualifiers></QualificationElement></Qualifications></Extension>'
           '</ServiceInformationExtensions>')
    base = "http://uri.etsi.org/TrstSvc/"
    partes = []
    for tipo, estado, nombre, b64, qualifiers in servicios:
        q = "".join(f'<Qualifier uri="{base}TrustedList/SvcInfoExt/{x}"/>' for x in qualifiers)
        partes.append(
            f"<TSPService><ServiceInformation><ServiceTypeIdentifier>{base}Svctype/{tipo}"
            f"</ServiceTypeIdentifier><ServiceName><Name>{nombre}</Name></ServiceName>"
            f"<ServiceDigitalIdentity><DigitalId><X509Certificate>{b64}</X509Certificate>"
            f"</DigitalId></ServiceDigitalIdentity><ServiceStatus>{base}TrustedList/Svcstatus/"
            f"{estado}</ServiceStatus>{ext.format(q) if qualifiers else ''}"
            f"</ServiceInformation></TSPService>")
    return (
        '<TrustServiceStatusList xmlns="http://uri.etsi.org/02231/v2#"><SchemeInformation>'
        "<TSLSequenceNumber>7</TSLSequenceNumber><ListIssueDateTime>2026-01-01T00:00:00Z"
        "</ListIssueDateTime><NextUpdate><dateTime>2030-01-01T00:00:00Z</dateTime></NextUpdate>"
        "</SchemeInformation><TrustServiceProviderList><TrustServiceProvider><TSPInformation>"
        "<TSPName><Name>Proveedor de prueba</Name></TSPName></TSPInformation><TSPServices>"
        + "".join(partes) +
        "</TSPServices></TrustServiceProvider></TrustServiceProviderList>"
        "</TrustServiceStatusList>").encode()


class TestListaDeConfianza(_ConCarpeta):
    """(r43) Lista de confianza de España (TSL) para validar firmas."""

    def test_seleccion_de_servicios_de_la_tsl(self):
        import create_trust_list as ctl
        xml = _tsl_de_prueba([
            ("CA/QC", "granted", "firma", _cert_b64("Firma", 300), ["QCForESig"]),
            ("CA/QC", "granted", "sin qualifiers", _cert_b64("Sin", 300), []),
            # FNMT «AC Sector Público»: sin propósito declarado = firma por defecto.
            ("CA/QC", "granted", "sector público", _cert_b64("Publico", 300),
             ["QCQSCDManagedOnBehalf"]),
            ("TSA/QTST", "granted", "sello de tiempo", _cert_b64("TSA", 300), []),
            ("CA/QC", "granted", "solo web", _cert_b64("Web", 300), ["QCForWSA"]),
            ("CA/QC", "granted", "web y firma", _cert_b64("WebFirma", 300),
             ["QCForWSA", "QCForESeal"]),
            ("CA/QC", "withdrawn", "retirado", _cert_b64("Retirado", 300), []),
            ("CA/QC", "granted", "caducado", _cert_b64("Caducado", -10), []),
            ("Certstatus/OCSP/QC", "granted", "otro tipo", _cert_b64("Otro", 300), []),
        ])
        cab, filas = ctl.seleccionar(xml)
        self.assertEqual((cab["emision"], cab["proxima"]), ("7", "2030-01-01T00:00:00Z"))
        self.assertEqual(sorted(f[1] for f in filas),
                         ["firma", "sector público", "sello de tiempo", "sin qualifiers",
                          "web y firma"])

        # Lo escrito lo carga la validación y solo trae esos certificados.
        import signature_validation as sv
        from unittest import mock
        pem = os.path.join(self.tmp, "lista.pem")
        ctl.escribir(cab, filas, "https://ejemplo/TSL.xml", pem)
        with open(pem, encoding="utf-8") as f:
            self.assertIn("Próxima actualización: 2030-01-01", f.read())
        sv._bundled_trust_anchors.cache_clear()
        with mock.patch.object(sv, "TRUST_LIST", pem):
            anclas = sv._bundled_trust_anchors()
        sv._bundled_trust_anchors.cache_clear()
        self.assertEqual(sorted(c.subject.native["common_name"] for c in anclas),
                         ["Firma", "Publico", "Sin", "TSA", "WebFirma"])

    def test_la_lista_incluida_esta_cargada_y_vigente(self):
        import datetime
        import signature_validation as sv
        anclas = sv._bundled_trust_anchors()
        self.assertGreater(len(anclas), 100, "falta vendor/trust/es_tsl.pem")
        nombres = {c.subject.native.get("common_name", "") for c in anclas}
        self.assertIn("Autoridad de Certificación de los Registradores - AC Interna", nombres)
        self.assertIn("AC SECTOR PÚBLICO G2", nombres)
        ahora = datetime.datetime.now(datetime.timezone.utc)
        self.assertFalse([c for c in anclas
                          if c["tbs_certificate"]["validity"]["not_after"].native <= ahora],
                         "hay certificados caducados: ejecutar create_trust_list.py")
        # La TSL tiene fecha de caducidad: pasada, faltarían las CA nuevas.
        with open(sv.TRUST_LIST, encoding="utf-8") as f:
            cab = "".join(next(f) for _ in range(10))
        proxima = cab.split("Próxima actualización:")[1].splitlines()[0].strip()
        limite = datetime.datetime.fromisoformat(proxima.replace("Z", "+00:00"))
        self.assertGreater(limite, ahora,
                           "la lista de confianza ha caducado: ejecutar create_trust_list.py")

    @unittest.skipUnless(os.path.isfile(os.path.join(RAIZ, "Notificacion.PDF")),
                         "falta Notificacion.PDF")
    def test_firma_de_los_registradores_sale_de_confianza(self):
        """Antes: «Firma íntegra, identidad no verificada», porque la raíz de los
        Registradores no está en Windows (Adobe sí la da por buena: EUTL)."""
        from signature_validation import validate_signatures
        with open(os.path.join(RAIZ, "Notificacion.PDF"), "rb") as f:
            reports = validate_signatures(f.read())
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0].error, "")
        self.assertEqual(reports[0].verdict, "ok")


def _tiene_signxml() -> bool:
    try:
        import signxml  # noqa: F401
        return True
    except ImportError:
        return False


def _par_rsa_firmante(cn: str = "Firmante de prueba"):
    """(clave privada, certificado `cryptography`) autofirmado, RSA porque es
    el algoritmo por defecto de `signxml.XMLSigner`."""
    import datetime
    from cryptography import x509 as cx
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    clave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    n = cx.Name([cx.NameAttribute(NameOID.COMMON_NAME, cn)])
    ahora = datetime.datetime.now(datetime.timezone.utc)
    cert = (cx.CertificateBuilder().subject_name(n).issuer_name(n)
            .public_key(clave.public_key()).serial_number(cx.random_serial_number())
            .not_valid_before(ahora - datetime.timedelta(days=1))
            .not_valid_after(ahora + datetime.timedelta(days=365))
            .sign(clave, hashes.SHA256()))
    return clave, cert


@unittest.skipUnless(_tiene_signxml(), "falta signxml (pip install signxml; solo hace "
                     "falta para generar vendor/trust/, no para ejecutar la app)")
class TestFirmaXml(unittest.TestCase):
    """(r43) `create_trust_list.verificar_firma`: la app confía en la lista de
    España solo si la LOTL y la TSL están firmadas de verdad, no solo porque
    lleguen por HTTPS. Confirmado además a mano el 22/09/2026 contra la LOTL y
    la TSL de España reales (ver vendor/trust/oj_signers.pem)."""

    def _firmar(self, reference_uri=None):
        from lxml import etree
        from signxml import XMLSigner

        clave, cert = _par_rsa_firmante()
        doc = etree.fromstring(
            b'<Root><A Id="a">contenido A</A><B Id="b">contenido B</B></Root>')
        firmado = XMLSigner().sign(doc, key=clave, cert=[cert], reference_uri=reference_uri)
        return etree.tostring(firmado), cert

    def test_firma_valida_contra_su_ancla(self):
        import create_trust_list as ctl

        xml, cert = self._firmar(reference_uri=["#a", "#b"])
        firmante = ctl.verificar_firma(xml, [cert], refs=2)
        self.assertEqual(firmante.subject.rfc4514_string(), cert.subject.rfc4514_string())

    def test_documento_manipulado_no_valida(self):
        import create_trust_list as ctl

        xml, cert = self._firmar(reference_uri=["#a", "#b"])
        manipulado = xml.replace(b"contenido A", b"contenido X")
        self.assertNotEqual(manipulado, xml)
        with self.assertRaises(ctl.FirmaNoValida):
            ctl.verificar_firma(manipulado, [cert], refs=2)

    def test_certificado_no_incluido_en_las_anclas_no_vale(self):
        import create_trust_list as ctl

        xml, _cert = self._firmar(reference_uri=["#a", "#b"])
        _clave_otro, otro = _par_rsa_firmante("Otro firmante, no es ancla")
        with self.assertRaises(ctl.FirmaNoValida):
            ctl.verificar_firma(xml, [otro], refs=2)

    def test_numero_de_referencias_se_exige(self):
        """Una firma con menos partes de las que debería (p. ej. sin las
        propiedades XAdES) tampoco debe aceptarse aunque el certificado sea
        el correcto."""
        import create_trust_list as ctl

        xml, cert = self._firmar(reference_uri=None)          # una sola referencia
        self.assertEqual(ctl.verificar_firma(xml, [cert], refs=1).subject,
                         cert.subject)
        with self.assertRaises(ctl.FirmaNoValida):
            ctl.verificar_firma(xml, [cert], refs=2)

    def test_puntero_a_espana_toma_solo_el_de_tipo_xml(self):
        import base64
        import create_trust_list as ctl

        _clave, cert_xml = _par_rsa_firmante("Firmante TSL XML")
        _clave2, cert_pdf = _par_rsa_firmante("Firmante TSL PDF")
        der_xml = cert_xml.public_bytes(__import__(
            "cryptography.hazmat.primitives.serialization", fromlist=["Encoding"]).Encoding.DER)
        der_pdf = cert_pdf.public_bytes(__import__(
            "cryptography.hazmat.primitives.serialization", fromlist=["Encoding"]).Encoding.DER)

        def puntero(url, mime, der):
            return (
                '<OtherTSLPointer xmlns="http://uri.etsi.org/02231/v2#" '
                'xmlns:a="http://uri.etsi.org/02231/v2/additionaltypes#">'
                f"<TSLLocation>{url}</TSLLocation>"
                "<ServiceDigitalIdentity><DigitalId>"
                f"<X509Certificate>{base64.b64encode(der).decode()}</X509Certificate>"
                "</DigitalId></ServiceDigitalIdentity>"
                "<AdditionalInformation><OtherInformation>"
                "<SchemeTerritory>ES</SchemeTerritory>"
                f'<a:MimeType>{mime}</a:MimeType>'
                "</OtherInformation></AdditionalInformation>"
                "</OtherTSLPointer>")

        xml = (
            '<TrustServiceStatusList xmlns="http://uri.etsi.org/02231/v2#">'
            "<SchemeInformation><PointersToOtherTSL>"
            + puntero("https://ejemplo/TSL.pdf", "application/pdf", der_pdf)
            + puntero("https://ejemplo/TSL.xml", "application/vnd.etsi.tsl+xml", der_xml)
            + "</PointersToOtherTSL></SchemeInformation></TrustServiceStatusList>"
        ).encode()

        url, certs = ctl.puntero_es(xml)
        self.assertEqual(url, "https://ejemplo/TSL.xml")
        self.assertEqual(certs, [der_xml])

class TestFirmaManuscrita(unittest.TestCase):
    """(r68) Firma manuscrita con aspecto de estilográfica (firma_manuscrita)."""

    @staticmethod
    def _recta(x0, y0, x1, y1, segundos=0.5, n=40):
        return [(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n, segundos * i / n)
                for i in range(n + 1)]

    @staticmethod
    def _grosor_medio(pieces):
        radios = [r for pz in pieces for _x, _y, r in pz[len(pz) // 4: -len(pz) // 4]]
        return sum(radios) / len(radios)

    def test_plumilla_biselada_y_velocidad(self):
        import firma_manuscrita as fm
        # Bajar en vertical (contra el bisel) deja más tinta que ir en la
        # dirección del bisel (abajo-izquierda → arriba-derecha).
        vertical = fm.ink_pieces([self._recta(100, 20, 100, 180)], 6)
        a = fm.NIB_ANGLE
        bisel = fm.ink_pieces([self._recta(40, 180, 40 + 160 * math.cos(a),
                                           180 - 160 * math.sin(a))], 6)
        self.assertGreater(self._grosor_medio(vertical), 2 * self._grosor_medio(bisel))
        # Despacio sale más grueso que deprisa.
        lento = fm.ink_pieces([self._recta(100, 20, 100, 180, segundos=3.0)], 6)
        rapido = fm.ink_pieces([self._recta(100, 20, 100, 180, segundos=0.05)], 6)
        self.assertGreater(self._grosor_medio(lento), self._grosor_medio(rapido) * 1.2)

    def test_la_tinta_se_superpone_en_los_cruces(self):
        import firma_manuscrita as fm
        # Dos trazos = dos rellenos; un trazo que se corta a sí mismo, también
        # se parte (bucle de una «l»); uno sin cruces es un solo relleno.
        dos = fm.ink_pieces([self._recta(0, 50, 200, 50), self._recta(100, 0, 100, 100)], 4)
        self.assertEqual(len(dos), 2)
        bucle = [(100 + 60 * math.sin(t), 100 - 80 * math.sin(t / 2), t / 10)
                 for t in [i * 0.1 for i in range(64)]]
        self.assertEqual(len(fm.ink_pieces([bucle[:10]], 4)), 1)
        self.assertGreaterEqual(len(fm.ink_pieces([bucle], 4)), 2)
        ops, _caja = fm.pdf_ops(dos, (0, 0, 1))
        self.assertEqual(ops.split().count(b"f"), 2)
        # Pintado: el cruce queda más oscuro que el trazo suelto.
        doc = fitz.open()
        page = doc.new_page()
        sig = fm.HandSignature(strokes=[self._recta(0, 50, 200, 50),
                                        self._recta(100, 0, 100, 100)], width=6,
                               color=(0, 0, 0))
        rect = fm.fit_rect(sig, box=fitz.Rect(100, 100, 300, 300))
        fm.add_hand_signature(doc, 0, rect, sig)
        pix = page.get_pixmap(dpi=144)
        caja = sig.bounds()
        escala = rect.width / caja.width

        def gris(x, y):              # (x, y) en píxeles del lienzo
            px = (rect.x0 + (x - caja.x0) * escala) * 2
            py = (rect.y0 + (y - caja.y0) * escala) * 2
            return pix.pixel(int(px), int(py))[0]
        self.assertLess(gris(100, 50), gris(40, 50) - 20)
        self.assertLess(gris(40, 50), 150)

    def test_anotacion_se_mueve_sin_perder_la_apariencia(self):
        import emoji_font
        import firma_manuscrita as fm
        doc = fitz.open()
        page = doc.new_page()
        sig = fm.HandSignature(strokes=[self._recta(0, 0, 300, 60)], width=5)
        rect = fm.fit_rect(sig, center=fitz.Point(200, 200))
        self.assertAlmostEqual(rect.width, fm.DEFAULT_PLACE_WIDTH)
        self.assertAlmostEqual(rect.width / rect.height, sig.aspect(), places=3)
        a = fm.add_hand_signature(doc, 0, rect, sig)
        self.assertTrue(fm.is_hand_signature(a.info["subject"]))
        self.assertTrue(emoji_font.is_stamp(a.info["subject"]))
        self.assertFalse(emoji_font.is_emoji(a.info["subject"]))
        nuevo = rect + (50, 80, 50, 80)
        emoji_font.write_rect(page, a, nuevo)
        data = doc.tobytes(garbage=3, deflate=True)
        d2 = fitz.open("pdf", data)
        p2 = d2[0]                   # la Annot solo guarda una referencia débil a su página
        an = next(p2.annots())
        self.assertEqual(an.type[1], "Stamp")
        self.assertLess(abs(an.rect.x0 - nuevo.x0) + abs(an.rect.y1 - nuevo.y1), 0.1)
        pix = p2.get_pixmap(clip=nuevo)
        self.assertLess(min(pix.samples[0::3]), 120)               # hay tinta azul
        self.assertIn(b"AG-FIRMA", d2.xref_stream(
            int(d2.xref_get_key(an.xref, "AP/N")[1].split()[0])))

    def test_firma_desde_imagen(self):
        import firma_manuscrita as fm
        # RGBA: raya negra opaca sobre fondo transparente.
        muestras = bytearray(120 * 40 * 4)
        for x in range(10, 110):
            for y in range(18, 22):
                muestras[(y * 120 + x) * 4 + 3] = 255
        pix = fitz.Pixmap(fitz.csRGB, 120, 40, bytes(muestras), True)
        sig = fm.HandSignature(png=pix.tobytes("png"), png_size=(120, 40))
        self.assertAlmostEqual(sig.aspect(), 3.0)
        doc = fitz.open()
        page = doc.new_page()
        rect = fm.fit_rect(sig, box=fitz.Rect(50, 50, 350, 350))
        self.assertAlmostEqual(rect.width, 300)
        a = fm.add_hand_signature(doc, 0, rect, sig)
        self.assertEqual(a.info["subject"], "FirmaManuscrita|img")
        render = page.get_pixmap(clip=rect)
        self.assertLess(min(render.samples), 60)                   # la raya negra
        self.assertEqual(render.pixel(2, 2), (255, 255, 255))      # fondo transparente


if __name__ == "__main__":
    unittest.main(verbosity=2)
