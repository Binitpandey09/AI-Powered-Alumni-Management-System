"""
apps/ai_tools/views.py
AI Tools API views — Resume Scorer, Resume Builder, AI Mock Interview, Skill Gap Analyzer.
Payment gate is handled by apps/payments/views.py (AIToolPaymentInitView / AIToolPaymentVerifyView).
These views handle what happens AFTER the payment gate is passed.
"""
import json
import logging

# ── Page Views ────────────────────────────────────────────────────────────────

from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.conf import settings as django_settings
from utils.auth_helpers import get_user_from_token


class JWTLoginRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        token = request.COOKIES.get('access_token', '')
        user = get_user_from_token(token)
        if not user:
            return redirect(f'/auth/login/?next={request.path}')
        if not user.is_profile_complete and request.path not in ('/profile/setup/',):
            return redirect('/profile/setup/')
        request.user = user
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['user'] = self.request.user
        ctx['user_role'] = self.request.user.role
        return ctx


class AIToolsHubPageView(JWTLoginRequiredMixin, TemplateView):
    template_name = 'ai_tools/hub.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        from apps.payments.models import AIToolUsage
        ctx['resume_check_count'] = AIToolUsage.objects.filter(
            user=user, tool_type='resume_check'
        ).count()
        ctx['resume_builder_count'] = AIToolUsage.objects.filter(
            user=user, tool_type='resume_builder'
        ).count()
        ctx['ai_interview_count'] = AIToolUsage.objects.filter(
            user=user, tool_type='ai_interview'
        ).count()
        ctx['skill_gap_count'] = AIToolUsage.objects.filter(
            user=user, tool_type='skill_gap'
        ).count()
        ctx['resume_check_free_remaining'] = AIToolUsage.get_free_uses_remaining(
            user, 'resume_check'
        )
        return ctx


class AIToolPageMixin(JWTLoginRequiredMixin, TemplateView):
    tool_type = ''
    tool_name = ''
    tool_price = '0'
    tool_description = ''

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['tool_type'] = self.tool_type
        ctx['tool_name'] = self.tool_name
        ctx['tool_price'] = self.tool_price
        ctx['tool_description'] = self.tool_description
        ctx['razorpay_key_id'] = django_settings.RAZORPAY_KEY_ID
        
        user = getattr(self.request, 'user', None)
        if user:
            from apps.payments.models import AIToolUsage
            ctx['free_remaining'] = AIToolUsage.get_free_uses_remaining(user, self.tool_type)
            ctx['past_results'] = AIToolUsage.objects.filter(
                user=user, tool_type=self.tool_type
            ).exclude(result_data={}).order_by('-created_at')[:5]
            
        return ctx


class ResumeCheckPageView(AIToolPageMixin):
    template_name = 'ai_tools/resume_check.html'
    tool_type = 'resume_check'
    tool_name = 'Resume Score Checker'
    tool_price = '49'
    tool_description = 'Get an AI-powered score and detailed feedback on your resume. First use is FREE.'


class AIInterviewPageView(AIToolPageMixin):
    template_name = 'ai_tools/ai_interview.html'
    tool_type = 'ai_interview'
    tool_name = 'AI Mock Interview'
    tool_price = '99'
    tool_description = 'AI-powered interview based on your CV. Realistic questions. Detailed feedback.'


class ResumeBuilderPageView(AIToolPageMixin):
    template_name = 'ai_tools/resume_build.html'
    tool_type = 'resume_builder'
    tool_name = 'Resume Builder'
    tool_price = '149'
    tool_description = 'Build a professional resume with AI assistance. ATS-optimized templates.'


class SkillGapPageView(AIToolPageMixin):
    template_name = 'ai_tools/skill_gap.html'
    tool_type = 'skill_gap'
    tool_name = 'Skill Gap Analyzer'
    tool_price = '79'
    tool_description = 'Discover exactly what skills you need for your dream role.'


# ── API Views ─────────────────────────────────────────────────────────────────

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from apps.payments.models import AIToolUsage

logger = logging.getLogger(__name__)

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from apps.payments.models import AIToolUsage

logger = logging.getLogger(__name__)


# ── Profile data builder ──────────────────────────────────────────────────────

