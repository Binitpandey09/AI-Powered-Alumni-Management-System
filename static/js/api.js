/* ============================================================
   AlumniAI — Global JS Utilities
   Loaded on every page via base.html
   ============================================================ */

// ── CSRF ──────────────────────────────────────────────────────
function getCSRFToken() {
  const name = 'csrftoken';
  const cookies = document.cookie.split(';');
  for (let c of cookies) {
    c = c.trim();
    if (c.startsWith(name + '=')) {
      return decodeURIComponent(c.slice(name.length + 1));
    }
  }
  return '';
}

// ── Token storage ─────────────────────────────────────────────
function saveTokens(access, refresh) {
  localStorage.setItem('access_token', access);
  localStorage.setItem('refresh_token', refresh);
}

function getAccessToken() {
  return localStorage.getItem('access_token') || '';
}

function clearTokens() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
}

// ── Fetch helpers ─────────────────────────────────────────────
async function apiPost(url, data) {
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken(),
      },
      body: JSON.stringify(data),
    });
    const json = await res.json().catch(() => ({}));
    return { ok: res.ok, status: res.status, data: json, error: res.ok ? null : json };
  } catch (err) {
    return { ok: false, status: 0, data: null, error: { detail: 'Network error. Please try again.' } };
  }
}

async function apiGet(url) {
  try {
    const res = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${getAccessToken()}`,
      },
      credentials: 'include',
    });
    const json = await res.json().catch(() => ({}));
    return { ok: res.ok, status: res.status, data: json, error: res.ok ? null : json };
  } catch (err) {
    return { ok: false, status: 0, data: null, error: { detail: 'Network error. Please try again.' } };
  }
}

/**
 * General-purpose authenticated fetch.
 * For file uploads pass FormData as body (no Content-Type header — browser sets multipart).
 * For JSON pass an object and set headers: {'Content-Type':'application/json'}.
 */
async function apiFetch(url, options = {}) {
  const headers = {
    'Authorization': `Bearer ${getAccessToken()}`,
    'X-CSRFToken': getCSRFToken(),
    ...(options.headers || {}),
  };
  // Don't set Content-Type for FormData — let browser handle multipart boundary
  if (options.body instanceof FormData) {
    delete headers['Content-Type'];
  }
  try {
    const res = await fetch(url, { credentials: 'include', ...options, headers });
    const json = await res.json().catch(() => ({}));
    return { ok: res.ok, status: res.status, data: json, error: res.ok ? null : json };
  } catch (err) {
    return { ok: false, status: 0, data: null, error: { detail: 'Network error. Please try again.' } };
  }
}

/**
 * Upload a file via multipart POST. Returns {ok, data, error}.
 */
async function uploadFile(url, formData) {
  return apiFetch(url, { method: 'POST', body: formData });
}

// ── Toast notifications ───────────────────────────────────────
function showToast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const colors = {
    success: 'bg-emerald-500',
    error:   'bg-red-500',
    info:    'bg-blue-600',
    warning: 'bg-amber-500',
  };

  const toast = document.createElement('div');
  toast.className = [
    'pointer-events-auto px-5 py-3 rounded-lg text-white text-sm font-medium shadow-lg',
    'fade-in-up max-w-xs',
    colors[type] || colors.info,
  ].join(' ');
  toast.textContent = message;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity 0.3s';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// ── Error display helpers ─────────────────────────────────────
function extractErrorMessage(errorObj) {
  if (!errorObj) return 'Something went wrong.';
  if (typeof errorObj === 'string') return errorObj;
  if (errorObj.detail) return errorObj.detail;
  if (errorObj.non_field_errors) return errorObj.non_field_errors.join(' ');
  const firstKey = Object.keys(errorObj)[0];
  if (firstKey) {
    const val = errorObj[firstKey];
    return `${firstKey}: ${Array.isArray(val) ? val.join(' ') : val}`;
  }
  return 'Something went wrong.';
}

function showFieldErrors(errorObj, prefix = 'err-') {
  document.querySelectorAll('[id^="' + prefix + '"]').forEach(el => {
    el.textContent = '';
    el.classList.add('hidden');
  });
  if (!errorObj || typeof errorObj !== 'object') return;
  for (const [field, messages] of Object.entries(errorObj)) {
    const el = document.getElementById(prefix + field);
    if (el) {
      el.textContent = Array.isArray(messages) ? messages.join(' ') : messages;
      el.classList.remove('hidden');
    }
  }
}

// ── URL helpers ───────────────────────────────────────────────
function getQueryParam(name) {
  return new URLSearchParams(window.location.search).get(name) || '';
}

// ── Debounce ──────────────────────────────────────────────────
/**
 * Returns a debounced version of fn that fires after `delay` ms of inactivity.
 */
function debounce(fn, delay) {
  let timer;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), delay);
  };
}

// ── Poll until ────────────────────────────────────────────────
/**
 * Polls checkFn every intervalMs. Resolves true when checkFn returns true.
 * Rejects after maxAttempts.
 */
function pollUntil(checkFn, intervalMs = 2000, maxAttempts = 10) {
  return new Promise((resolve, reject) => {
    let attempts = 0;
    const id = setInterval(async () => {
      attempts++;
      try {
        const done = await checkFn();
        if (done) { clearInterval(id); resolve(true); }
        else if (attempts >= maxAttempts) { clearInterval(id); reject(new Error('Poll timeout')); }
      } catch (e) { clearInterval(id); reject(e); }
    }, intervalMs);
  });
}

// ── Skill tag input ───────────────────────────────────────────
/**
 * Renders skill pills inside containerEl.
 * If editable=true, appends an input that adds tags on Enter/comma and removes on click-x.
 * Returns { getTags } — call getTags() to get current array.
 */
function renderSkillTags(containerEl, skills = [], editable = false) {
  let tags = [...skills];

  function render() {
    containerEl.innerHTML = '';
    tags.forEach((skill, i) => {
      const pill = document.createElement('span');
      pill.className = 'inline-flex items-center gap-1 px-2.5 py-1 bg-slate-100 text-slate-700 text-xs font-medium rounded-full';
      pill.textContent = skill;
      if (editable) {
        const x = document.createElement('button');
        x.type = 'button';
        x.className = 'ml-0.5 text-slate-400 hover:text-red-500 leading-none';
        x.innerHTML = '&times;';
        x.onclick = () => { tags.splice(i, 1); render(); };
        pill.appendChild(x);
      }
      containerEl.appendChild(pill);
    });

    if (editable) {
      const input = document.createElement('input');
      input.type = 'text';
      input.placeholder = 'Add skill…';
      input.className = 'outline-none text-xs px-1 py-1 min-w-[80px] bg-transparent text-slate-700';
      input.onkeydown = (e) => {
        if (e.key === 'Enter' || e.key === ',') {
          e.preventDefault();
          const val = input.value.trim().replace(/,$/, '');
          if (val && !tags.includes(val)) { tags.push(val); render(); }
          else input.value = '';
        } else if (e.key === 'Backspace' && input.value === '' && tags.length) {
          tags.pop(); render();
        }
      };
      containerEl.appendChild(input);
      // Focus input when clicking the container
      containerEl.onclick = (e) => { if (e.target === containerEl) input.focus(); };
    }
  }

  render();
  return { getTags: () => [...tags], setTags: (t) => { tags = [...t]; render(); } };
}

// ── Initials avatar fallback ──────────────────────────────────
function getInitials(name) {
  return (name || '?').split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();
}
