/* Tiny AJAX layer (fetch + CSRF).  Every endpoint answers {ok, data, error, message, ...}. */
(function () {
  function cookie(name) {
    const m = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'));
    return m ? decodeURIComponent(m[1]) : '';
  }
  async function request(method, url, body) {
    const opts = { method, credentials: 'same-origin', headers: { 'X-Requested-With': 'XMLHttpRequest' } };
    if (method !== 'GET') opts.headers['X-CSRFToken'] = cookie('csrftoken');
    if (body instanceof FormData) opts.body = body;
    else if (body !== undefined) { opts.headers['Content-Type'] = 'application/json'; opts.body = JSON.stringify(body); }
    let res, json;
    try { res = await fetch(url, opts); } catch (e) { throw { message: 'เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ กรุณาลองใหม่', network: true }; }
    try { json = await res.json(); } catch (e) { json = { ok: false, error: 'เซิร์ฟเวอร์ตอบกลับผิดปกติ (' + res.status + ')' }; }
    if (!res.ok || json.ok === false) throw Object.assign({ message: json.error || 'เกิดข้อผิดพลาด', status: res.status }, json);
    return json;
  }
  window.Ryu = window.Ryu || {};
  window.Ryu.ajax = {
    get: (u) => request('GET', u),
    post: (u, b) => request('POST', u, b),
    del: (u) => request('DELETE', u),
  };
  window.Ryu.esc = function (s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  };
  window.Ryu.baht = (n, d) => Number(n).toLocaleString('th-TH', { minimumFractionDigits: d || 0, maximumFractionDigits: d || 0 });
  window.Ryu.busy = function (btn, on, label) {
    if (!btn) return;
    if (on) { btn.dataset.label = btn.textContent; btn.disabled = true; if (label) btn.textContent = label; }
    else { btn.disabled = false; if (btn.dataset.label) btn.textContent = btn.dataset.label; }
  };
  window.Ryu.flash = function (box, kind, text) {
    if (!box) return;
    box.className = text ? (kind === 'ok' ? 'xp-alert-ok' : 'xp-alert-err') : 'd-none';
    box.textContent = text ? (kind === 'ok' ? '🟢 ' : '⚠️ ') + text : '';
  };
})();
