import json
import re

from django.test import TestCase, override_settings

from core import testing  # noqa: F401  (py3.14 template-copy shim)
from courses.models import Course
from microsites import registry
from microsites.middleware import PREVIEW_COOKIE
from users.models import User

KANJI = "คันจิ.online".encode("idna").decode()
LEARN = registry.BY_KEY["learn"].host
JAPANESE = registry.BY_KEY["japanese"].host
RYU = registry.BY_KEY["ryu"].host
# emoji / pictographs (arrows such as → stay allowed as plain text)
EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\u231A-\u23FF\u25A0-\u25FF\uFE0F\u200D\u3297\u3299]")


@override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver", *registry.all_hosts()], SITE_URL="https://www.ryusosense.online")
class MicrositeRoutingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        for i, (lvl, m) in enumerate([("N5", 1000), ("N4", 1250)], start=1):
            Course.objects.create(id=i, title=lvl, slug=lvl, level=lvl, sort_order=i, price=m, price_180=m * 5,
                                  price_365=m * 9, price_lifetime=10000 * i)

    def test_registry_hosts_are_punycode_and_unique(self):
        self.assertEqual(len(registry.SITES), 8)
        self.assertEqual(len({s.host for s in registry.SITES}), 8)
        self.assertTrue(all(s.host.isascii() and s.host.endswith(".online") for s in registry.SITES))
        self.assertEqual(registry.lookup("คันจิ.online").key, "kanji")       # unicode Host
        self.assertEqual(registry.lookup(f"WWW.{KANJI}:443").key, "kanji")  # case / www / port
        self.assertIsNone(registry.lookup("www.ryusosense.online"))

    def test_each_sales_domain_renders_its_own_page_with_live_prices(self):
        pages = {}
        for host in (LEARN, JAPANESE, RYU):
            with self.assertNumQueries(1):   # the price table only
                resp = self.client.get("/", HTTP_HOST=host)
            self.assertEqual(resp.status_code, 200)
            html = resp.content.decode()
            self.assertIn(f'<link rel="canonical" href="https://{host}/">', html)
            self.assertIn("utm_source=" + host, html)          # sign-up links are traced back to the domain
            self.assertIn("https://www.ryusosense.online/?auth=register", html)
            self.assertNotIn("noindex", html)
            pages[host] = html
        self.assertIn("เส้นทางจากศูนย์สู่ N1", pages[LEARN])
        self.assertIn("9,000 ฿", pages[LEARN])                   # 12-month N5 price from the DB
        self.assertIn("อยากใช้ภาษาญี่ปุ่นทำอะไร?", pages[JAPANESE])
        self.assertIn("เริ่มต้นเดือนละ ฿1,000", pages[JAPANESE])
        self.assertIn("ทำไมนักเรียนชอบเรียนกับพี่ริว", pages[RYU])
        titles = {p.split("<title>")[1].split("</title>")[0] for p in pages.values()}
        self.assertEqual(len(titles), 3)                         # no duplicate content between the three

    def test_tool_domain_shows_coming_soon_and_network_links(self):
        html = self.client.get("/", HTTP_HOST=KANJI).content.decode()
        self.assertIn("เร็ว ๆ นี้", html)
        self.assertIn(f"https://{LEARN}/", html)                 # footer links to sibling domains
        self.assertIn('aria-current="page"', html)

    def test_robots_sitemap_and_404_are_per_domain(self):
        self.assertIn(f"Sitemap: https://{KANJI}/sitemap.xml", self.client.get("/robots.txt", HTTP_HOST=KANJI).content.decode())
        self.assertIn(f"<loc>https://{LEARN}/</loc>", self.client.get("/sitemap.xml", HTTP_HOST=LEARN).content.decode())
        resp = self.client.get("/admin-panel/", HTTP_HOST=LEARN)  # main-site URLs do not exist on network domains
        self.assertEqual(resp.status_code, 404)
        self.assertIn("ไม่พบหน้านี้", resp.content.decode())

    def test_main_domain_is_untouched_and_links_to_the_network(self):
        html = self.client.get("/network/").content.decode()
        self.assertIn(f"https://{KANJI}/", html)
        self.assertEqual(self.client.get("/salepage/").status_code, 200)

    def test_preview_only_for_staff_when_debug_is_off(self):
        self.assertEqual(self.client.get("/?site=kanji").status_code, 200)    # anonymous: ignored, normal desktop
        self.assertNotIn(PREVIEW_COOKIE, self.client.cookies)
        staff = User.objects.create(email="s@test.local", role="admin", is_staff=True)
        self.client.force_login(staff)
        resp = self.client.get("/?site=learn")
        self.assertEqual((resp.status_code, resp["Location"]), (302, "/"))
        html = self.client.get("/").content.decode()
        self.assertIn("โหมดพรีวิว", html)
        self.assertIn("noindex", html)
        self.assertIn('href="/?site=kanji"', html)              # sibling links stay inside the preview
        self.client.get("/?site=off")
        self.assertNotIn("โหมดพรีวิว", self.client.get("/").content.decode())

    def test_pages_use_icons_not_emoji(self):
        for site in registry.SITES:
            html = self.client.get("/", HTTP_HOST=site.host).content.decode()
            self.assertEqual(EMOJI.findall(html), [], site.domain)
            self.assertIn('class="ms-ic', html)
        hub = self.client.get("/network/").content.decode()     # the hub's own content (the XP topbar is the legacy look)
        self.assertEqual(EMOJI.findall(hub[hub.index("<main"):hub.index("</main>")]), [])

    def test_kana_site_renders_both_charts_without_db(self):
        host = registry.BY_KEY["kana"].host
        with self.assertNumQueries(0):
            html = self.client.get("/", HTTP_HOST=host).content.decode()
        self.assertEqual(html.count('class="kn-cell"'), 208)          # 104 sounds x hiragana + katakana
        self.assertIn('data-key="きゃ"', html)
        self.assertIn(">キャ<", html)                                 # katakana derived from hiragana
        self.assertIn('id="kana-data"', html)
        self.assertIn(registry.BY_KEY["kanji"].url, html)            # next step: คันจิ.online
        self.assertNotIn("เร็ว ๆ นี้</span>\n    <h1", html)


