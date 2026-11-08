from courses.models import GameScore

LEVELS = ("N5", "N4", "N3", "N2", "N1")
TOP_N = 10


def _display_name(s):
    if s.user_id and s.user:
        name = s.user.name or s.user.email.split("@")[0]
        return f"{s.user.nickname} ({s.user.name or 'นักเรียน'})" if s.user.nickname else name
    return s.player_name or "ผู้เล่น Ryugame"


def leaderboard(game_mode, jlpt_level=None):
    """Top 10 for one game (and level).  One query: the user join is select_related."""
    qs = GameScore.objects.filter(game_mode=game_mode)
    if jlpt_level in LEVELS:
        qs = qs.filter(jlpt_level=jlpt_level)
    qs = qs.select_related("user").only(
        "id", "score", "game_mode", "created_at", "player_name", "user__name", "user__nickname", "user__email",
    ).order_by("-score", "created_at")[:TOP_N]
    return [{"id": s.id, "user_name": _display_name(s), "score": s.score, "game_mode": s.game_mode,
             "created_at": s.created_at.strftime("%d/%m/%Y %H:%M")} for s in qs]
