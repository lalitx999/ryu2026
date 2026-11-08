from django.urls import path

from . import views

app_name = "quizzes"
urlpatterns = [
    path("lesson/<int:lesson_id>/", views.quiz_detail, name="detail"),
    path("submit/", views.submit, name="submit"),
]
