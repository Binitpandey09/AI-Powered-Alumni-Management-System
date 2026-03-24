from django.urls import path
from .views import (
    FeedListView,
    PostDetailView,
    PostLikeView,
    PostSaveView,
    PostCommentListView,
    PostCommentDetailView,
    PostReportView,
    SavedPostsView,
    AdminFlaggedPostsView,
    AdminPostActionView,
)

urlpatterns = [
    path('', FeedListView.as_view()),                                      # GET feed, POST create
    path('saved/', SavedPostsView.as_view()),                              # GET saved posts
    path('admin/flagged/', AdminFlaggedPostsView.as_view()),               # GET flagged posts
    path('admin/<int:pk>/action/', AdminPostActionView.as_view()),         # POST approve/hide/delete
    path('<int:pk>/', PostDetailView.as_view()),                           # GET, PATCH, DELETE
    path('<int:pk>/like/', PostLikeView.as_view()),                        # POST toggle like
    path('<int:pk>/save/', PostSaveView.as_view()),                        # POST toggle save
    path('<int:pk>/comments/', PostCommentListView.as_view()),             # GET, POST comments
    path('<int:pk>/report/', PostReportView.as_view()),                    # POST report
    path('comments/<int:comment_id>/', PostCommentDetailView.as_view()),  # PATCH, DELETE comment
]
