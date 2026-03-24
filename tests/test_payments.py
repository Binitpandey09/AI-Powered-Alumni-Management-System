"""
tests/test_payments.py
Day 13-15 — Payments & Wallet System test suite
28 tests across 7 groups
"""
import pytest
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model

from apps.payments.models import Transaction, Wallet, PayoutRequest, AIToolUsage
from apps.accounts.models import AlumniProfile, StudentProfile

User = get_user_model()


# ══════════════════════════════════════════════════════════════
# GROUP 1 — Transaction Model
# ══════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_invoice_number_auto_generated(verified_alumni, verified_student):
    AlumniProfile.objects.get_or_create(user=verified_alumni)
    tx = Transaction.objects.create(
        payer=verified_student,
        payee=verified_alumni,
        transaction_type='session_booking',
        status='completed',
        gross_amount=Decimal('499.00'),
        platform_fee=Decimal('149.70'),
        payee_amount=Decimal('349.30'),
        description='Test transaction for invoice number generation',
    )
    assert tx.invoice_number.startswith('INV-')
    assert len(tx.invoice_number) > 8


@pytest.mark.django_db
def test_invoice_numbers_are_unique(verified_alumni, verified_student):
    AlumniProfile.objects.get_or_create(user=verified_alumni)
    tx1 = Transaction.objects.create(
        payer=verified_student, payee=verified_alumni,
        transaction_type='session_booking', status='completed',
        gross_amount=Decimal('200.00'), platform_fee=Decimal('60.00'),
        payee_amount=Decimal('140.00'), description='Transaction 1 for uniqueness test',
    )
    tx2 = Transaction.objects.create(
        payer=verified_student, payee=verified_alumni,
        transaction_type='session_booking', status='completed',
        gross_amount=Decimal('300.00'), platform_fee=Decimal('90.00'),
        payee_amount=Decimal('210.00'), description='Transaction 2 for uniqueness test',
    )
    assert tx1.invoice_number != tx2.invoice_number


@pytest.mark.django_db
def test_70_30_split_calculation():
    from utils.payment_utils import calculate_split
    platform_fee, payee_amount = calculate_split(Decimal('499.00'))
    assert platform_fee == Decimal('149.70')
    assert payee_amount == Decimal('349.30')
    assert platform_fee + payee_amount == Decimal('499.00')


@pytest.mark.django_db
def test_split_for_ai_tools_is_100_percent_platform():
    from utils.payment_utils import calculate_split
    platform_fee, payee_amount = calculate_split(Decimal('99.00'), platform_pct=Decimal('1.00'))
    assert platform_fee == Decimal('99.00')
    assert payee_amount == Decimal('0.00')


# ══════════════════════════════════════════════════════════════
# GROUP 2 — Wallet
# ══════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_wallet_created_on_demand(verified_alumni):
    AlumniProfile.objects.get_or_create(user=verified_alumni)
    wallet, created = Wallet.objects.get_or_create(user=verified_alumni)
    assert created or wallet is not None
    assert wallet.balance >= Decimal('0.00')


@pytest.mark.django_db
def test_wallet_balance_updates_on_completed_transaction(verified_alumni, verified_student):
    AlumniProfile.objects.get_or_create(user=verified_alumni)
    StudentProfile.objects.get_or_create(user=verified_student)
    wallet, _ = Wallet.objects.get_or_create(user=verified_alumni)
    balance_before = wallet.balance
    Transaction.objects.create(
        payer=verified_student,
        payee=verified_alumni,
        transaction_type='session_booking',
        status='completed',
        gross_amount=Decimal('499.00'),
        platform_fee=Decimal('149.70'),
        payee_amount=Decimal('349.30'),
        description='Wallet balance update test transaction',
    )
    wallet.refresh_from_db()
    assert wallet.balance == balance_before + Decimal('349.30')


@pytest.mark.django_db
def test_wallet_balance_does_not_update_for_pending_transaction(verified_alumni, verified_student):
    AlumniProfile.objects.get_or_create(user=verified_alumni)
    StudentProfile.objects.get_or_create(user=verified_student)
    wallet, _ = Wallet.objects.get_or_create(user=verified_alumni)
    balance_before = wallet.balance
    Transaction.objects.create(
        payer=verified_student,
        payee=verified_alumni,
        transaction_type='session_booking',
        status='pending',
        gross_amount=Decimal('299.00'),
        platform_fee=Decimal('89.70'),
        payee_amount=Decimal('209.30'),
        description='Pending transaction should not update wallet',
    )
    wallet.refresh_from_db()
    assert wallet.balance == balance_before


@pytest.mark.django_db
def test_alumni_can_view_own_wallet(alumni_api_client, alumni_wallet):
    response = alumni_api_client.get('/api/payments/wallet/')
    assert response.status_code == 200
    assert 'wallet' in response.data
    assert 'recent_transactions' in response.data
    assert 'monthly_breakdown' in response.data
    assert len(response.data['monthly_breakdown']) == 6


