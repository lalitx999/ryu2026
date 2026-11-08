"""Course / module / lesson management for the custom admin."""
import os
import uuid
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.db import transaction
from django.db.models import Max
from django.utils.text import slugify

from core.http import ServiceError
from courses.models import Course, Enrollment, Lesson, Module
from payments.models import Payment

LEVELS = {"N5", "N4", "N3", "N2", "N1"}
MAX_PDF_BYTES = 20 * 1024 * 1024


def truthy(v):
    return str(v).lower() in ("1", "true", "on", "yes")


def money(value, *, required=False, label="ราคา"):
    if value in (None, ""):
        if required:
            raise ServiceError(f"{label}ต้องไม่ว่าง")
        return None
    try:
        amount = Decimal(str(value))
    except InvalidOperation:
        raise ServiceError("รูปแบบราคาไม่ถูกต้อง")
    if amount <= 0:
        raise ServiceError("ราคาต้องมากกว่า 0 (เว้นว่างเพื่อปิดแพ็กเกจ)")
    return amount


def _int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@transaction.atomic
def save_course(data, course_id=None):
    if course_id:
        course = Course.objects.select_for_update().filter(pk=course_id).first()
        if not course:
            raise ServiceError("ไม่พบคอร์ส", status=404)
    else:
        title = str(data.get("title", "")).strip()
        if not title:
            raise ServiceError("กรุณาระบุชื่อคอร์สเรียน")
        course = Course(title=title, is_active=True)
        base = slugify(title, allow_unicode=True)[:150] or "course"
        course.slug = f"{base}-{uuid.uuid4().hex[:8]}"
        course.sort_order = (Course.objects.aggregate(m=Max("sort_order"))["m"] or 0) + 1
    if "title" in data and str(data["title"]).strip():
        course.title = str(data["title"]).strip()[:200]
    if "level" in data:
        if data["level"] not in LEVELS:
            raise ServiceError("ระดับ JLPT ไม่ถูกต้อง")
        course.level = data["level"]
    if "description" in data:
        course.description = str(data["description"])[:5000]
    course.price = money(data.get("price"), required=True, label="ราคารายเดือน")
    course.price_180 = money(data.get("price_180"))
    course.price_365 = money(data.get("price_365"))
    course.price_lifetime = money(data.get("price_lifetime"))
    if "sort_order" in data and _int(data["sort_order"]) is not None:
        course.sort_order = _int(data["sort_order"])
    if "is_active" in data:
        course.is_active = truthy(data["is_active"])
    course.save()
    return course


def delete_course(course_id):
    """Deleting a course that has sales/students would erase their history, so only empty courses can go."""
    if Payment.objects.filter(course_id=course_id).exists() or Enrollment.objects.filter(course_id=course_id).exists():
        raise ServiceError("คอร์สนี้มีประวัติการชำระเงิน/นักเรียนแล้ว ลบไม่ได้ กรุณาปิดขายแทน")
    deleted, _ = Course.objects.filter(pk=course_id).delete()
    if not deleted:
        raise ServiceError("ไม่พบคอร์ส", status=404)


def _next_order(qs):
    top = qs.aggregate(m=Max("sort_order"))["m"]
    return top + 1 if top is not None and top >= 0 else 1


@transaction.atomic
def save_module(data, module_id=None):
    title = str(data.get("title", "")).strip()
    if module_id:
        module = Module.objects.filter(pk=module_id).first()
        if not module:
            raise ServiceError("ไม่พบหมวดนี้", status=404)
        if title:
            module.title = title[:255]
    else:
        course = Course.objects.filter(pk=data.get("course_id")).first()
        if not course or not title:
            raise ServiceError("กรุณาระบุคอร์สและชื่อหมวด")
        module = Module(course=course, title=title[:255], is_active=True,
                        sort_order=_next_order(Module.objects.filter(course=course)))
    if _int(data.get("sort_order")) is not None:
        module.sort_order = _int(data["sort_order"])
    module.save()
    return module


def delete_module(module_id):
    if Lesson.objects.filter(module_id=module_id).exists():
        raise ServiceError("หมวดนี้ยังมีบทเรียนอยู่ กรุณาลบหรือย้ายบทเรียนก่อน")
    deleted, _ = Module.objects.filter(pk=module_id).delete()
    if not deleted:
        raise ServiceError("ไม่พบหมวดนี้", status=404)


