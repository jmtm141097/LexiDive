'use strict';

let currentJobId = null;
let pollTimer = null;

// ── File drag & drop ──────────────────────────────────────────────────────────

const dropZone    = document.getElementById('dropZone');
const epubFile    = document.getElementById('epubFile');
const dropContent = document.getElementById('dropContent');
const fileSelected = document.getElementById('fileSelected');
const fileNameEl  = document.getElementById('fileName');

document.getElementById('browseBtn').addEventListener('click', e => { e.stopPropagation(); epubFile.click(); });
document.getElementById('removeFile').addEventListener('click', clearEpub);

dropZone.addEventListener('click', () => {
  if (fileSelected.hidden) epubFile.click();
});

dropZone.addEventListener('dragover', e => {
  e.preventDefault();
  dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));

dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file) assignEpub(file);
});

epubFile.addEventListener('change', () => {
  if (epubFile.files[0]) assignEpub(epubFile.files[0]);
});

function assignEpub(file) {
  if (!file.name.toLowerCase().endsWith('.epub')) {
    alert('Por favor selecciona un archivo .epub');
    return;
  }
  const dt = new DataTransfer();
  dt.items.add(file);
  epubFile.files = dt.files;
  fileNameEl.textContent = file.name;
  dropContent.hidden = true;
  fileSelected.hidden = false;
}

function clearEpub() {
  epubFile.value = '';
  dropContent.hidden = false;
  fileSelected.hidden = true;
}

// ── Intensity presets ─────────────────────────────────────────────────────────

const intensidadInput = document.getElementById('intensidad');

document.querySelectorAll('.preset-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('preset-btn--active'));
    btn.classList.add('preset-btn--active');
    intensidadInput.value = btn.dataset.intensity;
  });
});

// ── Anki toggle ───────────────────────────────────────────────────────────────

const ankiToggle = document.getElementById('ankiToggle');

// ── Dictionary loader ─────────────────────────────────────────────────────────

const dictRadioGroup = document.getElementById('dictRadioGroup');

async function loadDiccionarios() {
  const origen = document.querySelector('select[name="origen"]').value;
  const destino = document.querySelector('select[name="destino"]').value;

  let dicts = [];
  try {
    const res = await fetch(`/diccionarios?origen=${origen}&destino=${destino}`);
    if (res.ok) dicts = await res.json();
  } catch { /* keep empty */ }

  const currentVal = (document.querySelector('input[name="diccionario_tipo"]:checked') || {}).value || 'ninguno';

  const rows = dicts.map(d => `
    <label class="radio-option">
      <input type="radio" name="diccionario_tipo" value="${d.id}" ${currentVal === d.id ? 'checked' : ''} />
      <div class="radio-content">
        <strong>${d.nombre}</strong>
        <span class="hint">${d.palabras} palabras ${langName(d.origen)} → ${langName(d.destino)}. No requiere API key.</span>
      </div>
    </label>`).join('');

  const ownChecked = currentVal === 'propio' ? 'checked' : '';
  const noneChecked = (!currentVal || currentVal === 'ninguno' || (!dicts.find(d => d.id === currentVal) && currentVal !== 'propio')) && dicts.length === 0 ? 'checked' : (currentVal === 'ninguno' ? 'checked' : '');

  dictRadioGroup.innerHTML = rows + `
    <label class="radio-option">
      <input type="radio" name="diccionario_tipo" value="propio" ${ownChecked} />
      <div class="radio-content">
        <strong>Subir mi propio diccionario JSON</strong>
        <span class="hint">Formato: <code>{"palabra_origen": "traducción"}</code></span>
      </div>
    </label>
    <label class="radio-option">
      <input type="radio" name="diccionario_tipo" value="ninguno" ${noneChecked} />
      <div class="radio-content">
        <strong>Sin diccionario base</strong>
        <span class="hint">Solo usará el proveedor de traducción configurado (requiere API Key)</span>
      </div>
    </label>`;

  // If there are matching dicts and no valid selection, select the first
  const checkedNow = document.querySelector('input[name="diccionario_tipo"]:checked');
  if (!checkedNow && dicts.length > 0) {
    dictRadioGroup.querySelector(`input[value="${dicts[0].id}"]`).checked = true;
  } else if (!checkedNow) {
    dictRadioGroup.querySelector('input[value="ninguno"]').checked = true;
  }

  // Re-attach show/hide logic for custom dict
  dictRadioGroup.querySelectorAll('input[name="diccionario_tipo"]').forEach(radio => {
    radio.addEventListener('change', () => {
      document.getElementById('customDictSection').hidden = radio.value !== 'propio';
    });
  });
  document.getElementById('customDictSection').hidden =
    (document.querySelector('input[name="diccionario_tipo"]:checked') || {}).value !== 'propio';
}

