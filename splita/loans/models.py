from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from datetime import date
from dateutil.utils import today
from django.db.models import Sum
import calendar

User = get_user_model()


class Loan(models.Model):
    """
    Model for Loans
    """
    LOAN_TYPES = [
        ('PERSONAL', 'Personal Loan'),
        ('HOME', 'Home Loan'),
        ('CAR', 'Car Loan'),
        ('EDUCATION', 'Education Loan'),
        ('BUSINESS', 'Business Loan'),
        ('OTHER', 'Other'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='loans')
    loan_name = models.CharField(max_length=100)
    loan_type = models.CharField(max_length=20, choices=LOAN_TYPES)
    lender_name = models.CharField(max_length=100)
    principal_amount = models.DecimalField(max_digits=15, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    current_balance = models.DecimalField(max_digits=15, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))])
    loan_term_months = models.IntegerField(validators=[MinValueValidator(1)])
    start_date = models.DateField()
    end_date = models.DateField()
    monthly_emi = models.DecimalField(max_digits=12, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.end_date:
            self.end_date = self.start_date + relativedelta(months=self.loan_term_months)
        if not self.current_balance:
            self.current_balance = self.principal_amount
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.loan_name} - {self.lender_name}"
    
    @property
    def remaining_months(self):
        today = date.today()
        if today >= self.end_date:
            return 0
        return (self.end_date.year - today.year) * 12 + (self.end_date.month - today.month)
    
    @property
    def total_paid(self):
        return self.principal_amount - self.current_balance
    
    @property
    def completion_percentage(self):
        if self.principal_amount > 0:
            return (self.total_paid / self.principal_amount) * 100
        return 0
    
    @property
    def emi_amount(self):
        """Return the monthly EMI amount"""
        return self.monthly_emi
    
    @property
    def remaining_amount(self):
        """Return the remaining loan amount"""
        return self.current_balance
    
    @property
    def is_due_this_month(self):
        """Check if loan EMI is due this month"""
        today = date.today()
        if today >= self.end_date:
            return False
        # For simplicity, assume loan EMI is due every month if loan is active
        return self.remaining_months > 0
    
    @property
    def next_due_date(self):
        """Get next due date for loan EMI"""
        today = date.today()
        if today >= self.end_date:
            return None
        # For simplicity, return next month's same day as start date
        next_month = today.replace(day=self.start_date.day) + relativedelta(months=1)
        return next_month if next_month <= self.end_date else None
    
    class Meta:
        db_table = 'loans'


