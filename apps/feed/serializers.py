import os
from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Post, PostComment, PostLike, PostSave

User = get_user_model()


# ── Author serializer ─────────────────────────────────────────────────────────

class PostAuthorSerializer(serializers.ModelSerializer):
    role_detail = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'role', 'profile_pic', 'college', 'role_detail']
        read_only_fields = fields

    def get_role_detail(self, obj):
        try:
            if obj.role == 'alumni':
                p = obj.alumni_profile
                return {'company': p.company, 'designation': p.designation}
            elif obj.role == 'faculty':
                p = obj.faculty_profile
                return {'department': p.department, 'designation': p.designation}
            elif obj.role == 'student':
                p = obj.student_profile
                return {'degree': p.degree, 'college': obj.college}
        except Exception:
            pass
        return {}


# ── Comment serializer ────────────────────────────────────────────────────────

class PostCommentSerializer(serializers.ModelSerializer):
    author = PostAuthorSerializer(read_only=True)
    replies = serializers.SerializerMethodField()
    parent = serializers.PrimaryKeyRelatedField(
        queryset=PostComment.objects.all(), required=False, allow_null=True, write_only=True
    )

    class Meta:
        model = PostComment
        fields = ['id', 'author', 'content', 'parent', 'replies', 'is_deleted', 'created_at']
        read_only_fields = ['id', 'author', 'replies', 'is_deleted', 'created_at']

    def get_replies(self, obj):
        # Only top-level comments expose replies
        if obj.parent_id is not None:
            return []
        qs = obj.replies.filter(is_deleted=False).select_related(
            'author', 'author__alumni_profile', 'author__student_profile', 'author__faculty_profile'
        )
        return PostCommentSerializer(qs, many=True, context=self.context).data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.is_deleted:
            data['content'] = '[This comment was deleted]'
        return data

    def validate_content(self, value):
        value = value.strip()
        if len(value) < 1:
            raise serializers.ValidationError('Comment cannot be empty.')
        if len(value) > 1000:
            raise serializers.ValidationError('Comment cannot exceed 1000 characters.')
        return value


# ── Post create serializer ────────────────────────────────────────────────────

class PostCreateSerializer(serializers.Serializer):
    post_type = serializers.ChoiceField(choices=[c[0] for c in Post.POST_TYPES])
    title = serializers.CharField(max_length=300, required=False, allow_blank=True)
    content = serializers.CharField(min_length=10, max_length=5000)
    image = serializers.ImageField(required=False, allow_null=True)
    tags = serializers.CharField(required=False, allow_blank=True, help_text='Comma-separated tag names')

    # Job / referral fields
    company_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    job_role = serializers.CharField(max_length=200, required=False, allow_blank=True)
    location = serializers.CharField(max_length=200, required=False, allow_blank=True)
    salary_range = serializers.CharField(max_length=100, required=False, allow_blank=True)
    required_skills = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )
    apply_link = serializers.URLField(required=False, allow_blank=True)

    # Session fields
    session_date = serializers.DateTimeField(required=False, allow_null=True)
    session_price = serializers.DecimalField(
        max_digits=8, decimal_places=2, required=False, allow_null=True
    )
    session_duration = serializers.IntegerField(required=False, allow_null=True)
    max_seats = serializers.IntegerField(required=False, allow_null=True)

    def validate_image(self, value):
        if value is None:
            return value
        ext = os.path.splitext(value.name)[1].lower().lstrip('.')
        if ext not in ['jpg', 'jpeg', 'png', 'webp']:
            raise serializers.ValidationError('Only JPG, PNG, and WebP images are allowed.')
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError('Image must be under 5MB.')
        return value

    def validate(self, data):
        post_type = data.get('post_type')
        if post_type in ('job', 'referral'):
            if not data.get('company_name'):
                raise serializers.ValidationError({'company_name': 'Required for job/referral posts.'})
            if not data.get('job_role'):
                raise serializers.ValidationError({'job_role': 'Required for job/referral posts.'})
        if post_type == 'session':
            if not data.get('session_date'):
                raise serializers.ValidationError({'session_date': 'Required for session posts.'})
            if data.get('session_price') is None:
                raise serializers.ValidationError({'session_price': 'Required for session posts.'})
        return data

    def create(self, validated_data):
        tags_str = validated_data.pop('tags', '')
        image = validated_data.pop('image', None)
        author = self.context['request'].user

        post = Post.objects.create(author=author, **validated_data)

        if image:
            post.image = image
            post.save(update_fields=['image'])

        if tags_str:
            tag_list = [t.strip() for t in tags_str.split(',') if t.strip()]
            post.tags.set(*tag_list)

        return post


# ── Post list serializer ──────────────────────────────────────────────────────

class PostListSerializer(serializers.ModelSerializer):
    author = PostAuthorSerializer(read_only=True)
    tags = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    is_saved = serializers.SerializerMethodField()
    content = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id', 'author', 'post_type', 'title', 'content', 'image', 'tags',
            'company_name', 'job_role', 'location', 'salary_range',
            'session_date', 'session_price', 'session_duration', 'max_seats',
            'likes_count', 'comments_count',
            'is_liked', 'is_saved', 'created_at', 'status',
        ]

    def get_tags(self, obj):
        return list(obj.tags.names())

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return PostLike.objects.filter(post=obj, user=request.user).exists()

    def get_is_saved(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return PostSave.objects.filter(post=obj, user=request.user).exists()

    def get_content(self, obj):
        if len(obj.content) > 300:
            return obj.content[:300] + '…'
        return obj.content

    def get_status(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated and request.user.role == 'admin':
            return obj.status
        return None


# ── Post detail serializer ────────────────────────────────────────────────────

class PostDetailSerializer(PostListSerializer):
    comments = serializers.SerializerMethodField()

    class Meta(PostListSerializer.Meta):
        fields = PostListSerializer.Meta.fields + [
            'required_skills', 'apply_link', 'comments', 'admin_note', 'flagged_count',
        ]

    def get_content(self, obj):
        # Full content — no truncation
        return obj.content

    def get_comments(self, obj):
        qs = obj.comments.filter(
            parent=None, is_deleted=False
        ).select_related(
            'author', 'author__alumni_profile', 'author__student_profile', 'author__faculty_profile'
        ).prefetch_related('replies')[:5]
        return PostCommentSerializer(qs, many=True, context=self.context).data
