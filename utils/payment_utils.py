import razorpay
from django.conf import settings
from decimal import Decimal


def get_razorpay_client():
    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )


def create_razorpay_order(amount_inr, receipt_id, notes=None):
    """
    Creates a Razorpay order.
    amount_inr: Decimal or float — amount in INR
    receipt_id: str — unique receipt identifier (max 40 chars)
    Returns: Razorpay order dict
    """
    client = get_razorpay_client()
    amount_paise = int(Decimal(str(amount_inr)) * 100)
    order_data = {
        'amount': amount_paise,
        'currency': 'INR',
        'receipt': str(receipt_id)[:40],
    }
    if notes:
        order_data['notes'] = notes
    return client.order.create(order_data)


def verify_razorpay_signature(order_id, payment_id, signature):
    """
    Verifies Razorpay payment signature.
    Returns True if valid, False otherwise.
    """
    try:
        client = get_razorpay_client()
        client.utility.verify_payment_signature({
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature,
        })
        return True
    except Exception:
        return False


def calculate_split(gross_amount, platform_pct=Decimal('0.30')):
    """
    Calculates the platform/payee split.
    Returns (platform_fee, payee_amount) both as Decimal.
    Uses subtraction to avoid floating-point rounding errors.
    """
    gross = Decimal(str(gross_amount))
    platform_fee = round(gross * Decimal(str(platform_pct)), 2)
    payee_amount = gross - platform_fee
    return platform_fee, payee_amount


def create_transaction(
    payer,
    gross_amount,
    transaction_type,
    description,
    payee=None,
    platform_pct=Decimal('0.30'),
    razorpay_order_id='',
    razorpay_payment_id='',
    razorpay_signature='',
    related_object_type='',
    related_object_id=None,
    status='pending',
):
    """
    Central function to create a Transaction record.
    Handles split calculation automatically.

    For AI tools / boosts: payee=None, platform_pct=1.0 (100% to platform)
    For sessions: payee=host, platform_pct=0.30 (30% platform, 70% host)
    """
    from apps.payments.models import Transaction

    if payee:
        platform_fee, payee_amount = calculate_split(gross_amount, platform_pct)
    else:
        platform_fee = Decimal(str(gross_amount))
        payee_amount = Decimal('0.00')

    transaction = Transaction.objects.create(
        payer=payer,
        payee=payee,
        transaction_type=transaction_type,
        status=status,
        gross_amount=Decimal(str(gross_amount)),
        platform_fee=platform_fee,
        payee_amount=payee_amount,
        razorpay_order_id=razorpay_order_id,
        razorpay_payment_id=razorpay_payment_id,
        razorpay_signature=razorpay_signature,
        related_object_type=related_object_type,
        related_object_id=related_object_id,
        description=description,
    )
    return transaction


def get_next_monday():
    """Returns the next Monday date (for payout scheduling display)."""
    from datetime import timedelta
    from django.utils import timezone
    today = timezone.now().date()
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    return today + timedelta(days=days_until_monday)
