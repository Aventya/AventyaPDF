"""
herramientas_idioma.py — Mantenimiento de los archivos de idioma (r136).

    python herramientas_idioma.py catalogo     # rehace idiomas/es.json desde el código
    python herramientas_idioma.py revisar      # qué falta o sobra en cada idioma
    python herramientas_idioma.py instalador   # rehace los textos del instalador y del
                                               # menú de Windows 11 desde empaquetado/idiomas

El catálogo se saca del código: todas las llamadas `tr("…")` con un texto
literal de los módulos de la aplicación. Las pruebas comprueban que el catálogo
está al día y que cada idioma tiene todos los textos con los mismos marcadores.
"""
import ast
import glob
import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
CARPETA = os.path.join(RAIZ, "idiomas")
MARCADOR = re.compile(r"\{[^{}]*\}|%\(\w+\)s|%\d|%n")
SIN_TEXTOS = {"herramientas_idioma.py"}


def textos_del_codigo() -> dict[str, list[str]]:
    """{texto: ["archivo.py:línea", …]} en orden de aparición."""
    vistos: dict[str, list[str]] = {}
    for ruta in sorted(glob.glob(os.path.join(RAIZ, "*.py"))):
        nombre = os.path.basename(ruta)
        if nombre in SIN_TEXTOS:
            continue
        with open(ruta, encoding="utf-8") as f:
            arbol = ast.parse(f.read())
        for nodo in ast.walk(arbol):
            if not isinstance(nodo, ast.Call):
                continue
            func = nodo.func
            nombre_f = func.id if isinstance(func, ast.Name) else \
                func.attr if isinstance(func, ast.Attribute) else ""
            # tr("texto") y tr_en(código, "texto")
            pos = 0 if nombre_f == "tr" else 1 if nombre_f == "tr_en" else None
            if (pos is not None and len(nodo.args) > pos
                    and isinstance(nodo.args[pos], ast.Constant)
                    and isinstance(nodo.args[pos].value, str)):
                vistos.setdefault(nodo.args[pos].value, []).append(f"{nombre}:{nodo.lineno}")
    return vistos


def marcadores(texto: str) -> list[str]:
    """Marcadores {nombre} de un texto (sin contar las llaves dobles «{{ }}»)."""
    return sorted(MARCADOR.findall(texto.replace("{{", "").replace("}}", "")))


def leer(codigo: str) -> dict[str, str]:
    with open(os.path.join(CARPETA, codigo + ".json"), encoding="utf-8") as f:
        return json.load(f)