class LoanEMI(models.Model):
    """
    Model for Loan EMI schedules
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PAID', 'Paid'),
        ('OVERDUE', 'Overdue'),
        ('PARTIAL', 'Partially Paid'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='loan_emis')
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='emis')
    emi_amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    start_date = models.DateField(help_text="Start date of the EMI plan")
    end_date = models.DateField(help_text="End date of the EMI plan")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    paid_date = models.DateField(null=True, blank=True)
    late_fee = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    description = models.CharField(max_length=200, blank=True, null=True, help_text="Description or purpose of the EMI")
    total_duration = models.IntegerField(default=1, help_text="Total duration of the EMI plan in months")
    is_auto_generated = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        """Override save to calculate end_date if not provided"""
        # Calculate end_date if not provided
        if self.start_date and not self.end_date and self.total_duration:
            # Calculate end date as start_date + (total_duration - 1) months
            end_month = self.start_date.month + self.total_duration - 1
            end_year = self.start_date.year + (end_month - 1) // 12
            end_month = ((end_month - 1) % 12) + 1
            try:
                self.end_date = date(end_year, end_month, self.start_date.day)
            except ValueError:
                # Handle end-of-month edge cases
                last_day = calendar.monthrange(end_year, end_month)[1]
                self.end_date = date(end_year, end_month, min(self.start_date.day, last_day))
                
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"EMI - {self.loan} - {self.start_date} to {self.end_date}"
    
    def get_due_date_for_month(self, year, month):
        """Calculate due date for a specific month based on start_date"""
        if not self.start_date:
            return None
            
        # Check if the requested month is within the EMI period
        start_year_month = (self.start_date.year, self.start_date.month)
        end_year_month = (self.end_date.year, self.end_date.month) if self.end_date else (9999, 12)
        requested_year_month = (year, month)
        
        if requested_year_month < start_year_month or requested_year_month > end_year_month:
            return None
            
        try:
            due_date = date(year, month, self.start_date.day)
        except ValueError:
            # Handle cases where the day doesn't exist in the month (e.g., Feb 30)
            last_day = calendar.monthrange(year, month)[1]
            due_date = date(year, month, min(self.start_date.day, last_day))
        
        return due_date
    
    @property
    def current_month_due_date(self):
        """Get the due date for current month if any"""
        today = date.today()
        return self.get_due_date_for_month(today.year, today.month)
    
    @property
    def is_overdue(self):
        next_due = self.next_due_date
        return next_due and date.today() > next_due and self.status != 'PAID'
    
    @property
    def remaining_amount(self):
        """Calculate remaining amount based on completed months"""
        total_emi_amount = self.emi_amount * self.total_duration
        completed_amount = self.completed_months * self.emi_amount
        return total_emi_amount - completed_amount
    
    @property
    def amount(self):
        """Alias for emi_amount for consistency"""
        return self.emi_amount
    
    @property
    def months_remaining(self):
        """Calculate months remaining from start date based on today's date"""
        return self.get_months_remaining()
    
    def get_months_remaining(self, reference_date=None):
        """Calculate months remaining from start date based on reference date"""
        if not self.start_date:
            return 0
            
        if reference_date is None:
            reference_date = date.today()
        
        # Calculate how many months have passed since start
        months_passed = (reference_date.year - self.start_date.year) * 12 + (reference_date.month - self.start_date.month)
        
        # If reference date's day is before the EMI day, subtract one month
        if reference_date.day < self.start_date.day:
            months_passed -= 1
            
        # Ensure we don't go negative
        months_passed = max(0, months_passed)
        
        return max(0, self.total_duration - months_passed)
    
    @property
    def total_months(self):
        """Return total duration"""
        return self.total_duration
    
    @property
    def completed_months(self):
        """Calculate completed months based on today's date"""
        return self.get_completed_months()
    
    def get_completed_months(self, reference_date=None):
        """Calculate completed months based on reference date"""
        return max(0, self.total_duration - self.get_months_remaining(reference_date))
    
    @property
    def progress_months(self):
        """Calculate progress in months based on today's date"""
        return self.get_progress_months()
    
    def get_progress_months(self, reference_date=None):
        """Calculate progress in months based on reference date"""
        completed = self.get_completed_months(reference_date)
        if self.total_duration > 0:
            return (completed / self.total_duration) * 100
        return 0
    
    @property
    def next_due_date(self):
        """Get the next upcoming payment date based on start_date"""
        if not self.start_date or self.months_remaining <= 0:
            return None
            
        today = date.today()
        
        # Calculate next payment date
        months_passed = self.completed_months
        next_payment_month = self.start_date.month + months_passed
        next_payment_year = self.start_date.year + (next_payment_month - 1) // 12
        next_payment_month = ((next_payment_month - 1) % 12) + 1
        
        try:
            next_date = date(next_payment_year, next_payment_month, self.start_date.day)
        except ValueError:
            # Handle cases where the day doesn't exist in the month (e.g., Feb 30)
            last_day = calendar.monthrange(next_payment_year, next_payment_month)[1]
            next_date = date(next_payment_year, next_payment_month, min(self.start_date.day, last_day))
        
        # If the calculated date is in the past (but not today), move to next month
        if next_date < today and self.months_remaining > 0:
            next_payment_month += 1
            if next_payment_month > 12:
                next_payment_month = 1
                next_payment_year += 1
            try:
                next_date = date(next_payment_year, next_payment_month, self.start_date.day)
            except ValueError:
                last_day = calendar.monthrange(next_payment_year, next_payment_month)[1]
                next_date = date(next_payment_year, next_payment_month, min(self.start_date.day, last_day))
        
        return next_date
    
    def get_all_payment_dates(self):
        """Get all payment dates for this EMI plan based on start_date and end_date"""
        if not self.start_date:
            return []
            
        payment_dates = []
        
        for month_offset in range(self.total_duration):
            payment_month = self.start_date.month + month_offset
            payment_year = self.start_date.year + (payment_month - 1) // 12
            payment_month = ((payment_month - 1) % 12) + 1
            
            try:
                payment_date = date(payment_year, payment_month, self.start_date.day)
            except ValueError:
                # Handle end-of-month edge cases (e.g., Jan 31 -> Feb 28)
                last_day = calendar.monthrange(payment_year, payment_month)[1]
                payment_date = date(payment_year, payment_month, min(self.start_date.day, last_day))
            
            # Stop if we've passed the end_date
            if self.end_date and payment_date > self.end_date:
                break
                
            payment_dates.append(payment_date)
        
        return payment_dates
    
    def get_upcoming_payment_dates(self, limit=None):
        """Get upcoming payment dates that are not yet paid"""
        today = date.today()
        all_dates = self.get_all_payment_dates()
        upcoming = [d for d in all_dates if d >= today]
        
        if limit:
            upcoming = upcoming[:limit]
        
        return upcoming
    
    @property
    def is_due_this_month(self):
        """Check if there's a payment due this month"""
        today = date.today()
        next_due = self.next_due_date
        if not next_due:
            return False
        return (next_due.year == today.year and next_due.month == today.month)
    
    def mark_as_paid(self, amount=None, payment_date=None):
        """Mark EMI as paid"""
        if amount is None:
            amount = self.remaining_amount
        
        self.paid_amount += amount
        self.paid_date = payment_date or date.today()
        
        if self.paid_amount >= self.emi_amount:
            self.status = 'PAID'
        elif self.paid_amount > 0:
            self.status = 'PARTIAL'
        
        self.save()
    
    class Meta:
        db_table = 'loan_emis'
        ordering = ['start_date']


class LoanPayment(models.Model):
    """
    Model to track payments made towards Loan EMIs
    """
    PAYMENT_METHODS = [
        ('CASH', 'Cash'),
        ('BANK_TRANSFER', 'Bank Transfer'),
        ('UPI', 'UPI'),
        ('CREDIT_CARD', 'Credit Card'),
        ('DEBIT_CARD', 'Debit Card'),
        ('NET_BANKING', 'Net Banking'),
        ('OTHER', 'Other'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='loan_payments')
    emi = models.ForeignKey(LoanEMI, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    payment_date = models.DateField()
    transaction_id = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Payment - {self.emi} - {self.amount}"
    
    class Meta:
        db_table = 'loan_payments'
        ordering = ['-payment_date']


class LoanEMIReminder(models.Model):
    """
    Model for Loan EMI reminders and notifications
    """
    REMINDER_TYPES = [
        ('EMAIL', 'Email'),
        ('SMS', 'SMS'),
        ('PUSH', 'Push Notification'),
        ('IN_APP', 'In-App Notification'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='loan_emi_reminders')
    emi = models.ForeignKey(LoanEMI, on_delete=models.CASCADE, related_name='reminders')
    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPES)
    reminder_date = models.DateTimeField()
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Reminder - {self.emi} - {self.reminder_type}"
    
    class Meta:
        db_table = 'loan_emi_reminders'
        ordering = ['reminder_date']
