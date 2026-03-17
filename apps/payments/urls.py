from django.urls import path, include
from rest_framework.routers import DefaultRouter

app_name = 'payments'

router = DefaultRouter()
# ViewSets will be registered here on Day 2:
# router.register(r'transactions', TransactionViewSet, basename='transaction')
# router.register(r'wallet', WalletViewSet, basename='wallet')
# router.register(r'withdrawals', WithdrawalViewSet, basename='withdrawal')

urlpatterns = [
    path('', include(router.urls)),
    # Additional URL patterns will be added on Day 2:
    # path('razorpay/webhook/', RazorpayWebhookView.as_view(), name='razorpay-webhook'),
    # path('initiate/', PaymentInitiateView.as_view(), name='payment-initiate'),
]
