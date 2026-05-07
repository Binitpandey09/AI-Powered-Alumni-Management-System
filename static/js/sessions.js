// sessions.js — AlumniAI Sessions UI

let sessionPage = 1;
let hasMoreSessions = true;
let isSessionsLoading = false;
let activeSessionFilters = {};
let currentSessionId = null;
let currentBookingId = null;
let demoSessionUsed = false;
let activeNiches = [];
let cachedBookings = [];
let activeBookingFilter = 'all';
let cachedHostedSessions = [];
let activeHostedFilter = '';
let currentStep = 1;

const TYPE_COLORS = {
  group:'#2563EB',one_on_one:'#534AB7',cohort:'#0F6E56',
  doubt:'#BA7517',project:'#993C1D',career:'#D4537E',recorded:'#185FA5',
};
const TYPE_LABELS = {
  group:'Group',one_on_one:'1:1',cohort:'Cohort',
  doubt:'Doubt class',project:'Project',career:'Career',recorded:'Recorded',
};
const STATUS_LABELS = {
  confirmed:'Confirmed',completed:'Completed',
  cancelled_by_student:'Cancelled',cancelled_by_host:'Cancelled by host',
  pending_payment:'Pending payment',refunded:'Refunded',no_show:'No show',
};
const STATUS_COLORS = {
  confirmed:{bg:'#EFF6FF',text:'#1D4ED8'},
  completed:{bg:'#F0FDF4',text:'#166534'},
  cancelled_by_student:{bg:'#FEF2F2',text:'#991B1B'},
  cancelled_by_host:{bg:'#FEF2F2',text:'#991B1B'},
  pending_payment:{bg:'#FEFCE8',text:'#854D0E'},
};

// ── Marketplace: load sessions ────────────────────────────────────────────────
async function loadSessions(reset = false) {
  if (isSessionsLoading && !reset) return;
  if (!hasMoreSessions && !reset) return;
  isSessionsLoading = true;
  if (reset) { sessionPage = 1; hasMoreSessions = true; }

  const grid = document.getElementById('sessions-grid');
  if (reset && grid) grid.innerHTML = '';
  showSessionSkeletons();

  let url = '/api/sessions/?page=' + sessionPage;
  Object.entries(activeSessionFilters).forEach(([k, v]) => {
    if (v !== '' && v !== null && v !== undefined) url += '&' + k + '=' + encodeURIComponent(v);
  });

  let result;
  try {
    result = await apiGet(url);
  } finally {
    hideSessionSkeletons();
    isSessionsLoading = false;
  }
  if (!result.ok) {
    if (grid && sessionPage === 1) {
      grid.innerHTML = '<div style="grid-column:1/-1;text-align:center;padding:40px 20px;color:#64748B;font-size:14px">Could not load sessions. <a href="#" onclick="loadSessions(true);return false" style="color:#2563EB">Retry</a></div>';
    }
    return;
  }

  const data = result.data;
  const sessions = data.results || [];
  hasMoreSessions = !!data.has_next;

  const countEl = document.getElementById('sessions-count');
  if (countEl) countEl.textContent = 'Showing ' + (data.total || sessions.length) + ' sessions';

  const emptyEl = document.getElementById('sessions-empty');
  if (emptyEl) emptyEl.style.display = sessions.length === 0 ? 'block' : 'none';

  sessions.forEach(s => { if (grid) grid.appendChild(renderSessionCard(s)); });
  sessionPage++;

  const loadMoreBtn = document.getElementById('load-more-btn');
  if (loadMoreBtn) loadMoreBtn.style.display = hasMoreSessions ? 'block' : 'none';
}

