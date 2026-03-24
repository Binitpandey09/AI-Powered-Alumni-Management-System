/**
 * payments.js — Wallet, Invoices, AI Tools, Admin Payments
 * Dispatches on PAGE_NAME constant set by each template.
 */

// ── State ─────────────────────────────────────────────────────────────────────
let _walletData = null;
let _allTransactions = [];
let _currentFilter = 'all';
let _earningsChart = null;
let _revenueChart = null;
let _pendingPayoutId = null;
let _rejectTargetId = null;
let _processTargetId = null;

// ── Entry point ───────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const page = typeof PAGE_NAME !== 'undefined' ? PAGE_NAME : '';
  if (page === 'wallet')          loadWalletData();
  else if (page === 'admin_payments') loadAdminPayments();
  else if (typeof INVOICE_NUMBER !== 'undefined') loadInvoiceData();
  else if (typeof TOOL_TYPE !== 'undefined')      initToolPage();
});

// ── Helpers ───────────────────────────────────────────────────────────────────
function formatINR(amount) {
  return '₹' + Number(amount || 0).toLocaleString('en-IN', {
    minimumFractionDigits: 2, maximumFractionDigits: 2,
  });
}

function getTransactionTypeColor(type) {
  const map = {
    session_booking: 'blue',
    ai_interview:    'violet',
    resume_check:    'indigo',
    resume_builder:  'purple',
    skill_gap:       'fuchsia',
    referral_boost:  'amber',
    payout:          'emerald',
    refund:          'red',
  };
  return map[type] || 'slate';
}

function getStatusBadgeHtml(status) {
  const map = {
    completed: 'bg-emerald-100 text-emerald-700',
    pending:   'bg-amber-100 text-amber-700',
    failed:    'bg-red-100 text-red-700',
    refunded:  'bg-slate-100 text-slate-600',
    cancelled: 'bg-slate-100 text-slate-500',
    approved:  'bg-blue-100 text-blue-700',
    processed: 'bg-emerald-100 text-emerald-700',
    rejected:  'bg-red-100 text-red-700',
  };
  const cls = map[status] || 'bg-slate-100 text-slate-600';
  return `<span class="px-2 py-0.5 rounded-full text-xs font-medium ${cls}">${status}</span>`;
}

function getNextMonday() {
  const today = new Date();
  const day = today.getDay();
  const diff = day === 1 ? 7 : (8 - day) % 7;
  const next = new Date(today);
  next.setDate(today.getDate() + diff);
  return next.toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long' });
}

function extractErr(err) {
  if (!err) return 'Something went wrong.';
  if (typeof err === 'string') return err;
  if (err.error) return err.error;
  if (err.detail) return err.detail;
  return JSON.stringify(err);
}

// ── WALLET PAGE ───────────────────────────────────────────────────────────────
async function loadWalletData() {
  try {
    const [walletRes, txRes] = await Promise.all([
      apiGet('/api/payments/wallet/'),
      apiGet('/api/payments/transactions/'),
    ]);

    if (!walletRes.ok) {
      showToast('Failed to load wallet data', 'error');
      return;
    }

    const data = walletRes.data;
    _walletData = data;

    populateWalletCards(data.wallet);
    renderEarningsChart(data.monthly_breakdown || []);
    renderBankDetailsCard(data.wallet);
    updatePayoutButton(data.wallet);
    updateNextPayoutDisplay(data.next_payout_date);

    if (txRes.ok) {
      _allTransactions = txRes.data.results || txRes.data || [];
      renderTransactionsTable(_allTransactions);
    }

    const payoutRes = await apiGet('/api/payments/payout/');
    if (payoutRes.ok) renderPayoutHistory(payoutRes.data);

  } catch (err) {
    showToast('Failed to load wallet', 'error');
  }
}

function populateWalletCards(wallet) {
  const cards = [
    {
      label: 'Available Balance',
      value: formatINR(wallet.available_for_withdrawal),
      sub: 'Ready to withdraw',
      color: 'text-emerald-600', bg: 'bg-emerald-50',
      icon: `<path stroke-linecap="round" stroke-linejoin="round" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"/>`,
    },
    {
      label: 'This Month',
      value: formatINR(wallet.this_month_earned),
      sub: 'Net earnings (70%)',
      color: 'text-blue-600', bg: 'bg-blue-50',
      icon: `<path stroke-linecap="round" stroke-linejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>`,
    },
    {
      label: 'All Time Earned',
      value: formatINR(wallet.total_earned),
      sub: 'Lifetime net earnings',
      color: 'text-violet-600', bg: 'bg-violet-50',
      icon: `<path stroke-linecap="round" stroke-linejoin="round" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>`,
    },
    {
      label: 'Total Withdrawn',
      value: formatINR(wallet.total_withdrawn),
      sub: 'Paid out to bank',
      color: 'text-amber-600', bg: 'bg-amber-50',
      icon: `<path stroke-linecap="round" stroke-linejoin="round" d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z"/>`,
    },
  ];

  document.getElementById('metric-cards').innerHTML = cards.map(c => `
    <div class="bg-white rounded-xl border border-slate-200 p-5">
      <div class="flex items-start justify-between">
        <div>
          <p class="text-xs font-medium text-slate-500 uppercase tracking-wide">${c.label}</p>
          <p class="text-2xl font-bold text-slate-800 mt-1">${c.value}</p>
          <p class="text-xs text-slate-400 mt-1">${c.sub}</p>
        </div>
        <div class="w-10 h-10 rounded-lg ${c.bg} flex items-center justify-center flex-shrink-0">
          <svg class="w-5 h-5 ${c.color}" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">${c.icon}</svg>
        </div>
      </div>
    </div>`).join('');
}

