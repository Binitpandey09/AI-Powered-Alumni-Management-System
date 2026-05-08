from django.db import models
from django.conf import settings
from django.utils import timezone


class Notification(models.Model):
    NOTIF_TYPES = [
        ('general', 'General'),
        ('session', 'Session'),
        ('referral', 'Referral'),
        ('payment', 'Payment'),
        ('verification', 'Verification'),
        ('booking_confirmed', 'Booking Confirmed'),
        ('booking_cancelled', 'Booking Cancelled'),
        ('new_booking', 'New Booking'),
        ('session_cancelled_by_host', 'Session Cancelled by Host'),
        ('referral_applied', 'Referral Applied'),
        ('payout', 'Payout'),
        ('connection_request', 'Connection Request'),
        ('connection_accepted', 'Connection Accepted'),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    notif_type = models.CharField(max_length=40, choices=NOTIF_TYPES, default='general')
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=300, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    # Generic FK for related object (optional)
    related_object_type = models.CharField(max_length=50, blank=True)
    related_object_id = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['recipient', 'created_at']),
        ]

    def __str__(self):
        return f"Notification({self.notif_type}) → {self.recipient.email}"

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class NotificationPreference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notification_preference',
    )
    # In-app toggles (granular)
    inapp_general = models.BooleanField(default=True)
    inapp_session = models.BooleanField(default=True)
    inapp_referral = models.BooleanField(default=True)
    inapp_payment = models.BooleanField(default=True)
    # Granular in-app aliases (map to category fields above)
    in_app_session_booked = models.BooleanField(default=True)
    in_app_session_reminder = models.BooleanField(default=True)
    in_app_session_cancelled = models.BooleanField(default=True)
    in_app_payment_received = models.BooleanField(default=True)
    in_app_referral_applied = models.BooleanField(default=True)
    in_app_application_update = models.BooleanField(default=True)
    in_app_general = models.BooleanField(default=True)
    in_app_admin_broadcast = models.BooleanField(default=True)
    # Email toggles
    email_general = models.BooleanField(default=False)
    email_session = models.BooleanField(default=True)
    email_referral = models.BooleanField(default=True)
    email_payment = models.BooleanField(default=True)
    # Granular email aliases
    email_session_booked = models.BooleanField(default=True)
    email_session_reminder = models.BooleanField(default=False)
    email_session_cancelled = models.BooleanField(default=True)
    email_payment_received = models.BooleanField(default=True)
    email_referral_applied = models.BooleanField(default=True)
    email_application_update = models.BooleanField(default=False)
    email_admin_broadcast = models.BooleanField(default=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"NotificationPreference({self.user.email})"
