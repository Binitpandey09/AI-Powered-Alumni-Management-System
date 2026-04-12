import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alumni_platform.settings.dev')
django.setup()

print("=============================================================")
print("STEP 7 — CREATE TEST DATA SO DASHBOARD SHOWS REAL CONTENT")
print("=============================================================")

from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
User = get_user_model()

student = User.objects.get(email='dev.student@college.ac.in')
alumni = User.objects.get(email='dev.alumni@techcompany.com')

try:
    sp = student.student_profile
    sp.skills = ['Python', 'Django', 'JavaScript', 'React', 'SQL', 'Git', 'REST API']
    sp.save(update_fields=['skills'])
    print("Student skills updated:", sp.skills)
except Exception as e:
    print("Profile error:", e)

from apps.sessions_app.models import Session, Booking
session, created = Session.objects.get_or_create(
    host=alumni,
    title='Python & Django Masterclass',
    defaults={
        'session_type': 'group',
        'description': 'Learn Python and Django from an experienced engineer at a top company.',
        'niche': 'Backend Development',
        'skills_covered': ['Python', 'Django', 'REST API'],
        'scheduled_at': timezone.now() + timedelta(days=3),
        'duration_minutes': 60,
        'price': Decimal('299.00'),
        'max_seats': 20,
        'status': 'upcoming',
        'is_free': False,
        'is_demo_eligible': True,
        'tags': ['Python', 'Django', 'Backend'],
    }
)
print("Session:", session.title, "| Created:", created)

booking, b_created = Booking.objects.get_or_create(
    session=session,
    student=student,
    defaults={
        'status': 'confirmed',
        'amount_paid': Decimal('299.00'),
        'platform_cut': Decimal('89.70'),
        'host_share': Decimal('209.30'),
        'razorpay_order_id': 'order_test_001',
        'razorpay_payment_id': 'pay_test_001',
    }
)
print("Booking created:", b_created, "| Status:", booking.status)

from apps.referrals.models import Referral, ReferralApplication
referral, r_created = Referral.objects.get_or_create(
    posted_by=alumni,
    job_title='Backend Developer',
    defaults={
        'company_name': 'TechCorp',
        'job_description': 'We are looking for a backend developer with Python and Django skills to join our growing team.',
        'work_type': 'full_time',
        'experience_level': 'fresher',
        'location': 'Bangalore',
        'required_skills': ['Python', 'Django', 'SQL'],
        'preferred_skills': ['React', 'REST API'],
        'max_applicants': 5,
        'deadline': timezone.now() + timedelta(days=10),
        'status': 'active',
        'is_urgent': True,
        'tags': ['Python', 'Backend', 'Fresher'],
    }
)
print("Referral created:", r_created, "| Title:", referral.job_title)

application, a_created = ReferralApplication.objects.get_or_create(
    referral=referral,
    student=student,
    defaults={
        'status': 'shortlisted',
        'match_score': 85,
        'matched_skills': ['Python', 'Django', 'SQL'],
        'missing_skills': [],
        'cover_note': 'I am very interested in this role.',
    }
)
print("Application created:", a_created, "| Status:", application.status)

from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
client = APIClient()
refresh = RefreshToken.for_user(student)
client.credentials(HTTP_AUTHORIZATION='Bearer ' + str(refresh.access_token))

response = client.get('/api/dashboard/student-data/', SERVER_NAME='localhost')
print("\n=== DASHBOARD API RESPONSE ===")
print("Status:", response.status_code)
data = response.json()
print("Profile score:", data.get('profile', {}).get('score'))
print("Sessions booked:", data.get('sessions', {}).get('total_booked'))
print("Upcoming sessions:", len(data.get('sessions', {}).get('upcoming', [])))
print("Referrals applied:", data.get('referrals', {}).get('total_applied'))
print("Shortlisted:", data.get('referrals', {}).get('shortlisted'))
print("AI uses:", data.get('ai_tools', {}).get('total_uses'))
print("Top referrals count:", len(data.get('top_referrals_for_you', [])))
print("Feed posts count:", len(data.get('recent_feed_posts', [])))
print("Alumni to connect count:", len(data.get('alumni_to_connect', [])))
