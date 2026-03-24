from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.utils import timezone
from django.db.models import Sum, Q
from decimal import Decimal

from .models import Transaction, Wallet, PayoutRequest, AIToolUsage, ReferralBoost
from .serializers import (
    TransactionSerializer, WalletSerializer, PayoutRequestSerializer,
    AIToolUsageSerializer, PaymentInitSerializer, ReferralBoostSerializer,
)
from utils.payment_utils import (
    create_razorpay_order, verify_razorpay_signature,
    create_transaction, calculate_split, get_next_monday,
)
from utils.permissions import CanHostSession


class WalletView(APIView):
    permission_classes = [IsAuthenticated, CanHostSession]

    def get(self, request):
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        serializer = WalletSerializer(wallet)

        recent = Transaction.objects.filter(
            payee=request.user,
            status='completed',
        ).order_by('-created_at')[:10]

        monthly = []
        now = timezone.now()
        for i in range(5, -1, -1):
            m_date = now.replace(day=1)
            for _ in range(i):
                if m_date.month == 1:
                    m_date = m_date.replace(year=m_date.year - 1, month=12)
                else:
                    m_date = m_date.replace(month=m_date.month - 1)
            m_total = Transaction.objects.filter(
                payee=request.user,
                status='completed',
                created_at__year=m_date.year,
                created_at__month=m_date.month,
            ).aggregate(total=Sum('payee_amount'))['total'] or Decimal('0.00')
            monthly.append({
                'month': m_date.strftime('%b %Y'),
                'month_short': m_date.strftime('%b'),
                'earned': float(m_total),
            })

        return Response({
            'wallet': serializer.data,
            'recent_transactions': TransactionSerializer(recent, many=True).data,
            'monthly_breakdown': monthly,
            'next_payout_date': str(get_next_monday()),
        })


class TransactionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Transaction.objects.filter(
            Q(payer=request.user) | Q(payee=request.user)
        ).order_by('-created_at')

        tx_type = request.query_params.get('type')
        if tx_type:
            qs = qs.filter(transaction_type=tx_type)

        tx_status = request.query_params.get('status')
        if tx_status:
            qs = qs.filter(status=tx_status)

        role = request.query_params.get('role')
        if role == 'payer':
            qs = Transaction.objects.filter(payer=request.user).order_by('-created_at')
        elif role == 'payee':
            qs = Transaction.objects.filter(payee=request.user).order_by('-created_at')

        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(
            TransactionSerializer(page, many=True).data
        )


class PayoutRequestView(APIView):
    permission_classes = [IsAuthenticated, CanHostSession]

    def get(self, request):
        payout_qs = PayoutRequest.objects.filter(
            user=request.user
        ).order_by('-requested_at')
        return Response(PayoutRequestSerializer(payout_qs, many=True).data)

    def post(self, request):
        wallet, _ = Wallet.objects.get_or_create(user=request.user)

        amount_str = request.data.get('amount')
        try:
            amount = Decimal(str(amount_str))
        except Exception:
            return Response({'error': 'Invalid amount.'}, status=400)

        if amount < Decimal('500.00'):
            return Response({'error': 'Minimum withdrawal amount is ₹500.'}, status=400)

        if amount > wallet.available_for_withdrawal:
            return Response({
                'error': f'Insufficient balance. Available: ₹{wallet.available_for_withdrawal}',
            }, status=400)

        bank_details = {}
        try:
            if request.user.role == 'alumni':
                bank_details = request.user.alumni_profile.bank_details or {}
            elif request.user.role == 'faculty':
                bank_details = request.user.faculty_profile.bank_details or {}
        except Exception:
            pass

        if not bank_details.get('account_number'):
            return Response({
                'error': 'Please add your bank details before requesting a payout.',
                'redirect': '/payments/wallet/',
            }, status=400)

        if PayoutRequest.objects.filter(
            user=request.user, status__in=['pending', 'approved']
        ).exists():
            return Response({
                'error': 'You already have a pending payout request. Please wait for it to be processed.',
            }, status=400)

        payout = PayoutRequest.objects.create(
            user=request.user,
            wallet=wallet,
            amount=amount,
            bank_details_snapshot=bank_details,
            status='pending',
        )

        return Response({
            'message': f'Payout request of ₹{amount} submitted successfully. Will be processed by next Monday.',
            'payout_id': payout.id,
            'next_payout_date': str(get_next_monday()),
        }, status=201)

    def delete(self, request, pk):
        payout = get_object_or_404(PayoutRequest, pk=pk, user=request.user)
        if payout.status not in ['pending']:
            return Response(
                {'error': 'Only pending payout requests can be cancelled.'},
                status=400,
            )
        payout.status = 'cancelled'
        payout.save()
        return Response({'message': 'Payout request cancelled.'})


