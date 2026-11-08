from django.urls import include, path

from community import views as community_views
from courses import game_views, pdf_views
from django.views.generic import RedirectView
from support import araigogu_views

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
    path("", include("portal.urls")),
]
