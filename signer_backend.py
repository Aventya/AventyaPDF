import os
import re
import traceback
from dataclasses import dataclass
from io import BytesIO

import fitz
from cryptography.hazmat.primitives.serialization import pkcs12 as crypto_pkcs12
from cryptography.x509 import ObjectIdentifier
from cryptography.x509.oid import NameOID

from pyhanko.sign import signers
from pyhanko.sign.fields import SigSeedSubFilter, SigFieldSpec, MDPPerm
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.pdf_utils.misc import PdfReadError
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.stamp import TextStampStyle
from pyhanko.stamp.text import TextStamp

import doc_tools

# Fondo del sello: PDF vectorial generado desde MOSCA.svg con
# create_signature_background.py (regenerarlo si cambia el SVG).
BACKGROUND_PDF = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "signature_background.pdf")

# Recuadro detrás del logotipo: #D1CCBD con un 75 % de transparencia
# (opacidad 0,25) y esquinas redondeadas de 14 pt (= 14 px al 100 %).
PANEL_RGB = (0xD1, 0xCC, 0xBD)
PANEL_ALPHA = 0.25
PANEL_RADIUS = 14.0

# Margen interno entre el texto y el borde del recuadro: el 10 % del alto,
# y nunca menos de 7 pt (= 7 px al 100 %).
TEXT_MARGIN_MIN = 7.0
TEXT_MARGIN_RATIO = 0.10

# OID para organizationIdentifier (NIF de la organización representada)
_OID_ORG_ID = ObjectIdentifier("2.5.4.97")

# Servidores de sellado de tiempo (RFC 3161) gratuitos y conocidos.
TSA_PRESETS = [
    "http://timestamp.digicert.com",
    "http://timestamp.sectigo.com",
    "https://freetsa.org/tsr",
]


def _clean_id(value: str) -> str:
    """Elimina el prefijo de país (ej. IDCES-, VATES-) de los campos de identidad."""
    m = re.match(r'^[A-Z]{2,6}-(.+)$', value)
    return m.group(1) if m else value


# Identificadores que la FNMT mete en el CN junto al nombre:
#   representante:   «12345678Z NOMBRE APELLIDO1 (R: B12345678)»
#   persona física:  «APELLIDO1 APELLIDO2 NOMBRE - NIF 12345678Z»
_RE_CN_ID_START = re.compile(r"^\s*(?:IDC?ES-)?[XYZ]?\d{7,8}[A-Z]\s+", re.IGNORECASE)
_RE_CN_ID_END = re.compile(r"\s*-\s*(?:NIF:?\s*)?[XYZ]?\d{7,8}[A-Z]\s*$", re.IGNORECASE)
_RE_CN_REPR = re.compile(r"\s*\(\s*R(?:EPR)?\.?\s*:[^)]*\)\s*$", re.IGNORECASE)


def _signer_display_name(given_name: str, surname: str, common_name: str) -> str:
    """Solo nombre y apellidos, sin DNI/NIE ni CIF.
    givenName + surname es lo más fiable (el CN de representante de la FNMT
    solo trae el primer apellido); si no vienen, se limpia el CN."""
    full = " ".join(p.strip() for p in (given_name, surname) if p and p.strip())
    if full:
        return full
    name = _RE_CN_REPR.sub("", common_name or "")
    name = _RE_CN_ID_START.sub("", name)
    name = _RE_CN_ID_END.sub("", name)
    return name.strip() or (common_name or "").strip() or "Firmante desconocido"


def extract_cert_info(pfx_path: str, pfx_password: str) -> dict:
    """
    Extrae del PKCS12 los datos obligatorios para la firma visible:
    nombre completo, NIF del firmante y NIF de la entidad representada.
    """
    with open(pfx_path, "rb") as f:
        pfx_data = f.read()

    passphrase = pfx_password.encode("utf-8") if pfx_password else None
    _, cert, _ = crypto_pkcs12.load_key_and_certificates(pfx_data, passphrase)

    def _get(oid, fallback=""):
        try:
            return cert.subject.get_attributes_for_oid(oid)[0].value
        except Exception:
            return fallback

    name = _signer_display_name(_get(NameOID.GIVEN_NAME), _get(NameOID.SURNAME),
                                _get(NameOID.COMMON_NAME))
    nif_raw = _get(NameOID.SERIAL_NUMBER, "")
    nif = _clean_id(nif_raw) if nif_raw else ""
    org_nif_raw = _get(_OID_ORG_ID, "")
    org_nif = _clean_id(org_nif_raw) if org_nif_raw else _get(NameOID.ORGANIZATION_NAME, "")

    return {"name": name, "nif": nif, "org_nif": org_nif}


