# Simplify Intensity UX Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminar las opciones `max_palabras` y `semilla` de la UI, vincular `max_palabras` a los presets de intensidad, añadir texto explicativo, y hacer que la intensidad escale dinámicamente con la longitud de los párrafos en el backend.

**Architecture:** Los tres botones Sutil/Normal/Intenso ya existen en la UI — se amplían para actualizar un campo oculto `max_palabras` además del campo `intensidad`. El backend (`anotar_texto`) reemplaza su tope fijo por un tope dinámico `max(intensidad, word_count // divisor)`. No hay cambios al CLI ni a `webapp.py`.

**Tech Stack:** Python 3.14, FastAPI, vanilla JS, HTML/CSS. Sin framework de tests — se verifica el backend con `python -c` y el frontend manualmente en el navegador.

---

## Archivos a modificar

| Archivo | Cambio |
|---------|--------|
| `immersion/anotador.py` | Añadir `_DIVISOR` y lógica de tope dinámico en `anotar_texto` |
| `static/index.html` | Eliminar 2 bloques de opciones avanzadas, añadir campo oculto y texto explicativo |
| `static/app.js` | Actualizar preset handlers, eliminar lógica de semilla |

---

## Task 1: Crear rama de trabajo

**Files:**
- (git)

- [ ] **Step 1: Crear y moverse a la nueva rama**

```bash
git checkout -b feat/simplify-intensity-ux
```

Expected: `Switched to a new branch 'feat/simplify-intensity-ux'`

---

## Task 2: Backend — intensidad dinámica en `anotador.py`

**Files:**
- Modify: `immersion/anotador.py:50-111`

- [ ] **Step 1: Verificar que el comportamiento actual es fijo**

```bash
python -c "
from immersion.anotador import anotar_texto
import random
dic = [('espada', 'sword'), ('bosque', 'forest'), ('oscuro', 'dark'), ('hombre', 'man'),
       ('noche', 'night'), ('fuego', 'fire'), ('tiempo', 'time'), ('lugar', 'place')]
# párrafo largo (~80 palabras, debería quedarse en cap=8 con código actual)
texto = ' '.join(['El hombre tomó su espada y miró hacia el bosque oscuro de la noche'] * 8)
resultado = anotar_texto(texto, dic, 8, random.Random(42), {})
import re
marks = re.findall(r'<mark', resultado)
print('Reemplazos encontrados:', len(marks))
"
```

Expected: imprime `Reemplazos encontrados: 8` (tope fijo actual).

- [ ] **Step 2: Añadir `_DIVISOR` a nivel de módulo y lógica dinámica en `anotar_texto`**

En `immersion/anotador.py`, localizar la línea `_CACHE: dict[str, re.Pattern] = {}` (aprox. línea 12) y añadir debajo:

```python
_DIVISOR: dict[int, int] = {2: 100, 4: 60, 8: 30}
```

Luego localizar la función `anotar_texto` (línea ~50). Reemplazar:

```python
    reemplazos_count = 0

    for origen, destino in entradas:
        if intensidad > 0 and reemplazos_count >= intensidad:
            break
```

por:

```python
    reemplazos_count = 0
    word_count = len(texto.split())
    divisor = _DIVISOR.get(intensidad, 50)
    cap = max(intensidad, word_count // divisor)

    for origen, destino in entradas:
        if intensidad > 0 and reemplazos_count >= cap:
            break
```

- [ ] **Step 3: Verificar que el cap escala con párrafos largos**

