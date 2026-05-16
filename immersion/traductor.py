"""Translation providers: DeepL and Google AI (Gemini)."""
import json

# DeepL requires specifying a regional variant for some target languages
_TARGET_DEFAULTS: dict[str, str] = {
    "en": "EN-US",
    "pt": "PT-BR",
    "zh": "ZH-HANS",
}


def _lang_code(codigo: str, es_destino: bool = False) -> str:
    codigo = codigo.lower()
    if es_destino:
        return _TARGET_DEFAULTS.get(codigo, codigo.upper())
    return codigo.upper()


def traducir_palabras(
    palabras: list[str],
    origen: str,
    destino: str,
    api_key: str,
    verbose: bool = True,
) -> dict[str, str]:
    """
    Translate a list of words using DeepL API.
    API key ending in ':fx' uses the free endpoint automatically.
    Returns {source_word: translated_word}.
    """
    try:
        import deepl
    except ImportError:
        raise ImportError("Instala deepl: pip install deepl")

    translator = deepl.Translator(api_key)
    lang_origen = _lang_code(origen)
    lang_destino = _lang_code(destino, es_destino=True)

    CHUNK = 50  # DeepL free tier: up to 50 texts per request
    resultado: dict[str, str] = {}
    total = len(palabras)

    for i in range(0, total, CHUNK):
        chunk = palabras[i:i + CHUNK]
        if verbose:
            print(f"   Traduciendo {i + 1}–{min(i + CHUNK, total)} / {total}…")
        results = translator.translate_text(
            chunk,
            source_lang=lang_origen,
            target_lang=lang_destino,
        )
        for palabra, result in zip(chunk, results):
            resultado[palabra] = result.text.lower()

    return resultado


def uso_api(api_key: str) -> tuple[int, int]:
    """Return (chars_used, chars_limit) for the DeepL account."""
    try:
        import deepl
    except ImportError:
        raise ImportError("Instala deepl: pip install deepl")

    usage = deepl.Translator(api_key).get_usage()
    return usage.character.count, usage.character.limit


_LANG_NAMES_GOOGLE: dict[str, str] = {
    "es": "Spanish", "en": "English", "fr": "French", "de": "German",
    "it": "Italian", "pt": "Portuguese", "ja": "Japanese", "zh": "Chinese",
    "ru": "Russian", "ko": "Korean",
}


def traducir_palabras_google(
    palabras: list[str],
    origen: str,
    destino: str,
    api_key: str,
    verbose: bool = True,
) -> dict[str, str]:
    """
    Translate a list of words using Google AI (Gemini) API.
    Returns {source_word: translated_word}.
    """
    try:
        import google.generativeai as genai
    except ImportError:
        raise ImportError("Instala google-generativeai: pip install google-generativeai")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")

    lang_origen = _LANG_NAMES_GOOGLE.get(origen.lower(), origen)
    lang_destino = _LANG_NAMES_GOOGLE.get(destino.lower(), destino)

    CHUNK = 100
    resultado: dict[str, str] = {}
    total = len(palabras)

    for i in range(0, total, CHUNK):
        chunk = palabras[i:i + CHUNK]
        if verbose:
            print(f"   Traduciendo {i + 1}–{min(i + CHUNK, total)} / {total}…")

        prompt = (
            f"Translate these {lang_origen} words to {lang_destino}. "
            f"Return ONLY a valid JSON object mapping each source word to its lowercase translation. "
            f"No explanations or extra text.\n\n"
            f"Words: {json.dumps(chunk, ensure_ascii=False)}"
        )

        response = model.generate_content(prompt)
        text = response.text.strip()

        if text.startswith("```"):
            lines = text.splitlines()
            inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
            text = "\n".join(inner).strip()

        try:
            translations = json.loads(text)
            for palabra in chunk:
                resultado[palabra] = str(translations.get(palabra, "")).lower()
        except (json.JSONDecodeError, AttributeError):
            for palabra in chunk:
                resultado[palabra] = ""

    return resultado


def cargar_diccionario(ruta: str) -> dict[str, str]:
    with open(ruta, 'r', encoding='utf-8') as f:
        return json.load(f)


def guardar_diccionario(diccionario: dict[str, str], ruta: str) -> None:
    with open(ruta, 'w', encoding='utf-8') as f:
        json.dump(diccionario, f, ensure_ascii=False, indent=2, sort_keys=True)
