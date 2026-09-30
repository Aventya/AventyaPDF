# Code signing policy — AventyaPDF

AventyaPDF es un proyecto de código abierto (licencia **GNU AGPL-3.0**,
ver [LICENSE](LICENSE)) desarrollado y mantenido por **Aventya Asesoría
Integral SL**. Esta página describe cómo se firman digitalmente los
instaladores de Windows que se publican en
[Releases](https://github.com/Aventya/AventyaPDF/releases), para que
Windows SmartScreen y los antivirus reconozcan al editor y el usuario pueda
verificar que el instalador que descarga es, de verdad, un build automático
construido a partir del código fuente de este repositorio, sin
modificaciones.

## Quién firma

La firma de los instaladores de AventyaPDF la hace **[SignPath.io](https://signpath.io)**,
con un certificado emitido a través de **SignPath Foundation** — su programa
gratuito de firma de código para proyectos de código abierto. AventyaPDF no
tiene ni gestiona la clave privada del certificado de firma: solo el equipo
de SignPath la posee, dentro de su infraestructura, y firma únicamente los
binarios que llegan desde el sistema de compilación de confianza de este
proyecto (ver «Cómo se compila y se firma» más abajo).

## Roles del equipo

| Rol | Persona |
| :-- | :-- |
| Autor / responsable del proyecto | Ricardo (Aventya Asesoría Integral SL) |
| Revisor de cambios | Ricardo |
| Aprobador de la firma de cada versión | Ricardo |

AventyaPDF es, hoy, un proyecto mantenido por una sola persona: todo cambio
que no viene de Ricardo se revisa antes de aceptarse, y cada publicación de
una versión firmada la aprueba él mismo, a mano, antes de que SignPath la
firme.

## Cómo se compila y se firma

1. El código fuente vive en este repositorio, público, bajo licencia AGPL-3.0.
2. Cada versión publicada se compila desde cero (lanzador propio + Inno Setup)
   en un sistema de compilación de confianza («trusted build system» de
   SignPath), no en un equipo personal, para que la firma dé fe de que el
   binario sale de verdad de este código fuente.
3. El instalador sin firmar se envía a SignPath, que lo firma con el
   certificado de SignPath Foundation tras la aprobación manual de la
   publicación.
4. El instalador firmado es el que se publica en
   [Releases](https://github.com/Aventya/AventyaPDF/releases).

## Qué se firma

El instalador de Windows (`AventyaPDF-Setup-<versión>.exe`, Inno Setup) y el
ejecutable de la aplicación que contiene.

## Privacidad

AventyaPDF **no recoge ni envía ningún dato personal ni de uso**. La única
conexión de red que hace la aplicación es, si el usuario lo pide (o al
iniciar, si no lo ha desactivado en «Ayuda › Avisar de actualizaciones al
iniciar»), una consulta a la API pública de GitHub para comprobar si hay una
versión más reciente publicada — una petición anónima, sin identificar al
usuario ni enviar información suya. Puede desactivarse desde el menú
«Ayuda». SignPath, por su parte, no recibe del proceso de firma ningún dato
de los usuarios finales de AventyaPDF: solo ve el binario que se le envía a
firmar.

## Desinstalar

AventyaPDF se instala para el usuario actual, sin permisos de administrador
(salvo la extensión del menú contextual del Explorador, que si el usuario la
acepta pide permiso una vez para confiar en el certificado propio del
paquete). Se desinstala igual que cualquier otro programa, desde
«Configuración › Aplicaciones» de Windows, o con el acceso directo
«Desinstalar AventyaPDF» del menú Inicio.

---

*AventyaPDF agradece a [SignPath.io](https://signpath.io) y a
**SignPath Foundation** la firma de código gratuita para proyectos de
código abierto.*
