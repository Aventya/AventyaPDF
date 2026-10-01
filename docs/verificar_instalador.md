# Comprobar que el instalador es auténtico

Cada instalador de AventyaPDF que se publica en
[Releases](https://github.com/Aventya/AventyaPDF/releases/latest) va firmado
con **[Sigstore](https://www.sigstore.dev)**: junto a
`AventyaPDF-Setup-<versión>.exe` está su firma,
`AventyaPDF-Setup-<versión>.exe.sigstore.json`.

La firma la hace el flujo de GitHub Actions
[`firmar-publicacion.yml`](../.github/workflows/firmar-publicacion.yml) de
este repositorio en cuanto se publica la versión, sin claves privadas que
guardar: la identidad que certifica es «el repositorio
`Aventya/AventyaPDF` en GitHub», y la firma queda además anotada en el
registro público de transparencia de Sigstore. Si alguien modifica el
instalador (una copia en otra web, un archivo dañado al descargar…), la
comprobación falla.

## Cómo se comprueba

Hace falta Python. En una consola (PowerShell), en la carpeta donde se
descargaron los dos archivos:

```powershell
pip install sigstore
sigstore verify github AventyaPDF-Setup-0.9.8.exe --bundle AventyaPDF-Setup-0.9.8.exe.sigstore.json --repository Aventya/AventyaPDF
```

(cambiando `0.9.8` por la versión descargada). Si todo está bien, responde:

```
OK: AventyaPDF-Setup-0.9.8.exe
```

Con [cosign](https://docs.sigstore.dev/cosign/system_config/installation/) en
vez de Python:

```powershell
cosign verify-blob AventyaPDF-Setup-0.9.8.exe --bundle AventyaPDF-Setup-0.9.8.exe.sigstore.json --certificate-identity-regexp "^https://github.com/Aventya/AventyaPDF/" --certificate-oidc-issuer https://token.actions.githubusercontent.com
```

## Qué demuestra y qué no

* **Sí**: que el archivo es exactamente el que se publicó en este
  repositorio y lo firmó su flujo de GitHub, y cuándo.
* **Y lo que descarga**: el instalador lleva dentro la huella SHA-256 de cada
  componente que descarga al instalar (Python, sus paquetes y las fuentes,
  ver [empaquetado.md](empaquetado.md)) y no instala nada que no coincida. Un
  instalador auténtico solo instala componentes auténticos.
* **No**: Sigstore no es una firma Authenticode de Windows. **Windows
  SmartScreen seguirá avisando** de «editor desconocido» al ejecutarlo
  («Más información» → «Ejecutar de todas formas»): eso solo lo quita un
  certificado de firma de código de una autoridad reconocida por Windows.
