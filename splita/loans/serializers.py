from rest_framework import serializers
from decimal import Decimal
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from .models import Loan, LoanEMI, LoanPayment, LoanEMIReminder


class LoanSerializer(serializers.ModelSerializer):
    """
    Serializer for Loan model
    """
    remaining_months = serializers.ReadOnlyField()
    total_paid = serializers.ReadOnlyField()
    completion_percentage = serializers.ReadOnlyField()
    
    class Meta:
        model = Loan
        fields = '__all__'
        read_only_fields = ('user', 'end_date', 'created_at', 'updated_at')
    
    def validate(self, attrs):
        if attrs.get('current_balance', 0) > attrs.get('principal_amount', 0):
            raise serializers.ValidationError("Current balance cannot exceed principal amount")
        
        start_date = attrs.get('start_date')
        if start_date and start_date > date.today():
            # Allow future start dates but validate they're reasonable
            if start_date > date.today() + timedelta(days=365):
                raise serializers.ValidationError("Start date cannot be more than 1 year in the future")
        
        return attrs


class LoanEMISerializer(serializers.ModelSerializer):
    """
    Serializer for Loan EMI model
    """
    is_overdue = serializers.ReadOnlyField()
    remaining_amount = serializers.ReadOnlyField()
    loan_name = serializers.CharField(source='loan.loan_name', read_only=True)
    total_months = serializers.ReadOnlyField()
    completed_months = serializers.ReadOnlyField()
    progress_months = serializers.ReadOnlyField()
    amount = serializers.ReadOnlyField()  # Alias for emi_amount
    
    class Meta:
        model = LoanEMI
        fields = '__all__'
        read_only_fields = ('user', 'created_at', 'updated_at')
    
    def validate(self, attrs):
        # Set default total_duration if not provided
        if not attrs.get('total_duration'):
            attrs['total_duration'] = 1
        
        return attrs


class LoanPaymentSerializer(serializers.ModelSerializer):
    """
    Serializer for Loan Payment model
    """
    emi_details = LoanEMISerializer(source='emi', read_only=True)
    
    class Meta:
        model = LoanPayment
        fields = '__all__'
        read_only_fields = ('user', 'created_at')
    
    def validate(self, attrs):
        emi = attrs.get('emi')
        amount = attrs.get('amount')
        
        if emi and amount:
            if amount > emi.remaining_amount:
                raise serializers.ValidationError(
                    f"Payment amount cannot exceed remaining EMI amount of {emi.remaining_amount}"
                )
        
        return attrs


class LoanEMIReminderSerializer(serializers.ModelSerializer):
    """
    Serializer for Loan EMI Reminder model
    """
    emi_details = LoanEMISerializer(source='emi', read_only=True)
    
    class Meta:
        model = LoanEMIReminder
        fields = '__all__'
        read_only_fields = ('user', 'is_sent', 'sent_at', 'created_at')


class LoanEMIScheduleSerializer(serializers.Serializer):
    """
    Serializer for generating Loan EMI schedules
    """
    loan_id = serializers.IntegerField()
    start_date = serializers.DateField()
    number_of_emis = serializers.IntegerField(min_value=1, max_value=360)
    emi_amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.01'))


class LoanSummarySerializer(serializers.Serializer):
    """
    Serializer for loan summary
    """
    total_loans = serializers.IntegerField()
    total_principal_amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    total_current_balance = serializers.DecimalField(max_digits=18, decimal_places=2)
    total_paid_amount = serializers.DecimalField(max_digits=18, decimal_places=2)
    average_completion_percentage = serializers.DecimalField(max_digits=5, decimal_places=2) 