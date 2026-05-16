# Immersion Reader

Herramienta de aprendizaje de idiomas por **inmersión lingüística** para archivos `.epub`. Toma cualquier libro en tu idioma nativo, reemplaza palabras clave con su traducción resaltada, y genera un mazo de Anki con el vocabulario — todo en un solo comando.

---

## ¿Para qué sirve?

El método de inmersión consiste en aprender un idioma consumiendo contenido real, no ejercicios artificiales. Esta herramienta aplica ese principio a libros epub:

- Lees en tu idioma nativo (español) con fluidez normal
- Ciertas palabras aparecen **resaltadas en inglés** dentro del texto
- Tu cerebro asocia el contexto narrativo con la palabra extranjera
- El vocabulario se refuerza después en Anki con flashcards

**Resultado:** en lugar de estudiar listas de palabras descontextualizadas, aprendes vocabulario mientras disfrutas un libro.

### Cómo se ve el texto anotado

Texto original:
```
El hombre tomó su espada y miró hacia el bosque oscuro.
```

Texto anotado (intensidad 3):
```
El man tomó su sword y looked hacia el dark bosque.
```

Las palabras resaltadas (`man`, `sword`, `looked`, `dark`) aparecen marcadas visualmente en tu lector epub favorito.

---

## Instalación

**Requisitos:** Python 3.10 o superior.

```bash
# 1. Clonar o descargar el repositorio
git clone https://github.com/jmtm141097/LexiDive
cd script-traductor

# 2. Instalar dependencias
pip install -r requirements.txt
```

### Dependencias

| Paquete | Uso |
|---|---|
| `ebooklib` | Leer y escribir archivos `.epub` |
| `beautifulsoup4` | Parsear el HTML interno del epub |
| `deepl` | API de traducción automática |
| `genanki` | Generar mazos `.apkg` para Anki |

### API key de DeepL (opcional pero recomendado)

Para traducir vocabulario de cualquier libro automáticamente necesitas una clave de DeepL:

1. Regístrate gratis en [deepl.com/pro#developer](https://www.deepl.com/pro#developer)
2. Copia tu API key — termina en `:fx` (ej: `abc123:fx`)
3. Úsala con `--deepl-key` o expórtala como variable de entorno:

```bash
export DEEPL_API_KEY="tu-clave:fx"
```

> El plan gratuito incluye **500.000 caracteres por mes**, suficiente para procesar decenas de libros.

---

## Uso rápido

```bash
python main.py run libro.epub --deepl-key TU_KEY
```

Eso es todo. El comando genera tres archivos junto al epub original:

| Archivo | Descripción |
|---|---|
| `libro_anotado.epub` | El libro con vocabulario resaltado |
| `libro_anotado.json` | Diccionario usado `{palabra_origen: traducción}` |
| `libro_anotado.apkg` | Mazo de Anki listo para importar |

---

## Comandos

El CLI tiene cinco subcomandos. Puedes usarlos en secuencia o por separado según tu flujo.

### `run` — Pipeline completo

Ejecuta los cuatro pasos en orden: extrae vocabulario → traduce → anota el epub → exporta Anki.

```bash
python main.py run <epub> [opciones]
```

| Opción | Descripción | Default |
|---|---|---|
| `--deepl-key KEY` | API key de DeepL (o `DEEPL_API_KEY` en entorno) | — |
| `--diccionario -d JSON` | Usar diccionario JSON existente (omite la llamada a DeepL) | — |
| `--salida -s RUTA` | Nombre del epub de salida | `<nombre>_anotado.epub` |
| `--origen` | Idioma del libro | `es` |
| `--destino` | Idioma de las traducciones | `en` |
| `--intensidad -i N` | Palabras distintas a reemplazar por fragmento de texto | `3` |
| `--max-palabras N` | Cuántas palabras extraer/traducir del libro | `500` |
| `--min-longitud N` | Ignorar palabras más cortas que N caracteres | `4` |
| `--semilla N` | Semilla aleatoria para resultados reproducibles | — |
| `--mazo NOMBRE` | Nombre del mazo Anki generado | nombre del epub |
| `--sin-anki` | No generar el archivo `.apkg` | — |

**Ejemplos:**

```bash
# Uso básico con DeepL (traduce vocabulario automáticamente)
python main.py run "Don Quijote.epub" --deepl-key abc123:fx

# Con diccionario ya preparado (no necesita internet)
python main.py run "Dune.epub" -d diccionarios/es_en_fantasia.json

# Resultado reproducible, intensidad alta, sin Anki
python main.py run "1984.epub" -d mi_dict.json --intensidad 5 --semilla 42 --sin-anki

# Traducir francés → inglés
python main.py run "Le Petit Prince.epub" --origen fr --destino en --deepl-key abc123:fx

# Limitar a las 200 palabras más frecuentes del libro
python main.py run "libro.epub" --deepl-key abc123:fx --max-palabras 200

# Guardar el epub anotado en otra carpeta
python main.py run "libro.epub" -d dict.json -s "/ruta/salida/libro_en.epub"
```

---

### `extraer` — Solo extraer vocabulario

Analiza el epub y extrae las palabras más frecuentes a un archivo JSON, sin traducirlas. Útil para revisar qué vocabulario se detectó antes de gastar caracteres de API.

```bash
python main.py extraer <epub> [opciones]
```

| Opción | Descripción | Default |
|---|---|---|
| `--salida -s JSON` | Archivo de salida | `<nombre>.vocab.json` |
| `--min-longitud N` | Ignorar palabras cortas | `4` |
| `--max-palabras N` | Número máximo de palabras | sin límite |

**Ejemplos:**

```bash
# Extraer las 300 palabras más frecuentes
python main.py extraer "Cien años de soledad.epub" --max-palabras 300

# Guardar en archivo específico
python main.py extraer "libro.epub" -s vocabulario_raw.json

# Ver solo palabras de 6+ letras
python main.py extraer "libro.epub" --min-longitud 6 --max-palabras 500
```

El archivo resultante tiene el formato `{"palabra": ""}` — las traducciones están vacías hasta que uses DeepL o las rellenes manualmente.

---

### `anotar` — Solo anotar con diccionario existente

Aplica un diccionario JSON ya traducido a un epub. No hace llamadas a internet.

```bash
python main.py anotar <epub> --diccionario <json> [opciones]
```

| Opción | Descripción | Default |
|---|---|---|
| `--diccionario -d JSON` | Diccionario `{palabra: traducción}` | requerido |
| `--salida -s RUTA` | Epub de salida | `<nombre>_anotado.epub` |
| `--intensidad -i N` | Palabras por fragmento | `3` |
| `--semilla N` | Semilla para reproducibilidad | — |

**Ejemplos:**

```bash
# Anotar con el diccionario de fantasía incluido en el repo
python main.py anotar "Juego de Tronos.epub" -d diccionarios/es_en_fantasia.json

# Intensidad alta, resultado reproducible
python main.py anotar "libro.epub" -d mi_dict.json --intensidad 6 --semilla 100

# Probar diferentes intensidades y comparar
python main.py anotar "libro.epub" -d dict.json -i 2 -s libro_suave.epub
python main.py anotar "libro.epub" -d dict.json -i 8 -s libro_intenso.epub
```

---

### `anki` — Solo generar mazo Anki

Convierte cualquier diccionario JSON en un mazo `.apkg` listo para importar en Anki.

```bash
python main.py anki <diccionario.json> [opciones]
```

| Opción | Descripción | Default |
|---|---|---|
| `--salida -s RUTA` | Archivo `.apkg` de salida | `<nombre>.apkg` |
| `--mazo NOMBRE` | Nombre del mazo en Anki | nombre del archivo |

**Ejemplos:**

```bash
# Generar mazo desde el diccionario incluido
python main.py anki diccionarios/es_en_fantasia.json --mazo "Fantasía Medieval"

# Desde un diccionario generado por el pipeline
python main.py anki "libro_anotado.json" --mazo "Dune - Vocabulario"

# Guardar en ruta específica
python main.py anki dict.json -s ~/Descargas/mi_mazo.apkg
```

Cada tarjeta muestra la palabra en el idioma origen al frente, y la traducción al reverso.

---

### `uso` — Ver uso de la cuenta DeepL

Muestra cuántos caracteres has usado este mes y cuántos te quedan.

```bash
python main.py uso --deepl-key TU_KEY
# o con variable de entorno configurada:
python main.py uso
```

Salida ejemplo:
```
📊  Uso DeepL API:
   12,450 / 500,000 caracteres (2.5%)
   487,550 caracteres restantes este mes
```

---

## Flujos de trabajo

### Flujo A: primer uso con un libro nuevo

```bash
# 1. Pipeline completo automático
python main.py run "mi-libro.epub" --deepl-key abc123:fx --intensidad 3

# Abre mi-libro_anotado.epub en tu lector favorito
# Importa mi-libro_anotado.apkg en Anki
```

### Flujo B: revisar vocabulario antes de traducir

```bash
# 1. Extraer vocabulario sin gastar API
python main.py extraer "mi-libro.epub" --max-palabras 500 -s vocab.json

# 2. Revisar vocab.json, borrar palabras que ya conoces o no te interesan

# 3. Traducir el vocabulario depurado
#    (próximamente: python main.py traducir vocab.json --deepl-key KEY)

# 4. Anotar y generar Anki
python main.py anotar "mi-libro.epub" -d vocab_traducido.json
python main.py anki vocab_traducido.json --mazo "Mi libro"
```

### Flujo C: sin API (diccionario manual o incluido)

```bash
# Usar el diccionario de fantasía medieval incluido
python main.py run "Juego de Tronos.epub" -d diccionarios/es_en_fantasia.json

# O crear tu propio diccionario JSON:
# {
#   "ciudad": "city",
#   "camino": "road",
#   "oscuridad": "darkness"
# }
python main.py anotar "libro.epub" -d mi_diccionario.json
```

### Flujo D: mismo libro, diferentes intensidades

La **intensidad** controla cuántas palabras distintas se reemplazan por cada fragmento de texto. Experimenta para encontrar tu punto óptimo:

| Intensidad | Experiencia de lectura |
|---|---|
| 1–2 | Apenas perceptible, muy cómodo |
| 3–4 | Balance ideal para la mayoría |
| 5–7 | Denso, bueno si ya tienes base |
| 8+ | Muy denso, casi traducción parcial |

```bash
python main.py anotar "libro.epub" -d dict.json -i 2 -s libro_nivel1.epub
python main.py anotar "libro.epub" -d dict.json -i 4 -s libro_nivel2.epub
python main.py anotar "libro.epub" -d dict.json -i 7 -s libro_nivel3.epub
```

---

## Diccionarios incluidos

El repositorio incluye un diccionario listo para usar en `diccionarios/`:

| Archivo | Contenido | Entradas |
|---|---|---|
| `es_en_fantasia.json` | Vocabulario de fantasía medieval español→inglés | 717 palabras |

Incluye verbos conjugados (pretérito, imperfecto, infinitivos), sustantivos (personas, lugares, objetos, naturaleza, emociones), adjetivos, adverbios y frases comunes. Optimizado para libros de fantasía como *Juego de Tronos*, *El Señor de los Anillos* o similares.

Puedes editar el JSON directamente o crear tus propios diccionarios para otros géneros.

---

## Idiomas soportados

Cualquier par de idiomas que soporte DeepL. Algunos ejemplos:

| `--origen` | `--destino` | Par |
|---|---|---|
| `es` | `en` | Español → Inglés (default) |
| `en` | `es` | Inglés → Español |
| `fr` | `en` | Francés → Inglés |
| `de` | `en` | Alemán → Inglés |
| `it` | `en` | Italiano → Inglés |
| `pt` | `en` | Portugués → Inglés |
| `ja` | `en` | Japonés → Inglés |

Lista completa: [developers.deepl.com/docs/resources/supported-languages](https://developers.deepl.com/docs/resources/supported-languages)

---

## Estructura del proyecto

```
script-traductor/
├── main.py                        # Entry point: python main.py <comando>
├── requirements.txt               # Dependencias Python
├── immersion/
│   ├── anotador.py                # Motor de anotación del epub
│   ├── extractor.py               # Extrae vocabulario por frecuencia
│   ├── traductor.py               # Integración con DeepL API
│   ├── anki_export.py             # Generación de mazos .apkg
│   ├── pipeline.py                # Orquesta los cuatro pasos
│   └── cli.py                     # Definición de subcomandos
├── diccionarios/
│   └── es_en_fantasia.json        # Diccionario incluido (717 entradas)
└── epub_traductor.py              # Script original (compatibilidad)
```

---

## Preguntas frecuentes

**¿El libro original se modifica?**
No. Siempre se crea un archivo nuevo (`_anotado.epub`). El original no se toca.

**¿Funciona con cualquier epub?**
Con la mayoría. El epub debe tener texto real (no ser un escaneo de imagen). DRM (protección de copia) impide procesarlo — asegúrate de usar epubs sin DRM.

**¿Qué pasa si no tengo API key de DeepL?**
Puedes usar el diccionario incluido (`-d diccionarios/es_en_fantasia.json`) o crear el tuyo propio en JSON. Solo los pasos de traducción automática requieren la API.

**¿Los resultados son siempre iguales?**
Por defecto, el vocabulario que se reemplaza varía en cada ejecución (para variar el vocabulario expuesto). Usa `--semilla N` con cualquier número entero para obtener resultados reproducibles entre ejecuciones.

**¿Cómo importo el mazo en Anki?**
Abre Anki → Archivo → Importar → selecciona el `.apkg` generado. Las tarjetas aparecen en el mazo con el nombre que especificaste.

**¿Consume muchos caracteres de DeepL?**
Depende del libro y `--max-palabras`. Con el default de 500 palabras, cada procesamiento consume aproximadamente 2.000–5.000 caracteres, muy por debajo del límite mensual gratuito de 500.000.
