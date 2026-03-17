from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from .models import (
    AlumniProfile, StudentProfile, FacultyProfile, EmailOTP,
    StudentEducation, StudentProject, StudentInternship,
    StudentCertification, StudentAward, StudentCompetitiveExam,
    StudentLanguage, StudentEmployment,
)

User = get_user_model()


# ─── Inline profile admins ────────────────────────────────────────────────────

class AlumniProfileInline(admin.StackedInline):
    model = AlumniProfile
    can_delete = False
    verbose_name_plural = 'Alumni Profile'
    fk_name = 'user'
    extra = 0
    fields = (
        'company', 'designation', 'company_email', 'linkedin_url',
        'years_of_experience', 'skills', 'wallet_balance', 'total_earned',
        'bank_verified', 'impact_score', 'is_available_for_1on1',
        'price_per_30min', 'price_per_60min', 'bio', 'verification_document',
    )


class StudentProfileInline(admin.StackedInline):
    model = StudentProfile
    can_delete = False
    verbose_name_plural = 'Student Profile'
    fk_name = 'user'
    extra = 0
    fields = (
        'college_email', 'enrollment_number', 'degree', 'branch',
        'graduation_year', 'skills', 'resume_file', 'resume_score',
        'github_url', 'portfolio_url', 'looking_for',
        'demo_session_used', 'resume_check_count',
        'profile_summary', 'gender', 'date_of_birth', 'current_location',
        'preferred_locations', 'availability', 'profile_completeness_score',
    )


class FacultyProfileInline(admin.StackedInline):
    model = FacultyProfile
    can_delete = False
    verbose_name_plural = 'Faculty Profile'
    fk_name = 'user'
    extra = 0
    fields = (
        'college_email', 'employee_id', 'department', 'designation',
        'subjects', 'wallet_balance', 'total_earned', 'bank_verified', 'bio',
    )


# ─── User admin ───────────────────────────────────────────────────────────────

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        'email', 'role', 'is_verified', 'is_profile_complete',
        'is_active', 'date_joined',
    ]
    list_filter  = ['role', 'is_verified', 'is_profile_complete', 'is_active', 'is_staff']
    search_fields = ['email', 'first_name', 'last_name', 'username']
    ordering = ['-date_joined']

    fieldsets = BaseUserAdmin.fieldsets + (
        ('AlumniAI Fields', {
            'fields': (
                'role', 'phone', 'profile_pic', 'college', 'batch_year',
                'is_verified', 'is_profile_complete',
            )
        }),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('AlumniAI Fields', {
            'fields': ('email', 'role', 'phone'),
        }),
    )

    def get_inlines(self, request, obj=None):
        """Show only the relevant profile inline based on role."""
        if obj is None:
            return []
        if obj.role == User.ALUMNI:
            return [AlumniProfileInline]
        if obj.role == User.STUDENT:
            return [StudentProfileInline]
        if obj.role == User.FACULTY:
            return [FacultyProfileInline]
        return []


# ─── Standalone profile admins ────────────────────────────────────────────────

@admin.register(AlumniProfile)
class AlumniProfileAdmin(admin.ModelAdmin):
    list_display  = ['user', 'company', 'designation', 'bank_verified', 'wallet_balance']
    search_fields = ['user__email', 'company', 'designation']
    list_filter   = ['bank_verified', 'is_available_for_1on1']


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display  = ['user', 'degree', 'branch', 'graduation_year', 'resume_score', 'profile_completeness_score']
    search_fields = ['user__email', 'enrollment_number', 'degree', 'branch']
    list_filter   = ['demo_session_used', 'gender']


@admin.register(FacultyProfile)
class FacultyProfileAdmin(admin.ModelAdmin):
    list_display  = ['user', 'department', 'designation', 'bank_verified', 'wallet_balance']
    search_fields = ['user__email', 'department', 'designation', 'employee_id']
    list_filter   = ['bank_verified']


# ─── OTP admin ────────────────────────────────────────────────────────────────

@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display  = ['email', 'purpose', 'is_used', 'created_at', 'expires_at']
    list_filter   = ['purpose', 'is_used']
    search_fields = ['email']
    readonly_fields = ['otp_code', 'created_at', 'expires_at']
    ordering = ['-created_at']


# ── Student Section Admins ────────────────────────────────────────────────────

@admin.register(StudentEducation)
class StudentEducationAdmin(admin.ModelAdmin):
    list_display  = ['user', 'education_type', 'degree', 'institute_name', 'end_year']
    list_filter   = ['education_type', 'is_pursuing']
    search_fields = ['user__email', 'institute_name', 'degree']


@admin.register(StudentProject)
class StudentProjectAdmin(admin.ModelAdmin):
    list_display  = ['user', 'title', 'is_ongoing', 'created_at']
    list_filter   = ['is_ongoing']
    search_fields = ['user__email', 'title']


@admin.register(StudentInternship)
class StudentInternshipAdmin(admin.ModelAdmin):
    list_display  = ['user', 'company_name', 'role', 'is_ongoing', 'created_at']
    list_filter   = ['is_ongoing']
    search_fields = ['user__email', 'company_name', 'role']


@admin.register(StudentCertification)
class StudentCertificationAdmin(admin.ModelAdmin):
    list_display  = ['user', 'title', 'issuing_organization', 'issue_date']
    search_fields = ['user__email', 'title', 'issuing_organization']


@admin.register(StudentAward)
class StudentAwardAdmin(admin.ModelAdmin):
    list_display  = ['user', 'title', 'issuer', 'date_received']
    search_fields = ['user__email', 'title', 'issuer']


@admin.register(StudentCompetitiveExam)
class StudentCompetitiveExamAdmin(admin.ModelAdmin):
    list_display  = ['user', 'exam_name', 'year', 'score_or_rank']
    search_fields = ['user__email', 'exam_name']


@admin.register(StudentLanguage)
class StudentLanguageAdmin(admin.ModelAdmin):
    list_display  = ['user', 'language', 'proficiency']
    list_filter   = ['proficiency']
    search_fields = ['user__email', 'language']


@admin.register(StudentEmployment)
class StudentEmploymentAdmin(admin.ModelAdmin):
    list_display  = ['user', 'company_name', 'job_title', 'is_current']
    list_filter   = ['is_current']
    search_fields = ['user__email', 'company_name', 'job_title']
