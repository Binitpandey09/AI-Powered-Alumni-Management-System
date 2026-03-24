from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class User(AbstractUser):
    """Custom User model with role-based access"""

    ALUMNI = 'alumni'
    STUDENT = 'student'
    FACULTY = 'faculty'
    ADMIN = 'admin'

    ROLE_CHOICES = (
        (ALUMNI, 'Alumni'),
        (STUDENT, 'Student'),
        (FACULTY, 'Faculty'),
        (ADMIN, 'Admin'),
    )

    role = models.CharField(max_length=10, choices=ROLE_CHOICES, blank=False)
    phone = models.CharField(max_length=15, blank=True)
    profile_pic = models.ImageField(upload_to='profiles/', blank=True, null=True)
    college = models.CharField(max_length=300, blank=True)
    batch_year = models.IntegerField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    is_profile_complete = models.BooleanField(default=False)
    is_suspended = models.BooleanField(default=False)
    suspended_reason = models.TextField(blank=True)
    suspended_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"

    @property
    def is_alumni(self):
        return self.role == self.ALUMNI

    @property
    def is_student(self):
        return self.role == self.STUDENT

    @property
    def is_faculty(self):
        return self.role == self.FACULTY

    @property
    def full_name(self):
        name = f"{self.first_name} {self.last_name}".strip()
        return name if name else self.username


class AlumniProfile(models.Model):
    """Extended profile for Alumni users"""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='alumni_profile'
    )
    company = models.CharField(max_length=300, blank=True)
    designation = models.CharField(max_length=300, blank=True)
    company_email = models.EmailField(unique=True, null=True, blank=True)
    linkedin_url = models.URLField(blank=True)
    years_of_experience = models.IntegerField(default=0)
    skills = models.JSONField(default=list, blank=True)
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_earned = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    bank_details = models.JSONField(default=dict, blank=True)
    bank_verified = models.BooleanField(default=False)
    impact_score = models.IntegerField(default=0)
    verification_document = models.FileField(
        upload_to='verification_docs/', blank=True, null=True
    )
    is_available_for_1on1 = models.BooleanField(default=False)
    price_per_30min = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    price_per_60min = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    bio = models.TextField(blank=True)
    # Verification fields
    is_verified = models.BooleanField(default=False)
    verification_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending Review'),
            ('verified', 'Verified'),
            ('rejected', 'Rejected'),
            ('not_submitted', 'Not Submitted'),
        ],
        default='not_submitted',
    )
    verification_document_url = models.URLField(blank=True)
    verification_note = models.TextField(blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='alumni_verifications_done',
    )

    class Meta:
        verbose_name = 'Alumni Profile'
        verbose_name_plural = 'Alumni Profiles'

    def __str__(self):
        return f"Alumni Profile — {self.user.email}"


class StudentProfile(models.Model):
    """Extended profile for Student users"""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='student_profile'
    )
    college_email = models.EmailField(unique=True, null=True, blank=True)
    enrollment_number = models.CharField(max_length=50, blank=True)
    degree = models.CharField(max_length=200, blank=True)
    branch = models.CharField(max_length=200, blank=True)
    graduation_year = models.IntegerField(null=True, blank=True)
    skills = models.JSONField(default=list, blank=True)
    resume_file = models.FileField(upload_to='resumes/', blank=True, null=True)
    resume_score = models.IntegerField(null=True, blank=True)
    github_url = models.URLField(blank=True)
    portfolio_url = models.URLField(blank=True)
    looking_for = models.CharField(max_length=200, blank=True)
    demo_session_used = models.BooleanField(default=False)
    resume_check_count = models.IntegerField(default=0)
    # New Naukri-style fields
    profile_summary = models.TextField(blank=True)
    gender = models.CharField(
        max_length=20,
        choices=[
            ('male', 'Male'), ('female', 'Female'),
            ('other', 'Other'), ('prefer_not_to_say', 'Prefer not to say'),
        ],
        blank=True,
    )
    date_of_birth = models.DateField(null=True, blank=True)
    current_location = models.CharField(max_length=200, blank=True)
    preferred_locations = models.JSONField(default=list, blank=True)
    availability = models.CharField(max_length=50, blank=True)
    profile_completeness_score = models.IntegerField(default=0)

    class Meta:
        verbose_name = 'Student Profile'
        verbose_name_plural = 'Student Profiles'

    def __str__(self):
        return f"Student Profile — {self.user.email}"


# ── Student Profile Section Models ───────────────────────────────────────────

