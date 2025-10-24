# Django management command to create default admin
from django.core.management.base import BaseCommand
from Authentication.models import Staff
from datetime import date

class Command(BaseCommand):
    help = 'Create default admin user'

    def handle(self, *args, **options):
        # Check if admin already exists
        if Staff.objects.filter(email='admin@hospital.com').exists():
            self.stdout.write(
                self.style.WARNING('Admin user already exists')
            )
            return

        # Create default admin
        admin = Staff.objects.create(
            staff_name='System Administrator',
            date_of_birth=date(1980, 1, 1),
            email='admin@hospital.com',
            phone='9876543210',
            gender='Male',
            address='Hospital Administration Office',
            experience=10,
            joining_date=date.today(),
            role='Admin',
            is_active=1,
            password='admin1234' # added pssword field
        )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created admin user: {admin.email}')
        )
