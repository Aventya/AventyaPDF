"""
sidebar.py
Panel de navegación lateral al estilo Acrobat: una barra de iconos (rail) y
cuatro paneles apilados — Miniaturas, Marcadores, Comentarios y Firmas.

El panel no modifica el documento por su cuenta: todas las acciones que
cambian el PDF se delegan en `MainWindow` (que gestiona deshacer y el estado
«modificado»). Se refresca con `doc_changed()`, que agrupa las peticiones
con un temporizador para no re-renderizar en cada pulsación.
"""
import fitz
from PyQt6.QtCore import QEvent, QItemSelectionModel, QMimeData, QRect, Qt, QSize, QTimer
from PyQt6.QtGui import QColor, QCursor, QDrag, QFont, QIcon, QImage, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView, QApplication, QFrame, QHBoxLayout, QInputDialog, QLabel, QListWidget,
    QListWidgetItem, QMenu, QPushButton, QScrollArea, QSizePolicy, QStackedWidget, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget,
)

import doc_tools
import icons
_ROLE = Qt.ItemDataRole.UserRole

COLUMN_MIN = 310          # ancho mínimo de la columna del panel lateral (r72: 290 → 310)
_THUMB_W = 130
_THUMB_H = int(_THUMB_W * 1.42)
_LABEL_H = 20


def _thumb_image(page: fitz.Page) -> QImage:
    zoom = min(_THUMB_W / max(1.0, page.rect.width), _THUMB_H / max(1.0, page.rect.height))
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
    return QImage(pix.samples, pix.width, pix.height, pix.stride,
                  QImage.Format.Format_RGB888).copy()   # copia: pix se libera


def _labeled_icon(img: QImage, number: int) -> QIcon:
    """El número de página se pinta dentro del propio icono, debajo de la
    imagen: así todas las celdas de la cuadrícula miden lo mismo."""
    pm = QPixmap(_THUMB_W, _THUMB_H + _LABEL_H)
    pm.fill(QColor(0, 0, 0, 0))
    p = QPainter(pm)
    x = (_THUMB_W - img.width()) // 2
    y = (_THUMB_H - img.height()) // 2
    p.fillRect(x + 2, y + 2, img.width(), img.height(), QColor(0, 0, 0, 40))
    p.drawImage(x, y, img)
    p.setPen(QColor("#8A8886"))
    p.drawRect(x, y, img.width() - 1, img.height() - 1)
    f = QFont(icons.noto_family("sans"))         # (r40) fuente base de la app
    f.setPixelSize(12)
    p.setFont(f)
    p.setPen(QColor("#201F1E"))
    p.drawText(QRect(0, _THUMB_H, _THUMB_W, _LABEL_H),
               int(Qt.AlignmentFlag.AlignCenter), str(number))
    p.end()
    return QIcon(pm)


def _panel_header(title: str) -> QLabel:
    lbl = QLabel(title)
    lbl.setObjectName("side_title")
    return lbl


# (r36) Iconos de Fluent UI System Icons para los botones de los paneles.
_G_ADD = icons.glyph("plus")
_G_RENAME = icons.glyph("rename")
_G_DELETE = icons.glyph("delete")
_G_REFRESH = icons.glyph("refresh")


def _small_btn(glyph: str, tip: str, fn) -> QPushButton:
    """Botón de icono (Fluent UI System Icons); lo que hace va en el tooltip."""
    b = QPushButton(glyph)
    b.setObjectName("side_icon_btn")
    b.setToolTip(tip)
    b.clicked.connect(fn)
    return b


# ── Miniaturas ────────────────────────────────────────────────────────────── #

