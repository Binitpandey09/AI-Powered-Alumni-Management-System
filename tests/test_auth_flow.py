import pytest
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import EmailOTP

User = get_user_model()

pytestmark = pytest.mark.django_db


# ── Test 1 ────────────────────────────────────────────────────
def test_student_registration_with_college_email(api_client):
    payload = {
        'first_name': 'Priya',
        'last_name': 'Sharma',
        'email': 'priya@college.ac.in',
        'password': 'securepass1',
        'role': 'student',
        'college': 'IIT Bombay',
        'batch_year': 2025,
    }
    response = api_client.post('/api/accounts/register/', payload, format='json')
    assert response.status_code == 201

    user = User.objects.get(email='priya@college.ac.in')
    assert user.is_verified is False
    assert EmailOTP.objects.filter(email='priya@college.ac.in', purpose='registration').exists()


# ── Test 2 ────────────────────────────────────────────────────
def test_student_registration_with_gmail_fails(api_client):
    payload = {
        'first_name': 'Priya',
        'last_name': 'Sharma',
        'email': 'priya@gmail.com',
        'password': 'securepass1',
        'role': 'student',
        'college': 'IIT Bombay',
        'batch_year': 2025,
    }
    response = api_client.post('/api/accounts/register/', payload, format='json')
    assert response.status_code == 400
    body = response.json()
    # Error should mention college email
    error_text = str(body).lower()
    assert 'college' in error_text or 'email' in error_text


# ── Test 3 ────────────────────────────────────────────────────
def test_alumni_registration_with_company_email(api_client):
    payload = {
        'first_name': 'Rohit',
        'last_name': 'Mehta',
        'email': 'rohit@techcompany.com',
        'password': 'securepass1',
        'role': 'alumni',
        'college': 'IIT Delhi',
        'batch_year': 2019,
    }
    response = api_client.post('/api/accounts/register/', payload, format='json')
    assert response.status_code == 201


# ── Test 4 ────────────────────────────────────────────────────
def test_alumni_registration_with_college_email_fails(api_client):
    payload = {
        'first_name': 'Rohit',
        'last_name': 'Mehta',
        'email': 'rohit@iitd.ac.in',
        'password': 'securepass1',
        'role': 'alumni',
        'college': 'IIT Delhi',
        'batch_year': 2019,
    }
    response = api_client.post('/api/accounts/register/', payload, format='json')
    assert response.status_code == 400


# ── Test 5 ────────────────────────────────────────────────────
def test_otp_verification_flow(api_client, db):
    user = User.objects.create_user(
        username='verify_test',
        email='verify@college.ac.in',
        password='testpass123',
        role='student',
        is_verified=False,
        is_active=True,
    )
    otp = EmailOTP.objects.create(
        user=user,
        email='verify@college.ac.in',
        otp_code='123456',
        purpose=EmailOTP.REGISTRATION,
        expires_at=timezone.now() + timedelta(minutes=10),
    )

    response = api_client.post('/api/accounts/verify-otp/', {
        'email': 'verify@college.ac.in',
        'otp_code': '123456',
    }, format='json')

    assert response.status_code == 200

    user.refresh_from_db()
    otp.refresh_from_db()
    assert user.is_verified is True
    assert otp.is_used is True


# ── Test 6 ────────────────────────────────────────────────────
def test_expired_otp_fails(api_client, db):
    user = User.objects.create_user(
        username='expired_test',
        email='expired@college.ac.in',
        password='testpass123',
        role='student',
        is_verified=False,
        is_active=True,
    )
    EmailOTP.objects.create(
        user=user,
        email='expired@college.ac.in',
        otp_code='654321',
        purpose=EmailOTP.REGISTRATION,
        expires_at=timezone.now() - timedelta(minutes=1),  # already expired
    )

    response = api_client.post('/api/accounts/verify-otp/', {
        'email': 'expired@college.ac.in',
        'otp_code': '654321',
    }, format='json')

    assert response.status_code == 400
    assert 'expired' in str(response.json()).lower()


# ── Test 7 ────────────────────────────────────────────────────
def test_login_otp_flow(api_client, verified_student):
    # Step 1 — request login OTP
    r1 = api_client.post('/api/accounts/login/', {
        'email': verified_student.email,
        'role': 'student',
    }, format='json')
    assert r1.status_code == 200

    # Grab the OTP directly from DB (Celery is not running in tests)
    otp = EmailOTP.objects.filter(
        email=verified_student.email,
        purpose=EmailOTP.LOGIN,
        is_used=False,
    ).latest('created_at')

    # Step 2 — verify OTP
    r2 = api_client.post('/api/accounts/login/verify/', {
        'email': verified_student.email,
        'otp_code': otp.otp_code,
    }, format='json')
    assert r2.status_code == 200

    data = r2.json()
    assert 'access' in data
    assert 'refresh' in data


# ── Test 8 ────────────────────────────────────────────────────
def test_me_endpoint_requires_auth(api_client, verified_student):
    # Without token → 401
    r1 = api_client.get('/api/accounts/me/')
    assert r1.status_code == 401

    # With valid token → 200
    refresh = RefreshToken.for_user(verified_student)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(refresh.access_token)}')
    r2 = api_client.get('/api/accounts/me/')
    assert r2.status_code == 200

    data = r2.json()
    assert data['email'] == verified_student.email
    assert data['role'] == 'student'
