"""StarDict dictionary generator for KOReader.

Produces a .zip with the three StarDict files (.ifo, .idx, .dict).
Install in KOReader: copy the three files to /mnt/us/koreader/data/dict/
"""
import struct
import zipfile
from pathlib import Path

from .pronunciacion import ipa_batch, ipa_a_fonetica


def generar_stardict(
    diccionario: dict[str, str],
    ruta_zip: str,
    nombre: str = "Immersion Reader",
) -> Path:
    """Build a StarDict dictionary from an es→en (or any src→dst) mapping.

    Each entry key is the translated (target) word; the definition shows the
    source word plus IPA and Spanish-readable phonetic:
        sword  →  espada [/sɔrd/ (sord)]

    Returns the path to the generated zip file.
    """
    dest_words = list({v for v in diccionario.values() if v})
    ipa_cache = ipa_batch(dest_words)

    # Merge duplicates: multiple source words can share the same target word
    merged: dict[bytes, str] = {}
    for origen, destino in diccionario.items():
        if not destino:
            continue
        key = destino.lower().encode("utf-8")
        merged.setdefault(key, []).append(origen)  # type: ignore[arg-type]

    # Build sorted entries list
    entries: list[tuple[bytes, bytes]] = []
    for key in sorted(merged):
        origenes: list[str] = merged[key]  # type: ignore[assignment]
        destino_lower = key.decode("utf-8")
        pron = ipa_cache.get(destino_lower, "")
        if pron:
            fonetica = ipa_a_fonetica(pron)
            pron_str = f" [/{pron}/ ({fonetica})]"
        else:
            pron_str = ""
        definition = " / ".join(origenes) + pron_str
        entries.append((key, definition.encode("utf-8")))

    # Serialize .dict (concatenated definitions) and .idx (binary index)
    dict_data = bytearray()
    idx_data = bytearray()
    for word, definition in entries:
        offset = len(dict_data)
        size = len(definition)
        dict_data += definition
        idx_data += word + b"\x00"
        idx_data += struct.pack(">II", offset, size)

    # .ifo metadata (plain text)
    stem = Path(ruta_zip).stem.replace(".stardict", "")
    ifo = (
        "StarDict's dict ifo file\n"
        "version=2.4.2\n"
        f"wordcount={len(entries)}\n"
        f"idxfilesize={len(idx_data)}\n"
        f"bookname={nombre}\n"
        "sametypesequence=m\n"
    )

    zip_path = Path(ruta_zip)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{stem}.ifo", ifo)
        zf.writestr(f"{stem}.idx", bytes(idx_data))
        zf.writestr(f"{stem}.dict", bytes(dict_data))

    return zip_path