const _LANG_NAMES = {
  es: 'Español', en: 'Inglés', fr: 'Francés', de: 'Alemán',
  it: 'Italiano', pt: 'Portugués', ja: 'Japonés', zh: 'Chino',
  ru: 'Ruso', ko: 'Coreano',
};
function langName(code) { return _LANG_NAMES[code] || code.toUpperCase(); }

document.querySelector('select[name="origen"]').addEventListener('change', loadDiccionarios);
document.querySelector('select[name="destino"]').addEventListener('change', loadDiccionarios);

loadDiccionarios();

// ── Translation provider toggle ───────────────────────────────────────────────

document.querySelectorAll('input[name="traductor_proveedor"]').forEach(radio => {
  radio.addEventListener('change', () => {
    document.getElementById('deeplKeySection').hidden = radio.value !== 'deepl';
    document.getElementById('googleKeySection').hidden = radio.value !== 'google';
  });
});

// ── Seed checkbox ─────────────────────────────────────────────────────────────

const semillaCheck = document.getElementById('semillaCheck');
const semillaInput = document.getElementById('semillaInput');

semillaCheck.addEventListener('change', () => {
  semillaInput.disabled = !semillaCheck.checked;
});

// ── Language pair validation ──────────────────────────────────────────────────────────

function validateLanguages() {
  const origen = document.querySelector('select[name="origen"]').value;
  const destino = document.querySelector('select[name="destino"]').value;
  if (origen === destino) {
    document.querySelector('select[name="destino"]').focus();
    alert('El idioma del libro y el idioma de traducción deben ser diferentes.');
    return false;
  }
  return true;
}

document.querySelector('select[name="origen"]').addEventListener('change', () => {
  const origen = document.querySelector('select[name="origen"]').value;
  const destino = document.querySelector('select[name="destino"]').value;
  if (origen === destino) {
    const opts = document.querySelectorAll('select[name="destino"] option');
    const fallback = [...opts].find(o => o.value !== origen);
    if (fallback) document.querySelector('select[name="destino"]').value = fallback.value;
    loadDiccionarios();
  }
});

// ── Form submit ───────────────────────────────────────────────────────────────

document.getElementById('processForm').addEventListener('submit', async e => {
  e.preventDefault();

  if (!epubFile.files[0]) {
    alert('Por favor selecciona un archivo .epub');
    return;
  }

  if (!validateLanguages()) return;

  const dictTipo = (document.querySelector('input[name="diccionario_tipo"]:checked') || {}).value || 'ninguno';
  const deepKey = document.getElementById('deeplKey').value.trim();
  const googleKey = document.getElementById('googleKey').value.trim();
  if (dictTipo === 'ninguno' && !deepKey && !googleKey) {
    document.querySelector('.card--details').open = true;
    document.querySelector('.card--details').scrollIntoView({ behavior: 'smooth', block: 'start' });
    alert('Para procesar tu libro necesitas al menos una de estas opciones:\n\n• Un diccionario base (selecciona uno en Opciones avanzadas)\n• Una API key de DeepL o Google AI');
    return;
  }

  const fd = new FormData(e.target);

  // sin_anki: the backend expects true when NOT generating the deck
  fd.set('sin_anki', (!ankiToggle.checked).toString());

  // Seed: only include if the checkbox is active
  if (semillaCheck.checked && semillaInput.value) {
    fd.set('semilla', semillaInput.value);
  }

  // Remove custom dict file if not needed
  if (fd.get('diccionario_tipo') !== 'propio') fd.delete('diccionario_json');

  umami.track('libro_enviado', {
    origen: fd.get('origen'),
    destino: fd.get('destino'),
    intensidad: fd.get('intensidad'),
    anki: ankiToggle.checked,
  });

  showProgress();

  try {
    const res = await fetch('/process', { method: 'POST', body: fd });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Error desconocido' }));
      showError(err.detail || 'Error al iniciar el proceso');
      return;
    }
    const data = await res.json();
    currentJobId = data.job_id;
    startPolling();
  } catch (err) {
    showError('Error de conexión: ' + err.message);
  }
});

