import io
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from community.models import Comment, Post
from community.selectors import post_selector
from core import testing  # noqa: F401  (py3.14 template-copy shim)
from users.models import User

TMP = tempfile.mkdtemp()


def img(name="a.png"):
    return SimpleUploadedFile(name, b"\x89PNG\r\n\x1a\n" + b"0" * 20, content_type="image/png")


@override_settings(COMMUNITY_STORAGE_DIR=TMP, DEEPSEEK_API_KEY="")
class CommunityTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP, ignore_errors=True)

    def setUp(self):
        self.u = User.objects.create_user("a@test.local", "pw123456", name="Alice")
        self.client.force_login(self.u)

    def post(self, **kw):
        data = {"category": "QNA", "title": "หัวข้อ", "content": "เนื้อหา"}
        data.update(kw)
        return self.client.post("/api/community/posts/", data)

    def test_create_published_after_moderation(self):
        r = self.post()
        self.assertEqual(r.status_code, 201)
        self.assertEqual(Post.objects.get().moderation_status, "APPROVED")

    def test_guest_cannot_post(self):
        self.client.logout()
        self.assertEqual(self.post().status_code, 401)

    def test_image_count_rule_and_type(self):
        self.assertEqual(self.post(images=[img()]).status_code, 400)
        bad = SimpleUploadedFile("x.exe", b"MZ", content_type="application/octet-stream")
        self.assertEqual(self.post(images=[img(), bad]).status_code, 400)
        self.assertEqual(self.post(images=[img(), img("b.png")]).status_code, 201)

    def test_list_query_count_is_constant(self):
        for i in range(3):
            Post.objects.create(user=self.u, title=f"t{i}", content="c", moderation_status="APPROVED")
        with self.assertNumQueries(2):  # posts (+counts, liked) and one prefetch for images
            post_selector.post_list(self.u)
        for i in range(20):
            p = Post.objects.create(user=self.u, title=f"x{i}", content="c", moderation_status="APPROVED")
            Comment.objects.create(user=self.u, post=p, content="hi", moderation_status="APPROVED")
        with self.assertNumQueries(2):
            post_selector.post_list(self.u)

    def test_rejected_and_pending_hidden_from_others(self):
        Post.objects.create(user=self.u, title="bad", content="c", moderation_status="REJECTED")
        Post.objects.create(user=self.u, title="wait", content="c", moderation_status="PENDING")
        other = User.objects.create_user("b@test.local", "pw123456", name="Bob")
        self.assertEqual(post_selector.post_list(other), [])
        self.assertEqual([p["title"] for p in post_selector.post_list(self.u)], ["wait"])

    def test_like_toggle_counts_once(self):
        p = Post.objects.create(user=self.u, title="t", content="c", moderation_status="APPROVED")
        url = f"/api/community/posts/{p.id}/like/"
        self.assertEqual(self.client.post(url).json()["data"], {"liked": True, "likes_count": 1})
        self.assertEqual(self.client.post(url).json()["data"], {"liked": False, "likes_count": 0})

    def test_comment_and_xss_escaped(self):
        p = Post.objects.create(user=self.u, title="t", content="<script>alert(1)</script> http://x.y", moderation_status="APPROVED")
        r = self.client.post(f"/api/community/posts/{p.id}/comments/", {"content": "ok"}, content_type="application/json")
        self.assertEqual(r.status_code, 201)
        page = self.client.get(f"/community/{p.id}/").content.decode()
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("&lt;script&gt;", page)
        self.assertIn('rel="noopener noreferrer nofollow"', page)

    def test_pages_render(self):
        self.assertEqual(self.client.get("/community/").status_code, 200)


@override_settings(COMMUNITY_STORAGE_DIR=TMP, DEEPSEEK_API_KEY="k")
class ModerationTests(TestCase):
    def setUp(self):
        self.u = User.objects.create_user("m@test.local", "pw123456", name="Mod")
        self.client.force_login(self.u)

    def _mock(self, payload):
        from unittest import mock
        resp = mock.Mock(status_code=200)
        resp.json.return_value = {"choices": [{"message": {"content": payload}}]}
        return mock.patch("community.tasks.requests.post", return_value=resp)

    def test_rewritten_keeps_original(self):
        with self._mock('{"status":"REWRITTEN","clean_title":"สุภาพ","clean_content":"เนื้อหาสุภาพ","reason":"r"}'):
            r = self.client.post("/api/community/posts/", {"title": "หยาบ", "content": "หยาบมาก"})
        self.assertEqual(r.json()["data"]["status"], "REWRITTEN")
        p = Post.objects.get()
        self.assertEqual((p.title, p.content, p.original_content), ("สุภาพ", "เนื้อหาสุภาพ", "หยาบมาก"))

    def test_rejected_is_hidden(self):
        with self._mock('{"status":"REJECTED","clean_title":"","clean_content":"","reason":"ร้ายแรง"}'):
            r = self.client.post("/api/community/posts/", {"title": "x", "content": "y"})
        self.assertEqual(r.json()["data"]["status"], "REJECTED")
        self.assertEqual(post_selector.post_list(self.u), [])

    def test_api_failure_fails_open(self):
        from unittest import mock
        with mock.patch("community.tasks.requests.post", side_effect=RuntimeError("down")):
            r = self.client.post("/api/community/posts/", {"title": "x", "content": "y"})
        self.assertEqual(r.json()["data"]["status"], "APPROVED")
