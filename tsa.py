"""
tsa.py — Servidores de sellado de tiempo (RFC 3161) gratuitos y conocidos.

(r131) Separado de signer_backend para que la ventana pueda mostrar la lista
(opciones de firma) sin cargar pyHanko al arrancar: pyHanko solo se carga al
firmar o al quitar una firma.
"""

TSA_PRESETS = [
    "http://timestamp.digicert.com",
    "http://timestamp.sectigo.com",
    "https://freetsa.org/tsr",
]
