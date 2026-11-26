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


@override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver", *registry.all_hosts()], SITE_URL="https://www.ryusosense.online",
                   **testing.LEGACY_PRICING)
class MicrositeRoutingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        for i, (lvl, m) in enumerate([("N5", 1000), ("N4", 1250)], start=1):
            Course.objects.create(id=i, title=lvl, slug=lvl, level=lvl, sort_order=i, price=m, price_180=m * 5,
                                  price_365=m * 9, price_lifetime=10000 * i)

    def test_registry_hosts_are_punycode_and_unique(self):
        self.assertEqual(len(registry.SITES), 8)
        self.assertEqual(len({s.host for s in registry.SITES}), 7)   # kana shares คันจิ.online
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

    def test_all_sites_live_and_network_footer_links_siblings(self):
        self.assertTrue(all(s.live for s in registry.SITES))     # all 8 phases shipped: no "coming soon" page left
        html = self.client.get("/", HTTP_HOST=KANJI).content.decode()
        self.assertNotIn("เร็ว ๆ นี้", html)
        for site in registry.SITES:
            self.assertIn(site.url, html)                          # footer links every network domain
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
            html = self.client.get("/kana/", HTTP_HOST=host).content.decode()
        self.assertEqual(html.count('class="kn-cell"'), 208)          # 104 sounds x hiragana + katakana
        self.assertIn('data-key="きゃ"', html)
        self.assertIn(">キャ<", html)                                 # katakana derived from hiragana
        self.assertIn('id="kana-data"', html)
        self.assertIn(registry.BY_KEY["kanji"].url, html)            # next step: คันจิ.online
        self.assertNotIn("เร็ว ๆ นี้</span>\n    <h1", html)

    def test_kana_lives_under_the_kanji_domain(self):
        kana, kanji = registry.BY_KEY["kana"], registry.BY_KEY["kanji"]
        self.assertEqual(kana.host, kanji.host)
        self.assertEqual(kana.url, "https://xn--42ci4c5era.online/kana/")
        self.assertNotIn("xn--12cyzbhxr5bc5a4bpb4b5b4qc.online", registry.all_hosts())   # อักษรภาษาญี่ปุ่น.online is not ours
        self.assertIs(registry.lookup(kanji.host), kanji)
        html = self.client.get("/kana/", HTTP_HOST=kanji.host).content.decode()
        self.assertIn('href="https://xn--42ci4c5era.online/kana/"', html)              # canonical
        self.assertEqual(self.client.get("/kana/", HTTP_HOST=registry.BY_KEY["dictionary"].host).status_code, 404)


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


@override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver", *registry.all_hosts()], SITE_URL="https://www.ryusosense.online",
                   CELERY_TASK_ALWAYS_EAGER=True, RYU_AI_PER_IP_HOUR=50, RYU_AI_DAILY_LIMIT=100,
                   CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "tr-tests"}})
