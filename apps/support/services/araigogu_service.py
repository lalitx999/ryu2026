"""Araigogu write side.  Ownership rule (the old API let anyone list/delete any session):
a session belongs to its user, or - for guests - to the browser session that created it."""
import uuid

from django.db.models import Q

from core.http import ServiceError
from support.models import AraigoguMessage, AraigoguSession

LANGS = {"JA", "ZH", "TH"}
MODES = {"chat", "checker", "interview"}
MAX_MESSAGE = 2000
GUEST_KEY = "ara_ids"
GUEST_CAP = 30


def owned(user, request_session):
    """Q object matching the sessions this requester may see."""
    if user.is_authenticated:
        return Q(user=user) | Q(session_id__in=request_session.get(GUEST_KEY, []))
    return Q(session_id__in=request_session.get(GUEST_KEY, []))


def _remember_guest(request_session, session_id):
    ids = [i for i in request_session.get(GUEST_KEY, []) if i != session_id] + [session_id]
    request_session[GUEST_KEY] = ids[-GUEST_CAP:]


def start_turn(user, request_session, session_id, lang, mode, message):
    """Persist the user message and return the session; the AI reply is produced by the Celery task."""
    message = (message or "").strip()
    if not message:
        raise ServiceError("กรุณาระบุข้อความ")
    lang, mode = (lang or "JA").upper(), mode or "chat"
    if lang not in LANGS or mode not in MODES:
        raise ServiceError("ภาษาหรือโหมดไม่ถูกต้อง")
    message = message[:MAX_MESSAGE]
    if session_id:
        sess = AraigoguSession.objects.filter(owned(user, request_session), session_id=session_id).first()
        if not sess:
            raise ServiceError("ไม่พบประวัติสนทนา", status=404)
        if user.is_authenticated and sess.user_id is None:
            sess.user = user  # claim a guest conversation after login
        sess.target_language, sess.mode = lang, mode
        sess.save()
    else:
        sess = AraigoguSession.objects.create(
            session_id=f"ara_{uuid.uuid4().hex[:12]}", user=user if user.is_authenticated else None,
            target_language=lang, mode=mode, title=message[:30] + ("..." if len(message) > 30 else ""))
        if not user.is_authenticated:
            _remember_guest(request_session, sess.session_id)
    AraigoguMessage.objects.create(session=sess, sender="user", content=message)
    return sess


def delete_session(user, request_session, session_id):
    deleted, _ = AraigoguSession.objects.filter(owned(user, request_session), session_id=session_id).delete()
    if not deleted:
        raise ServiceError("ไม่พบประวัติสนทนา", status=404)