class _ThumbList(QListWidget):
    """(r31; arrastre reescrito en r51, híbrido con OLE en r52) Cuadrícula de
    miniaturas.

    (r51, aviso de Ricardo: «al soltar no hace nada») El arrastre nativo de Qt
    dejaba el destino en manos de `dropEvent`, y ese evento no se llegaba a
    disparar con el ratón de verdad: en Windows, `QDrag.exec()` entra en su
    propio bucle OLE (`DoDragDrop`), que lee los mensajes del ratón
    **directamente del sistema operativo**, no de la cola de eventos de Qt, y
    la negociación no se completaba. Las pruebas automáticas no lo detectaban
    porque llamaban a `move_selection_to` directamente, sin pasar por ningún
    gesto de ratón.

    (r52, petición de Ricardo: «una solución híbrida — la funcionalidad de
    toda la vida (pulsar, mover, soltar) pero que visualmente siga
    apoyándose en OLE para mostrar ese desplazamiento») La parte visual
    (la miniatura semitransparente que sigue al cursor, el cursor de
    «prohibido/permitido») sí viene de un `QDrag.exec()` real — es Windows
    quien la dibuja, con más fidelidad que cualquier cosa que se pueda pintar
    a mano. Pero el **destino ya no sale de `dropEvent`** (ahí es donde
    fallaba): `_run_drag` lee la posición real del cursor (`QCursor.pos()`,
    la da el sistema operativo, no la cola de Qt) en cuanto `exec()`
    devuelve el control — y `exec()` **siempre** devuelve el control al
    soltar el botón, se haya aceptado el drop o no —, y sobre esa posición
    hace exactamente lo mismo que antes de este cambio: `drop_row()` +
    `move_selection_to()`. `dropEvent` se ignora a propósito; no se confía
    en que llegue (invariante 48). `organizing=False` deja pasar los eventos
    tal cual (clic navega, como siempre)."""

    _MIME = "application/x-aventyapdf-thumbnail"

    def __init__(self, panel: "ThumbnailsPanel"):
        super().__init__()
        self._panel = panel
        self._press_pos = None      # QPoint del mousePressEvent, o None
        self._press_item = None
        self.setAcceptDrops(True)   # para que OLE pinte el cursor de "permitido"

    def drop_row(self, pos) -> int:
        """Índice del hueco donde caería lo soltado en `pos` (coordenadas del
        viewport), en orden de lectura: antes de la primera celda que quede
        por debajo del punto, o en su misma fila y a la derecha del punto."""
        for i in range(self.count()):
            r = self.visualItemRect(self.item(i))
            if pos.y() < r.top() or (pos.y() <= r.bottom() and pos.x() < r.center().x()):
                return i
        return self.count()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)       # selección normal (clic, Ctrl, Mayús…)
        item = self.itemAt(event.position().toPoint())
        if self._panel.organizing and event.button() == Qt.MouseButton.LeftButton and item:
            self._press_pos = event.position().toPoint()
            self._press_item = item

    def mouseMoveEvent(self, event):
        if self._press_pos is not None:
            movido = (event.position().toPoint() - self._press_pos).manhattanLength()
            if movido < QApplication.startDragDistance():
                return                  # aún no es un arrastre: ni clic ni drag
            press_pos, item = self._press_pos, self._press_item
            self._press_pos = None      # exec() es reentrante: fuera antes de llamarlo
            self._run_drag(item, press_pos)
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._press_pos = None          # clic sin arrastre: solo limpia el estado
        super().mouseReleaseEvent(event)

    def dragEnterEvent(self, event):
        # Solo se acepta lo que arrastra esta misma lista (r52): así OLE pinta
        # el cursor de "permitido" mientras se está encima de las miniaturas,
        # aunque el destino real no salga de aquí — ver `_run_drag`.
        if self._panel.organizing and event.source() is self:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if self._panel.organizing and event.source() is self:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        event.ignore()      # el destino se calcula en _run_drag, no aquí (invariante 48)

    def _run_drag(self, item: QListWidgetItem, press_pos) -> None:
        """Arranca el arrastre nativo (para el fantasma y el cursor de OLE) y,
        en cuanto vuelve —siempre vuelve al soltar el botón—, mueve la
        selección al hueco bajo el cursor **de verdad** (invariante 48)."""
        rect = self.visualItemRect(item)
        # (petición de Ricardo: al arrastrar una miniatura, la parte inferior
        # de la pantalla se rellenaba de negro; el ajuste de devicePixelRatio
        # y el paso a QImage con alfa premultiplicado no lo arreglaron del
        # todo — Ricardo lo sigue viendo en vivo en su pantalla, aunque ni
        # una captura mía ni una grabación con la Herramienta Recortes lo
        # recogen, así que es real pero solo en la composición en pantalla,
        # no en el mapa de bits) El fantasma ya **no lleva canal alfa en
        # absoluto**: `Format_RGB32` en vez de `Format_ARGB32_Premultiplied`,
        # opaco del todo. Antes se apoyaba en que Windows (quien compone esta
        # imagen de arrastre por OLE, no Qt) mezclara bien el alfa; sin alfa
        # que mezclar no hay semitransparencia que salga mal — a cambio dejó
        # de verse a través del fantasma, que ahora es un rectángulo opaco.
        dpr = self.viewport().devicePixelRatioF()
        img = QImage(QSize(round(rect.width() * dpr), round(rect.height() * dpr)),
                     QImage.Format.Format_RGB32)
        img.setDevicePixelRatio(dpr)
        img.fill(QColor("#EAF3FC"))
        p = QPainter(img)
        pen = QColor("#0078D4")
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(1, 1, rect.width() - 2, rect.height() - 2)
        p.end()
        fantasma = QPixmap.fromImage(img)

        drag = QDrag(self)
        mime = QMimeData()
        mime.setData(self._MIME, b"1")      # exigido por QDrag; el contenido no se usa
        drag.setMimeData(mime)
        drag.setPixmap(fantasma)
        drag.setHotSpot(press_pos - rect.topLeft())

        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        drag.exec(Qt.DropAction.MoveAction)     # bloquea; vuelve siempre al soltar
        self.unsetCursor()

        destino = self.viewport().mapFromGlobal(QCursor.pos())
        if self.viewport().rect().contains(destino):
            self._panel.move_selection_to(self.drop_row(destino))


