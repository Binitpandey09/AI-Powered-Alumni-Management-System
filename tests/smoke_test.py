import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alumni_platform.settings.dev')
django.setup()

from django.test import Client
from apps.accounts.models import User

c = Client()
urls = ['/', '/auth/login/', '/auth/choose-role/']
print("ANON URLS:")
for u in urls:
    r = c.get(u, HTTP_HOST='localhost')
    print(f"[x] {u} -> {r.status_code}")

try:
    student = User.objects.get(email='test.student@college.ac.in')
    c.force_login(student)
    student_urls = ['/dashboard/student/', '/feed/', '/sessions/', '/referrals/', '/notifications/', '/tools/resume-check/']
    print("\nSTUDENT URLS:")
    for u in student_urls:
        r = c.get(u, HTTP_HOST='localhost')
        print(f"[x] {u} -> {r.status_code}")
except BaseException as e:
    print("Dev student not found or error:", e)

try:
    alumni = User.objects.get(email='test.alumni@techcompany.com')
    c.force_login(alumni)
    alumni_urls = ['/dashboard/alumni/', '/sessions/hosting/', '/payments/wallet/']
    print("\nALUMNI URLS:")
    for u in alumni_urls:
        r = c.get(u, HTTP_HOST='localhost')
        print(f"[x] {u} -> {r.status_code}")
except BaseException as e:
    print("Dev alumni not found or error:", e)

try:
    admin = User.objects.get(email='test.admin@alumniai.com')
    c.force_login(admin)
    print("\nADMIN URLS:")
    r = c.get('/admin-panel/', HTTP_HOST='localhost')
    print(f"[x] /admin-panel/ -> {r.status_code}")
except BaseException as e:
    print("Dev admin not found or error:", e)
