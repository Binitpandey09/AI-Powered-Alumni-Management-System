from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta
from .models import SessionRating, ReferralRating, UserRatingAggregate

class SubmitSessionRatingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from apps.sessions_app.models import Booking

        booking_id = request.data.get('booking_id')
        if not booking_id:
            return Response({'error': 'booking_id is required.'}, status=400)

        booking = get_object_or_404(Booking, pk=booking_id)

        # Verify the rater is part of this booking
        is_student = booking.student == request.user
        is_host = booking.session.host == request.user

        if not is_student and not is_host:
            return Response({'error': 'You are not part of this booking.'}, status=403)

        # Booking must be completed
        if booking.status != 'completed':
            return Response({'error': 'You can only rate completed sessions.'}, status=400)

        # Check 14-day window
        if booking.session.scheduled_at:
            days_since = (timezone.now() - booking.session.scheduled_at).days
            if days_since > 14:
                return Response({'error': 'Rating window has closed (14 days after session).'}, status=400)

        # Check if already rated
        if SessionRating.objects.filter(booking=booking, rater=request.user).exists():
            # Allow edit within 48 hours
            existing = SessionRating.objects.get(booking=booking, rater=request.user)
            if not existing.can_edit:
                return Response({'error': 'You have already rated this session. Edits are only allowed within 48 hours.'}, status=400)
            # Update existing rating
            return self._update_rating(request, existing, is_student)

        # Determine rating direction
        if is_student:
            ratee = booking.session.host
            rating_type = 'student_to_host'
        else:
            ratee = booking.student
            rating_type = 'host_to_student'

        # Validate required field
        overall = request.data.get('overall_rating')
        if not overall or int(overall) not in [1, 2, 3, 4, 5]:
            return Response({'error': 'overall_rating is required and must be 1-5.'}, status=400)

        rating_data = {
            'booking': booking,
            'rater': request.user,
            'ratee': ratee,
            'rating_type': rating_type,
            'overall_rating': int(overall),
        }

        if is_student:
            # Student rating the host
            for field in ['communication_rating', 'value_rating', 'professionalism_rating']:
                val = request.data.get(field)
                if val and int(val) in [1, 2, 3, 4, 5]:
                    rating_data[field] = int(val)
            would_recommend = request.data.get('would_recommend')
            if would_recommend is not None:
                rating_data['would_recommend'] = str(would_recommend).lower() in ['true', '1', 'yes']
            rating_data['review_text'] = request.data.get('review_text', '')[:300]
        else:
            # Host rating the student
            for field in ['preparation_rating', 'engagement_rating', 'punctuality_rating']:
                val = request.data.get(field)
                if val and int(val) in [1, 2, 3, 4, 5]:
                    rating_data[field] = int(val)
            rating_data['feedback_text'] = request.data.get('feedback_text', '')[:200]

        rating = SessionRating.objects.create(**rating_data)

        return Response({
            'message': 'Rating submitted successfully!',
            'rating_id': rating.id,
            'overall_rating': rating.overall_rating,
        }, status=201)

    def _update_rating(self, request, rating, is_student):
        overall = request.data.get('overall_rating')
        if overall and int(overall) in [1, 2, 3, 4, 5]:
            rating.overall_rating = int(overall)

        if is_student:
            for field in ['communication_rating', 'value_rating', 'professionalism_rating']:
                val = request.data.get(field)
                if val and int(val) in [1, 2, 3, 4, 5]:
                    setattr(rating, field, int(val))
            would_recommend = request.data.get('would_recommend')
            if would_recommend is not None:
                rating.would_recommend = str(would_recommend).lower() in ['true', '1', 'yes']
            review_text = request.data.get('review_text')
            if review_text is not None:
                rating.review_text = review_text[:300]
        else:
            for field in ['preparation_rating', 'engagement_rating', 'punctuality_rating']:
                val = request.data.get(field)
                if val and int(val) in [1, 2, 3, 4, 5]:
                    setattr(rating, field, int(val))
            feedback_text = request.data.get('feedback_text')
            if feedback_text is not None:
                rating.feedback_text = feedback_text[:200]

        rating.is_edited = True
        rating.edited_at = timezone.now()
        rating.save()

        return Response({
            'message': 'Rating updated successfully!',
            'rating_id': rating.id,
        })

class SubmitReferralRatingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != 'student':
            return Response({'error': 'Only students can rate referrals.'}, status=403)

        from apps.referrals.models import ReferralApplication
        application_id = request.data.get('application_id')
        if not application_id:
            return Response({'error': 'application_id is required.'}, status=400)

        application = get_object_or_404(
            ReferralApplication,
            pk=application_id,
            student=request.user
        )

        # Can only rate if shortlisted or hired
        if application.status not in ['shortlisted', 'interview_scheduled', 'hired']:
            return Response({'error': 'You can only rate after being shortlisted or hired.'}, status=400)

        # Check already rated
        if ReferralRating.objects.filter(application=application).exists():
            return Response({'error': 'You have already rated this referral.'}, status=400)

        overall = request.data.get('overall_rating')
        if not overall or int(overall) not in [1, 2, 3, 4, 5]:
            return Response({'error': 'overall_rating is required and must be 1-5.'}, status=400)

        rating = ReferralRating.objects.create(
            application=application,
            rater=request.user,
            ratee=application.referral.posted_by,
            overall_rating=int(overall),
            process_rating=int(request.data.get('process_rating', 0)) or None,
            communication_rating=int(request.data.get('communication_rating', 0)) or None,
            review_text=request.data.get('review_text', '')[:300],
        )

        return Response({
            'message': 'Referral rating submitted!',
            'rating_id': rating.id,
        }, status=201)

class UserRatingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = get_object_or_404(User, pk=user_id)

        try:
            agg = user.rating_aggregate
        except UserRatingAggregate.DoesNotExist:
            agg = None

        # Public session reviews (student_to_host, with review text)
        public_reviews = SessionRating.objects.filter(
            ratee=user,
            rating_type='student_to_host',
        ).exclude(review_text='').select_related('rater').order_by('-created_at')[:10]

        reviews_data = [{
            'rating_id': r.id,
            'rater_name': f"{r.rater.first_name} {r.rater.last_name}".strip(),
            'rater_initials': ((r.rater.first_name or '')[0] + (r.rater.last_name or '')[0]).upper(),
            'overall_rating': r.overall_rating,
            'communication_rating': r.communication_rating,
            'value_rating': r.value_rating,
            'professionalism_rating': r.professionalism_rating,
            'would_recommend': r.would_recommend,
            'review_text': r.review_text,
            'session_title': r.booking.session.title,
            'created_at': r.created_at.isoformat(),
            'time_ago': _time_ago(r.created_at),
            'is_edited': r.is_edited,
        } for r in public_reviews]

        # Referral reviews
        referral_reviews = ReferralRating.objects.filter(
            ratee=user
        ).exclude(review_text='').select_related('rater').order_by('-created_at')[:5]

        referral_reviews_data = [{
            'rater_name': f"{r.rater.first_name} {r.rater.last_name}".strip(),
            'rater_initials': ((r.rater.first_name or '')[0] + (r.rater.last_name or '')[0]).upper(),
            'overall_rating': r.overall_rating,
            'review_text': r.review_text,
            'created_at': r.created_at.isoformat(),
        } for r in referral_reviews]

        # Only show ratings if minimum 3 exist
        show_ratings = (agg and agg.host_total_ratings >= 3) if agg else False

        return Response({
            'user_id': user_id,
            'show_ratings': show_ratings,
            'has_enough_ratings': show_ratings,
            'summary': {
                'average_overall': float(agg.host_average_overall) if agg else 0,
                'total_ratings': agg.host_total_ratings if agg else 0,
                'average_communication': float(agg.host_average_communication) if agg else 0,
                'average_value': float(agg.host_average_value) if agg else 0,
                'average_professionalism': float(agg.host_average_professionalism) if agg else 0,
                'would_recommend_pct': agg.host_would_recommend_pct if agg else 0,
                'distribution': {
                    '5': agg.host_five_star if agg else 0,
                    '4': agg.host_four_star if agg else 0,
                    '3': agg.host_three_star if agg else 0,
                    '2': agg.host_two_star if agg else 0,
                    '1': agg.host_one_star if agg else 0,
                },
            },
            'referral_rating': {
                'average': float(agg.referral_average_overall) if agg else 0,
                'total': agg.referral_total_ratings if agg else 0,
            },
            'recent_reviews': reviews_data,
            'referral_reviews': referral_reviews_data,
        })

