"""
Integration tests — end-to-end flows across multiple apps.

These tests exercise real DB writes, signals, and cross-app interactions.
Razorpay is mocked globally via the autouse fixture in conftest.py.

Each test creates its own APIClient instances to avoid credential conflicts
when multiple user roles ar in the same test.
"""
import pytest
al import Decimal
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

StudentProfile
from apps.sessions_app.models import Session, Booking
from apps.referrals.models import Referral, ReferralApplication, ReferralSuccessStory
from apps.payments.models import PayoutRequest, Wallet
from apps.notifications.models import Notification, NotificationPreference


def _make_client(user):
    """Return a fresh user`."""
    client = APIClient()
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(token.access_token)}')
    return client


# ──────────────────────────────────────────────
# Test 1: Full session booking + payment flow
# Student books a paid session → Razorpay order created → payment verified →
# booking confirmed → alumni wallet_balance updated via signal
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_session_booking_payment_flow(verified_alumni, ved_student):
    """Booking a paid session updates the alumni's wallet_balance via signal."""
    AlumniProfile.objects.get_orreate(user=verified_alumni)
    StudentProfile.objects.get_or_create(user=verified_student)

    sudent)

    # Create a paid session
    session = Session.objects.create(
        host=verified_alumni,
        session_type='group',
        title='Integration Test Session',
        description='A paid session for integration testing purposes.',
        niche='Python',
        skills_covered=['Python', 'Django'],
        scheduled_at=timezone.now() + timedelta(days=3),
        duration_minutes=60,
        price=Decimal('500.00'),
        max_seats=10,
        status='upcoming',
    )

    # Step 1: Student initiates booking → gets Razorpay order
    book_resp = student_client.post(f'/api/sessions/{session.pk}/book/', {})
    assert book_resp.status_code == 201, book_resp.data
    booking_id = book_resp.data['booking_id']
    razorpay_order_id = book_resp.data['razorpay_order_id']

    # Booking should be in pending_payment state
    booking = Booking.objects.get(pk=booking_id)
    assert booking.status == 'pending_payment'

    # Step 2: Student verifies payment
    verify_resp = student_client.post('/api/sessions/payment/verify/', {
        'booking_id': booking_id,
        'razorpay_order_id': razorpay_order_id,
        'razorpay_payment_id': 'pay_integration_001',
        'razorpay_signature': 'sig_integration_001',
    })
    assert verify_resp.status_code == 200, verify_resp.data

    # Step 3: Booking should now be confirmed
    booking.refresh_from_db()
    assert booking.status == 'confirmed'

    # Step 4: Signal should have updated alumni wallet_balance (70% of 500 = 350)
    profile = AlumniProfile.objects.get(user=verified_alumni)
    assert float(profile.wallet_balance) == pytest.approx(350.0, abs=0.01)

    # Step 5: Notifications should have been created for both parties
    assert Notification.objects.filter(
        recipient=verified_student, notif_type='booking_confirmed'
    ).exists()
    assert Notification.objects.filter(
        recipient=verified_alumni, notif_type='new_booking'
    ).exists()


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Referral application → h auto-created
# Alumni posts referral → student applies → alumni updates status to 'hired' →
# signal creates ReferralSuccessStory and bumps alumni impact_score
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_referral_hired_creates_success_story(verified_alumni, verified_student):
    """Updating application to 'hired' auto-creates a ReferralSuccessStory."""
    AlumniProfile.objects.get_or_create(user=verified_alumni)
    StudentProfile.objects.get_or_create(user=verified_student)

    s
    alumni_client = _make_client(verified_alumni)

    # Alumni posts a referral
    referral = Referral.objects.create(
        posted_by=verified_alumni,
        company_name='IntegrationCorp',
        job_title='Django Developer',
        job_description='Looking for a Django developer with REST API experience and PostgreSQL knowledge.',
        work_type='full_time',
        experience_level='fresher',
        location='Bangalore',
        required_skills=['Python', 'Django'],
        max_applicants=10,
        deadline=timezone.now() + timedelta(days=7),
        status='active',
    )

    # Student applies
    apply_resp = student_client.post(f'/api/referrals/{referral.pk}/apply/', {
        'cover_note': 'I am a great fit for this role.',
    })
    assert apply_resp.status_code == 201, apply_resp.data
    application_id = apply_resp.data['application']['id']

    # Alumni updates status to 'hired'
    update_resp = alumni_client.patch(
        f'/api/referrals/applications/{application_id}/update/',
        {'status': 'hired'},
        format='json',
    )
    assert update_resp.status_code == 200, update_resp.data

    # Success story should be auto-created by signal
    assert ReferralSuccessStory.objects.filter(
        application_id=application_id,
        company_name='IntegrationCorp',
    ).exists()

    # Alumni impact_score should have increased by 5
    profile = AlumniProfile.objects.get(user=verified_alumni)
    assert profile.impact_score >= 5


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Admin payout processing flow
# Alumni requests payout → admin approves → admin processes with reference
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_admin_payout_processing_flow(verified_alumni):
    """Admin can approve and process a payout request."""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    AlumniProfile.objects.get_or_create(user=verified_alumni)

    # Create admin user
    admin_user, _ = User.objects.get_or_create(
        email='integration_admin@alumniai.com',
        defaults={
            'username': 'integration_admin',
            'role': 'admin',
            'first_name': 'Integration',
            'last_name': 'Admin',
            'is_verified': True,
 
    payout = PayoutRequest.objects.get(pk=payout_id)
    assert payout.status == 'approved'

    # Admin processes with transaction reference
    process_resp = admin_api_client.patch(
        f'/api/payments/admin/payouts/{payout_id}/',
        {
            'action': 'process',
            'transaction_reference': 'UTR123456789',
            'admin_note': 'Transferred via NEFT',
        },
        format='json',
    )
    assert process_resp.status_code == 200, process_resp.data

    payout.refresh_from_db()
    assert payout.status == 'processed'
    assert payout.transaction_reference == 'UTR123456789'


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: Notification preference respected
# Student disables 'in_app_session_booked' → books a free session →
# no booking_confirmed notification created
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_notification_preference_respected(student_api_client, verified_alumni, verified_student):
    """Disabling in_app_session_booked prevents booking_confirmed notifications."""
    AlumniProfile.objects.get_or_create(user=verified_alumni)
    StudentProfile.objects.get_or_create(user=verified_student)

    # Disable booking notifications for student
    pref, _ = NotificationPreference.objects.get_or_create(user=verified_student)
    pref.in_app_session_booked = False
    pref.save(update_fields=['in_app_session_booked'])

    # Create a free session
    session = Session.objects.create(
        host=verified_alumni,
        session_type='group',
        title='Free Notification Test Session',
        description='Free session to test notification preference suppression.',
        niche='Python',
        scheduled_at=timezone.now() + timedelta(days=2),
        duration_minutes=30,
        price=Decimal('0.00'),
        is_free=True,
        max_seats=50,
        status='upcoming',
    )

    # Student books the free session
    book_resp = student_api_client.post(f'/api/sessions/{session.pk}/book/', {})
    assert book_resp.status_code == 201, book_resp.data
    assert book_resp.data['booking_confirmed'] is True

    # booking_confirmed notification should NOT be created for student
    assert not Notification.objects.filter(
        recipient=verified_student,
        notif_type='booking_confirmed',
    ).exists()


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: Faculty recommendation flow
# Faculty recommends a student for a referral → alumni gets notified →
# application is marked as faculty recommended
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_faculty_recommendation_flow(
    faculty_api_client, student_api_client, alumni_api_client,
    verified_faculty, verified_student, verified_alumni,
):
    """Faculty can recommend a student; alumni gets notified and application is flagged."""
    AlumniProfile.objects.get_or_create(user=verified_alumni)
    StudentProfile.objects.get_or_create(user=verified_student)

    # Alumni posts referral
    referral = Referral.objects.create(
        posted_by=verified_alumni,
        company_name='FacultyTestCorp',
        job_title='Backend Engineer',
        job_description='Backend engineer role requiring Python, Django, REST APIs and database skills.',
        work_type='full_time',
        experience_level='fresher',
        location='Hyderabad',
        required_skills=['Python', 'Django'],
        max_applicants=10,
        deadline=timezone.now() + timedelta(days=7),
        status='active',
    )

    # Student applies first
    apply_resp = student_api_client.post(f'/api/referrals/{referral.pk}/apply/', {
        'cover_note': 'Interested in this role.',
    })
    assert apply_resp.status_code == 201, apply_resp.data

    # Faculty recommends the student
    rec_resp = faculty_api_client.post(f'/api/referrals/{referral.pk}/recommend/', {
        'student_id': verified_student.pk,
        'note': 'Excellent student, highly recommended.',
    }, format='json')
    assert rec_resp.status_code in (200, 201), rec_resp.data

    # Application should be marked as faculty recommended
    application = ReferralApplication.objects.get(
        referral=referral, student=verified_student
    )
    assert application.is_faculty_recommended is True

    # Alumni should receive a notification about the recommendation
    assert Notification.objects.filter(
        recipient=verified_alumni,
        notif_type='referral',
        title__icontains='recommendation',
    ).exists()


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: Suspended user gets 403 on API access
# User is suspended (is_active=False) → JWT middleware returns 403
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
def test_suspended_user_blocked(student_api_client, verified_student):
    """A suspended (is_active=False) user is blocked with 403 by JWTAuthMiddleware."""
    # Confirm access works before suspension
    resp = student_api_client.get('/api/sessions/')
    assert resp.status_code == 200

    # Suspend the user
    verified_student.is_active = False
    verified_student.save(update_fields=['is_active'])

    # Subsequent requests should be blocked
    resp = student_api_client.get('/api/sessions/')
    assert resp.status_code == 403
