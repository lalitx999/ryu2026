from django.db.models import Count
from django.utils import timezone

from support.models import AraigoguMessage, AraigoguSession
from support.services.araigogu_service import owned

HISTORY_LIMIT = 30


def history(user, request_session):
    qs = (AraigoguSession.objects.filter(owned(user, request_session))
          .annotate(message_count=Count("messages")).order_by("-updated_at")[:HISTORY_LIMIT])
    return [{"session_id": s.session_id, "title": s.title, "target_language": s.target_language, "mode": s.mode,
             "updated_at": timezone.localtime(s.updated_at).strftime("%Y-%m-%d %H:%M"),
             "message_count": s.message_count} for s in qs]


def session_detail(user, request_session, session_id):
    sess = AraigoguSession.objects.filter(owned(user, request_session), session_id=session_id).first()
    if not sess:
        return None
    msgs = AraigoguMessage.objects.filter(session=sess).only("id", "sender", "content", "model_used", "created_at")
    return {"session_id": sess.session_id, "title": sess.title, "target_language": sess.target_language,
            "mode": sess.mode, "messages": [
                {"id": m.id, "sender": m.sender, "content": m.content, "model_used": m.model_used,
                 "created_at": timezone.localtime(m.created_at).strftime("%H:%M")} for m in msgs]}
