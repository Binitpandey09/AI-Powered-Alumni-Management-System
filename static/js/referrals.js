/* ============================================================
   AlumniAI — Referrals JS
   Handles: referral_board, referral_detail, my_applications,
            manage_applications, success_stories
   ============================================================ */

// ── State ─────────────────────────────────────────────────────
let currentPage = 1;
let totalPages = 1;
let currentFilters = {};
let activeApplyReferralId = null;
let activeUpdateApplicationId = null;
let allApplications = [];  // for client-side status filter
let requiredSkillsCtrl = null;
let preferredSkillsCtrl = null;

// ── Work type / experience display maps ───────────────────────
const WORK_TYPE_LABELS = {
  full_time: 'Full Time', internship: 'Internship',
  part_time: 'Part Time', contract: 'Contract', remote: 'Remote',
};
const EXP_LABELS = {
  fresher: 'Fresher', junior: 'Junior', mid: 'Mid Level', senior: 'Senior',
};
const STATUS_COLORS = {
  applied:              'bg-blue-100 text-blue-700',
  under_review:         'bg-amber-100 text-amber-700',
  shortlisted:          'bg-violet-100 text-violet-700',
  interview_scheduled:  'bg-teal-100 text-teal-700',
  rejected:             'bg-red-100 text-red-700',
  hired:                'bg-emerald-100 text-emerald-700',
  withdrawn:            'bg-slate-100 text-slate-500',
};
const STATUS_LABELS = {
  applied: 'Applied', under_review: 'Under Review', shortlisted: 'Shortlisted',
  interview_scheduled: 'Interview Scheduled', rejected: 'Rejected',
  hired: '🎉 Hired', withdrawn: 'Withdrawn',
};

// ── Router: init based on page ────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const page = typeof PAGE !== 'undefined' ? PAGE : null;
  if (page === 'my_applications') {
    initMyApplications();
  } else if (page === 'manage_applications') {
    initManageApplications();
  } else if (page === 'success_stories') {
    initSuccessStories();
  } else if (typeof REFERRAL_ID !== 'undefined') {
    initDetailPage();
  } else {
    initBoard();
  }
});

// ══════════════════════════════════════════════════════════════
// REFERRAL BOARD
// ══════════════════════════════════════════════════════════════
function initBoard() {
  loadReferrals();
  setupBoardFilters();
  if (CAN_POST) initCreateModal();
}

function setupBoardFilters() {
  const searchInput = document.getElementById('search-input');
  const workType    = document.getElementById('filter-work-type');
  const experience  = document.getElementById('filter-experience');
  const smartMatch  = document.getElementById('smart-match-toggle');
  const remoteOnly  = document.getElementById('remote-toggle');

  const reload = debounce(() => { currentPage = 1; loadReferrals(); }, 400);

  if (searchInput) searchInput.addEventListener('input', reload);
  if (workType)    workType.addEventListener('change', reload);
  if (experience)  experience.addEventListener('change', reload);
  if (smartMatch)  smartMatch.addEventListener('change', reload);
  if (remoteOnly)  remoteOnly.addEventListener('change', reload);
}

async function loadReferrals() {
  const params = new URLSearchParams({ page: currentPage });

  const search     = document.getElementById('search-input')?.value.trim();
  const workType   = document.getElementById('filter-work-type')?.value;
  const experience = document.getElementById('filter-experience')?.value;
  const smartMatch = document.getElementById('smart-match-toggle')?.checked;
  const remoteOnly = document.getElementById('remote-toggle')?.checked;

  if (search)     params.set('search', search);
  if (workType)   params.set('work_type', workType);
  if (experience) params.set('experience', experience);
  if (smartMatch) params.set('smart_match', 'true');
  if (remoteOnly) params.set('remote', 'true');

  const result = await apiGet(`/api/referrals/?${params}`);
  hideSkeletons('.referral-skeleton');

  if (!result.ok) {
    showBoardError();
    return;
  }

  const data = result.data;
  const referrals = data.results || [];
  totalPages = Math.ceil((data.count || 0) / 10);

  updateStats(referrals, data.count || 0);
  renderReferralGrid(referrals);
  updatePagination(data.count || 0);
}

function updateStats(referrals, total) {
  const el = (id) => document.getElementById(id);
  if (el('stat-total'))    el('stat-total').textContent    = total;
  if (el('stat-fulltime')) el('stat-fulltime').textContent = referrals.filter(r => r.work_type === 'full_time').length;
  if (el('stat-intern'))   el('stat-intern').textContent   = referrals.filter(r => r.work_type === 'internship').length;
  if (el('stat-remote'))   el('stat-remote').textContent   = referrals.filter(r => r.is_remote).length;
}

function renderReferralGrid(referrals) {
  const grid = document.getElementById('referrals-grid');
  const empty = document.getElementById('empty-state');
  if (!grid) return;

  grid.innerHTML = '';
  if (!referrals.length) {
    if (empty) empty.classList.remove('hidden');
    return;
  }
  if (empty) empty.classList.add('hidden');
  referrals.forEach(r => grid.appendChild(renderReferralCard(r)));
}

