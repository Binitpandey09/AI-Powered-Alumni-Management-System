import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

User = get_user_model()

@pytest.fixture
def full_client_set(verified_student, verified_alumni, verified_faculty):
    """Returns authenticated API clients for all 3 roles"""
    clients = {}
    for user, role in [(verified_student, 'student'), (verified_alumni, 'alumni'), (verified_faculty, 'faculty')]:
        client = APIClient()
        refresh = RefreshToken.for_user(user)
        client.credentials(HTTP_AUTHORIZATION='Bearer ' + str(refresh.access_token))
        client._user = user
        clients[role] = client
    return clients

# ── Integration Test 1: Full session booking flow ──
@pytest.mark.django_db
def test_complete_session_booking_flow(full_client_set, verified_alumni, verified_student):
    """
    Tests the complete flow: alumni creates session → student books → payment verified → wallet updated
    """
    from apps.sessions_app.models import Session, Booking
    from apps.payments.models import Wallet
    from apps.notifications.models import Notification

    alumni_client = full_client_set['alumni']
    student_client = full_client_set['student']

    # Step 1: Alumni creates a session
    session_payload = {
        'session_type': 'group',
        'title': 'Integration Test Session',
        'description': 'End-to-end test session for integration testing purposes.',
        'niche': 'Testing',
        'skills_covered': ['Python', 'Django'],
        'scheduled_at': (timezone.now() + timedelta(days=5)).isoformat(),
        'duration_minutes': 60,
        'price': '299.00',
        'max_seats': 10,
        'is_free': False,
    }
    import unittest.mock as mock
    with mock.patch('apps.sessions_app.tasks.schedule_session_tasks.delay'):
        create_response = alumni_client.post('/api/sessions/', session_payload, format='json')
    assert create_response.status_code == 201, f"Session creation failed: {create_response.data}"
    session_id = create_response.data['id']

    # Step 2: Student views the session
    view_response = student_client.get(f'/api/sessions/{session_id}/')
    assert view_response.status_code == 200
    assert view_response.data['title'] == 'Integration Test Session'
    assert view_response.data['is_booked'] is False

    # Step 3: Student initiates booking (gets Razorpay order)
    # Mock Razorpay
    import unittest.mock as mock
    with mock.patch('apps.sessions_app.views.razorpay.Client') as mock_client:
        mock_client.return_value.order.create.return_value = {
            'id': 'order_integration_test_001',
            'amount': 29900,
            'currency': 'INR',
        }
        book_response = student_client.post(f'/api/sessions/{session_id}/book/', {}, format='json')

    print("DEBUG BOOKING RESPONSE:", book_response.data)
    assert book_response.status_code == 201
    booking_id = book_response.data['booking_id']
    razorpay_order_id = book_response.data['razorpay_order_id']

    booking = Booking.objects.get(id=booking_id)
    assert booking.status == 'pending_payment'

    # Step 4: Payment verification
    with mock.patch('utils.payment_utils.razorpay.Client') as mock_client:
        mock_client.return_value.utility.verify_payment_signature.return_value = True
        verify_response = student_client.post('/api/sessions/payment/verify/', {
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': 'pay_integration_001',
            'razorpay_signature': 'sig_integration_001',
            'booking_id': booking_id,
        }, format='json')

    assert verify_response.status_code == 200

    # Step 5: Verify booking is confirmed
    booking.refresh_from_db()
    assert booking.status == 'confirmed'

    # Manually trigger session completion to update host wallet
    from apps.sessions_app.tasks import mark_session_completed
    mark_session_completed(session_id)

    # Step 6: Verify wallet was updated (70% of 299 = 209.30)
    wallet, _ = Wallet.objects.get_or_create(user=verified_alumni)
    assert wallet.balance >= Decimal('209.30')

    # Step 7: Verify notifications were sent
    student_notifs = Notification.objects.filter(recipient=verified_student, notif_type='booking_confirmed')
    assert student_notifs.count() >= 1
    alumni_notifs = Notification.objects.filter(recipient=verified_alumni, notif_type='new_booking')
    assert alumni_notifs.count() >= 1

    # Step 8: Session shows as booked when student views it again
    view_response2 = student_client.get(f'/api/sessions/{session_id}/')
    assert view_response2.data['is_booked'] is True

    print('Integration Test 1: Complete session booking flow PASSED')


