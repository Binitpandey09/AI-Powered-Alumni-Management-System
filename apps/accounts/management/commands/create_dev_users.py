from django.core.management.base import BaseCommand
from apps.accounts.models import User, AlumniProfile, StudentProfile, FacultyProfile


class Command(BaseCommand):
    help = 'Create dev test users for all roles'

    def handle(self, *args, **kwargs):
        users = [
            {
                'email': 'dev.student@college.ac.in',
                'role': 'student',
                'first_name': 'Dev',
                'last_name': 'Student',
                'college': 'Test College',
            },
            {
                'email': 'dev.alumni@techcompany.com',
                'role': 'alumni',
                'first_name': 'Dev',
                'last_name': 'Alumni',
                'college': 'Test College',
            },
            {
                'email': 'dev.faculty@college.ac.in',
                'role': 'faculty',
                'first_name': 'Dev',
                'last_name': 'Faculty',
                'college': 'Test College',
            },
            {
                'email': 'dev.admin@alumniai.com',
                'role': 'admin',
                'first_name': 'Dev',
                'last_name': 'Admin',
                'college': '',
            },
        ]

        for u in users:
            user, created = User.objects.get_or_create(
                email=u['email'],
                defaults={
                    'username': u['email'],
                    'role': u['role'],
                    'first_name': u['first_name'],
                    'last_name': u['last_name'],
                    'college': u['college'],
                    'is_verified': True,
                    'is_profile_complete': False,
                }
            )
            if created:
                user.set_password('DevPass@123')
                user.save()
                self.stdout.write(f'Created {u["role"]} user: {u["email"]}')
            else:
                self.stdout.write(f'Already exists: {u["email"]}')

        self.stdout.write(self.style.SUCCESS('Dev users ready.'))