function updatePayoutButton(wallet) {
  const btn = document.getElementById('request-payout-btn');
  const tooltip = document.getElementById('payout-btn-tooltip');
  const alert = document.getElementById('pending-payout-alert');
  const alertText = document.getElementById('pending-payout-text');

  const avail = parseFloat(wallet.available_for_withdrawal || 0);
  const hasPending = wallet.has_pending_payout;

  if (hasPending) {
    btn.disabled = true;
    if (tooltip) { tooltip.textContent = 'You have a pending payout request'; tooltip.classList.remove('hidden'); }
    if (alert) { alert.classList.remove('hidden'); alertText.textContent = 'You have a pending payout request being processed.'; }
  } else if (avail < 500) {
    btn.disabled = true;
    if (tooltip) { tooltip.textContent = `Minimum ₹500 required (you have ${formatINR(avail)})`; tooltip.classList.remove('hidden'); }
  }
}

function updateNextPayoutDisplay(dateStr) {
  const el = document.getElementById('next-payout-date');
  if (el && dateStr) {
    const d = new Date(dateStr);
    el.textContent = d.toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long' });
  }
}

// ── Transactions Table ────────────────────────────────────────────────────────
function renderTransactionsTable(transactions) {
  const body = document.getElementById('transactions-body');
  if (!body) return;

  if (!transactions.length) {
    body.innerHTML = `<div class="p-8 text-center text-slate-400 text-sm">No transactions yet.</div>`;
    return;
  }

  const rows = transactions.map(tx => {
    const date = new Date(tx.created_at).toLocaleDateString('en-IN', {
      day: '2-digit', month: 'short', year: 'numeric',
    });
    const color = getTransactionTypeColor(tx.transaction_type);
    const typeLabel = tx.transaction_type_display || tx.transaction_type;
    const isPayee = tx.role === 'payee';
    const amountHtml = isPayee
      ? `<span class="text-emerald-600 font-semibold">+${formatINR(tx.payee_amount)}</span>`
      : `<span class="text-red-500 font-semibold">-${formatINR(tx.gross_amount)}</span>`;
    const invoiceBtn = tx.invoice_number
      ? `<a href="/payments/invoice/${tx.invoice_number}/" target="_blank"
           class="text-xs text-blue-600 hover:underline font-medium">${tx.invoice_number}</a>`
      : `<span class="text-slate-400 text-xs">—</span>`;

    return `
      <tr class="border-t border-slate-100 hover:bg-slate-50 transition-colors">
        <td class="px-5 py-3">${invoiceBtn}</td>
        <td class="px-5 py-3 text-xs text-slate-500">${date}</td>
        <td class="px-5 py-3">
          <span class="px-2 py-0.5 rounded-full text-xs font-medium bg-${color}-100 text-${color}-700">${typeLabel}</span>
        </td>
        <td class="px-5 py-3 text-sm text-slate-700 max-w-xs truncate">${tx.description || '—'}</td>
        <td class="px-5 py-3 text-sm font-mono">${formatINR(tx.gross_amount)}</td>
        <td class="px-5 py-3 text-sm font-mono">${isPayee ? formatINR(tx.payee_amount) : '—'}</td>
        <td class="px-5 py-3">${getStatusBadgeHtml(tx.status)}</td>
        <td class="px-5 py-3">${amountHtml}</td>
      </tr>`;
  }).join('');

  body.innerHTML = `
    <div class="overflow-x-auto">
      <table class="w-full text-left text-sm">
        <thead>
          <tr class="bg-slate-50 text-xs font-semibold text-slate-500 uppercase tracking-wide">
            <th class="px-5 py-3">Invoice</th>
            <th class="px-5 py-3">Date</th>
            <th class="px-5 py-3">Type</th>
            <th class="px-5 py-3">Description</th>
            <th class="px-5 py-3">Amount</th>
            <th class="px-5 py-3">My Share</th>
            <th class="px-5 py-3">Status</th>
            <th class="px-5 py-3">Net</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

function filterTransactions(filter) {
  _currentFilter = filter;

  // Update tab styles
  document.querySelectorAll('.tx-filter-btn').forEach(btn => {
    const isActive = btn.dataset.filter === filter;
    btn.className = isActive
      ? 'tx-filter-btn px-3 py-1 text-xs font-medium rounded-md bg-white text-slate-700 shadow-sm transition-all'
      : 'tx-filter-btn px-3 py-1 text-xs font-medium rounded-md text-slate-500 hover:text-slate-700 transition-all';
  });

  let filtered = _allTransactions;
  if (filter === 'earned')   filtered = _allTransactions.filter(tx => tx.role === 'payee');
  else if (filter === 'paid') filtered = _allTransactions.filter(tx => tx.role === 'payer');
  else if (filter === 'refunded') filtered = _allTransactions.filter(tx => tx.status === 'refunded');

  renderTransactionsTable(filtered);
}

function exportTransactionsCSV() {
  const data = _currentFilter === 'all' ? _allTransactions
    : _currentFilter === 'earned'   ? _allTransactions.filter(tx => tx.role === 'payee')
    : _currentFilter === 'paid'     ? _allTransactions.filter(tx => tx.role === 'payer')
    : _allTransactions.filter(tx => tx.status === 'refunded');

  if (!data.length) { showToast('No transactions to export', 'error'); return; }

  const headers = ['Invoice', 'Date', 'Type', 'Description', 'Amount (INR)', 'My Share (INR)', 'Status'];
  const rows = data.map(tx => [
    tx.invoice_number || '',
    new Date(tx.created_at).toLocaleDateString('en-IN'),
    tx.transaction_type,
    `"${(tx.description || '').replace(/"/g, '""')}"`,
    tx.gross_amount,
    tx.role === 'payee' ? tx.payee_amount : '',
    tx.status,
  ]);

  const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `transactions_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// ── Payout Modal ──────────────────────────────────────────────────────────────
function openPayoutModal() {
  const wallet = _walletData && _walletData.wallet;
  if (!wallet) return;

  const avail = parseFloat(wallet.available_for_withdrawal || 0);
  const el = document.getElementById('modal-available-balance');
  if (el) el.textContent = formatINR(avail);

  const nextEl = document.getElementById('modal-next-monday');
  if (nextEl) nextEl.textContent = getNextMonday();

  // Populate bank preview
  const bankName = document.getElementById('payout-bank-name');
  const bankAcc  = document.getElementById('payout-bank-acc');
  if (wallet.bank_name) {
    if (bankName) bankName.textContent = wallet.bank_name;
    if (bankAcc)  bankAcc.textContent  = wallet.account_masked ? `****${wallet.account_masked}` : '—';
  } else {
    if (bankName) bankName.textContent = 'No bank account linked';
    if (bankAcc)  bankAcc.textContent  = 'Add bank details first';
  }

  document.getElementById('payout-modal').classList.remove('hidden');
}

function closePayoutModal() {
  document.getElementById('payout-modal').classList.add('hidden');
  const inp = document.getElementById('payout-amount-input');
  if (inp) inp.value = '';
  const err = document.getElementById('payout-amount-error');
  if (err) err.classList.add('hidden');
}

function fillMaxAmount() {
  const wallet = _walletData && _walletData.wallet;
  if (!wallet) return;
  const inp = document.getElementById('payout-amount-input');
  if (inp) { inp.value = parseFloat(wallet.available_for_withdrawal || 0).toFixed(2); validatePayoutAmount(); }
}

function validatePayoutAmount() {
  const wallet = _walletData && _walletData.wallet;
  const inp = document.getElementById('payout-amount-input');
  const err = document.getElementById('payout-amount-error');
  const btn = document.getElementById('payout-submit-btn');
  if (!inp || !err || !wallet) return;

  const val = parseFloat(inp.value);
  const avail = parseFloat(wallet.available_for_withdrawal || 0);

  if (isNaN(val) || val <= 0) {
    err.textContent = 'Enter a valid amount.'; err.classList.remove('hidden');
    btn.disabled = true; return;
  }
  if (val < 500) {
    err.textContent = 'Minimum withdrawal is ₹500.'; err.classList.remove('hidden');
    btn.disabled = true; return;
  }
  if (val > avail) {
    err.textContent = `Exceeds available balance (${formatINR(avail)}).`; err.classList.remove('hidden');
    btn.disabled = true; return;
  }
  err.classList.add('hidden');
  btn.disabled = false;
}

async function submitPayoutRequest() {
  const inp = document.getElementById('payout-amount-input');
  const btn = document.getElementById('payout-submit-btn');
  const amount = parseFloat(inp ? inp.value : 0);
  if (!amount || amount < 500) { validatePayoutAmount(); return; }

  btn.disabled = true;
  btn.textContent = 'Submitting…';

  try {
    const result = await apiPost('/api/payments/payout/', { amount });
    if (!result.ok) { showToast(extractErr(result.error), 'error'); return; }
    showToast(result.data.message || 'Payout request submitted!', 'success');
    closePayoutModal();
    loadWalletData();
  } catch (err) {
    showToast(extractErr(err), 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Request Payout';
  }
}

// ── Payout History ────────────────────────────────────────────────────────────
function renderPayoutHistory(payouts) {
  const body = document.getElementById('payout-history-body');
  if (!body) return;

  if (!payouts.length) {
    body.innerHTML = `<div class="p-8 text-center text-slate-400 text-sm">No payout requests yet.</div>`;
    return;
  }

  const rows = payouts.map(p => {
    const date = new Date(p.requested_at).toLocaleDateString('en-IN', {
      day: '2-digit', month: 'short', year: 'numeric',
    });
    const cancelBtn = p.status === 'pending'
      ? `<button onclick="cancelPayout(${p.id})"
           class="text-xs text-red-500 hover:underline font-medium">Cancel</button>`
      : '';
    return `
      <tr class="border-t border-slate-100 hover:bg-slate-50 transition-colors">
        <td class="px-5 py-3 text-sm font-mono text-slate-700">${formatINR(p.amount)}</td>
        <td class="px-5 py-3 text-xs text-slate-500">${date}</td>
        <td class="px-5 py-3">${getStatusBadgeHtml(p.status)}</td>
        <td class="px-5 py-3 text-xs text-slate-500">${p.transaction_reference || '—'}</td>
        <td class="px-5 py-3">${cancelBtn}</td>
      </tr>`;
  }).join('');

  body.innerHTML = `
    <div class="overflow-x-auto">
      <table class="w-full text-left text-sm">
        <thead>
          <tr class="bg-slate-50 text-xs font-semibold text-slate-500 uppercase tracking-wide">
            <th class="px-5 py-3">Amount</th>
            <th class="px-5 py-3">Requested</th>
            <th class="px-5 py-3">Status</th>
            <th class="px-5 py-3">Reference</th>
            <th class="px-5 py-3"></th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

