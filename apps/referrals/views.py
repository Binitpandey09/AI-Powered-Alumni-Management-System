from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q

from .models import Referral, ReferralApplication, ReferralSuccessStory, FacultyReferralRecommendation
from .serializers import (
    ReferralListSerializer,
    ReferralDetailSerializer,
    ReferralCreateSerializer,
    ReferralApplicationSerializer,
    ReferralApplicationCreateSerializer,
    FacultyRecommendationSerializer,
    ReferralSuccessStorySerializer,
)
from utils.permissions import CanPostReferral, IsReferralAuthorOrAdmin, IsApplicationOwnerOrReferralAuthor
from utils.skill_matcher import calculate_skill_match
from utils.ai_skill_matcher import ai_calculate_skill_match


class ReferralPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


class ReferralListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Auto-expire referrals past deadline
        Referral.objects.filter(
            status='active',
            deadline__lt=timezone.now(),
        ).update(status='expired')

        qs = Referral.objects.filter(
            status__in=['active', 'closed'],
        ).select_related(
            'posted_by',
            'posted_by__alumni_profile',
            'posted_by__faculty_profile',
        )

        # ── Filters ──
        work_type = request.query_params.get('work_type')
        if work_type:
            qs = qs.filter(work_type=work_type)

        experience = request.query_params.get('experience')
        if experience:
            qs = qs.filter(experience_level=experience)

        company = request.query_params.get('company')
        if company:
            qs = qs.filter(company_name__icontains=company)

        location = request.query_params.get('location')
        if location:
            qs = qs.filter(Q(location__icontains=location) | Q(is_remote=True))

        if request.query_params.get('remote') == 'true':
            qs = qs.filter(is_remote=True)

        skill = request.query_params.get('skill')
        if skill:
            # In-memory filter for JSONField skill matching
            qs_list = [
                r for r in qs
                if any(
                    skill.lower() in s.lower() or s.lower() in skill.lower()
                    for s in r.required_skills
                )
            ]
            ids = [r.id for r in qs_list]
            qs = Referral.objects.filter(id__in=ids).select_related(
                'posted_by', 'posted_by__alumni_profile', 'posted_by__faculty_profile'
            )

        search = request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(job_title__icontains=search)
                | Q(company_name__icontains=search)
                | Q(job_description__icontains=search)
            )

        if request.query_params.get('posted_by'):
            qs = qs.filter(posted_by__id=request.query_params.get('posted_by'))

        if request.query_params.get('my_referrals') == 'true':
            qs = qs.filter(posted_by=request.user)

        # ── Smart match for students ──
        if request.query_params.get('smart_match') == 'true' and request.user.role == 'student':
            try:
                student_skills = request.user.student_profile.skills or []
                qs_list = list(qs)
                qs_list.sort(
                    key=lambda r: -calculate_skill_match(
                        student_skills, r.required_skills, r.preferred_skills
                    )['score']
                )
                ids = [r.id for r in qs_list]
                from django.db.models import Case, When, IntegerField
                preserved = Case(
                    *[When(id=pk, then=pos) for pos, pk in enumerate(ids)],
                    output_field=IntegerField(),
                )
                qs = Referral.objects.filter(id__in=ids).select_related(
                    'posted_by', 'posted_by__alumni_profile', 'posted_by__faculty_profile'
                ).order_by(preserved)
            except Exception:
                pass

        paginator = ReferralPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = ReferralListSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        if request.user.role not in ('alumni', 'faculty'):
            return Response({'error': 'Only alumni and faculty can post referrals.'}, status=403)
        serializer = ReferralCreateSerializer(data=request.data)
        if serializer.is_valid():
            referral = serializer.save(posted_by=request.user)
            return Response(
                ReferralDetailSerializer(referral, context={'request': request}).data,
                status=201,
            )
        return Response(serializer.errors, status=400)


class ReferralDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        referral = get_object_or_404(Referral, pk=pk)
        return Response(ReferralDetailSerializer(referral, context={'request': request}).data)

    def patch(self, request, pk):
        referral = get_object_or_404(Referral, pk=pk)
        if referral.posted_by != request.user and request.user.role != 'admin':
            return Response({'error': 'Permission denied.'}, status=403)
        serializer = ReferralCreateSerializer(referral, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(ReferralDetailSerializer(referral, context={'request': request}).data)
        return Response(serializer.errors, status=400)

    def delete(self, request, pk):
        referral = get_object_or_404(Referral, pk=pk)
        if referral.posted_by != request.user and request.user.role != 'admin':
            return Response({'error': 'Permission denied.'}, status=403)
        referral.status = 'paused'
        referral.save(update_fields=['status'])
        return Response({'message': 'Referral paused successfully.'})


class ReferralApplyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if request.user.role != 'student':
            return Response({'error': 'Only students can apply to referrals.'}, status=403)

        referral = get_object_or_404(Referral, pk=pk)

        if not referral.is_accepting_applications:
            if referral.is_expired:
                return Response({'error': 'This referral has expired.'}, status=400)
            if referral.is_full:
                return Response({'error': 'All slots are filled for this referral.'}, status=400)
            return Response({'error': 'This referral is no longer accepting applications.'}, status=400)

        if ReferralApplication.objects.filter(
            referral=referral, student=request.user
        ).exclude(status='withdrawn').exists():
            return Response({'error': 'You have already applied to this referral.'}, status=400)

        match_result = ai_calculate_skill_match(request.user, referral)

        if not match_result['can_apply']:
            return Response({
                'error': 'Your profile does not meet the minimum skill requirements for this referral.',
                'match_score': match_result['score'],
                'missing_skills': match_result['missing_skills'],
                'matched_skills': match_result['matched_skills'],
                'reason': match_result['reason'],
                'can_apply': False,
            }, status=400)

        cover_note = request.data.get('cover_note', '').strip()[:500]

        # Graduation year eligibility check
        if referral.eligible_graduation_years:
            try:
                student_grad_year = request.user.student_profile.graduation_year
                if student_grad_year and student_grad_year not in referral.eligible_graduation_years:
                    return Response({
                        'error': (
                            f'This referral is only for graduation years: '
                            f'{", ".join(map(str, referral.eligible_graduation_years))}'
                        ),
                    }, status=400)
            except Exception:
                pass

        # CGPA check
        if referral.minimum_cgpa:
            try:
                from apps.accounts.models import StudentEducation
                grad_edu = StudentEducation.objects.filter(
                    user=request.user,
                    education_type='graduation',
                    grade_type='cgpa',
                ).first()
                if grad_edu and grad_edu.grade_value:
                    student_cgpa = float(grad_edu.grade_value)
                    if student_cgpa < float(referral.minimum_cgpa):
                        return Response({
                            'error': (
                                f'Minimum CGPA required: {referral.minimum_cgpa}. '
                                f'Your CGPA: {student_cgpa}'
                            ),
                        }, status=400)
            except Exception:
                pass

        # Check for existing faculty recommendation
        from apps.referrals.models import FacultyReferralRecommendation
        rec = FacultyReferralRecommendation.objects.filter(
            referral=referral, student=request.user
        ).first()

        application = ReferralApplication.objects.create(
            referral=referral,
            student=request.user,
            match_score=match_result['score'],
            matched_skills=match_result['matched_skills'],
            missing_skills=match_result['missing_skills'],
            cover_note=cover_note,
            status='applied',
            is_faculty_recommended=bool(rec),
            recommended_by=rec.faculty if rec else None,
            recommendation_note=rec.note if rec else '',
        )

        return Response({
            'message': 'Application submitted successfully!',
            'application_id': application.id,
            'match_score': match_result['score'],
            'matched_skills': match_result['matched_skills'],
            'can_apply': True,
        }, status=201)


class SkillMatchCheckView(APIView):
    """Students call this BEFORE applying to check their match score — no application created."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        referral = get_object_or_404(Referral, pk=pk)
        result = ai_calculate_skill_match(request.user, referral)
        try:
            student_skills = request.user.student_profile.skills or []
        except Exception:
            student_skills = []
        return Response({
            'referral_id': pk,
            'job_title': referral.job_title,
            'company': referral.company_name,
            'required_skills': referral.required_skills,
            'student_skills': student_skills,
            **result,
        })


class AllMyApplicantsView(APIView):
    """GET /api/referrals/applicants/ — all applications across all of current user's referrals."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role not in ('alumni', 'faculty', 'admin'):
            return Response({'error': 'Only alumni/faculty can view applicants.'}, status=403)

        referrals = Referral.objects.filter(posted_by=request.user).order_by('-created_at')

        qs = ReferralApplication.objects.filter(
            referral__in=referrals
        ).exclude(status='withdrawn').select_related(
            'referral', 'student', 'recommended_by'
        ).order_by('-applied_at')

        # Optional filters
        ref_id = request.query_params.get('referral_id')
        if ref_id:
            qs = qs.filter(referral_id=ref_id)

        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        applications = []
        for app in qs:
            student = app.student
            pic = student.profile_pic.url if student.profile_pic else None
            try:
                sp = student.student_profile
                degree = f"{sp.degree} – {sp.branch}" if sp.degree else ''
            except Exception:
                degree = ''

            applications.append({
                'application_id': app.id,
                'referral_id': app.referral.id,
                'referral_title': app.referral.job_title,
                'company_name': app.referral.company_name,
                'student_id': student.id,
                'student_name': student.full_name,
                'student_email': student.email,
                'student_pic': pic,
                'student_degree': degree,
                'match_score': app.match_score,
                'matched_skills': app.matched_skills or [],
                'missing_skills': app.missing_skills or [],
                'status': app.status,
                'cover_note': app.cover_note,
                'applied_at': app.applied_at.isoformat(),
                'is_faculty_recommended': app.is_faculty_recommended,
                'alumni_note': app.alumni_note if hasattr(app, 'alumni_note') else '',
            })

        # Stats
        all_apps = ReferralApplication.objects.filter(referral__in=referrals).exclude(status='withdrawn')
        stats = {
            'total':       all_apps.count(),
            'shortlisted': all_apps.filter(status='shortlisted').count(),
            'hired':       all_apps.filter(status='hired').count(),
            'rejected':    all_apps.filter(status='rejected').count(),
        }

        referral_list = [
            {'id': r.id, 'job_title': r.job_title, 'company_name': r.company_name, 'status': r.status}
            for r in referrals
        ]

        return Response({
            'applications': applications,
            'stats': stats,
            'referrals': referral_list,
        })


class ReferralApplicationListView(APIView):
    """Alumni views all applications for their referral."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        referral = get_object_or_404(Referral, pk=pk)
        if referral.posted_by != request.user and request.user.role != 'admin':
            return Response({'error': 'Permission denied.'}, status=403)

        applications = ReferralApplication.objects.filter(
            referral=referral,
        ).select_related('student', 'student__student_profile', 'recommended_by')

        serializer = ReferralApplicationSerializer(applications, many=True)
        return Response({
            'referral': ReferralDetailSerializer(referral, context={'request': request}).data,
            'applications': serializer.data,
            'total': applications.count(),
            'by_status': {
                status: applications.filter(status=status).count()
                for status, _ in ReferralApplication.APPLICATION_STATUS
            },
        })


class ReferralApplicationUpdateView(APIView):
    """Alumni updates application status (shortlist, reject, hire, etc.)."""
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        application = get_object_or_404(ReferralApplication, pk=pk)
        referral = application.referral

        if referral.posted_by != request.user and request.user.role != 'admin':
            return Response(
                {'error': 'Only the referral author can update application status.'},
                status=403,
            )

        new_status = request.data.get('status')
        alumni_note = request.data.get('alumni_note', '').strip()
        valid_statuses = [s[0] for s in ReferralApplication.APPLICATION_STATUS]

        if new_status not in valid_statuses:
            return Response(
                {'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'},
                status=400,
            )

        application.status = new_status
        if alumni_note:
            application.alumni_note = alumni_note
        application.save()

        return Response({
            'message': f'Application status updated to {new_status}.',
            'application': ReferralApplicationSerializer(application).data,
        })


class StudentApplicationListView(APIView):
    """Student views and withdraws their own applications."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'student':
            return Response({'error': 'Only students can view their applications.'}, status=403)

        applications = ReferralApplication.objects.filter(
            student=request.user,
        ).select_related('referral', 'referral__posted_by').order_by('-applied_at')

        status_filter = request.query_params.get('status')
        if status_filter:
            applications = applications.filter(status=status_filter)

        serializer = ReferralApplicationSerializer(applications, many=True)
        return Response(serializer.data)

    def delete(self, request, application_id):
        application = get_object_or_404(
            ReferralApplication, pk=application_id, student=request.user
        )
        if application.status in ('hired', 'withdrawn'):
            return Response({'error': 'Cannot withdraw this application.'}, status=400)
        application.status = 'withdrawn'
        application.save()
        return Response({'message': 'Application withdrawn successfully.'})


class FacultyRecommendView(APIView):
    """Faculty recommends a student for a referral."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if request.user.role != 'faculty':
            return Response({'error': 'Only faculty can recommend students.'}, status=403)

        referral = get_object_or_404(Referral, pk=pk)
        student_id = request.data.get('student_id')
        note = request.data.get('note', '').strip()

        if not student_id:
            return Response({'error': 'student_id is required.'}, status=400)

        from django.contrib.auth import get_user_model
        User = get_user_model()
        student = get_object_or_404(User, pk=student_id, role='student', is_verified=True)

        rec, created = FacultyReferralRecommendation.objects.get_or_create(
            faculty=request.user,
            student=student,
            referral=referral,
            defaults={'note': note},
        )

        # Mark existing application as faculty recommended
        ReferralApplication.objects.filter(
            referral=referral, student=student,
        ).update(
            is_faculty_recommended=True,
            recommended_by=request.user,
            recommendation_note=note,
        )

        from utils.notify import send_notification
        send_notification(
            recipient=referral.posted_by,
            notif_type='general',
            title='Faculty Recommendation',
            message=f'{request.user.first_name} recommended {student.first_name} for your referral ({referral.job_title}).',
            link=f'/referrals/{referral.id}/applications/',
        )

        return Response({
            'message': f'Successfully recommended {student.first_name} for this referral.',
            'created': created,
        }, status=201 if created else 200)


class SuccessStoriesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        stories = ReferralSuccessStory.objects.filter(
            is_public=True,
        ).select_related('student', 'alumni').order_by('-created_at')[:20]
        serializer = ReferralSuccessStorySerializer(stories, many=True)
        return Response(serializer.data)