```bash
python -c "
from immersion.anotador import anotar_texto
import random
dic = [('espada', 'sword'), ('bosque', 'forest'), ('oscuro', 'dark'), ('hombre', 'man'),
       ('noche', 'night'), ('fuego', 'fire'), ('tiempo', 'time'), ('lugar', 'place'),
       ('reino', 'kingdom'), ('batalla', 'battle'), ('guerrero', 'warrior'), ('ciudad', 'city')]
# párrafo corto (~15 palabras) — debe respetar el mínimo de 8
texto_corto = 'El hombre tomó su espada y miró hacia el bosque oscuro de la noche con fuego'
r1 = anotar_texto(texto_corto, dic, 8, random.Random(42), {})
import re
print('Párrafo corto (Intenso):', len(re.findall(r'<mark', r1)), '(esperado: ≤8)')

# párrafo largo (~300 palabras) — debe superar 8
texto_largo = ' '.join(['El hombre tomó su espada y miró hacia el bosque oscuro de la noche con fuego en el reino de batalla con el guerrero de la ciudad'] * 15)
r2 = anotar_texto(texto_largo, dic, 8, random.Random(42), {})
print('Párrafo largo (Intenso):', len(re.findall(r'<mark', r2)), '(esperado: >8)')

# verificar Sutil en párrafo corto sigue siendo 2
r3 = anotar_texto(texto_corto, dic, 2, random.Random(42), {})
print('Párrafo corto (Sutil):', len(re.findall(r'<mark', r3)), '(esperado: 2)')
"
```

Expected:
```
Párrafo corto (Intenso): 8 (esperado: ≤8)
Párrafo largo (Intenso): <número mayor que 8> (esperado: >8)
Párrafo corto (Sutil): 2 (esperado: 2)
```

- [ ] **Step 4: Commit**

```bash
git add immersion/anotador.py
git commit -m "feat: dynamic annotation cap scales with paragraph length

Replaces fixed intensidad cap with max(intensidad, word_count // divisor).
Divisors: Sutil=100, Normal=60, Intenso=30. Fallback 50 for custom CLI values."
```

---

## Task 3: Frontend — limpiar `static/index.html`

**Files:**
- Modify: `static/index.html`

- [ ] **Step 1: Añadir texto explicativo antes de los botones de intensidad**

Localizar en `index.html` la línea con `<div class="setting-block">` que contiene `<label class="setting-label">Intensidad de las anotaciones</label>` (aprox. línea 81).

Insertar **antes** de ese `<div class="setting-block">` el bloque explicativo:

```html
        <div class="info-block">
          <p class="info-title">¿Cómo funciona la anotación?</p>
          <p class="info-body">
            La app analiza tu libro, extrae las palabras más frecuentes y las reemplaza con su
            traducción resaltada directamente en el texto. Así puedes leer con fluidez mientras
            absorbes vocabulario nuevo de forma natural.
          </p>
          <p class="info-body">
            Para mejores resultados, recomendamos usar <strong>DeepL</strong> o <strong>Google AI</strong>
            — traducen las palabras específicas de tu libro con mucha más precisión que un diccionario
            genérico. Puedes obtener una clave gratuita en menos de 2 minutos.
          </p>
        </div>
```

- [ ] **Step 2: Añadir campo oculto `max_palabras` junto al campo `intensidad`**

Localizar la línea:
```html
          <input type="range" id="intensidad" name="intensidad" min="1" max="10" value="4" hidden />
```

Añadir inmediatamente después:
```html
          <input type="hidden" id="maxPalabrasHidden" name="max_palabras" value="500" />
```

- [ ] **Step 3: Eliminar el bloque `maxPalabras` de Opciones avanzadas**

Localizar y eliminar este bloque completo (aprox. líneas 234–238):

```html
          <div class="setting-block">
            <label class="setting-label" for="maxPalabras">Máximo de palabras a procesar</label>
            <p class="hint" style="margin-bottom:.5rem">Cuántas palabras distintas extraer y anotar del libro</p>
            <input type="number" id="maxPalabras" name="max_palabras" value="500" min="10" max="5000" class="input-sm" />
          </div>
```

- [ ] **Step 4: Eliminar el bloque `semilla` de Opciones avanzadas**

Localizar y eliminar este bloque completo (aprox. líneas 240–249):

```html
          <div class="setting-block" style="margin-bottom:0">
            <label class="setting-label">Semilla aleatoria</label>
            <p class="hint" style="margin-bottom:.5rem">
              Activa para que el proceso sea reproducible — siempre se elegirán las mismas palabras
            </p>
            <div class="seed-row">
              <input type="checkbox" id="semillaCheck" />
              <input type="number" id="semillaInput" value="42" class="input-sm" disabled placeholder="42" />
            </div>
          </div>
```

