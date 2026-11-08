/* XP desktop behaviour: windows, start menu, profile, calendar, chat (dialogs live in dialogs.js).  Vanilla JS + Bootstrap 5. */
(function () {
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));
  const { ajax, esc, baht, busy, flash } = window.Ryu;
  const { openAuth, openPayment, renewalOffer, boot } = window.Ryu.dialogs;   // see dialogs.js
  const state = { welcomeOpen: true, profileOpen: true, showPublic: false, chatOpen: false };

  /* ---------- clock ---------- */
  function tick() {
    const d = new Date(); let h = d.getHours(); const m = String(d.getMinutes()).padStart(2, '0');
    const ap = h >= 12 ? 'PM' : 'AM'; h = h % 12 || 12;
    $('#xp-clock').textContent = h + ':' + m + ' ' + ap;
  }
  tick(); setInterval(tick, 60000);

  /* ---------- windows ---------- */
  const mainWin = () => (boot.loggedIn && !state.showPublic ? $('#win-profile') : $('#win-welcome'));
  function showMain() {
    const profileWin = $('#win-profile'); if (profileWin) profileWin.classList.add('hidden');
    $('#win-welcome').classList.add('hidden');
    const w = mainWin(); if (w && (boot.loggedIn && !state.showPublic ? state.profileOpen : state.welcomeOpen)) w.classList.remove('hidden');
    $$('[data-task="main"]').forEach((b) => {
      const prof = boot.loggedIn && !state.showPublic;
      b.classList.toggle('d-none', false);
      b.querySelector('.ic').textContent = prof ? '🎓' : '💻';
      b.querySelector('.lbl').textContent = prof ? 'โปรไฟล์นักเรียน' : 'RyuClass Dashboard';
      b.classList.toggle('active', !w.classList.contains('hidden'));
    });
  }
  function openMain(publicView) {
    if (publicView !== undefined) state.showPublic = publicView;
    if (boot.loggedIn && !state.showPublic) state.profileOpen = true; else state.welcomeOpen = true;
    showMain(); if (boot.loggedIn && !state.showPublic) loadCalendar();
  }
  function closeMain() {
    if (boot.loggedIn && !state.showPublic) state.profileOpen = false; else state.welcomeOpen = false;
    showMain();
  }
  function minimizeMain() { const w = mainWin(); w.classList.add('hidden'); $('[data-task="main"]').classList.remove('active'); }
  function toggleMain() { const w = mainWin(); if (w.classList.contains('hidden')) openMain(); else minimizeMain(); }
  function openChat() { state.chatOpen = true; $('#win-chat').classList.remove('hidden'); $('#task-chat').classList.remove('d-none'); $('#task-chat').classList.add('active'); $('#chat-input').focus(); }
  function closeChat() { state.chatOpen = false; $('#win-chat').classList.add('hidden'); $('#task-chat').classList.add('d-none'); }
  function toggleChat() { const w = $('#win-chat'); w.classList.toggle('hidden'); $('#task-chat').classList.toggle('active', !w.classList.contains('hidden')); }
  function closeStart() { $('#start-menu').classList.remove('open'); }

  /* ---------- profile window ---------- */
  const cal = { y: new Date().getFullYear(), m: new Date().getMonth() + 1 };
  const THAI_M = ['มกราคม', 'กุมภาพันธ์', 'มีนาคม', 'เมษายน', 'พฤษภาคม', 'มิถุนายน', 'กรกฎาคม', 'สิงหาคม', 'กันยายน', 'ตุลาคม', 'พฤศจิกายน', 'ธันวาคม'];
  async function loadCalendar() {
    if (!boot.loggedIn || !$('#cal-grid')) return;
    let d = { activity_dates: {} };
    try { d = (await ajax.get(`/api/courses/study-calendar/?year=${cal.y}&month=${cal.m}`)).data; } catch (e) {}
    $('#streak-n').textContent = (d.current_streak || 0) + ' วันติด!';
    $('#streak-msg').textContent = d.is_studied_today ? '🎉 วันนี้เรียนแล้ว สุดยอดมาก!' : '✨ มาเรียนสะสมไฟต่อเนื่องกันนะ!';
    $('#study-days').textContent = (d.total_study_days || 0) + ' วัน'; $('#study-mins').textContent = (d.total_minutes_this_month || 0) + ' น.';
    $('#longest').textContent = (d.longest_streak || 0) + ' วัน';
    $('#cal-title').textContent = '📅 ' + THAI_M[cal.m - 1] + ' ' + (cal.y + 543);
    const first = new Date(cal.y, cal.m - 1, 1).getDay(); const days = new Date(cal.y, cal.m, 0).getDate();
    const now = new Date(); const todayStr = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
    let html = '<div style="height:24px"></div>'.repeat(first);
    for (let day = 1; day <= days; day++) {
      const ds = `${cal.y}-${String(cal.m).padStart(2, '0')}-${String(day).padStart(2, '0')}`; const act = d.activity_dates[ds];
      const cls = act ? 'done' : ds === todayStr ? 'today' : '';
      const tip = act ? `${day} ${THAI_M[cal.m - 1]}: เข้าเรียนแล้ว (${act.minutes} นาที, ${act.lessons} บท)` : `${day} ${THAI_M[cal.m - 1]}`;
      html += `<div class="cal-day ${cls}" title="${esc(tip)}"><span style="line-height:1">${day}</span>${act ? '<span style="font-size:9px;line-height:1">💮</span>' : ''}</div>`;
    }
    $('#cal-grid').innerHTML = html;
  }
  $('#cal-prev') && $('#cal-prev').addEventListener('click', () => { cal.m--; if (cal.m < 1) { cal.m = 12; cal.y--; } loadCalendar(); });
  $('#cal-next') && $('#cal-next').addEventListener('click', () => { cal.m++; if (cal.m > 12) { cal.m = 1; cal.y++; } loadCalendar(); });
  $('#toggle-edit') && $('#toggle-edit').addEventListener('click', () => { const b = $('#edit-body'); b.classList.toggle('d-none'); $('#toggle-edit .st').textContent = b.classList.contains('d-none') ? '▼ เปิดแก้ไข' : '▲ ซ่อน'; });
  $('#form-profile') && $('#form-profile').addEventListener('submit', async (e) => {
    e.preventDefault(); const f = e.target; const btn = f.querySelector('[type=submit]'); busy(btn, true, 'กำลังบันทึก...');
    try { const r = await ajax.post('/api/auth/profile/', formData(f)); flash($('#profile-msg'), 'ok', r.message); f.elements.password.value = ''; }
    catch (err) { flash($('#profile-msg'), 'err', err.message); } finally { busy(btn, false); }
  });

  /* ---------- chat ---------- */
  const history = [];
  const tm = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  function addMsg(role, text, id) {
    const div = document.createElement('div'); div.className = 'msn-msg ' + (role === 'user' ? 'user' : 'bot'); if (id) div.id = id;
    div.innerHTML = `<div class="meta">${role === 'user' ? 'คุณ' : 'AIRIS'} - ${tm()}</div><div class="bubble">${esc(text)}</div>`;
    $('#chat-log').appendChild(div); $('#chat-log').scrollTop = 1e6; return div;
  }
  $('#form-chat').addEventListener('submit', async (e) => {
    e.preventDefault(); const input = $('#chat-input'); const text = input.value.trim(); if (!text) return;
    input.value = ''; history.push({ role: 'user', content: text }); addMsg('user', text);
    const wait = addMsg('bot', 'AIRIS กำลังประมวลผลคำตอบ... 💭', 'chat-wait'); input.disabled = true;
    try {
      let r = await ajax.post('/api/support/chat/', { messages: history });
      // Celery path: enqueue returned a task id -> poll until the worker finishes.
      for (let i = 0; r.data.state === 'pending' && i < 40; i++) { await new Promise((ok) => setTimeout(ok, 1500)); r = await ajax.get('/api/support/chat/' + r.data.task_id + '/'); }
      const reply = r.data.reply || 'AIRIS ตอบไม่ทันค่ะ ลองใหม่อีกครั้งนะคะ 💖';
      wait.remove(); history.push({ role: 'assistant', content: reply }); addMsg('bot', reply);
    } catch (err) { wait.remove(); addMsg('bot', err.message || 'ไม่สามารถติดต่อ AIRIS ได้ค่ะ'); }
    finally { input.disabled = false; input.focus(); }
  });

  /* ---------- wiring ---------- */
  const actions = {
    'open-main': () => openMain(false), 'open-public': () => { openMain(true); closeStart(); },
    'close-main': closeMain, 'min-main': minimizeMain, 'toggle-main': toggleMain,
    'open-chat': () => { openChat(); closeStart(); }, 'close-chat': closeChat, 'min-chat': () => { $('#win-chat').classList.add('hidden'); $('#task-chat').classList.remove('active'); }, 'toggle-chat': toggleChat,
    'open-auth': () => { openAuth('login'); closeStart(); }, 'open-pay': () => { openPayment(false); closeStart(); },
    'toggle-start': () => $('#start-menu').classList.toggle('open'), 'close-start': closeStart,
    'my-computer': () => (boot.loggedIn ? openMain(false) : openMain(true)),
    'logout': async () => { try { await ajax.post('/api/auth/logout/'); } finally { location.reload(); } },
    'goto-library': () => { location.href = '/library/'; },
  };
  document.addEventListener('click', (e) => {
    const t = e.target.closest('[data-act]'); if (t && actions[t.dataset.act]) { e.preventDefault(); actions[t.dataset.act](t); }
    const course = e.target.closest('[data-course-url]'); if (course) location.href = course.dataset.courseUrl;
  });

  document.body.classList.add('xp-lock');
  showMain(); if (boot.loggedIn) { loadCalendar(); renewalOffer(); }
})();
