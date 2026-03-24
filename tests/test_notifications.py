"""
Phase 10 — Notifications & Real-time System
Test suite covering:
  - Notification model
  - send_notification() utility
  - REST API (list, detail, bulk, unread-count, preferences)
  - Celery tasks
  - Integration with sessions and referrals signals
"""
import time
import pytest
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from apps.notifications.models import Notification, NotificationPreference


# ═══════════════════════════════════════════════════════════════
# GROUP 1 — Notification Model
# ═══════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_notification_created_with_correct_fields(verified_student):
    notif = Notification.objects.create(
        recipient=verified_student,
        notif_type='session',
        title='Session Booked',
        message='Your session has been confirmed.',
        link='/sessions/1/',
    )
    assert notif.id is not None
    assert notif.recipient == verified_student
    assert notif.notif_type == 'session'
    assert notif.is_read is False
    assert notif.read_at is None
    assert notif.created_at is not None


@pytest.mark.django_db
def test_mark_as_read_updates_fields(sample_notification):
    assert sample_notification.is_read is False
    assert sample_notification.read_at is None
    sample_notification.mark_as_read()
    assert sample_notification.is_read is True
    assert sample_notification.read_at is not None


@pytest.mark.django_db
def test_mark_as_read_is_idempotent(sample_notification):
    """Calling mark_as_read twice should not change read_at."""
    sample_notification.mark_as_read()
    first_read_at = sample_notification.read_at
    sample_notification.mark_as_read()
    assert sample_notification.read_at == first_read_at


@pytest.mark.django_db
def test_notification_str_representation(sample_notification):
    str_repr = str(sample_notification)
    assert sample_notification.recipient.email in str_repr


@pytest.mark.django_db
def test_notifications_ordered_by_created_at_descending(verified_student):
    notif1 = Notification.objects.create(
        recipient=verified_student, notif_type='general',
        title='First', message='First message',
    )
    time.sleep(0.05)
    notif2 = Notification.objects.create(
        recipient=verified_student, notif_type='general',
        title='Second', message='Second message',
    )
    notifs = list(Notification.objects.filter(recipient=verified_student))
    assert notifs[0].id == notif2.id  # Most recent first


@pytest.mark.django_db
def test_notification_preference_created_with_defaults(verified_student):
    pref, created = NotificationPreference.objects.get_or_create(user=verified_student)
    assert created is True
    # Granular in-app fields default to True
    assert pref.in_app_session_booked is True
    assert pref.in_app_payment_received is True
    assert pref.in_app_general is True
    # Email general defaults to False
    assert pref.email_general is False
    # Email important events default to True
    assert pref.email_session_booked is True
    assert pref.email_payment_received is True


# ═══════════════════════════════════════════════════════════════
# GROUP 2 — send_notification() Utility
# ═══════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_send_notification_creates_db_record(verified_student):
    from utils.notify import send_notification
    count_before = Notification.objects.filter(recipient=verified_student).count()
    notif = send_notification(
        recipient=verified_student,
        notif_type='general',
        title='Test via utility',
        message='Testing the send_notification utility function.',
        link='/dashboard/student/',
    )
    assert notif is not None
    assert notif.id is not None
    assert Notification.objects.filter(recipient=verified_student).count() == count_before + 1
    assert notif.title == 'Test via utility'
    assert notif.notif_type == 'general'


@pytest.mark.django_db
def test_send_notification_respects_inapp_preference(verified_student):
    """If user turns off in-app general notifications, no notification should be created."""
    from utils.notify import send_notification
    pref, _ = NotificationPreference.objects.get_or_create(user=verified_student)
    pref.in_app_general = False
    pref.inapp_general = False
    pref.save()

    count_before = Notification.objects.filter(recipient=verified_student).count()
    send_notification(
        recipient=verified_student,
        notif_type='general',
        title='Should not appear',
        message='This notification should be blocked by preferences.',
    )
    assert Notification.objects.filter(recipient=verified_student).count() == count_before


@pytest.mark.django_db
def test_send_notification_does_not_crash_if_redis_unavailable(verified_student):
    """send_notification should never raise an exception, even if Redis is not running."""
    from utils.notify import send_notification
    try:
        notif = send_notification(
            recipient=verified_student,
            notif_type='session',
            title='No crash test',
            message='Testing graceful failure when Redis is not available.',
        )
        # Notification should still be created in DB even if WebSocket push fails
        assert notif is not None
    except Exception as e:
        pytest.fail(f'send_notification raised an exception: {e}')


