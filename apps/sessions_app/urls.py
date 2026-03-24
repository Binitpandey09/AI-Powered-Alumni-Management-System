from django.urls import path
from .views import (
    SessionListView,
    SessionDetailView,
    SessionBookingView,
    PaymentVerifyView,
    BookingListView,
    BookingCancelView,
    HostedSessionsView,
    SessionBookingsView,
    AddMeetingLinkView,
    SessionReviewView,
    EarningsSummaryView,
    BankDetailsView,
)

urlpatterns = [
    path('', SessionListView.as_view()),
    path('hosting/', HostedSessionsView.as_view()),
    path('my-bookings/', BookingListView.as_view()),
    path('payment/verify/', PaymentVerifyView.as_view()),
    path('earnings/', EarningsSummaryView.as_view()),
    path('bank-details/', BankDetailsView.as_view()),
    path('bookings/<int:booking_id>/cancel/', BookingCancelView.as_view()),
    path('bookings/<int:booking_id>/review/', SessionReviewView.as_view()),
    path('<int:pk>/', SessionDetailView.as_view()),
    path('<int:pk>/book/', SessionBookingView.as_view()),
    path('<int:pk>/bookings/', SessionBookingsView.as_view()),
    path('<int:pk>/meeting-link/', AddMeetingLinkView.as_view()),
    path('<int:pk>/reviews/', SessionReviewView.as_view()),
]
