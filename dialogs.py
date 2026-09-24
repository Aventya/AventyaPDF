"""
dialogs.py
Diálogos de las herramientas de documento: texto multilínea, rango de
páginas, marca de agua, encabezado/pie/Bates, seguridad, propiedades,
opciones de firma, exportación a imágenes y atajos de teclado.
Todos devuelven valores planos (dict / listas); la aplicación los ejecuta
con `doc_tools` y gestiona deshacer.
"""
import os

import fitz
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPlainTextEdit, QPushButton, QSpinBox, QTabWidget, QVBoxLayout,
    QWidget,
)

import color_picker
import doc_tools

_SETTINGS = ("aventyapdf", "config")


def _button_box(dlg: QDialog, ok_text: str = "Aceptar") -> QDialogButtonBox:
    bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                          QDialogButtonBox.StandardButton.Cancel)
    bb.button(QDialogButtonBox.StandardButton.Ok).setText(ok_text)
    bb.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
    bb.accepted.connect(dlg.accept)
    bb.rejected.connect(dlg.reject)
    return bb


class ColorButton(QPushButton):
    """Muestra y edita un color como tupla RGB 0–1 (formato PyMuPDF)."""

    def __init__(self, color: tuple = (0, 0, 0), parent=None,
                 opacity: float | None = None, titulo: str = "Color"):
        super().__init__(parent)
        self.setFixedSize(40, 26)
        self._color = tuple(color)
        self._opacity = opacity              # (r41) None = sin transparencia
        self._titulo = titulo
        self._paint()
        self.clicked.connect(self._pick)

    def _paint(self):
        r, g, b = (int(c * 255) for c in self._color)
        self.setStyleSheet(f"QPushButton {{ background: rgb({r},{g},{b});"
                           " border: 1px solid #8A8886; border-radius: 4px; }")

    def _pick(self):
        elegido = color_picker.choose(self, self._color, self._opacity, self._titulo)
        if elegido:
            self._color, opacidad = elegido
            if opacidad is not None:
                self._opacity = opacidad
            self._paint()

    @property
    def opacity(self) -> float | None:
        """Opacidad elegida en la misma tabla (None si la herramienta no la usa)."""
        return self._opacity

    @property
    def color(self) -> tuple:
        return self._color


# ── Rango de páginas ─────────────────────────────────────────────────────── #

def _range_hint(page_count: int) -> str:
    return f"Ej.: 1-3, 5, 8-   ·   vacío = todas ({page_count} páginas)"


def ask_page_range(parent, title: str, page_count: int, default: str = "") -> list[int] | None:
    dlg = QDialog(parent)
    dlg.setWindowTitle(title)
    lay = QVBoxLayout(dlg)
    lay.addWidget(QLabel("Páginas:"))
    edit = QLineEdit(default)
    lay.addWidget(edit)
    hint = QLabel(_range_hint(page_count))
    hint.setStyleSheet("color:#8A8886;")
    lay.addWidget(hint)
    lay.addWidget(_button_box(dlg))
    while dlg.exec() == QDialog.DialogCode.Accepted:
        try:
            return doc_tools.parse_page_range(edit.text(), page_count)
        except ValueError as e:
            QMessageBox.warning(parent, title, str(e))
    return None


class _RangeMixin:
    def _add_range_row(self, form: QFormLayout, page_count: int, default: str = ""):
        self._page_count = page_count
        self._range = QLineEdit(default)
        self._range.setPlaceholderText(_range_hint(page_count))
        form.addRow("Páginas:", self._range)

    def _pages(self) -> list[int] | None:
        try:
            return doc_tools.parse_page_range(self._range.text(), self._page_count)
        except ValueError as e:
            QMessageBox.warning(self, self.windowTitle(), str(e))
            return None

    def accept(self):
        if self._pages() is not None:
            super().accept()


# ── Marca de agua ─────────────────────────────────────────────────────────── #

