"""Slow / external work for the users app.  Never call these inline from a view; use .delay()."""
import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)

WELCOME_BODY = (
    "ขอบคุณที่สมัครมาเรียนด้วยกันครับ เชิญเข้ากลุ่มเพื่อรับลิ้งค์ Zoom เข้าเรียนสดครับ\n\n"
    "เชิญเข้ากลุ่ม RYU CLASS เพื่อรับลิ้งค์เรียนสดผ่านระบบ ZOOM ได้ที่ https://line.me/R/ti/g/VDRgkPXRM9\n\n"
    "ขั้นตอนการเรียนคลิปย้อนหลัง\n"
    "1. ไปที่ Google พิมพ์ค้นหาว่า Ryuclass\n"
    "2. ทำการเข้าสู่ระบบ กรณีมือถือ ให้กดสามขีดด้านบน\n"
    "3. เข้าเรียนคลิปตาม Step ได้เลยครับ\n\n"
    "ทีมงาน RyuClass"
)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def send_verification_email(self, email, name, code, ttl_minutes):
    try:
        send_mail(
            subject="รหัสยืนยันอีเมล RyuClass",
            message=(
                f'สวัสดีครับ {name or "นักเรียน RyuClass"}\n\n'
                f"รหัสยืนยันอีเมลของคุณคือ: {code}\n"
                f"รหัสนี้ใช้ได้ {ttl_minutes} นาที และห้ามบอกรหัสนี้กับผู้อื่น\n\nทีมงาน RyuClass"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
        )
    except Exception as exc:  # SMTP hiccup -> retry later, not in the request
        logger.warning("verification email failed: %s", exc)
        raise self.retry(exc=exc)


@shared_task
def send_welcome_email(email):
    send_mail("ขอบคุณที่สมัครมาเรียนด้วยกันครับ - RyuClass", WELCOME_BODY,
              settings.DEFAULT_FROM_EMAIL, [email], fail_silently=True)


@shared_task
def send_broadcast_email(subject, message, recipients):
    """One connection, many messages (bulk) - used by the admin broadcast screen."""
    from django.core.mail import EmailMessage, get_connection

    with get_connection(fail_silently=True) as conn:
        conn.send_messages([
            EmailMessage(subject, message, settings.DEFAULT_FROM_EMAIL, [r], connection=conn) for r in recipients
        ])
    return len(recipients)