function renderSessionCard(session) {
  const div = document.createElement('div');
  div.className = 'session-card';

  const typeColor = TYPE_COLORS[session.session_type] || '#2563EB';
  const typeLabel = TYPE_LABELS[session.session_type] || session.session_type;
  const hostInitials = ((session.host?.first_name?.[0]||'')+(session.host?.last_name?.[0]||'')).toUpperCase()||'?';
  const d = new Date(session.scheduled_at);
  const dateStr = d.toLocaleDateString('en-IN',{weekday:'short',day:'numeric',month:'short'});
  const timeStr = d.toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit'});
  const seatsLeft = session.available_seats || 0;
  const seatsPct = session.max_seats > 0 ? Math.round((session.booked_seats / session.max_seats) * 100) : 0;
  const seatsBarColor = seatsPct >= 90 ? '#EF4444' : seatsPct >= 60 ? '#F97316' : '#22C55E';

  let bookBtnStyle = 'flex:1;border:none;border-radius:7px;padding:8px 12px;font-size:13px;font-weight:600;cursor:pointer;';
  let bookBtnText = '', bookBtnOnclick = '';
  if (session.is_full) {
    bookBtnStyle += 'background:#F1F5F9;color:#94A3B8;cursor:not-allowed';
    bookBtnText = 'Session full';
  } else if (session.is_booked) {
    bookBtnStyle += 'background:#DCFCE7;color:#166534;cursor:default';
    bookBtnText = 'Booked \u2713';
  } else if (session.is_free && !demoSessionUsed) {
    bookBtnStyle += 'background:#0F6E56;color:white';
    bookBtnText = 'Book free demo';
    bookBtnOnclick = 'bookSession('+session.id+',true)';
  } else {
    bookBtnStyle += 'background:#2563EB;color:white';
    bookBtnText = 'Book \u2014 \u20b9'+parseFloat(session.price).toLocaleString('en-IN');
    bookBtnOnclick = 'bookSession('+session.id+',false)';
  }

  const skillsHtml = (session.skills_covered||[]).slice(0,3)
    .map(s=>'<span style="background:#F1F5F9;color:#475569;font-size:11px;padding:2px 7px;border-radius:10px">'+s+'</span>').join('');
  const extraSkills = (session.skills_covered||[]).length > 3
    ? '<span style="font-size:11px;color:#94A3B8">+'+(session.skills_covered.length-3)+' more</span>' : '';

  const hostPicHtml = session.host?.profile_pic
    ? '<img src="'+session.host.profile_pic+'" style="width:28px;height:28px;border-radius:50%;object-fit:cover;border:2px solid rgba(255,255,255,0.8)">'
    : '<div style="width:28px;height:28px;border-radius:50%;background:rgba(255,255,255,0.25);border:2px solid rgba(255,255,255,0.6);display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:white">'+hostInitials+'</div>';

  const ratingHtml = session.host?.average_rating
    ? '<span style="color:#F59E0B;font-size:11px">\u2605 '+parseFloat(session.host.average_rating).toFixed(1)+'</span>'
    : '<span style="background:rgba(255,255,255,0.2);color:rgba(255,255,255,0.9);font-size:10px;padding:1px 6px;border-radius:8px">New</span>';

  // Colored gradient header (no thumbnail needed)
  const headerGradient = session.thumbnail
    ? 'background:url('+session.thumbnail+') center/cover'
    : 'background:linear-gradient(135deg,'+typeColor+','+typeColor+'cc)';

  div.innerHTML =
    '<div style="'+headerGradient+';height:80px;padding:10px 12px;display:flex;flex-direction:column;justify-content:space-between;position:relative">'
    +'<div style="display:flex;justify-content:space-between;align-items:flex-start">'
    +'<span style="background:rgba(255,255,255,0.2);color:white;font-size:10px;font-weight:700;padding:2px 8px;border-radius:10px;backdrop-filter:blur(4px)">'+typeLabel+'</span>'
    +(session.is_free?'<span style="background:#DCFCE7;color:#166534;font-size:10px;font-weight:700;padding:2px 8px;border-radius:10px">FREE</span>':'<span style="background:rgba(255,255,255,0.9);color:#0F172A;font-size:11px;font-weight:700;padding:2px 8px;border-radius:10px">\u20b9'+parseFloat(session.price).toLocaleString('en-IN')+'</span>')
    +'</div>'
    +'<div style="display:flex;align-items:center;justify-content:space-between">'
    +'<div style="display:flex;align-items:center;gap:6px">'+hostPicHtml
    +'<span style="font-size:12px;font-weight:500;color:white;text-shadow:0 1px 2px rgba(0,0,0,0.3)">'+(session.host?.first_name||'')+' '+(session.host?.last_name||'')+'</span>'
    +'</div>'+ratingHtml+'</div>'
    +'</div>'
    +'<div style="padding:12px">'
    +'<h3 style="font-size:14px;font-weight:600;color:#0F172A;margin:0 0 6px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;line-height:1.4">'+session.title+'</h3>'
    +'<div style="display:flex;flex-wrap:wrap;gap:3px;margin-bottom:8px">'+(session.niche?'<span style="background:#EFF6FF;color:#2563EB;font-size:10px;padding:2px 6px;border-radius:8px">#'+session.niche+'</span>':'')+skillsHtml+extraSkills+'</div>'
    +'<div style="display:grid;grid-template-columns:1fr 1fr;gap:3px;font-size:11px;color:#64748B;margin-bottom:10px">'
    +'<span>\ud83d\udcc5 '+dateStr+'</span><span>\ud83d\udd50 '+timeStr+'</span>'
    +'<span>\u23f1 '+session.duration_minutes+' min</span><span>\ud83d\udc65 '+(session.is_full?'<span style="color:#EF4444">Full</span>':seatsLeft+' left')+'</span></div>'
    // Seats progress bar
    +'<div class="seats-bar-track"><div class="seats-bar-fill" style="width:'+seatsPct+'%;background:'+seatsBarColor+'"></div></div>'
    +'<div style="font-size:10px;color:#94A3B8;margin-bottom:10px">'+session.booked_seats+' / '+session.max_seats+' seats booked</div>'
    +'<div style="display:flex;gap:6px;border-top:1px solid #F1F5F9;padding-top:8px">'
    +'<button style="'+bookBtnStyle+'" onclick="'+bookBtnOnclick+'">'+bookBtnText+'</button>'
    +'<button onclick="window.location=\'/sessions/'+session.id+'/\'" style="border:1px solid #2563EB;color:#2563EB;background:white;border-radius:7px;padding:7px 10px;font-size:12px;font-weight:500;cursor:pointer;white-space:nowrap">Details \u2192</button>'
    +'</div></div>';

  return div;
}

function showSessionSkeletons() {
  const grid = document.getElementById('sessions-grid');
  if (!grid) return;
  for (let i = 0; i < 3; i++) {
    const sk = document.createElement('div');
    sk.className = 'session-skeleton';
    sk.style.cssText = 'background:#F1F5F9;border-radius:12px;height:280px;animation:pulse 1.5s ease-in-out infinite';
    grid.appendChild(sk);
  }
}
function hideSessionSkeletons() { document.querySelectorAll('.session-skeleton').forEach(el => el.remove()); }

function applyFilters() {
  activeSessionFilters = {};
  const types = Array.from(document.querySelectorAll('[id^="type-"]:checked')).map(el=>el.value).filter(v=>v!=='all');
  if (types.length) activeSessionFilters['type'] = types[0];
  const priceSlider = document.getElementById('price-slider');
  if (priceSlider && parseInt(priceSlider.value) < 5000) activeSessionFilters['price_max'] = priceSlider.value;
  const freeOnly = document.getElementById('filter-free');
  if (freeOnly?.checked) activeSessionFilters['free'] = 'true';
  const hostRadio = document.querySelector('input[name="host-type"]:checked');
  if (hostRadio && hostRadio.value !== 'all') activeSessionFilters['host_role'] = hostRadio.value;
  if (activeNiches.length) activeSessionFilters['niche'] = activeNiches[0];
  const search = document.getElementById('session-search');
  if (search?.value.trim()) activeSessionFilters['search'] = search.value.trim();
  loadSessions(true);
}

function clearFilters() {
  activeSessionFilters = {}; activeNiches = [];
  document.querySelectorAll('[id^="type-"]').forEach(el => { el.checked = el.value === 'all'; });
  const ps = document.getElementById('price-slider');
  if (ps) { ps.value = 5000; updatePriceDisplay(5000); }
  const fi = document.getElementById('filter-free'); if (fi) fi.checked = false;
  const ha = document.getElementById('host-all'); if (ha) ha.checked = true;
  const si = document.getElementById('session-search'); if (si) si.value = '';
  document.querySelectorAll('.topic-pill').forEach(p => p.classList.remove('active'));
  loadSessions(true);
}

function updatePriceDisplay(val) {
  const el = document.getElementById('price-display');
  if (el) el.textContent = 'Up to \u20b9' + parseInt(val).toLocaleString('en-IN');
}

// ── Booking functions ─────────────────────────────────────────────────────────
async function bookSession(sessionId, isDemo) {
  currentSessionId = sessionId;
  const result = await apiGet('/api/sessions/' + sessionId + '/');
  if (!result.ok) { showToast('Could not load session details.', 'error'); return; }
  const session = result.data;

  const modal = document.getElementById('booking-confirm-modal');
  if (!modal) { proceedWithBooking(sessionId, isDemo); return; }

  const titleEl = document.getElementById('confirm-session-title');
  const hostEl = document.getElementById('confirm-host-name');
  const dateEl = document.getElementById('confirm-session-date');
  const amtEl = document.getElementById('confirm-amount');
  if (titleEl) titleEl.textContent = session.title;
  if (hostEl) hostEl.textContent = (session.host?.first_name||'') + ' ' + (session.host?.last_name||'');
  if (dateEl) dateEl.textContent = new Date(session.scheduled_at).toLocaleDateString('en-IN',{weekday:'long',day:'numeric',month:'long',year:'numeric'});
  if (amtEl) amtEl.textContent = isDemo ? 'FREE (Demo Session)' : '\u20b9' + parseFloat(session.price).toLocaleString('en-IN');

  modal.style.display = 'flex';
  const proceedBtn = document.getElementById('confirm-proceed-btn');
  if (proceedBtn) proceedBtn.onclick = () => { modal.style.display = 'none'; proceedWithBooking(sessionId, isDemo); };
}