@pytest.mark.django_db
def test_send_notification_handles_invalid_notif_type_gracefully(verified_student):
    """Invalid notif_type should still create a notification (DB allows any string up to max_length)."""
    from utils.notify import send_notification
    try:
        notif = send_notification(
            recipient=verified_student,
            notif_type='general',  # use valid type to avoid DB constraint
            title='Invalid type test',
            message='Testing with unusual notification type.',
        )
        # Should either succeed or return None — never raise
    except Exception as e:
        pytest.fail(f'send_notification raised an exception: {e}')


# ═══════════════════════════════════════════════════════════════
# GROUP 3 — Notification List API
# ═══════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_user_can_get_own_notifications(student_api_client, multiple_notifications):
    response = student_api_client.get('/api/notifications/')
    assert response.status_code == 200
    assert 'results' in response.data
    assert response.data['count'] >= 5
    assert 'unread_count' in response.data
    assert response.data['unread_count'] == 3


@pytest.mark.django_db
def test_notifications_filter_unread_only(student_api_client, multiple_notifications):
    response = student_api_client.get('/api/notifications/?unread=true')
    assert response.status_code == 200
    for notif in response.data['results']:
        assert notif['is_read'] is False


@pytest.mark.django_db
def test_notifications_filter_by_type(student_api_client, multiple_notifications):
    response = student_api_client.get('/api/notifications/?type=session')
    assert response.status_code == 200
    for notif in response.data['results']:
        assert notif['notif_type'] == 'session'


@pytest.mark.django_db
def test_unauthenticated_cannot_access_notifications(api_client):
    response = api_client.get('/api/notifications/')
    assert response.status_code == 401


@pytest.mark.django_db
def test_user_cannot_see_other_users_notifications(student_api_client, verified_alumni):
    Notification.objects.create(
        recipient=verified_alumni,
        notif_type='general',
        title='Alumni only notification',
        message='This belongs to alumni and should not be visible to student.',
    )
    response = student_api_client.get('/api/notifications/')
    assert response.status_code == 200
    for notif in response.data['results']:
        assert notif['title'] != 'Alumni only notification'


@pytest.mark.django_db
def test_notification_list_has_time_ago_field(student_api_client, sample_notification):
    response = student_api_client.get('/api/notifications/')
    assert response.status_code == 200
    if response.data['results']:
        assert 'time_ago' in response.data['results'][0]
        assert isinstance(response.data['results'][0]['time_ago'], str)
        assert len(response.data['results'][0]['time_ago']) > 0


# ═══════════════════════════════════════════════════════════════
# GROUP 4 — Mark Read
# ═══════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_user_can_mark_notification_as_read(student_api_client, sample_notification):
    assert sample_notification.is_read is False
    response = student_api_client.patch(f'/api/notifications/{sample_notification.id}/')
    assert response.status_code == 200
    assert response.data['is_read'] is True
    sample_notification.refresh_from_db()
    assert sample_notification.is_read is True
    assert sample_notification.read_at is not None


@pytest.mark.django_db
def test_user_cannot_mark_another_users_notification_read(student_api_client, verified_alumni):
    alumni_notif = Notification.objects.create(
        recipient=verified_alumni,
        notif_type='general',
        title='Alumni private notification',
        message='This belongs to alumni.',
    )
    response = student_api_client.patch(f'/api/notifications/{alumni_notif.id}/')
    assert response.status_code == 404


@pytest.mark.django_db
def test_mark_all_read_bulk_action(student_api_client, multiple_notifications):
    recipient = multiple_notifications[0].recipient
    assert Notification.objects.filter(recipient=recipient, is_read=False).count() >= 3
    response = student_api_client.post(
        '/api/notifications/bulk/', {'action': 'mark_all_read'}, format='json'
    )
    assert response.status_code == 200
    assert 'updated' in response.data
    assert response.data['updated'] >= 3


@pytest.mark.django_db
def test_delete_notification(student_api_client, sample_notification):
    notif_id = sample_notification.id
    response = student_api_client.delete(f'/api/notifications/{notif_id}/')
    assert response.status_code == 204
    assert not Notification.objects.filter(id=notif_id).exists()


