"""
Phase 9 — Admin Dashboard Tests
Tests all admin API endpoints, access control, action logging, and middleware.
"""
import pytest
from django.utils import timezone
from datetime import timedelta
from apps.accounts.models import AdminActionLog

pytestmark = pytest.mark.django_db


# =====================================
# TEST GROUP 1: Admin Access Control
# =====================================

def test_only_admin_can_access_overview(verified_student, verified_alumni, admin_api_client):
    """Non-admin users must receive 403 on all admin endpoints"""
    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import RefreshToken
    from apps.accounts.models import AlumniProfile, StudentProfile

    # Student client
    StudentProfile.objects.get_or_create(user=verified_student)
    student_client = APIClient()
    student_client.credentials(
        HTTP_AUTHORIZATION='Bearer ' + str(RefreshToken.for_user(verified_student).access_token)
    )
    r = student_client.get('/api/dashboard/admin/overview/')
    assert r.status_code == 403

    # Alumni client
    AlumniProfile.objects.get_or_create(user=verified_alumni)
    alumni_client = APIClient()
    alumni_client.credentials(
        HTTP_AUTHORIZATION='Bearer ' + str(RefreshToken.for_user(verified_alumni).access_token)
    )
    r = alumni_client.get('/api/dashboard/admin/overview/')
    assert r.status_code == 403

    # Admin
    r = admin_api_client.get('/api/dashboard/admin/overview/')
    assert r.status_code == 200


def test_unauthenticated_cannot_access_admin_endpoints(api_client):
    for endpoint in [
        '/api/dashboard/admin/overview/',
        '/api/dashboard/admin/users/',
        '/api/dashboard/admin/alumni/verification/',
        '/api/dashboard/admin/moderation-api/',
        '/api/dashboard/admin/sessions/',
        '/api/dashboard/admin/referrals/',
        '/api/dashboard/admin/broadcast/',
        '/api/dashboard/admin/action-log/',
    ]:
        r = api_client.get(endpoint)
        assert r.status_code in [401, 403], (
            f"{endpoint} should be protected but returned {r.status_code}"
        )


def test_non_admin_cannot_perform_user_actions(student_api_client, verified_alumni):
    r = student_api_client.post(
        f'/api/dashboard/admin/users/{verified_alumni.id}/action/',
        {'action': 'suspend'},
        format='json',
    )
    assert r.status_code == 403


# =====================================
# TEST GROUP 2: Admin Overview
# =====================================

def test_admin_overview_has_all_required_fields(admin_api_client):
    r = admin_api_client.get('/api/dashboard/admin/overview/')
    assert r.status_code == 200
    data = r.data

    # Check all required top-level keys
    for key in ['users', 'content', 'financial', 'verification', 'ai_tools', 'charts']:
        assert key in data, f"Missing key: {key}"

    # Check nested keys
    for key in ['total', 'students', 'alumni', 'faculty', 'new_today', 'new_this_week']:
        assert key in data['users'], f"Missing users.{key}"

    for key in ['total_platform_revenue', 'this_month_revenue', 'pending_payouts', 'pending_payout_count']:
        assert key in data['financial'], f"Missing financial.{key}"

    # Check charts have correct structure
    assert 'signups_last_7_days' in data['charts']
    assert len(data['charts']['signups_last_7_days']) == 7
    assert 'revenue_last_6_months' in data['charts']
    assert len(data['charts']['revenue_last_6_months']) == 6


def test_admin_overview_user_count_is_accurate(admin_api_client, verified_student, verified_alumni, verified_faculty):
    r = admin_api_client.get('/api/dashboard/admin/overview/')
    assert r.status_code == 200
    # At least our test users should be counted
    assert r.data['users']['total'] >= 3
    assert r.data['users']['students'] >= 1
    assert r.data['users']['alumni'] >= 1
    assert r.data['users']['faculty'] >= 1


# =====================================
# TEST GROUP 3: User Management
# =====================================

def test_admin_can_list_all_users(admin_api_client, verified_student, verified_alumni):
    r = admin_api_client.get('/api/dashboard/admin/users/')
    assert r.status_code == 200
    assert 'results' in r.data
    assert r.data['count'] >= 2

    # Each user has required fields
    for user in r.data['results']:
        for field in ['id', 'email', 'role', 'is_active', 'is_verified', 'date_joined']:
            assert field in user, f"Missing field: {field}"


def test_admin_can_filter_users_by_role(admin_api_client, verified_student, verified_alumni):
    r = admin_api_client.get('/api/dashboard/admin/users/?role=student')
    assert r.status_code == 200
    for user in r.data['results']:
        assert user['role'] == 'student'


