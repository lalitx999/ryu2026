from django.urls import path

from . import views

app_name = "community"
urlpatterns = [
    path("posts/", views.posts, name="posts"),
    path("posts/<int:post_id>/like/", views.like, name="like"),
    path("posts/<int:post_id>/comments/", views.comment, name="comment"),
    path("moderation/<str:task_id>/", views.moderation_result, name="moderation"),
]
