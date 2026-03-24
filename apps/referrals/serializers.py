from rest_framework import serializers
from django.utils import timezone
from .models import Referral, ReferralApplication, ReferralSuccessStory, FacultyReferralRecommendation


class ReferralAuthorSerializer(serializers.ModelSerializer):
    role_detail = serializers.SerializerMethodField()
    impact_score = serializers.SerializerMethodField()

    class Meta:
        from django.contrib.auth import get_user_model
        model = get_user_model()
        fields = ['id', 'first_name', 'last_name', 'role', 'profile_pic', 'college',
                  'role_detail', 'impact_score']

    def get_role_detail(self, obj):
        if obj.role == 'alumni':
            try:
                p = obj.alumni_profile
                return {'company': p.company, 'designation': p.designation}
            except Exception:
                return {}
        elif obj.role == 'faculty':
            try:
                p = obj.faculty_profile
                return {'department': p.department, 'designation': p.designation}
            except Exception:
                return {}
        return {}

    def get_impact_score(self, obj):
        if obj.role == 'alumni':
            try:
                return obj.alumni_profile.impact_score
            except Exception:
                return 0
        return 0


class ReferralListSerializer(serializers.ModelSerializer):
    posted_by = ReferralAuthorSerializer(read_only=True)
    is_expired = serializers.ReadOnlyField()
    is_full = serializers.ReadOnlyField()
    slots_remaining = serializers.ReadOnlyField()
    is_accepting_applications = serializers.ReadOnlyField()
    has_applied = serializers.SerializerMethodField()
    match_score = serializers.SerializerMethodField()
    time_remaining = serializers.SerializerMethodField()

    class Meta:
        model = Referral
        fields = [
            'id', 'posted_by', 'company_name', 'company_logo_url', 'job_title',
            'work_type', 'experience_level', 'location', 'is_remote', 'salary_range',
            'required_skills', 'preferred_skills', 'minimum_cgpa', 'eligible_branches',
            'eligible_graduation_years', 'max_applicants', 'total_applications',
            'slots_remaining', 'status', 'deadline', 'is_urgent', 'is_boosted',
            'is_expired', 'is_full', 'is_accepting_applications', 'tags',
            'has_applied', 'match_score', 'time_remaining', 'created_at', 'job_description',
        ]

    def get_has_applied(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return ReferralApplication.objects.filter(
            referral=obj,
            student=request.user,
        ).exclude(status='withdrawn').exists()

    def get_match_score(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        if request.user.role != 'student':
            return None
        try:
            student_skills = request.user.student_profile.skills or []
        except Exception:
            return None
        from utils.skill_matcher import calculate_skill_match
        result = calculate_skill_match(student_skills, obj.required_skills, obj.preferred_skills)
        return result['score']

    def get_time_remaining(self, obj):
        now = timezone.now()
        if now > obj.deadline:
            return 'Expired'
        diff = obj.deadline - now
        days = diff.days
        hours = diff.seconds // 3600
        if days > 1:
            return f'{days} days left'
        elif days == 1:
            return '1 day left'
        elif hours > 1:
            return f'{hours} hours left'
        else:
            return 'Closing soon'


class ReferralDetailSerializer(ReferralListSerializer):
    skill_match_detail = serializers.SerializerMethodField()

    class Meta(ReferralListSerializer.Meta):
        fields = ReferralListSerializer.Meta.fields + [
            'skill_match_detail', 'apply_link', 'admin_note',
        ]

    def get_skill_match_detail(self, obj):
        request = self.context.get('request')
        if not request or request.user.role != 'student':
            return None
        try:
            student_skills = request.user.student_profile.skills or []
        except Exception:
            return None
        from utils.skill_matcher import calculate_skill_match
        return calculate_skill_match(student_skills, obj.required_skills, obj.preferred_skills)


class ReferralCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Referral
        fields = [
            'company_name', 'company_logo_url', 'job_title', 'job_description',
            'work_type', 'experience_level', 'location', 'is_remote', 'salary_range',
            'required_skills', 'preferred_skills', 'minimum_cgpa', 'eligible_branches',
            'eligible_graduation_years', 'apply_link', 'max_applicants', 'deadline',
            'is_urgent', 'tags',
        ]

    def validate_required_skills(self, value):
        if not value or len(value) == 0:
            raise serializers.ValidationError('At least one required skill must be specified.')
        if len(value) > 15:
            raise serializers.ValidationError('Maximum 15 required skills allowed.')
        return value

    def validate_max_applicants(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError('Maximum applicants must be between 1 and 5.')
        return value

    def validate_deadline(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError('Deadline must be in the future.')
        return value

    def validate_job_description(self, value):
        if len(value.strip()) < 50:
            raise serializers.ValidationError('Job description must be at least 50 characters.')
        return value


class ReferralApplicationSerializer(serializers.ModelSerializer):
    student = serializers.SerializerMethodField()
    referral = ReferralListSerializer(read_only=True)

    class Meta:
        model = ReferralApplication
        fields = [
            'id', 'referral', 'student', 'status', 'match_score',
            'matched_skills', 'missing_skills', 'is_faculty_recommended',
            'recommended_by', 'recommendation_note', 'cover_note',
            'alumni_note', 'applied_at', 'updated_at',
        ]

    def get_student(self, obj):
        s = obj.student
        student_data = {
            'id': s.id,
            'first_name': s.first_name,
            'last_name': s.last_name,
            'email': s.email,
            'profile_pic': s.profile_pic.url if s.profile_pic else None,
            'college': s.college,
        }
        try:
            sp = s.student_profile
            student_data.update({
                'degree': sp.degree,
                'branch': sp.branch,
                'graduation_year': sp.graduation_year,
                'skills': sp.skills,
                'resume_file': sp.resume_file.url if sp.resume_file else None,
                'github_url': sp.github_url,
            })
        except Exception:
            pass
        return student_data


class ReferralApplicationCreateSerializer(serializers.Serializer):
    cover_note = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text='Optional cover note (max 500 chars)',
    )


class FacultyRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = FacultyReferralRecommendation
        fields = ['id', 'faculty', 'student', 'referral', 'note', 'created_at']
        read_only_fields = ['faculty', 'created_at']


class ReferralSuccessStorySerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    alumni_name = serializers.SerializerMethodField()

    class Meta:
        model = ReferralSuccessStory
        fields = [
            'id', 'student_name', 'alumni_name', 'company_name',
            'job_title', 'testimonial', 'is_public', 'created_at',
        ]

    def get_student_name(self, obj):
        return f"{obj.student.first_name} {obj.student.last_name}".strip()

    def get_alumni_name(self, obj):
        return f"{obj.alumni.first_name} {obj.alumni.last_name}".strip()