class _SpanishCertTextStamp(TextStamp):
    """
    TextStamp sin borde: de fondo, un recuadro semitransparente con esquinas
    redondeadas y el logotipo de signature_background.pdf centrado y con el
    alto del recuadro; encima, el texto.
    """

    def render(self) -> bytes:
        command_stream = [b"q"]
        inner_content = self._render_inner_content()
        command_stream.append(self._draw_panel())
        command_stream.append(self._draw_background())
        if inner_content:
            command_stream.extend(inner_content)
        command_stream.append(b"Q")
        return b" ".join(command_stream)

    def _rounded_box_path(self) -> str:
        """Trayecto del recuadro completo con esquinas redondeadas (sin pintar)."""
        w = float(self.box.width)
        h = float(self.box.height)
        r = max(0.0, min(PANEL_RADIUS, w / 2, h / 2))
        k = r * 0.552285            # aproximación de un cuarto de círculo con Bézier
        return (f"{r:.4f} 0 m {w - r:.4f} 0 l "
                f"{w - r + k:.4f} 0 {w:.4f} {r - k:.4f} {w:.4f} {r:.4f} c "
                f"{w:.4f} {h - r:.4f} l "
                f"{w:.4f} {h - r + k:.4f} {w - r + k:.4f} {h:.4f} {w - r:.4f} {h:.4f} c "
                f"{r:.4f} {h:.4f} l "
                f"{r - k:.4f} {h:.4f} 0 {h - r + k:.4f} 0 {h - r:.4f} c "
                f"0 {r:.4f} l "
                f"0 {r - k:.4f} {r - k:.4f} 0 {r:.4f} 0 c h")

    def _draw_panel(self) -> bytes:
        """Recuadro de color PANEL_RGB, con opacidad PANEL_ALPHA y esquinas
        redondeadas, detrás del logotipo."""
        from pyhanko.pdf_utils.generic import DictionaryObject, FloatObject, NameObject
        self.resources.ext_g_state["/SigPanelGS"] = DictionaryObject({
            NameObject("/Type"): NameObject("/ExtGState"),
            NameObject("/ca"): FloatObject(PANEL_ALPHA),
        })
        r, g, b = (c / 255 for c in PANEL_RGB)
        return (f"q /SigPanelGS gs {r:.6f} {g:.6f} {b:.6f} rg "
                f"{self._rounded_box_path()} f Q").encode()

    def _draw_background(self) -> bytes:
        """Logotipo de fondo como XObject de formulario (vectorial, con sus
        propias transparencias). Escala proporcional SIEMPRE por el alto del
        recuadro y pegado a su lado derecho; lo que sobresale en recuadros estrechos se
        recorta con el mismo contorno redondeado del recuadro de color."""
        if not os.path.isfile(BACKGROUND_PDF):
            print(f"Aviso: no existe {BACKGROUND_PDF}; el sello se crea sin fondo.")
            return b""
        with open(BACKGROUND_PDF, "rb") as fh:
            reader = PdfFileReader(BytesIO(fh.read()))
        xobj = self.writer.import_page_as_xobject(reader, page_ix=0)
        x1, y1, x2, y2 = (float(v) for v in xobj.get_object()["/BBox"])
        bw, bh = abs(x2 - x1), abs(y2 - y1)
        w = float(self.box.width)
        h = float(self.box.height)
        s = h / bh
        tx = w - bw * s - min(x1, x2) * s
        ty = -min(y1, y2) * s
        self.resources.xobject["/SigBackground"] = xobj
        return (f"q {self._rounded_box_path()} W n "
                f"{s:.6f} 0 0 {s:.6f} {tx:.6f} {ty:.6f} cm /SigBackground Do Q").encode()

    # El texto se compone a un cuerpo grande y luego se escala con `cm`: pyHanko
    # escribe `Tf`/`TL` como enteros y redondea el ancho de cada línea, así que
    # a 100 pt el error es menor del 1 %. La fuente es Courier (monoespaciada),
    # cuyo ancho medido por pyHanko es exacto.
    _LAYOUT_FONT_SIZE = 100
    # Hueco bajo la última línea (fracción del cuerpo) para los descendentes.
    _DESCENT = 0.25

    def _text_layout(self):
        from pyhanko.pdf_utils.text import TextBoxStyle, TextBox
        from pyhanko.pdf_utils.layout import AxisAlignment, LayoutError, Margins, SimpleBoxLayoutRule

        _params = self.get_default_text_params()
        if self.text_params:
            _params.update(self.text_params)
        try:
            text = self.style.stamp_text % _params
        except KeyError as e:
            raise LayoutError(f"Stamp text parameter '{e.args[0]}' is missing")

        fs = self._LAYOUT_FONT_SIZE
        text = self._arrange_lines(text.split("\n"))
        # Sin márgenes a los lados: el ancho natural es exactamente el de la
        # línea más larga (pyHanko pone 10 pt por lado si no se indica).
        rule = SimpleBoxLayoutRule(AxisAlignment.ALIGN_MIN, AxisAlignment.ALIGN_MIN,
                                   margins=Margins(0, 0, 0, round(fs * self._DESCENT)))
        self.text_box = tb = TextBox(
            TextBoxStyle(font_size=fs, box_layout_rule=rule),
            writer=self.writer,
            resources=self.resources,
            box=None,
        )
        tb.content = text
        return tb.render()

    # Separador al unir líneas del sello en recuadros anchos y bajos.
    _JOIN = " · "

    def _text_area(self) -> tuple[float, float, float]:
        """(margen, ancho, alto) del hueco para el texto dentro del recuadro.
        Margen = máx(7 pt, 10 % del alto); solo en recuadros diminutos, donde
        no quedaría sitio, se reduce para dejar al menos 1 pt de texto."""
        w = float(self.box.width)
        h = float(self.box.height)
        m = max(TEXT_MARGIN_MIN, TEXT_MARGIN_RATIO * h)
        m = max(0.0, min(m, (min(w, h) - 1) / 2))
        return m, w - 2 * m, h - 2 * m

    def _arrange_lines(self, lines: list[str]) -> str:
        """Reparte las líneas del sello para que, al ajustarlo al ancho del
        recuadro, quepa en alto con la letra más grande posible. En un
        recuadro alto o proporcionado se quedan como están; en uno ancho y
        bajo se unen líneas seguidas con « · », porque si no el alto
        limitaría la escala y el texto no llegaría al ancho. Se prueban todas
        las agrupaciones en orden (el sello tiene 6 líneas como mucho)."""
        _, w, h = self._text_area()
        n = len(lines)
        if n < 2 or w <= 0 or h <= 0:
            return "\n".join(lines)
        best, best_scale = lines, -1.0
        for mask in range(2 ** (n - 1)):              # bit i = unir línea i con la i+1
            grouped, current = [], lines[0]
            for i in range(1, n):
                if mask >> (i - 1) & 1:
                    current += self._JOIN + lines[i]
                else:
                    grouped.append(current)
                    current = lines[i]
            grouped.append(current)
            chars = max(len(g) for g in grouped)       # Courier: todas las letras miden igual
            scale = min(w / max(chars, 1), h / (len(grouped) + self._DESCENT))
            # Con escalas prácticamente iguales, mejor más líneas (lo de siempre).
            if scale > best_scale * 1.02 or (scale >= best_scale * 0.98 and len(grouped) > len(best)):
                best, best_scale = grouped, max(scale, best_scale)
        return "\n".join(best)

    def _render_inner_content(self):
        """Texto con el ancho exacto del hueco interior del recuadro (la línea
        más larga va de margen a margen, `_text_area`) y centrado en vertical. Si a ese ancho no
        cabe en alto, se reduce solo el alto de las letras (el BBox recortaría
        las líneas); `_arrange_lines` ya elige el reparto que menos lo necesita."""
        commands = self._text_layout()
        tw = float(self.text_box.box.width)
        th = float(self.text_box.box.height)
        m, w, h = self._text_area()
        if tw <= 0 or th <= 0 or w <= 0 or h <= 0:
            return []
        sx = w / tw
        sy = min(sx, h / th)
        ty = m + (h - th * sy) / 2
        return [b"q", f"{sx:.6f} 0 0 {sy:.6f} {m:.6f} {ty:.6f} cm".encode(), commands, b"Q"]