class ThumbnailsPanel(QWidget):
    BATCH = 4

    def __init__(self, mw):
        super().__init__()
        self.mw = mw
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.addWidget(_panel_header("Miniaturas de página"))
        self.list = _ThumbList(self)
        # (r31) Cuadrícula que se reparte al ancho del panel: al ensancharlo
        # caben más columnas; orden de izquierda a derecha y luego por filas.
        self.list.setViewMode(QListWidget.ViewMode.IconMode)
        self.list.setFlow(QListWidget.Flow.LeftToRight)
        self.list.setWrapping(True)
        self.list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.list.setUniformItemSizes(True)
        self.list.setMovement(QListWidget.Movement.Static)
        self.list.setIconSize(QSize(_THUMB_W, _THUMB_H + _LABEL_H))
        self.list.setSpacing(4)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._menu)
        self.list.itemClicked.connect(self._clicked)
        self.list.itemSelectionChanged.connect(self._selection_changed)
        # (r27) Modo «Operaciones de página»: arrastrar reordena y Supr elimina.
        self.list.installEventFilter(self)
        self.organizing = False
        self._select_next: list[int] | None = None
        lay.addWidget(self.list)
        self._pending: list[int] = []
        self._timer = QTimer(self)
        self._timer.setInterval(0)
        self._timer.timeout.connect(self._render_batch)
        placeholder = QPixmap(_THUMB_W, _THUMB_H + _LABEL_H)
        placeholder.fill(QColor("#E6E6E6"))
        self._placeholder = QIcon(placeholder)

    def rebuild(self):
        # Conserva la selección (o la que haya pedido la última operación).
        keep = self._select_next if self._select_next is not None else self._selected()
        self._select_next = None
        self.list.blockSignals(True)
        self.list.clear()
        self.list.blockSignals(False)
        doc = self.mw.doc
        if not doc:
            self._timer.stop()
            self._selection_changed()
            return
        for i in range(len(doc)):
            it = QListWidgetItem(self._placeholder, "")
            it.setData(_ROLE, i)
            it.setToolTip(f"Página {i + 1}")
            self.list.addItem(it)
        self._pending = list(range(len(doc)))
        self._timer.start()
        self.set_current(self.mw.current_page)
        keep = [r for r in keep if 0 <= r < self.list.count()]
        if keep:
            self.select_rows(keep)
        self._selection_changed()

    # ── modo «Operaciones de página» ──────────────────────────────────── #

    def set_organizing(self, on: bool):
        """(r51) El propio `dragDropMode` de Qt ya no se usa para el arrastre
        (ver `_ThumbList`); esta bandera es lo único que activa o desactiva
        los `mouse*Event` de reordenar."""
        self.organizing = on

    def select_rows(self, rows: list[int]):
        self.list.blockSignals(True)
        self.list.clearSelection()
        for r in rows:
            if 0 <= r < self.list.count():
                self.list.item(r).setSelected(True)
        if rows and 0 <= rows[0] < self.list.count():
            self.list.scrollToItem(self.list.item(rows[0]))
        self.list.blockSignals(False)
        self._selection_changed()

    def select_after_rebuild(self, rows: list[int]):
        """La operación va a cambiar la estructura: selecciona `rows` al
        reconstruir las miniaturas (que llega con retardo)."""
        self._select_next = list(rows)

    def selected_pages(self) -> list[int]:
        """Páginas seleccionadas; si no hay ninguna, la actual."""
        rows = self._selected()
        if not rows and self.mw.doc is not None:
            rows = [self.mw.current_page]
        return rows

    def _selection_changed(self):
        hook = getattr(self.mw, "_update_pages_panel", None)
        if hook:
            hook()

    def move_selection_to(self, row: int):
        """Mueve las páginas seleccionadas al hueco `row` (índice de la lista
        antes de moverlas), conservando su orden y dejándolas seleccionadas."""
        doc = self.mw.doc
        rows = self._selected()
        if doc is None or not rows or self.list.count() != len(doc):
            return
        others = [r for r in range(len(doc)) if r not in rows]
        k = sum(1 for r in others if r < row)
        order = others[:k] + rows + others[k:]
        self.mw.move_pages(order, list(range(k, k + len(rows))))

    def eventFilter(self, obj, event):
        if (obj is self.list and self.organizing and event.type() == QEvent.Type.KeyPress
                and event.key() == Qt.Key.Key_Delete):
            self.mw.delete_pages(self.selected_pages())
            return True
        return super().eventFilter(obj, event)

    def _render_batch(self):
        doc = self.mw.doc
        if not doc or not self._pending:
            self._timer.stop()
            return
        for _ in range(self.BATCH):
            if not self._pending:
                break
            i = self._pending.pop(0)
            if i < self.list.count() and i < len(doc):
                self.list.item(i).setIcon(_labeled_icon(_thumb_image(doc[i]), i + 1))

    def refresh_page(self, pno: int):
        doc = self.mw.doc
        if doc and 0 <= pno < min(len(doc), self.list.count()):
            self.list.item(pno).setIcon(_labeled_icon(_thumb_image(doc[pno]), pno + 1))

    def set_current(self, pno: int):
        if 0 <= pno < self.list.count():
            self.list.blockSignals(True)
            if self.organizing:
                # Organizando, la selección es de las acciones: no la pisa.
                self.list.selectionModel().setCurrentIndex(
                    self.list.model().index(pno, 0), QItemSelectionModel.SelectionFlag.NoUpdate)
            else:
                self.list.setCurrentRow(pno)
                self.list.scrollToItem(self.list.item(pno))
            self.list.blockSignals(False)

    def _clicked(self, item):
        self.mw.go_to_page(self.list.row(item))

    def _selected(self) -> list[int]:
        return sorted(self.list.row(i) for i in self.list.selectedItems())

    def _menu(self, pos):
        rows = self._selected()
        if not rows or not self.mw.doc:
            return
        m = QMenu(self)
        n = len(rows)
        sfx = f" ({n} páginas)" if n > 1 else ""
        a_l = m.addAction("Girar a la izquierda" + sfx)
        a_r = m.addAction("Girar a la derecha" + sfx)
        m.addSeparator()
        a_dup = m.addAction("Duplicar" + sfx)
        a_ins = m.addAction("Insertar página en blanco después")
        a_pdf = m.addAction("Insertar otro PDF después…")
        a_ext = m.addAction("Extraer" + sfx + "…")
        m.addSeparator()
        a_del = m.addAction("Eliminar" + sfx)
        chosen = m.exec(self.list.mapToGlobal(pos))
        if chosen == a_l:
            self.mw.rotate_pages(rows, -90)
        elif chosen == a_r:
            self.mw.rotate_pages(rows, 90)
        elif chosen == a_dup:
            self.mw.duplicate_pages(rows)
        elif chosen == a_ins:
            self.mw.insert_blank_after(rows[-1])
        elif chosen == a_pdf:
            self.mw.insert_pdf_after(rows[-1])
        elif chosen == a_ext:
            self.mw.extract_pages(rows)
        elif chosen == a_del:
            self.mw.delete_pages(rows)


