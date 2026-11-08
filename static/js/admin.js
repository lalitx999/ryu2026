(function () {
  const { ajax } = window.Ryu;
  function toast(msg, kind) {
    let w = document.querySelector('.toast-wrap'); if (!w) { w = document.createElement('div'); w.className = 'toast-wrap'; document.body.appendChild(w); }
    const t = document.createElement('div'); t.className = 'toast show align-items-center text-bg-' + (kind === 'err' ? 'danger' : 'success') + ' border-0';
    t.innerHTML = '<div class="d-flex"><div class="toast-body"></div><button type="button" class="btn-close btn-close-white me-2 m-auto"></button></div>';
    t.querySelector('.toast-body').textContent = msg; t.querySelector('button').onclick = () => t.remove(); w.appendChild(t); setTimeout(() => t.remove(), 4000);
  }
  window.Ryu.toast = toast;
  const side = document.getElementById('adm-side');
  document.getElementById('adm-toggle') && document.getElementById('adm-toggle').addEventListener('click', () => side.classList.toggle('open'));

  // Generic action button: <button data-post="url" data-body='{"a":1}' [data-note="#input"] [data-confirm="?"] [data-reload]>
  document.addEventListener('click', async (e) => {
    const b = e.target.closest('[data-post]'); if (!b) return;
    if (b.dataset.confirm && !confirm(b.dataset.confirm)) return;
    const body = b.dataset.body ? JSON.parse(b.dataset.body) : {};
    if (b.dataset.note) body.note = document.querySelector(b.dataset.note).value;
    b.disabled = true;
    try { const r = await ajax.post(b.dataset.post, body); toast(r.message || 'สำเร็จ'); if ('reload' in b.dataset) setTimeout(() => location.reload(), 500); else b.disabled = false; }
    catch (err) { toast(err.message, 'err'); b.disabled = false; }
  });
  // Payment detail dialog (profile, course, EasySlip result, slip image)
  document.addEventListener('click', async (e) => {
    const b = e.target.closest('[data-detail]'); if (!b) return;
    const { esc } = window.Ryu, body = document.getElementById('pay-body');
    body.innerHTML = '<div class="text-center text-secondary py-4">กำลังโหลด…</div>'; new bootstrap.Modal(document.getElementById('payModal')).show();
    try {
      const p = (await ajax.get('/admin-panel/payments/' + b.dataset.detail + '/')).data, row = (k, v) => `<tr><td class="text-secondary">${k}</td><td class="fw-semibold">${esc(v || '-')}</td></tr>`;
      const es = p.easyslip;
      body.innerHTML = `<div class="row g-3"><div class="col-md-6"><table class="table table-sm mb-3"><tbody>${row('รายการ', '#' + p.id + ' · ' + p.status)}${row('นักเรียน', p.user.name + ' (' + p.user.email + ')')}${row('เบอร์โทร', p.user.phone)}${row('ยอดสะสม', '฿' + p.user.total_spent)}
        ${row('คอร์ส', p.course.title)}${row('ยอดโอน', '฿' + p.amount)}${row('แพ็กเกจ', p.duration_days >= 999 ? 'ตลอดชีพ' : p.duration_days + ' วัน')}${row('ประเภท', p.is_renewal ? 'ต่ออายุ' : 'สมัครใหม่')}${row('เลขอ้างอิง', p.trans_ref)}${row('ส่งเมื่อ', p.submitted_at)}${row('ตรวจเมื่อ', p.reviewed_at)}${row('เหตุผลปฏิเสธ', p.rejection_reason)}${row('หมายเหตุ', p.note)}</tbody></table>
        <h6 class="small fw-bold">ผลตรวจอัตโนมัติ (EasySlip)</h6>${es ? `<table class="table table-sm"><tbody>${row('ผล', es.status)}${row('ยอดที่อ่านได้', es.amount)}${row('ธนาคาร', es.bank)}${row('บัญชีปลายทาง', es.account)}${row('ข้อผิดพลาด', es.error)}${row('เมื่อ', es.at)}</tbody></table>` : '<div class="small text-secondary">ยังไม่มีผลตรวจอัตโนมัติ</div>'}</div>
        <div class="col-md-6 text-center">${p.has_slip ? `<img class="img-fluid rounded border" style="max-height:60vh" src="/api/payments/slip/${p.id}/" alt="slip">` : '<div class="text-secondary">ไม่มีรูปสลิป</div>'}</div></div>`;
    } catch (err) { body.innerHTML = '<div class="alert alert-danger">' + esc(err.message) + '</div>'; }
  });
  // Slip preview modal
  document.addEventListener('click', (e) => {
    const img = e.target.closest('[data-slip]'); if (!img) return;
    document.getElementById('slip-img').src = img.dataset.slip; new bootstrap.Modal(document.getElementById('slipModal')).show();
  });
  // Payment review (approve / reject) - AJAX, row updates in place
  document.addEventListener('click', async (e) => {
    const b = e.target.closest('[data-review]'); if (!b) return;
    const action = b.dataset.review; let reason = '';
    if (action === 'reject') { reason = prompt('เหตุผลที่ปฏิเสธสลิป (แสดงให้นักเรียนเห็น):', 'สลิปไม่ถูกต้อง'); if (reason === null) return; }
    else if (!confirm('ยืนยันอนุมัติสลิปและเปิดสิทธิ์การเรียน?')) return;
    b.disabled = true;
    try {
      const r = await ajax.post('/admin-panel/payments/' + b.dataset.id + '/review/', { action, reason });
      const row = b.closest('tr'); row.querySelector('.st-cell').innerHTML = '<span class="st-pill st-' + r.data.status + '">' + r.data.status + '</span>';
      row.querySelector('.act-cell').innerHTML = '<span class="text-muted small">ดำเนินการแล้ว</span>'; toast(r.message);
    } catch (err) { b.disabled = false; toast(err.message, 'err'); }
  });
  // Generic JSON form posts: <form data-ajax-url="..."> (courses / users / broadcast)
  document.querySelectorAll('form[data-ajax-url]').forEach((f) => f.addEventListener('submit', async (e) => {
    e.preventDefault(); const btn = f.querySelector('[type=submit]'); btn && (btn.disabled = true);
    const body = Object.fromEntries(new FormData(f).entries());
    f.querySelectorAll('input[type=checkbox]').forEach((c) => (body[c.name] = c.checked ? '1' : '0'));
    try {
      const r = await ajax.post(f.dataset.ajaxUrl, body); toast(r.message); if (f.dataset.reset) f.reset();
      const m = f.closest('.modal'); m && bootstrap.Modal.getInstance(m) && bootstrap.Modal.getInstance(m).hide();
      f.dispatchEvent(new CustomEvent('ajax:done', { detail: r }));
      if (f.dataset.reload) setTimeout(() => location.reload(), 600);
    }
    catch (err) { toast(err.message, 'err'); } finally { btn && (btn.disabled = false); }
  }));
})();