// ── Render referral card (returns DOM element) ────────────────
function renderReferralCard(r) {
  const gradients = {
    full_time:   'from-blue-500 to-blue-700',
    internship:  'from-violet-500 to-violet-700',
    part_time:   'from-amber-500 to-amber-600',
    contract:    'from-slate-500 to-slate-700',
    remote:      'from-teal-500 to-teal-700',
  };
  const grad = gradients[r.work_type] || gradients.full_time;

  const card = document.createElement('div');
  card.className = 'session-card bg-white rounded-xl border border-slate-200 overflow-hidden hover:shadow-md transition-shadow cursor-pointer';
  card.onclick = () => window.location.href = `/referrals/${r.id}/`;

  // Header strip
  const header = document.createElement('div');
  header.className = `bg-gradient-to-r ${grad} p-4`;

  const headerTop = document.createElement('div');
  headerTop.className = 'flex items-start justify-between';

  // Logo / initials
  const logoWrap = document.createElement('div');
  logoWrap.className = 'w-10 h-10 rounded-lg bg-white/20 flex items-center justify-center text-white font-bold text-sm flex-shrink-0';
  if (r.company_logo_url) {
    const img = document.createElement('img');
    img.src = r.company_logo_url;
    img.alt = r.company_name;
    img.className = 'w-10 h-10 rounded-lg object-cover';
    logoWrap.appendChild(img);
  } else {
    logoWrap.textContent = (r.company_name || '?')[0].toUpperCase();
  }

  const badges = document.createElement('div');
  badges.className = 'flex flex-col items-end gap-1';
  if (r.is_urgent) {
    const urg = document.createElement('span');
    urg.className = 'px-2 py-0.5 bg-red-500 text-white text-xs font-semibold rounded-full';
    urg.textContent = '🔥 Urgent';
    badges.appendChild(urg);
  }
  if (r.is_boosted) {
    const boost = document.createElement('span');
    boost.className = 'px-2 py-0.5 bg-amber-400 text-white text-xs font-semibold rounded-full';
    boost.textContent = '⚡ Featured';
    badges.appendChild(boost);
  }

  headerTop.appendChild(logoWrap);
  headerTop.appendChild(badges);

  const titleEl = document.createElement('div');
  titleEl.className = 'mt-2';
  titleEl.innerHTML = `
    <p class="text-white font-bold text-base leading-tight">${escHtml(r.job_title)}</p>
    <p class="text-white/80 text-xs mt-0.5">${escHtml(r.company_name)}</p>
  `;

  header.appendChild(headerTop);
  header.appendChild(titleEl);

  // Body
  const body = document.createElement('div');
  body.className = 'p-4';

  // Meta row
  const meta = document.createElement('div');
  meta.className = 'flex flex-wrap gap-1.5 mb-3';
  [
    { text: WORK_TYPE_LABELS[r.work_type] || r.work_type, cls: 'bg-blue-50 text-blue-700' },
    { text: EXP_LABELS[r.experience_level] || r.experience_level, cls: 'bg-slate-100 text-slate-600' },
    r.is_remote ? { text: '🌐 Remote', cls: 'bg-teal-50 text-teal-700' } : null,
    r.location && !r.is_remote ? { text: `📍 ${r.location}`, cls: 'bg-slate-100 text-slate-600' } : null,
  ].filter(Boolean).forEach(({ text, cls }) => {
    const span = document.createElement('span');
    span.className = `px-2 py-0.5 text-xs font-medium rounded-full ${cls}`;
    span.textContent = text;
    meta.appendChild(span);
  });
  body.appendChild(meta);

  // Skills (first 3)
  if (r.required_skills?.length) {
    const skillsRow = document.createElement('div');
    skillsRow.className = 'flex flex-wrap gap-1 mb-3';
    r.required_skills.slice(0, 3).forEach(s => {
      const tag = document.createElement('span');
      tag.className = 'px-2 py-0.5 bg-slate-100 text-slate-600 text-xs rounded-full';
      tag.textContent = s;
      skillsRow.appendChild(tag);
    });
    if (r.required_skills.length > 3) {
      const more = document.createElement('span');
      more.className = 'px-2 py-0.5 bg-slate-100 text-slate-400 text-xs rounded-full';
      more.textContent = `+${r.required_skills.length - 3}`;
      skillsRow.appendChild(more);
    }
    body.appendChild(skillsRow);
  }

  // Slots progress bar
  const slotsWrap = document.createElement('div');
  slotsWrap.className = 'mb-3';
  const pct = r.max_applicants > 0 ? Math.min(100, (r.total_applications / r.max_applicants) * 100) : 0;
  const barColor = pct >= 100 ? 'bg-red-400' : pct >= 60 ? 'bg-amber-400' : 'bg-blue-500';
  slotsWrap.innerHTML = `
    <div class="flex justify-between text-xs text-slate-400 mb-1">
      <span>${r.total_applications}/${r.max_applicants} applied</span>
      <span>${r.slots_remaining} slot${r.slots_remaining !== 1 ? 's' : ''} left</span>
    </div>
    <div class="w-full bg-slate-100 rounded-full h-1.5">
      <div class="${barColor} h-1.5 rounded-full" style="width:${pct}%"></div>
    </div>
  `;
  body.appendChild(slotsWrap);

  // Footer row: time + match score + apply btn
  const footer = document.createElement('div');
  footer.className = 'flex items-center justify-between pt-2 border-t border-slate-100';

  const timeEl = document.createElement('span');
  timeEl.className = 'text-xs text-slate-400';
  timeEl.textContent = r.time_remaining || '';
  footer.appendChild(timeEl);

  const rightGroup = document.createElement('div');
  rightGroup.className = 'flex items-center gap-2';

  // Match score circle (students only)
  if (typeof IS_STUDENT !== 'undefined' && IS_STUDENT && r.match_score !== null && r.match_score !== undefined) {
    const scoreEl = renderMatchScoreMini(r.match_score);
    rightGroup.appendChild(scoreEl);
  }

  // Apply / Applied badge (students)
  if (typeof IS_STUDENT !== 'undefined' && IS_STUDENT) {
    if (r.has_applied) {
      const applied = document.createElement('span');
      applied.className = 'px-2.5 py-1 bg-emerald-100 text-emerald-700 text-xs font-semibold rounded-full';
      applied.textContent = '✓ Applied';
      rightGroup.appendChild(applied);
    } else if (r.is_accepting_applications) {
      const applyBtn = document.createElement('button');
      applyBtn.className = 'px-3 py-1.5 bg-blue-600 text-white text-xs font-medium rounded-lg hover:bg-blue-700 transition-colors';
      applyBtn.textContent = 'Apply';
      applyBtn.onclick = (e) => { e.stopPropagation(); openApplyModal(r.id, r.match_score); };
      rightGroup.appendChild(applyBtn);
    } else {
      const closed = document.createElement('span');
      closed.className = 'px-2.5 py-1 bg-slate-100 text-slate-400 text-xs font-medium rounded-full';
      closed.textContent = r.is_expired ? 'Expired' : 'Full';
      rightGroup.appendChild(closed);
    }
  }

  // Applicants link (alumni / faculty)
  if (typeof CAN_POST !== 'undefined' && CAN_POST) {
    const manageLink = document.createElement('a');
    manageLink.href = `/referrals/${r.id}/manage/`;
    manageLink.onclick = (e) => e.stopPropagation();
    if (r.total_applications > 0) {
      manageLink.className = 'px-3 py-1.5 bg-blue-50 text-blue-600 text-xs font-semibold rounded-lg hover:bg-blue-100 transition-colors';
      manageLink.textContent = `${r.total_applications} Applicant${r.total_applications !== 1 ? 's' : ''} →`;
    } else {
      manageLink.className = 'px-3 py-1.5 bg-slate-50 text-slate-400 text-xs font-medium rounded-lg hover:bg-slate-100 transition-colors';
      manageLink.textContent = 'Manage →';
    }
    rightGroup.appendChild(manageLink);
  }

  footer.appendChild(rightGroup);
  body.appendChild(footer);

  card.appendChild(header);
  card.appendChild(body);
  return card;
}