class StudentEducation(models.Model):
    EDUCATION_TYPES = [
        ('graduation', 'Graduation / Post Graduation'),
        ('class_12', 'Class XII'),
        ('class_10', 'Class X'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='educations')
    education_type = models.CharField(max_length=20, choices=EDUCATION_TYPES)
    degree = models.CharField(max_length=200, blank=True)
    specialization = models.CharField(max_length=200, blank=True)
    institute_name = models.CharField(max_length=300)
    board_or_university = models.CharField(max_length=300, blank=True)
    start_year = models.IntegerField(null=True, blank=True)
    end_year = models.IntegerField(null=True, blank=True)
    is_pursuing = models.BooleanField(default=False)
    grade_type = models.CharField(
        max_length=10,
        choices=[('percentage', 'Percentage'), ('cgpa', 'CGPA')],
        blank=True,
    )
    grade_value = models.CharField(max_length=10, blank=True)
    study_mode = models.CharField(
        max_length=20,
        choices=[('full_time', 'Full Time'), ('part_time', 'Part Time'), ('distance', 'Distance')],
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-end_year', '-start_year']

    def __str__(self):
        return f"{self.user.email} — {self.institute_name}"


class StudentProject(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects')
    title = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    tech_stack = models.JSONField(default=list)
    start_month = models.CharField(max_length=20, blank=True)
    end_month = models.CharField(max_length=20, blank=True)
    is_ongoing = models.BooleanField(default=False)
    project_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} — {self.title}"


class StudentInternship(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='internships')
    company_name = models.CharField(max_length=300)
    role = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_month = models.CharField(max_length=20, blank=True)
    end_month = models.CharField(max_length=20, blank=True)
    is_ongoing = models.BooleanField(default=False)
    stipend = models.CharField(max_length=50, blank=True)
    location = models.CharField(max_length=200, blank=True)
    skills_used = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} — {self.company_name}"


class StudentCertification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='certifications')
    title = models.CharField(max_length=300)
    issuing_organization = models.CharField(max_length=300)
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    does_not_expire = models.BooleanField(default=False)
    credential_id = models.CharField(max_length=200, blank=True)
    credential_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-issue_date']

    def __str__(self):
        return f"{self.user.email} — {self.title}"


class StudentAward(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='awards')
    title = models.CharField(max_length=300)
    issuer = models.CharField(max_length=300, blank=True)
    date_received = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} — {self.title}"


class StudentCompetitiveExam(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='competitive_exams')
    exam_name = models.CharField(max_length=200)
    year = models.IntegerField(null=True, blank=True)
    score_or_rank = models.CharField(max_length=100, blank=True)
    description = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} — {self.exam_name}"


class StudentLanguage(models.Model):
    PROFICIENCY = [
        ('beginner', 'Beginner'),
        ('proficient', 'Proficient'),
        ('expert', 'Expert / Native'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='languages')
    language = models.CharField(max_length=100)
    proficiency = models.CharField(max_length=20, choices=PROFICIENCY, default='proficient')
    can_read = models.BooleanField(default=True)
    can_write = models.BooleanField(default=True)
    can_speak = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} — {self.language}"


class StudentEmployment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='employments')
    company_name = models.CharField(max_length=300)
    job_title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_month = models.CharField(max_length=20, blank=True)
    end_month = models.CharField(max_length=20, blank=True)
    is_current = models.BooleanField(default=False)
    location = models.CharField(max_length=200, blank=True)
    skills_used = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} — {self.company_name}"


class FacultyProfile(models.Model):
    """Extended profile for Faculty users"""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='faculty_profile'
    )
    college_email = models.EmailField(unique=True, null=True, blank=True)
    employee_id = models.CharField(max_length=100, blank=True)
    department = models.CharField(max_length=200, blank=True)
    designation = models.CharField(max_length=200, blank=True)
    subjects = models.JSONField(default=list, blank=True)
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_earned = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    bank_details = models.JSONField(default=dict, blank=True)
    bank_verified = models.BooleanField(default=False)
    bio = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Faculty Profile'
        verbose_name_plural = 'Faculty Profiles'

    def __str__(self):
        return f"Faculty Profile — {self.user.email}"


class EmailOTP(models.Model):
    """OTP model for email-based authentication"""

    REGISTRATION = 'registration'
    LOGIN = 'login'
    VERIFY = 'verify'

    PURPOSE_CHOICES = (
        (REGISTRATION, 'Registration'),
        (LOGIN, 'Login'),
        (VERIFY, 'Verify'),
    )

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='otps', null=True, blank=True
    )
    email = models.EmailField()
    otp_code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        verbose_name = 'Email OTP'
        verbose_name_plural = 'Email OTPs'
        ordering = ['-created_at']

    def __str__(self):
        return f"OTP({self.purpose}) → {self.email}"

    def is_expired(self):
        return timezone.now() > self.expires_at

    def is_valid(self):
        return not self.is_used and not self.is_expired()


class AdminActionLog(models.Model):
    ACTION_TYPES = [
        ('user_verified', 'User Verified'),
        ('user_suspended', 'User Suspended'),
        ('user_unsuspended', 'User Unsuspended'),
        ('user_deleted', 'User Deleted'),
        ('post_hidden', 'Post Hidden'),
        ('post_deleted', 'Post Deleted'),
        ('post_approved', 'Post Approved'),
        ('session_cancelled', 'Session Cancelled'),
        ('referral_deactivated', 'Referral Deactivated'),
        ('payout_approved', 'Payout Approved'),
        ('payout_processed', 'Payout Processed'),
        ('payout_rejected', 'Payout Rejected'),
        ('alumni_verified', 'Alumni Profile Verified'),
        ('alumni_rejected', 'Alumni Verification Rejected'),
        ('broadcast_sent', 'Broadcast Notification Sent'),
        ('other', 'Other'),
    ]

    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='admin_actions',
    )
    action_type = models.CharField(max_length=30, choices=ACTION_TYPES)
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='admin_actions_received',
    )
    target_object_type = models.CharField(max_length=50, blank=True)
    target_object_id = models.IntegerField(null=True, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.admin} — {self.action_type} — {self.created_at.date()}"