class KanaDataTests(TestCase):
    def test_chart_shape_and_examples(self):
        from microsites import kana
        self.assertEqual([g["count"] for g in kana.chart("hiragana")], [46, 25, 33])
        self.assertEqual(kana.to_katakana("きょう"), "キョウ")
        basic = [c for c in kana.flat("katakana") if c["group"] == "basic"]
        self.assertEqual(sum(1 for c in basic if "example" in c), 45)  # every basic sound except ヲ


@override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver", *registry.all_hosts()], SITE_URL="https://www.ryusosense.online")
class KanjiSiteTests(TestCase):
    HOST = registry.BY_KEY["kanji"].host

    @classmethod
    def setUpTestData(cls):
        from microsites.models import Kanji
        from microsites.services.kanji_import import import_kanji
        rows = [{"c": "日", "lv": "N5", "sc": 4, "fr": 1, "gr": 1, "on": ["にち", "じつ"], "kun": ["ひ", "-び"], "en": ["day", "sun"], "sp": ["M1 1L2 2"] * 4},
                {"c": "本", "lv": "N5", "sc": 5, "fr": 10, "gr": 1, "on": ["ほん"], "kun": ["もと"], "en": ["book"], "sp": ["M1 1L2 2"] * 5},
                {"c": "議", "lv": "N3", "sc": 20, "fr": 50, "gr": 4, "on": ["ぎ"], "kun": [], "en": ["deliberation"], "sp": []}]
        import_kanji(rows)
        Kanji.objects.filter(char="日").update(th_meaning="วัน, ดวงอาทิตย์", ai_status=Kanji.AI_DRAFT,
                                              examples=[{"word": "毎日", "reading": "まいにち", "th": "ทุกวัน"}])
        cls.staff = User.objects.create(email="k@test.local", role="admin", is_staff=True)

    def get(self, path):
        return self.client.get(path, HTTP_HOST=self.HOST)

    def test_home_level_detail_search_and_sitemap(self):
        home = self.get("/").content.decode()
        self.assertIn('href="/kanji/%E6%97%A5/"', home)
        self.assertIn("วัน, ดวงอาทิตย์", home)
        level = self.get("/level/n5/").content.decode()
        self.assertIn('id="kj-quiz-data"', level)
        self.assertEqual(self.get("/level/n9/").status_code, 404)
        detail = self.get("/kanji/日/").content.decode()
        self.assertIn("ニチ", detail)                       # on reading shown in katakana
        self.assertIn("นิจิ", detail)                       # with an approximate Thai reading
        self.assertIn("ร่างโดย AI", detail)                 # draft label until a teacher approves
        self.assertIn('href="/kanji/%E6%9C%AC/"', detail)   # next kanji in the level
        self.assertEqual(self.get("/kanji/X/").status_code, 404)
        self.assertEqual(self.get("/search/?q=にち").json()["results"][0]["char"], "日")
        self.assertEqual(self.get("/search/?q=ดวงอาทิตย์").json()["results"][0]["char"], "日")
        self.assertEqual(self.get("/search/?q=book").json()["results"][0]["char"], "本")
        sitemap = self.get("/sitemap.xml").content.decode()
        self.assertIn(f"https://{self.HOST}/kanji/%E6%97%A5/", sitemap)
        self.assertEqual(EMOJI.findall(detail), [])

    def test_kanji_paths_do_not_exist_on_other_domains(self):
        self.assertEqual(self.client.get("/kanji/日/", HTTP_HOST=LEARN).status_code, 404)
        self.assertEqual(self.client.get("/credits/", HTTP_HOST=LEARN).status_code, 404)
        self.assertEqual(self.client.get("/credits/", HTTP_HOST=registry.BY_KEY["kana"].host).status_code, 200)

    def test_reimport_keeps_reviewed_thai(self):
        from microsites.models import Kanji
        from microsites.services.kanji_import import import_kanji
        import_kanji([{"c": "日", "lv": "N5", "sc": 4, "fr": 1, "on": ["にち"], "kun": [], "en": ["day"], "sp": []}])
        k = Kanji.objects.get(char="日")
        self.assertEqual((k.th_meaning, k.on_readings), ("วัน, ดวงอาทิตย์", ["にち"]))

    def test_admin_review_approves_and_validates(self):
        from microsites.models import Kanji
        k = Kanji.objects.get(char="日")
        self.client.force_login(self.staff)
        url = f"/admin-panel/kanji/{k.id}/save/"
        bad = self.client.post(url, {"th_meaning": "วัน", "examples": "毎日 | mainichi | ทุกวัน", "approve": True}, content_type="application/json")
        self.assertEqual(bad.status_code, 400)                # reading must be kana
        r = self.client.post(url, {"th_meaning": "วัน", "th_note": "", "examples": "毎日 | まいにち | ทุกวัน", "approve": True}, content_type="application/json")
        self.assertEqual(r.json()["data"]["ai_status"], "approved")
        k.refresh_from_db()
        self.assertEqual((k.reviewed_by, k.examples[0]["reading"]), (self.staff, "まいにち"))
        self.assertIn("ตรวจคันจิ", self.client.get("/admin-panel/kanji/?level=N5").content.decode())
        self.assertNotIn("ร่างโดย AI", self.get("/kanji/日/").content.decode())


