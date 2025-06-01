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

from .models import CreditCard, Loan, EMI, Payment, EMIReminder
from .serializers import (
    CreditCardSerializer, LoanSerializer, EMISerializer, PaymentSerializer,
    EMIReminderSerializer, EMIScheduleSerializer, CreditCardSummarySerializer,
    LoanSummarySerializer, EMISummarySerializer, DashboardSerializer
)


# Create your views here.

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


# Loan Views
class LoanListCreateView(generics.ListCreateAPIView):
    """
    List all loans or create a new loan
    """
    serializer_class = LoanSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Loan.objects.filter(user=self.request.user, is_active=True)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class LoanDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a loan
    """
    serializer_class = LoanSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Loan.objects.filter(user=self.request.user)
    
    def perform_destroy(self, instance):
        # Soft delete by setting is_active to False
        instance.is_active = False
        instance.save()


# EMI Views
class EMIListCreateView(generics.ListCreateAPIView):
    """
    List all EMIs or create a new EMI
    """
    serializer_class = EMISerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = EMI.objects.filter(user=self.request.user)
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by EMI type
        emi_type = self.request.query_params.get('emi_type', None)
        if emi_type:
            queryset = queryset.filter(emi_type=emi_type)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        if start_date:
            queryset = queryset.filter(due_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(due_date__lte=end_date)

        return queryset.order_by('due_date')
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class EMIDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete an EMI
    """
    serializer_class = EMISerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return EMI.objects.filter(user=self.request.user)


class EMIScheduleGeneratorView(APIView):
    """
    Generate EMI schedule for credit cards or loans
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = EMIScheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        source_type = data['source_type']
        source_id = data['source_id']
        start_date = data['start_date']
        number_of_emis = data['number_of_emis']
        emi_amount = data['emi_amount']
        
        # Validate source exists and belongs to user
        if source_type == 'credit_card':
            try:
                source = CreditCard.objects.get(id=source_id, user=request.user)
                emi_type = 'CREDIT_CARD'
            except CreditCard.DoesNotExist:
                return Response({'error': 'Credit card not found'}, status=status.HTTP_404_NOT_FOUND)
        else:
            try:
                source = Loan.objects.get(id=source_id, user=request.user)
                emi_type = 'LOAN'
            except Loan.DoesNotExist:
                return Response({'error': 'Loan not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Generate EMI schedule
        emis_created = []
        current_date = start_date
        
        for i in range(number_of_emis):
            emi_data = {
                'user': request.user,
                'emi_type': emi_type,
                'emi_amount': emi_amount,
                'due_date': current_date,
                'status': 'PENDING',
                'is_auto_generated': True
            }
            
            if source_type == 'credit_card':
                emi_data['credit_card'] = source
            else:
                emi_data['loan'] = source
            
            emi = EMI.objects.create(**emi_data)
            emis_created.append(emi)
            
            # Move to next month
            current_date = current_date + relativedelta(months=1)
        
        return Response({
            'message': f'{len(emis_created)} EMIs created successfully',
            'emis': EMISerializer(emis_created, many=True).data
        }, status=status.HTTP_201_CREATED)


class MarkEMIPaidView(APIView):
    """
    Mark an EMI as paid
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, emi_id):
        try:
            emi = EMI.objects.get(id=emi_id, user=request.user)
        except EMI.DoesNotExist:
            return Response({'error': 'EMI not found'}, status=status.HTTP_404_NOT_FOUND)
        
        amount = request.data.get('amount', emi.emi_amount)
        payment_date = request.data.get('payment_date', date.today())
        
        # Mark EMI as paid
        emi.mark_as_paid(amount=Decimal(str(amount)), payment_date=payment_date)
        
        return Response({
            'message': 'EMI marked as paid successfully',
            'emi': EMISerializer(emi).data
        }, status=status.HTTP_200_OK)


# Payment Views
class PaymentListCreateView(generics.ListCreateAPIView):
    """
    List all payments or create a new payment
    """
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        payment = serializer.save(user=self.request.user)
        
        # Update EMI status based on payment
        emi = payment.emi
        total_paid = emi.payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        if total_paid >= emi.emi_amount:
            emi.status = 'PAID'
            emi.paid_amount = total_paid
            emi.paid_date = payment.payment_date
        elif total_paid > 0:
            emi.status = 'PARTIAL'
            emi.paid_amount = total_paid
        
        emi.save()


class PaymentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a payment
    """
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user)


# Dashboard and Summary Views
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def credit_card_summary(request):
    """
    Get credit card summary for the user
    """
    user = request.user
    credit_cards = CreditCard.objects.filter(user=user, is_active=True)
    
    if not credit_cards.exists():
        return Response({
            'total_cards': 0,
            'total_credit_limit': 0,
            'total_current_balance': 0,
            'total_available_credit': 0,
            'average_utilization': 0
        })
    
    summary = credit_cards.aggregate(
        total_credit_limit=Sum('credit_limit'),
        total_current_balance=Sum('current_balance')
    )
    
    total_cards = credit_cards.count()
    total_credit_limit = summary['total_credit_limit'] or Decimal('0.00')
    total_current_balance = summary['total_current_balance'] or Decimal('0.00')
    total_available_credit = total_credit_limit - total_current_balance
    
    # Calculate average utilization
    if total_credit_limit > 0:
        average_utilization = (total_current_balance / total_credit_limit) * 100
    else:
        average_utilization = 0
    
    data = {
        'total_cards': total_cards,
        'total_credit_limit': total_credit_limit,
        'total_current_balance': total_current_balance,
        'total_available_credit': total_available_credit,
        'average_utilization': round(average_utilization, 2)
    }
    
    return Response(data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def loan_summary(request):
    """
    Get loan summary for the user
    """
    user = request.user
    loans = Loan.objects.filter(user=user, is_active=True)
    
    if not loans.exists():
        return Response({
            'total_loans': 0,
            'total_principal_amount': 0,
            'total_current_balance': 0,
            'total_paid_amount': 0,
            'average_completion_percentage': 0
        })
    
    summary = loans.aggregate(
        total_principal_amount=Sum('principal_amount'),
        total_current_balance=Sum('current_balance')
    )
    
    total_loans = loans.count()
    total_principal_amount = summary['total_principal_amount'] or Decimal('0.00')
    total_current_balance = summary['total_current_balance'] or Decimal('0.00')
    total_paid_amount = total_principal_amount - total_current_balance
    
    # Calculate average completion percentage
    if total_principal_amount > 0:
        average_completion_percentage = (total_paid_amount / total_principal_amount) * 100
    else:
        average_completion_percentage = 0
    
    data = {
        'total_loans': total_loans,
        'total_principal_amount': total_principal_amount,
        'total_current_balance': total_current_balance,
        'total_paid_amount': total_paid_amount,
        'average_completion_percentage': round(average_completion_percentage, 2)
    }
    
    return Response(data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def emi_summary(request):
    """
    Get EMI summary for the user
    """
    user = request.user
    emis = EMI.objects.filter(user=user)
    
    total_emis = emis.count()
    pending_emis = emis.filter(status='PENDING').count()
    overdue_emis = emis.filter(status='OVERDUE').count()
    paid_emis = emis.filter(status='PAID').count()
    
    # Calculate total monthly payment (pending + overdue)
    monthly_payment = emis.filter(
        status__in=['PENDING', 'OVERDUE']
    ).aggregate(total=Sum('emi_amount'))['total'] or Decimal('0.00')
    
    # Get next due EMI
    next_emi = emis.filter(
        status='PENDING',
        due_date__gte=date.today()
    ).order_by('due_date').first()
    
    next_due_date = next_emi.due_date if next_emi else None
    next_due_amount = next_emi.emi_amount if next_emi else Decimal('0.00')
    
    data = {
        'total_emis': total_emis,
        'pending_emis': pending_emis,
        'overdue_emis': overdue_emis,
        'paid_emis': paid_emis,
        'total_monthly_payment': monthly_payment,
        'next_due_date': next_due_date,
        'next_due_amount': next_due_amount
    }
    
    return Response(data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def dashboard(request):
    """
    Get comprehensive dashboard data
    """
    user = request.user
    
    # Get recent payments (last 10)
    recent_payments = Payment.objects.filter(user=user).order_by('-payment_date')[:10]
    
    # Get upcoming EMIs (next 5)
    upcoming_emis = EMI.objects.filter(
        user=user,
        status='PENDING',
        due_date__gte=date.today()
    ).order_by('due_date')[:5]
    
    # Get summaries
    credit_card_summary_data = credit_card_summary(request).data
    loan_summary_data = loan_summary(request).data
    emi_summary_data = emi_summary(request).data
    
    data = {
        'credit_card_summary': credit_card_summary_data,
        'loan_summary': loan_summary_data,
        'emi_summary': emi_summary_data,
        'recent_payments': PaymentSerializer(recent_payments, many=True).data,
        'upcoming_emis': EMISerializer(upcoming_emis, many=True).data
    }
    
    return Response(data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def enhanced_dashboard(request):
    """
    Get enhanced dashboard data matching mobile app requirements
    """
    user = request.user
    today = date.today()
    
    # Get all active credit cards and loans
    credit_cards = CreditCard.objects.filter(user=user, is_active=True)
    loans = Loan.objects.filter(user=user, is_active=True)
    
    # Calculate totalEMIDueThisMonth
    total_emi_due_this_month = Decimal('0.00')
    
    # Credit card EMIs due this month
    for card in credit_cards:
        credit_card_emis = card.emis.filter(
            due_date__year=today.year,
            due_date__month=today.month,
            status__in=['PENDING', 'OVERDUE']
        )
        for emi in credit_card_emis:
            total_emi_due_this_month += emi.amount
    
    # Loan EMIs due this month
    for loan in loans:
        if loan.is_due_this_month:
            total_emi_due_this_month += loan.emi_amount
    
    # Calculate totalCreditCardEMI
    total_credit_card_emi = Decimal('0.00')
    for card in credit_cards:
        total_credit_card_emi += card.total_emi_amount
    
    # Calculate totalLoanEMI
    total_loan_emi = Decimal('0.00')
    for loan in loans:
        total_loan_emi += loan.emi_amount
    
    # Calculate totalRemainingAmount
    total_remaining_amount = Decimal('0.00')
    for card in credit_cards:
        total_remaining_amount += card.total_remaining_amount
    for loan in loans:
        total_remaining_amount += loan.remaining_amount
    
    # Get upcomingPayments
    upcoming_payments = []
    
    # Add credit card EMIs
    for card in credit_cards:
        for emi in card.emis.filter(status__in=['PENDING', 'OVERDUE']):
            if emi.months_remaining > 0:
                upcoming_payments.append({
                    'type': 'credit_card',
                    'title': f'{card.card_name} - {emi.description or "EMI"}',
                    'amount': float(emi.amount),
                    'dueDate': emi.next_due_date.isoformat(),
                    'isDueThisMonth': emi.is_due_this_month,
                })
    
    # Add loan EMIs
    for loan in loans:
        if loan.remaining_months > 0:
            upcoming_payments.append({
                'type': 'loan',
                'title': f'{loan.lender_name} - {loan.get_loan_type_display()}',
                'amount': float(loan.emi_amount),
                'dueDate': loan.next_due_date.isoformat() if loan.next_due_date else None,
                'isDueThisMonth': loan.is_due_this_month,
            })
    
    # Sort by due date
    upcoming_payments.sort(key=lambda x: x['dueDate'] if x['dueDate'] else '9999-12-31')
    
    # Get basic summaries for additional context
    credit_card_summary_data = credit_card_summary(request).data
    loan_summary_data = loan_summary(request).data
    emi_summary_data = emi_summary(request).data
    
    data = {
        # Dashboard calculations matching mobile app
        'totalEMIDueThisMonth': float(total_emi_due_this_month),
        'totalCreditCardEMI': float(total_credit_card_emi),
        'totalLoanEMI': float(total_loan_emi),
        'totalRemainingAmount': float(total_remaining_amount),
        'upcomingPayments': upcoming_payments,
        
        # Additional context data
        'credit_card_summary': credit_card_summary_data,
        'loan_summary': loan_summary_data,
        'emi_summary': emi_summary_data,
        
        # User greeting data
        'user': {
            'name': user.get_full_name() or user.username,
            'firstName': user.first_name or 'User',
        }
    }
    
    return Response(data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def overdue_emis(request):
    """
    Get all overdue EMIs for the user
    """
    user = request.user
    today = date.today()
    
    # Update EMI status to overdue if past due date
    EMI.objects.filter(
        user=user,
        status='PENDING',
        due_date__lt=today
    ).update(status='OVERDUE')
    
    overdue_emis = EMI.objects.filter(user=user, status='OVERDUE').order_by('due_date')
    
    return Response({
        'count': overdue_emis.count(),
        'emis': EMISerializer(overdue_emis, many=True).data
    })


# Credit Card EMI Specific Views
class CreditCardEMIListView(generics.ListAPIView):
    """
    List all EMIs for a specific credit card
    """
    serializer_class = EMISerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        credit_card_id = self.kwargs.get('credit_card_id')
        try:
            credit_card = CreditCard.objects.get(id=credit_card_id, user=self.request.user)
        except CreditCard.DoesNotExist:
            return EMI.objects.none()
        
        queryset = EMI.objects.filter(
            user=self.request.user,
            credit_card=credit_card,
            emi_type='CREDIT_CARD'
        )
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        print("EMI LIST:", queryset.order_by('due_date'))
        return queryset.order_by('due_date')


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
        
        data = request.data.copy()
        print("DATA:", data)
        data['credit_card'] = credit_card.id
        data['emi_type'] = 'CREDIT_CARD'
        
        serializer = EMISerializer(data=data)
        serializer.is_valid(raise_exception=True)
        emi = serializer.save(user=request.user)
        
        return Response({
            'message': 'EMI created successfully',
            'emi': EMISerializer(emi).data
        }, status=status.HTTP_201_CREATED)


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
        
        # Get EMIs for this credit card
        emis = EMI.objects.filter(
            user=request.user,
            credit_card=instance,
            emi_type='CREDIT_CARD'
        ).order_by('due_date')
        
        # Calculate EMI summary for this card
        total_emis = emis.count()
        pending_emis = emis.filter(status='PENDING').count()
        overdue_emis = emis.filter(status='OVERDUE').count()
        paid_emis = emis.filter(status='PAID').count()
        
        total_emi_amount = emis.filter(
            status__in=['PENDING', 'OVERDUE']
        ).aggregate(total=Sum('emi_amount'))['total'] or Decimal('0.00')
        
        # Calculate remaining balance for all EMIs
        total_remaining_balance = Decimal('0.00')
        for emi in emis.filter(status__in=['PENDING', 'OVERDUE']):
            total_remaining_balance += emi.remaining_amount
        
        # Get next due EMI
        next_emi = emis.filter(
            status='PENDING',
            due_date__gte=date.today()
        ).first()
        
        # Serialize EMIs with enhanced information
        emis_data = []
        for emi in emis:
            emi_data = EMISerializer(emi).data
            # Add additional calculated fields for frontend
            emi_data.update({
                'totalMonths': emi.total_months,
                'totalDuration': emi.total_duration,  # Explicit total duration
                'completedMonths': emi.completed_months,
                'progressMonths': emi.progress_months,
                'remainingAmount': float(emi.remaining_amount),
                'emiAmount': float(emi.emi_amount),
                'isOnTrack': emi.status in ['PENDING', 'PAID'],  # Simple on-track logic
                'progressPercentage': round((emi.completed_months / emi.total_months) * 100, 1) if emi.total_months > 0 else 0
            })
            emis_data.append(emi_data)
        
        data = serializer.data
        data.update({
            'emi_summary': {
                'total_emis': total_emis,
                'pending_emis': pending_emis,
                'overdue_emis': overdue_emis,
                'paid_emis': paid_emis,
                'total_emi_amount': float(total_emi_amount),
                'total_remaining_balance': float(total_remaining_balance),
                'next_due_date': next_emi.due_date if next_emi else None,
                'next_due_amount': float(next_emi.emi_amount) if next_emi else 0.0
            },
            'emis': emis_data
        })
        
        return Response(data)


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
    
    # Validate input data
    required_fields = ['start_date', 'number_of_emis', 'emi_amount']
    for field in required_fields:
        if field not in request.data:
            return Response({'error': f'{field} is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        start_date = date.fromisoformat(request.data['start_date'])
        number_of_emis = int(request.data['number_of_emis'])
        emi_amount = Decimal(str(request.data['emi_amount']))
        description = request.data.get('description', f'{credit_card.card_name} EMI')
    except (ValueError, TypeError) as e:
        return Response({'error': 'Invalid data format'}, status=status.HTTP_400_BAD_REQUEST)
    
    if number_of_emis < 1 or number_of_emis > 360:
        return Response({'error': 'Number of EMIs must be between 1 and 360'}, status=status.HTTP_400_BAD_REQUEST)
    
    if emi_amount <= 0:
        return Response({'error': 'EMI amount must be greater than 0'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Generate EMI schedule
    emis_created = []
    current_date = start_date
    
    for i in range(number_of_emis):
        emi = EMI.objects.create(
            user=request.user,
            credit_card=credit_card,
            emi_type='CREDIT_CARD',
            emi_amount=emi_amount,
            due_date=current_date,
            status='PENDING',
            description=f"{description} - {i+1}/{number_of_emis}",
            total_duration=number_of_emis,  # Set the total duration
            is_auto_generated=True
        )
        emis_created.append(emi)
        
        # Move to next month
        current_date = current_date + relativedelta(months=1)
    
    return Response({
        'message': f'{len(emis_created)} EMIs created successfully for {credit_card.card_name}',
        'credit_card': CreditCardSerializer(credit_card).data,
        'emis': EMISerializer(emis_created, many=True).data
    }, status=status.HTTP_201_CREATED)


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
    
    emis = EMI.objects.filter(
        user=request.user,
        credit_card=credit_card,
        emi_type='CREDIT_CARD'
    )
    
    total_emis = emis.count()
    pending_emis = emis.filter(status='PENDING').count()
    overdue_emis = emis.filter(status='OVERDUE').count()
    paid_emis = emis.filter(status='PAID').count()
    partial_emis = emis.filter(status='PARTIAL').count()
    
    total_emi_amount = emis.aggregate(total=Sum('emi_amount'))['total'] or Decimal('0.00')
    total_paid_amount = emis.aggregate(total=Sum('paid_amount'))['total'] or Decimal('0.00')
    remaining_amount = total_emi_amount - total_paid_amount
    
    # Monthly payment (pending + overdue)
    monthly_payment = emis.filter(
        status__in=['PENDING', 'OVERDUE']
    ).aggregate(total=Sum('emi_amount'))['total'] or Decimal('0.00')
    
    # Progress calculation
    progress_percentage = 0
    if total_emis > 0:
        progress_percentage = (paid_emis / total_emis) * 100
    
    # Next due EMI
    next_emi = emis.filter(
        status='PENDING',
        due_date__gte=date.today()
    ).order_by('due_date').first()
    
    data = {
        'credit_card': CreditCardSerializer(credit_card).data,
        'emi_summary': {
            'total_emis': total_emis,
            'pending_emis': pending_emis,
            'overdue_emis': overdue_emis,
            'paid_emis': paid_emis,
            'partial_emis': partial_emis,
            'total_emi_amount': total_emi_amount,
            'total_paid_amount': total_paid_amount,
            'remaining_amount': remaining_amount,
            'monthly_payment': monthly_payment,
            'progress_percentage': round(progress_percentage, 2),
            'next_due_date': next_emi.due_date if next_emi else None,
            'next_due_amount': next_emi.emi_amount if next_emi else Decimal('0.00')
        }
    }
    
    return Response(data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def enhanced_emi_list(request, credit_card_id=None):
    """
    Get enhanced EMI list with all frontend required information
    """
    user = request.user
    
    # Build queryset based on parameters
    if credit_card_id:
        try:
            credit_card = CreditCard.objects.get(id=credit_card_id, user=user)
            emis = EMI.objects.filter(
                user=user,
                credit_card=credit_card,
                emi_type='CREDIT_CARD'
            ).order_by('due_date')
        except CreditCard.DoesNotExist:
            return Response({'error': 'Credit card not found'}, status=status.HTTP_404_NOT_FOUND)
    else:
        # Get all EMIs for the user
        emis = EMI.objects.filter(user=user).order_by('due_date')
    
    # Apply filters
    status_filter = request.query_params.get('status', None)
    if status_filter:
        emis = emis.filter(status=status_filter)
    
    # Prepare enhanced EMI data
    enhanced_emis = []
    for emi in emis:
        emi_data = {
            'id': emi.id,
            'description': emi.description or 'EMI',
            'emi_amount': float(emi.emi_amount),
            'remaining_amount': float(emi.remaining_amount),
            'due_date': emi.due_date.isoformat(),
            'status': emi.status,
            'total_months': emi.total_months,
            'total_duration': emi.total_duration,  # Explicit total duration field
            'completed_months': emi.completed_months,
            'progress_months': emi.progress_months,
            'progress_percentage': round((emi.completed_months / emi.total_months) * 100, 1) if emi.total_months > 0 else 0,
            'is_due_this_month': emi.is_due_this_month,
            'is_overdue': emi.is_overdue,
            'is_on_track': emi.status in ['PENDING', 'PAID'],
            'emi_type': emi.emi_type,
            'credit_card_name': emi.credit_card.card_name if emi.credit_card else None,
            'loan_name': emi.loan.loan_name if emi.loan else None,
            # Frontend specific fields
            'title': emi.description or f"{emi.credit_card.card_name if emi.credit_card else emi.loan.loan_name} EMI",
            'amount': float(emi.emi_amount),  # Alias for consistency
        }
        enhanced_emis.append(emi_data)
    
    return Response({
        'count': len(enhanced_emis),
        'emis': enhanced_emis
    })