# ── Marcadores ────────────────────────────────────────────────────────────── #

class BookmarksPanel(QWidget):
    def __init__(self, mw):
        super().__init__()
        self.mw = mw
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.addWidget(_panel_header("Marcadores"))
        row = QHBoxLayout()
        row.addWidget(_small_btn(_G_ADD, "Añadir marcador en la página actual", self._add))
        row.addWidget(_small_btn(_G_RENAME, "Cambiar nombre del marcador", self._rename))
        row.addWidget(_small_btn(_G_DELETE, "Eliminar marcador", self._delete))
        row.addStretch()
        lay.addLayout(row)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemClicked.connect(self._clicked)
        self.tree.itemDoubleClicked.connect(lambda *_: self._rename())
        lay.addWidget(self.tree)
        self._empty = QLabel("Este documento no tiene marcadores.")
        self._empty.setWordWrap(True)
        self._empty.setStyleSheet("color:#8A8886; padding:8px;")
        lay.addWidget(self._empty)
        self._toc: list = []

    def rebuild(self):
        self.tree.clear()
        doc = self.mw.doc
        self._toc = [list(e[:3]) for e in doc.get_toc(simple=True)] if doc else []
        parents: dict[int, QTreeWidgetItem] = {}
        for i, (lvl, title, page) in enumerate(self._toc):
            parent = parents.get(lvl - 1)
            it = QTreeWidgetItem([title])
            it.setData(0, _ROLE, i)
            it.setToolTip(0, f"{title}  ·  página {page}" if page > 0 else title)
            if parent is not None and lvl > 1:
                parent.addChild(it)
            else:
                self.tree.addTopLevelItem(it)
            parents[lvl] = it
        self.tree.expandToDepth(0)
        self._empty.setVisible(not self._toc)

    def _clicked(self, item, _col=0):
        i = item.data(0, _ROLE)
        if i is not None and 0 <= i < len(self._toc) and self._toc[i][2] > 0:
            self.mw.go_to_page(self._toc[i][2] - 1)

    def _commit(self, label: str):
        self.mw.checkpoint(label)
        toc = [[lvl, title, max(1, min(page, len(self.mw.doc)))] for lvl, title, page in self._toc]
        self.mw.doc.set_toc(toc)
        self.mw.mark_modified(structure=False)
        self.rebuild()

    def _add(self):
        if not self.mw.doc:
            return
        page = self.mw.current_page + 1
        title, ok = QInputDialog.getText(self, "Nuevo marcador", "Nombre:", text=f"Página {page}")
        if not ok or not title.strip():
            return
        cur = self.tree.currentItem()
        if cur is not None:
            i = cur.data(0, _ROLE)
            lvl = self._toc[i][0]
            j = i + 1
            while j < len(self._toc) and self._toc[j][0] > lvl:
                j += 1
            self._toc.insert(j, [lvl, title.strip(), page])
        else:
            self._toc.append([1, title.strip(), page])
        self._commit("Añadir marcador")

    def _rename(self):
        cur = self.tree.currentItem()
        if cur is None:
            return
        i = cur.data(0, _ROLE)
        title, ok = QInputDialog.getText(self, "Cambiar nombre", "Nombre:", text=self._toc[i][1])
        if ok and title.strip():
            self._toc[i][1] = title.strip()
            self._commit("Renombrar marcador")

    def _delete(self):
        cur = self.tree.currentItem()
        if cur is None:
            return
        i = cur.data(0, _ROLE)
        lvl = self._toc[i][0]
        j = i + 1
        while j < len(self._toc) and self._toc[j][0] > lvl:
            j += 1
        del self._toc[i:j]
        # Un hijo no puede quedar dos niveles por debajo de su predecesor.
        for k in range(len(self._toc)):
            prev = self._toc[k - 1][0] if k else 0
            self._toc[k][0] = min(self._toc[k][0], prev + 1)
        self._commit("Eliminar marcador")


