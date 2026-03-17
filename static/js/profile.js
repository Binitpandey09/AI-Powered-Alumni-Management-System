/* ============================================================
   AlumniAI — Student Profile Page JS
   Handles: data loading, section rendering, shared modal,
            all CRUD operations for every profile section.
   ============================================================ */

window.studentProfile = {};

// ── Modal ─────────────────────────────────────────────────────────────────────
let _modalOnSave = null;

function openModal(title, bodyHTML, onSave) {
  _modalOnSave = onSave;
  document.getElementById('modal-title').textContent = title;
  document.getElementById('modal-body').innerHTML = bodyHTML;
  document.getElementById('modal-error').textContent = '';
  document.getElementById('modal-overlay').classList.remove('hidden');
  document.getElementById('modal-overlay').classList.add('flex');
  // Focus first input
  setTimeout(() => {
    const first = document.querySelector('#modal-body input, #modal-body textarea, #modal-body select');
    if (first) first.focus();
  }, 50);
}

function closeModal() {
  document.getElementById('modal-overlay').classList.add('hidden');
  document.getElementById('modal-overlay').classList.remove('flex');
  _modalOnSave = null;
}

async function submitModal() {
  if (!_modalOnSave) return;
  const btn = document.getElementById('modal-save-btn');
  const errEl = document.getElementById('modal-error');
  errEl.textContent = '';
  btn.disabled = true;
  btn.innerHTML = '<svg class="w-4 h-4 animate-spin inline mr-1" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z"/></svg>Saving…';
  try {
    await _modalOnSave();
    closeModal();
  } catch (e) {
    errEl.textContent = e.message || 'Save failed. Please try again.';
  } finally {
    btn.disabled = false;
    btn.innerHTML = 'Save';
  }
}

// ── Data Loading ──────────────────────────────────────────────────────────────
async function loadFullProfile() {
  showSkeletons();
  const res = await apiFetch('/api/accounts/profile/student/full/');
  if (!res.ok) { showToast('Failed to load profile', 'error'); return; }
  window.studentProfile = res.data;
  renderAll(res.data);
}

async function refreshSection(sectionKey) {
  // Re-fetch only what changed and re-render that section
  const res = await apiFetch('/api/accounts/profile/student/full/');
  if (!res.ok) return;
  window.studentProfile = res.data;
  switch (sectionKey) {
    case 'header':       renderHeader(res.data); renderCompleteness(res.data.profile_completeness); break;
    case 'preferences':  renderPreferences(res.data.profile); break;
    case 'education':    renderEducation(res.data.educations); break;
    case 'skills':       renderSkills(res.data.profile); break;
    case 'languages':    renderLanguages(res.data.languages); break;
    case 'internships':  renderInternships(res.data.internships); break;
    case 'projects':     renderProjects(res.data.projects); break;
    case 'summary':      renderSummary(res.data.profile); break;
    case 'certifications': renderCertifications(res.data.certifications); break;
    case 'awards':       renderAwards(res.data.awards); break;
    case 'exams':        renderExams(res.data.competitive_exams); break;
    case 'employment':   renderEmployment(res.data.employments); break;
    case 'resume':       renderResume(res.data.profile); break;
    default:             renderAll(res.data);
  }
}

function renderAll(data) {
  renderHeader(data);
  renderCompleteness(data.profile_completeness);
  renderPreferences(data.profile);
  renderEducation(data.educations);
  renderSkills(data.profile);
  renderLanguages(data.languages);
  renderInternships(data.internships);
  renderProjects(data.projects);
  renderSummary(data.profile);
  renderCertifications(data.certifications);
  renderAwards(data.awards);
  renderExams(data.competitive_exams);
  renderEmployment(data.employments);
  renderResume(data.profile);
}

function showSkeletons() {
  document.querySelectorAll('.skeleton-zone').forEach(el => {
    el.innerHTML = '<div class="animate-pulse space-y-2"><div class="h-4 bg-slate-200 rounded w-3/4"></div><div class="h-4 bg-slate-200 rounded w-1/2"></div></div>';
  });
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function pill(text, cls = 'bg-slate-100 text-slate-700') {
  return `<span class="inline-block px-2.5 py-0.5 rounded-full text-xs font-medium ${cls} mr-1 mb-1">${esc(text)}</span>`;
}
function esc(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function editBtn(onclick) {
  return `<button onclick="${onclick}" class="p-1.5 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors" title="Edit">
    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"/></svg>
  </button>`;
}
function deleteBtn(onclick) {
  return `<button onclick="${onclick}" class="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors" title="Delete">
    <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
  </button>`;
}
function addBtn(onclick, label = '+ Add') {
  return `<button onclick="${onclick}" class="text-sm text-blue-600 font-medium hover:underline">${label}</button>`;
}
function emptyState(msg) {
  return `<p class="text-sm text-slate-400 italic">${msg}</p>`;
}
function tagInputHTML(id, placeholder = 'Add…') {
  return `<div id="${id}-container" class="flex flex-wrap gap-1 border border-slate-200 rounded-lg p-2 min-h-[42px] cursor-text" onclick="document.getElementById('${id}-input').focus()"></div>
  <input id="${id}-input" type="text" placeholder="${placeholder}" class="mt-1 w-full px-3 py-1.5 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
  <p class="text-xs text-slate-400 mt-0.5">Press Enter or comma to add</p>`;
}
function initTagInput(id, initial = []) {
  let tags = [...initial];
  const container = document.getElementById(`${id}-container`);
  const input = document.getElementById(`${id}-input`);
  function render() {
    container.innerHTML = tags.map((t, i) =>
      `<span class="inline-flex items-center gap-1 px-2 py-0.5 bg-blue-50 text-blue-700 text-xs rounded-full">
        ${esc(t)}<button type="button" onclick="window._tagRemove('${id}',${i})" class="text-blue-400 hover:text-red-500 leading-none">&times;</button>
      </span>`
    ).join('');
  }
  window._tagRemove = (tid, idx) => {
    if (tid !== id) return;
    tags.splice(idx, 1); render();
  };
  input.onkeydown = (e) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      const v = input.value.trim().replace(/,$/, '');
      if (v && !tags.includes(v)) { tags.push(v); render(); }
      input.value = '';
    } else if (e.key === 'Backspace' && !input.value && tags.length) {
      tags.pop(); render();
    }
  };
  render();
  return { getTags: () => [...tags] };
}
function getTagInputValue(id) {
  // flush any pending input value
  const input = document.getElementById(`${id}-input`);
  if (input && input.value.trim()) {
    input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
  }
  // read from container spans
  const container = document.getElementById(`${id}-container`);
  if (!container) return [];
  return Array.from(container.querySelectorAll('span')).map(s => s.textContent.replace('×','').trim()).filter(Boolean);
}

