from django.core.cache import cache
from django.test import TestCase

from core import testing  # noqa: F401  (py3.14 template-copy shim)
from courses.models import GameScore
from courses.selectors import game_selector
from users.models import User


class GameScoreTests(TestCase):
    def setUp(self):
        cache.clear()

    def submit(self, **kw):
        body = {"game_mode": "survival100", "jlpt_level": "N5", "player_name": "Guest", "score": 100}
        body.update(kw)
        return self.client.post("/api/games/submit-score/", body, content_type="application/json")

    def test_guest_submit_and_listing_order(self):
        for s in (50, 900, 300):
            self.assertEqual(self.submit(score=s).status_code, 200)
        rows = self.client.get("/api/games/leaderboard/?game_mode=survival100&jlpt_level=N5").json()
        self.assertEqual([r["score"] for r in rows], [900, 300, 50])
        self.assertEqual(rows[0]["user_name"], "Guest")

    def test_validation(self):
        self.assertEqual(self.submit(game_mode="hax").status_code, 400)
        self.assertEqual(self.submit(jlpt_level="N9").status_code, 400)
        self.assertEqual(self.submit(score="abc").status_code, 400)
        self.assertEqual(self.submit(score=-5).status_code, 400)
        self.assertEqual(self.submit(score=10_000_000).status_code, 400)   # beyond what survival100 can reach
        self.assertEqual(self.submit(player_name="  ").status_code, 400)
        self.assertEqual(GameScore.objects.count(), 0)

    def test_member_score_uses_account_name(self):
        u = User.objects.create_user("m@test.local", "pw123456", name="Mika", nickname="Mi")
        self.client.force_login(u)
        self.assertEqual(self.submit(player_name="").status_code, 200)
        self.assertEqual(self.client.get("/api/games/leaderboard/?game_mode=survival100").json()[0]["user_name"], "Mi (Mika)")

    def test_rate_limit(self):
        codes = [self.submit().status_code for _ in range(22)]
        self.assertEqual(codes[:20], [200] * 20)
        self.assertEqual(codes[20:], [429, 429])

    def test_leaderboard_query_count_constant(self):
        u = User.objects.create_user("q@test.local", "pw123456", name="Q")
        for i in range(15):
            GameScore.objects.create(user=u if i % 2 else None, player_name="g", game_mode="speed_quiz", jlpt_level="N5", score=i)
        with self.assertNumQueries(1):
            rows = game_selector.leaderboard("speed_quiz", "N5")
        self.assertEqual(len(rows), 10)

    def test_pages(self):
        self.assertEqual(self.client.get("/games/").status_code, 200)
        r = self.client.get("/speed-quiz/")
        self.assertEqual((r.status_code, r["Location"]), (302, "/games/?play=speed_quiz"))
