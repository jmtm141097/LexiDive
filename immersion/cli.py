"""CLI with subcommands for the immersion pipeline."""
import argparse
import os
import sys
from pathlib import Path


def cmd_run(args) -> None:
    from .pipeline import ejecutar_pipeline

    api_key = args.deepl_key or os.environ.get("DEEPL_API_KEY")
    if not api_key and not args.diccionario:
        print("⚠️   Sin API key ni diccionario. Pasa --deepl-key KEY o -d diccionario.json")

    ejecutar_pipeline(
        ruta_epub=args.epub,
        ruta_salida=args.salida,
        origen=args.origen,
        destino=args.destino,
        intensidad=args.intensidad,
        api_key=api_key,
        ruta_diccionario=args.diccionario,
        semilla=args.semilla,
        max_palabras=args.max_palabras,
        min_longitud=args.min_longitud,
        exportar_anki_deck=not args.sin_anki,
        nombre_mazo=args.mazo,
    )


def cmd_extraer(args) -> None:
    from .extractor import extraer_vocab
    from .traductor import guardar_diccionario

    print(f"\n🔍  Extrayendo vocabulario de: {Path(args.epub).name}")
    vocab = extraer_vocab(
        args.epub,
        min_longitud=args.min_longitud,
        max_palabras=args.max_palabras,
    )
    print(f"   {len(vocab)} palabras encontradas")

    salida = args.salida or str(Path(args.epub).with_suffix('.vocab.json'))
    guardar_diccionario({p: "" for p, _ in vocab}, salida)
    print(f"✅  Vocabulario guardado: {salida}\n")


def cmd_anotar(args) -> None:
    from .traductor import cargar_diccionario
    from .anotador import anotar_epub

    print(f"\n📖  Cargando diccionario: {args.diccionario}")
    diccionario = {k: v for k, v in cargar_diccionario(args.diccionario).items() if v}
    print(f"   {len(diccionario)} entradas")

    entrada = Path(args.epub)
    salida = args.salida or str(entrada.with_stem(entrada.stem + "_anotado"))

    print(f"✏️   Anotando {entrada.name} (intensidad={args.intensidad}, semilla={args.semilla})…")
    capitulos = anotar_epub(args.epub, salida, diccionario, args.intensidad, args.semilla)
    print(f"✅  {capitulos} capítulos → {Path(salida).name}\n")


def cmd_anki(args) -> None:
    from .traductor import cargar_diccionario
    from .anki_export import exportar_anki

    diccionario = {k: v for k, v in cargar_diccionario(args.diccionario).items() if v}
    salida = args.salida or str(Path(args.diccionario).with_suffix('.apkg'))
    nombre = args.mazo or Path(args.diccionario).stem

    print(f"\n🎴  Generando mazo '{nombre}' con {len(diccionario)} tarjetas…")
    exportar_anki(diccionario, salida, nombre_mazo=nombre)
    print(f"✅  Mazo guardado: {salida}\n")


