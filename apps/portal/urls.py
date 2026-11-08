from django.urls import path, re_path
from django.views.generic import RedirectView

from . import views

app_name = "portal"
urlpatterns = [
    path("", views.home, name="home"),
    path("guide/", views.guide, name="guide"),
    path("library/", views.library, name="library"),
    path("ryutube/", views.ryutube, name="ryutube"),
    path("courses/<int:course_id>/", views.course_page, name="course"),
    path("salepage/", views.salepage, name="salepage"),
    path("free-course/", RedirectView.as_view(pattern_name="portal:ryutube", permanent=True)),
    path("auth/register/", views.register_redirect),
    path("register/", views.register_redirect),
    path("robots.txt", views.robots_txt, name="robots"),
    path("sitemap.xml", views.sitemap_xml, name="sitemap"),
    path("manifest.json", views.manifest_json, name="manifest"),
    path("sw.js", views.service_worker, name="sw"),
    re_path(r"^(?P<name>llms?(?:-full)?)\.txt$", views.llms_txt, name="llms"),
]