# ── Comentarios ───────────────────────────────────────────────────────────── #

class CommentsPanel(QWidget):
    def __init__(self, mw):
        super().__init__()
        self.mw = mw
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        head = QHBoxLayout()
        head.addWidget(_panel_header("Comentarios"))
        head.addStretch()
        head.addWidget(_small_btn(_G_REFRESH, "Actualizar comentarios", self.rebuild))
        lay.addLayout(head)
        self.list = QListWidget()
        self.list.setWordWrap(True)
        self.list.itemClicked.connect(self._clicked)
        lay.addWidget(self.list)
        self._count = QLabel()
        self._count.setStyleSheet("color:#8A8886;")
        lay.addWidget(self._count)

    def rebuild(self):
        self.list.clear()
        doc = self.mw.doc
        items = doc_tools.annotation_summary(doc) if doc else []
        for c in items:
            text = f"Pág. {c['page'] + 1} · {c['label']}"
            if c["content"]:
                text += f"\n{c['content']}"
            it = QListWidgetItem(text)
            it.setData(_ROLE, (c["page"], c["idx"]))
            self.list.addItem(it)
        self._count.setText(f"{len(items)} comentarios" if items else "Sin comentarios")

    def _clicked(self, item):
        page, idx = item.data(_ROLE)
        self.mw.select_annotation(page, idx)


# ── Firmas ────────────────────────────────────────────────────────────────── #

