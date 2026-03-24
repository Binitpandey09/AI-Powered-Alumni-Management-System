from django.urls import path
from .views import (
    WalletView,
    TransactionListView,
    PayoutRequestView,
    AIToolPaymentInitView,
    AIToolPaymentVerifyView,
    ReferralBoostPaymentView,
    InvoiceView,
    AdminPayoutManageView,
    PlatformRevenueView,
    AIToolUsageCheckView,
)

urlpatterns = [
    path('wallet/', WalletView.as_view()),
    path('transactions/', TransactionListView.as_view()),
    path('payout/', PayoutRequestView.as_view()),
    path('payout/<int:pk>/', PayoutRequestView.as_view()),
    path('ai-tools/init/', AIToolPaymentInitView.as_view()),
    path('ai-tools/verify/', AIToolPaymentVerifyView.as_view()),
    path('ai-tools/check/<str:tool_type>/', AIToolUsageCheckView.as_view()),
    path('boost/', ReferralBoostPaymentView.as_view()),
    path('boost/verify/', ReferralBoostPaymentView.as_view()),
    path('invoice/<str:invoice_number>/', InvoiceView.as_view()),
    path('admin/payouts/', AdminPayoutManageView.as_view()),
    path('admin/payouts/<int:pk>/', AdminPayoutManageView.as_view()),
    path('admin/revenue/', PlatformRevenueView.as_view()),
]