@dataclass(frozen=True)
class _SpanishCertStampStyle(TextStampStyle):
    """TextStampStyle que instancia _SpanishCertTextStamp en lugar de TextStamp."""

    def create_stamp(self, writer, box, text_params) -> "_SpanishCertTextStamp":
        return _SpanishCertTextStamp(
            writer=writer, style=self, box=box, text_params=text_params
        )


def _build_stamp_text(cert_info: dict, reason: str = "", location: str = "") -> str:
    """Construye el texto del sello con los datos obligatorios del certificado."""
    lines = [cert_info["name"]]
    if cert_info["nif"]:
        lines.append(f"NIF: {cert_info['nif']}")
    if cert_info["org_nif"]:
        lines.append(f"Repr.: {cert_info['org_nif']}")
    if reason:
        lines.append(f"Motivo: {reason}")
    if location:
        lines.append(f"Lugar: {location}")
    lines.append("Firmado: %(ts)s")
    # «%» literal del usuario no debe romper el formateo del sello.
    return "\n".join(l if "%(ts)s" in l else l.replace("%", "%%") for l in lines)


def _empty_sig_field(writer, name: str) -> bool:
    """¿El documento trae ya un campo de firma con ese nombre y sin firmar?"""
    try:
        from pyhanko.sign.fields import enumerate_sig_fields
        for campo, valor, _ref in enumerate_sig_fields(writer, filled_status=None):
            if campo == name:
                return valor is None
    except Exception:  # noqa: BLE001
        pass
    return False


