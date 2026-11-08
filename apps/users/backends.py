from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):
    """Case-insensitive email login.  User.check_password() also upgrades legacy PHP bcrypt hashes."""

    def authenticate(self, request, email=None, password=None, **kwargs):
        email = (email or kwargs.get("username") or "").strip()
        if not email or not password:
            return None
        user = get_user_model().objects.filter(email__iexact=email).first()
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
