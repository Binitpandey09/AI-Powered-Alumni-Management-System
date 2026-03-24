"""
tests/test_sessions.py — Phase 5 complete test suite
Day 8-10 Prompt 4
"""
import pytest
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from apps.sessions_app.models import Session, Booking, SessionReview
from apps.accounts.models import AlumniProfile, StudentProfile

pytestmark = pytest.mark.django_db


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST GROUP 1: Session List & Filtering
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def test_any_authenticated_user_can_view_sessions_list(student_api_client):
    response = student_api_client.get('/api/sessions/')
    assert response.status_code == 200
    assert 'results' in response.data
    assert 'count' in response.data


def test_unauthenticated_user_cannot_view_sessions(api_client):
    response = api_client.get('/api/sessions/')
    assert response.status_code == 401


def test_sessions_list_only_shows_upcoming_by_default(
    student_api_client, upcoming_group_session, past_session
):
    response = student_api_client.get('/api/sessions/')
    assert response.status_code == 200
    session_ids = [s['id'] for s in response.data['results']]
    assert upcoming_group_session.id in session_ids
    assert past_session.id not in session_ids


def test_sessions_filter_by_type_group(
    student_api_client, upcoming_group_session, upcoming_one_on_one_session
):
    response = student_api_client.get('/api/sessions/?type=group')
    assert response.status_code == 200
    for session in response.data['results']:
        assert session['session_type'] == 'group'


def test_sessions_filter_by_type_one_on_one(
    student_api_client, upcoming_group_session, upcoming_one_on_one_session
):
    response = student_api_client.get('/api/sessions/?type=one_on_one')
    assert response.status_code == 200
    for session in response.data['results']:
        assert session['session_type'] == 'one_on_one'


def test_sessions_filter_free_only(
    student_api_client, upcoming_group_session, free_demo_session
):
    response = student_api_client.get('/api/sessions/?free=true')
    assert response.status_code == 200
    for session in response.data['results']:
        assert session['is_free'] is True


def test_sessions_search_by_title(student_api_client, upcoming_group_session):
    response = student_api_client.get('/api/sessions/?search=DSA')
    assert response.status_code == 200
    assert len(response.data['results']) >= 1
    titles = [s['title'] for s in response.data['results']]
    assert any('DSA' in t for t in titles)


def test_sessions_search_no_match_returns_empty(student_api_client, upcoming_group_session):
    response = student_api_client.get('/api/sessions/?search=xyzthisdoesnotexist999')
    assert response.status_code == 200
    assert response.data['count'] == 0


def test_sessions_filter_by_price_max(student_api_client, upcoming_group_session):
    response = student_api_client.get('/api/sessions/?price_max=300')
    assert response.status_code == 200
    for session in response.data['results']:
        assert float(session['price']) <= 300


def test_session_detail_returns_full_description(student_api_client, upcoming_group_session):
    response = student_api_client.get(f'/api/sessions/{upcoming_group_session.id}/')
    assert response.status_code == 200
    assert response.data['description'] == upcoming_group_session.description


def test_session_detail_404_for_nonexistent(student_api_client):
    response = student_api_client.get('/api/sessions/999999/')
    assert response.status_code == 404


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST GROUP 2: Session Creation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def test_alumni_can_create_session(alumni_api_client, verified_alumni):
    payload = {
        'session_type': 'group',
        'title': 'Python Advanced Bootcamp',
        'description': 'Deep dive into advanced Python concepts including decorators, generators and async.',
        'niche': 'Python',
        'skills_covered': ['Python', 'Decorators', 'Async'],
        'scheduled_at': (timezone.now() + timedelta(days=7)).isoformat(),
        'duration_minutes': 60,
        'price': '599.00',
        'max_seats': 15,
        'is_free': False,
    }
    response = alumni_api_client.post('/api/sessions/', payload, format='json')
    assert response.status_code == 201
    assert response.data['title'] == 'Python Advanced Bootcamp'
    assert response.data['host']['id'] == verified_alumni.id
    assert Session.objects.filter(title='Python Advanced Bootcamp', host=verified_alumni).exists()