# ── Integration Test 2: Full referral application flow ──
@pytest.mark.django_db
def test_complete_referral_flow(full_client_set, verified_alumni, verified_student, verified_faculty):
    """
    Tests: alumni posts referral → faculty recommends student → student applies → alumni accepts → success story created
    """
    from apps.referrals.models import Referral, ReferralApplication, ReferralSuccessStory
    from apps.notifications.models import Notification

    alumni_client = full_client_set['alumni']
    student_client = full_client_set['student']
    faculty_client = full_client_set['faculty']

    # Set student skills to match referral
    try:
        sp = verified_student.student_profile
        sp.skills = ['Python', 'Django', 'REST API', 'PostgreSQL', 'Git']
        sp.save(update_fields=['skills'])
    except Exception:
        pass

    # Step 1: Alumni posts a referral
    referral_payload = {
        'company_name': 'Integration Corp',
        'job_title': 'Backend Developer',
        'job_description': 'We need a Python backend developer for our product team. Must have Django and REST API experience.',
        'work_type': 'full_time',
        'experience_level': 'fresher',
        'location': 'Bangalore',
        'required_skills': ['Python', 'Django', 'REST API'],
        'preferred_skills': ['PostgreSQL', 'Git'],
        'max_applicants': 3,
        'deadline': (timezone.now() + timedelta(days=7)).isoformat(),
    }
    create_r = alumni_client.post('/api/referrals/', referral_payload, format='json')
    assert create_r.status_code == 201
    referral_id = create_r.data['id']

    # Step 2: Student checks their match score
    match_r = student_client.get(f'/api/referrals/{referral_id}/match-check/')
    assert match_r.status_code == 200
    assert match_r.data['score'] >= 40
    assert match_r.data['can_apply'] is True

    # Step 3: Faculty recommends the student
    recommend_r = faculty_client.post(f'/api/referrals/{referral_id}/recommend/', {
        'student_id': verified_student.id,
        'note': 'Excellent student with strong Python background.',
    }, format='json')
    assert recommend_r.status_code == 201

    # Verify alumni was notified about recommendation
    rec_notif = Notification.objects.filter(
        recipient=verified_alumni,
        notif_type='general',
        message__icontains='recommend'
    )
    assert rec_notif.count() >= 1

    # Step 4: Student applies to the referral
    apply_r = student_client.post(f'/api/referrals/{referral_id}/apply/', {
        'cover_note': 'I am very interested in this role. Python and Django are my core skills.'
    }, format='json')
    assert apply_r.status_code == 201
    assert apply_r.data['can_apply'] is True
    assert apply_r.data['match_score'] >= 40

    # Step 5: Verify application exists with faculty recommendation flag
    application = ReferralApplication.objects.get(referral_id=referral_id, student=verified_student)
    assert application.status == 'applied'
    assert application.is_faculty_recommended is True

    # Step 6: Referral total_applications incremented
    referral = Referral.objects.get(id=referral_id)
    assert referral.total_applications == 1

    # Step 7: Alumni views applications
    apps_r = alumni_client.get(f'/api/referrals/{referral_id}/applications/')
    assert apps_r.status_code == 200
    assert apps_r.data['total'] == 1

    # Step 8: Alumni shortlists the student
    shortlist_r = alumni_client.patch(f'/api/referrals/applications/{application.id}/update/', {
        'status': 'shortlisted',
        'alumni_note': 'Great profile, moving forward.',
    }, format='json')
    assert shortlist_r.status_code == 200
    application.refresh_from_db()
    assert application.status == 'shortlisted'

    # Step 9: Student was notified of shortlist
    shortlist_notif = Notification.objects.filter(
        recipient=verified_student,
        message__icontains='shortlisted'
    )
    assert shortlist_notif.count() >= 1

    # Step 10: Alumni marks as hired
    hire_r = alumni_client.patch(f'/api/referrals/applications/{application.id}/update/', {
        'status': 'hired',
        'alumni_note': 'Congratulations! You are selected.',
    }, format='json')
    assert hire_r.status_code == 200

    # Step 11: Success story created automatically
    assert ReferralSuccessStory.objects.filter(application=application).exists()

    print('Integration Test 2: Complete referral flow PASSED')


