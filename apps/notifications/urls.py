from django.urls import path
from . import views

urlpatterns = [
    path('', views.NotificationListView.as_view(), name='notification-list'),
    path('unread-count/', views.NotificationUnreadCountView.as_view(), name='notification-unread-count'),
    path('bulk/', views.NotificationBulkActionView.as_view(), name='notification-bulk'),
    path('preferences/', views.NotificationPreferenceView.as_view(), name='notification-preferences'),
    path('<int:pk>/', views.NotificationDetailView.as_view(), name='notification-detail'),
]