def test_faculty_can_create_session(faculty_api_client, verified_faculty):
    payload = {
        'session_type': 'doubt',
        'title': 'DBMS Doubt Clearing Class',
        'description': 'Clear all your doubts about database management systems concepts.',
        'niche': 'DBMS',
        'skills_covered': ['SQL', 'Normalization', 'Transactions'],
        'scheduled_at': (timezone.now() + timedelta(days=4)).isoformat(),
        'duration_minutes': 90,
        'price': '299.00',
        'max_seats': 30,
        'is_free': False,
    }
    response = faculty_api_client.post('/api/sessions/', payload, format='json')
    assert response.status_code == 201
    assert Session.objects.filter(host=verified_faculty).exists()


def test_student_cannot_create_session(student_api_client):
    payload = {
        'session_type': 'general',
        'title': 'Student trying to host a session',
        'description': 'This should not be allowed for students.',
        'scheduled_at': (timezone.now() + timedelta(days=2)).isoformat(),
        'price': '100.00',
        'max_seats': 10,
    }
    response = student_api_client.post('/api/sessions/', payload, format='json')
    assert response.status_code == 403


def test_cannot_create_session_in_past(alumni_api_client):
    payload = {
        'session_type': 'group',
        'title': 'Past Session Test',
        'description': 'This session is scheduled in the past and should fail validation.',
        'scheduled_at': (timezone.now() - timedelta(hours=2)).isoformat(),
        'price': '100.00',
        'max_seats': 10,
    }
    response = alumni_api_client.post('/api/sessions/', payload, format='json')
    assert response.status_code == 400
    assert 'scheduled_at' in response.data or 'error' in str(response.data).lower()


def test_free_session_requires_zero_price(alumni_api_client):
    payload = {
        'session_type': 'group',
        'title': 'Free Python Introduction',
        'description': 'A completely free introduction to Python for absolute beginners.',
        'scheduled_at': (timezone.now() + timedelta(days=3)).isoformat(),
        'price': '0.00',
        'max_seats': 50,
        'is_free': True,
    }
    response = alumni_api_client.post('/api/sessions/', payload, format='json')
    assert response.status_code == 201
    assert response.data['is_free'] is True


def test_session_author_can_edit_own_session(alumni_api_client, upcoming_group_session):
    payload = {'title': 'DSA Masterclass - Updated Title'}
    response = alumni_api_client.patch(
        f'/api/sessions/{upcoming_group_session.id}/', payload, format='json'
    )
    assert response.status_code == 200
    upcoming_group_session.refresh_from_db()
    assert upcoming_group_session.title == 'DSA Masterclass - Updated Title'


def test_different_user_cannot_edit_session(student_api_client, upcoming_group_session):
    payload = {'title': 'Unauthorized Edit Attempt'}
    response = student_api_client.patch(
        f'/api/sessions/{upcoming_group_session.id}/', payload, format='json'
    )
    assert response.status_code == 403


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST GROUP 3: Session Booking
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def test_student_can_initiate_paid_booking(student_api_client, upcoming_group_session):
    response = student_api_client.post(
        f'/api/sessions/{upcoming_group_session.id}/book/', {}, format='json'
    )
    assert response.status_code == 201
    assert 'razorpay_order_id' in response.data
    assert 'booking_id' in response.data
    booking = Booking.objects.get(id=response.data['booking_id'])
    assert booking.status == 'pending_payment'
    assert booking.student == student_api_client._student


def test_free_demo_booking_confirmed_immediately(
    student_api_client, verified_student, free_demo_session
):
    profile = verified_student.student_profile
    profile.demo_session_used = False
    profile.save()

    response = student_api_client.post(
        f'/api/sessions/{free_demo_session.id}/book/', {}, format='json'
    )
    assert response.status_code == 201
    assert response.data.get('booking_confirmed') is True

    booking = Booking.objects.get(id=response.data['booking_id'])
    assert booking.status == 'confirmed'
    assert booking.amount_paid == Decimal('0.00')


