from django.urls import path, include
from rest_framework.routers import DefaultRouter

app_name = 'notifications'

router = DefaultRouter()
# ViewSets will be registered here on Day 2:
# router.register(r'', NotificationViewSet, basename='notification')

urlpatterns = [
    path('', include(router.urls)),
]
