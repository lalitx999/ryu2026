from django.db import models
from django.conf import settings
from courses.models import Course

class Payment(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payments', db_column='user_id')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='payments', db_column='course_id')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    duration_days = models.IntegerField(default=30)
    level_access = models.CharField(max_length=50, blank=True, null=True)
    is_zoom_included = models.BooleanField(default=True)
    slip_path = models.TextField(blank=True, null=True, help_text="AES-256 encrypted file path")
    trans_ref = models.CharField(max_length=100, blank=True, null=True)
    telegram_message_id = models.CharField(max_length=100, blank=True, null=True)
    note = models.CharField(max_length=500, blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        default='pending'
    )
    rejection_reason = models.CharField(max_length=255, blank=True, null=True)
    is_renewal = models.BooleanField(default=False)
    discount_percent = models.PositiveSmallIntegerField(default=0)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='reviewed_payments',
        db_column='reviewed_by'
    )

    class Meta:
        db_table = 'payments'

    def __str__(self):
        return f"Payment {self.id}: {self.user.email} -> {self.amount} THB ({self.status})"

class SlipBlacklistPattern(models.Model):
    id = models.AutoField(primary_key=True)
    pattern = models.CharField(max_length=255)
    type = models.CharField(
        max_length=20,
        choices=[('bank', 'Bank'), ('amount', 'Amount'), ('name', 'Name'), ('keyword', 'Keyword')],
        default='keyword'
    )
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'slip_blacklist_patterns'

    def __str__(self):
        return f"Blacklist {self.type}: {self.pattern}"

class SlipVerificationLog(models.Model):
    id = models.AutoField(primary_key=True)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='verification_logs', db_column='payment_id')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='slip_verifications', db_column='user_id')
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('suspicious', 'Suspicious')],
        default='pending'
    )
    verified_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    verified_bank = models.CharField(max_length=100, blank=True, null=True)
    verified_account = models.CharField(max_length=50, blank=True, null=True)
    raw_response = models.TextField(blank=True, null=True, help_text="JSON payload from EasySlip API")
    error_message = models.TextField(blank=True, null=True)
    verified_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='reviewed_verifications',
        db_column='reviewed_by'
    )
    reviewed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'slip_verification_logs'

    def __str__(self):
        return f"Verification {self.id} for Payment {self.payment.id} ({self.status})"
