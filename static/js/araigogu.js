/* Araigogu AI: language/mode switch, history sidebar, chat with polling for the Celery reply. */
(function () {
  const $ = (s) => document.querySelector(s), $$ = (s) => Array.from(document.querySelectorAll(s));
  const { ajax, esc } = window.Ryu;
  const st = { lang: 'JA', mode: 'chat', sid: null, sending: false };

  const WELCOME = {
    JA: { chat: 'こんにちは！(สวัสดีค่ะ!) น้องริวโซ่ (Ryuso Sense) พร้อมช่วยสอนภาษาญี่ปุ่นแล้วค่ะ 🇯🇵 สอบถามคำศัพท์ ไวยากรณ์ คันจิ หรือ JLPT N5-N1 ได้เลยนะคะ!',
      checker: '📝 กรุณาพิมพ์ประโยคหรือข้อความภาษาญี่ปุ่นที่ต้องการให้ตรวจทานไวยากรณ์ คันจิ และฟุริงะนะลงในช่องข้อความด้านล่างได้เลยค่ะ 🇯🇵',
      interview: 'こんにちは！(สวัสดีค่ะ!) ยินดีต้อนรับสู่ห้องสอบสัมภาษณ์ภาษาญี่ปุ่นค่ะ 🇯🇵 โปรดแนะนำตัวเป็นภาษาญี่ปุ่นสักนิดนะคะ (自己紹介をお願いします)' },
    ZH: { chat: '你好！(สวัสดีครับ!) เหล่าซือ (Lao Shi) พร้อมช่วยสอนภาษาจีนแล้วครับ 🇨🇳 สอบถามพินอิน (Pinyin), ตัวอักษรจีน (Hanzi) หรือ HSK 1-6 ได้เลยครับ!',
      checker: '📝 กรุณาพิมพ์ประโยคภาษาจีนที่ต้องการให้ตรวจทานไวยากรณ์ พินอิน (Pinyin) และลำดับคำลงในช่องข้อความด้านล่างได้เลยครับ 🇨🇳',
      interview: '你好！(สวัสดีครับ!) ยินดีต้อนรับสู่ห้องสัมภาษณ์ภาษาจีนครับ 🇨🇳 请你用中文自我介绍一下 (โปรดแนะนำตัวเป็นภาษาจีนสักนิดนะครับ)' },
    TH: { chat: 'สวัสดีครับ! ครูริว (Kuru Thai) พร้อมช่วยเหลือด้านภาษาไทยครับ 🇹🇭 สอบถามไวยากรณ์ การสะกดคำ ระดับภาษา หรือการแต่งประโยคได้เลยครับ!',
      checker: '📝 กรุณาพิมพ์ประโยคหรือข้อความภาษาไทยที่ต้องการให้ตรวจทานคำผิด ไวยากรณ์ หรือสละสลวยประโยคได้เลยครับ 🇹🇭',
      interview: 'สวัสดีครับ! ยินดีต้อนรับสู่ห้องสัมภาษณ์งานภาษาไทยครับ 🇹🇭 โปรดแนะนำตัวและเล่าประสบการณ์ของคุณสักครู่นะครับ' },
  };
  const PLACEHOLDER = {
    JA: 'พิมพ์ข้อความภาษาญี่ปุ่นหรือสอบถามเรื่องเรียนที่นี่... (กด Enter เพื่อส่ง)',
    ZH: 'พิมพ์ข้อความภาษาจีนหรือสอบถามที่นี่... (กด Enter เพื่อส่ง)',
    TH: 'พิมพ์ข้อความภาษาไทยเพื่อตรวจทานหรือสอบถามที่นี่... (กด Enter เพื่อส่ง)',
  };
  const LABEL = { JA: '🇯🇵 日本語 (ญี่ปุ่น)', ZH: '🇨🇳 中文 (จีน)', TH: '🇹🇭 ภาษาไทย' };
  const FLAG = { JA: '🇯🇵 JP', ZH: '🇨🇳 CN', TH: '🇹🇭 TH' };

  const log = $('#ara-log');
  function bubble(m) {
    const user = m.sender === 'user';
    log.insertAdjacentHTML('beforeend', `
      <div class="d-flex ${user ? 'justify-content-end' : 'justify-content-start'}"><div class="ara-msg ${user ? 'user' : 'bot'}">
        <div class="d-flex justify-content-between align-items-center t10 pb-1 mb-1" style="opacity:.75;border-bottom:1px solid rgba(255,255,255,.1);gap:8px">
          <b>${user ? '👤 คุณ (นักเรียน)' : '🤖 Araigogu AI'}</b>${m.model_used ? `<span class="ara-model">${esc(m.model_used)}</span>` : ''}</div>
        <div style="white-space:pre-wrap;line-height:1.6">${esc(m.content)}</div></div></div>`);
    log.scrollTop = log.scrollHeight;
  }
  function thinking(on) {
    const el = $('#ara-thinking');
    if (!on) return el && el.remove();
    if (!el) log.insertAdjacentHTML('beforeend', '<div id="ara-thinking" class="d-flex"><div class="ara-msg bot" style="color:#fcd34d"><span class="ara-dot"></span> Araigogu AI กำลังคิดประมวลผลคำตอบ</div></div>');
    log.scrollTop = log.scrollHeight;
  }
  function welcome() {
    log.innerHTML = ''; bubble({ sender: 'assistant', content: WELCOME[st.lang][st.mode], model_used: 'System' });
    $('#ara-input').placeholder = PLACEHOLDER[st.lang]; $('#ara-hint').textContent = '💡 เลือกภาษาเป้าหมาย: ' + LABEL[st.lang];
  }
  function sync() {
    $$('.ara-lang').forEach((b) => b.classList.toggle('active', b.dataset.lang === st.lang));
    $$('.ara-mode').forEach((b) => b.classList.toggle('active', b.dataset.mode === st.mode));
  }

  async function loadHistory() {
    const box = $('#ara-history');
    try {
      const rows = (await ajax.get('/api/araigogu/history/')).data;
      box.innerHTML = rows.length ? rows.map((s) => `
        <div class="ara-sess ${s.session_id === st.sid ? 'on' : ''}" data-sid="${esc(s.session_id)}">
          <div class="fw-semibold text-truncate pe-4">${esc(s.title)}</div>
          <div class="d-flex justify-content-between t9" style="color:#6b7280"><span class="ara-flag">${FLAG[s.target_language] || ''}</span><span>${esc(s.updated_at)}</span></div>
          <button type="button" class="ara-del" data-del="${esc(s.session_id)}" title="ลบประวัติสนทนานี้">🗑️</button></div>`).join('')
        : '<div class="p-3 text-center t11" style="color:#9ca3af">ยังไม่มีประวัติการสนทนา</div>';
    } catch (e) { box.innerHTML = '<div class="p-3 text-center t11" style="color:#9ca3af">โหลดประวัติไม่สำเร็จ</div>'; }
  }
  function fresh() { st.sid = null; $('#ara-input').value = ''; welcome(); loadHistory(); }

  $('#ara-langs').addEventListener('click', (e) => { const b = e.target.closest('[data-lang]'); if (!b) return; st.lang = b.dataset.lang; st.sid = null; sync(); welcome(); });
  $('#ara-modes').addEventListener('click', (e) => { const b = e.target.closest('[data-mode]'); if (!b) return; st.mode = b.dataset.mode; st.sid = null; sync(); welcome(); });
  $('#ara-new').addEventListener('click', fresh);
  $('#ara-toggle-side').addEventListener('click', () => {
    const side = $('#ara-side'); const hide = !side.classList.toggle('d-none');
    $('#ara-toggle-side').textContent = hide ? '📖 ซ่อนประวัติ' : '📜 ประวัติ';
  });
  $('#ara-history').addEventListener('click', async (e) => {
    const del = e.target.closest('[data-del]');
    if (del) {
      e.stopPropagation(); if (!confirm('คุณต้องการลบประวัติสนทนานี้ใช่หรือไม่?')) return;
      try { await ajax.del('/api/araigogu/sessions/' + del.dataset.del + '/'); if (st.sid === del.dataset.del) fresh(); else loadHistory(); }
      catch (err) { alert(err.message || 'ไม่สามารถลบประวัติสนทนาได้'); }
      return;
    }
    const row = e.target.closest('[data-sid]'); if (!row) return;
    try {
      const d = (await ajax.get('/api/araigogu/sessions/' + row.dataset.sid + '/')).data;
      st.sid = d.session_id; st.lang = d.target_language || st.lang; st.mode = d.mode || st.mode; sync();
      log.innerHTML = ''; d.messages.forEach(bubble); loadHistory();
    } catch (err) { alert(err.message || 'ไม่สามารถโหลดประวัติสนทนาได้'); }
  });

  async function send() {
    const input = $('#ara-input'), text = input.value.trim();
    if (!text || st.sending) return;
    st.sending = true; $('#ara-send').disabled = true; $('#ara-send').textContent = '⏳ กำลังส่ง...';
    bubble({ sender: 'user', content: text }); input.value = ''; thinking(true);
    try {
      let d = (await ajax.post('/api/araigogu/chat/', { session_id: st.sid, target_language: st.lang, mode: st.mode, message: text })).data;
      if (d.session_id) st.sid = d.session_id;
      for (let i = 0; i < 45 && d.state === 'pending'; i++) {
        await new Promise((r) => setTimeout(r, 1500));
        d = Object.assign({ session_id: st.sid }, (await ajax.get('/api/araigogu/chat/' + d.task_id + '/')).data, { task_id: d.task_id });
        if (d.state === 'pending' && i === 44) throw { message: 'AI ตอบช้าเกินไป ลองใหม่อีกครั้งนะคะ' };
      }
      if (d.session_id) st.sid = d.session_id;
      thinking(false); bubble({ sender: 'assistant', content: d.content || 'ไม่สามารถดึงคำตอบได้', model_used: d.model_used });
      loadHistory();
    } catch (err) {
      thinking(false); bubble({ sender: 'assistant', content: '⚠️ เกิดข้อผิดพลาด: ' + (err.message || 'ไม่สามารถเชื่อมต่อ AI Engine ได้'), model_used: 'Error' });
    }
    st.sending = false; $('#ara-send').disabled = false; $('#ara-send').textContent = 'ส่งข้อความ 💬';
  }
  $('#ara-form').addEventListener('submit', (e) => { e.preventDefault(); send(); });
  $('#ara-input').addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } });

  sync(); welcome(); loadHistory();
})();
