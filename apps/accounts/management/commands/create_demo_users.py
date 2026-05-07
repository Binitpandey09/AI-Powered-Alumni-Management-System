from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from apps.accounts.models import StudentProfile, FacultyProfile, AlumniProfile

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates demo users for presentation purposes'

    def handle(self, *args, **kwargs):
        demo_users = [
            {
                'email': 'student@test.com',
                'role': 'student',
                'first_name': 'Demo',
                'last_name': 'Student',
                'college': 'Test Institute of Technology',
            },
            {
                'email': 'faculty@test.com',
                'role': 'faculty',
                'first_name': 'Demo',
                'last_name': 'Faculty',
                'college': 'Test Institute of Technology',
            },
            {
                'email': 'alumni@test.com',
                'role': 'alumni',
                'first_name': 'Demo',
                'last_name': 'Alumni',
                'college': 'Test Institute of Technology',
            }
        ]

        for user_data in demo_users:
            email = user_data['email']
            role = user_data['role']
            username = email.split('@')[0]

            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': username,
                    'first_name': user_data['first_name'],
                    'last_name': user_data['last_name'],
                    'role': role,
                    'college': user_data['college'],
                    'password': make_password('demopass123'),  # Doesn't matter, OTP bypasses it
                    'is_verified': True,
                    'is_active': True,
                    'is_profile_complete': True,
                }
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f'Created user {email}'))
                
                # Create related profiles
                if role == 'student':
                    StudentProfile.objects.get_or_create(
                        user=user,
                        defaults={
                            'degree': 'B.Tech',
                            'branch': 'Computer Science',
                            'graduation_year': 2025,
                            'profile_summary': 'Enthusiastic computer science student looking for opportunities.',
                        }
                    )
                elif role == 'faculty':
                    FacultyProfile.objects.get_or_create(
                        user=user,
                        defaults={
                            'department': 'Computer Science and Engineering',
                            'designation': 'Professor',
                            'bio': 'Experienced professor specializing in Artificial Intelligence.',
                        }
                    )
                elif role == 'alumni':
                    AlumniProfile.objects.get_or_create(
                        user=user,
                        defaults={
                            'company': 'Tech Innovations Inc.',
                            'designation': 'Senior Software Engineer',
                            'bio': 'Passionate software engineer with 5 years of industry experience.',
                            'is_available_for_1on1': True,
                        }
                    )
            else:
                # Ensure they are active and verified if they already existed
                user.is_verified = True
                user.is_active = True
                user.is_profile_complete = True
                user.save(update_fields=['is_verified', 'is_active', 'is_profile_complete'])
                self.stdout.write(self.style.WARNING(f'User {email} already exists. Marked as verified.'))

        self.stdout.write(self.style.SUCCESS('Successfully completed demo users setup.'))
