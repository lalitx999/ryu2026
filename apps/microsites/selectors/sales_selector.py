"""Read-only data the sales sites need (live prices from the course table)."""
from courses.selectors import course_selector


def pricing():
    """Live price rows (one query) plus the cheapest monthly price for 'from ฿X / month' headlines.
    Once the all-access plan is on sale `plan` is set, `rows` is empty and the headline is the plan's monthly price."""
    plan = course_selector.plan()
    rows = course_selector.price_table()
    monthly = [r["monthly"] for r in rows if r["monthly"]]
    from_monthly = plan["monthly"] if plan else (min(monthly) if monthly else None)
    return {"plan": plan, "rows": rows, "from_monthly": from_monthly,
            "by_level": {r["level"]: r for r in rows}}
