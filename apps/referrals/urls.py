from django.urls import path
from .views import (
    ReferralListView,
    ReferralDetailView,
    ReferralApplyView,
    SkillMatchCheckView,
    ReferralApplicationListView,
    ReferralApplicationUpdateView,
    StudentApplicationListView,
    FacultyRecommendView,
    SuccessStoriesView,
)

urlpatterns = [
    path('', ReferralListView.as_view()),
    path('my-applications/', StudentApplicationListView.as_view()),
    path('my-applications/<int:application_id>/', StudentApplicationListView.as_view()),
    path('success-stories/', SuccessStoriesView.as_view()),
    path('<int:pk>/', ReferralDetailView.as_view()),
    path('<int:pk>/apply/', ReferralApplyView.as_view()),
    path('<int:pk>/match-check/', SkillMatchCheckView.as_view()),
    path('<int:pk>/applications/', ReferralApplicationListView.as_view()),
    path('<int:pk>/recommend/', FacultyRecommendView.as_view()),
    path('applications/<int:pk>/update/', ReferralApplicationUpdateView.as_view()),
]
