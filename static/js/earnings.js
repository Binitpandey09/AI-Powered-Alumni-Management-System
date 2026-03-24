/**
 * earnings.js — Wallet & Earnings Dashboard
 */

let _earningsData = null;
let _earningsChart = null;

document.addEventListener('DOMContentLoaded', () => {
  loadEarningsData();
  updateNextPayoutDate();
});

async function loadEarningsData() {
  try {
    const result = await apiGet('/api/sessions/earnings/');
    if (!result.ok) {
      showToast('Failed to load earnings data', 'error');
      return;
    }
    const data = result.data;
    _earningsData = data;
    populateMetricCards(data);
    renderEarningsChart(data.monthly_breakdown || []);
    renderTransactions(data.transactions || []);
  } catch (err) {
    showToast('Failed to load earnings data', 'error');
  }
  try {
    const bdResult = await apiGet('/api/sessions/bank-details/');
    if (bdResult.ok) renderBankDetailsCard(bdResult.data);
  } catch (err) { /* keep default empty state */ }
}

function populateMetricCards(data) {
  const cards = [
    {
      label: 'Wallet Balance',
      value: '&#8377;' + (data.wallet_balance || 0).toLocaleString('en-IN'),
      sub: 'Available for payout',
      icon: `<path stroke-linecap="round" stroke-linejoin="round" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"/>`,
      color: 'text-indigo-600', bg: 'bg-indigo-50',
    },
    {
      label: 'Total Earned (Net)',
      value: '&#8377;' + (data.net_earned || 0).toLocaleString('en-IN'),
      sub: `After ${data.platform_fee_pct || 30}% platform fee`,
      icon: `<path stroke-linecap="round" stroke-linejoin="round" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>`,
      color: 'text-emerald-600', bg: 'bg-emerald-50',
    },
    {
      label: 'Total Sessions',
      value: (data.total_sessions || 0).toLocaleString('en-IN'),
      sub: 'Sessions hosted',
      icon: `<rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>`,
      color: 'text-blue-600', bg: 'bg-blue-50',
    },
    {
      label: 'Total Bookings',
      value: (data.total_bookings || 0).toLocaleString('en-IN'),
      sub: 'Confirmed bookings',
      icon: `<path stroke-linecap="round" stroke-linejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/>`,
      color: 'text-amber-600', bg: 'bg-amber-50',
    },
  ];

  const container = document.getElementById('metric-cards');
  container.innerHTML = cards.map(c => `
    <div class="bg-white rounded-xl border border-slate-200 p-5">
      <div class="flex items-start justify-between">
        <div>
          <p class="text-xs font-medium text-slate-500 uppercase tracking-wide">${c.label}</p>
          <p class="text-2xl font-bold text-slate-800 mt-1">${c.value}</p>
          <p class="text-xs text-slate-400 mt-1">${c.sub}</p>
        </div>
        <div class="w-10 h-10 rounded-lg ${c.bg} flex items-center justify-center flex-shrink-0">
          <svg class="w-5 h-5 ${c.color}" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            ${c.icon}
          </svg>
        </div>
      </div>
    </div>
  `).join('');
}

function renderEarningsChart(monthly) {
  const ctx = document.getElementById('earningsChart');
  if (!ctx) return;
  if (_earningsChart) _earningsChart.destroy();

  _earningsChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: monthly.map(m => m.label),
      datasets: [
        {
          label: 'Net Earnings',
          data: monthly.map(m => m.net),
          backgroundColor: 'rgba(99, 102, 241, 0.85)',
          borderRadius: 6,
          borderSkipped: false,
        },
        {
          label: 'Gross',
          data: monthly.map(m => m.gross),
          backgroundColor: 'rgba(99, 102, 241, 0.2)',
          borderRadius: 6,
          borderSkipped: false,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'top', labels: { font: { size: 11 }, boxWidth: 12 } },
        tooltip: {
          callbacks: {
            label: ctx => `${ctx.dataset.label}: \u20B9${ctx.parsed.y.toLocaleString('en-IN')}`,
          },
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { callback: v => '\u20B9' + v.toLocaleString('en-IN'), font: { size: 11 } },
          grid: { color: 'rgba(0,0,0,0.05)' },
        },
        x: { ticks: { font: { size: 11 } }, grid: { display: false } },
      },
    },
  });
}