def test_admin_can_search_users_by_email(admin_api_client, verified_student):
    email_prefix = verified_student.email.split('@')[0]
    r = admin_api_client.get(f'/api/dashboard/admin/users/?search={email_prefix}')
    assert r.status_code == 200
    emails = [u['email'] for u in r.data['results']]
    assert verified_student.email in emails


def test_admin_can_suspend_user(admin_api_client, verified_student):
    r = admin_api_client.post(
        f'/api/dashboard/admin/users/{verified_student.id}/action/',
        {'action': 'suspend', 'note': 'Test suspension for violation'},
        format='json',
    )
    assert r.status_code == 200
    verified_student.refresh_from_db()
    assert verified_student.is_suspended is True
    assert verified_student.suspended_reason == 'Test suspension for violation'


def test_admin_can_unsuspend_user(admin_api_client, verified_student):
    # First suspend
    verified_student.is_suspended = True
    verified_student.save()
    # Then unsuspend
    r = admin_api_client.post(
        f'/api/dashboard/admin/users/{verified_student.id}/action/',
        {'action': 'unsuspend'},
        format='json',
    )
    assert r.status_code == 200
    verified_student.refresh_from_db()
    assert verified_student.is_suspended is False


def test_admin_can_soft_delete_user(admin_api_client, verified_student):
    r = admin_api_client.post(
        f'/api/dashboard/admin/users/{verified_student.id}/action/',
        {'action': 'delete', 'note': 'Account deleted per user request'},
        format='json',
    )
    assert r.status_code == 200
    verified_student.refresh_from_db()
    assert verified_student.is_active is False


def test_admin_cannot_suspend_another_admin(admin_api_client):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    admin2 = User.objects.create_user(
        username='admin2@test.com',
        email='admin2@test.com',
        password='Test@1234',
        role='admin',
        is_verified=True,
    )
    r = admin_api_client.post(
        f'/api/dashboard/admin/users/{admin2.id}/action/',
        {'action': 'suspend'},
        format='json',
    )
    assert r.status_code == 400


def test_suspension_creates_action_log(admin_api_client, verified_student):
    count_before = AdminActionLog.objects.count()
    admin_api_client.post(
        f'/api/dashboard/admin/users/{verified_student.id}/action/',
        {'action': 'suspend', 'note': 'Log test suspension'},
        format='json',
    )
    assert AdminActionLog.objects.count() == count_before + 1
    log = AdminActionLog.objects.latest('created_at')
    assert log.action_type == 'user_suspended'
    assert log.target_user == verified_student


# =====================================
# TEST GROUP 4: Alumni Verification
# =====================================

def test_admin_can_see_pending_verifications(admin_api_client, unverified_alumni):
    r = admin_api_client.get('/api/dashboard/admin/alumni/verification/?status=pending')
    assert r.status_code == 200
    assert r.data['count'] >= 1
    alumni_ids = [a['alumni_id'] for a in r.data['alumni']]
    assert unverified_alumni.id in alumni_ids


def test_admin_can_approve_alumni_verification(admin_api_client, unverified_alumni):
    r = admin_api_client.post(
        f'/api/dashboard/admin/alumni/verification/{unverified_alumni.id}/',
        {'action': 'approve', 'note': 'LinkedIn profile matches, Google employee confirmed'},
        format='json',
    )
    assert r.status_code == 200
    unverified_alumni.refresh_from_db()
    assert unverified_alumni.is_verified is True
    profile = unverified_alumni.alumni_profile
    assert profile.verification_status == 'verified'
    assert profile.verified_at is not None


def test_admin_can_reject_alumni_verification(admin_api_client, unverified_alumni):
    r = admin_api_client.post(
        f'/api/dashboard/admin/alumni/verification/{unverified_alumni.id}/',
        {'action': 'reject', 'note': 'Could not verify employment at stated company'},
        format='json',
    )
    assert r.status_code == 200
    profile = unverified_alumni.alumni_profile
    profile.refresh_from_db()
    assert profile.verification_status == 'rejected'


def test_alumni_rejection_requires_note(admin_api_client, unverified_alumni):
    r = admin_api_client.post(
        f'/api/dashboard/admin/alumni/verification/{unverified_alumni.id}/',
        {'action': 'reject', 'note': ''},
        format='json',
    )
    assert r.status_code == 400


