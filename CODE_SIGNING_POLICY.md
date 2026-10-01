# Política de firma — AventyaPDF

AventyaPDF es un proyecto de código abierto (licencia **GNU AGPL-3.0**,
ver [LICENSE](LICENSE)) desarrollado y mantenido por **Aventya Asesoría
Integral SL**. Esta página describe cómo se firman los instaladores de
Windows que se publican en
[Releases](https://github.com/Aventya/AventyaPDF/releases), para que
cualquiera pueda comprobar que el instalador que descarga es exactamente el
que publicó este repositorio, sin modificaciones.

## Con qué se firma

Con **[Sigstore](https://www.sigstore.dev)**, el sistema de firma abierto de
la Linux Foundation (OpenSSF). No hay certificado ni clave privada que
guardar: en cada publicación, el flujo de GitHub Actions
[`.github/workflows/firmar-publicacion.yml`](.github/workflows/firmar-publicacion.yml)
obtiene de GitHub una identidad temporal («este flujo, de este
repositorio»), Sigstore emite con ella un certificado de unos minutos, se
firma el instalador y la firma queda anotada en su registro público de
transparencia (Rekor). La firma se publica junto al instalador como
`AventyaPDF-Setup-<versión>.exe.sigstore.json`.

(Se pidió antes un certificado Authenticode gratuito a SignPath Foundation,
pero no lo conceden a proyectos tan recientes como este.)

## Cómo se compila y se firma

1. El código fuente vive en este repositorio, público, bajo licencia AGPL-3.0.
2. El instalador se compila desde ese código con
   [`empaquetado/construir.ps1`](empaquetado/construir.ps1) (lanzador propio
   + Inno Setup), que antes de crearlo pasa un autodiagnóstico y, para cada
   publicación, una instalación de prueba real.
3. Al publicar la versión en GitHub, el flujo `firmar-publicacion.yml` firma
   el instalador con Sigstore, comprueba la firma y la sube a la publicación.
4. El instalador solo lleva el código propio: Python, sus paquetes y las
   fuentes los descarga al instalar de sus sitios oficiales, comprobando la
   huella SHA-256 de cada archivo, fijada en el instalador firmado.

Cómo comprobar la firma: [docs/verificar_instalador.md](docs/verificar_instalador.md).

## Lo que no hace

Sigstore no es una firma **Authenticode** de Windows: **Windows SmartScreen
sigue avisando** de «editor desconocido» al ejecutar el instalador («Más
información» → «Ejecutar de todas formas»). Eso solo lo quita un certificado
de firma de código de una autoridad reconocida por Windows.

## Roles del equipo

| Rol | Persona |
| :-- | :-- |
| Autor / responsable del proyecto | Ricardo (Aventya Asesoría Integral SL) |
| Revisor de cambios | Ricardo |
| Quien publica (y con ello firma) cada versión | Ricardo |

AventyaPDF es, hoy, un proyecto mantenido por una sola persona: todo cambio
que no viene de Ricardo se revisa antes de aceptarse, y solo él publica
versiones.

## Privacidad

AventyaPDF **no recoge ni envía ningún dato personal ni de uso**. La única
conexión de red que hace la aplicación es, si el usuario lo pide (o al
iniciar, si no lo ha desactivado en «Ayuda › Avisar de actualizaciones al
iniciar»), una consulta a la API pública de GitHub para comprobar si hay una
versión más reciente publicada — una petición anónima, sin identificar al
usuario ni enviar información suya. La firma con Sigstore no incluye datos
personales: la identidad que figura es la del repositorio y su flujo.

## Desinstalar

AventyaPDF se instala para el usuario actual, sin permisos de administrador
(salvo la extensión del menú contextual del Explorador, que si el usuario la
acepta pide permiso una vez para confiar en el certificado propio del
paquete). Se desinstala igual que cualquier otro programa, desde
«Configuración › Aplicaciones» de Windows, o con el acceso directo
«Desinstalar AventyaPDF» del menú Inicio.
