from django.contrib import admin
from .models import Referral, ReferralApplication, ReferralSuccessStory, FacultyReferralRecommendation


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'job_title', 'company_name', 'posted_by_email', 'work_type',
        'status', 'total_applications', 'max_applicants', 'deadline',
        'is_urgent', 'is_boosted',
    ]
    list_filter = ['status', 'work_type', 'experience_level', 'is_urgent', 'is_boosted', 'is_remote']
    search_fields = ['job_title', 'company_name', 'posted_by__email']
    readonly_fields = ['total_applications', 'created_at', 'updated_at']
    actions = ['deactivate_referrals', 'activate_referrals']

    def posted_by_email(self, obj):
        return obj.posted_by.email
    posted_by_email.short_description = 'Posted By'

    def deactivate_referrals(self, request, queryset):
        queryset.update(status='deactivated')
    deactivate_referrals.short_description = 'Deactivate selected referrals'

    def activate_referrals(self, request, queryset):
        queryset.update(status='active')
    activate_referrals.short_description = 'Activate selected referrals'


@admin.register(ReferralApplication)
class ReferralApplicationAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'student_email', 'referral_title', 'company',
        'status', 'match_score', 'is_faculty_recommended', 'applied_at',
    ]
    list_filter = ['status', 'is_faculty_recommended']
    search_fields = ['student__email', 'referral__job_title', 'referral__company_name']

    def student_email(self, obj):
        return obj.student.email

    def referral_title(self, obj):
        return obj.referral.job_title

    def company(self, obj):
        return obj.referral.company_name


@admin.register(ReferralSuccessStory)
class SuccessStoryAdmin(admin.ModelAdmin):
    list_display = ['student', 'alumni', 'company_name', 'job_title', 'is_public', 'created_at']


@admin.register(FacultyReferralRecommendation)
class FacultyRecommendationAdmin(admin.ModelAdmin):
    list_display = ['faculty', 'student', 'referral', 'created_at']
