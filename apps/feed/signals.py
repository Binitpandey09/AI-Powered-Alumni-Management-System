from django.db.models import F
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Post, PostLike, PostComment, PostReport


@receiver(post_save, sender=PostLike)
def increment_likes_count(sender, instance, created, **kwargs):
    if created:
        Post.objects.filter(pk=instance.post_id).update(likes_count=F('likes_count') + 1)


@receiver(post_delete, sender=PostLike)
def decrement_likes_count(sender, instance, **kwargs):
    Post.objects.filter(pk=instance.post_id).update(likes_count=F('likes_count') - 1)


@receiver(post_save, sender=PostComment)
def increment_comments_count(sender, instance, created, **kwargs):
    # Only top-level comments (no parent) count toward the cached total
    if created and not instance.parent_id:
        Post.objects.filter(pk=instance.post_id).update(comments_count=F('comments_count') + 1)


@receiver(post_save, sender=PostReport)
def handle_post_report(sender, instance, created, **kwargs):
    if created:
        # Increment flagged_count; auto-flag if threshold reached
        updated = Post.objects.filter(pk=instance.post_id).update(
            flagged_count=F('flagged_count') + 1
        )
        # Re-fetch to check threshold
        post = Post.objects.get(pk=instance.post_id)
        if post.flagged_count >= 3 and post.status == 'active':
            Post.objects.filter(pk=instance.post_id).update(status='flagged')
