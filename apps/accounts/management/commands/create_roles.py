from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from decouple import config

User = get_user_model()


class Command(BaseCommand):
    help = 'Create initial admin user and role-based test users'

    def handle(self, *args, **options):
        # Get credentials from environment
        admin_email = config('ADMIN_EMAIL', default='admin@alumniconnect.com')
        admin_password = config('ADMIN_PASSWORD', default='admin123')
        
        # Create Admin user
        if not User.objects.filter(email=admin_email).exists():
            admin_user = User.objects.create_superuser(
                username='admin',
                email=admin_email,
                password=admin_password,
                first_name='Admin',
                last_name='User',
                role='admin'
            )
            self.stdout.write(
                self.style.SUCCESS(f'Successfully created admin user: {admin_email}')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'Admin user already exists: {admin_email}')
            )
        
        # Create test users for each role (optional, for development)
        test_users = [
            {
                'username': 'alumni_test',
                'email': 'alumni@test.com',
                'password': 'test123',
                'first_name': 'Alumni',
                'last_name': 'Test',
                'role': 'alumni',
                'company': 'Google',
                'designation': 'Senior Software Engineer',
                'graduation_year': 2018
            },
            {
                'username': 'student_test',
                'email': 'student@test.com',
                'password': 'test123',
                'first_name': 'Student',
                'last_name': 'Test',
                'role': 'student',
                'graduation_year': 2026
            },
            {
                'username': 'faculty_test',
                'email': 'faculty@test.com',
                'password': 'test123',
                'first_name': 'Faculty',
                'last_name': 'Test',
                'role': 'faculty',
                'designation': 'Professor'
            }
        ]
        
        for user_data in test_users:
            if not User.objects.filter(email=user_data['email']).exists():
                User.objects.create_user(**user_data)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully created {user_data["role"]} user: {user_data["email"]}'
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f'{user_data["role"].capitalize()} user already exists: {user_data["email"]}'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS('\nAll users created successfully!')
        )
        self.stdout.write('Default password for test users: test123')
