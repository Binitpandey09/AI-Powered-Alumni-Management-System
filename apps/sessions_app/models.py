from django.db import models
from django.conf import settings


class Session(models.Model):
    SESSION_TYPES = [
        ('group', 'Group Session'),
        ('one_on_one', '1:1 Session'),
        ('cohort', 'Cohort Bundle'),
        ('recorded', 'Recorded Session'),
        ('doubt', 'Doubt Clearing Class'),
        ('project', 'Project Guidance'),
        ('career', 'Career Path Guidance'),
    ]
    STATUS_CHOICES = [
        ('upcoming', 'Upcoming'),
        ('live', 'Live Now'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    host = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='hosted_sessions',
    )
    co_host = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='co_hosted_sessions',
    )
    session_type = models.CharField(max_length=20, choices=SESSION_TYPES)
    title = models.CharField(max_length=300)
    description = models.TextField()
    niche = models.CharField(max_length=200, blank=True)
    skills_covered = models.JSONField(default=list)
    scheduled_at = models.DateTimeField()
    duration_minutes = models.IntegerField(default=60)
    total_sessions_in_bundle = models.IntegerField(default=1)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    is_free = models.BooleanField(default=False)
    is_demo_eligible = models.BooleanField(default=True)
    max_seats = models.IntegerField(default=10)
    booked_seats = models.IntegerField(default=0)
    meeting_link = models.URLField(blank=True)
    recording_url = models.URLField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='upcoming')
    cancellation_reason = models.TextField(blank=True)
    thumbnail = models.ImageField(upload_to='sessions/thumbnails/', blank=True, null=True)
    tags = models.JSONField(default=list)
    # Revenue tracking
    total_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    platform_earned = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    host_earned = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['scheduled_at']
        indexes = [
            models.Index(fields=['status', 'scheduled_at']),
            models.Index(fields=['host', 'status']),
            models.Index(fields=['host', '-created_at']),
            models.Index(fields=['session_type', 'status']),
        ]

    @property
    def is_full(self):
        return self.booked_seats >= self.max_seats

    @property
    def available_seats(self):
        return max(0, self.max_seats - self.booked_seats)

    @property
    def is_upcoming(self):
        from django.utils import timezone
        return self.scheduled_at > timezone.now()

    def __str__(self):
        return f"{self.title} by {self.host.email}"


class Booking(models.Model):
    BOOKING_STATUS = [
        ('pending_payment', 'Pending Payment'),
        ('confirmed', 'Confirmed'),
        ('cancelled_by_student', 'Cancelled by Student'),
        ('cancelled_by_host', 'Cancelled by Host'),
        ('completed', 'Completed'),
        ('refunded', 'Refunded'),
        ('no_show', 'No Show'),
    ]

    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='bookings')
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='session_bookings',
    )
    status = models.CharField(max_length=30, choices=BOOKING_STATUS, default='pending_payment')
    # Payment
    amount_paid = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    is_free_demo = models.BooleanField(default=False)
    platform_cut = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    host_share = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    # Razorpay
    razorpay_order_id = models.CharField(max_length=200, blank=True)
    razorpay_payment_id = models.CharField(max_length=200, blank=True)
    razorpay_signature = models.CharField(max_length=500, blank=True)
    # Refund
    refund_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    refund_reason = models.TextField(blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)
    booked_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('session', 'student')
        ordering = ['-booked_at']

    def __str__(self):
        return f"{self.student.email} → {self.session.title} [{self.status}]"


class SessionReview(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='review')
    rating = models.IntegerField()  # 1 to 5
    review_text = models.TextField(blank=True)
    is_anonymous = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def clean(self):
        from django.core.exceptions import ValidationError
        if not 1 <= self.rating <= 5:
            raise ValidationError('Rating must be between 1 and 5.')
        if self.booking.status != 'completed':
            raise ValidationError('Can only review completed sessions.')

    def __str__(self):
        return f"Review by {self.booking.student.email} — {self.rating}★"


class SessionSlot(models.Model):
    """Time slots that alumni/faculty mark as available for 1:1 bookings"""
    host = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='available_slots',
    )
    slot_start = models.DateTimeField()
    slot_end = models.DateTimeField()
    is_booked = models.BooleanField(default=False)
    booking = models.OneToOneField(
        Booking,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='slot',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['slot_start']

    def __str__(self):
        return f"{self.host.email} slot: {self.slot_start} — {self.slot_end}"