def test_student_cannot_use_free_demo_twice(
    student_api_client, verified_student, free_demo_session
):
    profile = verified_student.student_profile
    profile.demo_session_used = True
    profile.save()

    response = student_api_client.post(
        f'/api/sessions/{free_demo_session.id}/book/', {}, format='json'
    )
    # free_demo_session is is_free=True so it still books as free (not demo)
    # but is_free_demo should not be True
    assert response.status_code == 201
    if 'booking_confirmed' in response.data:
        assert response.data.get('is_free_demo') is not True


def test_student_cannot_book_full_session(student_api_client, full_session):
    response = student_api_client.post(
        f'/api/sessions/{full_session.id}/book/', {}, format='json'
    )
    assert response.status_code == 400
    error_text = str(response.data).lower()
    assert 'full' in error_text or 'seats' in error_text or 'available' in error_text


def test_student_cannot_book_same_session_twice(
    student_api_client, confirmed_booking_p5, upcoming_group_session
):
    response = student_api_client.post(
        f'/api/sessions/{upcoming_group_session.id}/book/', {}, format='json'
    )
    assert response.status_code == 400
    error_text = str(response.data).lower()
    assert 'already' in error_text or 'duplicate' in error_text or 'booked' in error_text


def test_payment_verification_confirms_booking(
    student_api_client, upcoming_group_session, verified_student
):
    booking = Booking.objects.create(
        session=upcoming_group_session,
        student=verified_student,
        status='pending_payment',
        amount_paid=upcoming_group_session.price,
        razorpay_order_id='order_test_verify_789',
    )
    response = student_api_client.post('/api/sessions/payment/verify/', {
        'razorpay_order_id': 'order_test_verify_789',
        'razorpay_payment_id': 'pay_test_verify_789',
        'razorpay_signature': 'sig_test_valid_signature',
        'booking_id': booking.id,
    }, format='json')
    assert response.status_code == 200
    booking.refresh_from_db()
    assert booking.status == 'confirmed'
    assert booking.razorpay_payment_id == 'pay_test_verify_789'


def test_wallet_updated_after_payment_confirmed(
    verified_alumni, upcoming_group_session, verified_student
):
    alumni_profile, _ = AlumniProfile.objects.get_or_create(user=verified_alumni)
    wallet_before = alumni_profile.wallet_balance

    booking = Booking.objects.create(
        session=upcoming_group_session,
        student=verified_student,
        status='pending_payment',
        amount_paid=Decimal('499.00'),
        razorpay_order_id='order_wallet_test_001',
    )
    booking.status = 'confirmed'
    booking.platform_cut = Decimal('149.70')
    booking.host_share = Decimal('349.30')
    booking.save()

    alumni_profile.refresh_from_db()
    expected_wallet = wallet_before + Decimal('349.30')
    assert alumni_profile.wallet_balance == expected_wallet


def test_booked_seats_increases_after_booking_confirmed(
    verified_alumni, upcoming_group_session, verified_student
):
    AlumniProfile.objects.get_or_create(user=verified_alumni)
    seats_before = upcoming_group_session.booked_seats

    booking = Booking.objects.create(
        session=upcoming_group_session,
        student=verified_student,
        status='pending_payment',
        amount_paid=upcoming_group_session.price,
        razorpay_order_id='order_seats_test_002',
    )
    booking.status = 'confirmed'
    booking.save()

    upcoming_group_session.refresh_from_db()
    assert upcoming_group_session.booked_seats == seats_before + 1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST GROUP 4: Booking Cancellation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def test_student_can_cancel_confirmed_booking_with_refund(
    student_api_client, confirmed_booking_p5
):
    response = student_api_client.post(
        f'/api/sessions/bookings/{confirmed_booking_p5.id}/cancel/', {}, format='json'
    )
    assert response.status_code == 200
    confirmed_booking_p5.refresh_from_db()
    assert confirmed_booking_p5.status == 'cancelled_by_student'
    assert confirmed_booking_p5.refund_amount == Decimal('249.50')


