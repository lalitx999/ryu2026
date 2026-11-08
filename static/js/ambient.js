/* Lightweight 2D ambient particles (snow / sakura / off) - replaces the Three.js layer, no external lib. */
(function () {
  const canvas = document.getElementById('ambient-canvas'); if (!canvas) return;
  const btn = document.getElementById('ambient-toggle'); const ctx = canvas.getContext('2d');
  const MODES = { snow: { icon: '❄️', label: 'หิมะ', color: '255,255,255' }, sakura: { icon: '🌸', label: 'ซากุระ', color: '255,183,197' }, off: { icon: '✨', label: 'ปิดเอฟเฟกต์' } };
  const order = ['snow', 'sakura', 'off']; let mode = 'snow';
  try { mode = localStorage.getItem('ryu_ambient_mode') || 'snow'; } catch (e) {}
  if (!MODES[mode]) mode = 'snow';
  let W, H, parts = [];
  const reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  function resize() { W = canvas.width = innerWidth; H = canvas.height = innerHeight; }
  function seed() { parts = Array.from({ length: Math.min(70, Math.floor(W / 20)) }, () => ({ x: Math.random() * W, y: Math.random() * H, r: 1.5 + Math.random() * 3, s: .4 + Math.random() * 1.1, d: Math.random() * Math.PI * 2 })); }
  function label() { btn.innerHTML = `<span>${MODES[mode].icon}</span><span>${MODES[mode].label}</span><span style="opacity:.6">⇄</span>`; }
  function frame() {
    ctx.clearRect(0, 0, W, H);
    if (mode !== 'off') {
      ctx.fillStyle = `rgba(${MODES[mode].color},.8)`;
      for (const p of parts) {
        p.y += p.s; p.d += .01; p.x += Math.sin(p.d) * (mode === 'sakura' ? 1 : .4);
        if (p.y > H + 5) { p.y = -5; p.x = Math.random() * W; }
        ctx.beginPath(); if (mode === 'sakura') ctx.ellipse(p.x, p.y, p.r * 1.6, p.r, p.d, 0, 7); else ctx.arc(p.x, p.y, p.r, 0, 7); ctx.fill();
      }
    }
    if (!reduce) requestAnimationFrame(frame);
  }
  btn.addEventListener('click', () => { mode = order[(order.indexOf(mode) + 1) % order.length]; try { localStorage.setItem('ryu_ambient_mode', mode); } catch (e) {} label(); if (reduce) frame(); });
  addEventListener('resize', () => { resize(); seed(); });
  resize(); seed(); label(); frame();
})();