// ── Mini match score circle (SVG) ─────────────────────────────
function renderMatchScoreMini(score) {
  const r = 10, circ = 2 * Math.PI * r;
  const offset = circ - (score / 100) * circ;
  const color = score >= 80 ? '#10b981' : score >= 60 ? '#f59e0b' : score >= 40 ? '#3b82f6' : '#ef4444';

  const wrap = document.createElement('div');
  wrap.className = 'flex items-center gap-1';
  wrap.innerHTML = `
    <svg width="28" height="28" viewBox="0 0 28 28">
      <circle cx="14" cy="14" r="${r}" fill="none" stroke="#e2e8f0" stroke-width="3"/>
      <circle cx="14" cy="14" r="${r}" fill="none" stroke="${color}" stroke-width="3"
        stroke-linecap="round"
        stroke-dasharray="${circ.toFixed(2)}"
        stroke-dashoffset="${offset.toFixed(2)}"
        transform="rotate(-90 14 14)"/>
      <text x="14" y="14" text-anchor="middle" dominant-baseline="central"
        font-size="7" font-weight="700" fill="${color}">${score}%</text>
    </svg>
  `;
  return wrap;
}

// ── Pagination ────────────────────────────────────────────────
function updatePagination(total) {
  const pag = document.getElementById('pagination');
  const info = document.getElementById('page-info');
  const prev = document.getElementById('prev-btn');
  const next = document.getElementById('next-btn');
  if (!pag) return;

  totalPages = Math.ceil(total / 10);
  if (totalPages <= 1) { pag.classList.add('hidden'); return; }
  pag.classList.remove('hidden');
  if (info) info.textContent = `Page ${currentPage} of ${totalPages}`;
  if (prev) prev.disabled = currentPage <= 1;
  if (next) next.disabled = currentPage >= totalPages;
}

