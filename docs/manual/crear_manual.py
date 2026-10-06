# -*- coding: utf-8 -*-
"""
(r138) Genera el manual de AventyaPDF en cada idioma (docs/manual/MANUAL_<código>.pdf),
las imágenes de las diapositivas del instalador (empaquetado/diapositivas/) y
las capturas del README (docs/capturas/, del manual en español).

    python docs/manual/crear_manual.py              # todos los idiomas
    python docs/manual/crear_manual.py es en        # solo esos
    python docs/manual/crear_manual.py --revisar    # comprueba las traducciones

El texto de cada manual está en docs/manual/<código>.md (el español es el
original; los demás, su traducción con la misma estructura). Formato:

* Cabecera entre dos líneas «---»: «clave: valor», con los títulos fijos y los
  textos de los documentos de muestra que salen en las capturas.
* «# Capítulo» (empieza página) y «## Sección».
* Párrafos separados por una línea en blanco; «- » para listas.
* «> **Consejo:** …» o «> **Importante:** …»: recuadro destacado.
* «![captura] Pie de la imagen»: una captura de docs/manual/capturas.py.
* «[[atajos]]»: la tabla de atajos de teclado de la aplicación (dialogs.SHORTCUTS).
* En el texto, **negrita** (menús y botones) y `tecla` (teclas y variables).

Cada idioma se genera en un proceso aparte (la aplicación elige el idioma al
arrancar), con la plataforma «offscreen» de Qt: no hace falta pantalla. Se
puede ejecutar en Windows y en Linux con el entorno de la aplicación.
"""
from __future__ import annotations

import datetime
import html
import os
import re
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
DIAPOSITIVAS = os.path.join(RAIZ, "empaquetado", "diapositivas")
CAPTURAS_README = {"ventana": "ventana.png", "recortar": "recortar.png",
                   "formulario": "formulario.png", "ocr": "ocr.png"}

# Página A4 y márgenes (puntos).
W, H = 595, 842
MI, MD, MS, MB = 64, 64, 74, 70
ANCHO = W - MI - MD
ALTO = H - MS - MB
# Captura: como mucho 0,62 pt por píxel (más o menos su tamaño en pantalla;
# nunca se agranda) y la mitad del alto útil de la página.
ESCALA_MAX = 0.62
ALTO_FIGURA_MAX = ALTO * 0.5
# Resolución con la que se guardan las capturas dentro del PDF.
PX_POR_PT = 2.0

AZUL = "#17355E"
TURQUESA = "#1B7B8B"
GRIS = "#5E6A70"

# Diapositivas del instalador: todas las de la presentación salvo la primera
# («Bienvenido…») y la última («Listo para empezar»). La misma regla está en
# herramientas_idioma.py (textos) y en el instalador.
DIAPO_PX = (420, 260)            # 1,5 × el hueco del instalador a escala 100 %
# En el hueco pequeño del instalador, de las capturas de la ventana entera
# solo se enseña la parte que importa (x, y, ancho, alto en píxeles de la
# captura), con la proporción de la diapositiva: el panel lateral y el
# principio de la página; del formulario, la página.
RECORTE_VENTANA = (0, 0, 860, 532)
RECORTE_DIAPO = {"formulario": (300, 0, 860, 532)}


# ── lectura del texto ──────────────────────────────────────────────────── #

def ruta_md(codigo: str) -> str:
    return os.path.join(AQUI, f"{codigo}.md")


