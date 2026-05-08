from django.urls import path
from .views import FeedPageView, PostDetailPageView

urlpatterns = [
    path('feed/', FeedPageView.as_view(), name='feed'),
    path('feed/<int:pk>/', PostDetailPageView.as_view(), name='feed-post-detail'),
]
