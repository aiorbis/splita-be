from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from pyfcm import FCMNotification
import logging

from .models import Notification, NotificationTemplate, NotificationPreference

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service class for handling all types of notifications
    """
    
    def __init__(self):
        self.fcm = FCMNotification(api_key=settings.FIREBASE_SERVER_KEY) if settings.FIREBASE_SERVER_KEY else None
    
    def send_emi_reminder(self, user, emi):
        """
        Send EMI reminder notification
        """
        try:
            # Get user notification preferences
            preferences = getattr(user, 'notification_preferences', None)
            if not preferences:
                # Create default preferences if not exists
                preferences = NotificationPreference.objects.create(user=user)
            
            # Get notification template
            template = NotificationTemplate.objects.filter(
                template_type='EMI_REMINDER',
                is_active=True
            ).first()
            
            if not template:
                logger.warning("EMI reminder template not found")
                return
            
            # Prepare context data
            context = {
                'user_name': user.first_name or user.username,
                'emi_amount': emi.emi_amount,
                'due_date': emi.due_date,
                'card_name': emi.credit_card.card_name if emi.credit_card else None,
                'loan_name': emi.loan.loan_name if emi.loan else None,
            }
            
            # Send email notification
            if preferences.emi_email_enabled and template.email_subject and template.email_body:
                self._send_email_notification(
                    user=user,
                    subject=template.email_subject.format(**context),
                    message=template.email_body.format(**context),
                    notification_type='EMI_REMINDER',
                    emi_id=emi.id
                )
            
            # Send push notification
            if preferences.emi_push_enabled and template.push_title and template.push_body:
                self._send_push_notification(
                    user=user,
                    title=template.push_title.format(**context),
                    body=template.push_body.format(**context),
                    notification_type='EMI_REMINDER',
                    emi_id=emi.id
                )
            
            # Send SMS notification (placeholder - implement with your SMS provider)
            if preferences.emi_sms_enabled and template.sms_body:
                self._send_sms_notification(
                    user=user,
                    message=template.sms_body.format(**context),
                    notification_type='EMI_REMINDER',
                    emi_id=emi.id
                )
                
        except Exception as e:
            logger.error(f"Error sending EMI reminder: {str(e)}")
    
    def send_payment_confirmation(self, user, payment):
        """
        Send payment confirmation notification
        """
        try:
            preferences = getattr(user, 'notification_preferences', None)
            if not preferences:
                preferences = NotificationPreference.objects.create(user=user)
            
            template = NotificationTemplate.objects.filter(
                template_type='PAYMENT_CONFIRMATION',
                is_active=True
            ).first()
            
            if not template:
                logger.warning("Payment confirmation template not found")
                return
            
            context = {
                'user_name': user.first_name or user.username,
                'payment_amount': payment.amount,
                'payment_date': payment.payment_date,
                'emi_amount': payment.emi.emi_amount,
                'due_date': payment.emi.due_date,
            }
            
            # Send email notification
            if preferences.payment_confirmation_email and template.email_subject and template.email_body:
                self._send_email_notification(
                    user=user,
                    subject=template.email_subject.format(**context),
                    message=template.email_body.format(**context),
                    notification_type='PAYMENT_CONFIRMATION'
                )
            
            # Send push notification
            if preferences.payment_confirmation_push and template.push_title and template.push_body:
                self._send_push_notification(
                    user=user,
                    title=template.push_title.format(**context),
                    body=template.push_body.format(**context),
                    notification_type='PAYMENT_CONFIRMATION'
                )
                
        except Exception as e:
            logger.error(f"Error sending payment confirmation: {str(e)}")
    
    def send_overdue_alert(self, user, emi):
        """
        Send overdue EMI alert
        """
        try:
            preferences = getattr(user, 'notification_preferences', None)
            if not preferences:
                preferences = NotificationPreference.objects.create(user=user)
            
            template = NotificationTemplate.objects.filter(
                template_type='OVERDUE_ALERT',
                is_active=True
            ).first()
            
            if not template:
                logger.warning("Overdue alert template not found")
                return
            
            context = {
                'user_name': user.first_name or user.username,
                'emi_amount': emi.emi_amount,
                'due_date': emi.due_date,
                'days_overdue': (timezone.now().date() - emi.due_date).days,
                'card_name': emi.credit_card.card_name if emi.credit_card else None,
                'loan_name': emi.loan.loan_name if emi.loan else None,
            }
            
            # Send email notification
            if preferences.overdue_email_enabled and template.email_subject and template.email_body:
                self._send_email_notification(
                    user=user,
                    subject=template.email_subject.format(**context),
                    message=template.email_body.format(**context),
                    notification_type='OVERDUE_ALERT',
                    emi_id=emi.id
                )
            
            # Send push notification
            if preferences.overdue_push_enabled and template.push_title and template.push_body:
                self._send_push_notification(
                    user=user,
                    title=template.push_title.format(**context),
                    body=template.push_body.format(**context),
                    notification_type='OVERDUE_ALERT',
                    emi_id=emi.id
                )
            
            # Send SMS notification
            if preferences.overdue_sms_enabled and template.sms_body:
                self._send_sms_notification(
                    user=user,
                    message=template.sms_body.format(**context),
                    notification_type='OVERDUE_ALERT',
                    emi_id=emi.id
                )
                
        except Exception as e:
            logger.error(f"Error sending overdue alert: {str(e)}")
    
    def send_credit_utilization_alert(self, user, credit_card):
        """
        Send credit utilization alert
        """
        try:
            preferences = getattr(user, 'notification_preferences', None)
            if not preferences:
                preferences = NotificationPreference.objects.create(user=user)
            
            # Check if alert is enabled and threshold is exceeded
            if not preferences.credit_utilization_alert_enabled:
                return
            
            if credit_card.utilization_percentage < preferences.credit_utilization_threshold:
                return
            
            template = NotificationTemplate.objects.filter(
                template_type='CREDIT_UTILIZATION',
                is_active=True
            ).first()
            
            if not template:
                logger.warning("Credit utilization alert template not found")
                return
            
            context = {
                'user_name': user.first_name or user.username,
                'card_name': credit_card.card_name,
                'utilization_percentage': round(credit_card.utilization_percentage, 2),
                'current_balance': credit_card.current_balance,
                'credit_limit': credit_card.credit_limit,
            }
            
            # Send email notification
            if template.email_subject and template.email_body:
                self._send_email_notification(
                    user=user,
                    subject=template.email_subject.format(**context),
                    message=template.email_body.format(**context),
                    notification_type='CREDIT_UTILIZATION',
                    credit_card_id=credit_card.id
                )
            
            # Send push notification
            if template.push_title and template.push_body:
                self._send_push_notification(
                    user=user,
                    title=template.push_title.format(**context),
                    body=template.push_body.format(**context),
                    notification_type='CREDIT_UTILIZATION',
                    credit_card_id=credit_card.id
                )
                
        except Exception as e:
            logger.error(f"Error sending credit utilization alert: {str(e)}")
    
    def _send_email_notification(self, user, subject, message, notification_type, **kwargs):
        """
        Send email notification
        """
        try:
            # Create notification record
            notification = Notification.objects.create(
                user=user,
                notification_type=notification_type,
                delivery_method='EMAIL',
                title=subject,
                message=message,
                status='PENDING',
                **kwargs
            )
            
            # Send email
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            
            # Update notification status
            notification.status = 'SENT'
            notification.sent_at = timezone.now()
            notification.save()
            
            logger.info(f"Email notification sent to {user.email}")
            
        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}")
            if 'notification' in locals():
                notification.status = 'FAILED'
                notification.save()
    
    def _send_push_notification(self, user, title, body, notification_type, **kwargs):
        """
        Send push notification via FCM
        """
        try:
            if not self.fcm or not user.fcm_token:
                logger.warning(f"FCM not configured or user {user.email} has no FCM token")
                return
            
            # Create notification record
            notification = Notification.objects.create(
                user=user,
                notification_type=notification_type,
                delivery_method='PUSH',
                title=title,
                message=body,
                status='PENDING',
                **kwargs
            )
            
            # Send push notification
            result = self.fcm.notify_single_device(
                registration_id=user.fcm_token,
                message_title=title,
                message_body=body,
                data_message={
                    'notification_type': notification_type,
                    'notification_id': str(notification.id)
                }
            )
            
            # Update notification status
            if result.get('success'):
                notification.status = 'SENT'
                notification.fcm_message_id = result.get('message_id')
            else:
                notification.status = 'FAILED'
            
            notification.sent_at = timezone.now()
            notification.save()
            
            logger.info(f"Push notification sent to {user.email}")
            
        except Exception as e:
            logger.error(f"Error sending push notification: {str(e)}")
            if 'notification' in locals():
                notification.status = 'FAILED'
                notification.save()
    
    def _send_sms_notification(self, user, message, notification_type, **kwargs):
        """
        Send SMS notification (placeholder - implement with your SMS provider)
        """
        try:
            if not user.phone_number:
                logger.warning(f"User {user.email} has no phone number for SMS")
                return
            
            # Create notification record
            notification = Notification.objects.create(
                user=user,
                notification_type=notification_type,
                delivery_method='SMS',
                title='SMS Notification',
                message=message,
                status='PENDING',
                **kwargs
            )
            
            # TODO: Implement SMS sending with your preferred SMS provider
            # Example providers: Twilio, AWS SNS, etc.
            
            # For now, just mark as sent (placeholder)
            notification.status = 'SENT'
            notification.sent_at = timezone.now()
            notification.save()
            
            logger.info(f"SMS notification sent to {user.phone_number}")
            
        except Exception as e:
            logger.error(f"Error sending SMS notification: {str(e)}")
            if 'notification' in locals():
                notification.status = 'FAILED'
                notification.save()


# Global notification service instance
notification_service = NotificationService() 