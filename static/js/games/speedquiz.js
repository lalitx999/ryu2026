/* Hardcore Speed Quiz 3D: 125 JLPT questions, shrinking timer, critical hits, overdrive.  three.js is self-hosted (importmap). */
import * as THREE from 'three';

const G = window.Ryu.games;
const LS_KEY = 'ryu_speed_quiz_high_scores';

/* ---------- sound (WebAudio, no assets) ---------- */
const audio = (() => {
  let ctx = null;
  const init = () => { if (!ctx) { const C = window.AudioContext || window.webkitAudioContext; if (C) ctx = new C(); } if (ctx && ctx.state === 'suspended') ctx.resume(); return ctx; };
  const tone = (type, freqs, gainStart, dur, ramp) => {
    if (!init()) return; const now = ctx.currentTime, o = ctx.createOscillator(), g = ctx.createGain(); o.type = type;
    freqs.forEach(([f, dt, exp]) => (exp ? o.frequency.exponentialRampToValueAtTime(f, now + dt) : o.frequency.setValueAtTime(f, now + dt)));
    g.gain.setValueAtTime(gainStart, now); g.gain.exponentialRampToValueAtTime(ramp, now + dur); o.connect(g); g.connect(ctx.destination); o.start(now); o.stop(now + dur);
  };
  const correct = () => tone('triangle', [[523.25, 0], [659.25, 0.08], [783.99, 0.16], [1046.5, 0.24]], 0.15, 0.45, 0.001);
  return {
    correct,
    critical() { tone('sawtooth', [[1200, 0], [200, 0.2, true]], 0.25, 0.2, 0.01); correct(); },
    wrong() { tone('sawtooth', [[150, 0], [110, 0.12]], 0.2, 0.35, 0.01); },
    heartbeat() { tone('sine', [[75, 0], [40, 0.08, true]], 0.3, 0.12, 0.01); },
    fever() {
      if (!init()) return; const now = ctx.currentTime;
      [523.25, 659.25, 783.99, 1046.5, 1318.51, 1567.98].forEach((f, i) => {
        const o = ctx.createOscillator(), g = ctx.createGain(); o.type = 'sine'; o.frequency.setValueAtTime(f, now + i * 0.05);
        g.gain.setValueAtTime(0.12, now + i * 0.05); g.gain.exponentialRampToValueAtTime(0.001, now + i * 0.05 + 0.2); o.connect(g); g.connect(ctx.destination); o.start(now + i * 0.05); o.stop(now + i * 0.05 + 0.2);
      });
    },
  };
})();