function renderTransactions(transactions) {
  const body = document.getElementById('transactions-body');
  const countEl = document.getElementById('tx-count');
  if (countEl) countEl.textContent = `${transactions.length} transactions`;

  if (!transactions.length) {
    body.innerHTML = `<div class="p-8 text-center text-slate-400 text-sm">No transactions yet. Host a session to start earning.</div>`;
    return;
  }

  const rows = transactions.map(tx => {
    const date = new Date(tx.date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
    const badge = tx.status === 'confirmed'
      ? `<span class="px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-100 text-emerald-700">Confirmed</span>`
      : `<span class="px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600">${tx.status}</span>`;
    return `
      <tr class="border-t border-slate-100 hover:bg-slate-50 transition">
        <td class="px-6 py-3 text-sm text-slate-800 font-medium">${tx.session_title}</td>
        <td class="px-6 py-3 text-sm text-slate-600">${tx.student_name}</td>
        <td class="px-6 py-3 text-sm text-slate-500">${date}</td>
        <td class="px-6 py-3 text-sm text-slate-600">\u20B9${tx.amount.toLocaleString('en-IN')}</td>
        <td class="px-6 py-3 text-sm font-semibold text-emerald-700">\u20B9${tx.net.toLocaleString('en-IN')}</td>
        <td class="px-6 py-3">${badge}</td>
      </tr>`;
  }).join('');

  body.innerHTML = `
    <div class="overflow-x-auto">
      <table class="w-full text-left">
        <thead>
          <tr class="bg-slate-50 text-xs font-semibold text-slate-500 uppercase tracking-wide">
            <th class="px-6 py-3">Session</th>
            <th class="px-6 py-3">Student</th>
            <th class="px-6 py-3">Date</th>
            <th class="px-6 py-3">Gross</th>
            <th class="px-6 py-3">Net (70%)</th>
            <th class="px-6 py-3">Status</th>
          </tr>
        </thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
}

function renderBankDetailsCard(data) {
  const body = document.getElementById('bank-card-body');
  if (!body) return;
  const details = data.bank_details || {};
  if (!details.bank_name) return;

  const maskedAcc = details.account_number_masked || '****';
  const verifiedBadge = data.bank_verified
    ? `<span class="inline-flex items-center gap-1 text-xs text-emerald-600 font-medium">
        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
        </svg>Verified</span>`
    : `<span class="text-xs text-amber-600 font-medium">Pending verification</span>`;

  body.innerHTML = `
    <div class="space-y-3 w-full">
      <div class="flex items-center justify-between">
        <span class="text-xs text-slate-500">Bank</span>
        <span class="text-sm font-semibold text-slate-800">${details.bank_name}</span>
      </div>
      <div class="flex items-center justify-between">
        <span class="text-xs text-slate-500">Account</span>
        <span class="text-sm font-mono text-slate-700">${maskedAcc}</span>
      </div>
      <div class="flex items-center justify-between">
        <span class="text-xs text-slate-500">IFSC</span>
        <span class="text-sm font-mono text-slate-700">${details.ifsc_code || '&mdash;'}</span>
      </div>
      ${details.upi_id ? `
      <div class="flex items-center justify-between">
        <span class="text-xs text-slate-500">UPI</span>
        <span class="text-sm text-slate-700">${details.upi_id}</span>
      </div>` : ''}
      <div class="pt-1">${verifiedBadge}</div>
    </div>`;
}

function openBankModal() {
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
  btn.textContent = 'Saving...';

  const payload = {
    account_holder_name: document.getElementById('bank-holder').value.trim(),
    account_number: document.getElementById('bank-account').value.trim(),
    ifsc_code: document.getElementById('bank-ifsc').value.trim().toUpperCase(),
    bank_name: document.getElementById('bank-name').value.trim(),
    branch: document.getElementById('bank-branch').value.trim(),
    upi_id: document.getElementById('bank-upi').value.trim(),
  };

  try {
    const result = await apiPost('/api/sessions/bank-details/', payload);
    if (!result.ok) {
      showToast(extractErrorMessage(result.error), 'error');
      return;
    }
    showToast('Bank details saved successfully', 'success');
    closeBankModal();
    const bdResult = await apiGet('/api/sessions/bank-details/');
    if (bdResult.ok) renderBankDetailsCard(bdResult.data);
  } catch (err) {
    showToast(err.message || 'Failed to save bank details', 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Save Details';
  }
}

function exportCSV() {
  if (!_earningsData || !(_earningsData.transactions || []).length) {
    showToast('No transactions to export', 'error');
    return;
  }
  const headers = ['Session', 'Student', 'Date', 'Gross (INR)', 'Net 70% (INR)', 'Status'];
  const rows = _earningsData.transactions.map(tx => [
    `"${tx.session_title}"`,
    `"${tx.student_name}"`,
    new Date(tx.date).toLocaleDateString('en-IN'),
    tx.amount.toLocaleString('en-IN'),
    tx.net.toLocaleString('en-IN'),
    tx.status,
  ]);
  const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `earnings_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

function updateNextPayoutDate() {
  const el = document.getElementById('next-payout-date');
  if (!el) return;
  const today = new Date();
  const day = today.getDay();
  const daysUntilMonday = day === 1 ? 7 : (8 - day) % 7;
  const nextMonday = new Date(today);
  nextMonday.setDate(today.getDate() + daysUntilMonday);
  el.textContent = nextMonday.toLocaleDateString('en-IN', {
    weekday: 'long', day: 'numeric', month: 'long',
  });
}
