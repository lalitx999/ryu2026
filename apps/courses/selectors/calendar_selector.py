from datetime import timedelta

from django.utils import timezone

from courses.models import Progress, StudyActivityLog


def study_calendar(user, year=None, month=None):
    today = timezone.localdate()
    year, month = year or today.year, month or today.month

    # Streaks need every active day; a single values_list per source keeps it to 2 queries.
    days = set(StudyActivityLog.objects.filter(user=user).values_list("date", flat=True))
    days.update(d for d in Progress.objects.filter(user=user, is_completed=True, completed_at__isnull=False)
                .values_list("completed_at__date", flat=True) if d)
    studied_today = today in days
    cursor, current = (today if studied_today else today - timedelta(days=1)), 0
    while cursor in days:
        current += 1
        cursor -= timedelta(days=1)
    longest = run = 0
    prev = None
    for d in sorted(days):
        run = run + 1 if prev and d == prev + timedelta(days=1) else 1
        longest, prev = max(longest, run), d

    activity, minutes_total = {}, 0
    for log in StudyActivityLog.objects.filter(user=user, date__year=year, date__month=month):
        activity[log.date.isoformat()] = {"minutes": log.minutes_spent, "lessons": log.lessons_completed}
        minutes_total += log.minutes_spent
    for p in Progress.objects.filter(user=user, is_completed=True, completed_at__year=year,
                                     completed_at__month=month).only("completed_at", "video_time"):
        key = timezone.localtime(p.completed_at).date().isoformat()
        if key not in activity:
            mins = max(10, p.video_time // 60) if p.video_time else 15
            activity[key] = {"minutes": mins, "lessons": 1}
            minutes_total += mins
    return {"year": year, "month": month, "current_streak": current, "longest_streak": max(longest, current),
            "total_study_days": len(activity), "total_minutes_this_month": minutes_total,
            "is_studied_today": studied_today, "activity_dates": activity}