# ── Integration Test 3: Alumni earnings flow ──
@pytest.mark.django_db
def test_alumni_earnings_and_payout_flow(full_client_set, verified_alumni):
    """
    Tests: booking confirmed → wallet updated → payout requested → admin processes
    """
    from apps.payments.models import Wallet, PayoutRequest, Transaction
    from django.contrib.auth import get_user_model

    alumni_client = full_client_set['alumni']

    # Get or create wallet with balance
    wallet, _ = Wallet.objects.get_or_create(user=verified_alumni)
    wallet.balance = Decimal('1500.00')
    wallet.total_earned = Decimal('3000.00')
    wallet.save()

    # Add bank details
    try:
        profile = verified_alumni.alumni_profile
        profile.bank_details = {
            'account_holder_name': 'Dev Alumni',
            'bank_name': 'HDFC Bank',
            'account_number': '50100123456789',
            'ifsc_code': 'HDFC0001234',
        }
        profile.bank_verified = True
        profile.save(update_fields=['bank_details', 'bank_verified'])
    except Exception:
        pass

    # Request payout
    payout_r = alumni_client.post('/api/payments/payout/', {'amount': '500.00'}, format='json')
    assert payout_r.status_code == 201

    # Verify wallet locked
    wallet.refresh_from_db()
    assert wallet.pending_withdrawal == Decimal('500.00')
    assert wallet.available_for_withdrawal == Decimal('1000.00')

    # Cannot request another payout while one is pending
    second_r = alumni_client.post('/api/payments/payout/', {'amount': '500.00'}, format='json')
    assert second_r.status_code == 400
    assert 'pending' in str(second_r.data).lower()

    # Admin processes payout
    User = get_user_model()
    try:
        admin = User.objects.get(email='test.admin@alumniai.com')
    except User.DoesNotExist:
        admin = User.objects.create_user(
            username='test.admin@alumniai.com', email='test.admin@alumniai.com',
            password='DevPass@123', role='admin', is_verified=True,
        )
    admin_client = APIClient()
    refresh = RefreshToken.for_user(admin)
    admin_client.credentials(HTTP_AUTHORIZATION='Bearer ' + str(refresh.access_token))

    payout = PayoutRequest.objects.get(user=verified_alumni, status='pending')
    process_r = admin_client.patch(f'/api/payments/admin/payouts/{payout.id}/', {
        'action': 'process',
        'transaction_reference': 'NEFT20250328001',
        'admin_note': 'Processed via NEFT',
    }, format='json')
    assert process_r.status_code == 200

    # Wallet balance reduced, pending cleared
    wallet.refresh_from_db()
    assert wallet.balance == Decimal('1000.00')
    assert wallet.total_withdrawn == Decimal('500.00')
    assert wallet.pending_withdrawal == Decimal('0.00')

    print('Integration Test 3: Alumni earnings and payout flow PASSED')


# ── Integration Test 4: Notification preferences respected ──
@pytest.mark.django_db
def test_notification_preferences_block_creation(verified_student):
    """
    Tests that turning off a notification type prevents notification creation
    """
    from apps.notifications.models import Notification, NotificationPreference
    from utils.notify import send_notification

    # Turn off session_booked in-app notification
    pref, _ = NotificationPreference.objects.get_or_create(user=verified_student)
    pref.in_app_session_booked = False
    pref.save()

    count_before = Notification.objects.filter(recipient=verified_student).count()

    send_notification(
        recipient=verified_student,
        notif_type='session_booked',
        title='Should not appear',
        message='This should be blocked by preference.',
    )

    assert Notification.objects.filter(recipient=verified_student).count() == count_before
    print('Integration Test 4: Notification preference blocking PASSED')


# ── Integration Test 5: Security — suspended user blocked ──
@pytest.mark.django_db
def test_suspended_user_blocked_from_all_endpoints(verified_student):
    """Suspended user must be blocked from all API endpoints"""
    from rest_framework_simplejwt.tokens import RefreshToken

    verified_student.is_suspended = True
    verified_student.suspended_reason = 'Integration test suspension'
    verified_student.save()

    client = APIClient()
    refresh = RefreshToken.for_user(verified_student)
    client.credentials(HTTP_AUTHORIZATION='Bearer ' + str(refresh.access_token))

    protected_endpoints = [
        '/api/accounts/me/',
        '/api/feed/',
        '/api/sessions/',
        '/api/notifications/',
    ]

    for endpoint in protected_endpoints:
        r = client.get(endpoint)
        assert r.status_code == 403, f'{endpoint} should return 403 for suspended user, got {r.status_code}'

    print('Integration Test 5: Suspended user blocked from all endpoints PASSED')


# ── Integration Test 6: Admin cannot be deleted or suspended ──
@pytest.mark.django_db
def test_admin_protected_from_suspension():
    """Admin users cannot be suspended or deleted by another admin"""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    admin1 = User.objects.get_or_create(
        email='admin1@alumniai.com',
        defaults={'username': 'admin1@alumniai.com', 'role': 'admin', 'is_verified': True}
    )[0]
    admin2 = User.objects.get_or_create(
        email='admin2@alumniai.com',
        defaults={'username': 'admin2@alumniai.com', 'role': 'admin', 'is_verified': True}
    )[0]

    client = APIClient()
    refresh = RefreshToken.for_user(admin1)
    client.credentials(HTTP_AUTHORIZATION='Bearer ' + str(refresh.access_token))

    r = client.post(f'/api/dashboard/admin/users/{admin2.id}/action/', {'action': 'suspend'}, format='json')
    assert r.status_code == 400

    r2 = client.post(f'/api/dashboard/admin/users/{admin2.id}/action/', {'action': 'delete'}, format='json')
    assert r2.status_code == 400

    print('Integration Test 6: Admin protection PASSED')
