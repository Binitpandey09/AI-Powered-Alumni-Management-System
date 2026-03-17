from django.utils import timezone
from datetime import timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import EmailOTP
from .serializers import (
    UserRegistrationSerializer,
    OTPVerificationSerializer,
    LoginRequestSerializer,
    LoginOTPSerializer,
    UserProfileSerializer,
)
from .validators import generate_otp


class RegisterView(APIView):
    """
    POST /api/accounts/register/
    Register a new user and send OTP to their email.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return Response(
            {'message': 'OTP sent to your email. Please verify to complete registration.'},
            status=status.HTTP_201_CREATED,
        )


class VerifyRegistrationOTPView(APIView):
    """
    POST /api/accounts/verify-otp/
    Verify the registration OTP and activate the account.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OTPVerificationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return Response(
            {'message': 'Email verified successfully. You can now log in.'},
            status=status.HTTP_200_OK,
        )


class LoginRequestView(APIView):
    """
    POST /api/accounts/login/
    Validate credentials and send a login OTP.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return Response(
            {'message': 'OTP sent to your registered email.'},
            status=status.HTTP_200_OK,
        )


class LoginVerifyOTPView(APIView):
    """
    POST /api/accounts/login/verify/
    Verify login OTP and return JWT tokens + set httponly cookie.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        token_data = serializer.save()
        response = Response(token_data, status=status.HTTP_200_OK)

        # Set httponly cookie so JWTAuthMiddleware can read it for page-level auth
        response.set_cookie(
            key='access_token',
            value=token_data['access'],
            httponly=True,
            secure=not request.META.get('SERVER_NAME', '').startswith('localhost'),
            samesite='Lax',
            max_age=60 * 60,  # 1 hour — matches ACCESS_TOKEN_LIFETIME
        )
        return response