async function cancelPayout(payoutId) {
  if (!confirm('Cancel this payout request?')) return;
  try {
    const result = await apiDelete(`/api/payments/payout/${payoutId}/`);
    if (!result.ok) { showToast(extractErr(result.error), 'error'); return; }
    showToast('Payout request cancelled.', 'success');
    loadWalletData();
  } catch (err) {
    showToast(extractErr(err), 'error');
  }
}

// ── Bank Details Modal ────────────────────────────────────────────────────────
function renderBankDetailsCard(wallet) {
  const body = document.getElementById('bank-card-body');
  if (!body) return;

  const bankName = wallet.bank_name;
  if (!bankName) return; // keep default empty state

  const masked = wallet.account_masked ? `****${wallet.account_masked}` : '****';
  body.innerHTML = `
    <div class="space-y-3 w-full">
      <div class="flex items-center justify-between">
        <span class="text-xs text-slate-500">Bank</span>
        <span class="text-sm font-semibold text-slate-800">${bankName}</span>
      </div>
      <div class="flex items-center justify-between">
        <span class="text-xs text-slate-500">Account</span>
        <span class="text-sm font-mono text-slate-700">${masked}</span>
      </div>
      <div class="flex items-center justify-between">
        <span class="text-xs text-slate-500">IFSC</span>
        <span class="text-sm font-mono text-slate-700">${wallet.ifsc_code || '—'}</span>
      </div>
      ${wallet.upi_id ? `
      <div class="flex items-center justify-between">
        <span class="text-xs text-slate-500">UPI</span>
        <span class="text-sm text-slate-700">${wallet.upi_id}</span>
      </div>` : ''}
    </div>`;
}

