/* ============================================================
   AlumniAI — Feed Page JS
   ============================================================ */

let _feedPage = 1;
let _feedFilter = '';
let _feedTagFilter = '';
let _feedMyPosts = false;
let _feedLoading = false;
let _feedDone = false;
let _currentUser = null;

// ── Init ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  await loadCurrentUser();
  loadFeed(true);
  initInfiniteScroll();
  // Close modal on overlay click
  const overlay = document.getElementById('modal-overlay-feed');
  if (overlay) overlay.addEventListener('click', e => { if (e.target === overlay) closeCreatePostModal(); });
});

async function loadCurrentUser() {
  const res = await apiGet('/api/accounts/me/');
  if (!res.ok) return;
  _currentUser = res.data;

  const initials = ((_currentUser.first_name?.[0] || '') + (_currentUser.last_name?.[0] || '')).toUpperCase() || '?';
  const roleColors = { alumni: '#534AB7', student: '#2563EB', faculty: '#0F6E56' };
  const color = roleColors[_currentUser.role] || '#2563EB';
  const roleBadgeStyles = {
    student: 'background:#fef3c7;color:#92400e;',
    alumni:  'background:#ede9fe;color:#5b21b6;',
    faculty: 'background:#ccfbf1;color:#065f46;',
  };

  // Mini profile card
  const avatarEl = document.getElementById('feed-avatar-circle');
  if (avatarEl) { avatarEl.textContent = initials; avatarEl.style.background = color; }

  const nameEl = document.getElementById('feed-user-name');
  if (nameEl) nameEl.textContent = (_currentUser.first_name + ' ' + _currentUser.last_name).trim() || _currentUser.email;

  const subEl = document.getElementById('feed-user-sub');
  if (subEl) subEl.textContent = _currentUser.college || _currentUser.email || '';

  const roleBadge = document.getElementById('feed-role-badge');
  if (roleBadge) {
    roleBadge.textContent = _currentUser.role.charAt(0).toUpperCase() + _currentUser.role.slice(1);
    roleBadge.style.cssText += roleBadgeStyles[_currentUser.role] || '';
  }

  const profileLink = document.getElementById('feed-profile-link');
  if (profileLink) {
    const links = { student: '/profile/student/', alumni: '/profile/alumni/', faculty: '/profile/faculty/' };
    profileLink.href = links[_currentUser.role] || '#';
  }

  // Create box avatar
  const createAvatar = document.getElementById('create-avatar');
  if (createAvatar) { createAvatar.textContent = initials; createAvatar.style.background = color; }

  // Modal author row
  const cpAvatar = document.getElementById('cp-author-avatar');
  if (cpAvatar) { cpAvatar.textContent = initials; cpAvatar.style.background = color; }
  const cpName = document.getElementById('cp-author-name');
  if (cpName) cpName.textContent = (_currentUser.first_name + ' ' + _currentUser.last_name).trim() || _currentUser.email;
  const cpBadge = document.getElementById('cp-author-badge');
  if (cpBadge) {
    cpBadge.textContent = _currentUser.role.charAt(0).toUpperCase() + _currentUser.role.slice(1);
    cpBadge.style.cssText += roleBadgeStyles[_currentUser.role] || '';
  }

  // Show/hide create box vs student info bar
  const canPost = _currentUser.role === 'alumni' || _currentUser.role === 'faculty';
  const createBox = document.getElementById('create-post-box');
  const infoBar = document.getElementById('student-info-bar');
  if (createBox) createBox.classList.toggle('hidden', !canPost);
  if (infoBar) { infoBar.classList.toggle('hidden', canPost); infoBar.style.display = canPost ? 'none' : 'flex'; }

  // Show "Your Posts" filter for alumni/faculty
  const myPostsSection = document.getElementById('my-posts-section');
  if (myPostsSection && canPost) myPostsSection.classList.remove('hidden');

  // Load completeness
  const compRes = await apiGet('/api/accounts/profile/completeness/');
  if (compRes.ok) {
    const pct = compRes.data.percentage || 0;
    const fill = document.getElementById('feed-completeness-fill');
    const pctEl = document.getElementById('feed-completeness-pct');
    if (fill) { fill.style.width = pct + '%'; fill.style.background = pct >= 80 ? '#22c55e' : pct >= 50 ? '#f97316' : '#ef4444'; }
    if (pctEl) pctEl.textContent = pct + '% complete';
  }
}

