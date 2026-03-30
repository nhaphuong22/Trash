/* admin.js — Waste Sorter Admin Dashboard */

const prev = { METAL: 0, PLASTIC: 0, other: 0 };

function flash(id) {
  const el = document.getElementById(id);
  el.classList.add('flash');
  setTimeout(() => el.classList.remove('flash'), 800);
}

async function refresh() {
  try {
    const [c, u] = await Promise.all([
      fetch('/api/counts').then(r => r.json()),
      fetch('/api/users').then(r => r.json())
    ]);

    // Cập nhật counts + flash khi tăng
    const cnt = c.counts;
    if (cnt.METAL   !== prev.METAL)   { flash('si-metal');   prev.METAL   = cnt.METAL; }
    if (cnt.PLASTIC !== prev.PLASTIC) { flash('si-plastic'); prev.PLASTIC = cnt.PLASTIC; }
    if (cnt.other   !== prev.other)   { flash('si-other');   prev.other   = cnt.other; }

    document.getElementById('cnt-metal').textContent   = cnt.METAL;
    document.getElementById('cnt-plastic').textContent = cnt.PLASTIC;
    document.getElementById('cnt-other').textContent   = cnt.other;

    // Active user indicator
    const dot = document.getElementById('pulse-dot');
    const lbl = document.getElementById('active-lbl');

    if (c.active_user) {
      dot.style.background  = '#48bb78';
      dot.style.animation   = 'pulse 1.5s infinite';
      lbl.style.color       = '#e2e8f0';
      lbl.textContent       = '🟢 ' + c.active_user + ' đang bỏ rác';
    } else {
      dot.style.background  = '#718096';
      dot.style.animation   = 'none';
      lbl.style.color       = '#718096';
      lbl.textContent       = 'Chờ người dùng nhập ID...';
    }

    // Leaderboard
    const tbody = document.getElementById('user-table');
    if (!u.users.length) {
      tbody.innerHTML = '<tr><td colspan="4" class="empty-msg">Chưa có dữ liệu</td></tr>';
      return;
    }

    const ranks = ['r1', 'r2', 'r3'];
    tbody.innerHTML = u.users.map((r, i) => `
      <tr>
        <td><span class="rank ${ranks[i] || ''}">${i + 1}</span></td>
        <td style="font-weight:600">${r.id}</td>
        <td style="color:#48bb78;font-weight:700">${r.total}</td>
        <td style="color:#718096;font-size:.8rem">${r.last}</td>
      </tr>
    `).join('');

  } catch (e) {
    console.warn('[Admin] refresh error:', e);
  }
}

async function resetCounts() {
  if (!confirm('Reset toàn bộ bộ đếm hôm nay?')) return;
  await fetch('/api/reset', { method: 'POST' });
  refresh();
}

// Refresh mỗi 2 giây
setInterval(refresh, 2000);
refresh();