function openBankModal() {
  // Pre-fill if wallet has bank data
  const wallet = _walletData && _walletData.wallet;
  if (wallet) {
    const setVal = (id, val) => { const el = document.getElementById(id); if (el && val) el.value = val; };
    setVal('bank-name',   wallet.bank_name);
    setVal('bank-ifsc',   wallet.ifsc_code);
    setVal('bank-upi',    wallet.upi_id);
    setVal('bank-holder', wallet.account_holder_name);
  }
  const m = document.getElementById('bank-modal');
  m.classList.remove('hidden');
  m.classList.add('flex');
}

function closeBankModal() {
  const m = document.getElementById('bank-modal');
  m.classList.add('hidden');
  m.classList.remove('flex');
}

async function saveBankDetails(e) {
  e.preventDefault();
  const btn = document.getElementById('bank-save-btn');
  btn.disabled = true;
  btn.textContent = 'Saving…';

  const payload = {
    account_holder_name: document.getElementById('bank-holder').value.trim(),
    account_number:      document.getElementById('bank-account').value.trim(),
    ifsc_code:           document.getElementById('bank-ifsc').value.trim().toUpperCase(),
    bank_name:           document.getElementById('bank-name').value.trim(),
    branch:              document.getElementById('bank-branch').value.trim(),
    upi_id:              document.getElementById('bank-upi').value.trim(),
  };

  // Determine endpoint based on user role (alumni or faculty)
  const endpoint = '/api/sessions/bank-details/';
  try {
    const result = await apiPost(endpoint, payload);
    if (!result.ok) { showToast(extractErr(result.error), 'error'); return; }
    showToast('Bank details saved successfully', 'success');
    closeBankModal();
    loadWalletData();
  } catch (err) {
    showToast(extractErr(err), 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Save Details';
  }
}

// ── Earnings Chart ────────────────────────────────────────────────────────────
function renderEarningsChart(monthly) {
  const ctx = document.getElementById('earningsChart');
  if (!ctx) return;
  if (_earningsChart) _earningsChart.destroy();

  _earningsChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: monthly.map(m => m.month_short || m.month),
      datasets: [{
        label: 'Net Earnings (₹)',
        data: monthly.map(m => m.earned || 0),
        backgroundColor: 'rgba(99, 102, 241, 0.85)',
        borderRadius: 6,
        borderSkipped: false,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => `Net: ${formatINR(ctx.parsed.y)}`,
          },
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { callback: v => '₹' + Number(v).toLocaleString('en-IN'), font: { size: 11 } },
          grid: { color: 'rgba(0,0,0,0.05)' },
        },
        x: { ticks: { font: { size: 11 } }, grid: { display: false } },
      },
    },
  });
}

