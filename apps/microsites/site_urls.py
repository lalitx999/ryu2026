"""URLconf used for every RYU Network domain (picked per request by MicrositeMiddleware)."""
from django.urls import path
from . import views

urlpatterns = [
    path("", views.site_home, name="microsite_home"),
    path("robots.txt", views.robots_txt, name="microsite_robots"),
    path("sitemap.xml", views.sitemap_xml, name="microsite_sitemap"),
    path("favicon.ico", views.favicon, name="microsite_favicon"),
]

handler404 = "microsites.views.not_found"