async function apiCall(method, url, body) {
  const opts = { method };
  if (body) { opts.headers = { 'Content-Type': 'application/json' }; opts.body = JSON.stringify(body); }
  const res = await apiFetch(url, opts);
  if (!res.ok) {
    const msg = res.data ? (Object.values(res.data).flat().join(' ') || 'Request failed') : 'Request failed';
    throw new Error(msg);
  }
  return res.data;
}

// ── Header ────────────────────────────────────────────────────────────────────
function renderHeader(data) {
  const u = data.user || {};
  const p = data.profile || {};
  const edu = (data.educations || []).find(e => e.education_type === 'graduation') || {};
  const pct = (data.profile_completeness || {}).percentage || 0;
  const r = 44; const circ = 2 * Math.PI * r;
  const dash = circ - (pct / 100) * circ;
  const picSrc = u.profile_pic || `https://ui-avatars.com/api/?name=${encodeURIComponent(u.first_name||'?')}&background=2563eb&color=fff&size=100`;

  document.getElementById('profile-header').innerHTML = `
    <div class="flex flex-col sm:flex-row gap-6 items-start">
      <div class="relative flex-shrink-0 cursor-pointer" onclick="document.getElementById('pic-file-input').click()">
        <svg width="108" height="108" class="absolute top-0 left-0" style="transform:rotate(-90deg)">
          <circle cx="54" cy="54" r="${r}" fill="none" stroke="#e2e8f0" stroke-width="5"/>
          <circle cx="54" cy="54" r="${r}" fill="none" stroke="#2563eb" stroke-width="5"
            stroke-dasharray="${circ}" stroke-dashoffset="${dash}" stroke-linecap="round"
            style="transition:stroke-dashoffset 0.6s ease"/>
        </svg>
        <img id="header-pic" src="${picSrc}" alt="Profile"
          class="w-24 h-24 rounded-full object-cover border-2 border-white shadow m-[6px]"
          onerror="this.src='https://ui-avatars.com/api/?name=${encodeURIComponent(u.first_name||'?')}&background=2563eb&color=fff&size=100'" />
        <div class="absolute -bottom-1 left-1/2 -translate-x-1/2 bg-blue-600 text-white text-xs font-bold px-2 py-0.5 rounded-full">${pct}%</div>
        <input id="pic-file-input" type="file" accept="image/jpeg,image/png" class="hidden" onchange="uploadProfilePic(this)" />
      </div>
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2 flex-wrap">
          <h1 class="text-xl font-extrabold text-slate-900">${esc(u.first_name)} ${esc(u.last_name)}</h1>
          ${editBtn('openBasicInfoModal()')}
        </div>
        ${edu.degree ? `<p class="text-sm text-slate-600 mt-0.5">${esc(edu.degree)}${edu.specialization ? ' — ' + esc(edu.specialization) : ''}</p>` : ''}
        ${edu.institute_name ? `<p class="text-sm text-slate-500">${esc(edu.institute_name)}</p>` : ''}
        <div class="flex flex-wrap gap-3 mt-2 text-xs text-slate-500">
          ${p.current_location ? `<span>📍 ${esc(p.current_location)}</span>` : ''}
          ${u.phone ? `<span>📞 ${esc(u.phone)}</span>` : ''}
          ${u.email ? `<span>✉️ ${esc(u.email)}</span>` : ''}
          ${p.date_of_birth ? `<span>🎂 ${esc(p.date_of_birth)}</span>` : ''}
          ${p.gender ? `<span class="capitalize">${esc(p.gender)}</span>` : ''}
        </div>
      </div>
    </div>`;
}

async function uploadProfilePic(input) {
  const file = input.files[0]; if (!file) return;
  const fd = new FormData(); fd.append('profile_pic', file);
  const res = await apiFetch('/api/accounts/profile/picture/', { method: 'POST', body: fd });
  if (res.ok) {
    document.getElementById('header-pic').src = res.data.profile_pic + '?t=' + Date.now();
    showToast('Profile picture updated', 'success');
  } else {
    showToast(Object.values(res.data || {}).flat().join(' ') || 'Upload failed', 'error');
  }
}

function openBasicInfoModal() {
  const p = window.studentProfile.profile || {};
  const u = window.studentProfile.user || {};
  const body = `
    <div class="grid grid-cols-2 gap-3">
      <div><label class="label">First Name</label><input id="bi-first_name" class="inp" value="${esc(u.first_name||'')}"/></div>
      <div><label class="label">Last Name</label><input id="bi-last_name" class="inp" value="${esc(u.last_name||'')}"/></div>
    </div>
    <div class="grid grid-cols-2 gap-3 mt-3">
      <div><label class="label">Phone</label><input id="bi-phone" class="inp" value="${esc(u.phone||'')}"/></div>
      <div><label class="label">Date of Birth</label><input id="bi-dob" type="date" class="inp" value="${esc(p.date_of_birth||'')}"/></div>
    </div>
    <div class="grid grid-cols-2 gap-3 mt-3">
      <div><label class="label">Gender</label>
        <select id="bi-gender" class="inp">
          <option value="">Select</option>
          ${['male','female','other','prefer_not_to_say'].map(g=>`<option value="${g}" ${p.gender===g?'selected':''}>${g.replace(/_/g,' ')}</option>`).join('')}
        </select>
      </div>
      <div><label class="label">Current Location</label><input id="bi-location" class="inp" value="${esc(p.current_location||'')}"/></div>
    </div>`;
  openModal('Edit Basic Info', body, async () => {
    await apiCall('PATCH', '/api/accounts/profile/basic/', {
      first_name: document.getElementById('bi-first_name').value,
      last_name: document.getElementById('bi-last_name').value,
      phone: document.getElementById('bi-phone').value,
    });
    await apiCall('PATCH', '/api/accounts/profile/student/', {
      gender: document.getElementById('bi-gender').value,
      date_of_birth: document.getElementById('bi-dob').value || null,
      current_location: document.getElementById('bi-location').value,
    });
    await refreshSection('header');
    showToast('Basic info updated', 'success');
  });
}