def _store_pdf(lesson, pdf):
    if not pdf.name.lower().endswith(".pdf"):
        raise ServiceError("รองรับเฉพาะไฟล์ PDF")
    if pdf.size > MAX_PDF_BYTES:
        raise ServiceError("ไฟล์ PDF ต้องมีขนาดไม่เกิน 20MB")
    if pdf.read(5) != b"%PDF-":
        raise ServiceError("ไฟล์ไม่ใช่ PDF ที่ถูกต้อง")
    pdf.seek(0)
    os.makedirs(os.path.join(settings.MEDIA_ROOT, "pdfs"), exist_ok=True)
    lesson.pdf_file.save(f"lesson_{lesson.id}_{uuid.uuid4().hex[:8]}.pdf", pdf, save=False)


@transaction.atomic
def save_lesson(data, files, lesson_id=None):
    if lesson_id:
        lesson = Lesson.objects.filter(pk=lesson_id).first()
        if not lesson:
            raise ServiceError("ไม่พบบทเรียนนี้", status=404)
    else:
        course = Course.objects.filter(pk=data.get("course_id")).first()
        title = str(data.get("title", "")).strip()
        if not course or not title:
            raise ServiceError("กรุณาระบุคอร์สและชื่อบทเรียน")
        module = Module.objects.filter(pk=data.get("module_id"), course=course).first() if data.get("module_id") else None
        lesson = Lesson(course=course, module=module, is_active=True,
                        sort_order=_next_order(Lesson.objects.filter(course=course, module=module)))
    for field in ("title", "description", "video_url", "pdf_title"):
        if field in data:
            setattr(lesson, field, str(data[field]).strip())
    if not lesson.title:
        raise ServiceError("กรุณาระบุชื่อบทเรียน")
    if "is_free" in data:
        lesson.is_free = truthy(data["is_free"])
    if _int(data.get("duration")) is not None:
        lesson.duration = max(0, _int(data["duration"]))
    if _int(data.get("sort_order")) is not None:
        lesson.sort_order = _int(data["sort_order"])
    lesson.save()  # id is needed for the PDF file name
    if truthy(data.get("remove_pdf", "")):
        lesson.pdf_file, lesson.pdf_title = "", ""
    elif files.get("pdf_file"):
        _store_pdf(lesson, files["pdf_file"])
    lesson.save()
    return lesson


def delete_lesson(lesson_id):
    deleted, _ = Lesson.objects.filter(pk=lesson_id).delete()
    if not deleted:
        raise ServiceError("ไม่พบบทเรียนนี้", status=404)


@transaction.atomic
def reorder(model, ids):
    """Persist a drag-and-drop order in one bulk update (positions start at 1)."""
    if not isinstance(ids, list) or not ids:
        raise ServiceError("ลำดับไม่ถูกต้อง")
    ids = [i for i in (_int(x) for x in ids) if i is not None]
    objs = {o.pk: o for o in model.objects.filter(pk__in=ids)}
    ordered = []
    for pos, pk in enumerate(ids, start=1):
        if pk in objs:
            objs[pk].sort_order = pos
            ordered.append(objs[pk])
    model.objects.bulk_update(ordered, ["sort_order"])


_NUM = __import__("re").compile(r"\d+")


@transaction.atomic
def sort_lessons_by_number(module_id):
    """Order a module's lessons by the first number in each title ("บทที่ 2" before "บทที่ 10"); untitled-number lessons keep
    their relative order at the end.  Positions become 1..N."""
    lessons = list(Lesson.objects.filter(module_id=module_id).order_by("sort_order", "id"))
    if not lessons:
        raise ServiceError("ไม่พบบทเรียนในหมวดนี้", status=404)

    def key(l):
        m = _NUM.search(l.title)
        return (0, int(m.group()), l.sort_order, l.id) if m else (1, 0, l.sort_order, l.id)

    ordered = sorted(lessons, key=key)
    for pos, l in enumerate(ordered, start=1):
        l.sort_order = pos
    Lesson.objects.bulk_update(ordered, ["sort_order"])
    return len(ordered)
