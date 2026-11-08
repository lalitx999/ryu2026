/* RyuGames shell: check-in, header, ranking board, tabs, gallery.  Each game registers itself with G.register(). */
(function () {
  const $ = (s, r) => (r || document).querySelector(s);
  const { ajax, esc } = window.Ryu;
  const LEVELS = ['N5', 'N4', 'N3', 'N2', 'N1'];
  const RANK_MODE = { restaurant: 'shiba_restaurant', memory: 'shiba_memory', boss_rush: 'boss_rush',
    survival100: 'survival100', sentence_builder: 'sentence_builder', speed_quiz: 'speed_quiz' };
  const TABS = [['gallery', '🕹️ Games Gallery (6 Games)'], ['restaurant', '🍱 Shiba Diner (Hardcore)'], ['memory', '🧠 Shiba Memory'],
    ['boss_rush', '👹 Boss Rush'], ['survival100', '🎮 Survival 100'], ['sentence_builder', '✍️ Sentence Builder'], ['speed_quiz', '⚡ Speed Quiz']];
  const CATS = [['all', 'ทั้งหมด (6)'], ['action', '⚔️ Action & Arcade'], ['puzzle', '🧩 Puzzle & Logic'], ['cards', '🎴 Cards & Board'],
    ['sim', '🍱 Simulation & Rush'], ['rpg', '🗺️ RPG & Story']];

  const G = (window.Ryu.games = {
    mods: {}, data: null, quiz: null, active: null,
    st: { identity: null, name: '', level: 'N5', xp: 1250, lv: 5, tab: 'gallery', cat: 'all', q: '' },
    register(id, mod) { G.mods[id] = mod; },
    esc,
  });

  G.shuffle = (a) => { const r = a.slice(); for (let i = r.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [r[i], r[j]] = [r[j], r[i]]; } return r; };
  G.pick = (a) => a[Math.floor(Math.random() * a.length)];
  G.speak = (text) => {
    if (!('speechSynthesis' in window)) return;
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(String(text).replace(/[()]/g, '').trim()); u.lang = 'ja-JP'; u.rate = 0.9; speechSynthesis.speak(u);
  };
  G.confetti = (opts) => { try { window.confetti && window.confetti(opts); } catch (e) { /* cosmetic only */ } };
  G.addXp = (n) => { G.st.xp += n; $('#g-xp').textContent = G.st.xp + ' XP'; };

  /* ---- leaderboard ---- */
  G.loadRanking = async function (mode) {
    const box = $('#g-rank');
    if (!mode) { box.classList.add('d-none'); return; }
    box.classList.remove('d-none');
    box.innerHTML = `<div class="d-flex justify-content-between mb-2"><h2 class="mb-0" style="font-size:14px;font-weight:700;color:#172554">🏆 Ranking Board · ${G.st.level}</h2><span class="t10 text-secondary">เฉพาะเกมและระดับที่กำลังเล่น</span></div><p class="t12 text-secondary mb-0">กำลังโหลดคะแนน…</p>`;
    let rows = [];
    try { rows = await (await fetch(`/api/games/leaderboard/?game_mode=${mode}&jlpt_level=${G.st.level}`)).json(); } catch (e) { rows = []; }
    if (G.rankMode !== mode) return;  // user switched tabs while loading
    const head = box.firstElementChild.outerHTML;
    box.innerHTML = head + (rows.length ? `<ol class="list-unstyled mb-0 row g-1">${rows.map((r, i) => `<li class="col-12 col-sm-6 col-lg-4"><div class="g-rankli"><span><b class="me-2" style="color:#d97706">#${i + 1}</b>${esc(r.user_name)}</span><b style="color:#1e40af">${Number(r.score).toLocaleString()}</b></div></li>`).join('')}</ol>`
      : `<p class="bg-white rounded p-3 t12 text-secondary mb-0">ยังไม่มีคะแนนสำหรับเกมนี้ในระดับ ${G.st.level} — เป็นคนแรกเลย!</p>`);
  };
  G.submitScore = async function (mode, score, level) {
    if (!(score > 0)) return;  // a zero score would only clutter the ranking board
    try {
      await ajax.post('/api/games/submit-score/', { game_mode: mode, score, player_name: G.st.name, jlpt_level: level || (G.st.level) });
      if (G.rankMode === mode) G.loadRanking(mode);
    } catch (e) { /* offline / rate-limited: the game result is still shown */ }
  };

  /* ---- shell rendering ---- */
  function renderHeader() { $('#g-name').textContent = G.st.name; $('#g-lvl').textContent = `Lv.${G.st.lv} Shiba Master`; $('#g-xp').textContent = G.st.xp + ' XP'; }
  function renderTabs() {
    $('#g-tabs').innerHTML = TABS.map(([id, label]) => `<button type="button" class="g-tab ${G.st.tab === id ? 'active' : ''}" data-tab="${id}">${label}</button>`).join('');
  }
  G.launch = function (tab) {
    if (G.active && G.mods[G.active] && G.mods[G.active].stop) G.mods[G.active].stop();
    G.active = tab === 'gallery' ? null : tab; G.st.tab = tab; G.rankMode = RANK_MODE[tab] || null;
    renderTabs(); G.loadRanking(G.rankMode);
    const stage = $('#g-stage'); stage.innerHTML = '';
    if (tab === 'gallery') return renderGallery(stage);
    G.mods[tab].start(stage, G);
  };
  G.box = (stage, title, icon, extraHtml, wide) => {  // shared game window chrome
    stage.innerHTML = `<div class="g-stagebox g-bevel ${wide ? '' : 'w4'}"><div class="g-gamebar"><span>${icon} ${title}</span><span class="d-flex gap-2 align-items-center">${extraHtml || ''}<button type="button" class="g-red" data-act="gallery">✖ กลับ Gallery</button></span></div><div id="g-body" class="d-flex flex-column gap-3"></div></div>`;
    stage.querySelector('[data-act="gallery"]').addEventListener('click', () => G.launch('gallery'));
    return stage.querySelector('#g-body');
  };

  function countFor(level) { return level === 'all' ? G.data.GAMES_LIST.length : G.data.GAMES_LIST.filter((g) => g.jlptLevels.includes(level)).length; }
  const BADGE = { 'bg-red-600 text-white': '#dc2626', 'bg-blue-600 text-white': '#2563eb', 'bg-purple-600 text-white': '#9333ea',
    'bg-emerald-600 text-white': '#059669', 'bg-amber-600 text-white': '#d97706', 'bg-sky-600 text-white': '#0284c7' };

  function renderGallery(stage) {
    const s = G.st;
    stage.innerHTML = `<div class="g-stagebox g-bevel" style="gap:16px">
      <div class="bg-white border rounded p-3 d-flex flex-column gap-3">
        <div><p class="fw-bold t12 mb-2" style="color:#1e3a8a">1. เลือกระดับ JLPT</p><div class="d-flex gap-1 overflow-auto scrollbar-none" id="gal-levels">${['all', ...LEVELS].map((l) => `<button type="button" class="g-pill ${s.level === l ? 'active' : ''}" data-level="${l}">${l === 'all' ? 'ทุกระดับ' : l} <span style="opacity:.75">(${countFor(l)})</span></button>`).join('')}</div></div>
        <div class="d-flex flex-column flex-sm-row align-items-center justify-content-between gap-3 border-top pt-3">
          <div class="d-flex gap-1 overflow-auto w-100 scrollbar-none" id="gal-cats">${CATS.map(([id, label]) => `<button type="button" class="g-cat ${s.cat === id ? 'active' : ''}" data-cat="${id}">${label}</button>`).join('')}</div>
          <input id="gal-q" class="form-control form-control-sm" style="max-width:16rem;background:#fffbeb" placeholder="🔍 ค้นหาชื่อเกม / ศัพท์..." value="${esc(s.q)}"></div></div>
      <p id="gal-count" class="fw-bold t12 mb-0" style="color:#4b5563"></p>
      <div id="gal-grid" class="row g-3"></div></div>`;
    const draw = () => {
      const q = s.q.toLowerCase();
      const games = G.data.GAMES_LIST.filter((g) => (s.cat === 'all' || g.category === s.cat) && (s.level === 'all' || g.jlptLevels.includes(s.level))
        && (g.titleTh.toLowerCase().includes(q) || g.titleJp.toLowerCase().includes(q) || g.description.toLowerCase().includes(q))).sort((a, b) => a.difficultyOrder - b.difficultyOrder);
      $('#gal-count').textContent = `${s.level === 'all' ? 'เกมทุกระดับ' : 'เกมระดับ ' + s.level} · ${games.length} เกม · เรียงจากง่ายไปยาก`;
      $('#gal-grid').innerHTML = games.map((g) => `<div class="col-12 col-sm-6 col-md-4 col-lg-3"><div class="g-game h-100" data-play="${g.gameTabId}">
        <div class="d-flex justify-content-between mb-2"><span class="g-badge" style="background:${BADGE[g.badgeColor] || '#374151'}">${g.status === 'playable' ? 'PLAY NOW' : esc(g.status.toUpperCase())}</span><span class="g-jl">JLPT ${esc(g.jlpt)}</span></div>
        <div class="d-flex gap-3 mb-3"><div class="ic">${g.icon}</div><div><h3 class="mb-0" style="font-size:14px;font-weight:700;color:#111827;line-height:1.3">${esc(g.titleTh)}</h3><p class="mb-0 t12 text-secondary font-monospace">${esc(g.titleJp)}</p></div></div>
        <p class="t12 text-secondary g-clamp2" style="line-height:1.6">${esc(g.description)}</p>
        <div class="pt-2 border-top d-flex justify-content-between align-items-center"><span class="t10 fw-semibold text-secondary">${esc(g.categoryName)}</span><button type="button" class="g-btn green py-1 px-2" data-play="${g.gameTabId}">▶️ เล่นเลย</button></div></div></div>`).join('');
    };
    stage.addEventListener('click', (e) => {
      const lv = e.target.closest('[data-level]'); if (lv) { s.level = lv.dataset.level; renderGallery(stage); return; }
      const ct = e.target.closest('[data-cat]'); if (ct) { s.cat = ct.dataset.cat; renderGallery(stage); return; }
      const pl = e.target.closest('[data-play]'); if (pl) G.launch(pl.dataset.play);
    });
    $('#gal-q').addEventListener('input', (e) => { s.q = e.target.value; draw(); });
    draw();
  }

  /* ---- check-in ---- */
  function enter(identity, name) {
    G.st.identity = identity; G.st.name = name.slice(0, 50);
    $('#g-checkin').classList.add('d-none'); $('#g-app').classList.remove('d-none');
    renderHeader(); G.launch(G.st.play || 'gallery');
  }
  G.init = async function () {
    const root = $('#games-root');
    try {
      [G.data, G.quiz] = await Promise.all([fetch(root.dataset.gamesUrl).then((r) => r.json()), fetch(root.dataset.quizUrl).then((r) => r.json())]);
    } catch (e) { $('#g-checkin').innerHTML = '<div class="p-4 text-center">โหลดข้อมูลเกมไม่สำเร็จ กรุณารีเฟรชหน้า</div>'; return; }
    const play = new URLSearchParams(location.search).get('play');
    if (play && RANK_MODE[play]) G.st.play = play;
    const levelBox = $('#g-levels');
    const drawLevels = () => { levelBox.innerHTML = LEVELS.map((l) => `<button type="button" class="g-lvl ${G.st.level === l ? 'active' : ''}" data-level="${l}">${l} (${countFor(l)} เกม)</button>`).join(''); };
    drawLevels();
    levelBox.addEventListener('click', (e) => { const b = e.target.closest('[data-level]'); if (b) { G.st.level = b.dataset.level; drawLevels(); } });
    const guest = $('#g-guest'), go = $('#g-guest-go');
    guest.addEventListener('input', () => { go.disabled = !guest.value.trim(); });
    const start = () => guest.value.trim() && enter('guest', guest.value.trim());
    go.addEventListener('click', start); guest.addEventListener('keydown', (e) => { if (e.key === 'Enter') start(); });
    const member = $('#g-member-go'); if (member) member.addEventListener('click', () => enter('member', root.dataset.member || 'สมาชิก RyuClass'));
    $('#g-tabs').addEventListener('click', (e) => { const b = e.target.closest('[data-tab]'); if (b) G.launch(b.dataset.tab); });
  };
})();
