import re

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()
URL_RE = re.compile(r"(https?://[^\s<]+)")


@register.filter
def linkify(value):
    """Escape first, then link URLs: user text can never inject markup."""
    text = escape(value or "")
    text = URL_RE.sub(r'<a href="\1" target="_blank" rel="noopener noreferrer nofollow">\1</a>', text)
    return mark_safe(text.replace("\n", "<br>"))
