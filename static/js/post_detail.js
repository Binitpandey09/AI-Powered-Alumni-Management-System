/* ============================================================
   AlumniAI — Post Detail Page JS  (redesigned)
   ============================================================ */

let _postId = null;
let _currentUser = null;

document.addEventListener('DOMContentLoaded', async () => {
    const root = document.getElementById('post-detail-root');
    _postId = root ? parseInt(root.dataset.postId) : null;
    if (!_postId) return;
    await loadCurrentUser();
    await loadPost();
});

async function loadCurrentUser() {
    const res = await apiGet('/api/accounts/me/');
    if (res.ok) _currentUser = res.data;
}

async function loadPost() {
    const root = document.getElementById('post-detail-root');
    if (!root) return;

    root.innerHTML = `
    <div style="display:flex;justify-content:center;align-items:center;padding:80px 0;gap:14px;">
      <div style="width:32px;height:32px;border:3px solid #e2e8f0;border-top-color:#2563eb;border-radius:50%;animation:spin .75s linear infinite;"></div>
      <span style="color:#94a3b8;font-size:.9375rem;">Loading post…</span>
    </div>`;

    const res = await apiGet(`/api/feed/${_postId}/`);
    if (!res.ok) {
        root.innerHTML = `
        <div style="text-align:center;padding:80px 20px;">
          <div style="font-size:2.5rem;margin-bottom:12px;">🔍</div>
          <p style="font-size:1rem;font-weight:600;color:#0f172a;margin:0 0 6px;">Post not found</p>
          <p style="font-size:.875rem;color:#64748b;margin:0 0 20px;">This post may have been removed or is no longer available.</p>
          <a href="/feed/" style="display:inline-flex;align-items:center;gap:6px;padding:10px 22px;background:#2563eb;color:#fff;border-radius:10px;text-decoration:none;font-size:.875rem;font-weight:600;">
            ← Back to Feed
          </a>
        </div>`;
        return;
    }
    renderPost(res.data, root);
}

