import html as _html
import os as _os
import re as _re

import fitz

import icons

# Mensajes emergentes (tooltips): fondo amarillo crema en toda la aplicación.
# Un `setStyleSheet` local sin selector («background: …;») se aplica también al
# tooltip de sus hijos y taparía el de la hoja global, así que esos estilos
# locales deben añadir esta regla (invariante 44).
TOOLTIP_QSS = ("QToolTip { background: #FFF8DC; color: #201F1E;"
               " border: 1px solid #E3D5A6; padding: 4px 6px; }")


class PDFUtils:

    # Opciones de letra de la herramienta Texto → familia CSS guardada en la
    # anotación. (r36) Se dibujan con Noto Sans / Serif / Sans Mono (apply_text_appearance).
    FONT_CSS = {
        "sans":  "sans-serif",
        "serif": "serif",
        "mono":  "monospace",
    }
    # Etiqueta del combo ↔ opción
    FONT_LABELS = {"Documento": "doc", "Noto Sans": "sans", "Noto Serif": "serif",
                   "Noto Sans Mono": "mono"}
    CSS_LABELS = {"sans-serif": "Noto Sans", "serif": "Noto Serif", "monospace": "Noto Sans Mono"}

    TEXT_PAD = 2.0          # margen interior del cuadro de texto, en pt

    @staticmethod
    def apply_text_appearance(doc: fitz.Document, annot) -> bool:
        """(r36) Dibuja la apariencia del cuadro de texto con la fuente Noto
        incluida en la app.

        El generador de texto enriquecido de MuPDF ignora la familia pedida y
        escribe siempre con Charis SIL o Nimbus, así que tras cada
        `annot.update()` se sustituye el flujo /AP /N por uno propio: texto
        repartido en el ancho del cuadro, con su alineación, color, negrita y
        cursiva, y la Noto incrustada como recurso. Devuelve False si no se pudo
        (se queda la apariencia de MuPDF)."""
        try:
            if annot.type[1] != "FreeText":
                return False
            info = annot.info
            st = PDFUtils.decode_text_style(info.get("subject", ""))
            if not (info.get("subject") or "").startswith("TXT|"):
                return False
            try:
                size = float(info.get("title") or 12)
            except (TypeError, ValueError):
                size = 12.0
            text = (info.get("content") or "").replace("\r\n", "\n").replace("\r", "\n")
            kind = icons.CSS_TO_NOTO.get(st["font_css"], "sans")
            path = icons.noto_path(kind, st["bold"], st["italic"])
            font = fitz.Font(fontfile=path)
            page = annot.parent
            name = _re.sub(r"[^A-Za-z0-9]", "", _os.path.splitext(_os.path.basename(path))[0])
            fxref = page.insert_font(fontname=name, fontfile=path)
            kind_ap, ap = doc.xref_get_key(annot.xref, "AP/N")
            if kind_ap != "xref":
                return False
            apx = int(ap.split()[0])
            x0, y0, x1, y1 = (float(v) for v in _re.findall(
                r"[-\d.]+", doc.xref_get_key(apx, "BBox")[1]))
            pad = PDFUtils.TEXT_PAD
            ancho = max(1.0, (x1 - x0) - 2 * pad)
            import pdf_edit                       # aquí: pdf_edit importa módulos pesados
            lineas = pdf_edit.wrap(text, font, size, ancho) if text else []
            salto = (font.ascender - font.descender) * size
            r, g, b = (max(0.0, min(1.0, c)) for c in st["color"])
            ops = [f"q BT {r:.4f} {g:.4f} {b:.4f} rg /{name} {size:.2f} Tf"]
            y = y1 - pad - font.ascender * size
            for linea in lineas:
                if linea:
                    w = font.text_length(linea, size)
                    align = st["align"]
                    x = (x0 + pad + (ancho - w) / 2 if align == 1 else
                         x1 - pad - w if align == 2 else x0 + pad)
                    gids = "".join(f"{font.has_glyph(ord(c)):04x}" for c in linea)
                    ops.append(f"1 0 0 1 {x:.2f} {y:.2f} Tm <{gids}> Tj")
                y -= salto
            ops.append("ET Q")
            doc.update_stream(apx, " ".join(ops).encode("latin-1"))
            doc.xref_set_key(apx, "Resources", f"<</Font<</{name} {fxref} 0 R>>>>")
            return True
        except Exception:  # noqa: BLE001 — si falla, se queda la apariencia de MuPDF
            return False

    @staticmethod
    def detect_doc_font_css(page) -> str:
        """Best-effort classification of the page's dominant font into a CSS
        generic family, so the "Documento" option can mimic the PDF's look."""
        try:
            for font in page.get_fonts(full=False):
                name = (font[3] or "").lower()
                if any(k in name for k in ("times", "serif", "roman",
                                            "georgia", "minion", "garamond")):
                    return "serif"
                if any(k in name for k in ("courier", "mono", "consol")):
                    return "monospace"
                if name:
                    return "sans-serif"
        except Exception:
            pass
        return "sans-serif"

    @staticmethod
    def _rounded_rect_path(x: float, y: float, w: float, h: float,
                            radius: float) -> str:
        """Build a PDF path (operators) for a rounded rectangle in the
        appearance-stream coordinate system. Coordinates are PDF-native
        (y grows upwards). Returns the path ending with `h` (closepath)."""
        r = max(0.0, min(radius, w / 2.0, h / 2.0))
        k = 0.5523 * r  # Bézier handle length for a quarter circle
        x0, y0, x1, y1 = x, y, x + w, y + h
        return "\n".join([
            f"{x0+r:.2f} {y0:.2f} m",
            f"{x1-r:.2f} {y0:.2f} l",
            f"{x1-r+k:.2f} {y0:.2f} {x1:.2f} {y0+r-k:.2f} {x1:.2f} {y0+r:.2f} c",
            f"{x1:.2f} {y1-r:.2f} l",
            f"{x1:.2f} {y1-r+k:.2f} {x1-r+k:.2f} {y1:.2f} {x1-r:.2f} {y1:.2f} c",
            f"{x0+r:.2f} {y1:.2f} l",
            f"{x0+r-k:.2f} {y1:.2f} {x0:.2f} {y1-r+k:.2f} {x0:.2f} {y1-r:.2f} c",
            f"{x0:.2f} {y0+r:.2f} l",
            f"{x0:.2f} {y0+r-k:.2f} {x0+r-k:.2f} {y0:.2f} {x0+r:.2f} {y0:.2f} c",
            "h",
        ])

    @staticmethod
    def apply_rounded_corners(annot, corner_radius: int = 6) -> None:
        """Rewrite a Square annotation's appearance stream so it renders with
        rounded corners. PyMuPDF regenerates a sharp `re` rectangle on every
        ``annot.update()``, so this must be re-applied after any update (create,
        move, resize, color/width change)."""
        try:
            ap = annot._getAP().decode("latin-1")
            m = _re.search(r"([-\d.]+) ([-\d.]+) ([-\d.]+) ([-\d.]+) re", ap)
            if not m:
                return
            x, y, w, h = (float(v) for v in m.groups())
            path = PDFUtils._rounded_rect_path(x, y, w, h, corner_radius)
            annot._setAP((ap.replace(m.group(0), path)).encode("latin-1"))
        except Exception:
            pass

    # ── Free text (rich text: bold / italic / alignment / font) ──────────── #

    @staticmethod
    def _text_richtext(text: str, fontsize: int, color: tuple,
                        bold: bool, italic: bool, font_css: str) -> str:
        hexcol = "#%02x%02x%02x" % tuple(
            max(0, min(255, int(c * 255))) for c in color)
        style = (
            f"font-family:{font_css};"
            f"font-size:{int(fontsize)}px;"
            f"font-weight:{'bold' if bold else 'normal'};"
            f"font-style:{'italic' if italic else 'normal'};"
            f"color:{hexcol};"
        )
        body = _html.escape(text).replace("\r\n", "\n").replace("\n", "<br/>")
        return f'<span style="{style}">{body}</span>'

    @staticmethod
    def _encode_text_style(bold: bool, italic: bool, align: int,
                            font_css: str, color: tuple) -> str:
        """Compact token stored in the annotation subject so the options panel
        can recover the styling when the annotation is re-selected."""
        hexcol = "#%02x%02x%02x" % tuple(
            max(0, min(255, int(c * 255))) for c in color)
        return (f"TXT|b{int(bold)}|i{int(italic)}|a{int(align)}"
                f"|f{font_css}|c{hexcol}")

    @staticmethod
    def _set_info_keys(doc, annot, title: str = None, content: str = None,
                       subject: str = None) -> None:
        """Set annotation metadata directly via xref keys. Unlike
        ``annot.set_info`` this does NOT regenerate the appearance stream, so it
        is safe to call after a custom (rich-text / image) appearance was built."""
        if title is not None:
            doc.xref_set_key(annot.xref, "T", fitz.get_pdf_str(title))
        if content is not None:
            doc.xref_set_key(annot.xref, "Contents", fitz.get_pdf_str(content))
        if subject is not None:
            doc.xref_set_key(annot.xref, "Subj", fitz.get_pdf_str(subject))

    @staticmethod
    def decode_text_style(subject: str) -> dict:
        out = {"bold": False, "italic": False, "align": 0,
               "font_css": "sans-serif", "color": (0.0, 0.0, 0.0)}
        if not subject or not subject.startswith("TXT|"):
            return out
        for part in subject.split("|")[1:]:
            if part.startswith("b"):
                out["bold"] = part[1:] == "1"
            elif part.startswith("i"):
                out["italic"] = part[1:] == "1"
            elif part.startswith("a"):
                try:
                    out["align"] = int(part[1:])
                except ValueError:
                    pass
            elif part.startswith("f"):
                out["font_css"] = part[1:] or "sans-serif"
            elif part.startswith("c") and len(part) >= 8:
                try:
                    h = part[2:8]
                    out["color"] = (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255,
                                    int(h[4:6], 16) / 255)
                except ValueError:
                    pass
        return out

    @staticmethod
    def add_text_annotation(doc: fitz.Document, page_num: int,
                             rect: fitz.Rect, text: str,
                             fontsize: int = 12,
                             text_color: tuple = (0.0, 0.0, 0.0),
                             bold: bool = False, italic: bool = False,
                             align: int = 0, font_css: str = "sans-serif"):
        page = doc[page_num]
        rc = PDFUtils._text_richtext(text, fontsize, text_color,
                                     bold, italic, font_css)
        annot = page.add_freetext_annot(
            rect, rc, fontsize=fontsize, richtext=True, align=align)
        # Rich-text FreeText always carries a callout line — drop it.
        doc.xref_set_key(annot.xref, "CL", "null")
        annot.update()
        PDFUtils._set_info_keys(
            doc, annot, title=str(int(fontsize)), content=text,
            subject=PDFUtils._encode_text_style(
                bold, italic, align, font_css, text_color))
        PDFUtils.apply_text_appearance(doc, annot)
        return annot

    @staticmethod
    def rebuild_text_annotation(doc: fitz.Document, annot, text: str,
                                 fontsize: int, text_color: tuple,
                                 bold: bool, italic: bool, align: int,
                                 font_css: str):
        """Re-apply rich text to an existing FreeText annotation (used when the
        text, size, color, weight, style, alignment or font changes)."""
        rc = PDFUtils._text_richtext(text, fontsize, text_color,
                                     bold, italic, font_css)
        doc.xref_set_key(annot.xref, "RC", fitz.get_pdf_str(rc))
        doc.xref_set_key(annot.xref, "Q", str(int(align)))
        doc.xref_set_key(annot.xref, "CL", "null")
        annot.update()
        PDFUtils._set_info_keys(
            doc, annot, title=str(int(fontsize)), content=text,
            subject=PDFUtils._encode_text_style(
                bold, italic, align, font_css, text_color))
        PDFUtils.apply_text_appearance(doc, annot)

    @staticmethod
    def add_rectangle_annotation(doc: fitz.Document, page_num: int,
                                   rect: fitz.Rect,
                                   color: tuple = (0.82, 0.20, 0.22),
                                   width: int = 2,
                                   corner_radius: int = 6):
        page = doc[page_num]
        annot = page.add_rect_annot(rect)
        annot.set_colors(stroke=color)
        annot.set_border(width=width)
        annot.update()
        # The PDF Border-array corner radius is ignored by most viewers, so we
        # draw the rounded rectangle directly into the appearance stream.
        PDFUtils.apply_rounded_corners(annot, corner_radius)