def escribir(codigo: str, datos: dict[str, str]) -> None:
    with open(os.path.join(CARPETA, codigo + ".json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)
        f.write("\n")


def problemas(codigo: str, catalogo: dict) -> list[str]:
    datos = leer(codigo)
    out = []
    for texto in catalogo:
        if texto not in datos or not datos[texto]:
            out.append(f"falta: {texto[:70]!r}")
        elif marcadores(datos[texto]) != marcadores(texto):
            out.append(f"marcadores distintos: {texto[:70]!r}")
    out += [f"sobra: {t[:70]!r}" for t in datos if t not in catalogo]
    return out


# ── Instalador y menú del Explorador ──────────────────────────────────────── #

INSTALADOR = os.path.join(RAIZ, "empaquetado", "idiomas")
MENSAJES_ISS = os.path.join(INSTALADOR, "mensajes.iss")
TEXTOS_MENU_H = os.path.join(RAIZ, "shell", "textos_menu.h")
# Mensajes de Inno Setup propios (sección [Messages]); el resto son [CustomMessages].
MENSAJES_INNO = {"WelcomeLabel2"}
# Identificador principal de idioma de Windows de cada código (como idioma.py).
LANGID = {"es": 0x0A, "en": 0x09, "ca": 0x03, "gl": 0x56, "eu": 0x2D}


def textos_instalador() -> dict[str, dict[str, str]]:
    """{código: {clave: texto}}; a un idioma sin traducción le toca el español."""
    sys.path.insert(0, RAIZ)
    import idioma
    with open(os.path.join(INSTALADOR, "instalador.json"), encoding="utf-8") as f:
        es = json.load(f)["es"]
    out = {}
    for codigo in idioma.IDIOMAS:
        datos = dict(es)
        ruta = os.path.join(INSTALADOR, f"instalador_{codigo}.json")
        if codigo != "es" and os.path.exists(ruta):
            with open(ruta, encoding="utf-8") as f:
                datos.update({k: v for k, v in json.load(f).items() if k in es and v})
        out[codigo] = datos
    return out


def diapositivas() -> list[tuple[str, str, str]]:
    """(r138) Las diapositivas de la presentación (presentacion.SLIDES) que
    enseña el instalador mientras instala: (título, texto, captura) en español,
    leídas del código sin importar Qt. Todas salvo la primera («Bienvenido…»)
    y la última («Listo para empezar»): la misma regla que
    docs/manual/crear_manual.py, que hace sus imágenes."""
    with open(os.path.join(RAIZ, "presentacion.py"), encoding="utf-8") as f:
        arbol = ast.parse(f.read())
    out = []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Call) and getattr(nodo.func, "id", "") == "Slide":
            titulo, texto = (a.args[0].value for a in nodo.args[1:3])
            captura = nodo.args[3].value if len(nodo.args) > 3 else ""
            out.append((nodo.lineno, titulo, texto, captura))
    out.sort()
    return [(t, x, c) for _l, t, x, c in out][1:-1]


def _cpp(texto: str) -> str:
    return 'L"' + "".join(c if 32 <= ord(c) < 127 and c not in '"\\' else
                          f"\\u{ord(c):04X}" for c in texto) + '"'


def generar_instalador() -> tuple[str, str]:
    """(mensajes.iss, textos_menu.h), sin escribirlos."""
    textos = textos_instalador()
    sys.path.insert(0, RAIZ)
    import idioma
    diapos = diapositivas()
    iss = ["; Generado por «python herramientas_idioma.py instalador» a partir de",
           "; empaquetado/idiomas/*.json y de las diapositivas de presentacion.py",
           "; (traducidas en idiomas/*.json): no editar a mano (r136, r138).", "",
           f"#define NumDiapositivas {len(diapos)}", "", "[Messages]"]
    for codigo, datos in textos.items():
        iss += [f"{codigo}.{k}={v}" for k, v in datos.items() if k in MENSAJES_INNO]
    iss += ["", "[CustomMessages]"]
    for codigo, datos in textos.items():
        iss += [f"{codigo}.{k}={v}" for k, v in datos.items() if k not in MENSAJES_INNO]
    for codigo in textos:
        traducidos = {} if codigo == "es" else idioma.cargar_textos(codigo)
        for i, (titulo, texto, _c) in enumerate(diapos, start=1):
            iss.append(f"{codigo}.Diapo{i:02d}Titulo={traducidos.get(titulo, titulo)}")
            iss.append(f"{codigo}.Diapo{i:02d}Texto={traducidos.get(texto, texto)}")
    h = ["// Generado por «python herramientas_idioma.py instalador» a partir de",
         "// empaquetado/idiomas/*.json: no editar a mano (r136).", "#pragma once", "",
         "struct TextosMenu { const wchar_t* codigo; const wchar_t* firmar;",
         "                    const wchar_t* combinar; const wchar_t* convertir; };",
         "static const TextosMenu TEXTOS_MENU[] = {"]
    for codigo, d in textos.items():
        h.append(f"    {{L\"{codigo}\", {_cpp(d['MenuFirmar'])}, {_cpp(d['MenuCombinar'])}, "
                 f"{_cpp(d['MenuConvertir'])}}},")
    h += ["};", "", "struct IdiomaWindows { WORD primario; const wchar_t* codigo; };",
          "static const IdiomaWindows WINDOWS_IDIOMAS[] = {"]
    h += [f"    {{0x{LANGID[c]:02X}, L\"{c}\"}}," for c in textos]
    h += ["};", ""]
    return "\n".join(iss) + "\n", "\n".join(h)


def main(args: list[str]) -> int:
    if args[:1] == ["instalador"]:
        iss, h = generar_instalador()
        with open(MENSAJES_ISS, "w", encoding="utf-8-sig", newline="\n") as f:
            f.write(iss)
        with open(TEXTOS_MENU_H, "w", encoding="utf-8", newline="\n") as f:
            f.write(h)
        print(f"{os.path.relpath(MENSAJES_ISS, RAIZ)} y {os.path.relpath(TEXTOS_MENU_H, RAIZ)}")
        return 0
    if args[:1] == ["catalogo"]:
        textos = textos_del_codigo()
        escribir("es", {t: t for t in textos})
        print(f"idiomas/es.json: {len(textos)} textos")
        return 0
    if args[:1] == ["revisar"]:
        sys.path.insert(0, RAIZ)
        import idioma
        catalogo = leer("es")
        malos = 0
        for codigo in idioma.IDIOMAS:
            if codigo == "es":
                continue
            try:
                lista = problemas(codigo, catalogo)
            except OSError:
                lista = ["no existe el archivo"]
            malos += len(lista)
            print(f"{codigo}: {'bien' if not lista else f'{len(lista)} problemas'}")
            for p in lista[:20]:
                print("   ", p)
        return 1 if malos else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