def _unique_field_name(writer, base: str = "Firma") -> str:
    """Un campo nuevo por firma: reutilizar un nombre ya firmado hace fallar
    a pyHanko, lo que impedía firmar dos veces el mismo documento."""
    used = set()
    try:
        from pyhanko.sign.fields import enumerate_sig_fields
        for name, _value, _ref in enumerate_sig_fields(writer, filled_status=None):
            used.add(name)
    except Exception:
        pass
    n = 1
    while f"{base}{n}" in used:
        n += 1
    return f"{base}{n}"


class SigningError(RuntimeError):
    pass


def _tolerant_writer(pdf_bytes: bytes, doc_password: str) -> IncrementalPdfFileWriter:
    """Escritor para los PDF que pyHanko rechaza en modo estricto: los de
    referencias cruzadas híbridas (tabla clásica + /XRefStm, habituales en Word
    y Acrobat, donde lectores distintos podrían ver objetos distintos) y (r37)
    los que tienen otros defectos que los visores aceptan, como una tabla xref
    con un objeto más de los que declara el tráiler.
    - Sin firmas previas: se reescribe con PyMuPDF (tabla xref clásica, conserva
      el cifrado) y se firma el resultado en modo estricto.
    - Con firmas previas: reescribir las invalidaría, así que se firma de forma
      incremental con el lector en modo no estricto."""
    doc = fitz.open("pdf", pdf_bytes)
    try:
        if doc.needs_pass and not (doc_password and doc.authenticate(doc_password)):
            raise SigningError("El documento está protegido con contraseña.")
        if doc_tools.has_signatures(doc):
            return IncrementalPdfFileWriter(BytesIO(pdf_bytes), strict=False)
        clean = doc.tobytes(garbage=1, deflate=True, encryption=fitz.PDF_ENCRYPT_KEEP)
    finally:
        doc.close()
    return IncrementalPdfFileWriter(BytesIO(clean))