def get_student_profile_data(user):
    """Builds a unified dict of student profile data for AI services."""
    data = {
        'name':              f"{user.first_name} {user.last_name}".strip(),
        'email':             user.email,
        'phone':             getattr(user, 'phone', ''),
        'location':          '',
        'skills':            [],
        'education':         [],
        'education_summary': '',
        'projects':          [],
        'projects_summary':  '',
        'projects_count':    0,
        'internships':       [],
        'internships_count': 0,
        'certifications':    [],
        'profile_summary':   '',
        'github_url':        '',
        'experience_level':  'fresher',
    }

    # StudentProfile
    try:
        sp = user.student_profile
        data['location']        = sp.current_location or ''
        data['skills']          = sp.skills or []
        data['profile_summary'] = sp.profile_summary or ''
        data['github_url']      = sp.github_url or ''
    except Exception:
        pass

    # Education
    try:
        from apps.accounts.models import StudentEducation
        educations = StudentEducation.objects.filter(user=user).order_by('education_type')
        data['education'] = [
            {
                'degree':      e.degree,
                'institution': e.institute_name,
                'year':        str(e.end_year or ''),
                'grade':       str(e.grade_value or ''),
            }
            for e in educations
        ]
        grad = educations.filter(education_type='graduation').first()
        if grad:
            data['education_summary'] = f"{grad.degree} from {grad.institute_name}"
        elif educations.exists():
            e = educations.first()
            data['education_summary'] = f"{e.degree} from {e.institute_name}"
    except Exception:
        pass

    # Projects — model uses 'title' and 'tech_stack'
    try:
        from apps.accounts.models import StudentProject
        projects = StudentProject.objects.filter(user=user)[:5]
        data['projects'] = [
            {
                'name':        p.title,
                'description': (p.description or '')[:200],
                'tech_stack':  p.tech_stack or [],
            }
            for p in projects
        ]
        data['projects_count']   = projects.count()
        data['projects_summary'] = ', '.join(p.title for p in projects)
    except Exception:
        pass

    # Internships — model uses 'role' not 'designation'
    try:
        from apps.accounts.models import StudentInternship
        internships = StudentInternship.objects.filter(user=user)[:3]
        data['internships'] = [
            {'title': i.role, 'company': i.company_name}
            for i in internships
        ]
        data['internships_count'] = internships.count()
        if internships.count() > 0:
            data['experience_level'] = 'junior'
    except Exception:
        pass

    # Certifications — model uses 'title' not 'certificate_name'
    try:
        from apps.accounts.models import StudentCertification
        certs = StudentCertification.objects.filter(user=user)[:5]
        data['certifications'] = [
            {'name': c.title, 'issuer': c.issuing_organization}
            for c in certs
        ]
    except Exception:
        pass

    return data


# ── Access verifier ───────────────────────────────────────────────────────────

def verify_tool_access(user, tool_type, usage_id):
    """
    Verifies that a student has paid for or has a free use for this tool.
    usage_id comes from the frontend after payment/free verification.
    Returns (True, usage_object) or (False, error_message)
    """
    try:
        usage = AIToolUsage.objects.get(id=usage_id, user=user, tool_type=tool_type)
        return True, usage
    except AIToolUsage.DoesNotExist:
        return False, "Tool access not verified. Please complete payment first."


# ── GenerateSummaryView (existing — keep) ─────────────────────────────────────

