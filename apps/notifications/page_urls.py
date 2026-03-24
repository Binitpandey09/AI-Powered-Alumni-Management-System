from django.urls import path
from .views import NotificationsPageView, NotificationPreferencesPageView

urlpatterns = [
    path('', NotificationsPageView.as_view()),
    path('preferences/', NotificationPreferencesPageView.as_view()),
]
