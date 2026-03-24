from django.contrib import admin
from .models import Transaction, Wallet, PayoutRequest, AIToolUsage, ReferralBoost


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        'invoice_number', 'transaction_type', 'status',
        'gross_amount', 'platform_fee', 'payee_amount',
        'payer_email', 'payee_email', 'created_at',
    ]
    list_filter = ['transaction_type', 'status']
    search_fields = ['invoice_number', 'payer__email', 'payee__email', 'razorpay_payment_id']
    readonly_fields = ['invoice_number', 'created_at', 'updated_at']

    def payer_email(self, obj):
        return obj.payer.email if obj.payer else '—'

    def payee_email(self, obj):
        return obj.payee.email if obj.payee else 'Platform'


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = [
        'user_email', 'balance', 'total_earned',
        'total_withdrawn', 'pending_withdrawal', 'last_payout_at',
    ]
    search_fields = ['user__email']
    readonly_fields = ['created_at', 'updated_at']

    def user_email(self, obj):
        return obj.user.email


@admin.register(PayoutRequest)
class PayoutRequestAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user_email', 'amount', 'status',
        'requested_at', 'processed_at', 'transaction_reference',
    ]
    list_filter = ['status']
    search_fields = ['user__email', 'transaction_reference']
    readonly_fields = ['requested_at', 'bank_details_snapshot']
    actions = ['mark_as_approved']

    def user_email(self, obj):
        return obj.user.email

    def mark_as_approved(self, request, queryset):
        queryset.update(status='approved')
    mark_as_approved.short_description = 'Mark selected as Approved'


@admin.register(AIToolUsage)
class AIToolUsageAdmin(admin.ModelAdmin):
    list_display = ['user', 'tool_type', 'is_free_use', 'created_at']
    list_filter = ['tool_type', 'is_free_use']
    search_fields = ['user__email']


@admin.register(ReferralBoost)
class ReferralBoostAdmin(admin.ModelAdmin):
    list_display = ['referral', 'boosted_by', 'boost_amount', 'boosted_at', 'expires_at', 'is_active']

    def is_active(self, obj):
        return obj.is_active
    is_active.boolean = True