/* ---------- 3D background ---------- */
function makeScene(container, flags) {
  const scene = new THREE.Scene(); scene.fog = new THREE.FogExp2(0x0a0e17, 0.015);
  const camera = new THREE.PerspectiveCamera(60, container.clientWidth / container.clientHeight, 0.1, 1000); camera.position.set(0, 0, 25);
  let renderer;
  try { renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true }); } catch (e) { return null; }  // no WebGL: the quiz still works
  renderer.setSize(container.clientWidth, container.clientHeight); renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  container.appendChild(renderer.domElement);
  scene.add(new THREE.AmbientLight(0xffffff, 0.6));
  const point = new THREE.PointLight(0x06c755, 3, 50); point.position.set(0, 0, 15); scene.add(point);
  const feverLight = new THREE.PointLight(0xffaa00, 0, 50); feverLight.position.set(0, 0, 10); scene.add(feverLight);
  const N = 1200, geo = new THREE.BufferGeometry(), pos = new Float32Array(N * 3), col = new Float32Array(N * 3);
  const c1 = new THREE.Color(0x0053e1), c2 = new THREE.Color(0x06c755);
  for (let i = 0; i < N; i++) {
    pos[i * 3] = (Math.random() - 0.5) * 60; pos[i * 3 + 1] = (Math.random() - 0.5) * 60; pos[i * 3 + 2] = (Math.random() - 0.5) * 100 - 20;
    const m = c1.clone().lerp(c2, Math.random()); col[i * 3] = m.r; col[i * 3 + 1] = m.g; col[i * 3 + 2] = m.b;
  }
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3)); geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
  const particles = new THREE.Points(geo, new THREE.PointsMaterial({ size: 0.35, vertexColors: true, transparent: true, opacity: 0.8, blending: THREE.AdditiveBlending }));
  scene.add(particles);
  const core = new THREE.Mesh(new THREE.OctahedronGeometry(4, 0), new THREE.MeshPhongMaterial({ color: 0x0053e1, emissive: 0x00227a, wireframe: true, shininess: 100 })); core.position.set(0, 0, -5); scene.add(core);
  const ring = new THREE.Mesh(new THREE.TorusGeometry(7, 0.15, 16, 100), new THREE.MeshBasicMaterial({ color: 0x06c755, wireframe: true })); ring.position.set(0, 0, -5); scene.add(ring);
  const clock = new THREE.Clock(); let raf, shake = 0, wasHit = false;
  const loop = () => {
    raf = requestAnimationFrame(loop); const t = clock.getElapsedTime();
    core.rotation.x = t * 0.4; core.rotation.y = t * 0.6; ring.rotation.z = -t * 0.3; ring.rotation.x = t * 0.2;
    const speed = flags.fever ? 1.2 : 0.25, p = geo.attributes.position.array;
    for (let i = 0; i < N; i++) { p[i * 3 + 2] += speed; if (p[i * 3 + 2] > 25) p[i * 3 + 2] = -75; }
    geo.attributes.position.needsUpdate = true;
    const hit = flags.critical || flags.wrong; if (hit && !wasHit) shake = 1; wasHit = hit;
    if (shake > 0) { shake -= 0.05; const k = shake * 0.6; camera.position.x = (Math.random() - 0.5) * k; camera.position.y = (Math.random() - 0.5) * k; }
    else { camera.position.x = THREE.MathUtils.lerp(camera.position.x, 0, 0.1); camera.position.y = THREE.MathUtils.lerp(camera.position.y, 0, 0.1); }
    feverLight.intensity = THREE.MathUtils.lerp(feverLight.intensity, flags.fever ? 5 : 0, 0.1); core.material.color.setHex(flags.fever ? 0xff8800 : 0x0053e1);
    renderer.render(scene, camera);
  };
  loop();
  const resize = () => { camera.aspect = container.clientWidth / container.clientHeight; camera.updateProjectionMatrix(); renderer.setSize(container.clientWidth, container.clientHeight); };
  window.addEventListener('resize', resize);
  return () => { cancelAnimationFrame(raf); window.removeEventListener('resize', resize); renderer.dispose(); geo.dispose(); renderer.domElement.remove(); };
}

/* ---------- game ---------- */
function questionsFor(level) {  // shuffle questions and each question's options
  return G.shuffle(G.quiz.filter((q) => q.level === level)).map((q) => {
    const opts = G.shuffle(q.options.map((text, i) => ({ text, ok: i === q.correctIndex })));
    return Object.assign({}, q, { options: opts.map((o) => o.text), correctIndex: opts.findIndex((o) => o.ok) });
  });
}
const duration = (combo) => (combo >= 15 ? 1.8 : combo >= 10 ? 2.5 : combo >= 5 ? 3.5 : 5.0);
const grade = (sc) => (sc >= 3000 ? ['S+', '⚡ GODLIKE (ระดับเซียน)', '#fbbf24'] : sc >= 2000 ? ['S', '🔥 MASTER (ระดับปรมาจารย์)', '#fb7185']
  : sc >= 1200 ? ['A', '⚔️ EXPERT (ยอดยุทธ์)', '#06C755'] : sc >= 600 ? ['B', '👍 ADVANCED (ผู้เชี่ยวชาญ)', '#60a5fa'] : ['C', '🔰 ROOKIE (มือใหม่ฝึกหัด)', '#cbd5e1']);

let S, root, tick, stopScene, timeouts = [], flags = { fever: false, critical: false, wrong: false };
function later(fn, ms) { const id = setTimeout(fn, ms); timeouts.push(id); }
function highScores() { try { return JSON.parse(localStorage.getItem(LS_KEY) || '{}'); } catch (e) { return {}; } }