// ── INVOICE PAGE ──────────────────────────────────────────────────────────────
async function loadInvoiceData() {
  const invoiceNumber = typeof INVOICE_NUMBER !== 'undefined' ? INVOICE_NUMBER : '';
  if (!invoiceNumber) { showInvoiceError(); return; }

  try {
    const result = await apiGet(`/api/payments/invoice/${invoiceNumber}/`);
    if (!result.ok) { showInvoiceError(); return; }
    populateInvoice(result.data);
  } catch (err) {
    showInvoiceError();
  }
}

function showInvoiceError() {
  document.getElementById('invoice-loading').classList.add('hidden');
  document.getElementById('invoice-error').classList.remove('hidden');
}

function populateInvoice(data) {
  document.getElementById('invoice-loading').classList.add('hidden');
  document.getElementById('invoice-card').classList.remove('hidden');

  const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val || '—'; };
  const setHtml = (id, val) => { const el = document.getElementById(id); if (el) el.innerHTML = val || '—'; };

  set('inv-number', data.invoice_number);
  set('inv-date', data.date);
  set('inv-payer-name', data.payer.name);
  set('inv-payer-email', data.payer.email);
  set('inv-description', data.description);
  set('inv-razorpay-id', data.razorpay_payment_id || 'N/A');

  const gross = formatINR(data.amounts.gross);
  set('inv-unit-price', gross);
  set('inv-total-col', gross);
  set('inv-subtotal', gross);
  set('inv-total-paid', gross);

  const fee = parseFloat(data.amounts.platform_fee || 0);
  const payeeAmt = parseFloat(data.amounts.payee_amount || 0);

  if (fee > 0) {
    document.getElementById('inv-fee-row').classList.remove('hidden');
    set('inv-platform-fee', formatINR(fee));
  }
  if (payeeAmt > 0 && data.payee && data.payee.name) {
    document.getElementById('inv-payee-row').classList.remove('hidden');
    set('inv-payee-amount', formatINR(payeeAmt));
  }
}

// ── AI TOOL PAGES ─────────────────────────────────────────────────────────────
async function initToolPage() {
  const toolType = typeof TOOL_TYPE !== 'undefined' ? TOOL_TYPE : '';
  if (!toolType) return;

  try {
    const result = await checkToolAccess(toolType);
    if (result.is_free_next) {
      showToolFreeState(result.free_uses_remaining);
    } else {
      showToolPaidState(result.price);
    }
  } catch (err) {
    // Default to showing paid state
    showToolPaidState(typeof TOOL_PRICE !== 'undefined' ? TOOL_PRICE : '0');
  }
}

async function checkToolAccess(toolType) {
  const result = await apiGet(`/api/payments/ai-tools/check/${toolType}/`);
  if (!result.ok) throw new Error('Check failed');
  return result.data;
}

function showToolFreeState(freeRemaining) {
  const badge = document.getElementById('tool-access-badge');
  const btn   = document.getElementById('tool-start-btn');
  if (badge) {
    badge.textContent = freeRemaining > 0 ? `${freeRemaining} free use${freeRemaining > 1 ? 's' : ''} remaining` : 'Free';
    badge.className = 'px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-700';
  }
  if (btn) {
    btn.textContent = 'Start Free';
    btn.onclick = () => proceedWithTool(true);
  }
}

function showToolPaidState(price) {
  const badge = document.getElementById('tool-access-badge');
  const btn   = document.getElementById('tool-start-btn');
  if (badge) {
    badge.textContent = `₹${price}`;
    badge.className = 'px-3 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-700';
  }
  if (btn) {
    btn.textContent = `Pay ₹${price} & Start`;
    btn.onclick = () => initiateToolPayment(typeof TOOL_TYPE !== 'undefined' ? TOOL_TYPE : '');
  }
}

