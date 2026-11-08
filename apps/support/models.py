from django.db import models
from django.conf import settings

class SupportTicket(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='support_tickets', db_column='user_id')
    category = models.CharField(max_length=100, help_text="หมวดหมู่ เช่น วิดีโอ, การจ่ายเงิน, ควิซ")
    message = models.TextField(help_text="รายละเอียดปัญหา")
    user_agent = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('resolved', 'Resolved')], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'support_tickets'

    def __str__(self):
        return f"Ticket #{self.id} ({self.category}) - {self.user.email}"

class ChatLog(models.Model):
    id = models.AutoField(primary_key=True)
    session_id = models.CharField(max_length=100)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='chat_logs', db_column='user_id')
    user_message = models.TextField()
    ai_response = models.TextField()
    triggered_action = models.CharField(max_length=50, choices=[('FREE_COURSE', 'Free Course'), ('REGISTER', 'Register'), ('NONE', 'None')], default='NONE')
    created_at = models.DateTimeField(auto_now_add=True)
    response_time_ms = models.IntegerField(default=0)
    model_used = models.CharField(max_length=50, blank=True, null=True)
    tokens_used = models.IntegerField(default=0)

    class Meta:
        db_table = 'chat_logs'

    def __str__(self):
        return f"ChatLog #{self.id} (Session: {self.session_id})"

class ConversationSession(models.Model):
    id = models.AutoField(primary_key=True)
    session_id = models.CharField(max_length=100, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='conversation_sessions', db_column='user_id')
    state = models.CharField(max_length=50, default='GREETING')
    selected_course_id = models.PositiveIntegerField(blank=True, null=True)
    selected_package = models.CharField(max_length=50, blank=True, null=True)
    order_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    temp_user_data = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'conversation_sessions'

    def __str__(self):
        return f"Session {self.session_id} ({self.state})"

class AraigoguSession(models.Model):
    id = models.AutoField(primary_key=True)
    session_id = models.CharField(max_length=100, unique=True, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='araigogu_sessions', db_column='user_id')
    target_language = models.CharField(max_length=10, default='JA', choices=[('TH', 'Thai'), ('JA', 'Japanese'), ('ZH', 'Chinese')])
    mode = models.CharField(max_length=30, default='chat', choices=[('chat', 'Chat Tutor'), ('checker', 'Grammar Checker'), ('interview', 'Interview Practice')])
    title = models.CharField(max_length=255, default='บทสนทนาใหม่')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'araigogu_sessions'
        ordering = ['-updated_at']

    def __str__(self):
        return f"AraigoguSession {self.session_id} [{self.target_language}] - {self.title}"

class AraigoguMessage(models.Model):
    id = models.AutoField(primary_key=True)
    session = models.ForeignKey(AraigoguSession, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=20, choices=[('user', 'User'), ('assistant', 'Assistant'), ('system', 'System')])
    content = models.TextField()
    tokens_used = models.IntegerField(default=0)
    model_used = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'araigogu_messages'
        ordering = ['created_at']

    def __str__(self):
        return f"Message #{self.id} ({self.sender}) in {self.session.session_id}"
