from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class NotificationPreference(models.Model):
    """
    Model to store user notification preferences
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_preferences')
    
    # EMI Reminders
    emi_email_enabled = models.BooleanField(default=True)
    emi_push_enabled = models.BooleanField(default=True)
    emi_sms_enabled = models.BooleanField(default=False)
    
    # Reminder timing (days before due date)
    emi_reminder_days_before = models.IntegerField(default=3)
    
    # Payment confirmations
    payment_confirmation_email = models.BooleanField(default=True)
    payment_confirmation_push = models.BooleanField(default=True)
    
    # Overdue notifications
    overdue_email_enabled = models.BooleanField(default=True)
    overdue_push_enabled = models.BooleanField(default=True)
    overdue_sms_enabled = models.BooleanField(default=True)
    
    # Credit utilization alerts
    credit_utilization_alert_enabled = models.BooleanField(default=True)
    credit_utilization_threshold = models.IntegerField(default=80)  # Percentage
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Notification Preferences - {self.user.email}"
    
    class Meta:
        db_table = 'notification_preferences'


class Notification(models.Model):
    """
    Model to store all notifications sent to users
    """
    NOTIFICATION_TYPES = [
        ('EMI_REMINDER', 'EMI Reminder'),
        ('PAYMENT_CONFIRMATION', 'Payment Confirmation'),
        ('OVERDUE_ALERT', 'Overdue Alert'),
        ('CREDIT_UTILIZATION', 'Credit Utilization Alert'),
        ('LOAN_COMPLETION', 'Loan Completion'),
        ('GENERAL', 'General Notification'),
    ]
    
    DELIVERY_METHODS = [
        ('EMAIL', 'Email'),
        ('PUSH', 'Push Notification'),
        ('SMS', 'SMS'),
        ('IN_APP', 'In-App'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SENT', 'Sent'),
        ('DELIVERED', 'Delivered'),
        ('FAILED', 'Failed'),
        ('READ', 'Read'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    delivery_method = models.CharField(max_length=20, choices=DELIVERY_METHODS)
    title = models.CharField(max_length=200)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # Optional reference to related objects
    emi_id = models.IntegerField(null=True, blank=True)
    credit_card_id = models.IntegerField(null=True, blank=True)
    loan_id = models.IntegerField(null=True, blank=True)
    
    # Delivery tracking
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    # For push notifications
    fcm_message_id = models.CharField(max_length=200, null=True, blank=True)
    
    # For email notifications
    email_message_id = models.CharField(max_length=200, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.notification_type} - {self.user.email} - {self.status}"
    
    def mark_as_read(self):
        from django.utils import timezone
        self.status = 'READ'
        self.read_at = timezone.now()
        self.save()
    
    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']


class NotificationTemplate(models.Model):
    """
    Model to store notification templates
    """
    TEMPLATE_TYPES = [
        ('EMI_REMINDER', 'EMI Reminder'),
        ('PAYMENT_CONFIRMATION', 'Payment Confirmation'),
        ('OVERDUE_ALERT', 'Overdue Alert'),
        ('CREDIT_UTILIZATION', 'Credit Utilization Alert'),
        ('LOAN_COMPLETION', 'Loan Completion'),
        ('WELCOME', 'Welcome Message'),
    ]
    
    template_type = models.CharField(max_length=30, choices=TEMPLATE_TYPES, unique=True)
    email_subject = models.CharField(max_length=200, blank=True)
    email_body = models.TextField(blank=True)
    push_title = models.CharField(max_length=200, blank=True)
    push_body = models.TextField(blank=True)
    sms_body = models.TextField(blank=True)
    
    # Template variables that can be used: {user_name}, {emi_amount}, {due_date}, etc.
    variables_help = models.TextField(
        help_text="Available variables: {user_name}, {emi_amount}, {due_date}, {card_name}, {loan_name}, etc.",
        blank=True
    )
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Template - {self.template_type}"
    
    class Meta:
        db_table = 'notification_templates'
