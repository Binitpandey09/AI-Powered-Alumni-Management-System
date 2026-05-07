/* ============================================================
   AlumniAI — Notifications JS
   Loaded on every page via base.html
   Handles: WebSocket, bell badge, dropdown, list page, preferences
   ============================================================ */

// ── Global state ──────────────────────────────────────────────
let wsConnection = null;
let notifPage = 1;
let hasMoreNotifs = true;
let activeNotifFilter = 'all';
let currentUnreadCount = 0;

// ── WebSocket ─────────────────────────────────────────────────

function initWebSocket() {
  if (!localStorage.getItem('access_token')) return;
  const token = localStorage.getItem('access_token');
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws/notifications/?token=${token}`;

  try {
    wsConnection = new WebSocket(wsUrl);

    wsConnection.onopen = () => {
      console.log('[Notifications] WebSocket connected');
    };

    wsConnection.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
      } catch (e) {
        console.error('[Notifications] WS parse error:', e);
      }
    };

    wsConnection.onclose = (event) => {
      wsConnection = null;
      if (event.code !== 4001) {
        // Reconnect after 5s unless auth failed
        setTimeout(() => initWebSocket(), 5000);
      }
    };

    wsConnection.onerror = () => {
      console.log('[Notifications] WebSocket unavailable — falling back to polling');
      startPolling();
    };
  } catch (e) {
    console.log('[Notifications] WebSocket init failed — using polling fallback');
    startPolling();
  }
}

function handleWebSocketMessage(data) {
  if (data.type === 'unread_count') {
    updateUnreadBadge(data.count);
  } else if (data.type === 'notification') {
    const notif = data.notification;
    updateUnreadBadge(currentUnreadCount + 1);
    showToastNotification(notif);
    // Prepend to open dropdown
    const dropdown = document.getElementById('notif-dropdown');
    if (dropdown && !dropdown.classList.contains('hidden')) {
      prependNotifItem(notif);
    }
    // Prepend to open list page
    if (window.location.pathname.startsWith('/notifications/') &&
        !window.location.pathname.startsWith('/notifications/preferences')) {
      const container = document.getElementById('notifications-container');
      if (container) container.insertBefore(renderPageNotifItem(notif), container.firstChild);
    }
  }
}

function sendWebSocketAction(action, extra = {}) {
  if (wsConnection && wsConnection.readyState === WebSocket.OPEN) {
    wsConnection.send(JSON.stringify({ action, ...extra }));
  }
}

// ── Polling fallback ──────────────────────────────────────────

let pollingInterval = null;

function startPolling() {
  if (pollingInterval) return;
  pollingInterval = setInterval(async () => {
    const result = await apiGet('/api/notifications/unread-count/');
    if (result.ok) {
      updateUnreadBadge(result.data.unread_count);
    } else if (result.status === 401) {
      clearInterval(pollingInterval);
      pollingInterval = null;
    }
  }, 30000);
}

// ── Badge & panel count ───────────────────────────────────────

function updateUnreadBadge(count) {
  currentUnreadCount = Math.max(0, count);

  const badge = document.getElementById('notif-badge');
  const panelCount = document.getElementById('notif-panel-count');
  const pageCount = document.getElementById('page-unread-count');

  if (badge) {
    if (currentUnreadCount > 0) {
      badge.style.display = 'inline-flex';
      badge.textContent = currentUnreadCount > 99 ? '99+' : currentUnreadCount;
    } else {
      badge.style.display = 'none';
    }
  }

  if (panelCount) {
    if (currentUnreadCount > 0) {
      panelCount.style.display = 'inline-block';
      panelCount.textContent = currentUnreadCount;
    } else {
      panelCount.style.display = 'none';
    }
  }

  if (pageCount) {
    pageCount.textContent = currentUnreadCount > 0 ? `(${currentUnreadCount} unread)` : '';
  }
}

// ── Dropdown ──────────────────────────────────────────────────

async function loadNotifDropdown() {
  const list = document.getElementById('notif-items-list');
  const loading = document.getElementById('notif-loading');
  if (!list) return;

  if (loading) loading.style.display = 'block';

  const result = await apiGet('/api/notifications/?page=1');

  if (loading) loading.style.display = 'none';

  if (!result.ok) {
    list.innerHTML = '<div style="padding:16px;text-align:center;color:#94A3B8;font-size:13px;">Could not load notifications</div>';
    return;
  }

  const notifications = result.data.results || [];
  if (notifications.length === 0) {
    list.innerHTML = '<div style="padding:24px;text-align:center;color:#94A3B8;font-size:13px;">No notifications yet</div>';
    return;
  }

  list.innerHTML = '';
  notifications.slice(0, 8).forEach(n => list.appendChild(renderDropdownNotifItem(n)));
}

function renderDropdownNotifItem(notif) {
  const div = document.createElement('div');
  const isUnread = !notif.is_read;
  const bg = isUnread ? '#F0F9FF' : 'white';

  div.style.cssText = `display:flex;align-items:flex-start;gap:10px;padding:12px 16px;border-bottom:1px solid #F8FAFC;cursor:pointer;background:${bg};transition:background .1s;`;
  div.onmouseover = () => div.style.background = '#F8FAFC';
  div.onmouseout = () => div.style.background = bg;

  div.innerHTML = `
    <div style="width:8px;height:8px;border-radius:50%;background:${isUnread ? '#2563EB' : 'transparent'};flex-shrink:0;margin-top:6px;"></div>
    <div style="flex:1;min-width:0;">
      <div style="font-size:13px;font-weight:${isUnread ? '600' : '400'};color:#0F172A;margin-bottom:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${_esc(notif.title)}</div>
      <div style="font-size:12px;color:#64748B;line-height:1.4;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;">${_esc(notif.message)}</div>
      <div style="font-size:11px;color:#94A3B8;margin-top:4px;">${notif.time_ago || ''}</div>
    </div>
  `;

  div.onclick = () => {
    markNotifRead(notif.id);
    if (notif.link) window.location.href = notif.link;
    document.getElementById('notif-dropdown')?.classList.add('hidden');
  };

  return div;
}

