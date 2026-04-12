from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone


# ── Signal 1 & 2 & 3: Booking status transitions ─────────────────────────────

# Track previous status to detect transitions
_booking_prev_status = {}


@receiver(pre_save, sender='sessions_app.Booking')
def booking_pre_save(sender, instance, **kwargs):
    """Cache the previous status before save so post_save can detect transitions."""
    if instance.pk:
        try:
            _booking_prev_status[instance.pk] = sender.objects.get(pk=instance.pk).status
        except sender.DoesNotExist:
            _booking_prev_status[instance.pk] = None
    else:
        _booking_prev_status[instance.pk] = None


@receiver(post_save, sender='sessions_app.Booking')
def booking_post_save(sender, instance, created, **kwargs):
    prev = _booking_prev_status.pop(instance.pk, None)
    current = instance.status

    if current == prev and not created:
        return  # No status change

    if current == 'confirmed' and prev != 'confirmed':
        _handle_booking_confirmed(instance)

    elif current == 'cancelled_by_student' and prev not in ('cancelled_by_student',):
        _handle_cancelled_by_student(instance)

    elif current == 'cancelled_by_host' and prev not in ('cancelled_by_host',):
        _handle_cancelled_by_host(instance)


def _handle_booking_confirmed(booking):
    """Increment seat count, calculate revenue split, update wallets, notify."""
    from django.db import transaction
    from apps.accounts.models import AlumniProfile, FacultyProfile

    session = booking.session

    # Increment booked seats
    session.__class__.objects.filter(pk=session.pk).update(
        booked_seats=session.__class__._default_manager.filter(pk=session.pk).values('booked_seats')[0]['booked_seats'] + 1
    )
    session.refresh_from_db(fields=['booked_seats'])

    # Calculate revenue split
    if booking.is_free_demo or booking.amount_paid == 0:
        platform_cut = 0
        host_share = 0
    else:
        platform_cut = round(float(booking.amount_paid) * 0.30, 2)
        host_share = round(float(booking.amount_paid) * 0.70, 2)

    # Update booking splits (avoid re-triggering signal by using queryset update)
    booking.__class__.objects.filter(pk=booking.pk).update(
        platform_cut=platform_cut,
        host_share=host_share,
    )

    # Update session revenue totals
    session.__class__.objects.filter(pk=session.pk).update(
        total_revenue=float(session.total_revenue) + float(booking.amount_paid),
        platform_earned=float(session.platform_earned) + platform_cut,
        host_earned=float(session.host_earned) + host_share,
    )

    # Update host wallet
    host = session.host
    if host_share > 0:
        from apps.payments.models import Wallet
        from decimal import Decimal
        wallet, _ = Wallet.objects.get_or_create(user=host)
        wallet.balance += Decimal(str(host_share))
        wallet.total_earned += Decimal(str(host_share))
        wallet.save(update_fields=['balance', 'total_earned', 'updated_at'])

        if host.role == 'alumni':
            try:
                profile = host.alumni_profile
                profile.__class__.objects.filter(pk=profile.pk).update(
                    wallet_balance=wallet.balance,
                    total_earned=wallet.total_earned,
                )
            except Exception:
                pass
        elif host.role == 'faculty':
            try:
                profile = host.faculty_profile
                profile.__class__.objects.filter(pk=profile.pk).update(
                    wallet_balance=wallet.balance,
                    total_earned=wallet.total_earned,
                )
            except Exception:
                pass

    # Notifications
    _create_notification(
        user=booking.student,
        title='Booking Confirmed',
        message=f'Your booking for "{session.title}" is confirmed!',
        notif_type='booking_confirmed',
        data={'session_id': session.id, 'booking_id': booking.id},
    )
    _create_notification(
        user=host,
        title='New Booking',
        message=f'New booking for "{session.title}" from {booking.student.full_name}',
        notif_type='new_booking',
        data={'session_id': session.id, 'booking_id': booking.id},
    )