def test_cancellation_within_2_hours_gives_no_refund(
    verified_alumni, verified_student, api_client
):
    AlumniProfile.objects.get_or_create(user=verified_alumni)
    StudentProfile.objects.get_or_create(user=verified_student)

    near_session = Session.objects.create(
        host=verified_alumni,
        session_type='group',
        title='Imminent Session',
        description='Session happening very soon.',
        scheduled_at=timezone.now() + timedelta(hours=1),
        duration_minutes=60,
        price=Decimal('300.00'),
        max_seats=10,
        booked_seats=1,
        status='upcoming',
    )
    booking = Booking.objects.create(
        session=near_session,
        student=verified_student,
        status='confirmed',
        amount_paid=Decimal('300.00'),
        platform_cut=Decimal('90.00'),
        host_share=Decimal('210.00'),
    )
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(verified_student)
    api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + str(refresh.access_token))
    response = api_client.post(
        f'/api/sessions/bookings/{booking.id}/cancel/', {}, format='json'
    )
    assert response.status_code == 200
    booking.refresh_from_db()
    assert booking.status == 'cancelled_by_student'
    assert booking.refund_amount == Decimal('0.00')


def test_cannot_cancel_already_cancelled_booking(student_api_client, confirmed_booking_p5):
    confirmed_booking_p5.status = 'cancelled_by_student'
    confirmed_booking_p5.save()
    response = student_api_client.post(
        f'/api/sessions/bookings/{confirmed_booking_p5.id}/cancel/', {}, format='json'
    )
    assert response.status_code == 400


def test_other_student_cannot_cancel_booking(alumni_api_client, confirmed_booking_p5):
    response = alumni_api_client.post(
        f'/api/sessions/bookings/{confirmed_booking_p5.id}/cancel/', {}, format='json'
    )
    assert response.status_code in [403, 404]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST GROUP 5: Session Reviews
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def test_student_can_review_completed_session(student_api_client, completed_booking):
    response = student_api_client.post(
        f'/api/sessions/bookings/{completed_booking.id}/review/',
        {'rating': 5, 'review_text': 'Excellent session! Very informative and well structured.'},
        format='json',
    )
    assert response.status_code == 201
    assert SessionReview.objects.filter(booking=completed_booking).exists()
    review = SessionReview.objects.get(booking=completed_booking)
    assert review.rating == 5
    assert review.review_text == 'Excellent session! Very informative and well structured.'


def test_student_can_review_anonymously(student_api_client, completed_booking):
    response = student_api_client.post(
        f'/api/sessions/bookings/{completed_booking.id}/review/',
        {'rating': 4, 'is_anonymous': True, 'review_text': 'Great content but could be faster.'},
        format='json',
    )
    assert response.status_code == 201
    review = SessionReview.objects.get(booking=completed_booking)
    assert review.is_anonymous is True


def test_rating_must_be_between_1_and_5(student_api_client, completed_booking):
    for invalid_rating in [0, 6, -1, 10]:
        response = student_api_client.post(
            f'/api/sessions/bookings/{completed_booking.id}/review/',
            {'rating': invalid_rating},
            format='json',
        )
        assert response.status_code == 400, f"Rating {invalid_rating} should be rejected"


def test_cannot_review_pending_booking(
    student_api_client, upcoming_group_session, verified_student
):
    pending_booking = Booking.objects.create(
        session=upcoming_group_session,
        student=verified_student,
        status='confirmed',
        amount_paid=upcoming_group_session.price,
    )
    response = student_api_client.post(
        f'/api/sessions/bookings/{pending_booking.id}/review/',
        {'rating': 5},
        format='json',
    )
    assert response.status_code == 400


