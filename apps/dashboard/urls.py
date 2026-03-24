from django.urls import path
from .views import (
    AlumniDashboardView,
    StudentDashboardView,
    FacultyDashboardView,
    AdminModerationView,
    AdminOverviewView,
    AdminUserListView,
    AdminUserActionView,
    AdminAlumniVerificationView,
    AdminContentModerationView,
    AdminSessionsView,
    AdminBroadcastView,
    AdminReferralsView,
    AdminActionLogView,
)

urlpatterns = [
    # Page views
    path('alumni/', AlumniDashboardView.as_view(), name='alumni_dashboard'),
    path('student/', StudentDashboardView.as_view(), name='student_dashboard'),
    path('faculty/', FacultyDashboardView.as_view(), name='faculty_dashboard'),
    path('admin/moderation/', AdminModerationView.as_view(), name='admin_moderation'),

    # Admin API views
    path('admin/overview/', AdminOverviewView.as_view()),
    path('admin/users/', AdminUserListView.as_view()),
    path('admin/users/<int:user_id>/action/', AdminUserActionView.as_view()),
    path('admin/alumni/verification/', AdminAlumniVerificationView.as_view()),
    path('admin/alumni/verification/<int:alumni_id>/', AdminAlumniVerificationView.as_view()),
    path('admin/moderation-api/', AdminContentModerationView.as_view()),
    path('admin/sessions/', AdminSessionsView.as_view()),
    path('admin/referrals/', AdminReferralsView.as_view()),
    path('admin/broadcast/', AdminBroadcastView.as_view()),
    path('admin/action-log/', AdminActionLogView.as_view()),
]
