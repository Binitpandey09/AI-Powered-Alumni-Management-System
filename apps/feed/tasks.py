from celery import shared_task
from django.utils import timezone


@shared_task(name='apps.feed.tasks.expire_old_posts')
def expire_old_posts():
    """Mark posts as expired when their expires_at datetime has passed."""
    from .models import Post
    now = timezone.now()
    count = Post.objects.filter(
        status='active',
        expires_at__isnull=False,
        expires_at__lt=now,
    ).update(status='expired')
    return f'Expired {count} post(s)'
