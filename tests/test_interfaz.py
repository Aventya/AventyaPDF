"""
Prueba de humo de la ventana principal sin pantalla (QT_QPA_PLATFORM=offscreen).
Recorre las operaciones que no abren diálogos de archivo: abrir, zoom,
navegación, duplicar/girar/insertar/eliminar páginas, deshacer/rehacer,
marcado de texto, notas, redacción, búsqueda, panel lateral y guardar.

Los QMessageBox se sustituyen por respuestas automáticas («Sí») para que nada
se quede esperando. La configuración del usuario que toca la prueba (recientes,
panel lateral) se restaura al terminar.

    .\\run.ps1 -Pruebas
"""
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import fitz  # noqa: E402
from PyQt6.QtCore import QSettings, Qt  # noqa: E402
from PyQt6.QtWidgets import QApplication, QMessageBox  # noqa: E402

import color_picker  # noqa: E402
import doc_tools  # noqa: E402

_CLAVES = ("recent/files", "recent/dir", "view/sidebar")


def _objetos_pdf(doc) -> list[str]:
    out = []
    for x in range(1, doc.xref_length()):
        try:
            out.append(doc.xref_object(x, compressed=True))
        except Exception:  # noqa: BLE001 — objetos libres
            pass
    return out


class TestVentanaPrincipal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication(sys.argv[:1] or ["aventyapdf"])
        s = QSettings("aventyapdf", "config")
        cls._guardado = {k: s.value(k) for k in _CLAVES if s.contains(k)}

    @classmethod
    def tearDownClass(cls):
        s = QSettings("aventyapdf", "config")
        for k in _CLAVES:
            if k in cls._guardado:
                s.setValue(k, cls._guardado[k])
            else:
                s.remove(k)
        s.sync()

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="agpdf_ui_")
        si = QMessageBox.StandardButton.Yes
        self._parches = [
            mock.patch.object(QMessageBox, "question", return_value=si),
            mock.patch.object(QMessageBox, "warning", return_value=si),
            mock.patch.object(QMessageBox, "information", return_value=si),
            mock.patch.object(QMessageBox, "critical", return_value=si),
        ]
        for p in self._parches:
            p.start()
        from main_window import MainWindow
        self.w = MainWindow()
        self.w.resize(1200, 800)
        self.w.show()
        self.app.processEvents()

    def tearDown(self):
        self.w._modified = False
        for s in self.w._sessions:       # pestañas en segundo plano
            if s:
                s["_modified"] = False
        self.w.close()
        self.w.deleteLater()
        self.app.processEvents()
        for p in self._parches:
            p.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _crear_pdf(self, paginas=3) -> str:
        doc = fitz.open()
        for i in range(paginas):
            page = doc.new_page()
            page.insert_text((72, 100), f"Hola mundo pagina {i + 1}", fontsize=14)
        path = os.path.join(self.tmp, "entrada.pdf")
        doc.save(path)
        doc.close()
        return path

    def test_operaciones_de_pagina_en_el_panel_lateral(self):
        """(r27) Sin ventana de organizar: el botón pone las miniaturas del panel
        lateral en modo organizar y las acciones encima; todo con deshacer."""
        from PyQt6.QtCore import Qt, QPoint
        from PyQt6.QtGui import QKeyEvent
        from PyQt6.QtCore import QEvent
        import importlib.util
        self.assertIsNone(importlib.util.find_spec("organize_dialog"))
        w = self.w
        path = os.path.join(self.tmp, "paginas.pdf")
        doc = fitz.open()
        for i in range(4):
            doc.new_page().insert_text((72, 100), f"Pagina {i + 1}", fontsize=14)
        doc.save(path)
        doc.close()
        self.assertTrue(w.open_path(path))
        w.sidebar.collapse()
        w._toggle_tool("SIGN")
        self.app.processEvents()

        def textos():
            return [w.doc[i].get_text().strip() for i in range(len(w.doc))]

        def selecciona(rows):
            w.sidebar._flush()                  # sin esperar al temporizador
            self.app.processEvents()
            w.sidebar.thumbs.select_rows(rows)

        w._btn_pages.click()
        self.app.processEvents()
        th = w.sidebar.thumbs
        self.assertTrue(w._btn_pages.isChecked())
        self.assertTrue(w._pages_panel.isVisible())
        self.assertTrue(w.sidebar.stack.isVisible())
        self.assertEqual(w.sidebar.stack.currentWidget(), th)
        self.assertTrue(th.organizing)
        self.assertTrue(w._opt_row.isHidden())      # salió de Firma
        self.assertEqual(w.viewer.mode, "NONE")
        self.assertEqual(th.list.count(), 4)

        selecciona([1])
        self.assertIn("1 de 4", w._lbl_pages_sel.text())
        w._pages_op("right")
        self.assertEqual(w.doc[1].rotation, 90)
        w._pages_op("dup")
        self.assertEqual(textos(), ["Pagina 1", "Pagina 2", "Pagina 2", "Pagina 3", "Pagina 4"])
        w._pages_op("blank")
        self.assertEqual(len(w.doc), 6)
        w.undo()
        w.undo()
        w.undo()
        self.assertEqual(textos(), ["Pagina 1", "Pagina 2", "Pagina 3", "Pagina 4"])
        self.assertEqual(w.doc[1].rotation, 0)

        # Arrastre: el orden de la lista pasa al documento.
        w.sidebar._flush()
        w.move_pages([3, 0, 1, 2], [0])
        self.assertEqual(textos(), ["Pagina 4", "Pagina 1", "Pagina 2", "Pagina 3"])
        w.undo()

        # (r31) Cuadrícula: al ensanchar el panel caben varias columnas, en
        # orden de lectura, y soltar calcula el hueco por filas y columnas.
        w.sidebar._flush()
        self.app.processEvents()
        lst = th.list
        w._splitter.setSizes([44 + 560, 1000])
        for _ in range(10):
            self.app.processEvents()
        rects = [lst.visualItemRect(lst.item(i)) for i in range(4)]
        self.assertEqual(rects[0].top(), rects[1].top())             # misma fila
        self.assertLess(rects[0].left(), rects[1].left())            # de izquierda a derecha
        self.assertEqual(lst.drop_row(rects[2].center() + QPoint(5, 0)), 3)
        self.assertEqual(lst.drop_row(rects[0].topLeft() + QPoint(1, 1)), 0)
        self.assertEqual(lst.drop_row(QPoint(rects[-1].right() + 5, rects[-1].bottom() + 50)), 4)
        selecciona([0])
        th.move_selection_to(3)                                       # la 1.ª, detrás de la 3.ª
        self.assertEqual(textos(), ["Pagina 2", "Pagina 3", "Pagina 1", "Pagina 4"])
        w.sidebar._flush()
        self.app.processEvents()
        self.assertEqual(th._selected(), [2])
        selecciona([2, 3])
        th.move_selection_to(0)
        self.assertEqual(textos(), ["Pagina 1", "Pagina 4", "Pagina 2", "Pagina 3"])
        w.undo()
        w.undo()
        self.assertEqual(textos(), ["Pagina 1", "Pagina 2", "Pagina 3", "Pagina 4"])
        w.move_pages([3, 0, 1, 2], [0])

        # Supr sobre las miniaturas elimina la selección (con confirmación).
        selecciona([0, 1])
        th.eventFilter(th.list, QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Delete,
                                          Qt.KeyboardModifier.NoModifier))
        self.assertEqual(textos(), ["Pagina 2", "Pagina 3"])

        # Insertar otro PDF y extraer, sin diálogos de archivo reales.
        otro = os.path.join(self.tmp, "otro.pdf")
        d2 = fitz.open()
        d2.new_page().insert_text((72, 100), "Otro", fontsize=14)
        d2.save(otro)
        d2.close()
        selecciona([0])
        with mock.patch("window_menus.QFileDialog.getOpenFileName", return_value=(otro, "")):
            w._pages_op("pdf")
        self.assertEqual(textos(), ["Pagina 2", "Otro", "Pagina 3"])
        salida = os.path.join(self.tmp, "extracto.pdf")
        selecciona([1, 2])
        with mock.patch("window_document.QFileDialog.getSaveFileName", return_value=(salida, "")):
            w._pages_op("extract")
        with fitz.open(salida) as ex:
            self.assertEqual([pg.get_text().strip() for pg in ex], ["Otro", "Pagina 3"])

        # Salir con el mismo botón: el panel lateral vuelve a cerrarse.
        w._btn_pages.click()
        self.app.processEvents()
        self.assertFalse(w._pages_mode)
        self.assertFalse(th.organizing)
        self.assertTrue(w._pages_panel.isHidden())
        self.assertTrue(w.sidebar.stack.isHidden())
        # Elegir otra herramienta también sale del modo.
        w._btn_pages.click()
        w._toggle_tool("TEXT")
        self.app.processEvents()
        self.assertFalse(w._pages_mode)
        self.assertTrue(w._pages_panel.isHidden())
        w._toggle_tool("TEXT")

    def test_arrastrar_una_miniatura_la_traslada_de_verdad(self):
        """(r51, aviso de Ricardo: «al soltar no hace nada») El destino del
        arrastre nativo de Qt salía de `dropEvent`, que nunca llegaba a
        disparase con el ratón de verdad (en Windows, `QDrag.exec()` negocia
        por OLE, fuera de la cola de eventos de Qt); las pruebas anteriores no
        lo detectaban porque llamaban a `move_selection_to` directamente, sin
        pasar por ningún gesto de ratón. (r52, petición de Ricardo: híbrido)
        Ahora sí hay un `QDrag.exec()` real —para el fantasma y el cursor de
        OLE—, pero el destino se calcula con `QCursor.pos()` al volver de
        `exec()`, no con `dropEvent`. Bajo `offscreen`, `QTest.mouseMove` NO
        mueve el cursor global que lee `QCursor.pos()` (comprobado a mano: se
        queda en el punto de la pulsación), así que la prueba fija ese cursor
        con `QCursor.setPos()` antes del gesto — exactamente lo que haría el
        sistema operativo de verdad al mover el ratón."""
        from PyQt6.QtCore import QPoint
        from PyQt6.QtGui import QCursor
        from PyQt6.QtTest import QTest
        w = self.w
        path = os.path.join(self.tmp, "arrastre.pdf")
        doc = fitz.open()
        for i in range(4):
            doc.new_page().insert_text((72, 100), f"Pagina {i + 1}", fontsize=14)
        doc.save(path)
        doc.close()
        self.assertTrue(w.open_path(path))

        def textos():
            return [w.doc[i].get_text().strip() for i in range(len(w.doc))]

        w._btn_pages.click()
        self.app.processEvents()
        th = w.sidebar.thumbs
        w.sidebar._flush()
        self.app.processEvents()
        self.assertTrue(th.organizing)
        lst = th.list
        vp = lst.viewport()
        # Panel ancho, como en test_operaciones_de_pagina_en_el_panel_lateral,
        # para que la cuadrícula quepa sin necesitar scroll.
        w._splitter.setSizes([44 + 560, 1000])
        for _ in range(10):
            self.app.processEvents()
        r0 = lst.visualItemRect(lst.item(0))
        r3 = lst.visualItemRect(lst.item(3))
        self.assertTrue(vp.rect().contains(r3.center()), "la miniatura 4 debe verse sin scroll")

        # Un clic sin apenas moverse no debe arrancar el arrastre ni reordenar.
        QTest.mousePress(vp, Qt.MouseButton.LeftButton, pos=r0.center())
        QTest.mouseMove(vp, r0.center() + QPoint(1, 1))
        QTest.mouseRelease(vp, Qt.MouseButton.LeftButton, pos=r0.center() + QPoint(1, 1))
        self.app.processEvents()
        self.assertEqual(textos(), ["Pagina 1", "Pagina 2", "Pagina 3", "Pagina 4"])
        self.assertEqual(lst.cursor().shape(), Qt.CursorShape.ArrowCursor)

        # Mantener pulsado sobre la página 1 y moverla detrás de la última:
        # el gesto de ratón real debe trasladarla a la nueva posición.
        destino = QPoint(r3.right() - 2, r3.bottom() - 2)
        QTest.mousePress(vp, Qt.MouseButton.LeftButton, pos=r0.center())
        # QTest.mousePress ya deja QCursor.pos() en la pulsación; hay que fijar
        # el destino DESPUÉS (QTest.mouseMove, bajo offscreen, no mueve el
        # cursor global — comprobado a mano).
        QCursor.setPos(vp.mapToGlobal(destino))   # ahí «está» el ratón al mover
        QTest.mouseMove(vp, destino)              # dispara mouseMoveEvent → _run_drag
        self.app.processEvents()
        QTest.mouseRelease(vp, Qt.MouseButton.LeftButton, pos=destino)
        self.app.processEvents()
        w.sidebar._flush()
        self.app.processEvents()
        self.assertEqual(textos(), ["Pagina 2", "Pagina 3", "Pagina 4", "Pagina 1"])
        self.assertEqual(lst.cursor().shape(), Qt.CursorShape.ArrowCursor)  # cursor repuesto
        w.undo()

        # Soltar fuera de la cuadrícula no debe reordenar nada.
        QTest.mousePress(vp, Qt.MouseButton.LeftButton, pos=r0.center())
        QCursor.setPos(vp.mapToGlobal(QPoint(-50, -50)))
        QTest.mouseMove(vp, QPoint(-50, -50))
        self.app.processEvents()
        QTest.mouseRelease(vp, Qt.MouseButton.LeftButton, pos=QPoint(-50, -50))
        self.app.processEvents()
        self.assertEqual(textos(), ["Pagina 1", "Pagina 2", "Pagina 3", "Pagina 4"])

        # Fuera de «Operaciones de página» el mismo gesto no reordena: navega.
        w._btn_pages.click()
        self.app.processEvents()
        self.assertFalse(th.organizing)
        r0 = lst.visualItemRect(lst.item(0))
        r3 = lst.visualItemRect(lst.item(3))
        QCursor.setPos(vp.mapToGlobal(QPoint(r3.right() - 2, r3.bottom() - 2)))
        QTest.mousePress(vp, Qt.MouseButton.LeftButton, pos=r0.center())
        QTest.mouseMove(vp, QPoint(r3.right() - 2, r3.bottom() - 2))
        QTest.mouseRelease(vp, Qt.MouseButton.LeftButton,
                           pos=QPoint(r3.right() - 2, r3.bottom() - 2))
        self.app.processEvents()
        self.assertEqual(textos(), ["Pagina 1", "Pagina 2", "Pagina 3", "Pagina 4"])

    def test_campo_de_pagina_maximo_4_digitos_alineado_a_la_derecha(self):
        """(r53, petición de Ricardo) El campo del número de página actual
        admite como máximo 4 dígitos y el texto va alineado a la derecha."""
        w = self.w
        self.assertEqual(w._page_edit.maxLength(), 4)
        self.assertTrue(w._page_edit.alignment() & Qt.AlignmentFlag.AlignRight)
        self.assertTrue(w.open_path(self._crear_pdf(1)))
        w._page_edit.setText("123456")     # más de 4 dígitos escritos a mano
        self.assertEqual(w._page_edit.text(), "1234")

    def test_editar_contenido_vive_en_herramientas_sin_menu_propio(self):
        """(r54, petición de Ricardo) «Editar contenido» ya no tiene su propio
        menú en la barra: la acción pasa a Herramientas."""
        w = self.w
        titulos = [a.text().replace("&", "") for a in w.menuBar().actions()]
        self.assertNotIn("Editar contenido", titulos)
        self.assertEqual(titulos,
                         ["Archivo", "Edición", "Ver", "Comentar", "Organizar",
                          "Herramientas", "Proteger", "Firmar", "Ayuda"])
        herramientas = next(a for a in w.menuBar().actions()
                            if a.text().replace("&", "") == "Herramientas").menu()
        acciones = [a.text() for a in herramientas.actions() if not a.isSeparator()]
        self.assertEqual(acciones[0], "Editar texto e imágenes del PDF")

    def _crear_imagen(self, nombre="foto.png", color=120):
        pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 30, 20), 0)
        pix.clear_with(color)
        path = os.path.join(self.tmp, nombre)
        pix.save(path)
        return path

    def _crear_pdf_con_nombre(self, nombre: str, paginas: int) -> str:
        # _crear_pdf() siempre guarda en «entrada.pdf»: para combinar dos
        # archivos hacen falta rutas distintas.
        doc = fitz.open()
        for i in range(paginas):
            doc.new_page().insert_text((72, 100), f"Hola mundo pagina {i + 1}", fontsize=14)
        path = os.path.join(self.tmp, nombre)
        doc.save(path)
        doc.close()
        return path

    def test_combinar_pdf_desde_menu_contextual(self):
        """(r55, petición de Ricardo) Menú contextual del Explorador: combinar
        varios PDF en uno nuevo sin guardar, en una pestaña nueva."""
        w = self.w
        a = self._crear_pdf_con_nombre("a.pdf", 2)
        b = self._crear_pdf_con_nombre("b.pdf", 3)
        self.assertIsNone(w.doc)                  # nada abierto todavía
        w.combine_pdfs_from_paths([a, b])
        self.assertEqual(len(w._sessions), 1)
        self.assertEqual(len(w.doc), 5)
        self.assertEqual(w.pdf_path, "")           # sin guardar
        self.assertTrue(w._modified)

    def test_combinar_pdf_con_un_solo_archivo_avisa_y_no_hace_nada(self):
        w = self.w
        a = self._crear_pdf(1)
        w.combine_pdfs_from_paths([a])
        self.assertIsNone(w.doc)

    def test_convertir_imagenes_a_un_solo_pdf_desde_menu_contextual(self):
        """(r55) Ya existía create_from_images(); aquí se prueba invocada tal
        como lo haría el menú contextual (con rutas, sin diálogo)."""
        w = self.w
        imgs = [self._crear_imagen("a.png", 80), self._crear_imagen("b.png", 200)]
        w.create_from_images(imgs)
        self.assertEqual(len(w._sessions), 1)
        self.assertEqual(len(w.doc), 2)
        self.assertEqual(w.pdf_path, "")

    def test_convertir_imagenes_a_varios_pdf_desde_menu_contextual(self):
        """(r55, petición de Ricardo) Cada imagen seleccionada acaba en su
        propio PDF de una página, cada uno en su propia pestaña sin guardar."""
        w = self.w
        imgs = [self._crear_imagen("a.png", 80), self._crear_imagen("b.png", 200),
               self._crear_imagen("c.png", 30)]
        w.create_separate_pdfs_from_images(imgs)
        self.assertEqual(len(w._sessions), 3)
        self.assertEqual(len(w.doc), 1)            # la pestaña activa es la última creada
        w.switch_document(0)
        self.assertEqual(len(w.doc), 1)
        self.assertEqual(w.pdf_path, "")

    def test_procesar_argumentos_combina_pdf(self):
        """(r55) main.procesar_argumentos(): el indicador del menú contextual
        para combinar PDF llega hasta MainWindow tal cual."""
        import main
        w = self.w
        a = self._crear_pdf_con_nombre("a.pdf", 1)
        b = self._crear_pdf_con_nombre("b.pdf", 1)
        main.procesar_argumentos(w, [main.ARG_COMBINAR_PDF, a, b])
        self.assertEqual(len(w.doc), 2)

    def test_procesar_argumentos_imagenes_un_pdf(self):
        import main
        w = self.w
        imgs = [self._crear_imagen("a.png"), self._crear_imagen("b.png", 5)]
        main.procesar_argumentos(w, [main.ARG_IMAGENES_UN_PDF] + imgs)
        self.assertEqual(len(w._sessions), 1)
        self.assertEqual(len(w.doc), 2)

    def test_procesar_argumentos_imagenes_varios_pdf(self):
        import main
        w = self.w
        imgs = [self._crear_imagen("a.png"), self._crear_imagen("b.png", 5)]
        main.procesar_argumentos(w, [main.ARG_IMAGENES_VARIOS_PDF] + imgs)
        self.assertEqual(len(w._sessions), 2)

    def test_procesar_argumentos_abre_un_pdf_como_siempre(self):
        """(r55) Sin indicador del menú contextual: sigue abriendo el primer
        .pdf de la lista, como el «Abrir con…» normal de toda la vida."""
        import main
        w = self.w
        a = self._crear_pdf(1)
        main.procesar_argumentos(w, [a])
        self.assertEqual(w.pdf_path, a)

    def test_icono_de_la_aplicacion_con_todos_los_tamanos(self):
        """(r57) vendor/icono/aventyapdf.ico existe, Qt lo lee y trae los
        tamaños oficiales de Windows (create_app_icon.TAMANOS)."""
        from PyQt6.QtGui import QIcon
        import create_app_icon
        import icons
        self.assertTrue(os.path.isfile(icons.APP_ICON))
        icono = QIcon(icons.APP_ICON)
        self.assertFalse(icono.isNull())
        tamanos = sorted(s.width() for s in icono.availableSizes())
        self.assertEqual(tamanos, sorted(create_app_icon.TAMANOS))

    def test_imagenes_del_instalador_generadas_y_usadas(self):
        """(r64) Las imágenes del asistente de Inno Setup salen del icono
        (create_app_icon.py), existen con su tamaño y el .iss las usa todas."""
        from PyQt6.QtGui import QImage
        import create_app_icon as c
        with open(os.path.join(c.RAIZ, "empaquetado", "AventyaPDF.iss"), encoding="utf-8") as f:
            iss = f.read()
        for nombre, tamanos in (("pequena", c.ASISTENTE_PEQUENA), ("grande", c.ASISTENTE_GRANDE)):
            for escala, (ancho, alto) in tamanos.items():
                archivo = f"asistente_{nombre}_{escala}.bmp"
                img = QImage(os.path.join(c.IMAGENES_INSTALADOR, archivo))
                self.assertEqual((img.width(), img.height()), (ancho, alto), archivo)
                self.assertIn("imagenes\\" + archivo, iss)

    def test_panel_de_firmas_verificado_solo_y_papelera_en_la_ultima(self):
        """(r61) Sin botón de verificar: al abrir el panel las firmas salen ya
        verificadas. La más reciente lleva una papelera que la quita y deja su
        recuadro vacío; al guardar, la firma anterior sigue válida."""
        from PyQt6.QtWidgets import QLabel
        import icons
        from create_test_cert import build_test_pfx
        from signature_validation import validate_signatures
        from signer_backend import PAdESSigner
        pfx = os.path.join(self.tmp, "prueba.pfx")
        with open(pfx, "wb") as fh:
            fh.write(build_test_pfx(b"1234"))
        d = fitz.open()
        for i in range(2):
            d.new_page().insert_text((72, 100), f"Pagina {i + 1}")
        uno = PAdESSigner.sign_pdf_bytes(d.tobytes(), pfx, "1234", 0, (72, 600, 272, 680))
        dos = PAdESSigner.sign_pdf_bytes(uno, pfx, "1234", 1, (72, 600, 272, 680))
        ruta = os.path.join(self.tmp, "firmado.pdf")
        with open(ruta, "wb") as fh:
            fh.write(dos)
        w = self.w
        self.assertTrue(w.open_path(ruta))
        panel = w.sidebar.signatures
        self.assertFalse(hasattr(panel, "_validate_btn"), "no hay verificación manual")
        w.sidebar.show_panel("signatures")
        self.assertTrue(panel.wait())
        self.assertEqual([r.field_name for r in panel.reports], ["Firma1", "Firma2"])
        self.assertTrue(all(r.intact and r.valid for r in panel.reports))
        self.assertEqual(list(panel.trash_buttons), ["Firma2"], "papelera solo en la última")
        papelera = panel.trash_buttons["Firma2"]
        self.assertTrue(papelera.isEnabled())
        self.assertEqual(papelera.text(), icons.glyph("delete"))

        papelera.click()                                # confirmación simulada: Sí
        self.app.processEvents()
        self.assertTrue(w._modified and w._pending_bytes is not None)
        w.sidebar.show_panel("signatures")
        self.assertTrue(panel.wait())
        self.assertEqual([r.field_name for r in panel.reports], ["Firma1"])
        self.assertEqual(list(panel.trash_buttons), ["Firma1"], "ahora la última es Firma1")
        textos = [panel.list.itemWidget(panel.list.item(i)).findChild(QLabel).text()
                  for i in range(panel.list.count()) if panel.list.itemWidget(panel.list.item(i))]
        self.assertTrue(any("Recuadro de firma vacío" in t and "Firma2" in t for t in textos))

        self.assertTrue(w._write_to(ruta))              # guarda los bytes exactos
        with open(ruta, "rb") as fh:
            guardado = fh.read()
        self.assertTrue(guardado.startswith(uno))
        reports = validate_signatures(guardado)
        self.assertEqual([r.field_name for r in reports], ["Firma1"])
        self.assertTrue(reports[0].intact and reports[0].valid)

        # Con otros cambios sin guardar, la papelera no se puede usar.
        w.add_note(fitz.Point(50, 50), "nota")
        w.sidebar._flush()                              # sin esperar al temporizador
        self.assertTrue(panel.wait())
        self.assertFalse(panel.trash_buttons["Firma1"].isEnabled())
        w._modified = False

    def _arrastrar(self, puntos_pdf, segundos=0.1):
        """Gesto de ratón real en el visor (pulsar, mover, soltar) por los
        puntos dados; `segundos` = duración que verá el visor."""
        from PyQt6.QtCore import QEvent, QPointF, Qt
        from PyQt6.QtGui import QMouseEvent
        v = self.w.viewer
        izq, nada = Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton

        def ev(tipo, pt, boton, botones):
            pos = QPointF(pt.x * v.scale_factor, pt.y * v.scale_factor)
            return QMouseEvent(tipo, pos, v.mapToGlobal(pos), boton, botones,
                               Qt.KeyboardModifier.NoModifier)
        with mock.patch("viewer.time.monotonic", side_effect=[100.0, 100.0 + segundos]):
            v.mousePressEvent(ev(QEvent.Type.MouseButtonPress, puntos_pdf[0], izq, izq))
            for pt in puntos_pdf[1:]:
                v.mouseMoveEvent(ev(QEvent.Type.MouseMove, pt, nada, izq))
            v.mouseReleaseEvent(ev(QEvent.Type.MouseButtonRelease, puntos_pdf[-1], izq, nada))
        self.app.processEvents()

    def test_marcar_a_mano_alzada_fuera_del_texto(self):
        """(r59) «Resaltar, subrayar o tachar»: sobre el texto marca el texto;
        fuera de él (una imagen) marca a mano alzada, y un trazo rápido sale
        recto. El antiguo «Marcador a mano alzada» ya no existe y su icono
        pasa a esta herramienta."""
        import icons
        import viewer
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 100), "Texto que se puede marcar", fontsize=14)
        page.draw_rect(fitz.Rect(100, 200, 400, 400), color=(0, 0, 1), fill=(0.6, 0.8, 1))
        ruta = os.path.join(self.tmp, "imagen.pdf")
        doc.save(ruta)
        doc.close()
        w = self.w
        self.assertTrue(w.open_path(ruta))
        self.assertNotIn("HIGHLIGHT", w._tool_btns)
        self.assertFalse(hasattr(w, "_mrk_panel"))
        self.assertEqual(w._tool_btns["MARKUP"].text(), icons.glyph("highlight"))
        w._select_tool("MARKUP")

        # 1) Sobre el texto: anotación Highlight de texto, como siempre.
        self._arrastrar([fitz.Point(74, 95), fitz.Point(150, 95), fitz.Point(240, 95)])
        tipos = [a.type[1] for a in w.doc[0].annots()]
        self.assertEqual(tipos, ["Highlight"])

        # 2) Sobre el dibujo, rápido y tembloroso: una recta horizontal (Ink).
        pts = [fitz.Point(120 + 8 * i, 300 + (3 if i % 2 else -3)) for i in range(30)]
        self._arrastrar(pts, segundos=0.12)
        ink = [a for a in w.doc[0].annots() if a.type[1] == "Ink"]
        self.assertEqual(len(ink), 1)
        trazo = ink[0].vertices
        self.assertEqual(len(trazo[0]) if isinstance(trazo[0], list) else len(trazo), 2)
        self.assertEqual(ink[0].info["subject"], "MANO|highlight")
        self.assertEqual(ink[0].blendmode, "Multiply")      # tiñe, no tapa
        self.assertAlmostEqual(ink[0].border["width"], viewer.FREEHAND_WIDTHS["highlight"])
        self.assertEqual(w.viewer.mode, "MARKUP")           # sigue activa

        # 3) Tachar a mano alzada: línea fina, sin fundido.
        w._cb_markup.setCurrentIndex(w._cb_markup.findData("strike"))
        self._arrastrar([fitz.Point(150, 250), fitz.Point(250, 350)], segundos=0.1)
        ink = [a for a in w.doc[0].annots() if a.type[1] == "Ink"]
        self.assertEqual(len(ink), 2)
        self.assertEqual(ink[1].info["subject"], "MANO|strike")
        self.assertAlmostEqual(ink[1].border["width"], viewer.FREEHAND_WIDTHS["strike"])

        # 4) Deshacer quita la última marca.
        w.undo()
        self.assertEqual(len([a for a in w.doc[0].annots() if a.type[1] == "Ink"]), 1)

        # 5) Al seleccionar la marca a mano alzada, el panel muestra su tipo y grosor.
        w._select_tool("NONE")
        a = [x for x in w.doc[0].annots() if x.type[1] == "Ink"][0]
        w._sync_panel_to_annot(a, "MARKUP")
        self.assertEqual(w._cb_markup.currentData(), "highlight")
        from PyQt6.QtWidgets import QSpinBox
        self.assertEqual(w._markup_width_spin.findChild(QSpinBox).value(),
                         int(viewer.FREEHAND_WIDTHS["highlight"]))
        w._modified = False

    def test_negrita_y_cursiva_con_iconos_fluent(self):
        """(r58) Los botones de negrita y cursiva (Texto y Editar contenido)
        llevan el glifo de Fluent UI System Icons, no una letra en Segoe UI."""
        import icons
        import main
        w = self.w
        app = QApplication.instance()
        antes = app.styleSheet()
        app.setStyleSheet(main.STYLESHEET)     # la batería no carga la hoja global
        try:
            for btn, clave in ((w._txt_bold_btn, "bold"), (w._txt_italic_btn, "italic"),
                               (w._edit_bold_btn, "bold"), (w._edit_italic_btn, "italic")):
                btn.ensurePolished()
                self.assertEqual(btn.text(), icons.glyph(clave))
                self.assertNotIn("Segoe", btn.styleSheet())
                self.assertEqual(btn.font().family(), icons.ICON_FAMILY)
        finally:
            app.setStyleSheet(antes)

    def test_icono_ajustar_ancho_alto_muestra_la_accion_libre(self):
        """(r48, petición de Ricardo) El botón de ajustar ancho/alto no lleva
        un icono fijo: muestra la acción que el clic va a ejecutar (la que
        está libre), no la que ya está activa. (r51) Tampoco queda marcado
        como seleccionado tras pulsarlo: no es «checkable», el icono ya dice
        qué va a hacer el próximo clic."""
        import icons
        w = self.w
        self.assertTrue(w.open_path(self._crear_pdf(1)))
        btn = w._zoom_btns["type"]
        self.assertFalse(btn.isCheckable())

        # Zoom 100 %: ninguna de las dos activa, el próximo clic ajusta al
        # ancho → icono de ancho.
        w.zoom_actual()
        self.assertEqual(btn.text(), icons.glyph("type"))
        self.assertFalse(btn.isChecked())

        # Ajustado al ancho: el próximo clic ajustaría al alto → icono de alto.
        w.zoom_fit_width()
        self.assertEqual(w.zoom_mode, "width")
        self.assertEqual(btn.text(), icons.glyph("type_height"))
        self.assertFalse(btn.isChecked())

        # Ajustado al alto: el próximo clic ajustaría al ancho → icono de ancho.
        w.zoom_fit_page()
        self.assertEqual(w.zoom_mode, "height")
        self.assertEqual(btn.text(), icons.glyph("type"))
        self.assertFalse(btn.isChecked())

        # El propio botón alterna igual (clic real, no solo la llamada directa)
        # y sigue sin quedar marcado como seleccionado.
        btn.click()
        self.app.processEvents()
        self.assertEqual(w.zoom_mode, "width")
        self.assertEqual(btn.text(), icons.glyph("type_height"))
        self.assertFalse(btn.isChecked())
        btn.click()
        self.app.processEvents()
        self.assertEqual(w.zoom_mode, "height")
        self.assertEqual(btn.text(), icons.glyph("type"))
        self.assertFalse(btn.isChecked())

        # Volver a un zoom numérico también deja el icono en «ancho».
        w._set_custom_zoom(150)
        self.assertEqual(btn.text(), icons.glyph("type"))
        self.assertFalse(btn.isChecked())

    def test_recorrido_completo(self):
        w = self.w
        path = self._crear_pdf(3)
        self.assertTrue(w.open_path(path))
        self.assertEqual(len(w.doc), 3)
        self.assertFalse(w._modified)

        # Zoom y navegación
        w.zoom_fit_width()
        w.zoom_fit_page()
        w.zoom_step(1)
        w.zoom_actual()
        self.assertAlmostEqual(w.viewer.scale_factor, 1.0)
        w.last_page()
        self.assertEqual(w.current_page, 2)
        w.prev_page()
        w.next_page()

        # Duplicar la última página (antes lanzaba ValueError) y deshacer/rehacer
        w.copy_page()
        self.assertEqual(len(w.doc), 4)
        self.assertEqual(w.current_page, 3)
        self.assertTrue(w._modified)
        w.undo()
        self.assertEqual(len(w.doc), 3)
        w.redo()
        self.assertEqual(len(w.doc), 4)

        # Girar, insertar en blanco al final y eliminar
        w.rotate_current(90)
        self.assertEqual(w.doc[w.current_page].rotation, 90)
        w.insert_blank_after(len(w.doc) - 1)
        self.assertEqual(len(w.doc), 5)
        w.delete_pages([4])
        self.assertEqual(len(w.doc), 4)

        # Comentarios sobre la primera página
        w.go_to_page(0)
        hits = doc_tools.search_document(w.doc, "Hola")
        self.assertTrue(hits)
        w.add_text_markup([hits[0][1]], "highlight")
        w.add_note(fitz.Point(300, 300), "Nota de prueba")
        tipos = sorted(c["type"] for c in doc_tools.annotation_summary(w.doc))
        self.assertEqual(tipos, ["Highlight", "Text"])
        w.select_annotation(0, 0)
        self.assertIsNotNone(w.viewer._sel)
        w._on_escape()

        # Selección de texto con la API del visor
        words = w.viewer._page_words()
        # PyMuPDF 1.28 no tiene Rect.center.
        centro = lambda p: fitz.Point((p[0] + p[2]) / 2, (p[1] + p[3]) / 2)  # noqa: E731
        w.viewer._tsel_start = centro(words[0])
        w.viewer._update_text_selection(centro(words[1]))
        self.assertEqual(w.viewer._tsel_text, "Hola mundo")
        w.copy_selected_text()
        self.assertEqual(QApplication.clipboard().text(), "Hola mundo")

        # Búsqueda
        w._find_edit.setText("mundo")
        w.find_next()
        self.assertGreaterEqual(len(w._find_hits), 3)
        w.find_next()
        w.hide_find()

        # Panel lateral
        for key in ("thumbs", "bookmarks", "comments", "signatures"):
            w.sidebar.show_panel(key)
            self.app.processEvents()
        w.sidebar._flush()
        self.assertEqual(w.sidebar.comments.list.count(), 2)
        w.sidebar.toggle()

        # Herramientas: activar y desactivar cada modo
        for mode in ("TEXT", "NOTE", "MARKUP", "RECT", "EMOJI",
                     "ERASE", "SIGN"):
            w._select_tool(mode)
            self.assertEqual(w.viewer.mode, mode)
        w._on_escape()
        self.assertEqual(w.viewer.mode, "NONE")

        # Guardar en otra ruta y comprobar lo escrito
        out = os.path.join(self.tmp, "salida.pdf")
        self.assertTrue(w._write_to(out))
        self.assertFalse(w._modified)
        with fitz.open(out) as saved:
            self.assertEqual(len(saved), 4)

        w._modified = False
        w.close_document()
        self.assertIsNone(w.doc)

    def test_emojis_con_color_transparencia_y_selector(self):
        """(r40) Los emojis se escriben con la fuente Noto Emoji en el color y la
        transparencia elegidos; el selector los busca en español y los dibuja con
        esa misma fuente. Moverlos y redimensionarlos no los sustituye por un
        sello estándar."""
        import emoji_font
        from viewer import AnnotSelection, _keep_aspect

        w = self.w
        self.assertTrue(w.open_path(self._crear_pdf(1)))
        todos = emoji_font.catalog()
        self.assertGreater(len(todos), 1000, "deben estar todos los emojis, no una paleta")
        picker = w._emoji_picker
        self.assertEqual(picker.list.count(), 0, "no se rellena hasta mostrarse")
        picker._refill()                      # lo que hace showEvent la primera vez
        self.assertEqual(picker.list.count(), len(todos))
        # Buscar sin tildes, en español, y filtrar por grupo.
        picker.search.setText("corazon")
        visibles = [picker.list.item(i).data(Qt.ItemDataRole.UserRole)
                    for i in range(picker.list.count())]
        self.assertTrue(visibles and all("coraz" in " ".join(emoji_font.find(v)["es"])
                                         for v in visibles))
        picker.search.setText("pineapple")
        self.assertEqual([picker.list.item(i).data(Qt.ItemDataRole.UserRole)
                          for i in range(picker.list.count())], ["🍍"])
        picker.group.setCurrentIndex(picker.group.findData("Flags"))
        picker.search.clear()
        self.assertTrue(0 < picker.list.count() < len(todos))
        picker.group.setCurrentIndex(0)
        # Elegir en la cuadrícula cambia el emoji de la herramienta.
        picker.search.setText("pineapple")
        picker._clicked(picker.list.item(0))
        self.assertEqual(w.viewer.selected_emoji, "🍍")
        picker.search.clear()

        # Color y transparencia del panel.
        w._toggle_tool("EMOJI")
        with mock.patch.object(color_picker, "choose", return_value=((0.0, 0.4, 0.8), 0.4)):
            w._on_emoji_color()
        self.assertEqual([round(c, 2) for c in w.viewer.emoji_color], [0.0, 0.4, 0.8])
        self.assertAlmostEqual(w.viewer.emoji_opacity, 0.4, places=2)

        fitz.TOOLS.reset_mupdf_warnings()
        muestra = ["📌", "⚠️", "💡", "✅", "❤️", "🍍"]
        for i, e in enumerate(muestra):
            w._insert_emoji(fitz.Point(40 + 70 * i, 300), e, 24)
        w._insert_emoji(fitz.Point(40, 420), "📌", 48, (1.0, 0.0, 0.0), 1.0)
        w.mark_modified()
        w.render_page()

        page = w.doc[0]
        annots = list(page.annots())
        self.assertEqual(len(annots), len(muestra) + 1)
        for a in annots:
            with self.subTest(emoji=a.info["content"]):
                self.assertTrue(emoji_font.is_emoji(a.info["subject"]))
                fs = float(a.info["title"])
                ancho, alto = emoji_font.box_size(a.info["content"], fs)
                self.assertAlmostEqual(a.rect.width, ancho, delta=0.01)
                self.assertAlmostEqual(a.rect.height, alto, delta=0.01)
                pix = page.get_pixmap(clip=a.rect, matrix=fitz.Matrix(4, 4))
                self.assertTrue(any(b < 220 for b in pix.samples), "el emoji debe verse")
        color, opacidad = emoji_font.parse_style(annots[0].info["subject"])
        self.assertEqual([round(c, 2) for c in color], [0.0, 0.4, 0.8])
        self.assertAlmostEqual(opacidad, 0.4, places=2)
        self.assertEqual([round(c, 2) for c in
                          emoji_font.parse_style(annots[-1].info["subject"])[0]], [1.0, 0.0, 0.0])
        # Vectorial: ni imágenes ni fuentes de color.
        objetos = _objetos_pdf(w.doc)
        self.assertFalse(any("/Subtype/Image" in o for o in objetos), "no debe haber imágenes")
        self.assertTrue(any("Noto" in o and "Emoji" in o for o in objetos),
                        "la fuente Noto Emoji va incrustada")

        # Mover (como el visor) y guardar/reabrir: Rect y apariencia intactos.
        a = annots[0]
        nr = fitz.Rect(a.rect.x0 + 10, a.rect.y0 + 20, a.rect.x1 + 10, a.rect.y1 + 20)
        emoji_font.write_rect(page, a, nr)
        w.render_page()
        with fitz.open("pdf", w.doc.tobytes(garbage=3, deflate=True)) as d2:
            p2 = d2[0]
            p2.get_pixmap()
            a2 = next(p2.annots())
            self.assertEqual([round(v, 2) for v in a2.rect], [round(v, 2) for v in nr])
            ap = d2.xref_stream(int(d2.xref_get_key(a2.xref, "AP/N")[1].split()[0]))
            self.assertTrue(ap.startswith(emoji_font.AP_MARKER), "apariencia sustituida")
        self.assertNotIn("ICC", fitz.TOOLS.mupdf_warnings())

        # Redimensionar conserva la proporción desde cualquier esquina.
        o = fitz.Rect(100, 100, 124, 130)
        for esquina, arrastre in (("BR", fitz.Rect(100, 100, 190, 140)),
                                  ("TL", fitz.Rect(60, 90, 124, 130))):
            r = _keep_aspect(arrastre, o, esquina)
            self.assertAlmostEqual(r.width / r.height, o.width / o.height, places=6)

        # Cambiar el tamaño de un emoji seleccionado lo recrea en su sitio, y el
        # panel recupera su color y su transparencia (con la herramienta cerrada:
        # recrear solo actúa sobre la anotación seleccionada, modo NONE).
        w._toggle_tool("NONE")
        w.render_page()
        pagina0 = w.doc[0]
        a0 = next(pagina0.annots())
        r0 = fitz.Rect(a0.rect)
        w.viewer.selected_emoji = a0.info["content"]
        w.viewer._sel = AnnotSelection(0, r0, fitz.Rect(r0), "Stamp")
        w._sync_panel_to_annot(a0, "EMOJI")
        self.assertEqual([round(c, 2) for c in w.viewer.emoji_color], [0.0, 0.4, 0.8])
        self.assertAlmostEqual(w.viewer.emoji_opacity, 0.4, places=2)
        w._on_emoji_size(30)
        pagina0 = w.doc[0]                    # las Annot referencian débilmente su página
        anots = list(pagina0.annots())
        self.assertEqual(len(anots), len(muestra) + 1)
        self.assertEqual(anots[-1].info["title"], "30")
        self.assertAlmostEqual(anots[-1].rect.x0, r0.x0, delta=0.01)
        w._modified = False

    def test_fuente_e_indice_de_emojis(self):
        """(r40) Noto Emoji (vendor/fonts/noto-emoji) dibuja todos los emojis del
        índice; solo emojis de un carácter, y con nombre en español."""
        import emoji_font
        self.assertTrue(os.path.isfile(emoji_font.FONT_PATH))
        self.assertTrue(os.path.isfile(
            os.path.join(os.path.dirname(emoji_font.FONT_PATH), "OFL.txt")))
        todos = emoji_font.catalog()
        f = emoji_font.font()
        self.assertEqual(f.name.split()[:2], ["Noto", "Emoji"])
        for e in todos:
            self.assertEqual(len(e["key"]), 1, f"{e['emoji']} no es de un carácter")
            self.assertTrue(f.has_glyph(ord(e["key"])), f"la fuente no dibuja {e['emoji']}")
        con_es = sum(1 for e in todos if e["es"])
        self.assertGreater(con_es / len(todos), 0.9, "casi todos con nombre en español")
        self.assertIsNotNone(emoji_font.find("⚠"))            # sin selector de variación
        self.assertIsNone(emoji_font.find("🇪🇸"), "las banderas de países son secuencias")

    def test_todos_los_colores_usan_la_misma_tabla(self):
        """(r41, paleta de r42) Los selectores de color son la misma tabla de 17
        colores, con opacidad solo donde la herramienta la admite."""
        from PyQt6.QtWidgets import QDialog, QPushButton

        w = self.w
        self.assertTrue(w.open_path(self._crear_pdf(1)))
        # (r42) La paleta es la de Ricardo, con su mismo orden y sus nombres.
        self.assertEqual(color_picker.PALETTE,
                         ["#FFFFFF", "#AAAAAA", "#000000", "#AA0000", "#FF0000", "#FFAA00",
                          "#FFFF00", "#FFFFAA", "#AAFF00", "#00FF00", "#00FFAA", "#AAFFFF",
                          "#00AAFF", "#0000FF", "#AA00FF", "#FF00FF", "#FFAAFF"])
        self.assertLessEqual(color_picker.SWATCH, 24)
        self.assertTrue(all(h in color_picker._NOMBRES for h in color_picker.PALETTE))

        # El cuadro: un recuadro por color, del tamaño indicado, y opacidad
        # solo cuando se le pasa.
        dlg = color_picker.ColorDialog(w, (1, 0, 0), None, "Color")
        recuadros = [b for b in dlg.findChildren(QPushButton) if b.objectName() == "swatch"]
        self.assertEqual(len(recuadros), len(color_picker.PALETTE))
        self.assertEqual(recuadros[0].size().width(), color_picker.SWATCH)
        self.assertFalse(hasattr(dlg, "_slider"))
        self.assertEqual(dlg.values(), (color_picker.to_rgb("#FF0000"), None))
        con_op = color_picker.ColorDialog(w, (1, 1, 0), 0.45, "Color")
        self.assertEqual(con_op.values()[1], 0.45)
        con_op._pick("#0000FF")
        self.assertEqual(con_op.values(), (color_picker.to_rgb("#0000FF"), 0.45))
        # Sin opacidad, un clic elige y cierra; con opacidad hay que aceptar.
        dlg._pick("#00FF00")
        self.assertEqual(dlg.result(), int(QDialog.DialogCode.Accepted))
        self.assertNotEqual(con_op.result(), int(QDialog.DialogCode.Accepted))

        # Cada herramienta abre esa tabla; las que tienen transparencia la piden.
        casos = [
            (w._on_txt_color, None), (w._on_note_color, None), (w._on_rect_color, None),
            (w._on_markup_color, 1.0), (w._on_emoji_color, 1.0),
        ]
        for handler, opacidad in casos:
            llamadas = []

            def falso(_parent, color=(0, 0, 0), opacity=None, title="", _l=llamadas):
                _l.append(opacity)
                return (color_picker.to_rgb("#00AAFF"), opacity if opacity is None else 0.5)

            with mock.patch.object(color_picker, "choose", falso):
                handler()
            with self.subTest(herramienta=handler.__name__):
                self.assertEqual(len(llamadas), 1, "debe abrir la tabla común")
                if opacidad is None:
                    self.assertIsNone(llamadas[0], "esta herramienta no tiene transparencia")
                else:
                    self.assertIsNotNone(llamadas[0], "debe ofrecer transparencia")
        self.assertEqual([round(c, 3) for c in w.viewer.markup_color],
                         [round(c, 3) for c in color_picker.to_rgb("#00AAFF")])
        self.assertAlmostEqual(w.viewer.markup_opacity, 0.5, places=2)

        # El marcado de texto se escribe con esa transparencia.
        w.viewer.markup_opacity = 0.5
        w.add_text_markup([fitz.Rect(60, 60, 200, 80)], "highlight", (1, 1, 0), 0.5)
        a = [x for x in w.doc[0].annots() if x.type[1] == "Highlight"][0]
        self.assertAlmostEqual(a.opacity, 0.5, places=2)
        w._modified = False

    def test_comprimir_pdf_desde_la_interfaz(self):
        import pdf_compression
        w = self.w
        cb = w._compress_level_cb
        self.assertEqual([cb.itemData(i) for i in range(cb.count())],
                         [lvl.key for lvl in pdf_compression.LEVELS])
        self.assertEqual(cb.currentData(), pdf_compression.DEFAULT_LEVEL)

        # PDF con una foto grande (ruido: no se comprime sin reducir resolución).
        foto = fitz.Pixmap(fitz.csRGB, 1600, 1067, os.urandom(1600 * 1067 * 3), 0)
        doc = fitz.open()
        page = doc.new_page()
        page.insert_image(fitz.Rect(40, 40, 40 + 288, 40 + 192), stream=foto.tobytes("jpeg", jpg_quality=95))
        entrada = os.path.join(self.tmp, "fotos.pdf")
        doc.save(entrada)
        doc.close()
        self.assertTrue(w.open_path(entrada))

        salida = os.path.join(self.tmp, "fotos_comprimido.pdf")
        cb.setCurrentIndex(cb.findData("extrema"))
        with mock.patch("main_window.QFileDialog.getSaveFileName", return_value=(salida, "")):
            w.compress_pdf()
        self.assertTrue(os.path.isfile(salida))
        self.assertLess(os.path.getsize(salida), os.path.getsize(entrada) / 5)
        with fitz.open(salida) as d:
            self.assertGreaterEqual(pdf_compression.min_print_ppi(d), pdf_compression.MIN_PRINT_PPI)
        self.assertFalse(w._modified, "comprimir no modifica el documento abierto")

    def test_ocr_desactivado_sin_tesseract(self):
        w = self.w
        self.assertTrue(w.open_path(self._crear_pdf(1)))
        self.assertTrue(w._act_ocr.isEnabled())
        w.set_ocr_available(False, "sin internet")
        self.assertFalse(w._act_ocr.isEnabled())
        w._update_actions()                      # abrir o cambiar de documento no lo reactiva
        self.assertFalse(w._act_ocr.isEnabled())
        self.assertIn("Tesseract no instalado", w._act_ocr.text())
        w.set_ocr_available(True)
        self.assertTrue(w._act_ocr.isEnabled())

    def test_instalacion_forzada_de_tesseract_al_iniciar(self):
        import tesseract_setup as ts
        import tesseract_ui
        listo = ts.Status(r"C:\Tesseract-OCR\tesseract.exe", [])
        falta = ts.Status(None, list(ts.CORE_LANGS))
        with mock.patch.object(ts, "configure_environment"), \
                mock.patch.object(ts, "status", return_value=listo), \
                mock.patch.object(ts, "ensure") as ensure:
            self.assertEqual(tesseract_ui.ensure_at_startup(), (True, ""))
            ensure.assert_not_called()
        with mock.patch.object(ts, "configure_environment"), \
                mock.patch.object(ts, "status", return_value=falta), \
                mock.patch.object(ts, "ensure", return_value=listo) as ensure:
            self.assertEqual(tesseract_ui.ensure_at_startup(), (True, ""))
            ensure.assert_called_once()
        QMessageBox.warning.reset_mock()
        with mock.patch.object(ts, "configure_environment"), \
                mock.patch.object(ts, "status", return_value=falta), \
                mock.patch.object(ts, "ensure", side_effect=ts.TesseractSetupError("sin internet")):
            ok, motivo = tesseract_ui.ensure_at_startup()
        self.assertFalse(ok)
        self.assertIn("sin internet", motivo)
        QMessageBox.warning.assert_called_once()

    # ── Formularios, cursor de texto y OCR ─────────────────────────────── #

    def _abrir_formulario(self):
        from tests.test_nucleo import formulario_de_prueba
        ruta = os.path.join(self.tmp, "formulario.pdf")
        with open(ruta, "wb") as fh:
            fh.write(formulario_de_prueba())
        self.assertTrue(self.w.open_path(ruta))
        self.w.zoom_actual()
        self.app.processEvents()
        return self.w

    def _campo(self, nombre, i=0):
        return [f for f in self.w.viewer.forms.fields if f["name"] == nombre][i]

    def _mover(self, pdf_pt):
        from PyQt6.QtCore import QEvent, QPointF, Qt
        from PyQt6.QtGui import QMouseEvent
        v = self.w.viewer
        pos = QPointF(pdf_pt.x * v.scale_factor, pdf_pt.y * v.scale_factor)
        ev = QMouseEvent(QEvent.Type.MouseMove, pos, v.mapToGlobal(pos), Qt.MouseButton.NoButton,
                         Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
        v.mouseMoveEvent(ev)
        return v.cursor().shape()

    # ── Escritura sobre la propia página (inplace_editor) ──────────────── #

    def _sin_ventanas(self):
        """Comprueba que no se ha abierto ninguna ventana para escribir.

        No se parchea QDialog.exec: sustituir un método C++ de Qt tumbaba el
        proceso (0xC0000409). Se mira lo que de verdad importa: que no hay
        ningún widget modal y que el cuadro de escritura es hijo del visor."""
        import dialogs
        self.assertFalse(hasattr(dialogs, "TextInputDialog"),
                         "el diálogo de texto debería haber desaparecido")
        self.assertIsNone(self.app.activeModalWidget(),
                          "hay una ventana modal abierta para escribir")
        editor = self.w.viewer.text_editor
        if editor is not None:
            self.assertIs(editor.parent(), self.w.viewer,
                          "el cuadro debe estar SOBRE la página, no en una ventana")
            self.assertFalse(editor.isWindow(), "el cuadro no puede ser una ventana")

    def _esc_de_ventana(self):
        """Esc como lo pulsa el usuario: lo coge el QShortcut de la ventana."""
        self.w._esc_shortcut.activated.emit()
        self.app.processEvents()

    def test_la_herramienta_texto_escribe_sobre_la_pagina(self):
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        w = self.w
        self.assertTrue(w.open_path(self._crear_pdf(1)))
        w.zoom_actual()
        w._toggle_tool("TEXT")
        self._clic(fitz.Point(120, 300))
        v = w.viewer
        self.assertIsNotNone(v.text_editor, "debe abrirse el cuadro sobre la página")
        self._sin_ventanas()
        if True:
            # Está dentro del visor, encima del punto donde se hizo clic.
            caja = v.text_editor.geometry()
            self.assertEqual(v.text_editor.parent(), v)
            self.assertAlmostEqual(caja.left() / v.scale_factor, 120, delta=3)
            self.assertAlmostEqual(caja.top() / v.scale_factor, 300, delta=3)

            QTest.keyClicks(v.text_editor, "Escrito encima del PDF")
            QTest.keyClick(v.text_editor, Qt.Key.Key_Return)      # línea nueva
            QTest.keyClicks(v.text_editor, "en dos renglones")
            self.assertIsNotNone(v.text_editor, "Intro no confirma: abre línea")
            QTest.keyClick(v.text_editor, Qt.Key.Key_Return,
                           Qt.KeyboardModifier.ControlModifier)
            self.app.processEvents()
        self.assertIsNone(w.viewer.text_editor)
        textos = [a.info.get("content", "") for a in w.doc[0].annots()]
        self.assertTrue(any("Escrito encima del PDF" in t for t in textos), textos)
        self.assertTrue(any("en dos renglones" in t for t in textos), textos)
        self.assertTrue(w._modified)
        self.assertTrue(w._history.can_undo())
        self.assertEqual(w.viewer.mode, "NONE")       # la herramienta se suelta
        w._modified = False

    def test_el_cuadro_crece_al_escribir_y_el_texto_no_se_recorta(self):
        w = self.w
        self.assertTrue(w.open_path(self._crear_pdf(1)))
        w.zoom_actual()
        v = w.viewer
        v.begin_text(fitz.Rect(45, 140, 325, 165))
        alto_inicial = v.text_editor.height()
        v.text_editor.setPlainText(
            "Esto se escribe directamente sobre la pagina, sin abrir ninguna "
            "ventana, y tiene que verse entero mientras se escribe.")
        self.app.processEvents()
        # El cuadro crece: si no, se escribiria a ciegas. (En QPlainTextEdit el
        # alto de documentSize viene en LINEAS, no en pixeles.)
        self.assertGreater(v.text_editor.height(), alto_inicial)
        lineas = int(round(
            v.text_editor.document().documentLayout().documentSize().height()))
        self.assertGreaterEqual(lineas, 2)

        v.text_editor.commit()
        self.app.processEvents()
        page = w.doc[0]          # invariante 3: la pagina, viva en una variable
        cajas = [fitz.Rect(a.rect) for a in page.annots()]
        self.assertEqual(len(cajas), 1)
        fs = v.text_font_size
        self.assertGreaterEqual(cajas[0].height, fs * 1.45 * lineas,
                                "la caja se queda corta y el texto se recorta")
        w._modified = False

    def test_escribir_sobre_la_pagina_se_cancela_con_esc(self):
        from PyQt6.QtTest import QTest
        w = self.w
        self.assertTrue(w.open_path(self._crear_pdf(1)))
        w.zoom_actual()
        w._toggle_tool("TEXT")
        self._clic(fitz.Point(120, 300))
        QTest.keyClicks(w.viewer.text_editor, "esto no debe quedar")
        # Esc de verdad: los QShortcut de ventana se procesan ANTES que las
        # teclas del widget, así que tiene que cancelarlo _on_escape.
        self._esc_de_ventana()
        self.assertIsNone(w.viewer.text_editor)
        self.assertEqual(len(list(w.doc[0].annots())), 0)
        self.assertFalse(w._modified)

    def test_la_nota_se_escribe_sobre_la_pagina(self):
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        w = self.w
        self.assertTrue(w.open_path(self._crear_pdf(1)))
        w.zoom_actual()
        w._toggle_tool("NOTE")
        self._clic(fitz.Point(200, 250))
        self.assertIsNotNone(w.viewer.text_editor)
        self._sin_ventanas()
        # QTest.keyClicks tumba el proceso con caracteres no ASCII (ver §7.1),
        # así que las tildes se ponen con setPlainText.
        QTest.keyClicks(w.viewer.text_editor, "Comentario escrito en la ")
        ed = w.viewer.text_editor
        ed.setPlainText(ed.toPlainText() + "página")
        QTest.keyClick(w.viewer.text_editor, Qt.Key.Key_Return,
                       Qt.KeyboardModifier.ControlModifier)
        self.app.processEvents()
        page = w.doc[0]          # invariante 3: la página, viva en una variable
        notas = [a.info.get("content") for a in page.annots() if a.type[1] == "Text"]
        self.assertEqual(notas, ["Comentario escrito en la página"])
        w._modified = False

    def test_editar_una_anotacion_existente_sobre_la_pagina(self):
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        from viewer import AnnotSelection
        w = self.w
        self.assertTrue(w.open_path(self._crear_pdf(1)))
        w.zoom_actual()
        w.viewer.begin_text(fitz.Rect(100, 200, 300, 230))
        w.viewer.text_editor.setPlainText("Primera versión")
        QTest.keyClick(w.viewer.text_editor, Qt.Key.Key_Return,
                       Qt.KeyboardModifier.ControlModifier)
        self.app.processEvents()

        v = w.viewer
        page = w.doc[0]          # invariante 3: la página, viva en una variable
        datos = [(fitz.Rect(a.rect), a.type[1]) for a in page.annots()]
        self.assertEqual(len(datos), 1)
        r, tipo = datos[0]
        v._sel = AnnotSelection(0, fitz.Rect(r), fitz.Rect(r), tipo)
        v._edit_selected_text()
        self.assertIsNotNone(v.text_editor, "debe editarse encima, sin ventana")
        self._sin_ventanas()
        self.assertEqual(v.text_editor.toPlainText(), "Primera versión")
        v.text_editor.setPlainText("Segunda versión")
        QTest.keyClick(v.text_editor, Qt.Key.Key_Return,
                       Qt.KeyboardModifier.ControlModifier)
        self.app.processEvents()
        textos = [a.info.get("content", "") for a in w.doc[0].annots()]
        self.assertIn("Segunda versión", textos)
        self.assertNotIn("Primera versión", textos)
        w._modified = False

    def test_el_estilo_de_la_barra_se_ve_mientras_se_escribe(self):
        w = self.w
        self.assertTrue(w.open_path(self._crear_pdf(1)))
        w.zoom_actual()
        w._toggle_tool("TEXT")
        self._clic(fitz.Point(120, 300))
        editor = w.viewer.text_editor
        self.assertIsNotNone(editor)
        self.assertFalse(editor.font().bold())
        w._txt_bold_btn.setChecked(True)
        w._on_txt_bold()
        self.app.processEvents()
        self.assertTrue(editor.font().bold(), "la negrita debe verse al escribir")
        antes = editor.font().pixelSize()
        w._on_txt_size(28)
        self.app.processEvents()
        self.assertGreater(editor.font().pixelSize(), antes)
        w.viewer.close_text_editor(commit=False)
        w._modified = False

    def test_un_segundo_clic_confirma_y_no_abre_otro_cuadro(self):
        from PyQt6.QtTest import QTest
        w = self.w
        self.assertTrue(w.open_path(self._crear_pdf(1)))
        w.zoom_actual()
        w._toggle_tool("TEXT")
        self._clic(fitz.Point(120, 300))
        QTest.keyClicks(w.viewer.text_editor, "Queda escrito")
        self._clic(fitz.Point(320, 480))          # clic en otro sitio
        self.assertIsNone(w.viewer.text_editor, "el clic confirma y no reabre")
        textos = [a.info.get("content", "") for a in w.doc[0].annots()]
        self.assertEqual(textos, ["Queda escrito"])
        w._modified = False

    # ── Herramienta «Editar contenido» (edit_ui / pdf_edit) ────────────── #

    def _abrir_editable(self):
        from tests.test_nucleo import pdf_editable
        ruta = os.path.join(self.tmp, "editable.pdf")
        with open(ruta, "wb") as fh:
            fh.write(pdf_editable())
        self.assertTrue(self.w.open_path(ruta))
        self.w.zoom_actual()
        self.w._tool_btns["EDIT"].click()
        self.app.processEvents()
        return self.w

    def _clic(self, pdf_pt, boton="left"):
        from PyQt6.QtCore import QEvent, QPointF, Qt
        from PyQt6.QtGui import QMouseEvent
        v = self.w.viewer
        pos = QPointF(pdf_pt.x * v.scale_factor, pdf_pt.y * v.scale_factor)
        b = Qt.MouseButton.LeftButton if boton == "left" else Qt.MouseButton.RightButton
        for tipo in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease):
            ev = QMouseEvent(tipo, pos, v.mapToGlobal(pos), b, b,
                             Qt.KeyboardModifier.NoModifier)
            (v.mousePressEvent if tipo == QEvent.Type.MouseButtonPress
             else v.mouseReleaseEvent)(ev)
        self.app.processEvents()

    @staticmethod
    def _centro(caja):
        r = fitz.Rect(caja.bbox)
        return fitz.Point((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2)

    def _linea(self, trozo):
        return [b for b in self.w.viewer.content.blocks if trozo in b.text][0]

    def _arrastrar_esquina(self, destino):
        """Arrastra el tirador de la esquina inferior derecha de lo que esté
        seleccionado hasta `destino` (coordenadas de página), como el usuario."""
        caja = self.w.viewer.content._rect
        self.assertIsNotNone(caja, "hay que seleccionar algo antes de estirarlo")
        from PyQt6.QtCore import QEvent, QPointF, Qt
        from PyQt6.QtGui import QMouseEvent
        v = self.w.viewer
        esc = v.scale_factor
        r = fitz.Rect(caja)
        # El tirador va 6 px FUERA del cuadro (así no lo tapa el editor).
        desde = QPointF(r.x1 * esc + 6, r.y1 * esc + 6)
        hasta = QPointF(destino[0] * esc, destino[1] * esc)
        pasos = ((QEvent.Type.MouseButtonPress, desde, Qt.MouseButton.LeftButton,
                  v.mousePressEvent),
                 (QEvent.Type.MouseMove, hasta, Qt.MouseButton.LeftButton,
                  v.mouseMoveEvent),
                 (QEvent.Type.MouseButtonRelease, hasta, Qt.MouseButton.NoButton,
                  v.mouseReleaseEvent))
        for tipo, punto, botones, handler in pasos:
            handler(QMouseEvent(tipo, punto, v.mapToGlobal(punto),
                                Qt.MouseButton.LeftButton, botones,
                                Qt.KeyboardModifier.NoModifier))
        self.app.processEvents()

    def test_editar_texto_del_pdf_con_raton_y_teclado(self):
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        w = self._abrir_editable()
        c = w.viewer.content
        self.assertEqual(w.viewer.mode, "EDIT")
        self.assertFalse(w._edit_panel.isHidden())
        self.assertEqual(len(c.blocks), 4)
        self.assertEqual(len(c.boxes), 2)

        # Cursor: texto, imagen y hueco vacío se distinguen.
        self.assertEqual(self._mover(self._centro(self._linea("Importe"))),
                         Qt.CursorShape.IBeamCursor)
        self.assertEqual(self._mover(self._centro(c.boxes[0])),
                         Qt.CursorShape.SizeAllCursor)
        self.assertEqual(self._mover(fitz.Point(410, 292)), Qt.CursorShape.ArrowCursor)

        # Clic en una línea: se abre el editor con su texto y su estilo.
        self._clic(self._centro(self._linea("Importe")))
        self.assertIsNotNone(c.editor)
        self.assertEqual(c.editor.toPlainText(), "Importe total: 1.234,56 €")
        self.assertEqual(c._editing.size, 15.0)

        # Se escribe con el teclado real. Intro abre línea nueva (el texto es de
        # varias líneas); se confirma con Ctrl+Intro.
        c.editor.clear()
        QTest.keyClicks(c.editor, "Importe: 9.999,99 EUR")
        QTest.keyClick(c.editor, Qt.Key.Key_Return)
        self.assertIsNotNone(c.editor, "Intro no confirma: abre línea nueva")
        QTest.keyClick(c.editor, Qt.Key.Key_Backspace)
        QTest.keyClick(c.editor, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier)
        self.app.processEvents()
        self.assertIsNone(c.editor)
        texto = w.doc[0].get_text().replace("\xa0", " ")
        # (r36) Noto Sans es más ancha que Calibri: puede repartirse en dos líneas.
        self.assertIn("Importe: 9.999,99 EUR", " ".join(texto.split()))
        self.assertNotIn("1.234,56", texto)
        self.assertIn("Segunda línea que no se toca", texto)
        self.assertTrue(w._modified)
        self.assertTrue(w._history.can_undo())

        # Deshacer devuelve el texto original.
        w.undo()
        self.app.processEvents()
        self.assertIn("1.234,56", w.doc[0].get_text().replace("\xa0", " "))

        # Tab pasa a la línea siguiente; Esc cancela sin tocar nada.
        self._clic(self._centro(self._linea("Importe")))
        QTest.keyClick(c.editor, Qt.Key.Key_Tab)
        self.assertIn("Segunda línea", c._editing.text)
        c.editor.setPlainText("esto no debe guardarse")
        QTest.keyClick(c.editor, Qt.Key.Key_Escape)
        self.app.processEvents()
        self.assertIsNone(c.editor)
        self.assertNotIn("no debe guardarse", w.doc[0].get_text())
        w._modified = False

    def test_cambiar_el_estilo_desde_la_barra_secundaria(self):
        from PyQt6.QtWidgets import QSpinBox
        w = self._abrir_editable()
        c = w.viewer.content
        self._clic(self._centro(self._linea("Segunda")))
        self.assertEqual(w._edit_bold_btn.isChecked(), False)
        # (r40) La fuente del documento no cambia: se reescribe con la misma.
        self.assertIn("Calibri", w._lbl_edit_hint.text())
        self.assertIn("Calibri", w._lbl_edit_hint.toolTip())

        w._edit_size_spin.findChild(QSpinBox).setValue(20)
        self.app.processEvents()
        linea = self._linea("Segunda")
        self.assertEqual(linea.size, 20.0)
        # Sigue en edición y sobre LA MISMA línea: reescribirla cambia el orden
        # de extracción, así que buscarla por su índice abría otra (invariante 36).
        self.assertIsNotNone(c.editor)
        self.assertIn("Segunda", c._editing.text)
        self.assertEqual(c.editor.toPlainText(), linea.text)

        w._edit_bold_btn.click()
        self.app.processEvents()
        self.assertTrue(self._linea("Segunda").bold)
        w.viewer.content.close_editor(commit=False)
        w._modified = False

    def test_avisa_de_los_caracteres_que_no_puede_escribir(self):
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        w = self._abrir_editable()
        c = w.viewer.content
        self._clic(self._centro(self._linea("Segunda")))
        c.editor.setPlainText("Caracteres chinos 漢字")
        QTest.keyClick(c.editor, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier)
        self.app.processEvents()
        self.assertIn("漢", w.statusBar().currentMessage())
        w._modified = False

    def test_estirar_el_cuadro_reajusta_el_texto(self):
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        w = self._abrir_editable()
        c = w.viewer.content
        parrafo = [b for b in c.blocks if len(b.line_rects) == 3][0]
        caja = fitz.Rect(parrafo.bbox)
        largo = ("Texto mucho más largo que el original, escrito expresamente para "
                 "comprobar que se reparte solo en todas y cada una de las líneas "
                 "que hagan falta cuando se estira el cuadro.")

        self._clic(self._centro(parrafo))
        self.assertIsNotNone(c.editor)
        c.editor.setPlainText(largo)
        self.app.processEvents()
        # El indicador en vivo avisa de que no cabe, sin haber confirmado aún.
        self.assertIn("NO cabe", w._lbl_edit_fit.text())

        QTest.keyClick(c.editor, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier)
        self.app.processEvents()
        self.assertIsNotNone(c._overflow, "el cuadro debe quedar marcado en rojo")
        bloque = self._linea("mucho más largo")
        self.assertGreater(len(bloque.line_rects), 3)

        # Se estira el tirador de abajo a la derecha: ahora cabe.
        self._arrastrar_esquina((caja.x1, caja.y0 + 130))
        self.assertIsNone(c._overflow, "ya debería caber")
        texto = w.doc[0].get_text().replace("\xa0", " ")
        self.assertIn("Texto mucho más largo", texto)
        self.assertIn("Importe total", texto)
        self.assertTrue(w._history.can_undo())
        w._modified = False

    def test_estrechar_el_cuadro_reparte_en_mas_lineas(self):
        w = self._abrir_editable()
        c = w.viewer.content
        parrafo = [b for b in c.blocks if len(b.line_rects) == 3][0]
        caja = fitz.Rect(parrafo.bbox)
        antes = len(parrafo.line_rects)
        self._clic(self._centro(parrafo))          # seleccionarlo primero
        # Se estrecha a la mitad y se alarga mucho hacia abajo.
        self._arrastrar_esquina((caja.x0 + caja.width / 2, caja.y1 + 160))
        despues = [b for b in c.blocks if "reajustar al cuadro" in b.text][0]
        self.assertGreater(len(despues.line_rects), antes)
        w._modified = False

    def test_mover_sustituir_y_borrar_una_imagen(self):
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        from PyQt6.QtWidgets import QFileDialog
        w = self._abrir_editable()
        c = w.viewer.content

        # Seleccionar y borrar con Supr: solo desaparece esa aparición.
        self._clic(self._centro(c.boxes[0]))
        self.assertIsNotNone(c.selected_image)
        QTest.keyClick(w.viewer, Qt.Key.Key_Delete)
        self.app.processEvents()
        self.assertEqual(len(c.boxes), 1)
        w.undo()
        self.app.processEvents()
        self.assertEqual(len(c.boxes), 2)

        # Sustituir por un archivo.
        verde = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 30, 30))
        verde.set_rect(verde.irect, (20, 180, 60))
        ruta = os.path.join(self.tmp, "verde.png")
        verde.save(ruta)
        antes = fitz.Rect(c.boxes[0].bbox)
        with mock.patch.object(QFileDialog, "getOpenFileName", return_value=(ruta, "")):
            c.replace_image(c.boxes[0])
        self.app.processEvents()
        self.assertEqual(len(c.boxes), 2)
        r, g, b = w.doc[0].get_pixmap(
            clip=fitz.Rect(antes.x0 + 5, antes.y0 + 5, antes.x0 + 11, antes.y0 + 11),
            dpi=72).pixel(0, 0)
        self.assertTrue(g > 120 and r < 100, f"no se sustituyó: {(r, g, b)}")

        # Mover arrastrando.
        caja = c.boxes[0]
        origen = fitz.Rect(caja.bbox)
        c.selected = caja
        c._drag_from = fitz.Point(origen.x0 + 5, origen.y0 + 5)
        c._rect = fitz.Rect(origen) + (-60, 20, -60, 20)
        c.release()
        self.app.processEvents()
        movida = min(c.boxes, key=lambda b: fitz.Rect(b.bbox).x0)
        self.assertAlmostEqual(fitz.Rect(movida.bbox).x0, origen.x0 - 60, places=0)
        w._modified = False

    def test_salir_de_la_herramienta_limpia_los_recuadros(self):
        w = self._abrir_editable()
        self.assertTrue(w.viewer.content.blocks)
        w._finish_action()
        self.app.processEvents()
        self.assertEqual(w.viewer.mode, "NONE")
        self.assertEqual(w.viewer.content.blocks, [])
        self.assertIsNone(w.viewer.content.editor)
        self.assertTrue(w._edit_panel.isHidden())

    def test_cursor_de_texto_y_de_campos(self):
        from PyQt6.QtCore import Qt
        w = self.w
        self.assertTrue(w.open_path(self._crear_pdf(1)))
        palabra = w.viewer._page_words()[0]
        centro = fitz.Point((palabra[0] + palabra[2]) / 2, (palabra[1] + palabra[3]) / 2)
        self.assertEqual(self._mover(centro), Qt.CursorShape.IBeamCursor)
        self.assertEqual(self._mover(fitz.Point(5, 5)), Qt.CursorShape.ArrowCursor)
        self._abrir_formulario()
        self.assertEqual(self._mover(self._campo("a")["rect"].tl + (5, 5)), Qt.CursorShape.IBeamCursor)
        self.assertEqual(self._mover(self._campo("btn_js")["rect"].tl + (5, 5)),
                         Qt.CursorShape.PointingHandCursor)
        self.assertEqual(self._mover(self._campo("fijo")["rect"].tl + (5, 5)), Qt.CursorShape.ArrowCursor)

    def test_rellenar_en_linea_con_tab_y_calculo(self):
        from PyQt6.QtCore import Qt
        from PyQt6.QtTest import QTest
        w = self._abrir_formulario()
        forms = w.viewer.forms
        forms.click(self._campo("a"))
        self.assertIsNotNone(forms.editor)
        forms.editor.setText("2")
        QTest.keyClick(forms.editor, Qt.Key.Key_Tab)
        self.assertEqual(forms._editing["name"], "b", "Tab pasa al siguiente campo de texto")
        forms.editor.setText("3")
        QTest.keyClick(forms.editor, Qt.Key.Key_Return)
        self.assertIsNone(forms.editor)
        valores = {f["name"]: f["value"] for f in forms.fields}
        self.assertEqual((valores["a"], valores["b"], valores["total"]), ("2", "3", "5"))
        self.assertTrue(w._modified)
        self.assertTrue(w._history.can_undo())
        # Esc cancela sin cambiar nada
        forms.click(self._campo("a"))
        forms.editor.setText("999")
        QTest.keyClick(forms.editor, Qt.Key.Key_Escape)
        self.assertEqual(self._campo("a")["value"], "2")
        w._modified = False

    def test_casilla_y_botones_del_formulario(self):
        w = self._abrir_formulario()
        forms = w.viewer.forms
        forms.click(self._campo("acepto"))
        self.assertNotIn(self._campo("acepto")["value"], ("", "Off"))

        pasos = len(w._history._undo)
        QMessageBox.information.reset_mock()
        forms.click(self._campo("btn_aviso"))
        QMessageBox.information.assert_called_once()
        self.assertIn("Solo aviso", QMessageBox.information.call_args[0][2])
        self.assertEqual(len(w._history._undo), pasos, "un botón que no cambia nada no deja deshacer")

        with mock.patch("form_ui.QDesktopServices.openUrl") as abrir, \
                mock.patch.object(w, "print_pdf") as imprimir:
            forms.click(self._campo("btn_js"))
        valores = {f["name"]: f["value"] for f in forms.fields}
        self.assertEqual((valores["a"], valores["b"], valores["total"]), ("5", "7", "12"))
        abrir.assert_called_once()
        imprimir.assert_called_once()

        forms.click(self._campo("btn_next"))
        self.assertEqual(w.current_page, 1)
        w._modified = False

    def test_resaltar_campos_se_puede_desactivar(self):
        w = self._abrir_formulario()
        act = w._act_highlight_fields
        self.assertTrue(act.isCheckable())
        antes = act.isChecked()
        act.trigger()
        self.assertNotEqual(act.isChecked(), antes)
        act.trigger()
        self.assertEqual(act.isChecked(), antes)
        w._modified = False

    def test_ocr_sobre_el_documento_abierto_y_deshacer(self):
        w = self.w
        self.assertTrue(w.open_path(self._crear_pdf(2)))

        class Dialogo:
            def __init__(self, *a, **k):
                pass

            def exec(self):
                return True

            def values(self):
                return dict(lang="spa", all_pages=True, orientation=False)

        def ocr_falso(page, lang, detect_orientation=True):
            page.insert_text((50, 400), "Texto reconocido", fontsize=12, render_mode=3)
            return 2

        with mock.patch("dialogs.OcrDialog", Dialogo), \
                mock.patch("tesseract_ui.ensure_languages", return_value=True), \
                mock.patch("pdf_ocr.ocr_page", side_effect=ocr_falso):
            w.run_ocr()
        self.assertEqual(len(w.doc), 2)
        self.assertIn("Texto reconocido", w.doc[0].get_text())
        self.assertIn("Hola mundo", w.doc[0].get_text(), "la página original se conserva")
        self.assertEqual(w._history.undo_label(), "Reconocer texto (OCR)")
        w.undo()
        self.assertNotIn("Texto reconocido", w.doc[0].get_text())
        w._modified = False

    def test_clic_en_el_recuadro_de_firma_inicia_la_firma(self):
        """(r38) El campo de firma de un formulario responde al clic: antes se
        descartaba al leer el formulario y el recuadro no hacía nada."""
        import pdf_forms
        from tests.test_nucleo import pdf_con_campo_de_firma

        w = self.w
        ruta = os.path.join(self.tmp, "con_firma.pdf")
        with open(ruta, "wb") as fh:
            fh.write(pdf_con_campo_de_firma())
        self.assertTrue(w.open_path(ruta))
        w.zoom_actual()
        campo = [c for c in w.viewer.forms.fields if c["type"] == pdf_forms.SIGNATURE][0]
        self.assertFalse(campo["signed"])
        centro = fitz.Point((campo["rect"].x0 + campo["rect"].x1) / 2,
                            (campo["rect"].y0 + campo["rect"].y1) / 2)
        self.assertIsNotNone(w.viewer.forms.field_at(centro))
        llamadas = []
        with mock.patch.object(type(w), "sign_in_field",
                               lambda _self, f: llamadas.append(f["name"])):
            self._clic(centro)
        self.assertEqual(llamadas, ["FIRMA"], "el clic debe iniciar la firma del campo")

        # (r39) Al firmar en el recuadro se pide SIEMPRE el certificado, aunque
        # haya uno guardado de otra sesión, y cancelarlo no firma nada.
        import window_document
        guardado = {"type": "pfx", "path": "C:/no/existe.pfx", "password": "x",
                    "name": "Certificado de otra sesión", "thumbprint": ""}
        abiertos = []

        class _PickerFalso:
            def __init__(self, *_a, **kw):
                abiertos.append(kw.get("saved_cert"))

            def exec(self):
                return 0                      # el usuario cancela

        with mock.patch.object(window_document, "load_saved_cert", lambda: guardado), \
             mock.patch.object(window_document, "CertPickerDialog", _PickerFalso), \
             mock.patch.object(window_document.dialogs.SignOptionsDialog, "exec",
                               lambda _s: self.fail("las opciones van después del certificado")):
            w.sign_in_field(campo)
        self.assertEqual(abiertos, [guardado], "debe ofrecer el certificado guardado")
        sigue = [c for c in pdf_forms.field_boxes(w.doc[0]) if c["type"] == pdf_forms.SIGNATURE][0]
        self.assertFalse(sigue["signed"], "cancelar no firma")
        self.assertIsNone(w._sign_worker)
        w._modified = False

    def test_varios_documentos_como_pestanas(self):
        w = self.w
        a = self._crear_pdf(3)
        b = os.path.join(self.tmp, "segundo.pdf")
        with fitz.open() as d:
            for _ in range(5):
                d.new_page()
            d.save(b)
        self.assertTrue(w.open_path(a))
        self.assertTrue(w.sidebar._doc_area.isHidden(), "con un documento no hay pestañas")
        w.go_to_page(1)
        w.insert_blank_after(1)                     # cambio sin guardar en el primero
        pagina = w.current_page
        self.assertTrue(w._modified)

        self.assertTrue(w.open_path(b))
        self.assertEqual((len(w._sessions), w._active, len(w.doc), w._modified), (2, 1, 5, False))
        self.assertFalse(w.sidebar._doc_area.isHidden())
        self.assertFalse(w.sidebar._doc_sep.isHidden())
        botones = w.sidebar._doc_btns
        self.assertEqual(len(botones), 2)
        self.assertTrue(botones[0].toolTip().startswith("● entrada.pdf"))
        self.assertTrue(botones[1].toolTip().startswith("segundo.pdf"))
        self.assertEqual(botones[0].text(), w.sidebar.DOC_GLYPH)
        self.assertTrue(botones[1].isChecked())
        self.assertFalse(w._history.can_undo(), "cada documento tiene su historial")

        botones[0].click()
        self.app.processEvents()
        self.assertEqual((w._active, len(w.doc), w.current_page, w._modified), (0, 4, pagina, True))
        self.assertTrue(w.windowTitle().startswith("● entrada.pdf"))
        self.assertTrue(w.sidebar._doc_btns[0].isChecked())
        w.undo()
        self.assertEqual(len(w.doc), 3)

        self.assertTrue(w.open_path(b))             # ya abierto: solo cambia de pestaña
        self.assertEqual((len(w._sessions), w._active), (2, 1))
        w.next_document()
        self.assertEqual(w._active, 0)
        w.new_blank_document()
        self.assertEqual((len(w._sessions), w._active), (3, 2))
        self.assertEqual(w.sidebar._doc_btns[2].text(), w.sidebar.NEW_DOC_GLYPH)

        w._modified = False
        w.close_document()                          # se pasa a la pestaña contigua
        self.assertEqual((len(w._sessions), w._active, len(w.doc)), (2, 1, 5))
        w.close_document()
        self.assertEqual((len(w._sessions), w._active, len(w.doc)), (1, 0, 3))
        self.assertTrue(w.sidebar._doc_area.isHidden())
        w._modified = False
        w.close_document()
        self.assertIsNone(w.doc)
        self.assertEqual((w._sessions, w._active), ([], -1))

    def test_documento_nuevo_y_cifrado(self):
        w = self.w
        w.new_blank_document()
        self.assertEqual(len(w.doc), 1)
        self.assertTrue(w._modified)

        # Guardar con contraseña y reabrir: el estado debe quedar cifrado.
        w._encrypt_opts = dict(encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="abrir",
                               owner_pw="permisos", permissions=4095)
        out = os.path.join(self.tmp, "cifrado.pdf")
        self.assertTrue(w._write_to(out))
        self.assertTrue(w._orig_encrypted)
        self.assertEqual(w._password, "permisos")
        with fitz.open(out) as saved:
            self.assertTrue(saved.needs_pass)

        # Una modificación y deshacer mantienen el documento usable.
        w.insert_blank_after(0)
        self.assertEqual(len(w.doc), 2)
        w.undo()
        self.assertEqual(len(w.doc), 1)
        w._modified = False

    def test_boton_de_busqueda_alterna_y_busqueda_dinamica(self):
        """(r50, petición de Ricardo) El botón de la barra principal alterna
        mostrar/ocultar la barra de búsqueda; escribir busca sin necesidad de
        pulsar Intro; ya no hay icono de lupa (el contador ocupa su sitio, con
        ancho fijo para no desplazar el resto de la barra al crecer)."""
        from PyQt6.QtTest import QTest
        from PyQt6.QtWidgets import QLabel
        w = self.w
        self.assertTrue(w.open_path(self._crear_pdf(3)))  # "Hola mundo pagina N" × 3

        # El botón de la barra principal alterna mostrar/ocultar.
        self.assertTrue(w._find_bar.isHidden())
        w._toggle_find_bar()
        self.assertFalse(w._find_bar.isHidden())
        self.assertTrue(w._find_edit.hasFocus())
        w._toggle_find_bar()
        self.assertTrue(w._find_bar.isHidden())
        w._toggle_find_bar()
        self.assertFalse(w._find_bar.isHidden())

        # Sin icono de lupa: el contador tiene ancho fijo y no se mueve nada
        # de la barra al crecer el texto del contador.
        self.assertEqual(w._find_bar.findChildren(QLabel, "opt_glyph"), [])
        self.assertEqual(w._find_count.width(), 96)
        x_edit = w._find_edit.mapTo(w, w._find_edit.rect().topLeft()).x()
        self.app.processEvents()

        # Escribir busca sola, sin pulsar Intro; hay un pequeño retardo real.
        self.assertEqual(w._find_count.text(), "")
        QTest.keyClicks(w._find_edit, "mundo")
        self.assertEqual(w._find_count.text(), "", "no debe buscar antes del retardo")
        self.assertTrue(w._find_live_timer.isActive())
        QTest.qWait(400)
        self.app.processEvents()
        self.assertEqual(w._find_count.text(), "1 de 3")
        self.assertEqual(w._find_edit.mapTo(w, w._find_edit.rect().topLeft()).x(), x_edit)

        # Sin resultados: el contador crece a su texto más largo sin desplazar nada.
        QTest.keyClicks(w._find_edit, "1")
        QTest.qWait(400)
        self.app.processEvents()
        self.assertEqual(w._find_count.text(), "Sin resultados")
        self.assertEqual(w._find_edit.mapTo(w, w._find_edit.rect().topLeft()).x(), x_edit)

        # Vaciar el campo limpia el contador y no deja el retardo pendiente.
        w._find_edit.clear()
        self.assertEqual(w._find_count.text(), "")
        self.assertFalse(w._find_live_timer.isActive())
        w.hide_find()

    def test_opciones_de_herramienta_en_el_panel_lateral(self):
        """(r26; vuelta a este comportamiento en r50 tras probar la
        superposición de r46) Zoom y herramientas de anotación ponen sus
        opciones arriba del panel lateral, en una línea por fila y sin iconos
        sueltos, y lo empujan hacia abajo (con scroll, lo que ya se veía sigue
        disponible); Firma y Comprimir usan la barra secundaria, que solo
        empuja el visor, igual que el aviso superior."""
        from PyQt6.QtWidgets import QLabel
        w = self.w
        self.assertTrue(w.open_path(self._crear_pdf(2)))
        w.sidebar.show_panel("thumbs")
        self.app.processEvents()
        barra = w._opt_row
        self.assertIs(barra.parentWidget(), w._center.parentWidget())
        self.assertFalse(w.sidebar.isAncestorOf(barra))
        techo_panel = w.sidebar.stack.mapTo(w, w.sidebar.stack.rect().topLeft()).y()
        for mode, panel in (("TEXT", w._txt_panel), ("NOTE", w._note_panel),
                            ("MARKUP", w._markup_panel),
                            ("RECT", w._rect_panel), ("EMOJI", w._emoji_panel),
                            ("EDIT", w._edit_panel)):
            with self.subTest(mode=mode):
                w._toggle_tool(mode)
                self.app.processEvents()
                self.assertTrue(w.sidebar.tools.isAncestorOf(panel))
                self.assertTrue(panel.isVisible() and w.sidebar.column.isVisible())
                self.assertTrue(barra.isHidden())
                # (r50) Opciones encima del panel: lo empujan hacia abajo, no
                # lo tapan.
                self.assertLessEqual(panel.mapTo(w, panel.rect().bottomLeft()).y(),
                                     w.sidebar.stack.mapTo(w, w.sidebar.stack.rect().topLeft()).y())
                self.assertEqual(panel.findChildren(QLabel, "opt_glyph"), [])
                for lbl in panel.findChildren(QLabel):
                    if lbl.isVisible() and lbl.text():
                        self.assertFalse(lbl.wordWrap())
                        self.assertGreaterEqual(lbl.width(), lbl.sizeHint().width() - 1,
                                                f"no cabe en una línea: {lbl.text()!r}")
                w._toggle_tool(mode)
                self.app.processEvents()
                self.assertEqual(
                    w.sidebar.stack.mapTo(w, w.sidebar.stack.rect().topLeft()).y(), techo_panel)
        self.assertTrue(w.sidebar.tools.isHidden())
        # Firma es la única herramienta que sigue usando la barra secundaria
        # (Redactar y su panel se retiraron de la app).
        arriba = w.sidebar.mapTo(w, w.sidebar.rect().topLeft()).y()
        visor = w._center.mapTo(w, w._center.rect().topLeft()).y()
        w._toggle_tool("SIGN")
        self.app.processEvents()
        self.assertFalse(barra.isHidden())
        self.assertTrue(w.sidebar.tools.isHidden())
        self.assertEqual(w.sidebar.mapTo(w, w.sidebar.rect().topLeft()).y(), arriba)
        self.assertEqual(w._center.mapTo(w, w._center.rect().topLeft()).y(),
                         visor + barra.height())
        w._toggle_tool("SIGN")
        self.app.processEvents()

        # (r46) El aviso superior («documento firmado / cifrado / con
        # formulario») va en la columna del visor: solo lo empuja a él.
        self.assertIs(w._banner.parentWidget(), w._center.parentWidget())
        self.assertFalse(w.sidebar.isAncestorOf(w._banner))
        arriba = w.sidebar.mapTo(w, w.sidebar.rect().topLeft()).y()
        visor = w._center.mapTo(w, w._center.rect().topLeft()).y()
        self.assertTrue(w._banner.isHidden())
        w._banner_lbl.setText("Documento protegido con cifrado.")
        w._banner.show()
        self.app.processEvents()
        self.assertEqual(w.sidebar.mapTo(w, w.sidebar.rect().topLeft()).y(), arriba)
        self.assertEqual(w._center.mapTo(w, w._center.rect().topLeft()).y(),
                         visor + w._banner.height())
        w._banner.hide()
        self.app.processEvents()

        # (r46, corregido tras aviso de Ricardo: «la barra del buscador sigue
        # desplazando el panel lateral») La barra de búsqueda va en la misma
        # columna que el visor: solo lo empuja a él, igual que el aviso.
        self.assertIs(w._find_bar.parentWidget(), w._center.parentWidget())
        self.assertFalse(w.sidebar.isAncestorOf(w._find_bar))
        arriba = w.sidebar.mapTo(w, w.sidebar.rect().topLeft()).y()
        visor = w._center.mapTo(w, w._center.rect().topLeft()).y()
        self.assertTrue(w._find_bar.isHidden())
        w.show_find()
        self.app.processEvents()
        self.assertFalse(w._find_bar.isHidden())
        self.assertEqual(w.sidebar.mapTo(w, w.sidebar.rect().topLeft()).y(), arriba)
        self.assertEqual(w._center.mapTo(w, w._center.rect().topLeft()).y(),
                         visor + w._find_bar.height())
        w.hide_find()
        self.app.processEvents()

    def test_tooltips_con_fondo_amarillo_crema(self):
        """Todos los mensajes emergentes salen en crema, también los de los
        widgets con un estilo local sin selector (paneles de la barra
        secundaria, que los dejaban transparentes, y el visor, en gris)."""
        from PyQt6.QtCore import QPoint
        from PyQt6.QtWidgets import QAbstractItemView, QToolTip, QWidget
        import main
        w = self.w
        self.assertTrue(w.open_path(self._crear_pdf(2)))
        anterior = self.app.styleSheet()
        self.app.setStyleSheet(main.STYLESHEET + main.TOOLTIP_QSS)
        try:
            destinos = []
            for x in [w] + w.findChildren(QWidget):
                if x.toolTip():
                    destinos.append(x)
                if isinstance(x, QAbstractItemView):
                    destinos.append(x.viewport())
            destinos.append(w.viewer)
            self.assertGreater(len(destinos), 40)
            malos = []
            for d in destinos:
                QToolTip.hideText()
                QToolTip.showText(d.mapToGlobal(QPoint(2, 2)), "Prueba", d)
                self.app.processEvents()
                tip = next(t for t in self.app.topLevelWidgets()
                           if t.objectName() == "qtooltip_label" and t.isVisible())
                img = tip.grab().toImage()
                color = img.pixelColor(img.width() - 3, img.height() // 2).name()
                if color != "#fff8dc":
                    malos.append(f"{type(d).__name__}#{d.objectName()} {d.toolTip()!r}: {color}")
            self.assertEqual(malos, [])
        finally:
            QToolTip.hideText()
            self.app.setStyleSheet(anterior)

    def test_firma_manuscrita_desde_la_barra_de_firma(self):
        """(r68) Botón de la plumilla en la barra de Firma: firma dibujada con
        el ratón (o imagen), un clic la coloca, se mueve y se deshace."""
        import math
        from PyQt6.QtCore import QEvent, QPointF
        from PyQt6.QtGui import QColor, QImage, QMouseEvent
        from PyQt6.QtWidgets import QDialogButtonBox
        import firma_manuscrita as fm
        import firma_manuscrita_ui as fmu
        w = self.w
        self.assertTrue(w.open_path(self._crear_pdf(1)))
        w._toggle_tool("SIGN")
        self.app.processEvents()
        self.assertTrue(w._btn_handsign.isVisible())

        def raton(widget, tipo, x, y):
            pulsado = tipo != QEvent.Type.MouseButtonRelease
            ev = QMouseEvent(tipo, QPointF(x, y), QPointF(x, y), Qt.MouseButton.LeftButton,
                             Qt.MouseButton.LeftButton if pulsado else Qt.MouseButton.NoButton,
                             Qt.KeyboardModifier.NoModifier)
            {QEvent.Type.MouseButtonPress: widget.mousePressEvent,
             QEvent.Type.MouseMove: widget.mouseMoveEvent,
             QEvent.Type.MouseButtonRelease: widget.mouseReleaseEvent}[tipo](ev)

        # Lienzo: se firma con el ratón; color y grosor se aplican a la tinta.
        dlg = fmu.HandSignatureDialog(w)
        dlg._tabs.setCurrentIndex(0)
        c = dlg.canvas
        c.clear()
        self.assertFalse(dlg._bb.button(QDialogButtonBox.StandardButton.Ok).isEnabled())
        raton(c, QEvent.Type.MouseButtonPress, 60, 150)
        for i in range(1, 40):
            raton(c, QEvent.Type.MouseMove, 60 + i * 12, 150 - 60 * math.sin(i / 4))
        raton(c, QEvent.Type.MouseButtonRelease, 540, 120)
        self.assertEqual(len(c.strokes), 1)
        dlg._width_spin.setValue(7)
        self.assertEqual(c.width, 7)
        self.assertTrue(dlg._bb.button(QDialogButtonBox.StandardButton.Ok).isEnabled())
        sig = dlg.signature()
        self.assertFalse(sig.is_image)
        self.assertEqual(sig.width, 7)
        img = c.grab().toImage()
        rojo = min(img.pixelColor(x, y).red() for x in range(40, 600, 2) for y in range(60, 200, 2))
        self.assertLess(rojo, 120)                                   # hay tinta azul
        dlg.deleteLater()

        # Colocar: la herramienta queda armada y un clic la estampa.
        with mock.patch.object(fmu, "ask_hand_signature", return_value=sig):
            w._btn_handsign.click()
        self.app.processEvents()
        v = w.viewer
        self.assertTrue(w._btn_handsign.isChecked())
        self.assertIs(v.hand_signature, sig)
        p = v._to_screen_rect(fitz.Rect(250, 300, 251, 301)).topLeft()
        raton(v, QEvent.Type.MouseMove, p.x(), p.y())
        self.assertIsNotNone(v._hover_pos)
        v.grab()                                     # pinta la vista previa sin fallar
        raton(v, QEvent.Type.MouseButtonPress, p.x(), p.y())
        raton(v, QEvent.Type.MouseButtonRelease, p.x(), p.y())
        self.app.processEvents()
        pagina = w.doc[0]            # la Annot solo guarda una referencia débil a su página
        annots = list(pagina.annots())
        self.assertEqual(len(annots), 1)
        a = annots[0]
        self.assertTrue(fm.is_hand_signature(a.info["subject"]))
        self.assertAlmostEqual(a.rect.width, fm.DEFAULT_PLACE_WIDTH, delta=0.5)
        self.assertLess(abs((a.rect.x0 + a.rect.x1) / 2 - 250), 2)
        self.assertEqual(v.mode, "NONE")
        self.assertIsNone(v.hand_signature)
        self.assertFalse(w._btn_handsign.isChecked())
        # Seleccionarla no abre el panel de emoji ni el de texto.
        w._show_annot_opts(a)
        self.assertTrue(w._emoji_panel.isHidden())
        self.assertTrue(w._txt_panel.isHidden())
        self.assertEqual([d["label"] for d in doc_tools.annotation_summary(w.doc)],
                         ["Firma manuscrita"])
        w.undo()
        self.assertEqual(len(list(w.doc[0].annots())), 0)

        # Esc suelta la firma preparada sin estamparla.
        w._toggle_tool("SIGN")
        with mock.patch.object(fmu, "ask_hand_signature", return_value=sig):
            w._btn_handsign.click()
        w._on_escape()
        self.assertIsNone(v.hand_signature)
        self.assertEqual(v.mode, "NONE")

        # Imagen: el papel se vuelve transparente y se recorta alrededor.
        ruta = os.path.join(self.tmp, "firma.png")
        im = QImage(300, 120, QImage.Format.Format_RGB32)
        im.fill(QColor("#F4F4F0"))
        for x in range(50, 250):
            for y in range(58, 64):
                im.setPixelColor(x, y, QColor("#101030"))
        im.save(ruta)
        out = fmu.load_signature_image(ruta)
        self.assertLess(out.width(), 215)
        self.assertLess(out.height(), 20)
        self.assertEqual(out.pixelColor(1, 1).alpha(), 0)
        self.assertGreater(out.pixelColor(out.width() // 2, out.height() // 2).alpha(), 240)
        self.assertEqual(fmu.load_signature_image(ruta, False).pixelColor(1, 1).alpha(), 255)

    def test_texto_se_escribe_con_la_fuente_elegida_y_sin_justificar(self):
        """(r69) El combo enseña cada fuente con su tipografía, el cuadro de
        escritura usa la fuente, el tamaño y el estilo elegidos mientras se
        escribe (la hoja de estilos global los pisaba) y no hay justificado."""
        import main
        from PyQt6.QtWidgets import QSpinBox
        from utils import PDFUtils
        anterior = self.app.styleSheet()
        self.app.setStyleSheet(main.STYLESHEET)      # la de verdad: es la que pisaba la fuente
        try:
            w = self.w
            self.assertTrue(w.open_path(self._crear_pdf(1)))
            w._toggle_tool("TEXT")
            self.app.processEvents()
            cb = w._cb_font
            familias = {cb.itemText(i): cb.itemData(i, type(cb.itemDelegate()).FAMILY_ROLE)
                        for i in range(cb.count())}
            self.assertEqual(familias, {"Documento": None, "Noto Sans": "Noto Sans",
                                        "Noto Serif": "Noto Serif",
                                        "Noto Sans Mono": "Noto Sans Mono"})
            cb.setCurrentText("Noto Serif")
            self.app.processEvents()
            self.assertEqual(cb.fontInfo().family(), "Noto Serif")

            w._txt_size_spin.findChild(QSpinBox).setValue(20)
            w.viewer.begin_text(fitz.Rect(72, 200, 300, 240))
            self.app.processEvents()
            ed = w.viewer.text_editor
            ed.insertPlainText("Hola")
            info = ed.fontInfo()
            self.assertEqual(info.family(), "Noto Serif")
            self.assertEqual(info.pixelSize(), round(20 * w.viewer.scale_factor))
            # Cambiar la fuente mientras se escribe se ve al momento.
            cb.setCurrentText("Noto Sans Mono")
            w._txt_bold_btn.click()
            self.app.processEvents()
            self.assertEqual(ed.fontInfo().family(), "Noto Sans Mono")
            self.assertTrue(ed.fontInfo().bold())
            self.assertEqual(ed.toPlainText(), "Hola")
            w.viewer.close_text_editor(commit=False)

            # Alineación: izquierda → centro → derecha → izquierda, nunca justificado.
            vistas = []
            for _ in range(6):
                w._txt_align_btn.click()
                vistas.append(w.viewer.text_align)
            self.assertEqual(vistas, [1, 2, 0, 1, 2, 0])
            self.assertEqual(w._ALIGN_GLYPHS, ["align_left", "align_center", "align_right"])
            # Un texto antiguo justificado se muestra (y sigue) a la izquierda.
            import icons
            page = w.doc[0]              # la Annot solo guarda una referencia débil a su página
            PDFUtils.add_text_annotation(w.doc, 0, fitz.Rect(72, 300, 300, 340), "Viejo",
                                         align=3)
            a = next(x for x in page.annots() if x.type[1] == "FreeText")
            w.viewer.text_align = 2
            w._sync_panel_to_annot(a, "TEXT")
            self.assertEqual(w.viewer.text_align, 0)
            self.assertEqual(w._txt_align_btn.text(), icons.glyph("align_left"))
        finally:
            self.app.setStyleSheet(anterior)

    def test_presentacion_inicial_y_no_volver_a_mostrar(self):
        """(r70) Presentación al arrancar: recorre las características, avanza
        sola, y «No volver a mostrar» impide que salga en el siguiente inicio;
        desde Ayuda se vuelve a ver y a reactivar."""
        from PyQt6.QtWidgets import QLabel
        import icons
        import presentacion as pr
        s = QSettings("aventyapdf", "config")
        habia = s.contains(pr.KEY_SHOW)
        antes = s.value(pr.KEY_SHOW)
        try:
            s.remove(pr.KEY_SHOW)
            self.assertTrue(pr.should_show())              # por defecto, sale
            for sl in pr.SLIDES:
                icons.glyph(sl.icon)                          # todos los iconos existen
            self.assertGreaterEqual(len(pr.SLIDES), 10)
            textos = " ".join(sl.title + sl.text for sl in pr.SLIDES)
            for tema in ("PAdES", "manuscrita", "OCR", "formularios", "páginas", "AES-256"):
                self.assertIn(tema.lower(), textos.lower())

            d = pr.show_welcome(self.w, only_if_enabled=True)
            self.assertIsNotNone(d)
            self.app.processEvents()
            self.assertTrue(d.isVisible())
            self.assertEqual(d.index, 0)
            self.assertFalse(d._btn_prev.isEnabled())
            # Avanza sola…
            for _ in range(pr.SLIDE_MS // pr.TICK_MS + 1):
                d._tick()
            self.assertEqual(d.index, 1)
            self.assertGreater(d._progress.value, 0)
            # …pero no mientras el ratón está encima.
            d._paused = True
            for _ in range(pr.SLIDE_MS // pr.TICK_MS + 1):
                d._tick()
            self.assertEqual(d.index, 1)
            d._paused = False
            d.go(len(pr.SLIDES) - 1)
            self.assertEqual(d._btn_next.text(), "Empezar")
            self.assertAlmostEqual(d._progress.value, 1.0)
            # Las fuentes de la maqueta no las pisa la hoja de estilos global.
            titulo = d.findChild(QLabel, "titulo")
            self.assertGreater(titulo.fontInfo().pixelSize(), 40)
            # (r71) Pie: titular real, libre distribución y enlace al repositorio.
            pie = d.findChild(QLabel, "pie").text()
            self.assertIn("Aventya Asesoría Integral SL", pie)
            self.assertIn("https://github.com/Aventya/AventyaPDF", pie)
            self.assertNotIn("Technologies", pie)
            self.assertNotIn("derechos reservados", pie)

            d._chk.setChecked(True)
            d._btn_next.click()                               # «Empezar» cierra
            self.app.processEvents()
            self.assertFalse(pr.should_show())
            self.assertIsNone(pr.show_welcome(self.w, only_if_enabled=True))

            # Desde el menú Ayuda sí sale, con la casilla marcada; desmarcarla reactiva.
            d = self.w.show_welcome()
            self.assertIsNotNone(d)
            self.assertTrue(d._chk.isChecked())
            d._chk.setChecked(False)
            d.reject()
            self.app.processEvents()
            self.assertTrue(pr.should_show())
        finally:
            if habia:
                s.setValue(pr.KEY_SHOW, antes)
            else:
                s.remove(pr.KEY_SHOW)
            s.sync()


if __name__ == "__main__":
    unittest.main(verbosity=2)
