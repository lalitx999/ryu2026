from django.db import models
from django.conf import settings

class SystemSetting(models.Model):
    key_name = models.CharField(max_length=100, primary_key=True)
    key_value = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'settings'

    def __str__(self):
        return f"{self.key_name} = {self.key_value[:30] if self.key_value else ''}"

class LifetimeStudentImport(models.Model):
    id = models.AutoField(primary_key=True)
    email = models.CharField(max_length=100)
    level = models.CharField(max_length=10)
    invite_code = models.CharField(max_length=20, blank=True, null=True)
    code_generated_at = models.DateTimeField(blank=True, null=True)
    is_registered = models.BooleanField(default=False)
    registered_user_id = models.IntegerField(blank=True, null=True)
    registered_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'lifetime_students_import'

    def __str__(self):
        return f"{self.email} ({self.level}) - Registered: {self.is_registered}"

class MigrationRequest(models.Model):
    id = models.AutoField(primary_key=True)
    email = models.CharField(max_length=255)
    tracking_code = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('processing', 'Processing'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending')
    level = models.CharField(max_length=10, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    processed_by = models.IntegerField(blank=True, null=True)
    admin_note = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'migration_requests'

    def __str__(self):
        return f"Migration #{self.id} ({self.email}) - {self.status}"
