# Diseño: Simplificación de opciones de conversión + intensidad dinámica

**Fecha:** 2026-05-20
**Rama:** feat/simplify-intensity-ux

---

## Objetivo

Simplificar la experiencia del usuario en la webapp eliminando opciones técnicas innecesarias (`max_palabras`, `semilla`) y haciendo que la intensidad escale automáticamente con la longitud de los párrafos. Se añade también un texto explicativo para que el usuario entienda qué hace la herramienta y conozca las ventajas de usar una API key.

---

## Cambios

### 1. Frontend — `static/index.html`

**Eliminar** de la sección "Opciones avanzadas":
- Bloque `maxPalabras` (input numérico "Máximo de palabras a procesar")
- Bloque `semilla` (checkbox + input numérico "Semilla aleatoria")

**Añadir** campo oculto para `max_palabras`:
```html
<input type="hidden" id="maxPalabrasHidden" name="max_palabras" value="500" />
```

**Añadir** texto explicativo en la card "¿Cómo quieres aprenderlo?", antes de los botones de intensidad:

> **¿Cómo funciona la anotación?**
> La app analiza tu libro, extrae las palabras más frecuentes y las reemplaza con su traducción resaltada directamente en el texto. Así puedes leer con fluidez mientras absorbes vocabulario nuevo de forma natural.
>
> Para mejores resultados, recomendamos usar **DeepL** o **Google AI** — traducen las palabras específicas de tu libro con mucha más precisión que un diccionario genérico. Puedes obtener una clave gratuita en menos de 2 minutos.

### 2. Frontend — `static/app.js`

**Actualizar** los listeners de los botones de preset para que también actualicen `max_palabras`:

| Preset  | `intensidad` | `max_palabras` |
|---------|-------------|----------------|
| Sutil   | 2           | 300            |
| Normal  | 4           | 500            |
| Intenso | 8           | 800            |

**Eliminar**:
- Variables y listeners de `semillaCheck` y `semillaInput`
- Lógica `fd.set('semilla', ...)` en el submit handler

### 3. Backend — `immersion/anotador.py`

Cambiar el tope de reemplazos en `anotar_texto` de fijo a proporcional con fallback:

```python
_DIVISOR = {2: 100, 4: 60, 8: 30}

word_count = len(texto.split())
divisor = _DIVISOR.get(intensidad, 50)
cap = max(intensidad, word_count // divisor)
```

Comportamiento resultante:

| Párrafo  | Sutil (÷100) | Normal (÷60) | Intenso (÷30) |
|----------|-------------|-------------|--------------|
| 100 pal. | 2           | 4           | 8            |
| 300 pal. | 3           | 5           | 10           |
| 600 pal. | 6           | 10          | 20           |

Para valores de intensidad fuera del mapa (uso desde CLI con valores personalizados), el divisor cae a 50 como fallback.

### 4. Sin cambios

- `webapp.py`: recibe `max_palabras` desde el form hidden y `semilla=None` por defecto — sin modificaciones necesarias.
- `immersion/pipeline.py`, `immersion/cli.py`: el CLI mantiene todas sus opciones (`--max-palabras`, `--semilla`, `--intensidad`) sin cambios.

---

## Alcance excluido

- No se modifica el CLI.
- No se cambia la lógica de extracción de vocabulario (`extractor.py`).
- No se tocan los valores de intensidad por defecto del backend (siguen siendo parámetros independientes).
