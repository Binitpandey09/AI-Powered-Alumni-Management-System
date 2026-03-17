import pytest
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import EmailOTP, AlumniProfile, StudentProfile, FacultyProfile

User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def verified_student(db):
    user = User.objects.create_user(
        username='student_test',
        email='student@college.ac.in',
        password='testpass123',
        first_name='Test',
        last_name='Student',
        role='student',
        college='Test College',
        batch_year=2024,
        is_verified=True,
        is_active=True,
    )
    return user


@pytest.fixture
def verified_alumni(db):
    user = User.objects.create_user(
        username='alumni_test',
        email='alumni@techcompany.com',
        password='testpass123',
        first_name='Test',
        last_name='Alumni',
        role='alumni',
        college='Test College',
        batch_year=2020,
        is_verified=True,
        is_active=True,
    )
    return user


@pytest.fixture
def verified_faculty(db):
    user = User.objects.create_user(
        username='faculty_test',
        email='faculty@college.ac.in',
        password='testpass123',
        first_name='Test',
        last_name='Faculty',
        role='faculty',
        college='Test College',
        is_verified=True,
        is_active=True,
        is_profile_complete=False,
    )
    FacultyProfile.objects.get_or_create(user=user)
    return user


@pytest.fixture
def student_with_token(api_client, verified_student):
    # Ensure profile exists (signal may have created it already)
    StudentProfile.objects.get_or_create(user=verified_student)
    token = RefreshToken.for_user(verified_student)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(token.access_token)}')
    return api_client


@pytest.fixture
def alumni_with_token(api_client, verified_alumni):
    AlumniProfile.objects.get_or_create(user=verified_alumni)
    token = RefreshToken.for_user(verified_alumni)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(token.access_token)}')
    return api_client


@pytest.fixture
def faculty_with_token(api_client, verified_faculty):
    token = RefreshToken.for_user(verified_faculty)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(token.access_token)}')
    return api_client
