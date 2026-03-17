from django.urls import path, include
from rest_framework.routers import DefaultRouter

app_name = 'referrals'

router = DefaultRouter()
# ViewSets will be registered here on Day 2:
# router.register(r'referrals', ReferralViewSet, basename='referral')
# router.register(r'applications', ApplicationViewSet, basename='application')

urlpatterns = [
    path('', include(router.urls)),
]