// ── Completeness ──────────────────────────────────────────────────────────────
function renderCompleteness(data) {
  if (!data) return;
  const pct = data.percentage || 0;
  const sections = data.sections || {};
  const missing = Object.entries(sections).filter(([,v]) => !v.complete);
  const el = document.getElementById('completeness-card');
  if (!el) return;
  const color = pct >= 80 ? 'text-emerald-600' : pct >= 50 ? 'text-amber-500' : 'text-red-500';
  const barColor = pct >= 80 ? 'bg-emerald-500' : pct >= 50 ? 'bg-amber-400' : 'bg-red-400';
  el.innerHTML = `
    <div class="flex items-center justify-between mb-2">
      <span class="text-sm font-semibold text-slate-700">Profile Strength</span>
      <span class="text-sm font-bold ${color}">${pct}%</span>
    </div>
    <div class="w-full bg-slate-100 rounded-full h-2 mb-3">
      <div class="${barColor} h-2 rounded-full transition-all duration-500" style="width:${pct}%"></div>
    </div>
    ${missing.length ? `
      <p class="text-xs text-slate-500 mb-2 font-medium">Complete these to boost your profile:</p>
      <ul class="space-y-1">
        ${missing.slice(0,5).map(([k,v]) => `
          <li class="flex items-center gap-2 text-xs text-slate-600">
            <span class="w-2 h-2 rounded-full bg-amber-400 flex-shrink-0"></span>
            <span class="capitalize">${k.replace(/_/g,' ')}</span>
            <span class="ml-auto text-blue-600 font-medium">+${v.weight}%</span>
          </li>`).join('')}
      </ul>` : `<p class="text-xs text-emerald-600 font-medium">🎉 Profile complete!</p>`}`;
}

// ── Career Preferences ────────────────────────────────────────────────────────
function renderPreferences(p) {
  if (!p) return;
  const el = document.getElementById('section-preferences');
  if (!el) return;
  const locs = (p.preferred_locations || []).join(', ');
  el.innerHTML = `
    <div class="flex items-start justify-between">
      <div class="space-y-1 text-sm text-slate-600">
        ${p.looking_for ? `<p><span class="font-medium text-slate-700">Job type:</span> <span class="capitalize">${esc(p.looking_for)}</span></p>` : ''}
        ${p.availability ? `<p><span class="font-medium text-slate-700">Availability:</span> ${esc(p.availability)}</p>` : ''}
        ${locs ? `<p><span class="font-medium text-slate-700">Preferred locations:</span> ${esc(locs)}</p>` : ''}
        ${!p.looking_for && !p.availability && !locs ? `<p class="text-slate-400 italic">No preferences set yet.</p>` : ''}
      </div>
      ${editBtn('openPreferencesModal()')}
    </div>`;
}

function openPreferencesModal() {
  const p = window.studentProfile.profile || {};
  let locTags;
  const body = `
    <div class="space-y-3">
      <div><label class="label">Looking for</label>
        <select id="pref-looking" class="inp">
          <option value="">Select</option>
          ${['internship','full-time','part-time','freelance'].map(v=>`<option value="${v}" ${p.looking_for===v?'selected':''}>${v}</option>`).join('')}
        </select>
      </div>
      <div><label class="label">Availability</label>
        <input id="pref-avail" class="inp" placeholder="e.g. Immediate, 15 Days or less" value="${esc(p.availability||'')}"/>
      </div>
      <div><label class="label">Preferred Locations</label>
        ${tagInputHTML('pref-locs', 'Add city…')}
      </div>
    </div>`;
  openModal('Career Preferences', body, async () => {
    locTags = getTagInputValue('pref-locs');
    await apiCall('PATCH', '/api/accounts/profile/student/', {
      looking_for: document.getElementById('pref-looking').value,
      availability: document.getElementById('pref-avail').value,
      preferred_locations: locTags,
    });
    await refreshSection('preferences');
    showToast('Preferences saved', 'success');
  });
  setTimeout(() => initTagInput('pref-locs', p.preferred_locations || []), 50);
}

// ── Education ─────────────────────────────────────────────────────────────────
function renderEducation(list) {
  const el = document.getElementById('section-education');
  if (!el) return;
  if (!list || !list.length) { el.innerHTML = emptyState('No education added yet.'); return; }
  el.innerHTML = list.map(e => `
    <div class="py-3 border-b border-slate-100 last:border-0">
      <div class="flex items-start justify-between gap-2">
        <div>
          <p class="font-semibold text-slate-800 text-sm">${esc(e.degree)}${e.specialization ? ' — ' + esc(e.specialization) : ''}</p>
          <p class="text-sm text-slate-600">${esc(e.institute_name)}${e.board_or_university ? ' · ' + esc(e.board_or_university) : ''}</p>
          <p class="text-xs text-slate-400 mt-0.5">
            ${e.start_year && e.end_year ? `${e.start_year} – ${e.is_pursuing ? 'Pursuing' : e.end_year}` : e.end_year || ''}
            ${e.study_mode ? ' · ' + e.study_mode.replace('_',' ') : ''}
            ${e.grade_value ? ' · ' + (e.grade_type === 'cgpa' ? 'CGPA: ' : '') + esc(e.grade_value) : ''}
          </p>
        </div>
        <div class="flex gap-1 flex-shrink-0">
          ${editBtn(`openEducationModal(${e.id})`)}
          ${deleteBtn(`deleteItem('education',${e.id},'education')`)}
        </div>
      </div>
    </div>`).join('');
}

