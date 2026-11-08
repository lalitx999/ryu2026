"""AI moderation (DeepSeek) runs in Celery so the request never waits on the external API."""
import json
import logging
import re

import requests
from celery import shared_task
from django.conf import settings

from community.models import Comment, Post

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a strict safety officer and AI Content Moderator for RyuClass Online Community Forum (a Pantip-style educational platform).
Inspect user posts/comments for violence, harassment, toxic/rude language, hate speech, illegal activities, or explicit profanity.
RULES:
1. Appropriate and constructive: status "APPROVED", clean_title/clean_content = originals, reason "".
2. Mild profanity or aggressive tone that CAN be softened: status "REWRITTEN", sanitized clean_title/clean_content in polite Thai, reason "ปรับเปลี่ยนถ้อยคำที่ไม่เหมาะสมโดย AI ให้สุภาพและเป็นมิตร".
3. Severe violence, threats, harassment, illegal acts or extreme hate speech that CANNOT be softened: status "REJECTED", clean_title "", clean_content "", reason "พบเนื้อหารุนแรงหรือหยาบคายร้ายแรง ไม่สามารถเผยแพร่ในชุมชนได้".
Respond ONLY with valid JSON, no markdown: {"status": "...", "clean_title": "...", "clean_content": "...", "reason": "..."}"""


def moderate(title, content):
    """Return {status, clean_title, clean_content, reason}; fail-open (APPROVED) like the original system."""
    fallback = {"status": "APPROVED", "clean_title": title, "clean_content": content, "reason": ""}
    if not settings.DEEPSEEK_API_KEY:
        return fallback
    try:
        resp = requests.post(
            "https://api.deepseek.com/chat/completions",
            json={"model": settings.DEEPSEEK_MODEL, "temperature": 0.1, "max_tokens": 1000,
                  "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                               {"role": "user", "content": f"TITLE: {title}\nCONTENT: {content}"}]},
            headers={"Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}"}, timeout=15)
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"].strip()
        raw = re.sub(r"```(?:json)?\s*(.*?)\s*```", r"\1", raw, flags=re.DOTALL).strip()
        data = json.loads(raw)
        status = data.get("status") if data.get("status") in ("APPROVED", "REWRITTEN", "REJECTED") else "APPROVED"
        return {"status": status, "clean_title": data.get("clean_title") or title,
                "clean_content": data.get("clean_content") or content, "reason": data.get("reason", "")}
    except Exception as exc:  # network/JSON failure must not block posting
        logger.warning("moderation failed, defaulting to APPROVED: %s", exc)
        return fallback


def _apply(obj, title, result):
    original = obj.content
    obj.moderation_status = result["status"]
    obj.moderation_reason = result["reason"]
    if result["status"] == "REWRITTEN":
        obj.original_content = original
        obj.content = result["clean_content"]
        if title is not None:
            obj.title = result["clean_title"][:255]
    return obj


@shared_task
def moderate_post(post_id):
    post = Post.objects.get(pk=post_id)
    result = moderate(post.title, post.content)
    _apply(post, post.title, result).save(update_fields=[
        "moderation_status", "moderation_reason", "original_content", "content", "title", "updated_at"])
    return {"status": result["status"], "reason": result["reason"], "id": post_id}


@shared_task
def moderate_comment(comment_id):
    comment = Comment.objects.get(pk=comment_id)
    result = moderate("Comment", comment.content)
    _apply(comment, None, result).save(update_fields=[
        "moderation_status", "moderation_reason", "original_content", "content"])
    return {"status": result["status"], "reason": result["reason"], "id": comment_id}
