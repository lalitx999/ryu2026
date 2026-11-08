/* Course page.  Port of the legacy player: YouTube chrome hidden (controls=0), the iframe is driven through the
   IFrame API's postMessage channel, with our own control bar, notes (time stamps), handouts and quiz. */
(function () {
  const $ = (s, r) => (r || document).querySelector(s);
  const $$ = (s, r) => Array.from((r || document).querySelectorAll(s));
  const { ajax, esc } = window.Ryu;
  const outline = JSON.parse($('#ryu-outline').textContent);
  const D = window.Ryu.dialogs;                       // sign-in / payment dialogs (dialogs.js)
  const courseId = window.RYU_COURSE, loggedIn = !!window.RYU_AUTH;

  const modules = outline.modules, allLessons = modules.flatMap((m) => m.lessons), byId = {};
  allLessons.forEach((l) => (byId[l.id] = l));
  const done = new Set(allLessons.filter((l) => l.is_completed).map((l) => l.id));

  /* player state */
  const P = { lesson: null, playing: false, time: 0, duration: 0, volume: 100, muted: false, rate: 1, cc: false, tab: 'notes' };
  const frame = $('#p-frame');
  let beat = null, noteTimer = null, lastSent = 0;

  /* ---------- helpers ---------- */
  const mmss = (sec) => { if (!sec || isNaN(sec)) return '00:00'; const m = Math.floor(sec / 60), s = Math.floor(sec % 60); return String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0'); };
  const safeName = (t) => String(t || '').replace(/[^a-zA-Z0-9ก-๙_-]/g, '_');
  const csrf = () => { const m = document.cookie.match(/(?:^|; )csrftoken=([^;]*)/); return m ? decodeURIComponent(m[1]) : ''; };
  function linkify(text) {   // escape first, then link bare URLs
    return esc(text).replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer nofollow">$1</a>');
  }
  function download(filename, content) {
    const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([content], { type: 'text/plain;charset=utf-8' }));
    a.download = filename; document.body.appendChild(a); a.click(); document.body.removeChild(a); URL.revokeObjectURL(a.href);
  }

  /* ---------- YouTube IFrame API over postMessage ---------- */
  function secureUrl(raw) {
    if (!raw) return '';
    let url = raw;
    if (url.includes('youtube.com/watch?v=')) url = 'https://www.youtube.com/embed/' + url.split('v=')[1].split('&')[0];
    else if (url.includes('youtu.be/')) url = 'https://www.youtube.com/embed/' + url.split('youtu.be/')[1].split('?')[0];
    if (!url.includes('enablejsapi=1')) {
      url += (url.includes('?') ? '&' : '?') + 'enablejsapi=1&controls=0&modestbranding=1&rel=0&showinfo=0&iv_load_policy=3&disablekb=1&playsinline=1&fs=0&cc_load_policy=1';
    }
    return url;
  }
  const yt = (func, args) => { if (frame.contentWindow) frame.contentWindow.postMessage(JSON.stringify({ event: 'command', func, args: args || [] }), '*'); };
  window.addEventListener('message', (e) => {
    if (e.source !== frame.contentWindow || typeof e.data !== 'string') return;
    let d; try { d = JSON.parse(e.data); } catch (err) { return; }
    if (d.event !== 'infoDelivery' || !d.info) return;
    if (typeof d.info.currentTime === 'number') P.time = d.info.currentTime;
    if (typeof d.info.duration === 'number' && d.info.duration > 0) P.duration = d.info.duration;
    if (typeof d.info.playerState === 'number') {
      const was = P.playing; P.playing = d.info.playerState === 1;
      if (was && !P.playing) flush();               // paused or ended: save where the student stopped
    }
    paintBar();
  });
  setInterval(() => { if (P.lesson && P.lesson.video_url && frame.contentWindow) frame.contentWindow.postMessage(JSON.stringify({ event: 'listening', id: 1 }), '*'); }, 1000);

  /* ---------- control bar ---------- */
  function paintBar() {
    const sc = $('#cb-scrub'); sc.max = P.duration || 100; sc.value = P.time;
    $('#cb-time').textContent = mmss(P.time); $('#cb-dur').textContent = mmss(P.duration);
    $('#cb-play').textContent = P.playing ? '⏸️ หยุด' : '▶️ เล่น';
    $('#p-bigplay').classList.toggle('d-none', P.playing);
    $('#cb-mute').textContent = P.muted || P.volume === 0 ? '🔇' : P.volume < 50 ? '🔉' : '🔊';
    $('#cb-vol').value = P.muted ? 0 : P.volume; $('#cb-volpct').textContent = (P.muted ? 0 : P.volume) + '%';
    $('#cb-cc').classList.toggle('on', P.cc); $('#cb-ccst').textContent = P.cc ? 'เปิดอยู่' : 'ปิดอยู่';
    $('#cb-rate').value = String(P.rate);
    stamps();
  }
  function togglePlay() { if (P.playing) { yt('pauseVideo'); P.playing = false; flush(); } else { yt('playVideo'); P.playing = true; } paintBar(); }
  function seek(sec) { P.time = Math.max(0, Math.min(P.duration || 9999, sec)); yt('seekTo', [P.time, true]); paintBar(); }
  $('#cb-play').addEventListener('click', togglePlay);
  $('#p-shield').addEventListener('click', togglePlay);
  $('#cb-back').addEventListener('click', () => seek(P.time - 10));
  $('#cb-fwd').addEventListener('click', () => seek(P.time + 10));
  $('#cb-scrub').addEventListener('input', (e) => seek(Number(e.target.value)));
  $('#cb-vol').addEventListener('input', (e) => { P.volume = Number(e.target.value); P.muted = P.volume === 0; yt('setVolume', [P.volume]); if (P.volume > 0) yt('unMute'); paintBar(); });
  $('#cb-mute').addEventListener('click', () => { if (P.muted) { P.muted = false; yt('unMute'); yt('setVolume', [P.volume || 80]); } else { P.muted = true; yt('mute'); } paintBar(); });
  $('#cb-rate').addEventListener('change', (e) => { P.rate = Number(e.target.value); yt('setPlaybackRate', [P.rate]); paintBar(); });
  $('#cb-cc').addEventListener('click', () => {
    P.cc = !P.cc;
    if (P.cc) { yt('loadModule', ['captions']); yt('setOption', ['captions', 'track', { languageCode: 'th' }]); } else yt('unloadModule', ['captions']);
    paintBar();
  });
  $('#cb-full').addEventListener('click', () => {
    const box = $('#video-player-container');
    if (!document.fullscreenElement) box.requestFullscreen && box.requestFullscreen().catch(() => {}); else document.exitFullscreen().catch(() => {});
  });
  $('#video-player-container').addEventListener('contextmenu', (e) => e.preventDefault());

  /* ---------- progress (real playback time, saved while playing, on pause and when leaving) ---------- */
  function flush(keepalive) {
    const l = P.lesson; if (!loggedIn || !l || l.locked || !P.time || Math.abs(P.time - lastSent) < 1) return;
    lastSent = P.time;
    const body = JSON.stringify({ lesson_id: l.id, video_time: Math.floor(P.time), is_completed: false });
    if (keepalive) fetch('/api/courses/save-progress/', { method: 'POST', keepalive: true, credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() }, body });
    else ajax.post('/api/courses/save-progress/', JSON.parse(body)).catch(() => {});
  }
  function startBeat() { clearInterval(beat); beat = setInterval(() => { if (P.playing) flush(); }, 30000); }
  addEventListener('pagehide', () => flush(true));

  /* ---------- curriculum ---------- */
  function counts() { $$('.done-n').forEach((e) => (e.textContent = done.size)); $$('.all-n').forEach((e) => (e.textContent = allLessons.length)); }
  function marks() {
    $$('.lesson-row').forEach((b) => {
      const l = byId[b.dataset.lesson]; b.classList.toggle('active', P.lesson && l.id === P.lesson.id);
      $('.mark', b).textContent = done.has(l.id) ? '🟢' : l.is_free ? '🎁' : '⚪';
    });
    counts();
  }
  let currOpen = false;
  $('#toggle-curr').addEventListener('click', () => {
    currOpen = !currOpen; $('#curr').classList.toggle('d-none', !currOpen);
    $('#toggle-curr .st').textContent = currOpen ? 'ซ่อน ▲' : 'เลือกบทเรียน ▼';
    if (currOpen) setTimeout(() => $('#curr').scrollIntoView({ behavior: 'smooth', block: 'start' }), 50);
  });
  function closeCurr() { currOpen = false; $('#curr').classList.add('d-none'); $('#toggle-curr .st').textContent = 'เลือกบทเรียน ▼'; }

  /* ---------- open a lesson ---------- */
  function open(id) {
    flush();
    const l = byId[id]; if (!l) return;
    P.lesson = l; P.playing = false; P.time = 0; P.duration = 0; lastSent = 0; P.cc = false;
    quiz = null; quizResult = null; quizAnswers = {};
    $('#player-empty').classList.add('d-none'); $('#player').classList.remove('d-none');
    $('#p-title').textContent = '🎥 บทเรียน: ' + l.title; $('#p-done').classList.toggle('d-none', !done.has(id));
    $('#p-sub').textContent = l.is_free ? '🎁 บทเรียนทดลองเรียนฟรี' : l.locked ? '🔒 ล็อกสิทธิ์เฉพาะผู้สมัครเรียน' : '🟢 ปลดล็อกแล้ว';
    $('#p-descbox').classList.toggle('d-none', !l.description); $('#p-desc').innerHTML = linkify(l.description || '');
    // video / lock / empty states
    const has = !!l.video_url;
    frame.classList.toggle('d-none', !has); $('#p-shield').classList.toggle('d-none', !has);
    $('#p-lock').classList.toggle('d-none', has || !l.locked); $('#p-novideo').classList.toggle('d-none', has || l.locked);
    frame.src = has ? secureUrl(l.video_url) : 'about:blank';
    // handout + prev/next + complete toggle
    const pdf = $('#p-pdf'); pdf.classList.toggle('d-none', !l.pdf_url);
    if (l.pdf_url) { pdf.href = l.pdf_url; pdf.lastElementChild.textContent = l.pdf_title || 'เปิดเอกสาร PDF'; }
    const i = allLessons.indexOf(l); $('#btn-prev').disabled = i <= 0; $('#btn-next').disabled = i < 0 || i >= allLessons.length - 1;
    paintComplete(); marks(); paintBar(); loadNote(l); setTab(P.tab === 'quiz' ? 'notes' : P.tab);
    closeCurr(); startBeat();
  }
  $$('.lesson-row').forEach((b) => b.addEventListener('click', () => open(+b.dataset.lesson)));
  $('#btn-prev').addEventListener('click', () => { const i = allLessons.indexOf(P.lesson); if (i > 0) open(allLessons[i - 1].id); });
  $('#btn-next').addEventListener('click', () => { const i = allLessons.indexOf(P.lesson); if (i >= 0 && i < allLessons.length - 1) open(allLessons[i + 1].id); });

  function paintComplete() {
    const on = P.lesson && done.has(P.lesson.id), b = $('#btn-complete');
    b.classList.toggle('done', !!on); $('.ic', b).textContent = on ? '✅' : '⚪';
    $('.tx', b).textContent = on ? 'เรียนสำเร็จแล้ว (กดเลิก)' : 'ทำเครื่องหมายว่าเรียนจบ';
    $('#p-done').classList.toggle('d-none', !on);
  }
  $('#btn-complete').addEventListener('click', async () => {
    const l = P.lesson; if (!l) return;
    if (!loggedIn) { D.openAuth('login'); return; }
    const mark = !done.has(l.id);
    try {
      await ajax.post('/api/courses/save-progress/', { lesson_id: l.id, video_time: Math.floor(P.time), is_completed: mark, set_completed: mark });
      if (mark) done.add(l.id); else done.delete(l.id);
      paintComplete(); marks();
    } catch (e) { alert(e.message); }
  });

  /* handout: the PDF when there is one, otherwise the same text sheet the legacy page generated */
  $('#btn-attach').addEventListener('click', () => {
    const l = P.lesson; if (!l) return;
    if (l.pdf_url) { window.open(l.pdf_url, '_blank'); return; }
    const bar = '=====================================================';
    download('เอกสารประกอบ_' + safeName(l.title) + '.txt',
      `${bar}\n   RYUCLASS JAPANESE LEARNING SYSTEM - เอกสารประกอบการเรียน\n${bar}\nวิชาเรียน: ${outline.course_title || ''}\nบทเรียน: ${l.title}\nวันที่ดาวน์โหลด: ${new Date().toLocaleString('th-TH')}\n-----------------------------------------------------\n\n[1. สรุปไวยากรณ์หลักประจำบทเรียน]\n- โครงสร้างประโยคและหลักการใช้งานที่ออกสอบ JLPT บ่อยที่สุด\n\n[2. คำศัพท์และคันจิที่ต้องจำ]\n- รวบรวมคันจิ N5/N4 พร้อมคำอ่านฟูริงานะและคำแปลภาษาไทย\n\n[3. แบบฝึกหัดทบทวนหลังเรียน]\n- แนะนำให้ทำแบบฝึกหัดในแท็บ "❓ แบบฝึกหัด" บนระบบเพื่อวัดผลคะแนนทันที\n\n${bar}\nเอกสารลิขสิทธิ์เฉพาะผู้เรียนระบบ RyuClass เท่านั้น ห้ามนำไปแจกจ่ายต่อ\n${bar}`);
  });

  /* ---------- sign-in / payment from this page ---------- */
  const buy = () => (loggedIn ? D.openPayment(false, courseId) : D.openAuth('login'));
  ['buy-btn', 'lock-buy', 'btn-pay'].forEach((id) => { const e = $('#' + id); if (e) e.addEventListener('click', buy); });
  $('#btn-login') && $('#btn-login').addEventListener('click', () => D.openAuth('login'));

  /* ---------- tabs ---------- */
  function setTab(t) {
    P.tab = t; $('#pane-notes').classList.toggle('d-none', t !== 'notes'); $('#pane-quiz').classList.toggle('d-none', t !== 'quiz');
    $('#tab-notes').classList.toggle('on-notes', t === 'notes'); $('#tab-quiz').classList.toggle('on-quiz', t === 'quiz');
  }
  $('#tab-notes').addEventListener('click', () => setTab('notes'));
  $('#tab-quiz').addEventListener('click', () => loadQuiz(P.lesson.id));

  /* ---------- notes: DB when signed in, always mirrored in localStorage ---------- */
  const noteKey = (l) => `ryu_note_${courseId}_${l.id}`;
  const ta = $('#note-text');
  function noteStatus(kind, text) { const s = $('#note-status'); s.className = 'cp-ns ' + kind; s.textContent = (kind === 'saving' ? '⏳ ' : '✓ ') + text; }
  function loadNote(l) {
    let local = ''; try { local = localStorage.getItem(noteKey(l)) || ''; } catch (e) {}
    ta.value = local; noteStatus('saved', local ? 'โหลดโน้ตล่าสุดเรียบร้อย' : 'บันทึกให้อัตโนมัติ'); stamps();
    if (loggedIn && !l.locked) {
      ajax.get('/api/courses/notes/' + l.id + '/').then((r) => {
        if (P.lesson !== l || !r.data.content) return;
        ta.value = r.data.content; try { localStorage.setItem(noteKey(l), r.data.content); } catch (e) {}
        noteStatus('saved', 'ซิงก์สมุดโน้ตจากฐานข้อมูลเรียบร้อย'); stamps();
      }).catch(() => {});
    }
  }
  function noteChanged() {
    noteStatus('saving', 'กำลังบันทึก...'); stamps(); clearTimeout(noteTimer);
    const l = P.lesson, text = ta.value;
    noteTimer = setTimeout(() => {
      try { localStorage.setItem(noteKey(l), text); } catch (e) {}
      const t = new Date().toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit' });
      if (!loggedIn) return noteStatus('saved', 'บันทึกในเครื่องเรียบร้อย ' + t);
      ajax.post('/api/courses/notes/save/', { lesson_id: l.id, content: text })
        .then(() => noteStatus('saved', 'ซิงก์ฐานข้อมูลเรียบร้อย ' + t)).catch(() => noteStatus('saved', 'บันทึกในเครื่องเรียบร้อย ' + t));
    }, 1000);
  }
  ta.addEventListener('input', noteChanged);
  const toSec = (stamp) => { const p = stamp.replace(/[[\]]/g, '').split(':').map(Number); return p.length === 3 ? p[0] * 3600 + p[1] * 60 + p[2] : p.length === 2 ? p[0] * 60 + p[1] : 0; };
  function stamps() {   // clickable [mm:ss] pills found in the note text
    const found = Array.from(new Set(ta.value.match(/\[(\d{1,2}:)?\d{1,2}:\d{2}\]/g) || []));
    $('#note-stamps').classList.toggle('d-none', !found.length);
    const box = $('#note-stamps-list'); if (box.dataset.key === found.join('|')) return; box.dataset.key = found.join('|');
    box.innerHTML = found.map((s) => `<button type="button" class="cp-pill" data-seek="${toSec(s)}"><span>▶️</span><span>${esc(s)}</span></button>`).join('');
  }
  $('#note-stamps-list').addEventListener('click', (e) => { const b = e.target.closest('[data-seek]'); if (b) seek(+b.dataset.seek); });
  $('#note-stamp').addEventListener('click', () => {
    const mark = ` [${mmss(P.time)}] `, s = ta.selectionStart || 0, en = ta.selectionEnd || 0;
    ta.value = ta.value.slice(0, s) + mark + ta.value.slice(en); noteChanged();
    setTimeout(() => { ta.selectionStart = ta.selectionEnd = s + mark.length; ta.focus(); }, 50);
  });
  $('#note-copy').addEventListener('click', () => {
    if (!ta.value.trim()) { alert('⚠️ ไม่มีข้อความโน้ตให้คัดลอกค่ะ'); return; }
    navigator.clipboard.writeText(ta.value).then(() => alert('📋 คัดลอกสมุดโน้ตลง Clipboard เรียบร้อยแล้ว!'));
  });
  $('#note-dl').addEventListener('click', () => {
    if (!ta.value.trim()) { alert('⚠️ ไม่มีข้อความโน้ตให้ดาวน์โหลดค่ะ'); return; }
    const head = `=== สรุปสมุดโน้ตส่วนตัว RyuClass ===\nคอร์ส: ${outline.course_title || ''}\nบทเรียน: ${P.lesson ? P.lesson.title : ''}\nวันที่ส่งออก: ${new Date().toLocaleString('th-TH')}\n===================================\n\n`;
    download('โน้ตเรียน_' + (P.lesson ? safeName(P.lesson.title) : 'lesson') + '.txt', head + ta.value);
  });

  /* ---------- quiz ---------- */
  let quiz = null, quizResult = null, quizAnswers = {};
  async function loadQuiz(lessonId) {
    setTab('quiz'); const box = $('#pane-quiz'); quiz = null; quizResult = null; quizAnswers = {}; draw();
    try { quiz = (await ajax.get('/api/quizzes/lesson/' + lessonId + '/')).data; quizResult = null; quizAnswers = {}; draw(); }
    catch (e) { alert(e.message || 'ไม่สามารถโหลดแบบฝึกหัดสำหรับบทเรียนนี้ได้'); setTab('notes'); }
  }
  function draw() {
    const box = $('#pane-quiz');
    const head = `<div class="d-flex justify-content-between align-items-center border-bottom pb-2" style="border-color:#fef08a !important"><h4 class="fw-bold t12 mb-0" style="color:#422006">📝 ${esc((quiz && quiz.quiz_title) || 'แบบฝึกหัดทบทวน')}</h4><button type="button" class="btn btn-link p-0 t12 fw-bold" id="quiz-back">กลับไปหน้าโน้ต</button></div>`;
    let body;
    if (!quiz) body = '<div class="p-4 text-center fst-italic" style="color:#6b7280">กำลังโหลดแบบฝึกหัด...</div>';
    else if (!quizResult) {
      body = `<form id="quiz-form" class="t12 d-flex flex-column gap-3">${quiz.questions.map((q, i) => `<div class="border-bottom pb-2" style="border-color:#fef08a !important"><div class="fw-bold mb-1" style="color:#1f2937">Q${i + 1}. ${esc(q.question_text)}</div>
        <div class="row g-2 ps-2">${[['A', q.option_a], ['B', q.option_b], ['C', q.option_c], ['D', q.option_d]].map(([k, v]) => `<div class="col-sm-6"><label class="quiz-opt ${quizAnswers[q.id] === k ? 'sel' : ''}"><input type="radio" class="d-none" name="q${q.id}" value="${k}" ${quizAnswers[q.id] === k ? 'checked' : ''}><span>(${k})</span><span>${esc(v)}</span></label></div>`).join('')}</div></div>`).join('')}
        <div class="text-end"><button class="xp-btn-green px-4 py-1 fw-bold" type="submit">ส่งข้อสอบตรวจ</button></div></form>`;
    } else {
      const r = quizResult;
      body = `<div class="t12 d-flex flex-column gap-3"><div class="text-center p-3 rounded" style="background:#fef9c3;border:1px solid #fde047"><div class="fw-bold" style="font-size:14px;color:#422006">ผลการทดสอบของคุณ</div>
        <div class="fw-bold" style="font-size:24px;color:#1e40af">${r.score} / ${r.total_questions} คะแนน</div><div style="color:#4b5563">ประมวลผลสำเร็จ ระดับความถูกต้อง ${r.percentage}%</div></div>
        <div><h5 class="fw-bold border-bottom pb-1 t12" style="color:#1f2937">เฉลยและคำอธิบายโดยละเอียด:</h5>${r.details.map((d, i) => `<div class="bg-white border rounded p-2 mb-2"><div class="fw-semibold">ข้อ ${i + 1}. ${esc(d.question_text)}</div>
          <div class="fw-medium">คำตอบของคุณ: ${esc(d.chosen || '-')} | <span style="color:#166534">คำตอบที่ถูกต้อง: ${esc(d.correct_option)}</span> | ${d.is_correct ? '🟢 ถูกต้อง' : '🔴 ผิด'}</div>
          ${d.explanation ? `<div class="mt-1 p-1 rounded t11" style="background:#f9fafb;color:#4b5563">💡 <b>คำอธิบาย:</b> ${esc(d.explanation)}</div>` : ''}</div>`).join('')}</div>
        <div class="text-end"><button class="xp-btn-green px-4 py-1" id="quiz-retry" type="button">ทำแบบฝึกหัดใหม่อีกครั้ง</button></div></div>`;
    }
    box.innerHTML = head + body;
    $('#quiz-back').addEventListener('click', () => setTab('notes'));
    const f = $('#quiz-form', box);
    if (f) {
      $$('input[type=radio]', f).forEach((r) => r.addEventListener('change', () => { quizAnswers[r.name.slice(1)] = r.value; draw(); }));
      f.addEventListener('submit', async (e) => {
        e.preventDefault();
        try { quizResult = (await ajax.post('/api/quizzes/submit/', { quiz_id: quiz.quiz_id, answers: quizAnswers })).data; draw(); }
        catch (err) { alert(err.message || 'เกิดข้อผิดพลาดในการส่งตรวจข้อสอบ'); }
      });
    }
    const retry = $('#quiz-retry', box); if (retry) retry.addEventListener('click', () => { quizResult = null; quizAnswers = {}; draw(); });
  }

  /* ---------- start: a free preview if there is one, else the first lesson (as the legacy page did) ---------- */
  counts();
  const first = allLessons.find((l) => l.is_free) || allLessons[0];
  if (first) open(first.id);
})();
