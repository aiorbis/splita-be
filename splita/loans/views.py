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

from .models import Loan, LoanEMI, LoanPayment, LoanEMIReminder
from .serializers import (
    LoanSerializer, LoanEMISerializer, LoanPaymentSerializer,
    LoanEMIReminderSerializer, LoanEMIScheduleSerializer, LoanSummarySerializer
)


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


class LoanDetailWithEMIsView(generics.RetrieveAPIView):
    """
    Get loan details with its EMIs and summary
    """
    serializer_class = LoanSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Loan.objects.filter(user=self.request.user)
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        # Get EMIs for this loan
        emis = LoanEMI.objects.filter(loan=instance).order_by('start_date')
        
        # Calculate summary data
        total_emis = emis.count()
        pending_emis = emis.filter(status__in=['PENDING', 'OVERDUE']).count()
        paid_emis = emis.filter(status='PAID').count()
        overdue_emis = emis.filter(status='OVERDUE').count()
        
        total_emi_amount = emis.filter(status__in=['PENDING', 'OVERDUE']).aggregate(
            total=Sum('emi_amount'))['total'] or Decimal('0.00')
        
        next_emi = emis.filter(status__in=['PENDING', 'OVERDUE']).first()
        
        # Enhanced summary for mobile app requirements
        emi_this_month = emis.filter(
            start_date__year=date.today().year,
            start_date__month=date.today().month,
            status__in=['PENDING', 'OVERDUE']
        )
        
        total_emi_due_this_month = emi_this_month.aggregate(
            total=Sum('emi_amount'))['total'] or Decimal('0.00')
        
        total_remaining_amount = sum(emi.remaining_amount for emi in emis.filter(status__in=['PENDING', 'OVERDUE']))
        
        data = serializer.data
        data.update({
            'emis': LoanEMISerializer(emis, many=True).data,
            'emi_summary': {
                'total_emis': total_emis,
                'pending_emis': pending_emis,
                'paid_emis': paid_emis,
                'overdue_emis': overdue_emis,
                'total_emi_amount': float(total_emi_amount),
                'total_emi_due_this_month': float(total_emi_due_this_month),
                'total_remaining_amount': float(total_remaining_amount),
                'next_emi': {
                    'due_date': next_emi.due_date if next_emi else None,
                    'amount': float(next_emi.emi_amount) if next_emi else 0,
                } if next_emi else None
            }
        })
        
        return Response(data)


# Loan EMI Views
class LoanEMIListView(generics.ListAPIView):
    """
    List all EMIs for a specific loan
    """
    serializer_class = LoanEMISerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        loan_id = self.kwargs['loan_id']
        queryset = LoanEMI.objects.filter(
            loan_id=loan_id,
            user=self.request.user
        )
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Filter by date range
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        if start_date:
            queryset = queryset.filter(start_date__gte=start_date)
        if end_date:
            queryset = queryset.filter(start_date__lte=end_date)

        return queryset.order_by('start_date')


class LoanEMICreateView(APIView):
    """
    Create a new EMI for a specific loan
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, loan_id):
        try:
            loan = Loan.objects.get(id=loan_id, user=request.user)
        except Loan.DoesNotExist:
            return Response({'error': 'Loan not found'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = LoanEMISerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        serializer.save(user=request.user, loan=loan)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class LoanEMIDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a loan EMI
    """
    serializer_class = LoanEMISerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return LoanEMI.objects.filter(user=self.request.user)


class MarkLoanEMIPaidView(APIView):
    """
    Mark a loan EMI as paid
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, emi_id):
        try:
            emi = LoanEMI.objects.get(id=emi_id, user=request.user)
        except LoanEMI.DoesNotExist:
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
        
        payment = LoanPayment.objects.create(
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
            'emi': LoanEMISerializer(emi).data,
            'payment': LoanPaymentSerializer(payment).data
        }, status=status.HTTP_200_OK)


# Payment Views
class LoanPaymentListCreateView(generics.ListCreateAPIView):
    """
    List all loan payments or create a new payment
    """
    serializer_class = LoanPaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return LoanPayment.objects.filter(user=self.request.user)
    
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


class LoanPaymentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a loan payment
    """
    serializer_class = LoanPaymentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return LoanPayment.objects.filter(user=self.request.user)