// ── Feed loading ──────────────────────────────────────────────
async function loadFeed(reset = false) {
  if (_feedLoading || (_feedDone && !reset)) return;
  if (reset) {
    _feedPage = 1;
    _feedDone = false;
    document.getElementById('feed-container').innerHTML = '';
    document.getElementById('feed-end').classList.add('hidden');
    showFeedSkeleton();
  }
  _feedLoading = true;
  document.getElementById('feed-loader').classList.remove('hidden');

  let url = `/api/feed/?page=${_feedPage}&page_size=10`;
  if (_feedFilter === 'job') url += '&type=job';
  else if (_feedFilter) url += `&type=${_feedFilter}`;
  if (_feedTagFilter) url += `&tag=${encodeURIComponent(_feedTagFilter)}`;
  if (_feedMyPosts) url += '&my_posts=true';

  try {
    const res = await apiGet(url);

    // Always clear skeletons and loader regardless of result
    hideFeedSkeleton();
    document.getElementById('feed-loader').classList.add('hidden');
    _feedLoading = false;

    if (!res.ok) {
      const container = document.getElementById('feed-container');
      if (container && _feedPage === 1) {
        const detail = res.error?.detail || res.error?.error || `HTTP ${res.status}`;
        container.innerHTML = `<div class="post-card" style="text-align:center;padding:40px 20px;">
          <div style="font-size:32px;margin-bottom:12px;">📡</div>
          <p style="font-size:.9375rem;font-weight:500;color:#0f172a;margin:0 0 6px;">Could not load posts</p>
          <p style="font-size:.8125rem;color:#64748b;margin:0 0 16px;">${escHtml(detail)}</p>
          <button onclick="loadFeed(true)" style="padding:8px 20px;background:#2563eb;color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:.875rem;font-weight:600;">Try again</button>
        </div>`;
      }
      console.error('Feed load failed:', res.status, res.error);
      return;
    }

    const posts = res.data.results || [];
    const container = document.getElementById('feed-container');

    if (posts.length === 0 && _feedPage === 1) {
      container.innerHTML = `<div class="post-card text-center py-12">
        <svg style="width:48px;height:48px;color:#cbd5e1;margin:0 auto 12px;display:block;" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z"/>
        </svg>
        <p style="color:#64748b;font-weight:500;margin:0 0 4px;">No posts yet</p>
        <p style="font-size:.875rem;color:#94a3b8;margin:0;">Be the first to share something!</p>
      </div>`;
      return;
    }

    posts.forEach(post => container.appendChild(renderPostCard(post)));

    if (!res.data.next) {
      _feedDone = true;
      if (_feedPage > 1) document.getElementById('feed-end').classList.remove('hidden');
    } else {
      _feedPage++;
    }

  } catch (err) {
    // Catch unexpected JS errors — always remove skeletons
    hideFeedSkeleton();
    document.getElementById('feed-loader').classList.add('hidden');
    _feedLoading = false;
    console.error('loadFeed unexpected error:', err);

    const container = document.getElementById('feed-container');
    if (container && _feedPage === 1) {
      container.innerHTML = `<div class="post-card" style="text-align:center;padding:40px 20px;">
        <p style="font-size:.875rem;color:#64748b;margin:0 0 12px;">Something went wrong loading the feed.</p>
        <button onclick="loadFeed(true)" style="padding:8px 20px;background:#2563eb;color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:.875rem;font-weight:600;">Retry</button>
      </div>`;
    }
  }
}

function showFeedSkeleton() {
  const container = document.getElementById('feed-container');
  container.innerHTML = '';
  for (let i = 0; i < 3; i++) {
    const sk = document.createElement('div');
    sk.className = 'post-card feed-skeleton-card';
    sk.innerHTML = `
      <div style="display:flex;gap:12px;margin-bottom:14px;">
        <div class="skeleton-pulse" style="width:40px;height:40px;border-radius:50%;flex-shrink:0;"></div>
        <div style="flex:1;"><div class="skeleton-pulse" style="height:13px;width:40%;margin-bottom:6px;"></div><div class="skeleton-pulse" style="height:11px;width:25%;"></div></div>
      </div>
      <div class="skeleton-pulse" style="height:13px;width:100%;margin-bottom:8px;"></div>
      <div class="skeleton-pulse" style="height:13px;width:80%;margin-bottom:8px;"></div>
      <div class="skeleton-pulse" style="height:13px;width:60%;"></div>`;
    container.appendChild(sk);
  }
}

function hideFeedSkeleton() {
  document.querySelectorAll('.feed-skeleton-card').forEach(el => el.remove());
}

