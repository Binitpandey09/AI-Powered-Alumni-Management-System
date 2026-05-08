from django.db import models
from django.conf import settings
from decimal import Decimal
from django.utils import timezone


class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('session_booking', 'Session Booking'),
        ('session_refund', 'Session Refund'),
        ('resume_check', 'Resume Score Check'),
        ('resume_builder', 'Resume Builder'),
        ('ai_interview', 'AI Mock Interview'),
        ('skill_gap', 'Skill Gap Analysis'),
        ('course_commission', 'Course Commission'),
        ('referral_boost', 'Referral Boost'),
        ('wallet_topup', 'Wallet Top-up'),
        ('payout', 'Payout to Bank'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('partially_refunded', 'Partially Refunded'),
    ]

    # Who paid
    payer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='payments_made',
    )
    # Who received (null for platform-only transactions like AI tools)
    payee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='payments_received',
    )

    transaction_type = models.CharField(max_length=30, choices=TRANSACTION_TYPES)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending')

    # Amounts — all in INR
    gross_amount = models.DecimalField(max_digits=10, decimal_places=2)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    payee_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    # Razorpay fields
    razorpay_order_id = models.CharField(max_length=200, blank=True)
    razorpay_payment_id = models.CharField(max_length=200, blank=True)
    razorpay_signature = models.CharField(max_length=500, blank=True)
    razorpay_refund_id = models.CharField(max_length=200, blank=True)

    # Related object (generic)
    related_object_type = models.CharField(max_length=50, blank=True)
    related_object_id = models.IntegerField(null=True, blank=True)

    # Invoice
    invoice_number = models.CharField(max_length=50, unique=True)

    description = models.CharField(max_length=500, blank=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payer', 'status']),
            models.Index(fields=['payer', '-created_at']),
            models.Index(fields=['payee', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['transaction_type', 'status']),
        ]

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            year = timezone.now().year
            count = Transaction.objects.filter(created_at__year=year).count() + 1
            self.invoice_number = f"INV-{year}-{str(count).zfill(4)}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.invoice_number} — {self.transaction_type} — ₹{self.gross_amount}"


class Wallet(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wallet',
    )
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_earned = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_withdrawn = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    pending_withdrawal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    last_payout_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Wallet — {self.user.email} — ₹{self.balance}"

    @property
    def available_for_withdrawal(self):
        return max(Decimal('0.00'), self.balance - self.pending_withdrawal)

    @property
    def can_withdraw(self):
        return self.available_for_withdrawal >= Decimal('500.00')


class PayoutRequest(models.Model):
    PAYOUT_STATUS = [
        ('pending', 'Pending Admin Approval'),
        ('approved', 'Approved — Processing'),
        ('processed', 'Processed — Paid'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled by User'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payout_requests',
    )
    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name='payout_requests',
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=PAYOUT_STATUS, default='pending')

    # Bank details snapshot at time of request (immutable record)
    bank_details_snapshot = models.JSONField(default=dict)

    # Admin fields
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='processed_payouts',
    )
    admin_note = models.TextField(blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    transaction_reference = models.CharField(max_length=200, blank=True)

    requested_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-requested_at']

    def __str__(self):
        return f"Payout #{self.id} — {self.user.email} — ₹{self.amount} [{self.status}]"


class AIToolUsage(models.Model):
    TOOL_TYPES = [
        ('resume_check', 'Resume Score Check'),
        ('resume_builder', 'Resume Builder'),
        ('ai_interview', 'AI Mock Interview'),
        ('skill_gap', 'Skill Gap Analysis'),
        ('cv_parser', 'CV Auto-Parse'),
        ('summary_generator', 'Profile Summary Generator'),
    ]
    PRICING = {
        'resume_check': Decimal('49.00'),
        'resume_builder': Decimal('149.00'),
        'ai_interview': Decimal('99.00'),
        'skill_gap': Decimal('0.00'),     # Free for all users
        'cv_parser': Decimal('0.00'),
        'summary_generator': Decimal('0.00'),
    }
    FREE_USES = {
        'resume_check': 1,       # 1 free check, then ₹49
        'resume_builder': 0,     # Paid only (₹149)
        'ai_interview': 0,       # Paid only (₹99)
        'skill_gap': 999,        # Always free
        'cv_parser': 999,
        'summary_generator': 3,
    }

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ai_tool_usages',
    )
    tool_type = models.CharField(max_length=30, choices=TOOL_TYPES)
    is_free_use = models.BooleanField(default=False)
    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='ai_usage',
    )
    result_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} — {self.tool_type} ({'free' if self.is_free_use else 'paid'})"

    @classmethod
    def get_free_uses_remaining(cls, user, tool_type):
        free_limit = cls.FREE_USES.get(tool_type, 0)
        used_free = cls.objects.filter(
            user=user,
            tool_type=tool_type,
            is_free_use=True,
        ).count()
        return max(0, free_limit - used_free)

    @classmethod
    def get_price(cls, tool_type):
        return cls.PRICING.get(tool_type, Decimal('0.00'))


class ReferralBoost(models.Model):
    referral = models.OneToOneField(
        'referrals.Referral',
        on_delete=models.CASCADE,
        related_name='boost',
    )
    boosted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='referral_boosts',
    )
    transaction = models.OneToOneField(
        Transaction,
        on_delete=models.SET_NULL,
        null=True,
        related_name='referral_boost',
    )
    boost_amount = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('99.00'))
    boosted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def __str__(self):
        return f"Boost — {self.referral} — expires {self.expires_at}"

    @property
    def is_active(self):
        return timezone.now() < self.expires_at
