# apps/registry/partners/management/commands/create_test_data.py
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.registry.partners.models import Partner, PartnerMember

User = get_user_model()

class Command(BaseCommand):
    help = 'Создает тестовые данные для партнеров'
    
    def handle(self, *args, **options):
        # Создаем тестового пользователя
        user, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@example.com',
                'is_active': True
            }
        )
        if created:
            user.set_password('testpassword123')
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Создан пользователь: {user.username}'))
        
        # Создаем суперпользователя
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'is_superuser': True,
                'is_staff': True,
                'is_active': True
            }
        )
        if created:
            admin_user.set_password('adminpassword123')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS(f'Создан админ: {admin_user.username}'))
        
        # Создаем партнеров для тестового пользователя
        partner_data = [
            {
                'name': 'ООО "ТехноПром"',
                'inn': '1234567890',
                'ogrn': '1234567890123',
                'email': 'info@technoprom.ru',
                'phone': '+79991234567',
                'owner': user,
            },
            {
                'name': 'ИП Иванов И.И.',
                'inn': '0987654321',
                'ogrn': '3210987654321',
                'phone': '+79997654321',
                'owner': user,
            },
        ]
        
        for data in partner_data:
            partner, created = Partner.objects.get_or_create(
                inn=data['inn'],
                defaults=data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Создан партнер: {partner.name}'))
        
        # Создаем членов партнера
        partner = Partner.objects.first()
        if partner:
            member_data = [
                {
                    'partner': partner,
                    'name': 'Петров Петр Петрович',
                    'work_email': 'petrov@technoprom.ru',
                    'role': PartnerMember.ROLE_DIRECTOR,
                },
                {
                    'partner': partner,
                    'name': 'Сидорова Мария Ивановна',
                    'work_email': 'sidorova@technoprom.ru',
                    'role': PartnerMember.ROLE_ACCOUNTANT,
                },
            ]
            
            for data in member_data:
                member, created = PartnerMember.objects.get_or_create(
                    partner=data['partner'],
                    work_email=data['work_email'],
                    defaults=data
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Создан член партнера: {member.name}'))
        
        self.stdout.write(self.style.SUCCESS('Тестовые данные созданы успешно!'))
        self.stdout.write('\nУчетные данные для тестирования:')
        self.stdout.write(f'  Обычный пользователь: {user.username} / testpassword123')
        self.stdout.write(f'  Администратор: {admin_user.username} / adminpassword123')
        self.stdout.write(f'\nAPI доступно по адресу: http://127.0.0.1:8000/api/')