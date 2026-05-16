"""Anki deck generation (.apkg) from translation dictionaries."""

# Fixed model ID so Anki recognizes the note type across imports
_MODEL_ID = 1607392319

_CSS = """
.card {
    font-family: Arial, sans-serif;
    background: #fafafa;
    padding: 20px;
}
.palabra {
    font-size: 2.2em;
    text-align: center;
    color: #222;
    margin-bottom: 10px;
}
.traduccion {
    font-size: 1.8em;
    text-align: center;
    color: #0066cc;
    margin-top: 10px;
}
hr { border-color: #ccc; }
"""

_FRONT = '<div class="palabra">{{Palabra}}</div>'
_BACK = (
    '<div class="palabra">{{Palabra}}</div>'
    '<hr>'
    '<div class="traduccion">{{Traducción}}</div>'
)


def exportar_anki(
    diccionario: dict[str, str],
    ruta_salida: str,
    nombre_mazo: str = "Inmersión",
    tag: str = "inmersion",
) -> None:
    """Generate an Anki .apkg deck from a {source: target} dictionary."""
    try:
        import genanki
    except ImportError:
        raise ImportError("Instala genanki: pip install genanki")

    modelo = genanki.Model(
        _MODEL_ID,
        'Inmersión Lingüística',
        fields=[{'name': 'Palabra'}, {'name': 'Traducción'}],
        templates=[{'name': 'Tarjeta', 'qfmt': _FRONT, 'afmt': _BACK}],
        css=_CSS,
    )

    # Derive stable deck ID from name so re-imports update rather than duplicate
    mazo_id = abs(hash(nombre_mazo)) % (1 << 31)
    mazo = genanki.Deck(mazo_id, nombre_mazo)

    for palabra, traduccion in sorted(diccionario.items()):
        if not traduccion:
            continue
        nota = genanki.Note(model=modelo, fields=[palabra, traduccion], tags=[tag])
        mazo.add_note(nota)

    genanki.Package(mazo).write_to_file(ruta_salida)
