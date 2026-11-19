"""Serve each RYU Network domain from this same Django project.

A request whose Host is one of the registry domains gets `request.urlconf = microsites.site_urls`, so
"/" on คันจิ.online is that site's own page (no redirect to ryusosense).  Every other host keeps
the main RyuClass URLs untouched.

Preview before DNS points here: `?site=<key>` sets a cookie (DEBUG, or a signed-in staff user) and
the main domain then renders that microsite; `?site=off` goes back.  Preview pages are noindex.
"""
from django.conf import settings
from django.http import HttpResponseRedirect

from . import registry

PREVIEW_COOKIE = "ryu_site_preview"
SITE_URLCONF = "microsites.site_urls"


def _can_preview(request):
    if settings.DEBUG:
        return True
    user = getattr(request, "user", None)
    return bool(user and user.is_authenticated and user.is_staff)


class MicrositeMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.microsite = registry.lookup(request.get_host())
        request.microsite_preview = False

        if request.microsite is None and _can_preview(request):
            wanted = request.GET.get("site")
            if wanted is not None:
                # strip ?site= from the URL and remember the choice in a cookie
                query = request.GET.copy()
                query.pop("site")
                target = request.path + (f"?{query.urlencode()}" if query else "")
                resp = HttpResponseRedirect(target)
                if wanted in registry.BY_KEY:
                    resp.set_cookie(PREVIEW_COOKIE, wanted, max_age=60 * 60 * 8, samesite="Lax", httponly=True)
                else:
                    resp.delete_cookie(PREVIEW_COOKIE)
                return resp
            preview = registry.BY_KEY.get(request.COOKIES.get(PREVIEW_COOKIE, ""))
            if preview is not None:
                request.microsite, request.microsite_preview = preview, True

        if request.microsite is not None:
            request.urlconf = SITE_URLCONF
        return self.get_response(request)
