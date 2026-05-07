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

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='alumni_profile'
    )

    # ── Section 2: Professional Information ──
    company = models.CharField(max_length=300, blank=True)
    # Current company name e.g. "Google", "Microsoft", "Infosys"
    designation = models.CharField(max_length=200, blank=True)
    # Current job title e.g. "Software Engineer", "Product Manager", "Data Scientist"
    employment_type = models.CharField(
        max_length=20,
        choices=[
            ('full_time', 'Full Time'),
            ('part_time', 'Part Time'),
            ('freelance', 'Freelance / Consultant'),
            ('entrepreneur', 'Entrepreneur / Founder'),
            ('not_working', 'Not Currently Working'),
        ],
        blank=True
    )
    industry = models.CharField(max_length=200, blank=True)
    # e.g. "Information Technology", "Finance", "Healthcare", "EdTech"
    years_of_experience = models.CharField(
        max_length=20,
        choices=[
            ('0-1', 'Fresher (0-1 years)'),
            ('1-3', '1-3 years'),
            ('3-5', '3-5 years'),
            ('5-10', '5-10 years'),
            ('10+', '10+ years'),
        ],
        blank=True
    )
    current_location = models.CharField(max_length=200, blank=True)
    # e.g. "Bangalore, Karnataka, India"
    is_open_to_opportunities = models.BooleanField(default=False)
    # Whether alumni is open to new job opportunities

    # ── Section 3: Academic Background ──
    graduation_year = models.IntegerField(null=True, blank=True)
    # Year they graduated e.g. 2020
    degree = models.CharField(max_length=200, blank=True)
    # e.g. "B.Tech", "B.E.", "MCA", "MBA"
    branch = models.CharField(max_length=200, blank=True)
    # e.g. "Computer Science", "Electronics", "Mechanical Engineering"
    college_name = models.CharField(max_length=300, blank=True)
    # College where they studied (auto-filled from User.college usually)
    cgpa_or_percentage = models.CharField(max_length=20, blank=True)
    # e.g. "8.5" or "85%"

    # ── Section 4: Skills & Expertise ──
    technical_skills = models.JSONField(default=list, blank=True)
    # e.g. ["Python", "Django", "React", "System Design", "AWS"]
    domain_expertise = models.JSONField(default=list, blank=True)
    # Higher-level domains e.g. ["Backend Development", "Machine Learning", "DevOps"]
    tools_used = models.JSONField(default=list, blank=True)
    # e.g. ["Git", "Docker", "Kubernetes", "Jira", "Figma"]
    soft_skills = models.JSONField(default=list, blank=True)
    # e.g. ["Leadership", "Mentoring", "Communication", "Problem Solving"]
    languages_known = models.JSONField(default=list, blank=True)
    # e.g. ["English", "Hindi", "Tamil"]

    # ── Section 5: Mentorship Preferences ──
    available_for_mentorship = models.BooleanField(default=True)
    # Can students book sessions with them?
    mentorship_areas = models.JSONField(default=list, blank=True)
    # What they mentor in e.g. ["Career Guidance", "Resume Review", "DSA Prep", "Interview Prep", "Project Help"]
    preferred_session_mode = models.CharField(
        max_length=10,
        choices=[('online', 'Online'), ('offline', 'Offline'), ('both', 'Both')],
        default='online'
    )
    preferred_session_duration = models.CharField(
        max_length=10,
        choices=[
            ('30', '30 minutes'),
            ('45', '45 minutes'),
            ('60', '60 minutes'),
            ('90', '90 minutes'),
        ],
        default='60'
    )
    max_students_per_week = models.IntegerField(default=5)
    # How many students they can take per week across all sessions
    session_price_range = models.CharField(max_length=50, blank=True)
    # e.g. "₹299 - ₹999" — informational only, actual price set per session

    # ── Section 6: Social & Online Presence ──
    linkedin_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    portfolio_url = models.URLField(blank=True)
    # Personal website or portfolio
    blog_url = models.URLField(blank=True)

    # ── Section 7: Bio & About ──
    bio = models.TextField(blank=True, max_length=600)
    # Shown on connect page, session cards, referral cards
    # Describe expertise, what you help students with, career highlights
    achievements = models.TextField(blank=True, max_length=500)
    # Notable achievements e.g. "Led a team of 15, shipped product used by 1M+ users"
    advice_for_students = models.TextField(blank=True, max_length=400)
    # Optional motivational advice shown on public profile

    # ── Section 8: Verification (for admin) ──
    is_verified = models.BooleanField(default=False)
    verification_status = models.CharField(
        max_length=20,
        choices=[
            ('not_submitted', 'Not Submitted'),
            ('pending', 'Pending Review'),
            ('verified', 'Verified'),
            ('rejected', 'Rejected'),
        ],
        default='not_submitted'
    )
    verification_document_url = models.URLField(blank=True)
    # LinkedIn URL or company email submitted for verification
    verification_note = models.TextField(blank=True)
    # Admin note on approval or rejection
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='alumni_verifications_done'
    )

    # ── Section 9: Bank Details (for payouts) ──
    bank_details = models.JSONField(default=dict, blank=True)
    # {account_holder_name, bank_name, account_number, ifsc_code, account_type}
    bank_verified = models.BooleanField(default=False)

    # ── Auto-calculated / Platform fields ──
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_earned = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    impact_score = models.IntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_ratings = models.IntegerField(default=0)
    # Impact score increases with: sessions hosted (+2 each), students helped (+1 each), placements (+5 each)

    # ── Profile completeness ──
    profile_completeness_score = models.IntegerField(default=0)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def calculate_completeness(self):
        score = 0
        user = self.user

        # Basic info (20 points)
        if user.first_name and user.last_name:
            score += 7
        if user.profile_pic:
            score += 7
        if self.current_location:
            score += 3
        if hasattr(user, 'phone') and user.phone:
            score += 3

        # Professional info (25 points)
        if self.company:
            score += 8
        if self.designation:
            score += 8
        if self.industry:
            score += 4
        if self.years_of_experience:
            score += 5

        # Academic background (10 points)
        if self.graduation_year:
            score += 4
        if self.degree and self.branch:
            score += 4
        if self.college_name:
            score += 2

        # Skills (20 points)
        if len(self.technical_skills or []) >= 5:
            score += 12
        elif len(self.technical_skills or []) >= 2:
            score += 6
        if len(self.domain_expertise or []) >= 1:
            score += 4
        if len(self.tools_used or []) >= 1:
            score += 4

        # Bio (10 points)
        if self.bio and len(self.bio) >= 80:
            score += 10
        elif self.bio and len(self.bio) >= 30:
            score += 5

        # Mentorship preferences set (5 points)
        if self.available_for_mentorship and len(self.mentorship_areas or []) >= 1:
            score += 5

        # Social links (5 points)
        if self.linkedin_url:
            score += 3
        if self.github_url or self.portfolio_url:
            score += 2

        # Bank details (5 points)
        if self.bank_details and self.bank_details.get('account_number'):
            score += 5

        return min(100, score)

    def save(self, *args, **kwargs):
        self.profile_completeness_score = self.calculate_completeness()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"AlumniProfile — {self.user.email}"

    class Meta:
        verbose_name = 'Alumni Profile'

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
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='faculty_profile'
    )
    college_email = models.EmailField(unique=True, null=True, blank=True)
    
    # ── Section 2: Professional Information ──
    college_name = models.CharField(max_length=300, blank=True)
    department = models.CharField(max_length=200, blank=True)
    designation = models.CharField(max_length=200, blank=True)
    employee_id = models.CharField(max_length=100, blank=True)
    years_of_experience = models.CharField(
        max_length=20,
        choices=[
            ('0-2', '0-2 years'),
            ('2-5', '2-5 years'),
            ('5-10', '5-10 years'),
            ('10-20', '10-20 years'),
            ('20+', '20+ years'),
        ],
        blank=True
    )
    teaching_mode = models.CharField(
        max_length=20,
        choices=[
            ('full_time', 'Full Time'),
            ('part_time', 'Part Time'),
            ('visiting', 'Visiting Faculty'),
            ('guest', 'Guest Lecturer'),
        ],
        blank=True
    )

    # ── Section 3: Academic & Teaching Details ──
    subjects_taught = models.JSONField(default=list, blank=True)
    specialization = models.CharField(max_length=300, blank=True)
    highest_qualification = models.CharField(max_length=200, blank=True)
    qualification_university = models.CharField(max_length=300, blank=True)
    research_publications_count = models.IntegerField(default=0)

    # ── Section 4: Skills & Expertise ──
    technical_skills = models.JSONField(default=list, blank=True)
    soft_skills = models.JSONField(default=list, blank=True)
    tools_technologies = models.JSONField(default=list, blank=True)
    languages_known = models.JSONField(default=list, blank=True)

    # ── Section 5: Session Hosting Details ──
    available_for_sessions = models.BooleanField(default=True)
    session_types_offered = models.JSONField(default=list, blank=True)
    preferred_session_mode = models.CharField(
        max_length=10,
        choices=[('online', 'Online'), ('offline', 'Offline'), ('both', 'Both')],
        default='online'
    )
    office_hours = models.CharField(max_length=200, blank=True)
    max_students_per_session = models.IntegerField(default=10)
    preferred_session_duration = models.CharField(
        max_length=10,
        choices=[
            ('30', '30 minutes'),
            ('45', '45 minutes'),
            ('60', '60 minutes'),
            ('90', '90 minutes'),
        ],
        default='60'
    )

    # ── Section 6: Social & Online Presence ──
    linkedin_url = models.URLField(blank=True)
    google_scholar_url = models.URLField(blank=True)
    researchgate_url = models.URLField(blank=True)
    personal_website = models.URLField(blank=True)
    college_staff_page_url = models.URLField(blank=True)

    # ── Section 7: Bio ──
    bio = models.TextField(blank=True, max_length=500)

    # ── Section 8: Bank Details ──
    bank_details = models.JSONField(default=dict, blank=True)
    bank_verified = models.BooleanField(default=False)

    # ── Auto-calculated fields ──
    wallet_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_earned = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    total_ratings = models.IntegerField(default=0)

    # ── Profile completeness ──
    profile_completeness_score = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def calculate_completeness(self):
        score = 0
        user = self.user

        # Basic info (20 points)
        if user.first_name and user.last_name:
            score += 8
        if user.profile_pic:
            score += 7
        if hasattr(user, 'phone') and user.phone:
            score += 5

        # Professional info (25 points)
        if self.college_name:
            score += 8
        if self.department:
            score += 8
        if self.designation:
            score += 9

        # Subjects taught + skills (20 points)
        if len(self.subjects_taught or []) >= 3:
            score += 10
        elif len(self.subjects_taught or []) >= 1:
            score += 5
        if len(self.technical_skills or []) >= 3:
            score += 10
        elif len(self.technical_skills or []) >= 1:
            score += 5

        # Bio (10 points)
        if self.bio and len(self.bio) >= 50:
            score += 10
        elif self.bio:
            score += 5

        # Session availability (10 points)
        if self.available_for_sessions and len(self.session_types_offered or []) >= 1:
            score += 10

        # Social links (5 points)
        if self.linkedin_url or self.google_scholar_url or self.personal_website:
            score += 5

        # Bank details (10 points)
        if self.bank_details and self.bank_details.get('account_number'):
            score += 10

        return min(100, score)

    def save(self, *args, **kwargs):
        self.profile_completeness_score = self.calculate_completeness()
        super().save(*args, **kwargs)

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
