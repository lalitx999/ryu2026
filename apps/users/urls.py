from django.urls import path

from . import views

app_name = "users"
urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register_view, name="register"),
    path("verify-email/", views.verify_email_view, name="verify_email"),
    path("resend-verification/", views.resend_verification_view, name="resend_verification"),
    path("reset-password/", views.reset_password_view, name="reset_password"),
    path("profile/", views.profile_view, name="profile"),
]
