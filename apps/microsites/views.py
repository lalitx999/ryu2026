"""Pages of the RYU Network domains.  Each domain is one page; views only gather data and render."""
from django.conf import settings
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.templatetags.static import static

from microsites import content, registry
from microsites.selectors import sales_selector
from microsites.services import links, seo


def _site(request):
    site = getattr(request, "microsite", None)
    if site is None:  # only reachable through MicrositeMiddleware
        raise Http404
    return site


def _base_context(request, site, faq=None):
    preview = request.microsite_preview
    return {
        "site": site,
        "preview": preview,
        "canonical": seo.canonical(site),
        "jsonld": seo.structured_data(site, faq),
        "network": links.network(site, preview),
        "main_site_url": links.main_url(site),
        "register_url": links.register_url(site),
        "faq": faq or [],
    }


def _sales_context(request, site):
    pricing = sales_selector.pricing()
    level_links = {lvl["level"]: links.register_url(site, lvl["level"]) for lvl in content.LEVELS}
    levels = [{**lvl, "register": level_links[lvl["level"]], "price": pricing["by_level"].get(lvl["level"])}
              for lvl in content.LEVELS]
    return {"pricing": pricing, "levels": levels, "included": content.INCLUDED, "how_steps": content.HOW_STEPS,
            "lifetime": content.LIFETIME, "free_trial_url": links.main_url(site, "/ryutube/")}


def _learn(request, site):
    return {**_base_context(request, site, content.LEARN_FAQ), **_sales_context(request, site)}


def _japanese(request, site):
    preview = request.microsite_preview
    path = [{"site": registry.BY_KEY[key], "href": links.sibling_url(registry.BY_KEY[key], preview), "title": t, "text": d}
            for key, t, d in content.FREE_PATH]
    return {**_base_context(request, site, content.JAPANESE_FAQ), **_sales_context(request, site),
            "goals": content.GOALS, "myths": content.MYTHS, "free_path": path,
            "course_site": links.sibling_url(registry.BY_KEY["learn"], preview)}


def _ryu(request, site):
    return {**_base_context(request, site, content.RYU_FAQ), **_sales_context(request, site),
            "style": content.TEACHING_STYLE, "videos": content.VIDEOS, "socials": content.SOCIALS}


SALES_PAGES = {"learn": _learn, "japanese": _japanese, "ryu": _ryu}


def site_home(request):
    site = _site(request)
    builder = SALES_PAGES.get(site.key) if site.live else None
    if builder is None:
        return render(request, "microsites/soon.html", _base_context(request, site))
    return render(request, f"microsites/{site.key}.html", builder(request, site))


def robots_txt(request):
    return HttpResponse(seo.robots_txt(_site(request)), content_type="text/plain; charset=utf-8")


def sitemap_xml(request):
    return HttpResponse(seo.sitemap_xml(_site(request)), content_type="application/xml; charset=utf-8")


def favicon(request):
    return HttpResponseRedirect(static("favicon.ico"))


def not_found(request, exception=None):
    site = getattr(request, "microsite", None)
    if site is None:
        return HttpResponse("Not found", status=404)
    return render(request, "microsites/404.html", _base_context(request, site), status=404)
