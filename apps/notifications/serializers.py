from rest_framework import serializers
from .models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id', 'notif_type', 'title', 'message', 'link',
            'is_read', 'read_at', 'related_object_type', 'related_object_id',
            'created_at',
        ]
        read_only_fields = fields


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """
    Returns preferences in nested format:
      { "in_app": { "session_booked": true, ... }, "email": { ... } }
    Also accepts flat field updates for backward compat with the toggle UI.
    """
    in_app = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()

    class Meta:
        model = NotificationPreference
        fields = ['in_app', 'email', 'updated_at']
        read_only_fields = ['updated_at']

    def get_in_app(self, obj):
        return {
            'session_booked': obj.in_app_session_booked,
            'session_reminder': obj.in_app_session_reminder,
            'session_cancelled': obj.in_app_session_cancelled,
            'payment_received': obj.in_app_payment_received,
            'referral_applied': obj.in_app_referral_applied,
            'application_update': obj.in_app_application_update,
            'general': obj.in_app_general,
            'admin_broadcast': obj.in_app_admin_broadcast,
        }

    def get_email(self, obj):
        return {
            'session_booked': obj.email_session_booked,
            'session_reminder': obj.email_session_reminder,
            'session_cancelled': obj.email_session_cancelled,
            'payment_received': obj.email_payment_received,
            'referral_applied': obj.email_referral_applied,
            'application_update': obj.email_application_update,
            'general': obj.email_general,
            'admin_broadcast': obj.email_admin_broadcast,
        }

    def update(self, instance, validated_data):
        # Handle nested in_app / email dicts from request.data directly
        request_data = self.context['request'].data if self.context.get('request') else {}

        in_app_data = request_data.get('in_app', {})
        email_data = request_data.get('email', {})

        # Map nested keys → model fields
        in_app_map = {
            'session_booked': 'in_app_session_booked',
            'session_reminder': 'in_app_session_reminder',
            'session_cancelled': 'in_app_session_cancelled',
            'payment_received': 'in_app_payment_received',
            'referral_applied': 'in_app_referral_applied',
            'application_update': 'in_app_application_update',
            'general': 'in_app_general',
            'admin_broadcast': 'in_app_admin_broadcast',
        }
        email_map = {
            'session_booked': 'email_session_booked',
            'session_reminder': 'email_session_reminder',
            'session_cancelled': 'email_session_cancelled',
            'payment_received': 'email_payment_received',
            'referral_applied': 'email_referral_applied',
            'application_update': 'email_application_update',
            'general': 'email_general',
            'admin_broadcast': 'email_admin_broadcast',
        }

        for key, field in in_app_map.items():
            if key in in_app_data:
                setattr(instance, field, in_app_data[key])

        for key, field in email_map.items():
            if key in email_data:
                setattr(instance, field, email_data[key])

        # Also handle flat field updates (from the toggle UI: inapp_general, email_session etc.)
        flat_fields = [
            'inapp_general', 'inapp_session', 'inapp_referral', 'inapp_payment',
            'email_general', 'email_session', 'email_referral', 'email_payment',
        ]
        for field in flat_fields:
            if field in request_data:
                setattr(instance, field, request_data[field])

        instance.save()
        return instance