class PAdESSigner:
    @staticmethod
    def sign_pdf_bytes(
        pdf_bytes: bytes,
        pfx_path: str,
        pfx_password: str,
        page_num: int,
        box: tuple,
        reason: str = "",
        location: str = "",
        contact: str = "",
        field_name: str = "",
        tsa_url: str = "",
        certify: bool = False,
        doc_password: str = "",
    ) -> bytes:
        """
        Firma PAdES visible e incremental (no invalida firmas previas).
        box: (x1, y1, x2, y2) en coordenadas PDF nativas (origen abajo-izquierda).
        field_name: (r38) si el documento ya trae un campo de firma vacío con ese
                 nombre (el recuadro de firma de un formulario), se firma DENTRO
                 de él, con su propio recuadro; si no, se crea un campo nuevo.
        tsa_url: si se indica, añade sello de tiempo RFC 3161 (PAdES-B-T).
        certify: firma de certificación (DocMDP): solo permite rellenar
                 formularios y firmar después.
        Devuelve los bytes del PDF firmado; lanza SigningError con un mensaje
        legible si algo falla.
        """
        try:
            cert_info = extract_cert_info(pfx_path, pfx_password)
        except ValueError as e:
            raise SigningError(
                "No se pudo abrir el certificado: la contraseña es incorrecta "
                "o el archivo PKCS#12 está dañado.") from e

        cms_signer = signers.SimpleSigner.load_pkcs12(
            pfx_path, passphrase=pfx_password.encode("utf-8") if pfx_password else None
        )
        if cms_signer is None:   # pyHanko devuelve None en lugar de lanzar
            raise SigningError("No se pudo cargar la clave privada del certificado.")

        try:
            w = IncrementalPdfFileWriter(BytesIO(pdf_bytes))
            if w.prev.xrefs.hybrid_xrefs_present:
                w = _tolerant_writer(pdf_bytes, doc_password)
        except PdfReadError:
            w = _tolerant_writer(pdf_bytes, doc_password)
        if getattr(w.prev, "encrypted", False):
            if not doc_password:
                raise SigningError("El documento está protegido con contraseña.")
            w.encrypt(doc_password)

        existente = field_name and _empty_sig_field(w, field_name)
        if not existente:
            field_name = _unique_field_name(w)
        meta_kwargs = dict(
            field_name=field_name,
            location=location or None,
            reason=reason or None,
            contact_info=contact or None,
            name=cert_info["name"],
            subfilter=SigSeedSubFilter.PADES,
        )
        if certify:
            meta_kwargs.update(certify=True, docmdp_permissions=MDPPerm.FILL_FORMS)
        sig_meta = signers.PdfSignatureMetadata(**meta_kwargs)

        timestamper = None
        if tsa_url:
            from pyhanko.sign.timestamps import HTTPTimeStamper
            timestamper = HTTPTimeStamper(tsa_url, timeout=15)

        stamp_style = _SpanishCertStampStyle(
            stamp_text=_build_stamp_text(cert_info, reason, location),
            timestamp_format="%d/%m/%Y %H:%M:%S",
            border_width=0,
        )

        pdf_signer = signers.PdfSigner(
            sig_meta,
            signer=cms_signer,
            timestamper=timestamper,
            stamp_style=stamp_style,
            new_field_spec=(None if existente else
                            SigFieldSpec(field_name, on_page=page_num, box=box)),
        )

        out = BytesIO()
        try:
            pdf_signer.sign_pdf(w, output=out)
        except Exception as e:
            traceback.print_exc()
            msg = str(e) or e.__class__.__name__
            if tsa_url and ("timestamp" in msg.lower() or "http" in msg.lower()):
                msg = f"Falló el sellado de tiempo con {tsa_url}:\n{msg}"
            raise SigningError(msg) from e
        return out.getvalue()

    @staticmethod
    def sign_pdf_visible_with_widget(
        input_pdf_path: str,
        output_pdf_path: str,
        pfx_path: str,
        pfx_password: str,
        page_num: int,
        box: tuple,
        reason: str = "Firma PAdES",
        location: str = "ES",
    ) -> bool:
        """Compatibilidad con la API anterior basada en archivos."""
        try:
            with open(input_pdf_path, "rb") as f:
                data = f.read()
            signed = PAdESSigner.sign_pdf_bytes(
                data, pfx_path, pfx_password, page_num, box,
                reason=reason, location=location)
            with open(output_pdf_path, "wb") as f:
                f.write(signed)
            return True
        except Exception as e:
            print(f"Error al firmar el PDF: {e}")
            traceback.print_exc()
            return False


