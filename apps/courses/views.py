from core.http import ServiceError, ajax_view, json_body, ok
from courses.selectors import calendar_selector, course_selector
from courses.services import progress_service


@ajax_view("GET")
def dashboard(request):
    return ok(course_selector.catalog(request.user))


@ajax_view("GET")
def course_detail(request, course_id):
    outline = course_selector.course_outline(course_id, request.user)
    if outline is None:
        raise ServiceError("ไม่พบคอร์สเรียน", status=404)
    return ok(outline)


@ajax_view("GET")
def free_trial(request):
    return ok(course_selector.free_trial_lessons())


@ajax_view("POST", login=True)
def save_progress(request):
    data = json_body(request)
    truthy = lambda v: str(v).lower() in ("1", "true")  # noqa: E731
    p = progress_service.save_progress(request.user, data.get("lesson_id"), data.get("video_time", 0),
                                       truthy(data.get("is_completed")),
                                       truthy(data["set_completed"]) if "set_completed" in data else None)
    return ok({"video_time": p.video_time, "is_completed": p.is_completed}, message="บันทึกความคืบหน้าสำเร็จ")


@ajax_view("GET", login=True)
def study_calendar(request):
    try:
        year, month = int(request.GET.get("year", 0)) or None, int(request.GET.get("month", 0)) or None
    except ValueError:
        year = month = None
    return ok(calendar_selector.study_calendar(request.user, year, month))


@ajax_view("GET", "POST", login=True)
def note(request, lesson_id=None):
    if request.method == "GET":
        n = progress_service.get_note(request.user, lesson_id)
        return ok({"content": n.content if n else "", "updated_at": n.updated_at.strftime("%H:%M:%S") if n else None})
    data = json_body(request)
    n = progress_service.save_note(request.user, data.get("lesson_id"), data.get("content", ""))
    return ok({"content": n.content, "updated_at": n.updated_at.strftime("%H:%M:%S")},
              message="บันทึกสมุดโน้ตส่วนตัวสำเร็จ")
