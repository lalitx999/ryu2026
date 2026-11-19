from celery import shared_task

from microsites.services import kanji_ai


@shared_task(time_limit=900, soft_time_limit=850)
def draft_kanji_thai(level=None, limit=24):
    """Admin button "สร้างร่าง AI": draft the next `limit` kanji that have no Thai yet."""
    return kanji_ai.draft_pending(level or None, limit)


@shared_task(time_limit=120, soft_time_limit=110)
def explain_word(entry_id):
    from microsites.services import dict_ai
    return dict_ai.explain_one(entry_id)


@shared_task(time_limit=90, soft_time_limit=80)
def thai_lookup(query):
    from microsites.services import dict_ai
    obj = dict_ai.thai_lookup(query)
    return bool(obj)