class TranslatorSiteTests(TestCase):
    HOST = registry.BY_KEY["translator"].host
    ANSWER = {"translation": "いつも助けてくれてありがとう。", "reading": "いつもたすけてくれてありがとう。",
              "alternatives": [{"style": "business", "text": "いつもお世話になっております。", "reading": "いつもおせわになっております。"},
                               {"style": "polite", "text": "same style must be dropped", "reading": ""}],
              "notes": ["ข้อสังเกต"], "words": [{"word": "助ける", "reading": "たすける", "th": "ช่วยเหลือ"}]}

    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    def post(self, body):
        return self.client.post("/api/translate/", body, content_type="application/json", HTTP_HOST=self.HOST)

    def fake(self, data):
        from unittest import mock
        from support.ai import Completion
        return mock.patch("support.ai.complete", return_value=Completion(json.dumps(data, ensure_ascii=False), "Fake (test)"))

    def test_page_and_translation_is_cached(self):
        html = self.client.get("/", HTTP_HOST=self.HOST).content.decode()
        self.assertIn('data-api="/api/translate/"', html)
        self.assertEqual(EMOJI.findall(html), [])
        with self.fake(self.ANSWER) as m:
            r1 = self.post({"text": "ขอบคุณที่ช่วยเหลือเสมอนะ", "direction": "auto", "style": "polite"}).json()["data"]
            r2 = self.post({"text": "ขอบคุณที่ช่วยเหลือเสมอนะ", "direction": "auto", "style": "polite"}).json()["data"]
        self.assertEqual(m.call_count, 1)                                   # second request served from the cache
        res = r1["result"]
        self.assertEqual((r1["state"], res["direction"], res["translation"]), ("done", "th2ja", "いつも助けてくれてありがとう。"))
        self.assertEqual([a["style"] for a in res["alternatives"]], ["business"])   # same-style alternative dropped
        self.assertTrue(res["reading_th"])
        self.assertEqual(r2["result"]["translation"], res["translation"])
        poll = self.client.get(f"/api/translate/{r1['key']}/", HTTP_HOST=self.HOST).json()["data"]
        self.assertEqual(poll["state"], "done")

    def test_japanese_input_detected_and_limits(self):
        with self.fake({"translation": "ขอบคุณสำหรับวันนี้", "reading": "おつかれさまでした"}):
            res = self.post({"text": "お疲れ様でした"}).json()["data"]["result"]
        self.assertEqual(res["direction"], "ja2th")
        self.assertEqual(self.post({"text": "   "}).status_code, 400)
        self.assertEqual(self.post({"text": "ก" * 501}).status_code, 400)
        with override_settings(RYU_AI_PER_IP_HOUR=0), self.fake(self.ANSWER):
            self.assertEqual(self.post({"text": "ข้อความใหม่"}).status_code, 429)

    def test_purge_old_rows(self):
        from datetime import timedelta
        from django.utils import timezone
        from microsites.models import TranslationCache
        from microsites.services import translator
        old = TranslationCache.objects.create(key="a" * 64, direction="th2ja", style="polite", result={"translation": "x"})
        TranslationCache.objects.filter(pk=old.pk).update(created_at=timezone.now() - timedelta(days=31))
        TranslationCache.objects.create(key="b" * 64, direction="th2ja", style="polite", result={"translation": "y"})
        self.assertEqual(translator.purge(30), 1)


