import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alumni_platform.settings.dev')
django.setup()

from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
User = get_user_model()

print("=============================================================")
print("STEP 1 — DIAGNOSE THE API ENDPOINT FIRST")
print("=============================================================")

try:
    student = User.objects.get(email='dev.student@college.ac.in')
    print("Student found:", student.email, "| Role:", student.role, "| Active:", student.is_active)
except User.DoesNotExist:
    print("ERROR: dev.student@college.ac.in does not exist — run create_dev_users first")
    exit()

client = APIClient()
refresh = RefreshToken.for_user(student)
client.credentials(HTTP_AUTHORIZATION='Bearer ' + str(refresh.access_token))

response = client.get('/api/dashboard/student-data/', SERVER_NAME='localhost')
print("Status:", response.status_code)
print("Response:", response.json())


print("\n=============================================================")
print("STEP 2 — CHECK WHAT DATA ACTUALLY EXISTS IN THE DATABASE")
print("=============================================================")

try:
    sp = student.student_profile
    print("Profile score:", sp.profile_completeness_score)
    print("Skills:", sp.skills)
except Exception as e:
    print("No student profile:", e)

from apps.sessions_app.models import Booking, Session
bookings = Booking.objects.filter(student=student)
print("Total bookings:", bookings.count())
print("Confirmed bookings:", bookings.filter(status='confirmed').count())

from apps.referrals.models import ReferralApplication
apps = ReferralApplication.objects.filter(student=student)
print("Total applications:", apps.count())

from apps.payments.models import AIToolUsage
usages = AIToolUsage.objects.filter(user=student)
print("AI tool usages:", usages.count())

print("Total sessions in DB:", Session.objects.count())
print("Active sessions:", Session.objects.filter(status='upcoming').count())