class SignaturesPanel(QWidget):
    """(r61) Las firmas se ven SIEMPRE verificadas: al mostrarse el panel se
    comprueban solas en segundo plano (window_document.ValidateWorker), sin
    botón. La firma más reciente lleva una papelera que la quita y deja su
    recuadro vacío para firmar de nuevo (solo la más reciente: quitar una
    anterior invalidaría las posteriores)."""
    _ICON = {"ok": ("✔", "#107C10"), "untrusted": ("⚠", "#C19C00"),
             "invalid": ("✖", "#D13438"), "error": ("✖", "#D13438")}

    def __init__(self, mw):
        super().__init__()
        self.mw = mw
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.addWidget(_panel_header("Firmas Certificadas"))
        self.list = QListWidget()
        self.list.setWordWrap(True)
        self.list.itemClicked.connect(self._clicked)
        lay.addWidget(self.list)
        self._widgets: list = []
        self._turn = 0                      # descarta verificaciones ya obsoletas
        self._workers: set = set()
        self.reports: list | None = None    # último resultado (None = verificando)
        self.trash_buttons: dict = {}       # nombre del campo → papelera

    def rebuild(self):
        self.list.clear()
        self.trash_buttons = {}
        self.reports = None
        self._turn += 1
        doc = self.mw.doc
        self._widgets = doc_tools.signature_widgets(doc) if doc else []
        if doc is None:
            return
        if not self._widgets:
            self.list.addItem(QListWidgetItem("Este documento no contiene firmas."))
            self.reports = []
            return
        self.list.addItem(QListWidgetItem("Verificando las firmas…"))
        data = self.mw.signature_bytes()
        from window_document import ValidateWorker
        w = ValidateWorker(data, self.mw._password, self._turn, self)
        w.done.connect(self._show)
        w.finished.connect(lambda w=w: (self._workers.discard(w), w.deleteLater()))
        self._workers.add(w)
        w.start()

    def wait(self, ms: int = 60000) -> bool:
        """Espera a que termine la verificación en curso (pruebas)."""
        from PyQt6.QtCore import QCoreApplication, QElapsedTimer
        t = QElapsedTimer()
        t.start()
        while self.reports is None and t.elapsed() < ms:
            QCoreApplication.processEvents()
            for w in list(self._workers):
                w.wait(20)
        QCoreApplication.processEvents()
        return self.reports is not None

    def _show(self, result, turn: int):
        if turn != self._turn:
            return
        self.list.clear()
        self.trash_buttons = {}
        if isinstance(result, str):
            self.reports = []
            it = QListWidgetItem(f"✖  No se pudieron verificar las firmas\n{result}")
            it.setForeground(QColor("#D13438"))
            self.list.addItem(it)
            return
        self.reports = list(result)
        pages = {name: pno for pno, name, _r in self._widgets}
        ultima = max((r.revision for r in self.reports), default=-1)
        puede, motivo = self.mw.can_remove_signature()
        for rep in self.reports:
            sym, col = self._ICON[rep.verdict]
            lines = [f"{sym}  {rep.verdict_text}", f"Campo: {rep.field_name}"]
            if rep.signer:
                etiqueta = "Autoridad de sellado" if rep.is_timestamp else "Firmante"
                lines.append(f"{etiqueta}: {rep.signer}")
            if rep.signed_at:
                lines.append(f"Fecha declarada: {rep.signed_at}")
            if rep.timestamp:
                lines.append(f"Sello de tiempo: {rep.timestamp}")
            if rep.modification:
                lines.append(rep.modification)
            if rep.error:
                lines.append(f"Error: {rep.error}")
            papelera = None
            if rep.revision == ultima:
                papelera = _small_btn(
                    _G_DELETE,
                    ("Quitar esta firma y dejar su recuadro vacío para firmar de nuevo"
                     if puede else motivo),
                    lambda _c=False, n=rep.field_name: self.mw.remove_last_signature(n))
                papelera.setEnabled(puede)
                self.trash_buttons[rep.field_name] = papelera
            self._add_row("\n".join(lines), col, pages.get(rep.field_name, -1), papelera)
        firmados = {r.field_name for r in self.reports}
        for pno, name, _r in self._widgets:             # recuadros de firma vacíos
            if name not in firmados:
                self._add_row(f"▢  Recuadro de firma vacío\nCampo: {name}  ·  pág. {pno + 1}\n"
                              "Haz clic en él para firmar", "#605E5C", pno, None)
        if self.mw.unsaved_rewrite() and self.reports:
            aviso = QListWidgetItem("Hay cambios sin guardar: al guardar se reescribe el "
                                    "archivo y estas firmas dejarán de ser válidas.")
            aviso.setForeground(QColor("#C19C00"))
            self.list.addItem(aviso)

    def _add_row(self, text: str, color: str, pno: int, button):
        it = QListWidgetItem()
        it.setData(_ROLE, pno)
        fila = QWidget()
        h = QHBoxLayout(fila)
        h.setContentsMargins(4, 4, 4, 4)
        h.setSpacing(4)
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setStyleSheet(f"color: {color}; background: transparent;")
        # El clic atraviesa la etiqueta y llega a la lista (ir a la página).
        lbl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        h.addWidget(lbl, 1)
        if button is not None:
            h.addWidget(button, 0, Qt.AlignmentFlag.AlignTop)
        self.list.addItem(it)
        self.list.setItemWidget(it, fila)
        ancho = max(120, self.list.viewport().width() - 8)
        alto = lbl.heightForWidth(ancho - (button.sizeHint().width() + 12 if button else 8))
        it.setSizeHint(QSize(ancho, max(alto, fila.sizeHint().height()) + 10))

    def _clicked(self, item):
        pno = item.data(_ROLE)
        if isinstance(pno, int) and pno >= 0:
            self.mw.go_to_page(pno)


# ── Contenedor ────────────────────────────────────────────────────────────── #

