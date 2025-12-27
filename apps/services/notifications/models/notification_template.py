from django.db import models


class NotificationTemplate(models.Model):
    CODE_CHOICES = [
        ('order_created', 'Создание заказа'),
        ('order_status_change', 'Изменение статуса заказа'),
        ('partner_new_message', 'Новое сообщение партнёру'),
    ]
    
    code = models.CharField(max_length=50, choices=CODE_CHOICES, unique=True)
    name = models.CharField(max_length=255)
    subject_template = models.TextField()
    message_template = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'notifications_template'

    def __str__(self):
        return f"Template {self.code} - {self.name}"