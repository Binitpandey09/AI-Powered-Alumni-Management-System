from django.contrib import admin
from .models import Session, Booking, SessionReview, SessionSlot


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'host_email', 'session_type', 'scheduled_at',
        'status', 'booked_seats', 'max_seats', 'price', 'total_revenue',
    ]
    list_filter = ['session_type', 'status', 'is_free']
    search_fields = ['title', 'host__email', 'niche']
    readonly_fields = ['booked_seats', 'total_revenue', 'platform_earned', 'host_earned']

    def host_email(self, obj):
        return obj.host.email
    host_email.short_description = 'Host'


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = [
        'session_title', 'student_email', 'status',
        'amount_paid', 'platform_cut', 'host_share', 'booked_at',
    ]
    list_filter = ['status', 'is_free_demo']
    search_fields = ['session__title', 'student__email']

    def session_title(self, obj):
        return obj.session.title
    session_title.short_description = 'Session'

    def student_email(self, obj):
        return obj.student.email
    student_email.short_description = 'Student'


@admin.register(SessionReview)
class SessionReviewAdmin(admin.ModelAdmin):
    list_display = ['booking', 'rating', 'is_anonymous', 'created_at']
    list_filter = ['rating', 'is_anonymous']
    search_fields = ['booking__student__email', 'booking__session__title']


@admin.register(SessionSlot)
class SessionSlotAdmin(admin.ModelAdmin):
    list_display = ['host', 'slot_start', 'slot_end', 'is_booked']
    list_filter = ['is_booked']
    search_fields = ['host__email']