class AIToolPaymentInitView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        tool_type = request.data.get('tool_type')
        if not tool_type or tool_type not in dict(AIToolUsage.TOOL_TYPES):
            return Response({'error': 'Invalid tool type.'}, status=400)

        price = AIToolUsage.get_price(tool_type)
        free_remaining = AIToolUsage.get_free_uses_remaining(request.user, tool_type)

        if free_remaining > 0 or price == Decimal('0.00'):
            return Response({
                'is_free': True,
                'can_proceed': True,
                'free_uses_remaining': free_remaining,
                'tool_type': tool_type,
                'price': str(price),
            })

        receipt_id = f"aitool_{tool_type}_{request.user.id}_{int(timezone.now().timestamp())}"
        try:
            order = create_razorpay_order(
                price, receipt_id,
                notes={'tool': tool_type, 'user': request.user.email},
            )
        except Exception as e:
            return Response({'error': f'Payment gateway error: {str(e)}'}, status=500)

        return Response({
            'is_free': False,
            'can_proceed': True,
            'tool_type': tool_type,
            'price': str(price),
            'razorpay_order_id': order['id'],
            'razorpay_key_id': settings.RAZORPAY_KEY_ID,
            'amount': str(price),
            'currency': 'INR',
            'description': f'AlumniAI — {dict(AIToolUsage.TOOL_TYPES)[tool_type]}',
            'student_name': f"{request.user.first_name} {request.user.last_name}".strip(),
            'student_email': request.user.email,
        })


class AIToolPaymentVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        tool_type = request.data.get('tool_type')
        razorpay_order_id = request.data.get('razorpay_order_id', '')
        razorpay_payment_id = request.data.get('razorpay_payment_id', '')
        razorpay_signature = request.data.get('razorpay_signature', '')
        is_free = request.data.get('is_free', False)

        if not tool_type:
            return Response({'error': 'tool_type is required.'}, status=400)

        price = AIToolUsage.get_price(tool_type)

        if is_free:
            usage = AIToolUsage.objects.create(
                user=request.user,
                tool_type=tool_type,
                is_free_use=True,
            )
            return Response({
                'success': True,
                'usage_id': usage.id,
                'is_free': True,
                'message': f'Free use confirmed. Proceed to use {dict(AIToolUsage.TOOL_TYPES)[tool_type]}.',
            })

        if not verify_razorpay_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature):
            return Response({'error': 'Payment verification failed.'}, status=400)

        transaction = create_transaction(
            payer=request.user,
            gross_amount=price,
            transaction_type=tool_type,
            description=f'{dict(AIToolUsage.TOOL_TYPES)[tool_type]} — AlumniAI',
            payee=None,
            platform_pct=Decimal('1.00'),
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_signature=razorpay_signature,
            related_object_type='ai_tool',
            status='completed',
        )

        usage = AIToolUsage.objects.create(
            user=request.user,
            tool_type=tool_type,
            is_free_use=False,
            transaction=transaction,
        )

        return Response({
            'success': True,
            'usage_id': usage.id,
            'invoice_number': transaction.invoice_number,
            'is_free': False,
            'message': 'Payment successful. You can now use the tool.',
        })


class ReferralBoostPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        referral_id = request.data.get('referral_id')
        if not referral_id:
            return Response({'error': 'referral_id is required.'}, status=400)

        from apps.referrals.models import Referral
        referral = get_object_or_404(Referral, pk=referral_id, posted_by=request.user)

        boost_amount = Decimal('99.00')
        receipt_id = f"boost_{referral_id}_{request.user.id}"

        try:
            order = create_razorpay_order(
                boost_amount, receipt_id,
                notes={'referral_id': str(referral_id)},
            )
        except Exception as e:
            return Response({'error': str(e)}, status=500)

        return Response({
            'razorpay_order_id': order['id'],
            'razorpay_key_id': settings.RAZORPAY_KEY_ID,
            'amount': str(boost_amount),
            'currency': 'INR',
            'description': f'Referral Boost — {referral.job_title} @ {referral.company_name}',
            'referral_id': referral_id,
        })

    def patch(self, request):
        razorpay_order_id = request.data.get('razorpay_order_id', '')
        razorpay_payment_id = request.data.get('razorpay_payment_id', '')
        razorpay_signature = request.data.get('razorpay_signature', '')
        referral_id = request.data.get('referral_id')

        if not verify_razorpay_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature):
            return Response({'error': 'Payment verification failed.'}, status=400)

        from apps.referrals.models import Referral
        referral = get_object_or_404(Referral, pk=referral_id, posted_by=request.user)

        boost_amount = Decimal('99.00')
        transaction = create_transaction(
            payer=request.user,
            gross_amount=boost_amount,
            transaction_type='referral_boost',
            description=f'Referral Boost — {referral.job_title} @ {referral.company_name}',
            payee=None,
            platform_pct=Decimal('1.00'),
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_signature=razorpay_signature,
            related_object_type='referral',
            related_object_id=referral.id,
            status='completed',
        )

        boost_expires = timezone.now() + timezone.timedelta(hours=48)
        boost, _ = ReferralBoost.objects.get_or_create(
            referral=referral,
            defaults={
                'boosted_by': request.user,
                'transaction': transaction,
                'expires_at': boost_expires,
            },
        )
        boost.expires_at = boost_expires
        boost.transaction = transaction
        boost.save(update_fields=['expires_at', 'transaction'])

        referral.is_boosted = True
        referral.boosted_until = boost_expires
        referral.save(update_fields=['is_boosted', 'boosted_until'])

        return Response({
            'message': 'Referral boosted successfully for 48 hours!',
            'expires_at': boost_expires.isoformat(),
            'invoice_number': transaction.invoice_number,
        })


class InvoiceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, invoice_number):
        transaction = get_object_or_404(Transaction, invoice_number=invoice_number)

        if (
            transaction.payer != request.user
            and transaction.payee != request.user
            and request.user.role != 'admin'
        ):
            return Response({'error': 'Permission denied.'}, status=403)

        return Response({
            'invoice_number': transaction.invoice_number,
            'date': transaction.created_at.strftime('%d %B %Y'),
            'transaction_type': transaction.get_transaction_type_display(),
            'status': transaction.status,
            'payer': {
                'name': (
                    f"{transaction.payer.first_name} {transaction.payer.last_name}".strip()
                    if transaction.payer else 'AlumniAI Platform'
                ),
                'email': transaction.payer.email if transaction.payer else '',
            },
            'payee': {
                'name': (
                    f"{transaction.payee.first_name} {transaction.payee.last_name}".strip()
                    if transaction.payee else 'AlumniAI Platform'
                ),
                'email': transaction.payee.email if transaction.payee else '',
            },
            'amounts': {
                'gross': str(transaction.gross_amount),
                'platform_fee': str(transaction.platform_fee),
                'payee_amount': str(transaction.payee_amount),
            },
            'description': transaction.description,
            'razorpay_payment_id': transaction.razorpay_payment_id,
        })


