"""Read side of the forum.  Every list/detail is a fixed number of queries (no per-post lookups)."""
from django.utils import timezone
from django.db.models import Count, Exists, OuterRef, Prefetch, Q

from community.models import Comment, Post, PostImage, PostLike

PAGE_LIMIT = 50


def _fmt(dt):
    return timezone.localtime(dt).strftime("%Y-%m-%d %H:%M:%S")

VISIBLE = ("APPROVED", "REWRITTEN")


def _visible_to(user):
    """Published posts, plus the author's own posts that are still being moderated."""
    cond = Q(moderation_status__in=VISIBLE)
    if user and user.is_authenticated:
        cond |= Q(user=user, moderation_status="PENDING")
    return cond


def _annotated(user):
    qs = Post.objects.select_related("user").only(
        "id", "category", "title", "content", "views_count", "likes_count", "moderation_status",
        "moderation_reason", "created_at", "user__id", "user__name", "user__role",
    ).annotate(
        comments_n=Count("comments", filter=Q(comments__moderation_status__in=VISIBLE), distinct=True),
    )
    if user and user.is_authenticated:
        qs = qs.annotate(liked=Exists(PostLike.objects.filter(post=OuterRef("pk"), user=user)))
    return qs.prefetch_related(Prefetch("images", queryset=PostImage.objects.only("post_id", "image_url", "sort_order")))


def post_list(user, category="", search=""):
    qs = _annotated(user).filter(_visible_to(user))
    if category and category != "ALL":
        qs = qs.filter(category=category)
    if search:
        qs = qs.filter(Q(title__icontains=search) | Q(content__icontains=search))
    return [_post_dict(p) for p in qs.order_by("-created_at")[:PAGE_LIMIT]]


def post_detail(user, post_id):
    post = _annotated(user).filter(_visible_to(user), pk=post_id).first()
    if not post:
        return None
    comments = Comment.objects.filter(post_id=post_id, moderation_status__in=VISIBLE).select_related("user").only(
        "id", "content", "moderation_status", "created_at", "user__id", "user__name").order_by("created_at")
    data = _post_dict(post)
    data["comments"] = [{
        "id": c.id, "content": c.content, "moderation_status": c.moderation_status,
        "created_at": _fmt(c.created_at), "user": {"id": c.user_id, "name": c.user.name},
    } for c in comments]
    data["comments_count"] = len(data["comments"])
    return data


def _post_dict(p):
    return {
        "id": p.id, "category": p.category, "category_display": p.get_category_display(),
        "title": p.title, "content": p.content, "views_count": p.views_count, "likes_count": p.likes_count,
        "comments_count": getattr(p, "comments_n", 0), "is_liked": bool(getattr(p, "liked", False)),
        "moderation_status": p.moderation_status,
        "moderation_reason": p.moderation_reason if p.moderation_status == "REWRITTEN" else "",
        "created_at": _fmt(p.created_at), "images": [i.image_url for i in p.images.all()],
        "user": {"id": p.user_id, "name": p.user.name, "role": p.user.role},
    }
