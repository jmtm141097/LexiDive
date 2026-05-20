"""Annotation engine: replaces source-language words with highlighted target-language equivalents."""
import re
import random
from html import escape as _he
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup, NavigableString

from . import pronunciacion


_CACHE: dict[str, re.Pattern] = {}

_DIVISOR: dict[int, int] = {2: 100, 4: 60, 8: 30}  # presets Sutil/Normal/Intenso
_DIVISOR_FALLBACK = 50  # for custom CLI intensity values outside the preset map

_CSS_TOOLTIP = (
    "mark[data-tooltip]{"
    "position:relative;cursor:help;"
    "}"
    "mark[data-tooltip]::after{"
    "content:attr(data-tooltip);"
    "position:absolute;"
    "bottom:1.5em;left:50%;"
    "transform:translateX(-50%);"
    "background:rgba(0,0,0,0.82);"
    "color:#fff;"
    "padding:3px 8px;"
    "border-radius:4px;"
    "white-space:nowrap;"
    "font-size:0.76em;"
    "font-style:normal;"
    "pointer-events:none;"
    "opacity:0;"
    "z-index:999;"
    "}"
    "mark[data-tooltip]:hover::after,"
    "mark[data-tooltip]:focus::after{"
    "opacity:1;"
    "}"
)


def _patron_de(palabra: str) -> re.Pattern:
    if palabra not in _CACHE:
        _CACHE[palabra] = re.compile(
            r'(?<!\w)' + re.escape(palabra) + r'(?!\w)',
            re.IGNORECASE
        )
    return _CACHE[palabra]


def anotar_texto(
    texto: str,
    entradas_sorted: list[tuple[str, str]],
    intensidad: int,
    rng: random.Random,
    ipa_cache: dict[str, str],
) -> str:
    """Replace source words with <mark>target</mark>. Returns modified text."""
    if not texto.strip():
        return texto

    entradas = list(entradas_sorted)
    rng.shuffle(entradas)

    texto_trabajo = texto
    texto_lower = texto.lower()
    reemplazos_count = 0
    word_count = len(texto.split())
    divisor = _DIVISOR.get(intensidad, _DIVISOR_FALLBACK)
    cap = max(intensidad, word_count // divisor)

    for origen, destino in entradas:
        if intensidad > 0 and reemplazos_count >= cap:
            break

        if origen.lower() not in texto_lower:
            continue

        patron = _patron_de(origen)
        nueva_cadena = []
        ultimo = 0
        hubo = False

        for m in patron.finditer(texto_trabajo):
            ini, fin = m.start(), m.end()

            antes = texto_trabajo[:ini]
            if antes.count('<mark') > antes.count('</mark>'):
                continue

            token_orig = m.group(0)
            destino_disp = destino[0].upper() + destino[1:] if token_orig[0].isupper() else destino

            pron = ipa_cache.get(destino.lower(), "")
            if pron:
                fonetica = pronunciacion.ipa_a_fonetica(pron)
                tooltip_text = f"{origen} [/{pron}/ ({fonetica})]"
            else:
                tooltip_text = origen
            tooltip_attr = _he(tooltip_text, quote=True)

            nueva_cadena.append(texto_trabajo[ultimo:ini])
            nueva_cadena.append(
                f'<mark title="{tooltip_attr}" data-tooltip="{tooltip_attr}">'
                f'{destino_disp}</mark>'
            )
            ultimo = fin
            hubo = True

        if hubo:
            nueva_cadena.append(texto_trabajo[ultimo:])
            texto_trabajo = "".join(nueva_cadena)
            reemplazos_count += 1

    return texto_trabajo


def _procesar_nodo(
    nodo: NavigableString,
    entradas_sorted: list[tuple[str, str]],
    intensidad: int,
    rng: random.Random,
    ipa_cache: dict[str, str],
) -> None:
    if isinstance(nodo, NavigableString) and nodo.parent.name not in ('script', 'style', 'code', 'pre', 'mark'):
        texto = str(nodo)
        nuevo = anotar_texto(texto, entradas_sorted, intensidad, rng, ipa_cache)
        if nuevo != texto:
            fragmento = BeautifulSoup(nuevo, 'html.parser')
            nodo.replace_with(fragmento)


def procesar_html(
    contenido_html: bytes,
    entradas_sorted: list[tuple[str, str]],
    intensidad: int,
    rng: random.Random,
    ipa_cache: dict[str, str],
) -> bytes:
    sopa = BeautifulSoup(contenido_html, 'html.parser')
    for nodo in list(sopa.find_all(string=True)):
        _procesar_nodo(nodo, entradas_sorted, intensidad, rng, ipa_cache)

    if sopa.find('mark'):
        head = sopa.find('head')
        if head:
            estilo = sopa.new_tag('style')
            estilo.string = _CSS_TOOLTIP
            head.append(estilo)

    return str(sopa).encode('utf-8')


def anotar_epub(
    ruta_entrada: str,
    ruta_salida: str,
    diccionario: dict[str, str],
    intensidad: int = 3,
    semilla: int | None = None,
) -> int:
    """Annotate epub with dictionary translations. Returns number of chapters processed."""
    rng = random.Random(semilla)
    libro = epub.read_epub(ruta_entrada)

    entradas_sorted = sorted(diccionario.items(), key=lambda x: -len(x[0]))
    dest_words = list({v for v in diccionario.values() if v})
    ipa_cache = pronunciacion.ipa_batch(dest_words)

    count = 0
    for item in libro.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        contenido = procesar_html(item.get_content(), entradas_sorted, intensidad, rng, ipa_cache)
        item.set_content(contenido)
        count += 1

    epub.write_epub(ruta_salida, libro)
    return count
