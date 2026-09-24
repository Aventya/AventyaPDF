"""
Herramienta «Editar contenido» del visor (Qt), al estilo de Acrobat «Editar PDF»:

* con la herramienta activa, cada párrafo y cada imagen de la página se enmarcan
  con un recuadro discontinuo y se resaltan al pasar por encima;
* clic en un párrafo = editor sobre su propio cuadro. El texto se **reajusta**
  al cuadro: si escribes más, se reparte en más líneas, y si no caben puedes
  **estirar una esquina** para hacerlo más alto o más ancho. La barra secundaria
  va diciendo cuántas líneas ocupa y si cabe;
* el cuadro de escritura es el compartido de `inplace_editor` (mismas teclas en
  toda la app): Intro abre línea nueva, **Ctrl+Intro** confirma, Esc cancela y
  Tab / Mayús+Tab pasan al párrafo siguiente o anterior (por orden visual);
* clic en una imagen = la selecciona: se arrastra, se redimensiona por las
  esquinas sin deformarla, Supr la borra y el menú contextual la sustituye o la
  guarda;
* cada cambio es un paso de deshacer y los avisos (fuente sustituida, caracteres
  sin glifo, texto que no cabe) se enseñan en la barra de estado.

La lógica de PDF está en pdf_edit (sin Qt).
"""
import os

import fitz
from PyQt6.QtCore import QPoint, QRect, Qt
from PyQt6.QtGui import QColor, QPen
from PyQt6.QtWidgets import QFileDialog, QMenu, QMessageBox

import inplace_editor
import pdf_edit

_TEXT_BOX = QColor(0, 120, 212, 130)       # azul Fluent, discontinuo
_IMAGE_BOX = QColor(16, 137, 62, 150)      # verde para distinguir imagen de texto
_HOVER = QColor(0, 120, 212, 30)
_SELECTED = QColor(0, 120, 212)
_OVERFLOW = QColor(196, 43, 28)            # rojo: el texto no cabe en el cuadro
_HANDLE = 8                                # lado del tirador de esquina, en píxeles
_OUT = 6                                   # cuánto se salen los tiradores del cuadro

_FILTRO_IMG = ("Imágenes (*.png *.jpg *.jpeg *.bmp *.gif *.tif *.tiff *.webp)"
               ";;Todos los archivos (*.*)")


