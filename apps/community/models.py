from django.db import models
from django.conf import settings

class Post(models.Model):
    CATEGORY_CHOICES = [
        ('QNA', '❓ สอบถามภาษาญี่ปุ่น'),
        ('TECHNIQUE', '💡 แชร์เทคนิคการเรียน'),
        ('JAPAN_EXP', '✈️ ประสบการณ์ญี่ปุ่น'),
        ('GENERAL', '🎌 พูดคุยทั่วไป'),
    ]

    MODERATION_CHOICES = [
        ('PENDING', '⏳ รอตรวจสอบ'),
        ('APPROVED', '✅ ผ่านการอนุมัติ'),
        ('REWRITTEN', '✨ ปรับแต่งโดย AI'),
        ('REJECTED', '❌ ไม่อนุญาตให้โพสต์'),
    ]

    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='community_posts', db_column='user_id', db_constraint=False)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='GENERAL')
    title = models.CharField(max_length=255)
    content = models.TextField()
    original_content = models.TextField(blank=True, null=True, help_text="Original content before AI moderation rewrite")
    views_count = models.PositiveIntegerField(default=0)
    likes_count = models.PositiveIntegerField(default=0)
    moderation_status = models.CharField(max_length=20, choices=MODERATION_CHOICES, default='APPROVED')
    moderation_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'community_posts'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.category}] {self.title} by {self.user.email}"

class PostImage(models.Model):
    id = models.AutoField(primary_key=True)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='images', db_column='post_id')
    image_url = models.CharField(max_length=500)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'community_post_images'
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f"Image #{self.id} for Post #{self.post.id}"

class PostLike(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='post_likes', db_column='user_id', db_constraint=False)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes', db_column='post_id')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'community_post_likes'
        unique_together = ('user', 'post')

class Comment(models.Model):
    MODERATION_CHOICES = [
        ('PENDING', '⏳ รอตรวจสอบ'),
        ('APPROVED', '✅ ผ่านการอนุมัติ'),
        ('REWRITTEN', '✨ ปรับแต่งโดย AI'),
        ('REJECTED', '❌ ไม่อนุญาตให้โพสต์'),
    ]

    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='community_comments', db_column='user_id', db_constraint=False)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments', db_column='post_id')
    content = models.TextField()
    original_content = models.TextField(blank=True, null=True)
    moderation_status = models.CharField(max_length=20, choices=MODERATION_CHOICES, default='APPROVED')
    moderation_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        db_table = 'community_comments'
        ordering = ['created_at']

    def __str__(self):
        return f"Comment #{self.id} on Post #{self.post.id} by {self.user.email}"
