from django.urls import path

from . import views

app_name = "payments"
urlpatterns = [
    path("upload-slip/", views.upload_slip, name="upload_slip"),
    path("slip/<int:payment_id>/", views.slip_image, name="slip"),
]
