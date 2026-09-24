"""
Formularios PDF (AcroForm) con el motor JavaScript de MuPDF, sin Qt.

* Rellenar: pdf_set_field_value con eventos → formato, validación y cálculos
  (AFSimple_Calculate, scripts propios…) como en Acrobat.
* Casillas y radios: eventos de ratón + pdf_toggle_widget. Los radios con el
  mismo nombre y sin /Parent (como los crea PyMuPDF) se desmarcan a mano.
* Botones: eventos de ratón (enter/down/up/exit). MuPDF ejecuta el JavaScript y
  ResetForm; las demás acciones (URI, Named, GoTo, SubmitForm, Launch) se
  devuelven como FormEvent para que las ejecute la aplicación.
* app.alert, app.response, app.launchURL, app.mailMsg, app.execMenuItem,
  this.print, this.mailDoc y this.submitForm son nativos de MuPDF: no avisan a
  nadie (su callback no es accesible desde Python) y no se pueden sustituir
  (propiedades no configurables). Mientras dura el evento, el JavaScript de
  las acciones implicadas se envuelve en «with (__agpdf.scope) {…}», con esas
  funciones capturadas, y después se restaura tal cual: los avisos llegan a la
  app como FormEvent y el script sigue hasta el final.
* Solo se ejecuta el JavaScript que dispara el usuario (nunca al abrir).
"""
import json
from contextlib import contextmanager
from dataclasses import dataclass

import fitz
from pymupdf import mupdf

TEXT = fitz.PDF_WIDGET_TYPE_TEXT
CHECKBOX = fitz.PDF_WIDGET_TYPE_CHECKBOX
RADIO = fitz.PDF_WIDGET_TYPE_RADIOBUTTON
COMBOBOX = fitz.PDF_WIDGET_TYPE_COMBOBOX
LISTBOX = fitz.PDF_WIDGET_TYPE_LISTBOX
BUTTON = fitz.PDF_WIDGET_TYPE_BUTTON
SIGNATURE = fitz.PDF_WIDGET_TYPE_SIGNATURE

READ_ONLY = fitz.PDF_FIELD_IS_READ_ONLY
MULTILINE = fitz.PDF_TX_FIELD_IS_MULTILINE
PASSWORD = getattr(fitz, "PDF_TX_FIELD_IS_PASSWORD", 1 << 13)
EDITABLE_CHOICE = getattr(fitz, "PDF_CH_FIELD_IS_EDIT", 1 << 18)

_SCOPE_JS = r"""
if (typeof __agpdf === "undefined") {
  var __agpdf = { events: [] };
  __agpdf.push = function (k, t) {
    __agpdf.events.push([k, (t === undefined || t === null) ? "" : String(t)]);
  };
  __agpdf.msg = function (a) { return (a !== null && typeof a === "object") ? a.cMsg : a; };
  __agpdf.def = function (o, k, f) {
    Object.defineProperty(o, k, {value: f, writable: true, configurable: true});
  };
  __agpdf.app = Object.create(app);
  __agpdf.def(__agpdf.app, "alert", function (a) { __agpdf.push("alert", __agpdf.msg(a)); return 1; });
  __agpdf.def(__agpdf.app, "beep", function () {});
  __agpdf.def(__agpdf.app, "response", function (a) { __agpdf.push("response", __agpdf.msg(a)); return null; });
  __agpdf.def(__agpdf.app, "launchURL", function (u) { __agpdf.push("url", u); });
  __agpdf.def(__agpdf.app, "mailMsg", function (o) { __agpdf.push("mail", (o && o.cTo) || ""); });
  __agpdf.def(__agpdf.app, "execMenuItem", function (m) { __agpdf.push("menu", m); });
  __agpdf.scope = {
    app: __agpdf.app,
    __agpdf_print: function () { __agpdf.push("print", ""); },
    __agpdf_mail: function (o) { __agpdf.push("mail", (o && o.cTo) || ""); },
    __agpdf_submit: function (o) { __agpdf.push("submit", (o && o.cURL) || o || ""); }
  };
}
"ok"
"""
_POLL_JS = 'var __agpdf_r = JSON.stringify(__agpdf.events); __agpdf.events = []; __agpdf_r'


@dataclass
class FormEvent:
    """Algo que el documento pide a la aplicación: alert, response, url, mail,
    print, submit, menu, named, goto (texto = nº de página) o launch."""
    kind: str
    text: str = ""


# ── Acceso a MuPDF ─────────────────────────────────────────────────────── #

def _pdf(doc: fitz.Document):
    return fitz._as_pdf_document(doc)


def _pdf_page(page: fitz.Page):
    return page.this if isinstance(page.this, mupdf.PdfPage) else mupdf.pdf_page_from_fz_page(page.this)


def _pdf_widget(page: fitz.Page, xref: int):
    widget = mupdf.pdf_first_widget(_pdf_page(page))
    while widget.m_internal:
        if mupdf.pdf_to_num(mupdf.pdf_annot_obj(widget)) == xref:
            return widget
        widget = mupdf.pdf_next_widget(widget)
    return None


