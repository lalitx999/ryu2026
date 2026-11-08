"""Celery tasks: EasySlip verification and Telegram notification (external HTTP, so never in a request)."""
import logging
import mimetypes
import os
import re
from decimal import Decimal

import requests
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from payments.models import Payment, SlipVerificationLog
from payments.services import payment_service

logger = logging.getLogger(__name__)
EASYSLIP_API_URL = "https://developer.easyslip.com/api/v1/verify"


def _log(payment, status, **kw):
    return SlipVerificationLog.objects.create(payment=payment, user=payment.user, status=status, **kw)


def _verify_with_easyslip(payment):
    """Return (approved: bool, message). Mirrors the legacy rules: duplicate ref, exact amount, merchant tail."""
    if not settings.EASYSLIP_API_KEY:
        _log(payment, "pending", error_message="EASYSLIP_API_KEY is not configured")
        return False, "ยังไม่ได้ตั้งค่า EASYSLIP_API_KEY"
    path = os.path.join(settings.SLIPS_STORAGE_DIR, payment.slip_path)
    try:
        with open(path, "rb") as fh:
            mime = mimetypes.guess_type(path)[0] or "image/jpeg"
            resp = requests.post(EASYSLIP_API_URL, headers={"Authorization": f"Bearer {settings.EASYSLIP_API_KEY}"},
                                 files={"file": (os.path.basename(path), fh, mime)}, timeout=30)
        raw = resp.text
        body = resp.json()
    except Exception as exc:
        logger.error("EasySlip call failed for payment %s: %s", payment.id, exc)
        _log(payment, "pending", error_message=str(exc))
        return False, f"เกิดข้อผิดพลาดในการเชื่อมต่อระบบตรวจสลิป: {exc}"

    if resp.status_code != 200 or body.get("status", resp.status_code) != 200:
        msg = body.get("message") or body.get("error") or f"EasySlip API HTTP {resp.status_code}"
        _log(payment, "pending", raw_response=raw, error_message=msg)
        return False, f"ตรวจสอบสลิปไม่สำเร็จ: {msg}"

    data = body.get("data", {})
    trans_ref = data.get("transRef") or data.get("payload", "")
    amt = data.get("amount", {})
    value = (amt.get("amount") or amt.get("local", {}).get("amount")) if isinstance(amt, dict) else amt
    verified = Decimal(str(value)) if value is not None else None
    receiver = data.get("receiver", {})
    bank = receiver.get("bank", {}).get("name", "") or receiver.get("bank", {}).get("short", "")
    account = str(receiver.get("account", {}).get("value", "") or receiver.get("proxy", {}).get("value", ""))
    common = dict(verified_amount=verified, verified_bank=bank, verified_account=account, raw_response=raw)

    if trans_ref and Payment.objects.filter(trans_ref=trans_ref, status="approved").exclude(id=payment.id).exists():
        _log(payment, "rejected", error_message="สลิปนี้ถูกใช้งานไปแล้ว (Duplicate Slip trans_ref)", **common)
        Payment.objects.filter(pk=payment.pk).update(status="rejected", trans_ref=trans_ref,
                                                     rejection_reason="สลิปนี้ถูกใช้งานไปแล้วในระบบ")
        return False, "สลิปนี้ถูกใช้งานไปแล้วในระบบ"
    if verified is None or abs(verified - payment.amount) > Decimal("0.01"):
        msg = f"ยอดเงินในสลิป (฿{verified}) ไม่ตรงกับยอดที่ต้องชำระ (฿{payment.amount})"
        _log(payment, "suspicious", error_message=msg, **common)
        if trans_ref:
            Payment.objects.filter(pk=payment.pk).update(trans_ref=trans_ref)
        return False, msg
    merchant = re.sub(r"\D", "", settings.MERCHANT_ACCOUNT_NUMBER)
    tail = re.sub(r"\D", "", account)
    if merchant and tail and not tail.endswith(merchant[-4:]):
        msg = f"บัญชีผู้รับในสลิป ({account}) ไม่ตรงกับบัญชีของทางร้าน ({settings.MERCHANT_ACCOUNT_NUMBER})"
        _log(payment, "suspicious", error_message=msg, **common)
        return False, msg

    payment_service.approve_payment(payment.id, trans_ref=trans_ref)
    _log(payment, "approved", **common)
    return True, "ตรวจสอบสลิปผ่าน EasySlip สำเร็จ และเปิดสิทธิ์การเรียนให้อัตโนมัติแล้ว"


def _telegram(text, photo_path=None):
    token, chats = settings.TELEGRAM_BOT_TOKEN, settings.TELEGRAM_ADMIN_CHAT_ID
    if not token or not chats:
        return False
    for chat_id in filter(None, (c.strip() for c in chats.split(","))):
        try:
            if photo_path and os.path.exists(photo_path):
                with open(photo_path, "rb") as photo:
                    requests.post(f"https://api.telegram.org/bot{token}/sendPhoto",
                                  data={"chat_id": chat_id, "caption": text, "parse_mode": "HTML"},
                                  files={"photo": photo}, timeout=15)
            else:
                requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                              json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, timeout=10)
        except Exception as exc:
            logger.warning("telegram failed: %s", exc)
    return True


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def process_new_slip(self, payment_id):
    """Verify the slip (auto-approve when it matches), then tell the admins."""
    payment = Payment.objects.select_related("user", "course").get(pk=payment_id)
    try:
        approved, message = _verify_with_easyslip(payment)
    except Exception as exc:
        raise self.retry(exc=exc)
    payment.refresh_from_db()
    user = payment.user
    lines = [
        "💰 <b>AUTO-APPROVED NEW REGISTRATION</b>" if payment.status == "approved" else "🛒 <b>คำสั่งซื้อใหม่ / NEW REGISTRATION</b>",
        f"👤 <b>{user.name or user.email}</b>", f"📧 <code>{user.email}</code>",
    ]
    if user.phone:
        lines.append(f"📞 <code>{user.phone}</code>")
    lines += [f"📚 Level: <b>{payment.level_access}</b> ({payment.course.title})",
              f"⌛ Duration: <b>{payment.duration_days} days</b>", f"💰 Amount: <b>฿{payment.amount:,.2f}</b>",
              f"📋 Payment ID: #<b>{payment.id}</b>", f"⏰ {timezone.localtime().strftime('%d/%m/%Y %H:%M')}",
              f"\n🔗 <a href='{settings.SITE_URL.rstrip('/')}/admin-panel/payments/'>ตรวจสอบสลิปใน Admin</a>"]
    _telegram("\n".join(lines), os.path.join(settings.SLIPS_STORAGE_DIR, payment.slip_path or ""))
    return message
