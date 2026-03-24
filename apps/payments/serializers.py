from rest_framework import serializers
from decimal import Decimal
from .models import Transaction, Wallet, PayoutRequest, AIToolUsage, ReferralBoost


class TransactionSerializer(serializers.ModelSerializer):
    payer_name = serializers.SerializerMethodField()
    payee_name = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = [
            'id', 'invoice_number', 'transaction_type', 'status',
            'gross_amount', 'platform_fee', 'payee_amount', 'refund_amount',
            'razorpay_order_id', 'razorpay_payment_id',
            'related_object_type', 'related_object_id',
            'description', 'payer_name', 'payee_name',
            'created_at', 'updated_at',
        ]

    def get_payer_name(self, obj):
        if not obj.payer:
            return None
        return f"{obj.payer.first_name} {obj.payer.last_name}".strip() or obj.payer.email

    def get_payee_name(self, obj):
        if not obj.payee:
            return 'Platform'
        return f"{obj.payee.first_name} {obj.payee.last_name}".strip() or obj.payee.email


class WalletSerializer(serializers.ModelSerializer):
    available_for_withdrawal = serializers.ReadOnlyField()
    can_withdraw = serializers.ReadOnlyField()
    next_payout_date = serializers.SerializerMethodField()

    class Meta:
        model = Wallet
        fields = [
            'id', 'balance', 'total_earned', 'total_withdrawn',
            'pending_withdrawal', 'available_for_withdrawal',
            'can_withdraw', 'last_payout_at', 'next_payout_date',
            'created_at', 'updated_at',
        ]

    def get_next_payout_date(self, obj):
        from utils.payment_utils import get_next_monday
        return str(get_next_monday())


class PayoutRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = PayoutRequest
        fields = [
            'id', 'amount', 'status', 'bank_details_snapshot',
            'admin_note', 'processed_at', 'transaction_reference',
            'requested_at', 'updated_at',
        ]
        read_only_fields = [
            'status', 'admin_note', 'processed_at',
            'transaction_reference', 'bank_details_snapshot',
        ]

    def validate_amount(self, value):
        if value < Decimal('500.00'):
            raise serializers.ValidationError('Minimum withdrawal amount is ₹500.')
        return value


class AIToolUsageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIToolUsage
        fields = ['id', 'tool_type', 'is_free_use', 'result_data', 'created_at']


class PaymentInitSerializer(serializers.Serializer):
    """Used to initiate payment for AI tools."""
    tool_type = serializers.ChoiceField(choices=AIToolUsage.TOOL_TYPES)


class ReferralBoostSerializer(serializers.Serializer):
    referral_id = serializers.IntegerField()
