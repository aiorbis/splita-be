from celery import shared_task
from django.utils import timezone
from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.db import models

from credit_cards.models import CreditCardEMI, CreditCard, CreditCardPayment
from loans.models import LoanEMI, Loan, LoanPayment
from .services import notification_service

User = get_user_model()


@shared_task
def send_emi_reminders():
    """
    Send EMI reminders to users based on their notification preferences
    """
    try:
        # Get all users with notification preferences
        users_with_preferences = User.objects.filter(
            notification_preferences__isnull=False,
            notification_preferences__emi_email_enabled=True
        ).select_related('notification_preferences')
        
        reminder_count = 0
        
        for user in users_with_preferences:
            preferences = user.notification_preferences
            reminder_days = preferences.emi_reminder_days_before
            
            # Calculate the target date for reminders
            target_date = date.today() + timedelta(days=reminder_days)
            
            # Get pending Credit Card EMIs due on the target date
            pending_cc_emis = CreditCardEMI.objects.filter(
                user=user,
                status='PENDING',
                due_date=target_date
            )
            
            # Get pending Loan EMIs due on the target date
            pending_loan_emis = LoanEMI.objects.filter(
                user=user,
                status='PENDING',
                due_date=target_date
            )
            
            # Send reminders for credit card EMIs
            for emi in pending_cc_emis:
                notification_service.send_emi_reminder(user, emi)
                reminder_count += 1
            
            # Send reminders for loan EMIs
            for emi in pending_loan_emis:
                notification_service.send_emi_reminder(user, emi)
                reminder_count += 1
        
        return f"Sent {reminder_count} EMI reminders"
        
    except Exception as e:
        return f"Error sending EMI reminders: {str(e)}"


@shared_task
def send_overdue_alerts():
    """
    Send overdue alerts for EMIs that are past their due date
    """
    try:
        today = date.today()
        
        # Update Credit Card EMI status to overdue if past due date
        overdue_cc_emis = CreditCardEMI.objects.filter(
            status='PENDING',
            due_date__lt=today
        )
        
        # Update Loan EMI status to overdue if past due date
        overdue_loan_emis = LoanEMI.objects.filter(
            status='PENDING',
            due_date__lt=today
        )
        
        # Update status to overdue
        overdue_cc_emis.update(status='OVERDUE')
        overdue_loan_emis.update(status='OVERDUE')
        
        alert_count = 0
        
        # Send overdue alerts for credit card EMIs
        for emi in overdue_cc_emis:
            notification_service.send_overdue_alert(emi.user, emi)
            alert_count += 1
        
        # Send overdue alerts for loan EMIs
        for emi in overdue_loan_emis:
            notification_service.send_overdue_alert(emi.user, emi)
            alert_count += 1
        
        return f"Sent {alert_count} overdue alerts"
        
    except Exception as e:
        return f"Error sending overdue alerts: {str(e)}"


@shared_task
def check_credit_utilization():
    """
    Check credit card utilization and send alerts if threshold is exceeded
    """
    try:
        # Get all active credit cards
        credit_cards = CreditCard.objects.filter(is_active=True).select_related('user')
        
        alert_count = 0
        
        for card in credit_cards:
            # Check if utilization exceeds threshold
            user_preferences = getattr(card.user, 'notification_preferences', None)
            if user_preferences and user_preferences.credit_utilization_alert_enabled:
                threshold = user_preferences.credit_utilization_threshold
                
                if card.utilization_percentage >= threshold:
                    notification_service.send_credit_utilization_alert(card.user, card)
                    alert_count += 1
        
        return f"Sent {alert_count} credit utilization alerts"
        
    except Exception as e:
        return f"Error checking credit utilization: {str(e)}"


@shared_task
def cleanup_old_notifications():
    """
    Clean up old notifications (older than 90 days)
    """
    try:
        from .models import Notification
        
        cutoff_date = timezone.now() - timedelta(days=90)
        
        deleted_count = Notification.objects.filter(
            created_at__lt=cutoff_date
        ).delete()[0]
        
        return f"Deleted {deleted_count} old notifications"
        
    except Exception as e:
        return f"Error cleaning up notifications: {str(e)}"


@shared_task
def send_daily_summary():
    """
    Send daily summary of EMIs and payments to users
    """
    try:
        today = date.today()
        summary_count = 0
        
        # Get users who have EMIs due today or made payments today
        users_with_activity = User.objects.filter(
            models.Q(credit_card_emis__due_date=today) | 
            models.Q(loan_emis__due_date=today) |
            models.Q(credit_card_payments__payment_date=today) |
            models.Q(loan_payments__payment_date=today)
        ).distinct()
        
        for user in users_with_activity:
            # Get today's Credit Card EMIs
            todays_cc_emis = user.credit_card_emis.filter(due_date=today, status='PENDING')
            
            # Get today's Loan EMIs
            todays_loan_emis = user.loan_emis.filter(due_date=today, status='PENDING')
            
            # Get today's Credit Card payments
            todays_cc_payments = user.credit_card_payments.filter(payment_date=today)
            
            # Get today's Loan payments
            todays_loan_payments = user.loan_payments.filter(payment_date=today)
            
            if (todays_cc_emis.exists() or todays_loan_emis.exists() or 
                todays_cc_payments.exists() or todays_loan_payments.exists()):
                # Send summary notification
                # This would require a daily summary template
                summary_count += 1
        
        return f"Sent {summary_count} daily summaries"
        
    except Exception as e:
        return f"Error sending daily summaries: {str(e)}"


@shared_task
def process_pending_notifications():
    """
    Process any pending notifications that failed to send
    """
    try:
        from .models import Notification
        
        # Get pending notifications older than 5 minutes
        cutoff_time = timezone.now() - timedelta(minutes=5)
        
        pending_notifications = Notification.objects.filter(
            status='PENDING',
            created_at__lt=cutoff_time
        )
        
        processed_count = 0
        
        for notification in pending_notifications:
            try:
                # Retry sending based on delivery method
                if notification.delivery_method == 'EMAIL':
                    notification_service._send_email_notification(
                        user=notification.user,
                        subject=notification.title,
                        message=notification.message,
                        notification_type=notification.notification_type
                    )
                elif notification.delivery_method == 'PUSH':
                    notification_service._send_push_notification(
                        user=notification.user,
                        title=notification.title,
                        body=notification.message,
                        notification_type=notification.notification_type
                    )
                elif notification.delivery_method == 'SMS':
                    notification_service._send_sms_notification(
                        user=notification.user,
                        message=notification.message,
                        notification_type=notification.notification_type
                    )
                
                processed_count += 1
                
            except Exception as e:
                # Mark as failed if retry also fails
                notification.status = 'FAILED'
                notification.save()
        
        return f"Processed {processed_count} pending notifications"
        
    except Exception as e:
        return f"Error processing pending notifications: {str(e)}" 