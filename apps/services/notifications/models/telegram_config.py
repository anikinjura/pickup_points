from django.db import models
from apps.registry.partners.models import Partner


class TelegramConfig(models.Model):
    partner = models.OneToOneField(Partner, on_delete=models.CASCADE)
    bot_token = models.CharField(max_length=255, help_text="Токен бота партнёра")
    chat_id = models.CharField(max_length=255, help_text="ID чата для уведомлений")
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False, help_text="Использовать по умолчанию")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    validated_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'notifications_telegram_config'
        unique_together = [['partner']]

    def __str__(self):
        return f"TelegramConfig for {self.partner.name}"