async function initiateToolPayment(toolType) {
  const btn = document.getElementById('tool-start-btn');
  if (btn) { btn.disabled = true; btn.textContent = 'Processing…'; }

  try {
    const result = await apiPost('/api/payments/ai-tools/init/', { tool_type: toolType });
    if (!result.ok) { showToast(extractErr(result.error), 'error'); return; }

    const data = result.data;
    if (data.is_free) {
      await proceedWithTool(true, toolType);
      return;
    }

    showPaymentGateModal(toolType, data.price, data.razorpay_order_id, data.razorpay_key_id, data);
  } catch (err) {
    showToast(extractErr(err), 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = `Pay & Start`; }
  }
}

function showPaymentGateModal(toolType, price, orderId, keyId, orderData) {
  // Use Razorpay checkout directly
  const options = {
    key: keyId,
    amount: Math.round(parseFloat(price) * 100),
    currency: 'INR',
    name: 'AlumniAI',
    description: orderData.description || 'AI Tool Access',
    order_id: orderId,
    prefill: {
      name:  orderData.student_name  || '',
      email: orderData.student_email || '',
    },
    theme: { color: '#4F46E5' },
    handler: (response) => verifyToolPayment(toolType, response),
    modal: { ondismiss: () => showToast('Payment cancelled', 'error') },
  };
  const rzp = new Razorpay(options);
  rzp.open();
}

async function verifyToolPayment(toolType, razorpayResponse) {
  try {
    const result = await apiPost('/api/payments/ai-tools/verify/', {
      tool_type:            toolType,
      razorpay_order_id:    razorpayResponse.razorpay_order_id,
      razorpay_payment_id:  razorpayResponse.razorpay_payment_id,
      razorpay_signature:   razorpayResponse.razorpay_signature,
      is_free: false,
    });
    if (!result.ok) { showToast(extractErr(result.error), 'error'); return; }
    showToast('Payment successful! Loading tool…', 'success');
    setTimeout(() => unlockToolUI(toolType, result.data), 1200);
  } catch (err) {
    showToast(extractErr(err), 'error');
  }
}

async function proceedWithTool(isFree, toolType) {
  const tt = toolType || (typeof TOOL_TYPE !== 'undefined' ? TOOL_TYPE : '');
  try {
    const result = await apiPost('/api/payments/ai-tools/verify/', {
      tool_type: tt, is_free: isFree,
    });
    if (!result.ok) { showToast(extractErr(result.error), 'error'); return; }
    showToast('Access granted! Loading tool…', 'success');
    setTimeout(() => unlockToolUI(tt, result.data), 800);
  } catch (err) {
    showToast(extractErr(err), 'error');
  }
}

function unlockToolUI(toolType, data) {
  const gate = document.getElementById('payment-gate');
  const content = document.getElementById('tool-content');
  if (gate) gate.classList.add('hidden');
  if (content) content.classList.remove('hidden');
  // Store usage_id for the tool to use
  window._toolUsageId = data.usage_id;
  window._toolInvoice  = data.invoice_number;
}

// ── REFERRAL BOOST ────────────────────────────────────────────────────────────
async function initiateBoostPayment(referralId) {
  const btn = document.getElementById(`boost-btn-${referralId}`);
  if (btn) { btn.disabled = true; btn.textContent = 'Processing…'; }

  try {
    const result = await apiPost('/api/payments/boost/', { referral_id: referralId });
    if (!result.ok) { showToast(extractErr(result.error), 'error'); return; }

    const data = result.data;
    const options = {
      key: data.razorpay_key_id,
      amount: Math.round(parseFloat(data.amount) * 100),
      currency: data.currency || 'INR',
      name: 'AlumniAI',
      description: data.description || 'Referral Boost — 48 hours',
      order_id: data.razorpay_order_id,
      theme: { color: '#D97706' },
      handler: (response) => verifyBoostPayment(referralId, response),
      modal: { ondismiss: () => showToast('Boost payment cancelled', 'error') },
    };
    const rzp = new Razorpay(options);
    rzp.open();
  } catch (err) {
    showToast(extractErr(err), 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = 'Boost ₹99'; }
  }
}

async function verifyBoostPayment(referralId, razorpayResponse) {
  try {
    const result = await apiPatch('/api/payments/boost/verify/', {
      referral_id:          referralId,
      razorpay_order_id:    razorpayResponse.razorpay_order_id,
      razorpay_payment_id:  razorpayResponse.razorpay_payment_id,
      razorpay_signature:   razorpayResponse.razorpay_signature,
    });
    if (!result.ok) { showToast(extractErr(result.error), 'error'); return; }
    showToast('Referral boosted for 48 hours!', 'success');
    // Update the boost button to show "Boosted ✓"
    const btn = document.getElementById(`boost-btn-${referralId}`);
    if (btn) {
      btn.textContent = 'Boosted ✓';
      btn.disabled = true;
      btn.className = btn.className.replace(/bg-amber-\d+/g, 'bg-emerald-100').replace(/text-amber-\d+/g, 'text-emerald-700');
    }
  } catch (err) {
    showToast(extractErr(err), 'error');
  }
}

