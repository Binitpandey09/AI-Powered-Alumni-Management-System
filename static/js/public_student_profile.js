/* ============================================================
   AlumniAI — Public Student Profile Page JS
   ============================================================ */

document.addEventListener('DOMContentLoaded', () => {
  loadPublicStudentProfile();
  if (VIEWER_ROLE === 'faculty') {
    loadReferralsForModal();
  }
});

async function loadPublicStudentProfile() {
  const result = await apiGet(`/api/accounts/profile/student/full/${STUDENT_ID}/`);
  document.getElementById('profile-skeleton')?.remove();

  if (!result.ok) {
    document.getElementById('profile-error')?.classList.remove('hidden');
    return;
  }

  renderPublicProfile(result.data);
  document.getElementById('profile-content')?.classList.remove('hidden');
}

function renderPublicProfile(data) {
  const user = data.user || {};
  const profile = data.profile || {};

  // Avatar
  const avatarEl = document.getElementById('pub-avatar');
  if (avatarEl) {
    if (user.profile_pic) {
      avatarEl.innerHTML = `<img src="${user.profile_pic}" class="w-20 h-20 object-cover" alt=""/>`;
    } else {
      const initials = getInitials(`${user.first_name || ''} ${user.last_name || ''}`);
      avatarEl.textContent = initials;
    }
  }

  setText('pub-name', `${user.first_name || ''} ${user.last_name || ''}`.trim());

  const degree = profile.degree || '';
  const branch = profile.branch || '';
  setText('pub-degree', [degree, branch].filter(Boolean).join(' · '));
  setText('pub-college', user.college || '');

  if (profile.current_location) {
    setText('pub-location-text', profile.current_location);
    document.getElementById('pub-location')?.classList.remove('hidden');
  }
  if (profile.graduation_year) {
    setText('pub-grad-year-text', `Class of ${profile.graduation_year}`);
    document.getElementById('pub-grad-year')?.classList.remove('hidden');
  }

  // Skills
  const skillsEl = document.getElementById('pub-skills');
  const skills = profile.skills || [];
  if (skillsEl) {
    if (skills.length) {
      skillsEl.innerHTML = '';
      skills.forEach(s => {
        const tag = document.createElement('span');
        tag.className = 'px-2.5 py-1 bg-slate-100 text-slate-700 text-xs font-medium rounded-full';
        tag.textContent = s;
        skillsEl.appendChild(tag);
      });
    } else {
      document.getElementById('pub-skills-empty')?.classList.remove('hidden');
    }
  }

  // Education
  const eduEl = document.getElementById('pub-education');
  const educations = data.educations || [];
  if (eduEl) {
    if (educations.length) {
      educations.forEach(edu => {
        const item = document.createElement('div');
        item.className = 'flex items-start gap-3';
        item.innerHTML = `
          <div class="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center flex-shrink-0 mt-0.5">
            <svg class="w-4 h-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 14l9-5-9-5-9 5 9 5z"/>
            </svg>
          </div>
          <div>
            <p class="text-sm font-semibold text-slate-800">${escHtml(edu.institution || '')}</p>
            <p class="text-xs text-slate-500">${escHtml(edu.degree || '')} ${edu.field_of_study ? `· ${edu.field_of_study}` : ''}</p>
            <p class="text-xs text-slate-400">${edu.start_year || ''} – ${edu.end_year || 'Present'}</p>
          </div>
        `;
        eduEl.appendChild(item);
      });
    } else {
      document.getElementById('pub-education-empty')?.classList.remove('hidden');
    }
  }

  // Projects
  const projects = data.projects || [];
  if (projects.length) {
    document.getElementById('pub-projects-card')?.classList.remove('hidden');
    const projEl = document.getElementById('pub-projects');
    if (projEl) {
      projects.forEach(p => {
        const item = document.createElement('div');
        item.className = 'border-l-2 border-blue-200 pl-3';
        item.innerHTML = `
          <p class="text-sm font-semibold text-slate-800">${escHtml(p.title || '')}</p>
          <p class="text-xs text-slate-500 mt-0.5 leading-relaxed">${escHtml(p.description || '')}</p>
          ${p.tech_stack?.length ? `<div class="flex flex-wrap gap-1 mt-1">${p.tech_stack.map(t => `<span class="px-1.5 py-0.5 bg-slate-100 text-slate-600 text-xs rounded">${escHtml(t)}</span>`).join('')}</div>` : ''}
        `;
        projEl.appendChild(item);
      });
    }
  }

  // Internships
  const internships = data.internships || [];
  if (internships.length) {
    document.getElementById('pub-internships-card')?.classList.remove('hidden');
    const intEl = document.getElementById('pub-internships');
    if (intEl) {
      internships.forEach(i => {
        const item = document.createElement('div');
        item.className = 'flex items-start gap-3';
        item.innerHTML = `
          <div class="flex-1">
            <p class="text-sm font-semibold text-slate-800">${escHtml(i.role || '')}</p>
            <p class="text-xs text-slate-500">${escHtml(i.company || '')} · ${escHtml(i.location || '')}</p>
            <p class="text-xs text-slate-400">${i.start_date || ''} – ${i.end_date || 'Present'}</p>
          </div>
        `;
        intEl.appendChild(item);
      });
    }
  }
}

  // Avatar
  const avatarEl = document.getElementById('pub-avatar');
  if (avatarEl) {
    if (user.profile_pic) {
      avatarEl.innerHTML = `<img src="${user.profile_pic}" class="w-20 h-20 object-cover" alt=""/>`;
    } else {
      const initials = getInitials(`${user.first_name || ''} ${user.last_name || ''}`);
      avatarEl.textContent = initials;
    }
  }

  setText('pub-name', `${user.first_name || ''} ${user.last_name || ''}`.trim());

  const degree = profile.degree || '';
  const branch = profile.branch || '';
  setText('pub-degree', [degree, branch].filter(Boolean).join(' · '));
  setText('pub-college', user.college || '');

  if (profile.current_location) {
    setText('pub-location-text', profile.current_location);
    document.getElementById('pub-location')?.classList.remove('hidden');
  }
  if (profile.graduation_year) {
    setText('pub-grad-year-text', `Class of ${profile.graduation_year}`);
    document.getElementById('pub-grad-year')?.classList.remove('hidden');
  }

  // Skills
  const skillsEl = document.getElementById('pub-skills');
  const skills = profile.skills || [];
  if (skillsEl) {
    if (skills.length) {
      skillsEl.innerHTML = '';
      skills.forEach(s => {
        const tag = document.createElement('span');
        tag.className = 'px-2.5 py-1 bg-slate-100 text-slate-700 text-xs font-medium rounded-full';
        tag.textContent = s;
        skillsEl.appendChild(tag);
      });
    } else {
      document.getElementById('pub-skills-empty')?.classList.remove('hidden');
    }
  }

  // Education
  const eduEl = document.getElementById('pub-education');
  const educations = data.educations || [];
  if (eduEl) {
    if (educations.length) {
      educations.forEach(edu => {
        const item = document.createElement('div');
        item.className = 'flex items-start gap-3';
        item.innerHTML = `
          <div class="w-8 h-8 rounded-lg bg-blue-50 flex items-center justify-center flex-shrink-0 mt-0.5">
            <svg class="w-4 h-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 14l9-5-9-5-9 5 9 5z"/>
            </svg>
          </div>
          <div>
            <p class="text-sm font-semibold text-slate-800">${escHtml(edu.institution || '')}</p>
            <p class="text-xs text-slate-500">${escHtml(edu.degree || '')} ${edu.field_of_study ? `· ${edu.field_of_study}` : ''}</p>
            <p class="text-xs text-slate-400">${edu.start_year || ''} – ${edu.end_year || 'Present'}</p>
          </div>
        `;
        eduEl.appendChild(item);
      });
    } else {
      document.getElementById('pub-education-empty')?.classList.remove('hidden');
    }
  }

  // Projects
  const projects = data.projects || [];
  if (projects.length) {
    document.getElementById('pub-projects-card')?.classList.remove('hidden');
    const projEl = document.getElementById('pub-projects');
    if (projEl) {
      projects.forEach(p => {
        const item = document.createElement('div');
        item.className = 'border-l-2 border-blue-200 pl-3';
        item.innerHTML = `
          <p class="text-sm font-semibold text-slate-800">${escHtml(p.title || '')}</p>
          <p class="text-xs text-slate-500 mt-0.5 leading-relaxed">${escHtml(p.description || '')}</p>
          ${p.tech_stack?.length ? `<div class="flex flex-wrap gap-1 mt-1">${p.tech_stack.map(t => `<span class="px-1.5 py-0.5 bg-slate-100 text-slate-600 text-xs rounded">${escHtml(t)}</span>`).join('')}</div>` : ''}
        `;
        projEl.appendChild(item);
      });
    }
  }

  // Internships
  const internships = data.internships || [];
  if (internships.length) {
    document.getElementById('pub-internships-card')?.classList.remove('hidden');
    const intEl = document.getElementById('pub-internships');
    if (intEl) {
      internships.forEach(i => {
        const item = document.createElement('div');
        item.className = 'flex items-start gap-3';
        item.innerHTML = `
          <div class="flex-1">
            <p class="text-sm font-semibold text-slate-800">${escHtml(i.role || '')}</p>
            <p class="text-xs text-slate-500">${escHtml(i.company || '')} · ${escHtml(i.location || '')}</p>
            <p class="text-xs text-slate-400">${i.start_date || ''} – ${i.end_date || 'Present'}</p>
          </div>
        `;
        intEl.appendChild(item);
      });
    }
  }
}

