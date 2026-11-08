"""Score intake.  Scores come from the browser so they cannot be trusted blindly: only known games are
accepted, each with a ceiling the game cannot legitimately exceed, and submissions are rate limited."""
from django.core.cache import cache

from core.http import ServiceError
from courses.models import GameScore
from courses.selectors.game_selector import LEVELS

# game_mode -> highest score achievable in a perfect run
MAX_SCORE = {
    "shiba_restaurant": 300_000,   # 20 customers x 1,500 yen x 10 pieces
    "shiba_memory": 100_000,
    "boss_rush": 100_000,
    "survival100": 1_000,          # 100 questions x 10 pts
    "sentence_builder": 100_000,
    "speed_quiz": 250_000,
    "kana": 250_000,
}
SUBMITS_PER_MINUTE = 20


def submit_score(user, ip, game_mode, jlpt_level, player_name, raw_score):
    if game_mode not in MAX_SCORE:
        raise ServiceError("ไม่รู้จักโหมดเกมนี้")
    if jlpt_level not in LEVELS:
        raise ServiceError("ระดับ JLPT ไม่ถูกต้อง")
    try:
        score = int(raw_score)
    except (TypeError, ValueError):
        raise ServiceError("คะแนนไม่ถูกต้อง")
    if score < 0 or score > MAX_SCORE[game_mode]:
        raise ServiceError("คะแนนไม่อยู่ในช่วงที่เป็นไปได้")
    player_name = (player_name or "").strip()[:50]
    if not user.is_authenticated and not player_name:
        raise ServiceError("กรุณาระบุชื่อผู้เล่น")
    key = f"gscore:{user.pk or ip}"
    n = cache.get(key, 0)
    if n >= SUBMITS_PER_MINUTE:
        raise ServiceError("ส่งคะแนนถี่เกินไป กรุณารอสักครู่", status=429)
    cache.set(key, n + 1, 60)
    return GameScore.objects.create(
        user=user if user.is_authenticated else None, player_name="" if user.is_authenticated else player_name,
        game_mode=game_mode, jlpt_level=jlpt_level, score=score)
