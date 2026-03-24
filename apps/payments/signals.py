from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal


def _send_notification(user, title, message, link='/payments/wallet/'):
    """Send a notification via the central notify utility."""
    try:
        from utils.notify import send_notification
        send_notification(user=user, notif_type='payout', title=title, message=message, link=link)
    except Exception:
        pass


@receiver(post_save, sender='payments.Transaction')
def handle_transaction_completed(sender, instance, created, **kwargs):
    """When a completed transaction is created, credit the payee's wallet."""
    if not created:
        return
    if instance.status != 'completed':
        return
    if not instance.payee or instance.payee_amount <= 0:
        return

    from apps.payments.models import Wallet
    wallet, _ = Wallet.objects.get_or_create(user=instance.payee)
    wallet.balance += instance.payee_amount
    wallet.total_earned += instance.payee_amount
    wallet.save(update_fields=['balance', 'total_earned', 'updated_at'])

    # Keep profile wallet_balance fields in sync
    try:
        if instance.payee.role == 'alumni':
            from apps.accounts.models import AlumniProfile
            AlumniProfile.objects.filter(user=instance.payee).update(
                wallet_balance=wallet.balance,
                total_earned=wallet.total_earned,
            )
        elif instance.payee.role == 'faculty':
            from apps.accounts.models import FacultyProfile
            FacultyProfile.objects.filter(user=instance.payee).update(
                wallet_balance=wallet.balance,
                total_earned=wallet.total_earned,
            )
    except Exception:
        pass


@receiver(post_save, sender='payments.PayoutRequest')
def handle_payout_status_change(sender, instance, created, **kwargs):
    """Handle wallet mutations when a payout request changes state."""
    from apps.payments.models import Wallet
    from django.utils import timezone

    if created:
        # Lock the requested amount in pending_withdrawal
        try:
            wallet = instance.wallet
            wallet.pending_withdrawal += instance.amount
            wallet.save(update_fields=['pending_withdrawal', 'updated_at'])
        except Exception:
            pass
        return

    if instance.status == 'processed':
        try:
            wallet = instance.wallet
            wallet.balance -= instance.amount
            wallet.total_withdrawn += instance.amount
            wallet.pending_withdrawal -= instance.amount
            wallet.last_payout_at = timezone.now()
            wallet.save()

            user = instance.user
            if user.role == 'alumni':
                from apps.accounts.models import AlumniProfile
                AlumniProfile.objects.filter(user=user).update(wallet_balance=wallet.balance)
            elif user.role == 'faculty':
                from apps.accounts.models import FacultyProfile
                FacultyProfile.objects.filter(user=user).update(wallet_balance=wallet.balance)
        except Exception:
            pass

        _send_notification(
            instance.user,
            title='Payout processed!',
            message=(
                f'₹{instance.amount} has been transferred to your bank account. '
                f'Reference: {instance.transaction_reference or "Processing"}'
            ),
        )

    elif instance.status == 'rejected':
        # Release locked amount back to available balance
        try:
            wallet = instance.wallet
            wallet.pending_withdrawal -= instance.amount
            wallet.save(update_fields=['pending_withdrawal', 'updated_at'])
        except Exception:
            pass

        _send_notification(
            instance.user,
            title='Payout request rejected',
            message=(
                f'Your payout request of ₹{instance.amount} was rejected. '
                f'Reason: {instance.admin_note or "Please contact support."}'
            ),
        )

    elif instance.status == 'cancelled':
        # Release locked amount
        try:
            wallet = instance.wallet
            wallet.pending_withdrawal -= instance.amount
            wallet.save(update_fields=['pending_withdrawal', 'updated_at'])
        except Exception:
            pass
