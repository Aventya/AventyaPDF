"""
Prueba de concepto (r66): interfaz WinUI 3 desde Python con PyWinRT, con el
núcleo de AventyaPDF (PyMuPDF) debajo. NO es parte de la aplicación.

    <venv-winui3>\\Scripts\\python.exe prototipos\\winui3\\visor_poc.py [archivo.pdf]

Entorno aparte (no el de la app): %LOCALAPPDATA%\\aventyapdf\\venv-winui3, con
winui3-Microsoft.UI.Xaml* 3.2.1 (Windows App SDK 1.7), winrt-runtime 3.2.1 y
PyMuPDF. Ver docs/plan_migracion_winui3.md, §10.

Qué comprueba:
* ventana WinUI 3 con el XAML cargado en tiempo de ejecución (XamlReader),
  fondo Mica y barra de título propia con el icono de la app;
* barra de comandos con Fluent UI System Icons (la fuente de vendor/, como la
  app Qt);
* página del PDF renderizada con PyMuPDF y volcada a un WriteableBitmap;
* Ctrl + rueda = zoom (se vuelve a renderizar, nítido), rueda sola = desplazar;
* clic sobre la página → coordenadas de la página en puntos (las de PyMuPDF).
"""
import ctypes
import os
import sys
from typing import Tuple, Union

from typing_extensions import override

