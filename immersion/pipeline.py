"""Full immersion pipeline orchestration."""
from pathlib import Path

from .extractor import extraer_vocab
from .traductor import traducir_palabras, traducir_palabras_google, cargar_diccionario, guardar_diccionario
from .anotador import anotar_epub
from .anki_export import exportar_anki
from .stardict import generar_stardict


def ejecutar_pipeline(
    ruta_epub: str,
    ruta_salida: str | None = None,
    origen: str = "es",
    destino: str = "en",
    intensidad: int = 3,
    api_key: str | None = None,
    google_api_key: str | None = None,
    ruta_diccionario: str | None = None,
    semilla: int | None = None,
    max_palabras: int | None = 500,
    min_longitud: int = 4,
    exportar_anki_deck: bool = True,
    nombre_mazo: str | None = None,
) -> dict:
    """
    Run the full immersion pipeline:
      1. Load or initialize dictionary
      2. Extract new vocabulary from epub
      3. Translate new words via DeepL (if api_key provided)
      4. Annotate epub
      5. Export Anki deck

    Returns stats: {capitulos, palabras_nuevas, total_diccionario}
    """
    entrada = Path(ruta_epub)
    if not entrada.exists():
        raise FileNotFoundError(f"No se encontró: {ruta_epub}")

    if ruta_salida is None:
        ruta_salida = str(entrada.with_stem(entrada.stem + "_anotado"))
    salida = Path(ruta_salida)

    print(f"\n📖  {entrada.name}")

    # ── 1. Cargar diccionario base ─────────────────────────────────────────────
    diccionario: dict[str, str] = {}
    if ruta_diccionario and Path(ruta_diccionario).exists():
        print(f"📚  Diccionario base: {ruta_diccionario}")
        diccionario = cargar_diccionario(ruta_diccionario)
        print(f"   {len(diccionario)} entradas cargadas")

    # ── 2. Extraer vocabulario del epub ────────────────────────────────────────
    print(f"🔍  Extrayendo vocabulario (idioma={origen}, mín={min_longitud} letras)…")
    vocab = extraer_vocab(
        ruta_epub,
        idioma=origen,
        min_longitud=min_longitud,
        max_palabras=max_palabras,
        excluir=set(diccionario.keys()),
    )
    palabras_nuevas = [p for p, _ in vocab]
    print(f"   {len(palabras_nuevas)} palabras nuevas extraídas")

    # ── 3. Traducir (DeepL o Google AI) ───────────────────────────────────────
    if palabras_nuevas and (api_key or google_api_key):
        if google_api_key:
            print(f"🌐  Traduciendo {len(palabras_nuevas)} palabras ({origen}→{destino}) via Google AI…")
            nuevas = traducir_palabras_google(palabras_nuevas, origen, destino, google_api_key)
        else:
            print(f"🌐  Traduciendo {len(palabras_nuevas)} palabras ({origen}→{destino}) via DeepL…")
            nuevas = traducir_palabras(palabras_nuevas, origen, destino, api_key)

        diccionario.update(nuevas)
        ruta_dict_json = salida.with_suffix('.json')
        guardar_diccionario(diccionario, str(ruta_dict_json))
        print(f"   Diccionario guardado: {ruta_dict_json.name}")
    elif palabras_nuevas:
        print("⚠️   Sin API key — se usará el diccionario existente sin traducciones nuevas.")
        print("     Proporciona una API key de DeepL o Google AI.")

    # Filtrar entradas vacías (palabras extraídas sin traducción aún)
    diccionario_activo = {k: v for k, v in diccionario.items() if v}

    if not diccionario_activo:
        print("❌  Diccionario vacío. Proporciona --deepl-key o --diccionario.\n")
        return {"capitulos": 0, "palabras_nuevas": len(palabras_nuevas), "total_diccionario": 0}

    # ── 4. Anotar epub ─────────────────────────────────────────────────────────
    print(f"✏️   Anotando (intensidad={intensidad}, semilla={semilla})…")
    capitulos = anotar_epub(ruta_epub, ruta_salida, diccionario_activo, intensidad, semilla)
    print(f"   {capitulos} capítulos → {salida.name}")

    # ── 4b. Generar diccionario StarDict para KOReader ─────────────────────────
    ruta_zip = salida.with_suffix(".stardict.zip")
    generar_stardict(diccionario_activo, str(ruta_zip), nombre_mazo or entrada.stem)
    print(f"📖  Diccionario KOReader → {ruta_zip.name}")

    # ── 5. Exportar Anki ───────────────────────────────────────────────────────
    if exportar_anki_deck:
        nombre = nombre_mazo or entrada.stem
        ruta_apkg = salida.with_suffix('.apkg')
        print(f"🎴  Generando mazo Anki ({len(diccionario_activo)} tarjetas)…")
        exportar_anki(diccionario_activo, str(ruta_apkg), nombre_mazo=nombre)
        print(f"   Mazo guardado: {ruta_apkg.name}")

    print(f"\n✅  Pipeline completado!\n")

    return {
        "capitulos": capitulos,
        "palabras_nuevas": len(palabras_nuevas),
        "total_diccionario": len(diccionario_activo),
    }
