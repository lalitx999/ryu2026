from django.contrib.auth.decorators import user_passes_test

from .http import is_admin_user

# Page-level guard for the custom admin dashboard (rule #4); redirects non-admins to the desktop.
admin_required = user_passes_test(is_admin_user, login_url="/admin-panel/login/")