# ── Quitar la última firma (r61) ─────────────────────────────────────────── #

def _revision_end(data: bytes, reader: PdfFileReader, revision: int) -> int:
    """Byte donde termina la revisión `revision` (tras su «%%EOF» y el salto
    de línea): en un PDF firmado cada firma se añade como actualización
    incremental, así que lo anterior a ese punto es el archivo exacto de
    antes de la firma siguiente."""
    startxref = reader.xrefs.get_startxref_for_revision(revision)
    fin = data.index(b"%%EOF", startxref) + len(b"%%EOF")
    while fin < len(data) and data[fin:fin + 1] in (b"\r", b"\n"):
        fin += 1
    return fin


def remove_last_signature(pdf_bytes: bytes, field_name: str, doc_password: str = "") -> bytes:
    """(r61) Quita la firma MÁS RECIENTE del documento y deja su recuadro de
    firma vacío, listo para firmar de nuevo (con otro certificado si se quiere).

    No se edita el campo y se reescribe el PDF: eso invalidaría todas las
    firmas anteriores. Se vuelve a la versión del archivo de justo antes de esa
    firma (sigue íntegra dentro del propio PDF, ver `_revision_end`) y, si el
    campo no existía ya vacío en ella (se creó al firmar), se le añade un campo
    de firma vacío con el mismo nombre y recuadro en una actualización
    incremental. Las firmas anteriores siguen válidas.

    Solo la más reciente: quitar una anterior invalidaría las posteriores, que
    la protegen. Lanza SigningError con un mensaje legible si no se puede."""
    try:
        reader = PdfFileReader(BytesIO(pdf_bytes), strict=False)
        if getattr(reader, "encrypted", False):
            if not doc_password:
                raise SigningError("El documento está protegido con contraseña.")
            reader.decrypt(doc_password)
        firmas = list(reader.embedded_signatures)
    except SigningError:
        raise
    except Exception as e:  # noqa: BLE001
        raise SigningError(f"No se pudieron leer las firmas del documento: {e}") from e
    if not firmas:
        raise SigningError("El documento no contiene firmas.")
    ultima = max(firmas, key=lambda f: f.signed_revision)
    if (ultima.field_name or "") != field_name:
        raise SigningError(
            f"Solo se puede quitar la firma más reciente («{ultima.field_name}»): "
            "quitar una anterior invalidaría las que se firmaron después.")
    if ultima.signed_revision < 1:
        raise SigningError(
            "Esta firma se hizo al crear el archivo: no hay una versión anterior "
            "sin ella a la que volver.")

    anterior = pdf_bytes[:_revision_end(pdf_bytes, reader, ultima.signed_revision - 1)]
    es_sello = getattr(ultima, "sig_object_type", "/Sig") == "/DocTimeStamp"
    campo = ultima.sig_field
    try:
        w = IncrementalPdfFileWriter(BytesIO(anterior), strict=False)
        if getattr(w.prev, "encrypted", False):
            w.encrypt(doc_password)
        from pyhanko.sign.fields import enumerate_sig_fields, append_signature_field
        ya_esta = any(nombre == field_name for nombre, _v, _r
                      in enumerate_sig_fields(w, filled_status=None))
        if ya_esta or es_sello:
            # El recuadro ya estaba vacío en esa versión (campo de un
            # formulario, r38), o era un sello de tiempo sin recuadro.
            return anterior
        ref_pagina = campo.raw_get("/P")
        with fitz.open("pdf", anterior) as d:
            if d.needs_pass:
                d.authenticate(doc_password)
            pagina = next((p.number for p in d if p.xref == ref_pagina.idnum), None)
        if pagina is None:
            raise SigningError("No se encontró la página del recuadro de la firma.")
        caja = tuple(float(v) for v in campo["/Rect"])
        append_signature_field(w, SigFieldSpec(field_name, on_page=pagina, box=caja))
        out = BytesIO()
        w.write(out)
        return out.getvalue()
    except SigningError:
        raise
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        raise SigningError(f"No se pudo dejar el recuadro de firma vacío: {e}") from e
