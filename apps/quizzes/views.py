from core.http import ajax_view, json_body, ok
from quizzes.services import quiz_service


@ajax_view("GET", login=True)
def quiz_detail(request, lesson_id):
    return ok(quiz_service.quiz_for_lesson(lesson_id))


@ajax_view("POST", login=True)
def submit(request):
    data = json_body(request)
    return ok(quiz_service.grade(request.user, data.get("quiz_id"), data.get("answers")), status=201)
