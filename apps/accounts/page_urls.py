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
    path('alumni/', BrowseAlumniPageView.as_view(), name='browse_alumni'),
    path('alumni/<int:user_id>/', PublicAlumniProfilePageView.as_view(), name='alumni_public'),
]