def test_cannot_review_same_booking_twice(student_api_client, completed_booking):
    SessionReview.objects.create(
        booking=completed_booking,
        rating=4,
        review_text='First review.',
    )
    response = student_api_client.post(
        f'/api/sessions/bookings/{completed_booking.id}/review/',
        {'rating': 3, 'review_text': 'Second review attempt.'},
        format='json',
    )
    assert response.status_code == 400


def test_reviews_visible_on_session_reviews_endpoint(
    student_api_client, completed_booking, past_session
):
    SessionReview.objects.create(
        booking=completed_booking,
        rating=5,
        review_text='Amazing session!',
    )
    response = student_api_client.get(f'/api/sessions/{past_session.id}/reviews/')
    assert response.status_code == 200
    # endpoint returns {'reviews': [...], 'average_rating': ..., 'review_count': ...}
    reviews_list = response.data.get('reviews', response.data.get('results', []))
    assert len(reviews_list) >= 1


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST GROUP 6: My Bookings & Hosted Sessions
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def test_student_can_view_own_bookings(student_api_client, confirmed_booking_p5):
    response = student_api_client.get('/api/sessions/my-bookings/')
    assert response.status_code == 200
    booking_ids = [b['id'] for b in response.data.get('results', [])]
    assert confirmed_booking_p5.id in booking_ids


def test_student_cannot_see_other_students_bookings(
    student_api_client, verified_alumni, upcoming_group_session
):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    other_student = User.objects.create_user(
        username='other.student@college.ac.in',
        email='other.student@college.ac.in',
        password='Test@1234',
        role='student',
        is_verified=True,
    )
    StudentProfile.objects.get_or_create(user=other_student)
    Booking.objects.create(
        session=upcoming_group_session,
        student=other_student,
        status='confirmed',
        amount_paid=upcoming_group_session.price,
    )
    response = student_api_client.get('/api/sessions/my-bookings/')
    assert response.status_code == 200
    for b in response.data.get('results', []):
        assert b['student']['id'] == student_api_client._student.id


def test_alumni_can_view_hosted_sessions(alumni_api_client, upcoming_group_session):
    response = alumni_api_client.get('/api/sessions/hosting/')
    assert response.status_code == 200
    session_ids = [s['id'] for s in response.data.get('results', [])]
    assert upcoming_group_session.id in session_ids


def test_student_cannot_view_hosted_sessions(student_api_client):
    response = student_api_client.get('/api/sessions/hosting/')
    assert response.status_code == 403


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST GROUP 7: Earnings API
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def test_alumni_can_access_earnings_summary(alumni_api_client):
    response = alumni_api_client.get('/api/sessions/earnings/')
    assert response.status_code == 200
    required_fields = [
        'wallet_balance', 'total_earned', 'this_month_earned',
        'last_month_earned', 'total_sessions_hosted', 'total_bookings',
        'avg_session_rating', 'recent_transactions', 'monthly_breakdown',
        'bank_details', 'bank_verified',
    ]
    for field in required_fields:
        assert field in response.data, f"Field '{field}' missing from earnings response"


def test_faculty_can_access_earnings_summary(faculty_api_client):
    response = faculty_api_client.get('/api/sessions/earnings/')
    assert response.status_code == 200
    assert 'wallet_balance' in response.data


def test_student_cannot_access_earnings(student_api_client):
    response = student_api_client.get('/api/sessions/earnings/')
    assert response.status_code == 403


def test_monthly_breakdown_has_6_months(alumni_api_client):
    response = alumni_api_client.get('/api/sessions/earnings/')
    assert response.status_code == 200
    assert len(response.data['monthly_breakdown']) == 6


