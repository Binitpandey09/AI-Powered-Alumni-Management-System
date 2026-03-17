from django.urls import path
from .views import (
    RegisterView,
    VerifyRegistrationOTPView,
    LoginRequestView,
    LoginVerifyOTPView,
    ResendOTPView,
    LogoutView,
    MeView,
    # Section views
    StudentEducationListView, StudentEducationDetailView,
    StudentProjectListView, StudentProjectDetailView,
    StudentInternshipListView, StudentInternshipDetailView,
    StudentCertificationListView, StudentCertificationDetailView,
    StudentAwardListView, StudentAwardDetailView,
    StudentCompetitiveExamListView, StudentCompetitiveExamDetailView,
    StudentLanguageListView, StudentLanguageDetailView,
    StudentEmploymentListView, StudentEmploymentDetailView,
    FullStudentProfileView,
)
from .profile_views import (
    AlumniProfileView,
    StudentProfileView,
    FacultyProfileView,
    ProfilePictureUploadView,
    CVUploadView,
    BasicProfileUpdateView,
    AlumniBrowseView,
    PublicAlumniProfileView,
    ProfileCompletenessView,
)

app_name = 'accounts'

urlpatterns = [
    # Auth
    path('register/',       RegisterView.as_view(),             name='register'),
    path('verify-otp/',     VerifyRegistrationOTPView.as_view(), name='verify-otp'),
    path('login/',          LoginRequestView.as_view(),          name='login'),
    path('login/verify/',   LoginVerifyOTPView.as_view(),        name='login-verify'),
    path('resend-otp/',     ResendOTPView.as_view(),             name='resend-otp'),
    path('logout/',         LogoutView.as_view(),                name='logout'),
    path('me/',             MeView.as_view(),                    name='me'),

    # Profile management
    path('profile/basic/',        BasicProfileUpdateView.as_view(),    name='profile-basic'),
    path('profile/alumni/',       AlumniProfileView.as_view(),         name='profile-alumni'),
    path('profile/student/',      StudentProfileView.as_view(),        name='profile-student'),
    path('profile/faculty/',      FacultyProfileView.as_view(),        name='profile-faculty'),
    path('profile/picture/',      ProfilePictureUploadView.as_view(),  name='profile-picture'),
    path('profile/cv-upload/',    CVUploadView.as_view(),              name='cv-upload'),
    path('profile/completeness/', ProfileCompletenessView.as_view(),   name='profile-completeness'),

    # Full student profile
    path('profile/student/full/',              FullStudentProfileView.as_view(), name='student-full-profile'),
    path('profile/student/full/<int:user_id>/', FullStudentProfileView.as_view(), name='student-full-profile-public'),

    # Education
    path('profile/education/',         StudentEducationListView.as_view(),   name='education-list'),
    path('profile/education/<int:pk>/', StudentEducationDetailView.as_view(), name='education-detail'),

    # Projects
    path('profile/projects/',         StudentProjectListView.as_view(),   name='project-list'),
    path('profile/projects/<int:pk>/', StudentProjectDetailView.as_view(), name='project-detail'),

    # Internships
    path('profile/internships/',         StudentInternshipListView.as_view(),   name='internship-list'),
    path('profile/internships/<int:pk>/', StudentInternshipDetailView.as_view(), name='internship-detail'),

    # Certifications
    path('profile/certifications/',         StudentCertificationListView.as_view(),   name='certification-list'),
    path('profile/certifications/<int:pk>/', StudentCertificationDetailView.as_view(), name='certification-detail'),

    # Awards
    path('profile/awards/',         StudentAwardListView.as_view(),   name='award-list'),
    path('profile/awards/<int:pk>/', StudentAwardDetailView.as_view(), name='award-detail'),

    # Competitive Exams
    path('profile/exams/',         StudentCompetitiveExamListView.as_view(),   name='exam-list'),
    path('profile/exams/<int:pk>/', StudentCompetitiveExamDetailView.as_view(), name='exam-detail'),

    # Languages
    path('profile/languages/',         StudentLanguageListView.as_view(),   name='language-list'),
    path('profile/languages/<int:pk>/', StudentLanguageDetailView.as_view(), name='language-detail'),

    # Employment
    path('profile/employment/',         StudentEmploymentListView.as_view(),   name='employment-list'),
    path('profile/employment/<int:pk>/', StudentEmploymentDetailView.as_view(), name='employment-detail'),

    # Alumni browse / public profile
    path('alumni/',               AlumniBrowseView.as_view(),        name='alumni-browse'),
    path('alumni/<int:user_id>/', PublicAlumniProfileView.as_view(), name='alumni-public'),
]