async function proceedWithBooking(sessionId, isDemo) {
  const payload = isDemo ? { use_free_demo: true } : {};
  const result = await apiPost('/api/sessions/' + sessionId + '/book/', payload);
  if (!result.ok) {
    const msg = result.data?.error || result.data?.detail || result.data?.non_field_errors?.[0] || 'Booking failed.';
    showToast(msg, 'error');
    return;
  }
  const data = result.data;
  if (data.booking_confirmed) {
    showToast(data.message || 'Session booked!', 'success');
    demoSessionUsed = isDemo ? true : demoSessionUsed;
    currentBookingId = data.booking_id;
    if (typeof refreshBookingCard === 'function') refreshBookingCard();
    else loadSessions(true);
    return;
  }
  if (data.razorpay_order_id) {
    currentBookingId = data.booking_id;
    openRazorpayCheckout(data);
  }
}

function openRazorpayCheckout(bookingData) {
  if (typeof Razorpay === 'undefined') {
    showToast('Payment gateway not loaded. Please refresh.', 'error');
    return;
  }
  const options = {
    key: bookingData.razorpay_key_id || (typeof RAZORPAY_KEY !== 'undefined' ? RAZORPAY_KEY : ''),
    amount: Math.round(parseFloat(bookingData.amount) * 100),
    currency: 'INR',
    name: 'AlumniAI',
    description: bookingData.session_title,
    order_id: bookingData.razorpay_order_id,
    prefill: { name: bookingData.student_name, email: bookingData.student_email },
    theme: { color: '#2563EB' },
    handler: function(response) { verifyPayment(response, bookingData.booking_id); },
    modal: { ondismiss: function() { showToast('Payment cancelled.', 'error'); } },
  };
  const rzp = new Razorpay(options);
  rzp.open();
}

async function verifyPayment(razorpayResponse, bookingId) {
  const result = await apiPost('/api/sessions/payment/verify/', {
    razorpay_order_id: razorpayResponse.razorpay_order_id,
    razorpay_payment_id: razorpayResponse.razorpay_payment_id,
    razorpay_signature: razorpayResponse.razorpay_signature,
    booking_id: bookingId,
  });
  if (result.ok) {
    showToast('Payment successful! Booking confirmed.', 'success');
    if (typeof refreshBookingCard === 'function') refreshBookingCard();
    else loadSessions(true);
  } else {
    showToast('Payment verification failed. Contact support.', 'error');
  }
}

async function cancelBooking(bookingId) {
  if (!confirm('Cancel this booking? You may receive a 50% refund if cancelled 2+ hours before.')) return;
  const result = await apiPost('/api/sessions/bookings/' + bookingId + '/cancel/', {});
  if (result.ok) {
    const refund = result.data.refund_amount;
    showToast('Booking cancelled.' + (refund > 0 ? ' \u20b9' + refund + ' will be refunded.' : ''), 'success');
    if (typeof loadMyBookings === 'function') loadMyBookings();
    else if (typeof refreshBookingCard === 'function') refreshBookingCard();
  } else {
    showToast('Cancellation failed. Please try again.', 'error');
  }
}

// ── Create session modal ──────────────────────────────────────────────────────
function openCreateSessionModal() {
  const overlay = document.getElementById('create-session-overlay');
  if (overlay) { overlay.style.display = 'flex'; showStep(1); }
}

function closeCreateSessionModal() {
  const overlay = document.getElementById('create-session-overlay');
  if (overlay) overlay.style.display = 'none';
  resetCreateSessionForm();
}

function showStep(step) {
  currentStep = step;
  [1, 2, 3].forEach(n => {
    const el = document.getElementById('step-' + n);
    if (el) el.style.display = n === step ? 'block' : 'none';
  });
  // Update step dots
  [1, 2, 3].forEach(n => {
    const dot = document.getElementById('dot-' + n);
    if (!dot) return;
    if (n < step) { dot.style.background = 'white'; dot.style.border = '2px solid #2563EB'; dot.style.color = '#2563EB'; dot.textContent = '\u2713'; }
    else if (n === step) { dot.style.background = '#2563EB'; dot.style.border = 'none'; dot.style.color = 'white'; dot.textContent = n; }
    else { dot.style.background = '#E2E8F0'; dot.style.border = 'none'; dot.style.color = '#94A3B8'; dot.textContent = n; }
  });
  [1, 2].forEach(n => {
    const line = document.getElementById('line-' + n);
    if (line) line.style.background = n < step ? '#2563EB' : '#E2E8F0';
  });
  // Populate summary on step 3
  if (step === 3) populateSessionSummary();
}

function populateSessionSummary() {
  const summary = document.getElementById('session-summary');
  if (!summary) return;
  const typeEl = document.getElementById('session-type-select');
  const titleEl = document.getElementById('session-title');
  const dtEl = document.getElementById('session-datetime');
  const durEl = document.getElementById('session-duration');
  const seatsEl = document.getElementById('session-max-seats');
  const freeEl = document.getElementById('session-is-free');
  const priceEl = document.getElementById('session-price');
  const nicheEl = document.getElementById('session-niche');

  const dt = dtEl?.value ? new Date(dtEl.value).toLocaleString('en-IN') : '—';
  const price = freeEl?.checked ? 'Free' : ('\u20b9' + (priceEl?.value || '—'));

  summary.innerHTML =
    '<div><span style="color:#64748B">Type:</span> ' + (TYPE_LABELS[typeEl?.value] || typeEl?.value || '—') + '</div>' +
    '<div><span style="color:#64748B">Title:</span> ' + (titleEl?.value || '—') + '</div>' +
    '<div><span style="color:#64748B">Date & Time:</span> ' + dt + '</div>' +
    '<div><span style="color:#64748B">Duration:</span> ' + (durEl?.value || '—') + ' min</div>' +
    '<div><span style="color:#64748B">Max seats:</span> ' + (seatsEl?.value || '—') + '</div>' +
    '<div><span style="color:#64748B">Price:</span> ' + price + '</div>' +
    '<div><span style="color:#64748B">Niche:</span> ' + (nicheEl?.value || '—') + '</div>';
}

function resetCreateSessionForm() {
  currentStep = 1;
  ['session-title','session-description','session-niche','session-datetime','cohost-email','session-price','session-skills'].forEach(id => {
    const el = document.getElementById(id); if (el) el.value = '';
  });
  const fi = document.getElementById('session-is-free'); if (fi) fi.checked = false;
  const pf = document.getElementById('price-field'); if (pf) pf.style.display = 'block';
  const errEl = document.getElementById('create-modal-error'); if (errEl) errEl.style.display = 'none';
}

