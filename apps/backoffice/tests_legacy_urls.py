from core import testing  # noqa: F401  (py3.14 template-copy shim)
from django.test import TestCase


class LegacyAdminUrlTests(TestCase):
    def test_old_admin_urls_redirect_to_admin_panel(self):
        for old, new in {"/admin/login": "/admin-panel/login/", "/admin/login/": "/admin-panel/login/",
                         "/admin/": "/admin-panel/", "/admin": "/admin-panel/", "/admin/payments": "/admin-panel/payments/",
                         "/admin/users/?page=2": "/admin-panel/users/?page=2"}.items():
            r = self.client.get(old)
            self.assertEqual((r.status_code, r["Location"]), (302, new), old)

    def test_login_page_itself_opens(self):
        self.assertEqual(self.client.get("/admin-panel/login/").status_code, 200)