# Empaquetado con PyInstaller, los datos (vendor/, el PDF de ejemplo) van en
# _internal con el mismo árbol que en el proyecto.
RAIZ = (sys._MEIPASS if getattr(sys, "frozen", False)
        else os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.insert(0, RAIZ)

import fitz  # noqa: E402
import icons  # noqa: E402  (sin Qt: solo lee el JSON de códigos)

from winrt.system import Array  # noqa: E402
from winrt.windows.graphics import SizeInt32  # noqa: E402
from winrt.windows.ui.xaml.interop import TypeKind, TypeName  # noqa: E402
from winui3.microsoft.ui.xaml import (  # noqa: E402
    Application, ApplicationInitializationCallbackParams, FrameworkElement,
    LaunchActivatedEventArgs, Window,
)
from winui3.microsoft.ui.xaml.controls import (  # noqa: E402
    AppBarButton, Image, ScrollViewer, TextBlock, XamlControlsResources,
)
from winui3.microsoft.ui.xaml.markup import (  # noqa: E402
    IXamlMetadataProvider, IXamlType, XamlReader, XmlnsDefinition,
)
from winui3.microsoft.ui.xaml.media import MicaBackdrop  # noqa: E402
from winui3.microsoft.ui.xaml.media.imaging import BitmapImage, WriteableBitmap  # noqa: E402
from winrt.windows.foundation import Uri  # noqa: E402
from winui3.microsoft.ui.xaml.xamltypeinfo import XamlControlsXamlMetaDataProvider  # noqa: E402
from winui3.microsoft.windows.applicationmodel.dynamicdependency.bootstrap import (  # noqa: E402
    InitializeOptions, initialize,
)

FUENTE_ICONOS = os.path.join(RAIZ, "vendor", "fonts", "fluent-icons", "FluentSystemIcons-Regular.ttf")
PDF_POR_DEFECTO = os.path.join(RAIZ, "Formulario.pdf")
ZOOM_MIN, ZOOM_MAX = 0.25, 6.0


def _xml(texto: str) -> str:
    return texto.replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;")


def _glifo(clave: str) -> str:
    return f"&#x{ord(icons.glyph(clave)):X};"


def _uri_recurso(ruta: str) -> str:
    """URI de un archivo propio para XAML. WinUI 3 solo carga fuentes propias
    con ms-appx:///, que en una app sin empaquetar (MSIX) es la carpeta del
    .exe: vale con PyInstaller (vendor/ va en _internal) pero no con
    python.exe, donde es la carpeta de Python (probado: ni file:/// ni la
    ruta absoluta cargan la fuente)."""
    base = os.path.dirname(os.path.abspath(sys.executable))
    rel = os.path.relpath(os.path.abspath(ruta), base)
    if getattr(sys, "frozen", False) and not rel.startswith(".."):
        return "ms-appx:///" + rel.replace("\\", "/")
    return "file:///" + os.path.abspath(ruta).replace("\\", "/")


def _boton(nombre: str, icono: str, etiqueta: str) -> str:
    familia = _uri_recurso(FUENTE_ICONOS) + "#" + icons.ICON_FAMILY
    return (f'<AppBarButton x:Name="{nombre}" Label="{_xml(etiqueta)}" ToolTipService.ToolTip="{_xml(etiqueta)}">'
            f'<AppBarButton.Icon><FontIcon FontFamily="{familia}" Glyph="{_glifo(icono)}"/></AppBarButton.Icon>'
            f'</AppBarButton>')


XAML = f"""
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml">
  <Grid>
    <Grid.RowDefinitions>
      <RowDefinition Height="32"/>
      <RowDefinition Height="Auto"/>
      <RowDefinition Height="*"/>
      <RowDefinition Height="Auto"/>
    </Grid.RowDefinitions>

    <Grid x:Name="barraTitulo" Grid.Row="0" Padding="12,0,0,0">
      <StackPanel Orientation="Horizontal" Spacing="10" VerticalAlignment="Center">
        <Image x:Name="iconoApp" Width="16" Height="16"/>
        <TextBlock x:Name="titulo" Text="AventyaPDF — prueba WinUI 3"
                   Style="{{StaticResource CaptionTextBlockStyle}}" VerticalAlignment="Center"/>
      </StackPanel>
    </Grid>

    <CommandBar Grid.Row="1" DefaultLabelPosition="Right" HorizontalAlignment="Left"
                Background="Transparent" IsDynamicOverflowEnabled="False">
      {_boton("anterior", "prev", "Página anterior")}
      {_boton("siguiente", "next", "Página siguiente")}
      <AppBarSeparator/>
      {_boton("alejar", "zoom_out", "Alejar")}
      {_boton("acercar", "zoom100", "Acercar")}
      {_boton("ancho", "type", "Ajustar al ancho")}
    </CommandBar>

    <ScrollViewer x:Name="desplazador" Grid.Row="2" Margin="8,0,8,0" CornerRadius="8"
                  HorizontalScrollBarVisibility="Auto" VerticalScrollBarVisibility="Auto"
                  ZoomMode="Disabled"
                  Background="{{ThemeResource LayerFillColorDefaultBrush}}">
      <Border Padding="24" HorizontalAlignment="Center">
        <Image x:Name="pagina" Stretch="None"/>
      </Border>
    </ScrollViewer>

    <TextBlock x:Name="estado" Grid.Row="3" Margin="16,6,16,8"
               Style="{{StaticResource CaptionTextBlockStyle}}"/>
  </Grid>
</Window>
"""


class Visor:
    """La ventana y su estado (documento, página, zoom)."""

    def __init__(self, ruta_pdf: str):
        self.doc = fitz.open(ruta_pdf)
        self.nombre = os.path.basename(ruta_pdf)
        self.num = 0
        self.zoom = 1.0
        self.ultimo_clic = ""

        self.window = XamlReader.load(XAML).as_(Window)
        raiz = self.window.content.as_(FrameworkElement)
        buscar = raiz.find_name
        self.pagina = buscar("pagina").as_(Image)
        self.desplazador = buscar("desplazador").as_(ScrollViewer)
        self.estado = buscar("estado").as_(TextBlock)
        buscar("titulo").as_(TextBlock).text = f"{self.nombre} — AventyaPDF (prueba WinUI 3)"
        buscar("iconoApp").as_(Image).source = BitmapImage(Uri(_uri_recurso(icons.APP_ICON)))

        # Ventana de Windows 11: Mica, barra de título propia e icono de la app.
        self.window.system_backdrop = MicaBackdrop()
        self.window.extends_content_into_title_bar = True
        self.window.set_title_bar(buscar("barraTitulo").as_(FrameworkElement))
        self.window.app_window.set_icon(icons.APP_ICON)
        self.window.title = f"{self.nombre} — AventyaPDF (prueba WinUI 3)"   # Alt+Tab y barra de tareas
        self.window.app_window.resize(SizeInt32(1400, 900))

        acciones = {
            "anterior": lambda: self.ir(self.num - 1),
            "siguiente": lambda: self.ir(self.num + 1),
            "alejar": lambda: self.poner_zoom(self.zoom / 1.25),
            "acercar": lambda: self.poner_zoom(self.zoom * 1.25),
            "ancho": self.ajustar_ancho,
        }
        for nombre, fn in acciones.items():
            buscar(nombre).as_(AppBarButton).add_click(lambda s, e, fn=fn: fn())

        self.desplazador.add_pointer_wheel_changed(self._rueda)
        self.pagina.add_pointer_pressed(self._clic)

    # ── renderizado ─────────────────────────────────────────────────────── #

    def _escala_pantalla(self) -> float:
        xr = self.window.content.xaml_root
        return xr.rasterization_scale if xr is not None else 1.0

    def renderizar(self):
        """La página a `zoom` (1 = 100 %) con los píxeles reales de la pantalla,
        para que se vea nítida a 125 %, 150 %…; la imagen mide en DIP."""
        escala = self._escala_pantalla()
        pag = self.doc[self.num]
        pix = pag.get_pixmap(matrix=fitz.Matrix(self.zoom * escala, self.zoom * escala), alpha=True)
        # PyMuPDF da RGBA; WriteableBitmap quiere BGRA (premultiplicado; la
        # página es opaca, así que da igual).
        datos = bytearray(pix.samples)
        datos[0::4], datos[2::4] = datos[2::4], datos[0::4]
        wb = WriteableBitmap(pix.width, pix.height)
        memoryview(wb.pixel_buffer)[:len(datos)] = datos
        wb.invalidate()
        self.pagina.source = wb
        self.pagina.width = pix.width / escala
        self.pagina.height = pix.height / escala
        self._estado()

    def _estado(self):
        texto = f"Página {self.num + 1} de {len(self.doc)}   ·   Zoom {self.zoom * 100:.0f} %"
        if self.ultimo_clic:
            texto += f"   ·   {self.ultimo_clic}"
        self.estado.text = texto

    # ── acciones ────────────────────────────────────────────────────────── #

    def ir(self, n: int):
        if 0 <= n < len(self.doc):
            self.num = n
            self.ultimo_clic = ""
            self.renderizar()
            self.desplazador.change_view(0.0, 0.0, None)

    def poner_zoom(self, z: float):
        z = max(ZOOM_MIN, min(ZOOM_MAX, z))
        if abs(z - self.zoom) > 1e-6:
            self.zoom = z
            self.renderizar()

    def ajustar_ancho(self):
        disponible = self.desplazador.actual_width - 48 - 16      # Padding del Border + barra
        self.poner_zoom(disponible / self.doc[self.num].rect.width)

    # ── eventos ─────────────────────────────────────────────────────────── #

    def _rueda(self, sender, args):
        if ctypes.windll.user32.GetKeyState(0x11) & 0x8000:      # Ctrl pulsado
            delta = args.get_current_point(self.desplazador).properties.mouse_wheel_delta
            self.poner_zoom(self.zoom * (1.1 if delta > 0 else 1 / 1.1))
            args.handled = True

    def _clic(self, sender, args):
        p = args.get_current_point(self.pagina).position
        x, y = p.x / self.zoom, p.y / self.zoom          # DIP → puntos de la página
        self.ultimo_clic = f"Clic en la página: x = {x:.1f} pt, y = {y:.1f} pt"
        print(self.ultimo_clic, flush=True)
        self._estado()


class App(Application, IXamlMetadataProvider):
    """El runtime exige IXamlMetadataProvider en la clase Application.
    PyWinRT no admite argumentos en el constructor de una subclase de
    Application («Invalid parameter count»): la ruta va en un atributo de clase."""

    ruta_pdf = PDF_POR_DEFECTO

    def __init__(self) -> None:
        self._provider = XamlControlsXamlMetaDataProvider()
        self._ruta = App.ruta_pdf
        self.visor = None

    @override
    def _on_launched(self, args: LaunchActivatedEventArgs) -> None:
        self.resources.merged_dictionaries.append(XamlControlsResources())
        self.visor = Visor(self._ruta)
        self.visor.window.activate()
        # La escala de pantalla solo se conoce con la ventana ya en pantalla.
        self.visor.window.content.as_(FrameworkElement).add_loaded(
            lambda s, e: self.visor.renderizar())

    @override
    def get_xaml_type(self, type: Union[TypeName, Tuple[str, TypeKind]]) -> IXamlType:
        return self._provider.get_xaml_type(type)

    @override
    def get_xaml_type_by_full_name(self, full_name: str) -> IXamlType:
        return self._provider.get_xaml_type_by_full_name(full_name)

    @override
    def get_xmlns_definitions(self) -> Array[XmlnsDefinition]:
        return self._provider.get_xmlns_definitions()


def main() -> None:
    if len(sys.argv) > 1:
        App.ruta_pdf = sys.argv[1]

    def init(_: ApplicationInitializationCallbackParams) -> None:
        App()

    with initialize(options=InitializeOptions.ON_NO_MATCH_SHOW_UI):
        Application.start(init)


if __name__ == "__main__":
    main()
