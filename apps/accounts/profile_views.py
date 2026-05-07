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
from utils.affinda_parser import parse_cv_with_affinda
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
    and pre-fill the user's profile fields using apply_cv_data_to_profile.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = CVUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        cv_file = serializer.validated_data['cv_file']

        # ── Parse with Affinda ────────────────────────────────────────────────
        from django.conf import settings
        from utils.ai_cv_parser import apply_cv_data_to_profile

        cv_data = {}
        parse_error = None

        try:
            if not getattr(settings, 'AFFINDA_API_KEY', ''):
                parse_error = "Affinda API Key is not configured."
            else:
                cv_file.seek(0)
                cv_data = parse_cv_with_affinda(cv_file, cv_file.name)
                if not cv_data:
                    parse_error = "Affinda parsing failed or returned no data."
        except Exception as exc:
            parse_error = str(exc)

        # ── Save resume file regardless of parse outcome ───────────────────────
        if hasattr(user, 'student_profile'):
            try:
                cv_file.seek(0)
                profile = user.student_profile
                profile.resume_file = cv_file
                profile.save(update_fields=['resume_file'])
            except Exception:
                pass

        if parse_error:
            return Response(
                {'message': parse_error, 'applied_fields': [], 'resume_saved': True},
                status=status.HTTP_200_OK,
            )

        if not cv_data:
            return Response(
                {'message': 'Resume saved. Parsing returned no data — fill details manually.',
                 'applied_fields': [], 'resume_saved': True},
                status=status.HTTP_200_OK,
            )

        # ── Apply parsed data to profile ───────────────────────────────────────
        result = apply_cv_data_to_profile(user, cv_data)
        return Response(
            {
                'message': 'CV parsed and profile pre-filled.',
                'applied_fields': result.get('updated_sections', []),
                'profile_completeness': result.get('profile_completeness', 0),
                'is_complete': result.get('is_complete', False),
            },
            status=status.HTTP_200_OK,
        )


# ── Basic User Fields Update ──────────────────────────────────────────────────

class BasicProfileUpdateView(APIView):
    """PATCH /api/accounts/profile/basic/ — update user fields + student profile fields"""
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        user = request.user
        user_fields = ['first_name', 'last_name', 'phone', 'college', 'batch_year']
        user_dirty = False
        for field in user_fields:
            if field in request.data:
                val = request.data[field]
                if field == 'batch_year':
                    try:
                        val = int(val) if val not in (None, '') else None
                    except (ValueError, TypeError):
                        from rest_framework.exceptions import ValidationError
                        raise ValidationError({'batch_year': 'Must be a valid year.'})
                setattr(user, field, val)
                user_dirty = True
        if user_dirty:
            user.save()

        # Student-profile fields that live on StudentProfile, not User
        student_profile_fields = ['gender', 'date_of_birth', 'current_location']
        profile_dirty = False
        if user.is_student:
            try:
                profile = user.student_profile
            except Exception:
                profile = None
            if profile:
                for field in student_profile_fields:
                    if field in request.data:
                        val = request.data[field]
                        if field == 'date_of_birth' and val == '':
                            val = None
                        setattr(profile, field, val)
                        profile_dirty = True
                if profile_dirty:
                    profile.save()

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
                'skills': p.technical_skills,
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
            'skills': profile.technical_skills,
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
                'skills': p.technical_skills,
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