// ── Faculty recommend modal ───────────────────────────────────
async function loadReferralsForModal() {
  const result = await apiGet('/api/referrals/?page_size=50');
  const select = document.getElementById('modal-referral-select');
  if (!select) return;

  select.innerHTML = '<option value="">Select a referral…</option>';
  const referrals = result.ok ? (result.data.results || []) : [];
  referrals.filter(r => r.status === 'active').forEach(r => {
    const opt = document.createElement('option');
    opt.value = r.id;
    opt.textContent = `${r.job_title} @ ${r.company_name}`;
    select.appendChild(opt);
  });
  if (!referrals.length) {
    select.innerHTML = '<option value="">No active referrals available</option>';
  }
}

function openRecommendModal() {
  document.getElementById('recommend-modal')?.classList.remove('hidden');
  document.getElementById('modal-rec-note').value = '';
  document.getElementById('modal-rec-error')?.classList.add('hidden');
}

function closeRecommendModal() {
  document.getElementById('recommend-modal')?.classList.add('hidden');
}

async function submitModalRecommendation() {
  const referralId = document.getElementById('modal-referral-select')?.value;
  const note = document.getElementById('modal-rec-note')?.value.trim() || '';
  const btn = document.getElementById('modal-rec-submit-btn');
  const errEl = document.getElementById('modal-rec-error');

  if (!referralId) {
    errEl.textContent = 'Please select a referral.';
    errEl.classList.remove('hidden');
    return;
  }

  btn.disabled = true;
  btn.textContent = 'Recommending…';
  errEl.classList.add('hidden');

  const result = await apiPost(`/api/referrals/${referralId}/recommend/`, {
    student_id: STUDENT_ID,
    note,
  });

  btn.disabled = false;
  btn.textContent = 'Recommend';

  if (result.ok) {
    closeRecommendModal();
    showToast('Recommendation sent! The alumni has been notified.', 'success');
  } else {
    errEl.textContent = extractErrorMessage(result.error);
    errEl.classList.remove('hidden');
  }
}

// ── Utilities ─────────────────────────────────────────────────
function escHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text ?? '';
}