def cmd_uso(args) -> None:
    from .traductor import uso_api

    api_key = args.deepl_key or os.environ.get("DEEPL_API_KEY")
    if not api_key:
        print("❌  Falta --deepl-key o variable DEEPL_API_KEY")
        sys.exit(1)

    usados, limite = uso_api(api_key)
    porcentaje = usados / limite * 100 if limite else 0
    print(f"\n📊  Uso DeepL API:")
    print(f"   {usados:,} / {limite:,} caracteres ({porcentaje:.1f}%)")
    restantes = limite - usados
    print(f"   {restantes:,} caracteres restantes este mes\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="immersion",
        description="Herramienta de aprendizaje por inmersión lingüística para epubs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Pipeline completo con DeepL
  python main.py run libro.epub --deepl-key TU_KEY

  # Pipeline con diccionario existente (sin API)
  python main.py run libro.epub -d diccionario.json

  # Solo extraer vocabulario
  python main.py extraer libro.epub --max-palabras 300

  # Solo anotar con diccionario ya traducido
  python main.py anotar libro.epub -d traducido.json --intensidad 5 --semilla 42

  # Solo generar mazo Anki
  python main.py anki traducido.json --mazo "Game of Thrones"

  # Ver uso de caracteres DeepL
  python main.py uso --deepl-key TU_KEY

La API key de DeepL gratuita termina en ':fx'. Regístrate en deepl.com/pro#developer
        """,
    )

    sub = parser.add_subparsers(dest="comando", required=True)

    # ── run ──────────────────────────────────────────────────────────────────
    p_run = sub.add_parser("run", help="Pipeline completo: extrae → traduce → anota → Anki")
    p_run.add_argument("epub", help="Archivo .epub de entrada")
    p_run.add_argument("--salida", "-s", help="Ruta del epub de salida (default: <nombre>_anotado.epub)")
    p_run.add_argument("--origen", default="es", help="Idioma de origen (default: es)")
    p_run.add_argument("--destino", default="en", help="Idioma de destino (default: en)")
    p_run.add_argument("--intensidad", "-i", type=int, default=3,
                       help="Palabras distintas a reemplazar por fragmento (default: 3)")
    p_run.add_argument("--deepl-key", metavar="KEY",
                       help="DeepL API key (o variable de entorno DEEPL_API_KEY)")
    p_run.add_argument("--diccionario", "-d", metavar="JSON",
                       help="Diccionario JSON existente {origen: destino}")
    p_run.add_argument("--semilla", type=int,
                       help="Semilla aleatoria para resultados reproducibles")
    p_run.add_argument("--max-palabras", type=int, default=500,
                       help="Máximo de palabras a extraer/traducir (default: 500)")
    p_run.add_argument("--min-longitud", type=int, default=4,
                       help="Longitud mínima de palabra en caracteres (default: 4)")
    p_run.add_argument("--sin-anki", action="store_true",
                       help="No generar mazo Anki")
    p_run.add_argument("--mazo", help="Nombre del mazo Anki (default: nombre del epub)")
    p_run.set_defaults(func=cmd_run)

    # ── extraer ───────────────────────────────────────────────────────────────
    p_ext = sub.add_parser("extraer", help="Extraer vocabulario del epub a un JSON")
    p_ext.add_argument("epub")
    p_ext.add_argument("--salida", "-s", help="Archivo JSON de salida")
    p_ext.add_argument("--min-longitud", type=int, default=4)
    p_ext.add_argument("--max-palabras", type=int, default=None,
                       help="Limitar número de palabras (default: sin límite)")
    p_ext.set_defaults(func=cmd_extraer)

    # ── anotar ────────────────────────────────────────────────────────────────
    p_ano = sub.add_parser("anotar", help="Anotar epub con diccionario JSON existente")
    p_ano.add_argument("epub")
    p_ano.add_argument("--diccionario", "-d", required=True, help="Diccionario JSON {origen: destino}")
    p_ano.add_argument("--salida", "-s", help="Epub de salida")
    p_ano.add_argument("--intensidad", "-i", type=int, default=3)
    p_ano.add_argument("--semilla", type=int)
    p_ano.set_defaults(func=cmd_anotar)

    # ── anki ──────────────────────────────────────────────────────────────────
    p_anki = sub.add_parser("anki", help="Generar mazo Anki desde diccionario JSON")
    p_anki.add_argument("diccionario", help="Diccionario JSON {origen: destino}")
    p_anki.add_argument("--salida", "-s", help="Archivo .apkg de salida")
    p_anki.add_argument("--mazo", help="Nombre del mazo (default: nombre del archivo)")
    p_anki.set_defaults(func=cmd_anki)

    # ── uso ───────────────────────────────────────────────────────────────────
    p_uso = sub.add_parser("uso", help="Ver uso de caracteres de la cuenta DeepL")
    p_uso.add_argument("--deepl-key", metavar="KEY")
    p_uso.set_defaults(func=cmd_uso)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