function startGame(level) {
  Object.assign(S, { state: 'playing', level, qs: questionsFor(level), i: 0, score: 0, combo: 0, maxCombo: 0, crits: 0, lives: 3, picked: null, answered: false,
    fever: false, left: duration(0), max: duration(0), t0: Date.now(), banner: false });
  flags.fever = flags.critical = flags.wrong = false; render(); runTimer();
}
function runTimer() {
  clearInterval(tick);
  tick = setInterval(() => {
    if (S.state !== 'playing' || S.answered) return;
    if (S.left <= 0.1) { clearInterval(tick); S.left = 0; return timeout(); }
    if (S.left <= 1.5 && S.sound && Math.round(S.left * 10) % 5 === 0) audio.heartbeat();
    S.left = Math.round((S.left - 0.1) * 10) / 10; paintTimer();
  }, 100);
}
function paintTimer() { const bar = root.querySelector('.sq-timer div'); if (bar) { bar.style.width = (S.left / S.max * 100) + '%'; bar.className = S.left <= 1.5 ? 'danger' : S.left <= 3 ? 'warn' : ''; } }
function timeout() {
  S.answered = true; flags.wrong = true; if (S.sound) audio.wrong(); S.combo = 0; S.fever = flags.fever = false; S.lives -= 1; render();
  later(() => { flags.wrong = false; S.lives <= 0 || S.i + 1 >= S.qs.length ? end() : next(0); }, 1000);
}
function answer(idx) {
  if (S.answered || S.state !== 'playing') return;
  S.answered = true; S.picked = idx; clearInterval(tick);
  const q = S.qs[S.i], rt = (Date.now() - S.t0) / 1000;
  if (idx === q.correctIndex) {
    S.combo += 1; S.maxCombo = Math.max(S.maxCombo, S.combo);
    const crit = rt <= 1.2; let pts = 100 + S.combo * 20;
    if (crit) { pts += 300; S.crits += 1; flags.critical = true; S.banner = true; if (S.sound) audio.critical(); } else if (S.sound) audio.correct();
    const wasFever = S.fever;  // overdrive doubles from the *next* answer, as in the original
    if (S.combo >= 10 && !S.fever) { S.fever = flags.fever = true; if (S.sound) audio.fever(); }
    if (wasFever) pts *= 2;
    S.score += pts; render();
    later(() => { flags.critical = false; S.banner = false; S.i + 1 >= S.qs.length ? end() : next(S.combo); }, crit ? 900 : 700);
  } else {
    if (S.sound) audio.wrong(); flags.wrong = true; S.combo = 0; S.fever = flags.fever = false; S.lives -= 1; render();
    later(() => { flags.wrong = false; S.lives <= 0 || S.i + 1 >= S.qs.length ? end() : next(0); }, 1000);
  }
}
function next(combo) { S.i += 1; S.answered = false; S.picked = null; S.left = S.max = duration(combo); S.t0 = Date.now(); render(); runTimer(); }
function end() {
  clearInterval(tick); S.state = 'gameover';
  const hs = highScores(), isNew = S.score > (hs[S.level] || 0); S.newHigh = isNew;
  if (isNew) { hs[S.level] = S.score; try { localStorage.setItem(LS_KEY, JSON.stringify(hs)); } catch (e) { /* private mode */ } }
  if (isNew || S.score > 1000) G.confetti({ particleCount: 120, spread: 80, origin: { y: 0.6 } });
  if (S.score > 0) G.submitScore('speed_quiz', S.score, S.level);
  render();
}

