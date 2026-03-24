from django.urls import path
from .page_views import (
    WalletPageView,
    InvoicePageView,
    AdminPaymentsPageView,
)

# Mounted at /payments/
urlpatterns = [
    path('wallet/', WalletPageView.as_view(), name='wallet'),
    path('invoice/<str:invoice_number>/', InvoicePageView.as_view(), name='invoice'),
    path('admin/', AdminPaymentsPageView.as_view(), name='admin_payments'),
]