function prependNotifItem(notif) {
  const list = document.getElementById('notif-items-list');
  if (!list) return;
  const item = renderDropdownNotifItem(notif);
  list.insertBefore(item, list.firstChild);
}

// ── Toast ─────────────────────────────────────────────────────

function showToastNotification(notification) {
  const existing = document.getElementById('notif-toast');
  if (existing) existing.remove();

  // Inject animation style once
  if (!document.getElementById('notif-toast-style')) {
    const style = document.createElement('style');
    style.id = 'notif-toast-style';
    style.textContent = `@keyframes slideInRight { from { transform:translateX(100px); opacity:0; } to { transform:translateX(0); opacity:1; } }`;
    document.head.appendChild(style);
  }

  const toast = document.createElement('div');
  toast.id = 'notif-toast';
  toast.style.cssText = `position:fixed;bottom:80px;right:16px;background:white;border:1px solid #E2E8F0;border-radius:12px;padding:14px 16px;box-shadow:0 4px 20px rgba(0,0,0,0.12);z-index:9999;max-width:300px;display:flex;gap:10px;align-items:flex-start;animation:slideInRight .3s ease;cursor:pointer;`;

  const msgPreview = (notification.message || '').substring(0, 80) + ((notification.message || '').length > 80 ? '...' : '');

  toast.innerHTML = `
    <div style="width:32px;height:32px;border-radius:50%;background:#EFF6FF;display:flex;align-items:center;justify-content:center;flex-shrink:0;">
      <svg width="14" height="14" fill="none" stroke="#2563EB" stroke-width="2" viewBox="0 0 24 24">
        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
        <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
      </svg>
    </div>
    <div style="flex:1;min-width:0;">
      <div style="font-size:13px;font-weight:600;color:#0F172A;margin-bottom:2px;">${_esc(notification.title)}</div>
      <div style="font-size:12px;color:#64748B;">${_esc(msgPreview)}</div>
    </div>
    <button onclick="event.stopPropagation();this.parentElement.remove();" style="background:none;border:none;color:#94A3B8;cursor:pointer;font-size:18px;line-height:1;padding:0;margin-left:4px;flex-shrink:0;">×</button>
  `;

  toast.onclick = (e) => {
    if (e.target.tagName !== 'BUTTON') {
      if (notification.link) window.location.href = notification.link;
      toast.remove();
    }
  };

  document.body.appendChild(toast);
  setTimeout(() => { if (toast.parentNode) toast.remove(); }, 5000);
}

