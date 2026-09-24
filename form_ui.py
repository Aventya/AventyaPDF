"""
Interacción con formularios en el visor (Qt), al estilo de Acrobat:

* campos resaltados (Ver › Resaltar campos de formulario);
* cursor de texto sobre campos de texto y de mano sobre casillas, listas y botones;
* edición en línea sobre el propio campo: Intro confirma, Esc cancela y
  Tab / Mayús+Tab pasan al campo de texto siguiente o anterior;
* casillas y radios con un clic, listas con un menú, botones que ejecutan su
  JavaScript y sus acciones (avisos, enlaces, imprimir, navegar…);
* un solo paso de deshacer por cambio y ninguno si no cambia nada.

La lógica de PDF está en pdf_forms (sin Qt).
"""
from PyQt6.QtCore import QEvent, QObject, Qt, QUrl
from PyQt6.QtGui import QColor, QDesktopServices, QFont, QPen
from PyQt6.QtWidgets import QInputDialog, QLineEdit, QMenu, QMessageBox, QPlainTextEdit

import icons
import pdf_forms

_HIGHLIGHT = QColor(204, 215, 255, 120)


class _EditorFilter(QObject):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller

    def eventFilter(self, obj, event):
        if obj is not self.controller.editor:
            return False
        if event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_Escape:
                self.controller.close_editor(commit=False)
                return True
            if key in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
                back = key == Qt.Key.Key_Backtab or bool(
                    event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
                self.controller.close_editor(commit=True, move=-1 if back else 1)
                return True
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and isinstance(obj, QLineEdit):
                self.controller.close_editor(commit=True)
                return True
        elif event.type() == QEvent.Type.FocusOut:
            self.controller.close_editor(commit=True)
        return False


class FormController:
    def __init__(self, viewer):
        self.viewer = viewer
        self.fields: list[dict] = []
        self.editor = None
        self._editing: dict | None = None
        self._busy = False
        self._filter = _EditorFilter(self)

    @property
    def mw(self):
        return self.viewer.main_window

    # ── estado ─────────────────────────────────────────────────────────── #

    def refresh(self) -> None:
        page = self.viewer.pdf_page
        try:
            self.fields = pdf_forms.field_boxes(page) if page is not None else []
        except Exception:  # noqa: BLE001 — página huérfana tras deshacer
            self.fields = []

    def field_at(self, pdf_pt) -> dict | None:
        for field in self.fields:
            if field["rect"].contains(pdf_pt):
                return field
        return None

    def cursor_for(self, field: dict):
        if field["type"] == pdf_forms.SIGNATURE and not field.get("signed"):
            return Qt.CursorShape.PointingHandCursor
        if field["readonly"]:
            return Qt.CursorShape.ArrowCursor
        if field["type"] == pdf_forms.TEXT:
            return Qt.CursorShape.IBeamCursor
        return Qt.CursorShape.PointingHandCursor

    def highlight_enabled(self) -> bool:
        act = getattr(self.mw, "_act_highlight_fields", None)
        return act.isChecked() if act is not None else True

    def paint(self, painter) -> None:
        if not self.fields:
            return
        if self.highlight_enabled():
            for field in self.fields:
                if not field["readonly"]:
                    painter.fillRect(self.viewer._to_screen_rect(field["rect"]), _HIGHLIGHT)
        if self._editing is not None:
            painter.setPen(QPen(QColor(0, 120, 212), 2))
            painter.drawRect(self.viewer._to_screen_rect(self._editing["rect"]))

    # ── clics ──────────────────────────────────────────────────────────── #

    def click(self, field: dict) -> None:
        if field["type"] == pdf_forms.SIGNATURE:
            if field.get("signed"):
                self.mw.statusBar().showMessage(
                    "Este campo ya está firmado (panel Firmas para comprobarla)")
            else:                                   # (r38) firmar en el recuadro
                self.mw.sign_in_field(field)
            return
        if field["readonly"]:
            self.mw.statusBar().showMessage("Campo de solo lectura")
            return
        kind = field["type"]
        if kind == pdf_forms.TEXT:
            self.open_editor(field)
        elif kind in (pdf_forms.CHECKBOX, pdf_forms.RADIO):
            self._apply("Rellenar formulario",
                        lambda doc, page: (True, pdf_forms.toggle(doc, page, field["xref"])))
        elif kind in (pdf_forms.COMBOBOX, pdf_forms.LISTBOX):
            self._choose(field)
        elif kind == pdf_forms.BUTTON:
            self._apply(f"Botón «{field['label']}»",
                        lambda doc, page: (True, pdf_forms.press(doc, page, field["xref"])))

    def _apply(self, label: str, fn) -> bool:
        """Ejecuta un cambio de formulario con un punto de deshacer, que se
        descarta si ningún valor ha cambiado (p. ej. un botón que solo avisa)."""
        mw, page = self.mw, self.viewer.pdf_page
        if mw is None or mw.doc is None or page is None:
            return False
        doc = mw.doc
        before = pdf_forms.values(doc)
        mw.checkpoint(label)
        ok, events = fn(doc, page)
        if pdf_forms.values(doc) != before:
            mw.mark_modified()
            mw.render_page(keep_selection=True)
        else:
            mw._history.discard_last()
            mw._update_actions()
            self.refresh()
            self.viewer.update()
        self.handle_events(events)
        return ok

    def _choose(self, field: dict) -> None:
        menu = QMenu(self.viewer)
        for export, shown in field["choices"]:
            act = menu.addAction(shown)
            act.setCheckable(True)
            act.setChecked(field["value"] in (export, shown))
            act.setData(export)
        other = menu.addAction("Escribir otro valor…") if field["editable"] else None
        where = self.viewer._to_screen_rect(field["rect"]).bottomLeft()
        chosen = menu.exec(self.viewer.mapToGlobal(where))
        if chosen is None:
            return
        if chosen is other:
            value, ok = QInputDialog.getText(self.viewer, "Rellenar campo",
                                             field["label"] + ":", text=field["value"])
            if not ok:
                return
        else:
            value = chosen.data()
        if value != field["value"]:
            self._apply("Rellenar formulario",
                        lambda doc, page: pdf_forms.choose(doc, page, field["xref"], value))

    # ── edición en línea ───────────────────────────────────────────────── #

    def open_editor(self, field: dict) -> None:
        self.close_editor(commit=True)
        viewer = self.viewer
        rect = viewer._to_screen_rect(field["rect"])
        editor = QPlainTextEdit(viewer) if field["multiline"] else QLineEdit(viewer)
        size = field["fontsize"] or field["rect"].height * (0.5 if field["multiline"] else 0.62)
        font = QFont(icons.noto_family("sans"))   # (r40) fuente base de la app
        font.setPixelSize(max(8, int(size * viewer.scale_factor)))
        editor.setFont(font)
        if field["multiline"]:
            editor.setPlainText(field["value"])
            editor.selectAll()
        else:
            editor.setText(field["value"])
            if field["maxlen"]:
                editor.setMaxLength(field["maxlen"])
            if field["password"]:
                editor.setEchoMode(QLineEdit.EchoMode.Password)
            editor.selectAll()
        editor.setStyleSheet("background: #FFFFFF; color: #201F1E; border: 2px solid #0078D4;"
                             " border-radius: 0; padding: 0 2px;")
        editor.setGeometry(rect)
        editor.installEventFilter(self._filter)
        self.editor, self._editing = editor, field
        editor.show()
        editor.setFocus()
        viewer.update()

    def close_editor(self, commit: bool = True, move: int = 0) -> None:
        if self.editor is None or self._busy:
            return
        self._busy = True
        editor, field = self.editor, self._editing
        self.editor = self._editing = None
        text = editor.toPlainText() if isinstance(editor, QPlainTextEdit) else editor.text()
        editor.removeEventFilter(self._filter)
        editor.hide()
        editor.deleteLater()
        try:
            if commit and text != field["value"]:
                self._apply("Rellenar formulario",
                            lambda doc, page: pdf_forms.set_text(doc, page, field["xref"], text))
        finally:
            self._busy = False
        if move:
            order = [f for f in self.fields if f["type"] == pdf_forms.TEXT and not f["readonly"]]
            idx = next((i for i, f in enumerate(order) if f["xref"] == field["xref"]), -1)
            if order and idx >= 0:
                self.open_editor(order[(idx + move) % len(order)])
                return
        self.viewer.update()

    # ── lo que pide el documento ───────────────────────────────────────── #

    def handle_events(self, events) -> None:
        mw = self.mw
        for event in events:
            kind, text = event.kind, event.text
            if kind == "alert":
                QMessageBox.information(mw, "Mensaje del documento", text)
            elif kind == "response":
                QMessageBox.information(mw, "Pregunta del documento",
                                        f"{text}\n\n(AventyaPDF no permite responder "
                                        "preguntas de formularios.)")
            elif kind == "url" and text:
                r = QMessageBox.question(mw, "Abrir enlace",
                                         f"El documento quiere abrir:\n{text}\n\n¿Abrirlo?")
                if r == QMessageBox.StandardButton.Yes:
                    QDesktopServices.openUrl(QUrl(text))
            elif kind == "mail":
                QDesktopServices.openUrl(QUrl("mailto:" + text))
            elif kind == "print" or (kind in ("named", "menu") and text == "Print"):
                mw.print_pdf()
            elif kind in ("named", "menu"):
                action = {"NextPage": mw.next_page, "PrevPage": mw.prev_page,
                          "FirstPage": mw.first_page, "LastPage": mw.last_page,
                          "SaveAs": mw.save_pdf_as}.get(text)
                if action is not None:
                    action()
            elif kind == "goto":
                try:
                    mw.go_to_page(int(text))
                except (TypeError, ValueError):
                    pass
            elif kind == "submit":
                QMessageBox.information(
                    mw, "Enviar formulario",
                    f"El formulario pide enviarse a:\n{text or '(destino no indicado)'}\n\n"
                    "AventyaPDF no envía formularios por Internet: guarda el PDF "
                    "relleno y envíalo tú.")
            elif kind == "launch":
                QMessageBox.warning(mw, "Abrir archivo",
                                    f"Por seguridad no se abren archivos desde un formulario:\n{text}")
