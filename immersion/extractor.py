"""Extract vocabulary from epub files."""
import re
from collections import Counter
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup


STOPWORDS_ES: set[str] = {
    # Articles
    "el", "la", "los", "las", "un", "una", "unos", "unas",
    # Prepositions
    "a", "de", "en", "con", "por", "para", "sin", "sobre",
    "hasta", "desde", "entre", "hacia", "según", "durante",
    "mediante", "ante", "bajo", "contra", "tras",
    # Conjunctions
    "y", "e", "o", "u", "pero", "sino", "que", "si",
    "porque", "aunque", "como", "cuando", "donde", "mientras",
    "pues", "ni", "mas", "ya", "sea", "ni",
    # Pronouns
    "yo", "tu", "él", "ella", "nosotros", "vosotros", "ellos",
    "ellas", "me", "te", "se", "nos", "os", "le", "les",
    "mi", "mis", "tus", "su", "sus", "nuestro", "nuestra",
    "nuestros", "nuestras", "vuestro", "vuestra", "vuestros", "vuestras",
    # Common verb forms
    "es", "son", "está", "están", "fue", "era", "eran",
    "ser", "estar", "ha", "han", "he", "hemos", "hay", "haya",
    "sido", "tengo", "tiene", "tienen", "tener", "hacer",
    "haber", "poder", "querer", "saber", "ir", "iba",
    # Determiners / demonstratives
    "este", "esta", "estos", "estas", "ese", "esa", "esos",
    "esas", "aquel", "aquella", "aquellos", "aquellas",
    # Common adverbs
    "no", "sí", "más", "menos", "muy", "también", "tampoco",
    "ya", "aún", "todavía", "aquí", "allí", "ahora", "entonces",
    "así", "bien", "mal", "tan", "tanto", "cuanto",
    # Quantifiers / indefinites
    "todo", "toda", "todos", "todas", "algo", "nada", "alguien",
    "nadie", "cada", "otro", "otra", "otros", "otras",
    "mismo", "misma", "mismos", "mismas", "propio", "propia",
    # Interrogatives
    "qué", "quién", "cuál", "cuáles", "cuándo", "dónde",
    "cómo", "cuánto", "cuánta", "cuántos", "cuántas",
    # Numbers (words)
    "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete",
    "ocho", "nueve", "diez", "cien", "mil",
    # Fillers
    "le", "lo", "les", "les",
}

STOPWORDS_EN: set[str] = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
    "for", "of", "with", "by", "from", "up", "about", "into",
    "through", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "need",
    "he", "she", "it", "they", "we", "you", "i", "me", "him",
    "her", "us", "them", "my", "your", "his", "its", "our",
    "their", "this", "that", "these", "those", "what", "which",
    "who", "when", "where", "how", "all", "each", "every", "both",
    "few", "more", "most", "other", "some", "such", "no", "not",
    "only", "same", "than", "too", "very", "just", "so",
}

STOPWORDS_BY_LANG: dict[str, set[str]] = {
    "es": STOPWORDS_ES,
    "en": STOPWORDS_EN,
}


def extraer_texto_epub(ruta_epub: str) -> str:
    """Extract all plain text from epub."""
    libro = epub.read_epub(ruta_epub)
    partes: list[str] = []
    for item in libro.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        sopa = BeautifulSoup(item.get_content(), 'html.parser')
        partes.append(sopa.get_text(' '))
    return ' '.join(partes)


def extraer_vocab(
    ruta_epub: str,
    idioma: str = "es",
    stopwords: set[str] | None = None,
    min_longitud: int = 4,
    max_palabras: int | None = None,
    excluir: set[str] | None = None,
) -> list[tuple[str, int]]:
    """
    Extract unique words from epub sorted by frequency (most common first).
    Returns list of (word, count) tuples.
    """
    sw = stopwords if stopwords is not None else STOPWORDS_BY_LANG.get(idioma, set())
    excluir = excluir or set()

    texto = extraer_texto_epub(ruta_epub)
    # Capture sequences of alphabetical chars including accented Spanish/common chars
    tokens = re.findall(r'[a-záéíóúüñàèìòùâêîôûäëïöüçãõ]+', texto.lower())

    conteo = Counter(
        t for t in tokens
        if len(t) >= min_longitud
        and t not in sw
        and t not in excluir
    )

    return conteo.most_common(max_palabras)
