# Immersion Reader

Herramienta de aprendizaje de idiomas por **inmersión lingüística** para archivos `.epub`.
Sube cualquier libro en el idioma que estudias, y la app reemplaza palabras clave con su
traducción resaltada y genera un mazo Anki con el vocabulario — todo en segundos.

---

## ¿Cómo funciona?

El método de inmersión consiste en aprender un idioma consumiendo contenido real, no ejercicios
artificiales. Esta herramienta aplica ese principio a libros epub:

1. Lees el libro en el idioma que estudias con fluidez normal
2. Ciertas palabras aparecen **resaltadas con su traducción** dentro del texto
3. Tu cerebro asocia el contexto narrativo con la palabra extranjera
4. El vocabulario se refuerza después en Anki con flashcards

### Cómo se ve el texto anotado

Texto original:
```
El hombre tomó su espada y miró hacia el bosque oscuro.
```

Texto anotado (intensidad 3):
```
El man tomó su sword y looked hacia el dark bosque.
```

Las palabras resaltadas (`man`, `sword`, `looked`, `dark`) aparecen marcadas visualmente
en cualquier lector epub.

---

## Webapp (uso recomendado)

### Despliegue propio en Railway

1. Haz fork del repositorio en GitHub
2. Conéctalo a [Railway](https://railway.app) como nuevo proyecto
3. Railway detecta el `Procfile` automáticamente — no hace falta configuración adicional

El `Procfile` ejecuta:
```
web: uvicorn webapp:app --host 0.0.0.0 --port $PORT
```

### Uso local

```bash
git clone https://github.com/jmtm141097/LexiDive
cd LexiDive
pip install -r requirements.txt
uvicorn webapp:app --reload
```

Abre `http://localhost:8000` en tu navegador.

### Límites de la webapp

| Parámetro | Valor |
|---|---|
| Tamaño máximo del EPUB | 50 MB |
| Requests por IP | 5 por minuto |
| Archivos disponibles para descarga | 2 horas tras completarse |

---

## CLI

También puedes usar la herramienta directamente desde la terminal:

```bash
python main.py run libro.epub --deepl-key TU_KEY
```

Genera cuatro archivos junto al epub original:

| Archivo | Descripción |
|---|---|
| `libro_anotado.epub` | El libro con vocabulario resaltado |
| `libro_anotado.json` | Diccionario usado `{palabra_origen: traducción}` |
| `libro_anotado.apkg` | Mazo de Anki listo para importar |
| `libro_anotado.stardict.zip` | Diccionario para KOReader |

### Comandos disponibles

| Comando | Descripción |
|---|---|
| `run` | Pipeline completo: extrae → traduce → anota → Anki |
| `extraer` | Solo extraer vocabulario a JSON |
| `anotar` | Solo anotar con diccionario existente |
| `anki` | Solo generar mazo desde diccionario |
| `uso` | Ver uso de caracteres de la cuenta DeepL |

```bash
# Uso básico con DeepL
python main.py run "Don Quijote.epub" --deepl-key abc123:fx

# Sin API (diccionario incluido)
python main.py run "Dune.epub" -d diccionarios/es_en_fantasia.json

# Traducir francés → español
python main.py run "Le Petit Prince.epub" --origen fr --destino es --deepl-key abc123:fx
```

### Opciones del comando `run`

| Opción | Descripción | Default |
|---|---|---|
| `--deepl-key KEY` | API key de DeepL | `DEEPL_API_KEY` env |
| `--diccionario -d JSON` | Diccionario JSON existente | — |
| `--origen` | Idioma del libro | `es` |
| `--destino` | Idioma de las traducciones | `en` |
| `--intensidad -i N` | Palabras a reemplazar por fragmento | `3` |
| `--max-palabras N` | Cuántas palabras extraer/traducir | `500` |
| `--semilla N` | Semilla para resultados reproducibles | — |
| `--sin-anki` | No generar `.apkg` | — |

---

## Proveedores de traducción

### DeepL (recomendado)

1. Regístrate gratis en [deepl.com/pro#developer](https://www.deepl.com/pro#developer)
2. Copia tu API key — termina en `:fx`
3. El plan gratuito incluye **500.000 caracteres/mes**

### Google AI (Gemini)

1. Obtén una clave en [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. La clave empieza con `AIzaSy...`
3. Tier gratuito disponible

---

## Diccionarios incluidos

El repositorio incluye diccionarios listos para usar que no requieren API key:

| Archivo | Par de idiomas | Género |
|---|---|---|
| `es_en_fantasia.json` | Español → Inglés | Fantasía medieval |
| `es_en_romance.json` | Español → Inglés | Romance |
| `es_en_terror.json` | Español → Inglés | Terror / Horror |
| `es_en_ciencia_ficcion.json` | Español → Ciencia ficción | Sci-Fi |
| `en_es_fantasia.json` | Inglés → Español | Fantasía medieval |
| `en_es_romance.json` | Inglés → Español | Romance |
| `fr_es_fantasia.json` | Francés → Español | Fantasía medieval |
| `fr_es_romance.json` | Francés → Español | Romance |
| `de_es_fantasia.json` | Alemán → Español | Fantasía medieval |

Puedes subir tu propio diccionario JSON en la webapp (formato `{"palabra_origen": "traducción"}`).

---

## Idiomas soportados

| Código | Idioma |
|---|---|
| `es` | Español |
| `en` | Inglés |
| `fr` | Francés |
| `de` | Alemán |
| `it` | Italiano |
| `pt` | Portugués |
| `ja` | Japonés |
| `zh` | Chino |
| `ru` | Ruso |
| `ko` | Coreano |

Para DeepL, la lista completa está en [developers.deepl.com/docs/resources/supported-languages](https://developers.deepl.com/docs/resources/supported-languages).

---

## Estructura del proyecto

```
LexiDive/
├── webapp.py              # FastAPI app — servidor web y API REST
├── main.py                # Entry point del CLI: python main.py <comando>
├── requirements.txt       # Dependencias Python
├── Procfile               # Comando de arranque para Railway
├── immersion/
│   ├── pipeline.py        # Orquestador del pipeline completo
│   ├── extractor.py       # Extrae vocabulario del epub por frecuencia
│   ├── traductor.py       # Integración con DeepL y Google AI
│   ├── anotador.py        # Motor de anotación HTML del epub
│   ├── anki_export.py     # Generación de mazos .apkg para Anki
│   ├── stardict.py        # Generación de diccionarios KOReader
│   ├── pronunciacion.py   # Pronunciación IPA para inglés
│   └── cli.py             # Definición de subcomandos CLI
├── diccionarios/          # Diccionarios JSON incluidos (9 archivos)
└── static/
    ├── index.html         # Frontend
    ├── app.js             # Lógica de la UI
    ├── style.css          # Estilos
    └── favicon.svg        # Icono de la app
```

---

## Preguntas frecuentes

**¿El libro original se modifica?**
No. Siempre se crea un archivo nuevo (`_anotado.epub`). El original no se toca.

**¿Funciona con cualquier epub?**
Con la mayoría. El epub debe tener texto real (no ser un escaneo de imagen). Los epubs con DRM no se pueden procesar.

**¿Cuánto consume de la API de DeepL?**
Con el default de 500 palabras, cada procesamiento usa aproximadamente 2.000–5.000 caracteres — muy por debajo del límite gratuito de 500.000 por mes.

**¿Los resultados son siempre iguales?**
Por defecto varían en cada ejecución (para exponer vocabulario variado). Usa la opción "Semilla aleatoria" en opciones avanzadas para resultados reproducibles.

**¿Cómo importo el mazo en Anki?**
Abre Anki → Archivo → Importar → selecciona el `.apkg` generado.

**¿Cómo instalo el diccionario KOReader?**
Descomprime el `.stardict.zip` y copia los tres archivos (`.ifo`, `.idx`, `.dict`) a `/koreader/data/dict/` en tu dispositivo.