class SidePanel(QWidget):
    PANELS = [
        ("thumbs",   icons.glyph("panel_thumbs"), "Miniaturas de página"),
        ("bookmarks", icons.glyph("panel_bookmarks"), "Marcadores"),
        ("comments", icons.glyph("panel_comments"), "Comentarios"),
        # (r77, petición de Ricardo: «el icono debería ser el del
        # certificado») Icono del certificado digital, como el botón
        # «Seleccionar un certificado digital…» del panel Firma.
        ("signatures", icons.glyph("opt_cert"), "Firmas Certificadas"),
    ]

    def __init__(self, mw):
        super().__init__()
        self.mw = mw
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.rail = QFrame()
        self.rail.setObjectName("rail")
        self.rail.setFixedWidth(44)
        rl = QVBoxLayout(self.rail)
        rl.setContentsMargins(4, 8, 4, 8)
        rl.setSpacing(4)

        # (r26; r50, petición de Ricardo) Columna a la derecha del rail: las
        # opciones de la herramienta activa (`tools`) van arriba de los
        # paneles (`stack`) y lo empujan hacia abajo, para que la herramienta
        # y lo que ya se veía en el panel estén disponibles a la vez (con
        # scroll si hace falta). La columna se ve si se ve cualquiera de los dos.
        self.column = QWidget()
        self.column.setObjectName("side_column")
        # (r40) Ancho mínimo: el panel de opciones más ancho («Añadir texto»,
        # 306 px desde r69, por el combo de fuentes de 160 px) debe caber sin
        # que se corten sus etiquetas ni sus controles (invariante 46).
        self.column.setMinimumWidth(COLUMN_MIN)
        col = QVBoxLayout(self.column)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)
        self.tools = QFrame()
        self.tools.setObjectName("side_tools")
        self.tools.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self._tools_lay = QVBoxLayout(self.tools)
        self._tools_lay.setContentsMargins(0, 0, 0, 0)
        self._tools_lay.setSpacing(0)
        self.tools.hide()
        self.stack = QStackedWidget()
        self.stack.setObjectName("side_stack")
        # (r72) AlignTop: con el panel cerrado la columna solo tiene las
        # opciones y, sin anclarlas, el layout las centraba en vertical.
        col.addWidget(self.tools, 0, Qt.AlignmentFlag.AlignTop)
        col.addWidget(self.stack, 1)
        self.thumbs = ThumbnailsPanel(mw)
        self.bookmarks = BookmarksPanel(mw)
        self.comments = CommentsPanel(mw)
        self.signatures = SignaturesPanel(mw)
        self._panels = {"thumbs": self.thumbs, "bookmarks": self.bookmarks,
                        "comments": self.comments, "signatures": self.signatures}
        self._btns: dict[str, QPushButton] = {}
        for key, glyph, tip in self.PANELS:
            b = QPushButton(glyph)
            b.setObjectName("rail_btn")
            b.setToolTip(tip)
            b.setCheckable(True)
            b.clicked.connect(lambda _c, k=key: self.show_panel(k, toggle=True))
            self._btns[key] = b
            rl.addWidget(b)
            self.stack.addWidget(self._panels[key])

        # (r20) Documentos abiertos como pestañas, bajo un separador; solo
        # aparecen con dos o más documentos. Con muchos, se desplazan con la rueda.
        self._doc_sep = QFrame()
        self._doc_sep.setObjectName("rail_sep")
        self._doc_sep.setFixedHeight(1)
        self._doc_sep.hide()
        rl.addWidget(self._doc_sep)
        self._doc_area = QScrollArea()
        self._doc_area.setObjectName("rail_docs")
        self._doc_area.setWidgetResizable(True)
        self._doc_area.setFrameShape(QFrame.Shape.NoFrame)
        self._doc_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._doc_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        holder = QWidget()
        holder.setObjectName("rail_docs_holder")
        self._doc_lay = QVBoxLayout(holder)
        self._doc_lay.setContentsMargins(0, 0, 0, 0)
        self._doc_lay.setSpacing(4)
        self._doc_lay.addStretch()
        self._doc_area.setWidget(holder)
        self._doc_area.hide()
        rl.addWidget(self._doc_area, 1)
        self._doc_btns: list[QPushButton] = []
        self._doc_key: tuple = ()
        rl.addStretch()

        lay.addWidget(self.rail)
        lay.addWidget(self.column)
        self._current = ""
        self._dirty = {k: True for k in self._panels}
        self._structure_pending = False
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(350)
        self._timer.timeout.connect(self._flush)
        self.stack.hide()
        self.column.hide()
        self.setMaximumWidth(self.rail.maximumWidth())

    # ── visibilidad ───────────────────────────────────────────────────── #

    def show_panel(self, key: str, toggle: bool = False):
        if toggle and self._current == key and self.stack.isVisible():
            self.collapse()
            return
        self._current = key
        for k, b in self._btns.items():
            b.setChecked(k == key)
        self.stack.setCurrentWidget(self._panels[key])
        was_visible = self.stack.isVisible()
        self.stack.show()
        self._update_column()
        if self._dirty.get(key):
            self._rebuild(key)
        if not was_visible:
            self.mw._sync_splitter()
        self._notify_panel()

    def collapse(self):
        self.stack.hide()
        for b in self._btns.values():
            b.setChecked(False)
        self._update_column()
        self.mw._sync_splitter()
        self._notify_panel()

    def _notify_panel(self):
        hook = getattr(self.mw, "_on_sidebar_panel", None)
        if hook:
            hook(self._current if not self.stack.isHidden() else "")

    def is_open(self) -> bool:
        """¿Se ve la columna (panel, opciones de herramienta o ambos)?"""
        return not self.column.isHidden()

    def _update_column(self) -> bool:
        """Muestra la columna si hay panel u opciones; devuelve si cambió."""
        show = not self.stack.isHidden() or not self.tools.isHidden()
        changed = show == self.column.isHidden()
        self.column.setVisible(show)
        # Sin límite de ancho el QSplitter dejaría un hueco vacío.
        self.setMaximumWidth(16777215 if show else self.rail.maximumWidth())
        return changed

    # ── opciones de la herramienta activa ─────────────────────────────── #

    def add_tool_panel(self, panel: QWidget):
        self._tools_lay.addWidget(panel)

    def set_tools_visible(self, visible: bool):
        """Enseña u oculta las opciones de herramienta encima del panel."""
        if visible == (not self.tools.isHidden()):
            return
        self.tools.setVisible(visible)
        if self._update_column():
            self.mw._sync_splitter()

    def toggle(self):
        if self.stack.isVisible():
            self.collapse()
        else:
            self.show_panel(self._current or "thumbs")

    # ── documentos abiertos (pestañas) ────────────────────────────────── #

    DOC_GLYPH = icons.glyph("doc_pdf")
    NEW_DOC_GLYPH = icons.glyph("doc_new")     # aún sin guardar

    def set_documents(self, items: list[tuple[str, str, bool]], active: int):
        """items = (nombre, ruta, modificado) por documento abierto."""
        key = (tuple(items), active)
        if key == self._doc_key:
            return
        self._doc_key = key
        for b in self._doc_btns:
            self._doc_lay.removeWidget(b)
            b.deleteLater()
        self._doc_btns = []
        show = len(items) > 1
        self._doc_sep.setVisible(show)
        self._doc_area.setVisible(show)
        if not show:
            return
        for i, (name, path, modified) in enumerate(items):
            b = QPushButton(self.DOC_GLYPH if path else self.NEW_DOC_GLYPH)
            b.setObjectName("rail_doc")
            b.setCheckable(True)
            b.setChecked(i == active)
            b.setToolTip(("● " if modified else "") + name + (f"\n{path}" if path else ""))
            b.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            b.clicked.connect(lambda _c=False, k=i: self._doc_clicked(k))
            b.customContextMenuRequested.connect(
                lambda pos, k=i, btn=b: self._doc_menu(k, btn, pos))
            self._doc_lay.insertWidget(self._doc_lay.count() - 1, b, 0, Qt.AlignmentFlag.AlignHCenter)
            self._doc_btns.append(b)

    def _doc_clicked(self, index: int):
        self.mw.switch_document(index)
        for i, b in enumerate(self._doc_btns):      # pulsar la pestaña activa no la desmarca
            b.setChecked(i == self.mw._active)

    def _doc_menu(self, index: int, btn: QPushButton, pos):
        m = QMenu(self)
        a_close = m.addAction("Cerrar documento")
        if m.exec(btn.mapToGlobal(pos)) == a_close:
            self.mw.close_document_at(index)

    # ── sincronización con el documento ──────────────────────────────── #

    def _rebuild(self, key: str):
        self._panels[key].rebuild()
        self._dirty[key] = False

    def set_document(self):
        """Documento nuevo (abrir, cerrar, deshacer): todo se reconstruye."""
        self._dirty = {k: True for k in self._panels}
        if self.stack.isVisible() and self._current:
            self._rebuild(self._current)

    def set_current_page(self, pno: int):
        if not self._dirty["thumbs"]:
            self.thumbs.set_current(pno)

    def doc_changed(self, structure: bool = False):
        self._structure_pending |= structure
        self._timer.start()

    def _flush(self):
        structure = self._structure_pending
        self._structure_pending = False
        doc = self.mw.doc
        if structure or (doc and self.thumbs.list.count() != len(doc)):
            self._dirty["thumbs"] = True
            self._dirty["bookmarks"] = True
        elif not self._dirty["thumbs"]:
            self.thumbs.refresh_page(self.mw.current_page)
        self._dirty["comments"] = True
        self._dirty["signatures"] = True
        if self.stack.isVisible() and self._current and self._dirty[self._current]:
            self._rebuild(self._current)