class KanaThaiReadingTests(TestCase):
    def test_reading_to_thai(self):
        from microsites import kana
        self.assertEqual([kana.reading_to_thai(r) for r in ("にち", "きょう", "かん", "せん", "ひと.つ")],
                         ["นิจิ", "เคียว", "คัน", "เส็น", "ฮิโทะทสึ"])


@override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver", *registry.all_hosts()], SITE_URL="https://www.ryusosense.online",
                   CELERY_TASK_ALWAYS_EAGER=True, RYU_AI_PER_IP_HOUR=50, RYU_AI_DAILY_LIMIT=100,
                   CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "dict-tests"}})
class DictionarySiteTests(TestCase):
    HOST = registry.BY_KEY["dictionary"].host

    @classmethod
    def setUpTestData(cls):
        from microsites.services.dict_import import import_words
        import_words([
            {"id": 1, "k": ["食べる"], "r": ["たべる"], "s": [{"pos": ["v1", "vt"], "g": ["to eat"], "m": []}], "rk": 0},
            {"id": 2, "k": ["食堂"], "r": ["しょくどう"], "s": [{"pos": ["n"], "g": ["cafeteria", "dining hall"], "m": []}], "rk": 1},
            {"id": 3, "k": [], "r": ["テレビ"], "s": [{"pos": ["n"], "g": ["television", "TV"], "m": []}], "rk": 2},
            {"id": 4, "k": ["劇場"], "r": ["げきじょう"], "s": [{"pos": ["n"], "g": ["theater", "theatre"], "m": []}], "rk": 3},
            {"id": 5, "k": ["美味しい"], "r": ["おいしい"], "s": [{"pos": ["adj-i"], "g": ["delicious", "tasty"], "m": []}], "rk": 4},
        ])

    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    def get(self, path):
        return self.client.get(path, HTTP_HOST=self.HOST)

    def post(self, path, body=None):
        return self.client.post(path, body or {}, content_type="application/json", HTTP_HOST=self.HOST)

    def search(self, q):
        return self.get(f"/api/dict/search/?q={q}").json()

    def test_search_japanese_english_thai(self):
        self.assertEqual(self.search("食べる")["results"][0]["word"], "食べる")
        self.assertEqual(self.search("たべ")["results"][0]["word"], "食べる")            # prefix on reading
        self.assertEqual(self.search("てれび")["results"][0]["word"], "テレビ")            # hiragana finds katakana
        self.assertEqual(self.search("eat")["results"][0]["word"], "食べる")               # whole word before "theater"
        th = self.search("อร่อย")
        self.assertEqual((th["script"], th["results"], th["thai_cached"]), ("th", [], False))

    def _fake_ai(self, text):
        from unittest import mock
        from support.ai import Completion
        return mock.patch("support.ai.complete", return_value=Completion(text, "Fake (test)"))

    def test_word_page_and_ai_explanation_is_written_once(self):
        html = self.get("/word/" + str(self._id(1)) + "/").content.decode()
        self.assertIn("<ruby>食べる<rt>たべる</rt></ruby>", html)
        self.assertIn("กริยากลุ่ม 2", html)                           # Thai part-of-speech label
        self.assertIn("/kanji/%E9%A3%9F/", html)                       # link to คันจิ.online
        self.assertEqual(EMOJI.findall(html), [])
        answer = json.dumps([{"id": self._id(1), "th_gloss": "กิน", "th_explain": "ใช้ทั่วไป",
                              "examples": [{"ja": "ご飯を食べる。", "reading": "ごはんをたべる。", "th": "กินข้าว"},
                                           {"ja": "No kanji here", "reading": "abc", "th": "x"}]}], ensure_ascii=False)
        with self._fake_ai(answer) as m:
            r = self.post(f"/api/dict/word/{self._id(1)}/").json()
            self.post(f"/api/dict/word/{self._id(1)}/")
        self.assertEqual(m.call_count, 1)
        self.assertEqual((r["data"]["th"], len(r["data"]["examples"])), ("กิน", 1))   # invalid example dropped
        self.assertIn(f"/word/{self._id(1)}/", self.get("/sitemap.xml").content.decode())

    def test_thai_lookup_matches_dictionary_and_caches(self):
        answer = json.dumps([{"word": "美味しい", "reading": "おいしい"}, {"word": "旨い", "reading": "うまい"}], ensure_ascii=False)
        with self._fake_ai(answer) as m:
            self.assertEqual(self.post("/api/dict/thai/", {"q": "อร่อย"}).status_code, 200)
            self.post("/api/dict/thai/", {"q": "อร่อย"})
        self.assertEqual(m.call_count, 1)
        res = self.search("อร่อย")
        self.assertEqual((res["thai_cached"], res["results"][0]["word"], res["suggestions"][0]["word"]), (True, "美味しい", "旨い"))
        self.assertEqual(self.post("/api/dict/thai/", {"q": "eat"}).status_code, 400)

    @override_settings(RYU_AI_PER_IP_HOUR=1)
    def test_ai_is_rate_limited_per_visitor(self):
        with self._fake_ai("[]"):
            self.assertEqual(self.post(f"/api/dict/word/{self._id(2)}/").status_code, 200)
            self.assertEqual(self.post(f"/api/dict/word/{self._id(3)}/").status_code, 429)

    def test_dictionary_paths_only_on_dictionary_domain(self):
        self.assertEqual(self.client.get(f"/word/{self._id(1)}/", HTTP_HOST=LEARN).status_code, 404)
        self.assertEqual(self.client.get("/api/dict/search/?q=a", HTTP_HOST=registry.BY_KEY["kanji"].host).status_code, 404)

    @staticmethod
    def _id(jmdict_id):
        from microsites.models import DictEntry
        return DictEntry.objects.get(jmdict_id=jmdict_id).id
