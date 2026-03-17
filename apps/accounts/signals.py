from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

User = get_user_model()


@receiver(post_save, sender=User)
def create_role_profile(sender, instance, created, **kwargs):
    """
    Auto-create the correct profile model based on user.role
    immediately after a new User is created.
    """
    if not created:
        return

    from .models import AlumniProfile, StudentProfile, FacultyProfile

    if instance.role == User.ALUMNI:
        AlumniProfile.objects.get_or_create(user=instance)
    elif instance.role == User.STUDENT:
        StudentProfile.objects.get_or_create(user=instance)
    elif instance.role == User.FACULTY:
        FacultyProfile.objects.get_or_create(user=instance)
    # ADMIN role gets no profile model
