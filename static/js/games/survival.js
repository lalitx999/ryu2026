/* Shiba Survival 100: 3 lives, up to 100 questions (the pool of 20 cycles). */
(function () {
  const G = window.Ryu.games;
  let idx, lives, score, q, active, end, body;
  function ask(i) { const p = G.data.SURVIVAL_POOL[(i - 1) % G.data.SURVIVAL_POOL.length]; q = Object.assign({}, p, { choices: G.shuffle(p.choices) }); }
  function begin() { idx = 1; lives = 3; score = 0; active = true; end = null; ask(1); draw(); }
  function finish(text) { active = false; end = text; G.submitScore('survival100', score); draw(); }
  function answer(c) {
    if (!active) return;
    if (c === q.answer) {
      score += 10;
      if (idx >= 100) return finish('🎉 ยินดีด้วย! คุณพิชิต Shiba Survival 100 ข้อสำเร็จแล้ว!');
      idx += 1; ask(idx);
    } else {
      lives -= 1;
      if (lives <= 0) return finish(`☠️ Game Over! คุณรอดมาได้ ${idx - 1} ข้อ (ทำไป ${score} คะแนน)`);
      idx += 1; ask(idx);
    }
    draw();
  }
  function draw() {
    body.innerHTML = `<div class="g-stat"><div>ด่านที่: <b class="big" style="color:#1e40af">${idx} / 100</b></div><div>ชีวิตที่เหลือ: <b class="big" style="color:#dc2626">${'❤️'.repeat(Math.max(lives, 0))}</b></div><div>คะแนนสะสม: <b class="big" style="color:#d97706">${score}</b></div></div>
      ${active ? `<div class="g-card g-center" style="padding:24px"><h3 class="mb-0" style="font-size:20px;font-weight:700;color:#111827">${G.esc(q.question)}</h3><div class="g-grid2">${q.choices.map((c) => `<button type="button" class="g-opt g-jp" data-c="${G.esc(c)}">${G.esc(c)}</button>`).join('')}</div></div>`
        : `<div class="g-card g-center" style="padding:24px"><h3 class="mb-0" style="font-size:18px;font-weight:700;color:#1e3a8a">${G.esc(end)}</h3><button class="g-btn blue" style="font-size:14px;padding:10px 24px" data-act="again">🔄 เล่นใหม่อีกครั้ง</button></div>`}`;
  }
  G.register('survival100', {
    start(st) {
      body = G.box(st, 'Shiba Survival 100 — เอาชีวิตรอด 100 คำ', '🎮');
      body.addEventListener('click', (e) => { const c = e.target.closest('[data-c]'); if (c) answer(c.dataset.c); else if (e.target.closest('[data-act="again"]')) begin(); });
      begin();
    },
  });
})();
