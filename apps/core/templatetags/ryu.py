import re

from django import template

register = template.Library()

LEVELS = {1: "N5", 2: "N4", 3: "N3", 4: "N2", 5: "N1"}


@register.filter
def baht(value):
    try:
        return f"{float(value):,.0f}"
    except (TypeError, ValueError):
        return value


@register.filter
def baht2(value):
    try:
        return f"{float(value):,.2f}"
    except (TypeError, ValueError):
        return value


@register.filter
def level_code(course):
    """JLPT level badge: title wins, falls back to the stored level / id (same as the old UI)."""
    match = re.search(r"N[1-5]", getattr(course, "title", "") or "", re.I)
    if match:
        return match.group(0).upper()
    return getattr(course, "level", None) or LEVELS.get(getattr(course, "id", 0), "N5")


@register.filter
def minutes(seconds):
    try:
        return int(seconds) // 60
    except (TypeError, ValueError):
        return 0


@register.filter
def get_item(mapping, key):
    try:
        return mapping.get(key)
    except AttributeError:
        return None