function openEducationModal(id) {
  const existing = id ? (window.studentProfile.educations || []).find(e => e.id === id) : null;
  const v = existing || {};
  const body = `
    <div class="space-y-3">
      <div><label class="label">Education Type</label>
        <select id="edu-type" class="inp">
          ${[['graduation','Graduation / Post Graduation'],['class_12','Class XII'],['class_10','Class X']].map(([val,lbl])=>`<option value="${val}" ${v.education_type===val?'selected':''}>${lbl}</option>`).join('')}
        </select>
      </div>
      <div class="grid grid-cols-2 gap-3">
        <div><label class="label">Degree</label><input id="edu-degree" class="inp" value="${esc(v.degree||'')}" placeholder="B.Tech, MCA…"/></div>
        <div><label class="label">Specialization</label><input id="edu-spec" class="inp" value="${esc(v.specialization||'')}" placeholder="Computer Science"/></div>
      </div>
      <div><label class="label">Institute Name *</label><input id="edu-inst" class="inp" value="${esc(v.institute_name||'')}" required/></div>
      <div><label class="label">Board / University</label><input id="edu-board" class="inp" value="${esc(v.board_or_university||'')}"/></div>
      <div class="grid grid-cols-2 gap-3">
        <div><label class="label">Start Year</label><input id="edu-start" type="number" class="inp" value="${v.start_year||''}" min="1990" max="2035"/></div>
        <div><label class="label">End Year</label><input id="edu-end" type="number" class="inp" value="${v.end_year||''}" min="1990" max="2035"/></div>
      </div>
      <div class="flex items-center gap-2">
        <input id="edu-pursuing" type="checkbox" ${v.is_pursuing?'checked':''} class="w-4 h-4 accent-blue-600"/>
        <label for="edu-pursuing" class="text-sm text-slate-600">Currently pursuing</label>
      </div>
      <div class="grid grid-cols-2 gap-3">
        <div><label class="label">Grade Type</label>
          <select id="edu-gtype" class="inp">
            <option value="">Select</option>
            <option value="percentage" ${v.grade_type==='percentage'?'selected':''}>Percentage</option>
            <option value="cgpa" ${v.grade_type==='cgpa'?'selected':''}>CGPA</option>
          </select>
        </div>
        <div><label class="label">Grade Value</label><input id="edu-gval" class="inp" value="${esc(v.grade_value||'')}" placeholder="8.5 or 92%"/></div>
      </div>
      <div><label class="label">Study Mode</label>
        <select id="edu-mode" class="inp">
          <option value="">Select</option>
          ${[['full_time','Full Time'],['part_time','Part Time'],['distance','Distance']].map(([val,lbl])=>`<option value="${val}" ${v.study_mode===val?'selected':''}>${lbl}</option>`).join('')}
        </select>
      </div>
    </div>`;
  openModal(id ? 'Edit Education' : 'Add Education', body, async () => {
    const payload = {
      education_type: document.getElementById('edu-type').value,
      degree: document.getElementById('edu-degree').value,
      specialization: document.getElementById('edu-spec').value,
      institute_name: document.getElementById('edu-inst').value,
      board_or_university: document.getElementById('edu-board').value,
      start_year: document.getElementById('edu-start').value || null,
      end_year: document.getElementById('edu-end').value || null,
      is_pursuing: document.getElementById('edu-pursuing').checked,
      grade_type: document.getElementById('edu-gtype').value,
      grade_value: document.getElementById('edu-gval').value,
      study_mode: document.getElementById('edu-mode').value,
    };
    if (id) await apiCall('PATCH', `/api/accounts/profile/education/${id}/`, payload);
    else await apiCall('POST', '/api/accounts/profile/education/', payload);
    await refreshSection('education');
    showToast('Education saved', 'success');
  });
}

// ── Skills ────────────────────────────────────────────────────────────────────
function renderSkills(p) {
  const el = document.getElementById('section-skills');
  if (!el) return;
  const skills = (p && p.skills) || [];
  el.innerHTML = `
    <div class="flex items-start justify-between">
      <div class="flex flex-wrap gap-1">${skills.length ? skills.map(s => pill(s)).join('') : emptyState('No skills added yet.')}</div>
      ${editBtn('openSkillsModal()')}
    </div>`;
}

function openSkillsModal() {
  const skills = (window.studentProfile.profile || {}).skills || [];
  const body = `<div><label class="label">Skills</label>${tagInputHTML('sk', 'Add skill…')}</div>`;
  openModal('Edit Key Skills', body, async () => {
    const tags = getTagInputValue('sk');
    await apiCall('PATCH', '/api/accounts/profile/student/', { skills: tags });
    await refreshSection('skills');
    showToast('Skills updated', 'success');
  });
  setTimeout(() => initTagInput('sk', skills), 50);
}

// ── Languages ─────────────────────────────────────────────────────────────────
function renderLanguages(list) {
  const el = document.getElementById('section-languages');
  if (!el) return;
  if (!list || !list.length) { el.innerHTML = emptyState('No languages added yet.'); return; }
  el.innerHTML = list.map(l => `
    <div class="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">
      <div>
        <p class="text-sm font-semibold text-slate-800">${esc(l.language)} <span class="text-xs text-slate-400 font-normal capitalize">(${esc(l.proficiency)})</span></p>
        <p class="text-xs text-slate-400">${[l.can_speak&&'Speak',l.can_read&&'Read',l.can_write&&'Write'].filter(Boolean).join(', ')}</p>
      </div>
      <div class="flex gap-1">
        ${editBtn(`openLanguageModal(${l.id})`)}
        ${deleteBtn(`deleteItem('languages',${l.id},'languages')`)}
      </div>
    </div>`).join('');
}

function openLanguageModal(id) {
  const v = id ? (window.studentProfile.languages || []).find(l => l.id === id) || {} : {};
  const body = `
    <div class="space-y-3">
      <div><label class="label">Language *</label><input id="lang-name" class="inp" value="${esc(v.language||'')}" placeholder="Hindi, English…"/></div>
      <div><label class="label">Proficiency</label>
        <select id="lang-prof" class="inp">
          ${[['beginner','Beginner'],['proficient','Proficient'],['expert','Expert / Native']].map(([val,lbl])=>`<option value="${val}" ${v.proficiency===val?'selected':''}>${lbl}</option>`).join('')}
        </select>
      </div>
      <div class="flex gap-4">
        <label class="flex items-center gap-2 text-sm"><input type="checkbox" id="lang-speak" ${v.can_speak!==false?'checked':''} class="accent-blue-600"/> Speak</label>
        <label class="flex items-center gap-2 text-sm"><input type="checkbox" id="lang-read" ${v.can_read!==false?'checked':''} class="accent-blue-600"/> Read</label>
        <label class="flex items-center gap-2 text-sm"><input type="checkbox" id="lang-write" ${v.can_write!==false?'checked':''} class="accent-blue-600"/> Write</label>
      </div>
    </div>`;
  openModal(id ? 'Edit Language' : 'Add Language', body, async () => {
    const payload = {
      language: document.getElementById('lang-name').value,
      proficiency: document.getElementById('lang-prof').value,
      can_speak: document.getElementById('lang-speak').checked,
      can_read: document.getElementById('lang-read').checked,
      can_write: document.getElementById('lang-write').checked,
    };
    if (id) await apiCall('PATCH', `/api/accounts/profile/languages/${id}/`, payload);
    else await apiCall('POST', '/api/accounts/profile/languages/', payload);
    await refreshSection('languages');
    showToast('Language saved', 'success');
  });
}

