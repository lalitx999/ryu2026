"""URLconf used for every RYU Network domain (picked per request by MicrositeMiddleware)."""
from django.urls import path
from . import views

urlpatterns = [
    path("", views.site_home, name="microsite_home"),
    path("robots.txt", views.robots_txt, name="microsite_robots"),
    path("sitemap.xml", views.sitemap_xml, name="microsite_sitemap"),
    path("level/<str:level>/", views.kanji_level, name="kanji_level"),
    path("kanji/<str:char>/", views.kanji_detail, name="kanji_detail"),
    path("search/", views.kanji_search, name="kanji_search"),
    path("word/<int:entry_id>/", views.dict_word, name="dict_word"),
    path("api/dict/search/", views.dict_search, name="dict_search"),
    path("api/dict/word/<int:entry_id>/", views.dict_word_api, name="dict_word_api"),
    path("api/dict/thai/", views.dict_thai, name="dict_thai"),
    path("api/translate/", views.translate_api, name="translate_api"),
    path("api/translate/<str:key>/", views.translate_result, name="translate_result"),
    path("test/<str:kind>/", views.jlpt_test, name="jlpt_test"),
    path("api/exam/report/<int:item_id>/", views.jlpt_report, name="jlpt_report"),
    path("credits/", views.credits, name="microsite_credits"),
    path("favicon.ico", views.favicon, name="microsite_favicon"),
]

handler404 = "microsites.views.not_found"