class MyRatingView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, booking_id):
        existing = SessionRating.objects.filter(
            booking_id=booking_id,
            rater=request.user
        ).first()

        if existing:
            return Response({
                'has_rated': True,
                'rating_id': existing.id,
                'overall_rating': existing.overall_rating,
                'can_edit': existing.can_edit,
                'review_text': existing.review_text if existing.rating_type == 'student_to_host' else None,
            })
        return Response({'has_rated': False})

class PendingRatingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.sessions_app.models import Booking
        from apps.referrals.models import ReferralApplication

        pending = []
        window = timezone.now() - timedelta(days=14)

        if request.user.role == 'student':
            # Completed bookings not yet rated by student
            completed_bookings = Booking.objects.filter(
                student=request.user,
                status='completed',
                session__scheduled_at__gte=window
            ).select_related('session', 'session__host')

            rated_booking_ids = set(
                SessionRating.objects.filter(
                    rater=request.user,
                    rating_type='student_to_host'
                ).values_list('booking_id', flat=True)
            )

            for b in completed_bookings:
                if b.id not in rated_booking_ids:
                    pending.append({
                        'type': 'session',
                        'booking_id': b.id,
                        'session_id': b.session.id,
                        'title': f"Rate your session: {b.session.title}",
                        'subtitle': f"With {b.session.host.first_name} {b.session.host.last_name}",
                        'date': b.session.scheduled_at.isoformat(),
                        'days_remaining': max(0, 14 - (timezone.now() - b.session.scheduled_at).days),
                    })

            # Referral applications shortlisted/hired but not yet rated
            eligible_apps = ReferralApplication.objects.filter(
                student=request.user,
                status__in=['shortlisted', 'interview_scheduled', 'hired']
            ).select_related('referral', 'referral__posted_by').exclude(
                rating__isnull=False
            )
            for a in eligible_apps:
                pending.append({
                    'type': 'referral',
                    'application_id': a.id,
                    'title': f"Rate referral: {a.referral.job_title} at {a.referral.company_name}",
                    'subtitle': f"Posted by {a.referral.posted_by.first_name} {a.referral.posted_by.last_name}",
                    'status': a.status,
                })

        else:
            # Host: completed sessions not yet rated by host
            completed_as_host = Booking.objects.filter(
                session__host=request.user,
                status='completed',
                session__scheduled_at__gte=window
            ).select_related('student', 'session')

            rated_booking_ids = set(
                SessionRating.objects.filter(
                    rater=request.user,
                    rating_type='host_to_student'
                ).values_list('booking_id', flat=True)
            )

            for b in completed_as_host:
                if b.id not in rated_booking_ids:
                    pending.append({
                        'type': 'session',
                        'booking_id': b.id,
                        'session_id': b.session.id,
                        'title': f"Rate student: {b.student.first_name} {b.student.last_name}",
                        'subtitle': f"Session: {b.session.title}",
                        'date': b.session.scheduled_at.isoformat(),
                        'days_remaining': max(0, 14 - (timezone.now() - b.session.scheduled_at).days),
                    })

        return Response({'pending_ratings': pending, 'count': len(pending)})

def _time_ago(dt):
    from django.utils import timezone as tz
    diff = tz.now() - dt
    s = int(diff.total_seconds())
    if s < 3600: return f"{s//60}m ago"
    if s < 86400: return f"{s//3600}h ago"
    if s < 604800: return f"{s//86400}d ago"
    return dt.strftime('%d %b %Y')
