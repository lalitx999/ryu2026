/* RYU KANA (คันจิ.online/kana): chart + detail, speech, progress (localStorage), quiz, writing pad.
   Works without login; progress lives only in this browser. */
(function () {
  'use strict';
  var DATA = JSON.parse(document.getElementById('kana-data').textContent);
  var STORE_KEY = 'ryu_kana_v1';
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var byKey = { hiragana: {}, katakana: {} };
  ['hiragana', 'katakana'].forEach(function (s) { DATA[s].forEach(function (c) { byKey[s][c.key] = c; }); });
  var other = function (s) { return s === 'hiragana' ? 'katakana' : 'hiragana'; };

  /* ---------- progress (per browser) ---------- */
  var learned = { hiragana: [], katakana: [] };
  try { var saved = JSON.parse(localStorage.getItem(STORE_KEY) || 'null'); if (saved) { learned.hiragana = saved.hiragana || []; learned.katakana = saved.katakana || []; } } catch (e) { /* private mode */ }
  function save() { try { localStorage.setItem(STORE_KEY, JSON.stringify(learned)); } catch (e) { /* ignore */ } }
  function isLearned(s, k) { return learned[s].indexOf(k) !== -1; }
  function toggleLearned(s, k) {
    var i = learned[s].indexOf(k);
    if (i === -1) learned[s].push(k); else learned[s].splice(i, 1);
    save(); paintProgress();
  }
  function paintProgress() {
    ['hiragana', 'katakana'].forEach(function (s) {
      var n = learned[s].length, total = DATA[s].length;
      $('[data-progress-bar="' + s + '"]').style.width = (100 * n / total) + '%';
      $('[data-progress-text="' + s + '"]').textContent = n + '/' + total;
    });
    $$('.kn-cell').forEach(function (b) { b.classList.toggle('learned', isLearned(b.dataset.script, b.dataset.key)); });
    if (current) $('[data-act="learn"]').setAttribute('aria-pressed', isLearned(current.script, current.key));
  }

  /* ---------- speech (device voices) ---------- */
  var synth = window.speechSynthesis, jaVoice = null;
  function pickVoice() {
    if (!synth) return;
    var voices = synth.getVoices();
    jaVoice = voices.filter(function (v) { return /^ja/i.test(v.lang); })[0] || null;
    $('.kn-voice-note').hidden = !!jaVoice || voices.length === 0;
  }
  if (synth) { pickVoice(); synth.onvoiceschanged = pickVoice; } else { $('.kn-voice-note').hidden = false; }
  function speak(text) {
    if (!synth || !text) return;
    synth.cancel();
    var u = new SpeechSynthesisUtterance(text);
    u.lang = 'ja-JP'; u.rate = 0.8;
    if (jaVoice) u.voice = jaVoice;
    synth.speak(u);
  }

  /* ---------- stroke order (KanjiVG) ---------- */
  var STROKES = null, strokesWanted = false;
  var strokesUrl = document.getElementById('kana-js').dataset.strokesUrl;
  function loadStrokes() {
    if (STROKES) return Promise.resolve(STROKES);
    return fetch(strokesUrl).then(function (r) { return r.json(); }).then(function (d) { STROKES = d; return d; });
  }
  function drawStrokes(text) {
    var svg = D('strokes'), glyph = D('kana'), chars = text.split('');
    var have = STROKES && chars.every(function (ch) { return STROKES[ch]; });
    var show = !!(strokesWanted && have);
    svg.toggleAttribute('hidden', !show);   // SVG elements have no .hidden property: use the attribute
    glyph.hidden = show;
    if (!show) return;
    svg.setAttribute('viewBox', '0 0 ' + (109 * chars.length) + ' 109');
    var guide = '', ink = '';
    chars.forEach(function (ch, i) {
      var g = '<g transform="translate(' + (109 * i) + ',0)">';
      var paths = STROKES[ch].map(function (d) { return '<path d="' + d + '"/>'; }).join('');
      guide += g + paths + '</g>'; ink += g + paths + '</g>';
    });
    svg.innerHTML = '<g class="kj-guide">' + guide + '</g><g class="kj-ink">' + ink + '</g>';
    var plan = [];
    Array.prototype.forEach.call(svg.querySelectorAll('.kj-ink path'), function (p) {
      var len = p.getTotalLength();
      p.style.transition = 'none'; p.style.opacity = 0;
      p.style.strokeDasharray = len + ' ' + len; p.style.strokeDashoffset = len;
      plan.push([p, Math.max(260, len * 9)]);
    });
    requestAnimationFrame(function () { requestAnimationFrame(function () {
      var delay = 0;
      plan.forEach(function (x) {
        x[0].style.transition = 'stroke-dashoffset ' + x[1] + 'ms ease ' + delay + 'ms, opacity 0s linear ' + delay + 'ms';
        x[0].style.opacity = 1; x[0].style.strokeDashoffset = 0;
        delay += x[1] + 120;
      });
    }); });
  }

  /* ---------- chart + detail ---------- */
  var current = null;
  var D = function (name) { return $('[data-d="' + name + '"]'); };
  function select(script, key, opts) {
    var c = byKey[script][key]; if (!c) return;
    current = { script: script, key: key, cell: c };
    D('kana').textContent = c.kana;
    D('romaji').textContent = c.romaji;
    D('thai').textContent = c.thai;
    D('other').textContent = byKey[other(script)][key].kana;
    var ex = c.example;
    D('example-box').hidden = !ex;
    if (ex) { D('ex-word').textContent = ex.word; D('ex-romaji').textContent = ex.romaji; D('ex-meaning').textContent = ex.meaning; }
    $('[data-act="speak-ex"]').hidden = !ex;
    $$('.kn-cell.active').forEach(function (b) { b.classList.remove('active'); });
    var cell = $('.kn-cell[data-script="' + script + '"][data-key="' + key + '"]');
    if (cell) cell.classList.add('active');
    paintProgress();
    setWriting(c);
    if (strokesWanted) drawStrokes(c.kana);
    if (opts && opts.speak) speak(c.kana);
  }
  function showScript(script) {
    $$('[data-script-tab]').forEach(function (b) { var on = b.dataset.scriptTab === script; b.classList.toggle('active', on); b.setAttribute('aria-selected', on); });
    $$('.kn-chart').forEach(function (el) { el.classList.toggle('d-none', el.dataset.script !== script); });
    select(script, current ? current.key : 'あ');
  }
  $$('[data-script-tab]').forEach(function (b) { b.addEventListener('click', function () { showScript(b.dataset.scriptTab); }); });
  $$('.kn-cell').forEach(function (b) { b.addEventListener('click', function () { select(b.dataset.script, b.dataset.key, { speak: true }); }); });
  $('[data-act="speak"]').addEventListener('click', function () { if (current) speak(current.cell.kana); });
  $('[data-act="speak-ex"]').addEventListener('click', function () { if (current && current.cell.example) speak(current.cell.example.word); });
  $('[data-act="strokes"]').addEventListener('click', function () {
    strokesWanted = true;   // from now on every selected kana shows (and replays) its stroke order
    loadStrokes().then(function () { if (current) drawStrokes(current.cell.kana); }).catch(function () { /* offline */ });
  });
  $('[data-act="learn"]').addEventListener('click', function () { if (current) toggleLearned(current.script, current.key); });

  /* ---------- quiz ---------- */
  var settings = { script: 'hiragana', set: 'basic', mode: 'read' };
  $$('.kn-pills').forEach(function (group) {
    group.addEventListener('click', function (e) {
      var b = e.target.closest('button'); if (!b) return;
      $$('button', group).forEach(function (x) { x.classList.toggle('active', x === b); });
      settings[group.dataset.name] = b.dataset.v;
    });
  });
  var Q = function (name) { return $('[data-q="' + name + '"]'); };
  var stage = function (name) { $$('[data-quiz]').forEach(function (el) { el.hidden = el.dataset.quiz !== name; }); };
  var quiz = null;
  function shuffle(a) { for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)); var t = a[i]; a[i] = a[j]; a[j] = t; } return a; }
  function pool() {
    var scripts = settings.script === 'mix' ? ['hiragana', 'katakana'] : [settings.script];
    var out = [];
    scripts.forEach(function (s) {
      DATA[s].forEach(function (c) {
        if (settings.set === 'basic' && c.group !== 'basic') return;
        if (settings.set === 'todo' && isLearned(s, c.key)) return;
        out.push({ script: s, cell: c });
      });
    });
    return out;
  }
  function startQuiz() {
    var items = pool();
    if (items.length < 4) {   // "not learned yet" can run dry
      stage('setup');
      $('[data-act="quiz-start"]').insertAdjacentHTML('afterend', '<p class="ms-note text-center mt-2 mb-0 kn-quiz-empty">จำได้เกือบครบแล้ว เลือก "ทั้งหมด" เพื่อทดสอบต่อ</p>');
      return;
    }
    $$('.kn-quiz-empty').forEach(function (el) { el.remove(); });
    quiz = { items: shuffle(items.slice()).slice(0, 10), i: 0, score: 0, misses: [], all: items };
    stage('run'); ask();
  }
  function ask() {
    var q = quiz.items[quiz.i], read = settings.mode === 'read';
    Q('count').textContent = 'ข้อ ' + (quiz.i + 1) + '/' + quiz.items.length;
    Q('score').textContent = 'ถูก ' + quiz.score;
    Q('prompt').textContent = read ? q.cell.kana : q.cell.romaji;
    Q('prompt').classList.toggle('romaji', !read);
    Q('feedback').textContent = '';
    var label = function (it) { return read ? it.cell.romaji : it.cell.kana; };
    var seen = {}; seen[label(q)] = 1;
    var options = [q];
    shuffle(quiz.all.slice()).some(function (it) {
      // a distractor must not be another correct answer (じ/ぢ are both "ji"; あ/ア share "a" in mixed mode)
      if (!seen[label(it)] && it.cell.romaji !== q.cell.romaji) { seen[label(it)] = 1; options.push(it); }
      return options.length === 4;
    });
    Q('choices').innerHTML = '';
    shuffle(options).forEach(function (it) {
      var b = document.createElement('button');
      b.type = 'button'; b.textContent = label(it); if (!read) b.className = 'jp';
      b.addEventListener('click', function () { answer(b, it === q, q); });
      Q('choices').appendChild(b);
    });
  }
  var speakLater = null;
  function answer(btn, ok, q) {
    $$('button', Q('choices')).forEach(function (b) {
      b.disabled = true;
      if (b.textContent === (settings.mode === 'read' ? q.cell.romaji : q.cell.kana)) b.classList.add('right');
    });
    if (ok) { quiz.score++; Q('feedback').textContent = 'ถูกต้อง  ' + q.cell.kana + ' อ่านว่า ' + q.cell.thai; }
    else { btn.classList.add('wrong'); quiz.misses.push(q); Q('feedback').textContent = 'คำตอบคือ ' + q.cell.kana + ' = ' + q.cell.romaji + ' (' + q.cell.thai + ')'; }
    Q('score').textContent = 'ถูก ' + quiz.score;
    speak(q.cell.kana);
    clearTimeout(speakLater);
    speakLater = setTimeout(function () {
      quiz.i++;
      if (quiz.i < quiz.items.length) ask(); else finish();
    }, ok ? 900 : 1900);
  }
  function finish() {
    stage('result');
    var n = quiz.items.length;
    Q('final').textContent = quiz.score;
    Q('final').nextElementSibling.textContent = '/' + n;
    Q('verdict').textContent = quiz.score === n ? 'เยี่ยมมาก ตอบถูกทุกข้อ ลองชุดที่ยากขึ้นได้เลย'
      : quiz.score >= n * 0.7 ? 'ดีมาก ทบทวนตัวที่ผิดอีกนิดก็จำได้ครบ' : 'ไม่เป็นไร ทบทวนตัวที่ผิดในตาราง แล้วลองใหม่อีกรอบ';
    Q('misses').innerHTML = '';
    quiz.misses.forEach(function (m) {
      var s = document.createElement('span');
      s.innerHTML = '<span class="ms-jp"></span><small></small>';
      s.firstChild.textContent = m.cell.kana; s.lastChild.textContent = m.cell.romaji;
      Q('misses').appendChild(s);
    });
  }
  $$('[data-act="quiz-start"]').forEach(function (b) { b.addEventListener('click', startQuiz); });
  $('[data-act="quiz-setup"]').addEventListener('click', function () { stage('setup'); });

  /* ---------- writing pad ---------- */
  var canvas = $('#kn-canvas'), ctx = canvas.getContext('2d'), showGuide = true, writing = null, drawing = false, strokes = [];
  function redraw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (writing && showGuide) {
      ctx.fillStyle = 'rgba(15, 23, 42, .12)';
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      var size = writing.kana.length > 1 ? 280 : 440;
      ctx.font = '600 ' + size + 'px "Hiragino Sans", "Noto Sans JP", "Yu Gothic", sans-serif';
      ctx.fillText(writing.kana, canvas.width / 2, canvas.height / 2 + 10);
    }
    ctx.strokeStyle = '#0b0d12'; ctx.lineWidth = 18; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    strokes.forEach(function (pts) {
      ctx.beginPath();
      pts.forEach(function (p, i) { if (i) ctx.lineTo(p[0], p[1]); else ctx.moveTo(p[0], p[1]); });
      if (pts.length === 1) ctx.lineTo(pts[0][0] + .1, pts[0][1]);
      ctx.stroke();
    });
  }
  function setWriting(c) {
    writing = c; strokes = [];
    $('[data-w="kana"]').textContent = c.kana; $('[data-w="romaji"]').textContent = c.romaji;
    redraw();
  }
  function point(e) {
    var r = canvas.getBoundingClientRect();
    return [(e.clientX - r.left) * canvas.width / r.width, (e.clientY - r.top) * canvas.height / r.height];
  }
  canvas.addEventListener('pointerdown', function (e) { drawing = true; canvas.setPointerCapture(e.pointerId); strokes.push([point(e)]); redraw(); });
  canvas.addEventListener('pointermove', function (e) { if (!drawing) return; strokes[strokes.length - 1].push(point(e)); redraw(); });
  ['pointerup', 'pointercancel', 'pointerleave'].forEach(function (t) { canvas.addEventListener(t, function () { drawing = false; }); });
  $('[data-act="write-clear"]').addEventListener('click', function () { strokes = []; redraw(); });
  $('[data-act="write-guide"]').addEventListener('click', function () { showGuide = !showGuide; this.setAttribute('aria-pressed', showGuide); redraw(); });
  $('[data-act="write-random"]').addEventListener('click', function () {
    var s = current ? current.script : 'hiragana', list = DATA[s].filter(function (c) { return c.group === 'basic'; });
    var c = list[Math.floor(Math.random() * list.length)];
    select(s, c.key);
  });

  showScript('hiragana');
})();