class WatermarkDialog(_RangeMixin, QDialog):
    def __init__(self, parent, page_count: int):
        super().__init__(parent)
        self.setWindowTitle("Añadir marca de agua")
        form = QFormLayout(self)
        self._text = QLineEdit("CONFIDENCIAL")
        form.addRow("Texto:", self._text)
        self._size = QSpinBox(); self._size.setRange(8, 250); self._size.setValue(64)
        form.addRow("Tamaño (pt):", self._size)
        # (r41) El color y la opacidad se eligen juntos, en la tabla común.
        self._color = ColorButton((0.75, 0.1, 0.1), opacity=0.25,
                                  titulo="Color de la marca de agua")
        form.addRow("Color y opacidad:", self._color)
        self._angle = QSpinBox(); self._angle.setRange(-180, 180); self._angle.setValue(45)
        self._angle.setSuffix("°")
        form.addRow("Ángulo:", self._angle)
        self._add_range_row(form, page_count)
        form.addRow(_button_box(self, "Aplicar"))

    def accept(self):
        if not self._text.text().strip():
            QMessageBox.warning(self, self.windowTitle(), "Escribe el texto de la marca de agua.")
            return
        super().accept()

    def values(self) -> dict:
        return dict(text=self._text.text(), fontsize=self._size.value(),
                    color=self._color.color, opacity=self._color.opacity,
                    angle=self._angle.value(), pages=self._pages())


# ── Encabezado, pie y numeración Bates ───────────────────────────────────── #

class HeaderFooterDialog(_RangeMixin, QDialog):
    def __init__(self, parent, page_count: int):
        super().__init__(parent)
        self.setWindowTitle("Encabezado, pie de página y numeración")
        self.resize(620, 0)
        lay = QVBoxLayout(self)

        grid_box = QGroupBox("Contenido")
        grid = QGridLayout(grid_box)
        for c, name in enumerate(("Izquierda", "Centro", "Derecha")):
            lbl = QLabel(name); lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(lbl, 0, c + 1)
        self._slots = {}
        for r, (prefix, name) in enumerate((("h", "Encabezado"), ("f", "Pie"))):
            grid.addWidget(QLabel(name), r + 1, 0)
            for c, pos in enumerate("lcr"):
                e = QLineEdit()
                self._slots[prefix + pos] = e
                grid.addWidget(e, r + 1, c + 1)
        self._slots["fc"].setText("Página {n} de {total}")
        lay.addWidget(grid_box)
        tokens = QLabel("Variables: {n} página · {total} total · {fecha} hoy · {bates} número Bates")
        tokens.setStyleSheet("color:#605E5C;")
        lay.addWidget(tokens)

        form = QFormLayout()
        self._size = QSpinBox(); self._size.setRange(5, 48); self._size.setValue(9)
        form.addRow("Tamaño (pt):", self._size)
        self._color = ColorButton((0.2, 0.2, 0.2))
        form.addRow("Color:", self._color)
        self._margin = QSpinBox(); self._margin.setRange(6, 144); self._margin.setValue(28)
        self._margin.setSuffix(" pt")
        form.addRow("Margen:", self._margin)
        bates = QHBoxLayout()
        self._bprefix = QLineEdit(); self._bprefix.setPlaceholderText("Prefijo (ej. EXP-)")
        self._bstart = QSpinBox(); self._bstart.setRange(0, 99_999_999); self._bstart.setValue(1)
        self._bdigits = QSpinBox(); self._bdigits.setRange(1, 12); self._bdigits.setValue(6)
        bates.addWidget(self._bprefix); bates.addWidget(QLabel("Inicio:"))
        bates.addWidget(self._bstart); bates.addWidget(QLabel("Dígitos:"))
        bates.addWidget(self._bdigits)
        form.addRow("Bates:", bates)
        self._add_range_row(form, page_count)
        lay.addLayout(form)
        lay.addWidget(_button_box(self, "Aplicar"))

    def values(self) -> dict:
        spec = {k: e.text() for k, e in self._slots.items()}
        spec.update(fontsize=self._size.value(), color=self._color.color,
                    margin=self._margin.value(), bates_prefix=self._bprefix.text(),
                    bates_start=self._bstart.value(), bates_digits=self._bdigits.value())
        return dict(spec=spec, pages=self._pages())


# ── Seguridad ─────────────────────────────────────────────────────────────── #

class SecurityDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Proteger con contraseña")
        lay = QVBoxLayout(self)

        box_open = QGroupBox("Contraseña para abrir el documento (opcional)")
        f1 = QFormLayout(box_open)
        self._user = QLineEdit(); self._user.setEchoMode(QLineEdit.EchoMode.Password)
        self._user2 = QLineEdit(); self._user2.setEchoMode(QLineEdit.EchoMode.Password)
        f1.addRow("Contraseña:", self._user)
        f1.addRow("Repetir:", self._user2)
        lay.addWidget(box_open)

        box_perm = QGroupBox("Restricciones (requieren contraseña de permisos)")
        f2 = QFormLayout(box_perm)
        self._owner = QLineEdit(); self._owner.setEchoMode(QLineEdit.EchoMode.Password)
        f2.addRow("Contraseña de permisos:", self._owner)
        self._p_print = QCheckBox("Permitir imprimir"); self._p_print.setChecked(True)
        self._p_copy = QCheckBox("Permitir copiar texto e imágenes"); self._p_copy.setChecked(True)
        self._p_modify = QCheckBox("Permitir modificar el documento"); self._p_modify.setChecked(True)
        self._p_annot = QCheckBox("Permitir comentarios y rellenar formularios"); self._p_annot.setChecked(True)
        for cb in (self._p_print, self._p_copy, self._p_modify, self._p_annot):
            f2.addRow(cb)
        lay.addWidget(box_perm)

        note = QLabel("Cifrado AES de 256 bits. Se aplica al guardar el documento.")
        note.setStyleSheet("color:#605E5C;")
        lay.addWidget(note)
        lay.addWidget(_button_box(self, "Aplicar"))

    def _restricted(self) -> bool:
        return not all(cb.isChecked() for cb in
                       (self._p_print, self._p_copy, self._p_modify, self._p_annot))

    def accept(self):
        if self._user.text() != self._user2.text():
            QMessageBox.warning(self, self.windowTitle(), "Las contraseñas de apertura no coinciden.")
            return
        if not self._user.text() and not self._owner.text():
            QMessageBox.warning(self, self.windowTitle(), "Indica al menos una contraseña.")
            return
        if self._restricted() and not self._owner.text():
            QMessageBox.warning(self, self.windowTitle(),
                                "Las restricciones necesitan una contraseña de permisos.")
            return
        if self._owner.text() and self._owner.text() == self._user.text():
            QMessageBox.warning(self, self.windowTitle(),
                                "La contraseña de permisos debe ser distinta de la de apertura.")
            return
        super().accept()

    def values(self) -> dict:
        perms = fitz.PDF_PERM_ACCESSIBILITY
        if self._p_print.isChecked():
            perms |= fitz.PDF_PERM_PRINT | fitz.PDF_PERM_PRINT_HQ
        if self._p_copy.isChecked():
            perms |= fitz.PDF_PERM_COPY
        if self._p_modify.isChecked():
            perms |= fitz.PDF_PERM_MODIFY | fitz.PDF_PERM_ASSEMBLE
        if self._p_annot.isChecked():
            perms |= fitz.PDF_PERM_ANNOTATE | fitz.PDF_PERM_FORM
        owner = self._owner.text() or self._user.text()
        return dict(encryption=fitz.PDF_ENCRYPT_AES_256, user_pw=self._user.text(),
                    owner_pw=owner, permissions=perms)


# ── Propiedades del documento ────────────────────────────────────────────── #

class PropertiesDialog(QDialog):
    def __init__(self, parent, doc: fitz.Document, path: str, n_signatures: int):
        super().__init__(parent)
        self.setWindowTitle("Propiedades del documento")
        self.resize(560, 460)
        lay = QVBoxLayout(self)
        tabs = QTabWidget()
        lay.addWidget(tabs)

        meta = doc.metadata or {}
        desc = QWidget(); f = QFormLayout(desc)
        self._edits = {}
        for key, label in doc_tools.METADATA_FIELDS:
            e = QLineEdit(meta.get(key) or "")
            self._edits[key] = e
            f.addRow(label + ":", e)
        tabs.addTab(desc, "Descripción")

        info = QWidget(); g = QFormLayout(info)
        size = ""
        if path and os.path.exists(path):
            size = f"{os.path.getsize(path) / 1024:,.1f} KB".replace(",", ".")
        p0 = doc[0].rect if len(doc) else fitz.Rect()
        fonts = set()
        for pno in range(min(len(doc), 50)):
            for fnt in doc[pno].get_fonts():
                if fnt[3]:
                    fonts.add(fnt[3].split("+")[-1])
        rows = [
            ("Archivo", path or "(sin guardar)"),
            ("Tamaño", size or "—"),
            ("Páginas", str(len(doc))),
            ("Tamaño de página", f"{p0.width / 72 * 25.4:.0f} × {p0.height / 72 * 25.4:.0f} mm"),
            ("Versión PDF", meta.get("format") or "—"),
            ("Cifrado", meta.get("encryption") or "No"),
            ("Formulario", "Sí" if doc.is_form_pdf else "No"),
            ("Firmas digitales", str(n_signatures)),
            ("Creado", meta.get("creationDate") or "—"),
            ("Modificado", meta.get("modDate") or "—"),
        ]
        for label, value in rows:
            v = QLabel(value); v.setWordWrap(True)
            v.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            g.addRow(label + ":", v)
        fl = QPlainTextEdit("\n".join(sorted(fonts)) or "(ninguna)")
        fl.setReadOnly(True); fl.setMaximumHeight(110)
        g.addRow("Fuentes:", fl)
        tabs.addTab(info, "Información")

        lay.addWidget(_button_box(self, "Guardar propiedades"))

    def metadata(self) -> dict:
        return {k: e.text() for k, e in self._edits.items()}


