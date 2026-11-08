from django.urls import path

app_name = "community_pages"

from . import views

urlpatterns = [
    path("", views.forum_page, name="forum"),
    path("<int:post_id>/", views.post_page, name="post"),
]
