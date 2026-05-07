from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
import json

User = get_user_model()

alumni = User.objects.get(email='dev.alumni@techcompany.com')
client = APIClient()
client.credentials(HTTP_AUTHORIZATION='Bearer ' + str(RefreshToken.for_user(alumni).access_token))

r = client.get('/api/accounts/alumni/profile/', SERVER_NAME='localhost')
print("GET status:", r.status_code)
print("Company:", r.json().get('company'))
print("Technical skills:", r.json().get('technical_skills'))
print("Completeness:", r.json().get('profile_completeness_score'))

r2 = client.patch('/api/accounts/alumni/profile/', {
    'company': 'Google',
    'designation': 'Software Engineer L4',
    'employment_type': 'full_time',
    'industry': 'Information Technology',
    'years_of_experience': '3-5',
    'graduation_year': 2020,
    'degree': 'B.Tech',
    'branch': 'Computer Science',
    'college_name': 'Test Engineering College',
    'technical_skills': ['Python', 'Django', 'React', 'PostgreSQL', 'System Design', 'AWS'],
    'domain_expertise': ['Backend Development', 'Cloud Computing'],
    'bio': 'Software engineer at Google with 3+ years of experience in backend development. Love mentoring students for FAANG interviews and career guidance.',
    'linkedin_url': 'https://linkedin.com/in/devalumni',
    'available_for_mentorship': True,
    'mentorship_areas': ['career_guidance', 'interview_prep', 'dsa_prep', 'system_design'],
}, format='json', SERVER_NAME='localhost')
print("PATCH status:", r2.status_code)
print("Updated completeness:", r2.json().get('profile_completeness_score'))

r3 = client.patch('/api/accounts/alumni/bank-details/', {
    'account_holder_name': 'Dev Alumni',
    'bank_name': 'HDFC Bank',
    'account_number': '50100123456789',
    'confirm_account_number': '50100123456789',
    'ifsc_code': 'HDFC0001234',
    'account_type': 'savings',
}, format='json', SERVER_NAME='localhost')
print("Bank details status:", r3.status_code)