# ── Opciones de firma ─────────────────────────────────────────────────────── #

class SignOptionsDialog(QDialog):
    """Motivo, lugar, contacto, sellado de tiempo y certificación. Recuerda
    los últimos valores en QSettings."""

    def __init__(self, parent, has_signatures: bool, tsa_presets: list[str],
                 ok_text: str = "Firmar"):
        super().__init__(parent)
        self.setWindowTitle("Opciones de firma")
        self.resize(480, 0)
        s = QSettings(*_SETTINGS)
        form = QFormLayout(self)

        self._reason = QComboBox(); self._reason.setEditable(True)
        self._reason.addItems(["", "Aprobación", "Conformidad", "He revisado este documento",
                               "Soy el autor de este documento"])
        self._reason.setCurrentText(s.value("signing/reason", ""))
        form.addRow("Motivo:", self._reason)
        self._location = QLineEdit(s.value("signing/location", ""))
        form.addRow("Lugar:", self._location)
        self._contact = QLineEdit(s.value("signing/contact", ""))
        form.addRow("Contacto:", self._contact)

        self._tsa = QCheckBox("Añadir sello de tiempo cualificado (PAdES-B-T)")
        self._tsa.setChecked(s.value("signing/tsa_on", "false") == "true")
        form.addRow(self._tsa)
        self._tsa_url = QComboBox(); self._tsa_url.setEditable(True)
        self._tsa_url.addItems(tsa_presets)
        self._tsa_url.setCurrentText(s.value("signing/tsa_url", tsa_presets[0]))
        self._tsa_url.setEnabled(self._tsa.isChecked())
        self._tsa.toggled.connect(self._tsa_url.setEnabled)
        form.addRow("Servidor TSA:", self._tsa_url)

        self._certify = QCheckBox("Certificar documento (solo permitirá rellenar formularios y firmar)")
        self._certify.setEnabled(not has_signatures)
        if has_signatures:
            self._certify.setToolTip("Solo la primera firma de un documento puede certificarlo.")
        form.addRow(self._certify)

        self._remember = QCheckBox("No volver a preguntar (cambiar en Firma › Opciones de firma…)")
        self._remember.setChecked(s.value("signing/skip_dialog", "false") == "true")
        form.addRow(self._remember)
        form.addRow(_button_box(self, ok_text))

    def accept(self):
        s = QSettings(*_SETTINGS)
        s.setValue("signing/reason", self._reason.currentText())
        s.setValue("signing/location", self._location.text())
        s.setValue("signing/contact", self._contact.text())
        s.setValue("signing/tsa_on", "true" if self._tsa.isChecked() else "false")
        s.setValue("signing/tsa_url", self._tsa_url.currentText())
        s.setValue("signing/skip_dialog", "true" if self._remember.isChecked() else "false")
        s.sync()
        super().accept()

    def values(self) -> dict:
        return SignOptionsDialog.saved(certify=self._certify.isChecked())

    @staticmethod
    def saved(certify: bool = False) -> dict:
        s = QSettings(*_SETTINGS)
        return dict(
            reason=s.value("signing/reason", ""),
            location=s.value("signing/location", ""),
            contact=s.value("signing/contact", ""),
            tsa_url=s.value("signing/tsa_url", "") if s.value("signing/tsa_on", "false") == "true" else "",
            certify=certify,
        )

    @staticmethod
    def skip_requested() -> bool:
        return QSettings(*_SETTINGS).value("signing/skip_dialog", "false") == "true"


# ── Exportar como imágenes ───────────────────────────────────────────────── #

class ExportImagesDialog(_RangeMixin, QDialog):
    def __init__(self, parent, page_count: int, current_page: int):
        super().__init__(parent)
        self.setWindowTitle("Exportar páginas como imágenes")
        form = QFormLayout(self)
        self._fmt = QComboBox(); self._fmt.addItems(["PNG", "JPG"])
        form.addRow("Formato:", self._fmt)
        self._dpi = QComboBox(); self._dpi.addItems(["72", "96", "150", "200", "300", "600"])
        self._dpi.setCurrentText("150")
        form.addRow("Resolución (ppp):", self._dpi)
        self._add_range_row(form, page_count, "")
        form.addRow(_button_box(self, "Exportar…"))

    def values(self) -> dict:
        return dict(fmt=self._fmt.currentText().lower(), dpi=int(self._dpi.currentText()),
                    pages=self._pages())