// ── Main render ───────────────────────────────────────────────
function renderPost(post, root) {
    const author   = post.author || {};
    const initials = ((author.first_name?.[0] || '') + (author.last_name?.[0] || '')).toUpperCase() || '?';
    const roleColors = { alumni: '#534AB7', student: '#2563EB', faculty: '#0F6E56' };
    const avatarColor = roleColors[author.role] || '#94a3b8';
    const authorName  = ((author.first_name || '') + ' ' + (author.last_name || '')).trim() || 'Unknown';

    const rd = author.role_detail || {};
    let roleDetail = '';
    if (author.role === 'alumni' && rd.company)    roleDetail = `${rd.designation || ''} @ ${rd.company}`.trim().replace(/^@ /, '');
    else if (author.role === 'faculty' && rd.department) roleDetail = `${rd.designation || 'Faculty'} · ${rd.department}`;
    else if (author.role === 'student')            roleDetail = author.college || '';

    const badgeCfg = {
        job:          { cls: 'badge-job',         label: 'Job Opportunity', icon: '💼' },
        referral:     { cls: 'badge-referral',     label: 'Job Referral',    icon: '🤝' },
        session:      { cls: 'badge-session',      label: 'Session',         icon: '🎓' },
        announcement: { cls: 'badge-announcement', label: 'Announcement',    icon: '📢' },
        general:      { cls: 'badge-general',      label: 'General',         icon: '' },
        ad:           { cls: 'badge-ad',           label: 'Ad',              icon: '' },
    };
    const badge = badgeCfg[post.post_type] || { cls: 'badge-general', label: post.post_type, icon: '' };

    const tagsHtml = (post.tags || []).map(t =>
        `<span style="padding:3px 10px;font-size:.6875rem;background:#f1f5f9;color:#475569;border-radius:9999px;border:1px solid #e2e8f0;">#${escHtml(t)}</span>`
    ).join('');

    const expiryBadge = buildDetailExpiryBadge(post);

    const hasActionPanel = post.post_type === 'job' || post.post_type === 'referral' || post.post_type === 'session';
    const actionPanelHtml = hasActionPanel ? buildActionPanel(post) : '';
    const jobDetailHtml   = (post.post_type === 'job' || post.post_type === 'referral') ? buildJobDetailSection(post) : '';
    const sessionDetailHtml = post.post_type === 'session' ? buildSessionDetailSection(post) : '';

    // Two-col on desktop when there's an action panel
    const layoutStyle = hasActionPanel
        ? 'display:flex;gap:20px;align-items:flex-start;'
        : 'display:block;';
    const mainColStyle  = hasActionPanel ? 'flex:1;min-width:0;' : '';
    const rightColStyle = 'width:320px;flex-shrink:0;position:sticky;top:20px;';

    root.innerHTML = `
    <!-- Back -->
    <div style="margin-bottom:20px;">
      <a href="/feed/" style="display:inline-flex;align-items:center;gap:7px;font-size:.875rem;font-weight:500;color:#64748b;text-decoration:none;padding:6px 12px;border-radius:8px;border:1px solid #e2e8f0;background:#fff;transition:all .15s;"
         onmouseover="this.style.background='#f8fafc';this.style.borderColor='#cbd5e1';this.style.color='#0f172a'"
         onmouseout="this.style.background='#fff';this.style.borderColor='#e2e8f0';this.style.color='#64748b'">
        <svg width="15" height="15" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M19 12H5M5 12l7 7M5 12l7-7"/>
        </svg>
        Back to Feed
      </a>
    </div>

    <div id="pd-layout" style="${layoutStyle}">

      <!-- ═══ LEFT / MAIN COLUMN ═══ -->
      <div style="${mainColStyle}">

        <!-- Post card -->
        <div style="background:#fff;border:1px solid #e2e8f0;border-radius:16px;overflow:hidden;box-shadow:0 1px 6px rgba(0,0,0,.05);margin-bottom:16px;">

          <!-- Post image (if any) - full width at top -->
          ${post.image ? `<img src="${escHtml(post.image)}" alt="Post image" style="width:100%;max-height:380px;object-fit:cover;display:block;"/>` : ''}

          <div style="padding:24px;">

            <!-- Author row -->
            <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:18px;">
              <div style="display:flex;align-items:center;gap:12px;">
                <div style="width:48px;height:48px;border-radius:50%;background:${avatarColor};display:flex;align-items:center;justify-content:center;color:#fff;font-size:16px;font-weight:700;flex-shrink:0;box-shadow:0 0 0 3px ${avatarColor}22;">${initials}</div>
                <div>
                  <p style="font-size:.9375rem;font-weight:700;color:#0f172a;margin:0 0 2px;">${escHtml(authorName)}</p>
                  ${roleDetail ? `<p style="font-size:.8125rem;color:#64748b;margin:0 0 2px;">${escHtml(roleDetail)}</p>` : ''}
                  <p style="font-size:.75rem;color:#94a3b8;margin:0;">${timeAgo(post.created_at)}</p>
                </div>
              </div>
              <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;justify-content:flex-end;">
                ${badge.label ? `<span class="post-type-badge ${badge.cls}" style="white-space:nowrap;">${badge.icon ? badge.icon + ' ' : ''}${badge.label}</span>` : ''}
                ${expiryBadge}
              </div>
            </div>

            <!-- Title -->
            ${post.title ? `<h1 style="font-size:1.25rem;font-weight:800;color:#0f172a;margin:0 0 12px;line-height:1.35;letter-spacing:-.01em;">${escHtml(post.title)}</h1>` : ''}

            <!-- Content -->
            <p style="font-size:.9375rem;color:#374151;line-height:1.8;margin:0 0 16px;white-space:pre-line;">${escHtml(post.content)}</p>

            <!-- Job detail section (inline in main card) -->
            ${jobDetailHtml}

            <!-- Session detail section -->
            ${sessionDetailHtml}

            <!-- Tags -->
            ${tagsHtml ? `<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:16px;">${tagsHtml}</div>` : ''}

            <!-- Interaction bar -->
            <div style="display:flex;align-items:center;gap:2px;padding-top:14px;border-top:1px solid #f1f5f9;">
              <button class="action-btn ${post.is_liked ? 'liked' : ''}" id="pd-like-btn" onclick="pdToggleLike(${post.id}, this)">
                <svg width="17" height="17" fill="${post.is_liked ? 'currentColor' : 'none'}" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"/>
                </svg>
                <span id="pd-like-count">${post.likes_count || 0}</span>
              </button>
              <button class="action-btn" onclick="pdShare(${post.id})">
                <svg width="17" height="17" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"/>
                </svg>
                Share
              </button>
              <button class="action-btn ${post.is_saved ? 'saved' : ''}" id="pd-save-btn" onclick="pdToggleSave(${post.id}, this)" style="margin-left:auto;">
                <svg width="17" height="17" fill="${post.is_saved ? 'currentColor' : 'none'}" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"/>
                </svg>
                <span>${post.is_saved ? 'Saved' : 'Save'}</span>
              </button>
            </div>
          </div>
        </div>

        <!-- Comments card -->
        <div style="background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:24px;box-shadow:0 1px 6px rgba(0,0,0,.05);">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:20px;">
            <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="#2563eb" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/>
            </svg>
            <h2 style="font-size:1rem;font-weight:700;color:#0f172a;margin:0;">
              Comments <span id="pd-comment-count" style="font-size:.875rem;color:#94a3b8;font-weight:400;">(${post.comments_count || 0})</span>
            </h2>
          </div>

          <!-- Write comment -->
          <div style="display:flex;gap:10px;margin-bottom:24px;align-items:flex-start;">
            <div id="pd-user-avatar" style="width:36px;height:36px;border-radius:50%;background:#2563eb;display:flex;align-items:center;justify-content:center;color:#fff;font-size:12px;font-weight:700;flex-shrink:0;margin-top:2px;">?</div>
            <div style="flex:1;">
              <textarea id="pd-comment-input" placeholder="Write a thoughtful comment… (Ctrl+Enter to post)"
                style="width:100%;padding:12px 14px;font-size:.875rem;border:1.5px solid #e2e8f0;border-radius:12px;outline:none;resize:none;min-height:80px;font-family:inherit;box-sizing:border-box;transition:border-color .15s;line-height:1.6;"
                onkeydown="if(event.ctrlKey&&event.key==='Enter')pdSubmitComment()"
                onfocus="this.style.borderColor='#2563eb'" onblur="this.style.borderColor='#e2e8f0'"></textarea>
              <div style="display:flex;justify-content:flex-end;margin-top:8px;">
                <button onclick="pdSubmitComment()"
                  style="padding:8px 20px;font-size:.875rem;font-weight:600;color:#fff;background:#2563eb;border:none;border-radius:9px;cursor:pointer;transition:background .15s;"
                  onmouseover="this.style.background='#1d4ed8'" onmouseout="this.style.background='#2563eb'">
                  Post Comment
                </button>
              </div>
            </div>
          </div>

          <!-- List -->
          <div id="pd-comments-list"></div>
        </div>

      </div><!-- end left col -->

      <!-- ═══ RIGHT / ACTION PANEL ═══ -->
      ${hasActionPanel ? `<div style="${rightColStyle}" id="pd-action-col">${actionPanelHtml}</div>` : ''}

    </div>`;

    // Set user avatar
    setTimeout(() => {
        const av = document.getElementById('pd-user-avatar');
        if (av && _currentUser) {
            const ini = ((_currentUser.first_name?.[0]||'') + (_currentUser.last_name?.[0]||'')).toUpperCase() || '?';
            av.textContent = ini;
            const rc = { alumni: '#534AB7', student: '#2563EB', faculty: '#0F6E56' };
            av.style.background = rc[_currentUser.role] || '#2563EB';
        }
    }, 0);

    pdLoadComments();
}

// ── Job detail section (inside post card) ─────────────────────
function buildJobDetailSection(post) {
    const skills = post.required_skills || [];
    if (!post.company_name && !post.job_role && !post.location && !post.salary_range && !skills.length) return '';

    const skillsHtml = skills.map(s =>
        `<span style="padding:4px 12px;font-size:.75rem;background:#eff6ff;color:#2563eb;border-radius:9999px;border:1px solid #bfdbfe;font-weight:500;">${escHtml(s)}</span>`
    ).join('');

    const infoItems = [
        post.company_name && `<div style="display:flex;align-items:center;gap:10px;padding:10px 14px;background:#f8fafc;border-radius:10px;border:1px solid #e2e8f0;">
            <span style="font-size:1.125rem;">🏢</span>
            <div><p style="font-size:.6875rem;color:#94a3b8;margin:0 0 1px;text-transform:uppercase;letter-spacing:.05em;font-weight:500;">Company</p>
            <p style="font-size:.875rem;font-weight:700;color:#0f172a;margin:0;">${escHtml(post.company_name)}</p></div>
        </div>`,
        post.job_role && `<div style="display:flex;align-items:center;gap:10px;padding:10px 14px;background:#f8fafc;border-radius:10px;border:1px solid #e2e8f0;">
            <span style="font-size:1.125rem;">💼</span>
            <div><p style="font-size:.6875rem;color:#94a3b8;margin:0 0 1px;text-transform:uppercase;letter-spacing:.05em;font-weight:500;">Role</p>
            <p style="font-size:.875rem;font-weight:600;color:#0f172a;margin:0;">${escHtml(post.job_role)}</p></div>
        </div>`,
        post.location && `<div style="display:flex;align-items:center;gap:10px;padding:10px 14px;background:#f8fafc;border-radius:10px;border:1px solid #e2e8f0;">
            <span style="font-size:1.125rem;">📍</span>
            <div><p style="font-size:.6875rem;color:#94a3b8;margin:0 0 1px;text-transform:uppercase;letter-spacing:.05em;font-weight:500;">Location</p>
            <p style="font-size:.875rem;color:#374151;font-weight:500;margin:0;">${escHtml(post.location)}</p></div>
        </div>`,
        post.salary_range && `<div style="display:flex;align-items:center;gap:10px;padding:10px 14px;background:#f8fafc;border-radius:10px;border:1px solid #e2e8f0;">
            <span style="font-size:1.125rem;">💰</span>
            <div><p style="font-size:.6875rem;color:#94a3b8;margin:0 0 1px;text-transform:uppercase;letter-spacing:.05em;font-weight:500;">Salary</p>
            <p style="font-size:.875rem;color:#374151;font-weight:500;margin:0;">${escHtml(post.salary_range)}</p></div>
        </div>`,
    ].filter(Boolean);

    return `<div style="border:1.5px solid #e2e8f0;border-radius:12px;padding:18px;margin-bottom:16px;background:#fafbfc;">
      <p style="font-size:.75rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.08em;margin:0 0 14px;display:flex;align-items:center;gap:6px;">
        <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>
        Job Details
      </p>
      <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:10px;${skillsHtml ? 'margin-bottom:14px;' : ''}">${infoItems.join('')}</div>
      ${skillsHtml ? `<div>
        <p style="font-size:.6875rem;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.06em;margin:0 0 8px;">Required Skills</p>
        <div style="display:flex;flex-wrap:wrap;gap:6px;">${skillsHtml}</div>
      </div>` : ''}
    </div>`;
}

// ── Session detail section ────────────────────────────────────
function buildSessionDetailSection(post) {
    const dateStr = post.session_date
        ? new Date(post.session_date).toLocaleString('en-IN', { weekday:'long', day:'numeric', month:'long', year:'numeric', hour:'2-digit', minute:'2-digit' })
        : '';

    const items = [
        dateStr && `<div style="display:flex;align-items:center;gap:10px;padding:10px 14px;background:#fdf4ff;border-radius:10px;border:1px solid #e9d5ff;">
            <span style="font-size:1.125rem;">📅</span>
            <div><p style="font-size:.6875rem;color:#7e22ce;margin:0 0 1px;text-transform:uppercase;letter-spacing:.05em;font-weight:600;">Date &amp; Time</p>
            <p style="font-size:.8125rem;font-weight:600;color:#0f172a;margin:0;">${dateStr}</p></div>
        </div>`,
        post.session_duration && `<div style="display:flex;align-items:center;gap:10px;padding:10px 14px;background:#fdf4ff;border-radius:10px;border:1px solid #e9d5ff;">
            <span style="font-size:1.125rem;">⏱</span>
            <div><p style="font-size:.6875rem;color:#7e22ce;margin:0 0 1px;text-transform:uppercase;letter-spacing:.05em;font-weight:600;">Duration</p>
            <p style="font-size:.875rem;font-weight:600;color:#0f172a;margin:0;">${post.session_duration} minutes</p></div>
        </div>`,
        (post.session_price !== null && post.session_price !== undefined) && `<div style="display:flex;align-items:center;gap:10px;padding:10px 14px;background:#fdf4ff;border-radius:10px;border:1px solid #e9d5ff;">
            <span style="font-size:1.125rem;">💰</span>
            <div><p style="font-size:.6875rem;color:#7e22ce;margin:0 0 1px;text-transform:uppercase;letter-spacing:.05em;font-weight:600;">Price</p>
            <p style="font-size:.875rem;font-weight:600;color:#0f172a;margin:0;">${post.session_price == 0 ? 'Free' : '₹' + post.session_price + ' / seat'}</p></div>
        </div>`,
        post.max_seats && `<div style="display:flex;align-items:center;gap:10px;padding:10px 14px;background:#fdf4ff;border-radius:10px;border:1px solid #e9d5ff;">
            <span style="font-size:1.125rem;">👥</span>
            <div><p style="font-size:.6875rem;color:#7e22ce;margin:0 0 1px;text-transform:uppercase;letter-spacing:.05em;font-weight:600;">Seats</p>
            <p style="font-size:.875rem;font-weight:600;color:#0f172a;margin:0;">${post.max_seats} seats</p></div>
        </div>`,
    ].filter(Boolean);

    return `<div style="border:1.5px solid #e9d5ff;border-radius:12px;padding:18px;margin-bottom:16px;background:#fdf4ff20;">
      <p style="font-size:.75rem;font-weight:700;color:#7e22ce;text-transform:uppercase;letter-spacing:.08em;margin:0 0 14px;display:flex;align-items:center;gap:6px;">
        <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
        Session Details
      </p>
      <div style="display:grid;grid-template-columns:repeat(2,1fr);gap:10px;">${items.join('')}</div>
    </div>`;
}

// ── Action panel (right column) ───────────────────────────────
function buildActionPanel(post) {
    if (post.post_type === 'referral') return buildReferralPanel(post);
    if (post.post_type === 'job')      return buildJobPanel(post);
    if (post.post_type === 'session')  return buildSessionPanel(post);
    return '';
}

// ── Referral action panel ─────────────────────────────────────
function buildReferralPanel(post) {
    const r = post.referral_data;
    if (!r || !r.referral_id) return '';

    const userRole = _currentUser ? _currentUser.role : null;
    if (!userRole) return '';

    // Owner panel
    if (userRole !== 'student') {
        if (post.author && _currentUser && post.author.id === _currentUser.id) {
            return `<div style="background:#fff;border:1.5px solid #e2e8f0;border-radius:16px;overflow:hidden;box-shadow:0 1px 6px rgba(0,0,0,.05);">
              <div style="padding:16px 18px;background:linear-gradient(135deg,#7c3aed,#6d28d9);color:#fff;">
                <p style="font-size:.75rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;margin:0 0 4px;opacity:.85;">Your Referral</p>
                <p style="font-size:1rem;font-weight:700;margin:0;">${escHtml(r.job_title || post.title || 'Job Opening')}</p>
              </div>
              <div style="padding:18px;">
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px;">
                  <div style="text-align:center;padding:12px;background:#f5f3ff;border-radius:10px;">
                    <p style="font-size:1.5rem;font-weight:800;color:#7c3aed;margin:0;">${r.total_applications || 0}</p>
                    <p style="font-size:.75rem;color:#64748b;margin:4px 0 0;">Applicants</p>
                  </div>
                  <div style="text-align:center;padding:12px;background:#f0fdf4;border-radius:10px;">
                    <p style="font-size:1.5rem;font-weight:800;color:#16a34a;margin:0;">${r.slots_remaining || 0}</p>
                    <p style="font-size:.75rem;color:#64748b;margin:4px 0 0;">Slots Left</p>
                  </div>
                </div>
                <a href="/referrals/${r.referral_id}/manage/"
                   style="display:flex;align-items:center;justify-content:center;gap:6px;width:100%;padding:12px;background:#7c3aed;color:#fff;border-radius:10px;text-decoration:none;font-size:.875rem;font-weight:700;box-sizing:border-box;transition:background .15s;"
                   onmouseover="this.style.background='#6d28d9'" onmouseout="this.style.background='#7c3aed'">
                  Manage Applications →
                </a>
              </div>
            </div>`;
        }
        return '';
    }

    // Student panel
    const matchScore = r.student_match_score || 0;
    const hasApplied = r.student_has_applied;
    const slotsLeft  = r.slots_remaining;
    const isActive   = r.status === 'active';
    const canApply   = matchScore >= 40;

    const scoreColor = matchScore >= 80 ? '#16A34A' : matchScore >= 60 ? '#2563EB' : matchScore >= 40 ? '#D97706' : '#EF4444';
    const scoreBg    = matchScore >= 80 ? '#F0FDF4' : matchScore >= 60 ? '#EFF6FF' : matchScore >= 40 ? '#FFFBEB' : '#FEF2F2';
    const scoreBorder= matchScore >= 80 ? '#bbf7d0' : matchScore >= 60 ? '#bfdbfe' : matchScore >= 40 ? '#fde68a' : '#fecaca';

    const deadlineStr = r.deadline
        ? new Date(r.deadline).toLocaleDateString('en-IN', { day:'numeric', month:'short', year:'numeric' })
        : '';

    // Score ring visual
    const circumference = 2 * Math.PI * 20; // r=20
    const offset = circumference - (matchScore / 100) * circumference;

    const scoreRing = `
    <div style="display:flex;flex-direction:column;align-items:center;padding:20px 0 16px;">
      <div style="position:relative;width:80px;height:80px;">
        <svg width="80" height="80" viewBox="0 0 48 48">
          <circle cx="24" cy="24" r="20" fill="none" stroke="#e2e8f0" stroke-width="4"/>
          <circle cx="24" cy="24" r="20" fill="none" stroke="${scoreColor}" stroke-width="4"
            stroke-dasharray="${circumference.toFixed(1)}"
            stroke-dashoffset="${offset.toFixed(1)}"
            stroke-linecap="round"
            transform="rotate(-90 24 24)"/>
        </svg>
        <div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;">
          <span style="font-size:1.125rem;font-weight:800;color:${scoreColor};">${matchScore}%</span>
        </div>
      </div>
      <p style="font-size:.8125rem;font-weight:600;color:#64748b;margin:8px 0 0;">Skill Match</p>
    </div>`;

    const statsRow = `
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;padding:0 18px 16px;">
      <div style="text-align:center;padding:10px;background:#f8fafc;border-radius:10px;border:1px solid #e2e8f0;">
        <p style="font-size:1.125rem;font-weight:800;color:#0f172a;margin:0;">${slotsLeft}</p>
        <p style="font-size:.6875rem;color:#64748b;margin:2px 0 0;">Slots Left</p>
      </div>
      <div style="text-align:center;padding:10px;background:#f8fafc;border-radius:10px;border:1px solid #e2e8f0;">
        <p style="font-size:.875rem;font-weight:700;color:#0f172a;margin:0;">${deadlineStr || '—'}</p>
        <p style="font-size:.6875rem;color:#64748b;margin:2px 0 0;">Deadline</p>
      </div>
    </div>`;

    // Already applied
    if (hasApplied) {
        return `<div style="background:#fff;border:1.5px solid #e2e8f0;border-radius:16px;overflow:hidden;box-shadow:0 1px 6px rgba(0,0,0,.05);">
          <div style="padding:16px 18px;background:linear-gradient(135deg,#16a34a,#15803d);color:#fff;">
            <p style="font-size:.75rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;margin:0 0 4px;opacity:.85;">Application</p>
            <p style="font-size:1rem;font-weight:700;margin:0;">Already Applied ✓</p>
          </div>
          ${scoreRing}${statsRow}
          <div style="padding:0 18px 18px;">
            <div style="padding:12px 14px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;margin-bottom:12px;">
              <p style="font-size:.8125rem;color:#15803d;font-weight:500;margin:0;">Your application is under review. You'll be notified of any updates.</p>
            </div>
            <a href="/referrals/my-applications/"
               style="display:flex;align-items:center;justify-content:center;gap:6px;width:100%;padding:12px;background:#0f172a;color:#fff;border-radius:10px;text-decoration:none;font-size:.875rem;font-weight:700;box-sizing:border-box;"
               onmouseover="this.style.background='#1e293b'" onmouseout="this.style.background='#0f172a'">
              Track Application →
            </a>
          </div>
        </div>`;
    }

    // Slots full or inactive
    if (!isActive || slotsLeft === 0) {
        return `<div style="background:#fff;border:1.5px solid #e2e8f0;border-radius:16px;overflow:hidden;box-shadow:0 1px 6px rgba(0,0,0,.05);">
          <div style="padding:16px 18px;background:linear-gradient(135deg,#64748b,#475569);color:#fff;">
            <p style="font-size:.75rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;margin:0 0 4px;opacity:.85;">Status</p>
            <p style="font-size:1rem;font-weight:700;margin:0;">Applications Closed</p>
          </div>
          ${scoreRing}
          <div style="padding:0 18px 18px;">
            <button disabled style="width:100%;padding:12px;background:#f1f5f9;color:#94a3b8;border:none;border-radius:10px;font-size:.875rem;font-weight:600;cursor:not-allowed;">All Slots Filled</button>
          </div>
        </div>`;
    }

    // Low match
    if (!canApply) {
        return `<div style="background:#fff;border:1.5px solid #e2e8f0;border-radius:16px;overflow:hidden;box-shadow:0 1px 6px rgba(0,0,0,.05);">
          <div style="padding:16px 18px;background:linear-gradient(135deg,#d97706,#b45309);color:#fff;">
            <p style="font-size:.75rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;margin:0 0 4px;opacity:.85;">Skill Match</p>
            <p style="font-size:1rem;font-weight:700;margin:0;">Below Threshold</p>
          </div>
          ${scoreRing}${statsRow}
          <div style="padding:0 18px 18px;">
            <div style="padding:12px 14px;background:#fffbeb;border:1px solid #fde68a;border-radius:10px;margin-bottom:12px;">
              <p style="font-size:.8125rem;color:#92400e;margin:0;">Need 40%+ match to apply. Update your profile skills to improve your score.</p>
            </div>
            <a href="/profile/student/"
               style="display:flex;align-items:center;justify-content:center;gap:6px;width:100%;padding:12px;background:#d97706;color:#fff;border-radius:10px;text-decoration:none;font-size:.875rem;font-weight:700;box-sizing:border-box;"
               onmouseover="this.style.background='#b45309'" onmouseout="this.style.background='#d97706'">
              Update Skills →
            </a>
          </div>
        </div>`;
    }

    // Can apply
    return `<div style="background:#fff;border:1.5px solid #e2e8f0;border-radius:16px;overflow:hidden;box-shadow:0 1px 6px rgba(0,0,0,.05);" id="pd-apply-container">
      <div style="padding:16px 18px;background:linear-gradient(135deg,#2563eb,#1d4ed8);color:#fff;">
        <p style="font-size:.75rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;margin:0 0 4px;opacity:.85;">Apply Now</p>
        <p style="font-size:1rem;font-weight:700;margin:0;">${escHtml(r.job_title || post.title || 'Job Opening')}</p>
      </div>
      ${scoreRing}${statsRow}
      <div style="padding:0 18px 18px;" id="pd-apply-form">
        <p style="font-size:.8125rem;font-weight:600;color:#374151;margin:0 0 8px;">Cover Note <span style="color:#94a3b8;font-weight:400;">(optional)</span></p>
        <textarea id="pd-cover-note" placeholder="Briefly explain why you're a great fit…"
          style="width:100%;padding:10px 12px;font-size:.8125rem;border:1.5px solid #e2e8f0;border-radius:10px;outline:none;resize:none;min-height:90px;font-family:inherit;box-sizing:border-box;line-height:1.6;"
          onfocus="this.style.borderColor='#2563eb'" onblur="this.style.borderColor='#e2e8f0'"></textarea>
        <button id="pd-apply-btn" onclick="pdSubmitApply(${r.referral_id})"
          style="width:100%;margin-top:10px;padding:12px;background:#2563eb;color:#fff;border:none;border-radius:10px;font-size:.9375rem;font-weight:700;cursor:pointer;transition:background .15s;"
          onmouseover="this.style.background='#1d4ed8'" onmouseout="this.style.background='#2563eb'">
          Apply Now →
        </button>
      </div>
    </div>`;
}

// ── Job action panel ──────────────────────────────────────────
function buildJobPanel(post) {
    const userRole = _currentUser ? _currentUser.role : null;
    // Alumni and faculty should not see apply buttons on job posts
    if (userRole && userRole !== 'student') return '';

    const author = post.author || {};
    const authorName = ((author.first_name || '') + ' ' + (author.last_name || '')).trim();
    const rd = author.role_detail || {};

    if (post.apply_link) {
        // Already applied — show applied state
        if (post.is_externally_applied) {
            return `<div style="background:#fff;border:1.5px solid #e2e8f0;border-radius:16px;overflow:hidden;box-shadow:0 1px 6px rgba(0,0,0,.05);">
              <div style="padding:16px 18px;background:linear-gradient(135deg,#0f172a,#1e293b);color:#fff;">
                <p style="font-size:.75rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;margin:0 0 4px;opacity:.85;">Job Opportunity</p>
                <p style="font-size:1rem;font-weight:700;margin:0;">${escHtml(post.job_role || post.title || 'Open Position')}</p>
              </div>
              <div style="padding:20px 18px;">
                <div style="display:flex;align-items:center;gap:12px;padding:12px 14px;background:#f8fafc;border-radius:10px;border:1px solid #e2e8f0;margin-bottom:16px;">
                  <div style="width:38px;height:38px;border-radius:9px;background:#e2e8f0;display:flex;align-items:center;justify-content:center;font-size:1.25rem;flex-shrink:0;">🏢</div>
                  <div>
                    <p style="font-size:.875rem;font-weight:700;color:#0f172a;margin:0;">${escHtml(post.company_name || 'Company')}</p>
                    ${post.location ? `<p style="font-size:.75rem;color:#64748b;margin:2px 0 0;">📍 ${escHtml(post.location)}</p>` : ''}
                  </div>
                </div>
                <div id="job-apply-state-${post.id}">
                  <div style="display:flex;align-items:center;gap:10px;padding:12px 14px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;margin-bottom:10px;">
                    <span style="font-size:1.25rem;">✅</span>
                    <div>
                      <p style="font-size:.875rem;font-weight:700;color:#15803d;margin:0;">Application Tracked</p>
                      <p style="font-size:.75rem;color:#64748b;margin:2px 0 0;">You marked this as applied</p>
                    </div>
                  </div>
                  <div style="display:flex;gap:10px;">
                    <a href="${escHtml(post.apply_link)}" target="_blank" rel="noopener"
                       style="flex:1;display:flex;align-items:center;justify-content:center;gap:6px;padding:10px;background:#f8fafc;color:#374151;border:1px solid #e2e8f0;border-radius:10px;text-decoration:none;font-size:.875rem;font-weight:600;">
                      Visit Again ↗
                    </a>
                    <button onclick="unmarkJobApplied(${post.id})"
                      style="padding:10px 14px;background:none;color:#94a3b8;border:1px solid #e2e8f0;border-radius:10px;font-size:.8125rem;cursor:pointer;"
                      onmouseover="this.style.color='#ef4444';this.style.borderColor='#fecaca'" onmouseout="this.style.color='#94a3b8';this.style.borderColor='#e2e8f0'">
                      Not applied
                    </button>
                  </div>
                </div>
              </div>
            </div>`;
        }

        // Not yet applied
        return `<div style="background:#fff;border:1.5px solid #e2e8f0;border-radius:16px;overflow:hidden;box-shadow:0 1px 6px rgba(0,0,0,.05);">
          <div style="padding:16px 18px;background:linear-gradient(135deg,#0f172a,#1e293b);color:#fff;">
            <p style="font-size:.75rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;margin:0 0 4px;opacity:.85;">Job Opportunity</p>
            <p style="font-size:1rem;font-weight:700;margin:0;">${escHtml(post.job_role || post.title || 'Open Position')}</p>
          </div>
          <div style="padding:20px 18px;">
            <div style="display:flex;align-items:center;gap:12px;padding:12px 14px;background:#f8fafc;border-radius:10px;border:1px solid #e2e8f0;margin-bottom:16px;">
              <div style="width:38px;height:38px;border-radius:9px;background:#e2e8f0;display:flex;align-items:center;justify-content:center;font-size:1.25rem;flex-shrink:0;">🏢</div>
              <div>
                <p style="font-size:.875rem;font-weight:700;color:#0f172a;margin:0;">${escHtml(post.company_name || 'Company')}</p>
                ${post.location ? `<p style="font-size:.75rem;color:#64748b;margin:2px 0 0;">📍 ${escHtml(post.location)}</p>` : ''}
              </div>
            </div>
            <div id="job-apply-state-${post.id}">
              <a href="${escHtml(post.apply_link)}" target="_blank" rel="noopener"
                 onclick="showDidYouApplyPopup(${post.id}, event)"
                 style="display:flex;align-items:center;justify-content:center;gap:8px;width:100%;padding:12px;background:#0f172a;color:#fff;border-radius:10px;text-decoration:none;font-size:.9375rem;font-weight:700;box-sizing:border-box;transition:background .15s;"
                 onmouseover="this.style.background='#1e293b'" onmouseout="this.style.background='#0f172a'">
                Apply Now
                <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
                </svg>
              </a>
              <p style="font-size:.75rem;color:#94a3b8;text-align:center;margin:10px 0 0;">Opens on external website</p>
            </div>
          </div>
        </div>`;
    }

    // No apply link — show poster profile
    return `<div style="background:#fff;border:1.5px solid #e2e8f0;border-radius:16px;overflow:hidden;box-shadow:0 1px 6px rgba(0,0,0,.05);">
      <div style="padding:16px 18px;background:linear-gradient(135deg,#0f172a,#1e293b);color:#fff;">
        <p style="font-size:.75rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;margin:0 0 4px;opacity:.85;">How to Apply</p>
        <p style="font-size:1rem;font-weight:700;margin:0;">Contact the Poster</p>
      </div>
      <div style="padding:20px 18px;">
        <p style="font-size:.875rem;color:#374151;margin:0 0 16px;line-height:1.6;">
          Reach out to <strong>${escHtml(authorName)}</strong>${rd.company ? ` at <strong>${escHtml(rd.company)}</strong>` : ''} directly to express your interest.
        </p>
        <a href="/profile/${author.role || 'alumni'}/${author.id || ''}/"
           style="display:flex;align-items:center;justify-content:center;gap:6px;width:100%;padding:12px;background:#2563eb;color:#fff;border-radius:10px;text-decoration:none;font-size:.875rem;font-weight:700;box-sizing:border-box;"
           onmouseover="this.style.background='#1d4ed8'" onmouseout="this.style.background='#2563eb'">
          View Profile →
        </a>
      </div>
    </div>`;
}

// ── Session action panel ──────────────────────────────────────
function buildSessionPanel(post) {
    const userRole = _currentUser ? _currentUser.role : null;
    if (!userRole) return '';

    const author = post.author || {};
    const priceLabel = post.session_price == 0 ? 'Free' : post.session_price ? `₹${post.session_price}` : null;

    if (userRole === 'student') {
        if (post.is_enrolled_in_session) {
            return `<div style="background:#fff;border:1.5px solid #e2e8f0;border-radius:16px;overflow:hidden;box-shadow:0 1px 6px rgba(0,0,0,.05);">
              <div style="padding:16px 18px;background:linear-gradient(135deg,#16a34a,#15803d);color:#fff;">
                <p style="font-size:.75rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;margin:0 0 4px;opacity:.85;">Booking</p>
                <p style="font-size:1rem;font-weight:700;margin:0;">You're Enrolled ✓</p>
              </div>
              <div style="padding:20px 18px;">
                <div style="padding:12px 14px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;">
                  <p style="font-size:.875rem;color:#15803d;font-weight:500;margin:0;">Check your bookings for the meeting link and details.</p>
                </div>
                <a href="/sessions/my-bookings/" style="display:flex;align-items:center;justify-content:center;gap:6px;width:100%;margin-top:12px;padding:12px;background:#0f172a;color:#fff;border-radius:10px;text-decoration:none;font-size:.875rem;font-weight:700;box-sizing:border-box;">
                  My Bookings →
                </a>
              </div>
            </div>`;
        }
        if (!post.session_id) return '';
        return `<div style="background:#fff;border:1.5px solid #e2e8f0;border-radius:16px;overflow:hidden;box-shadow:0 1px 6px rgba(0,0,0,.05);">
          <div style="padding:16px 18px;background:linear-gradient(135deg,#7c3aed,#6d28d9);color:#fff;">
            <p style="font-size:.75rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;margin:0 0 4px;opacity:.85;">Mentorship Session</p>
            <p style="font-size:1rem;font-weight:700;margin:0;">${escHtml(post.title || 'Live Session')}</p>
          </div>
          <div style="padding:20px 18px;">
            ${priceLabel ? `<div style="display:flex;align-items:center;justify-content:space-between;padding:12px 14px;background:#f5f3ff;border-radius:10px;border:1px solid #ddd6fe;margin-bottom:16px;">
              <span style="font-size:.875rem;color:#5b21b6;font-weight:500;">Session Fee</span>
              <span style="font-size:1.125rem;font-weight:800;color:#5b21b6;">${priceLabel}</span>
            </div>` : ''}
            <a href="/sessions/${post.session_id}/"
               style="display:flex;align-items:center;justify-content:center;gap:8px;width:100%;padding:12px;background:#7c3aed;color:#fff;border-radius:10px;text-decoration:none;font-size:.9375rem;font-weight:700;box-sizing:border-box;transition:background .15s;"
               onmouseover="this.style.background='#6d28d9'" onmouseout="this.style.background='#7c3aed'">
              Book Session →
            </a>
            <p style="font-size:.75rem;color:#94a3b8;text-align:center;margin:10px 0 0;">Secure payment via Razorpay</p>
          </div>
        </div>`;
    }

    if ((userRole === 'alumni' || userRole === 'faculty') && post.author && _currentUser && post.author.id === _currentUser.id && post.session_id) {
        return `<div style="background:#fff;border:1.5px solid #e2e8f0;border-radius:16px;overflow:hidden;box-shadow:0 1px 6px rgba(0,0,0,.05);">
          <div style="padding:16px 18px;background:linear-gradient(135deg,#0d9488,#0f766e);color:#fff;">
            <p style="font-size:.75rem;font-weight:600;letter-spacing:.06em;text-transform:uppercase;margin:0 0 4px;opacity:.85;">Your Session</p>
            <p style="font-size:1rem;font-weight:700;margin:0;">Manage &amp; Track</p>
          </div>
          <div style="padding:20px 18px;">
            <a href="/sessions/hosting/"
               style="display:flex;align-items:center;justify-content:center;gap:6px;width:100%;padding:12px;background:#0d9488;color:#fff;border-radius:10px;text-decoration:none;font-size:.875rem;font-weight:700;box-sizing:border-box;"
               onmouseover="this.style.background='#0f766e'" onmouseout="this.style.background='#0d9488'">
              Manage Session →
            </a>
          </div>
        </div>`;
    }
    return '';
}

// ── External job apply tracking ───────────────────────────────

function showDidYouApplyPopup(postId, event) {
    // Link still opens normally — popup appears below Apply Now button after a short delay
    const stateEl = document.getElementById(`job-apply-state-${postId}`);
    if (!stateEl) return;

    // Don't show duplicate popups
    if (document.getElementById(`did-you-apply-popup-${postId}`)) return;

    const popup = document.createElement('div');
    popup.id = `did-you-apply-popup-${postId}`;
    popup.style.cssText = `
        background:#fff;border:1.5px solid #e2e8f0;border-radius:12px;
        padding:16px;margin-top:12px;box-shadow:0 4px 16px rgba(0,0,0,.1);
        animation:fadeInUp .25s ease;
    `;
    popup.innerHTML = `
        <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px;margin-bottom:12px;">
            <div>
                <p style="font-size:.9375rem;font-weight:700;color:#0f172a;margin:0 0 3px;">Did you apply?</p>
                <p style="font-size:.8125rem;color:#64748b;margin:0;">Let us know and we'll help you track your application.</p>
            </div>
            <button onclick="document.getElementById('did-you-apply-popup-${postId}').remove()"
                style="background:none;border:none;cursor:pointer;color:#94a3b8;font-size:1.1rem;padding:0;flex-shrink:0;"
                onmouseover="this.style.color='#475569'" onmouseout="this.style.color='#94a3b8'">✕</button>
        </div>
        <div style="display:flex;gap:10px;">
            <button onclick="markJobApplied(${postId})"
                style="flex:1;padding:10px;background:#0f172a;color:#fff;border:none;border-radius:9px;font-size:.875rem;font-weight:700;cursor:pointer;transition:background .15s;"
                onmouseover="this.style.background='#1e293b'" onmouseout="this.style.background='#0f172a'">
                Yes, I applied
            </button>
            <button onclick="document.getElementById('did-you-apply-popup-${postId}').remove()"
                style="flex:1;padding:10px;background:#f8fafc;color:#374151;border:1px solid #e2e8f0;border-radius:9px;font-size:.875rem;font-weight:600;cursor:pointer;">
                No, not yet
            </button>
        </div>`;

    stateEl.appendChild(popup);
}

async function markJobApplied(postId) {
    const res = await apiPost(`/api/feed/${postId}/mark-applied/`, {});
    if (res.ok) {
        showToast('Application tracked! ✅', 'success');
        // Replace the whole apply state section with "Applied" UI
        const stateEl = document.getElementById(`job-apply-state-${postId}`);
        if (stateEl) {
            stateEl.innerHTML = `
                <div style="display:flex;align-items:center;gap:10px;padding:12px 14px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;margin-bottom:10px;">
                    <span style="font-size:1.25rem;">✅</span>
                    <div>
                        <p style="font-size:.875rem;font-weight:700;color:#15803d;margin:0;">Application Tracked</p>
                        <p style="font-size:.75rem;color:#64748b;margin:2px 0 0;">You marked this as applied</p>
                    </div>
                </div>
                <button onclick="unmarkJobApplied(${postId})"
                    style="padding:8px 14px;background:none;color:#94a3b8;border:1px solid #e2e8f0;border-radius:9px;font-size:.8125rem;cursor:pointer;"
                    onmouseover="this.style.color='#ef4444';this.style.borderColor='#fecaca'" onmouseout="this.style.color='#94a3b8';this.style.borderColor='#e2e8f0'">
                    Not applied
                </button>`;
        }
    } else {
        showToast('Could not track — please try again.', 'error');
    }
}

async function unmarkJobApplied(postId) {
    const res = await apiFetch(`/api/feed/${postId}/mark-applied/`, { method: 'DELETE' });
    if (res.ok || res.status === 204) {
        showToast('Removed from applied', 'info');
        // Restore the Apply Now button
        const stateEl = document.getElementById(`job-apply-state-${postId}`);
        if (stateEl) {
            // Re-load the post to get fresh apply_link
            const postRes = await apiGet(`/api/feed/${postId}/`);
            if (postRes.ok && postRes.data.apply_link) {
                stateEl.innerHTML = `
                    <a href="${escHtml(postRes.data.apply_link)}" target="_blank" rel="noopener"
                       onclick="showDidYouApplyPopup(${postId}, event)"
                       style="display:flex;align-items:center;justify-content:center;gap:8px;width:100%;padding:12px;background:#0f172a;color:#fff;border-radius:10px;text-decoration:none;font-size:.9375rem;font-weight:700;box-sizing:border-box;"
                       onmouseover="this.style.background='#1e293b'" onmouseout="this.style.background='#0f172a'">
                        Apply Now
                        <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                            <path stroke-linecap="round" stroke-linejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
                        </svg>
                    </a>
                    <p style="font-size:.75rem;color:#94a3b8;text-align:center;margin:10px 0 0;">Opens on external website</p>`;
            }
        }
    }
}

// ── Apply ─────────────────────────────────────────────────────
async function pdSubmitApply(referralId) {
    const btn = document.getElementById('pd-apply-btn');
    const coverNote = document.getElementById('pd-cover-note')?.value?.trim() || '';
    if (btn) { btn.textContent = 'Submitting…'; btn.disabled = true; btn.style.background = '#1d4ed8'; }

    const res = await apiPost(`/api/referrals/${referralId}/apply/`, { cover_note: coverNote });

    if (res.ok) {
        const container = document.getElementById('pd-apply-container');
        if (container) {
            const header = container.querySelector('div[style*="linear-gradient"]');
            if (header) header.style.background = 'linear-gradient(135deg,#16a34a,#15803d)';
            const form = document.getElementById('pd-apply-form');
            if (form) {
                form.innerHTML = `
                <div style="text-align:center;padding:8px 0 8px;">
                  <div style="font-size:2.5rem;margin-bottom:8px;">🎉</div>
                  <p style="font-size:.9375rem;font-weight:700;color:#15803d;margin:0 0 6px;">Application Submitted!</p>
                  <p style="font-size:.8125rem;color:#64748b;margin:0 0 16px;">You'll be notified of any status updates.</p>
                  <a href="/referrals/my-applications/"
                     style="display:inline-flex;align-items:center;gap:6px;padding:10px 20px;background:#0f172a;color:#fff;border-radius:10px;text-decoration:none;font-size:.875rem;font-weight:700;">
                    Track Application →
                  </a>
                </div>`;
            }
        }
        showToast('Application submitted!', 'success');
    } else {
        if (btn) { btn.textContent = 'Apply Now →'; btn.disabled = false; btn.style.background = '#2563eb'; }
        const error = res.data?.error || res.data?.detail || 'Application failed. Please try again.';
        showToast(error, 'error');
    }
}

// ── Like / Save / Share ───────────────────────────────────────
async function pdToggleLike(postId, btn) {
    const countEl  = document.getElementById('pd-like-count');
    const wasLiked = btn.classList.contains('liked');
    const prev     = parseInt(countEl?.textContent || '0');
    btn.classList.toggle('liked', !wasLiked);
    const svg = btn.querySelector('svg');
    if (svg) svg.setAttribute('fill', !wasLiked ? 'currentColor' : 'none');
    if (countEl) countEl.textContent = wasLiked ? Math.max(0, prev - 1) : prev + 1;

    const res = await apiPost(`/api/feed/${postId}/like/`, {});
    if (!res.ok) {
        btn.classList.toggle('liked', wasLiked);
        if (svg) svg.setAttribute('fill', wasLiked ? 'currentColor' : 'none');
        if (countEl) countEl.textContent = prev;
        showToast('Failed to like post', 'error');
        return;
    }
    if (countEl) countEl.textContent = res.data.likes_count;
    if (svg) svg.setAttribute('fill', res.data.liked ? 'currentColor' : 'none');
    btn.classList.toggle('liked', res.data.liked);
}

async function pdToggleSave(postId, btn) {
    const wasSaved = btn.classList.contains('saved');
    btn.classList.toggle('saved', !wasSaved);
    const svg  = btn.querySelector('svg');
    const span = btn.querySelector('span');
    if (svg) svg.setAttribute('fill', !wasSaved ? 'currentColor' : 'none');
    if (span) span.textContent = !wasSaved ? 'Saved' : 'Save';

    const res = await apiPost(`/api/feed/${postId}/save/`, {});
    if (!res.ok) {
        btn.classList.toggle('saved', wasSaved);
        if (svg) svg.setAttribute('fill', wasSaved ? 'currentColor' : 'none');
        if (span) span.textContent = wasSaved ? 'Saved' : 'Save';
        showToast('Failed to save post', 'error');
        return;
    }
    const saved = res.data.saved;
    btn.classList.toggle('saved', saved);
    if (svg) svg.setAttribute('fill', saved ? 'currentColor' : 'none');
    if (span) span.textContent = saved ? 'Saved' : 'Save';
    showToast(saved ? 'Post saved' : 'Post unsaved', 'success');
}

function pdShare(postId) {
    const url = `${window.location.origin}/feed/${postId}/`;
    if (navigator.clipboard) {
        navigator.clipboard.writeText(url).then(() => showToast('Link copied!', 'success'));
    } else {
        showToast('Link: ' + url, 'info');
    }
}

// ── Comments ──────────────────────────────────────────────────
async function pdLoadComments() {
    const listEl = document.getElementById('pd-comments-list');
    if (!listEl) return;
    listEl.innerHTML = '<p style="font-size:.875rem;color:#94a3b8;padding:4px 0;">Loading…</p>';

    const res = await apiGet(`/api/feed/${_postId}/comments/?page_size=50`);
    if (!res.ok) { listEl.innerHTML = ''; return; }

    const comments = res.data.results || [];
    listEl.innerHTML = '';
    if (!comments.length) {
        listEl.innerHTML = `<div style="text-align:center;padding:24px 0;">
          <div style="font-size:2rem;margin-bottom:8px;">💬</div>
          <p style="font-size:.875rem;color:#94a3b8;margin:0;">No comments yet. Start the conversation!</p>
        </div>`;
        return;
    }
    comments.forEach(c => listEl.appendChild(pdRenderComment(c)));
}

function pdRenderComment(c) {
    const wrap = document.createElement('div');
    wrap.style.cssText = 'display:flex;gap:12px;margin-bottom:16px;';
    const author = c.author || {};
    const ini    = ((author.first_name?.[0]||'')+(author.last_name?.[0]||'')).toUpperCase()||'?';
    const name   = ((author.first_name||'')+' '+(author.last_name||'')).trim()||'User';
    const roleColors = { alumni:'#534AB7', student:'#2563EB', faculty:'#0F6E56' };
    const color  = roleColors[author.role] || '#2563EB';
    const rd     = author.role_detail || {};
    let sub = '';
    if (author.role==='alumni' && rd.company) sub = `${rd.designation||''} @ ${rd.company}`.trim().replace(/^@ /,'');
    else if (author.role==='faculty') sub = rd.department || 'Faculty';
    else if (author.role==='student') sub = author.college || 'Student';

    wrap.innerHTML = `
    <div style="width:36px;height:36px;border-radius:50%;background:${color};display:flex;align-items:center;justify-content:center;color:#fff;font-size:12px;font-weight:700;flex-shrink:0;margin-top:2px;">${ini}</div>
    <div style="flex:1;">
      <div style="background:#f8fafc;border:1px solid #f1f5f9;border-radius:12px;padding:12px 14px;">
        <div style="display:flex;align-items:baseline;gap:8px;flex-wrap:wrap;margin-bottom:5px;">
          <span style="font-size:.875rem;font-weight:700;color:#0f172a;">${escHtml(name)}</span>
          ${sub ? `<span style="font-size:.75rem;color:#94a3b8;">${escHtml(sub)}</span>` : ''}
          <span style="font-size:.75rem;color:#cbd5e1;margin-left:auto;">${timeAgo(c.created_at)}</span>
        </div>
        <p style="font-size:.875rem;color:#374151;margin:0;line-height:1.65;">${escHtml(c.content)}</p>
      </div>
    </div>`;
    return wrap;
}

async function pdSubmitComment() {
    const input = document.getElementById('pd-comment-input');
    if (!input) return;
    const content = input.value.trim();
    if (!content) return;

    const listEl = document.getElementById('pd-comments-list');
    const tempEl = pdRenderComment({ author: _currentUser || {}, content, created_at: new Date().toISOString() });
    tempEl.style.opacity = '0.5';
    if (listEl) listEl.prepend(tempEl);
    input.value = '';

    const res = await apiPost(`/api/feed/${_postId}/comments/`, { content });
    if (!res.ok) {
        tempEl.remove();
        input.value = content;
        showToast(extractErrorMessage(res.error), 'error');
        return;
    }
    tempEl.remove();
    const countEl = document.getElementById('pd-comment-count');
    if (countEl) {
        const prev = parseInt(countEl.textContent.replace(/\D/g,'')) || 0;
        countEl.textContent = `(${prev + 1})`;
    }
    await pdLoadComments();
}

// ── Expiry badge ──────────────────────────────────────────────
function buildDetailExpiryBadge(post) {
    if (!post.expires_at || post.post_type === 'session') return '';
    const diffMs = new Date(post.expires_at).getTime() - Date.now();
    if (diffMs <= 0) return '<span style="padding:4px 12px;font-size:.75rem;font-weight:600;background:#fef2f2;color:#dc2626;border-radius:9999px;">Expired</span>';
    const diffDays  = Math.floor(diffMs / 86400000);
    const diffHours = Math.floor(diffMs / 3600000);
    let label, bg, color;
    if (diffHours < 24)      { label = `⏰ Closes in ${diffHours}h`;                        bg = '#fef2f2'; color = '#dc2626'; }
    else if (diffDays <= 3)  { label = `🔥 ${diffDays} day${diffDays!==1?'s':''} left`;     bg = '#fff7ed'; color = '#c2410c'; }
    else if (diffDays <= 7)  { label = `⏳ ${diffDays} days left`;                           bg = '#fffbeb'; color = '#d97706'; }
    else {
        const d = new Date(post.expires_at).toLocaleDateString('en-IN', { day:'numeric', month:'short', year:'numeric' });
        label = `📅 Open until ${d}`; bg = '#f0fdf4'; color = '#15803d';
    }
    return `<span style="padding:4px 12px;font-size:.75rem;font-weight:600;background:${bg};color:${color};border-radius:9999px;white-space:nowrap;">${label}</span>`;
}

// ── Utils ─────────────────────────────────────────────────────
function escHtml(str) {
    if (!str) return '';
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function timeAgo(dateStr) {
    if (!dateStr) return '';
    const diff = Math.floor((Date.now() - new Date(dateStr)) / 1000);
    if (diff < 60)     return 'just now';
    if (diff < 3600)   return `${Math.floor(diff/60)}m ago`;
    if (diff < 86400)  return `${Math.floor(diff/3600)}h ago`;
    if (diff < 604800) return `${Math.floor(diff/86400)}d ago`;
    return new Date(dateStr).toLocaleDateString('en-IN', { day:'numeric', month:'short', year:'numeric' });
}
