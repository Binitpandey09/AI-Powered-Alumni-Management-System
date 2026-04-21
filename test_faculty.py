import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alumni_platform.settings.dev')
django.setup()

from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
User = get_user_model()

faculty = User.objects.filter(email='dev.faculty@college.ac.in').first()
if faculty:
    client = APIClient(SERVER_NAME='localhost')
    client.credentials(HTTP_AUTHORIZATION='Bearer ' + str(RefreshToken.for_user(faculty).access_token))

    r = client.get('/api/accounts/faculty/profile/')
    print("GET Status:", r.status_code)
    print("College:", r.json().get('college_name'))
    print("Department:", r.json().get('department'))
    print("Subjects:", r.json().get('subjects_taught'))
    print("Completeness:", r.json().get('profile_completeness_score'))

    r = client.patch('/api/accounts/faculty/profile/', {
        'college_name': 'Test Engineering College',
        'department': 'Computer Science',
        'designation': 'Assistant Professor',
        'subjects_taught': ['Data Structures', 'DBMS', 'Operating Systems'],
        'technical_skills': ['Python', 'Java', 'C++'],
        'bio': 'Passionate educator with 5 years of experience teaching computer science subjects.',
    }, format='json')
    print("PATCH status:", r.status_code)
    print("Completeness after save:", r.json().get('profile_completeness_score'))
else:
    print("Faculty user dev.faculty@college.ac.in not found")
