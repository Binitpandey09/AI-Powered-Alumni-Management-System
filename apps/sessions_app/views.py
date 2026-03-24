from django.conf import settings
from django.utils import timezone
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

try:
    import razorpay
except ImportError:
    razorpay = None

from .models import Session, Booking, SessionReview, SessionSlot
from .serializers import (
    SessionListSerializer,
    SessionDetailSerializer,
    SessionCreateSerializer,
    BookingSerializer,
    BookingCreateSerializer,
    SessionReviewSerializer,
)
from utils.permissions import CanHostSession, IsSessionHostOrAdmin, IsBookingOwner


# ── Session List + Create ─────────────────────────────────────────────────────

class SessionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Session.objects.select_related('host', 'co_host').all()

        # Filters
        session_type = request.query_params.get('type')
        if session_type:
            qs = qs.filter(session_type=session_type)

        host_id = request.query_params.get('host')
        if host_id:
            qs = qs.filter(host__id=host_id)

        niche = request.query_params.get('niche')
        if niche:
            qs = qs.filter(niche__icontains=niche)

        skill = request.query_params.get('skill')
        if skill:
            # JSONField contains check
            qs = qs.filter(skills_covered__icontains=skill)

        price_max = request.query_params.get('price_max')
        if price_max:
            try:
                qs = qs.filter(price__lte=float(price_max))
            except ValueError:
                pass

        if request.query_params.get('free', '').lower() == 'true':
            qs = qs.filter(is_free=True)

        search = request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(niche__icontains=search)
            )

        if request.query_params.get('my_sessions', '').lower() == 'true':
            qs = qs.filter(host=request.user)
        else:
            qs = qs.filter(status='upcoming')

        # Pagination
        page = max(int(request.query_params.get('page', 1)), 1)
        page_size = 12
        total = qs.count()
        start = (page - 1) * page_size
        sessions = qs[start:start + page_size]

        serializer = SessionListSerializer(sessions, many=True, context={'request': request})
        return Response({
            'results': serializer.data,
            'count': total,
            'total': total,
            'page': page,
            'has_next': (start + page_size) < total,
        })

    def post(self, request):
        # Enforce host permission manually (CanHostSession checks SAFE_METHODS)
        if request.user.role not in ('alumni', 'faculty'):
            return Response(
                {'error': 'Only alumni and faculty can create sessions.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = SessionCreateSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        session = serializer.save(host=request.user)

        # Schedule celery tasks
        try:
            from .tasks import schedule_session_tasks
            schedule_session_tasks.delay(session.id)
        except Exception:
            pass

        return Response(
            SessionDetailSerializer(session, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


# ── Session Detail + Edit + Cancel ───────────────────────────────────────────

class SessionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_session(self, pk):
        try:
            return Session.objects.select_related('host', 'co_host').get(pk=pk)
        except Session.DoesNotExist:
            return None

    def get(self, request, pk):
        session = self._get_session(pk)
        if not session:
            return Response({'error': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(SessionDetailSerializer(session, context={'request': request}).data)

    def patch(self, request, pk):
        session = self._get_session(pk)
        if not session:
            return Response({'error': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Check host permission
        if session.host != request.user and request.user.role != 'admin':
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

        allowed_fields = {
            'title', 'description', 'niche', 'skills_covered', 'scheduled_at',
            'duration_minutes', 'price', 'max_seats', 'thumbnail', 'tags', 'meeting_link',
        }
        data = {k: v for k, v in request.data.items() if k in allowed_fields}

        serializer = SessionCreateSerializer(session, data=data, partial=True, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        return Response(SessionDetailSerializer(session, context={'request': request}).data)

    def delete(self, request, pk):
        session = self._get_session(pk)
        if not session:
            return Response({'error': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

        if session.host != request.user and request.user.role != 'admin':
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

        reason = request.data.get('cancellation_reason', '')
        session.status = 'cancelled'
        session.cancellation_reason = reason
        session.save(update_fields=['status', 'cancellation_reason'])

        # Cancel all confirmed bookings — signal handles wallet reversal + notifications
        confirmed_bookings = Booking.objects.filter(session=session, status='confirmed')
        for booking in confirmed_bookings:
            booking.status = 'cancelled_by_host'
            booking.save(update_fields=['status'])

        return Response({'message': 'Session cancelled. All students will be notified.'})


# ── Book a Session ────────────────────────────────────────────────────────────

class SessionBookingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            session = Session.objects.get(pk=pk)
        except Session.DoesNotExist:
            return Response({'error': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

        data = {'session': pk, 'use_free_demo': request.data.get('use_free_demo', False)}
        serializer = BookingCreateSerializer(data=data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        student = request.user
        use_free_demo = serializer.validated_data.get('use_free_demo', False)

        # Determine if this is a free demo booking
        is_free_demo = use_free_demo and session.is_demo_eligible

        if is_free_demo or session.is_free:
            booking = Booking.objects.create(
                session=session,
                student=student,
                status='confirmed',
                amount_paid=0,
                is_free_demo=is_free_demo,
            )
            if is_free_demo:
                try:
                    profile = student.student_profile
                    profile.demo_session_used = True
                    profile.save(update_fields=['demo_session_used'])
                except Exception:
                    pass

            return Response({
                'booking_confirmed': True,
                'is_free_demo': is_free_demo,
                'booking_id': booking.id,
                'message': 'Free demo session booked!' if is_free_demo else 'Free session booked!',
            }, status=status.HTTP_201_CREATED)

        # Paid booking — create Razorpay order
        try:
            client = razorpay.Client(
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
            )
            amount_paise = int(float(session.price) * 100)
            order = client.order.create({
                'amount': amount_paise,
                'currency': 'INR',
                'receipt': f'session_{session.id}_{student.id}',
            })
        except Exception as e:
            return Response(
                {'error': f'Payment gateway error: {str(e)}'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        booking = Booking.objects.create(
            session=session,
            student=student,
            status='pending_payment',
            amount_paid=session.price,
            razorpay_order_id=order['id'],
        )

        return Response({
            'booking_id': booking.id,
            'razorpay_order_id': order['id'],
            'razorpay_key_id': settings.RAZORPAY_KEY_ID,
            'amount': str(session.price),
            'currency': 'INR',
            'session_title': session.title,
            'student_name': student.full_name,
            'student_email': student.email,
        }, status=status.HTTP_201_CREATED)


# ── Payment Verification ──────────────────────────────────────────────────────

class PaymentVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        razorpay_order_id = request.data.get('razorpay_order_id', '')
        razorpay_payment_id = request.data.get('razorpay_payment_id', '')
        razorpay_signature = request.data.get('razorpay_signature', '')
        booking_id = request.data.get('booking_id')

        if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature, booking_id]):
            return Response(
                {'error': 'razorpay_order_id, razorpay_payment_id, razorpay_signature and booking_id are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            booking = Booking.objects.select_related('session').get(
                pk=booking_id, student=request.user
            )
        except Booking.DoesNotExist:
            return Response({'error': 'Booking not found.'}, status=status.HTTP_404_NOT_FOUND)

        if booking.status != 'pending_payment':
            return Response(
                {'error': 'Booking is not in pending_payment state.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verify Razorpay signature
        try:
            client = razorpay.Client(
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
            )
            client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature,
            })
        except Exception:
            return Response(
                {'error': 'Payment verification failed. Invalid signature.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Confirm booking — signal handles wallet + notifications
        booking.status = 'confirmed'
        booking.razorpay_payment_id = razorpay_payment_id
        booking.razorpay_signature = razorpay_signature
        booking.save(update_fields=['status', 'razorpay_payment_id', 'razorpay_signature'])

        return Response({
            'message': 'Payment successful! Booking confirmed.',
            'booking_id': booking.id,
        })


# ── My Bookings ───────────────────────────────────────────────────────────────

class BookingListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Booking.objects.filter(student=request.user).select_related(
            'session', 'session__host'
        )
        filter_status = request.query_params.get('status')
        if filter_status:
            qs = qs.filter(status=filter_status)

        serializer = BookingSerializer(qs, many=True, context={'request': request})
        return Response({'results': serializer.data, 'count': qs.count()})


# ── Cancel Booking ────────────────────────────────────────────────────────────

class BookingCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, booking_id):
        try:
            booking = Booking.objects.select_related('session').get(pk=booking_id)
        except Booking.DoesNotExist:
            return Response({'error': 'Booking not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Object-level permission
        if booking.student != request.user and request.user.role != 'admin':
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

        if booking.status != 'confirmed':
            return Response(
                {'error': 'Only confirmed bookings can be cancelled.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        hours_until = (
            booking.session.scheduled_at - timezone.now()
        ).total_seconds() / 3600

        refund_pct = 0.50 if hours_until > 2 else 0
        refund_amount = round(float(booking.amount_paid) * refund_pct, 2)

        booking.status = 'cancelled_by_student'
        booking.refund_amount = refund_amount
        booking.save(update_fields=['status', 'refund_amount'])

        return Response({
            'message': 'Booking cancelled.',
            'refund_amount': refund_amount,
            'refund_note': '50% refund will be processed.' if refund_pct > 0 else 'No refund — cancelled within 2 hours of session.',
        })


# ── Hosted Sessions ───────────────────────────────────────────────────────────

class HostedSessionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role not in ('alumni', 'faculty'):
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

        qs = Session.objects.filter(host=request.user).order_by('-scheduled_at')

        filter_status = request.query_params.get('status')
        if filter_status:
            qs = qs.filter(status=filter_status)

        serializer = SessionListSerializer(qs, many=True, context={'request': request})
        return Response({'results': serializer.data, 'count': qs.count()})


# ── Session Bookings (host view) ──────────────────────────────────────────────

class SessionBookingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            session = Session.objects.get(pk=pk)
        except Session.DoesNotExist:
            return Response({'error': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

        if session.host != request.user and request.user.role != 'admin':
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

        bookings = Booking.objects.filter(session=session).select_related('student')
        serializer = BookingSerializer(bookings, many=True, context={'request': request})
        return Response(serializer.data)


# ── Add Meeting Link ──────────────────────────────────────────────────────────

class AddMeetingLinkView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            session = Session.objects.get(pk=pk)
        except Session.DoesNotExist:
            return Response({'error': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

        if session.host != request.user and request.user.role != 'admin':
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

        meeting_link = request.data.get('meeting_link', '').strip()
        if not meeting_link:
            return Response({'error': 'meeting_link is required.'}, status=status.HTTP_400_BAD_REQUEST)

        session.meeting_link = meeting_link
        session.save(update_fields=['meeting_link'])

        # Notify all confirmed students
        confirmed_bookings = Booking.objects.filter(
            session=session, status='confirmed'
        ).select_related('student')

        for booking in confirmed_bookings:
            try:
                from apps.notifications.models import Notification
                Notification.objects.create(
                    user=booking.student,
                    title='Meeting Link Added',
                    message=f'The meeting link for "{session.title}" is now available.',
                    notification_type='meeting_link_added',
                    data={'session_id': session.id, 'meeting_link': meeting_link},
                )
            except Exception:
                pass

        return Response({'message': 'Meeting link updated.', 'meeting_link': meeting_link})


# ── Session Reviews ───────────────────────────────────────────────────────────

class SessionReviewView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, booking_id):
        """POST /api/sessions/bookings/<booking_id>/review/"""
        try:
            booking = Booking.objects.select_related('student', 'session').get(pk=booking_id)
        except Booking.DoesNotExist:
            return Response({'error': 'Booking not found.'}, status=status.HTTP_404_NOT_FOUND)

        if booking.student != request.user and request.user.role != 'admin':
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

        data = {**request.data, 'booking': booking_id}
        serializer = SessionReviewSerializer(data=data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        review = serializer.save()
        return Response(
            SessionReviewSerializer(review, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )

    def get(self, request, pk):
        """GET /api/sessions/<pk>/reviews/"""
        try:
            session = Session.objects.get(pk=pk)
        except Session.DoesNotExist:
            return Response({'error': 'Session not found.'}, status=status.HTTP_404_NOT_FOUND)

        reviews = SessionReview.objects.filter(
            booking__session=session
        ).select_related('booking__student').order_by('-created_at')

        serializer = SessionReviewSerializer(reviews, many=True, context={'request': request})

        from django.db.models import Avg
        avg = reviews.aggregate(avg=Avg('rating'))['avg']

        return Response({
            'reviews': serializer.data,
            'average_rating': round(float(avg), 1) if avg else None,
            'review_count': reviews.count(),
        })


# ── Earnings Summary ──────────────────────────────────────────────────────────

class EarningsSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role not in ('alumni', 'faculty'):
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

        from django.db.models import Sum, Count
        from decimal import Decimal

        # All confirmed bookings for sessions hosted by this user
        confirmed_bookings = Booking.objects.filter(
            session__host=user,
            status='confirmed',
        ).select_related('session', 'student')

        total_sessions = Session.objects.filter(host=user).count()
        total_bookings = confirmed_bookings.count()
        gross = confirmed_bookings.aggregate(total=Sum('amount_paid'))['total'] or Decimal('0')
        platform_cut = gross * Decimal('0.30')
        net_earned = gross - platform_cut

        # Get profile wallet balance
        try:
            if user.role == 'alumni':
                profile = user.alumni_profile
            else:
                profile = user.faculty_profile
            wallet_balance = float(profile.wallet_balance)
            bank_verified = profile.bank_verified
        except Exception:
            wallet_balance = 0.0
            bank_verified = False

        # Monthly breakdown (last 6 months)
        from django.utils import timezone as tz
        from datetime import timedelta
        now = tz.now()
        monthly = []
        for i in range(5, -1, -1):
            month_start = (now.replace(day=1) - timedelta(days=i * 30)).replace(
                day=1, hour=0, minute=0, second=0, microsecond=0
            )
            if i > 0:
                month_end = (now.replace(day=1) - timedelta(days=(i - 1) * 30)).replace(
                    day=1, hour=0, minute=0, second=0, microsecond=0
                )
            else:
                month_end = now
            month_bookings = confirmed_bookings.filter(
                session__scheduled_at__gte=month_start,
                session__scheduled_at__lt=month_end,
            )
            month_gross = month_bookings.aggregate(total=Sum('amount_paid'))['total'] or Decimal('0')
            month_net = month_gross * Decimal('0.70')
            monthly.append({
                'label': month_start.strftime('%b %Y'),
                'gross': float(month_gross),
                'net': float(month_net),
                'sessions': month_bookings.values('session').distinct().count(),
            })

        # Recent transactions (last 20 confirmed bookings)
        recent = confirmed_bookings.order_by('-session__scheduled_at')[:20]
        transactions = []
        for b in recent:
            transactions.append({
                'id': b.id,
                'session_title': b.session.title,
                'student_name': b.student.full_name,
                'amount': float(b.amount_paid),
                'net': float(b.amount_paid * Decimal('0.70')),
                'host_share': str(round(b.amount_paid * Decimal('0.70'), 2)),
                'platform_cut': str(round(b.amount_paid * Decimal('0.30'), 2)),
                'date': b.session.scheduled_at.isoformat(),
                'status': b.status,
            })

        # This month / last month earnings
        from django.utils import timezone as tz
        now2 = tz.now()
        this_month_start = now2.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_end = this_month_start
        last_month_start = (this_month_start - timedelta(days=1)).replace(
            day=1, hour=0, minute=0, second=0, microsecond=0
        )
        this_month_gross = confirmed_bookings.filter(
            session__scheduled_at__gte=this_month_start
        ).aggregate(total=Sum('amount_paid'))['total'] or Decimal('0')
        last_month_gross = confirmed_bookings.filter(
            session__scheduled_at__gte=last_month_start,
            session__scheduled_at__lt=last_month_end,
        ).aggregate(total=Sum('amount_paid'))['total'] or Decimal('0')

        # Average session rating
        from django.db.models import Avg
        avg_rating_agg = SessionReview.objects.filter(
            booking__session__host=user
        ).aggregate(avg=Avg('rating'))
        avg_rating = round(float(avg_rating_agg['avg']), 1) if avg_rating_agg['avg'] else None

        # Bank details
        try:
            bank_details_data = dict(profile.bank_details) if profile else {}
            acc = bank_details_data.get('account_number', '')
            if acc and len(acc) > 4:
                bank_details_data['account_number_masked'] = '*' * (len(acc) - 4) + acc[-4:]
            bank_details_data.pop('account_number', None)
        except Exception:
            bank_details_data = {}

        return Response({
            'total_sessions': total_sessions,
            'total_sessions_hosted': total_sessions,
            'total_bookings': total_bookings,
            'gross_earned': float(gross),
            'net_earned': float(net_earned),
            'total_earned': float(net_earned),
            'this_month_earned': float(this_month_gross * Decimal('0.70')),
            'last_month_earned': float(last_month_gross * Decimal('0.70')),
            'avg_session_rating': avg_rating,
            'wallet_balance': wallet_balance,
            'bank_verified': bank_verified,
            'bank_details': bank_details_data,
            'platform_fee_pct': 30,
            'monthly_breakdown': monthly,
            'transactions': transactions,
            'recent_transactions': transactions,
        })


# ── Bank Details ──────────────────────────────────────────────────────────────

class BankDetailsView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_profile(self, user):
        if user.role == 'alumni':
            return user.alumni_profile
        elif user.role == 'faculty':
            return user.faculty_profile
        return None

    def get(self, request):
        profile = self._get_profile(request.user)
        if not profile:
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)
        details = dict(profile.bank_details)
        # Mask account number
        acc = details.get('account_number', '')
        if acc and len(acc) > 4:
            details['account_number_masked'] = '*' * (len(acc) - 4) + acc[-4:]
        else:
            details['account_number_masked'] = acc
        details.pop('account_number', None)
        return Response({
            'bank_details': details,
            'bank_verified': profile.bank_verified,
        })

    def post(self, request):
        profile = self._get_profile(request.user)
        if not profile:
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

        import re
        data = request.data
        errors = {}

        # Required field validation
        required = ['account_holder_name', 'account_number', 'ifsc_code', 'bank_name']
        for field in required:
            if not data.get(field, '').strip():
                errors[field] = [f'{field} is required.']

        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        # IFSC format: 4 uppercase letters + 0 + 6 alphanumeric chars
        ifsc = data['ifsc_code'].strip()
        if not re.match(r'^[A-Z]{4}0[A-Z0-9]{6}$', ifsc):
            return Response(
                {'ifsc_code': ['IFSC code must be in format: 4 letters + 0 + 6 alphanumeric (e.g. SBIN0001234).']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ifsc = ifsc.upper()

        # Account number: 9–18 digits
        account_number = data['account_number'].strip()
        if not re.match(r'^\d{9,18}$', account_number):
            return Response(
                {'account_number': ['Account number must be 9–18 digits.']},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Confirm account number match
        confirm = data.get('confirm_account_number', '').strip()
        if confirm and confirm != account_number:
            return Response(
                {'confirm_account_number': ['Account numbers do not match.']},
                status=status.HTTP_400_BAD_REQUEST,
            )

        profile.bank_details = {
            'account_holder_name': data['account_holder_name'].strip(),
            'account_number': account_number,
            'ifsc_code': ifsc,
            'bank_name': data['bank_name'].strip(),
            'branch': data.get('branch', '').strip(),
            'upi_id': data.get('upi_id', '').strip(),
        }
        profile.bank_verified = False  # reset on update
        profile.save(update_fields=['bank_details', 'bank_verified'])

        return Response({'message': 'Bank details saved successfully.'})