def leer(codigo: str) -> tuple[dict, list]:
    """Cabecera y bloques: ("h1"|"h2"|"p"|"tip"|"ul"|"img"|"atajos", …)."""
    with open(ruta_md(codigo), encoding="utf-8") as fh:
        texto = fh.read().replace("\r\n", "\n")
    m = re.match(r"---\n(.*?)\n---\n", texto, re.S)
    if not m:
        raise ValueError(f"{codigo}.md: falta la cabecera entre «---»")
    meta = {}
    for linea in m.group(1).splitlines():
        if linea.strip():
            clave, _, valor = linea.partition(":")
            meta[clave.strip()] = valor.strip()
    bloques: list = []
    for parrafo in re.split(r"\n\s*\n", texto[m.end():].strip()):
        lineas = [x.rstrip() for x in parrafo.strip().splitlines()]
        primera = lineas[0]
        if primera.startswith("# "):
            bloques.append(("h1", primera[2:].strip()))
        elif primera.startswith("## "):
            bloques.append(("h2", primera[3:].strip()))
        elif primera.startswith("!["):
            mm = re.match(r"!\[(\w+)\]\s*(.*)", primera)
            bloques.append(("img", mm.group(1), mm.group(2).strip()))
        elif primera.strip() == "[[atajos]]":
            bloques.append(("atajos",))
        elif primera.startswith(">"):
            bloques.append(("tip", " ".join(x.lstrip("> ").strip() for x in lineas)))
        elif primera.startswith("- "):
            items: list[str] = []
            for x in lineas:
                if x.startswith("- "):
                    items.append(x[2:].strip())
                else:
                    items[-1] += " " + x.strip()
            bloques.append(("ul", items))
        else:
            bloques.append(("p", " ".join(x.strip() for x in lineas)))
    return meta, bloques


def _firma(bloque) -> tuple:
    """Lo que tiene que coincidir entre un manual y su traducción."""
    tipo = bloque[0]
    if tipo == "img":
        return ("img", bloque[1])
    if tipo == "ul":
        return ("ul", len(bloque[1]))
    return (tipo,)


def _marcas(texto: str) -> list[str]:
    return sorted(re.findall(r"\{\w+\}", texto))


def revisar(codigo: str) -> list[str]:
    """Problemas de la traducción `codigo` frente al original en español."""
    if not os.path.isfile(ruta_md(codigo)):
        return ["falta el archivo"]
    meta_es, bloques_es = leer("es")
    meta, bloques = leer(codigo)
    problemas = []
    for clave in meta_es:
        if not meta.get(clave):
            problemas.append(f"cabecera: falta «{clave}»")
        elif _marcas(meta[clave]) != _marcas(meta_es[clave]):
            problemas.append(f"cabecera: marcadores distintos en «{clave}»")
    for clave in set(meta) - set(meta_es):
        problemas.append(f"cabecera: sobra «{clave}»")
    if meta.get("muestra_texto"):
        for clave in ("buscar", "resaltar"):
            if meta.get(clave) and meta[clave] not in meta["muestra_texto"]:
                problemas.append(f"cabecera: «{clave}» no aparece en muestra_texto")
    if len(meta.get("explorador_opciones", "").split("|")) != 3:
        problemas.append("cabecera: explorador_opciones debe tener tres opciones con «|»")
    f_es = [_firma(b) for b in bloques_es]
    f = [_firma(b) for b in bloques]
    if f != f_es:
        for i, (a, b) in enumerate(zip(f_es, f)):
            if a != b:
                problemas.append(f"bloque {i + 1}: se esperaba {a} y hay {b}")
                break
        else:
            problemas.append(f"hay {len(f)} bloques y el original tiene {len(f_es)}")
    for b_es, b in zip(bloques_es, bloques):
        if b_es[0] in ("p", "tip", "ul") and b[0] == b_es[0]:
            t_es = " ".join(b_es[1]) if b_es[0] == "ul" else b_es[1]
            t = " ".join(b[1]) if b[0] == "ul" else b[1]
            if _marcas(t) != _marcas(t_es):
                problemas.append(f"marcadores distintos en: {t[:60]}…")
            if t.count("`") % 2 or t.count("**") % 2:
                problemas.append(f"` o ** sin cerrar en: {t[:60]}…")
    return problemas


# ── maquetación ────────────────────────────────────────────────────────── #