// ── Internships ───────────────────────────────────────────────────────────────
function renderInternships(list) {
  const el = document.getElementById('section-internships');
  if (!el) return;
  if (!list || !list.length) { el.innerHTML = emptyState('Talk about the company you interned at, what projects you undertook and what special skills you learned.'); return; }
  el.innerHTML = list.map(i => `
    <div class="py-3 border-b border-slate-100 last:border-0">
      <div class="flex items-start justify-between gap-2">
        <div class="flex-1">
          <p class="font-semibold text-slate-800 text-sm">${esc(i.role)} <span class="text-slate-500 font-normal">@ ${esc(i.company_name)}</span></p>
          <p class="text-xs text-slate-400 mt-0.5">${[i.start_month,i.is_ongoing?'Present':i.end_month].filter(Boolean).join(' – ')}${i.location?' · '+esc(i.location):''}${i.stipend?' · '+esc(i.stipend):''}</p>
          ${i.description ? `<p class="text-sm text-slate-600 mt-1">${esc(i.description)}</p>` : ''}
          ${(i.skills_used||[]).length ? `<div class="mt-1">${i.skills_used.map(s=>pill(s)).join('')}</div>` : ''}
        </div>
        <div class="flex gap-1 flex-shrink-0">
          ${editBtn(`openInternshipModal(${i.id})`)}
          ${deleteBtn(`deleteItem('internships',${i.id},'internships')`)}
        </div>
      </div>
    </div>`).join('');
}

function openInternshipModal(id) {
  const v = id ? (window.studentProfile.internships || []).find(x => x.id === id) || {} : {};
  const body = `
    <div class="space-y-3">
      <div class="grid grid-cols-2 gap-3">
        <div><label class="label">Company *</label><input id="int-company" class="inp" value="${esc(v.company_name||'')}"/></div>
        <div><label class="label">Role *</label><input id="int-role" class="inp" value="${esc(v.role||'')}"/></div>
      </div>
      <div class="grid grid-cols-2 gap-3">
        <div><label class="label">Start Month</label><input id="int-start" class="inp" value="${esc(v.start_month||'')}" placeholder="Jun'24"/></div>
        <div><label class="label">End Month</label><input id="int-end" class="inp" value="${esc(v.end_month||'')}" placeholder="Aug'24"/></div>
      </div>
      <div class="flex items-center gap-2"><input id="int-ongoing" type="checkbox" ${v.is_ongoing?'checked':''} class="accent-blue-600"/><label for="int-ongoing" class="text-sm">Currently ongoing</label></div>
      <div class="grid grid-cols-2 gap-3">
        <div><label class="label">Location</label><input id="int-loc" class="inp" value="${esc(v.location||'')}"/></div>
        <div><label class="label">Stipend</label><input id="int-stipend" class="inp" value="${esc(v.stipend||'')}" placeholder="₹15,000/month"/></div>
      </div>
      <div><label class="label">Description</label><textarea id="int-desc" class="inp" rows="3">${esc(v.description||'')}</textarea></div>
      <div><label class="label">Skills Used</label>${tagInputHTML('int-skills','Add skill…')}</div>
    </div>`;
  openModal(id ? 'Edit Internship' : 'Add Internship', body, async () => {
    const payload = {
      company_name: document.getElementById('int-company').value,
      role: document.getElementById('int-role').value,
      start_month: document.getElementById('int-start').value,
      end_month: document.getElementById('int-end').value,
      is_ongoing: document.getElementById('int-ongoing').checked,
      location: document.getElementById('int-loc').value,
      stipend: document.getElementById('int-stipend').value,
      description: document.getElementById('int-desc').value,
      skills_used: getTagInputValue('int-skills'),
    };
    if (id) await apiCall('PATCH', `/api/accounts/profile/internships/${id}/`, payload);
    else await apiCall('POST', '/api/accounts/profile/internships/', payload);
    await refreshSection('internships');
    showToast('Internship saved', 'success');
  });
  setTimeout(() => initTagInput('int-skills', v.skills_used || []), 50);
}

// ── Projects ──────────────────────────────────────────────────────────────────
function renderProjects(list) {
  const el = document.getElementById('section-projects');
  if (!el) return;
  if (!list || !list.length) { el.innerHTML = emptyState('No projects added yet.'); return; }
  el.innerHTML = list.map(p => `
    <div class="py-3 border-b border-slate-100 last:border-0">
      <div class="flex items-start justify-between gap-2">
        <div class="flex-1">
          <p class="font-semibold text-slate-800 text-sm">${esc(p.title)}</p>
          <p class="text-xs text-slate-400 mt-0.5">${[p.start_month,p.is_ongoing?'Present':p.end_month].filter(Boolean).join(' – ')}</p>
          ${p.description ? `<p class="text-sm text-slate-600 mt-1">${esc(p.description)}</p>` : ''}
          ${(p.tech_stack||[]).length ? `<div class="mt-1">${p.tech_stack.map(s=>pill(s,'bg-blue-50 text-blue-700')).join('')}</div>` : ''}
          ${p.github_url ? `<a href="${esc(p.github_url)}" target="_blank" class="text-xs text-blue-600 hover:underline mt-1 inline-block">GitHub ↗</a>` : ''}
          ${p.project_url ? `<a href="${esc(p.project_url)}" target="_blank" class="text-xs text-blue-600 hover:underline mt-1 ml-2 inline-block">Live ↗</a>` : ''}
        </div>
        <div class="flex gap-1 flex-shrink-0">
          ${editBtn(`openProjectModal(${p.id})`)}
          ${deleteBtn(`deleteItem('projects',${p.id},'projects')`)}
        </div>
      </div>
    </div>`).join('');
}

