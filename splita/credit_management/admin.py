from django.contrib import admin
from .models import CreditCard, Loan, EMI, Payment, EMIReminder


@admin.register(CreditCard)
class CreditCardAdmin(admin.ModelAdmin):
    """
    Admin configuration for CreditCard model
    """
    list_display = ('card_name', 'user', 'bank_name', 'card_type', 'last_four_digits', 
                   'credit_limit', 'current_balance', 'utilization_percentage', 'is_active')
    list_filter = ('card_type', 'bank_name', 'is_active', 'created_at')
    search_fields = ('card_name', 'user__email', 'user__username', 'bank_name', 'last_four_digits')
    readonly_fields = ('available_credit', 'utilization_percentage', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Card Information', {
            'fields': ('user', 'card_name', 'card_type', 'bank_name', 'last_four_digits')
        }),
        ('Financial Details', {
            'fields': ('credit_limit', 'current_balance', 'minimum_payment', 'interest_rate',
                      'available_credit', 'utilization_percentage')
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
        }),
    )


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    """
    Admin configuration for Loan model
    """
    list_display = ('loan_name', 'user', 'loan_type', 'lender_name', 'principal_amount',
                   'current_balance', 'monthly_emi', 'completion_percentage', 'is_active')
    list_filter = ('loan_type', 'lender_name', 'is_active', 'start_date', 'created_at')
    search_fields = ('loan_name', 'user__email', 'user__username', 'lender_name')
    readonly_fields = ('end_date', 'remaining_months', 'total_paid', 'completion_percentage', 
                      'created_at', 'updated_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Loan Information', {
            'fields': ('user', 'loan_name', 'loan_type', 'lender_name')
        }),
        ('Financial Details', {
            'fields': ('principal_amount', 'current_balance', 'interest_rate', 'monthly_emi',
                      'total_paid', 'completion_percentage')
        }),
        ('Term Details', {
            'fields': ('loan_term_months', 'start_date', 'end_date', 'remaining_months')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(EMI)
class EMIAdmin(admin.ModelAdmin):
    """
    Admin configuration for EMI model
    """
    list_display = ('user', 'emi_type', 'emi_amount', 'due_date', 'status', 
                   'paid_amount', 'is_overdue', 'is_auto_generated')
    list_filter = ('emi_type', 'status', 'is_auto_generated', 'due_date', 'created_at')
    search_fields = ('user__email', 'user__username', 'credit_card__card_name', 'loan__loan_name')
    readonly_fields = ('is_overdue', 'remaining_amount', 'created_at', 'updated_at')
    ordering = ('-due_date',)
    date_hierarchy = 'due_date'
    
    fieldsets = (
        ('EMI Information', {
            'fields': ('user', 'emi_type', 'credit_card', 'loan')
        }),
        ('Payment Details', {
            'fields': ('emi_amount', 'due_date', 'status', 'paid_amount', 'paid_date',
                      'remaining_amount', 'late_fee', 'total_duration')
        }),
        ('System Information', {
            'fields': ('is_auto_generated', 'is_overdue')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """
    Admin configuration for Payment model
    """
    list_display = ('user', 'emi', 'amount', 'payment_method', 'payment_date', 'transaction_id')
    list_filter = ('payment_method', 'payment_date', 'created_at')
    search_fields = ('user__email', 'user__username', 'transaction_id', 'emi__id')
    readonly_fields = ('created_at',)
    ordering = ('-payment_date',)
    date_hierarchy = 'payment_date'
    
    fieldsets = (
        ('Payment Information', {
            'fields': ('user', 'emi', 'amount', 'payment_method', 'payment_date')
        }),
        ('Transaction Details', {
            'fields': ('transaction_id', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(EMIReminder)
class EMIReminderAdmin(admin.ModelAdmin):
    """
    Admin configuration for EMIReminder model
    """
    list_display = ('user', 'emi', 'reminder_type', 'reminder_date', 'is_sent', 'sent_at')
    list_filter = ('reminder_type', 'is_sent', 'reminder_date', 'created_at')
    search_fields = ('user__email', 'user__username', 'emi__id')
    readonly_fields = ('created_at',)
    ordering = ('-reminder_date',)
    date_hierarchy = 'reminder_date'
    
    fieldsets = (
        ('Reminder Information', {
            'fields': ('user', 'emi', 'reminder_type', 'reminder_date')
        }),
        ('Message', {
            'fields': ('message',)
        }),
        ('Status', {
            'fields': ('is_sent', 'sent_at')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