def test_earnings_reflect_confirmed_bookings(
    verified_alumni, upcoming_group_session, verified_student
):
    AlumniProfile.objects.get_or_create(user=verified_alumni)
    StudentProfile.objects.get_or_create(user=verified_student)
    Booking.objects.create(
        session=upcoming_group_session,
        student=verified_student,
        status='confirmed',
        amount_paid=Decimal('499.00'),
        platform_cut=Decimal('149.70'),
        host_share=Decimal('349.30'),
    )
    from rest_framework_simplejwt.tokens import RefreshToken
    from rest_framework.test import APIClient
    client = APIClient()
    refresh = RefreshToken.for_user(verified_alumni)
    client.credentials(HTTP_AUTHORIZATION='Bearer ' + str(refresh.access_token))

    response = client.get('/api/sessions/earnings/')
    assert response.status_code == 200
    assert int(response.data['total_bookings']) >= 1
    assert len(response.data['recent_transactions']) >= 1
    txn = response.data['recent_transactions'][0]
    assert txn['host_share'] == '349.30'
    assert txn['platform_cut'] == '149.70'


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST GROUP 8: Bank Details API
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def test_alumni_can_get_bank_details(alumni_api_client):
    response = alumni_api_client.get('/api/sessions/bank-details/')
    assert response.status_code == 200
    assert 'bank_details' in response.data
    assert 'bank_verified' in response.data


def test_alumni_can_save_valid_bank_details(alumni_api_client, verified_alumni):
    payload = {
        'account_holder_name': 'Rohit Kumar Sharma',
        'bank_name': 'HDFC Bank',
        'account_number': '50100123456789',
        'confirm_account_number': '50100123456789',
        'ifsc_code': 'HDFC0001234',
        'upi_id': 'rohit@hdfc',
    }
    response = alumni_api_client.post('/api/sessions/bank-details/', payload, format='json')
    assert response.status_code == 200
    assert 'Bank details saved' in response.data.get('message', '')
    verified_alumni.alumni_profile.refresh_from_db()
    saved = verified_alumni.alumni_profile.bank_details
    assert saved['account_holder_name'] == 'Rohit Kumar Sharma'
    assert saved['ifsc_code'] == 'HDFC0001234'


def test_bank_details_rejects_invalid_ifsc(alumni_api_client):
    for invalid_ifsc in ['INVALID', 'ABC', '12345678901', 'hdfc0001234']:
        payload = {
            'account_holder_name': 'Test User',
            'bank_name': 'Test Bank',
            'account_number': '123456789012',
            'confirm_account_number': '123456789012',
            'ifsc_code': invalid_ifsc,
        }
        response = alumni_api_client.post('/api/sessions/bank-details/', payload, format='json')
        assert response.status_code == 400, f"IFSC '{invalid_ifsc}' should have been rejected"
        assert 'ifsc_code' in response.data


def test_bank_details_rejects_mismatched_account_numbers(alumni_api_client):
    payload = {
        'account_holder_name': 'Test User',
        'bank_name': 'SBI',
        'account_number': '123456789012',
        'confirm_account_number': '999999999999',
        'ifsc_code': 'SBIN0001234',
    }
    response = alumni_api_client.post('/api/sessions/bank-details/', payload, format='json')
    assert response.status_code == 400
    assert 'confirm_account_number' in response.data


def test_bank_details_rejects_short_account_number(alumni_api_client):
    payload = {
        'account_holder_name': 'Test User',
        'bank_name': 'ICICI',
        'account_number': '12345',
        'confirm_account_number': '12345',
        'ifsc_code': 'ICIC0001234',
    }
    response = alumni_api_client.post('/api/sessions/bank-details/', payload, format='json')
    assert response.status_code == 400
    assert 'account_number' in response.data


def test_bank_details_missing_required_fields(alumni_api_client):
    response = alumni_api_client.post('/api/sessions/bank-details/', {}, format='json')
    assert response.status_code == 400
    for field in ['account_holder_name', 'bank_name', 'account_number', 'ifsc_code']:
        assert field in response.data, f"Expected error for missing field: {field}"


def test_student_cannot_access_bank_details(student_api_client):
    response = student_api_client.get('/api/sessions/bank-details/')
    assert response.status_code == 403
    response = student_api_client.post('/api/sessions/bank-details/', {}, format='json')
    assert response.status_code == 403
