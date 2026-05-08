from django.urls import path
from .views import (
    HomeView,
    ChooseRoleView,
    RegisterPageView,
    VerifyOTPPageView,
    LoginPageView,
    ProfileEditPageView,
    ProfileSetupPageView,
    EditProfilePageView,
    BrowseAlumniPageView,
    PublicAlumniProfilePageView,
    StudentProfilePageView,
    PublicStudentProfilePageView,
    ConnectPageView,
    AlumniProfilePageView,
    FacultyProfilePageView,
    AlumniProfileSelfPageView,
    FacultyEditProfilePageView,
)

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('auth/choose-role/', ChooseRoleView.as_view(), name='choose_role'),
    path('auth/register/', RegisterPageView.as_view(), name='register_page'),
    path('auth/verify-otp/', VerifyOTPPageView.as_view(), name='verify_otp_page'),
    path('auth/login/', LoginPageView.as_view(), name='login_page'),
    path('profile/', ProfileEditPageView.as_view(), name='profile_edit'),
    path('profile/setup/', ProfileSetupPageView.as_view(), name='profile_setup'),
    path('profile/edit/', EditProfilePageView.as_view(), name='profile_edit_new'),
    path('profile/student/', StudentProfilePageView.as_view(), name='student_profile'),
    path('profile/alumni/', AlumniProfileSelfPageView.as_view(), name='alumni_profile_self'),
    path('profile/faculty/edit/', FacultyEditProfilePageView.as_view(), name='faculty_profile_edit'),
    # Connect page (replaces Browse Alumni for students)
    path('connect/', ConnectPageView.as_view(), name='connect'),
    # Public profiles
    path('alumni/<int:user_id>/', AlumniProfilePageView.as_view(), name='alumni_public'),
    path('faculty/<int:user_id>/', FacultyProfilePageView.as_view(), name='faculty_public'),
    path('students/<int:user_id>/profile/', PublicStudentProfilePageView.as_view(), name='student_public_profile'),
    # Keep old /alumni/ route for backward compat (redirects to /connect/)
    path('alumni/', BrowseAlumniPageView.as_view(), name='browse_alumni'),
]

from .views import AlumniEditProfilePageView, ConnectionsPageView

urlpatterns += [
    path('profile/alumni/edit/', AlumniEditProfilePageView.as_view(), name='alumni_profile_edit'),
    path('connections/', ConnectionsPageView.as_view(), name='connections'),
]
