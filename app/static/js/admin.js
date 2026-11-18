/* Verdant admin panel */
const $admin = (selector, root = document) => root.querySelector(selector);
const $$admin = (selector, root = document) => Array.from(root.querySelectorAll(selector));

function adminEscape(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[char]);
}

async function adminApi(path, options = {}) {
  const response = await fetch(path, options);
  let payload = {};
  try { payload = await response.json(); } catch (_) { /* ignore */ }
  if (!response.ok) throw new Error(payload.detail || `Request failed (${response.status})`);
  return payload;
}

function adminToast(message, type = 'info') {
  const node = document.createElement('div');
  node.className = `toast ${type}`;
  node.textContent = message;
  $admin('#toast-root').appendChild(node);
  setTimeout(() => node.remove(), 4000);
}

function adminStatusChip(status) {
  const map = {
    success: ['badge-success', 'Identified'],
    uncertain: ['badge-warn', 'Needs review'],
    unsupported: ['badge-info', 'Outside reference set'],
    rejected: ['badge-danger', 'Image unsuitable'],
  };
  const [cls, label] = map[status] || ['badge-muted', 'Not recorded'];
  return `<span class="status-chip ${cls}">${adminEscape(label)}</span>`;
}

function adminPathLabel(name) {
  const map = {
    local_model: 'Reference set',
    ai_assisted: 'Extended reference',
  };
  return map[name] || String(name).replace(/[_-]+/g, ' ');
}

function adminChart(target, rows, labelFn = (name) => name) {
  const max = Math.max(1, ...rows.map((row) => row.value));
  target.innerHTML = rows.length
    ? rows.slice(0, 8).map((row) => {
        const label = adminEscape(labelFn(row.name));
        return `<div class="bar-row"><span class="bar-label" title="${label}">${label}</span><div class="bar-track"><div class="bar-fill" style="width:${(row.value / max) * 100}%"></div></div><span class="bar-value">${row.value}</span></div>`;
      }).join('')
    : '<div class="empty-compact">No records yet.</div>';
}

function adminRecentTable(rows) {
  if (!rows || !rows.length) return '<div class="empty-compact">No records yet.</div>';
  return `<table class="table"><thead><tr><th>Image</th><th>Result</th><th>Time</th></tr></thead><tbody>${rows.map((row) => `<tr>
    <td><img src="${adminEscape(row.image_url)}" alt=""></td>
    <td><strong>${adminEscape(row.disease || row.status)}</strong><br><small class="muted">${adminEscape(row.plant || '')}</small></td>
    <td>${adminEscape(row.created_at)}</td>
  </tr>`).join('')}</tbody></table>`;
}

function adminHistoryTable(rows) {
  if (!rows || !rows.length) return '<div class="empty-compact">No records.</div>';
  return `<table class="table"><thead><tr><th>Image</th><th>Plant / condition</th><th>Status</th><th>Time</th><th></th></tr></thead><tbody>${rows.map((row) => `<tr>
    <td><img src="${adminEscape(row.image_url)}" alt=""></td>
    <td><strong>${adminEscape(row.disease || '—')}</strong><br><small class="muted">${adminEscape(row.plant || '')}</small></td>
    <td>${adminStatusChip(row.status)}</td>
    <td>${adminEscape(row.created_at)}</td>
    <td><button class="link-btn admin-row-delete" data-id="${row.id}">Delete</button></td>
  </tr>`).join('')}</tbody></table>`;
}

function setAdminSection(name) {
  $$admin('.admin-view').forEach((view) => view.classList.toggle('active', view.id === `admin-view-${name}`));
  $$admin('.nav-item[data-admin-section]').forEach((item) => item.classList.toggle('active', item.dataset.adminSection === name));
}

async function loadAdminOverview() {
  try {
    const stats = await adminApi('/api/admin/stats');
    $admin('#admin-total').textContent = stats.total;
    $admin('#admin-healthy').textContent = stats.healthy;
    $admin('#admin-diseased').textContent = stats.diseased;
    $admin('#admin-review').textContent = stats.uncertain + stats.rejected_or_unsupported;
    $admin('#admin-assisted').textContent = stats.ai_assisted || 0;
    adminChart($admin('#admin-source-chart'), stats.by_source || [], adminPathLabel);
    adminChart($admin('#admin-disease-chart'), stats.by_disease);
    adminChart($admin('#admin-plant-chart'), stats.by_plant);
    $admin('#admin-recent').innerHTML = adminRecentTable(stats.recent);
  } catch (error) { adminToast(error.message, 'error'); }
}