// ── Mark read ─────────────────────────────────────────────────

async function markNotifRead(notifId) {
  sendWebSocketAction('mark_read', { notification_id: notifId });
  await apiPost(`/api/notifications/${notifId}/`, {}, 'PATCH');
}

async function markAllNotificationsRead() {
  sendWebSocketAction('mark_all_read');
  const result = await apiPost('/api/notifications/bulk/', { action: 'mark_all_read' });
  if (result.ok) {
    updateUnreadBadge(0);
    const dropdown = document.getElementById('notif-dropdown');
    if (dropdown && !dropdown.classList.contains('hidden')) loadNotifDropdown();
    if (window.location.pathname.startsWith('/notifications/') &&
        !window.location.pathname.startsWith('/notifications/preferences')) {
      loadNotificationsPage(true);
    }
    showToast('All notifications marked as read', 'success');
  }
}

// ── Notifications list page ───────────────────────────────────

async function loadNotificationsPage(reset = false) {
  if (reset) { notifPage = 1; }

  let url = `/api/notifications/?page=${notifPage}`;
  if (activeNotifFilter === 'unread') url += '&unread=true';
  else if (activeNotifFilter !== 'all') url += `&type=${activeNotifFilter}`;

  const result = await apiGet(url);
  if (!result.ok) return;

  const container = document.getElementById('notifications-container');
  if (!container) return;

  if (reset) container.innerHTML = '';

  const notifications = result.data.results || [];
  hasMoreNotifs = !!result.data.has_next;

  updateUnreadBadge(result.data.unread_count || 0);

  const emptyEl = document.getElementById('notif-empty');
  if (emptyEl) {
    const isEmpty = notifications.length === 0 && notifPage === 1;
    emptyEl.style.display = isEmpty ? 'block' : 'none';
    if (isEmpty) {
      const titleEl = document.getElementById('notif-empty-title');
      const msgEl = document.getElementById('notif-empty-msg');
      if (activeNotifFilter === 'unread') {
        if (titleEl) titleEl.textContent = 'All caught up!';
        if (msgEl) msgEl.textContent = 'No unread notifications.';
      } else {
        if (titleEl) titleEl.textContent = 'No notifications';
        if (msgEl) msgEl.textContent = 'They will appear here.';
      }
    }
  }

  notifications.forEach(n => container.appendChild(renderPageNotifItem(n)));
  notifPage++;

  const loadMoreBtn = document.getElementById('load-more-notifs');
  if (loadMoreBtn) loadMoreBtn.style.display = hasMoreNotifs ? 'block' : 'none';
}

