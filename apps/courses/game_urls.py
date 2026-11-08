from django.urls import path

from . import game_views as v

app_name = "games"
urlpatterns = [
    path("leaderboard/", v.leaderboard, name="leaderboard"),
    path("submit-score/", v.submit_score, name="submit_score"),
]