// ── Polling ───────────────────────────────────────────────────────────────────

function startPolling() {
  pollTimer = setInterval(async () => {
    try {
      const res = await fetch(`/status/${currentJobId}`);
      if (!res.ok) return;
      const data = await res.json();

      setProgress(data.progress ?? 0, data.message ?? '');

      if (data.status === 'done') {
        clearInterval(pollTimer);
        umami.track('libro_procesado', {
          capitulos: data.stats?.capitulos,
          palabras_nuevas: data.stats?.palabras_nuevas,
          total_diccionario: data.stats?.total_diccionario,
        });
        showResults(data.stats, currentJobId);
      } else if (data.status === 'error') {
        clearInterval(pollTimer);
        umami.track('error_procesamiento', { mensaje: data.message });
        showError(data.message);
      }
    } catch {
      // transient network error — keep polling
    }
  }, 1500);
}

// ── UI state helpers ──────────────────────────────────────────────────────────

function showProgress() {
  hide('resultsSection');
  hide('errorSection');
  show('progressSection');
  document.getElementById('progressTitle').textContent = 'Procesando tu libro…';
  document.getElementById('submitBtn').disabled = true;
  setProgress(3, 'Iniciando…');
  scroll('progressSection');
}

function setProgress(pct, msg) {
  document.getElementById('progressFill').style.width = pct + '%';
  document.getElementById('progressMsg').textContent = msg;
}

function showResults(stats, jobId) {
  hide('progressSection');
  show('resultsSection');
  document.getElementById('submitBtn').disabled = false;

  document.getElementById('statsBox').innerHTML =
    statCard(stats.capitulos,        'Capítulos anotados')
    + statCard(stats.palabras_nuevas,  'Palabras extraídas')
    + statCard(stats.total_diccionario,'Palabras en diccionario');

  const base = `/download/${jobId}`;
  setDownload('dlEpub', `${base}/epub`);
  setDownload('dlJson', `${base}/json`);

  const dlApkg = document.getElementById('dlApkg');
  if (ankiToggle.checked) {
    setDownload('dlApkg', `${base}/apkg`);
    dlApkg.hidden = false;
  } else {
    dlApkg.hidden = true;
  }

  setDownload('dlDict', `${base}/dict`);

  scroll('resultsSection');
}

function setDownload(id, href) {
  const el = document.getElementById(id);
  el.href = href;
  el.classList.remove('unavailable');
  el.addEventListener('click', () => umami.track('descarga', { tipo: id.replace('dl', '').toLowerCase() }), { once: true });
}

function showError(msg) {
  hide('progressSection');
  show('errorSection');
  document.getElementById('errorMsg').textContent = msg;
  document.getElementById('submitBtn').disabled = false;
  scroll('errorSection');
}

function statCard(num, label) {
  return `<div class="stat-item"><span class="stat-num">${num ?? '—'}</span><span class="stat-label">${label}</span></div>`;
}

function show(id)   { document.getElementById(id).hidden = false; }
function hide(id)   { document.getElementById(id).hidden = true; }
function scroll(id) { document.getElementById(id).scrollIntoView({ behavior: 'smooth', block: 'start' }); }

// ── Reset ─────────────────────────────────────────────────────────────────────

document.getElementById('newJobBtn').addEventListener('click', resetUI);
document.getElementById('retryBtn').addEventListener('click', resetUI);

function resetUI() {
  hide('resultsSection');
  hide('errorSection');
  currentJobId = null;
  clearInterval(pollTimer);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}
