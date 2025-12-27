from django.db import models
from apps.registry.partners.models import Partner


class Notification(models.Model):
    CHANNEL_CHOICES = [
        ('email', 'Email'),
        ('telegram', 'Telegram'),
        ('sms', 'SMS'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'В ожидании'),
        ('sent', 'Отправлено'),
        ('failed', 'Ошибка'),
        ('delivered', 'Доставлено'),
    ]
    
    partner = models.ForeignKey(Partner, on_delete=models.CASCADE)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    subject = models.CharField(max_length=255)
    message = models.TextField()
    recipient = models.CharField(max_length=255)  # email или chat_id
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'notifications_history'
        indexes = [
            models.Index(fields=['partner', 'created_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Notification {self.id} - {self.channel} - {self.status}"