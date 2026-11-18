/* Verdant user dashboard */
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[char]);
}

const TECHNICAL_PATTERNS = [
  /\bAI\b/i,
  /artificial intelligence/i,
  /gemini/i,
  /plant\s*[@#]?\s*net/i,
  /\bAI[- ]assisted\b/i,
  /local (model|classifier|dataset)/i,
  /trained (model|classifier)/i,
  /\bclassifier\b/i,
  /\bmodel\b/i,
  /\bdataset\b/i,
  /\bfallback\b/i,
  /\bAPI\b/i,
  /confidence (score|source)/i,
  /\bscore\b/i,
  /candidate species/i,
  /primary analysis/i,
  /supporting only/i,
  /system[- ]generated/i,
  /reliability threshold/i,
  /\bthreshold\b/i,
  /\bsources?\b/i,
];

function cleanText(value) {
  if (Array.isArray(value)) return value.map(cleanText).filter(Boolean);
  const raw = String(value ?? '').trim();
  if (!raw) return '';
  return raw
    .split(/(?<=[.!?])\s+/)
    .map((sentence) => sentence.trim())
    .filter((sentence) => !TECHNICAL_PATTERNS.some((pattern) => pattern.test(sentence)))
    .join(' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function cleanList(values) {
  if (!Array.isArray(values)) return [];
  return [...new Set(values.map(cleanText).filter(Boolean))];
}

function firstText(...values) {
  for (const value of values) {
    const text = cleanText(value);
    if (text) return text;
  }
  return '';
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  let payload = {};
  try { payload = await response.json(); } catch (_) { /* empty response */ }
  if (!response.ok) {
    throw new Error(payload.detail || payload.error || `Request failed (${response.status})`);
  }
  return payload;
}

function toast(message, type = 'info') {
  const node = document.createElement('div');
  node.className = `toast ${type}`;
  node.textContent = message;
  $('#toast-root').appendChild(node);
  setTimeout(() => node.remove(), 4200);
}

function setView(name) {
  $$('.view').forEach((view) => view.classList.toggle('active', view.id === `view-${name}`));
  $$('.nav-item[data-section]').forEach((item) => item.classList.toggle('active', item.dataset.section === name));
  if (name === 'dashboard') loadDashboard();
  if (name === 'history') loadHistory();
  if (name === 'library') loadLibrary();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function statusParts(status) {
  const map = {
    success: ['badge-success', 'Identified'],
    uncertain: ['badge-warn', 'Needs review'],
    unsupported: ['badge-info', 'Outside reference set'],
    rejected: ['badge-danger', 'Image unsuitable'],
  };
  return map[status] || ['badge-muted', 'Not recorded'];
}

function statusBadge(status) {
  const [cls, label] = statusParts(status);
  return `<span class="badge ${cls}">${escapeHtml(label)}</span>`;
}

function statusMessage(status) {
  const map = {
    success: 'Identification complete.',
    uncertain: 'Please review the result carefully.',
    unsupported: 'This plant is outside the reference set.',
    rejected: 'The image could not be reviewed.',
  };
  return map[status] || 'Identification complete.';
}

function listHtml(items, empty = 'Not specified in this study.') {
  if (!Array.isArray(items) || !items.length) {
    return `<div class="muted">${escapeHtml(empty)}</div>`;
  }
  return `<ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>`;
}

function sectionHtml(title, content, empty = 'Not specified in this study.') {
  return `<div class="info-block"><h4>${escapeHtml(title)}</h4>${content || `<div class="muted">${escapeHtml(empty)}</div>`}</div>`;
}

function renderResult(data) {
  const explanation = (data.ai && data.ai.explanation) || {};
  const localInfo = data.localInfo || {};
  const healthy = Boolean(data.isHealthy);
  const plant = cleanText(data.plant) || 'Plant not identified';
  const condition = cleanText(data.disease) || (healthy ? 'Healthy' : 'Condition not recorded');

  const description = firstText(explanation.assessment, localInfo.description, localInfo.notes);
  const characteristics = cleanList([
    ...(explanation.keyFindings || []),
    ...(explanation.symptoms || []),
    ...(localInfo.symptoms || []),
  ]);
  const uses = cleanList(explanation.uses);
  const growingConditions = cleanList(explanation.causes);
  const careInstructions = cleanList([
    ...(localInfo.recommendedActions || []),
    ...(localInfo.prevention || []),
    ...(explanation.prevention || []),
    ...(explanation.treatment || []),
    ...(explanation.futureCare || []),
  ]);

  const observation = healthy
    ? 'No disease symptoms were recorded for this image.'
    : 'Observed features are recorded below for review.';

  let html = `<div class="result-summary">
    <div class="result-image">${data.imageUrl ? `<img src="${escapeHtml(data.imageUrl)}" alt="Uploaded leaf">` : '<div class="empty-compact">No preview</div>'}</div>
    <div class="result-main">
      <div class="result-sub">${escapeHtml(plant)}</div>
      <div class="result-title">${escapeHtml(condition)}</div>
      <div class="result-sub">${escapeHtml(observation)}</div>
    </div>
  </div>`;

  html += sectionHtml('Plant Information', `<div class="kv-row">
    <span>Plant: <strong>${escapeHtml(plant)}</strong></span>
    <span>Condition: <strong>${escapeHtml(condition)}</strong></span>
    <span>Observation: <strong>${healthy ? 'Healthy' : 'Condition observed'}</strong></span>
  </div>`);

  html += sectionHtml('Identification Result', `<p class="assessment">${escapeHtml(condition)}</p>`);

  html += sectionHtml(
    'Plant Description',
    description ? `<p class="assessment">${escapeHtml(description)}</p>` : '',
    'A written description is not available for this record.',
  );

  html += sectionHtml(
    'Characteristics',
    listHtml(characteristics, 'No distinguishing features were recorded.'),
    'No distinguishing features were recorded.',
  );

  html += sectionHtml(
    'Uses',
    listHtml(uses, 'Use information is not recorded in this study.'),
    'Use information is not recorded in this study.',
  );

  html += sectionHtml(
    'Growing Conditions',
    listHtml(growingConditions, 'Growing conditions are not recorded in this study.'),
    'Growing conditions are not recorded in this study.',
  );

  html += sectionHtml(
    'Care Instructions',
    listHtml(careInstructions, 'No care instructions were recorded.'),
    'No care instructions were recorded.',
  );

  if (data.weather && data.weather.available) {
    html += `<div class="weather-card">Local weather: ${escapeHtml(data.weather.condition)} · ${data.weather.temperature}°C · humidity ${data.weather.humidity}% · rain ${data.weather.precipitation} mm</div>`;
  }

  return html;
}

async function loadDashboard() {
  try {
    const stats = await api('/api/stats');
    $('#stat-total').textContent = stats.total;
    $('#stat-healthy').textContent = stats.healthy;
    $('#stat-diseased').textContent = stats.diseased;
    const conditions = stats.by_disease || [];
    const max = Math.max(1, ...conditions.map((item) => item.value));
    $('#dash-diseases').innerHTML = conditions.length
      ? conditions.slice(0, 6).map((item) => `<div class="bar-row"><span class="bar-label" title="${escapeHtml(item.name)}">${escapeHtml(item.name)}</span><div class="bar-track"><div class="bar-fill" style="width:${(item.value / max) * 100}%"></div></div><span class="bar-value">${item.value}</span></div>`).join('')
      : '<div class="empty-compact">No records yet.</div>';
    const recent = stats.recent || [];
    $('#dash-recent').innerHTML = recent.length
      ? recent.slice(0, 5).map((item) => `<div class="recent-item"><img src="${escapeHtml(item.image_url)}" alt=""><div class="recent-meta"><strong>${escapeHtml(cleanText(item.disease) || 'Not recorded')}</strong><small>${escapeHtml(cleanText(item.plant) || '')} · ${escapeHtml(item.created_at)}</small></div>${statusBadge(item.status)}</div>`).join('')
      : '<div class="empty-compact">No records yet.</div>';
  } catch (error) { toast(error.message, 'error'); }
}

let selectedFile = null;
function setFile(file) {
  selectedFile = file || null;
  const input = $('#image-input');
  if (!file) {
    input.value = '';
    $('#preview-wrap').hidden = true;
    $('#file-line').textContent = 'No file selected';
    $('#analyze-btn').disabled = true;
    return;
  }
  if (!file.type.startsWith('image/')) {
    toast('Please choose an image file.', 'error');
    return setFile(null);
  }
  $('#file-line').textContent = `${file.name} · ${(file.size / 1024 / 1024).toFixed(2)} MB`;
  $('#preview-img').src = URL.createObjectURL(file);
  $('#preview-wrap').hidden = false;
  $('#analyze-btn').disabled = false;
}

function getLocation() {
  return new Promise((resolve) => {
    if (!navigator.geolocation) return resolve({});
    navigator.geolocation.getCurrentPosition(
      (position) => resolve({ latitude: position.coords.latitude, longitude: position.coords.longitude }),
      () => resolve({}),
      { timeout: 6000, maximumAge: 300000 },
    );
  });
}

async function runDetection() {
  if (!selectedFile) return;
  const button = $('#analyze-btn');
  button.disabled = true;
  button.textContent = 'Identifying…';
  $('#progress-track').hidden = false;
  $('#result-empty').hidden = true;
  $('#result-content').hidden = false;
  $('#result-content').innerHTML = '<div class="empty-compact">Reviewing the image…</div>';
  $('#result-badge').hidden = true;
  try {
    const form = new FormData();
    form.append('image', selectedFile);
    if ($('#weather-opt').checked) {
      const location = await getLocation();
      if (location.latitude != null) {
        form.append('latitude', location.latitude);
        form.append('longitude', location.longitude);
      } else {
        toast('Location unavailable; continuing without weather.', 'info');
      }
    }
    const result = await api('/api/detect', { method: 'POST', body: form });
    $('#result-content').innerHTML = renderResult(result);
    $('#result-badge').hidden = false;
    const [badgeClass, badgeLabel] = statusParts(result.status);
    $('#result-badge').className = `badge ${badgeClass}`;
    $('#result-badge').textContent = badgeLabel;
    setFile(null);
    loadDashboard();
    toast(statusMessage(result.status), 'success');
  } catch (error) {
    $('#result-empty').hidden = false;
    $('#result-content').hidden = true;
    toast(error.message, 'error');
  } finally {
    button.disabled = !selectedFile;
    button.innerHTML = 'Identify plant <span>→</span>';
    $('#progress-track').hidden = true;
  }
}

async function loadHistory() {
  const query = $('#history-search').value.trim();
  const status = $('#history-status').value;
  try {
    const data = await api(`/api/history?limit=100&query=${encodeURIComponent(query)}&status=${encodeURIComponent(status)}`);
    const items = data.items || [];
    $('#history-list').innerHTML = items.length ? items.map((item) => `
      <div class="history-card" data-id="${item.id}">
        <img src="${escapeHtml(item.image_url)}" alt="">
        <div class="history-meta"><strong>${escapeHtml(cleanText(item.disease) || 'Not recorded')}</strong><small>${escapeHtml(cleanText(item.plant) || 'Plant not recorded')} · ${escapeHtml(item.created_at)}</small></div>
        <div class="history-actions">${statusBadge(item.status)}<button class="link-btn history-delete" data-id="${item.id}">Delete</button></div>
      </div>`).join('') : '<div class="empty-compact">No matching records.</div>';

    $$('.history-card').forEach((card) => card.addEventListener('click', (event) => {
      if (event.target.closest('.history-delete')) return;
      openDetail(card.dataset.id);
    }));
    $$('.history-delete').forEach((button) => button.addEventListener('click', async (event) => {
      event.stopPropagation();
      if (!confirm('Delete this record and its image?')) return;
      try {
        await api(`/api/history/${button.dataset.id}`, { method: 'DELETE' });
        toast('Record deleted.', 'success');
        loadHistory(); loadDashboard();
      } catch (error) { toast(error.message, 'error'); }
    }));
  } catch (error) { toast(error.message, 'error'); }
}

async function openDetail(id) {
  try {
    const detail = await api(`/api/history/${id}`);
    const result = {
      imageUrl: detail.image_url,
      status: detail.status,
      plant: detail.plant,
      disease: detail.disease,
      isHealthy: detail.is_healthy,
      localInfo: {},
      ai: { explanation: detail.ai_explanation || {} },
      weather: detail.weather,
    };
    $('#detail-modal-body').innerHTML = renderResult(result);
    $('#detail-modal').hidden = false;
  } catch (error) { toast(error.message, 'error'); }
}

let libraryItems = [];
async function loadLibrary() {
  try {
    libraryItems = await api('/api/diseases');
    renderLibrary();
  } catch (error) { toast(error.message, 'error'); }
}
function renderLibrary() {
  const query = $('#library-search').value.trim().toLowerCase();
  const filtered = libraryItems.filter((item) => `${item.plant} ${item.disease}`.toLowerCase().includes(query));
  $('#library-count').textContent = `${filtered.length} of ${libraryItems.length}`;
  $('#library-grid').innerHTML = filtered.length ? filtered.map((item) => `
    <div class="lib-card">
      <span class="tag ${item.isHealthy ? 'tag-healthy' : ''}">${item.isHealthy ? 'Healthy' : escapeHtml(item.severity)}</span>
      <h4>${escapeHtml(item.disease)}</h4>
      <p>${escapeHtml(item.plant)}</p>
      <div class="top-preds">${(item.symptoms || []).slice(0, 2).map((s) => `<span class="chip">${escapeHtml(s)}</span>`).join('')}</div>
    </div>`).join('') : '<div class="empty-compact">No matching conditions.</div>';
}

function init() {
  $$('.nav-item[data-section]').forEach((item) => item.addEventListener('click', (event) => {
    event.preventDefault(); setView(item.dataset.section);
  }));
  $$('[data-goto]').forEach((button) => button.addEventListener('click', () => setView(button.dataset.goto)));
  $('#menu-toggle').addEventListener('click', () => $('#sidebar').classList.toggle('open'));

  const zone = $('#drop-zone');
  // The admin page shares base.html but has no detection form.
  if (!zone) return;

  zone.addEventListener('click', () => $('#image-input').click());
  zone.addEventListener('keydown', (event) => { if (event.key === 'Enter' || event.key === ' ') $('#image-input').click(); });
  $('#image-input').addEventListener('change', (event) => setFile(event.target.files[0]));
  $('#preview-clear').addEventListener('click', (event) => { event.stopPropagation(); setFile(null); });
  ['dragenter', 'dragover'].forEach((type) => zone.addEventListener(type, (event) => { event.preventDefault(); zone.classList.add('dragover'); }));
  ['dragleave', 'drop'].forEach((type) => zone.addEventListener(type, (event) => { event.preventDefault(); zone.classList.remove('dragover'); }));
  zone.addEventListener('drop', (event) => setFile(event.dataTransfer.files[0]));
  $('#detect-form').addEventListener('submit', (event) => { event.preventDefault(); runDetection(); });

  $('#history-search').addEventListener('input', loadHistory);
  $('#history-status').addEventListener('change', loadHistory);
  $('#history-refresh').addEventListener('click', loadHistory);
  $('#library-search').addEventListener('input', renderLibrary);
  $$('[data-modal-close]').forEach((element) => element.addEventListener('click', () => { $('#detail-modal').hidden = true; }));
  document.addEventListener('keydown', (event) => { if (event.key === 'Escape') $('#detail-modal').hidden = true; });

  $('#clear-history').addEventListener('click', async () => {
    if (!confirm('Delete ALL saved records and uploaded images?')) return;
    try {
      const result = await api('/api/history', { method: 'DELETE' });
      toast(result.message || 'Records deleted.', 'success'); loadHistory(); loadDashboard();
    } catch (error) { toast(error.message, 'error'); }
  });

  loadDashboard();
}

document.addEventListener('DOMContentLoaded', init);
