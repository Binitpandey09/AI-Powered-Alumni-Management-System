from django.db.models import Q
from django.utils import timezone
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from .models import Post, PostLike, PostComment, PostReport, PostSave
from .serializers import (
    PostCreateSerializer, PostListSerializer, PostDetailSerializer, PostCommentSerializer,
)
from utils.permissions import CanCreatePost, IsPostAuthorOrAdmin


# ── Pagination ────────────────────────────────────────────────────────────────

class FeedPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


class CommentPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# ── Feed list + create ────────────────────────────────────────────────────────

class FeedListView(APIView):
    permission_classes = [IsAuthenticated]

    def _base_qs(self):
        return (
            Post.objects
            .filter(status='active')
            .exclude(post_type='session', session_date__lt=timezone.now())
            .exclude(post_type='referral', referral__status__in=['closed', 'expired', 'paused'])
            .select_related(
                'author',
                'author__alumni_profile',
                'author__student_profile',
                'author__faculty_profile',
            )
            .prefetch_related('tags')
        )

    def get(self, request):
        qs = self._base_qs()

        post_type = request.query_params.get('type')
        if post_type:
            qs = qs.filter(post_type=post_type)

        author_id = request.query_params.get('author')
        if author_id:
            qs = qs.filter(author_id=author_id)

        tag = request.query_params.get('tag')
        if tag:
            qs = qs.filter(tags__name__iexact=tag)

        search = request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(content__icontains=search))

        if request.query_params.get('my_posts') == 'true':
            qs = qs.filter(author=request.user)

        paginator = FeedPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = PostListSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        # Check create permission manually (CanCreatePost)
        perm = CanCreatePost()
        if not perm.has_permission(request, self):
            return Response({'detail': perm.message}, status=status.HTTP_403_FORBIDDEN)

        serializer = PostCreateSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        post = serializer.save()
        return Response(
            PostDetailSerializer(post, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


# ── Post detail ───────────────────────────────────────────────────────────────

class PostDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_post(self, pk):
        try:
            return Post.objects.select_related(
                'author', 'author__alumni_profile',
                'author__student_profile', 'author__faculty_profile',
            ).prefetch_related('tags').get(pk=pk)
        except Post.DoesNotExist:
            return None

    def get(self, request, pk):
        post = self._get_post(pk)
        if not post or post.status in ('deleted',):
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(PostDetailSerializer(post, context={'request': request}).data)

    def patch(self, request, pk):
        post = self._get_post(pk)
        if not post:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        perm = IsPostAuthorOrAdmin()
        if not perm.has_object_permission(request, self, post):
            return Response({'detail': perm.message}, status=status.HTTP_403_FORBIDDEN)

        allowed = [
            'title', 'content', 'image', 'tags',
            'company_name', 'job_role', 'location', 'salary_range',
            'required_skills', 'apply_link',
            'session_date', 'session_price', 'session_duration', 'max_seats',
        ]
        for field in allowed:
            if field in request.data:
                if field == 'tags':
                    tag_list = [t.strip() for t in request.data['tags'].split(',') if t.strip()]
                    post.tags.set(*tag_list)
                elif field == 'image':
                    post.image = request.FILES.get('image')
                else:
                    setattr(post, field, request.data[field])
        post.save()
        return Response(PostDetailSerializer(post, context={'request': request}).data)

    def delete(self, request, pk):
        post = self._get_post(pk)
        if not post:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        perm = IsPostAuthorOrAdmin()
        if not perm.has_object_permission(request, self, post):
            return Response({'detail': perm.message}, status=status.HTTP_403_FORBIDDEN)

        post.status = 'deleted'
        post.save(update_fields=['status'])
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Like toggle ───────────────────────────────────────────────────────────────

class PostLikeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            post = Post.objects.get(pk=pk, status='active')
        except Post.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        like = PostLike.objects.filter(post=post, user=request.user).first()
        if like:
            like.delete()
            post.refresh_from_db(fields=['likes_count'])
            return Response({'liked': False, 'likes_count': post.likes_count})
        else:
            PostLike.objects.create(post=post, user=request.user)
            post.refresh_from_db(fields=['likes_count'])
            return Response({'liked': True, 'likes_count': post.likes_count})


# ── Save toggle ───────────────────────────────────────────────────────────────

class PostSaveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            post = Post.objects.get(pk=pk, status='active')
        except Post.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        save = PostSave.objects.filter(post=post, user=request.user).first()
        if save:
            save.delete()
            return Response({'saved': False})
        else:
            PostSave.objects.create(post=post, user=request.user)
            return Response({'saved': True})


# ── Comments ──────────────────────────────────────────────────────────────────

class PostCommentListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            post = Post.objects.get(pk=pk, status='active')
        except Post.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        qs = post.comments.filter(parent=None).select_related(
            'author', 'author__alumni_profile',
            'author__student_profile', 'author__faculty_profile',
        ).prefetch_related('replies')

        paginator = CommentPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = PostCommentSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, pk):
        try:
            post = Post.objects.get(pk=pk, status='active')
        except Post.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = PostCommentSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        comment = serializer.save(author=request.user, post=post)
        return Response(
            PostCommentSerializer(comment, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


# ── Comment detail (edit / soft-delete) ──────────────────────────────────────

class PostCommentDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_comment(self, comment_id):
        try:
            return PostComment.objects.select_related('author').get(pk=comment_id)
        except PostComment.DoesNotExist:
            return None

    def patch(self, request, comment_id):
        comment = self._get_comment(comment_id)
        if not comment:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if comment.author != request.user:
            return Response({'detail': 'Only the comment author can edit.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = PostCommentSerializer(
            comment, data={'content': request.data.get('content', '')},
            partial=True, context={'request': request}
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, comment_id):
        comment = self._get_comment(comment_id)
        if not comment:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if comment.author != request.user and request.user.role != 'admin':
            return Response({'detail': 'Not allowed.'}, status=status.HTTP_403_FORBIDDEN)

        comment.is_deleted = True
        comment.save(update_fields=['is_deleted'])
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Report ────────────────────────────────────────────────────────────────────

class PostReportView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            post = Post.objects.get(pk=pk)
        except Post.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        if PostReport.objects.filter(post=post, reported_by=request.user).exists():
            return Response(
                {'detail': 'You have already reported this post.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reason = request.data.get('reason', '')
        valid_reasons = [r[0] for r in PostReport.REASONS]
        if reason not in valid_reasons:
            return Response(
                {'reason': f'Must be one of: {", ".join(valid_reasons)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        PostReport.objects.create(
            post=post,
            reported_by=request.user,
            reason=reason,
            description=request.data.get('description', ''),
        )
        return Response(
            {'message': 'Post reported. Our team will review it.'},
            status=status.HTTP_201_CREATED,
        )


# ── Saved posts ───────────────────────────────────────────────────────────────

class SavedPostsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        saved_ids = PostSave.objects.filter(user=request.user).values_list('post_id', flat=True)
        qs = (
            Post.objects
            .filter(pk__in=saved_ids, status='active')
            .select_related(
                'author', 'author__alumni_profile',
                'author__student_profile', 'author__faculty_profile',
            )
            .prefetch_related('tags')
        )
        paginator = FeedPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = PostListSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)


# ── Feed page view ────────────────────────────────────────────────────────────

class FeedPageView(LoginRequiredMixin, TemplateView):
    template_name = 'feed/feed.html'
    login_url = '/auth/login/'


# ── Admin: flagged posts list ─────────────────────────────────────────────────

class AdminFlaggedPostsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Admin only'}, status=status.HTTP_403_FORBIDDEN)
        posts = (
            Post.objects
            .filter(status__in=['flagged', 'active'])
            .select_related('author', 'author__alumni_profile',
                            'author__student_profile', 'author__faculty_profile')
            .prefetch_related('tags')
            .order_by('-flagged_count', '-created_at')[:50]
        )
        return Response(PostListSerializer(posts, many=True, context={'request': request}).data)


# ── Admin: post action ────────────────────────────────────────────────────────

class AdminPostActionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if request.user.role != 'admin':
            return Response({'error': 'Admin only'}, status=status.HTTP_403_FORBIDDEN)

        action = request.data.get('action')
        post = get_object_or_404(Post, pk=pk)

        if action == 'approve':
            post.status = 'active'
            post.flagged_count = 0
        elif action == 'hide':
            post.status = 'hidden'
        elif action == 'delete':
            post.status = 'deleted'
        else:
            return Response({'error': 'Invalid action. Use approve/hide/delete.'},
                            status=status.HTTP_400_BAD_REQUEST)

        post.admin_note = request.data.get('note', '')
        post.save()
        return Response({'message': f'Post {action}d successfully'})
