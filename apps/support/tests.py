from unittest import mock

from django.core.cache import cache
from django.test import TestCase

from core import testing  # noqa: F401  (py3.14 template-copy shim)
from support import ai
from support.models import AraigoguMessage, AraigoguSession
from users.models import User


def fake(text="こんにちは"):
    return mock.patch("support.tasks.ai.complete", return_value=ai.Completion(text, "Test (m)", 5))


class AraigoguTests(TestCase):
    def setUp(self):
        cache.clear()

    def chat(self, client, msg="hello", **kw):
        body = {"target_language": "JA", "mode": "chat", "message": msg}
        body.update(kw)
        return client.post("/api/araigogu/chat/", body, content_type="application/json")

    def test_guest_chat_stores_history_and_reply(self):
        with fake():
            r = self.chat(self.client)
        d = r.json()["data"]
        self.assertEqual((d["state"], d["content"]), ("done", "こんにちは"))
        self.assertEqual(list(AraigoguMessage.objects.order_by("id").values_list("sender", flat=True)), ["user", "assistant"])
        self.assertEqual(len(self.client.get("/api/araigogu/history/").json()["data"]), 1)

    def test_other_browser_cannot_read_or_delete(self):
        with fake():
            sid = self.chat(self.client).json()["data"]["session_id"]
        from django.test import Client
        other = Client()
        self.assertEqual(other.get("/api/araigogu/history/").json()["data"], [])
        self.assertEqual(other.get(f"/api/araigogu/sessions/{sid}/").status_code, 404)
        self.assertEqual(other.delete(f"/api/araigogu/sessions/{sid}/").status_code, 404)
        self.assertTrue(AraigoguSession.objects.filter(session_id=sid).exists())
        with fake():
            self.assertEqual(self.chat(other, session_id=sid).status_code, 404)

    def test_owner_can_delete_and_user_history_is_scoped(self):
        u = User.objects.create_user("a@test.local", "pw123456", name="A")
        self.client.force_login(u)
        with fake():
            sid = self.chat(self.client).json()["data"]["session_id"]
        self.assertEqual(self.client.delete(f"/api/araigogu/sessions/{sid}/", HTTP_X_CSRFTOKEN="x").status_code, 200)
        self.assertFalse(AraigoguSession.objects.exists())

    def test_validation_and_fallback(self):
        self.assertEqual(self.chat(self.client, msg="  ").status_code, 400)
        self.assertEqual(self.chat(self.client, target_language="XX").status_code, 400)
        with mock.patch("support.tasks.ai.complete", return_value=None):
            d = self.chat(self.client).json()["data"]
        self.assertEqual(d["model_used"], "fallback")

    def test_rate_limit(self):
        with fake():
            codes = [self.chat(self.client).status_code for _ in range(17)]
        self.assertEqual(codes[:15], [200] * 15)
        self.assertEqual(codes[15:], [429, 429])

    def test_history_query_count_constant(self):
        with fake():
            for _ in range(3):
                self.chat(self.client)
        from support.selectors import araigogu_selector
        ids = list(AraigoguSession.objects.values_list("session_id", flat=True))
        with self.assertNumQueries(1):  # sessions + message_count in one aggregate query, however many sessions
            araigogu_selector.history(mock.Mock(is_authenticated=False), {"ara_ids": ids})

    def test_page_renders(self):
        self.assertEqual(self.client.get("/araigogu/").status_code, 200)
