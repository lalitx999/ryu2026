from django.urls import path

from . import views

app_name = "courses"
urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("free-trial/", views.free_trial, name="free_trial"),
    path("<int:course_id>/", views.course_detail, name="detail"),
    path("save-progress/", views.save_progress, name="save_progress"),
    path("study-calendar/", views.study_calendar, name="study_calendar"),
    path("notes/<int:lesson_id>/", views.note, name="note_get"),
    path("notes/save/", views.note, name="note_save"),
]