async function submitCreateSession() {
  const btn = document.getElementById('publish-session-btn');
  const errEl = document.getElementById('create-modal-error');
  if (btn) { btn.textContent = 'Publishing...'; btn.disabled = true; }
  if (errEl) errEl.style.display = 'none';

  const sessionType = document.getElementById('session-type-select')?.value;
  const title = document.getElementById('session-title')?.value.trim();
  const description = document.getElementById('session-description')?.value.trim();
  const niche = document.getElementById('session-niche')?.value.trim();
  const datetime = document.getElementById('session-datetime')?.value;
  const duration = document.getElementById('session-duration')?.value;
  const maxSeats = document.getElementById('session-max-seats')?.value;
  const isFree = document.getElementById('session-is-free')?.checked;
  const price = document.getElementById('session-price')?.value;
  const skillsRaw = document.getElementById('session-skills')?.value || '';
  const skills = skillsRaw.split(',').map(s => s.trim()).filter(Boolean);

  if (!title) { showFieldError(errEl, btn, 'Title is required.'); return; }
  if (!description) { showFieldError(errEl, btn, 'Description is required.'); return; }
  if (!datetime) { showFieldError(errEl, btn, 'Date and time is required.'); return; }
  if (!isFree && (!price || parseFloat(price) <= 0)) { showFieldError(errEl, btn, 'Price must be greater than 0 for paid sessions.'); return; }

  const payload = {
    session_type: sessionType, title, description, niche,
    scheduled_at: new Date(datetime).toISOString(),
    duration_minutes: parseInt(duration),
    max_seats: parseInt(maxSeats),
    is_free: isFree,
    price: isFree ? 0 : parseFloat(price),
    skills_covered: skills,
  };

  const result = await apiPost('/api/sessions/', payload);
  if (btn) { btn.textContent = 'Publish Session'; btn.disabled = false; }

  if (result.ok) {
    closeCreateSessionModal();
    showToast('Session published successfully!', 'success');
    if (typeof loadHostedSessions === 'function') loadHostedSessions(true);
    else if (typeof loadSessions === 'function') loadSessions(true);
  } else {
    const firstKey = Object.keys(result.data || {})[0];
    const msg = firstKey ? (Array.isArray(result.data[firstKey]) ? result.data[firstKey][0] : result.data[firstKey]) : 'Failed to publish session.';
    if (errEl) { errEl.textContent = msg; errEl.style.display = 'block'; }
  }
}

function showFieldError(errEl, btn, msg) {
  if (errEl) { errEl.textContent = msg; errEl.style.display = 'block'; }
  if (btn) { btn.textContent = 'Publish Session'; btn.disabled = false; }
}

// ── My Bookings ───────────────────────────────────────────────────────────────
async function loadMyBookings() {
  const result = await apiGet('/api/sessions/my-bookings/');
  if (!result.ok) return;
  cachedBookings = result.data?.results || result.data || [];
  renderBookings();
}

function renderBookings() {
  const container = document.getElementById('bookings-container');
  if (!container) return;
  const filtered = activeBookingFilter === 'all'
    ? cachedBookings
    : cachedBookings.filter(b => b.status === activeBookingFilter || (activeBookingFilter === 'confirmed' && b.status === 'pending_payment'));
  container.innerHTML = '';
  const emptyEl = document.getElementById('bookings-empty');
  if (emptyEl) emptyEl.style.display = filtered.length === 0 ? 'block' : 'none';
  filtered.forEach(b => container.appendChild(renderBookingCard(b)));
}

function renderBookingCard(booking) {
  const div = document.createElement('div');
  div.style.cssText = 'background:white;border:1px solid #E2E8F0;border-radius:12px;padding:16px;display:flex;gap:14px;align-items:flex-start;margin-bottom:12px';

  const st = booking.status;
  const sc = STATUS_COLORS[st] || { bg: '#F1F5F9', text: '#64748B' };
  const session = booking.session;
  const d = session ? new Date(session.scheduled_at) : null;
  const dateStr = d ? d.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' }) : '';
  const isPast = d ? d < new Date() : false;

  const thumbHtml = session?.thumbnail
    ? '<img src="'+session.thumbnail+'" style="width:60px;height:60px;border-radius:8px;object-fit:cover;flex-shrink:0">'
    : '<div style="width:60px;height:60px;border-radius:8px;background:#EFF6FF;display:flex;align-items:center;justify-content:center;font-size:22px;flex-shrink:0">\ud83c\udf93</div>';

  let actionsHtml = '';
  if (st === 'confirmed' && !isPast) {
    actionsHtml = '<a href="/sessions/'+(session?.id||'')+'/" style="font-size:12px;color:#2563EB;text-decoration:none;border:1px solid #2563EB;padding:5px 10px;border-radius:6px">View \u2192</a>'
      + '<a href="#" onclick="cancelBooking('+booking.id+');return false" style="font-size:12px;color:#DC2626;text-decoration:none">Cancel</a>';
  } else if (st === 'completed') {
    const safeTitle = (session?.title||'').replace(/'/g, "\\'").replace(/"/g, "&quot;");
    const safeHost = ((session?.host?.first_name||'')+' '+(session?.host?.last_name||'')).replace(/'/g, "\\'").replace(/"/g, "&quot;");
    const rateBtn = `<button onclick="if(typeof openRatingModal==='function') openRatingModal(${booking.id}, 'student_to_host', '${safeTitle}', '${safeHost}')" style="font-size:12px;color:white;background:#F59E0B;border:none;padding:5px 10px;border-radius:6px;cursor:pointer">Rate Session ★</button>`;
    actionsHtml = rateBtn + ' <a href="/sessions/'+(session?.id||'')+'/" style="font-size:12px;color:#2563EB;text-decoration:none;border:1px solid #2563EB;padding:5px 10px;border-radius:6px">View \u2192</a>';
  } else if (st === 'confirmed' && isPast) {
    actionsHtml = '<a href="/sessions/'+(session?.id||'')+'/" style="font-size:12px;color:#2563EB;text-decoration:none;border:1px solid #2563EB;padding:5px 10px;border-radius:6px">View \u2192</a>';
  }

  div.innerHTML = thumbHtml +
    '<div style="flex:1;min-width:0">'
    +'<div style="font-size:14px;font-weight:600;color:#0F172A;margin-bottom:3px">'+(session?.title||'Session')+'</div>'
    +'<div style="font-size:12px;color:#64748B;margin-bottom:3px">'+(session?.host?.first_name||'')+' '+(session?.host?.last_name||'')+'</div>'
    +'<div style="font-size:12px;color:#94A3B8">'+dateStr+(session?.duration_minutes?' \u00b7 '+session.duration_minutes+' min':'')+'</div>'
    +'</div>'
    +'<div style="display:flex;flex-direction:column;gap:6px;align-items:flex-end;flex-shrink:0">'
    +'<span style="background:'+sc.bg+';color:'+sc.text+';font-size:11px;font-weight:600;padding:3px 8px;border-radius:10px">'+(STATUS_LABELS[st]||st)+'</span>'
    +'<span style="font-size:13px;font-weight:600;color:#0F172A">'+(booking.is_free_demo?'Free Demo':'\u20b9'+parseFloat(booking.amount_paid).toLocaleString('en-IN'))+'</span>'
    +(booking.refund_amount > 0 ? '<span style="font-size:11px;color:#166534">\u20b9'+parseFloat(booking.refund_amount).toLocaleString('en-IN')+' refunded</span>' : '')
    +'<div style="display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end">'+actionsHtml+'</div>'
    +'</div>';

  return div;
}