class GenerateSummaryView(APIView):
    """POST /api/ai/generate-summary/ — generate a profile summary using Gemini."""
    from utils.permissions import IsStudent
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from django.conf import settings
        from rest_framework import status as drf_status

        user = request.user
        api_key = getattr(settings, 'GEMINI_API_KEY', '')
        if not api_key:
            return Response(
                {'error': 'AI service not configured. Add GEMINI_API_KEY to .env'},
                status=drf_status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        try:
            p = user.student_profile
        except Exception:
            return Response(
                {'error': 'Student profile not found.'},
                status=drf_status.HTTP_404_NOT_FOUND,
            )

        profile_data = {
            'name':            user.full_name,
            'degree':          p.degree,
            'branch':          p.branch,
            'graduation_year': p.graduation_year,
            'college':         user.college,
            'skills':          p.skills or [],
            'looking_for':     p.looking_for,
            'projects':        list(user.projects.values('title', 'description', 'tech_stack')),
            'internships':     list(user.internships.values('company_name', 'role', 'description')),
            'certifications':  list(user.certifications.values('title', 'issuing_organization')),
        }

        try:
            from utils.ai_cv_parser import generate_summary_with_ai
            summary = generate_summary_with_ai(profile_data, api_key)
            return Response({'summary': summary})
        except RuntimeError as exc:
            return Response(
                {'error': str(exc)},
                status=drf_status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as exc:
            logger.warning('AI summary generation failed: %s', exc)
            return Response(
                {'error': 'AI generation failed. Please try again.'},
                status=drf_status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# ══════════════════════════════════════════════════════════════
# VIEW 1 — Resume Scorer
# ══════════════════════════════════════════════════════════════

class ResumeScoreView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        """
        Scores the student's resume.
        Requires: usage_id (from payment verification), optional job_role.
        Resume text is extracted from StudentProfile.resume_file (PDF).
        Falls back to profile data if no PDF uploaded.
        """
        usage_id = request.data.get('usage_id')
        job_role  = request.data.get('job_role', '').strip() or None

        if not usage_id:
            return Response({'error': 'usage_id is required. Complete payment first.'}, status=400)

        has_access, result = verify_tool_access(request.user, 'resume_check', usage_id)
        if not has_access:
            return Response({'error': result}, status=403)

        usage = result

        # Return cached result if already processed
        if usage.result_data:
            return Response({'success': True, 'result': usage.result_data, 'cached': True})

        # Extract resume text from PDF
        resume_text = ''
        try:
            sp = request.user.student_profile
            if sp.resume_file:
                import PyPDF2
                import io
                sp.resume_file.seek(0)
                reader = PyPDF2.PdfReader(io.BytesIO(sp.resume_file.read()))
                for page in reader.pages:
                    resume_text += page.extract_text() or ''
        except Exception as e:
            logger.warning('PDF extraction failed for user %s: %s', request.user.id, e)

        # Fallback: build resume text from profile data
        profile_data = get_student_profile_data(request.user)
        if not resume_text.strip():
            resume_text = (
                f"Name: {profile_data['name']}\n"
                f"Skills: {', '.join(profile_data['skills'])}\n"
                f"Education: {profile_data['education_summary']}\n"
                f"Projects: {profile_data['projects_summary']}\n"
                f"Summary: {profile_data['profile_summary']}"
            )

        from utils.ai_tools_service import score_resume
        ai_result = score_resume(resume_text, profile_data, job_role)

        if not ai_result['success']:
            return Response({'error': ai_result['error']}, status=500)

        usage.result_data = ai_result['data']
        usage.save(update_fields=['result_data'])

        return Response({'success': True, 'result': ai_result['data'], 'cached': False})

    def get(self, request):
        """Returns student's past resume score results (latest 10)."""
        usages = (
            AIToolUsage.objects
            .filter(user=request.user, tool_type='resume_check')
            .exclude(result_data={})
            .order_by('-created_at')[:10]
        )
        results = [
            {
                'usage_id':     u.id,
                'overall_score': u.result_data.get('overall_score', 0),
                'grade':         u.result_data.get('grade', ''),
                'ats_score':     u.result_data.get('ats_score', 0),
                'is_free':       u.is_free_use,
                'created_at':    u.created_at.isoformat(),
                'summary':       u.result_data.get('summary', ''),
            }
            for u in usages
        ]
        return Response({'results': results})


# ══════════════════════════════════════════════════════════════
# VIEW 2 — Resume Builder
# ══════════════════════════════════════════════════════════════

class ResumeBuildView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Builds a professional resume from student profile data.
        Requires: usage_id, optional target_role and template_style.
        """
        usage_id       = request.data.get('usage_id')
        target_role    = request.data.get('target_role', '').strip() or None
        template_style = request.data.get('template_style', 'professional')

        if not usage_id:
            return Response({'error': 'usage_id is required.'}, status=400)

        has_access, result = verify_tool_access(request.user, 'resume_builder', usage_id)
        if not has_access:
            return Response({'error': result}, status=403)

        usage = result

        if usage.result_data:
            return Response({'success': True, 'result': usage.result_data, 'cached': True})

        profile_data = get_student_profile_data(request.user)

        from utils.ai_tools_service import build_resume
        ai_result = build_resume(profile_data, target_role, template_style)

        if not ai_result['success']:
            return Response({'error': ai_result['error']}, status=500)

        usage.result_data = ai_result['data']
        usage.save(update_fields=['result_data'])

        return Response({'success': True, 'result': ai_result['data'], 'cached': False})

    def get(self, request):
        """Returns past resume builds (latest 5)."""
        usages = (
            AIToolUsage.objects
            .filter(user=request.user, tool_type='resume_builder')
            .exclude(result_data={})
            .order_by('-created_at')[:5]
        )
        results = [
            {
                'usage_id':   u.id,
                'created_at': u.created_at.isoformat(),
                'has_result': bool(u.result_data),
                'target_role': u.result_data.get('tailoring_notes', '')[:80] if u.result_data else '',
            }
            for u in usages
        ]
        return Response({'results': results})


# ══════════════════════════════════════════════════════════════
# VIEW 3 — AI Mock Interview
# ══════════════════════════════════════════════════════════════

class AIInterviewView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Handles the AI interview flow.
        action='start'         — generates questions and returns them
        action='submit_answer' — evaluates one answer
        action='finish'        — generates full report
        """
        action   = request.data.get('action')
        usage_id = request.data.get('usage_id')

        if not usage_id:
            return Response({'error': 'usage_id is required.'}, status=400)

        has_access, result = verify_tool_access(request.user, 'ai_interview', usage_id)
        if not has_access:
            return Response({'error': result}, status=403)

        usage = result

        # ── START ──────────────────────────────────────────────
        if action == 'start':
            # Return cached questions if already started
            if usage.result_data.get('questions'):
                return Response({
                    'success': True,
                    'data': {
                        'questions':                  usage.result_data['questions'],
                        'job_role':                   usage.result_data.get('job_role', ''),
                        'total_questions':            len(usage.result_data['questions']),
                        'estimated_duration_minutes': len(usage.result_data['questions']) * 4,
                    },
                    'cached': True,
                })

            job_role      = request.data.get('job_role', 'Software Engineer').strip()
            num_questions = int(request.data.get('num_questions', 5))
            num_questions = max(3, min(8, num_questions))

            profile_data = get_student_profile_data(request.user)

            from utils.ai_tools_service import generate_interview_questions
            ai_result = generate_interview_questions(profile_data, job_role, num_questions)

            if not ai_result['success']:
                return Response({'error': ai_result['error']}, status=500)

            from django.utils import timezone as tz
            usage.result_data = {
                'questions':  ai_result['data']['questions'],
                'job_role':   job_role,
                'answers':    [],
                'status':     'in_progress',
                'started_at': tz.now().isoformat(),
            }
            usage.save(update_fields=['result_data'])

            return Response({'success': True, 'data': ai_result['data']})

        # ── SUBMIT ANSWER ──────────────────────────────────────
        elif action == 'submit_answer':
            question_id = request.data.get('question_id')
            answer_text = request.data.get('answer', '').strip()

            if not question_id or not answer_text:
                return Response({'error': 'question_id and answer are required.'}, status=400)

            questions   = usage.result_data.get('questions', [])
            question_obj = next(
                (q for q in questions if q['id'] == int(question_id)), None
            )
            if not question_obj:
                return Response({'error': 'Question not found.'}, status=404)

            profile_data = get_student_profile_data(request.user)

            from utils.ai_tools_service import evaluate_interview_answer
            ai_result = evaluate_interview_answer(
                question=question_obj['question'],
                answer=answer_text,
                job_role=usage.result_data.get('job_role', 'Software Engineer'),
                student_skills=profile_data.get('skills', []),
            )

            if not ai_result['success']:
                return Response({'error': ai_result['error']}, status=500)

            # Append answer + evaluation to result_data
            existing = usage.result_data
            answers  = existing.get('answers', [])
            answers.append({
                'question_id':   int(question_id),
                'question':      question_obj['question'],
                'question_type': question_obj.get('type', 'technical'),
                'answer':        answer_text,
                'score':         ai_result['data']['score'],
                'feedback':      ai_result['data'],
            })
            existing['answers'] = answers
            usage.result_data   = existing
            usage.save(update_fields=['result_data'])

            return Response({'success': True, 'evaluation': ai_result['data']})

        # ── FINISH ─────────────────────────────────────────────
        elif action == 'finish':
            questions_and_answers = usage.result_data.get('answers', [])
            if not questions_and_answers:
                return Response({'error': 'No answers submitted yet.'}, status=400)

            # Return cached report if already generated
            if usage.result_data.get('final_report'):
                return Response({
                    'success': True,
                    'report':  usage.result_data['final_report'],
                    'cached':  True,
                })

            from utils.ai_tools_service import generate_interview_report
            student_name = f"{request.user.first_name} {request.user.last_name}".strip()
            ai_result = generate_interview_report(
                questions_and_answers,
                usage.result_data.get('job_role', 'Software Engineer'),
                student_name,
            )

            if not ai_result['success']:
                return Response({'error': ai_result['error']}, status=500)

            existing                  = usage.result_data
            existing['final_report']  = ai_result['data']
            existing['status']        = 'completed'
            usage.result_data         = existing
            usage.save(update_fields=['result_data'])

            return Response({'success': True, 'report': ai_result['data']})

        return Response(
            {'error': 'Invalid action. Use: start, submit_answer, finish'},
            status=400,
        )

    def get(self, request):
        """Returns past interview sessions (latest 10)."""
        usages = (
            AIToolUsage.objects
            .filter(user=request.user, tool_type='ai_interview')
            .order_by('-created_at')[:10]
        )
        sessions = []
        for u in usages:
            report = u.result_data.get('final_report', {}) if u.result_data else {}
            sessions.append({
                'usage_id':              u.id,
                'job_role':              u.result_data.get('job_role', '') if u.result_data else '',
                'status':                u.result_data.get('status', 'not_started') if u.result_data else 'not_started',
                'overall_score':         report.get('overall_score', 0),
                'grade':                 report.get('grade', ''),
                'hiring_recommendation': report.get('hiring_recommendation', ''),
                'created_at':            u.created_at.isoformat(),
            })
        return Response({'sessions': sessions})


# ══════════════════════════════════════════════════════════════
# VIEW 4 — Skill Gap Analyzer
# ══════════════════════════════════════════════════════════════

class SkillGapView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Analyzes skill gap for a target role.
        Requires: usage_id, target_role.
        """
        usage_id    = request.data.get('usage_id')
        target_role = request.data.get('target_role', '').strip()

        if not usage_id:
            return Response({'error': 'usage_id is required.'}, status=400)
        if not target_role:
            return Response(
                {'error': 'target_role is required. e.g. "Full Stack Developer at Google"'},
                status=400,
            )

        has_access, result = verify_tool_access(request.user, 'skill_gap', usage_id)
        if not has_access:
            return Response({'error': result}, status=403)

        usage = result

        if usage.result_data:
            return Response({'success': True, 'result': usage.result_data, 'cached': True})

        profile_data = get_student_profile_data(request.user)

        from utils.ai_tools_service import analyze_skill_gap
        ai_result = analyze_skill_gap(
            student_skills=profile_data.get('skills', []),
            target_role=target_role,
            current_education=profile_data.get('education_summary', ''),
        )

        if not ai_result['success']:
            return Response({'error': ai_result['error']}, status=500)

        usage.result_data = ai_result['data']
        usage.save(update_fields=['result_data'])

        return Response({'success': True, 'result': ai_result['data'], 'cached': False})

    def get(self, request):
        """Returns past skill gap analyses (latest 10)."""
        usages = (
            AIToolUsage.objects
            .filter(user=request.user, tool_type='skill_gap')
            .exclude(result_data={})
            .order_by('-created_at')[:10]
        )
        results = [
            {
                'usage_id':       u.id,
                'target_role':    u.result_data.get('target_role', ''),
                'readiness_score': u.result_data.get('readiness_score', 0),
                'readiness_level': u.result_data.get('readiness_level', ''),
                'total_weeks':    u.result_data.get('total_weeks_to_ready', 0),
                'created_at':     u.created_at.isoformat(),
            }
            for u in usages
        ]
        return Response({'results': results})
