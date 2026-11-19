"""Links that leave a RYU Network site.

* back to the main RyuClass site (sign-up, free lessons, ...) carry UTM tags, so sales can be traced to the domain
* to a sibling network site use its real domain, or `?site=<key>` while previewing on the main host
"""
from urllib.parse import urlencode

from django.conf import settings

from microsites import registry


def main_url(site, path="/", **params):
    """Absolute URL on the main RyuClass site, tagged with where the visitor came from."""
    params = {k: v for k, v in params.items() if v not in (None, "")}
    params.update(utm_source=site.host, utm_medium="ryu_network", utm_campaign=site.key)
    return f"{settings.SITE_URL.rstrip('/')}{path}?{urlencode(params)}"


def register_url(site, level=None):
    return main_url(site, "/", auth="register", level=level)


def sibling_url(target, preview=False):
    return f"/?site={target.key}" if preview else target.url


def network(current=None, preview=False):
    """Cards for the 'RYU Network' footer / hub: every site except the current one."""
    return [{"site": s, "href": sibling_url(s, preview), "current": s == current} for s in registry.SITES]