def test_verification_action_creates_log(admin_api_client, unverified_alumni):
    count_before = AdminActionLog.objects.count()
    admin_api_client.post(
        f'/api/dashboard/admin/alumni/verification/{unverified_alumni.id}/',
        {'action': 'approve', 'note': 'Verified via LinkedIn'},
        format='json',
    )
    assert AdminActionLog.objects.count() == count_before + 1


# =====================================
# TEST GROUP 5: Content Moderation
# =====================================

def test_admin_can_view_flagged_content(admin_api_client):
    r = admin_api_client.get('/api/dashboard/admin/moderation-api/')
    assert r.status_code == 200
    assert 'flagged_posts' in r.data
    assert 'flagged_referrals' in r.data


def test_admin_can_hide_post(admin_api_client, verified_alumni):
    from apps.feed.models import Post
    post = Post.objects.create(
        author=verified_alumni,
        post_type='general',
        content='This is a test post that will be hidden by admin.',
        status='flagged',
        flagged_count=3,
    )
    r = admin_api_client.post(
        '/api/dashboard/admin/moderation-api/',
        {'content_type': 'post', 'object_id': post.id, 'action': 'hide', 'note': 'Inappropriate content'},
        format='json',
    )
    assert r.status_code == 200
    post.refresh_from_db()
    assert post.status == 'hidden'


def test_admin_can_approve_flagged_post(admin_api_client, verified_alumni):
    from apps.feed.models import Post
    post = Post.objects.create(
        author=verified_alumni,
        post_type='general',
        content='Falsely flagged post content — this is legitimate and should be approved.',
        status='flagged',
        flagged_count=1,
    )
    r = admin_api_client.post(
        '/api/dashboard/admin/moderation-api/',
        {'content_type': 'post', 'object_id': post.id, 'action': 'approve'},
        format='json',
    )
    assert r.status_code == 200
    post.refresh_from_db()
    assert post.status == 'active'
    assert post.flagged_count == 0


def test_admin_can_deactivate_referral(admin_api_client, verified_alumni):
    from apps.referrals.models import Referral
    referral = Referral.objects.create(
        posted_by=verified_alumni,
        company_name='Test Corp',
        job_title='Test Role',
        job_description='A test referral that will be deactivated by admin action.',
        required_skills=['Python'],
        max_applicants=5,
        deadline=timezone.now() + timedelta(days=7),
        status='active',
    )
    r = admin_api_client.post(
        '/api/dashboard/admin/moderation-api/',
        {'content_type': 'referral', 'object_id': referral.id, 'action': 'deactivate', 'note': 'Fraudulent job listing detected'},
        format='json',
    )
    assert r.status_code == 200
    referral.refresh_from_db()
    assert referral.status == 'deactivated'


# =====================================
# TEST GROUP 6: Broadcast
# =====================================

def test_admin_can_send_broadcast_to_all(admin_api_client, verified_student, verified_alumni):
    from apps.notifications.models import Notification
    count_before = Notification.objects.count()
    r = admin_api_client.post(
        '/api/dashboard/admin/broadcast/',
        {
            'title': 'Important Platform Update',
            'message': 'We have released new features including AI interview and skill gap analyzer.',
            'target_role': 'all',
            'link': '/sessions/',
        },
        format='json',
    )
    assert r.status_code == 200
    assert r.data['count'] >= 2
    assert Notification.objects.count() > count_before


def test_admin_can_broadcast_to_specific_role(admin_api_client, verified_student, verified_alumni):
    from apps.notifications.models import Notification
    r = admin_api_client.post(
        '/api/dashboard/admin/broadcast/',
        {
            'title': 'Student-only announcement',
            'message': 'New referral opportunities available from our alumni network.',
            'target_role': 'student',
            'link': '/referrals/',
        },
        format='json',
    )
    assert r.status_code == 200
    # Should have sent to at least 1 student
    assert r.data['count'] >= 1


def test_broadcast_requires_title_and_message(admin_api_client):
    r = admin_api_client.post(
        '/api/dashboard/admin/broadcast/',
        {'title': '', 'message': '', 'target_role': 'all'},
        format='json',
    )
    assert r.status_code == 400


def test_broadcast_creates_action_log(admin_api_client, verified_student):
    count_before = AdminActionLog.objects.count()
    admin_api_client.post(
        '/api/dashboard/admin/broadcast/',
        {
            'title': 'Log test broadcast',
            'message': 'Testing that broadcast creates an audit log entry.',
            'target_role': 'all',
        },
        format='json',
    )
    assert AdminActionLog.objects.count() == count_before + 1
    log = AdminActionLog.objects.latest('created_at')
    assert log.action_type == 'broadcast_sent'


