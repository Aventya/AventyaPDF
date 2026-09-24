"""
Autodiagnóstico de la aplicación (r62): comprueba, sin mostrar ninguna ventana,
que todo lo que necesita AventyaPDF está dentro y funciona. Sirve sobre todo
para la aplicación ya empaquetada (AventyaPDF.exe no tiene consola: sus errores
no se ven), y lo usa empaquetado/construir.ps1 tras cada compilación.

    AventyaPDF.exe --autodiagnostico resultado.json [certificado.pfx contraseña]

Escribe en `resultado.json` una lista de comprobaciones {nombre, ok, detalle}
y sale con código 0 si todas han ido bien y 1 si no. Con un certificado de
pruebas, además firma, verifica y quita la firma de un PDF.
"""
import json
import os
import sys
import tempfile
import time
import traceback

ARG = "--autodiagnostico"


def _comprobar(resultados: list, nombre: str, fn) -> None:
    t = time.time()
    try:
        detalle = fn() or ""
        resultados.append(dict(nombre=nombre, ok=True, detalle=str(detalle),
                               segundos=round(time.time() - t, 1)))
    except Exception as e:  # noqa: BLE001
        resultados.append(dict(nombre=nombre, ok=False,
                               detalle=f"{e.__class__.__name__}: {e}\n{traceback.format_exc()}",
                               segundos=round(time.time() - t, 1)))


def run(args: list[str]) -> int:
    """`args` = lo que va detrás de --autodiagnostico."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    salida = args[0] if args else os.path.join(tempfile.gettempdir(), "aventyapdf-diagnostico.json")
    pfx, clave = (args[1], args[2]) if len(args) >= 3 else (None, None)
    res: list = []

    def entorno():
        return dict(ejecutable=sys.executable, empaquetada=bool(getattr(sys, "frozen", False)),
                    python=sys.version.split()[0])
    _comprobar(res, "Entorno", entorno)

    def archivos():
        import icons
        import emoji_font
        import signature_validation
        import signer_backend
        rutas = [icons.ICON_TTF, icons.ICON_JSON, icons.APP_ICON, icons.noto_path("sans"),
                 icons.noto_path("serif", True, True), icons.noto_path("mono"),
                 emoji_font.FONT_PATH, emoji_font.EMOJI_JSON,
                 signature_validation.TRUST_LIST, signer_backend.BACKGROUND_PDF]
        faltan = [r for r in rutas if not os.path.isfile(r)]
        if faltan:
            raise FileNotFoundError(", ".join(faltan))
        return f"{len(rutas)} archivos"
    _comprobar(res, "Archivos incluidos (fuentes, iconos, confianza, sello)", archivos)

    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([sys.argv[0]])

    def ventana():
        from main_window import MainWindow
        # main.py corre como __main__ (en el ejecutable no se puede importar «main»).
        principal = sys.modules.get("__main__")
        if not hasattr(principal, "STYLESHEET"):
            import main as principal
        app.setStyleSheet(principal.STYLESHEET)
        w = MainWindow()
        w.resize(1200, 800)
        w.show()
        app.processEvents()
        import fitz
        doc = fitz.open()
        doc.new_page().insert_text((72, 100), "Prueba", fontsize=20)
        ruta = os.path.join(tempfile.mkdtemp(prefix="agpdf_diag_"), "prueba.pdf")
        doc.save(ruta)
        if not w.open_path(ruta):
            raise RuntimeError("no abre un PDF")
        w._modified = False
        w.close()
        return "ventana, estilo y apertura de PDF"
    _comprobar(res, "Ventana principal", ventana)

    def ocr():
        import tesseract_setup
        st = tesseract_setup.ensure(tesseract_setup.CORE_LANGS)
        tesseract_setup.verify_ocr("spa")
        return f"Tesseract: {st.exe}"
    _comprobar(res, "OCR (Tesseract e idiomas)", ocr)

    def pdf_a_word():
        import pdf2docx  # noqa: F401
        import cv2  # noqa: F401
        return "pdf2docx y OpenCV cargan"
    _comprobar(res, "Exportar a Word / OpenCV", pdf_a_word)

    def sellado():
        # El sellado de tiempo (TSA) de la firma usa aiohttp en pyHanko 0.37.
        from pyhanko.sign.timestamps import HTTPTimeStamper
        HTTPTimeStamper("https://freetsa.org/tsr", timeout=5)
        return "cliente HTTP del sellado de tiempo"
    _comprobar(res, "Sellado de tiempo (módulos)", sellado)

    if pfx:
        def firma():
            import fitz
            from signature_validation import validate_signatures
            from signer_backend import PAdESSigner, remove_last_signature
            d = fitz.open()
            for i in range(2):
                d.new_page().insert_text((72, 100), f"Pagina {i + 1}")
            uno = PAdESSigner.sign_pdf_bytes(d.tobytes(), pfx, clave, 0, (72, 600, 272, 680))
            dos = PAdESSigner.sign_pdf_bytes(uno, pfx, clave, 1, (72, 600, 272, 680))
            reps = validate_signatures(dos)
            if [r.intact and r.valid for r in reps] != [True, True]:
                raise RuntimeError(f"firmas no íntegras: {[(r.field_name, r.verdict) for r in reps]}")
            sin = remove_last_signature(dos, "Firma2")
            reps = validate_signatures(sin)
            if [r.field_name for r in reps] != ["Firma1"] or not reps[0].intact:
                raise RuntimeError("quitar la última firma falló")
            return "firmar, verificar y quitar la última firma"
        _comprobar(res, "Firma digital", firma)

    ok = all(r["ok"] for r in res)
    with open(salida, "w", encoding="utf-8") as fh:
        json.dump(dict(ok=ok, comprobaciones=res), fh, ensure_ascii=False, indent=1)
    return 0 if ok else 1
