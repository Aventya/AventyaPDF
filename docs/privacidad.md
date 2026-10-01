# Política de privacidad de AventyaPDF

*Responsable: Aventya Asesoría Integral SL. Última actualización: 1 de octubre de 2026.*

AventyaPDF es un visor y editor de PDF que funciona **en tu equipo**. Los
documentos que abres, editas, firmas o reconoces con OCR **no salen de tu
equipo**: la aplicación no tiene servidores propios, no recoge datos
personales ni de uso, no lleva publicidad ni analítica y no comparte nada con
terceros.

## Conexiones a Internet

AventyaPDF solo se conecta a Internet en estos casos, y nunca envía tus
documentos ni datos que te identifiquen:

* **Comprobar si hay una versión nueva** (solo en la versión descargada de
  GitHub; en la de Microsoft Store las actualizaciones las gestiona la Store):
  una consulta anónima a la API pública de GitHub. Se puede desactivar en
  «Ayuda › Avisar de actualizaciones al iniciar».
* **Sellado de tiempo de una firma digital**, si lo activas al firmar: se
  envía al servidor de sellado que elijas un resumen criptográfico (hash) del
  documento, no el documento.
* **Idiomas de OCR adicionales**, si los pides: se descargan del repositorio
  público de Tesseract en GitHub.
* **Instalación** (solo la versión descargada de GitHub): el instalador
  descarga Python, sus componentes y las fuentes tipográficas de sus sitios
  oficiales.

## Datos que se guardan en tu equipo

La configuración (documentos recientes, preferencias, opciones de firma) se
guarda en tu perfil de Windows. Si eliges recordar la contraseña de un
certificado `.pfx`, se guarda en el Administrador de credenciales de Windows.
Todo ello se borra al desinstalar la aplicación desde la Microsoft Store, y
en la versión de GitHub queda en `%LOCALAPPDATA%\aventyapdf` hasta que lo
borres.

## Contacto

Para cualquier consulta sobre privacidad, abre una incidencia en
[github.com/Aventya/AventyaPDF/issues](https://github.com/Aventya/AventyaPDF/issues).