function infoList(entries) {
  return `<div class="info-list">${entries.map(([label, value]) => `<div><span>${adminEscape(label)}</span>${adminEscape(value)}</div>`).join('')}</div>`;
}

async function loadAdminSystem() {
  try {
    const data = await adminApi('/api/admin/system');
    const model = data.model || {};
    const plantReference = data.gemini || {};
    const speciesReference = data.plantnet || {};
    const config = data.config || {};
    $admin('#admin-model-info').innerHTML = infoList([
      ['Status', model.loaded ? 'Ready' : 'Unavailable'],
      ['Reference set', model.loaded ? 'Study reference available' : 'Not available'],
      ['Conditions', model.classCount ?? '—'],
    ]);
    $admin('#admin-services-info').innerHTML = infoList([
      ['Plant reference', plantReference.available ? 'Available' : 'Unavailable'],
      ['Species reference', speciesReference.configured ? 'Available' : 'Unavailable'],
      ['Local weather', data.weather && data.weather.enabled ? 'Enabled' : 'Disabled'],
      ['Extended identification', config.aiFallbackEnabled ? 'Enabled' : 'Disabled'],
    ]);
    const app = data.app || {};
    $admin('#admin-app-info').innerHTML = infoList([
      ['Application', `${app.name} v${app.version}`],
      ['Study version', app.version || '—'],
      ['Runtime', app.python || '—'],
      ['Platform', app.platform || '—'],
      ['Records file', app.database || '—'],
      ['Plant reference key', config.geminiKeyConfigured ? 'Configured' : 'Not configured'],
      ['Species reference key', config.plantnetKeyConfigured ? 'Configured' : 'Not configured'],
    ]);
  } catch (error) { adminToast(error.message, 'error'); }
}

async function loadAdminHistory() {
  const query = $admin('#admin-history-search').value.trim();
  try {
    const data = await adminApi(`/api/history?limit=150&query=${encodeURIComponent(query)}`);
    $admin('#admin-history-table').innerHTML = adminHistoryTable(data.items);
    $$admin('.admin-row-delete').forEach((button) => button.addEventListener('click', async () => {
      if (!confirm('Delete this record and its image?')) return;
      try {
        await adminApi(`/api/history/${button.dataset.id}`, { method: 'DELETE' });
        adminToast('Record deleted.', 'success');
        loadAdminHistory(); loadAdminOverview();
      } catch (error) { adminToast(error.message, 'error'); }
    }));
  } catch (error) { adminToast(error.message, 'error'); }
}

async function checkAdminAccess() {
  try {
    const status = await adminApi('/api/admin/status');
    if (status.authenticated) {
      $admin('#admin-gate').hidden = true;
      $admin('#admin-content').hidden = false;
      loadAdminOverview();
    } else {
      $admin('#admin-gate').hidden = false;
      $admin('#admin-content').hidden = true;
    }
  } catch (error) { adminToast(error.message, 'error'); }
}

function initAdmin() {
  $admin('#admin-login-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const password = $admin('#admin-password').value;
    try {
      await adminApi('/api/admin/login', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      });
      $admin('#admin-password').value = '';
      checkAdminAccess();
      adminToast('Access granted.', 'success');
    } catch (error) { adminToast(error.message, 'error'); }
  });

  $admin('#admin-logout').addEventListener('click', async () => {
    try {
      await adminApi('/api/admin/logout', { method: 'POST' });
      checkAdminAccess();
    } catch (error) { adminToast(error.message, 'error'); }
  });

  $$admin('[data-admin-section]').forEach((item) => item.addEventListener('click', (event) => {
    event.preventDefault();
    setAdminSection(item.dataset.adminSection);
    if (item.dataset.adminSection === 'system') loadAdminSystem();
    if (item.dataset.adminSection === 'history') loadAdminHistory();
  }));
  $$admin('[data-admin-goto]').forEach((button) => button.addEventListener('click', () => setAdminSection(button.dataset.adminGoto)));

  $admin('#admin-history-search').addEventListener('input', loadAdminHistory);
  $admin('#admin-history-refresh').addEventListener('click', loadAdminHistory);
  $admin('#admin-clear-history').addEventListener('click', async () => {
    if (!confirm('Delete ALL saved records and uploaded images?')) return;
    try {
      const result = await adminApi('/api/history', { method: 'DELETE' });
      adminToast(result.message || 'Records deleted.', 'success');
      loadAdminHistory(); loadAdminOverview();
    } catch (error) { adminToast(error.message, 'error'); }
  });

  checkAdminAccess();
}

document.addEventListener('DOMContentLoaded', initAdmin);
