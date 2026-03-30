/* user.js — Trash Rewards Mobile PWA */

let userId         = '';
let pollTimer      = null;
let isProcessing   = false;
let processingTimer = null;
let prevTotal      = 0;   // Tổng số items đã xử lý trong phiên

// ── Helpers ──────────────────────────────────────────────────────

function show(id) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById(id).classList.add('active');
}

function updateBanner(state) {
  const banner = document.getElementById('status-banner');
  const icon   = document.getElementById('status-icon');
  const title  = document.getElementById('status-title');
  const sub    = document.getElementById('status-sub');

  banner.classList.remove('state-idle', 'state-processing');

  if (state === 'processing') {
    banner.classList.add('state-processing');
    icon.textContent  = '⚙️';
    title.textContent = 'Đang xử lý...';
    sub.textContent   = 'Vui lòng chờ hệ thống gạt xong';
  } else {
    banner.classList.add('state-idle');
    icon.textContent  = '✅';
    title.textContent = 'Sẵn sàng!';
    sub.textContent   = 'Vui lòng bỏ 1 chai hoặc lon vào';
  }
}

function showToast(msg) {
  const toast = document.getElementById('toast-msg');
  toast.textContent = msg;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 3500);
}

// ── Login ─────────────────────────────────────────────────────────

async function startSession() {
  const uid = document.getElementById('uid-input').value.trim();
  const err = document.getElementById('login-err');

  if (!uid) { err.textContent = 'Vui lòng nhập ID'; return; }
  err.textContent = '';

  try {
    const r = await fetch('/api/active_user', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: uid })
    });
    const d = await r.json();

    if (!d.ok) { err.textContent = d.error || 'Lỗi không xác định'; return; }

    userId = uid;
    // Reset trạng thái phiên mới
    prevTotal   = 0;
    isProcessing = false;
    clearTimeout(processingTimer);
    updateBanner('idle');

    document.getElementById('sess-name').textContent   = uid;
    document.getElementById('sess-avatar').textContent = uid[0].toUpperCase();
    document.getElementById('sess-total').textContent  = '0';
    document.getElementById('br-metal').textContent    = '×0';
    document.getElementById('br-plastic').textContent  = '×0';
    document.getElementById('br-other').textContent    = '×0';

    show('scr-session');
    startPolling();

  } catch (e) {
    err.textContent = 'Không kết nối được server';
  }
}

function startPolling() {
  clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    try {
      const d = await fetch('/api/session_status').then(r => r.json());
      if (!d.active) { clearInterval(pollTimer); return; }

      const b        = d.breakdown || {};
      const currTotal = (b.METAL || 0) + (b.PLASTIC || 0) + (b.other || 0);

      // Cập nhật điểm và số lượng
      document.getElementById('sess-total').textContent  = d.session_points || 0;
      document.getElementById('br-metal').textContent    = '×' + (b.METAL   || 0);
      document.getElementById('br-plastic').textContent  = '×' + (b.PLASTIC || 0);
      document.getElementById('br-other').textContent    = '×' + (b.other   || 0);

      // Phát hiện có item mới vừa được xử lý
      if (currTotal > prevTotal && !isProcessing) {
        isProcessing = true;
        updateBanner('processing');
        clearTimeout(processingTimer);
        processingTimer = setTimeout(() => {
          isProcessing = false;
          updateBanner('idle');
          showToast('✅ Xong! Mời bạn bỏ tiếp hoặc kết thúc phiên');
        }, 3000);
      }
      prevTotal = currTotal;

    } catch (e) {
      // Bỏ qua lỗi mạng tạm thời
    }
  }, 1500);
}

async function endSession() {
  clearInterval(pollTimer);
  clearTimeout(processingTimer);
  isProcessing = false;
  try {
    const r = await fetch('/api/end_session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: userId })
    });
    const d = await r.json();

    if (d.ok) {
      document.getElementById('res-earned').textContent = '+' + d.total_earned + ' điểm';
      document.getElementById('res-total').textContent  = 'Tổng tích lũy: ' + d.new_total + ' điểm';
      show('scr-result');
    }
  } catch (e) {
    alert('Lỗi kết nối');
  }
}

function goLogin() {
  userId = '';
  prevTotal    = 0;
  isProcessing = false;
  clearTimeout(processingTimer);
  updateBanner('idle');
  document.getElementById('uid-input').value = '';
  show('scr-login');
}

// Đăng ký Service Worker cho PWA
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/static/sw.js').catch(() => {});
}
