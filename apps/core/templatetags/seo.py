from django import template
from django.utils.safestring import mark_safe

from portal import seo

register = template.Library()


@register.simple_tag
def jsonld():
    """The three schema.org blocks (organisation, course list, FAQ) as inline JSON-LD."""
    return mark_safe("".join(f'<script type="application/ld+json">{seo.dumps_safe(b)}</script>' for b in seo.structured_data()))
