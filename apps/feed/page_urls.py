from django.urls import path
from .views import FeedPageView

urlpatterns = [
    path('feed/', FeedPageView.as_view(), name='feed'),
]