// ── ADMIN PAYMENTS PAGE ───────────────────────────────────────────────────────
async function loadAdminPayments() {
  try {
    const [revenueRes] = await Promise.all([
      apiGet('/api/payments/admin/revenue/'),
    ]);

    if (revenueRes.ok) {
      renderAdminMetricCards(revenueRes.data);
      renderRevenueChart(revenueRes.data.monthly_breakdown || []);
      renderRevenueByType(revenueRes.data.by_type || {});
    }
  } catch (err) {
    showToast('Failed to load admin data', 'error');
  }

  loadAdminPayouts('pending');
}

function renderAdminMetricCards(data) {
  const cards = [
    { label: 'Total Revenue',    value: formatINR(data.total_revenue),       color: 'text-emerald-600', bg: 'bg-emerald-50' },
    { label: 'This Month',       value: formatINR(data.this_month_revenue),  color: 'text-blue-600',    bg: 'bg-blue-50' },
    { label: 'Pending Payouts',  value: formatINR(data.pending_payouts),     color: 'text-amber-600',   bg: 'bg-amber-50' },
    { label: 'Sessions Revenue', value: formatINR((data.by_type && data.by_type.session_booking) ? data.by_type.session_booking.total : 0), color: 'text-violet-600', bg: 'bg-violet-50' },
    { label: 'AI Tools Revenue', value: formatINR(
        ['ai_interview','resume_check','resume_builder','skill_gap'].reduce((sum, k) =>
          sum + parseFloat((data.by_type && data.by_type[k]) ? data.by_type[k].total : 0), 0)
      ), color: 'text-indigo-600', bg: 'bg-indigo-50' },
  ];

  document.getElementById('admin-metric-cards').innerHTML = cards.map(c => `
    <div class="bg-white rounded-xl border border-slate-200 p-5">
      <p class="text-xs font-medium text-slate-500 uppercase tracking-wide">${c.label}</p>
      <p class="text-xl font-bold ${c.color} mt-1">${c.value}</p>
    </div>`).join('');
}

function renderRevenueChart(monthly) {
  const ctx = document.getElementById('revenueChart');
  if (!ctx) return;
  if (_revenueChart) _revenueChart.destroy();

  _revenueChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: monthly.map(m => m.month),
      datasets: [{
        label: 'Platform Revenue (₹)',
        data: monthly.map(m => m.revenue || 0),
        backgroundColor: 'rgba(16, 185, 129, 0.8)',
        borderRadius: 6,
        borderSkipped: false,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: ctx => `Revenue: ${formatINR(ctx.parsed.y)}` } },
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { callback: v => '₹' + Number(v).toLocaleString('en-IN'), font: { size: 11 } },
          grid: { color: 'rgba(0,0,0,0.05)' },
        },
        x: { ticks: { font: { size: 11 } }, grid: { display: false } },
      },
    },
  });
}

function renderRevenueByType(byType) {
  const container = document.getElementById('revenue-by-type');
  if (!container) return;

  const entries = Object.entries(byType).filter(([, v]) => parseFloat(v.total) > 0);
  if (!entries.length) {
    container.innerHTML = `<p class="text-sm text-slate-400">No revenue data yet.</p>`;
    return;
  }

  const max = Math.max(...entries.map(([, v]) => parseFloat(v.total)));
  container.innerHTML = entries.map(([key, val]) => {
    const pct = max > 0 ? (parseFloat(val.total) / max * 100).toFixed(0) : 0;
    const color = getTransactionTypeColor(key);
    return `
      <div>
        <div class="flex justify-between text-xs mb-1">
          <span class="text-slate-600 font-medium">${val.label}</span>
          <span class="text-slate-700 font-semibold">${formatINR(val.total)}</span>
        </div>
        <div class="h-2 bg-slate-100 rounded-full overflow-hidden">
          <div class="h-full bg-${color}-500 rounded-full transition-all" style="width:${pct}%"></div>
        </div>
      </div>`;
  }).join('');
}

// ── Admin Payout Management ───────────────────────────────────────────────────
async function loadAdminPayouts(status) {
  // Update tab styles
  document.querySelectorAll('.payout-tab-btn').forEach(btn => {
    const isActive = btn.dataset.pstatus === status;
    btn.className = isActive
      ? 'payout-tab-btn px-3 py-1 text-xs font-medium rounded-md bg-white text-slate-700 shadow-sm transition-all'
      : 'payout-tab-btn px-3 py-1 text-xs font-medium rounded-md text-slate-500 hover:text-slate-700 transition-all';
  });

  const container = document.getElementById('admin-payouts-list');
  container.innerHTML = `<div class="animate-pulse h-20 bg-slate-50 rounded-xl"></div>`;

  try {
    const result = await apiGet(`/api/payments/admin/payouts/?status=${status}`);
    if (!result.ok) { showToast('Failed to load payouts', 'error'); return; }
    renderAdminPayouts(result.data.payouts || [], status);
  } catch (err) {
    showToast(extractErr(err), 'error');
  }
}