CSS = f"""
@font-face {{font-family: Texto; src: url(fuentes/NotoSans-Regular.ttf);}}
@font-face {{font-family: Texto; src: url(fuentes/NotoSans-Bold.ttf); font-weight: bold;}}
@font-face {{font-family: Texto; src: url(fuentes/NotoSans-Italic.ttf); font-style: italic;}}
@font-face {{font-family: Mono; src: url(fuentes/NotoSansMono-Regular.ttf);}}
p, ul, li, div, h1, h2, table {{margin: 0; padding: 0;}}
body {{margin: 0; padding: 0; font-family: Texto; font-size: 10.5pt; line-height: 1.5; color: #23272B;}}
h1 {{font-size: 24pt; line-height: 1.2; color: {AZUL};}}
h1 .num {{color: {TURQUESA};}}
h2 {{font-size: 14pt; line-height: 1.25; color: {TURQUESA};}}
h2 .num {{color: {GRIS}; font-weight: normal;}}
li {{margin: 0 0 2pt 0;}}
ul {{margin: 0 0 0 14pt;}}
.tecla {{font-family: Mono; font-size: 9pt; color: {AZUL}; background-color: #EEF1F4;}}
.consejo {{background-color: #E7F2F3; padding: 7pt 9pt;}}
.importante {{background-color: #FBEEE6; padding: 7pt 9pt;}}
.pie {{font-size: 8.5pt; font-style: italic; color: {GRIS}; text-align: center;}}
.indice1 {{font-size: 11.5pt; font-weight: bold; color: {AZUL};}}
.indice2 {{font-size: 9.5pt; color: #3B4248;}}
table {{width: 100%; border-collapse: collapse;}}
th {{text-align: left; font-size: 9pt; color: #FFFFFF; background-color: {AZUL}; padding: 4pt 6pt;}}
td {{font-size: 9.5pt; padding: 3.5pt 6pt; border-bottom: 0.5pt solid #D5DADF;}}
p.k {{font-family: Mono; font-size: 8.5pt; color: {AZUL};}}
p.th {{font-size: 9pt; font-weight: bold; color: #FFFFFF;}}
"""


