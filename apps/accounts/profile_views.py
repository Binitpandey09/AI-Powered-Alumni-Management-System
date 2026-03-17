"""
Day 4-5: Profile management + CV auto-import views.
"""
import os
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import AlumniProfile, StudentProfile, FacultyProfile
from .serializers import (
    AlumniProfileSerializer,
    StudentProfileSerializer,
    FacultyProfileSerializer,
    CVUploadSerializer,
    ProfilePictureSerializer,
)
from utils.cv_parser import extract_cv_text
from utils.ai_cv_parser import parse_cv_with_ai
from utils.permissions import IsAlumni, IsStudent, IsFaculty


# ── Profile Retrieve / Update ─────────────────────────────────────────────────

class AlumniProfileView(APIView):
    """GET / PATCH /api/accounts/profile/alumni/"""
    permission_classes = [IsAuthenticated, IsAlumni]

    def get(self, request):
        profile = self._get_or_404(request.user)
        return Response(AlumniProfileSerializer(profile).data)

    def patch(self, request):
        profile = self._get_or_404(request.user)
        serializer = AlumniProfileSerializer(profile, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data)

    def _get_or_404(self, user):
        try:
            return user.alumni_profile
        except AlumniProfile.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("Alumni profile not found.")


class StudentProfileView(APIView):
    """GET / PATCH /api/accounts/profile/student/"""
    permission_classes = [IsAuthenticated, IsStudent]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        profile = self._get_or_404(request.user)
        return Response(StudentProfileSerializer(profile).data)

    def patch(self, request):
        profile = self._get_or_404(request.user)
        serializer = StudentProfileSerializer(profile, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data)

    def _get_or_404(self, user):
        try:
            return user.student_profile
        except StudentProfile.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("Student profile not found.")


class FacultyProfileView(APIView):
    """GET / PATCH /api/accounts/profile/faculty/"""
    permission_classes = [IsAuthenticated, IsFaculty]

    def get(self, request):
        profile = self._get_or_404(request.user)
        return Response(FacultyProfileSerializer(profile).data)

    def patch(self, request):
        profile = self._get_or_404(request.user)
        serializer = FacultyProfileSerializer(profile, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data)

    def _get_or_404(self, user):
        try:
            return user.faculty_profile
        except FacultyProfile.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("Faculty profile not found.")


# ── Profile Picture Upload ────────────────────────────────────────────────────

