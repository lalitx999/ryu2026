"""Write side of the forum.  Moderation itself runs in Celery (see community.tasks)."""
import os
import uuid

from django.conf import settings
from django.db import transaction
from django.db.models import F

from core.http import ServiceError
from community.models import Comment, Post, PostImage, PostLike

CATEGORIES = {c for c, _ in Post.CATEGORY_CHOICES}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_IMAGE_BYTES = 5 * 1024 * 1024


def _save_images(post, files):
    os.makedirs(settings.COMMUNITY_STORAGE_DIR, exist_ok=True)
    rows = []
    for idx, f in enumerate(files):
        ext = os.path.splitext(f.name)[1].lower()
        if ext not in IMAGE_EXT:
            raise ServiceError("รองรับเฉพาะไฟล์รูปภาพ (jpg, png, webp, gif)")
        if f.size > MAX_IMAGE_BYTES:
            raise ServiceError("รูปภาพต้องมีขนาดไม่เกิน 5MB ต่อภาพ")
        name = f"{uuid.uuid4().hex}{ext}"
        with open(os.path.join(settings.COMMUNITY_STORAGE_DIR, name), "wb") as out:
            for chunk in f.chunks():
                out.write(chunk)
        rows.append(PostImage(post=post, image_url=f"/storage/community/{name}", sort_order=idx))
    PostImage.objects.bulk_create(rows)


def create_post(user, category, title, content, files):
    title, content = (title or "").strip()[:150], (content or "").strip()
    if not title or not content:
        raise ServiceError("กรุณากรอกหัวข้อกระทู้และเนื้อหาให้ครบถ้วน")
    if files and not 2 <= len(files) <= 5:
        raise ServiceError("ระบบกำหนดให้แนบรูปภาพได้ระหว่าง 2 ถึง 5 ภาพเท่านั้นครับ")
    with transaction.atomic():
        post = Post.objects.create(user=user, category=category if category in CATEGORIES else "GENERAL",
                                   title=title, content=content, moderation_status="PENDING")
        _save_images(post, files)
    return post


def toggle_like(user, post_id):
    with transaction.atomic():
        if not Post.objects.filter(pk=post_id, moderation_status__in=("APPROVED", "REWRITTEN")).exists():
            raise ServiceError("ไม่พบกระทู้", status=404)
        like, created = PostLike.objects.get_or_create(user=user, post_id=post_id)
        if created:
            Post.objects.filter(pk=post_id).update(likes_count=F("likes_count") + 1)
        else:
            like.delete()
            Post.objects.filter(pk=post_id, likes_count__gt=0).update(likes_count=F("likes_count") - 1)
        count = Post.objects.values_list("likes_count", flat=True).get(pk=post_id)
    return {"liked": created, "likes_count": count}


def add_comment(user, post_id, content):
    content = (content or "").strip()
    if not content:
        raise ServiceError("กรุณากรอกข้อความแสดงความคิดเห็น")
    if not Post.objects.filter(pk=post_id, moderation_status__in=("APPROVED", "REWRITTEN")).exists():
        raise ServiceError("ไม่พบกระทู้", status=404)
    return Comment.objects.create(user=user, post_id=post_id, content=content[:2000], moderation_status="PENDING")


def bump_views(post_id):
    Post.objects.filter(pk=post_id).update(views_count=F("views_count") + 1)