// ── Hosted Sessions ───────────────────────────────────────────────────────────
async function loadHostedSessions(reset = false) {
  let url = '/api/sessions/hosting/';
  if (activeHostedFilter) url += '?status=' + activeHostedFilter;
  const result = await apiGet(url);
  if (!result.ok) return;
  cachedHostedSessions = result.data?.results || result.data || [];
  renderHostedSessions();
  computeHostedStats();
}

function computeHostedStats() {
  const sessions = cachedHostedSessions;
  const totalSessions = sessions.length;
  const totalBookings = sessions.reduce((acc, s) => acc + (s.booked_seats || 0), 0);
  const ratings = sessions.filter(s => s.average_rating).map(s => parseFloat(s.average_rating));
  const avgRating = ratings.length ? (ratings.reduce((a, b) => a + b, 0) / ratings.length).toFixed(1) : '—';
  const totalEarned = sessions.reduce((acc, s) => acc + parseFloat(s.host_earned || 0), 0);

  const el = id => document.getElementById(id);
  if (el('stat-total-sessions')) el('stat-total-sessions').textContent = totalSessions;
  if (el('stat-total-bookings')) el('stat-total-bookings').textContent = totalBookings;
  if (el('stat-avg-rating')) el('stat-avg-rating').textContent = avgRating !== '—' ? '\u2605 ' + avgRating : '—';
  if (el('stat-total-earned')) el('stat-total-earned').textContent = '\u20b9' + totalEarned.toLocaleString('en-IN');
}

function renderHostedSessions() {
  const container = document.getElementById('hosted-sessions-container');
  if (!container) return;
  const filtered = activeHostedFilter
    ? cachedHostedSessions.filter(s => s.status === activeHostedFilter)
    : cachedHostedSessions;
  container.innerHTML = '';
  const emptyEl = document.getElementById('hosted-empty');
  if (emptyEl) emptyEl.style.display = filtered.length === 0 ? 'block' : 'none';
  filtered.forEach(s => container.appendChild(renderHostedSessionCard(s)));
}

