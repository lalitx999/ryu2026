from django.urls import path

from . import views

app_name = "support"
urlpatterns = [
    path("chat/", views.chat_send, name="chat"),
    path("chat/<str:task_id>/", views.chat_result, name="chat_result"),
]