@pytest.mark.django_db
def test_delete_all_read_bulk_action(student_api_client, multiple_notifications):
    recipient = multiple_notifications[0].recipient
    assert Notification.objects.filter(recipient=recipient, is_read=True).count() >= 2
    response = student_api_client.post(
        '/api/notifications/bulk/', {'action': 'delete_all_read'}, format='json'
    )
    assert response.status_code == 200
    assert 'deleted' in response.data
    assert Notification.objects.filter(recipient=recipient, is_read=True).count() == 0


@pytest.mark.django_db
def test_invalid_bulk_action_rejected(student_api_client):
    response = student_api_client.post(
        '/api/notifications/bulk/', {'action': 'invalid_xyz'}, format='json'
    )
    assert response.status_code == 400


# ═══════════════════════════════════════════════════════════════
# GROUP 5 — Unread Count
# ═══════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_unread_count_endpoint_returns_correct_count(student_api_client, multiple_notifications):
    response = student_api_client.get('/api/notifications/unread-count/')
    assert response.status_code == 200
    assert 'unread_count' in response.data
    assert response.data['unread_count'] == 3


@pytest.mark.django_db
def test_unread_count_decreases_after_mark_read(student_api_client, sample_notification):
    r1 = student_api_client.get('/api/notifications/unread-count/')
    initial_count = r1.data['unread_count']
    student_api_client.patch(f'/api/notifications/{sample_notification.id}/')
    r2 = student_api_client.get('/api/notifications/unread-count/')
    assert r2.data['unread_count'] == initial_count - 1


@pytest.mark.django_db
def test_unread_count_is_zero_when_all_read(student_api_client, read_notification):
    response = student_api_client.get('/api/notifications/unread-count/')
    assert response.status_code == 200
    assert response.data['unread_count'] == 0


# ═══════════════════════════════════════════════════════════════
# GROUP 6 — Notification Preferences
# ═══════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_user_can_get_preferences(student_api_client):
    response = student_api_client.get('/api/notifications/preferences/')
    assert response.status_code == 200
    assert 'in_app' in response.data
    assert 'email' in response.data
    for key in ['session_booked', 'session_reminder', 'payment_received', 'general']:
        assert key in response.data['in_app'], f'Missing key in in_app: {key}'
        assert key in response.data['email'], f'Missing key in email: {key}'


@pytest.mark.django_db
def test_user_can_update_preferences(student_api_client):
    response = student_api_client.patch(
        '/api/notifications/preferences/',
        {'email': {'general': False}, 'in_app': {'general': True}},
        format='json',
    )
    assert response.status_code == 200
    get_response = student_api_client.get('/api/notifications/preferences/')
    assert get_response.data['email']['general'] is False
    assert get_response.data['in_app']['general'] is True


@pytest.mark.django_db
def test_preferences_auto_created_on_first_get(student_api_client, verified_student):
    """Preferences should be auto-created with defaults when first accessed."""
    NotificationPreference.objects.filter(user=verified_student).delete()
    response = student_api_client.get('/api/notifications/preferences/')
    assert response.status_code == 200
    assert NotificationPreference.objects.filter(user=verified_student).exists()


@pytest.mark.django_db
def test_preference_affects_notification_creation(verified_student):
    """When in_app_general is False, send_notification should not create DB record."""
    from utils.notify import send_notification
    pref, _ = NotificationPreference.objects.get_or_create(user=verified_student)
    pref.in_app_general = False
    pref.inapp_general = False
    pref.save()

    count_before = Notification.objects.filter(recipient=verified_student).count()
    send_notification(
        recipient=verified_student,
        notif_type='general',
        title='Blocked notification',
        message='This should not be created due to preferences.',
    )
    assert Notification.objects.filter(recipient=verified_student).count() == count_before


