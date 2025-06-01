from rest_framework import serializers
from .models import Notification, NotificationPreference, NotificationTemplate


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """
    Serializer for notification preferences
    """
    class Meta:
        model = NotificationPreference
        fields = '__all__'
        read_only_fields = ('user', 'created_at', 'updated_at')


class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for notifications
    """
    class Meta:
        model = Notification
        fields = '__all__'
        read_only_fields = ('user', 'created_at', 'updated_at', 'sent_at', 'delivered_at', 'read_at')


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """
    Serializer for notification templates
    """
    class Meta:
        model = NotificationTemplate
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class TriggerNotificationSerializer(serializers.Serializer):
    """
    Serializer for manually triggering notifications
    """
    notification_type = serializers.ChoiceField(choices=[
        ('EMI_REMINDER', 'EMI Reminder'),
        ('OVERDUE_ALERT', 'Overdue Alert'),
        ('CREDIT_UTILIZATION', 'Credit Utilization Alert'),
        ('GENERAL', 'General Notification'),
    ])
    title = serializers.CharField(max_length=200)
    message = serializers.CharField()
    delivery_methods = serializers.MultipleChoiceField(
        choices=[
            ('EMAIL', 'Email'),
            ('PUSH', 'Push Notification'),
            ('SMS', 'SMS'),
        ],
        default=['EMAIL', 'PUSH']
    )
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="List of user IDs to send notification to. If empty, sends to all users."
    ) 