# Idiomas de AventyaPDF

> Desde la revisión r136 (2026-10-06). AventyaPDF está en español, inglés,
> catalán, gallego y euskera. (r141, petición de Ricardo: «puedes quitar los
> idiomas francés e italiano, pues con el inglés como internacional es
> suficiente»; quien los tuviera elegidos pasa al inglés.)

## Cómo se elige el idioma

1. **Al instalar**: el instalador pregunta el idioma (propone el de Windows).
   Ese idioma se usa para el propio instalador y para la aplicación.
2. **Después**: menú **Ayuda › Idioma**. El cambio se ve la próxima vez que se
   abre AventyaPDF.
3. **Sin instalador** (Microsoft Store, o si nunca se eligió): el idioma de
   Windows si es uno de los cinco; si no, inglés.

Al actualizar, el instalador propone el idioma de la instalación anterior y
no cambia el que se haya puesto después en Ayuda › Idioma, salvo que en el
instalador se elija otro distinto.

También salen en el idioma elegido:

- el submenú **AventyaPDF** del botón derecho del Explorador (Windows 11 y
  «Mostrar más opciones»);
- el **sello visible de la firma digital** («Motivo:», «Lugar:»,
  «Firmado:»…);
- los botones estándar de Windows que dibuja Qt («Sí», «No», menú de copiar y
  pegar en los campos). Qt no trae gallego ni euskera: ahí salen en español.

## Dónde están los textos

| Archivo | Qué contiene |
|---|---|
| `idiomas/es.json` | Todos los textos de la aplicación en español (el idioma de referencia). Se genera desde el código, no se edita a mano. |
| `idiomas/<código>.json` | La traducción de cada texto: `"texto en español": "traducción"`. Códigos: `en`, `fr`, `it`, `ca`, `gl`, `eu`. |
| `docs/idiomas/glosario_<código>.md` | Términos elegidos en cada idioma (firma, certificado, sellado de tiempo…), para que las correcciones y los textos nuevos sean coherentes. |
| `empaquetado/idiomas/instalador*.json` | Textos del instalador y del menú del botón derecho. |
| `empaquetado/idiomas/mensajes.iss`, `shell/textos_menu.h` | Generados a partir de los anteriores para el instalador y el menú de Windows 11. No se editan a mano. |
| `docs/manual/<código>.md` | (r138) El manual de cada idioma (el español es el original). `python docs/manual/crear_manual.py` genera `MANUAL_<código>.pdf` (r141: no va en el instalador; la aplicación lo descarga de GitHub, de la rama `main`), con capturas de la aplicación en ese idioma, y las imágenes de las diapositivas del instalador (`empaquetado/diapositivas/`); `--revisar` comprueba que cada traducción tiene la estructura del original. |
| `presentacion.py` (`SLIDES`) | (r138) Las diapositivas de la presentación de inicio; el instalador enseña sus textos traducidos mientras instala (`herramientas_idioma.py instalador`). |
| `empaquetado/idiomas/Galician.isl`, `Basque.isl` | Mensajes estándar del instalador en gallego y euskera (traducciones no oficiales de Inno Setup). |

## Corregir una traducción

Se edita el valor en `idiomas/<código>.json` (se puede abrir con cualquier
editor de texto). Hay que respetar:

- **Los marcadores** entre llaves (`{nombre}`, `{n}`…), `%(ts)s` y las
  etiquetas HTML: se copian igual, aunque pueden cambiar de sitio en la frase.
- **El `&` de los menús**: marca la letra subrayada; uno por texto.

Las pruebas automáticas (`.\run.ps1 -Pruebas`) avisan si falta un texto o si
un marcador no coincide.

## Para quien programa

- Todo texto visible se escribe en español dentro de `tr("…")`
  (`from idioma import tr`). Con datos: `tr("Abierto: {nombre}").format(nombre=…)`;
  nunca una f-string dentro de `tr()`.
- No pasan por `tr()` los textos que son datos y no interfaz: claves de
  ajustes, tipos de anotación, contenido que se escribe dentro del PDF y que
  la aplicación vuelve a leer, nombres de campos, órdenes y rutas.
- Tras añadir o cambiar textos: `python herramientas_idioma.py catalogo` y
  traducir lo nuevo en cada idioma (`python herramientas_idioma.py revisar`
  dice qué falta). Si se cambian los textos del instalador:
  `python herramientas_idioma.py instalador`.
- Los textos se traducen al importar cada módulo: el idioma se decide antes
  (`idioma.py`) y un cambio se aplica al volver a abrir la aplicación.
