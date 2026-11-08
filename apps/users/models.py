from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.conf import settings

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('points', 0)
        extra_fields.setdefault('custom_renewal_price', None)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    id = models.AutoField(primary_key=True)
    username = None
    email = models.EmailField(unique=True)
    
    # Custom fields mapping to PHP database schema
    name = models.CharField(max_length=255, blank=True)
    role = models.CharField(
        max_length=20, 
        choices=[('student', 'Student'), ('admin', 'Admin')], 
        default='student'
    )
    nickname = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    telegram_chat_id = models.CharField(max_length=50, blank=True, null=True)
    total_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    points = models.IntegerField(default=0, help_text="คะแนนสะสม / Reward Points")
    custom_renewal_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="ราคาต่ออายุเฉพาะบุคคล")
    admin_remark = models.TextField(blank=True, null=True, help_text="บันทึกข้อความจาก Admin")
    is_affiliate = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    force_password_change = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    class Meta:
        db_table = 'users'

    def check_password(self, raw_password):
        # Try standard Django check
        is_correct = super().check_password(raw_password)
        if is_correct:
            return True
            
        # Try legacy PHP bcrypt check
        h = self.password
        if h and (h.startswith('$2y$') or h.startswith('$2a$') or h.startswith('$2b$')):
            try:
                import bcrypt
                h_mod = h
                if h_mod.startswith('$2y$'):
                    h_mod = h_mod.replace('$2y$', '$2a$', 1)
                
                if bcrypt.checkpw(raw_password.encode('utf-8'), h_mod.encode('utf-8')):
                    # Upgrade password to Django's default hasher on successful login
                    self.set_password(raw_password)
                    self.save(update_fields=['password'])
                    return True
            except Exception:
                pass
        return False

    def __str__(self):
        return f"{self.name or self.email} ({self.role})"


class EmailVerificationCode(models.Model):
    """One-time email verification challenge for newly registered students."""
    # Legacy users.id is unsigned in production; avoid a fragile MySQL FK constraint.
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='email_verification_codes', db_constraint=False)
    code_hash = models.CharField(max_length=128)
    expires_at = models.DateTimeField()
    sent_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(blank=True, null=True)
    attempts = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = 'email_verification_codes'
        ordering = ('-sent_at',)
