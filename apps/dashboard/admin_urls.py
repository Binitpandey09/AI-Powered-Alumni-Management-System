from django.urls import path
from .views import (
    AdminDashboardPageView,
    AdminUsersPageView,
    AdminAlumniVerificationPageView,
    AdminModerationPageView,
    AdminSessionsPageView,
    AdminReferralsPageView,
    AdminRevenuePageView,
    AdminPayoutsPageView,
    AdminAIUsagePageView,
    AdminBroadcastPageView,
    AdminAuditLogPageView,
)

urlpatterns = [
    path('', AdminDashboardPageView.as_view(), name='admin_dashboard'),
    path('users/', AdminUsersPageView.as_view(), name='admin_users'),
    path('alumni-verification/', AdminAlumniVerificationPageView.as_view(), name='admin_alumni_verification'),
    path('moderation/', AdminModerationPageView.as_view(), name='admin_moderation_page'),
    path('sessions/', AdminSessionsPageView.as_view(), name='admin_sessions'),
    path('referrals/', AdminReferralsPageView.as_view(), name='admin_referrals'),
    path('revenue/', AdminRevenuePageView.as_view(), name='admin_revenue'),
    path('payouts/', AdminPayoutsPageView.as_view(), name='admin_payouts'),
    path('ai-usage/', AdminAIUsagePageView.as_view(), name='admin_ai_usage'),
    path('broadcast/', AdminBroadcastPageView.as_view(), name='admin_broadcast'),
    path('audit-log/', AdminAuditLogPageView.as_view(), name='admin_audit_log'),
]