function changePage(delta) {
  const next = currentPage + delta;
  if (next < 1 || next > totalPages) return;
  currentPage = next;
  loadReferrals();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ── Board error state ─────────────────────────────────────────
function showBoardError() {
  const grid = document.getElementById('referrals-grid');
  if (!grid) return;
  grid.innerHTML = `
    <div class="col-span-3 text-center py-16">
      <p class="text-slate-500">Failed to load referrals.</p>
      <button onclick="loadReferrals()" class="mt-3 text-sm text-blue-600 hover:underline">Retry</button>
    </div>
  `;
}

// ── Create modal ──────────────────────────────────────────────
function initCreateModal() {
  const reqContainer  = document.getElementById('required-skills-container');
  const prefContainer = document.getElementById('preferred-skills-container');
  if (reqContainer)  requiredSkillsCtrl  = renderSkillTags(reqContainer,  [], true);
  if (prefContainer) preferredSkillsCtrl = renderSkillTags(prefContainer, [], true);
}

function openCreateModal() {
  document.getElementById('create-modal')?.classList.remove('hidden');
  document.getElementById('create-form')?.reset();
  if (requiredSkillsCtrl)  requiredSkillsCtrl.setTags([]);
  if (preferredSkillsCtrl) preferredSkillsCtrl.setTags([]);
  hideEl('create-error');
}

function closeCreateModal() {
  document.getElementById('create-modal')?.classList.add('hidden');
}

async function submitCreateReferral(e) {
  e.preventDefault();
  const form = e.target;
  const btn  = document.getElementById('create-submit-btn');
  const errEl = document.getElementById('create-error');

  const requiredSkills  = requiredSkillsCtrl  ? requiredSkillsCtrl.getTags()  : [];
  const preferredSkills = preferredSkillsCtrl ? preferredSkillsCtrl.getTags() : [];

  if (!requiredSkills.length) {
    showEl('create-error', 'Please add at least one required skill.');
    return;
  }

  const deadlineVal = form.deadline.value;
  const deadlineISO = deadlineVal ? new Date(deadlineVal).toISOString() : '';

  const payload = {
    company_name:      form.company_name.value.trim(),
    job_title:         form.job_title.value.trim(),
    work_type:         form.work_type.value,
    experience_level:  form.experience_level.value,
    location:          form.location.value.trim(),
    salary_range:      form.salary_range.value.trim(),
    job_description:   form.job_description.value.trim(),
    required_skills:   requiredSkills,
    preferred_skills:  preferredSkills,
    max_applicants:    parseInt(form.max_applicants.value, 10),
    deadline:          deadlineISO,
    apply_link:        form.apply_link.value.trim(),
    is_remote:         form.is_remote.checked,
    is_urgent:         form.is_urgent.checked,
  };

  if (form.minimum_cgpa.value) payload.minimum_cgpa = parseFloat(form.minimum_cgpa.value);

  btn.disabled = true;
  btn.textContent = 'Posting…';
  hideEl('create-error');

  const result = await apiPost('/api/referrals/', payload);
  btn.disabled = false;
  btn.textContent = 'Post Referral';

  if (result.ok) {
    closeCreateModal();
    showToast('Referral posted successfully!', 'success');
    currentPage = 1;
    loadReferrals();
  } else {
    const msg = extractErrorMessage(result.error);
    showEl('create-error', msg);
  }
}

// ── Apply modal (board + detail) ──────────────────────────────
function openApplyModal(referralId, matchScore) {
  activeApplyReferralId = referralId;
  const modal = document.getElementById('apply-modal');
  if (!modal) return;
  modal.classList.remove('hidden');

  const coverNote = document.getElementById('apply-cover-note');
  if (coverNote) coverNote.value = '';
  hideEl('apply-error');

  const matchInfo = document.getElementById('apply-match-info');
  if (matchInfo && matchScore !== null && matchScore !== undefined) {
    const color = matchScore >= 80 ? 'emerald' : matchScore >= 60 ? 'amber' : matchScore >= 40 ? 'blue' : 'red';
    matchInfo.innerHTML = `
      <div class="flex items-center gap-3 p-3 bg-${color}-50 rounded-lg border border-${color}-100">
        ${renderMatchScoreMini(matchScore).outerHTML}
        <div>
          <p class="text-sm font-semibold text-${color}-700">${matchScore}% Match</p>
          <p class="text-xs text-${color}-600">${matchScore >= 40 ? 'You meet the minimum requirements.' : 'Low match — you may still apply.'}</p>
        </div>
      </div>
    `;
  } else if (matchInfo) {
    matchInfo.innerHTML = '';
  }
}

function closeApplyModal() {
  document.getElementById('apply-modal')?.classList.add('hidden');
  activeApplyReferralId = null;
}

async function submitApplication() {
  if (!activeApplyReferralId) return;
  const btn = document.getElementById('apply-submit-btn');
  const coverNote = document.getElementById('apply-cover-note')?.value.trim() || '';

  btn.disabled = true;
  btn.textContent = 'Submitting…';
  hideEl('apply-error');

  const result = await apiPost(`/api/referrals/${activeApplyReferralId}/apply/`, { cover_note: coverNote });
  btn.disabled = false;
  btn.textContent = 'Submit Application';

  if (result.ok) {
    closeApplyModal();
    showToast('Application submitted!', 'success');
    // Refresh current page
    if (typeof REFERRAL_ID !== 'undefined') {
      loadDetail();
    } else {
      loadReferrals();
    }
  } else {
    const msg = extractErrorMessage(result.error);
    showEl('apply-error', msg);
  }
}

// ══════════════════════════════════════════════════════════════
// REFERRAL DETAIL PAGE
// ══════════════════════════════════════════════════════════════
function initDetailPage() {
  loadDetail();
}

async function loadDetail() {
  showEl('detail-skeleton');
  hideEl('detail-content');
  hideEl('detail-error');

  const result = await apiGet(`/api/referrals/${REFERRAL_ID}/`);
  hideEl('detail-skeleton');

  if (!result.ok) {
    showEl('detail-error');
    return;
  }

  const r = result.data;
  renderDetailContent(r);
  showEl('detail-content');
}

function renderDetailContent(r) {
  setText('detail-title',   r.job_title);
  setText('detail-company', r.company_name);
  setText('detail-description', r.job_description);

  const logo = document.getElementById('detail-logo');
  if (logo) {
    if (r.company_logo_url) {
      logo.innerHTML = `<img src="${r.company_logo_url}" alt="${escHtml(r.company_name)}" class="w-14 h-14 rounded-xl object-cover"/>`;
    } else {
      logo.textContent = (r.company_name || '?')[0].toUpperCase();
    }
  }

  // Badges
  if (r.is_urgent) showEl('detail-urgent-badge');
  const statusBadge = document.getElementById('detail-status-badge');
  if (statusBadge) {
    const cls = r.status === 'active' ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500';
    statusBadge.className = `px-2.5 py-1 text-xs font-semibold rounded-full ${cls}`;
    statusBadge.textContent = r.status === 'active' ? 'Active' : r.status.charAt(0).toUpperCase() + r.status.slice(1);
  }

  setText('detail-work-type', WORK_TYPE_LABELS[r.work_type] || r.work_type);
  setText('detail-exp-level', EXP_LABELS[r.experience_level] || r.experience_level);
  setText('detail-location',  r.location || (r.is_remote ? 'Remote' : 'Location TBD'));
  if (r.salary_range) { setText('detail-salary', r.salary_range); showEl('detail-salary'); }
  if (r.is_remote) showEl('detail-remote-badge');

  // Slots
  const pct = r.max_applicants > 0 ? Math.min(100, (r.total_applications / r.max_applicants) * 100) : 0;
  setText('detail-slots-text', `${r.total_applications} / ${r.max_applicants} applied`);
  const bar = document.getElementById('detail-slots-bar');
  if (bar) {
    bar.style.width = `${pct}%`;
    bar.className = `h-2 rounded-full transition-all ${pct >= 100 ? 'bg-red-400' : pct >= 60 ? 'bg-amber-400' : 'bg-blue-500'}`;
  }
  setText('detail-deadline', `Deadline: ${r.time_remaining || 'N/A'}`);

  // Required skills
  const reqSkills = document.getElementById('detail-required-skills');
  if (reqSkills) {
    reqSkills.innerHTML = '';
    (r.required_skills || []).forEach(s => {
      const tag = document.createElement('span');
      tag.className = 'px-2.5 py-1 bg-blue-50 text-blue-700 text-xs font-medium rounded-full';
      tag.textContent = s;
      reqSkills.appendChild(tag);
    });
  }

  // Preferred skills
  if (r.preferred_skills?.length) {
    showEl('preferred-skills-section');
    const prefSkills = document.getElementById('detail-preferred-skills');
    if (prefSkills) {
      prefSkills.innerHTML = '';
      r.preferred_skills.forEach(s => {
        const tag = document.createElement('span');
        tag.className = 'px-2.5 py-1 bg-slate-100 text-slate-600 text-xs font-medium rounded-full';
        tag.textContent = s;
        prefSkills.appendChild(tag);
      });
    }
  }

  // Eligibility
  const eligContent = document.getElementById('eligibility-content');
  const eligCard    = document.getElementById('eligibility-card');
  if (eligContent && eligCard) {
    const items = [];
    if (r.minimum_cgpa)              items.push(`Minimum CGPA: ${r.minimum_cgpa}`);
    if (r.eligible_branches?.length) items.push(`Branches: ${r.eligible_branches.join(', ')}`);
    if (r.eligible_graduation_years?.length) items.push(`Graduation Years: ${r.eligible_graduation_years.join(', ')}`);
    if (items.length) {
      eligContent.innerHTML = items.map(i => `<p class="flex items-center gap-2"><span class="text-blue-500">•</span>${escHtml(i)}</p>`).join('');
      eligCard.classList.remove('hidden');
    }
  }

  // Author
  const author = r.posted_by;
  if (author) {
    const avatarEl = document.getElementById('author-avatar');
    if (avatarEl) {
      if (author.profile_pic) {
        avatarEl.innerHTML = `<img src="${author.profile_pic}" class="w-10 h-10 rounded-full object-cover"/>`;
      } else {
        avatarEl.textContent = getInitials(`${author.first_name} ${author.last_name}`);
      }
    }
    setText('author-name', `${author.first_name} ${author.last_name}`);
    const detail = author.role_detail || {};
    setText('author-detail', detail.company ? `${detail.designation || ''} @ ${detail.company}` : detail.department || author.role);
  }

  // Match score (students)
  if (typeof IS_STUDENT !== 'undefined' && IS_STUDENT && r.skill_match_detail) {
    renderDetailMatchScore(r.skill_match_detail);
  }

  // Action card
  renderDetailActionCard(r);
}

function renderDetailMatchScore(match) {
  const card = document.getElementById('match-score-card');
  if (!card) return;
  card.classList.remove('hidden');

  const score = match.score || 0;
  const circ  = 2 * Math.PI * 40;
  const offset = circ - (score / 100) * circ;
  const color = score >= 80 ? '#10b981' : score >= 60 ? '#f59e0b' : score >= 40 ? '#3b82f6' : '#ef4444';

  const circle = document.getElementById('match-circle');
  const scoreText = document.getElementById('match-score-text');
  if (circle) {
    circle.setAttribute('stroke', color);
    circle.setAttribute('stroke-dashoffset', offset.toFixed(2));
  }
  if (scoreText) scoreText.textContent = `${score}%`;

  setText('match-reason', match.reason || '');

  const detail = document.getElementById('match-skills-detail');
  if (detail) {
    detail.innerHTML = '';
    if (match.matched_skills?.length) {
      const row = document.createElement('div');
      row.innerHTML = `<p class="text-xs font-medium text-slate-500 mb-1">Matched</p>`;
      const tags = document.createElement('div');
      tags.className = 'flex flex-wrap gap-1';
      match.matched_skills.forEach(s => {
        const t = document.createElement('span');
        t.className = 'px-2 py-0.5 bg-emerald-50 text-emerald-700 text-xs rounded-full';
        t.textContent = s;
        tags.appendChild(t);
      });
      row.appendChild(tags);
      detail.appendChild(row);
    }
    if (match.missing_skills?.length) {
      const row = document.createElement('div');
      row.innerHTML = `<p class="text-xs font-medium text-slate-500 mb-1 mt-2">Missing</p>`;
      const tags = document.createElement('div');
      tags.className = 'flex flex-wrap gap-1';
      match.missing_skills.forEach(s => {
        const t = document.createElement('span');
        t.className = 'px-2 py-0.5 bg-red-50 text-red-600 text-xs rounded-full';
        t.textContent = s;
        tags.appendChild(t);
      });
      row.appendChild(tags);
      detail.appendChild(row);
    }
  }
}

function renderDetailActionCard(r) {
  const section = document.getElementById('apply-section');
  if (!section) return;
  section.innerHTML = '';

  if (typeof IS_STUDENT !== 'undefined' && IS_STUDENT) {
    if (r.has_applied) {
      section.innerHTML = `
        <div class="text-center py-2">
          <span class="inline-flex items-center gap-2 px-4 py-2 bg-emerald-100 text-emerald-700 text-sm font-semibold rounded-full">
            ✓ Application Submitted
          </span>
          <p class="text-xs text-slate-400 mt-2">Check status in <a href="/referrals/my-applications/" class="text-blue-600 hover:underline">My Applications</a></p>
        </div>
      `;
    } else if (r.is_accepting_applications) {
      const btn = document.createElement('button');
      btn.className = 'w-full px-4 py-3 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 transition-colors';
      btn.textContent = 'Apply for Referral';
      btn.onclick = () => openApplyModal(r.id, r.match_score);
      section.appendChild(btn);
      if (r.apply_link) {
        const ext = document.createElement('a');
        ext.href = r.apply_link;
        ext.target = '_blank';
        ext.rel = 'noopener noreferrer';
        ext.className = 'block text-center text-xs text-blue-600 hover:underline mt-2';
        ext.textContent = 'Also apply directly →';
        section.appendChild(ext);
      }
    } else {
      section.innerHTML = `
        <div class="text-center py-2">
          <span class="inline-flex items-center gap-2 px-4 py-2 bg-slate-100 text-slate-500 text-sm font-medium rounded-full">
            ${r.is_expired ? '⏰ Expired' : r.is_full ? '🔒 All Slots Filled' : 'Closed'}
          </span>
        </div>
      `;
    }
  } else if (typeof CAN_POST !== 'undefined' && CAN_POST) {
    const manageBtn = document.createElement('a');
    manageBtn.href = `/referrals/${r.id}/manage/`;
    manageBtn.className = 'block w-full text-center px-4 py-3 bg-blue-600 text-white text-sm font-semibold rounded-lg hover:bg-blue-700 transition-colors';
    manageBtn.textContent = 'Manage Applications';
    section.appendChild(manageBtn);
  }
}

// ══════════════════════════════════════════════════════════════
// MY APPLICATIONS (student)
// ══════════════════════════════════════════════════════════════
function initMyApplications() {
  loadMyApplications();
  // Style active tab
  document.querySelectorAll('.status-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.status-tab').forEach(b => b.classList.remove('active-tab', 'bg-blue-600', 'text-white', 'border-blue-600'));
      btn.classList.add('active-tab', 'bg-blue-600', 'text-white', 'border-blue-600');
    });
  });
}

