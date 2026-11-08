/* Shared dialogs: sign-in / register / verify / reset, payment + renewal, ?auth= deep links.
   Loaded by the desktop (home) and by the course page; both embed #ryu-boot = {loggedIn, profile, courses}. */
(function () {
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));
  const { ajax, esc, baht, busy, flash } = window.Ryu;
  const boot = JSON.parse($('#ryu-boot').textContent);   // {loggedIn, profile, courses}
  const state = { paymentRenewal: false };

  /* ---------- bootstrap modals ---------- */
  const authModal = new bootstrap.Modal($('#authModal'));
  const payModal = new bootstrap.Modal($('#payModal'));
  const renewModalEl = $('#renewModal'); const renewModal = renewModalEl ? new bootstrap.Modal(renewModalEl) : null;
  // ?next=/community/ lets other pages send guests here to sign in and come back (same-site paths only)
  function goNext() {
    const n = new URLSearchParams(location.search).get('next');
    if (n && n.startsWith('/') && !n.startsWith('//')) location.href = n; else location.reload();
  }
  function openAuth(tab) { setAuthTab(tab || 'login'); authModal.show(); }
  function openPayment(renewal, courseId) {
    if (!boot.loggedIn) { openAuth('login'); return; }
    state.paymentRenewal = !!renewal; setupPayment(courseId); payModal.show();
  }

  /* ---------- auth tabs ---------- */
  const TITLES = { login: 'เข้าสู่ระบบสมาชิก RyuClass', register: 'ลงทะเบียนสมัครคอร์สเรียนใหม่', verify: 'ยืนยันอีเมลสมาชิก', reset: 'ตั้งรหัสผ่านใหม่ (Reset Password)' };
  function setAuthTab(tab) {
    $$('#authModal [data-pane]').forEach((p) => p.classList.toggle('d-none', p.dataset.pane !== tab));
    $$('#authModal .xp-tabs button').forEach((b) => b.classList.toggle('active', b.dataset.tab === tab));
    $('#auth-title').textContent = TITLES[tab];
    $('#authModal .xp-tabs').classList.toggle('d-none', tab === 'verify');
    flash($('#auth-msg'), 'err', '');
    if (tab === 'register') setupRegister();
  }
  $$('#authModal .xp-tabs button').forEach((b) => b.addEventListener('click', () => setAuthTab(b.dataset.tab)));
  $$('[data-goto-tab]').forEach((b) => b.addEventListener('click', () => setAuthTab(b.dataset.gotoTab)));

  function formData(form) { return Object.fromEntries(new FormData(form).entries()); }
  function bindForm(sel, handler) {
    const f = $(sel); if (!f) return;
    f.addEventListener('submit', async (e) => {
      e.preventDefault(); const btn = f.querySelector('[type=submit]'); busy(btn, true, 'กำลังดำเนินการ...');
      try { await handler(f); } catch (err) { flash($('#auth-msg'), 'err', err.message); if (err.verification_required) { $('#verify-email').value = f.elements.email ? f.elements.email.value : ''; setAuthTab('verify'); flash($('#auth-msg'), 'err', err.message); } }
      finally { busy(btn, false); }
    });
  }
  bindForm('#form-login', async (f) => {
    await ajax.post('/api/auth/login/', formData(f)); flash($('#auth-msg'), 'ok', 'เข้าสู่ระบบสำเร็จ!'); setTimeout(goNext, 600);
  });
  bindForm('#form-reset', async (f) => {
    const r = await ajax.post('/api/auth/reset-password/', formData(f)); flash($('#auth-msg'), 'ok', r.message);
    setTimeout(() => { setAuthTab('login'); $('#form-login').elements.email.value = f.elements.email.value; flash($('#auth-msg'), 'ok', 'กรุณาเข้าสู่ระบบด้วยรหัสผ่านใหม่'); }, 1500);
  });
  bindForm('#form-register', async (f) => {
    if (!f.dataset.amount) throw { message: 'กรุณาเลือกแพ็กเกจที่มีราคาปัจจุบันก่อนโอนเงิน' };
    const fd = new FormData(f); fd.append('expected_amount', f.dataset.amount);
    const r = await ajax.post('/api/auth/register/', fd);
    $('#verify-email').value = f.elements.email.value; $('#verify-code').value = '';
    setAuthTab('verify'); flash($('#auth-msg'), 'ok', r.message);
  });
  bindForm('#form-verify', async (f) => {
    await ajax.post('/api/auth/verify-email/', formData(f));
    $('#verify-form-wrap').classList.add('d-none'); $('#verify-success').classList.remove('d-none');
    flash($('#auth-msg'), 'ok', 'ยืนยันอีเมลและลงทะเบียนสำเร็จเรียบร้อยแล้ว!');
  });
  $('#verify-code').addEventListener('input', (e) => { e.target.value = e.target.value.replace(/\D/g, '').slice(0, 6); $('#verify-submit').disabled = e.target.value.length !== 6; });
  $('#btn-resend').addEventListener('click', async () => {
    try { const r = await ajax.post('/api/auth/resend-verification/', { email: $('#verify-email').value }); flash($('#auth-msg'), 'ok', r.message); }
    catch (err) { flash($('#auth-msg'), 'err', err.message); }
  });
  $('#btn-continue').addEventListener('click', () => location.reload());
  $('#btn-copy-pass').addEventListener('click', function () { navigator.clipboard && navigator.clipboard.writeText('12123'); this.textContent = '✓ คัดลอกแล้ว'; setTimeout(() => (this.textContent = '📋 คัดลอกรหัส'), 2500); });

  /* ---------- pricing selects (register + payment) ---------- */
  function fillPackages(select, course, keep) {
    const pk = (course && course.packages) || [];
    select.innerHTML = '<option value="">เลือกแพ็กเกจ</option>' + pk.map((p) => `<option value="${p.duration}">${esc(p.label)} — ฿${baht(p.price)}</option>`).join('');
    if (keep && pk.some((p) => String(p.duration) === keep)) select.value = keep;
    else if (pk.length) select.value = pk[0].duration;
  }
  function setupRegister() {
    const f = $('#form-register'); const lvl = f.elements.level; const dur = f.elements.duration;
    if (!lvl.dataset.ready) {
      lvl.innerHTML = '<option value="">เลือกคอร์ส</option>' + boot.courses.map((c) => `<option value="${c.level}">${esc(c.title)}</option>`).join('');
      lvl.value = (boot.courses.find((c) => c.level === 'N5') || boot.courses[0] || {}).level || '';
      lvl.dataset.ready = 1;
      lvl.addEventListener('change', recalc); dur.addEventListener('change', recalc);
    }
    recalc();
    function recalc() {
      const c = boot.courses.find((x) => x.level === lvl.value);
      if (document.activeElement !== dur) fillPackages(dur, c, dur.value);
      else fillPackages(dur, c, dur.value);
      const p = c && c.packages.find((x) => String(x.duration) === dur.value);
      f.dataset.amount = p ? p.price : '';
      $('#reg-amount').textContent = p ? 'ยอดที่ต้องชำระ ฿' + baht(p.price, 2) : 'กรุณาเลือกคอร์สและแพ็กเกจที่เปิดจำหน่าย';
      f.querySelector('[type=submit]').disabled = !p;
    }
  }
  function setupPayment(courseId) {
    const f = $('#form-payment'); const sel = f.elements.course_id; const dur = f.elements.duration;
    const renewal = state.paymentRenewal;
    sel.innerHTML = boot.courses.map((c) => `<option value="${c.id}">${esc(c.title)}</option>`).join('');
    if (courseId) sel.value = String(courseId);
    $('#pay-renew-note').classList.toggle('d-none', !renewal);
    sel.disabled = renewal;
    flash($('#pay-msg'), 'err', '');
    sel.onchange = recalc; dur.onchange = recalc; recalc();
    function recalc() {
      const c = boot.courses.find((x) => String(x.id) === sel.value);
      let p;
      if (renewal) {
        p = c && c.packages.find((x) => x.duration === 30);
        if (p && c.renewal_price) p = Object.assign({}, p, { price: c.renewal_price });   // admin-set personal renewal price
        dur.innerHTML = '<option value="33">ต่ออายุ (33 วัน)</option>'; dur.disabled = true;
      } else {
        dur.disabled = false; fillPackages(dur, c, dur.value); p = c && c.packages.find((x) => String(x.duration) === dur.value);
      }
      f.dataset.amount = p ? p.price : '';
      $('#pay-amount').textContent = p ? 'ยอดที่ต้องชำระ ฿' + baht(p.price, 2) : 'ยังไม่มีแพ็กเกจที่เปิดจำหน่าย';
      f.querySelector('[type=submit]').disabled = !p;
    }
  }
  $('#form-payment').addEventListener('submit', async (e) => {
    e.preventDefault(); const f = e.target; const btn = f.querySelector('[type=submit]'); busy(btn, true, 'กำลังส่งข้อมูล...');
    const fd = new FormData(); fd.append('course_id', f.elements.course_id.value);
    fd.append('duration', state.paymentRenewal ? '33' : f.elements.duration.value);
    fd.append('renewal', state.paymentRenewal ? '1' : ''); fd.append('expected_amount', f.dataset.amount);
    fd.append('slip', f.elements.slip.files[0]);
    try { const r = await ajax.post('/api/payments/upload-slip/', fd); flash($('#pay-msg'), 'ok', r.message); setTimeout(() => location.reload(), 1800); }
    catch (err) { flash($('#pay-msg'), 'err', err.message); busy(btn, false); }
  });

  /* ---------- renewal reminder (≤3 days before expiry) ---------- */
  function renewalOffer() {
    if (!boot.loggedIn || !renewModal) return;
    const today = new Date(); today.setHours(0, 0, 0, 0);
    for (const a of boot.profile.courses_access) {
      if (a.is_lifetime || !a.video_expires_at) continue;
      const exp = new Date(a.video_expires_at + 'T00:00:00'); const days = Math.round((exp - today) / 86400000);
      if (days < 0 || days > 3) continue;
      const key = 'ryu_renewal_dismissed_' + a.course_id + '_' + new Date().toISOString().slice(0, 10);
      try { if (localStorage.getItem(key)) continue; } catch (e) {}
      $('#renew-text').innerHTML = `คอร์ส ${esc(a.course_title)} จะหมดอายุในวันที่ ${exp.toLocaleDateString('th-TH', { day: 'numeric', month: 'long', year: 'numeric' })}`;
      $('#renew-days').textContent = days;
      $('#renew-later').onclick = () => { try { localStorage.setItem(key, '1'); } catch (e) {} renewModal.hide(); };
      $('#renew-now').onclick = () => { renewModal.hide(); openPayment(true, a.course_id); };
      renewModal.show(); return;
    }
  }


  // ?auth=login|register[&level=N3] opens the dialog on arrival (used by the sale page, forum and games)
  (function () {
    const qp = new URLSearchParams(location.search), tab = qp.get('auth');
    if (!tab || boot.loggedIn || !TITLES[tab] || tab === 'verify') return;
    openAuth(tab);
    const lv = qp.get('level'), sel = $('#form-register').elements.level;
    if (tab === 'register' && /^N[1-5]$/.test(lv || '') && Array.from(sel.options).some((o) => o.value === lv)) { sel.value = lv; sel.dispatchEvent(new Event('change')); }
  })();

  window.Ryu.dialogs = { openAuth, openPayment, renewalOffer, boot };
})();