def en_linea(texto: str) -> str:
    """**negrita** y `tecla` a HTML."""
    t = html.escape(texto, quote=False)
    # Los espacios que no se separan (« … » y « : » en francés) se los salta
    # MuPDF al partir líneas: las palabras unidas por ellos van en un bloque
    # que no se parte.
    t = re.sub(r"[^\s\u00a0\u202f]+(?:[\u00a0\u202f][^\s\u00a0\u202f]+)+",
               lambda m: f'<span style="white-space:nowrap">{m.group(0)}</span>', t)
    t = re.sub(r"`([^`]+)`", r'<span class="tecla">\1</span>', t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    return t


class Maquetador:
    """Va colocando los bloques de arriba abajo. El texto lo maqueta MuPDF
    (fitz.Story) en un DocumentWriter; las capturas, los filetes y las
    sombras se apuntan en `adornos` y se dibujan al final (`terminar`), en el
    hueco que se les reservó: así una captura que no cabe pasa entera a la
    página siguiente en vez de encogerse."""

    def __init__(self, archivo_fuentes: str, carpeta_capturas: str):
        import io
        import fitz
        self.fitz = fitz
        self.arch = fitz.Archive()
        self.arch.add(archivo_fuentes, "fuentes")
        self.arch.add(carpeta_capturas, "img")
        self.capturas = carpeta_capturas
        self._buffer = io.BytesIO()
        self._writer = fitz.DocumentWriter(self._buffer)
        self._dev = None
        self.paginas = 0
        self.y = MS
        self.capitulo = ""
        self.capitulo_de_pagina: list[str] = []
        self.titulos: list[tuple[int, str, int]] = []    # (nivel, texto, página)
        self.adornos: list[tuple] = []                   # (página, tipo, datos…)

    def nueva_pagina(self) -> None:
        if self._dev is not None:
            self._writer.end_page()
        self._dev = self._writer.begin_page(self.fitz.Rect(0, 0, W, H))
        self.paginas += 1
        self.y = MS
        self.capitulo_de_pagina.append(self.capitulo)

    @property
    def pagina(self) -> int:
        return self.paginas - 1

    def queda(self) -> float:
        return H - MB - self.y

    def colocar(self, contenido: str, antes: float = 0, despues: float = 0) -> None:
        """Coloca un trozo de HTML; si no cabe, sigue en páginas nuevas."""
        story = self.fitz.Story(html=contenido, user_css=CSS, archive=self.arch)
        if self._dev is None:
            self.nueva_pagina()
        if self.y > MS:
            self.y += antes
        while True:
            zona = self.fitz.Rect(MI, self.y, W - MD, H - MB)
            mas, lleno = story.place(zona)
            story.draw(self._dev)
            self.y = self.fitz.Rect(lleno).y1
            if not mas:
                break
            self.nueva_pagina()
        self.y += despues

    def filete(self) -> None:
        self.adornos.append((self.pagina, "filete", self.y))

    def capitulo_nuevo(self, numero: int, titulo: str) -> None:
        self.capitulo = f"{numero}. {titulo}"
        self.nueva_pagina()
        self.titulos.append((1, f"{numero}. {titulo}", self.pagina))
        self.y = MS + 40
        self.colocar(f'<h1><span class="num">{numero}</span>&#160;&#160;{en_linea(titulo)}</h1>',
                     despues=6)
        self.filete()
        self.y += 18

    def seccion(self, numero: str, titulo: str) -> None:
        if self.queda() < 110:                 # el título nunca solo al pie
            self.nueva_pagina()
        self.colocar(f'<h2><span class="num">{numero}</span>&#160;&#160;{en_linea(titulo)}</h2>',
                     antes=14, despues=6)
        self.titulos.append((2, f"{numero} {titulo}", self.pagina))

    def parrafo(self, texto: str) -> None:
        self.colocar(f"<p>{en_linea(texto)}</p>", despues=7)

    def lista(self, items: list[str]) -> None:
        cuerpo = "".join(f"<li>{en_linea(i)}</li>" for i in items)
        self.colocar(f"<ul>{cuerpo}</ul>", despues=6)

    def destacado(self, texto: str, clase: str) -> None:
        if self.queda() < 50:
            self.nueva_pagina()
        self.colocar(f'<div class="{clase}">{en_linea(texto)}</div>', antes=2, despues=10)

    def figura(self, clave: str, pie: str) -> None:
        ruta = os.path.join(self.capturas, clave + ".png")
        ancho_px, alto_px = _tamano_png(ruta)
        k = min(ESCALA_MAX, ANCHO / ancho_px, ALTO_FIGURA_MAX / alto_px)
        w, h = ancho_px * k, alto_px * k
        if self._dev is None or self.queda() < h + (24 if pie else 8) + 8:
            self.nueva_pagina()
        if self.y > MS:
            self.y += 4
        x0 = MI + (ANCHO - w) / 2
        self.adornos.append((self.pagina, "imagen", (x0, self.y, x0 + w, self.y + h), ruta))
        self.y += h + 6
        if pie:
            self.colocar(f'<p class="pie">{en_linea(pie)}</p>')
        self.y += 10

    def _celda(self, contenido: str, x0: float, x1: float, y: float) -> float:
        """Un trozo de HTML en una columna fija; devuelve dónde acaba."""
        story = self.fitz.Story(html=contenido, user_css=CSS, archive=self.arch)
        _mas, lleno = story.place(self.fitz.Rect(x0, y, x1, H - MB))
        story.draw(self._dev)
        return self.fitz.Rect(lleno).y1

    def tabla_atajos(self, meta: dict) -> None:
        """Tabla de dos columnas, fila a fila (el motor HTML de MuPDF no
        respeta el ancho de las columnas)."""
        import dialogs
        corte = MI + ANCHO * 0.36
        filas = [(f'<p class="th">{html.escape(meta["atajos_tecla"])}</p>',
                  f'<p class="th">{html.escape(meta["atajos_accion"])}</p>', True)]
        filas += [(f'<p class="k">{html.escape(k)}</p>', f"<p>{html.escape(v)}</p>", False)
                  for k, v in dialogs.SHORTCUTS]
        if self.y > MS:
            self.y += 4
        for izq, der, cabecera in filas:
            if self.queda() < 26:
                self.nueva_pagina()
            y0 = self.y
            if cabecera:
                self.adornos.append((self.pagina, "fondo", (MI, y0, W - MD, y0 + 20)))
            y1 = max(self._celda(izq, MI + 6, corte - 6, y0 + 4),
                     self._celda(der, corte, W - MD - 6, y0 + 4)) + 4
            if not cabecera:
                self.adornos.append((self.pagina, "raya", y1))
            self.y = y1
        self.y += 10

    def terminar(self):
        """Cierra el documento y dibuja los adornos. Devuelve el fitz.Document."""
        fitz = self.fitz
        if self._dev is not None:
            self._writer.end_page()
            self._dev = None
        self._writer.close()
        doc = fitz.open("pdf", self._buffer.getvalue())
        for pagina, tipo, *datos in self.adornos:
            page = doc[pagina]
            if tipo == "filete":
                y = datos[0]
                page.draw_line((MI, y), (MI + 70, y), color=_rgb(TURQUESA), width=2.5)
            elif tipo == "fondo":
                page.draw_rect(fitz.Rect(datos[0]), color=None, fill=_rgb(AZUL), overlay=False)
            elif tipo == "raya":
                page.draw_line((MI, datos[0]), (W - MD, datos[0]), color=(0.84, 0.86, 0.88),
                               width=0.5)
            elif tipo == "imagen":
                caja = fitz.Rect(datos[0])
                # Sombra suave y marco fino: la captura se distingue del papel.
                page.draw_rect(caja + (1.5, 1.5, 1.5, 1.5), color=None, fill=(0.88, 0.9, 0.92))
                page.insert_image(caja, filename=datos[1][:-4] + ".jpg")
                page.draw_rect(caja, color=(0.75, 0.78, 0.81), width=0.6)
        return doc


def _rgb(hexa: str) -> tuple:
    return tuple(int(hexa[i:i + 2], 16) / 255 for i in (1, 3, 5))


def _tamano_png(ruta: str) -> tuple[int, int]:
    with open(ruta, "rb") as fh:
        cab = fh.read(24)
    return int.from_bytes(cab[16:20], "big"), int.from_bytes(cab[20:24], "big")


def _reducir_capturas(carpeta: str) -> None:
    """Cada captura a la resolución con la que se va a ver (PX_POR_PT) y en
    JPEG de calidad alta, que es lo que va dentro del PDF: el manual pesa
    menos de la mitad y no se nota. El PNG se queda para medirla."""
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QColor, QImage, QPainter
    for nombre in os.listdir(carpeta):
        if not nombre.endswith(".png"):
            continue
        ruta = os.path.join(carpeta, nombre)
        ancho_px, alto_px = _tamano_png(ruta)
        k = min(ESCALA_MAX, ANCHO / ancho_px, ALTO_FIGURA_MAX / alto_px)
        img = QImage(ruta)
        objetivo = int(ancho_px * k * PX_POR_PT)
        if objetivo < ancho_px:
            img = img.scaledToWidth(objetivo, Qt.TransformationMode.SmoothTransformation)
        # Sin transparencia (la presentación tiene las esquinas redondeadas).
        fondo = QImage(img.size(), QImage.Format.Format_RGB32)
        fondo.fill(QColor("#FFFFFF"))
        p = QPainter(fondo)
        p.drawImage(0, 0, img)
        p.end()
        fondo.save(ruta[:-4] + ".jpg", "JPG", 88)


def _portada(doc, meta: dict, capturas: str, version: str, fecha: str, fuentes: str) -> None:
    import fitz
    page = doc.new_page(pno=0, width=W, height=H)
    # Banda superior en degradado (turquesa → azul marino), como la presentación.
    alto_banda = 430
    a, b = _rgb(TURQUESA), _rgb(AZUL)
    pasos = 120
    for i in range(pasos):
        t = i / (pasos - 1)
        c = tuple(a[j] + (b[j] - a[j]) * t for j in range(3))
        y0 = alto_banda * i / pasos
        page.draw_rect(fitz.Rect(0, y0, W, y0 + alto_banda / pasos + 0.6), color=None, fill=c)
    # Toque salmón, como la presentación de inicio.
    page.draw_rect(fitz.Rect(0, alto_banda, W, alto_banda + 5), color=None,
                   fill=(0.80, 0.43, 0.28))
    icono = os.path.join(RAIZ, "ICONO.png")
    if os.path.isfile(icono):
        page.insert_image(fitz.Rect(MI, 92, MI + 84, 176), filename=icono)
    page.insert_font(fontname="nb", fontfile=os.path.join(fuentes, "NotoSans-Bold.ttf"))
    page.insert_font(fontname="nr", fontfile=os.path.join(fuentes, "NotoSans-Regular.ttf"))
    blanco = (1, 1, 1)
    # Si un título no cabe, insert_textbox no escribe nada: se reduce la
    # letra hasta que quepa.
    _texto_que_quepa(page, fitz.Rect(MI, 200, W - MD, 290), meta["titulo"], 34, "nb", blanco)
    _texto_que_quepa(page, fitz.Rect(MI, 296, W - MD - 60, 360), meta["subtitulo"], 14, "nr",
                     (0.88, 0.94, 0.95), lineheight=1.3)
    # La ventana de la aplicación, montada sobre el borde de la banda.
    ventana = os.path.join(capturas, "ventana.png")
    if os.path.isfile(ventana):
        ancho_px, alto_px = _tamano_png(ventana)
        w = W - MI - MD
        h = w * alto_px / ancho_px
        caja = fitz.Rect(MI, alto_banda - 60, MI + w, alto_banda - 60 + h)
        page.draw_rect(caja + (3, 3, 3, 3), color=None, fill=(0.82, 0.85, 0.88))
        page.insert_image(caja, filename=ventana)
        page.draw_rect(caja, color=(0.70, 0.74, 0.78), width=0.6)
    gris = _rgb(GRIS)
    page.insert_textbox(fitz.Rect(MI, H - 120, W - MD, H - 100),
                        meta["version"].format(version=version) + "  ·  " + fecha,
                        fontsize=11, fontname="nb", color=_rgb(AZUL))
    page.insert_textbox(fitz.Rect(MI, H - 98, W - MD, H - 60),
                        "Aventya Asesoría Integral SL\ngithub.com/Aventya/AventyaPDF",
                        fontsize=9.5, fontname="nr", color=gris, lineheight=1.4)


def _texto_que_quepa(page, caja, texto: str, tamano: float, fuente: str, color,
                     **kw) -> None:
    while page.insert_textbox(caja, texto, fontsize=tamano, fontname=fuente, color=color,
                              **kw) < 0:
        tamano -= 1
        if tamano < 8:
            raise ValueError(f"No cabe en la portada: {texto!r}")


def _indice(m: Maquetador, meta: dict, desplazamiento: int):
    """Las páginas del índice, en un documento aparte. Devuelve el documento
    y sus enlaces (página del índice, recuadro, página de destino en el
    contenido), que se añaden al final, cuando ya está todo junto."""
    import fitz
    t = Maquetador(os.path.join(RAIZ, "vendor", "fonts", "noto"), m.capturas)
    t.capitulo = meta["indice"]
    t.nueva_pagina()
    t.y = MS + 40
    t.colocar(f"<h1>{html.escape(meta['indice'])}</h1>", despues=6)
    t.filete()
    t.y += 16
    # Todo el índice en una sola tabla; las posiciones de cada fila (para los
    # enlaces) las da MuPDF al colocarla.
    filas = []
    for i, (nivel, texto, pagina) in enumerate(m.titulos):
        clase = "indice1" if nivel == 1 else "indice2"
        sangria = "" if nivel == 1 else "&#160;" * 6
        arriba = "7pt" if nivel == 1 and i else "1pt"
        estilo = f"border-bottom:none; padding:{arriba} 0 1pt 0"
        filas.append(f'<tr><td id="t{i}" class="{clase}" style="{estilo}">{sangria}'
                     f'{html.escape(texto)}</td><td class="{clase}" style="{estilo}; '
                     f'text-align:right; width:12%">{pagina + desplazamiento + 1}</td></tr>')
    story = fitz.Story(html=f"<table>{''.join(filas)}</table>", user_css=CSS, archive=t.arch)
    posiciones: dict[int, tuple[int, fitz.Rect]] = {}

    def apuntar(pos):
        if pos.id and pos.id.startswith("t") and pos.open_close & 1:
            posiciones[int(pos.id[1:])] = (t.pagina, fitz.Rect(MI, pos.rect[1], W - MD, pos.rect[3]))

    while True:
        mas, lleno = story.place(fitz.Rect(MI, t.y, W - MD, H - MB))
        story.element_positions(apuntar)
        story.draw(t._dev)
        t.y = fitz.Rect(lleno).y1
        if not mas:
            break
        t.nueva_pagina()
    enlaces = [(pag, caja, m.titulos[i][2]) for i, (pag, caja) in posiciones.items()]
    return t.terminar(), t.capitulo_de_pagina, enlaces


def _cabeceras(doc, capitulos: list[str], meta: dict, fuentes: str, primera: int) -> None:
    import fitz
    for i in range(primera, len(doc)):
        page = doc[i]
        page.insert_font(fontname="nr", fontfile=os.path.join(fuentes, "NotoSans-Regular.ttf"))
        gris = _rgb(GRIS)
        page.insert_textbox(fitz.Rect(MI, 34, W / 2, 48), meta["cabecera"], fontsize=8,
                            fontname="nr", color=gris)
        capitulo = capitulos[i - primera] if i - primera < len(capitulos) else ""
        page.insert_textbox(fitz.Rect(W / 2, 34, W - MD, 48), capitulo, fontsize=8,
                            fontname="nr", color=gris, align=fitz.TEXT_ALIGN_RIGHT)
        page.draw_line((MI, 50), (W - MD, 50), color=(0.84, 0.86, 0.88), width=0.6)
        page.insert_textbox(fitz.Rect(0, H - 42, W, H - 28), str(i + 1), fontsize=9,
                            fontname="nr", color=gris, align=fitz.TEXT_ALIGN_CENTER)


def generar_uno(codigo: str) -> str:
    """Manual y diapositivas de un idioma (en este proceso, que ya arrancó
    con AVENTYAPDF_IDIOMA=codigo)."""
    sys.path.insert(0, RAIZ)
    sys.path.insert(0, AQUI)
    import capturas as cap
    meta, bloques = leer(codigo)
    tmp = tempfile.mkdtemp(prefix=f"aventyapdf_manual_{codigo}_")
    carpeta = os.path.join(tmp, "capturas")
    hechas = cap.generar(meta, carpeta)

    # Diapositivas del instalador (antes de reducir las capturas).
    import presentacion
    _diapositivas(codigo, presentacion.SLIDES[1:-1], carpeta)
    if codigo == "es":
        import shutil
        destino = os.path.join(RAIZ, "docs", "capturas")
        os.makedirs(destino, exist_ok=True)
        for clave, nombre in CAPTURAS_README.items():
            shutil.copy2(os.path.join(carpeta, clave + ".png"), os.path.join(destino, nombre))

    usadas = {b[1] for b in bloques if b[0] == "img"}
    faltan = usadas - set(hechas)
    if faltan:
        raise SystemExit(f"{codigo}.md usa capturas que no existen: {sorted(faltan)}")
    _reducir_capturas(carpeta)

    from window_menus import APP_VERSION
    fuentes = os.path.join(RAIZ, "vendor", "fonts", "noto")
    m = Maquetador(fuentes, carpeta)
    capitulo = 0
    seccion = 0
    for b in bloques:
        tipo = b[0]
        if tipo == "h1":
            capitulo += 1
            seccion = 0
            m.capitulo_nuevo(capitulo, b[1])
        elif tipo == "h2":
            seccion += 1
            m.seccion(f"{capitulo}.{seccion}", b[1])
        elif tipo == "p":
            m.parrafo(b[1])
        elif tipo == "ul":
            m.lista(b[1])
        elif tipo == "tip":
            clase = "importante" if b[1].startswith(f"**{meta['importante']}") else "consejo"
            m.destacado(b[1], clase)
        elif tipo == "img":
            m.figura(b[1], b[2])
        elif tipo == "atajos":
            m.tabla_atajos(meta)

    # Portada (1 página) + índice delante del contenido.
    import fitz
    contenido = m.terminar()
    paginas_indice = 1
    for _ in range(3):                    # el índice puede ocupar más de una página
        indice, cap_indice, enlaces = _indice(m, meta, 1 + paginas_indice)
        if len(indice) == paginas_indice:
            break
        paginas_indice = len(indice)
    doc = fitz.open()
    doc.insert_pdf(indice)
    doc.insert_pdf(contenido)
    meses = _meses(codigo)
    hoy = datetime.date.today()
    fecha = meta["fecha"].format(mes=meses[hoy.month - 1], anio=hoy.year)
    _portada(doc, meta, carpeta, APP_VERSION, fecha, fuentes)
    _cabeceras(doc, cap_indice + m.capitulo_de_pagina, meta, fuentes, 1)
    for pagina_indice, caja, destino in enlaces:
        doc[1 + pagina_indice].insert_link({"kind": fitz.LINK_GOTO, "from": caja,
                                            "page": destino + 1 + paginas_indice})
    doc.set_toc([[nivel, texto, pagina + 2 + paginas_indice]
                   for nivel, texto, pagina in m.titulos])
    doc.set_metadata({"title": meta["titulo"], "author": "Aventya Asesoría Integral SL",
                        "subject": meta["subtitulo"], "creator": "AventyaPDF"})
    try:
        doc.set_language(codigo)
    except Exception:  # noqa: BLE001  (versiones antiguas de PyMuPDF)
        pass
    salida = os.path.join(AQUI, f"MANUAL_{codigo}.pdf")
    # Las fuentes, solo con las letras que se usan (si no, van enteras: 1,5 MB).
    doc.subset_fonts()
    doc.save(salida, garbage=4, deflate=True)
    n = len(doc)
    doc.close()
    return f"{salida} ({n} páginas, {os.path.getsize(salida) / 1e6:.1f} MB)"


def _meses(codigo: str) -> list[str]:
    """Nombre de los meses para la fecha de la portada, de la cabecera."""
    meta, _ = leer(codigo)
    return meta.get("meses", "1|2|3|4|5|6|7|8|9|10|11|12").split("|")


def _diapositivas(codigo: str, slides, carpeta: str) -> None:
    """Imagen de cada diapositiva del instalador: la captura entera, centrada
    sobre fondo claro (sin recortar nada)."""
    from PyQt6.QtCore import QRect, Qt
    from PyQt6.QtGui import QColor, QImage, QPainter
    os.makedirs(DIAPOSITIVAS, exist_ok=True)
    for i, s in enumerate(slides, start=1):
        lienzo = QImage(*DIAPO_PX, QImage.Format.Format_RGB32)
        lienzo.fill(QColor("#EEF2F4"))
        img = QImage(os.path.join(carpeta, s.captura + ".png"))
        recorte = RECORTE_DIAPO.get(s.captura)
        if recorte is None and img.width() >= 1200:
            recorte = RECORTE_VENTANA
        if recorte:
            img = img.copy(QRect(*recorte))
        margen = 10
        img = img.scaled(DIAPO_PX[0] - 2 * margen, DIAPO_PX[1] - 2 * margen,
                         Qt.AspectRatioMode.KeepAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)
        p = QPainter(lienzo)
        x = (DIAPO_PX[0] - img.width()) // 2
        y = (DIAPO_PX[1] - img.height()) // 2
        p.fillRect(QRect(x + 2, y + 2, img.width(), img.height()), QColor(0, 0, 0, 30))
        p.drawImage(x, y, img)
        p.setPen(QColor("#B8C0C8"))
        p.drawRect(QRect(x, y, img.width() - 1, img.height() - 1))
        p.end()
        lienzo.save(os.path.join(DIAPOSITIVAS, f"{codigo}_{i:02d}.png"), "PNG", 9)


def main(argv: list[str]) -> int:
    sys.path.insert(0, RAIZ)
    import idioma
    if argv[:1] == ["--revisar"]:
        mal = 0
        for codigo in idioma.IDIOMAS:
            if codigo == "es":
                continue
            p = revisar(codigo)
            print(f"{codigo}: {'bien' if not p else f'{len(p)} problemas'}")
            for x in p:
                print("   ", x)
            mal += bool(p)
        return 1 if mal else 0
    if argv[:1] == ["--uno"]:
        print(generar_uno(argv[1]))
        return 0
    codigos = argv or list(idioma.IDIOMAS)
    for codigo in codigos:
        if codigo != "es" and revisar(codigo):
            print(f"{codigo}: la traducción tiene problemas (--revisar)")
            return 1
    fallos = 0
    for codigo in codigos:
        env = {**os.environ, "AVENTYAPDF_IDIOMA": codigo, "QT_QPA_PLATFORM": "offscreen",
               "PYTHONIOENCODING": "utf-8"}
        r = subprocess.run([sys.executable, os.path.abspath(__file__), "--uno", codigo],
                           env=env, capture_output=True, text=True, encoding="utf-8")
        lineas = [x for x in r.stdout.splitlines() if "MANUAL_" in x]
        if r.returncode or not lineas:
            fallos += 1
            print(f"{codigo}: ERROR\n{r.stderr[-3000:]}")
        else:
            print(lineas[-1])
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