async function loadMyApplications(statusFilter = '') {
  const url = statusFilter ? `/api/referrals/my-applications/?status=${statusFilter}` : '/api/referrals/my-applications/';
  const result = await apiGet(url);
  hideSkeletons('.app-skeleton');

  const list  = document.getElementById('applications-list');
  const empty = document.getElementById('empty-state');
  if (!list) return;

  if (!result.ok) {
    list.innerHTML = `<p class="text-center text-slate-500 py-10">Failed to load applications.</p>`;
    return;
  }

  allApplications = result.data || [];
  renderMyApplications(allApplications);
}

function filterByStatus(status) {
  loadMyApplications(status);
}

function renderMyApplications(apps) {
  const list  = document.getElementById('applications-list');
  const empty = document.getElementById('empty-state');
  if (!list) return;

  list.innerHTML = '';
  if (!apps.length) {
    if (empty) empty.classList.remove('hidden');
    return;
  }
  if (empty) empty.classList.add('hidden');
  apps.forEach(app => list.appendChild(renderApplicationCard(app)));
}

function renderApplicationCard(app) {
  const r = app.referral || {};
  const statusCls   = STATUS_COLORS[app.status]  || 'bg-slate-100 text-slate-500';
  const statusLabel = STATUS_LABELS[app.status]   || app.status;

  const card = document.createElement('div');
  card.className = 'bg-white rounded-xl border border-slate-200 p-5 hover:shadow-sm transition-shadow';

  card.innerHTML = `
    <div class="flex items-start gap-4">
      <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center text-white font-bold text-lg flex-shrink-0">
        ${escHtml((r.company_name || '?')[0].toUpperCase())}
      </div>
      <div class="flex-1 min-w-0">
        <div class="flex items-start justify-between gap-3">
          <div>
            <a href="/referrals/${r.id}/" class="text-sm font-bold text-slate-800 hover:text-blue-600 transition-colors">${escHtml(r.job_title || 'Unknown Role')}</a>
            <p class="text-xs text-slate-500 mt-0.5">${escHtml(r.company_name || '')} · ${WORK_TYPE_LABELS[r.work_type] || ''}</p>
          </div>
          <span class="px-2.5 py-1 text-xs font-semibold rounded-full flex-shrink-0 ${statusCls}">${statusLabel}</span>
        </div>
        <div class="flex items-center gap-4 mt-3">
          <span class="text-xs text-slate-400">Applied ${formatDate(app.applied_at)}</span>
          ${app.match_score ? `<span class="text-xs text-slate-400">Match: ${app.match_score}%</span>` : ''}
          ${app.is_faculty_recommended ? `<span class="px-2 py-0.5 bg-teal-50 text-teal-700 text-xs font-medium rounded-full">⭐ Faculty Recommended</span>` : ''}
        </div>
        ${app.alumni_note ? `<div class="mt-2 p-2.5 bg-blue-50 rounded-lg text-xs text-blue-700"><span class="font-medium">Note:</span> ${escHtml(app.alumni_note)}</div>` : ''}
      </div>
    </div>
    ${app.status !== 'withdrawn' && app.status !== 'hired' ? `
    <div class="flex justify-end mt-3 pt-3 border-t border-slate-100">
      <button onclick="openWithdrawModal(${app.id})" class="text-xs text-red-500 hover:text-red-700 hover:underline transition-colors">Withdraw Application</button>
    </div>` : ''}
  `;
  return card;
}