- [ ] **Step 5: Añadir estilos para el bloque explicativo en `static/style.css`**

Abrir `static/style.css` y añadir al final:

```css
.info-block {
  background: var(--parchment);
  border-left: 3px solid var(--accent);
  border-radius: 6px;
  padding: .85rem 1rem;
  margin-bottom: 1.25rem;
}

.info-title {
  font-weight: 600;
  margin: 0 0 .4rem;
  font-size: .95rem;
}

.info-body {
  margin: 0 0 .4rem;
  font-size: .875rem;
  line-height: 1.55;
  color: var(--muted);
}

.info-body:last-child {
  margin-bottom: 0;
}
```

---

## Task 4: Frontend — actualizar `static/app.js`

**Files:**
- Modify: `static/app.js`

- [ ] **Step 1: Actualizar preset button handler para también setear `max_palabras`**

Localizar el bloque actual (aprox. líneas 60–68):

```javascript
const intensidadInput = document.getElementById('intensidad');

document.querySelectorAll('.preset-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('preset-btn--active'));
    btn.classList.add('preset-btn--active');
    intensidadInput.value = btn.dataset.intensity;
  });
});
```

Reemplazar por:

```javascript
const intensidadInput = document.getElementById('intensidad');
const maxPalabrasInput = document.getElementById('maxPalabrasHidden');

const PRESET_MAX_PALABRAS = { '2': 300, '4': 500, '8': 800 };

document.querySelectorAll('.preset-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('preset-btn--active'));
    btn.classList.add('preset-btn--active');
    intensidadInput.value = btn.dataset.intensity;
    maxPalabrasInput.value = PRESET_MAX_PALABRAS[btn.dataset.intensity] ?? 500;
  });
});
```

- [ ] **Step 2: Eliminar listeners de semilla**

Localizar y eliminar este bloque completo (aprox. líneas 154–161):

```javascript
// ── Seed checkbox ─────────────────────────────────────────────────────────────

const semillaCheck = document.getElementById('semillaCheck');
const semillaInput = document.getElementById('semillaInput');

semillaCheck.addEventListener('change', () => {
  semillaInput.disabled = !semillaCheck.checked;
});
```

- [ ] **Step 3: Eliminar lógica de semilla en el submit handler**

Localizar y eliminar estas líneas del submit handler (aprox. líneas 226–228):

```javascript
  // Seed: only include if the checkbox is active
  if (semillaCheck.checked && semillaInput.value) {
    fd.set('semilla', semillaInput.value);
  }
```

- [ ] **Step 4: Commit**

```bash
git add static/index.html static/app.js static/style.css
git commit -m "feat: simplify UX — remove max_palabras/semilla controls

Preset buttons now control both intensidad and max_palabras (Sutil=300,
Normal=500, Intenso=800). Added explanatory block in form section 2.
Removed max_palabras input and semilla controls from advanced options."
```

---

## Task 5: Verificación manual en el navegador

- [ ] **Step 1: Arrancar el servidor**

```bash
uvicorn webapp:app --reload
```

- [ ] **Step 2: Verificar en http://localhost:8000**

Comprobar que:
- [ ] El texto explicativo aparece antes de los botones Sutil/Normal/Intenso con estilo correcto
- [ ] El bloque "Máximo de palabras" ya no aparece en Opciones avanzadas
- [ ] El bloque "Semilla aleatoria" ya no aparece en Opciones avanzadas
- [ ] Al hacer clic en cada preset, el campo oculto `max_palabras` cambia (verificar con DevTools → Elements buscando `maxPalabrasHidden`)
- [ ] El formulario envía correctamente con un epub de prueba y diccionario base

- [ ] **Step 3: Commit final si todo está bien**

```bash
git add docs/superpowers/specs/2026-05-20-simplify-intensity-ux-design.md
git add docs/superpowers/plans/2026-05-20-simplify-intensity-ux.md
git commit -m "docs: add spec and plan for simplify-intensity-ux"
```
