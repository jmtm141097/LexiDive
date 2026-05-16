"""English IPA pronunciation lookup and Spanish-readable phonetic conversion."""
try:
    import eng_to_ipa as _ipa
    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False

# IPA symbol → Spanish-readable approximation, longest patterns first
_IPA_MAP: list[tuple[str, str]] = [
    # 3-char sequences
    ("ɪər", "ir"), ("ɛər", "er"), ("ʊər", "ur"), ("ɜːr", "er"),
    ("ɑːr", "ar"), ("ɔːr", "or"),
    # 2-char sequences
    ("juː", "yu"), ("tʃ", "ch"), ("dʒ", "dy"),
    ("eɪ", "ei"), ("aɪ", "ai"), ("ɔɪ", "oi"), ("aʊ", "au"), ("oʊ", "ou"),
    ("ɑː", "a"),  ("ɔː", "o"),  ("iː", "i"),  ("uː", "u"),
    ("eː", "e"),  ("ɜː", "er"),
    # Single vowels
    ("æ", "a"), ("ʌ", "a"), ("ɑ", "a"), ("ɒ", "o"), ("ɔ", "o"),
    ("ɪ", "i"), ("ʊ", "u"), ("ə", "e"), ("ɛ", "e"), ("ɜ", "er"),
    # Single consonants (including ligature variants)
    ("ʤ", "dy"), ("ʧ", "ch"),
    ("θ", "z"), ("ð", "d"), ("ʃ", "sh"), ("ʒ", "zh"),
    ("ŋ", "ng"), ("j", "y"), ("w", "u"), ("h", "j"),
    # Markers to drop
    ("ˈ", ""), ("ˌ", ""), ("ː", ""), (".", ""),
]


def ipa_a_fonetica(ipa_str: str) -> str:
    """Convert IPA string to an approximate Spanish-readable phonetic spelling.

    Example: 'sɔːrd' → 'sord'
    """
    out: list[str] = []
    i = 0
    while i < len(ipa_str):
        for sym, equiv in _IPA_MAP:
            if ipa_str[i: i + len(sym)] == sym:
                out.append(equiv)
                i += len(sym)
                break
        else:
            out.append(ipa_str[i])
            i += 1
    return "".join(out)


def ipa(palabra: str) -> str:
    """Return IPA transcription for an English word, or empty string if unavailable."""
    if not _AVAILABLE:
        return ""
    resultado = _ipa.convert(palabra.lower())
    if not resultado or '*' in resultado:
        return ""
    return resultado


def ipa_batch(palabras: list[str]) -> dict[str, str]:
    """Return IPA transcriptions for multiple words using a single SQL query pass."""
    if not _AVAILABLE or not palabras:
        return {}
    lower_words = [p.lower() for p in palabras]
    try:
        resultados = _ipa.ipa_list(" ".join(lower_words))
        if len(resultados) == len(lower_words):
            out = {}
            for palabra, variantes in zip(lower_words, resultados):
                for v in variantes:
                    if v and '*' not in v:
                        out[palabra] = v
                        break
            return out
    except Exception:
        pass
    return {p: r for p in lower_words if (r := ipa(p))}
