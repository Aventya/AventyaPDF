"""
Genera el icono de Windows de la aplicación y las imágenes del instalador:

    python create_app_icon.py

Origen: ICONO.png (en la raíz del proyecto, cuadrado, con transparencia).
ICONO.svg no sirve de origen: no es vectorial, solo envuelve el mismo PNG
de 596 px (r64).

Resultados:

* vendor/icono/aventyapdf.ico, con los tamaños oficiales que pide Windows
  para el icono de una aplicación (guía «Construct icons» de Microsoft):
  16, 20, 24, 30, 32, 36, 40, 48, 60, 64, 72, 80, 96 y 256 px. Así cada sitio
  (barra de título, barra de tareas, Alt+Tab, Explorador en cada vista, menú
  Inicio, «Acerca de», instalador y desinstalador) coge el tamaño exacto a
  cada escala de pantalla (100 %–400 %) en vez de estirar otro.
* empaquetado/imagenes/asistente_pequena_*.bmp y asistente_grande_*.bmp: la
  imagen de la esquina del asistente de Inno Setup y la del lateral de la
  bienvenida, una por escala de pantalla (100 %, 150 %, 200 %, 250 %). Inno
  elige la que mejor encaja (WizardSmallImageFile / WizardImageFile).

Cada tamaño se reduce por separado desde el original con Lanczos (no en
cadena, que acumularía desenfoque). Como los iconos de Windows 11, la placa
deja un margen de 1/16 del lado desde 24 px (16 px de aire a 256); a 16 y 20
px no, que cada píxel cuenta. De 48 px para abajo se enfoca un poco (máscara
de enfoque) para que la «A» y «PDF» no queden borrosos.

Pillow solo hace falta para GENERAR; la aplicación usa el archivo .ico (Qt lo
lee sin nada más) e Inno Setup los .bmp.
"""
import os
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))
ORIGEN = os.path.join(RAIZ, "ICONO.png")
DESTINO = os.path.join(RAIZ, "vendor", "icono", "aventyapdf.ico")
IMAGENES_INSTALADOR = os.path.join(RAIZ, "empaquetado", "imagenes")
TAMANOS = (16, 20, 24, 30, 32, 36, 40, 48, 60, 64, 72, 80, 96, 256)
# Escala de pantalla → tamaño de las imágenes del asistente de Inno Setup
# (los que recomienda su documentación para WizardStyle=modern).
ASISTENTE_PEQUENA = {100: (55, 55), 150: (83, 80), 200: (110, 106), 250: (138, 140)}
ASISTENTE_GRANDE = {100: (164, 314), 150: (246, 459), 200: (328, 604), 250: (410, 797)}
FONDO_ASISTENTE = (255, 255, 255)        # el asistente «modern» es blanco
FONDO_LATERAL = (243, 243, 243)          # gris de Windows 11 para el lateral


def _margen(t: int) -> int:
    return t // 16 if t >= 24 else 0


def _icono(original, t: int):
    """El icono a t px: con su margen y, si es pequeño, enfocado."""
    from PIL import Image, ImageFilter
    m = _margen(t)
    placa = original.resize((t - 2 * m, t - 2 * m), Image.Resampling.LANCZOS)
    if t <= 48:
        # Se enfoca el color y se deja la transparencia de Lanczos: enfocar
        # el alfa pondría un halo en el borde redondeado.
        rgb = placa.convert("RGB").filter(ImageFilter.UnsharpMask(radius=0.8, percent=60, threshold=0))
        rgb.putalpha(placa.getchannel("A"))
        placa = rgb
    lienzo = Image.new("RGBA", (t, t), (0, 0, 0, 0))
    lienzo.paste(placa, (m, m))
    return lienzo


def _sobre_fondo(original, tamano, lado, fondo, alto_centro):
    """Imagen del asistente: el icono de `lado` px sobre un fondo liso (Inno
    no mezcla bien la transparencia), centrado en horizontal y con su centro a
    `alto_centro` (fracción del alto)."""
    from PIL import Image
    ancho, alto = tamano
    img = Image.new("RGBA", tamano, fondo + (255,))
    ico = _icono(original, lado)
    img.alpha_composite(ico, ((ancho - lado) // 2, round(alto * alto_centro - lado / 2)))
    return img.convert("RGB")


def main() -> int:
    from PIL import Image          # aquí: la app y las pruebas importan TAMANOS sin Pillow
    if not os.path.isfile(ORIGEN):
        print(f"No se encuentra {ORIGEN}", file=sys.stderr)
        return 1
    original = Image.open(ORIGEN).convert("RGBA")
    if original.width != original.height:
        # Se centra en un lienzo cuadrado transparente: sin deformar.
        lado = max(original.size)
        lienzo = Image.new("RGBA", (lado, lado), (0, 0, 0, 0))
        lienzo.paste(original, ((lado - original.width) // 2, (lado - original.height) // 2))
        original = lienzo

    marcos = [_icono(original, t) for t in TAMANOS]
    os.makedirs(os.path.dirname(DESTINO), exist_ok=True)
    marcos[-1].save(DESTINO, format="ICO", sizes=[(t, t) for t in TAMANOS],
                    append_images=marcos[:-1])
    print(f"{DESTINO}: {', '.join(str(t) for t in TAMANOS)} px")

    os.makedirs(IMAGENES_INSTALADOR, exist_ok=True)
    for escala, tam in ASISTENTE_PEQUENA.items():
        ruta = os.path.join(IMAGENES_INSTALADOR, f"asistente_pequena_{escala}.bmp")
        _sobre_fondo(original, tam, min(tam), FONDO_ASISTENTE, 0.5).save(ruta)
    for escala, tam in ASISTENTE_GRANDE.items():
        ruta = os.path.join(IMAGENES_INSTALADOR, f"asistente_grande_{escala}.bmp")
        _sobre_fondo(original, tam, round(tam[0] * 0.62), FONDO_LATERAL, 0.4).save(ruta)
    print(f"{IMAGENES_INSTALADOR}: asistente_pequena_*.bmp, asistente_grande_*.bmp "
          f"({', '.join(f'{e} %' for e in ASISTENTE_PEQUENA)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