function render() {
  const e = G.esc, ui = root.querySelector('.sq-main'); const q = S.qs && S.qs[S.i];
  root.querySelector('#sq-sound').textContent = S.sound ? '🔊' : '🔇';
  if (S.state === 'menu') {
    const hs = highScores();
    ui.innerHTML = `<div class="sq-card menu"><div><div style="font-size:40px">⚡</div><h2 class="mb-1" style="font-size:28px;font-weight:900">HARDCORE SPEED QUIZ 3D</h2>
      <p class="t12 mb-0" style="color:#cbd5e1;line-height:1.6">ท้าทายคลังข้อสอบ 125+ ข้อ! ตอบเร็วเพื่อทำ Critical Hit ปลดล็อก Overdrive Mode และสร้างสถิติสูงสุด!</p></div>
      <div><div class="t12 fw-bold text-uppercase mb-2" style="color:#94a3b8;letter-spacing:.05em">เลือกระดับความยาก (SELECT JLPT LEVEL)</div>
        <div class="sq-lvls">${['N5', 'N4', 'N3', 'N2', 'N1'].map((l) => `<button type="button" class="sq-lvl" data-start="${l}"><b>${l}</b><span class="t10 font-monospace" style="color:#94a3b8">🏆 ${hs[l] ? hs[l] + 'pt' : '-'}</span></button>`).join('')}</div></div>
      <div class="text-start p-3 rounded-4 t11" style="background:rgba(30,41,59,.6);border:1px solid #334155;color:#cbd5e1"><div class="fw-bold mb-1" style="color:#34d399">🛡️ กติกาความโหด (Hardcore Rules):</div>
        <ul class="mb-0 ps-3"><li>ตอบเร็วภายใน <b>1.2 วินาทีแรก</b> ได้คะแนน <b>Critical Hit +300pt</b></li><li>ทำ <b>Combo x10</b> จะเปิดระบบ <b>Overdrive Fever Mode (คะแนน x2)</b></li><li>ยิ่ง Combo สูง เวลานับถอยหลังจะยิ่งสั้นลงเรื่อยๆ (เหลือ 1.8 วิ!)</li><li>มีหัวใจ 3 ด้าม ตอบผิดหรือหมดเวลาครบ 3 ครั้ง = Game Over ทันที</li></ul></div></div>`;
  } else if (S.state === 'playing' && q) {
    const cls = flags.wrong ? 'wrong' : flags.critical ? 'crit' : S.fever ? 'fever' : '';
    ui.innerHTML = `<div class="sq-hud"><div class="sq-stats"><div class="d-flex align-items-center gap-2"><span class="px-3 py-1 rounded-3 fw-bolder" style="background:rgba(16,185,129,.2);border:1px solid rgba(16,185,129,.4);color:#34d399">${S.level}</span><span class="t12 fw-semibold d-none d-sm-inline" style="color:#94a3b8">ข้อที่ ${S.i + 1} / ${S.qs.length}</span></div>
        <div class="d-flex align-items-center gap-2">${S.fever ? '<span class="sq-fever">🔥 OVERDRIVE x2</span>' : ''}<span class="px-3 py-1 rounded-3 fw-bolder" style="background:#1e293b;border:1px solid #334155;color:#fbbf24">🔥 Combo x${S.combo}</span></div>
        <div class="d-flex align-items-center gap-3"><div>${[1, 2, 3].map((h) => `<span style="opacity:${h <= S.lives ? 1 : 0.2};transform:scale(${h <= S.lives ? 1 : 0.75});display:inline-block;transition:all .2s">❤️</span>`).join('')}</div>
          <div class="text-end"><div class="t10 fw-bold text-uppercase" style="color:#94a3b8">SCORE</div><div class="font-monospace fw-black" style="font-size:20px;font-weight:900">${S.score.toLocaleString()}</div></div></div></div>
      <div class="sq-timer"><div style="width:${S.left / S.max * 100}%"></div></div>
      ${S.banner ? '<div class="text-center"><span class="sq-crit">⚡ CRITICAL HIT! +500pt</span></div>' : ''}
      <div class="sq-card sq-q ${cls}"><div class="text-center"><span class="px-3 py-1 rounded-pill t10 fw-bold text-uppercase" style="background:#1e293b;border:1px solid #334155;color:#94a3b8;letter-spacing:.05em">${e(q.type.toUpperCase())} QUESTION</span>
        <h3 class="mt-2 mb-0 g-jp" style="font-size:26px;font-weight:900;line-height:1.5">${e(q.question)}</h3></div>
        <div class="sq-opts">${q.options.map((o, i) => { let c = ''; if (S.answered) c = i === q.correctIndex ? 'right' : i === S.picked ? 'miss' : 'dim'; return `<button type="button" class="sq-opt g-jp ${c}" data-ans="${i}" ${S.answered ? 'disabled' : ''}><span>${e(o)}</span><small>[${i + 1}]</small></button>`; }).join('')}</div>
        ${S.answered ? `<div class="p-3 rounded-3 t12 text-center fw-medium" style="background:rgba(30,41,59,.8);border:1px solid #334155;color:#cbd5e1">💡 ${e(q.explanation)}</div>` : ''}</div></div>`;
  } else if (S.state === 'gameover') {
    const [gr, title, color] = grade(S.score);
    ui.innerHTML = `<div class="sq-card text-center d-flex flex-column gap-3" style="max-width:28rem"><div><div class="font-monospace" style="font-size:48px;font-weight:900;color:${color}">${gr}</div><h2 class="mb-1" style="font-size:18px;font-weight:700">${title}</h2><p class="t12 mb-0" style="color:#94a3b8">จบเกมการแข่ง Speed Quiz ระดับ ${S.level}</p></div>
      <div class="row g-0 p-3 rounded-4" style="background:rgba(30,41,59,.6);border:1px solid #1e293b"><div class="col-4"><div class="t10 fw-bold text-uppercase" style="color:#94a3b8">คะแนนรวม</div><div class="font-monospace" style="font-size:18px;font-weight:900;color:#fbbf24">${S.score.toLocaleString()}</div></div>
        <div class="col-4"><div class="t10 fw-bold text-uppercase" style="color:#94a3b8">MAX COMBO</div><div class="font-monospace" style="font-size:18px;font-weight:900;color:#34d399">x${S.maxCombo}</div></div>
        <div class="col-4"><div class="t10 fw-bold text-uppercase" style="color:#94a3b8">CRITICAL</div><div class="font-monospace" style="font-size:18px;font-weight:900;color:#fb7185">${S.crits}</div></div></div>
      ${S.newHigh ? `<div class="p-2 rounded-3 t12 fw-bold" style="background:rgba(245,158,11,.2);border:1px solid rgba(245,158,11,.4);color:#fcd34d">✨ ยินดีด้วย! คุณทำสถิติสูงสุดใหม่ของระดับ ${S.level}!</div>` : ''}
      <button class="sq-go" style="background:#10b981;color:#fff" data-start="${S.level}">🔄 เล่นอีกครั้ง (Try Again)</button><button class="sq-go t12" style="background:#1e293b;color:#cbd5e1" data-menu="1">เปลี่ยนระดับ / กลับหน้าเมนู</button></div>`;
  }
}

