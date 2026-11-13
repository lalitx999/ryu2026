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



THAI_MONTHS = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]


@register.filter
def thai_date(value):
    """date / ISO string -> '12 ธ.ค. 2569' (Buddhist-era year)."""
    import datetime
    if isinstance(value, str):
        try:
            value = datetime.date.fromisoformat(value[:10])
        except ValueError:
            return value
    if isinstance(value, datetime.datetime):
        value = value.date()
    if not isinstance(value, datetime.date):
        return value
    return f"{value.day} {THAI_MONTHS[value.month - 1]} {value.year + 543}"