function openProjectModal(id) {
  const v = id ? (window.studentProfile.projects || []).find(x => x.id === id) || {} : {};
  const body = `
    <div class="space-y-3">
      <div><label class="label">Project Title *</label><input id="proj-title" class="inp" value="${esc(v.title||'')}"/></div>
      <div class="grid grid-cols-2 gap-3">
        <div><label class="label">Start Month</label><input id="proj-start" class="inp" value="${esc(v.start_month||'')}" placeholder="Sep'25"/></div>
        <div><label class="label">End Month</label><input id="proj-end" class="inp" value="${esc(v.end_month||'')}" placeholder="Nov'25"/></div>
      </div>
      <div class="flex items-center gap-2"><input id="proj-ongoing" type="checkbox" ${v.is_ongoing?'checked':''} class="accent-blue-600"/><label for="proj-ongoing" class="text-sm">Ongoing</label></div>
      <div><label class="label">Description</label><textarea id="proj-desc" class="inp" rows="3">${esc(v.description||'')}</textarea></div>
      <div><label class="label">Tech Stack</label>${tagInputHTML('proj-tech','Add technology…')}</div>
      <div class="grid grid-cols-2 gap-3">
        <div><label class="label">GitHub URL</label><input id="proj-gh" type="url" class="inp" value="${esc(v.github_url||'')}"/></div>
        <div><label class="label">Project URL</label><input id="proj-url" type="url" class="inp" value="${esc(v.project_url||'')}"/></div>
      </div>
    </div>`;
  openModal(id ? 'Edit Project' : 'Add Project', body, async () => {
    const payload = {
      title: document.getElementById('proj-title').value,
      start_month: document.getElementById('proj-start').value,
      end_month: document.getElementById('proj-end').value,
      is_ongoing: document.getElementById('proj-ongoing').checked,
      description: document.getElementById('proj-desc').value,
      tech_stack: getTagInputValue('proj-tech'),
      github_url: document.getElementById('proj-gh').value,
      project_url: document.getElementById('proj-url').value,
    };
    if (id) await apiCall('PATCH', `/api/accounts/profile/projects/${id}/`, payload);
    else await apiCall('POST', '/api/accounts/profile/projects/', payload);
    await refreshSection('projects');
    showToast('Project saved', 'success');
  });
  setTimeout(() => initTagInput('proj-tech', v.tech_stack || []), 50);
}

// ── Profile Summary ───────────────────────────────────────────────────────────
function renderSummary(p) {
  const el = document.getElementById('section-summary');
  if (!el) return;
  const text = p && p.profile_summary;
  el.innerHTML = `
    <div class="flex items-start justify-between gap-2">
      <p class="text-sm text-slate-600 flex-1">${text ? esc(text) : '<span class="text-slate-400 italic">No summary added yet. A good summary helps recruiters find you.</span>'}</p>
      ${editBtn('openSummaryModal()')}
    </div>`;
}

function openSummaryModal() {
  const p = window.studentProfile.profile || {};
  const body = `
    <div>
      <label class="label">Profile Summary</label>
      <textarea id="sum-text" class="inp" rows="6" maxlength="2000" placeholder="Write a compelling 3-4 sentence summary…">${esc(p.profile_summary||'')}</textarea>
      <div class="flex items-center justify-between mt-1">
        <span id="sum-count" class="text-xs text-slate-400">0 / 2000</span>
        <button type="button" onclick="generateAISummary()" class="text-xs text-blue-600 font-medium hover:underline flex items-center gap-1">
          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
          Generate with AI
        </button>
      </div>
      <div id="ai-gen-status" class="text-xs text-slate-400 mt-1 hidden">Generating…</div>
    </div>`;
  openModal('Profile Summary', body, async () => {
    await apiCall('PATCH', '/api/accounts/profile/student/', {
      profile_summary: document.getElementById('sum-text').value,
    });
    await refreshSection('summary');
    showToast('Summary saved', 'success');
  });
  setTimeout(() => {
    const ta = document.getElementById('sum-text');
    const counter = document.getElementById('sum-count');
    if (ta && counter) {
      counter.textContent = `${ta.value.length} / 2000`;
      ta.oninput = () => { counter.textContent = `${ta.value.length} / 2000`; };
    }
  }, 50);
}

async function generateAISummary() {
  const statusEl = document.getElementById('ai-gen-status');
  const ta = document.getElementById('sum-text');
  if (!statusEl || !ta) return;
  statusEl.textContent = 'Generating with AI…';
  statusEl.classList.remove('hidden');
  const res = await apiFetch('/api/ai/generate-summary/', { method: 'POST' });
  if (res.ok && res.data.summary) {
    ta.value = res.data.summary;
    ta.dispatchEvent(new Event('input'));
    statusEl.textContent = 'Generated! Review and edit before saving.';
    statusEl.className = 'text-xs text-emerald-600 mt-1';
  } else {
    statusEl.textContent = res.data.error || 'Generation failed. Try again.';
    statusEl.className = 'text-xs text-red-500 mt-1';
  }
}

// ── Certifications ────────────────────────────────────────────────────────────
function renderCertifications(list) {
  const el = document.getElementById('section-certifications');
  if (!el) return;
  if (!list || !list.length) { el.innerHTML = emptyState('No certifications added yet.'); return; }
  el.innerHTML = list.map(c => `
    <div class="flex items-start justify-between py-2 border-b border-slate-100 last:border-0 gap-2">
      <div>
        <p class="text-sm font-semibold text-slate-800">${esc(c.title)}</p>
        <p class="text-xs text-slate-500">${esc(c.issuing_organization)}${c.issue_date?' · '+esc(c.issue_date):''}</p>
        ${c.credential_url ? `<a href="${esc(c.credential_url)}" target="_blank" class="text-xs text-blue-600 hover:underline">View credential ↗</a>` : ''}
      </div>
      <div class="flex gap-1 flex-shrink-0">
        ${editBtn(`openCertModal(${c.id})`)}
        ${deleteBtn(`deleteItem('certifications',${c.id},'certifications')`)}
      </div>
    </div>`).join('');
}

function openCertModal(id) {
  const v = id ? (window.studentProfile.certifications || []).find(x => x.id === id) || {} : {};
  const body = `
    <div class="space-y-3">
      <div><label class="label">Certificate Title *</label><input id="cert-title" class="inp" value="${esc(v.title||'')}"/></div>
      <div><label class="label">Issuing Organization *</label><input id="cert-org" class="inp" value="${esc(v.issuing_organization||'')}"/></div>
      <div class="grid grid-cols-2 gap-3">
        <div><label class="label">Issue Date</label><input id="cert-issue" type="date" class="inp" value="${esc(v.issue_date||'')}"/></div>
        <div><label class="label">Expiry Date</label><input id="cert-expiry" type="date" class="inp" value="${esc(v.expiry_date||'')}"/></div>
      </div>
      <div class="flex items-center gap-2"><input id="cert-noexp" type="checkbox" ${v.does_not_expire?'checked':''} class="accent-blue-600"/><label for="cert-noexp" class="text-sm">Does not expire</label></div>
      <div class="grid grid-cols-2 gap-3">
        <div><label class="label">Credential ID</label><input id="cert-cid" class="inp" value="${esc(v.credential_id||'')}"/></div>
        <div><label class="label">Credential URL</label><input id="cert-curl" type="url" class="inp" value="${esc(v.credential_url||'')}"/></div>
      </div>
    </div>`;
  openModal(id ? 'Edit Certification' : 'Add Certification', body, async () => {
    const payload = {
      title: document.getElementById('cert-title').value,
      issuing_organization: document.getElementById('cert-org').value,
      issue_date: document.getElementById('cert-issue').value || null,
      expiry_date: document.getElementById('cert-noexp').checked ? null : (document.getElementById('cert-expiry').value || null),
      does_not_expire: document.getElementById('cert-noexp').checked,
      credential_id: document.getElementById('cert-cid').value,
      credential_url: document.getElementById('cert-curl').value,
    };
    if (id) await apiCall('PATCH', `/api/accounts/profile/certifications/${id}/`, payload);
    else await apiCall('POST', '/api/accounts/profile/certifications/', payload);
    await refreshSection('certifications');
    showToast('Certification saved', 'success');
  });
}