// ── Withdraw modal ────────────────────────────────────────────
let pendingWithdrawId = null;

function openWithdrawModal(applicationId) {
  pendingWithdrawId = applicationId;
  document.getElementById('withdraw-modal')?.classList.remove('hidden');
  const btn = document.getElementById('confirm-withdraw-btn');
  if (btn) btn.onclick = confirmWithdraw;
}

function closeWithdrawModal() {
  document.getElementById('withdraw-modal')?.classList.add('hidden');
  pendingWithdrawId = null;
}

async function confirmWithdraw() {
  if (!pendingWithdrawId) return;
  const btn = document.getElementById('confirm-withdraw-btn');
  if (btn) { btn.disabled = true; btn.textContent = 'Withdrawing…'; }

  const result = await apiFetch(`/api/referrals/my-applications/${pendingWithdrawId}/withdraw/`, { method: 'DELETE' });

  if (btn) { btn.disabled = false; btn.textContent = 'Withdraw'; }
  closeWithdrawModal();

  if (result.ok) {
    showToast('Application withdrawn.', 'info');
    loadMyApplications();
  } else {
    showToast(extractErrorMessage(result.error), 'error');
  }
}

// ══════════════════════════════════════════════════════════════
// MANAGE APPLICATIONS (alumni / faculty)
// ══════════════════════════════════════════════════════════════
function initManageApplications() {
  loadManageApplications();
  document.querySelectorAll('.manage-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.manage-tab').forEach(b => b.classList.remove('active-tab', 'bg-blue-600', 'text-white', 'border-blue-600'));
      btn.classList.add('active-tab', 'bg-blue-600', 'text-white', 'border-blue-600');
    });
  });
}

async function loadManageApplications() {
  const result = await apiGet(`/api/referrals/${REFERRAL_ID}/applications/`);
  hideSkeletons('.manage-skeleton');
  hideEl('referral-summary-skeleton');

  if (!result.ok) {
    showToast('Failed to load applications.', 'error');
    return;
  }

  const data = result.data;
  allApplications = data.applications || [];

  // Render referral summary
  const r = data.referral || {};
  const logo = document.getElementById('manage-logo');
  if (logo) logo.textContent = (r.company_name || '?')[0].toUpperCase();
  setText('manage-title',   r.job_title || '');
  setText('manage-company', r.company_name || '');
  setText('stat-total',       data.total || 0);
  setText('stat-shortlisted', data.by_status?.shortlisted || 0);
  setText('stat-hired',       data.by_status?.hired || 0);
  setText('stat-slots',       r.slots_remaining ?? '—');
  showEl('referral-summary');

  // Render boost button
  const boostContainer = document.getElementById('boost-btn-container');
  if (boostContainer) {
    if (r.is_boosted) {
      boostContainer.innerHTML = `
        <span class="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-100 text-emerald-700 text-xs font-semibold rounded-lg">
          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
            <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
          </svg>
          Boosted ✓
        </span>`;
    } else {
      boostContainer.innerHTML = `
        <button id="boost-btn-${REFERRAL_ID}" onclick="initiateBoostPayment(${REFERRAL_ID})"
          class="inline-flex items-center gap-1.5 px-3 py-1.5 bg-amber-100 text-amber-700 text-xs font-semibold rounded-lg hover:bg-amber-200 transition-colors">
          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z"/>
          </svg>
          Boost Referral ₹99
        </button>`;
    }
  }

  renderManageApplications(allApplications);
}

function filterApplications(status) {
  const filtered = status ? allApplications.filter(a => a.status === status) : allApplications;
  renderManageApplications(filtered);
}

function renderManageApplications(apps) {
  const list  = document.getElementById('manage-applications-list');
  const empty = document.getElementById('empty-state');
  if (!list) return;

  list.innerHTML = '';
  if (!apps.length) {
    if (empty) empty.classList.remove('hidden');
    return;
  }
  if (empty) empty.classList.add('hidden');
  apps.forEach(app => list.appendChild(renderManageCard(app)));
}