class AdminPayoutManageView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Admin only.'}, status=403)

        status_filter = request.query_params.get('status', 'pending')
        payouts = PayoutRequest.objects.filter(
            status=status_filter
        ).select_related('user', 'wallet').order_by('-requested_at')

        data = []
        for p in payouts:
            data.append({
                'id': p.id,
                'user_name': f"{p.user.first_name} {p.user.last_name}".strip(),
                'user_email': p.user.email,
                'user_role': p.user.role,
                'amount': str(p.amount),
                'status': p.status,
                'bank_details': p.bank_details_snapshot,
                'requested_at': p.requested_at.isoformat(),
                'wallet_balance': str(p.wallet.balance),
            })
        return Response({'payouts': data, 'count': len(data)})

    def patch(self, request, pk):
        if request.user.role != 'admin':
            return Response({'error': 'Admin only.'}, status=403)

        payout = get_object_or_404(PayoutRequest, pk=pk)
        action = request.data.get('action')
        note = request.data.get('admin_note', '').strip()
        reference = request.data.get('transaction_reference', '').strip()

        if action == 'approve':
            payout.status = 'approved'
            payout.admin_note = note
        elif action == 'process':
            if not reference:
                return Response(
                    {'error': 'transaction_reference is required when processing payout.'},
                    status=400,
                )
            payout.status = 'processed'
            payout.transaction_reference = reference
            payout.admin_note = note
            payout.processed_by = request.user
            payout.processed_at = timezone.now()
        elif action == 'reject':
            if not note:
                return Response(
                    {'error': 'admin_note (reason) is required when rejecting payout.'},
                    status=400,
                )
            payout.status = 'rejected'
            payout.admin_note = note
        else:
            return Response({'error': 'action must be approve, process, or reject.'}, status=400)

        payout.save()
        return Response({'message': f'Payout {action}d successfully.', 'payout_id': payout.id})


class PlatformRevenueView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'admin':
            return Response({'error': 'Admin only.'}, status=403)

        now = timezone.now()

        total_revenue = Transaction.objects.filter(
            status='completed'
        ).aggregate(total=Sum('platform_fee'))['total'] or Decimal('0.00')

        this_month = Transaction.objects.filter(
            status='completed',
            created_at__year=now.year,
            created_at__month=now.month,
        ).aggregate(total=Sum('platform_fee'))['total'] or Decimal('0.00')

        by_type = {}
        for tx_type, label in Transaction.TRANSACTION_TYPES:
            type_total = Transaction.objects.filter(
                status='completed',
                transaction_type=tx_type,
            ).aggregate(total=Sum('platform_fee'))['total'] or Decimal('0.00')
            by_type[tx_type] = {'label': label, 'total': str(type_total)}

        pending_payouts = PayoutRequest.objects.filter(
            status__in=['pending', 'approved']
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        monthly = []
        for i in range(5, -1, -1):
            m_date = now.replace(day=1)
            for _ in range(i):
                if m_date.month == 1:
                    m_date = m_date.replace(year=m_date.year - 1, month=12)
                else:
                    m_date = m_date.replace(month=m_date.month - 1)
            m_total = Transaction.objects.filter(
                status='completed',
                created_at__year=m_date.year,
                created_at__month=m_date.month,
            ).aggregate(total=Sum('platform_fee'))['total'] or Decimal('0.00')
            monthly.append({'month': m_date.strftime('%b %Y'), 'revenue': float(m_total)})

        return Response({
            'total_revenue': str(total_revenue),
            'this_month_revenue': str(this_month),
            'by_type': by_type,
            'pending_payouts': str(pending_payouts),
            'monthly_breakdown': monthly,
        })


class AIToolUsageCheckView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, tool_type):
        if tool_type not in dict(AIToolUsage.TOOL_TYPES):
            return Response({'error': 'Invalid tool type.'}, status=400)

        price = AIToolUsage.get_price(tool_type)
        free_remaining = AIToolUsage.get_free_uses_remaining(request.user, tool_type)

        return Response({
            'tool_type': tool_type,
            'price': str(price),
            'free_uses_remaining': free_remaining,
            'is_free_next': free_remaining > 0 or price == Decimal('0.00'),
            'total_used': AIToolUsage.objects.filter(
                user=request.user, tool_type=tool_type
            ).count(),
        })
