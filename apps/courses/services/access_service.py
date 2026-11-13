import datetime
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from courses.models import Course, Enrollment
from users.models import User


class AccessService:
    LIFETIME_THRESHOLDS = {10000.00: "N5", 20000.00: "N4", 30000.00: "N3", 40000.00: "N2", 50000.00: "N1"}
    LEVEL_RANK = {"N5": 1, "N4": 2, "N3": 3, "N2": 4, "N1": 5}

    @staticmethod
    def get_tier_progress(total_spent) -> dict:
        total = float(total_spent or 0.0)
        tiers = sorted(AccessService.LIFETIME_THRESHOLDS.items())
        current_level = None
        for amount, level in tiers:
            if total >= amount:
                current_level = level
        nxt = next(((a, l) for a, l in tiers if total < a), None)
        if nxt is None:
            return {"total_spent": total, "current_level": "N1", "next_level": None, "next_threshold": tiers[-1][0],
                    "remaining_amount": 0.0, "progress_percent": 100.0, "overall_progress_percent": 100.0,
                    "is_max_tier": True, "badge_label": "N1 Lifetime (สิทธิ์สูงสุด)",
                    "summary_text": "🎉 ได้รับสิทธิ์เรียนตลอดชีพครบทุกระดับแล้ว!"}
        next_amount, next_level = nxt
        prev = max([a for a, _ in tiers if a < next_amount], default=0.0)
        span = next_amount - prev
        pct = max(0.0, min(100.0, (total - prev) / span * 100.0)) if span > 0 else 0.0
        remaining = next_amount - total
        return {"total_spent": total, "current_level": current_level, "next_level": next_level,
                "next_threshold": next_amount, "remaining_amount": remaining, "progress_percent": round(pct, 1),
                "overall_progress_percent": round(min(100.0, total / next_amount * 100.0), 1), "is_max_tier": False,
                "badge_label": f"{current_level} Lifetime" if current_level else "เริ่มต้นสะสม",
                "summary_text": f"ยอดสะสม ฿{total:,.0f} / ฿{next_amount:,.0f} (ขาดอีก ฿{remaining:,.0f} ปลดล็อก {next_level})"}

    @staticmethod
    def video_rank_for(enrollments, today=None) -> int:
        """Highest JLPT rank a user can watch, computed in memory from already-loaded enrollments.

        A banned active enrollment blocks everything; a higher tier covers all lower ones.
        """
        today = today or timezone.localdate()
        best = 0
        for e in enrollments:
            if e.status == "BANNED":
                return 0
            rank = AccessService.LEVEL_RANK.get(e.course.level, 0)
            if e.is_lifetime_video or (e.status == "ACTIVE" and e.video_expires_at and e.video_expires_at >= today):
                best = max(best, rank)
        return best

    @staticmethod
    def access_window(enrollments, level, today=None):
        """How long the student can watch a course of `level`: (is_lifetime, valid_until, days_left) or None.

        Any valid enrollment of the same or a higher level covers it (a higher tier unlocks the lower ones);
        lifetime wins, otherwise the latest expiry.  Computed in memory from already-loaded enrollments.
        """
        today = today or timezone.localdate()
        need = AccessService.LEVEL_RANK.get(level, 99)
        cover = [e for e in enrollments
                 if e.status != "BANNED" and AccessService.LEVEL_RANK.get(e.course.level, 0) >= need
                 and (e.is_lifetime_video or (e.status == "ACTIVE" and e.video_expires_at and e.video_expires_at >= today))]
        if any(e.is_lifetime_video for e in cover):
            return True, None, None
        if cover:
            until = max(e.video_expires_at for e in cover)
            return False, until, (until - today).days
        return None

    @staticmethod
    def user_video_rank(user_id) -> int:
        enrollments = Enrollment.objects.filter(user_id=user_id, is_active=True).select_related("course").only(
            "status", "is_lifetime_video", "video_expires_at", "course__level")
        return AccessService.video_rank_for(enrollments)

    @staticmethod
    def has_video_access(user_id, level="N5") -> bool:
        return AccessService.user_video_rank(user_id) >= AccessService.LEVEL_RANK.get(level, 0) > 0

    @staticmethod
    @transaction.atomic
    def recalculate_lifetime_unlocks(user_id) -> None:
        user = User.objects.filter(id=user_id).only("id", "total_spent").first()
        if not user:
            return
        total = float(user.total_spent)
        unlocked = {lvl for threshold, lvl in AccessService.LIFETIME_THRESHOLDS.items() if total >= threshold}
        if not unlocked:
            return
        courses = {}
        for course in Course.objects.filter(level__in=unlocked).order_by("-id"):
            courses[course.level] = course  # lowest id wins (iterating desc, last write)
        existing = {e.course_id: e for e in Enrollment.objects.filter(user_id=user_id, course__in=courses.values())}
        now = timezone.now()
        to_create, to_update = [], []
        for course in courses.values():
            enrollment = existing.get(course.id)
            if enrollment is None:
                to_create.append(Enrollment(user_id=user_id, course=course, status="ACTIVE", is_active=True,
                                            is_lifetime_video=True, activated_at=now))
            elif not (enrollment.is_lifetime_video and enrollment.status == "ACTIVE" and enrollment.is_active):
                enrollment.is_lifetime_video, enrollment.status, enrollment.is_active = True, "ACTIVE", True
                enrollment.activated_at = now
                to_update.append(enrollment)
        Enrollment.objects.bulk_create(to_create)
        if to_update:
            Enrollment.objects.bulk_update(to_update, ["is_lifetime_video", "status", "is_active", "activated_at"])

    @staticmethod
    @transaction.atomic
    def add_payment(user_id, amount) -> None:
        User.objects.filter(id=user_id).update(
            total_spent=Decimal(str(User.objects.values_list("total_spent", flat=True).get(id=user_id) or "0"))
            + Decimal(str(amount or "0")))
        AccessService.recalculate_lifetime_unlocks(user_id)

    @staticmethod
    def calculate_expiry(days: int, include_zoom: bool) -> dict:
        today = datetime.date.today()
        video_date = today + datetime.timedelta(days=days)
        zoom_date = None
        if include_zoom:
            if days < 999:
                zoom_date = video_date
            else:
                nxt = today.replace(day=28) + datetime.timedelta(days=4)
                zoom_date = nxt - datetime.timedelta(days=nxt.day)
        return {"video": video_date, "zoom": zoom_date}
