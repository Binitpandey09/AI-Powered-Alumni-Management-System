from django.contrib import admin
from .models import Post, PostLike, PostComment, PostReport, PostSave


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'author_email', 'post_type', 'status',
        'likes_count', 'comments_count', 'flagged_count', 'created_at',
    ]
    list_filter = ['post_type', 'status']
    search_fields = ['author__email', 'title', 'content']
    readonly_fields = ['likes_count', 'comments_count', 'flagged_count', 'created_at', 'updated_at']
    actions = ['approve_posts', 'hide_posts']

    def author_email(self, obj):
        return obj.author.email
    author_email.short_description = 'Author'

    @admin.action(description='Mark selected posts as active')
    def approve_posts(self, request, queryset):
        queryset.update(status='active')

    @admin.action(description='Hide selected posts')
    def hide_posts(self, request, queryset):
        queryset.update(status='hidden')


@admin.register(PostLike)
class PostLikeAdmin(admin.ModelAdmin):
    list_display = ['id', 'post', 'user', 'created_at']
    raw_id_fields = ['post', 'user']


@admin.register(PostComment)
class PostCommentAdmin(admin.ModelAdmin):
    list_display = ['id', 'post', 'author', 'is_deleted', 'created_at']
    list_filter = ['is_deleted']
    search_fields = ['author__email', 'content']
    raw_id_fields = ['post', 'author', 'parent']


@admin.register(PostReport)
class PostReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'post', 'reported_by', 'reason', 'created_at']
    list_filter = ['reason']
    raw_id_fields = ['post', 'reported_by']


@admin.register(PostSave)
class PostSaveAdmin(admin.ModelAdmin):
    list_display = ['id', 'post', 'user', 'created_at']
    raw_id_fields = ['post', 'user']
