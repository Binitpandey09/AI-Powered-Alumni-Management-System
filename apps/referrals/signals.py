from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db.models import F

_application_previous_status = {}


@receiver(pre_save, sender='referrals.ReferralApplication')
def store_previous_application_status(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            _application_previous_status[instance.pk] = old.status
        except sender.DoesNotExist:
            pass


@receiver(post_save, sender='referrals.ReferralApplication')
def handle_application_status_change(sender, instance, created, **kwargs):
    from apps.referrals.models import Referral

    prev_status = _application_previous_status.pop(instance.pk, None)
    current_status = instance.status

    # ── NEW APPLICATION CREATED ──
    if created:
        Referral.objects.filter(pk=instance.referral.pk).update(
            total_applications=F('total_applications') + 1
        )
        instance.referral.refresh_from_db()
        if instance.referral.is_full:
            Referral.objects.filter(pk=instance.referral.pk).update(status='closed')

        try:
            from utils.notify import send_notification
            student_name = f"{instance.student.first_name} {instance.student.last_name}".strip()
            send_notification(
                user=instance.referral.posted_by,
                notif_type='referral_applied',
                title='New referral application',
                message=(
                    f'{student_name} applied to your referral: '
                    f'"{instance.referral.job_title} @ {instance.referral.company_name}". '
                    f'Match score: {instance.match_score}%'
                ),
                link=f'/referrals/{instance.referral.pk}/applications/',
            )
        except Exception:
            pass

    # ── STATUS CHANGED ──
    elif prev_status and prev_status != current_status:
        status_messages = {
            'shortlisted': (
                f'Congratulations! You have been shortlisted for '
                f'"{instance.referral.job_title} @ {instance.referral.company_name}".'
            ),
            'interview_scheduled': (
                f'Interview scheduled for '
                f'"{instance.referral.job_title} @ {instance.referral.company_name}". '
                f'Check your application for details.'
            ),
            'rejected': (
                f'Your application for '
                f'"{instance.referral.job_title} @ {instance.referral.company_name}" '
                f'was not selected this time. Keep applying!'
            ),
            'hired': (
                f'Congratulations! You have been selected for '
                f'"{instance.referral.job_title} @ {instance.referral.company_name}". '
                f'Best of luck!'
            ),
        }
        if current_status in status_messages:
            try:
                from utils.notify import send_notification
                send_notification(
                    user=instance.student,
                    notif_type='referral',
                    title=f'Application update: {current_status.replace("_", " ").title()}',
                    message=status_messages[current_status],
                    link='/referrals/my-applications/',
                )
            except Exception:
                pass

        # ── HIRED — create success story + update impact score ──
        if current_status == 'hired' and prev_status != 'hired':
            try:
                from apps.referrals.models import ReferralSuccessStory
                ReferralSuccessStory.objects.get_or_create(
                    application=instance,
                    defaults={
                        'student': instance.student,
                        'alumni': instance.referral.posted_by,
                        'company_name': instance.referral.company_name,
                        'job_title': instance.referral.job_title,
                        'is_public': True,
                    },
                )
                alumni = instance.referral.posted_by
                if alumni.role == 'alumni':
                    from apps.accounts.models import AlumniProfile
                    AlumniProfile.objects.filter(user=alumni).update(
                        impact_score=F('impact_score') + 5
                    )
            except Exception:
                pass

    # ── WITHDRAWN — decrement count and re-open if needed ──
    if current_status == 'withdrawn' and prev_status not in ('withdrawn', None):
        Referral.objects.filter(pk=instance.referral.pk).update(
            total_applications=F('total_applications') - 1
        )
        instance.referral.refresh_from_db()
        if instance.referral.status == 'closed' and not instance.referral.is_full:
            Referral.objects.filter(pk=instance.referral.pk).update(status='active')


@receiver(post_save, sender='referrals.FacultyReferralRecommendation')
def notify_alumni_of_faculty_recommendation(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        from utils.notify import send_notification
        faculty_name = f"{instance.faculty.first_name} {instance.faculty.last_name}".strip()
        student_name = f"{instance.student.first_name} {instance.student.last_name}".strip()
        send_notification(
            user=instance.referral.posted_by,
            notif_type='referral',
            title='Faculty recommendation received',
            message=(
                f'{faculty_name} recommends {student_name} for your referral '
                f'"{instance.referral.job_title} @ {instance.referral.company_name}".'
            ),
            link=f'/referrals/{instance.referral.pk}/applications/',
        )
    except Exception:
        pass
