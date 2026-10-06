// Generado por «python herramientas_idioma.py instalador» a partir de
// empaquetado/idiomas/*.json: no editar a mano (r136).
#pragma once

struct TextosMenu { const wchar_t* codigo; const wchar_t* firmar;
                    const wchar_t* combinar; const wchar_t* convertir; };
static const TextosMenu TEXTOS_MENU[] = {
    {L"es", L"Firmar digitalmente", L"Combinar en un PDF", L"Convertir a PDF"},
    {L"en", L"Sign digitally", L"Combine into one PDF", L"Convert to PDF"},
    {L"fr", L"Signer num\u00E9riquement", L"Combiner en un PDF", L"Convertir en PDF"},
    {L"it", L"Firma digitalmente", L"Combina in un PDF", L"Converti in PDF"},
    {L"ca", L"Signa digitalment", L"Combina en un PDF", L"Converteix a PDF"},
    {L"gl", L"Asinar dixitalmente", L"Combinar nun PDF", L"Converter a PDF"},
    {L"eu", L"Sinatu digitalki", L"Konbinatu PDF bakarrean", L"Bihurtu PDF"},
};

struct IdiomaWindows { WORD primario; const wchar_t* codigo; };
static const IdiomaWindows WINDOWS_IDIOMAS[] = {
    {0x0A, L"es"},
    {0x09, L"en"},
    {0x0C, L"fr"},
    {0x10, L"it"},
    {0x03, L"ca"},
    {0x56, L"gl"},
    {0x2D, L"eu"},
};