def enable_js(doc: fitz.Document) -> bool:
    """Activa el JavaScript de MuPDF y el ámbito de captura (idempotente)."""
    try:
        pdf = _pdf(doc)
        if not mupdf.pdf_js_supported(pdf):
            mupdf.pdf_enable_js(pdf)
        if not mupdf.pdf_js_supported(pdf) or not pdf.m_internal.js:
            return False
        mupdf.ll_pdf_js_execute(pdf.m_internal.js, "agpdf-scope", _SCOPE_JS)
        return True
    except Exception:  # noqa: BLE001 — MuPDF sin JavaScript
        return False


def _poll(doc: fitz.Document) -> list[FormEvent]:
    try:
        js = _pdf(doc).m_internal.js
        raw = mupdf.ll_pdf_js_execute(js, "agpdf-poll", _POLL_JS) if js else ""
        items = json.loads(json.loads(raw)) if raw else []
    except Exception:  # noqa: BLE001
        return []
    return [FormEvent(kind, text) for kind, text in items]


# ── Envolver temporalmente el JavaScript de las acciones ──────────────── #

def _key(doc, xref, key):
    try:
        return doc.xref_get_key(xref, key)
    except Exception:  # noqa: BLE001
        return ("null", "null")


def _holders(doc, xref):
    """El widget y sus campos padre (las acciones AA pueden estar en el campo)."""
    seen, current = set(), xref
    while current and current not in seen and len(seen) < 16:
        seen.add(current)
        yield current
        kind, value = _key(doc, current, "Parent")
        current = int(value.split()[0]) if kind == "xref" else 0


def _js_locations(doc, xref, keys):
    """(objeto, clave) del texto JS de cada acción JavaScript en `keys`."""
    for key in keys:
        for holder in _holders(doc, xref):
            kind, value = _key(doc, holder, key)
            if kind == "xref":
                target, prefix = int(value.split()[0]), ""
            elif kind == "dict":
                target, prefix = holder, key + "/"
            else:
                continue
            if _key(doc, target, prefix + "S")[1] == "/JavaScript":
                yield target, prefix + "JS"
            break


def _wrap(code: str) -> str:
    code = (code.replace("this.print(", "__agpdf_print(")
                .replace("this.mailDoc(", "__agpdf_mail(")
                .replace("this.submitForm(", "__agpdf_submit("))
    return "with (__agpdf.scope) {\n" + code + "\n}"


@contextmanager
def _captured(doc, xref, keys, active: bool):
    changed = []
    if active:
        for target, jskey in _js_locations(doc, xref, keys):
            kind, value = _key(doc, target, jskey)
            if kind == "xref":
                code = (doc.xref_stream(int(value.split()[0])) or b"").decode("utf-8", "replace")
                restore = value
            elif kind == "string":
                code, restore = value, fitz.get_pdf_str(value)
            else:
                continue
            doc.xref_set_key(target, jskey, fitz.get_pdf_str(_wrap(code)))
            changed.append((target, jskey, restore))
    try:
        yield
    finally:
        for target, jskey, restore in reversed(changed):
            doc.xref_set_key(target, jskey, restore)


# ── Acciones que ejecuta la aplicación ────────────────────────────────── #

def _string(doc, xref, key) -> str:
    kind, value = _key(doc, xref, key)
    if kind == "string":
        return value
    if kind in ("xref", "dict"):
        return _key(doc, xref, key + "/F")[1] if kind == "dict" else \
            _key(doc, int(value.split()[0]), "F")[1]
    return ""


def _app_actions(doc, holder, key, depth=0) -> list[FormEvent]:
    kind, value = _key(doc, holder, key)
    if kind == "xref":
        target, prefix = int(value.split()[0]), ""
    elif kind == "dict":
        target, prefix = holder, key + "/"
    else:
        return []
    kind_s = _key(doc, target, prefix + "S")[1]
    out = []
    if kind_s == "/URI":
        out.append(FormEvent("url", _key(doc, target, prefix + "URI")[1]))
    elif kind_s == "/Named":
        out.append(FormEvent("named", _key(doc, target, prefix + "N")[1].lstrip("/")))
    elif kind_s == "/SubmitForm":
        out.append(FormEvent("submit", _string(doc, target, prefix + "F")))
    elif kind_s == "/Launch":
        out.append(FormEvent("launch", _string(doc, target, prefix + "F")))
    elif kind_s == "/GoTo":
        dest_kind, dest = _key(doc, target, prefix + "D")
        if dest_kind == "array" and " R" in dest:
            page_xref = int(dest.strip("[] ").split()[0])
            pages = {doc.page_xref(i): i for i in range(len(doc))}
            if page_xref in pages:
                out.append(FormEvent("goto", str(pages[page_xref])))
    if depth < 8 and _key(doc, target, prefix + "Next")[0] in ("xref", "dict"):
        out += _app_actions(doc, target, prefix + "Next", depth + 1)
    return out


# ── Operaciones ───────────────────────────────────────────────────────── #

