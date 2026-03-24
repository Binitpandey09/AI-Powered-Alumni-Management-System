from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal


class Referral(models.Model):
    WORK_TYPES = [
        ('full_time', 'Full Time'),
        ('internship', 'Internship'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('remote', 'Remote'),
    ]
    EXPERIENCE_LEVELS = [
        ('fresher', 'Fresher / 0-1 years'),
        ('junior', 'Junior / 1-3 years'),
        ('mid', 'Mid Level / 3-5 years'),
        ('senior', 'Senior / 5+ years'),
    ]
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('closed', 'Closed — All slots filled'),
        ('deactivated', 'Deactivated by Admin'),
        ('paused', 'Paused by Author'),
    ]

    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='posted_referrals',
    )
    company_name = models.CharField(max_length=300)
    company_logo_url = models.URLField(blank=True)
    job_title = models.CharField(max_length=300)
    job_description = models.TextField()
    work_type = models.CharField(max_length=20, choices=WORK_TYPES, default='full_time')
    experience_level = models.CharField(max_length=20, choices=EXPERIENCE_LEVELS, default='fresher')
    location = models.CharField(max_length=200, blank=True)
    is_remote = models.BooleanField(default=False)
    salary_range = models.CharField(max_length=100, blank=True)
    required_skills = models.JSONField(default=list)
    preferred_skills = models.JSONField(default=list, blank=True)
    minimum_cgpa = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    eligible_branches = models.JSONField(default=list, blank=True)
    eligible_graduation_years = models.JSONField(default=list, blank=True)
    apply_link = models.URLField(blank=True)
    max_applicants = models.IntegerField(default=5)
    total_applications = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    deadline = models.DateTimeField()
    is_urgent = models.BooleanField(default=False)
    is_boosted = models.BooleanField(default=False)
    boosted_until = models.DateTimeField(null=True, blank=True)
    admin_note = models.TextField(blank=True)
    tags = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_boosted', '-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['posted_by', 'status']),
            models.Index(fields=['deadline', 'status']),
        ]

    @property
    def is_expired(self):
        return timezone.now() > self.deadline

    @property
    def is_full(self):
        return self.total_applications >= self.max_applicants

    @property
    def slots_remaining(self):
        return max(0, self.max_applicants - self.total_applications)

    @property
    def is_accepting_applications(self):
        return (
            self.status == 'active'
            and not self.is_expired
            and not self.is_full
        )

    def __str__(self):
        return f"{self.job_title} @ {self.company_name} by {self.posted_by.email}"


class ReferralApplication(models.Model):
    APPLICATION_STATUS = [
        ('applied', 'Applied'),
        ('under_review', 'Under Review'),
        ('shortlisted', 'Shortlisted'),
        ('interview_scheduled', 'Interview Scheduled'),
        ('rejected', 'Rejected'),
        ('hired', 'Hired'),
        ('withdrawn', 'Withdrawn by Student'),
    ]

    referral = models.ForeignKey(
        Referral,
        on_delete=models.CASCADE,
        related_name='applications',
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='referral_applications',
    )
    status = models.CharField(max_length=30, choices=APPLICATION_STATUS, default='applied')
    match_score = models.IntegerField(default=0)
    matched_skills = models.JSONField(default=list)
    missing_skills = models.JSONField(default=list)
    is_faculty_recommended = models.BooleanField(default=False)
    recommended_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='faculty_recommendations',
    )
    recommendation_note = models.TextField(blank=True)
    cover_note = models.TextField(blank=True)
    alumni_note = models.TextField(blank=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('referral', 'student')
        ordering = ['-is_faculty_recommended', '-match_score', 'applied_at']

    def __str__(self):
        return f"{self.student.email} → {self.referral.job_title} [{self.status}]"


class ReferralSuccessStory(models.Model):
    application = models.OneToOneField(
        ReferralApplication,
        on_delete=models.CASCADE,
        related_name='success_story',
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='success_stories',
    )
    alumni = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='referral_successes',
    )
    company_name = models.CharField(max_length=300)
    job_title = models.CharField(max_length=300)
    is_public = models.BooleanField(default=True)
    testimonial = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.email} hired at {self.company_name}"


class FacultyReferralRecommendation(models.Model):
    faculty = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='referral_recommendations',
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='faculty_referral_recommendations',
    )
    referral = models.ForeignKey(
        Referral,
        on_delete=models.CASCADE,
        related_name='faculty_recommendations',
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('faculty', 'student', 'referral')

    def __str__(self):
        return f"{self.faculty.email} recommends {self.student.email} for {self.referral.job_title}"