function renderPageNotifItem(notif) {
  const div = document.createElement('div');
  const isUnread = !notif.is_read;

  div.style.cssText = `background:white;border:1px solid #E2E8F0;border-left:3px solid ${isUnread ? '#2563EB' : '#E2E8F0'};border-radius:${isUnread ? '0 12px 12px 0' : '12px'};padding:14px 16px;margin-bottom:8px;display:flex;gap:14px;align-items:flex-start;cursor:pointer;transition:box-shadow .15s;`;
  div.onmouseover = () => div.style.boxShadow = '0 2px 8px rgba(0,0,0,0.06)';
  div.onmouseout = () => div.style.boxShadow = 'none';
  div.dataset.notifId = notif.id;

  const typeIcons = {
    booking_confirmed: `<svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>`,
    new_booking: `<svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>`,
    session: `<svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>`,
    payment: `<svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>`,
    payout: `<svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>`,
    referral: `<svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>`,
    referral_applied: `<svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><rect x="2" y="7" width="20" height="14" rx="2"/><path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/></svg>`,
    verification: `<svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>`,
  };

  const typeBg = {
    booking_confirmed: '#EFF6FF', new_booking: '#EFF6FF', session: '#EFF6FF',
    booking_cancelled: '#FEF2F2', session_cancelled_by_host: '#FEF2F2',
    payment: '#F0FDF4', payout: '#F0FDF4',
    referral: '#F5F3FF', referral_applied: '#F5F3FF',
    verification: '#F0FDFA',
    general: '#F8FAFC',
  };

  const typeColor = {
    booking_confirmed: '#1D4ED8', new_booking: '#1D4ED8', session: '#1D4ED8',
    booking_cancelled: '#991B1B', session_cancelled_by_host: '#991B1B',
    payment: '#166534', payout: '#166534',
    referral: '#6D28D9', referral_applied: '#6D28D9',
    verification: '#0F766E',
    general: '#475569',
  };

  const defaultIcon = `<svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>`;
  const iconHtml = typeIcons[notif.notif_type] || defaultIcon;
  const bg = typeBg[notif.notif_type] || '#F8FAFC';
  const color = typeColor[notif.notif_type] || '#475569';

  div.innerHTML = `
    <div style="width:36px;height:36px;border-radius:50%;background:${bg};color:${color};display:flex;align-items:center;justify-content:center;flex-shrink:0;">${iconHtml}</div>
    <div style="flex:1;min-width:0;">
      <div style="font-size:14px;font-weight:${isUnread ? '600' : '400'};color:#0F172A;margin-bottom:3px;">${_esc(notif.title)}</div>
      <div style="font-size:13px;color:#64748B;line-height:1.5;margin-bottom:6px;">${_esc(notif.message)}</div>
      <div style="font-size:11px;color:#94A3B8;">${notif.time_ago || ''}</div>
    </div>
    <div style="display:flex;flex-direction:column;align-items:flex-end;gap:6px;flex-shrink:0;">
      ${isUnread ? '<div style="width:8px;height:8px;border-radius:50%;background:#2563EB;"></div>' : ''}
      ${isUnread ? `<button onclick="event.stopPropagation();markNotifReadOnPage(${notif.id},this)" style="font-size:11px;color:#2563EB;background:none;border:none;cursor:pointer;">Mark read</button>` : ''}
      <button onclick="event.stopPropagation();deleteNotif(${notif.id},this)" style="font-size:11px;color:#EF4444;background:none;border:none;cursor:pointer;">Delete</button>
    </div>
  `;

  div.onclick = () => {
    if (!notif.is_read) markNotifReadOnPage(notif.id, null);
    if (notif.link) window.location.href = notif.link;
  };

  return div;
}

async function markNotifReadOnPage(notifId, btn) {
  await markNotifRead(notifId);
  const row = document.querySelector(`[data-notif-id="${notifId}"]`);
  if (row) {
    row.style.borderLeftColor = '#E2E8F0';
    row.style.borderRadius = '12px';
    // Remove blue dot
    const dot = row.querySelector('[style*="background:#2563EB"]');
    if (dot && dot.style.width === '8px') dot.remove();
    if (btn) btn.remove();
  }
  currentUnreadCount = Math.max(0, currentUnreadCount - 1);
  updateUnreadBadge(currentUnreadCount);
}

async function deleteNotif(notifId) {
  const result = await apiDelete(`/api/notifications/${notifId}/`);
  if (result.ok || result.status === 204) {
    const row = document.querySelector(`[data-notif-id="${notifId}"]`);
    if (row) row.remove();
  }
}