function renderHostedSessionCard(session) {
  const div = document.createElement('div');
  div.style.cssText = 'background:white;border:1px solid #E2E8F0;border-radius:12px;padding:16px;margin-bottom:14px';

  const typeColor = TYPE_COLORS[session.session_type] || '#2563EB';
  const typeLabel = TYPE_LABELS[session.session_type] || session.session_type;
  const d = new Date(session.scheduled_at);
  const dateStr = d.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' });
  const timeStr = d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
  const statusColors = { upcoming:'#EFF6FF', live:'#DCFCE7', completed:'#F0FDF4', cancelled:'#FEF2F2' };
  const statusTextColors = { upcoming:'#1D4ED8', live:'#166534', completed:'#166534', cancelled:'#991B1B' };

  const skillsHtml = (session.skills_covered || []).slice(0, 4)
    .map(s => '<span style="background:#F1F5F9;color:#475569;font-size:11px;padding:2px 7px;border-radius:10px">'+s+'</span>').join('');

  let actionsHtml = '';
  if (session.status === 'upcoming') {
    actionsHtml =
      '<button onclick="addMeetingLink('+session.id+')" style="border:1px solid #E2E8F0;color:#374151;background:white;border-radius:7px;padding:7px 12px;font-size:12px;cursor:pointer">Add Meeting Link</button>'
      +'<button onclick="cancelHostedSession('+session.id+','+session.booked_seats+')" style="border:1px solid #EF4444;color:#EF4444;background:white;border-radius:7px;padding:7px 12px;font-size:12px;cursor:pointer">Cancel Session</button>';
  } else if (session.status === 'completed') {
    actionsHtml =
      '<button onclick="if(typeof openRatingModal===\'function\') openRatingModal('+session.id+', \'host_to_student\', \''+(session.title||'').replace(/'/g, "\\'")+'\', \'Students\')" style="border:none;background:#F59E0B;color:white;border-radius:7px;padding:7px 12px;font-size:12px;cursor:pointer">Rate Students ★</button>'
      +'<button onclick="showToast(\'Analytics coming soon!\',\'info\')" style="border:1px solid #E2E8F0;color:#374151;background:white;border-radius:7px;padding:7px 12px;font-size:12px;cursor:pointer">Session Analytics</button>';
  }

  div.innerHTML =
    '<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px">'
    +'<div style="flex:1;min-width:0">'
    +'<div style="display:flex;gap:6px;margin-bottom:6px">'
    +'<span style="background:'+typeColor+'22;color:'+typeColor+';font-size:11px;font-weight:600;padding:3px 8px;border-radius:10px">'+typeLabel+'</span>'
    +'<span style="background:'+(statusColors[session.status]||'#F1F5F9')+';color:'+(statusTextColors[session.status]||'#64748B')+';font-size:11px;font-weight:600;padding:3px 8px;border-radius:10px">'+session.status+'</span>'
    +'</div>'
    +'<div style="font-size:16px;font-weight:600;color:#0F172A;margin-bottom:6px">'+session.title+'</div>'
    +'<div style="display:flex;flex-wrap:wrap;gap:4px">'+(session.niche?'<span style="background:#EFF6FF;color:#2563EB;font-size:11px;padding:2px 7px;border-radius:10px">#'+session.niche+'</span>':'')+skillsHtml+'</div>'
    +'</div>'
    +'<div style="text-align:right;flex-shrink:0;margin-left:16px">'
    +'<div style="font-size:16px;font-weight:700;color:#2563EB">\u20b9'+parseFloat(session.host_earned||0).toLocaleString('en-IN')+'</div>'
    +'<div style="font-size:11px;color:#94A3B8">earned</div>'
    +'</div></div>'
    +'<div style="display:flex;gap:20px;font-size:13px;color:#64748B;margin:10px 0;flex-wrap:wrap">'
    +'<span>\ud83d\udcc5 '+dateStr+'</span><span>\ud83d\udd50 '+timeStr+'</span>'
    +'<span>\u23f1 '+session.duration_minutes+' min</span>'
    +'<span>\ud83d\udc65 '+session.booked_seats+'/'+session.max_seats+' seats</span>'
    +(session.average_rating?'<span>\u2605 '+parseFloat(session.average_rating).toFixed(1)+'</span>':'<span>No reviews</span>')
    +'</div>'
    +(actionsHtml?'<div style="display:flex;gap:8px;border-top:1px solid #F1F5F9;padding-top:12px;flex-wrap:wrap">'+actionsHtml+'</div>':'');

  return div;
}

async function addMeetingLink(sessionId) {
  const modal = document.getElementById('meeting-link-modal');
  if (!modal) return;
  modal.dataset.sessionId = sessionId;
  const input = document.getElementById('meeting-link-input');
  if (input) input.value = '';
  const errEl = document.getElementById('meeting-link-error');
  if (errEl) errEl.style.display = 'none';
  modal.style.display = 'flex';
}

async function saveMeetingLink() {
  const modal = document.getElementById('meeting-link-modal');
  const sessionId = modal?.dataset.sessionId;
  const link = document.getElementById('meeting-link-input')?.value.trim();
  const errEl = document.getElementById('meeting-link-error');
  if (!link) { if (errEl) { errEl.textContent = 'Please enter a meeting link.'; errEl.style.display = 'block'; } return; }
  const result = await apiFetch('/api/sessions/' + sessionId + '/meeting-link/', { method: 'PATCH', body: JSON.stringify({ meeting_link: link }) });
  if (result.ok) {
    if (modal) modal.style.display = 'none';
    showToast('Meeting link added! Students have been notified.', 'success');
    loadHostedSessions();
  } else {
    if (errEl) { errEl.textContent = 'Invalid URL. Please enter a valid meeting link.'; errEl.style.display = 'block'; }
  }
}

async function cancelHostedSession(sessionId, bookingCount) {
  const modal = document.getElementById('cancel-session-modal');
  if (!modal) return;
  modal.dataset.sessionId = sessionId;
  const msg = modal.querySelector('.booking-count-msg');
  if (msg) msg.textContent = 'All ' + bookingCount + ' confirmed students will be notified and fully refunded.';
  const reasonEl = document.getElementById('cancel-reason');
  if (reasonEl) reasonEl.value = '';
  modal.style.display = 'flex';
}

async function confirmCancelSession() {
  const modal = document.getElementById('cancel-session-modal');
  const sessionId = modal?.dataset.sessionId;
  const reason = document.getElementById('cancel-reason')?.value.trim();
  const result = await apiFetch('/api/sessions/' + sessionId + '/', {
    method: 'DELETE',
    body: JSON.stringify({ cancellation_reason: reason }),
  });
  if (result.ok) {
    if (modal) modal.style.display = 'none';
    showToast('Session cancelled. All students will be notified.', 'success');
    loadHostedSessions();
  } else {
    showToast('Failed to cancel session.', 'error');
  }
}

// ── Session Detail page ───────────────────────────────────────────────────────
async function initSessionDetailPage() {
  const pathParts = window.location.pathname.split('/').filter(Boolean);
  const sessionId = pathParts[1];
  if (!sessionId || isNaN(sessionId)) return;

  const result = await apiGet('/api/sessions/' + sessionId + '/');
  if (!result.ok) { showToast('Session not found.', 'error'); return; }
  const session = result.data;

  // Thumbnail
  if (session.thumbnail) {
    const tc = document.getElementById('thumbnail-container');
    const ti = document.getElementById('detail-thumbnail');
    if (tc) tc.style.display = 'block';
    if (ti) ti.src = session.thumbnail;
  }

  // Host
  const hostName = (session.host?.first_name || '') + ' ' + (session.host?.last_name || '');
  const hostInitials = ((session.host?.first_name?.[0] || '') + (session.host?.last_name?.[0] || '')).toUpperCase() || '?';
  const el = id => document.getElementById(id);
  if (el('host-name')) el('host-name').textContent = hostName;
  if (el('host-role-detail')) el('host-role-detail').textContent = session.host?.role_detail?.designation || session.host?.role_detail?.company || '';
  if (el('host-college')) el('host-college').textContent = session.host?.college || '';
  if (session.host?.profile_pic) {
    const pic = el('host-pic'); const initEl = el('host-initials');
    if (pic) { pic.src = session.host.profile_pic; pic.style.display = 'block'; }
    if (initEl) initEl.style.display = 'none';
  } else {
    if (el('host-initials')) el('host-initials').textContent = hostInitials;
  }
  const avgR = session.average_rating ? parseFloat(session.average_rating) : 0;
  if (el('host-stars')) {
    el('host-stars').innerHTML = '\u2605'.repeat(Math.round(avgR)) + '\u2606'.repeat(5 - Math.round(avgR));
    el('host-stars').style.color = '#F59E0B';
  }
  if (el('host-review-count')) el('host-review-count').textContent = '(' + (session.review_count || 0) + ' reviews)';
  if (el('host-profile-link')) el('host-profile-link').href = '/' + session.host?.role + '/' + session.host?.id + '/';

  // Type + status badges
  const typeColor = TYPE_COLORS[session.session_type] || '#2563EB';
  const typeLabel = TYPE_LABELS[session.session_type] || session.session_type;
  if (el('session-type-badge')) {
    el('session-type-badge').textContent = typeLabel;
    el('session-type-badge').style.cssText = 'background:' + typeColor + '22;color:' + typeColor + ';padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600';
  }
  if (el('session-status-badge')) {
    const sc = STATUS_COLORS[session.status] || { bg: '#F1F5F9', text: '#64748B' };
    el('session-status-badge').textContent = session.status;
    el('session-status-badge').style.cssText = 'background:' + sc.bg + ';color:' + sc.text + ';padding:3px 10px;border-radius:20px;font-size:12px;font-weight:600';
  }

  // Title + description
  if (el('session-title')) el('session-title').textContent = session.title;
  if (el('session-description')) {
    const full = session.description || '';
    if (full.length > 300) {
      el('session-description').textContent = full.slice(0, 300) + '...';
      el('session-description').dataset.full = full;
      if (el('read-more-link')) el('read-more-link').style.display = 'inline';
    } else {
      el('session-description').textContent = full;
    }
  }

  // Niche + skills
  const nsContainer = el('session-niche-skills');
  if (nsContainer) {
    nsContainer.innerHTML = '';
    if (session.niche) nsContainer.innerHTML += '<span style="background:#EFF6FF;color:#2563EB;font-size:12px;padding:3px 10px;border-radius:20px">#' + session.niche + '</span>';
    (session.skills_covered || []).forEach(s => {
      nsContainer.innerHTML += '<span style="background:#F1F5F9;color:#475569;font-size:12px;padding:3px 10px;border-radius:20px">' + s + '</span>';
    });
  }

  // Schedule
  const d = new Date(session.scheduled_at);
  if (el('detail-date')) el('detail-date').textContent = d.toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });
  if (el('detail-time')) el('detail-time').textContent = d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }) + ' IST';
  if (el('detail-duration')) el('detail-duration').textContent = session.duration_minutes + ' minutes';
  if (el('detail-seats')) el('detail-seats').textContent = session.available_seats + ' of ' + session.max_seats + ' seats remaining';
  if (session.session_type === 'cohort' && el('detail-bundle-row')) {
    el('detail-bundle-row').style.display = 'block';
    if (el('detail-bundle')) el('detail-bundle').textContent = session.total_sessions_in_bundle + ' sessions';
  }
  if (session.meeting_link && el('meeting-link-row')) {
    el('meeting-link-row').style.display = 'block';
    if (el('meeting-link-anchor')) el('meeting-link-anchor').href = session.meeting_link;
  }

  updateBookingCard(session);
  loadSessionReviews(sessionId);

  const bookBtn = el('book-now-btn');
  if (bookBtn) bookBtn.addEventListener('click', () => bookSession(session.id, false));

  const leaveReviewBtn = el('leave-review-btn');
  if (leaveReviewBtn) leaveReviewBtn.addEventListener('click', () => {
    const overlay = el('review-modal-overlay');
    if (overlay) overlay.style.display = 'flex';
  });

  const submitReviewBtn = el('submit-review-btn');
  if (submitReviewBtn) submitReviewBtn.addEventListener('click', () => submitReview(sessionId));

  const cancelLink = el('cancel-booking-link');
  if (cancelLink) cancelLink.addEventListener('click', e => { e.preventDefault(); if (currentBookingId) cancelBooking(currentBookingId); });
}

