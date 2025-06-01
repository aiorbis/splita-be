from django.contrib import admin
from .models import Loan, LoanEMI, LoanPayment, LoanEMIReminder


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ('loan_name', 'user', 'lender_name', 'loan_type', 'principal_amount', 'current_balance', 'completion_percentage', 'is_active')
    list_filter = ('loan_type', 'lender_name', 'is_active', 'start_date', 'created_at')
    search_fields = ('loan_name', 'user__username', 'user__email', 'lender_name')
    readonly_fields = ('end_date', 'created_at', 'updated_at', 'remaining_months', 'total_paid', 'completion_percentage')
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'loan_name', 'loan_type', 'lender_name')
        }),
        ('Financial Details', {
            'fields': ('principal_amount', 'current_balance', 'interest_rate', 'monthly_emi')
        }),
        ('Loan Term', {
            'fields': ('loan_term_months', 'start_date', 'end_date')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Computed Fields', {
            'fields': ('remaining_months', 'total_paid', 'completion_percentage'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(LoanEMI)
class LoanEMIAdmin(admin.ModelAdmin):
    list_display = ('loan', 'user', 'emi_amount', 'start_date', 'end_date', 'status', 'paid_amount', 'is_overdue')
    list_filter = ('status', 'start_date', 'is_auto_generated', 'created_at')
    search_fields = ('loan__loan_name', 'user__username', 'user__email', 'description')
    readonly_fields = ('created_at', 'updated_at', 'is_overdue', 'remaining_amount')
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('EMI Information', {
            'fields': ('user', 'loan', 'emi_amount', 'start_date', 'end_date', 'total_duration', 'status')
        }),
        ('Payment Details', {
            'fields': ('paid_amount', 'paid_date', 'late_fee')
        }),
        ('Additional Information', {
            'fields': ('description', 'is_auto_generated')
        }),
        ('Computed Fields', {
            'fields': ('remaining_amount', 'is_overdue'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )


@admin.register(LoanPayment)
class LoanPaymentAdmin(admin.ModelAdmin):
    list_display = ('emi', 'user', 'amount', 'payment_method', 'payment_date', 'transaction_id')
    list_filter = ('payment_method', 'payment_date', 'created_at')
    search_fields = ('user__username', 'user__email', 'transaction_id', 'emi__loan__loan_name')
    readonly_fields = ('created_at',)
    date_hierarchy = 'payment_date'


@admin.register(LoanEMIReminder)
class LoanEMIReminderAdmin(admin.ModelAdmin):
    list_display = ('emi', 'user', 'reminder_type', 'reminder_date', 'is_sent', 'sent_at')
    list_filter = ('reminder_type', 'is_sent', 'reminder_date', 'created_at')
    search_fields = ('user__username', 'user__email', 'emi__loan__loan_name')
    readonly_fields = ('created_at',)
    date_hierarchy = 'reminder_date'