// ── Render post card ──────────────────────────────────────────
function renderPostCard(post) {
  const card = document.createElement('div');
  card.className = 'post-card';
  card.dataset.postId = post.id;

  const author = post.author || {};
  const initials = ((author.first_name?.[0] || '') + (author.last_name?.[0] || '')).toUpperCase() || '?';
  const roleColors = { alumni: '#534AB7', student: '#2563EB', faculty: '#0F6E56' };
  const avatarColor = roleColors[author.role] || '#94a3b8';
  const authorName = ((author.first_name || '') + ' ' + (author.last_name || '')).trim() || 'Unknown';

  // Role detail line
  let roleDetail = '';
  const rd = author.role_detail || {};
  if (author.role === 'alumni' && rd.company) roleDetail = `${rd.designation || ''} @ ${rd.company}`.trim().replace(/^@ /, '');
  else if (author.role === 'faculty' && rd.department) roleDetail = `${rd.designation || 'Faculty'} · ${rd.department}`;
  else if (author.role === 'student') roleDetail = author.college || '';

  const badgeMap = {
    job:          { cls: 'badge-job',          label: 'Job Opportunity' },
    referral:     { cls: 'badge-referral',      label: 'Job Referral' },
    session:      { cls: 'badge-session',       label: 'Mentorship Session' },
    announcement: { cls: 'badge-announcement',  label: 'Announcement' },
    general:      { cls: '',                    label: '' },
    ad:           { cls: 'badge-ad',            label: 'Ad' },
  };
  const badge = badgeMap[post.post_type] || { cls: 'badge-general', label: post.post_type };

  // Content with "see more"
  const fullContent = post.content || '';
  const truncated = fullContent.length > 300;
  const displayContent = truncated ? fullContent.slice(0, 300) : fullContent;
  const contentHtml = truncated
    ? `<span id="content-short-${post.id}">${escHtml(displayContent)}<span>... <button onclick="expandContent(${post.id})" style="color:#2563eb;background:none;border:none;cursor:pointer;font-size:.875rem;padding:0;">see more</button></span></span>
       <span id="content-full-${post.id}" style="display:none;">${escHtml(fullContent)}</span>`
    : escHtml(fullContent);

  // Tags
  const tagsHtml = (post.tags || []).map(t =>
    `<button onclick="filterByTag('${escHtml(t)}')" style="padding:2px 8px;font-size:.6875rem;background:#f1f5f9;color:#475569;border:none;border-radius:9999px;cursor:pointer;" onmouseover="this.style.background='#dbeafe';this.style.color='#2563eb'" onmouseout="this.style.background='#f1f5f9';this.style.color='#475569'">#${escHtml(t)}</button>`
  ).join('');

  // Job/referral extra
  let extraHtml = '';
  if (post.post_type === 'job' || post.post_type === 'referral') {
    const skills = (post.required_skills || []).slice(0, 4);
    const moreSkills = (post.required_skills || []).length - 4;
    const skillsHtml = skills.map(s => `<span style="padding:2px 8px;font-size:.6875rem;background:#f1f5f9;color:#475569;border-radius:9999px;">${escHtml(s)}</span>`).join('');
    extraHtml = `<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:10px 14px;margin:10px 0;">
      <div style="display:flex;flex-wrap:wrap;gap:8px 16px;align-items:center;">
        ${post.company_name ? `<span style="font-size:.8125rem;font-weight:600;color:#0f172a;">🏢 ${escHtml(post.company_name)}</span>` : ''}
        ${post.job_role ? `<span style="font-size:.8125rem;color:#475569;">💼 ${escHtml(post.job_role)}</span>` : ''}
        ${post.location ? `<span style="font-size:.8125rem;color:#475569;">📍 ${escHtml(post.location)}</span>` : ''}
        ${post.salary_range ? `<span style="font-size:.8125rem;color:#475569;">💰 ${escHtml(post.salary_range)}</span>` : ''}
      </div>
      ${skillsHtml ? `<div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:8px;">${skillsHtml}${moreSkills > 0 ? `<span style="padding:2px 8px;font-size:.6875rem;background:#e2e8f0;color:#64748b;border-radius:9999px;">+${moreSkills} more</span>` : ''}</div>` : ''}`;
      if (post.post_type === 'referral') {
          extraHtml += `<div style="margin-top:12px;border-top:1px solid #e2e8f0;padding-top:12px;">` + renderReferralActionButton(post) + `</div>`;
      } else {
          extraHtml += post.apply_link ? `<div style="margin-top:8px;"><a href="${escHtml(post.apply_link)}" target="_blank" rel="noopener" style="display:inline-flex;align-items:center;gap:4px;padding:6px 14px;background:#2563eb;color:#fff;font-size:.8125rem;font-weight:600;border-radius:8px;text-decoration:none;" onmouseover="this.style.background='#1d4ed8'" onmouseout="this.style.background='#2563eb'">Apply Now →</a></div>` : '';
      }
      extraHtml += `</div>`;
  } else if (post.post_type === 'session') {
    const dateStr = post.session_date ? new Date(post.session_date).toLocaleString('en-IN', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '';
    extraHtml = `<div style="background:#fdf4ff;border:1px solid #e9d5ff;border-radius:8px;padding:10px 14px;margin:10px 0;">
      <div style="display:flex;flex-wrap:wrap;gap:8px 16px;align-items:center;">
        ${dateStr ? `<span style="font-size:.8125rem;color:#6d28d9;">📅 ${dateStr}</span>` : ''}
        ${post.session_duration ? `<span style="font-size:.8125rem;color:#6d28d9;">⏱ ${post.session_duration} min</span>` : ''}
        ${post.session_price !== null && post.session_price !== undefined ? `<span style="font-size:.8125rem;color:#6d28d9;">💰 ${post.session_price == 0 ? 'Free' : '₹' + post.session_price + ' / seat'}</span>` : ''}
        ${post.max_seats ? `<span style="font-size:.8125rem;color:#6d28d9;">👥 ${post.max_seats} seats</span>` : ''}
      </div>`;
      const userRole = _currentUser ? _currentUser.role : 'student';
      const currentUserId = _currentUser ? _currentUser.id : 0;
      const hostId = author ? author.id : null;
      const isOwnSession = (hostId && parseInt(hostId) === parseInt(currentUserId));
      
      let actionBtnHtml = '';
      
      if (userRole === 'student') {
          if (post.is_enrolled_in_session) {
              actionBtnHtml = `<div style="margin-top:8px;"><button disabled style="display:inline-flex;align-items:center;gap:4px;padding:6px 14px;background:#10b981;color:#fff;font-size:.8125rem;font-weight:600;border:none;border-radius:8px;cursor:not-allowed;">Enrolled ✓</button></div>`;
          } else {
              const btnAction = post.session_id ? `window.location.href='/sessions/${post.session_id}/'` : `showToast('Session details unavailable','error')`;
              actionBtnHtml = `<div style="margin-top:8px;"><button onclick="${btnAction}" style="display:inline-flex;align-items:center;gap:4px;padding:6px 14px;background:#7c3aed;color:#fff;font-size:.8125rem;font-weight:600;border:none;border-radius:8px;cursor:pointer;" onmouseover="this.style.background='#6d28d9'" onmouseout="this.style.background='#7c3aed'">Book Session →</button></div>`;
          }
      } else if (userRole === 'alumni' || userRole === 'faculty') {
          if (isOwnSession) {
              actionBtnHtml = `<div style="margin-top:8px;"><button onclick="window.location.href='/sessions/hosting/'" style="display:inline-flex;align-items:center;gap:4px;padding:6px 14px;background:#0d9488;color:#fff;font-size:.8125rem;font-weight:600;border:none;border-radius:8px;cursor:pointer;" onmouseover="this.style.background='#0f766e'" onmouseout="this.style.background='#0d9488'">Manage Session →</button></div>`;
          }
      } else if (userRole === 'admin') {
          const btnAction = post.session_id ? `window.location.href='/sessions/${post.session_id}/'` : `showToast('Session details unavailable','error')`;
          actionBtnHtml = `<div style="margin-top:8px;"><button onclick="${btnAction}" style="display:inline-flex;align-items:center;gap:4px;padding:6px 14px;background:#fff;color:#64748b;font-size:.8125rem;font-weight:600;border:1px solid #e2e8f0;border-radius:8px;cursor:pointer;" onmouseover="this.style.background='#f8fafc'" onmouseout="this.style.background='#fff'">View Session →</button></div>`;
      }
      extraHtml += actionBtnHtml;
      extraHtml += `</div>`;
  }

  const isOwn = _currentUser && _currentUser.id === author.id;

  card.innerHTML = `
    <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin-bottom:10px;">
      <div style="display:flex;align-items:center;gap:10px;">
        <div style="width:42px;height:42px;border-radius:50%;background:${avatarColor};display:flex;align-items:center;justify-content:center;color:#fff;font-size:14px;font-weight:700;flex-shrink:0;">${initials}</div>
        <div>
          <p style="font-size:.875rem;font-weight:600;color:#0f172a;margin:0 0 1px;">${escHtml(authorName)}</p>
          ${roleDetail ? `<p style="font-size:.75rem;color:#64748b;margin:0 0 1px;">${escHtml(roleDetail)}</p>` : ''}
          <p style="font-size:.6875rem;color:#94a3b8;margin:0;">${timeAgo(post.created_at)}</p>
        </div>
      </div>
      <div style="display:flex;align-items:center;gap:6px;flex-shrink:0;">
        ${badge.label ? `<span class="post-type-badge ${badge.cls}">${badge.label}</span>` : ''}
        ${isOwn ? `<button onclick="deletePost(${post.id})" title="Delete" style="background:none;border:none;cursor:pointer;color:#cbd5e1;padding:4px;border-radius:6px;" onmouseover="this.style.color='#ef4444'" onmouseout="this.style.color='#cbd5e1'">
          <svg width="15" height="15" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
        </button>` : ''}
      </div>
    </div>
    ${post.title ? `<p style="font-size:.9375rem;font-weight:600;color:#0f172a;margin:0 0 6px;">${escHtml(post.title)}</p>` : ''}
    <p style="font-size:.875rem;color:#374151;line-height:1.65;margin:0 0 8px;white-space:pre-line;">${contentHtml}</p>
    ${post.image ? `<img src="${escHtml(post.image)}" alt="Post image" style="width:100%;border-radius:8px;max-height:400px;object-fit:cover;margin-bottom:10px;"/>` : ''}
    ${extraHtml}
    ${tagsHtml ? `<div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:10px;">${tagsHtml}</div>` : ''}
    <div style="display:flex;align-items:center;gap:2px;padding-top:10px;border-top:1px solid #f1f5f9;">
      <button class="action-btn ${post.is_liked ? 'liked' : ''}" id="like-btn-${post.id}" onclick="toggleLike(${post.id}, this)">
        <svg width="16" height="16" fill="${post.is_liked ? 'currentColor' : 'none'}" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z"/></svg>
        <span id="like-count-${post.id}">${post.likes_count || 0}</span>
      </button>
      <button class="action-btn" onclick="toggleComments(${post.id})">
        <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"/></svg>
        <span id="comment-count-${post.id}">${post.comments_count || 0}</span>
      </button>
      <button class="action-btn" onclick="sharePost(${post.id})">
        <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.368 2.684 3 3 0 00-5.368-2.684z"/></svg>
        Share
      </button>
      <button class="action-btn ${post.is_saved ? 'saved' : ''}" id="save-btn-${post.id}" onclick="toggleSave(${post.id}, this)" style="margin-left:auto;">
        <svg width="16" height="16" fill="${post.is_saved ? 'currentColor' : 'none'}" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"/></svg>
        ${post.is_saved ? 'Saved' : 'Save'}
      </button>
      <button class="action-btn" onclick="reportPost(${post.id})" title="Report">
        <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6h-8.5l-1-1H5a2 2 0 00-2 2zm9-13.5V9"/></svg>
      </button>
    </div>
    <div class="comments-panel" id="comments-panel-${post.id}">
      <div id="comments-list-${post.id}"></div>
      <div style="display:flex;gap:8px;margin-top:10px;align-items:center;">
        <div id="comment-user-avatar-${post.id}" style="width:28px;height:28px;border-radius:50%;background:#2563eb;display:flex;align-items:center;justify-content:center;color:#fff;font-size:10px;font-weight:700;flex-shrink:0;">?</div>
        <input type="text" id="comment-input-${post.id}" placeholder="Write a comment..." style="flex:1;padding:7px 12px;font-size:.8125rem;border:1px solid #e2e8f0;border-radius:20px;outline:none;" onkeydown="if(event.key==='Enter')submitComment(${post.id})"/>
        <button onclick="submitComment(${post.id})" style="padding:7px 14px;font-size:.8125rem;font-weight:600;color:#fff;background:#2563eb;border:none;border-radius:8px;cursor:pointer;" onmouseover="this.style.background='#1d4ed8'" onmouseout="this.style.background='#2563eb'">Post</button>
      </div>
    </div>`;

  // Set comment avatar initials
  setTimeout(() => {
    const cAvatar = document.getElementById(`comment-user-avatar-${post.id}`);
    if (cAvatar && _currentUser) {
      const ini = ((_currentUser.first_name?.[0] || '') + (_currentUser.last_name?.[0] || '')).toUpperCase() || '?';
      cAvatar.textContent = ini;
      const rc = { alumni: '#534AB7', student: '#2563EB', faculty: '#0F6E56' };
      cAvatar.style.background = rc[_currentUser.role] || '#2563EB';
    }
  }, 0);

  return card;
}

function expandContent(postId) {
  const short = document.getElementById(`content-short-${postId}`);
  const full = document.getElementById(`content-full-${postId}`);
  if (short) short.style.display = 'none';
  if (full) full.style.display = 'inline';
}

function escHtml(str) {
  if (!str) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── Interactions ──────────────────────────────────────────────
async function toggleLike(postId, btn) {
  // Optimistic UI
  const countEl = document.getElementById(`like-count-${postId}`);
  const wasLiked = btn.classList.contains('liked');
  const prevCount = parseInt(countEl?.textContent || '0');
  btn.classList.toggle('liked', !wasLiked);
  const svg = btn.querySelector('svg');
  if (svg) svg.setAttribute('fill', !wasLiked ? 'currentColor' : 'none');
  if (countEl) countEl.textContent = wasLiked ? Math.max(0, prevCount - 1) : prevCount + 1;

  const res = await apiPost(`/api/feed/${postId}/like/`, {});
  if (!res.ok) {
    // Revert
    btn.classList.toggle('liked', wasLiked);
    if (svg) svg.setAttribute('fill', wasLiked ? 'currentColor' : 'none');
    if (countEl) countEl.textContent = prevCount;
    showToast('Failed to like post', 'error');
    return;
  }
  // Sync with server count
  if (countEl) countEl.textContent = res.data.likes_count;
  if (svg) svg.setAttribute('fill', res.data.liked ? 'currentColor' : 'none');
  btn.classList.toggle('liked', res.data.liked);
}

async function toggleSave(postId, btn) {
  const wasSaved = btn.classList.contains('saved');
  btn.classList.toggle('saved', !wasSaved);
  const svg = btn.querySelector('svg');
  if (svg) svg.setAttribute('fill', !wasSaved ? 'currentColor' : 'none');
  btn.querySelector('span') && (btn.querySelector('span') ? null : null); // text handled below

  const res = await apiPost(`/api/feed/${postId}/save/`, {});
  if (!res.ok) {
    btn.classList.toggle('saved', wasSaved);
    if (svg) svg.setAttribute('fill', wasSaved ? 'currentColor' : 'none');
    showToast('Failed to save post', 'error');
    return;
  }
  const saved = res.data.saved;
  btn.classList.toggle('saved', saved);
  if (svg) svg.setAttribute('fill', saved ? 'currentColor' : 'none');
  showToast(saved ? 'Post saved' : 'Post unsaved', 'success');
}

function sharePost(postId) {
  const url = window.location.origin + '/feed/?post=' + postId;
  if (navigator.clipboard) {
    navigator.clipboard.writeText(url).then(() => showToast('Link copied!', 'success'));
  } else {
    showToast('Link: ' + url, 'info');
  }
}

async function toggleComments(postId) {
  const panel = document.getElementById(`comments-panel-${postId}`);
  if (!panel) return;
  const isOpen = panel.classList.contains('open');
  panel.classList.toggle('open', !isOpen);
  if (!isOpen) {
    await loadComments(postId);
    const input = document.getElementById(`comment-input-${postId}`);
    if (input) input.focus();
  }
}

async function loadComments(postId) {
  const listEl = document.getElementById(`comments-list-${postId}`);
  if (!listEl) return;
  listEl.innerHTML = '<p style="font-size:.8125rem;color:#94a3b8;padding:4px 0;">Loading...</p>';
  const res = await apiGet(`/api/feed/${postId}/comments/`);
  if (!res.ok) { listEl.innerHTML = ''; return; }
  const comments = res.data.results || [];
  listEl.innerHTML = '';
  if (comments.length === 0) {
    listEl.innerHTML = '<p style="font-size:.8125rem;color:#94a3b8;padding:4px 0;">No comments yet. Be the first!</p>';
    return;
  }
  const show = comments.slice(0, 3);
  show.forEach(c => listEl.appendChild(renderComment(c)));
  if (comments.length > 3) {
    const more = document.createElement('button');
    more.style.cssText = 'font-size:.8125rem;color:#2563eb;background:none;border:none;cursor:pointer;padding:4px 0;';
    more.textContent = `View all ${comments.length} comments`;
    more.onclick = () => {
      listEl.innerHTML = '';
      comments.forEach(c => listEl.appendChild(renderComment(c)));
    };
    listEl.appendChild(more);
  }
}

function renderComment(c) {
  const wrap = document.createElement('div');
  wrap.className = 'comment-item';
  const author = c.author || {};
  const initials = ((author.first_name?.[0] || '') + (author.last_name?.[0] || '')).toUpperCase() || '?';
  const name = ((author.first_name || '') + ' ' + (author.last_name || '')).trim() || 'User';
  const roleColors = { alumni: '#534AB7', student: '#2563EB', faculty: '#0F6E56' };
  const color = roleColors[author.role] || '#2563EB';
  const rd = author.role_detail || {};
  let sub = '';
  if (author.role === 'alumni' && rd.company) sub = `${rd.designation || ''} @ ${rd.company}`.trim().replace(/^@ /, '');
  else if (author.role === 'faculty') sub = rd.department || 'Faculty';
  else if (author.role === 'student') sub = 'Student';

  wrap.innerHTML = `
    <div class="comment-avatar" style="background:${color};">${initials}</div>
    <div style="flex:1;background:#f8fafc;border-radius:10px;padding:8px 12px;">
      <div style="display:flex;align-items:baseline;gap:6px;margin-bottom:2px;">
        <p style="font-size:.8125rem;font-weight:600;color:#0f172a;margin:0;">${escHtml(name)}</p>
        ${sub ? `<p style="font-size:.6875rem;color:#94a3b8;margin:0;">${escHtml(sub)}</p>` : ''}
        <p style="font-size:.6875rem;color:#cbd5e1;margin:0 0 0 auto;">${timeAgo(c.created_at)}</p>
      </div>
      <p style="font-size:.8125rem;color:#374151;margin:0;">${escHtml(c.content)}</p>
    </div>`;
  return wrap;
}

async function submitComment(postId) {
  const input = document.getElementById(`comment-input-${postId}`);
  if (!input) return;
  const content = input.value.trim();
  if (!content) return;

  // Optimistic insert
  const listEl = document.getElementById(`comments-list-${postId}`);
  const tempComment = {
    author: _currentUser || {},
    content,
    created_at: new Date().toISOString(),
  };
  const tempEl = renderComment(tempComment);
  tempEl.style.opacity = '0.6';
  if (listEl) listEl.prepend(tempEl);
  input.value = '';

  const res = await apiPost(`/api/feed/${postId}/comments/`, { content });
  if (!res.ok) {
    tempEl.remove();
    input.value = content;
    showToast(extractErrorMessage(res.error), 'error');
    return;
  }
  tempEl.remove();
  const countEl = document.getElementById(`comment-count-${postId}`);
  if (countEl) countEl.textContent = parseInt(countEl.textContent || '0') + 1;
  await loadComments(postId);
}

async function deletePost(postId) {
  if (!confirm('Delete this post?')) return;
  const res = await apiFetch(`/api/feed/${postId}/`, { method: 'DELETE' });
  if (res.status === 204 || res.ok) {
    const card = document.querySelector(`[data-post-id="${postId}"]`);
    if (card) { card.style.opacity = '0'; card.style.transition = 'opacity .3s'; setTimeout(() => card.remove(), 300); }
    showToast('Post deleted', 'success');
  } else {
    showToast('Failed to delete post', 'error');
  }
}

async function reportPost(postId) {
  const reason = prompt('Reason:\nspam / inappropriate / misleading / harassment / other');
  if (!reason) return;
  const res = await apiPost(`/api/feed/${postId}/report/`, { reason: reason.trim() });
  if (res.ok) showToast('Post reported. Thank you.', 'success');
  else showToast(extractErrorMessage(res.error), 'error');
}

// ── Create post modal ─────────────────────────────────────────
function openCreatePostModal(preType) {
  if (_currentUser && _currentUser.role === 'student') {
    showToast('Only alumni and faculty can create posts', 'info');
    return;
  }
  const overlay = document.getElementById('modal-overlay-feed');
  if (!overlay) return;

  // Reset
  document.getElementById('cp-title').value = '';
  document.getElementById('cp-content').value = '';
  document.getElementById('cp-tags').value = '';
  document.getElementById('cp-error').textContent = '';
  document.getElementById('cp-char-count').textContent = '0/5000';
  const submitBtn = document.getElementById('cp-submit-btn');
  if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = 'Post'; }
  ['cp-company','cp-role','cp-location','cp-salary','cp-apply-link','cp-skills',
   'cp-session-price','cp-max-seats', 'cp-meeting-link'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
  const durEl = document.getElementById('cp-session-duration');
  if (durEl) durEl.value = '60';

  selectPostType(preType || 'general');
  overlay.classList.add('open');
  setTimeout(() => document.getElementById('cp-content')?.focus(), 100);
}

function closeCreatePostModal() {
  const overlay = document.getElementById('modal-overlay-feed');
  if (overlay) overlay.classList.remove('open');
}

function selectPostType(type) {
  document.getElementById('cp-type').value = type;
  document.querySelectorAll('.cp-type-pill').forEach(p => p.classList.toggle('active', p.dataset.type === type));
  const titleMap = { general: 'Create Post', announcement: 'Post Announcement', job: 'Post a Job', referral: 'Post a Referral', session: 'Post a Session' };
  const titleEl = document.getElementById('create-modal-title');
  if (titleEl) titleEl.textContent = titleMap[type] || 'Create Post';
  document.getElementById('cp-job-fields').style.display = (type === 'job' || type === 'referral') ? 'block' : 'none';
  document.getElementById('cp-session-fields').style.display = type === 'session' ? 'block' : 'none';
}

function updateCharCount() {
  const content = document.getElementById('cp-content');
  const counter = document.getElementById('cp-char-count');
  if (content && counter) {
    const len = content.value.length;
    counter.textContent = `${len}/5000`;
    counter.style.color = len > 4500 ? '#ef4444' : '#94a3b8';
  }
}

async function submitPost() {
  const errEl = document.getElementById('cp-error');
  const submitBtn = document.getElementById('cp-submit-btn');
  errEl.textContent = '';

  const type = document.getElementById('cp-type').value;
  const content = document.getElementById('cp-content').value.trim();
  if (!content || content.length < 10) { errEl.textContent = 'Content must be at least 10 characters.'; return; }

  const payload = {
    post_type: type,
    title: document.getElementById('cp-title').value.trim(),
    content,
    tags: document.getElementById('cp-tags').value.trim(),
  };

  if (type === 'job' || type === 'referral') {
    payload.company_name = document.getElementById('cp-company').value.trim();
    payload.job_role = document.getElementById('cp-role').value.trim();
    payload.location = document.getElementById('cp-location').value.trim();
    payload.salary_range = document.getElementById('cp-salary').value.trim();
    payload.apply_link = document.getElementById('cp-apply-link').value.trim();
    const skillsRaw = document.getElementById('cp-skills').value.trim();
    payload.required_skills = skillsRaw ? skillsRaw.split(',').map(s => s.trim()).filter(Boolean) : [];
    if (!payload.company_name || !payload.job_role) { errEl.textContent = 'Company name and job role are required.'; return; }
  }

  if (type === 'session') {
    payload.session_date = document.getElementById('cp-session-date').value;
    payload.session_price = document.getElementById('cp-session-price').value;
    payload.session_duration = document.getElementById('cp-session-duration').value || null;
    payload.max_seats = document.getElementById('cp-max-seats').value || null;
    payload.meeting_link = document.getElementById('cp-meeting-link').value.trim();
    if (!payload.session_date || payload.session_price === '' || !payload.meeting_link) { errEl.textContent = 'Session date, price, and meeting link are required.'; return; }
  }

  submitBtn.disabled = true;
  submitBtn.textContent = 'Posting...';
  const res = await apiPost('/api/feed/', payload);
  submitBtn.disabled = false;
  submitBtn.textContent = 'Post';

  if (!res.ok) { errEl.textContent = extractErrorMessage(res.error); return; }

  closeCreatePostModal();
  showToast('Post created!', 'success');
  // Prepend new post to top
  const container = document.getElementById('feed-container');
  if (container && res.data) {
    const newCard = renderPostCard(res.data);
    newCard.style.opacity = '0';
    newCard.style.transition = 'opacity .3s';
    container.prepend(newCard);
    setTimeout(() => { newCard.style.opacity = '1'; }, 50);
  }
}

// ── Filter ────────────────────────────────────────────────────
function setFilter(filterParam) {
  _feedFilter = filterParam;
  _feedTagFilter = '';
  _feedMyPosts = false;
  document.querySelectorAll('.feed-filter-btn').forEach(btn => btn.classList.remove('active'));
  const activeId = filterParam ? `filter-${filterParam}` : 'filter-all';
  const activeBtn = document.getElementById(activeId);
  if (activeBtn) activeBtn.classList.add('active');
  loadFeed(true);
}

function setMyPosts() {
  _feedFilter = '';
  _feedTagFilter = '';
  _feedMyPosts = true;
  document.querySelectorAll('.feed-filter-btn').forEach(btn => btn.classList.remove('active'));
  document.getElementById('filter-my-posts')?.classList.add('active');
  loadFeed(true);
}

function filterByTag(tag) {
  _feedFilter = '';
  _feedTagFilter = tag;
  _feedMyPosts = false;
  document.querySelectorAll('.feed-filter-btn').forEach(btn => btn.classList.remove('active'));
  loadFeed(true);
  showToast(`Filtering by #${tag}`, 'info');
}

// ── Infinite scroll ───────────────────────────────────────────
function initInfiniteScroll() {
  window.addEventListener('scroll', () => {
    if (_feedLoading || _feedDone) return;
    if ((window.innerHeight + window.scrollY) >= document.documentElement.scrollHeight - 400) {
      loadFeed(false);
    }
  });
}

// ── Time ago ──────────────────────────────────────────────────
function timeAgo(dateStr) {
  if (!dateStr) return '';
  const diff = Math.floor((Date.now() - new Date(dateStr)) / 1000);
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
  return new Date(dateStr).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

function renderReferralActionButton(post) {
    const userRole = _currentUser ? _currentUser.role : 'student';
    const r = post.referral_data;
    if (!r || !r.referral_id) return '';

    if (userRole !== 'student') {
        if (userRole === 'alumni' && post.author && _currentUser && post.author.id === _currentUser.id) {
            return `<a href="/referrals/${r.referral_id}/manage/"
                       style="display:inline-flex;align-items:center;gap:6px;background:#7C3AED;
                              color:white;padding:7px 16px;border-radius:8px;text-decoration:none;
                              font-size:12px;font-weight:500">
                       Manage Applications →
                    </a>`;
        }
        return '';
    }

    const matchScore = r.student_match_score || 0;
    const hasApplied = r.student_has_applied;
    const slotsLeft = r.slots_remaining;
    const isActive = r.status === 'active';
    const canApply = matchScore >= 40;

    const scoreColor = matchScore >= 80 ? '#16A34A' : matchScore >= 60 ? '#2563EB' : matchScore >= 40 ? '#D97706' : '#EF4444';
    const scoreBg = matchScore >= 80 ? '#F0FDF4' : matchScore >= 60 ? '#EFF6FF' : matchScore >= 40 ? '#FFFBEB' : '#FEF2F2';

    const matchBadge = `<span style="background:${scoreBg};color:${scoreColor};font-size:11px;font-weight:600;
                               padding:3px 9px;border-radius:20px;display:inline-flex;align-items:center;gap:4px">
                          <span>★</span> ${matchScore}% match
                        </span>`;

    const slotsBadge = slotsLeft > 0
        ? `<span style="font-size:11px;color:#64748B" data-slot-count>${slotsLeft} slot${slotsLeft !== 1 ? 's' : ''} left</span>`
        : `<span style="font-size:11px;color:#EF4444;font-weight:500">All slots filled</span>`;

    if (!isActive || slotsLeft === 0) {
        return `<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px">
                    <div style="display:flex;align-items:center;gap:8px">${matchBadge}${slotsBadge}</div>
                    <button disabled style="background:#F1F5F9;color:#94A3B8;padding:7px 16px;border-radius:8px;
                                           border:none;font-size:12px;font-weight:500;cursor:not-allowed">
                        Slots Full
                    </button>
                </div>`;
    }

    if (hasApplied) {
        return `<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px">
                    <div style="display:flex;align-items:center;gap:8px">${matchBadge}${slotsBadge}</div>
                    <span style="background:#F0FDF4;color:#16A34A;font-size:12px;font-weight:600;
                                 padding:7px 14px;border-radius:8px;display:inline-flex;align-items:center;gap:5px">
                        ✓ Applied
                    </span>
                </div>`;
    }

    if (!canApply) {
        return `<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px">
                    <div style="display:flex;align-items:center;gap:8px">${matchBadge}${slotsBadge}</div>
                    <button disabled title="Your skills don't match enough for this role (need 40%+)"
                            style="background:#FEF2F2;color:#EF4444;padding:7px 16px;border-radius:8px;
                                   border:1px solid #FECACA;font-size:12px;font-weight:500;cursor:not-allowed">
                        Low Match
                    </button>
                </div>`;
    }

    return `<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px">
                <div style="display:flex;align-items:center;gap:8px">${matchBadge}${slotsBadge}</div>
                <button onclick="applyToReferralFromFeed(${r.referral_id}, this)"
                        style="background:#2563EB;color:white;padding:7px 16px;border-radius:8px;
                               border:none;font-size:12px;font-weight:600;cursor:pointer;
                               transition:background .15s"
                        onmouseover="this.style.background='#1D4ED8'"
                        onmouseout="this.style.background='#2563EB'">
                    Apply Now →
                </button>
            </div>`;
}

async function applyToReferralFromFeed(referralId, btnElement) {
    if (btnElement.disabled) return;
    btnElement.textContent = 'Applying...';
    btnElement.disabled = true;
    btnElement.style.background = '#1D4ED8';

    const result = await apiPost(`/api/referrals/${referralId}/apply/`, {
        cover_note: ''
    });

    if (result.ok) {
        const btnContainer = btnElement.parentElement;
        const appliedBadge = document.createElement('span');
        appliedBadge.style.cssText = 'background:#F0FDF4;color:#16A34A;font-size:12px;font-weight:600;padding:7px 14px;border-radius:8px;display:inline-flex;align-items:center;gap:5px;';
        appliedBadge.innerHTML = '✓ Applied';
        btnElement.replaceWith(appliedBadge);
        showToast('Successfully applied! Check My Applications for updates.', 'success');

        const slotSpan = btnContainer.previousElementSibling?.querySelector('[data-slot-count]');
        if (slotSpan) {
            const current = parseInt(slotSpan.textContent);
            if (!isNaN(current) && current > 0) {
                slotSpan.textContent = `${current - 1} slot${current - 1 !== 1 ? 's' : ''} left`;
            }
        }
    } else {
        btnElement.textContent = 'Apply Now →';
        btnElement.disabled = false;
        btnElement.style.background = '#2563EB';
        const error = result.data?.error || result.data?.detail || 'Application failed. Please try again.';
        showToast(error, 'error');
    }
}
