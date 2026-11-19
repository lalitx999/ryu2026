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
