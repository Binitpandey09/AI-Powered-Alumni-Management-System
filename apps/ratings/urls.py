from django.urls import path
from .views import (
    SubmitSessionRatingView,
    SubmitReferralRatingView,
    UserRatingsView,
    MyRatingView,
    PendingRatingsView,
)

urlpatterns = [
    path('session/', SubmitSessionRatingView.as_view()),
    path('referral/', SubmitReferralRatingView.as_view()),
    path('user/<int:user_id>/', UserRatingsView.as_view()),
    path('my-rating/<int:booking_id>/', MyRatingView.as_view()),
    path('pending/', PendingRatingsView.as_view()),
]
