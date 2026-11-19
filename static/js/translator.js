/* RYU TRANSLATOR (แปลภาษาญี่ปุ่น.online): direction (auto / forced), politeness level, AI translation with polling,
   speech, copy, and a per-browser history.  No login; AI calls are rate-limited server-side. */
(function () {
  'use strict';
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var esc = function (t) { var d = document.createElement('div'); d.textContent = t == null ? '' : t; return d.innerHTML; };
  var wait = function (ms) { return new Promise(function (ok) { setTimeout(ok, ms); }); };
  function csrf() { var m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/); return m ? decodeURIComponent(m[1]) : ''; }
  var JA = /[぀-ヿ一-鿿]/, TH = /[฀-๿]/;
  var form = $('.tr-box'), text = $('textarea', form), O = function (n) { return $('[data-o="' + n + '"]'); }, OUT = function (n) { return $('[data-out="' + n + '"]'); };
  var state = { dir: 'auto', style: 'polite', last: null };

  /* ---------- direction + style ---------- */
  function effectiveDir() {
    if (state.dir !== 'auto') return state.dir;
    var t = text.value; return JA.test(t) && !TH.test(t) ? 'ja2th' : 'th2ja';
  }
  function paintDir() {
    var d = effectiveDir();
    $('[data-dir-from]').textContent = d === 'th2ja' ? 'ไทย' : 'ญี่ปุ่น';
    $('[data-dir-to]').textContent = d === 'th2ja' ? 'ญี่ปุ่น' : 'ไทย';
    $('[data-dir-auto]').hidden = state.dir !== 'auto';
    $('.tr-styles').classList.toggle('dim', d === 'ja2th');   // politeness only shapes Japanese output
  }
  $('[data-act="swap"]').addEventListener('click', function () { state.dir = effectiveDir() === 'th2ja' ? 'ja2th' : 'th2ja'; paintDir(); });
  $$('.tr-styles button').forEach(function (b) {
    b.addEventListener('click', function () { $$('.tr-styles button').forEach(function (x) { x.classList.toggle('active', x === b); }); state.style = b.dataset.v; });
  });
  text.addEventListener('input', function () { $('[data-count]').textContent = text.value.length + '/500'; paintDir(); });
  $$('[data-sample]').forEach(function (b) { b.addEventListener('click', function () { text.value = b.dataset.sample; state.dir = 'auto'; text.dispatchEvent(new Event('input')); go(); }); });

  /* ---------- speech + copy ---------- */
  var synth = window.speechSynthesis, voice = null;
  function pick() { if (synth) voice = synth.getVoices().filter(function (v) { return /^ja/i.test(v.lang); })[0] || null; }
  if (synth) { pick(); synth.onvoiceschanged = pick; }
  function say(t) { if (!synth || !t) return; synth.cancel(); var u = new SpeechSynthesisUtterance(t); u.lang = 'ja-JP'; u.rate = 0.9; if (voice) u.voice = voice; synth.speak(u); }
  document.addEventListener('click', function (e) { var b = e.target.closest('[data-say]'); if (b) say(b.dataset.say); });
  $('[data-act="speak"]').addEventListener('click', function () {
    var r = state.last; if (!r) return;
    say(r.direction === 'th2ja' ? r.translation : (r.source || ''));
  });
  $('[data-act="copy"]').addEventListener('click', function () {
    var btn = this; if (!state.last || !navigator.clipboard) return;
    navigator.clipboard.writeText(state.last.translation).then(function () { $('span', btn).textContent = 'คัดลอกแล้ว'; setTimeout(function () { $('span', btn).textContent = 'คัดลอก'; }, 1500); });
  });

  /* ---------- result ---------- */
  function show(r, source) {
    r.source = source; state.last = r;
    OUT('empty').hidden = true; OUT('wait').hidden = true; OUT('result').hidden = false; OUT('extra').hidden = false;
    O('translation').textContent = r.translation;
    O('translation').classList.toggle('ms-jp', r.direction === 'th2ja');
    O('reading').textContent = r.reading || '';
    O('reading_th').textContent = r.reading_th ? 'อ่านว่า ' + r.reading_th : '';
    $('[data-act="speak"]').hidden = !(r.direction === 'th2ja' ? r.translation : source);
    var alts = r.alternatives || [];
    $('[data-x="alt-col"]').hidden = !alts.length;
    O('alternatives').innerHTML = alts.map(function (a) {
      return '<button type="button" class="tr-alt" data-say="' + esc(a.reading || a.text) + '"><small>' + esc(a.label) + '</small><span class="ms-jp">' + esc(a.text) + '</span>' +
        (a.reading ? '<span class="rd ms-jp">' + esc(a.reading) + '</span>' : '') + '</button>';
    }).join('');
    O('politeness').textContent = r.politeness || '';
    O('notes').innerHTML = (r.notes || []).map(function (n) { return '<li>' + esc(n) + '</li>'; }).join('');
    $('[data-x="notes-col"]').hidden = !((r.notes || []).length || r.politeness);
    var dict = O('words').dataset.dict;
    O('words').innerHTML = (r.words || []).map(function (w) {
      return '<a class="tr-word" href="' + esc(dict) + (dict.indexOf('?') === -1 ? '?' : '&') + 'q=' + encodeURIComponent(w.word) + '"><span class="ms-jp">' + esc(w.word) + '</span>' +
        (w.reading && w.reading !== w.word ? '<small class="ms-jp">' + esc(w.reading) + '</small>' : '') + '<em>' + esc(w.th) + '</em></a>';
    }).join('');
    $('[data-x="words-col"]').hidden = !(r.words || []).length;
    remember(source, r);
  }
  function error(msg) { OUT('wait').hidden = true; OUT('empty').hidden = false; OUT('empty').textContent = msg; }

  function go() {
    var source = text.value.trim();
    if (!source) { text.focus(); return; }
    var btn = $('[data-act="translate"]'); btn.disabled = true;
    OUT('empty').hidden = true; OUT('result').hidden = true; OUT('wait').hidden = false;
    fetch(form.dataset.api, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
      body: JSON.stringify({ text: source, direction: state.dir, style: state.style }) })
      .then(function (r) { return r.json().then(function (d) { if (!r.ok || d.ok === false) throw new Error(d.message || 'แปลไม่สำเร็จ'); return d.data; }); })
      .then(function (d) {
        if (d.state === 'done') return d.result;
        var tries = 0;
        return (function poll() {
          return wait(1500).then(function () { return fetch(form.dataset.api + encodeURIComponent(d.key) + '/'); })
            .then(function (r) { return r.json(); })
            .then(function (p) { if (p.data && p.data.state === 'done') return p.data.result; if (++tries > 30) throw new Error('AI ตอบไม่ทัน ลองใหม่อีกครั้ง'); return poll(); });
        })();
      })
      .then(function (r) { show(r, source); })
      .catch(function (err) { error(err.message); })
      .then(function () { btn.disabled = false; });
  }
  form.addEventListener('submit', go);
  text.addEventListener('keydown', function (e) { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) go(); });

  /* ---------- history (this browser only) ---------- */
  var KEY = 'ryu_translate_history_v1';
  function load() { try { return JSON.parse(localStorage.getItem(KEY) || '[]') || []; } catch (e) { return []; } }
  function save(list) { try { localStorage.setItem(KEY, JSON.stringify(list.slice(0, 10))); } catch (e) { /* private mode */ } }
  function remember(source, r) {
    var list = load().filter(function (h) { return !(h.s === source && h.d === r.direction && h.st === r.style); });
    list.unshift({ s: source, t: r.translation, d: r.direction, st: r.style }); save(list); paintHistory();
  }
  function paintHistory() {
    var list = load(), box = $('[data-history]');
    box.innerHTML = list.length ? list.map(function (h, i) {
      return '<button type="button" class="tr-hist" data-hist="' + i + '"><span>' + esc(h.s) + '</span><span class="' + (h.d === 'th2ja' ? 'ms-jp' : '') + '">' + esc(h.t) + '</span></button>';
    }).join('') : '<p class="ms-note mb-0">ยังไม่มีประวัติ</p>';
  }
  $('[data-history]').addEventListener('click', function (e) {
    var b = e.target.closest('[data-hist]'); if (!b) return;
    var h = load()[+b.dataset.hist]; if (!h) return;
    text.value = h.s; state.dir = h.d; state.style = h.st;
    $$('.tr-styles button').forEach(function (x) { x.classList.toggle('active', x.dataset.v === h.st); });
    text.dispatchEvent(new Event('input')); window.scrollTo({ top: 0, behavior: 'smooth' }); go();
  });
  $('[data-act="clear-history"]').addEventListener('click', function () { save([]); paintHistory(); });

  paintDir(); paintHistory();
})();