class ProfilePictureUploadView(APIView):
    """POST /api/accounts/profile/picture/"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = ProfilePictureSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        # Delete old picture file if it exists
        if user.profile_pic:
            try:
                old_path = user.profile_pic.path
                if os.path.isfile(old_path):
                    os.remove(old_path)
            except Exception:
                pass

        user.profile_pic = serializer.validated_data['profile_pic']
        user.save(update_fields=['profile_pic'])

        return Response(
            {'message': 'Profile picture updated.', 'profile_pic': user.profile_pic.url},
            status=status.HTTP_200_OK,
        )


# ── CV Upload + AI Parse ──────────────────────────────────────────────────────

class CVUploadView(APIView):
    """
    POST /api/accounts/profile/cv-upload/
    Upload a CV (PDF/DOCX), extract text, parse with AI,
    and pre-fill the user's profile fields.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = CVUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        cv_file = serializer.validated_data['cv_file']
        filename = cv_file.name

        # 1. Extract raw text
        cv_text = extract_cv_text(cv_file, filename)
        if not cv_text:
            return Response(
                {'message': 'Could not extract text from the uploaded file.'},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        # 2. Parse with AI
        parsed = parse_cv_with_ai(cv_text)

        # 3. Apply parsed data to the correct profile
        user = request.user
        applied = self._apply_to_profile(user, parsed, cv_file if user.is_student else None)

        return Response(
            {
                'message': 'CV parsed and profile pre-filled.',
                'parsed_fields': parsed,
                'applied_fields': applied,
            },
            status=status.HTTP_200_OK,
        )

    def _apply_to_profile(self, user, parsed: dict, cv_file=None) -> list:
        """Apply AI-parsed fields to the role-specific profile. Returns list of applied field names."""
        applied = []

        # Update base user fields
        user_fields_map = {
            'phone': 'phone',
            'college': 'college',
        }
        user_dirty = False
        for parsed_key, user_attr in user_fields_map.items():
            val = parsed.get(parsed_key)
            if val and not getattr(user, user_attr):
                setattr(user, user_attr, val)
                applied.append(user_attr)
                user_dirty = True
        if user_dirty:
            user.save(update_fields=list(user_fields_map.values()))

        if user.is_alumni:
            try:
                profile = user.alumni_profile
            except AlumniProfile.DoesNotExist:
                return applied

            mapping = {
                'company': 'company',
                'designation': 'designation',
                'linkedin_url': 'linkedin_url',
                'years_of_experience': 'years_of_experience',
                'skills': 'skills',
                'bio': 'bio',
            }
            dirty = False
            for parsed_key, field in mapping.items():
                val = parsed.get(parsed_key)
                if val and not getattr(profile, field):
                    setattr(profile, field, val)
                    applied.append(field)
                    dirty = True
            if dirty:
                profile.save()

        elif user.is_student:
            try:
                profile = user.student_profile
            except StudentProfile.DoesNotExist:
                return applied

            mapping = {
                'degree': 'degree',
                'branch': 'branch',
                'graduation_year': 'graduation_year',
                'skills': 'skills',
                'github_url': 'github_url',
                'linkedin_url': 'portfolio_url',
                'portfolio_url': 'portfolio_url',
            }
            dirty = False
            for parsed_key, field in mapping.items():
                val = parsed.get(parsed_key)
                if val and not getattr(profile, field):
                    setattr(profile, field, val)
                    applied.append(field)
                    dirty = True

            # Save the actual CV file on the student profile
            if cv_file:
                profile.resume_file = cv_file
                applied.append('resume_file')
                dirty = True

            if dirty:
                profile.save()

        elif user.is_faculty:
            try:
                profile = user.faculty_profile
            except FacultyProfile.DoesNotExist:
                return applied

            mapping = {
                'designation': 'designation',
                'bio': 'bio',
            }
            dirty = False
            for parsed_key, field in mapping.items():
                val = parsed.get(parsed_key)
                if val and not getattr(profile, field):
                    setattr(profile, field, val)
                    applied.append(field)
                    dirty = True
            if dirty:
                profile.save()

        return applied


# ── Basic User Fields Update ──────────────────────────────────────────────────

class BasicProfileUpdateView(APIView):
    """PATCH /api/accounts/profile/basic/ — update first_name, last_name, phone, college, batch_year"""
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        user = request.user
        allowed = ['first_name', 'last_name', 'phone', 'college', 'batch_year']
        dirty = False
        for field in allowed:
            if field in request.data:
                val = request.data[field]
                if field == 'batch_year':
                    try:
                        val = int(val) if val not in (None, '') else None
                    except (ValueError, TypeError):
                        from rest_framework.exceptions import ValidationError
                        raise ValidationError({'batch_year': 'Must be a valid year.'})
                setattr(user, field, val)
                dirty = True
        if dirty:
            user.save()

        from .serializers import UserProfileSerializer
        return Response(UserProfileSerializer(user).data)


# ── Alumni Browse / Public Profile API ───────────────────────────────────────

class AlumniBrowseView(APIView):
    """GET /api/accounts/alumni/ — paginated alumni list with search + filters"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.contrib.auth import get_user_model
        User = get_user_model()

        qs = AlumniProfile.objects.select_related('user').filter(
            user__is_verified=True, user__is_active=True
        )

        search = request.query_params.get('search', '').strip()
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(company__icontains=search) |
                Q(designation__icontains=search)
            )

        available = request.query_params.get('available', '')
        if available == 'true':
            qs = qs.filter(is_available_for_1on1=True)

        company = request.query_params.get('company', '').strip()
        if company:
            qs = qs.filter(company__icontains=company)

        skill = request.query_params.get('skill', '').strip()
        if skill:
            qs = qs.filter(skills__icontains=skill)

        # Simple pagination
        page = max(int(request.query_params.get('page', 1)), 1)
        page_size = 12
        total = qs.count()
        start = (page - 1) * page_size
        profiles = qs[start:start + page_size]

        results = []
        for p in profiles:
            u = p.user
            pic_url = u.profile_pic.url if u.profile_pic else None
            results.append({
                'user_id': u.id,
                'full_name': u.full_name,
                'first_name': u.first_name,
                'profile_pic': pic_url,
                'college': u.college,
                'batch_year': u.batch_year,
                'company': p.company,
                'designation': p.designation,
                'skills': p.skills,
                'impact_score': p.impact_score,
                'is_available_for_1on1': p.is_available_for_1on1,
                'price_per_30min': str(p.price_per_30min),
                'price_per_60min': str(p.price_per_60min),
            })

        return Response({
            'results': results,
            'total': total,
            'page': page,
            'has_next': (start + page_size) < total,
        })


class PublicAlumniProfileView(APIView):
    """GET /api/accounts/alumni/{user_id}/ — public alumni profile"""
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(id=user_id, role='alumni', is_verified=True, is_active=True)
            profile = user.alumni_profile
        except (User.DoesNotExist, AlumniProfile.DoesNotExist):
            return Response({'detail': 'Alumni not found.'}, status=status.HTTP_404_NOT_FOUND)

        pic_url = user.profile_pic.url if user.profile_pic else None
        return Response({
            'user_id': user.id,
            'full_name': user.full_name,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'profile_pic': pic_url,
            'college': user.college,
            'batch_year': user.batch_year,
            'company': profile.company,
            'designation': profile.designation,
            'company_email': profile.company_email,
            'linkedin_url': profile.linkedin_url,
            'years_of_experience': profile.years_of_experience,
            'skills': profile.skills,
            'impact_score': profile.impact_score,
            'is_available_for_1on1': profile.is_available_for_1on1,
            'price_per_30min': str(profile.price_per_30min),
            'price_per_60min': str(profile.price_per_60min),
            'bio': profile.bio,
        })


# ── Profile Completeness ──────────────────────────────────────────────────────

class ProfileCompletenessView(APIView):
    """GET /api/accounts/profile/completeness/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        fields_filled = []
        fields_missing = []

        if user.is_alumni:
            try:
                p = user.alumni_profile
            except AlumniProfile.DoesNotExist:
                return Response({'percentage': 0, 'is_complete': False, 'missing_fields': ['profile']})
            checks = {
                'company': p.company,
                'designation': p.designation,
                'bio': p.bio,
                'linkedin_url': p.linkedin_url,
                'skills': p.skills,
                'company_email': p.company_email,
            }
        elif user.is_student:
            try:
                p = user.student_profile
            except StudentProfile.DoesNotExist:
                return Response({'percentage': 0, 'is_complete': False, 'missing_fields': ['profile']})
            checks = {
                'degree': p.degree,
                'branch': p.branch,
                'graduation_year': p.graduation_year,
                'skills': p.skills,
                'resume_file': p.resume_file,
            }
        elif user.is_faculty:
            try:
                p = user.faculty_profile
            except FacultyProfile.DoesNotExist:
                return Response({'percentage': 0, 'is_complete': False, 'missing_fields': ['profile']})
            checks = {
                'department': p.department,
                'designation': p.designation,
                'bio': p.bio,
                'subjects': p.subjects,
            }
        else:
            return Response({'percentage': 0, 'is_complete': False, 'missing_fields': []})

        # Also check base user fields
        base_checks = {
            'first_name': user.first_name,
            'phone': user.phone,
            'college': user.college,
        }
        checks.update(base_checks)

        for field, val in checks.items():
            if val:
                fields_filled.append(field)
            else:
                fields_missing.append(field)

        total = len(checks)
        pct = int((len(fields_filled) / total) * 100) if total else 0
        is_complete = len(fields_missing) == 0

        return Response({
            'percentage': pct,
            'is_complete': is_complete,
            'missing_fields': fields_missing,
            'filled_fields': fields_filled,
        })
