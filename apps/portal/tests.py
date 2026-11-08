import json

from django.test import TestCase

from core import testing  # noqa: F401  (py3.14 template-copy shim)
from courses.models import Course
from portal import seo


class MarketingPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        for i, (lvl, m, s, y, life) in enumerate([("N5", 1000, 5000, 9000, 10000), ("N4", 1250, 6500, 12000, 20000)], start=1):
            Course.objects.create(id=i, title=f"คอร์ส {lvl}", slug=lvl, level=lvl, sort_order=i, price=m, price_180=s,
                                  price_365=y, price_lifetime=life)
        Course.objects.create(id=9, title="inactive", slug="h", level="N1", price=7777, is_active=False)

    def test_salepage_prices_come_from_db(self):
        with self.assertNumQueries(1):
            html = self.client.get("/salepage/").content.decode()
        self.assertIn("9,000 ฿", html)
        self.assertIn("ประหยัด 3,000", html)         # 12 x 1,000 - 9,000
        self.assertIn("เรียน N5-N4", html)
        self.assertNotIn("7,777", html)   # inactive course is not listed

    def test_register_redirect_keeps_valid_level_only(self):
        self.assertEqual(self.client.get("/auth/register/?level=N3")["Location"], "/?auth=register&level=N3")
        self.assertEqual(self.client.get("/register/?level=<x>")["Location"], "/?auth=register")
        self.assertEqual(self.client.get("/free-course/")["Location"], "/ryutube/")

    def test_robots_sitemap_manifest_sw_llms(self):
        robots = self.client.get("/robots.txt")
        self.assertIn("Disallow: /admin-panel/", robots.content.decode())
        self.assertIn("Sitemap:", robots.content.decode())
        self.assertIn("<loc>", self.client.get("/sitemap.xml").content.decode())
        m = self.client.get("/manifest.json").json()
        self.assertEqual((m["short_name"], len(m["icons"])), ("Ryuclass", 8))
        sw = self.client.get("/sw.js")
        self.assertEqual(sw["Service-Worker-Allowed"], "/")
        self.assertEqual(self.client.get("/llms.txt").status_code, 200)
        self.assertEqual(self.client.get("/llm-full.txt").status_code, 200)
        self.assertEqual(self.client.get("/other.txt").status_code, 404)

    def test_jsonld_is_valid_and_script_safe(self):
        blocks = seo.structured_data()
        self.assertEqual([b["@type"] for b in blocks], ["EducationalOrganization", "ItemList", "FAQPage"])
        self.assertNotIn("<", seo.dumps_safe({"x": "</script><script>alert(1)</script>"}))
        html = self.client.get("/salepage/").content.decode()
        self.assertEqual(html.count('application/ld+json'), 3)
        payload = html.split('<script type="application/ld+json">')[1].split("</script>")[0]
        self.assertEqual(json.loads(payload)["@type"], "EducationalOrganization")

    def test_home_has_banner_and_manifest_link(self):
        html = self.client.get("/").content.decode()
        self.assertIn("halloweenModal", html)
        self.assertIn('rel="manifest"', html)