# EMI Schedule Generator
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def generate_loan_emi_schedule(request, loan_id):
    """
    Generate EMI schedule for a specific loan
    """
    try:
        loan = Loan.objects.get(id=loan_id, user=request.user)
    except Loan.DoesNotExist:
        return Response({'error': 'Loan not found'}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = LoanEMIScheduleSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    data = serializer.validated_data
    start_date = data['start_date']
    number_of_emis = data['number_of_emis']
    emi_amount = data['emi_amount']
    
    # Generate EMI schedule
    emis_created = []
    current_date = start_date
    
    for i in range(number_of_emis):
        emi = LoanEMI.objects.create(
            user=request.user,
            loan=loan,
            emi_amount=emi_amount,
            start_date=current_date,
            status='PENDING',
            total_duration=number_of_emis,
            is_auto_generated=True
        )
        emis_created.append(emi)
        
        # Move to next month
        current_date = current_date + relativedelta(months=1)
    
    return Response({
        'message': f'{len(emis_created)} EMIs created successfully',
        'emis': LoanEMISerializer(emis_created, many=True).data
    }, status=status.HTTP_201_CREATED)


# Summary Views
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def loan_summary(request):
    """
    Get summary of all loans for the authenticated user
    """
    loans = Loan.objects.filter(user=request.user, is_active=True)
    
    if not loans.exists():
        return Response({
            'total_loans': 0,
            'total_principal_amount': 0,
            'total_current_balance': 0,
            'total_paid_amount': 0,
            'average_completion_percentage': 0
        })
    
    # Calculate aggregated data
    totals = loans.aggregate(
        total_principal_amount=Sum('principal_amount'),
        total_current_balance=Sum('current_balance')
    )
    
    total_principal_amount = totals['total_principal_amount'] or Decimal('0.00')
    total_current_balance = totals['total_current_balance'] or Decimal('0.00')
    total_paid_amount = total_principal_amount - total_current_balance
    
    # Calculate average completion percentage
    if total_principal_amount > 0:
        average_completion_percentage = (total_paid_amount / total_principal_amount) * 100
    else:
        average_completion_percentage = Decimal('0.00')
    
    summary_data = {
        'total_loans': loans.count(),
        'total_principal_amount': total_principal_amount,
        'total_current_balance': total_current_balance,
        'total_paid_amount': total_paid_amount,
        'average_completion_percentage': average_completion_percentage
    }
    
    serializer = LoanSummarySerializer(summary_data)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def loan_emi_summary(request, loan_id):
    """
    Get EMI summary for a specific loan
    """
    try:
        loan = Loan.objects.get(id=loan_id, user=request.user)
    except Loan.DoesNotExist:
        return Response({'error': 'Loan not found'}, status=status.HTTP_404_NOT_FOUND)
    
    emis = LoanEMI.objects.filter(loan=loan)
    
    # Basic statistics
    total_emis = emis.count()
    pending_emis = emis.filter(status__in=['PENDING', 'OVERDUE']).count()
    paid_emis = emis.filter(status='PAID').count()
    overdue_emis = emis.filter(status='OVERDUE').count()
    
    # Amount calculations
    total_emi_amount = emis.aggregate(total=Sum('emi_amount'))['total'] or Decimal('0.00')
    total_paid_amount = emis.aggregate(total=Sum('paid_amount'))['total'] or Decimal('0.00')
    total_remaining_amount = total_emi_amount - total_paid_amount
    
    # This month's EMIs
    today = date.today()
    this_month_emis = emis.filter(
        start_date__year=today.year,
        start_date__month=today.month,
        status__in=['PENDING', 'OVERDUE']
    )
    total_emi_due_this_month = this_month_emis.aggregate(total=Sum('emi_amount'))['total'] or Decimal('0.00')
    
    # Next due EMI
    next_emi = emis.filter(status__in=['PENDING', 'OVERDUE']).order_by('start_date').first()
    
    return Response({
        'loan': LoanSerializer(loan).data,
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
                'due_date': next_emi.due_date,
                'amount': float(next_emi.emi_amount),
                'status': next_emi.status
            } if next_emi else None
        },
        'emis': LoanEMISerializer(emis, many=True).data
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def enhanced_loan_emi_list(request, loan_id=None):
    """
    Enhanced EMI list endpoint matching mobile app requirements
    """
    if loan_id:
        try:
            loan = Loan.objects.get(id=loan_id, user=request.user)
            emis = LoanEMI.objects.filter(loan=loan, user=request.user)
        except Loan.DoesNotExist:
            return Response({'error': 'Loan not found'}, status=status.HTTP_404_NOT_FOUND)
    else:
        emis = LoanEMI.objects.filter(user=request.user)
    
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
    
    # Order by due date
    emis = emis.order_by('start_date')
    
    # Enhanced response format
    emi_list = []
    for emi in emis:
        # Calculate months using reference date if provided
        if reference_date:
            completed_months = emi.get_completed_months(reference_date)
            progress_percentage = emi.get_progress_months(reference_date)
        else:
            completed_months = emi.completed_months
            progress_percentage = emi.progress_months
            
        emi_data = {
            'id': emi.id,
            'title': f"{emi.loan.loan_name} EMI",
            'amount': float(emi.emi_amount),
            'dueDate': emi.next_due_date.isoformat() if emi.next_due_date else None,
            'status': emi.status,
            'isPaid': emi.status == 'PAID',
            'isOverdue': emi.is_overdue,
            'isDueThisMonth': emi.is_due_this_month,
            'remainingAmount': float(emi.remaining_amount),
            'paidAmount': float(emi.paid_amount),
            'loan': {
                'id': emi.loan.id,
                'name': emi.loan.loan_name,
                'lender': emi.loan.lender_name,
                'type': emi.loan.loan_type
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