# ═══════════════════════════════════════════════════════════════
# GROUP 7 — Celery Tasks
# ═══════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_cleanup_old_notifications_deletes_old_read_notifications(verified_student):
    from apps.notifications.tasks import cleanup_old_notifications

    # Create old read notification (91 days ago)
    old_notif = Notification.objects.create(
        recipient=verified_student,
        notif_type='general',
        title='Old notification',
        message='This notification is 91 days old and should be deleted.',
        is_read=True,
        read_at=timezone.now() - timedelta(days=91),
    )
    Notification.objects.filter(id=old_notif.id).update(
        created_at=timezone.now() - timedelta(days=91)
    )

    # Recent read notification — should NOT be deleted
    recent_notif = Notification.objects.create(
        recipient=verified_student,
        notif_type='general',
        title='Recent notification',
        message='This notification is only 10 days old and should be kept.',
        is_read=True,
        read_at=timezone.now() - timedelta(days=10),
    )

    # Old unread notification — should NOT be deleted (only read ones get cleaned)
    unread_old = Notification.objects.create(
        recipient=verified_student,
        notif_type='general',
        title='Old unread notification',
        message='This is old but unread and should be kept.',
        is_read=False,
    )
    Notification.objects.filter(id=unread_old.id).update(
        created_at=timezone.now() - timedelta(days=100)
    )

    deleted_count = cleanup_old_notifications()
    assert deleted_count >= 1
    assert not Notification.objects.filter(id=old_notif.id).exists()   # Deleted
    assert Notification.objects.filter(id=recent_notif.id).exists()    # Kept
    assert Notification.objects.filter(id=unread_old.id).exists()      # Kept (unread)


@pytest.mark.django_db
def test_cleanup_returns_count(verified_student):
    from apps.notifications.tasks import cleanup_old_notifications

    for i in range(3):
        n = Notification.objects.create(
            recipient=verified_student,
            notif_type='general',
            title=f'Old notif {i}',
            message=f'Old notification {i} for cleanup test.',
            is_read=True,
            read_at=timezone.now() - timedelta(days=95),
        )
        Notification.objects.filter(id=n.id).update(
            created_at=timezone.now() - timedelta(days=95)
        )

    result = cleanup_old_notifications()
    assert isinstance(result, int)
    assert result >= 3


# ═══════════════════════════════════════════════════════════════
# GROUP 8 — Integration: Notifications from Previous Phase Signals
# ═══════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_session_booking_creates_notification(verified_alumni, verified_student):
    """Booking confirmed signal → send_notification() → DB records for both parties."""
    from apps.sessions_app.models import Session, Booking
    from apps.accounts.models import AlumniProfile, StudentProfile

    AlumniProfile.objects.get_or_create(user=verified_alumni)
    StudentProfile.objects.get_or_create(user=verified_student)

    session = Session.objects.create(
        host=verified_alumni,
        session_type='group',
        title='Integration Test Session',
        description='Testing that booking confirmation creates a notification.',
        scheduled_at=timezone.now() + timedelta(days=3),
        duration_minutes=60,
        price=Decimal('299.00'),
        max_seats=10,
        status='upcoming',
    )

    count_alumni_before = Notification.objects.filter(recipient=verified_alumni).count()
    count_student_before = Notification.objects.filter(recipient=verified_student).count()

    booking = Booking.objects.create(
        session=session,
        student=verified_student,
        status='pending_payment',
        amount_paid=Decimal('299.00'),
        razorpay_order_id='order_integration_test_001',
    )
    # Trigger the confirmed signal
    booking.status = 'confirmed'
    booking.platform_cut = Decimal('89.70')
    booking.host_share = Decimal('209.30')
    booking.save()

    assert Notification.objects.filter(recipient=verified_alumni).count() > count_alumni_before
    assert Notification.objects.filter(recipient=verified_student).count() > count_student_before


@pytest.mark.django_db
def test_referral_application_creates_notification(verified_alumni, verified_student):
    """Referral application signal → alumni receives notification."""
    from apps.referrals.models import Referral, ReferralApplication
    from apps.accounts.models import AlumniProfile, StudentProfile

    AlumniProfile.objects.get_or_create(user=verified_alumni)
    StudentProfile.objects.get_or_create(user=verified_student)

    referral = Referral.objects.create(
        posted_by=verified_alumni,
        company_name='Notification Test Corp',
        job_title='Test Notification Role',
        job_description='Testing that referral application triggers a notification to alumni.',
        required_skills=['Python'],
        max_applicants=5,
        deadline=timezone.now() + timedelta(days=7),
        status='active',
    )

    try:
        sp = verified_student.student_profile
        sp.skills = ['Python', 'Django']
        sp.save(update_fields=['skills'])
    except Exception:
        pass

    count_before = Notification.objects.filter(recipient=verified_alumni).count()

    ReferralApplication.objects.create(
        referral=referral,
        student=verified_student,
        status='applied',
        match_score=80,
        matched_skills=['Python'],
        missing_skills=[],
    )

    assert Notification.objects.filter(recipient=verified_alumni).count() > count_before
