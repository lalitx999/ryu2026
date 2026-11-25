"""Authoritative course prices, shared by the catalogue and payment endpoint.

From settings.SINGLE_PLAN_START (Asia/Bangkok, inclusive) the per-level prices give way to one all-access
plan: monthly / yearly, unlocking N5-N1.  The plan is sold on the N1 course because a higher level already
covers every lower one (AccessService.video_rank_for), so no schema change is needed.  Before that date
everything below behaves exactly as it always did.
"""
from decimal import Decimal

from django.conf import settings
from django.utils import timezone

PACKAGES = ((30, 'รายเดือน (30 วัน)', 'price'), (180, '6 เดือน (180 วัน)', 'price_180'),
            (365, 'รายปี (365 วัน)', 'price_365'), (9999, 'ตลอดชีพ', 'price_lifetime'))

PLAN_LEVEL = 'N1'               # the course the all-access plan is sold on
PLAN_LEVEL_ACCESS = 'N5-N1'     # stored on Payment.level_access for plan purchases
PLAN_LABEL = 'ทุกระดับ (N5–N1)'


def single_plan_active(today=None):
    return (today or timezone.localdate()) >= settings.SINGLE_PLAN_START


def plan_packages():
    """(days, label, price) of the all-access plan."""
    return ((30, 'รายเดือน (30 วัน)', Decimal(settings.SINGLE_PLAN_MONTHLY)),
            (365, 'รายปี (365 วัน)', Decimal(settings.SINGLE_PLAN_YEARLY)))


def plan_summary():
    """Everything a page needs to show the plan."""
    monthly, yearly = (price for _, _, price in plan_packages())
    return {'monthly': monthly, 'yearly': yearly, 'yearly_saving': monthly * 12 - yearly,
            'label': PLAN_LABEL, 'renewal_days': renewal_days()}


def plan_course():
    """The active N1 course (lowest id) that plan purchases are recorded on, or None."""
    from courses.models import Course  # local import: pricing is imported by models' neighbours
    return Course.objects.filter(level=PLAN_LEVEL, is_active=True).order_by('id').first()


def renewal_days():
    """Days a monthly renewal buys: the plan has no bonus days."""
    return 30 if single_plan_active() else 30 + settings.RENEWAL_BONUS_DAYS


def display_price(course):
    """Monthly price shown on a course card / page."""
    return Decimal(settings.SINGLE_PLAN_MONTHLY) if single_plan_active() else course.price


def package_prices(course):
    if single_plan_active():
        return [{'duration': days, 'label': label, 'price': str(price)} for days, label, price in plan_packages()]
    return [{'duration': days, 'label': label, 'price': str(getattr(course, field))}
            for days, label, field in PACKAGES
            if getattr(course, field) is not None and getattr(course, field) > 0]


def package_amount(course, days):
    if single_plan_active():
        for duration, _, price in plan_packages():
            if days == duration:
                return price
        raise ValueError('แพ็กเกจนี้ยังไม่ได้กำหนดราคาหรือปิดจำหน่าย')
    for duration, _, field in PACKAGES:
        if days == duration:
            value = getattr(course, field)
            if value is not None and value > 0:
                return value
    raise ValueError('แพ็กเกจนี้ยังไม่ได้กำหนดราคาหรือปิดจำหน่าย')
