"""Per-domain SEO: each network site is its own website to search engines (own canonical, robots, sitemap, JSON-LD)."""
import json

from django.conf import settings

ORG_NAME = "RYU CLASS"


def canonical(site):
    return site.url


def structured_data(site, faq=None):
    main = settings.SITE_URL.rstrip("/")
    blocks = [{
        "@context": "https://schema.org", "@type": "WebSite", "name": site.name, "url": site.url,
        "description": site.description, "inLanguage": "th",
        "publisher": {"@type": "EducationalOrganization", "name": ORG_NAME, "url": main},
    }]
    if faq:
        blocks.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]})
    return [json.dumps(b, ensure_ascii=False).replace("<", "\\u003c") for b in blocks]


def robots_txt(site):
    return "\n".join(["User-agent: *", "Allow: /", "", f"Sitemap: {site.url}sitemap.xml", ""])


def sitemap_xml(site):
    return ('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            f"<url><loc>{site.url}</loc><changefreq>weekly</changefreq><priority>1.0</priority></url></urlset>")