class ResendOTPView(APIView):
    """
    POST /api/accounts/resend-otp/
    Resend OTP with a 60-second rate limit.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        purpose = request.data.get('purpose', '').strip()

        if not email or not purpose:
            return Response(
                {'message': 'email and purpose are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        valid_purposes = [EmailOTP.REGISTRATION, EmailOTP.LOGIN, EmailOTP.VERIFY]
        if purpose not in valid_purposes:
            return Response(
                {'message': f'purpose must be one of: {", ".join(valid_purposes)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Rate-limit: reject if an OTP was sent in the last 60 seconds
        one_minute_ago = timezone.now() - timedelta(seconds=60)
        recent_otp = EmailOTP.objects.filter(
            email=email,
            purpose=purpose,
            created_at__gte=one_minute_ago,
        ).exists()

        if recent_otp:
            return Response(
                {'message': 'Please wait 60 seconds before requesting a new OTP.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # Find the user
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {'message': 'No account found with this email.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Invalidate all previous unused OTPs for this email + purpose
        EmailOTP.objects.filter(
            email=email, purpose=purpose, is_used=False
        ).update(is_used=True)

        # Create and send new OTP
        otp_code = generate_otp()
        EmailOTP.objects.create(
            user=user,
            email=email,
            otp_code=otp_code,
            purpose=purpose,
            expires_at=timezone.now() + timedelta(minutes=10),
        )

        from .tasks import send_otp_email
        try:
            from .tasks import send_otp_email_task
            send_otp_email_task.delay(user.id, email, otp_code, purpose)
        except Exception:
            send_otp_email(user.id, email, otp_code, purpose)

        return Response(
            {'message': 'A new OTP has been sent to your email.'},
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    """
    POST /api/accounts/logout/
    Blacklist the refresh token and clear the httponly cookie.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'message': 'Refresh token is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError as e:
            return Response(
                {'message': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        response = Response({'message': 'Logged out successfully.'}, status=status.HTTP_200_OK)
        response.delete_cookie('access_token')
        return response


class MeView(APIView):
    """
    GET /api/accounts/me/
    Return the authenticated user's profile.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ── Template / Page Views ──────────────────────────────────────────────────────

from django.views.generic import TemplateView
from django.shortcuts import redirect
from django.conf import settings as django_settings


class HomeView(TemplateView):
    template_name = 'home.html'


class ChooseRoleView(TemplateView):
    template_name = 'accounts/choose_role.html'


class RegisterPageView(TemplateView):
    template_name = 'accounts/register.html'


class VerifyOTPPageView(TemplateView):
    template_name = 'accounts/verify_otp.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # In DEBUG mode, surface the latest OTP so devs don't need real email
        if django_settings.DEBUG:
            email = self.request.GET.get('email', '').strip().lower()
            purpose = self.request.GET.get('purpose', 'registration')
            if email:
                otp = (
                    EmailOTP.objects
                    .filter(email=email, purpose=purpose, is_used=False)
                    .order_by('-created_at')
                    .first()
                )
                ctx['dev_otp'] = otp.otp_code if otp else None
        return ctx


class LoginPageView(TemplateView):
    template_name = 'accounts/login.html'


class ProfileEditPageView(TemplateView):
    template_name = 'accounts/profile_edit.html'


# ── JWT-protected page mixin ──────────────────────────────────────────────────

class JWTLoginRequiredMixin:
    """Validates httponly access_token cookie; redirects to login if missing/invalid."""

    def dispatch(self, request, *args, **kwargs):
        from utils.auth_helpers import get_user_from_token
        token = request.COOKIES.get('access_token', '')
        user = get_user_from_token(token)
        if not user:
            return redirect(f'/auth/login/?next={request.path}')
        # Redirect to profile setup if profile not complete (skip for setup page itself)
        if not user.is_profile_complete and request.path not in ('/profile/setup/', '/auth/login/', '/auth/logout/'):
            return redirect('/profile/setup/')
        request.user = user
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['user'] = self.request.user
        ctx['user_role'] = self.request.user.role
        return ctx


class ProfileSetupPageView(JWTLoginRequiredMixin, TemplateView):
    template_name = 'accounts/profile_setup.html'

    def dispatch(self, request, *args, **kwargs):
        # Bypass the profile-complete redirect for this view specifically
        from utils.auth_helpers import get_user_from_token
        token = request.COOKIES.get('access_token', '')
        user = get_user_from_token(token)
        if not user:
            return redirect(f'/auth/login/?next={request.path}')
        request.user = user
        return TemplateView.dispatch(self, request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['user'] = self.request.user
        ctx['user_role'] = self.request.user.role
        return ctx


class EditProfilePageView(JWTLoginRequiredMixin, TemplateView):
    template_name = 'accounts/edit_profile.html'


class BrowseAlumniPageView(JWTLoginRequiredMixin, TemplateView):
    template_name = 'accounts/browse_alumni.html'


class PublicAlumniProfilePageView(JWTLoginRequiredMixin, TemplateView):
    template_name = 'accounts/alumni_profile.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['alumni_user_id'] = kwargs.get('user_id')
        return ctx


class StudentProfilePageView(JWTLoginRequiredMixin, TemplateView):
    template_name = 'accounts/student_profile.html'

    def dispatch(self, request, *args, **kwargs):
        from utils.auth_helpers import get_user_from_token
        token = request.COOKIES.get('access_token', '')
        user = get_user_from_token(token)
        if not user:
            return redirect(f'/auth/login/?next={request.path}')
        if user.role != 'student':
            return redirect(f'/dashboard/{user.role}/')
        request.user = user
        return TemplateView.dispatch(self, request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['user'] = self.request.user
        ctx['user_role'] = 'student'
        return ctx


# ── Student Profile Section Views ─────────────────────────────────────────────

from django.http import Http404
from django.contrib.auth import get_user_model
from .models import (
    StudentEducation, StudentProject, StudentInternship,
    StudentCertification, StudentAward, StudentCompetitiveExam,
    StudentLanguage, StudentEmployment,
)
from .serializers import (
    StudentEducationSerializer, StudentProjectSerializer,
    StudentInternshipSerializer, StudentCertificationSerializer,
    StudentAwardSerializer, StudentCompetitiveExamSerializer,
    StudentLanguageSerializer, StudentEmploymentSerializer,
    FullStudentProfileSerializer,
)
from utils.permissions import IsStudent


def _make_list_view(Model, Serializer):
    """Factory that returns a list+create APIView class for a given model."""
    class ListView(APIView):
        permission_classes = [IsAuthenticated, IsStudent]

        def get(self, request):
            qs = Model.objects.filter(user=request.user)
            return Response(Serializer(qs, many=True).data)

        def post(self, request):
            s = Serializer(data=request.data)
            if s.is_valid():
                s.save(user=request.user)
                return Response(s.data, status=status.HTTP_201_CREATED)
            return Response(s.errors, status=status.HTTP_400_BAD_REQUEST)

    return ListView


def _make_detail_view(Model, Serializer):
    """Factory that returns a retrieve+patch+delete APIView class."""
    class DetailView(APIView):
        permission_classes = [IsAuthenticated, IsStudent]

        def _get_obj(self, pk, user):
            try:
                return Model.objects.get(pk=pk, user=user)
            except Model.DoesNotExist:
                raise Http404

        def get(self, request, pk):
            return Response(Serializer(self._get_obj(pk, request.user)).data)

        def patch(self, request, pk):
            obj = self._get_obj(pk, request.user)
            s = Serializer(obj, data=request.data, partial=True)
            if s.is_valid():
                s.save()
                return Response(s.data)
            return Response(s.errors, status=status.HTTP_400_BAD_REQUEST)

        def delete(self, request, pk):
            self._get_obj(pk, request.user).delete()
            return Response({'message': 'Deleted successfully'}, status=status.HTTP_204_NO_CONTENT)

    return DetailView


StudentEducationListView   = _make_list_view(StudentEducation,   StudentEducationSerializer)
StudentEducationDetailView = _make_detail_view(StudentEducation, StudentEducationSerializer)

StudentProjectListView   = _make_list_view(StudentProject,   StudentProjectSerializer)
StudentProjectDetailView = _make_detail_view(StudentProject, StudentProjectSerializer)

StudentInternshipListView   = _make_list_view(StudentInternship,   StudentInternshipSerializer)
StudentInternshipDetailView = _make_detail_view(StudentInternship, StudentInternshipSerializer)

StudentCertificationListView   = _make_list_view(StudentCertification,   StudentCertificationSerializer)
StudentCertificationDetailView = _make_detail_view(StudentCertification, StudentCertificationSerializer)

StudentAwardListView   = _make_list_view(StudentAward,   StudentAwardSerializer)
StudentAwardDetailView = _make_detail_view(StudentAward, StudentAwardSerializer)

StudentCompetitiveExamListView   = _make_list_view(StudentCompetitiveExam,   StudentCompetitiveExamSerializer)
StudentCompetitiveExamDetailView = _make_detail_view(StudentCompetitiveExam, StudentCompetitiveExamSerializer)

StudentLanguageListView   = _make_list_view(StudentLanguage,   StudentLanguageSerializer)
StudentLanguageDetailView = _make_detail_view(StudentLanguage, StudentLanguageSerializer)

StudentEmploymentListView   = _make_list_view(StudentEmployment,   StudentEmploymentSerializer)
StudentEmploymentDetailView = _make_detail_view(StudentEmployment, StudentEmploymentSerializer)


class FullStudentProfileView(APIView):
    """GET /api/accounts/profile/student/full/ or /api/accounts/profile/student/full/<user_id>/"""
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id=None):
        User = get_user_model()
        if user_id:
            try:
                target = User.objects.get(pk=user_id)
            except User.DoesNotExist:
                return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        else:
            target = request.user

        if target.role != 'student':
            return Response({'error': 'Not a student'}, status=status.HTTP_404_NOT_FOUND)

        return Response(FullStudentProfileSerializer(target).data)
