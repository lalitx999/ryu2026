/* RYU DICTIONARY (พจนานุกรมภาษาญี่ปุ่น.online): search (ja / th / en), "ask AI" for Thai words, on-demand AI
   explanation on word pages, speech.  No login; AI calls are rate-limited server-side. */
(function () {
  'use strict';
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var esc = function (t) { var d = document.createElement('div'); d.textContent = t == null ? '' : t; return d.innerHTML; };
  var wait = function (ms) { return new Promise(function (ok) { setTimeout(ok, ms); }); };
  function csrf() { var m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/); return m ? decodeURIComponent(m[1]) : ''; }
  function post(url, body) {
    return fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() }, body: JSON.stringify(body || {}) })
      .then(function (r) { return r.json().then(function (d) { if (!r.ok || d.ok === false) throw new Error(d.message || 'เกิดข้อผิดพลาด'); return d; }); });
  }
  var getJSON = function (url) { return fetch(url).then(function (r) { return r.json(); }); };

  /* ---------- speech ---------- */
  var synth = window.speechSynthesis, voice = null;
  function pick() { if (synth) voice = synth.getVoices().filter(function (v) { return /^ja/i.test(v.lang); })[0] || null; }
  if (synth) { pick(); synth.onvoiceschanged = pick; }
  document.addEventListener('click', function (e) {
    var b = e.target.closest('[data-say]'); if (!b || !synth) return;
    synth.cancel(); var u = new SpeechSynthesisUtterance(b.dataset.say); u.lang = 'ja-JP'; u.rate = 0.85; if (voice) u.voice = voice; synth.speak(u);
  });

  /* ---------- search page ---------- */
  var form = $('.dc-search');
  if (form) {
    var input = $('input', form), panel = $('#results-panel'), R = function (n) { return $('[data-r="' + n + '"]'); };
    var timer = null, seq = 0, lastQ = '';
    function card(w) {
      return '<a class="dc-card" href="/word/' + w.id + '/"><span class="w ms-jp">' + esc(w.word) + '</span>' +
        (w.reading ? '<span class="r ms-jp">' + esc(w.reading) + '</span>' : '') +
        '<span class="m">' + esc(w.th || w.en) + '</span>' + (w.th ? '<span class="e">' + esc(w.en) + '</span>' : '') + '</a>';
    }
    function render(d, q) {
      panel.hidden = !q;
      if (!q) return;
      R('title').textContent = 'ผลการค้นหา "' + q + '"';
      R('count').textContent = d.results.length ? d.results.length + ' คำ' : '';
      R('list').innerHTML = d.results.length ? d.results.map(card).join('') : '<p class="ms-note mb-0">ไม่พบคำที่ตรงกัน</p>';
      R('ai').hidden = !(d.script === 'th' && !d.thai_cached);
      R('ai-msg').textContent = '';
      var sug = d.suggestions || [];
      R('suggest').hidden = !sug.length;
      R('suggest').innerHTML = sug.length ? '<p class="ms-note mb-2">AI เสนอคำเหล่านี้เพิ่ม แต่ไม่พบในพจนานุกรมชุดคำที่ใช้บ่อย</p>' +
        sug.map(function (s) { return '<span class="ms-jp">' + esc(s.word) + (s.reading ? ' (' + esc(s.reading) + ')' : '') + '</span>'; }).join('') : '';
    }
    function run(q) {
      var mine = ++seq; lastQ = q;
      if (!q) { render({ results: [] }, ''); return Promise.resolve(); }
      return getJSON(form.dataset.searchUrl + '?q=' + encodeURIComponent(q)).then(function (d) { if (mine === seq) render(d, q); });
    }
    input.addEventListener('input', function () { clearTimeout(timer); var q = input.value.trim(); timer = setTimeout(function () { run(q); }, 250); });
    $$('[data-sample]').forEach(function (b) { b.addEventListener('click', function () { input.value = b.dataset.sample; run(b.dataset.sample); panel.scrollIntoView({ behavior: 'smooth' }); }); });
    $('[data-act="ask-ai"]').addEventListener('click', function () {
      var btn = this, q = lastQ; btn.disabled = true; R('ai-msg').textContent = 'AI กำลังหาคำ…';
      post(form.dataset.thaiUrl, { q: q }).then(function () {
        var tries = 0;
        (function poll() {
          getJSON(form.dataset.searchUrl + '?q=' + encodeURIComponent(q)).then(function (d) {
            if (d.thai_cached || tries++ > 20) { btn.disabled = false; if (q === lastQ) render(d, q); if (!d.thai_cached) R('ai-msg').textContent = 'AI ตอบไม่ทัน ลองใหม่อีกครั้ง'; }
            else wait(1500).then(poll);
          });
        })();
      }).catch(function (err) { btn.disabled = false; R('ai-msg').textContent = err.message; });
    });
    var initial = new URLSearchParams(location.search).get('q');
    if (initial) { input.value = initial; run(initial); }
  }

  /* ---------- word page: on-demand AI explanation ---------- */
  var box = $('[data-word-api]');
  if (box && box.dataset.ai === 'none') {
    var W = function (n) { return $('[data-w="' + n + '"]'); };
    W('wait').hidden = false;
    var fill = function (d) {
      W('th').textContent = d.th; W('explain').textContent = d.explain; W('wait').hidden = true; W('tag').hidden = false;
      if (d.examples && d.examples.length) {
        W('examples').innerHTML = d.examples.map(function (x) {
          return '<button type="button" class="dc-example" data-say="' + esc(x.reading) + '"><span class="ja ms-jp">' + esc(x.ja) + '</span><span class="rd ms-jp">' +
            esc(x.reading) + '</span><span class="th">' + esc(x.th) + '</span></button>';
        }).join('');
      }
    };
    post(box.dataset.wordApi).then(function (r) {
      if (r.data.ai !== 'none') { fill(r.data); return; }
      var tries = 0;
      (function poll() {
        getJSON(box.dataset.wordApi).then(function (d) {
          if (d.data && d.data.ai !== 'none') fill(d.data);
          else if (tries++ < 20) wait(2000).then(poll);
          else { W('wait').querySelector('span').textContent = 'AI ยังไม่ว่าง ลองเปิดหน้านี้ใหม่ภายหลัง'; }
        });
      })();
    }).catch(function (err) { W('wait').querySelector('span').textContent = err.message; });
  }
})();
