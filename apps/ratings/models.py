from django.db import models
from django.conf import settings

class SessionRating(models.Model):
    RATING_CHOICES = [(1,'1'),(2,'2'),(3,'3'),(4,'4'),(5,'5')]

    # The booking this rating is for
    booking = models.ForeignKey(
        'sessions_app.Booking',
        on_delete=models.CASCADE,
        related_name='ratings'
    )

    # Who is writing the rating
    rater = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ratings_given'
    )

    # Who is being rated
    ratee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ratings_received'
    )

    # Rating direction
    RATING_TYPE_CHOICES = [
        ('student_to_host', 'Student Rating Host'),
        ('host_to_student', 'Host Rating Student'),
    ]
    rating_type = models.CharField(max_length=20, choices=RATING_TYPE_CHOICES)

    # ── Core rating (always present) ──
    overall_rating = models.IntegerField(choices=RATING_CHOICES)

    # ── Student → Host specific fields ──
    communication_rating = models.IntegerField(choices=RATING_CHOICES, null=True, blank=True)
    value_rating = models.IntegerField(choices=RATING_CHOICES, null=True, blank=True)
    professionalism_rating = models.IntegerField(choices=RATING_CHOICES, null=True, blank=True)
    would_recommend = models.BooleanField(null=True, blank=True)
    review_text = models.TextField(blank=True, max_length=300)
    # Public review text — shown on host profile

    # ── Host → Student specific fields ──
    preparation_rating = models.IntegerField(choices=RATING_CHOICES, null=True, blank=True)
    engagement_rating = models.IntegerField(choices=RATING_CHOICES, null=True, blank=True)
    punctuality_rating = models.IntegerField(choices=RATING_CHOICES, null=True, blank=True)
    feedback_text = models.TextField(blank=True, max_length=200)
    # Private feedback — only visible to the student themselves

    # ── Meta ──
    is_edited = models.BooleanField(default=False)
    edited_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('booking', 'rater')
        # Only one rating per person per booking
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ratee', 'rating_type']),
            models.Index(fields=['ratee', 'overall_rating']),
        ]

    def __str__(self):
        return f"{self.rater.email} → {self.ratee.email} | {self.overall_rating}★ | {self.booking.session.title}"

    @property
    def can_edit(self):
        from django.utils import timezone
        from datetime import timedelta
        return (timezone.now() - self.created_at).total_seconds() < 48 * 3600

class ReferralRating(models.Model):
    RATING_CHOICES = [(1,'1'),(2,'2'),(3,'3'),(4,'4'),(5,'5')]

    application = models.OneToOneField(
        'referrals.ReferralApplication',
        on_delete=models.CASCADE,
        related_name='rating'
    )
    rater = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='referral_ratings_given'
    )
    ratee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='referral_ratings_received'
    )

    # Student rates the referral posting quality
    overall_rating = models.IntegerField(choices=RATING_CHOICES)
    process_rating = models.IntegerField(choices=RATING_CHOICES, null=True, blank=True)
    # How smooth/fair was the application process
    communication_rating = models.IntegerField(choices=RATING_CHOICES, null=True, blank=True)
    # How well the alumni communicated during the process
    review_text = models.TextField(blank=True, max_length=300)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Referral rating: {self.rater.email} → {self.ratee.email} | {self.overall_rating}★"

class UserRatingAggregate(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='rating_aggregate'
    )

    # Session ratings received as HOST (alumni/faculty rated by students)
    host_total_ratings = models.IntegerField(default=0)
    host_average_overall = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    host_average_communication = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    host_average_value = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    host_average_professionalism = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    host_would_recommend_pct = models.IntegerField(default=0)
    # Percentage of students who would recommend (0-100)

    # Rating distribution (how many 5★, 4★, 3★, 2★, 1★)
    host_five_star = models.IntegerField(default=0)
    host_four_star = models.IntegerField(default=0)
    host_three_star = models.IntegerField(default=0)
    host_two_star = models.IntegerField(default=0)
    host_one_star = models.IntegerField(default=0)

    # Session ratings received as STUDENT (student rated by alumni/faculty)
    student_total_ratings = models.IntegerField(default=0)
    student_average_overall = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    # This is private — not shown publicly

    # Referral ratings (alumni rated by students for referral quality)
    referral_total_ratings = models.IntegerField(default=0)
    referral_average_overall = models.DecimalField(max_digits=3, decimal_places=2, default=0)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"RatingAggregate — {self.user.email} — ★{self.host_average_overall}"
