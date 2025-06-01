from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import permissions
from django.db.models import Sum, Q
from datetime import date, timedelta
from decimal import Decimal
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from credit_cards.models import CreditCard, CreditCardEMI, CreditCardPayment
from credit_cards.serializers import CreditCardSerializer, CreditCardEMISerializer, CreditCardPaymentSerializer, CreditCardSummarySerializer
from loans.models import Loan, LoanEMI, LoanPayment
from loans.serializers import LoanSerializer, LoanEMISerializer, LoanPaymentSerializer, LoanSummarySerializer


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
@swagger_auto_schema(
    operation_summary="Combined dashboard endpoint that provides overview of credit cards and loans",
    security=[{'Bearer': []}],
    responses={
        200: openapi.Response(
            description="Dashboard data",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'credit_card_summary': openapi.Schema(type=openapi.TYPE_OBJECT),
                    'loan_summary': openapi.Schema(type=openapi.TYPE_OBJECT),
                    'emi_summary': openapi.Schema(type=openapi.TYPE_OBJECT),
                    'recent_payments': openapi.Schema(type=openapi.TYPE_OBJECT),
                    'upcoming_emis': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        )
    }
)
def dashboard(request):
    """
    Combined dashboard endpoint that provides overview of credit cards and loans
    """
    user = request.user
    
    # Credit Card Summary
    credit_cards = CreditCard.objects.filter(user=user, is_active=True)
    credit_card_totals = credit_cards.aggregate(
        total_credit_limit=Sum('credit_limit'),
        total_current_balance=Sum('current_balance')
    )
    
    total_credit_limit = credit_card_totals['total_credit_limit'] or Decimal('0.00')
    total_current_balance = credit_card_totals['total_current_balance'] or Decimal('0.00')
    total_available_credit = total_credit_limit - total_current_balance
    
    if total_credit_limit > 0:
        average_utilization = (total_current_balance / total_credit_limit) * 100
    else:
        average_utilization = Decimal('0.00')
    
    credit_card_summary = {
        'total_cards': credit_cards.count(),
        'total_credit_limit': total_credit_limit,
        'total_current_balance': total_current_balance,
        'total_available_credit': total_available_credit,
        'average_utilization': average_utilization
    }
    
    # Loan Summary
    loans = Loan.objects.filter(user=user, is_active=True)
    loan_totals = loans.aggregate(
        total_principal_amount=Sum('principal_amount'),
        total_current_balance=Sum('current_balance')
    )
    
    total_principal_amount = loan_totals['total_principal_amount'] or Decimal('0.00')
    total_loan_balance = loan_totals['total_current_balance'] or Decimal('0.00')
    total_paid_amount = total_principal_amount - total_loan_balance
    
    if total_principal_amount > 0:
        average_completion_percentage = (total_paid_amount / total_principal_amount) * 100
    else:
        average_completion_percentage = Decimal('0.00')
    
    loan_summary = {
        'total_loans': loans.count(),
        'total_principal_amount': total_principal_amount,
        'total_current_balance': total_loan_balance,
        'total_paid_amount': total_paid_amount,
        'average_completion_percentage': average_completion_percentage
    }
    
    # Combined EMI Summary
    today = date.today()
    
    # Get all active EMIs
    credit_card_emis = CreditCardEMI.objects.filter(user=user, status__in=['PENDING', 'OVERDUE'])
    loan_emis = LoanEMI.objects.filter(user=user, status__in=['PENDING', 'OVERDUE'])
    
    # Calculate EMIs due this month using dynamic due date logic
    credit_card_emi_this_month = Decimal('0.00')
    loan_emi_this_month = Decimal('0.00')
    
    for emi in credit_card_emis:
        if emi.is_due_this_month:
            credit_card_emi_this_month += emi.emi_amount
            
    for emi in loan_emis:
        if emi.is_due_this_month:
            loan_emi_this_month += emi.emi_amount
    
    total_emi_due_this_month = credit_card_emi_this_month + loan_emi_this_month
    
    # Calculate overdue EMIs using is_overdue property
    overdue_credit_card_emis = sum(1 for emi in credit_card_emis if emi.is_overdue)
    overdue_loan_emis = sum(1 for emi in loan_emis if emi.is_overdue)
    total_overdue_emis = overdue_credit_card_emis + overdue_loan_emis
    
    # Recent Payments (last 30 days)
    thirty_days_ago = today - timedelta(days=30)
    recent_credit_card_payments = CreditCardPayment.objects.filter(
        user=user,
        payment_date__gte=thirty_days_ago
    ).order_by('-payment_date')[:5]
    
    recent_loan_payments = LoanPayment.objects.filter(
        user=user,
        payment_date__gte=thirty_days_ago
    ).order_by('-payment_date')[:5]
    
    # Upcoming payments using dynamic due date calculation
    upcoming_payments = []
    
    # Add credit card EMI upcoming payments
    for emi in credit_card_emis:
        upcoming_dates = emi.get_upcoming_payment_dates(limit=2)  # Next 2 payments per EMI
        for due_date in upcoming_dates:
            upcoming_payments.append({
                'type': 'credit_card',
                'title': f"{emi.credit_card.card_name} EMI",
                'amount': float(emi.emi_amount),
                'dueDate': due_date.isoformat(),
                'status': 'OVERDUE' if due_date < today else 'PENDING',
                'isPaid': False,
                'isOverdue': due_date < today,
                'isDueThisMonth': due_date.year == today.year and due_date.month == today.month,
            })
    
    # Add loan EMI upcoming payments
    for emi in loan_emis:
        upcoming_dates = emi.get_upcoming_payment_dates(limit=2)  # Next 2 payments per EMI
        for due_date in upcoming_dates:
            upcoming_payments.append({
                'type': 'loan',
                'title': f"{emi.loan.loan_name} EMI",
                'amount': float(emi.emi_amount),
                'dueDate': due_date.isoformat(),
                'status': 'OVERDUE' if due_date < today else 'PENDING',
                'isPaid': False,
                'isOverdue': due_date < today,
                'isDueThisMonth': due_date.year == today.year and due_date.month == today.month,
            })
    
    # Sort by due date and limit to 10 total items
    upcoming_payments.sort(key=lambda x: x['dueDate'])
    upcoming_payments = upcoming_payments[:10]
    
    # Get limited sets for upcoming_emis response (for backward compatibility)
    upcoming_cc_emis = []
    upcoming_loan_emis = []
    
    for emi in credit_card_emis:
        next_date = emi.next_due_date
        if next_date and next_date >= today:
            upcoming_cc_emis.append(emi)
    
    for emi in loan_emis:
        next_date = emi.next_due_date
        if next_date and next_date >= today:
            upcoming_loan_emis.append(emi)
    
    # Sort by next_due_date and limit
    upcoming_cc_emis.sort(key=lambda x: x.next_due_date or date.max)
    upcoming_loan_emis.sort(key=lambda x: x.next_due_date or date.max)
    upcoming_cc_emis = upcoming_cc_emis[:5]
    upcoming_loan_emis = upcoming_loan_emis[:5]
    
    return Response({
        'credit_card_summary': credit_card_summary,
        'loan_summary': loan_summary,
        'emi_summary': {
            'total_emi_due_this_month': float(total_emi_due_this_month),
            'total_credit_card_emi': float(credit_card_emi_this_month),
            'total_loan_emi': float(loan_emi_this_month),
            'total_overdue_emis': total_overdue_emis,
            'overdue_credit_card_emis': overdue_credit_card_emis,
            'overdue_loan_emis': overdue_loan_emis,
        },
        'recent_payments': {
            'credit_card_payments': CreditCardPaymentSerializer(recent_credit_card_payments, many=True).data,
            'loan_payments': LoanPaymentSerializer(recent_loan_payments, many=True).data,
        },
        'upcoming_emis': {
            'credit_card_emis': CreditCardEMISerializer(upcoming_cc_emis, many=True).data,
            'loan_emis': LoanEMISerializer(upcoming_loan_emis, many=True).data,
        }
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
@swagger_auto_schema(
    operation_summary="Enhanced dashboard endpoint matching mobile app requirements",
    security=[{'Bearer': []}],
    responses={
        200: openapi.Response(
            description="Enhanced dashboard data",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'totalEMIDueThisMonth': openapi.Schema(type=openapi.TYPE_NUMBER),
                    'totalCreditCardEMI': openapi.Schema(type=openapi.TYPE_NUMBER),
                    'totalLoanEMI': openapi.Schema(type=openapi.TYPE_NUMBER),
                    'totalRemainingAmount': openapi.Schema(type=openapi.TYPE_NUMBER),
                    'upcomingPayments': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_OBJECT)),
                    'credit_card_summary': openapi.Schema(type=openapi.TYPE_OBJECT),
                    'loan_summary': openapi.Schema(type=openapi.TYPE_OBJECT),
                    'emi_summary': openapi.Schema(type=openapi.TYPE_OBJECT),
                    'user': openapi.Schema(type=openapi.TYPE_OBJECT)
                }
            )
        )
    }
)
def enhanced_dashboard(request):
    """
    Enhanced dashboard endpoint matching mobile app requirements
    """
    user = request.user
    today = date.today()
    
    # Get all active EMIs
    all_active_cc_emis = CreditCardEMI.objects.filter(
        user=user,
        status__in=['PENDING', 'OVERDUE']
    )
    all_active_loan_emis = LoanEMI.objects.filter(
        user=user,
        status__in=['PENDING', 'OVERDUE']
    )
    
    # Calculate EMIs due this month based on recurring schedule
    credit_card_emi_this_month = Decimal('0.00')
    loan_emi_this_month = Decimal('0.00')
    
    for emi in all_active_cc_emis:
        if emi.is_due_this_month:
            credit_card_emi_this_month += emi.emi_amount
            
    for emi in all_active_loan_emis:
        if emi.is_due_this_month:
            loan_emi_this_month += emi.emi_amount
    
    total_emi_due_this_month = credit_card_emi_this_month + loan_emi_this_month
    
    # Calculate total monthly EMI amounts (for all active EMIs)
    total_monthly_credit_card_emi = all_active_cc_emis.aggregate(
        total=Sum('emi_amount'))['total'] or Decimal('0.00')
    total_monthly_loan_emi = all_active_loan_emis.aggregate(
        total=Sum('emi_amount'))['total'] or Decimal('0.00')
    total_monthly_emi = total_monthly_credit_card_emi + total_monthly_loan_emi
    
    # Calculate total remaining amounts
    credit_card_remaining = sum(
        emi.remaining_amount for emi in all_active_cc_emis
    )
    loan_remaining = sum(
        emi.remaining_amount for emi in all_active_loan_emis
    )
    total_remaining_amount = credit_card_remaining + loan_remaining
    
    # Generate upcoming payments based on recurring EMI schedules
    upcoming_payments = []
    
    # Add credit card EMI upcoming payments
    for emi in all_active_cc_emis:
        upcoming_dates = emi.get_upcoming_payment_dates(limit=3)  # Next 3 payments per EMI
        for due_date in upcoming_dates:
            upcoming_payments.append({
                'type': 'credit_card',
                'title': f"{emi.credit_card.card_name} EMI",
                'amount': float(emi.emi_amount),
                    'dueDate': due_date.isoformat(),
                    'status': 'OVERDUE' if due_date < today else 'PENDING',
                    'isPaid': False,
                    'isOverdue': due_date < today,
                    'isDueThisMonth': due_date.year == today.year and due_date.month == today.month,
                    'emi_id': emi.id,
                    'description': emi.description or ''
            })
    
    # Add loan EMI upcoming payments
    for emi in all_active_loan_emis:
        upcoming_dates = emi.get_upcoming_payment_dates(limit=3)  # Next 3 payments per EMI
        for due_date in upcoming_dates:
            upcoming_payments.append({
                'type': 'loan',
                'title': f"{emi.loan.loan_name} EMI",
                'amount': float(emi.emi_amount),
                    'dueDate': due_date.isoformat(),
                    'status': 'OVERDUE' if due_date < today else 'PENDING',
                    'isPaid': False,
                    'isOverdue': due_date < today,
                    'isDueThisMonth': due_date.year == today.year and due_date.month == today.month,
                    'emi_id': emi.id,
                    'description': emi.description or ''
            })
    
    # Sort by due date and limit to 10 total items
    upcoming_payments.sort(key=lambda x: x['dueDate'])
    upcoming_payments = upcoming_payments[:10]
    
    # Get summaries from individual apps
    credit_cards = CreditCard.objects.filter(user=user, is_active=True)
    credit_card_totals = credit_cards.aggregate(
        total_credit_limit=Sum('credit_limit'),
        total_current_balance=Sum('current_balance')
    )
    
    total_credit_limit = credit_card_totals['total_credit_limit'] or Decimal('0.00')
    total_current_balance = credit_card_totals['total_current_balance'] or Decimal('0.00')
    total_available_credit = total_credit_limit - total_current_balance
    
    if total_credit_limit > 0:
        average_utilization = (total_current_balance / total_credit_limit) * 100
    else:
        average_utilization = Decimal('0.00')
    
    credit_card_summary = {
        'total_cards': credit_cards.count(),
        'total_credit_limit': total_credit_limit,
        'total_current_balance': total_current_balance,
        'total_available_credit': total_available_credit,
        'average_utilization': average_utilization,
        'total_monthly_emi': total_monthly_credit_card_emi,
    }
    
    loans = Loan.objects.filter(user=user, is_active=True)
    loan_totals = loans.aggregate(
        total_principal_amount=Sum('principal_amount'),
        total_current_balance=Sum('current_balance')
    )
    
    total_principal_amount = loan_totals['total_principal_amount'] or Decimal('0.00')
    total_loan_balance = loan_totals['total_current_balance'] or Decimal('0.00')
    total_paid_amount = total_principal_amount - total_loan_balance
    
    if total_principal_amount > 0:
        average_completion_percentage = (total_paid_amount / total_principal_amount) * 100
    else:
        average_completion_percentage = Decimal('0.00')
    
    loan_summary = {
        'total_loans': loans.count(),
        'total_principal_amount': total_principal_amount,
        'total_current_balance': total_loan_balance,
        'total_paid_amount': total_paid_amount,
        'average_completion_percentage': average_completion_percentage,
        'total_monthly_emi': total_monthly_loan_emi,
    }
    
    # EMI summary
    all_credit_card_emis = CreditCardEMI.objects.filter(user=user)
    all_loan_emis = LoanEMI.objects.filter(user=user)
    
    total_emis = all_credit_card_emis.count() + all_loan_emis.count()
    pending_emis = (all_credit_card_emis.filter(status__in=['PENDING', 'OVERDUE']).count() + 
                   all_loan_emis.filter(status__in=['PENDING', 'OVERDUE']).count())
    overdue_emis = (all_credit_card_emis.filter(status='OVERDUE').count() + 
                   all_loan_emis.filter(status='OVERDUE').count())
    paid_emis = (all_credit_card_emis.filter(status='PAID').count() + 
                all_loan_emis.filter(status='PAID').count())
    
    # Find the next due EMI payment from all recurring schedules
    next_due_date = None
    next_due_amount = 0
    
    all_upcoming = []
    for emi in all_active_cc_emis:
        next_date = emi.next_due_date
        if next_date:
            all_upcoming.append((next_date, emi.emi_amount))
    
    for emi in all_active_loan_emis:
        next_date = emi.next_due_date
        if next_date:
            all_upcoming.append((next_date, emi.emi_amount))
    
    if all_upcoming:
        all_upcoming.sort(key=lambda x: x[0])
        next_due_date = all_upcoming[0][0]
        next_due_amount = float(all_upcoming[0][1])
    
    emi_summary = {
        'total_emis': total_emis,
        'pending_emis': pending_emis,
        'overdue_emis': overdue_emis,
        'paid_emis': paid_emis,
        'total_monthly_payment': float(total_monthly_emi),
        'next_due_date': next_due_date,
        'next_due_amount': next_due_amount
    }
    
    return Response({
        'totalEMIDueThisMonth': float(total_emi_due_this_month),
        'totalCreditCardEMI': float(total_monthly_credit_card_emi),
        'totalLoanEMI': float(total_monthly_loan_emi),
        'totalRemainingAmount': float(total_remaining_amount),
        'upcomingPayments': upcoming_payments,
        'credit_card_summary': credit_card_summary,
        'loan_summary': loan_summary,
        'emi_summary': emi_summary,
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
        }
    })
