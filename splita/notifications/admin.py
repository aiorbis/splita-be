from django.contrib import admin
from .models import NotificationPreference, Notification, NotificationTemplate


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    """
    Admin configuration for NotificationPreference model
    """
    list_display = ('user', 'emi_email_enabled', 'emi_push_enabled', 'emi_sms_enabled',
                   'emi_reminder_days_before', 'credit_utilization_alert_enabled')
    list_filter = ('emi_email_enabled', 'emi_push_enabled', 'emi_sms_enabled',
                  'payment_confirmation_email', 'overdue_email_enabled', 'created_at')
    search_fields = ('user__email', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('EMI Reminders', {
            'fields': ('emi_email_enabled', 'emi_push_enabled', 'emi_sms_enabled',
                      'emi_reminder_days_before')
        }),
        ('Payment Confirmations', {
            'fields': ('payment_confirmation_email', 'payment_confirmation_push')
        }),
        ('Overdue Notifications', {
            'fields': ('overdue_email_enabled', 'overdue_push_enabled', 'overdue_sms_enabled')
        }),
        ('Credit Utilization Alerts', {
            'fields': ('credit_utilization_alert_enabled', 'credit_utilization_threshold')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """
    Admin configuration for Notification model
    """
    list_display = ('user', 'notification_type', 'delivery_method', 'title', 'status',
                   'sent_at', 'read_at')
    list_filter = ('notification_type', 'delivery_method', 'status', 'sent_at', 'created_at')
    search_fields = ('user__email', 'user__username', 'title', 'message')
    readonly_fields = ('sent_at', 'delivered_at', 'read_at', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Notification Information', {
            'fields': ('user', 'notification_type', 'delivery_method', 'title', 'message')
        }),
        ('Status', {
            'fields': ('status', 'sent_at', 'delivered_at', 'read_at')
        }),
        ('Related Objects', {
            'fields': ('emi_id', 'credit_card_id', 'loan_id'),
            'classes': ('collapse',)
        }),
        ('Delivery Tracking', {
            'fields': ('fcm_message_id', 'email_message_id'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_read', 'mark_as_sent']
    
    def mark_as_read(self, request, queryset):
        updated = queryset.update(status='READ')
        self.message_user(request, f'{updated} notifications marked as read.')
    mark_as_read.short_description = "Mark selected notifications as read"
    
    def mark_as_sent(self, request, queryset):
        updated = queryset.update(status='SENT')
        self.message_user(request, f'{updated} notifications marked as sent.')
    mark_as_sent.short_description = "Mark selected notifications as sent"


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    """
    Admin configuration for NotificationTemplate model
    """
    list_display = ('template_type', 'is_active', 'created_at', 'updated_at')
    list_filter = ('template_type', 'is_active', 'created_at')
    search_fields = ('template_type', 'email_subject', 'push_title')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('template_type',)
    
    fieldsets = (
        ('Template Information', {
            'fields': ('template_type', 'is_active')
        }),
        ('Email Template', {
            'fields': ('email_subject', 'email_body')
        }),
        ('Push Notification Template', {
            'fields': ('push_title', 'push_body')
        }),
        ('SMS Template', {
            'fields': ('sms_body',)
        }),
        ('Help', {
            'fields': ('variables_help',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
