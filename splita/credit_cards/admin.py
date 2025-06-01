from django.contrib import admin
from .models import CreditCard, CreditCardEMI, CreditCardPayment, CreditCardEMIReminder


@admin.register(CreditCard)
class CreditCardAdmin(admin.ModelAdmin):
    list_display = ('card_name', 'user', 'bank_name', 'last_four_digits', 'credit_limit', 'current_balance', 'is_active', 'created_at')
    list_filter = ('card_type', 'bank_name', 'is_active', 'created_at')
    search_fields = ('card_name', 'user__username', 'user__email', 'bank_name', 'last_four_digits')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'card_name', 'card_type', 'bank_name', 'last_four_digits')
        }),
        ('Financial Details', {
            'fields': ('credit_limit', 'current_balance', 'minimum_payment', 'interest_rate')
        }),
        ('Billing Information', {
            'fields': ('billing_cycle_day', 'payment_due_day')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(CreditCardEMI)
class CreditCardEMIAdmin(admin.ModelAdmin):
    list_display = ('credit_card', 'user', 'emi_amount', 'total_emi_amount', 'start_date', 'end_date', 'status', 'paid_amount', 'remaining_amount', 'months_remaining')
    list_filter = ('status', 'start_date', 'is_auto_generated', 'created_at')
    search_fields = ('credit_card__card_name', 'user__username', 'user__email', 'description')
    readonly_fields = ('total_emi_amount', 'created_at', 'updated_at', 'is_overdue', 'remaining_amount', 'months_remaining', 'completed_months', 'progress_months')
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('EMI Information', {
            'fields': ('user', 'credit_card', 'emi_amount', 'total_emi_amount', 'total_duration', 'start_date', 'end_date', 'status')
        }),
        ('Payment Details', {
            'fields': ('paid_amount', 'paid_date', 'late_fee')
        }),
        ('Additional Information', {
            'fields': ('description', 'is_auto_generated')
        }),
        ('Computed Fields', {
            'fields': ('remaining_amount', 'months_remaining', 'completed_months', 'progress_months', 'is_overdue'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(CreditCardPayment)
class CreditCardPaymentAdmin(admin.ModelAdmin):
    list_display = ('emi', 'user', 'amount', 'payment_method', 'payment_date', 'transaction_id')
    list_filter = ('payment_method', 'payment_date', 'created_at')
    search_fields = ('user__username', 'user__email', 'transaction_id', 'emi__credit_card__card_name')
    readonly_fields = ('created_at',)
    date_hierarchy = 'payment_date'


@admin.register(CreditCardEMIReminder)
class CreditCardEMIReminderAdmin(admin.ModelAdmin):
    list_display = ('emi', 'user', 'reminder_type', 'reminder_date', 'is_sent', 'sent_at')
    list_filter = ('reminder_type', 'is_sent', 'reminder_date', 'created_at')
    search_fields = ('user__username', 'user__email', 'emi__credit_card__card_name')
    readonly_fields = ('created_at',)
    date_hierarchy = 'reminder_date'
