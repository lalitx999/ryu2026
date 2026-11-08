from django.urls import path

from . import araigogu_views as v

app_name = "araigogu"
urlpatterns = [
    path("chat/", v.chat, name="chat"),
    path("chat/<str:task_id>/", v.result, name="result"),
    path("history/", v.history, name="history"),
    path("sessions/<str:session_id>/", v.session_detail, name="session"),
]