// ── Awards ────────────────────────────────────────────────────────────────────
function renderAwards(list) {
  const el = document.getElementById('section-awards');
  if (!el) return;
  if (!list || !list.length) { el.innerHTML = emptyState('No awards added yet.'); return; }
  el.innerHTML = list.map(a => `
    <div class="flex items-start justify-between py-2 border-b border-slate-100 last:border-0 gap-2">
      <div>
        <p class="text-sm font-semibold text-slate-800">${esc(a.title)}</p>
        <p class="text-xs text-slate-500">${a.issuer?esc(a.issuer):''}${a.date_received?' · '+esc(a.date_received):''}</p>
        ${a.description ? `<p class="text-xs text-slate-500 mt-0.5">${esc(a.description)}</p>` : ''}
      </div>
      <div class="flex gap-1 flex-shrink-0">
        ${editBtn(`openAwardModal(${a.id})`)}
        ${deleteBtn(`deleteItem('awards',${a.id},'awards')`)}
      </div>
    </div>`).join('');
}

function openAwardModal(id) {
  const v = id ? (window.studentProfile.awards || []).find(x => x.id === id) || {} : {};
  const body = `
    <div class="space-y-3">
      <div><label class="label">Award Title *</label><input id="aw-title" class="inp" value="${esc(v.title||'')}"/></div>
      <div class="grid grid-cols-2 gap-3">
        <div><label class="label">Issuer</label><input id="aw-issuer" class="inp" value="${esc(v.issuer||'')}"/></div>
        <div><label class="label">Date Received</label><input id="aw-date" type="date" class="inp" value="${esc(v.date_received||'')}"/></div>
      </div>
      <div><label class="label">Description</label><textarea id="aw-desc" class="inp" rows="3">${esc(v.description||'')}</textarea></div>
    </div>`;
  openModal(id ? 'Edit Award' : 'Add Award / Achievement', body, async () => {
    const payload = {
      title: document.getElementById('aw-title').value,
      issuer: document.getElementById('aw-issuer').value,
      date_received: document.getElementById('aw-date').value || null,
      description: document.getElementById('aw-desc').value,
    };
    if (id) await apiCall('PATCH', `/api/accounts/profile/awards/${id}/`, payload);
    else await apiCall('POST', '/api/accounts/profile/awards/', payload);
    await refreshSection('awards');
    showToast('Award saved', 'success');
  });
}

// ── Competitive Exams ─────────────────────────────────────────────────────────
function renderExams(list) {
  const el = document.getElementById('section-exams');
  if (!el) return;
  if (!list || !list.length) { el.innerHTML = emptyState('No competitive exams added yet.'); return; }
  el.innerHTML = list.map(e => `
    <div class="flex items-start justify-between py-2 border-b border-slate-100 last:border-0 gap-2">
      <div>
        <p class="text-sm font-semibold text-slate-800">${esc(e.exam_name)} ${e.year?`<span class="text-slate-400 font-normal">(${e.year})</span>`:''}
        </p>
        ${e.score_or_rank ? `<p class="text-xs text-slate-500">Got ${esc(e.score_or_rank)}</p>` : ''}
        ${e.description ? `<p class="text-xs text-slate-400">${esc(e.description)}</p>` : ''}
      </div>
      <div class="flex gap-1 flex-shrink-0">
        ${editBtn(`openExamModal(${e.id})`)}
        ${deleteBtn(`deleteItem('exams',${e.id},'exams')`)}
      </div>
    </div>`).join('');
}

function openExamModal(id) {
  const v = id ? (window.studentProfile.competitive_exams || []).find(x => x.id === id) || {} : {};
  const body = `
    <div class="space-y-3">
      <div><label class="label">Exam Name *</label><input id="ex-name" class="inp" value="${esc(v.exam_name||'')}" placeholder="JEE Mains, GATE, CAT…"/></div>
      <div class="grid grid-cols-2 gap-3">
        <div><label class="label">Year</label><input id="ex-year" type="number" class="inp" value="${v.year||''}" min="2000" max="2035"/></div>
        <div><label class="label">Score / Rank</label><input id="ex-score" class="inp" value="${esc(v.score_or_rank||'')}" placeholder="95 percentile, 78582 Rank"/></div>
      </div>
      <div><label class="label">Description</label><input id="ex-desc" class="inp" value="${esc(v.description||'')}"/></div>
    </div>`;
  openModal(id ? 'Edit Exam' : 'Add Competitive Exam', body, async () => {
    const payload = {
      exam_name: document.getElementById('ex-name').value,
      year: document.getElementById('ex-year').value || null,
      score_or_rank: document.getElementById('ex-score').value,
      description: document.getElementById('ex-desc').value,
    };
    if (id) await apiCall('PATCH', `/api/accounts/profile/exams/${id}/`, payload);
    else await apiCall('POST', '/api/accounts/profile/exams/', payload);
    await refreshSection('exams');
    showToast('Exam saved', 'success');
  });
}