function renderManageCard(app) {
  const s = app.student || {};
  const statusCls   = STATUS_COLORS[app.status]  || 'bg-slate-100 text-slate-500';
  const statusLabel = STATUS_LABELS[app.status]   || app.status;

  const card = document.createElement('div');
  card.className = 'bg-white rounded-xl border border-slate-200 p-5';

  const initials = getInitials(`${s.first_name || ''} ${s.last_name || ''}`);

  card.innerHTML = `
    <div class="flex items-start gap-4">
      <div class="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center text-white text-sm font-bold flex-shrink-0">
        ${s.profile_pic ? `<img src="${s.profile_pic}" class="w-10 h-10 rounded-full object-cover"/>` : escHtml(initials)}
      </div>
      <div class="flex-1 min-w-0">
        <div class="flex items-start justify-between gap-3">
          <div>
            <p class="text-sm font-bold text-slate-800">${escHtml(`${s.first_name || ''} ${s.last_name || ''}`.trim())}</p>
            <p class="text-xs text-slate-500">${escHtml(s.degree || '')} ${s.branch ? `· ${s.branch}` : ''} ${s.graduation_year ? `· ${s.graduation_year}` : ''}</p>
          </div>
          <span class="px-2.5 py-1 text-xs font-semibold rounded-full flex-shrink-0 ${statusCls}">${statusLabel}</span>
        </div>
        <div class="flex flex-wrap items-center gap-3 mt-2">
          <span class="text-xs text-slate-400">Match: <strong class="text-slate-600">${app.match_score}%</strong></span>
          ${app.is_faculty_recommended ? `<span class="px-2 py-0.5 bg-teal-50 text-teal-700 text-xs font-medium rounded-full">⭐ Faculty Rec.</span>` : ''}
          ${s.github_url ? `<a href="${escHtml(s.github_url)}" target="_blank" rel="noopener" class="text-xs text-blue-600 hover:underline">GitHub</a>` : ''}
          ${s.resume_file ? `<a href="${escHtml(s.resume_file)}" target="_blank" rel="noopener" class="text-xs text-blue-600 hover:underline">Resume</a>` : ''}
        </div>
        ${app.cover_note ? `<div class="mt-2 p-2.5 bg-slate-50 rounded-lg text-xs text-slate-600 italic">"${escHtml(app.cover_note)}"</div>` : ''}
        ${app.matched_skills?.length ? `
          <div class="flex flex-wrap gap-1 mt-2">
            ${app.matched_skills.map(sk => `<span class="px-2 py-0.5 bg-emerald-50 text-emerald-700 text-xs rounded-full">${escHtml(sk)}</span>`).join('')}
          </div>` : ''}
      </div>
    </div>
    <div class="flex justify-end mt-3 pt-3 border-t border-slate-100">
      <a href="/students/${s.id}/profile/" target="_blank"
        class="text-xs text-slate-500 hover:text-blue-600 hover:underline mr-auto transition-colors">
        View Profile →
      </a>
      <button onclick="openUpdateModal(${app.id}, '${app.status}', '${escHtml(`${s.first_name || ''} ${s.last_name || ''}`.trim())}')"
        class="px-3 py-1.5 bg-blue-600 text-white text-xs font-medium rounded-lg hover:bg-blue-700 transition-colors">
        Update Status
      </button>
    </div>
  `;
  return card;
}

// ── Update status modal ───────────────────────────────────────
function openUpdateModal(applicationId, currentStatus, studentName) {
  activeUpdateApplicationId = applicationId;
  const modal = document.getElementById('update-modal');
  if (!modal) return;
  modal.classList.remove('hidden');

  const select = document.getElementById('update-status-select');
  if (select) select.value = currentStatus;

  const noteEl = document.getElementById('update-note');
  if (noteEl) noteEl.value = '';

  const info = document.getElementById('update-student-info');
  if (info) {
    info.innerHTML = `
      <div class="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
        ${escHtml(getInitials(studentName))}
      </div>
      <div>
        <p class="text-sm font-semibold text-slate-800">${escHtml(studentName)}</p>
        <p class="text-xs text-slate-500">Current: ${STATUS_LABELS[currentStatus] || currentStatus}</p>
      </div>
    `;
  }
}

function closeUpdateModal() {
  document.getElementById('update-modal')?.classList.add('hidden');
  activeUpdateApplicationId = null;
}

async function submitStatusUpdate() {
  if (!activeUpdateApplicationId) return;
  const btn    = document.getElementById('update-submit-btn');
  const status = document.getElementById('update-status-select')?.value;
  const note   = document.getElementById('update-note')?.value.trim() || '';

  btn.disabled = true;
  btn.textContent = 'Updating…';

  const result = await apiPost(`/api/referrals/applications/${activeUpdateApplicationId}/update/`, { status, alumni_note: note }, 'PATCH');
  btn.disabled = false;
  btn.textContent = 'Update Status';

  if (result.ok) {
    closeUpdateModal();
    showToast(`Status updated to ${STATUS_LABELS[status] || status}`, 'success');
    loadManageApplications();
  } else {
    showToast(extractErrorMessage(result.error), 'error');
  }
}

// ══════════════════════════════════════════════════════════════
// SUCCESS STORIES
// ══════════════════════════════════════════════════════════════
function initSuccessStories() {
  loadSuccessStories();
}

async function loadSuccessStories() {
  const result = await apiGet('/api/referrals/success-stories/');
  hideSkeletons('.story-skeleton');

  const grid  = document.getElementById('stories-grid');
  const empty = document.getElementById('empty-state');
  if (!grid) return;

  grid.innerHTML = '';

  if (!result.ok) {
    grid.innerHTML = `<p class="col-span-3 text-center text-slate-500 py-10">Failed to load stories.</p>`;
    return;
  }

  const stories = result.data || [];
  if (!stories.length) {
    if (empty) empty.classList.remove('hidden');
    return;
  }
  if (empty) empty.classList.add('hidden');
  stories.forEach(s => grid.appendChild(renderStoryCard(s)));
}

function renderStoryCard(story) {
  const card = document.createElement('div');
  card.className = 'bg-white rounded-xl border border-slate-200 p-5 hover:shadow-md transition-shadow';

  card.innerHTML = `
    <div class="flex items-center gap-3 mb-4">
      <div class="w-10 h-10 rounded-full bg-gradient-to-br from-emerald-400 to-teal-600 flex items-center justify-center text-white text-sm font-bold flex-shrink-0">
        ${escHtml(getInitials(story.student_name))}
      </div>
      <div>
        <p class="text-sm font-bold text-slate-800">${escHtml(story.student_name)}</p>
        <p class="text-xs text-slate-500">Referred by ${escHtml(story.alumni_name)}</p>
      </div>
    </div>
    <div class="flex items-center gap-2 mb-3">
      <span class="px-2.5 py-1 bg-emerald-50 text-emerald-700 text-xs font-semibold rounded-full">🎉 Hired</span>
      <span class="text-xs text-slate-600 font-medium">${escHtml(story.job_title)}</span>
    </div>
    <p class="text-sm font-semibold text-slate-700 mb-2">@ ${escHtml(story.company_name)}</p>
    ${story.testimonial ? `
      <blockquote class="text-xs text-slate-500 italic border-l-2 border-emerald-200 pl-3 leading-relaxed">
        "${escHtml(story.testimonial)}"
      </blockquote>` : ''}
    <p class="text-xs text-slate-400 mt-3">${formatDate(story.created_at)}</p>
  `;
  return card;
}