function renderAdminPayouts(payouts, status) {
  const container = document.getElementById('admin-payouts-list');
  if (!payouts.length) {
    container.innerHTML = `<div class="text-center py-10 text-slate-400 text-sm">No ${status} payouts.</div>`;
    return;
  }

  container.innerHTML = payouts.map(p => {
    const date = new Date(p.requested_at).toLocaleDateString('en-IN', {
      day: '2-digit', month: 'short', year: 'numeric',
    });
    const bank = p.bank_details || {};
    const actions = status === 'pending' ? `
      <button onclick="approvePayoutAdmin(${p.id})"
        class="px-3 py-1.5 bg-blue-600 text-white text-xs font-semibold rounded-lg hover:bg-blue-700 transition-colors">
        Approve
      </button>
      <button onclick="openRejectModal(${p.id})"
        class="px-3 py-1.5 bg-red-100 text-red-700 text-xs font-semibold rounded-lg hover:bg-red-200 transition-colors">
        Reject
      </button>` : status === 'approved' ? `
      <button onclick="openProcessModal(${p.id})"
        class="px-3 py-1.5 bg-emerald-600 text-white text-xs font-semibold rounded-lg hover:bg-emerald-700 transition-colors">
        Mark Processed
      </button>` : '';

    return `
      <div class="bg-slate-50 rounded-xl p-4 flex items-center justify-between gap-4 flex-wrap">
        <div class="flex items-center gap-4">
          <div>
            <p class="text-sm font-semibold text-slate-800">${p.user_name}</p>
            <p class="text-xs text-slate-500">${p.user_email} · ${p.user_role}</p>
            <p class="text-xs text-slate-400 mt-0.5">${date}</p>
          </div>
          <div class="text-center">
            <p class="text-lg font-bold text-slate-800">${formatINR(p.amount)}</p>
            <p class="text-xs text-slate-500">Wallet: ${formatINR(p.wallet_balance)}</p>
          </div>
          ${bank.bank_name ? `
          <div class="text-xs text-slate-500">
            <p class="font-medium text-slate-700">${bank.bank_name}</p>
            <p>${bank.account_number_masked ? '****' + bank.account_number_masked : '—'} · ${bank.ifsc_code || '—'}</p>
          </div>` : ''}
        </div>
        <div class="flex items-center gap-2">${actions}${getStatusBadgeHtml(p.status)}</div>
      </div>`;
  }).join('');
}

async function approvePayoutAdmin(payoutId) {
  if (!confirm('Approve this payout request?')) return;
  try {
    const result = await apiPatch(`/api/payments/admin/payouts/${payoutId}/`, { action: 'approve' });
    if (!result.ok) { showToast(extractErr(result.error), 'error'); return; }
    showToast('Payout approved.', 'success');
    loadAdminPayouts('pending');
  } catch (err) {
    showToast(extractErr(err), 'error');
  }
}

function openRejectModal(payoutId) {
  _rejectTargetId = payoutId;
  document.getElementById('reject-reason').value = '';
  document.getElementById('reject-modal').classList.remove('hidden');
}

function closeRejectModal() {
  _rejectTargetId = null;
  document.getElementById('reject-modal').classList.add('hidden');
}

async function submitReject() {
  const reason = document.getElementById('reject-reason').value.trim();
  if (!reason) { showToast('Rejection reason is required.', 'error'); return; }
  try {
    const result = await apiPatch(`/api/payments/admin/payouts/${_rejectTargetId}/`, {
      action: 'reject', admin_note: reason,
    });
    if (!result.ok) { showToast(extractErr(result.error), 'error'); return; }
    showToast('Payout rejected.', 'success');
    closeRejectModal();
    loadAdminPayouts('pending');
  } catch (err) {
    showToast(extractErr(err), 'error');
  }
}

function openProcessModal(payoutId) {
  _processTargetId = payoutId;
  document.getElementById('process-reference').value = '';
  document.getElementById('process-modal').classList.remove('hidden');
}

function closeProcessModal() {
  _processTargetId = null;
  document.getElementById('process-modal').classList.add('hidden');
}

async function submitProcess() {
  const ref = document.getElementById('process-reference').value.trim();
  if (!ref) { showToast('Transaction reference is required.', 'error'); return; }
  try {
    const result = await apiPatch(`/api/payments/admin/payouts/${_processTargetId}/`, {
      action: 'process', transaction_reference: ref,
    });
    if (!result.ok) { showToast(extractErr(result.error), 'error'); return; }
    showToast('Payout marked as processed.', 'success');
    closeProcessModal();
    loadAdminPayouts('approved');
  } catch (err) {
    showToast(extractErr(err), 'error');
  }
}
