from django.urls import path
from .page_views import (
    ReferralBoardPageView,
    ReferralDetailPageView,
    MyApplicationsPageView,
    ManageApplicationsPageView,
    SuccessStoriesPageView,
)

urlpatterns = [
    path('', ReferralBoardPageView.as_view(), name='referral_board'),
    path('my-applications/', MyApplicationsPageView.as_view(), name='my_applications'),
    path('success-stories/', SuccessStoriesPageView.as_view(), name='success_stories'),
    path('<int:referral_id>/', ReferralDetailPageView.as_view(), name='referral_detail'),
    path('<int:referral_id>/manage/', ManageApplicationsPageView.as_view(), name='manage_applications'),
]