def set_text(doc: fitz.Document, page: fitz.Page, xref: int, value: str) -> tuple[bool, list[FormEvent]]:
    """Rellena un campo de texto o de lista. Devuelve (aceptado, eventos): la
    validación del documento puede rechazar el valor."""
    active = enable_js(doc)
    widget = _pdf_widget(page, xref)
    if widget is None:
        return False, []
    with _captured(doc, xref, ("AA/K", "AA/V", "AA/F"), active):
        ok = mupdf.pdf_set_field_value(_pdf(doc), mupdf.pdf_annot_obj(widget), value, 0)
        mupdf.pdf_update_page(_pdf_page(page))
    return bool(ok), _poll(doc) if active else []


choose = set_text


def toggle(doc: fitz.Document, page: fitz.Page, xref: int) -> list[FormEvent]:
    active = enable_js(doc)
    widget = _pdf_widget(page, xref)
    info = next((w for w in page.widgets() if w.xref == xref), None)
    if widget is None or info is None:
        return []
    field_type, name = info.field_type, info.field_name
    with _captured(doc, xref, ("A", "AA/D", "AA/U", "AA/V"), active):
        mupdf.pdf_annot_event_down(widget)
        mupdf.pdf_toggle_widget(widget)
        mupdf.pdf_annot_event_up(widget)
    now_on = next((w.field_value not in (None, False, "", "Off")
                   for w in page.widgets() if w.xref == xref), False)
    if field_type == RADIO and now_on and _key(doc, xref, "Parent")[0] == "null":
        for other_page in doc:
            for other in other_page.widgets():
                if (other.xref != xref and other.field_type == RADIO and other.field_name == name
                        and other.field_value not in (None, False, "", "Off")
                        and _key(doc, other.xref, "Parent")[0] == "null"):
                    other.field_value = False
                    other.update()
    if active:
        try:
            mupdf.pdf_calculate_form(_pdf(doc))
        except Exception:  # noqa: BLE001
            pass
    mupdf.pdf_update_page(_pdf_page(page))
    return _poll(doc) if active else []


def press(doc: fitz.Document, page: fitz.Page, xref: int) -> list[FormEvent]:
    """Pulsa un botón: ejecuta su JavaScript / ResetForm y devuelve lo que la
    aplicación tiene que hacer (avisos, enlaces, imprimir, navegar…)."""
    active = enable_js(doc)
    widget = _pdf_widget(page, xref)
    if widget is None:
        return []
    with _captured(doc, xref, ("A", "AA/E", "AA/D", "AA/U", "AA/X"), active):
        mupdf.pdf_annot_event_enter(widget)
        mupdf.pdf_annot_event_down(widget)
        mupdf.pdf_annot_event_up(widget)
        mupdf.pdf_annot_event_exit(widget)
    mupdf.pdf_update_page(_pdf_page(page))
    events = _poll(doc) if active else []
    for holder in _holders(doc, xref):
        if _key(doc, holder, "A")[0] != "null":
            events += _app_actions(doc, holder, "A")
            break
    return events


def values(doc: fitz.Document) -> dict[int, object]:
    out = {}
    for page in doc:
        for w in page.widgets():
            out[w.xref] = w.field_value
    return out


def field_boxes(page: fitz.Page) -> list[dict]:
    """Campos de la página con lo que necesita la interfaz.

    (r38) Incluye los **campos de firma**: los vacíos se pulsan para firmar en
    ellos (antes se descartaban y el recuadro de firma de un formulario no hacía
    nada); los ya firmados salen como de solo lectura."""
    out = []
    for w in page.widgets():
        flags = w.field_flags or 0
        if w.field_type == SIGNATURE:
            firmado = bool(page.parent.xref_get_key(w.xref, "V")[0] not in ("null", "unknown"))
            out.append(dict(
                xref=w.xref, rect=fitz.Rect(w.rect), type=SIGNATURE,
                name=w.field_name or "", label=w.field_name or "Firma", tooltip="",
                readonly=firmado, signed=firmado, multiline=False, password=False,
                editable=False, maxlen=0, fontsize=0, value="", choices=[]))
            continue
        choices = []
        for c in (w.choice_values or []):
            if isinstance(c, (list, tuple)):
                choices.append((str(c[0]), str(c[1] if len(c) > 1 else c[0])))
            else:
                choices.append((str(c), str(c)))
        label = w.button_caption if w.field_type == BUTTON and w.button_caption else ""
        tooltip = w.field_label if w.field_label and w.field_label != w.field_name else ""
        out.append(dict(
            xref=w.xref, rect=fitz.Rect(w.rect), type=w.field_type, name=w.field_name or "",
            label=label or tooltip or w.field_name or "Campo", tooltip=tooltip,
            readonly=bool(flags & READ_ONLY),
            multiline=w.field_type == TEXT and bool(flags & MULTILINE),
            password=w.field_type == TEXT and bool(flags & PASSWORD),
            editable=w.field_type == COMBOBOX and bool(flags & EDITABLE_CHOICE),
            maxlen=w.text_maxlen or 0, fontsize=w.text_fontsize or 0,
            value="" if w.field_value in (None, False) else str(w.field_value),
            choices=choices, signed=False))
    return out
