from rest_framework import serializers
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Avg, Count

from .models import Session, Booking, SessionReview, SessionSlot

User = get_user_model()


# ── Nested host serializer ────────────────────────────────────────────────────

class SessionHostSerializer(serializers.ModelSerializer):
    profile_pic = serializers.SerializerMethodField()
    role_detail = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'role', 'profile_pic', 'college',
                  'role_detail', 'average_rating']

    def get_profile_pic(self, obj):
        if obj.profile_pic:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.profile_pic.url)
            return obj.profile_pic.url
        return None

    def get_role_detail(self, obj):
        if obj.role == 'alumni':
            try:
                p = obj.alumni_profile
                return {'company': p.company, 'designation': p.designation}
            except Exception:
                return {}
        elif obj.role == 'faculty':
            try:
                p = obj.faculty_profile
                return {'department': p.department, 'designation': p.designation}
            except Exception:
                return {}
        return {}

    def get_average_rating(self, obj):
        agg = SessionReview.objects.filter(
            booking__session__host=obj
        ).aggregate(avg=Avg('rating'))
        val = agg['avg']
        return round(float(val), 1) if val else None


# ── Review serializer (used inside SessionDetailSerializer) ───────────────────

class SessionReviewSerializer(serializers.ModelSerializer):
    reviewer = serializers.SerializerMethodField()
    booking = serializers.PrimaryKeyRelatedField(queryset=Booking.objects.all())

    class Meta:
        model = SessionReview
        fields = ['id', 'booking', 'rating', 'review_text', 'is_anonymous',
                  'created_at', 'reviewer']
        read_only_fields = ['id', 'created_at', 'reviewer']

    def get_reviewer(self, obj):
        if obj.is_anonymous:
            return {'name': 'Anonymous', 'profile_pic': None}
        u = obj.booking.student
        pic = None
        if u.profile_pic:
            request = self.context.get('request')
            pic = request.build_absolute_uri(u.profile_pic.url) if request else u.profile_pic.url
        return {'id': u.id, 'name': u.full_name, 'profile_pic': pic}

    def validate_rating(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError('Rating must be between 1 and 5.')
        return value

    def validate_booking(self, booking):
        request = self.context.get('request')
        if request and booking.student != request.user:
            raise serializers.ValidationError('You can only review your own bookings.')
        if booking.status != 'completed':
            raise serializers.ValidationError('Can only review completed sessions.')
        if hasattr(booking, 'review'):
            raise serializers.ValidationError('You have already reviewed this session.')
        return booking


# ── Session list serializer ───────────────────────────────────────────────────

class SessionListSerializer(serializers.ModelSerializer):
    host = SessionHostSerializer(read_only=True)
    co_host = SessionHostSerializer(read_only=True)
    available_seats = serializers.IntegerField(read_only=True)
    is_full = serializers.BooleanField(read_only=True)
    is_booked = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()

    class Meta:
        model = Session
        fields = [
            'id', 'host', 'co_host', 'session_type', 'title', 'description',
            'niche', 'skills_covered', 'scheduled_at', 'duration_minutes',
            'price', 'is_free', 'max_seats', 'booked_seats', 'available_seats',
            'is_full', 'status', 'thumbnail', 'tags', 'total_sessions_in_bundle',
            'created_at', 'is_booked', 'average_rating', 'review_count',
        ]

    def get_description(self, obj):
        return obj.description[:200] if len(obj.description) > 200 else obj.description

    def get_is_booked(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return Booking.objects.filter(
            session=obj,
            student=request.user,
            status__in=['confirmed', 'completed'],
        ).exists()

    def get_average_rating(self, obj):
        agg = SessionReview.objects.filter(booking__session=obj).aggregate(avg=Avg('rating'))
        val = agg['avg']
        return round(float(val), 1) if val else None

    def get_review_count(self, obj):
        return SessionReview.objects.filter(booking__session=obj).count()


# ── Session detail serializer ─────────────────────────────────────────────────

class SessionDetailSerializer(SessionListSerializer):
    description = serializers.CharField()  # full, not truncated
    reviews = serializers.SerializerMethodField()
    meeting_link = serializers.SerializerMethodField()
    recording_url = serializers.SerializerMethodField()

    class Meta(SessionListSerializer.Meta):
        fields = SessionListSerializer.Meta.fields + [
            'meeting_link', 'recording_url', 'reviews',
            'total_revenue', 'platform_earned', 'host_earned',
            'cancellation_reason',
        ]

    def get_meeting_link(self, obj):
        request = self.context.get('request')
        if not request:
            return ''
        has_confirmed = Booking.objects.filter(
            session=obj, student=request.user, status__in=['confirmed', 'completed']
        ).exists()
        return obj.meeting_link if has_confirmed else ''

    def get_recording_url(self, obj):
        request = self.context.get('request')
        if not request:
            return ''
        has_confirmed = Booking.objects.filter(
            session=obj, student=request.user, status__in=['confirmed', 'completed']
        ).exists()
        return obj.recording_url if has_confirmed else ''

    def get_reviews(self, obj):
        reviews = SessionReview.objects.filter(
            booking__session=obj
        ).select_related('booking__student').order_by('-created_at')[:5]
        return SessionReviewSerializer(reviews, many=True, context=self.context).data


# ── Session create serializer ─────────────────────────────────────────────────

class SessionCreateSerializer(serializers.ModelSerializer):
    co_host = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role__in=['alumni', 'faculty'], is_verified=True),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Session
        fields = [
            'session_type', 'title', 'description', 'niche', 'skills_covered',
            'scheduled_at', 'duration_minutes', 'price', 'is_free',
            'is_demo_eligible', 'max_seats', 'total_sessions_in_bundle',
            'thumbnail', 'tags', 'co_host',
        ]

    def validate_scheduled_at(self, value):
        if self.instance is not None:
            # On partial update, only validate if scheduled_at is actually being changed
            if self.instance.scheduled_at == value:
                return value
        if value <= timezone.now() + __import__('datetime').timedelta(hours=1):
            raise serializers.ValidationError(
                'Session must be scheduled at least 1 hour in the future.'
            )
        return value

    def validate(self, data):
        # Only validate price if it's being set in this request
        if 'price' in data or 'is_free' in data:
            is_free = data.get('is_free', getattr(self.instance, 'is_free', False) if self.instance else False)
            if not is_free:
                price = data.get('price', getattr(self.instance, 'price', 0) if self.instance else 0)
                if not price or float(price) <= 0:
                    raise serializers.ValidationError(
                        {'price': 'Price must be greater than 0 for paid sessions.'}
                    )
        return data

    def validate_co_host(self, value):
        if value and value.role not in ('alumni', 'faculty'):
            raise serializers.ValidationError(
                'Co-host must be a verified alumni or faculty user.'
            )
        return value


# ── Booking serializers ───────────────────────────────────────────────────────

class BookingSerializer(serializers.ModelSerializer):
    session = SessionListSerializer(read_only=True)
    student = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            'id', 'session', 'student', 'status', 'amount_paid', 'is_free_demo',
            'platform_cut', 'host_share', 'razorpay_order_id', 'razorpay_payment_id',
            'refund_amount', 'booked_at', 'updated_at',
        ]

    def get_student(self, obj):
        u = obj.student
        pic = None
        if u.profile_pic:
            request = self.context.get('request')
            pic = request.build_absolute_uri(u.profile_pic.url) if request else u.profile_pic.url
        return {'id': u.id, 'full_name': u.full_name, 'email': u.email, 'profile_pic': pic}


class BookingCreateSerializer(serializers.Serializer):
    session = serializers.PrimaryKeyRelatedField(queryset=Session.objects.all())
    use_free_demo = serializers.BooleanField(default=False)

    def validate(self, data):
        session = data['session']
        request = self.context['request']
        student = request.user

        if session.status != 'upcoming':
            raise serializers.ValidationError('This session is not available for booking.')

        if session.is_full:
            raise serializers.ValidationError('This session is fully booked.')

        if Booking.objects.filter(
            session=session, student=student,
            status__in=['pending_payment', 'confirmed']
        ).exists():
            raise serializers.ValidationError('You already have a booking for this session.')

        if data.get('use_free_demo'):
            if not session.is_demo_eligible:
                raise serializers.ValidationError('This session is not eligible for free demo.')
            try:
                profile = student.student_profile
                if profile.demo_session_used:
                    raise serializers.ValidationError(
                        'You have already used your free demo session.'
                    )
            except Exception:
                raise serializers.ValidationError('Student profile not found.')

        return data