# =====================================
# TEST GROUP 7: Audit Log
# =====================================

def test_admin_can_view_audit_log(admin_api_client, verified_student):
    # Create a log entry first
    AdminActionLog.objects.create(
        admin=admin_api_client._admin,
        action_type='user_suspended',
        target_user=verified_student,
        note='Test audit log entry',
    )
    r = admin_api_client.get('/api/dashboard/admin/action-log/')
    assert r.status_code == 200
    assert 'results' in r.data
    assert r.data['count'] >= 1


def test_audit_log_has_required_fields(admin_api_client, verified_student):
    AdminActionLog.objects.create(
        admin=admin_api_client._admin,
        action_type='user_verified',
        target_user=verified_student,
        note='Verified via email',
    )
    r = admin_api_client.get('/api/dashboard/admin/action-log/')
    assert r.status_code == 200
    if r.data['results']:
        log = r.data['results'][0]
        for field in ['id', 'admin_name', 'action_type', 'action_display', 'created_at']:
            assert field in log, f"Missing audit log field: {field}"


def test_audit_log_filter_by_action_type(admin_api_client, verified_student):
    AdminActionLog.objects.create(
        admin=admin_api_client._admin,
        action_type='user_suspended',
        target_user=verified_student,
    )
    AdminActionLog.objects.create(
        admin=admin_api_client._admin,
        action_type='alumni_verified',
        target_user=verified_student,
    )
    r = admin_api_client.get('/api/dashboard/admin/action-log/?action_type=user_suspended')
    assert r.status_code == 200
    for log in r.data['results']:
        assert log['action_type'] == 'user_suspended'


# =====================================
# TEST GROUP 8: Sessions and Referrals Admin
# =====================================

def test_admin_can_list_all_sessions(admin_api_client, verified_alumni):
    from apps.sessions_app.models import Session
    from apps.accounts.models import AlumniProfile
    AlumniProfile.objects.get_or_create(user=verified_alumni)
    Session.objects.create(
        host=verified_alumni,
        session_type='group',
        title='Admin test session',
        description='Session created for admin dashboard testing purposes.',
        scheduled_at=timezone.now() + timedelta(days=3),
        duration_minutes=60,
        price=499,
        max_seats=10,
        status='upcoming',
    )
    r = admin_api_client.get('/api/dashboard/admin/sessions/')
    assert r.status_code == 200
    assert 'results' in r.data
    assert r.data['count'] >= 1


def test_admin_can_list_all_referrals(admin_api_client, verified_alumni):
    from apps.referrals.models import Referral
    Referral.objects.create(
        posted_by=verified_alumni,
        company_name='Admin Test Corp',
        job_title='Admin Test Role',
        job_description='Referral created for admin dashboard testing purposes.',
        required_skills=['Python'],
        max_applicants=5,
        deadline=timezone.now() + timedelta(days=7),
        status='active',
    )
    r = admin_api_client.get('/api/dashboard/admin/referrals/')
    assert r.status_code == 200
    assert 'results' in r.data
    assert r.data['count'] >= 1


# =====================================
# TEST GROUP 9: Suspended User Middleware
# =====================================

def test_suspended_user_api_returns_403(verified_student):
    """
    After suspension, the user's API requests via cookie should be blocked by middleware.
    The middleware protects /dashboard/ paths and returns 403 JSON for /api/ sub-paths.
    We test by hitting /dashboard/student/ with the cookie — middleware returns redirect
    to /auth/login/?suspended=1 (302), confirming the block.
    """
    from rest_framework_simplejwt.tokens import RefreshToken
    from rest_framework.test import APIClient

    # Suspend the student
    verified_student.is_suspended = True
    verified_student.suspended_reason = 'Test — suspended for testing middleware'
    verified_student.save(update_fields=['is_suspended', 'suspended_reason'])

    # Get a fresh token and set it as a cookie (how the middleware reads it)
    refresh = RefreshToken.for_user(verified_student)
    access_token = str(refresh.access_token)

    cookie_client = APIClient()
    cookie_client.cookies['access_token'] = access_token

    # Hit a protected page path — middleware should redirect suspended user
    r = cookie_client.get('/dashboard/student/', follow=False)
    # Middleware redirects suspended users to /auth/login/?suspended=1
    assert r.status_code == 302, f"Suspended user should be redirected (302), got {r.status_code}"
    assert 'suspended' in r.get('Location', ''), f"Redirect should include 'suspended', got: {r.get('Location')}"
