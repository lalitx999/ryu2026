/* Sentence Builder: put the Japanese word blocks in order (click, drag-and-drop, or arrow buttons). */
(function () {
  const G = window.Ryu.games;
  let target, chosen, avail, score = 0, streak = 0, fb, drag, over, body, t;
  function next() { target = G.pick(G.data.SENTENCE_POOL); chosen = []; avail = G.shuffle(target.words); fb = null; drag = over = null; draw(); }
  function reset() { chosen = []; avail = G.shuffle(target.words); fb = null; draw(); }
  function check() {
    if (!chosen.length) { fb = { type: 'error', message: '⚠️ กรุณาเลือกคำศัพท์มาต่อประโยคก่อนครับ' }; return draw(); }
    if (chosen.join(' ') === target.jpFull) {
      score += 100; streak += 1; fb = { type: 'success', message: '🎉 ยอดเยี่ยมมาก! ประโยคถูกต้องสมบูรณ์ (+100 คะแนน)' };
      G.speak(target.jpFull); G.confetti({ particleCount: 70, spread: 60, origin: { y: 0.6 } }); draw(); t = setTimeout(next, 2000);
    } else { streak = 0; fb = { type: 'error', message: '❌ ยังไม่ถูกต้อง ลองลากสลับตำแหน่งคำศัพท์ดูใหม่นะ!' }; draw(); }
  }
  function draw() {
    const e = G.esc;
    body.innerHTML = `<div class="g-card g-center" style="padding:20px">
      <div class="g-target"><div class="t11 fw-bold text-uppercase mb-1" style="color:#92400e">🇹🇭 แปลประโยคภาษาไทยต่อไปนี้เป็นภาษาญี่ปุ่น:</div><div style="font-size:24px;font-weight:900;color:#172554">"${e(target.th)}"</div>
        ${target.hint ? `<div class="t11 fw-semibold mt-1 px-3 py-1 rounded-pill d-inline-block" style="color:#b45309;background:rgba(255,255,255,.7);border:1px solid #fde68a">💡 คำใบ้: ${e(target.hint)}</div>` : ''}</div>
      ${fb ? `<div class="${fb.type === 'success' ? 'g-ok g-bounce' : 'g-bad'}"><span>${e(fb.message)}</span><button type="button" class="btn btn-sm btn-light t11 fw-bold border flex-shrink-0" data-act="speak">🔊 ฟังเสียงเฉลย</button></div>` : ''}
      <div class="w-100" style="max-width:42rem"><div class="d-flex justify-content-between mb-1 px-1"><span class="t12 fw-bold" style="color:#374151">📍 เรียงประโยคของคุณ (คลิกลากสลับที่ ✋ หรือกด ◀ ▶ เพื่อเลื่อนคำ):</span><span class="t11 text-secondary">${chosen.length}/${target.words.length} คำ</span></div>
        <div class="g-slots" id="s-slots">${chosen.length ? chosen.map((w, i) => `<div class="g-word g-jp ${over === i ? 'over' : ''}" draggable="true" data-i="${i}"><span class="t10" style="opacity:.6">⋮⋮</span>${i > 0 ? `<button type="button" class="mini" data-shift="${i}:-1" title="เลื่อนไปทางซ้าย">◀</button>` : ''}<span class="px-1" style="font-size:16px">${e(w)}</span>${i < chosen.length - 1 ? `<button type="button" class="mini" data-shift="${i}:1" title="เลื่อนไปทางขวา">▶</button>` : ''}<button type="button" class="mini rm" data-rm="${i}" title="นำคำนี้ออก">✕</button></div>`).join('')
          : '<div class="text-secondary t12 fw-medium py-3 d-flex flex-column align-items-center gap-1"><span style="font-size:24px;opacity:.6">👆</span><span>กดเลือกคำศัพท์จากด้านล่างเพื่อเริ่มเรียงประโยค</span></div>'}</div></div>
      <div class="g-avail"><div class="t11 fw-bold mb-2" style="color:#374151">📦 คลังคำศัพท์ที่มีให้ (คลิกคำที่ต้องการเพื่อนำไปต่อประโยค):</div><div class="d-flex flex-wrap gap-2 justify-content-center" style="min-height:46px">
        ${avail.length ? avail.map((w, i) => `<button type="button" class="g-jp" data-add="${i}"><span class="t12" style="color:#f59e0b">➕</span> ${e(w)}</button>`).join('') : '<span class="text-secondary t12 fst-italic">นำคำศัพท์ไปวางในประโยคครบแล้ว! กดตรวจคำตอบได้เลย</span>'}</div></div>
      <div class="d-flex flex-wrap gap-3 justify-content-center mt-1"><button class="g-btn green" style="font-size:14px;padding:10px 24px;font-weight:900" data-act="check" ${chosen.length ? '' : 'disabled'}>✔️ ตรวจคำตอบประโยค</button>
        <button class="btn btn-secondary btn-sm fw-bold" data-act="reset">🔄 เรียงใหม่ (Reset)</button><button class="btn btn-sm fw-bold" style="background:#dbeafe;color:#1e3a8a;border:1px solid #93c5fd" data-act="speak">🔊 ฟังเสียงประโยค</button>
        <button class="btn btn-sm fw-bold" style="background:#fef3c7;color:#78350f;border:1px solid #fcd34d" data-act="skip">⏭️ ข้ามประโยคนี้</button></div></div>`;
    document.getElementById('s-score').textContent = `🏆 ${score} แต้ม`; document.getElementById('s-streak').textContent = `🔥 ${streak} ข้อติด`;
  }
  function move(from, to) { if (to < 0 || to >= chosen.length || from === to) return; const [w] = chosen.splice(from, 1); chosen.splice(to, 0, w); fb = null; }
  G.register('sentence_builder', {
    start(st) {
      body = G.box(st, 'Sentence Builder — แต่งประโยคภาษาญี่ปุ่น', '✍️',
        '<span id="s-score" class="px-2 py-1 rounded font-monospace fw-bolder t12" style="background:#fbbf24;color:#000"></span><span id="s-streak" class="px-2 py-1 rounded font-monospace fw-bolder t12" style="background:#f97316;color:#fff"></span>');
      body.addEventListener('click', (ev) => {
        const t2 = ev.target;
        const add = t2.closest('[data-add]'); if (add) { const i = +add.dataset.add; chosen.push(avail[i]); avail.splice(i, 1); fb = null; return draw(); }
        const rm = t2.closest('[data-rm]'); if (rm) { const i = +rm.dataset.rm; avail.push(chosen[i]); chosen.splice(i, 1); fb = null; return draw(); }
        const sh = t2.closest('[data-shift]'); if (sh) { const [i, d] = sh.dataset.shift.split(':').map(Number); move(i, i + d); return draw(); }
        const a = t2.closest('[data-act]'); if (!a) return;
        ({ check, reset, skip: () => { clearTimeout(t); next(); }, speak: () => G.speak(target.jpFull) })[a.dataset.act]();
      });
      body.addEventListener('dragstart', (ev) => { const w = ev.target.closest('.g-word'); if (!w) return; drag = +w.dataset.i; ev.dataTransfer.setData('text/plain', String(drag)); ev.dataTransfer.effectAllowed = 'move'; });
      body.addEventListener('dragover', (ev) => { const w = ev.target.closest('.g-word'); if (!w) return; ev.preventDefault(); const i = +w.dataset.i; if (over !== i) { over = i; body.querySelectorAll('.g-word').forEach((x) => x.classList.toggle('over', +x.dataset.i === i)); } });
      body.addEventListener('drop', (ev) => { const w = ev.target.closest('.g-word'); if (!w) return; ev.preventDefault(); if (drag !== null) move(drag, +w.dataset.i); drag = over = null; draw(); });
      body.addEventListener('dragend', () => { drag = over = null; body.querySelectorAll('.g-word.over').forEach((x) => x.classList.remove('over')); });
      next();
    },
    stop() { clearTimeout(t); },
  });
})();
