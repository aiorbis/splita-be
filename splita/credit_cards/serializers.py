from rest_framework import serializers
from decimal import Decimal
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from .models import CreditCard, CreditCardEMI, CreditCardPayment, CreditCardEMIReminder


class CreditCardSerializer(serializers.ModelSerializer):
    """
    Serializer for Credit Card model
    """
    available_credit = serializers.ReadOnlyField()
    utilization_percentage = serializers.ReadOnlyField()
    total_emi_amount = serializers.ReadOnlyField()
    emi_count = serializers.ReadOnlyField()
    total_remaining_amount = serializers.ReadOnlyField()
    
    class Meta:
        model = CreditCard
        fields = '__all__'
        read_only_fields = ('user', 'created_at', 'updated_at')
    
    def validate_last_four_digits(self, value):
        if not value.isdigit() or len(value) != 4:
            raise serializers.ValidationError("Last four digits must be exactly 4 digits")
        return value
    
    def validate(self, attrs):
        if attrs.get('current_balance', 0) > attrs.get('credit_limit', 0):
            raise serializers.ValidationError("Current balance cannot exceed credit limit")
        return attrs


class CreditCardEMISerializer(serializers.ModelSerializer):
    """
    Serializer for Credit Card EMI model
    """
    is_overdue = serializers.ReadOnlyField()
    remaining_amount = serializers.ReadOnlyField()
    credit_card_name = serializers.CharField(source='credit_card.card_name', read_only=True)
    total_months = serializers.ReadOnlyField()
    completed_months = serializers.ReadOnlyField()
    progress_months = serializers.ReadOnlyField()
    amount = serializers.ReadOnlyField()
    months_remaining = serializers.ReadOnlyField()
    
    class Meta:
        model = CreditCardEMI
        fields = '__all__'
        read_only_fields = ('user', 'total_emi_amount', 'created_at', 'updated_at')
    
    def validate(self, attrs):
        # Set default total_duration if not provided
        if not attrs.get('total_duration'):
            attrs['total_duration'] = 1
        
        return attrs


class CreditCardPaymentSerializer(serializers.ModelSerializer):
    """
    Serializer for Credit Card Payment model
    """
    emi_details = CreditCardEMISerializer(source='emi', read_only=True)
    
    class Meta:
        model = CreditCardPayment
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


class CreditCardEMIReminderSerializer(serializers.ModelSerializer):
    """
    Serializer for Credit Card EMI Reminder model
    """
    emi_details = CreditCardEMISerializer(source='emi', read_only=True)
    
    class Meta:
        model = CreditCardEMIReminder
        fields = '__all__'
        read_only_fields = ('user', 'is_sent', 'sent_at', 'created_at')


class CreditCardEMIScheduleSerializer(serializers.Serializer):
    """
    Serializer for generating Credit Card EMI schedules
    """
    credit_card_id = serializers.IntegerField()
    start_date = serializers.DateField()
    number_of_emis = serializers.IntegerField(min_value=1, max_value=360)
    emi_amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.01'))


class CreditCardSummarySerializer(serializers.Serializer):
    """
    Serializer for credit card summary
    """
    total_cards = serializers.IntegerField()
    total_credit_limit = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_current_balance = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_available_credit = serializers.DecimalField(max_digits=15, decimal_places=2)
    average_utilization = serializers.DecimalField(max_digits=5, decimal_places=2) 