// ══════════════════════════════════════════════════════════════
// UTILITIES
// ══════════════════════════════════════════════════════════════
function escHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function setText(id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text ?? '';
}

function showEl(id, text) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.remove('hidden');
  if (text !== undefined) el.textContent = text;
}

function hideEl(id) {
  document.getElementById(id)?.classList.add('hidden');
}

function hideSkeletons(selector) {
  document.querySelectorAll(selector).forEach(el => el.remove());
}

function formatDate(iso) {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
  } catch {
    return iso;
  }
}

// Active tab styling on load
document.addEventListener('DOMContentLoaded', () => {
  const style = document.createElement('style');
  style.textContent = `
    .active-tab { background: #2563eb !important; color: #fff !important; border-color: #2563eb !important; }
  `;
  document.head.appendChild(style);
});

// ══════════════════════════════════════════════════════════════
// FACULTY RECOMMENDATION (detail page)
// ══════════════════════════════════════════════════════════════
let selectedStudentId = null;

function initFacultyRecommendation() {
  const searchInput = document.getElementById('faculty-student-search');
  if (!searchInput) return;

  const debouncedSearch = debounce(async (query) => {
    if (query.length < 2) {
      hideStudentDropdown();
      return;
    }
    const result = await apiGet(`/api/accounts/?role=student&search=${encodeURIComponent(query)}`);
    if (result.ok) {
      renderStudentDropdown(result.data.results || result.data || []);
    }
  }, 400);

  searchInput.addEventListener('input', (e) => debouncedSearch(e.target.value.trim()));

  // Close dropdown on outside click
  document.addEventListener('click', (e) => {
    if (!searchInput.contains(e.target)) hideStudentDropdown();
  });
}

function renderStudentDropdown(students) {
  const dropdown = document.getElementById('student-search-dropdown');
  if (!dropdown) return;

  dropdown.innerHTML = '';
  if (!students.length) {
    dropdown.innerHTML = `<p class="px-3 py-2 text-xs text-slate-400">No students found</p>`;
    dropdown.classList.remove('hidden');
    return;
  }

  students.slice(0, 8).forEach(s => {
    const item = document.createElement('button');
    item.type = 'button';
    item.className = 'w-full flex items-center gap-3 px-3 py-2.5 hover:bg-slate-50 transition-colors text-left';
    item.innerHTML = `
      <div class="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
        ${escHtml(getInitials(`${s.first_name || ''} ${s.last_name || ''}`))}
      </div>
      <div class="flex-1 min-w-0">
        <p class="text-sm font-medium text-slate-800 truncate">${escHtml(`${s.first_name || ''} ${s.last_name || ''}`.trim())}</p>
        <p class="text-xs text-slate-400 truncate">${escHtml(s.email || '')} · ${escHtml(s.college || '')}</p>
      </div>
    `;
    item.onclick = () => selectStudent(s);
    dropdown.appendChild(item);
  });

  dropdown.classList.remove('hidden');
}

function hideStudentDropdown() {
  document.getElementById('student-search-dropdown')?.classList.add('hidden');
}

function selectStudent(student) {
  selectedStudentId = student.id;
  hideStudentDropdown();

  const searchInput = document.getElementById('faculty-student-search');
  if (searchInput) searchInput.value = `${student.first_name || ''} ${student.last_name || ''}`.trim();

  const preview = document.getElementById('selected-student-preview');
  if (preview) {
    preview.classList.remove('hidden');
    const avatar = document.getElementById('rec-student-avatar');
    if (avatar) avatar.textContent = getInitials(`${student.first_name || ''} ${student.last_name || ''}`);
    const nameEl = document.getElementById('rec-student-name');
    if (nameEl) nameEl.textContent = `${student.first_name || ''} ${student.last_name || ''}`.trim();
    const collegeEl = document.getElementById('rec-student-college');
    if (collegeEl) collegeEl.textContent = student.college || '';

    // Skills pills
    const skillsEl = document.getElementById('rec-student-skills');
    if (skillsEl) {
      skillsEl.innerHTML = '';
      const skills = student.skills || student.student_profile?.skills || [];
      skills.slice(0, 5).forEach(sk => {
        const tag = document.createElement('span');
        tag.className = 'px-2 py-0.5 bg-teal-100 text-teal-700 text-xs rounded-full';
        tag.textContent = sk;
        skillsEl.appendChild(tag);
      });
    }
  }
}

function clearSelectedStudent() {
  selectedStudentId = null;
  const searchInput = document.getElementById('faculty-student-search');
  if (searchInput) searchInput.value = '';
  document.getElementById('selected-student-preview')?.classList.add('hidden');
}

async function submitFacultyRecommendation() {
  if (!selectedStudentId) {
    showEl('rec-error', 'Please search and select a student first.');
    return;
  }

  const btn  = document.getElementById('submit-recommendation-btn');
  const note = document.getElementById('recommendation-note')?.value.trim() || '';

  btn.disabled = true;
  btn.textContent = 'Recommending…';
  hideEl('rec-error');

  const result = await apiPost(`/api/referrals/${REFERRAL_ID}/recommend/`, {
    student_id: selectedStudentId,
    note,
  });

  btn.disabled = false;
  btn.textContent = 'Recommend Student';

  if (result.ok) {
    showToast('Recommendation sent! The alumni has been notified.', 'success');
    clearSelectedStudent();
    document.getElementById('recommendation-note').value = '';
  } else {
    showEl('rec-error', extractErrorMessage(result.error));
  }
}

// Wire up faculty recommendation on detail page init
const _origInitDetailPage = initDetailPage;
// Override initDetailPage to also init faculty recommendation
function initDetailPage() {
  loadDetail();
  if (typeof IS_FACULTY !== 'undefined' && IS_FACULTY) {
    initFacultyRecommendation();
  }
}
