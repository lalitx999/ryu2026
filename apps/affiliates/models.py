from django.db import models
from django.conf import settings

class AffiliateProfile(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='affiliate_profile', db_column='user_id')
    ref_code = models.CharField(max_length=50, unique=True)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    click_count = models.PositiveIntegerField(default=0)
    holding_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    ready_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    withdrawn_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=[('ACTIVE', 'Active'), ('PAUSED', 'Paused')], default='ACTIVE')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'affiliate_profiles'

    def __str__(self):
        return f"Affiliate {self.ref_code} ({self.user.email})"

class AffiliateClick(models.Model):
    id = models.AutoField(primary_key=True)
    affiliate_profile = models.ForeignKey(AffiliateProfile, on_delete=models.CASCADE, related_name='clicks', db_column='affiliate_profile_id')
    ip_address = models.CharField(max_length=45, blank=True, null=True)
    user_agent = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'affiliate_clicks'

class AffiliateCommission(models.Model):
    id = models.AutoField(primary_key=True)
    affiliate_profile = models.ForeignKey(AffiliateProfile, on_delete=models.CASCADE, related_name='commissions', db_column='affiliate_profile_id')
    referrer_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='referred_commissions', db_column='referrer_user_id')
    buyer_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='buyer_commissions', db_column='buyer_user_id')
    payment_id = models.PositiveIntegerField(db_column='payment_id')
    order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=[('HOLDING', 'Holding'), ('READY', 'Ready'), ('WITHDRAWN', 'Withdrawn'), ('CANCELLED', 'Cancelled')], default='HOLDING')
    hold_until = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'affiliate_commissions'

class AffiliateCouponLog(models.Model):
    id = models.AutoField(primary_key=True)
    affiliate_profile = models.ForeignKey(AffiliateProfile, on_delete=models.SET_NULL, null=True, blank=True, db_column='affiliate_profile_id')
    referrer_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='referrer_coupons', db_column='referrer_user_id')
    referred_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='referred_coupons', db_column='referred_user_id')
    ref_code = models.CharField(max_length=50)
    coupon_amount = models.DecimalField(max_digits=10, decimal_places=2, default=200.00)
    original_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discounted_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    terms_version = models.CharField(max_length=50)
    terms_text = models.TextField()
    accepted_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'affiliate_coupon_logs'

class AffiliatePayout(models.Model):
    id = models.AutoField(primary_key=True)
    affiliate_profile = models.ForeignKey(AffiliateProfile, on_delete=models.CASCADE, related_name='payouts', db_column='affiliate_profile_id')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payouts', db_column='user_id')
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    bank_name = models.CharField(max_length=120)
    bank_account = models.CharField(max_length=120)
    account_name = models.CharField(max_length=150)
    status = models.CharField(max_length=20, choices=[('REQUESTED', 'Requested'), ('PAID', 'Paid'), ('REJECTED', 'Rejected')], default='REQUESTED')
    requested_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'affiliate_payouts'
