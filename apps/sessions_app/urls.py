from django.urls import path, include
from rest_framework.routers import DefaultRouter

app_name = 'sessions_app'

router = DefaultRouter()
# ViewSets will be registered here on Day 2:
# router.register(r'sessions', SessionViewSet, basename='session')
# router.register(r'bookings', BookingViewSet, basename='booking')
# router.register(r'reviews', ReviewViewSet, basename='review')
# router.register(r'availability', AvailabilityViewSet, basename='availability')

urlpatterns = [
    path('', include(router.urls)),
]
