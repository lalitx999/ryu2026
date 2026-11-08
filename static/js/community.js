/* RyuCommunity: list / create / like / comment over AJAX (Bootstrap modal + XP skin). */
(function () {
  const $ = (s, r) => (r || document).querySelector(s);
  const { ajax, esc, flash } = window.Ryu;
  const loggedIn = () => ($('#forum') || $('#post-view')).dataset.loggedIn === '1';
  const needLogin = () => { location.href = '/?auth=login&next=' + encodeURIComponent(location.pathname); };

  document.addEventListener('click', async (e) => {
    if (e.target.closest('[data-act="logout"]')) { try { await ajax.post('/api/auth/logout/'); } finally { location.reload(); } }
    if (e.target.closest('[data-act="open-auth"]')) needLogin();
  });

  /* Poll the Celery moderation task until it finishes (instant when running eagerly). */
  async function awaitModeration(r) {
    let d = r.data;
    for (let i = 0; i < 20 && d.state === 'pending'; i++) {
      await new Promise((ok) => setTimeout(ok, 1000));
      d = (await ajax.get('/api/community/moderation/' + d.task_id + '/')).data;
    }
    return d;
  }

  /* ---------------- list page ---------------- */
  const list = $('#post-list');
  if (list) {
    let cat = 'ALL';
    const card = (p) => `
      <div class="bg-white border rounded p-3 d-flex flex-column gap-2 post-card">
        <div class="d-flex justify-content-between align-items-center">
          <div class="d-flex align-items-center gap-2"><div class="avatar-c">${esc((p.user.name || 'U').charAt(0).toUpperCase())}</div>
            <div><span class="fw-bold" style="color:#1e3a8a">${esc(p.user.name || 'นักเรียน RyuClass')}</span>
              <span class="role-chip">${p.user.role === 'admin' ? '🛡️ แอดมิน' : '🎓 นักเรียน'}</span><div class="t10 text-secondary">${esc(p.created_at)}</div></div></div>
          <div class="d-flex gap-1"><span class="cat-chip">${esc(p.category_display)}</span>
            ${p.moderation_status === 'REWRITTEN' ? `<span class="ai-chip" title="${esc(p.moderation_reason)}">✨ AI เกลาถ้อยคำ</span>` : ''}
            ${p.moderation_status === 'PENDING' ? '<span class="ai-chip">⏳ รอตรวจสอบ</span>' : ''}</div>
        </div>
        <a href="/community/${p.id}/" class="text-decoration-none"><h2 class="fw-bold mb-0" style="font-size:14px;color:#1e3a8a">${esc(p.title)}</h2></a>
        <p class="mb-0 clamp-3" style="color:#374151;white-space:pre-line;line-height:1.6">${esc(p.content)}</p>
        ${p.images.length ? `<div class="d-flex flex-wrap gap-2">${p.images.map((u) => `<a class="thumb" href="${esc(u)}" target="_blank" rel="noopener"><img src="${esc(u)}" alt="รูปแนบ" loading="lazy"></a>`).join('')}</div>` : ''}
        <div class="d-flex justify-content-between align-items-center border-top pt-2 t11 text-secondary">
          <div class="d-flex gap-2"><button type="button" class="like-btn ${p.is_liked ? 'on' : ''}" data-like="${p.id}">${p.is_liked ? '❤️' : '🤍'} ${p.likes_count} ถูกใจ</button>
            <a class="like-btn text-decoration-none" href="/community/${p.id}/">💬 ${p.comments_count} ความคิดเห็น</a></div>
          <span>👁️ ${p.views_count} เข้าชม</span></div>
      </div>`;

    async function load() {
      list.innerHTML = '<div class="bg-white border rounded p-4 text-center fw-bold text-secondary">⏳ กำลังโหลดกระทู้ในชุมชน...</div>';
      const q = $('#search-q').value.trim();
      try {
        const r = await ajax.get('/api/community/posts/?category=' + cat + (q ? '&search=' + encodeURIComponent(q) : ''));
        list.innerHTML = r.data.length ? r.data.map(card).join('') :
          `<div class="bg-white border rounded p-4 text-center"><div style="font-size:30px">💬</div><h3 class="fw-bold" style="font-size:14px">ยังไม่มีกระทู้ในหมวดหมู่นี้</h3><p class="text-secondary">เป็นคนแรกที่เริ่มตั้งกระทู้ถาม-ตอบ หรือแชร์ประสบการณ์กันได้เลย!</p><button class="xp-btn-green px-3 py-1" id="btn-first">✍️ เริ่มตั้งกระทู้แรก</button></div>`;
      } catch (err) { list.innerHTML = `<div class="xp-alert-err">${esc(err.message)}</div>`; }
    }

    $('#cat-tabs').addEventListener('click', (e) => {
      const b = e.target.closest('.cat-tab'); if (!b) return;
      document.querySelectorAll('.cat-tab').forEach((t) => t.classList.toggle('active', t === b)); cat = b.dataset.cat; load();
    });
    $('#search-form').addEventListener('submit', (e) => { e.preventDefault(); load(); });
    list.addEventListener('click', async (e) => {
      if (e.target.id === 'btn-first') return openCreate();
      const b = e.target.closest('[data-like]'); if (!b) return;
      if (!loggedIn()) return needLogin();
      try {
        const d = (await ajax.post('/api/community/posts/' + b.dataset.like + '/like/')).data;
        b.classList.toggle('on', d.liked); b.textContent = (d.liked ? '❤️ ' : '🤍 ') + d.likes_count + ' ถูกใจ';
      } catch (err) { /* ignore */ }
    });

    /* create post */
    const modalEl = $('#postModal'), modal = new bootstrap.Modal(modalEl), form = $('#post-form');
    function openCreate() { if (!loggedIn()) return needLogin(); flash($('#post-msg'), 'err', ''); modal.show(); }
    $('#btn-new-post').addEventListener('click', openCreate);
    modalEl.addEventListener('click', (e) => {
      const b = e.target.closest('[data-emoji]'); if (!b) return;
      const t = form.elements.content, s = t.selectionStart || t.value.length;
      t.value = t.value.slice(0, s) + b.dataset.emoji + t.value.slice(t.selectionEnd || s); t.focus();
    });
    $('#post-images').addEventListener('change', (e) => {
      const box = $('#post-previews'); box.innerHTML = '';
      Array.from(e.target.files).forEach((f, i) => {
        const url = URL.createObjectURL(f);
        box.insertAdjacentHTML('beforeend', `<div class="thumb"><img src="${url}" alt="ตัวอย่าง"><span class="num">#${i + 1}</span></div>`);
      });
    });
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const n = form.elements.images.files.length;
      if (n && (n < 2 || n > 5)) return flash($('#post-msg'), 'err', 'กรุณาแนบรูปภาพให้ครบ 2 ถึง 5 ภาพ (หรือลบรูปออกหากไม่ต้องการแนบ)');
      const btn = $('#post-submit'); btn.disabled = true; btn.textContent = '⏳ AI กำลังคัดกรอง & โพสต์...';
      try {
        const d = await awaitModeration(await ajax.post('/api/community/posts/', new FormData(form)));
        if (d.status === 'REJECTED') throw { message: d.reason || 'เนื้อหามีความรุนแรงหรือคำไม่เหมาะสมอย่างร้ายแรง ระบบปฏิเสธการโพสต์' };
        if (d.status === 'REWRITTEN') { flash($('#post-msg'), 'ok', '✨ RyusoAI ปรับแต่งถ้อยคำในกระทู้ของคุณให้สุภาพและเหมาะสมเรียบร้อยแล้ว!'); await new Promise((r) => setTimeout(r, 1500)); }
        form.reset(); $('#post-previews').innerHTML = ''; modal.hide(); load();
      } catch (err) { flash($('#post-msg'), 'err', err.message || 'ไม่สามารถตั้งกระทู้ได้ โปรดลองอีกครั้ง'); }
      btn.disabled = false; btn.textContent = '🚀 โพสต์กระทู้';
    });
    load();
  }

  /* ---------------- detail page ---------------- */
  const view = $('#post-view');
  if (view) {
    const id = view.dataset.postId;
    $('#like-btn').addEventListener('click', async () => {
      if (!loggedIn()) return needLogin();
      try {
        const d = (await ajax.post('/api/community/posts/' + id + '/like/')).data;
        $('#like-btn').classList.toggle('on', d.liked); $('#like-btn').firstChild.textContent = d.liked ? '❤️ ' : '🤍 '; $('#like-n').textContent = d.likes_count;
      } catch (err) { /* ignore */ }
    });
    $('#comment-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      if (!loggedIn()) return needLogin();
      const f = e.target, btn = $('#comment-submit'); btn.disabled = true; btn.textContent = 'กำลังตรวจสอบ...';
      try {
        const d = await awaitModeration(await ajax.post('/api/community/posts/' + id + '/comments/', { content: f.elements.content.value }));
        if (d.status === 'REJECTED') throw { message: d.reason || 'ความคิดเห็นมีเนื้อหาไม่เหมาะสมอย่างร้ายแรง ระบบปฏิเสธการโพสต์' };
        location.reload();
      } catch (err) { flash($('#comment-msg'), 'err', err.message); btn.disabled = false; btn.textContent = 'ส่งความคิดเห็น'; }
    });
  }
})();
