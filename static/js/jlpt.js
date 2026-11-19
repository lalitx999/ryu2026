/* RYU JLPT TEST (วัดระดับภาษาญี่ปุ่น.online): mock test runner (timer, palette, listening via device speech, scoring
   per section, placement estimate, review + "report wrong question") and last results on the home page. */
(function () {
  'use strict';
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var esc = function (t) { var d = document.createElement('div'); d.textContent = t == null ? '' : t; return d.innerHTML; };
  var STORE = 'ryu_jlpt_results_v1';
  function results() { try { return JSON.parse(localStorage.getItem(STORE) || '{}') || {}; } catch (e) { return {}; } }
  function saveResult(key, value) { try { var r = results(); r[key] = value; localStorage.setItem(STORE, JSON.stringify(r)); } catch (e) { /* private mode */ } }

  /* ---------- home: last results ---------- */
  $$('[data-last]').forEach(function (el) {
    var r = results()[el.dataset.last]; if (!r) return;
    el.textContent = 'ครั้งล่าสุด: ' + r.score + '/' + r.total + (r.estimate ? ' · ประเมินระดับ ' + r.estimate : '') + ' (' + r.date + ')';
  });

  var dataEl = document.getElementById('exam-data');
  if (!dataEl) return;
  var EXAM = JSON.parse(dataEl.textContent), ITEMS = EXAM.items, answers = new Array(ITEMS.length), i = 0, timer = null, left = EXAM.minutes * 60;
  var Q = function (n) { return $('[data-q="' + n + '"]'); }, R = function (n) { return $('[data-r="' + n + '"]'); };
  var stage = function (n) { $$('[data-stage]').forEach(function (el) { el.hidden = el.dataset.stage !== n; }); window.scrollTo({ top: 0, behavior: 'smooth' }); };
  var LEVELS = ['N5', 'N4', 'N3', 'N2', 'N1'];

  /* ---------- speech (listening section) ---------- */
  var synth = window.speechSynthesis, voice = null;
  function pick() { if (synth) voice = synth.getVoices().filter(function (v) { return /^ja/i.test(v.lang); })[0] || null; }
  if (synth) { pick(); synth.onvoiceschanged = pick; }
  function speakScript(script, question) {
    if (!synth) { Q('listen-note').textContent = 'อุปกรณ์นี้เล่นเสียงไม่ได้ ลองเปิดด้วย Chrome หรือ Safari'; return; }
    synth.cancel();
    var lines = script.split(/\n+/).map(function (l) { return l.replace(/^[^：:]{1,4}[：:]/, '').trim(); }).filter(Boolean);
    lines.concat(question ? [question] : []).forEach(function (line) {
      var u = new SpeechSynthesisUtterance(line); u.lang = 'ja-JP'; u.rate = 0.9; if (voice) u.voice = voice; synth.speak(u);
    });
  }

  /* ---------- runner ---------- */
  function fmt(s) { var m = Math.floor(s / 60), r = s % 60; return (m < 10 ? '0' : '') + m + ':' + (r < 10 ? '0' : '') + r; }
  function tick() {
    left--; $('[data-timer]').textContent = fmt(Math.max(left, 0));
    $('[data-timer]').classList.toggle('low', left <= 60);
    if (left <= 0) finish();
  }
  function plain(html) { var d = document.createElement('div'); d.innerHTML = html; return d.textContent; }
  function render() {
    var q = ITEMS[i];
    Q('section').textContent = (q.level && EXAM.kind === 'placement' ? q.level + ' · ' : '') + q.section_th;
    Q('count').textContent = 'ข้อ ' + (i + 1) + '/' + ITEMS.length;
    Q('progress').style.width = (100 * answers.filter(function (a) { return a != null; }).length / ITEMS.length) + '%';
    var reading = q.section === 'reading', listening = q.section === 'listening';
    Q('passage').hidden = !reading; Q('passage').textContent = reading ? q.passage : '';
    Q('listen').hidden = !listening;
    Q('stem').innerHTML = q.stem;
    Q('choices').innerHTML = '';
    q.choices.forEach(function (c, j) {
      var b = document.createElement('button'); b.type = 'button'; b.className = 'jl-choice' + (answers[i] === j ? ' on' : '');
      b.innerHTML = '<span class="n">' + (j + 1) + '</span><span class="ms-jp"></span>'; b.lastChild.textContent = c;
      b.addEventListener('click', function () { answers[i] = j; render(); });
      Q('choices').appendChild(b);
    });
    $('[data-act="prev"]').disabled = i === 0;
    $('[data-act="next"]').textContent = i === ITEMS.length - 1 ? 'ตรวจทานแล้วส่ง' : 'ถัดไป';
    Q('palette').innerHTML = ITEMS.map(function (_, k) {
      return '<button type="button" class="' + (k === i ? 'cur ' : '') + (answers[k] != null ? 'done' : '') + '" data-go="' + k + '">' + (k + 1) + '</button>';
    }).join('');
  }
  function start() {
    stage('run'); render();
    $('[data-timer]').textContent = fmt(left);
    timer = setInterval(tick, 1000);
  }
  function finish() {
    clearInterval(timer); if (synth) synth.cancel();
    var bySection = {}, byLevel = {}, score = 0;
    ITEMS.forEach(function (q, k) {
      var ok = answers[k] === q.answer; if (ok) score++;
      (bySection[q.section] = bySection[q.section] || { name: q.section_th, ok: 0, n: 0 }).n++; if (ok) bySection[q.section].ok++;
      (byLevel[q.level] = byLevel[q.level] || { ok: 0, n: 0 }).n++; if (ok) byLevel[q.level].ok++;
    });
    R('score').textContent = score; R('of').textContent = '/' + ITEMS.length;
    var estimate = '';
    if (EXAM.kind === 'placement') {
      // highest level reached while every easier level was also at least 60% right
      LEVELS.every(function (lv) { var s = byLevel[lv]; if (s && s.ok / s.n >= 0.6) { estimate = lv; return true; } return false; });
      R('verdict').innerHTML = estimate ? 'ระดับโดยประมาณของคุณ: <b>' + estimate + '</b> ลองข้อสอบจำลองเต็มของ ' + estimate + ' ต่อได้เลย'
        : 'แนะนำให้เริ่มจากพื้นฐาน N5 ทวนอักษรและคำศัพท์ แล้วกลับมาวัดระดับอีกครั้ง';
    } else {
      var pct = score / ITEMS.length, weak = Object.keys(bySection).filter(function (s) { return bySection[s].ok / bySection[s].n < 1 / 3; });
      R('verdict').textContent = pct >= 0.6 && !weak.length ? 'ดีมาก มีแนวโน้มผ่านระดับ ' + EXAM.level + ' ทวนส่วนที่ผิดอีกนิดก็พร้อมสอบ'
        : pct >= 0.6 ? 'คะแนนรวมดี แต่มีบางส่วนต่ำเกินไป ลองทวนส่วนที่ได้น้อยที่สุดก่อน'
        : 'ยังไม่ถึงเกณฑ์โดยประมาณ (60%) ดูเฉลยด้านล่างแล้วทวนส่วนที่ผิดบ่อย';
    }
    R('sections').innerHTML = Object.keys(bySection).map(function (s) {
      var x = bySection[s], p = Math.round(100 * x.ok / x.n);
      return '<div class="jl-sec"><span>' + esc(x.name) + '</span><div class="kn-bar"><i style="width:' + p + '%"></i></div><b>' + x.ok + '/' + x.n + '</b></div>';
    }).join('');
    R('review').innerHTML = ITEMS.map(function (q, k) {
      var mine = answers[k], ok = mine === q.answer;
      return '<div class="jl-rev ' + (ok ? 'ok' : 'bad') + '"><div class="jl-rev-head"><span>ข้อ ' + (k + 1) + ' · ' + esc(q.section_th) + '</span>' +
        (q.approved ? '<span class="tag ok">ผู้สอนตรวจแล้ว</span>' : '<span class="tag">โจทย์จาก AI</span>') + '</div>' +
        (q.passage ? '<details><summary>' + (q.section === 'listening' ? 'บทสนทนา' : 'บทอ่าน') + '</summary><p class="ms-jp">' + esc(q.passage).replace(/\n/g, '<br>') + '</p></details>' : '') +
        '<div class="ms-jp jl-rev-stem">' + q.stem + '</div>' +
        '<div class="jl-rev-ans">คำตอบของคุณ: <b class="ms-jp">' + (mine == null ? 'ไม่ได้ตอบ' : esc(q.choices[mine])) + '</b>' +
        (ok ? '' : ' · ที่ถูกคือ <b class="ms-jp">' + esc(q.choices[q.answer]) + '</b>') + '</div>' +
        (q.explanation ? '<p class="mb-1">' + esc(q.explanation) + '</p>' : '') +
        '<button type="button" class="jl-report" data-report="' + q.id + '">แจ้งโจทย์ผิด</button></div>';
    }).join('');
    var now = new Date();
    saveResult(EXAM.kind === 'placement' ? 'placement' : EXAM.level,
      { score: score, total: ITEMS.length, estimate: estimate, date: now.getDate() + '/' + (now.getMonth() + 1) });
    stage('result');
    $('[data-timer]').textContent = 'เสร็จแล้ว';
  }

  var startBtn = $('[data-act="start"]');
  if (startBtn) startBtn.addEventListener('click', start);
  $('[data-act="prev"]').addEventListener('click', function () { if (i > 0) { i--; render(); } });
  $('[data-act="next"]').addEventListener('click', function () { if (i < ITEMS.length - 1) { i++; render(); } else $('[data-act="submit"]').click(); });
  $('[data-act="submit"]').addEventListener('click', function () {
    var unanswered = ITEMS.length - answers.filter(function (a) { return a != null; }).length;
    if (unanswered && !confirm('ยังไม่ได้ตอบ ' + unanswered + ' ข้อ ส่งคำตอบเลยไหม?')) return;
    finish();
  });
  Q('palette').addEventListener('click', function (e) { var b = e.target.closest('[data-go]'); if (b) { i = +b.dataset.go; render(); } });
  $('[data-act="listen"]').addEventListener('click', function () { var q = ITEMS[i]; speakScript(q.passage, plain(q.stem)); });
  document.addEventListener('keydown', function (e) {
    if ($('[data-stage="run"]').hidden || e.target.closest('input, textarea')) return;
    if (e.key >= '1' && e.key <= '4') { answers[i] = +e.key - 1; render(); }
    if (e.key === 'ArrowRight' && i < ITEMS.length - 1) { i++; render(); }
    if (e.key === 'ArrowLeft' && i > 0) { i--; render(); }
  });

  /* ---------- report a wrong question ---------- */
  function csrf() { var m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/); return m ? decodeURIComponent(m[1]) : ''; }
  var reportUrl = document.getElementById('jlpt-js').dataset.reportUrl;
  document.addEventListener('click', function (e) {
    var b = e.target.closest('[data-report]'); if (!b) return;
    b.disabled = true;
    fetch(reportUrl + b.dataset.report + '/', { method: 'POST', headers: { 'X-CSRFToken': csrf() } })
      .then(function (r) { return r.json(); }).then(function (d) { b.textContent = d.message || 'ส่งแล้ว'; })
      .catch(function () { b.disabled = false; });
  });
  window.addEventListener('beforeunload', function (e) { if (!$('[data-stage="run"]').hidden) { e.preventDefault(); e.returnValue = ''; } });
})();