// ── Employment ────────────────────────────────────────────────────────────────
function renderEmployment(list) {
  const el = document.getElementById('section-employment');
  if (!el) return;
  if (!list || !list.length) { el.innerHTML = emptyState('Talk about the company you worked at, your designation and describe what you did there.'); return; }
  el.innerHTML = list.map(e => `
    <div class="py-3 border-b border-slate-100 last:border-0">
      <div class="flex items-start justify-between gap-2">
        <div class="flex-1">
          <p class="font-semibold text-slate-800 text-sm">${esc(e.job_title)} <span class="text-slate-500 font-normal">@ ${esc(e.company_name)}</span></p>
          <p class="text-xs text-slate-400 mt-0.5">${[e.start_month,e.is_current?'Present':e.end_month].filter(Boolean).join(' – ')}${e.location?' · '+esc(e.location):''}</p>
          ${e.description ? `<p class="text-sm text-slate-600 mt-1">${esc(e.description)}</p>` : ''}
          ${(e.skills_used||[]).length ? `<div class="mt-1">${e.skills_used.map(s=>pill(s)).join('')}</div>` : ''}
        </div>
        <div class="flex gap-1 flex-shrink-0">
          ${editBtn(`openEmploymentModal(${e.id})`)}
          ${deleteBtn(`deleteItem('employment',${e.id},'employment')`)}
        </div>
      </div>
    </div>`).join('');
}

function openEmploymentModal(id) {
  const v = id ? (window.studentProfile.employments || []).find(x => x.id === id) || {} : {};
  const body = `
    <div class="space-y-3">
      <div class="grid grid-cols-2 gap-3">
        <div><label class="label">Company *</label><input id="emp-company" class="inp" value="${esc(v.company_name||'')}"/></div>
        <div><label class="label">Job Title *</label><input id="emp-title" class="inp" value="${esc(v.job_title||'')}"/></div>
      </div>
      <div class="grid grid-cols-2 gap-3">
        <div><label class="label">Start Month</label><input id="emp-start" class="inp" value="${esc(v.start_month||'')}" placeholder="Jan'23"/></div>
        <div><label class="label">End Month</label><input id="emp-end" class="inp" value="${esc(v.end_month||'')}" placeholder="Dec'23"/></div>
      </div>
      <div class="flex items-center gap-2"><input id="emp-current" type="checkbox" ${v.is_current?'checked':''} class="accent-blue-600"/><label for="emp-current" class="text-sm">Currently working here</label></div>
      <div><label class="label">Location</label><input id="emp-loc" class="inp" value="${esc(v.location||'')}"/></div>
      <div><label class="label">Description</label><textarea id="emp-desc" class="inp" rows="3">${esc(v.description||'')}</textarea></div>
      <div><label class="label">Skills Used</label>${tagInputHTML('emp-skills','Add skill…')}</div>
    </div>`;
  openModal(id ? 'Edit Employment' : 'Add Employment', body, async () => {
    const payload = {
      company_name: document.getElementById('emp-company').value,
      job_title: document.getElementById('emp-title').value,
      start_month: document.getElementById('emp-start').value,
      end_month: document.getElementById('emp-end').value,
      is_current: document.getElementById('emp-current').checked,
      location: document.getElementById('emp-loc').value,
      description: document.getElementById('emp-desc').value,
      skills_used: getTagInputValue('emp-skills'),
    };
    if (id) await apiCall('PATCH', `/api/accounts/profile/employment/${id}/`, payload);
    else await apiCall('POST', '/api/accounts/profile/employment/', payload);
    await refreshSection('employment');
    showToast('Employment saved', 'success');
  });
  setTimeout(() => initTagInput('emp-skills', v.skills_used || []), 50);
}

// ── Resume ────────────────────────────────────────────────────────────────────
function renderResume(p) {
  const el = document.getElementById('section-resume');
  if (!el) return;
  const hasFile = p && p.resume_file;
  el.innerHTML = `
    ${hasFile ? `
      <div class="flex items-center justify-between p-3 bg-slate-50 rounded-lg border border-slate-200 mb-3">
        <div class="flex items-center gap-3">
          <svg class="w-8 h-8 text-red-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
          <div>
            <p class="text-sm font-medium text-slate-700">${esc(p.resume_file.split('/').pop())}</p>
            <p class="text-xs text-slate-400">Current resume</p>
          </div>
        </div>
        <a href="${esc(p.resume_file)}" download class="p-1.5 text-slate-400 hover:text-blue-600 rounded-lg" title="Download">
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/></svg>
        </a>
      </div>` : ''}
    <label class="block border-2 border-dashed border-slate-200 rounded-lg p-6 text-center hover:border-blue-400 transition-colors cursor-pointer">
      <svg class="w-8 h-8 text-slate-300 mx-auto mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>
      <p class="text-sm text-slate-500">${hasFile ? 'Update resume' : 'Upload resume'}</p>
      <p class="text-xs text-slate-400 mt-1">Supported: PDF, DOC, DOCX — max 5MB</p>
      <input type="file" accept=".pdf,.doc,.docx" class="hidden" onchange="uploadResume(this)"/>
    </label>
    <div id="resume-status" class="mt-2 text-sm"></div>`;
}

async function uploadResume(input) {
  const file = input.files[0]; if (!file) return;
  const statusEl = document.getElementById('resume-status');
  statusEl.innerHTML = '<span class="text-slate-400">Uploading and parsing CV with AI…</span>';
  const fd = new FormData(); fd.append('cv_file', file);
  const res = await apiFetch('/api/accounts/profile/cv-upload/', { method: 'POST', body: fd });
  if (res.ok) {
    const applied = res.data.applied_fields || [];
    statusEl.innerHTML = `<span class="text-emerald-600">CV parsed. Updated: ${applied.join(', ') || 'no new fields'}</span>`;
    showToast('CV imported — profile updated', 'success');
    await loadFullProfile();
  } else {
    statusEl.innerHTML = `<span class="text-red-500">${(res.data && res.data.message) || 'Upload failed'}</span>`;
  }
}

// ── Delete helper ─────────────────────────────────────────────────────────────
async function deleteItem(endpoint, id, sectionKey) {
  if (!confirm('Delete this entry?')) return;
  const res = await apiFetch(`/api/accounts/profile/${endpoint}/${id}/`, { method: 'DELETE' });
  if (res.ok || res.status === 204) {
    await refreshSection(sectionKey);
    showToast('Deleted', 'success');
  } else {
    showToast('Delete failed', 'error');
  }
}

// ── Init ──────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Close modal on overlay click
  document.getElementById('modal-overlay').addEventListener('click', (e) => {
    if (e.target === document.getElementById('modal-overlay')) closeModal();
  });
  // Close on Escape
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeModal(); });
  // Sidebar scroll
  document.querySelectorAll('[data-scroll-to]').forEach(link => {
    link.addEventListener('click', (e) => {
      e.preventDefault();
      const target = document.getElementById(link.dataset.scrollTo);
      if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });
  loadFullProfile();
});