// ── Preferences page ──────────────────────────────────────────

async function loadPreferences() {
  const result = await apiGet('/api/notifications/preferences/');
  if (!result.ok) return;
  const data = result.data;

  // Map API fields to toggle IDs
  const fieldMap = {
    inapp_general: 'inapp_general',
    inapp_session: 'inapp_session',
    inapp_referral: 'inapp_referral',
    inapp_payment: 'inapp_payment',
    email_general: 'email_general',
    email_session: 'email_session',
    email_referral: 'email_referral',
    email_payment: 'email_payment',
  };

  for (const [apiField, toggleId] of Object.entries(fieldMap)) {
    const el = document.getElementById(toggleId);
    if (el && data[apiField] !== undefined) el.checked = data[apiField];
  }
}

async function savePreferenceToggle(fieldId, value) {
  const indicator = document.getElementById(`pref-status-${fieldId}`);
  if (indicator) { indicator.textContent = 'Saving...'; indicator.style.color = '#64748B'; indicator.style.display = 'inline'; }

  // Map toggle ID to API field name
  const payload = { [fieldId]: value };
  const result = await apiPost('/api/notifications/preferences/', payload, 'PATCH');

  if (indicator) {
    if (result.ok) {
      indicator.textContent = 'Saved ✓';
      indicator.style.color = '#16A34A';
      setTimeout(() => { indicator.style.display = 'none'; }, 2000);
    } else {
      indicator.textContent = 'Error';
      indicator.style.color = '#EF4444';
    }
  }
}

async function saveAllPreferences() {
  const fields = [
    'inapp_general', 'inapp_session', 'inapp_referral', 'inapp_payment',
    'email_general', 'email_session', 'email_referral', 'email_payment',
  ];
  const payload = {};
  fields.forEach(f => {
    const el = document.getElementById(f);
    if (el) payload[f] = el.checked;
  });

  const result = await apiPost('/api/notifications/preferences/', payload, 'PATCH');
  if (result.ok) {
    showToast('Preferences saved!', 'success');
  } else {
    showToast('Failed to save preferences.', 'error');
  }
}

// ── Utility ───────────────────────────────────────────────────

function _esc(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Init ──────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  if (localStorage.getItem('access_token')) {
    initWebSocket();
    // Fetch initial count via REST in case WS is slow
    apiGet('/api/notifications/unread-count/').then(result => {
      if (result.ok) updateUnreadBadge(result.data.unread_count);
    });
  }

  const path = window.location.pathname;

  // ── Notifications list page ──
  if (path === '/notifications/' || path === '/notifications') {
    loadNotificationsPage(true);

    document.getElementById('page-mark-all-btn')?.addEventListener('click', markAllNotificationsRead);

    document.getElementById('page-delete-read-btn')?.addEventListener('click', async () => {
      if (!confirm('Delete all read notifications?')) return;
      const result = await apiPost('/api/notifications/bulk/', { action: 'delete_read' });
      if (result.ok) {
        showToast(result.data.detail || 'Deleted read notifications.', 'success');
        loadNotificationsPage(true);
      }
    });

    document.getElementById('load-more-notifs')?.addEventListener('click', () => loadNotificationsPage(false));

    // Filter tabs
    document.querySelectorAll('.notif-filter-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        document.querySelectorAll('.notif-filter-tab').forEach(t => {
          t.classList.remove('active-tab');
          t.style.background = 'white';
          t.style.color = '#64748B';
          t.style.borderColor = '#E2E8F0';
        });
        tab.classList.add('active-tab');
        tab.style.background = '#2563EB';
        tab.style.color = 'white';
        tab.style.borderColor = '#2563EB';
        activeNotifFilter = tab.dataset.filter;
        loadNotificationsPage(true);
      });
    });
  }

  // ── Preferences page ──
  if (path.startsWith('/notifications/preferences')) {
    loadPreferences();
    document.getElementById('save-all-prefs-btn')?.addEventListener('click', saveAllPreferences);
  }
});
