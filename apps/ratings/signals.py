from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db.models import Avg, Count
from decimal import Decimal

@receiver(post_save, sender='ratings.SessionRating')
def update_rating_aggregate_on_session_rating(sender, instance, created, **kwargs):
    """
    Recalculates UserRatingAggregate for the ratee whenever
    a new SessionRating is created or updated.
    """
    _recalculate_aggregate(instance.ratee)

@receiver(post_save, sender='ratings.ReferralRating')
def update_rating_aggregate_on_referral_rating(sender, instance, created, **kwargs):
    _recalculate_aggregate(instance.ratee)

def _recalculate_aggregate(user):
    from apps.ratings.models import SessionRating, ReferralRating, UserRatingAggregate
    from django.db.models import Avg, Count, Q

    agg, _ = UserRatingAggregate.objects.get_or_create(user=user)

    # ── HOST RATINGS (student_to_host) ──
    host_ratings = SessionRating.objects.filter(
        ratee=user,
        rating_type='student_to_host'
    )
    host_count = host_ratings.count()
    agg.host_total_ratings = host_count

    if host_count > 0:
        avgs = host_ratings.aggregate(
            avg_overall=Avg('overall_rating'),
            avg_comm=Avg('communication_rating'),
            avg_value=Avg('value_rating'),
            avg_prof=Avg('professionalism_rating'),
        )
        agg.host_average_overall = round(avgs['avg_overall'] or 0, 2)
        agg.host_average_communication = round(avgs['avg_comm'] or 0, 2)
        agg.host_average_value = round(avgs['avg_value'] or 0, 2)
        agg.host_average_professionalism = round(avgs['avg_prof'] or 0, 2)

        # Would recommend percentage
        recommend_count = host_ratings.filter(would_recommend=True).count()
        agg.host_would_recommend_pct = round((recommend_count / host_count) * 100)

        # Distribution
        agg.host_five_star = host_ratings.filter(overall_rating=5).count()
        agg.host_four_star = host_ratings.filter(overall_rating=4).count()
        agg.host_three_star = host_ratings.filter(overall_rating=3).count()
        agg.host_two_star = host_ratings.filter(overall_rating=2).count()
        agg.host_one_star = host_ratings.filter(overall_rating=1).count()

        # Update profile model wallet field (keep profile in sync)
        try:
            if user.role == 'alumni':
                from apps.accounts.models import AlumniProfile
                AlumniProfile.objects.filter(user=user).update(
                    average_rating=agg.host_average_overall,
                    total_ratings=agg.host_total_ratings
                )
            elif user.role == 'faculty':
                from apps.accounts.models import FacultyProfile
                FacultyProfile.objects.filter(user=user).update(
                    average_rating=agg.host_average_overall,
                    total_ratings=agg.host_total_ratings
                )
        except Exception:
            pass

    # ── STUDENT RATINGS (host_to_student) ──
    student_ratings = SessionRating.objects.filter(
        ratee=user,
        rating_type='host_to_student'
    )
    agg.student_total_ratings = student_ratings.count()
    if agg.student_total_ratings > 0:
        agg.student_average_overall = round(
            student_ratings.aggregate(avg=Avg('overall_rating'))['avg'] or 0, 2
        )

    # ── REFERRAL RATINGS ──
    ref_ratings = ReferralRating.objects.filter(ratee=user)
    agg.referral_total_ratings = ref_ratings.count()
    if agg.referral_total_ratings > 0:
        agg.referral_average_overall = round(
            ref_ratings.aggregate(avg=Avg('overall_rating'))['avg'] or 0, 2
        )

    agg.save()
