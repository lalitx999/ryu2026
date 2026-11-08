/* Kanji Boss Rush: answer vocabulary to hurt the Oni; wrong answers hurt you. */
(function () {
  const G = window.Ryu.games;
  let boss, me, combo, q, active, log, body;
  const MAX = 500;
  function ask() { const p = G.pick(G.data.BOSS_POOL); q = Object.assign({}, p, { choices: G.shuffle(p.choices) }); }
  function begin() { boss = MAX; me = 100; combo = 0; active = true; log = ['👹 Boss Red Oni ปรากฏตัวแล้ว! จงใช้ความรู้คันจิโจมตี!']; ask(); draw(); }
  function answer(c) {
    if (!active) return;
    if (c === q.answer) {
      combo += 1; const crit = combo % 3 === 0, dmg = crit ? 120 : 60; boss = Math.max(0, boss - dmg);
      log.unshift(crit ? `🔥 CRITICAL HIT! ${q.kanji} (${q.romaji}) ทำดามเมจแรงต้านบอส ${dmg} HP!` : `⚔️ โจมตีสำเร็จ! ${q.kanji} ดาเมจ ${dmg} HP! (Combo x${combo})`); log = log.slice(0, 5);
      G.speak(q.kanji);
      if (boss <= 0) { active = false; log = ['🏆 ปราบ Boss Oni สำเร็จแล้ว! ได้รับ +500 XP!']; G.addXp(500); G.confetti({ particleCount: 120, spread: 80, origin: { y: 0.6 } }); } else ask();
    } else {
      combo = 0; me = Math.max(0, me - 25); log.unshift('💥 ตอบผิด! โดนบอส Oni สวนกลับด้วยกระบะไฟ -25 HP!'); log = log.slice(0, 5);
      if (me <= 0) { active = false; log = ['☠️ คุณพ่ายแพ้แก่ Boss Oni! พักฟื้นแล้วลองใหม่นะ']; } else ask();
    }
    draw();
  }
  function draw() {
    body.innerHTML = `<div class="g-card d-flex flex-column gap-3"><div class="d-flex justify-content-between align-items-center fw-bold t12 flex-wrap gap-2"><span class="big" style="color:#b91c1c;font-size:16px">👹 BOSS: Red Oni (HP: ${boss} / ${MAX})</span><span style="color:#7e22ce">Combo: x${combo}</span><span style="color:#047857;font-size:16px">🛡️ PLAYER HP: ${me} / 100</span></div>
      <div class="g-hp"><div style="width:${boss / MAX * 100}%"></div></div></div>
      ${active ? `<div class="g-battle"><div class="t12 fw-bold text-uppercase" style="color:#92400e;letter-spacing:.1em">คันจิคำนี้แปลว่าอะไร?</div><div class="g-kanji g-jp">${G.esc(q.kanji)}</div>
        <div class="g-grid2">${q.choices.map((c) => `<button type="button" class="g-opt" data-c="${G.esc(c)}">${G.esc(c)}</button>`).join('')}</div></div>`
        : `<div class="text-center"><button class="g-btn blue" style="font-size:14px;padding:10px 24px" data-act="again">⚔️ ท้าบอสอีกครั้ง</button></div>`}
      <div class="g-log">${log.map((l) => `<div>${G.esc(l)}</div>`).join('')}</div>`;
  }
  G.register('boss_rush', {
    start(st) {
      body = G.box(st, 'Kanji Boss Rush — ตบบอสด้วยศัพท์', '👹');
      body.addEventListener('click', (e) => { const c = e.target.closest('[data-c]'); if (c) answer(c.dataset.c); else if (e.target.closest('[data-act="again"]')) begin(); });
      begin();
    },
  });
})();
