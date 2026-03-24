from django.db import models
from django.conf import settings
from taggit.managers import TaggableManager


class Post(models.Model):
    POST_TYPES = [
        ('job', 'Job Opportunity'),
        ('referral', 'Job Referral'),
        ('session', 'Mentorship Session'),
        ('ad', 'Advertisement'),
        ('announcement', 'Announcement'),
        ('general', 'General Post'),
    ]
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('hidden', 'Hidden by Admin'),
        ('deleted', 'Deleted'),
        ('flagged', 'Flagged for Review'),
    ]

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='posts'
    )
    post_type = models.CharField(max_length=20, choices=POST_TYPES, default='general')
    title = models.CharField(max_length=300, blank=True)
    content = models.TextField()
    image = models.ImageField(upload_to='posts/images/', blank=True, null=True)
    tags = TaggableManager(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')

    # Job / referral fields
    company_name = models.CharField(max_length=200, blank=True)
    job_role = models.CharField(max_length=200, blank=True)
    location = models.CharField(max_length=200, blank=True)
    salary_range = models.CharField(max_length=100, blank=True)
    required_skills = models.JSONField(default=list, blank=True)
    apply_link = models.URLField(blank=True)

    # Session fields
    session_date = models.DateTimeField(null=True, blank=True)
    session_price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    session_duration = models.IntegerField(null=True, blank=True)  # minutes
    max_seats = models.IntegerField(null=True, blank=True)

    # Cached engagement counts
    likes_count = models.IntegerField(default=0)
    comments_count = models.IntegerField(default=0)

    # Moderation
    admin_note = models.TextField(blank=True)
    flagged_count = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['author', 'status']),
            models.Index(fields=['post_type', 'status']),
        ]

    def __str__(self):
        return f"{self.author.email} — {self.post_type} — {self.created_at.date()}"


class PostLike(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='liked_posts'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('post', 'user')
        ordering = ['-created_at']


class PostComment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comments'
    )
    content = models.TextField()
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies'
    )
    is_deleted = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']


class PostReport(models.Model):
    REASONS = [
        ('spam', 'Spam'),
        ('inappropriate', 'Inappropriate Content'),
        ('misleading', 'Misleading Information'),
        ('harassment', 'Harassment'),
        ('other', 'Other'),
    ]
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='reports')
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reported_posts'
    )
    reason = models.CharField(max_length=20, choices=REASONS)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('post', 'reported_by')


class PostSave(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='saves')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='saved_posts'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('post', 'user')
