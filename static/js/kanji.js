/* RYU KANJI (คันจิ.online): search, "learned" progress (localStorage), stroke-order animation, speech, level quiz.
   Also exposes window.RyuStrokes.play(svg) for the kana site. */
(function () {
  'use strict';
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var esc = function (t) { var d = document.createElement('div'); d.textContent = t == null ? '' : t; return d.innerHTML; };

  /* ---------- stroke order ---------- */
  function play(svg) {
    if (!svg) return;
    var plan = [];
    $$('.kj-ink path', svg).forEach(function (p) {     // 1) hide every stroke without animating
      var len = p.getTotalLength ? p.getTotalLength() : 100;
      p.style.transition = 'none'; p.style.opacity = 0;
      p.style.strokeDasharray = len + ' ' + len; p.style.strokeDashoffset = len;
      plan.push([p, Math.max(260, len * 9)]);
    });
    requestAnimationFrame(function () { requestAnimationFrame(function () {   // 2) next frame: draw them one by one
      var delay = 0;
      plan.forEach(function (x) {
        x[0].style.transition = 'stroke-dashoffset ' + x[1] + 'ms ease ' + delay + 'ms, opacity 0s linear ' + delay + 'ms';
        x[0].style.opacity = 1; x[0].style.strokeDashoffset = 0;
        delay += x[1] + 120;
      });
    }); });
  }
  window.RyuStrokes = { play: play };

  /* ---------- speech ---------- */
  var synth = window.speechSynthesis, voice = null;
  function pick() { if (synth) voice = synth.getVoices().filter(function (v) { return /^ja/i.test(v.lang); })[0] || null; }
  if (synth) { pick(); synth.onvoiceschanged = pick; }
  function say(text) {
    if (!synth || !text) return;
    synth.cancel();
    var u = new SpeechSynthesisUtterance(text); u.lang = 'ja-JP'; u.rate = 0.85; if (voice) u.voice = voice;
    synth.speak(u);
  }
  document.addEventListener('click', function (e) { var b = e.target.closest('[data-say]'); if (b) say(b.dataset.say); });

  /* ---------- learned (per browser) ---------- */
  var KEY = 'ryu_kanji_v1', learned = [];
  try { learned = JSON.parse(localStorage.getItem(KEY) || '[]') || []; } catch (e) { learned = []; }
  function persist() { try { localStorage.setItem(KEY, JSON.stringify(learned)); } catch (e) { /* private mode */ } }
  function paint() {
    $$('.kj-tile').forEach(function (t) { t.classList.toggle('learned', learned.indexOf(t.dataset.char) !== -1); });
    var tiles = $$('.kj-tile'), bar = $('[data-kj-progress]');
    if (bar && tiles.length) {
      var n = tiles.filter(function (t) { return t.classList.contains('learned'); }).length;
      bar.style.width = (100 * n / tiles.length) + '%';
      $('[data-kj-progress-text]').textContent = n + '/' + tiles.length;
    }
    var btn = $('[data-act="kj-learn"]');
    if (btn) btn.setAttribute('aria-pressed', learned.indexOf(btn.dataset.char) !== -1);
  }
  var learnBtn = $('[data-act="kj-learn"]');
  if (learnBtn) learnBtn.addEventListener('click', function () {
    var i = learned.indexOf(learnBtn.dataset.char);
    if (i === -1) learned.push(learnBtn.dataset.char); else learned.splice(i, 1);
    persist(); paint();
  });

  /* ---------- search ---------- */
  $$('.kj-search').forEach(function (form) {
    var input = $('input', form), box = $('.kj-results', form), timer = null, seq = 0;
    function render(items, q) {
      if (!q) { box.hidden = true; return; }
      box.hidden = false;
      box.innerHTML = items.length ? items.map(function (r) {
        return '<a href="/kanji/' + encodeURIComponent(r.char) + '/"><span class="ms-jp">' + esc(r.char) + '</span><span class="txt"><b>' +
          esc(r.th || r.en) + '</b><small>' + esc(r.level) + (r.th ? ' · ' + esc(r.en) : '') + '</small></span></a>';
      }).join('') : '<div class="kj-noresult">ไม่พบคันจิที่ตรงกับ "' + esc(q) + '"</div>';
    }
    input.addEventListener('input', function () {
      clearTimeout(timer);
      var q = input.value.trim(), mine = ++seq;
      timer = setTimeout(function () {
        if (!q) { render([], ''); return; }
        fetch(form.dataset.searchUrl + '?q=' + encodeURIComponent(q)).then(function (r) { return r.json(); })
          .then(function (d) { if (mine === seq) render(d.results || [], q); }).catch(function () { /* offline */ });
      }, 220);
    });
    document.addEventListener('click', function (e) { if (!form.contains(e.target)) box.hidden = true; });
    input.addEventListener('focus', function () { if (input.value.trim() && box.innerHTML) box.hidden = false; });
  });

  /* ---------- level quiz ---------- */
  var quizData = document.getElementById('kj-quiz-data');
  if (quizData) {
    var ALL = JSON.parse(quizData.textContent), Q = function (n) { return $('[data-q="' + n + '"]'); }, quiz = null, timer2 = null;
    var stage = function (n) { $$('[data-quiz]').forEach(function (el) { el.hidden = el.dataset.quiz !== n; }); };
    var shuffle = function (a) { for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)); var t = a[i]; a[i] = a[j]; a[j] = t; } return a; };
    function start() {
      var todo = $('[data-kj-todo]') && $('[data-kj-todo]').checked;
      var pool = ALL.filter(function (x) { return x.m && (!todo || learned.indexOf(x.c) === -1); });
      if (pool.length < 4) pool = ALL.filter(function (x) { return x.m; });
      quiz = { items: shuffle(pool.slice()).slice(0, 10), i: 0, score: 0, misses: [] };
      stage('run'); ask();
    }
    function ask() {
      var q = quiz.items[quiz.i], options = [q], seen = {}; seen[q.m] = 1;
      shuffle(ALL.slice()).some(function (x) { if (x.m && !seen[x.m]) { seen[x.m] = 1; options.push(x); } return options.length === 4; });
      Q('count').textContent = 'ข้อ ' + (quiz.i + 1) + '/' + quiz.items.length;
      Q('score').textContent = 'ถูก ' + quiz.score;
      Q('prompt').textContent = q.c; Q('feedback').textContent = '';
      Q('choices').innerHTML = '';
      shuffle(options).forEach(function (x) {
        var b = document.createElement('button'); b.type = 'button'; b.textContent = x.m;
        b.addEventListener('click', function () { answer(b, x === q, q); });
        Q('choices').appendChild(b);
      });
    }
    function answer(btn, ok, q) {
      $$('button', Q('choices')).forEach(function (b) { b.disabled = true; if (b.textContent === q.m) b.classList.add('right'); });
      if (ok) quiz.score++; else { btn.classList.add('wrong'); quiz.misses.push(q); }
      Q('feedback').textContent = (ok ? 'ถูกต้อง  ' : 'คำตอบคือ ') + q.c + ' = ' + q.m;
      Q('score').textContent = 'ถูก ' + quiz.score;
      clearTimeout(timer2);
      timer2 = setTimeout(function () { quiz.i++; if (quiz.i < quiz.items.length) ask(); else finish(); }, ok ? 900 : 1900);
    }
    function finish() {
      stage('result');
      var n = quiz.items.length;
      Q('final').textContent = quiz.score; Q('of').textContent = '/' + n;
      Q('verdict').textContent = quiz.score === n ? 'เยี่ยมมาก ตอบถูกทุกข้อ' : quiz.score >= n * 0.7 ? 'ดีมาก ทบทวนตัวที่ผิดอีกนิด' : 'ไม่เป็นไร ลองดูรายละเอียดตัวที่ผิดแล้วทำใหม่';
      Q('misses').innerHTML = quiz.misses.map(function (m) {
        return '<a href="/kanji/' + encodeURIComponent(m.c) + '/" class="text-decoration-none"><span><span class="ms-jp">' + esc(m.c) + '</span><small>' + esc(m.m) + '</small></span></a>';
      }).join('');
    }
    $$('[data-act="kj-quiz-start"]').forEach(function (b) { b.addEventListener('click', start); });
  }

  /* ---------- detail page ---------- */
  var svg = $('[data-strokes]');
  if (svg) {
    var btnPlay = $('[data-act="play-strokes"]');
    if (btnPlay) btnPlay.addEventListener('click', function () { play(svg); });
    if ('IntersectionObserver' in window) {
      var io = new IntersectionObserver(function (en) { if (en[0].isIntersecting) { play(svg); io.disconnect(); } });
      io.observe(svg);
    } else { play(svg); }
  }
  paint();
})();
