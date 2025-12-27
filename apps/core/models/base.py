from django.db import models
from django.utils.translation import gettext_lazy as _

class RegistryModel(models.Model):
    """
    Минимальная базовая модель для справочников:
    содержит поле name и timestamps.
    """
    name = models.CharField(max_length=255, db_index=True, blank=True, null=True, verbose_name=_("Название"))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Дата создания"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Дата обновления"))

    class Meta:
        abstract = True

    def __str__(self):
        return self.name
