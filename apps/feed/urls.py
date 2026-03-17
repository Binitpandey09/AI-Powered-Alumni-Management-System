from django.urls import path, include
from rest_framework.routers import DefaultRouter

app_name = 'feed'

router = DefaultRouter()
# ViewSets will be registered here on Day 2:
# router.register(r'posts', PostViewSet, basename='post')
# router.register(r'comments', CommentViewSet, basename='comment')
# router.register(r'likes', LikeViewSet, basename='like')

urlpatterns = [
    path('', include(router.urls)),
]
