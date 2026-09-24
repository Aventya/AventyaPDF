"""
Genera el índice de emojis de la aplicación:

    python create_emoji_index.py

Resultado: vendor/emoji/emojis.json — los emojis que sabe dibujar la fuente
**Noto Emoji** (vendor/fonts/noto-emoji/NotoEmoji-Regular.ttf), en el orden
oficial de Unicode, con su grupo y sus nombres y palabras clave en español
(Unicode CLDR) y en inglés.

Solo entran los emojis de **un carácter** (sin contar el selector de variación
U+FE0F, que no se dibuja): las secuencias —banderas de países, combinaciones con
ZWJ, tonos de piel— necesitan ligaduras que no se pueden componer al escribir el
glifo suelto en el PDF.

Solo hace falta Internet para GENERAR el índice; la aplicación usa el archivo.
"""
import json
import os
import sys
import urllib.request

RAIZ = os.path.dirname(os.path.abspath(__file__))
DESTINO = os.path.join(RAIZ, "vendor", "emoji")
FUENTE = os.path.join(RAIZ, "vendor", "fonts", "noto-emoji", "NotoEmoji-Regular.ttf")
ORDEN_UNICODE = "https://unicode.org/Public/emoji/latest/emoji-test.txt"
CLDR = ("https://raw.githubusercontent.com/unicode-org/cldr-json/main/cldr-json/"
        "cldr-annotations-full/annotations/es/annotations.json")
GRUPOS_ES = {
    "Smileys & Emotion": "Caras y emociones",
    "People & Body": "Personas y cuerpo",
    "Animals & Nature": "Animales y naturaleza",
    "Food & Drink": "Comida y bebida",
    "Travel & Places": "Viajes y lugares",
    "Activities": "Actividades",
    "Objects": "Objetos",
    "Symbols": "Símbolos",
    "Flags": "Banderas",
}


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "aventyapdf"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def generar() -> int:
    import fitz

    font = fitz.Font(fontfile=FUENTE)
    es = json.loads(_get(CLDR))["annotations"]["annotations"]

    entradas = []
    grupo = subgrupo = ""
    for linea in _get(ORDEN_UNICODE).decode("utf-8").splitlines():
        if linea.startswith("# group:"):
            grupo = linea.split(":", 1)[1].strip()
            continue
        if linea.startswith("# subgroup:"):
            subgrupo = linea.split(":", 1)[1].strip()
            continue
        if not linea or linea.startswith("#") or ";" not in linea:
            continue
        codigos = [c for c in linea.split(";")[0].split() if c.upper() != "FE0F"]
        estado = linea.split(";")[1].split("#")[0].strip()
        if estado != "fully-qualified" or len(codigos) != 1:
            continue                      # secuencias: no son un solo glifo
        punto = int(codigos[0], 16)
        if not font.has_glyph(punto):
            continue                      # la fuente no lo dibuja
        emoji = chr(punto)
        anot = es.get(emoji) or es.get(emoji + "️") or {}
        nombre_en = linea.split("#", 1)[1].strip().split(" ", 2)[-1] if "#" in linea else ""
        entradas.append({
            "emoji": emoji,
            "name": (anot.get("tts") or [nombre_en])[0],
            "group": grupo,
            "subgroup": subgrupo,
            "es": list(dict.fromkeys((anot.get("tts") or []) + (anot.get("default") or []))),
            "keywords": [nombre_en] if nombre_en else [],
            "unicode": f"{punto:x}",
        })

    os.makedirs(DESTINO, exist_ok=True)
    salida = os.path.join(DESTINO, "emojis.json")
    with open(salida, "w", encoding="utf-8") as fh:
        json.dump(entradas, fh, ensure_ascii=False, separators=(",", ":"))
    con_es = sum(1 for e in entradas if e["es"])
    print(f"Hecho: {len(entradas)} emojis ({con_es} con nombre en español) en {salida}")
    return 0


if __name__ == "__main__":
    sys.exit(generar())
