from django.urls import path
from .page_views import (
    SessionsMarketplacePageView,
    SessionDetailPageView,
    MyBookingsPageView,
    HostedSessionsPageView,
    EarningsPageView,
)

urlpatterns = [
    path('', SessionsMarketplacePageView.as_view()),
    path('my-bookings/', MyBookingsPageView.as_view()),
    path('hosting/', HostedSessionsPageView.as_view()),
    path('earnings/', EarningsPageView.as_view()),
    path('<int:session_id>/', SessionDetailPageView.as_view()),
]
