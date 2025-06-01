from django.shortcuts import render
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Sum, Avg, Q
from django.utils import timezone
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from decimal import Decimal

from .models import CreditCard, CreditCardEMI, CreditCardPayment, CreditCardEMIReminder
from .serializers import (
    CreditCardSerializer, CreditCardEMISerializer, CreditCardPaymentSerializer,
    CreditCardEMIReminderSerializer, CreditCardEMIScheduleSerializer, CreditCardSummarySerializer
)


# Credit Card Views
class CreditCardListCreateView(generics.ListCreateAPIView):
    """
    List all credit cards or create a new credit card
    """
    serializer_class = CreditCardSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return CreditCard.objects.filter(user=self.request.user, is_active=True)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CreditCardDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a credit card
    """
    serializer_class = CreditCardSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return CreditCard.objects.filter(user=self.request.user)
    
    def perform_destroy(self, instance):
        # Soft delete by setting is_active to False
        instance.is_active = False
        instance.save()


class CreditCardDetailWithEMIsView(generics.RetrieveAPIView):
    """
    Get credit card details with its EMIs and summary
    """
    serializer_class = CreditCardSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return CreditCard.objects.filter(user=self.request.user)
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        # Get reference date from query parameters for testing purposes only
        reference_date_str = request.query_params.get('reference_date')
        reference_date = None
        if reference_date_str:
            try:
                reference_date = date.fromisoformat(reference_date_str)
            except ValueError:
                return Response({'error': 'Invalid reference_date format. Use YYYY-MM-DD'}, status=400)
        
        # Always use today's date for actual calculations
        today = date.today()
        
        # Get EMIs for this credit card - order by start_date instead of due_date
        emis = CreditCardEMI.objects.filter(credit_card=instance).order_by('start_date')
        
        # Calculate summary data
        total_emis = emis.count()
        pending_emis = emis.filter(status__in=['PENDING', 'OVERDUE']).count()
        paid_emis = emis.filter(status='PAID').count()
        overdue_emis = emis.filter(status='OVERDUE').count()
        
        total_emi_amount = emis.filter(status__in=['PENDING', 'OVERDUE']).aggregate(
            total=Sum('emi_amount'))['total'] or Decimal('0.00')
        
        next_emi = emis.filter(status__in=['PENDING', 'OVERDUE']).first()
        
        # Enhanced summary for mobile app requirements - use dynamic due date logic
        active_emis = emis.filter(status__in=['PENDING', 'OVERDUE'])
        total_emi_due_this_month = Decimal('0.00')
        
        for emi in active_emis:
            if emi.is_due_this_month:
                total_emi_due_this_month += emi.emi_amount
        
        total_remaining_amount = sum(emi.remaining_amount for emi in active_emis)
        
        # Enhanced EMI data - always use today's date for real progress
        emis_data = []
        for emi in emis:
            # Always calculate based on today's date for real progress
            completed_months = emi.get_completed_months(today)
            progress_months = emi.get_progress_months(today)
            months_remaining = emi.get_months_remaining(today)
            
            # If reference_date is provided (for testing), also include those calculations
            reference_data = {}
            if reference_date:
                reference_data = {
                    'reference_completed_months': emi.get_completed_months(reference_date),
                    'reference_progress_months': emi.get_progress_months(reference_date),
                    'reference_months_remaining': emi.get_months_remaining(reference_date),
                    'reference_date': reference_date.isoformat()
                }
            
            emi_dict = CreditCardEMISerializer(emi).data
            # Override the calculated fields with today's date calculations
            emi_dict.update({
                'completed_months': completed_months,
                'progress_months': progress_months,
                'months_remaining': months_remaining,
                'calculated_on': today.isoformat(),
                **reference_data  # Add reference date calculations if provided
            })
            emis_data.append(emi_dict)
        
        data = serializer.data
        data.update({
            'emis': emis_data,
            'calculated_on': today.isoformat(),
            'emi_summary': {
                'total_emis': total_emis,
                'pending_emis': pending_emis,
                'paid_emis': paid_emis,
                'overdue_emis': overdue_emis,
                'total_emi_amount': float(total_emi_amount),
                'total_emi_due_this_month': float(total_emi_due_this_month),
                'total_remaining_amount': float(total_remaining_amount),
                'next_emi': {
                    'due_date': next_emi.next_due_date.isoformat() if next_emi and next_emi.next_due_date else None,
                    'amount': float(next_emi.emi_amount) if next_emi else 0,
                } if next_emi else None
            }
        })
        
        # Add reference date info if provided (for testing)
        if reference_date:
            data['reference_date_info'] = {
                'reference_date': reference_date.isoformat(),
                'note': 'Reference date calculations included for testing purposes'
            }
        
        return Response(data)


# Credit Card EMI Views
class CreditCardEMIListView(generics.ListAPIView):
    """
    List all EMIs for a specific credit card
    """
    serializer_class = CreditCardEMISerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        credit_card_id = self.kwargs['credit_card_id']
        queryset = CreditCardEMI.objects.filter(
            credit_card_id=credit_card_id,
            user=self.request.user
        )
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by date range using start_date instead of due_date
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        if start_date:
            queryset = queryset.filter(start_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(end_date__lte=end_date)

        return queryset.order_by('start_date')


class CreditCardEMICreateView(APIView):
    """
    Create a new EMI for a specific credit card
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, credit_card_id):
        try:
            credit_card = CreditCard.objects.get(id=credit_card_id, user=request.user)
        except CreditCard.DoesNotExist:
            return Response({'error': 'Credit card not found'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = CreditCardEMISerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        serializer.save(user=request.user, credit_card=credit_card)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CreditCardEMIDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a credit card EMI
    """
    serializer_class = CreditCardEMISerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return CreditCardEMI.objects.filter(user=self.request.user)


class MarkCreditCardEMIPaidView(APIView):
    """
    Mark a credit card EMI as paid
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, emi_id):
        try:
            emi = CreditCardEMI.objects.get(id=emi_id, user=request.user)
        except CreditCardEMI.DoesNotExist:
            return Response({'error': 'EMI not found'}, status=status.HTTP_404_NOT_FOUND)
        
        amount = request.data.get('amount')
        payment_date = request.data.get('payment_date')
        
        if amount:
            amount = Decimal(str(amount))
            if amount > emi.remaining_amount:
                return Response(
                    {'error': f'Amount cannot exceed remaining amount of {emi.remaining_amount}'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Mark EMI as paid
        emi.mark_as_paid(amount=amount, payment_date=payment_date)
        
        # Create payment record
        payment_method = request.data.get('payment_method', 'OTHER')
        transaction_id = request.data.get('transaction_id', '')
        notes = request.data.get('notes', '')
        
        payment = CreditCardPayment.objects.create(
            user=request.user,
            emi=emi,
            amount=amount or emi.emi_amount,
            payment_method=payment_method,
            payment_date=payment_date or date.today(),
            transaction_id=transaction_id,
            notes=notes
        )
        
        return Response({
            'message': 'EMI marked as paid successfully',
            'emi': CreditCardEMISerializer(emi).data,
            'payment': CreditCardPaymentSerializer(payment).data
        }, status=status.HTTP_200_OK)


# Payment Views
class CreditCardPaymentListCreateView(generics.ListCreateAPIView):
    """
    List all credit card payments or create a new payment
    """
    serializer_class = CreditCardPaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return CreditCardPayment.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        payment = serializer.save(user=self.request.user)
        # Update EMI status when payment is made
        emi = payment.emi
        emi.paid_amount += payment.amount
        if emi.paid_amount >= emi.emi_amount:
            emi.status = 'PAID'
        elif emi.paid_amount > 0:
            emi.status = 'PARTIAL'
        emi.save()


class CreditCardPaymentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a credit card payment
    """
    serializer_class = CreditCardPaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return CreditCardPayment.objects.filter(user=self.request.user)


# EMI Schedule Generator
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def generate_credit_card_emi_schedule(request, credit_card_id):
    """
    Generate EMI schedule for a specific credit card
    """
    try:
        credit_card = CreditCard.objects.get(id=credit_card_id, user=request.user)
    except CreditCard.DoesNotExist:
        return Response({'error': 'Credit card not found'}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = CreditCardEMIScheduleSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    data = serializer.validated_data
    start_date = data['start_date']
    number_of_emis = data['number_of_emis']
    emi_amount = data['emi_amount']
    
    # Generate EMI schedule using new start_date/end_date logic
    emi = CreditCardEMI.objects.create(
        user=request.user,
        credit_card=credit_card,
        emi_amount=emi_amount,
        start_date=start_date,
        status='PENDING',
        total_duration=number_of_emis,
        is_auto_generated=True
    )
    
    return Response({
        'message': f'EMI schedule created successfully for {number_of_emis} months',
        'emi': CreditCardEMISerializer(emi).data
    }, status=status.HTTP_201_CREATED)


# Summary Views
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def credit_card_summary(request):
    """
    Get summary of all credit cards for the authenticated user
    """
    credit_cards = CreditCard.objects.filter(user=request.user, is_active=True)
    
    if not credit_cards.exists():
        return Response({
            'total_cards': 0,
            'total_credit_limit': 0,
            'total_current_balance': 0,
            'total_available_credit': 0,
            'average_utilization': 0
        })
    
    # Calculate aggregated data
    totals = credit_cards.aggregate(
        total_credit_limit=Sum('credit_limit'),
        total_current_balance=Sum('current_balance')
    )
    
    total_credit_limit = totals['total_credit_limit'] or Decimal('0.00')
    total_current_balance = totals['total_current_balance'] or Decimal('0.00')
    total_available_credit = total_credit_limit - total_current_balance
    
    # Calculate average utilization
    if total_credit_limit > 0:
        average_utilization = (total_current_balance / total_credit_limit) * 100
    else:
        average_utilization = Decimal('0.00')
    
    summary_data = {
        'total_cards': credit_cards.count(),
        'total_credit_limit': total_credit_limit,
        'total_current_balance': total_current_balance,
        'total_available_credit': total_available_credit,
        'average_utilization': average_utilization
    }
    
    serializer = CreditCardSummarySerializer(summary_data)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def credit_card_emi_summary(request, credit_card_id):
    """
    Get EMI summary for a specific credit card
    """
    try:
        credit_card = CreditCard.objects.get(id=credit_card_id, user=request.user)
    except CreditCard.DoesNotExist:
        return Response({'error': 'Credit card not found'}, status=status.HTTP_404_NOT_FOUND)
    
    emis = CreditCardEMI.objects.filter(credit_card=credit_card)
    
    # Basic statistics
    total_emis = emis.count()
    pending_emis = emis.filter(status__in=['PENDING', 'OVERDUE']).count()
    paid_emis = emis.filter(status='PAID').count()
    overdue_emis = emis.filter(status='OVERDUE').count()
    
    # Amount calculations
    total_emi_amount = emis.aggregate(total=Sum('emi_amount'))['total'] or Decimal('0.00')
    total_paid_amount = emis.aggregate(total=Sum('paid_amount'))['total'] or Decimal('0.00')
    total_remaining_amount = total_emi_amount - total_paid_amount
    
    # This month's EMIs using dynamic due date logic
    active_emis = emis.filter(status__in=['PENDING', 'OVERDUE'])
    total_emi_due_this_month = Decimal('0.00')
    
    for emi in active_emis:
        if emi.is_due_this_month:
            total_emi_due_this_month += emi.emi_amount
    
    # Next due EMI using dynamic due date logic
    next_emi = None
    next_due_date = None
    
    for emi in active_emis:
        emi_next_due = emi.next_due_date
        if emi_next_due and (not next_due_date or emi_next_due < next_due_date):
            next_due_date = emi_next_due
            next_emi = emi
    
    return Response({
        'credit_card': CreditCardSerializer(credit_card).data,
        'summary': {
            'total_emis': total_emis,
            'pending_emis': pending_emis,
            'paid_emis': paid_emis,
            'overdue_emis': overdue_emis,
            'total_emi_amount': float(total_emi_amount),
            'total_paid_amount': float(total_paid_amount),
            'total_remaining_amount': float(total_remaining_amount),
            'total_emi_due_this_month': float(total_emi_due_this_month),
            'next_emi': {
                'id': next_emi.id,
                'due_date': next_due_date.isoformat(),
                'amount': float(next_emi.emi_amount),
                'status': next_emi.status
            } if next_emi else None
        },
        'emis': CreditCardEMISerializer(emis, many=True).data
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def enhanced_credit_card_emi_list(request, credit_card_id=None):
    """
    Enhanced EMI list endpoint matching mobile app requirements
    """
    if credit_card_id:
        try:
            credit_card = CreditCard.objects.get(id=credit_card_id, user=request.user)
            emis = CreditCardEMI.objects.filter(credit_card=credit_card, user=request.user)
        except CreditCard.DoesNotExist:
            return Response({'error': 'Credit card not found'}, status=status.HTTP_404_NOT_FOUND)
    else:
        emis = CreditCardEMI.objects.filter(user=request.user)
    
    # Apply filters
    status_filter = request.query_params.get('status')
    if status_filter:
        emis = emis.filter(status=status_filter)
    
    # Get reference date from query parameters (default to today)
    reference_date_str = request.query_params.get('reference_date')
    reference_date = None
    if reference_date_str:
        try:
            reference_date = date.fromisoformat(reference_date_str)
        except ValueError:
            return Response({'error': 'Invalid reference_date format. Use YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Order by start_date instead of due_date
    emis = emis.order_by('start_date')
    
    # Enhanced response format using dynamic due date logic
    emi_list = []
    for emi in emis:
        next_due_date = emi.next_due_date
        
        # Calculate months using reference date if provided
        if reference_date:
            completed_months = emi.get_completed_months(reference_date)
            progress_percentage = emi.get_progress_months(reference_date)
        else:
            completed_months = emi.completed_months
            progress_percentage = emi.progress_months
            
        emi_data = {
            'id': emi.id,
            'title': f"{emi.credit_card.card_name} EMI",
            'amount': float(emi.emi_amount),
            'dueDate': next_due_date.isoformat() if next_due_date else None,
            'status': emi.status,
            'isPaid': emi.status == 'PAID',
            'isOverdue': emi.is_overdue,
            'isDueThisMonth': emi.is_due_this_month,
            'remainingAmount': float(emi.remaining_amount),
            'paidAmount': float(emi.paid_amount),
            'creditCard': {
                'id': emi.credit_card.id,
                'name': emi.credit_card.card_name,
                'lastFourDigits': emi.credit_card.last_four_digits
            },
            'totalDuration': emi.total_duration,
            'completedMonths': completed_months,
            'progressPercentage': progress_percentage,
            'referenceDate': reference_date.isoformat() if reference_date else date.today().isoformat()
        }
        emi_list.append(emi_data)
    
    return Response({
        'count': len(emi_list),
        'emis': emi_list,
        'reference_date': reference_date.isoformat() if reference_date else date.today().isoformat()
    })