G.register('speed_quiz', {
  start(stage) {
    stage.innerHTML = `<div class="w-100" style="max-width:64rem;margin:0 auto"><div class="sq"><div class="sq-canvas" id="sq-canvas"></div>
      <header class="sq-top"><div class="d-flex align-items-center gap-3"><button class="sq-btn" data-back="1">⬅ กลับ Gallery</button><h1 class="sq-title mb-0">⚔️ Speed Quiz 3D Arcade (125+ ศัพท์ & คันจิ)</h1></div>
        <button class="sq-btn" id="sq-sound" title="เปิด/ปิดเสียง">🔊</button></header><main class="sq-main"></main></div></div>`;
    root = stage.querySelector('.sq'); S = { state: 'menu', sound: true, level: 'N5' };
    stopScene = makeScene(root.querySelector('#sq-canvas'), flags);
    root.addEventListener('click', (ev) => {
      if (ev.target.closest('[data-back]')) return G.launch('gallery');
      if (ev.target.closest('#sq-sound')) { S.sound = !S.sound; return render(); }
      const st = ev.target.closest('[data-start]'); if (st) return startGame(st.dataset.start);
      if (ev.target.closest('[data-menu]')) { S.state = 'menu'; return render(); }
      const a = ev.target.closest('[data-ans]'); if (a) answer(+a.dataset.ans);
    });
    render();
  },
  stop() { clearInterval(tick); timeouts.forEach(clearTimeout); timeouts = []; if (stopScene) stopScene(); stopScene = null; },
});
