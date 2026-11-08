"""RyuGames: the page shell plus the leaderboard API."""
from django.shortcuts import render
from django.templatetags.static import static
from django.views.decorators.csrf import ensure_csrf_cookie

from core.http import ajax_view, json_body, ok
from courses.selectors import game_selector
from courses.services import game_service


@ensure_csrf_cookie
def page(request):
    u = request.user
    member = (u.nickname or u.name or u.email) if u.is_authenticated else ""
    return render(request, "portal/games.html", {
        "member_name": member,
        "games_json": static("data/games.json"),
        "quiz_json": static("data/speed_quiz.json"),
        "three_url": static("vendor/three/three.module.js"),
    })


@ajax_view("GET")
def leaderboard(request):
    # The legacy client reads a bare list, so keep that shape.
    from django.http import JsonResponse
    return JsonResponse(game_selector.leaderboard(request.GET.get("game_mode", "kana"), request.GET.get("jlpt_level")),
                        safe=False, json_dumps_params={"ensure_ascii": False})


@ajax_view("POST")
def submit_score(request):
    d = json_body(request)
    s = game_service.submit_score(request.user, request.META.get("REMOTE_ADDR", "?"), d.get("game_mode", "kana"),
                                  d.get("jlpt_level", "N5"), d.get("player_name"), d.get("score", 0))
    return ok({"score": s.score}, message="บันทึกคะแนนเข้าสู่ตารางคะแนนเรียบร้อย")