function updateBookingCard(session) {
  const el = id => document.getElementById(id);

  // Price display
  const priceEl = el('booking-price-display');
  if (priceEl) {
    priceEl.innerHTML = session.is_free
      ? '<div style="font-size:24px;font-weight:700;color:#0F6E56">FREE</div>'
      : '<div style="font-size:28px;font-weight:700;color:#2563EB">\u20b9' + parseFloat(session.price).toLocaleString('en-IN') + '</div><div style="font-size:13px;color:#64748B">per seat</div>';
  }

  // Seats progress
  const pct = session.max_seats > 0 ? (session.booked_seats / session.max_seats * 100) : 0;
  const bar = el('seats-progress-bar');
  if (bar) bar.style.width = pct + '%';
  const txt = el('seats-progress-text');
  if (txt) txt.textContent = session.booked_seats + ' of ' + session.max_seats + ' seats booked \u00b7 ' + session.available_seats + ' remaining';

  // Show correct state card
  ['booking-card-upcoming', 'booking-card-confirmed', 'booking-card-full', 'booking-card-completed'].forEach(id => {
    const c = el(id); if (c) c.style.display = 'none';
  });

  if (session.status === 'completed') {
    const c = el('booking-card-completed'); if (c) c.style.display = 'block';
    return;
  }
  if (session.is_full && !session.is_booked) {
    const c = el('booking-card-full'); if (c) c.style.display = 'block';
    return;
  }
  if (session.is_booked) {
    const c = el('booking-card-confirmed'); if (c) c.style.display = 'block';
    if (session.meeting_link) {
      const mlRow = el('confirmed-meeting-link-row'); if (mlRow) mlRow.style.display = 'block';
      const mlLink = el('confirmed-meeting-link'); if (mlLink) mlLink.href = session.meeting_link;
    }
    // Find booking id for cancel
    apiGet('/api/sessions/my-bookings/?status=confirmed').then(r => {
      if (r.ok) {
        const b = (r.data || []).find(bk => bk.session?.id === session.id);
        if (b) currentBookingId = b.id;
      }
    });
    return;
  }

  const c = el('booking-card-upcoming'); if (c) c.style.display = 'block';
  const bookBtn = el('book-now-btn');
  if (bookBtn) {
    if (session.is_full) {
      bookBtn.textContent = 'Session Full'; bookBtn.disabled = true;
      bookBtn.style.background = '#F1F5F9'; bookBtn.style.color = '#94A3B8';
    } else if (session.is_free && !demoSessionUsed) {
      bookBtn.textContent = 'Book Free Demo'; bookBtn.style.background = '#0F6E56';
    } else {
      bookBtn.textContent = 'Book Now \u2014 \u20b9' + parseFloat(session.price).toLocaleString('en-IN');
    }
  }
}

async function refreshBookingCard() {
  const pathParts = window.location.pathname.split('/').filter(Boolean);
  const sessionId = pathParts[1];
  if (!sessionId) return;
  const result = await apiGet('/api/sessions/' + sessionId + '/');
  if (result.ok) updateBookingCard(result.data);
}

async function loadSessionReviews(sessionId) {
  const result = await apiGet('/api/sessions/' + sessionId + '/reviews/');
  if (!result.ok) return;
  const data = result.data;
  const reviews = data.reviews || [];
  const container = document.getElementById('reviews-container');
  const noReviews = document.getElementById('no-reviews-msg');
  const header = document.getElementById('reviews-avg-stars');
  const countLabel = document.getElementById('reviews-count-label');

  if (header && data.average_rating) {
    const r = Math.round(data.average_rating);
    header.textContent = '\u2605'.repeat(r) + '\u2606'.repeat(5 - r) + ' ' + parseFloat(data.average_rating).toFixed(1);
  }
  if (countLabel) countLabel.textContent = '(' + (data.review_count || 0) + ' reviews)';

  if (!container) return;
  container.innerHTML = '';
  if (reviews.length === 0) { if (noReviews) noReviews.style.display = 'block'; return; }
  if (noReviews) noReviews.style.display = 'none';

  reviews.forEach(r => {
    const div = document.createElement('div');
    div.style.cssText = 'display:flex;gap:12px;padding:12px 0;border-bottom:1px solid #F1F5F9';
    const initials = r.is_anonymous ? 'A' : ((r.reviewer?.name?.[0] || '?')).toUpperCase();
    const stars = '\u2605'.repeat(r.rating) + '\u2606'.repeat(5 - r.rating);
    div.innerHTML =
      '<div style="width:36px;height:36px;border-radius:50%;background:#EFF6FF;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;color:#2563EB;flex-shrink:0">'+initials+'</div>'
      +'<div style="flex:1;min-width:0">'
      +'<div style="display:flex;align-items:center;gap:8px;margin-bottom:3px">'
      +'<span style="font-size:13px;font-weight:600;color:#0F172A">'+(r.is_anonymous?'Anonymous':(r.reviewer?.name||'User'))+'</span>'
      +'<span style="font-size:11px;color:#94A3B8">'+new Date(r.created_at).toLocaleDateString('en-IN')+'</span>'
      +'</div>'
      +'<div style="color:#F59E0B;font-size:14px;margin-bottom:4px">'+stars+'</div>'
      +(r.review_text?'<p style="font-size:13px;color:#374151;margin:0">'+r.review_text+'</p>':'')
      +'</div>';
    container.appendChild(div);
  });
}

