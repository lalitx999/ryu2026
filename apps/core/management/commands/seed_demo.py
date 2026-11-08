"""Dev-only demo data (admin + student + sample courses + forum posts).  Refuses to run with DEBUG off."""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from community.models import Post
from courses.models import Course, Lesson, Module
from users.models import User

PRICES = {"N5": (1000, 5000, 9000, 10000), "N4": (1250, 6500, 12000, 20000), "N3": (1500, 8000, 15000, 30000),
          "N2": (1750, 9500, 18000, 40000), "N1": (2000, 11000, 21000, 50000)}


class Command(BaseCommand):
    help = "Create demo users/courses for local development"

    def handle(self, *args, **opts):
        if not settings.DEBUG:
            raise CommandError("seed_demo only runs with DEBUG=True")
        admin, _ = User.objects.get_or_create(email="admin@test.local", defaults={
            "name": "Admin Ryu", "role": "admin", "is_staff": True, "is_superuser": True, "email_verified": True})
        student, _ = User.objects.get_or_create(email="student@test.local", defaults={
            "name": "นักเรียนทดสอบ", "role": "student", "email_verified": True, "force_password_change": False})
        for u in (admin, student):
            u.set_password("demo12345")
            u.save()
        for i, (level, (m, s, y, life)) in enumerate(PRICES.items(), start=1):
            c, _ = Course.objects.get_or_create(id=i, defaults=dict(
                title=f"คอร์สภาษาญี่ปุ่น {level}", slug=f"jlpt-{level.lower()}", level=level, sort_order=i, price=m,
                price_180=s, price_365=y, price_lifetime=life, description=f"เตรียมสอบ JLPT {level}"))
            mod, _ = Module.objects.get_or_create(course=c, title="บทที่ 1", defaults={"sort_order": 1})
            Lesson.objects.get_or_create(course=c, module=mod, title=f"{level} ปูพื้นฐาน EP1",
                                         defaults={"sort_order": 1, "is_free": i == 1, "duration": 600})
        if not Post.objects.exists():
            Post.objects.create(user=student, category="QNA", title="は กับ が ต่างกันยังไงคะ?",
                                content="สงสัยเรื่องการใช้ は กับ が ในประโยคพื้นฐาน มีเทคนิคจำไหมคะ 🙏", moderation_status="APPROVED")
        self.stdout.write(self.style.SUCCESS("seeded: admin@test.local / student@test.local (password demo12345)"))
