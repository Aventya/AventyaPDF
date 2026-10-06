# AventyaPDF

Visor y editor de PDF para Windows (Python, PyQt6 y PyMuPDF) de Aventya Asesoría Integral SL. Lo dirige Ricardo, que no programa: explícale en español claro qué cambia para quien usa la aplicación, sin jerga.

## Cada cambio
- Lee `MEMORIA_EVOLUTIVA.md` antes de tocar código —sobre todo los invariantes de §4— y actualízala al terminar según su §9: revisión, fecha y una fila en §10.
- Textos visibles en siete idiomas: escríbelos en español dentro de `tr("…")` (invariante 61 de la memoria) y, si añades o cambias alguno, `python herramientas_idioma.py catalogo` y tradúcelos en `idiomas/*.json` (guía en `docs/idiomas.md`).
- Pruebas: `.\run.ps1 -Pruebas` en Windows. En Linux (sesiones en la nube) fallan unas 36 que dependen de Windows (fuentes, Word, Tesseract, certificados): compara con el resultado de antes de tu cambio, no con cero.

## Ramas
Ricardo trabaja desde dos equipos. El trabajo en curso va a la rama **`desarrollo`**; `main` solo recibe lo que se publica.
- «Descarga la última versión» = `git fetch`, `git switch desarrollo`, `git pull`.
- Al terminar: commit y `git push` a `desarrollo`.

## Publicar una versión
Solo cuando Ricardo lo pida; los pasos están en §8 «Publicar una versión» de la memoria.
- El instalador se compila en el equipo `C:\Users\ricardo\Proyectos\AventyaPDF`, que tiene Inno Setup, Visual Studio y el certificado del menú contextual. Una sesión en la nube solo puede prepararla: `APP_VERSION`, la versión anterior en `docs/historial_versiones.md` y las notas en `empaquetado/notas/<versión>.md`.
- Una versión publicada no se toca: si aparece un fallo, se publica la siguiente. Quien ya la instaló no recibiría aviso de un instalador sustituido.
- Retirar la publicación anterior necesita que Ricardo lo autorice en la sesión.
