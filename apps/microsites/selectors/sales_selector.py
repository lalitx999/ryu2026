"""Read-only data the sales sites need (live prices from the course table)."""
from courses.selectors import course_selector


def pricing():
    """Live price rows (one query) plus the cheapest monthly price for 'from ฿X / month' headlines."""
    rows = course_selector.price_table()
    monthly = [r["monthly"] for r in rows if r["monthly"]]
    return {"rows": rows, "from_monthly": min(monthly) if monthly else None,
            "by_level": {r["level"]: r for r in rows}}
