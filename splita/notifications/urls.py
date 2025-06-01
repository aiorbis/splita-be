from django.urls import path
from .views import (
    NotificationListView, NotificationDetailView, MarkNotificationReadView,
    MarkAllNotificationsReadView, NotificationPreferenceView,
    NotificationTemplateListView, NotificationTemplateDetailView,
    TriggerNotificationView, trigger_emi_reminders, trigger_overdue_alerts,
    trigger_credit_utilization_check, notification_stats
)

app_name = 'notifications'

urlpatterns = [
    # Notification URLs
    path('', NotificationListView.as_view(), name='notification_list'),
    path('<int:pk>/', NotificationDetailView.as_view(), name='notification_detail'),
    path('<int:notification_id>/mark-read/', MarkNotificationReadView.as_view(), name='mark_notification_read'),
    path('mark-all-read/', MarkAllNotificationsReadView.as_view(), name='mark_all_notifications_read'),
    path('stats/', notification_stats, name='notification_stats'),
    
    # Notification Preferences
    path('preferences/', NotificationPreferenceView.as_view(), name='notification_preferences'),
    
    # Notification Templates (Admin only)
    path('templates/', NotificationTemplateListView.as_view(), name='notification_template_list'),
    path('templates/<int:pk>/', NotificationTemplateDetailView.as_view(), name='notification_template_detail'),
    
    # Manual Triggers (Admin only)
    path('trigger/', TriggerNotificationView.as_view(), name='trigger_notification'),
    path('trigger/emi-reminders/', trigger_emi_reminders, name='trigger_emi_reminders'),
    path('trigger/overdue-alerts/', trigger_overdue_alerts, name='trigger_overdue_alerts'),
    path('trigger/credit-utilization/', trigger_credit_utilization_check, name='trigger_credit_utilization'),
] 