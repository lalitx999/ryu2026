/* Shiba Memory: flip cards to match kanji with its reading + Thai meaning. */
(function () {
  const G = window.Ryu.games;
  let cards, open, flips, found, done, body, lock, t;
  function init() {
    cards = []; let id = 1;
    G.data.MEMORY_PAIRS.forEach((p) => { cards.push({ id: id++, text: p.kanji, pair: p.id, open: false, matched: false }); cards.push({ id: id++, text: p.reading, pair: p.id, open: false, matched: false }); });
    cards = G.shuffle(cards); open = []; flips = 0; found = 0; done = false; lock = false; draw();
  }
  function click(i) {
    const c = cards[i]; if (lock || c.open || c.matched || open.length >= 2) return;
    c.open = true; open.push(i);
    if (open.length === 2) {
      flips += 1; const [a, b] = open;
      if (cards[a].pair === cards[b].pair) { cards[a].matched = cards[b].matched = true; open = []; found += 1; if (found >= 6) { done = true; G.confetti({ particleCount: 90, spread: 70, origin: { y: 0.6 } }); } }
      else { lock = true; t = setTimeout(() => { cards[a].open = cards[b].open = false; open = []; lock = false; draw(); }, 1000); }
    }
    draw();
  }
  function draw() {
    body.innerHTML = `<div class="g-stat"><div>จับคู่สำเร็จ: <b class="big" style="color:#059669">${found} / 6</b></div><div>จำนวนครั้งที่เปิด: <b class="big" style="color:#d97706">${flips}</b></div><button class="g-btn blue py-1" data-act="again">🔄 เริ่มเกมใหม่</button></div>
      <div class="g-cards">${cards.map((c, i) => { const o = c.open || c.matched; return `<button type="button" class="g-cardbtn ${o ? 'open g-jp' : ''}" data-i="${i}">${o ? G.esc(c.text) : '🐕'}</button>`; }).join('')}</div>
      ${done ? `<div class="g-bounce text-center fw-bold p-3 rounded" style="background:#d1fae5;border:2px solid #10b981;color:#064e3b">🎉 ยินดีด้วย! คุณเคลียร์การ์ดจับคู่ได้หมดเรียบร้อยแล้วด้วยการเปิดเพียง ${flips} ครั้ง!</div>` : ''}`;
  }
  G.register('memory', {
    start(st) {
      body = G.box(st, 'Shiba Memory — เกมเปิดการ์ดจับคู่คันจิ', '🧠');
      body.addEventListener('click', (e) => { const c = e.target.closest('[data-i]'); if (c) click(+c.dataset.i); else if (e.target.closest('[data-act="again"]')) { clearTimeout(t); init(); } });
      init();
    },
    stop() { clearTimeout(t); },
  });
})();
