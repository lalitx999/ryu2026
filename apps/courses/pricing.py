"""Authoritative course prices, shared by the catalogue and payment endpoint."""
PACKAGES = ((30, 'รายเดือน (30 วัน)', 'price'), (180, '6 เดือน (180 วัน)', 'price_180'),
            (365, 'รายปี (365 วัน)', 'price_365'), (9999, 'ตลอดชีพ', 'price_lifetime'))


def package_prices(course):
    return [{'duration': days, 'label': label, 'price': str(getattr(course, field))}
            for days, label, field in PACKAGES
            if getattr(course, field) is not None and getattr(course, field) > 0]


def package_amount(course, days):
    for duration, _, field in PACKAGES:
        if days == duration:
            value = getattr(course, field)
            if value is not None and value > 0:
                return value
    raise ValueError('แพ็กเกจนี้ยังไม่ได้กำหนดราคาหรือปิดจำหน่าย')
