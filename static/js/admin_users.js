/* Student admin: edit dialog (profile + per-course access), CSV import with background polling. */
(function () {
  const { ajax, esc } = window.Ryu, $ = (s, r) => (r || document).querySelector(s);
  const toast = (m, k) => window.Ryu.toast(m, k);

  /* ---------- created-account notice (shows the generated password once) ---------- */
  document.querySelectorAll('form[data-created]').forEach((f) => f.addEventListener('ajax:done', (e) => {
    const d = e.detail.data; alert(`สร้างบัญชีแล้ว\nอีเมล: ${d.email}\nรหัสผ่าน: ${d.password_used}\n(คัดลอกไว้ - ระบบจะไม่แสดงอีก)`); location.reload();
  }));

  /* ---------- edit dialog ---------- */
  const modal = new bootstrap.Modal($('#editModal')), body = $('#edit-body'), save = $('#edit-save');
  let editing = null;
  const field = (label, name, val, type, cls) => `<div class="${cls || 'col-md-4'}"><label class="form-label small fw-semibold">${label}</label><input class="form-control form-control-sm" type="${type || 'text'}" name="${name}" value="${esc(val)}"></div>`;
  document.addEventListener('click', async (e) => {
    const b = e.target.closest('[data-edit-user]'); if (!b) return;
    editing = b.dataset.editUser; save.disabled = true; body.innerHTML = '<div class="text-center text-secondary py-5">กำลังโหลด…</div>'; modal.show();
    try {
      const u = (await ajax.get(`/admin-panel/users/${editing}/`)).data;
      $('#edit-title').textContent = `${u.email} · ระดับ: ${u.tier}`;
      body.innerHTML = `<div class="row g-2">
        ${field('ชื่อ-นามสกุล', 'name', u.name)}${field('อีเมล', 'email', u.email, 'email')}${field('ชื่อเล่น', 'nickname', u.nickname)}
        ${field('เบอร์โทร', 'phone', u.phone)}${field('Telegram Chat ID', 'telegram_chat_id', u.telegram_chat_id)}${field('รหัสผ่านใหม่ (ว่าง = ไม่เปลี่ยน)', 'password', '', 'text')}
        ${field('ยอดสะสม (บาท) — ปลดล็อกตลอดชีพอัตโนมัติ', 'total_spent', u.total_spent)}${field('คะแนนสะสม', 'points', u.points, 'number')}${field('ราคาต่ออายุเฉพาะบุคคล (บาท)', 'custom_renewal_price', u.custom_renewal_price)}
        <div class="col-md-4"><label class="form-label small fw-semibold">บทบาท</label><select name="role" class="form-select form-select-sm"><option value="student" ${u.role === 'student' ? 'selected' : ''}>Student</option><option value="admin" ${u.role === 'admin' ? 'selected' : ''}>Admin</option></select></div>
        <div class="col-md-8 d-flex align-items-end"><div class="form-check"><input class="form-check-input" type="checkbox" name="is_active" id="e-active" ${u.is_active ? 'checked' : ''}><label class="form-check-label small" for="e-active">เปิดใช้งานบัญชี (ปิด = ระงับการเข้าสู่ระบบ)</label></div></div>
        <div class="col-12"><label class="form-label small fw-semibold">บันทึกจากแอดมิน</label><textarea class="form-control form-control-sm" name="admin_remark" rows="2">${esc(u.admin_remark)}</textarea></div></div>
        <h6 class="mt-3 mb-2">สิทธิ์การเข้าถึงรายคอร์ส</h6>
        <div class="table-responsive"><table class="table adm-table"><thead><tr><th>คอร์ส</th><th>เปิดสิทธิ์</th><th>ตลอดชีพ</th><th>วันหมดอายุ</th></tr></thead><tbody>
        ${u.access.map((a) => `<tr data-course="${a.course_id}"><td><span class="dot ${a.is_active ? 'on' : 'off'}"></span>${esc(a.level)} · ${esc(a.course_title)}</td>
          <td><input class="form-check-input" type="checkbox" data-k="is_active" ${a.is_active ? 'checked' : ''}></td><td><input class="form-check-input" type="checkbox" data-k="is_lifetime" ${a.is_lifetime ? 'checked' : ''}></td>
          <td><input class="form-control form-control-sm" type="date" data-k="expires_at" value="${esc(a.expires_at)}" style="max-width:160px"></td></tr>`).join('')}</tbody></table></div>`;
      save.disabled = false;
    } catch (err) { body.innerHTML = `<div class="alert alert-danger">${esc(err.message)}</div>`; }
  });
  $('#edit-form').addEventListener('submit', async (e) => {
    e.preventDefault(); save.disabled = true;
    const payload = Object.fromEntries(new FormData(e.target).entries());
    payload.is_active = $('#e-active').checked ? '1' : '0';
    payload.course_entitlements = Array.from(body.querySelectorAll('tr[data-course]')).map((tr) => ({
      course_id: +tr.dataset.course, is_active: tr.querySelector('[data-k=is_active]').checked, is_lifetime: tr.querySelector('[data-k=is_lifetime]').checked,
      expires_at: tr.querySelector('[data-k=expires_at]').value }));
    try { const r = await ajax.post(`/admin-panel/users/${editing}/update/`, payload); toast(r.message); modal.hide(); setTimeout(() => location.reload(), 500); }
    catch (err) { toast(err.message, 'err'); save.disabled = false; }
  });

  /* ---------- CSV import ---------- */
  function parseCsv(text) {  // RFC-4180-ish: quoted fields, escaped quotes, CRLF
    const rows = []; let row = [], cur = '', q = false;
    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      if (q) { if (c === '"') { if (text[i + 1] === '"') { cur += '"'; i++; } else q = false; } else cur += c; }
      else if (c === '"') q = true;
      else if (c === ',') { row.push(cur); cur = ''; }
      else if (c === '\n' || c === '\r') { if (c === '\r' && text[i + 1] === '\n') i++; row.push(cur); cur = ''; if (row.some((x) => x.trim())) rows.push(row); row = []; }
      else cur += c;
    }
    row.push(cur); if (row.some((x) => x.trim())) rows.push(row); return rows;
  }
  let students = [];
  $('#csv-file').addEventListener('change', async (e) => {
    const f = e.target.files[0]; students = []; $('#csv-go').disabled = true; if (!f) return;
    const rows = parseCsv((await f.text()).replace(/^﻿/, '')); const head = (rows.shift() || []).map((h) => h.trim().toLowerCase());
    if (!head.includes('email')) { $('#csv-info').textContent = '⚠️ ไม่พบคอลัมน์ email ในแถวแรก'; return; }
    students = rows.map((r) => Object.fromEntries(head.map((h, i) => [h, (r[i] || '').trim()])));
    $('#csv-info').textContent = `พบ ${students.length} แถวพร้อมนำเข้า`; $('#csv-go').disabled = !students.length;
  });
  $('#csv-go').addEventListener('click', async (e) => {
    const btn = e.currentTarget, out = $('#csv-result'); btn.disabled = true; out.classList.remove('d-none'); out.textContent = 'กำลังนำเข้า…';
    try {
      let d = (await ajax.post('/admin-panel/users/import/', { students })).data;
      for (let i = 0; i < 120 && d.state === 'pending'; i++) { await new Promise((r) => setTimeout(r, 2000)); d = (await ajax.get(`/admin-panel/tasks/${d.task_id}/`)).data; }
      out.textContent = `เพิ่มใหม่ ${d.imported_count} · อัปเดต ${d.updated_count}` + (d.errors.length ? `\n\nข้อผิดพลาด:\n${d.errors.join('\n')}` : '');
      toast('นำเข้าเสร็จสิ้น'); setTimeout(() => location.reload(), d.errors.length ? 6000 : 1500);
    } catch (err) { out.textContent = err.message; btn.disabled = false; }
  });
})();