class ContentEditor:
    def __init__(self, viewer):
        self.viewer = viewer
        self.blocks: list = []
        self.boxes: list = []
        self.editor: inplace_editor.InPlaceEditor | None = None
        self._editing = None           # TextBlock en edición
        self._busy = False
        self.hover = None              # TextBlock o ImageBox bajo el cursor
        self.selected = None           # lo seleccionado (con tiradores)
        self._rect: fitz.Rect | None = None   # su cuadro actual, en la página vista
        self._overflow: fitz.Rect | None = None
        self._drag_from: fitz.Point | None = None
        self._resizing: str | None = None

    @property
    def mw(self):
        return self.viewer.main_window

    def active(self) -> bool:
        return self.viewer.mode == "EDIT"

    @property
    def selected_image(self):
        return self.selected if isinstance(self.selected, pdf_edit.ImageBox) else None

    # ── estado ─────────────────────────────────────────────────────────── #

    def refresh(self) -> None:
        page = self.viewer.pdf_page
        if not self.active() or page is None:
            self.blocks, self.boxes = [], []
            return
        try:
            self.blocks = pdf_edit.text_blocks(page)
            self.boxes = pdf_edit.images(page)
        except Exception as e:  # noqa: BLE001 — página huérfana tras deshacer
            print(f"[editar contenido] no se pudo leer la página: {e}")
            self.blocks, self.boxes = [], []
        self.hover = None
        self.selected = None
        self._rect = None

    def clear(self) -> None:
        self.close_editor(commit=True)
        self.blocks, self.boxes = [], []
        self.hover = self.selected = None
        self._rect = self._overflow = None
        self._drag_from = self._resizing = None

    def _item_at(self, pdf_pt):
        """El párrafo o la imagen bajo el punto. El texto gana: suele estar
        encima de la imagen de fondo y es lo que el usuario quiere tocar."""
        return (pdf_edit.block_at(self.blocks, pdf_pt)
                or pdf_edit.image_at(self.boxes, pdf_pt))

    def _closest(self, caja) -> object | None:
        """El párrafo que más se solapa con `caja`: así se recupera el que se
        acaba de reescribir, cuyo cuadro puede haber cambiado de sitio."""
        if caja is None:
            return None
        r = fitz.Rect(caja)
        mejor, mayor = None, 0.0
        for b in self.blocks:
            area = (fitz.Rect(b.bbox) & r).get_area()
            if area > mayor:
                mejor, mayor = b, area
        return mejor

    def _reading_order(self) -> list:
        """Orden visual (arriba-abajo, izquierda-derecha) para Tab."""
        return sorted(self.blocks, key=lambda b: (round(b.bbox[1], 1), round(b.bbox[0], 1)))

    # ── pintado ────────────────────────────────────────────────────────── #

    def paint(self, painter) -> None:
        if not self.active():
            return
        v = self.viewer
        for item in self.blocks:
            self._frame(painter, fitz.Rect(item.bbox), _TEXT_BOX)
        for item in self.boxes:
            self._frame(painter, fitz.Rect(item.bbox), _IMAGE_BOX)
        if self.hover is not None and self.hover is not self.selected:
            painter.fillRect(v._to_screen_rect(fitz.Rect(self.hover.bbox)), _HOVER)
        if self._overflow is not None:
            # Hasta dónde llega el texto: se ve cuánto hay que estirar. Va antes
            # del marco de selección, pero en rojo y más alto, así que asoma.
            painter.setPen(QPen(_OVERFLOW, 2, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(v._to_screen_rect(self._overflow))
        if self._rect is not None:
            # El marco de selección se pinta en rojo cuando el texto no cabe:
            # en azul quedaba encima del aviso y lo tapaba.
            color = _OVERFLOW if self._overflow is not None else _SELECTED
            r = v._to_screen_rect(self._rect)
            painter.setPen(QPen(color, 2, Qt.PenStyle.SolidLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(r)
            painter.setBrush(color)
            for pt in self._handle_points(r):
                painter.drawRect(QRect(pt.x() - _HANDLE // 2, pt.y() - _HANDLE // 2,
                                       _HANDLE, _HANDLE))
            painter.setBrush(Qt.BrushStyle.NoBrush)

    def _frame(self, painter, rect: fitz.Rect, color) -> None:
        painter.setPen(QPen(color, 1, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(self.viewer._to_screen_rect(rect))

    @staticmethod
    def _handle_points(r: QRect) -> list[QPoint]:
        """Los tiradores van FUERA del cuadro: mientras se edita, el editor lo
        tapa entero y, si cayesen dentro, los clics no llegarían al visor."""
        o = r.adjusted(-_OUT, -_OUT, _OUT, _OUT)
        return [o.topLeft(), o.topRight(), o.bottomLeft(), o.bottomRight()]

    def _corner_at(self, pos: QPoint) -> str | None:
        if self._rect is None:
            return None
        r = self.viewer._to_screen_rect(self._rect)
        for name, pt in zip(("TL", "TR", "BL", "BR"), self._handle_points(r)):
            if abs(pos.x() - pt.x()) <= _HANDLE and abs(pos.y() - pt.y()) <= _HANDLE:
                return name
        return None

    # ── ratón ──────────────────────────────────────────────────────────── #

    def cursor_at(self, pos: QPoint, pdf_pt) -> Qt.CursorShape:
        corner = self._corner_at(pos)
        if corner:
            return (Qt.CursorShape.SizeFDiagCursor if corner in ("TL", "BR")
                    else Qt.CursorShape.SizeBDiagCursor)
        item = self._item_at(pdf_pt)
        if isinstance(item, pdf_edit.TextBlock):
            return Qt.CursorShape.IBeamCursor
        if item is not None:
            return Qt.CursorShape.SizeAllCursor
        return Qt.CursorShape.ArrowCursor

    def press(self, pos: QPoint, pdf_pt) -> None:
        # Estirar una esquina no debe cerrar el editor: el visor no le quita el
        # foco porque su mousePressEvent no llama a super().
        corner = self._corner_at(pos)
        if corner:
            self._resizing = corner
            return
        self.close_editor(commit=True)
        item = self._item_at(pdf_pt)
        self.selected = item
        self._rect = fitz.Rect(item.bbox) if item is not None else None
        if isinstance(item, pdf_edit.TextBlock):
            self.open_editor(item)
        elif item is not None:
            self._drag_from = fitz.Point(pdf_pt)
            self.viewer.setFocus()
        self.viewer.update()

    def move(self, pos: QPoint, pdf_pt, left: bool) -> None:
        if left and self._resizing and self.selected is not None:
            self._rect = self._resized(fitz.Rect(self.selected.bbox), pdf_pt)
            if self.editor is not None:
                self.editor.setGeometry(self._editor_rect())
                self._update_fit()
            self.viewer.update()
            return
        if left and self._drag_from is not None and self.selected_image is not None:
            dx, dy = pdf_pt.x - self._drag_from.x, pdf_pt.y - self._drag_from.y
            self._rect = fitz.Rect(self.selected.bbox) + (dx, dy, dx, dy)
            self.viewer.update()
            return
        nuevo = self._item_at(pdf_pt)
        if nuevo is not self.hover:
            self.hover = nuevo
            self.viewer.update()

    def _resized(self, o: fitz.Rect, p) -> fitz.Rect:
        """El cuadro al arrastrar la esquina `self._resizing`, con la esquina
        opuesta fija. Las imágenes no se deforman; los cuadros de texto sí, que
        es justo lo que permite repartir el texto en más o menos líneas."""
        x, y = p.x, p.y
        r = {"TL": lambda: fitz.Rect(min(x, o.x1), min(y, o.y1), o.x1, o.y1),
             "TR": lambda: fitz.Rect(o.x0, min(y, o.y1), max(x, o.x0), o.y1),
             "BL": lambda: fitz.Rect(min(x, o.x1), o.y0, o.x1, max(y, o.y0)),
             "BR": lambda: fitz.Rect(o.x0, o.y0, max(x, o.x0), max(y, o.y0))}[self._resizing]()
        pagina = self.viewer.pdf_page.rect
        r = pdf_edit.clamp_box(r, pagina)
        return (pdf_edit.clamp_box(self._keep_aspect(r, o), pagina)
                if self.selected_image is not None else r)

    @staticmethod
    def _keep_aspect(r: fitz.Rect, o: fitz.Rect) -> fitz.Rect:
        """Las imágenes nunca se deforman (como los emojis, invariante 3)."""
        if o.width <= 0 or o.height <= 0 or r.width <= 0 or r.height <= 0:
            return r
        s = max(r.width / o.width, r.height / o.height)
        return fitz.Rect(r.x0, r.y0, r.x0 + o.width * s, r.y0 + o.height * s)

    def release(self, _pos: QPoint | None = None) -> None:
        redim, movida = self._resizing, self._drag_from is not None
        item, nuevo = self.selected, self._rect
        self._drag_from = self._resizing = None
        if not (redim or movida) or item is None or nuevo is None:
            return
        # Un clic sin arrastrar no debe gastar un paso de deshacer.
        viejo = fitz.Rect(item.bbox)
        if (abs(nuevo.x0 - viejo.x0) < 1 and abs(nuevo.y0 - viejo.y0) < 1
                and abs(nuevo.x1 - viejo.x1) < 1 and abs(nuevo.y1 - viejo.y1) < 1):
            self._rect = viejo
            return
        if isinstance(item, pdf_edit.TextBlock):
            texto = self.editor.toPlainText() if self.editor is not None else item.text
            seguia = self.editor is not None
            self.close_editor(commit=False)
            self._write(item, texto, rect=nuevo, label="Ajustar cuadro de texto",
                        reopen=seguia)
        else:
            self._apply("Redimensionar imagen" if redim else "Mover imagen",
                        lambda page: pdf_edit.place_image(page, item, rect=nuevo))

    # ── menú contextual y teclado ──────────────────────────────────────── #

    def context_menu(self, pos: QPoint, global_pos, pdf_pt) -> None:
        item = self._item_at(pdf_pt)
        if isinstance(item, pdf_edit.TextBlock):
            menu = QMenu(self.viewer)
            a_edit = menu.addAction("Editar este texto")
            a_del = menu.addAction("Eliminar este texto")
            chosen = menu.exec(global_pos)
            if chosen is a_edit:
                self.selected, self._rect = item, fitz.Rect(item.bbox)
                self.open_editor(item)
            elif chosen is a_del:
                self._apply("Eliminar texto",
                            lambda page: pdf_edit.delete_block(page, item))
            return
        if item is None:
            return
        self.selected, self._rect = item, fitz.Rect(item.bbox)
        self.viewer.update()
        menu = QMenu(self.viewer)
        a_rep = menu.addAction("Sustituir imagen…")
        a_save = menu.addAction("Guardar imagen como…")
        menu.addSeparator()
        a_del = menu.addAction("Eliminar imagen")
        if pdf_edit.is_shared(self.viewer.pdf_page, item):
            menu.addSeparator()
            nota = menu.addAction("Esta imagen está colocada en más sitios; "
                                  "solo se cambia esta")
            nota.setEnabled(False)
        chosen = menu.exec(global_pos)
        if chosen is a_rep:
            self.replace_image(item)
        elif chosen is a_save:
            self.save_image(item)
        elif chosen is a_del:
            self.delete_selected()

    def delete_selected(self) -> bool:
        caja = self.selected_image
        if caja is None:
            return False
        self._apply("Eliminar imagen", lambda page: pdf_edit.delete_image(page, caja))
        return True

    def replace_image(self, caja) -> None:
        ruta, _ = QFileDialog.getOpenFileName(self.mw, "Sustituir imagen", "", _FILTRO_IMG)
        if not ruta:
            return
        try:
            with open(ruta, "rb") as f:
                datos = f.read()
            fitz.Pixmap(datos)          # comprueba que MuPDF sabe leerla
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self.mw, "Sustituir imagen",
                                f"No se pudo leer «{os.path.basename(ruta)}»:\n{e}")
            return
        self._apply("Sustituir imagen",
                    lambda page: pdf_edit.place_image(page, caja, datos))

    def save_image(self, caja) -> None:
        page = self.viewer.pdf_page
        try:
            ext, datos = pdf_edit.image_bytes(page, caja)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self.mw, "Guardar imagen", f"No se pudo extraer:\n{e}")
            return
        base = os.path.splitext(os.path.basename(self.mw.pdf_path or "imagen"))[0]
        ruta, _ = QFileDialog.getSaveFileName(
            self.mw, "Guardar imagen como",
            f"{base}_p{page.number + 1}_{caja.index + 1}.{ext}",
            f"Imagen {ext.upper()} (*.{ext});;Todos los archivos (*.*)")
        if not ruta:
            return
        try:
            with open(ruta, "wb") as f:
                f.write(datos)
        except OSError as e:
            QMessageBox.warning(self.mw, "Guardar imagen", f"No se pudo guardar:\n{e}")
            return
        self.mw.statusBar().showMessage(f"Imagen guardada en {ruta}")

    # ── edición en línea ───────────────────────────────────────────────── #

    def _editor_rect(self) -> QRect:
        return self.viewer._to_screen_rect(self._rect)

    def open_editor(self, block) -> None:
        self.close_editor(commit=True)
        v = self.viewer
        self.selected = block
        if self._rect is None:
            self._rect = fitz.Rect(block.bbox)
        editor = inplace_editor.InPlaceEditor(v, self._editor_rect())
        editor.apply_style(family=pdf_edit.family_for(block.font, block.flags,
                                                      block.bold, block.italic),
                           pixel_size=block.size * v.scale_factor,
                           bold=block.bold, italic=block.italic, color=block.color,
                           align=inplace_editor.ALIGN_INDEX.get(block.align, 0))
        editor.setPlainText(block.text)
        editor.selectAll()
        editor.committed.connect(lambda _t: self.close_editor(commit=True))
        editor.cancelled.connect(lambda: self.close_editor(commit=False))
        editor.moved.connect(lambda d: self.close_editor(commit=True, move=d))
        editor.textChanged.connect(self._update_fit)
        self.editor, self._editing = editor, block
        self._overflow = None
        editor.show()
        editor.setFocus()
        self.mw._show_edit_opts(block)
        self._update_fit()
        v.update()

    def _update_fit(self) -> None:
        """Dice en la barra secundaria cuántas líneas ocupa el texto y si cabe
        en el cuadro, mientras se escribe o se estira una esquina."""
        block, editor = self._editing, self.editor
        if block is None or editor is None or self._rect is None:
            return
        try:
            font, _ = pdf_edit.resolve_font(block.font, block.flags, block.bold, block.italic)
            lineas = pdf_edit.wrap(editor.toPlainText(), font, block.size, self._rect.width)
            alto = pdf_edit.needed_height(len(lineas), block, font, block.size)
        except Exception:  # noqa: BLE001
            return
        self.mw._set_edit_fit(len(lineas), alto, self._rect.height)

    def close_editor(self, commit: bool = True, move: int = 0) -> None:
        if self.editor is None or self._busy:
            return
        self._busy = True
        editor, block, caja = self.editor, self._editing, self._rect
        self.editor = self._editing = None
        texto = editor.toPlainText()
        editor.finish()
        try:
            if commit and texto != block.text:
                self._write(block, texto, rect=caja, label="Editar texto")
        finally:
            self._busy = False
        if move and self.blocks:
            orden = self._reading_order()
            actual = self._closest(caja)
            i = next((k for k, b in enumerate(orden) if b is actual), -1)
            if i >= 0:
                siguiente = orden[(i + move) % len(orden)]
                self._rect = fitz.Rect(siguiente.bbox)
                self.open_editor(siguiente)
                return
        self.viewer.update()

    def apply_style(self, block=None, text: str | None = None, **estilo) -> None:
        """Lo llama la barra secundaria al cambiar tamaño, color o negrita.

        `block` y `text` permiten pasar lo que había en el editor antes de que un
        diálogo modal (el selector de color) le robase el foco y lo cerrase."""
        block = block if block is not None else self._editing
        if block is None:
            return
        if text is None:
            text = self.editor.toPlainText() if self.editor is not None else block.text
        caja = self._rect
        self.close_editor(commit=False)
        self._write(block, text, rect=caja, label="Editar texto", reopen=True, **estilo)

    def _write(self, block, texto: str, *, rect=None, label="Editar texto",
               reopen: bool = False, **estilo) -> None:
        """Reescribe el párrafo y, si hace falta, vuelve a abrir el editor
        sobre el cuadro que ha quedado."""
        if not texto.strip():
            self._apply("Eliminar texto", lambda page: pdf_edit.delete_block(page, block))
            return
        salida = {}
        self._apply(label, lambda page: salida.setdefault(
            "res", pdf_edit.replace_block(page, block, texto, rect=rect, **estilo)))
        res = salida.get("res")
        if res is None:
            return
        # Se guarda hasta dónde LLEGA el texto, no el cuadro: así el visor
        # enseña cuánto falta por estirar.
        caja_res = fitz.Rect(res.box) if res.box is not None else None
        self._overflow = (fitz.Rect(caja_res.x0, caja_res.y0, caja_res.x1,
                                    caja_res.y0 + res.needed)
                          if res.overflows and caja_res is not None else None)
        if res.warnings:
            self.mw.statusBar().showMessage("  ·  ".join(res.warnings), 15000)
        nuevo = self._closest(res.box)
        if nuevo is not None:
            self.selected = nuevo
            self._rect = fitz.Rect(res.box)
            if reopen:
                self.open_editor(nuevo)
        self.viewer.update()

    # ── un cambio = un paso de deshacer ────────────────────────────────── #

    def _apply(self, etiqueta: str, fn) -> None:
        mw, page = self.mw, self.viewer.pdf_page
        if mw is None or mw.doc is None or page is None:
            return
        mw.checkpoint(etiqueta)
        try:
            fn(page)
        except Exception as e:  # noqa: BLE001
            mw._rollback_last()
            QMessageBox.critical(mw, etiqueta, f"No se pudo completar la operación:\n{e}")
            return
        mw.mark_modified()
        mw.render_page()
        mw.statusBar().showMessage(f"{etiqueta}: hecho")