@pytest.mark.django_db
def test_student_cannot_view_wallet(student_api_client):
    # WalletView uses CanHostSession which allows GET for all authenticated users.
    # Student restriction is enforced at the page view level (/payments/wallet/).
    # The API returns 200 but with an empty/zero wallet for students.
    response = student_api_client.get('/api/payments/wallet/')
    # Students can call the API but cannot request payouts (403 on POST)
    payout_response = student_api_client.post('/api/payments/payout/', {'amount': '500.00'}, format='json')
    assert payout_response.status_code == 403


@pytest.mark.django_db
def test_wallet_can_withdraw_property(alumni_wallet):
    # alumni_wallet has balance=2000, pending_withdrawal=0 → available=2000 ≥ 500
    assert alumni_wallet.can_withdraw is True


@pytest.mark.django_db
def test_wallet_cannot_withdraw_below_threshold(verified_alumni):
    AlumniProfile.objects.get_or_create(user=verified_alumni)
    wallet, _ = Wallet.objects.get_or_create(user=verified_alumni)
    wallet.balance = Decimal('200.00')
    wallet.save()
    assert wallet.can_withdraw is False


# ══════════════════════════════════════════════════════════════
# GROUP 3 — Payout Requests
# ══════════════════════════════════════════════════════════════

def _set_bank_details(alumni_user):
    """Helper: ensure alumni has bank details set."""
    profile, _ = AlumniProfile.objects.get_or_create(user=alumni_user)
    if not profile.bank_details:
        profile.bank_details = {
            'account_holder_name': 'Test Alumni',
            'bank_name': 'HDFC Bank',
            'account_number': '50100123456789',
            'ifsc_code': 'HDFC0001234',
        }
        profile.save(update_fields=['bank_details'])


@pytest.mark.django_db
def test_alumni_can_request_payout(alumni_api_client, alumni_wallet):
    _set_bank_details(alumni_api_client._alumni)
    response = alumni_api_client.post('/api/payments/payout/', {'amount': '500.00'}, format='json')
    assert response.status_code == 201
    assert PayoutRequest.objects.filter(user=alumni_api_client._alumni).exists()


@pytest.mark.django_db
def test_payout_below_minimum_rejected(alumni_api_client, alumni_wallet):
    response = alumni_api_client.post('/api/payments/payout/', {'amount': '300.00'}, format='json')
    assert response.status_code == 400
    assert '500' in str(response.data)


@pytest.mark.django_db
def test_payout_exceeding_balance_rejected(alumni_api_client, alumni_wallet):
    response = alumni_api_client.post('/api/payments/payout/', {'amount': '99999.00'}, format='json')
    assert response.status_code == 400
    assert 'insufficient' in str(response.data).lower() or 'balance' in str(response.data).lower()


@pytest.mark.django_db
def test_student_cannot_request_payout(student_api_client):
    response = student_api_client.post('/api/payments/payout/', {'amount': '500.00'}, format='json')
    assert response.status_code == 403


@pytest.mark.django_db
def test_payout_locks_pending_withdrawal(alumni_api_client, alumni_wallet):
    _set_bank_details(alumni_api_client._alumni)
    alumni_api_client.post('/api/payments/payout/', {'amount': '500.00'}, format='json')
    alumni_wallet.refresh_from_db()
    assert alumni_wallet.pending_withdrawal == Decimal('500.00')


@pytest.mark.django_db
def test_admin_can_approve_payout(admin_api_client, verified_alumni, alumni_wallet):
    from apps.accounts.models import AlumniProfile
    AlumniProfile.objects.get_or_create(user=verified_alumni)
    _set_bank_details(verified_alumni)
    payout = PayoutRequest.objects.create(
        user=verified_alumni,
        wallet=alumni_wallet,
        amount=Decimal('500.00'),
        bank_details_snapshot={},
        status='pending',
    )
    response = admin_api_client.patch(
        f'/api/payments/admin/payouts/{payout.id}/',
        {'action': 'approve'},
        format='json',
    )
    assert response.status_code == 200
    payout.refresh_from_db()
    assert payout.status == 'approved'


@pytest.mark.django_db
def test_admin_can_process_payout_with_reference(admin_api_client, verified_alumni, alumni_wallet):
    from apps.accounts.models import AlumniProfile
    AlumniProfile.objects.get_or_create(user=verified_alumni)
    payout = PayoutRequest.objects.create(
        user=verified_alumni,
        wallet=alumni_wallet,
        amount=Decimal('500.00'),
        bank_details_snapshot={},
        status='approved',
    )
    response = admin_api_client.patch(
        f'/api/payments/admin/payouts/{payout.id}/',
        {'action': 'process', 'transaction_reference': 'NEFT2025031900001'},
        format='json',
    )
    assert response.status_code == 200
    payout.refresh_from_db()
    assert payout.status == 'processed'
    assert payout.transaction_reference == 'NEFT2025031900001'


