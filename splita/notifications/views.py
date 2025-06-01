from django.shortcuts import render
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model

from .models import Notification, NotificationPreference, NotificationTemplate
from .serializers import (
    NotificationSerializer, NotificationPreferenceSerializer,
    NotificationTemplateSerializer, TriggerNotificationSerializer
)
from .services import notification_service
from .tasks import send_emi_reminders, send_overdue_alerts, check_credit_utilization

User = get_user_model()


class NotificationListView(generics.ListAPIView):
    """
    List all notifications for the authenticated user
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = Notification.objects.filter(user=self.request.user)
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by notification type
        type_filter = self.request.query_params.get('type', None)
        if type_filter:
            queryset = queryset.filter(notification_type=type_filter)
        
        # Filter by delivery method
        method_filter = self.request.query_params.get('method', None)
        if method_filter:
            queryset = queryset.filter(delivery_method=method_filter)
        
        return queryset.order_by('-created_at')


class NotificationDetailView(generics.RetrieveAPIView):
    """
    Retrieve a specific notification and mark it as read
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Mark notification as read if it's not already read
        if instance.status != 'READ':
            instance.mark_as_read()
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class MarkNotificationReadView(APIView):
    """
    Mark a notification as read
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, notification_id):
        try:
            notification = Notification.objects.get(
                id=notification_id,
                user=request.user
            )
            notification.mark_as_read()
            
            return Response({
                'message': 'Notification marked as read',
                'notification': NotificationSerializer(notification).data
            }, status=status.HTTP_200_OK)
            
        except Notification.DoesNotExist:
            return Response({
                'error': 'Notification not found'
            }, status=status.HTTP_404_NOT_FOUND)


class MarkAllNotificationsReadView(APIView):
    """
    Mark all notifications as read for the user
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        updated_count = Notification.objects.filter(
            user=request.user,
            status__in=['PENDING', 'SENT', 'DELIVERED']
        ).update(status='READ')
        
        return Response({
            'message': f'{updated_count} notifications marked as read'
        }, status=status.HTTP_200_OK)


class NotificationPreferenceView(generics.RetrieveUpdateAPIView):
    """
    Retrieve and update notification preferences
    """
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        preferences, created = NotificationPreference.objects.get_or_create(
            user=self.request.user
        )
        return preferences


class NotificationTemplateListView(generics.ListAPIView):
    """
    List all notification templates (admin only)
    """
    serializer_class = NotificationTemplateSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = NotificationTemplate.objects.all()


class NotificationTemplateDetailView(generics.RetrieveUpdateAPIView):
    """
    Retrieve and update notification templates (admin only)
    """
    serializer_class = NotificationTemplateSerializer
    permission_classes = [permissions.IsAdminUser]
    queryset = NotificationTemplate.objects.all()


class TriggerNotificationView(APIView):
    """
    Manually trigger notifications (admin only)
    """
    permission_classes = [permissions.IsAdminUser]
    
    def post(self, request):
        serializer = TriggerNotificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        notification_type = data['notification_type']
        title = data['title']
        message = data['message']
        delivery_methods = data['delivery_methods']
        user_ids = data.get('user_ids', [])
        
        # Get target users
        if user_ids:
            users = User.objects.filter(id__in=user_ids)
        else:
            users = User.objects.filter(is_active=True)
        
        sent_count = 0
        
        for user in users:
            for method in delivery_methods:
                try:
                    # Create notification record
                    notification = Notification.objects.create(
                        user=user,
                        notification_type=notification_type,
                        delivery_method=method,
                        title=title,
                        message=message,
                        status='PENDING'
                    )
                    
                    # Send notification based on method
                    if method == 'EMAIL':
                        notification_service._send_email_notification(
                            user=user,
                            subject=title,
                            message=message,
                            notification_type=notification_type
                        )
                    elif method == 'PUSH':
                        notification_service._send_push_notification(
                            user=user,
                            title=title,
                            body=message,
                            notification_type=notification_type
                        )
                    elif method == 'SMS':
                        notification_service._send_sms_notification(
                            user=user,
                            message=message,
                            notification_type=notification_type
                        )
                    
                    sent_count += 1
                    
                except Exception as e:
                    continue
        
        return Response({
            'message': f'Triggered {sent_count} notifications',
            'users_targeted': users.count(),
            'delivery_methods': delivery_methods
        }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def trigger_emi_reminders(request):
    """
    Manually trigger EMI reminders task
    """
    try:
        result = send_emi_reminders.delay()
        return Response({
            'message': 'EMI reminders task triggered',
            'task_id': result.id
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'error': f'Failed to trigger EMI reminders: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def trigger_overdue_alerts(request):
    """
    Manually trigger overdue alerts task
    """
    try:
        result = send_overdue_alerts.delay()
        return Response({
            'message': 'Overdue alerts task triggered',
            'task_id': result.id
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'error': f'Failed to trigger overdue alerts: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def trigger_credit_utilization_check(request):
    """
    Manually trigger credit utilization check task
    """
    try:
        result = check_credit_utilization.delay()
        return Response({
            'message': 'Credit utilization check task triggered',
            'task_id': result.id
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'error': f'Failed to trigger credit utilization check: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def notification_stats(request):
    """
    Get notification statistics for the user
    """
    user = request.user
    
    total_notifications = user.notifications.count()
    unread_notifications = user.notifications.filter(
        status__in=['PENDING', 'SENT', 'DELIVERED']
    ).count()
    read_notifications = user.notifications.filter(status='READ').count()
    failed_notifications = user.notifications.filter(status='FAILED').count()
    
    # Get counts by notification type
    type_counts = {}
    for choice in Notification.NOTIFICATION_TYPES:
        type_key = choice[0]
        type_counts[type_key] = user.notifications.filter(
            notification_type=type_key
        ).count()
    
    return Response({
        'total_notifications': total_notifications,
        'unread_notifications': unread_notifications,
        'read_notifications': read_notifications,
        'failed_notifications': failed_notifications,
        'type_counts': type_counts
    }, status=status.HTTP_200_OK)