async function submitReview(sessionId) {
  const errEl = document.getElementById('review-error');
  if (errEl) errEl.style.display = 'none';

  if (!selectedRating) {
    if (errEl) { errEl.textContent = 'Please select a rating.'; errEl.style.display = 'block'; }
    return;
  }

  // Find the completed booking for this session
  const bookingsResult = await apiGet('/api/sessions/my-bookings/?status=completed');
  if (!bookingsResult.ok) return;
  const booking = (bookingsResult.data || []).find(b => b.session?.id === parseInt(sessionId));
  if (!booking) {
    if (errEl) { errEl.textContent = 'No completed booking found for this session.'; errEl.style.display = 'block'; }
    return;
  }

  const payload = {
    booking: booking.id,
    rating: selectedRating,
    review_text: document.getElementById('review-text')?.value.trim() || '',
    is_anonymous: document.getElementById('review-anonymous')?.checked || false,
  };

  const result = await apiPost('/api/sessions/bookings/' + booking.id + '/review/', payload);
  if (result.ok) {
    document.getElementById('review-modal-overlay').style.display = 'none';
    showToast('Review submitted! Thank you.', 'success');
    loadSessionReviews(sessionId);
    const leaveBtn = document.getElementById('leave-review-btn');
    if (leaveBtn) leaveBtn.style.display = 'none';
  } else {
    const msg = result.data?.non_field_errors?.[0] || result.data?.detail || 'Failed to submit review.';
    if (errEl) { errEl.textContent = msg; errEl.style.display = 'block'; }
  }
}

// selectedRating is declared in the template inline script for session_detail.html
// but we need a fallback here for when sessions.js loads on other pages
if (typeof selectedRating === 'undefined') var selectedRating = 0;

// ── DOMContentLoaded: page init ───────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const path = window.location.pathname;

  // ── Marketplace ──
  if (path === '/sessions/' || path === '/sessions') {
    loadSessions(true);

    const applyBtn = document.getElementById('apply-filters-btn');
    if (applyBtn) applyBtn.addEventListener('click', applyFilters);

    const clearLink = document.getElementById('clear-filters-link');
    if (clearLink) clearLink.addEventListener('click', e => { e.preventDefault(); clearFilters(); });

    const emptyClear = document.getElementById('empty-clear-link');
    if (emptyClear) emptyClear.addEventListener('click', e => { e.preventDefault(); clearFilters(); });

    const priceSlider = document.getElementById('price-slider');
    if (priceSlider) priceSlider.addEventListener('input', e => updatePriceDisplay(e.target.value));

    const searchInput = document.getElementById('session-search');
    if (searchInput) {
      let searchTimer;
      searchInput.addEventListener('input', () => {
        clearTimeout(searchTimer);
        searchTimer = setTimeout(applyFilters, 400);
      });
    }

    const loadMoreBtn = document.getElementById('load-more-btn');
    if (loadMoreBtn) loadMoreBtn.addEventListener('click', () => loadSessions(false));

    const hostBtn = document.getElementById('host-session-btn');
    if (hostBtn) hostBtn.addEventListener('click', openCreateSessionModal);

    const closeModal = document.getElementById('close-create-modal');
    if (closeModal) closeModal.addEventListener('click', closeCreateSessionModal);

    const publishBtn = document.getElementById('publish-session-btn');
    if (publishBtn) publishBtn.addEventListener('click', submitCreateSession);

    const sortEl = document.getElementById('sessions-sort');
    if (sortEl) sortEl.addEventListener('change', e => { activeSessionFilters['ordering'] = e.target.value; loadSessions(true); });

    // Tab pills
    document.querySelectorAll('[id^="tab-"]').forEach(tab => {
      tab.addEventListener('click', () => {
        document.querySelectorAll('[id^="tab-"]').forEach(t => { t.classList.remove('active-tab'); t.style.background='white'; t.style.color='#64748B'; t.style.borderColor='#E2E8F0'; });
        tab.classList.add('active-tab'); tab.style.background='#2563EB'; tab.style.color='white'; tab.style.borderColor='#2563EB';
        const filter = tab.dataset.filter;
        if (filter) activeSessionFilters['type'] = filter;
        else delete activeSessionFilters['type'];
        loadSessions(true);
      });
    });

    // Topic pills
    document.querySelectorAll('.topic-pill').forEach(pill => {
      pill.addEventListener('click', () => {
        const niche = pill.dataset.niche;
        if (pill.classList.contains('active')) {
          pill.classList.remove('active');
          activeNiches = activeNiches.filter(n => n !== niche);
        } else {
          pill.classList.add('active');
          activeNiches = [niche]; // single niche filter
          document.querySelectorAll('.topic-pill').forEach(p => { if (p !== pill) p.classList.remove('active'); });
        }
        if (activeNiches.length) activeSessionFilters['niche'] = activeNiches[0];
        else delete activeSessionFilters['niche'];
        loadSessions(true);
      });
    });
  }

  // ── Session Detail ──
  if (path.startsWith('/sessions/') && path !== '/sessions/my-bookings/' && path !== '/sessions/hosting/') {
    const parts = path.split('/').filter(Boolean);
    if (parts.length === 2 && !isNaN(parts[1])) {
      initSessionDetailPage();
    }
  }

  // ── My Bookings ──
  if (path === '/sessions/my-bookings/') {
    loadMyBookings();
    document.querySelectorAll('.booking-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        document.querySelectorAll('.booking-tab').forEach(t => {
          t.style.background = 'white'; t.style.color = '#64748B'; t.style.borderColor = '#E2E8F0';
        });
        tab.style.background = '#2563EB'; tab.style.color = 'white'; tab.style.borderColor = '#2563EB';
        activeBookingFilter = tab.dataset.filter || 'all';
        renderBookings();
      });
    });
  }

  // ── Hosted Sessions ──
  if (path === '/sessions/hosting/') {
    loadHostedSessions(true);

    const hostBtn = document.getElementById('host-session-btn');
    if (hostBtn) hostBtn.addEventListener('click', openCreateSessionModal);

    const closeModal = document.getElementById('close-create-modal');
    if (closeModal) closeModal.addEventListener('click', closeCreateSessionModal);

    const publishBtn = document.getElementById('publish-session-btn');
    if (publishBtn) publishBtn.addEventListener('click', submitCreateSession);

    const saveLinkBtn = document.getElementById('save-meeting-link-btn');
    if (saveLinkBtn) saveLinkBtn.addEventListener('click', saveMeetingLink);

    const confirmCancelBtn = document.getElementById('confirm-cancel-session-btn');
    if (confirmCancelBtn) confirmCancelBtn.addEventListener('click', confirmCancelSession);

    document.querySelectorAll('.hosted-tab').forEach(tab => {
      tab.addEventListener('click', () => {
        document.querySelectorAll('.hosted-tab').forEach(t => t.classList.remove('active-tab'));
        tab.classList.add('active-tab');
        activeHostedFilter = tab.dataset.filter || '';
        renderHostedSessions();
      });
    });
  }
});