def _handle_cancelled_by_student(booking):
    """Decrement seat, calculate refund, notify student."""
    session = booking.session

    # Decrement booked seats (floor at 0)
    current_seats = session.__class__.objects.filter(pk=session.pk).values('booked_seats')[0]['booked_seats']
    session.__class__.objects.filter(pk=session.pk).update(
        booked_seats=max(0, current_seats - 1)
    )

    # Calculate refund
    refund_amount = 0
    if booking.is_free_demo:
        # Reset demo slot
        try:
            profile = booking.student.student_profile
            profile.__class__.objects.filter(pk=profile.pk).update(demo_session_used=False)
        except Exception:
            pass
    else:
        hours_until = (session.scheduled_at - timezone.now()).total_seconds() / 3600
        if hours_until > 2:
            refund_amount = round(float(booking.amount_paid) * 0.50, 2)

    booking.__class__.objects.filter(pk=booking.pk).update(refund_amount=refund_amount)

    _create_notification(
        user=booking.student,
        title='Booking Cancelled',
        message='Your booking has been cancelled.',
        notif_type='booking_cancelled',
        data={'session_id': session.id, 'booking_id': booking.id, 'refund_amount': refund_amount},
    )


def _handle_cancelled_by_host(booking):
    """Full refund, reverse wallet, notify student."""
    from apps.accounts.models import AlumniProfile, FacultyProfile

    session = booking.session

    # Decrement booked seats
    current_seats = session.__class__.objects.filter(pk=session.pk).values('booked_seats')[0]['booked_seats']
    session.__class__.objects.filter(pk=session.pk).update(
        booked_seats=max(0, current_seats - 1)
    )

    # Full refund
    refund_amount = float(booking.amount_paid)
    booking.__class__.objects.filter(pk=booking.pk).update(
        refund_amount=refund_amount,
        refunded_at=timezone.now(),
    )

    # Reverse host wallet deduction
    host_share = float(booking.host_share)
    if host_share > 0:
        from apps.payments.models import Wallet
        from decimal import Decimal
        host = session.host
        wallet, _ = Wallet.objects.get_or_create(user=host)
        wallet.balance = max(Decimal('0.00'), wallet.balance - Decimal(str(host_share)))
        wallet.total_earned = max(Decimal('0.00'), wallet.total_earned - Decimal(str(host_share)))
        wallet.save(update_fields=['balance', 'total_earned', 'updated_at'])

        if host.role == 'alumni':
            try:
                profile = host.alumni_profile
                profile.__class__.objects.filter(pk=profile.pk).update(
                    wallet_balance=wallet.balance,
                    total_earned=wallet.total_earned,
                )
            except Exception:
                pass
        elif host.role == 'faculty':
            try:
                profile = host.faculty_profile
                profile.__class__.objects.filter(pk=profile.pk).update(
                    wallet_balance=wallet.balance,
                    total_earned=wallet.total_earned,
                )
            except Exception:
                pass

    _create_notification(
        user=booking.student,
        title='Session Cancelled by Host',
        message=f'Session "{session.title}" has been cancelled by the host. Full refund initiated.',
        notif_type='session_cancelled_by_host',
        data={'session_id': session.id, 'booking_id': booking.id, 'refund_amount': refund_amount},
    )


# ── Signal 4: SessionReview created → update host impact score ────────────────

@receiver(post_save, sender='sessions_app.SessionReview')
def review_post_save(sender, instance, created, **kwargs):
    if not created:
        return
    _update_host_impact_score(instance.booking.session.host)


def _update_host_impact_score(host):
    from apps.sessions_app.models import SessionReview
    from apps.accounts.models import AlumniProfile, FacultyProfile
    from django.db.models import Avg, Count

    # Get all reviews for sessions hosted by this user
    agg = SessionReview.objects.filter(
        booking__session__host=host
    ).aggregate(avg=Avg('rating'), count=Count('id'))

    avg_rating = float(agg['avg'] or 0)
    total_reviews = agg['count'] or 0

    # impact_score = (avg_rating * 20) + min(total_reviews * 2, 40), max 100
    impact_score = min(100, int((avg_rating * 20) + min(total_reviews * 2, 40)))

    if host.role == 'alumni':
        AlumniProfile.objects.filter(user=host).update(impact_score=impact_score)
    elif host.role == 'faculty':
        # FacultyProfile doesn't have impact_score yet — store in bio or skip gracefully
        pass


# ── Helper: create notification ───────────────────────────────────────────────

def _create_notification(user, title, message, notif_type, data=None):
    """Send a notification via the central notify utility."""
    try:
        from utils.notify import send_notification
        link = ''
        if data:
            session_id = data.get('session_id')
            if session_id:
                link = f'/sessions/{session_id}/'
        send_notification(user=user, notif_type=notif_type, title=title, message=message, link=link)
    except Exception:
        pass
