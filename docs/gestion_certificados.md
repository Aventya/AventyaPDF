# Gestión de Certificados Digitales

Este documento detalla la lógica de consulta, exportación y almacenamiento seguro de identidades y certificados digitales implementada en [cert_manager.py](file:///a:/CARPETA%20IA/RICARDO/AVENTYAPDF/cert_manager.py) y el script auxiliar [create_test_cert.py](file:///a:/CARPETA%20IA/RICARDO/AVENTYAPDF/create_test_cert.py).

## Índice del Documento
1. [El Almacén Personal de Windows](#el-almacén-personal-de-windows)
2. [Exportación Segura de Certificados de Windows](#exportación-segura-de-certificados-de-windows)
3. [Certificados PKCS#12 (PFX/P12) y Almacenamiento Seguro](#certificados-pkcs12-pfxp12-y-almacenamiento-seguro)
4. [Persistencia de la Configuración](#persistencia-de-la-configuración)
5. [Interfaz del Selector de Certificados (CertPickerDialog)](#interfaz-del-selector-de-certificados-certpickerdialog)
6. [Generación de Certificado de Pruebas (create_test_cert.py)](#generación-de-certificado-de-pruebas-create_test_certpy)
7. [Relación con otros Documentos](#relación-con-otros-documentos)

---

## El Almacén Personal de Windows

La aplicación permite firmar directamente utilizando certificados instalados en el sistema operativo del usuario. El método [list_windows_certs()](file:///a:/CARPETA%20IA/RICARDO/AVENTYAPDF/cert_manager.py#L58) realiza la enumeración de dichos certificados:

* **Acceso**: Lee el almacén Personal del usuario ("MY") a través de la función nativa de Python `ssl.enum_certificates("MY")`.
* **Filtros Aplicados**:
  * **Caducidad**: Descarta certificados cuya fecha de validez haya expirado (`expiry < now`).
  * **Uso de Firma (KeyUsage)**: Filtra certificados orientados únicamente a cifrado de datos. Si un certificado no especifica KeyUsage (común en ciertos emisores españoles como FNMT o ACCV), o bien posee habilitados los usos de firma digital (`digital_signature` o `content_commitment`), se incluye en la lista.
* **Procesamiento de Identidad**: Extrae los campos *Common Name* (CN), NIF (limpiando prefijos fiscales con `_clean_id`) y Organización, calculando la huella digital SHA-1 en mayúsculas (`thumbprint`) para identificar unívocamente el certificado.

---

## Exportación Segura de Certificados de Windows

Debido a que el motor criptográfico `pyHanko` requiere acceso a la clave privada en formato PKCS#12 para firmar localmente, la aplicación implementa el método [export_windows_cert_to_pfx(thumbprint)](file:///a:/CARPETA%20IA/RICARDO/AVENTYAPDF/cert_manager.py#L120):

* **Procedimiento**: Lanza un subproceso asíncrono de **PowerShell** que ejecuta directamente código **.NET** (`System.Security.Cryptography.X509Certificates.X509Store`). Esto evita depender de módulos de PowerShell externos o de permisos administrativos.
* **Seguridad de la Clave**: 
  1. Genera una contraseña segura y aleatoria de 24 caracteres alfanuméricos mediante `secrets.choice`.
  2. Solicita al motor .NET exportar el certificado y su clave asociada a un array de bytes cifrado con dicha contraseña temporal.
  3. Escribe el array en un archivo temporal `.pfx` en el directorio temporal del usuario.
* **Restricción**: Si la clave privada del certificado del almacén de Windows se marcó en su instalación como "no exportable" (o se encuentra en una tarjeta inteligente / DNIe), el proceso de exportación de .NET fallará de forma segura y la aplicación capturará la excepción para notificar el problema detalladamente al usuario.

---

## Certificados PKCS#12 (PFX/P12) y Almacenamiento Seguro

Además de los certificados del almacén de Windows, el usuario puede seleccionar un certificado en formato de archivo físico (`.pfx` / `.p12`):

* **Almacenamiento de Contraseñas (`keyring`)**:
  * Para no almacenar la contraseña en texto plano en los archivos de configuración, se utiliza la librería `keyring`.
  * La contraseña se delega al Administrador de Credenciales nativo de Windows (Windows Credential Manager) bajo el identificador de servicio `aventyapdf-signing` y asociada a la ruta absoluta del archivo PFX.
  * **Fallback**: Si la librería `keyring` no está instalada o falla, la aplicación almacena la contraseña en la configuración local como medida de contingencia.

---

## Persistencia de la Configuración

La aplicación guarda el certificado activo para evitar volver a solicitarlo en firmas sucesivas mediante el uso de la clase `QSettings` de Qt:

* **Huella Guardada (`load_saved_cert()`)**: Carga los datos de configuración. Si el tipo es `windows`, recupera la huella (`_K_THUMB`) y el nombre para mostrar. Si el tipo es `file`, recupera la ruta física y solicita la contraseña de forma transparente a `keyring`.
* **Guardado Atómico (`save_cert()`)**: Almacena las variables correspondientes a disco y fuerza la sincronización inmediata del registro mediante `.sync()`.
* **Eliminar Credenciales (`forget_cert()`)**: Borra todas las claves del registro de configuración y solicita a `keyring` la eliminación definitiva de la contraseña del Administrador de Credenciales del sistema.

---

## Interfaz del Selector de Certificados (CertPickerDialog)

La interfaz gráfica del selector de certificados se define en la clase [CertPickerDialog](file:///a:/CARPETA%20IA/RICARDO/AVENTYAPDF/cert_manager.py#L353) y consta de dos pestañas:
1. **Pestaña Almacén de Windows (`_WinCertTab`)**: Muestra una tabla con el nombre del titular, NIF u organización y la fecha de caducidad de todos los certificados detectados en el sistema operativo.
2. **Pestaña Archivo (`_FileCertTab`)**: Permite examinar el sistema de archivos local para elegir un archivo `.pfx` o `.p12`, ingresar su contraseña de acceso y activar el interruptor para recordar el certificado de forma permanente.

---

## Generación de Certificado de Pruebas (create_test_cert.py)

Para facilitar la verificación del sistema de firmas por parte de desarrolladores o en entornos donde no existan certificados instalados, el proyecto incluye el script ejecutable [create_test_cert.py](file:///a:/CARPETA%20IA/RICARDO/AVENTYAPDF/create_test_cert.py).

* **Funcionamiento**: Genera una clave RSA de 2048 bits y construye un certificado autofirmado válido por un año utilizando la API de `cryptography.x509`.
* **Datos Configurados**:
  * País: `ES`
  * Organización: `Aventya Software S.L.`
  * Nombre: `Usuario de Pruebas Aventya`
* **Salida**: Empaqueta la clave y el certificado en un archivo PKCS#12 llamado `test_certificate.pfx` protegido por la contraseña por defecto `1234`.

---

## Relación con otros Documentos

Este fichero se relaciona directamente con:
* **[Arquitectura General (arquitectura.md)](arquitectura.md)**: Estructura del flujo de datos de identidades.
* **[Firma Digital PAdES (firma_digital.md)](firma_digital.md)**: Destinatario de los archivos PFX y contraseñas para el proceso de firmado.
* **[Interfaz Gráfica y Visor (interfaz_grafica.md)](interfaz_grafica.md)**: El panel de opciones contextuales de firma que lee y muestra el estado del certificado activo.
