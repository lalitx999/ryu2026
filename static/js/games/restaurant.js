/* Shiba Diner: 20 customers order in Japanese; pick the dish and the counter word before patience runs out. */
(function () {
  const G = window.Ryu.games;
  const PATIENCE = { easy: 20, medium: 14, hard: 9, expert: 5 };
  const POOL = { easy: 12, medium: 24, hard: 36, expert: 45 };
  const QTY = { easy: 3, medium: 5, hard: 7, expert: 10 };
  const DIFFS = [['easy', '🟢 Easy (20s)'], ['medium', '🟡 Medium (14s)'], ['hard', '🔴 Hard (9s)'], ['expert', '☠️ Expert (5s)']];
  let s, body, timer, stage;

  function fresh() { return { diff: s ? s.diff : 'medium', score: 0, serves: 0, n: 1, order: null, patience: 0, menu: null, qty: null, feedback: null, playing: false, over: false, busy: false }; }
  const menuPool = () => G.data.ALL_MENU_ITEMS.slice(0, POOL[s.diff]);
  const qtyPool = () => G.data.COUNTER_ITEMS_10.slice(0, QTY[s.diff]);

  function stop() { clearInterval(timer); timer = null; }
  function nextCustomer() {
    const menu = G.pick(menuPool()), qty = G.pick(qtyPool());
    s.order = { menu, qty, emoji: G.pick(G.data.CUSTOMER_EMOJIS), name: G.pick(G.data.CUSTOMER_NAMES), phrase: `${menu.nameJp} を ${qty.wordJp} ください` };
    s.patience = PATIENCE[s.diff]; s.menu = null; s.qty = null; s.feedback = null; s.busy = false;
    G.speak(s.order.phrase); draw(); runTimer();
  }
  function runTimer() {
    stop();
    timer = setInterval(() => {
      s.patience -= 1;
      const el = body.querySelector('#r-pat'); if (el) el.textContent = s.patience + 's';
      if (s.patience <= 0) { stop(); s.busy = true; s.feedback = '😡 ลูกค้ารอนานเกินไปจนเดินออกจากร้าน!'; draw(); setTimeout(() => proceed(0), 1200); }
    }, 1000);
  }
  function proceed(yen) {
    s.score += yen;
    if (s.n >= 20) { s.playing = false; s.over = true; stop(); G.submitScore('shiba_restaurant', s.score); draw(); }
    else { s.n += 1; nextCustomer(); }
  }
  function serve() {
    if (!s.menu || !s.qty || s.busy) return;
    stop(); s.busy = true;
    if (s.menu.id === s.order.menu.id && s.qty.num === s.order.qty.num) {
      const yen = s.order.menu.price * s.order.qty.num; s.serves += 1;
      s.feedback = `✨ ถูกต้องแม่นยำ! เสิร์ฟ ${s.menu.nameJp} (${s.qty.wordJp}) +¥${yen}`; G.speak('ありがとうございます！'); draw(); setTimeout(() => proceed(yen), 1000);
    } else { s.feedback = `❌ เสิร์ฟผิด! ลูกค้าสั่ง: ${s.order.phrase}`; G.speak('ちがいます'); draw(); setTimeout(() => proceed(0), 1200); }
  }
  function begin() { const d = s.diff; s = fresh(); s.diff = d; s.playing = true; nextCustomer(); }

  function draw() {
    const e = G.esc;
    if (!s.playing && !s.over) {
      body.innerHTML = `<div class="g-card g-center" style="padding:24px"><div style="font-size:60px" class="g-bounce">🐕🍱</div><h2 class="mb-0" style="font-size:24px;font-weight:700;color:#1e3a8a">ยินดีต้อนรับสู่ร้านอาหารชิบะ!</h2>
        <p class="t12 text-secondary mb-0" style="max-width:28rem">ลูกค้า 20 คิวจะเดินสั่งอาหารภาษาญี่ปุ่นล้วน (ไม่มี Hint) คุณต้องเลือก <b>เมนูอาหาร</b> และ <b>คำนับจำนวน (ひとつ~とお)</b> ให้ถูกต้องสมบูรณ์!</p>
        <div class="w-100 text-start p-3 rounded" style="max-width:24rem;background:#fffbeb;border:1px solid #fcd34d"><label class="t12 fw-bold">ชื่อผู้เชฟ:</label><input id="r-name" class="form-control form-control-sm fw-bold mt-1 mb-2" maxlength="50" value="${e(G.st.name)}">
          <label class="t12 fw-bold">เลือกระดับความยาก:</label><div class="g-diff">${DIFFS.map(([id, l]) => `<button type="button" data-diff="${id}" class="${s.diff === id ? 'active' : ''}">${l}</button>`).join('')}</div></div>
        <button class="g-btn green big" data-act="start">🚀 เปิดร้านต้อนรับลูกค้า (20 คิว)</button></div>`;
    } else if (s.playing) {
      const o = s.order;
      body.innerHTML = `<div class="g-stat"><div style="color:#1e40af">ลูกค้าคนที่: <b class="big" style="color:#dc2626">${s.n}</b> / 20</div><div style="color:#d97706">รายได้รวม: ¥${s.score}</div><div style="color:#047857">สำเร็จ: ${s.serves} คน</div>
          <div class="px-3 py-1 rounded" style="background:#fee2e2;border:1px solid #fca5a5">⏱️ เวลาที่เหลือ: <b class="big font-monospace" style="color:#b91c1c" id="r-pat">${s.patience}s</b></div></div>
        <div class="g-order"><div class="face">${o.emoji}</div><div class="flex-grow-1"><div class="t12 fw-bold mb-1" style="color:#78350f">${e(o.name)} สั่งว่า:</div><div class="phrase g-jp">「 ${e(o.phrase)} 」</div>
          <button class="btn btn-sm ms-2 fw-bold t12" style="background:#fcd34d;color:#78350f" data-act="replay">🔊 ฟังเสียงอีกครั้ง</button></div></div>
        ${s.feedback ? `<div class="g-feedback g-bounce">${e(s.feedback)}</div>` : ''}
        <div class="row g-3"><div class="col-md-6"><div class="g-card h-100 d-flex flex-column gap-2" style="padding:12px"><h4 class="t12 fw-bold border-bottom pb-1 mb-0" style="color:#374151">1. เลือกเมนูอาหาร (Selected: ${s.menu ? e(s.menu.nameJp) : 'ยังไม่ได้เลือก'})</h4>
          <div class="g-menu">${menuPool().map((m) => `<button type="button" data-menu="${m.id}" class="${s.menu && s.menu.id === m.id ? 'sel' : ''}"><span style="font-size:20px">${m.icon}</span><span class="g-jp fw-bold t11">${e(m.nameJp)}</span></button>`).join('')}</div></div></div>
          <div class="col-md-6"><div class="g-card h-100 d-flex flex-column gap-2" style="padding:12px"><h4 class="t12 fw-bold border-bottom pb-1 mb-0" style="color:#374151">2. เลือกจำนวนคำนับ (Selected: ${s.qty ? e(s.qty.wordJp) : 'ยังไม่ได้เลือก'})</h4>
          <div class="g-qty">${qtyPool().map((q) => `<button type="button" data-qty="${q.num}" class="${s.qty && s.qty.num === q.num ? 'sel' : ''}"><b style="font-size:14px">${q.num}</b><b class="g-jp" style="font-size:14px">${e(q.wordJp)}</b></button>`).join('')}</div>
          <button class="g-btn green mt-auto py-3" style="font-size:14px" data-act="serve" ${s.menu && s.qty && !s.busy ? '' : 'disabled'}>🛎️ เสิร์ฟออเดอร์ให้ลูกค้า!</button></div></div></div>`;
    } else {
      const g = s.serves >= 18 ? 'RANK S' : s.serves >= 14 ? 'RANK A' : 'RANK B';
      body.innerHTML = `<div class="g-card g-center" style="padding:24px"><div style="font-size:48px">🏆 🎉</div><h2 class="mb-0" style="font-size:24px;font-weight:700;color:#1e3a8a">สรุปผลงานเปิดร้านชิบะ!</h2>
        <div class="w-100 text-start p-3 rounded d-flex flex-column gap-2 fw-bold t12" style="max-width:24rem;background:#fffbeb;border:1px solid #fcd34d;color:#1f2937">
          <div>ผู้เล่น: <span style="color:#1e40af">${e(G.st.name)}</span></div><div>ระดับความยาก: <span class="text-uppercase" style="color:#dc2626">${s.diff}</span></div>
          <div>ลูกค้าสำเร็จ: <span style="color:#059669">${s.serves} / 20 คน</span></div><div>รายได้รวม: <span style="color:#d97706;font-size:16px">¥${s.score}</span></div>
          <div>เกรดการประเมิน: <span style="font-size:20px;color:#7e22ce">${g}</span></div></div>
        <button class="g-btn blue" style="font-size:14px;padding:10px 24px" data-act="start">🔄 เล่นใหม่อีกครั้ง</button></div>`;
    }
  }

  G.register('restaurant', {
    start(st) {
      stage = st; s = null; s = fresh();
      body = G.box(st, 'Shiba Diner — ร้านอาหารชิบะระดับ Hardcore', '🍱');
      body.addEventListener('click', (ev) => {
        const t = ev.target;
        if (t.closest('[data-diff]')) { s.diff = t.closest('[data-diff]').dataset.diff; draw(); }
        else if (t.closest('[data-menu]')) { if (!s.busy) { s.menu = G.data.ALL_MENU_ITEMS.find((m) => m.id === t.closest('[data-menu]').dataset.menu); draw(); } }
        else if (t.closest('[data-qty]')) { if (!s.busy) { s.qty = G.data.COUNTER_ITEMS_10.find((q) => q.num === +t.closest('[data-qty]').dataset.qty); draw(); } }
        else if (t.closest('[data-act="serve"]')) serve();
        else if (t.closest('[data-act="replay"]')) G.speak(s.order.phrase);
        else if (t.closest('[data-act="start"]')) { const n = body.querySelector('#r-name'); if (n && n.value.trim()) G.st.name = n.value.trim().slice(0, 50); begin(); }
      });
      draw();
    },
    stop,
  });
})();