@override_settings(DEBUG=False, ALLOWED_HOSTS=["testserver", *registry.all_hosts()], SITE_URL="https://www.ryusosense.online",
                   CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache", "LOCATION": "jlpt-tests"}})
class JlptSiteTests(TestCase):
    HOST = registry.BY_KEY["jlpt"].host

    @classmethod
    def setUpTestData(cls):
        from microsites.models import ExamItem
        rows = []
        for lv in ("N5", "N4"):
            for sec in ("vocab", "kanji", "grammar"):
                for k in range(9):
                    rows.append(ExamItem(level=lv, section=sec, stem=f"{lv}{sec}{k} 【学校】に行きます。", choices=["a", "b", "c", "d"], answer=k % 4, explanation="ไทย"))
            for g in range(3):
                for k in range(2):
                    rows.append(ExamItem(level=lv, section="reading", group=f"r{lv}{g}", passage="本文", stem=f"q{k}", choices=["a", "b", "c", "d"], answer=1))
                rows.append(ExamItem(level=lv, section="listening", group=f"l{lv}{g}", passage="男：こんにちは\n女：はい", stem="何？", choices=["a", "b", "c", "d"], answer=2))
        ExamItem.objects.bulk_create(rows)
        ExamItem.objects.filter(stem__startswith="N5vocab0").update(status=ExamItem.HIDDEN)
        cls.staff = User.objects.create(email="j@test.local", role="admin", is_staff=True)

    def get(self, path):
        return self.client.get(path, HTTP_HOST=self.HOST)

    def exam(self, path):
        html = self.get(path).content.decode()
        return html, json.loads(html.split('id="exam-data" type="application/json">')[1].split("</script>")[0])

    def test_home_lists_levels_and_disclaimer(self):
        html = self.get("/").content.decode()
        self.assertIn("ไม่ใช่ข้อสอบทางการ", html)
        self.assertIn('href="/test/n5/"', html)
        self.assertNotIn('href="/test/n1/"', html)              # N1 has no questions yet: not offered
        self.assertEqual(EMOJI.findall(html), [])

    def test_mock_has_every_section_and_skips_hidden(self):
        html, data = self.exam("/test/n5/")
        sections = {i["section"] for i in data["items"]}
        self.assertEqual(sections, {"vocab", "kanji", "grammar", "reading", "listening"})
        self.assertEqual(sum(1 for i in data["items"] if i["section"] == "vocab"), 8)
        self.assertEqual(sum(1 for i in data["items"] if i["section"] == "reading"), 4)        # 2 passages x 2 questions
        self.assertFalse(any(i["stem"].startswith("N5vocab0") for i in data["items"]))
        self.assertIn("<u>学校</u>", next(i["stem"] for i in data["items"] if i["section"] == "kanji"))
        self.assertEqual((data["minutes"], data["level"]), (40, "N5"))
        self.assertEqual(self.get("/test/n9/").status_code, 404)

    def test_placement_mixes_levels(self):
        _, data = self.exam("/test/placement/")
        self.assertEqual({i["level"] for i in data["items"]}, {"N5", "N4"})
        self.assertEqual(len(data["items"]), 10)

    def test_report_counts_once_per_visitor(self):
        from microsites.models import ExamItem
        q = ExamItem.objects.filter(level="N5", section="kanji").first()
        for _ in range(2):
            self.client.post(f"/api/exam/report/{q.id}/", HTTP_HOST=self.HOST)
        q.refresh_from_db()
        self.assertEqual(q.reports, 1)

    def test_admin_approve_validates_and_resets_reports(self):
        from microsites.models import ExamItem
        q = ExamItem.objects.filter(level="N4", section="grammar").first()
        ExamItem.objects.filter(pk=q.pk).update(reports=3)
        self.client.force_login(self.staff)
        url = f"/admin-panel/exam/{q.id}/save/"
        bad = self.client.post(url, {"action": "approve", "stem": "x", "choices": ["a", "a", "b", "c"], "answer": 0}, content_type="application/json")
        self.assertEqual(bad.status_code, 400)
        r = self.client.post(url, {"action": "approve", "stem": "ใหม่", "choices": ["w", "x", "y", "z"], "answer": 3, "explanation": "e"},
                             content_type="application/json")
        self.assertEqual(r.json()["data"]["status"], "approved")
        q.refresh_from_db()
        self.assertEqual((q.answer, q.reports, q.reviewed_by), (3, 0, self.staff))
        self.client.post(url, {"action": "hide"}, content_type="application/json")
        q.refresh_from_db()
        self.assertEqual(q.status, "hidden")
        self.assertIn("ตรวจข้อสอบจำลอง", self.client.get("/admin-panel/exam/?status=reported").content.decode())

    def test_ai_build_keeps_only_verified_and_shuffles(self):
        from unittest import mock
        from microsites.models import ExamItem
        from microsites.services import exam_ai
        from support.ai import Completion
        gen = json.dumps([{"stem": f"s{k}（　　）", "choices": ["right", "w1", "w2", "w3"], "answer": 0, "explanation": "e"} for k in range(3)])
        before = ExamItem.objects.count()
        calls = []

        def fake(messages, **kw):
            calls.append(1)
            if len(calls) == 1:
                return Completion(gen, "Fake")
            # the checker answers the first two correctly (wherever "right" was shuffled to) and the third wrongly
            prompt = messages[-1]["content"]
            out = []
            for k, block in enumerate(prompt.split("ข้อ ")[1:]):
                opts = [line.split(") ", 1)[1] for line in block.splitlines()[1:] if ") " in line]
                idx = opts.index("right")
                out.append({"q": k, "answer": idx if k < 2 else (idx + 1) % 4})
            return Completion(json.dumps(out), "Fake")

        with mock.patch("support.ai.complete", side_effect=fake):
            made, kept = exam_ai.build("N3", "vocab", 3)
        self.assertEqual((made, kept, ExamItem.objects.count() - before), (3, 2, 2))
        for q in ExamItem.objects.filter(level="N3"):
            self.assertEqual(q.choices[q.answer], "right")
