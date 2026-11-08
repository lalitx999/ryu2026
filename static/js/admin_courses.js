/* Course editor: modules / lessons CRUD, PDF upload, drag-and-drop ordering (all AJAX). */
(function () {
  const { ajax } = window.Ryu, $ = (s, r) => (r || document).querySelector(s), $$ = (s, r) => Array.from((r || document).querySelectorAll(s));
  const courseId = $('#ce').dataset.course, lessons = JSON.parse($('#lessons-data').textContent);
  const reload = () => location.reload();
  const run = async (p, okMsg) => { try { const r = await p; window.Ryu.toast(okMsg || r.message); return r; } catch (e) { window.Ryu.toast(e.message, 'err'); return null; } };

  $('#add-module').addEventListener('click', async () => {
    const title = prompt('ชื่อหมวดใหญ่ใหม่:'); if (!title || !title.trim()) return;
    if (await run(ajax.post('/admin-panel/modules/save/', { course_id: courseId, title }))) reload();
  });
  $('#del-course').addEventListener('click', async (e) => {
    if (!confirm('ลบคอร์สนี้ถาวร? (ทำได้เฉพาะคอร์สที่ยังไม่มีนักเรียนหรือประวัติการชำระเงิน)')) return;
    if (await run(ajax.post(e.currentTarget.dataset.url, {}))) location.href = '/admin-panel/courses/';
  });

  const modal = new bootstrap.Modal($('#lessonModal')), form = $('#lesson-form');
  function openLesson(l, moduleId) {
    form.reset(); form.elements.lesson_id.value = l ? l.id : ''; form.elements.module_id.value = moduleId || (l && l.module_id) || '';
    $('#lesson-title').textContent = l ? 'แก้ไขบทเรียน' : 'เพิ่มบทเรียนใหม่';
    ['title', 'video_url', 'description', 'duration', 'pdf_title'].forEach((k) => { if (l) form.elements[k].value = l[k] == null ? '' : l[k]; });
    form.elements.is_free.checked = !!(l && l.is_free); modal.show();
  }
  form.addEventListener('submit', async (e) => {
    e.preventDefault(); const fd = new FormData(form), id = fd.get('lesson_id');
    fd.set('is_free', form.elements.is_free.checked ? '1' : '0'); fd.set('remove_pdf', form.elements.remove_pdf.checked ? '1' : '0');
    fd.set('course_id', courseId); if (!(form.elements.pdf_file.files || []).length) fd.delete('pdf_file');
    const btn = form.querySelector('.modal-footer button'); btn.disabled = true;
    const r = await run(ajax.post(id ? `/admin-panel/lessons/${id}/save/` : '/admin-panel/lessons/save/', fd));
    btn.disabled = false; if (r) reload();
  });

  document.addEventListener('click', async (e) => {
    const b = e.target.closest('[data-act]'); if (!b) return;
    const id = b.dataset.id, act = b.dataset.act;
    if (act === 'add-lesson') openLesson(null, b.dataset.module);
    else if (act === 'edit-lesson') openLesson(lessons[id]);
    else if (act === 'del-lesson') { if (confirm('ลบบทเรียนนี้?') && await run(ajax.post(`/admin-panel/lessons/${id}/delete/`, {}))) reload(); }
    else if (act === 'sort-module') { if (await run(ajax.post(`/admin-panel/modules/${id}/sort/`, {}))) setTimeout(reload, 600); }
    else if (act === 'del-module') { if (confirm('ลบหมวดนี้? (ต้องไม่มีบทเรียนค้างอยู่)') && await run(ajax.post(`/admin-panel/modules/${id}/delete/`, {}))) reload(); }
    else if (act === 'rename-module') {
      const cur = b.closest('.mod').querySelector('.mod-title').textContent, title = prompt('ชื่อหมวด:', cur);
      if (title && title.trim() && await run(ajax.post(`/admin-panel/modules/${id}/save/`, { title }))) reload();
    }
  });

  /* drag & drop ordering: modules among themselves, lessons within a module */
  let drag = null;
  const save = (kind, container, sel) => run(ajax.post(`/admin-panel/reorder/${kind}/`, { ids: $$(sel, container).map((n) => +n.dataset.id) }));
  document.addEventListener('dragstart', (e) => {
    const n = e.target.closest('.lesson, .mod'); if (!n) return;
    drag = n; e.stopPropagation(); n.classList.add('dragging'); e.dataTransfer.effectAllowed = 'move'; e.dataTransfer.setData('text/plain', n.dataset.id);
  });
  document.addEventListener('dragover', (e) => {
    if (!drag) return;
    const over = e.target.closest(drag.classList.contains('lesson') ? '.lesson' : '.mod');
    if (!over || over === drag || over.parentNode !== drag.parentNode) return;
    e.preventDefault();
    const r = over.getBoundingClientRect(), after = e.clientY > r.top + r.height / 2;
    over.parentNode.insertBefore(drag, after ? over.nextSibling : over);
  });
  document.addEventListener('dragend', async () => {
    if (!drag) return;
    const n = drag; drag = null; n.classList.remove('dragging');
    if (n.classList.contains('lesson')) await save('lessons', n.parentNode, '.lesson'); else await save('modules', n.parentNode, '.mod');
  });
})();