# ── Atajos de teclado ────────────────────────────────────────────────────── #

SHORTCUTS = [
    ("Ctrl+O", "Abrir"), ("Ctrl+S", "Guardar"), ("Ctrl+Mayús+S", "Guardar como"),
    ("Ctrl+P", "Imprimir"), ("Ctrl+W", "Cerrar documento"),
    ("Ctrl+Tab / Ctrl+Mayús+Tab", "Documento abierto siguiente / anterior"),
    ("Ctrl+Z / Ctrl+Y", "Deshacer / Rehacer"), ("Ctrl+F", "Buscar"),
    ("F3 / Mayús+F3", "Coincidencia siguiente / anterior"),
    ("Ctrl+C", "Copiar texto seleccionado"),
    ("Ctrl+Rueda, Ctrl + / Ctrl −", "Zoom"), ("Ctrl+0", "Zoom 100 %"),
    ("Ctrl+1 / Ctrl+2", "Ajustar ancho / página"),
    ("AvPág / RePág", "Página siguiente / anterior"),
    ("Rueda en el borde de la página", "Pasar de página"),
    ("Inicio / Fin", "Primera / última página"), ("Ctrl+G", "Ir a página"),
    ("F4", "Mostrar u ocultar panel lateral"), ("Supr", "Eliminar anotación"),
    ("Esc", "Herramienta de selección"),
    ("V · T · N · H · R · E", "Selección · Texto · Nota · Resaltar, subrayar o tachar · Rectángulo · Emoji"),
    ("C", "Editar el texto y las imágenes del PDF"),
]


# ── Reconocer texto (OCR) ─────────────────────────────────────────────────── #

OCR_LANGUAGE_NAMES = {
    "spa": "Español", "spa+eng": "Español e inglés", "eng": "Inglés", "cat": "Catalán",
    "glg": "Gallego", "eus": "Euskera", "por": "Portugués", "fra": "Francés",
    "deu": "Alemán", "ita": "Italiano",
}


class OcrDialog(QDialog):
    """Idioma, páginas y orientación para `pdf_ocr` (se recuerdan)."""

    def __init__(self, parent, languages: list[str], pages_without_text: int, page_count: int):
        super().__init__(parent)
        self.setWindowTitle("Reconocer texto (OCR)")
        self.setMinimumWidth(460)
        s = QSettings(*_SETTINGS)
        form = QFormLayout()
        self._lang = QComboBox()
        for code in languages:
            self._lang.addItem(OCR_LANGUAGE_NAMES.get(code, code), code)
        self._lang.setCurrentIndex(max(0, self._lang.findData(s.value("ocr/lang", languages[0]))))
        form.addRow("Idioma del documento:", self._lang)
        self._scope = QComboBox()
        self._scope.addItem(f"Todas las páginas ({page_count}) — recomendado", "all")
        self._scope.addItem(f"Solo las páginas sin texto ({pages_without_text})", "empty")
        form.addRow("Páginas:", self._scope)
        self._orientation = QCheckBox("Detectar la orientación de cada página")
        self._orientation.setChecked(s.value("ocr/orientation", True, type=bool))
        form.addRow("", self._orientation)
        hint = QLabel("«Todas las páginas» reconoce también el texto de imágenes, escaneos, sellos "
                      "o texto convertido en dibujo dentro de páginas que ya tienen texto.\n"
                      "El texto se añade como capa invisible: la página no cambia de aspecto, "
                      "se puede buscar y seleccionar, y la operación se puede deshacer.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#605E5C;")
        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(hint)
        lay.addWidget(_button_box(self, "Reconocer"))

    def values(self) -> dict:
        v = dict(lang=self._lang.currentData(),
                 all_pages=self._scope.currentData() == "all",
                 orientation=self._orientation.isChecked())
        s = QSettings(*_SETTINGS)
        s.setValue("ocr/lang", v["lang"])
        s.setValue("ocr/orientation", v["orientation"])
        return v


def show_shortcuts(parent):
    rows = "".join(f"<tr><td style='padding:3px 16px 3px 0'><b>{k}</b></td><td>{v}</td></tr>"
                   for k, v in SHORTCUTS)
    QMessageBox.information(parent, "Atajos de teclado", f"<table>{rows}</table>")
