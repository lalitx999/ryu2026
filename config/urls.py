from django.http import HttpResponseRedirect
from django.urls import include, path, re_path

from community import views as community_views
from courses import game_views, pdf_views
from django.views.generic import RedirectView
from support import araigogu_views

def legacy_admin(request, rest=None):
    """The old Next.js site kept its admin at /admin/login, /admin/payments, ... - keep those bookmarks working."""
    rest = (rest or "").strip("/")
    target = f"/admin-panel/{rest}/" if rest else "/admin-panel/"
    query = request.META.get("QUERY_STRING")
    return HttpResponseRedirect(f"{target}?{query}" if query else target)


urlpatterns = [
    path("api/auth/", include("users.urls")),
    path("api/courses/", include("courses.urls")),
    path("api/quizzes/", include("quizzes.urls")),
    path("api/payments/", include("payments.urls")),
    path("api/support/", include("support.urls")),
    path("api/araigogu/", include("support.araigogu_urls")),
    path("araigogu/", araigogu_views.page, name="araigogu_page"),
    path("api/games/", include("courses.game_urls")),
    path("games/", game_views.page, name="games_page"),
    path("speed-quiz/", RedirectView.as_view(url="/games/?play=speed_quiz", query_string=False)),
    path("api/community/", include("community.urls")),
    # Legacy image URLs stored in community_post_images ("/storage/community/<file>")
    path("storage/protected_pdfs/<str:filename>", pdf_views.lesson_pdf, name="lesson_pdf"),
    path("storage/community/<str:filename>", community_views.community_image, name="community_image"),
    path("community/", include("community.page_urls")),
    path("admin-panel/", include("backoffice.urls")),
    re_path(r"^admin(?:/(?P<rest>.*))?$", legacy_admin),   # legacy URLs -> /admin-panel/...
    path("", include("portal.urls")),
]