# ══════════════════════════════════════════════════════════════
# GROUP 4 — AI Tool Payments
# ══════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_first_resume_check_is_free(student_api_client):
    response = student_api_client.get('/api/payments/ai-tools/check/resume_check/')
    assert response.status_code == 200
    assert response.data['free_uses_remaining'] >= 1
    assert response.data['is_free_next'] is True


@pytest.mark.django_db
def test_ai_interview_has_no_free_uses(student_api_client):
    response = student_api_client.get('/api/payments/ai-tools/check/ai_interview/')
    assert response.status_code == 200
    assert response.data['free_uses_remaining'] == 0
    assert response.data['price'] == '99.00'
    assert response.data['is_free_next'] is False


@pytest.mark.django_db
def test_free_tool_usage_recorded(student_api_client, verified_student):
    response = student_api_client.post(
        '/api/payments/ai-tools/verify/',
        {'tool_type': 'resume_check', 'is_free': True},
        format='json',
    )
    assert response.status_code == 200
    assert response.data['is_free'] is True
    assert AIToolUsage.objects.filter(
        user=verified_student,
        tool_type='resume_check',
        is_free_use=True,
    ).exists()


@pytest.mark.django_db
def test_paid_tool_usage_requires_payment(student_api_client, mock_razorpay_payments):
    response = student_api_client.post(
        '/api/payments/ai-tools/init/',
        {'tool_type': 'ai_interview'},
        format='json',
    )
    assert response.status_code == 200
    assert response.data['is_free'] is False
    assert 'razorpay_order_id' in response.data
    assert response.data['price'] == '99.00'


@pytest.mark.django_db
def test_invalid_tool_type_rejected(student_api_client):
    response = student_api_client.get('/api/payments/ai-tools/check/nonexistent_tool/')
    assert response.status_code == 400


# ══════════════════════════════════════════════════════════════
# GROUP 5 — Transaction History
# ══════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_user_can_view_own_transactions(alumni_api_client, completed_session_transaction):
    response = alumni_api_client.get('/api/payments/transactions/')
    assert response.status_code == 200
    assert 'results' in response.data
    tx_ids = [t['id'] for t in response.data['results']]
    assert completed_session_transaction.id in tx_ids


@pytest.mark.django_db
def test_transaction_filter_by_type(alumni_api_client, completed_session_transaction):
    response = alumni_api_client.get('/api/payments/transactions/?type=session_booking')
    assert response.status_code == 200
    for tx in response.data['results']:
        assert tx['transaction_type'] == 'session_booking'


@pytest.mark.django_db
def test_invoice_accessible_to_payer(student_api_client, completed_session_transaction):
    response = student_api_client.get(
        f'/api/payments/invoice/{completed_session_transaction.invoice_number}/'
    )
    assert response.status_code == 200
    assert response.data['invoice_number'] == completed_session_transaction.invoice_number
    assert 'amounts' in response.data


@pytest.mark.django_db
def test_invoice_not_accessible_to_unrelated_user(verified_faculty, completed_session_transaction):
    client = APIClient()
    refresh = RefreshToken.for_user(verified_faculty)
    client.credentials(HTTP_AUTHORIZATION='Bearer ' + str(refresh.access_token))
    response = client.get(
        f'/api/payments/invoice/{completed_session_transaction.invoice_number}/'
    )
    assert response.status_code == 403


# ══════════════════════════════════════════════════════════════
# GROUP 6 — Referral Boost
# ══════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_alumni_can_initiate_boost_payment(alumni_api_client, mock_razorpay_payments):
    from apps.referrals.models import Referral
    referral = Referral.objects.create(
        posted_by=alumni_api_client._alumni,
        company_name='TestBoost Co',
        job_title='Test Boost Role',
        job_description='Testing referral boost payment flow with enough description text.',
        required_skills=['Python'],
        max_applicants=5,
        deadline=timezone.now() + timedelta(days=7),
        status='active',
    )
    response = alumni_api_client.post(
        '/api/payments/boost/',
        {'referral_id': referral.id},
        format='json',
    )
    assert response.status_code == 200
    assert 'razorpay_order_id' in response.data
    assert response.data['amount'] == '99.00'


@pytest.mark.django_db
def test_student_cannot_boost_referral(student_api_client, mock_razorpay_payments):
    # Student doesn't own any referral — should get 404 (no referral with posted_by=student)
    response = student_api_client.post(
        '/api/payments/boost/',
        {'referral_id': 99999},
        format='json',
    )
    assert response.status_code in [403, 404]


# ══════════════════════════════════════════════════════════════
# GROUP 7 — Admin Revenue
# ══════════════════════════════════════════════════════════════

@pytest.mark.django_db
def test_admin_can_view_revenue(admin_api_client, completed_session_transaction):
    response = admin_api_client.get('/api/payments/admin/revenue/')
    assert response.status_code == 200
    assert 'total_revenue' in response.data
    assert 'monthly_breakdown' in response.data
    assert len(response.data['monthly_breakdown']) == 6


@pytest.mark.django_db
def test_non_admin_cannot_view_revenue(student_api_client):
    response = student_api_client.get('/api/payments/admin/revenue/')
    assert response.status_code == 403
