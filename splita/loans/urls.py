from django.urls import path
from .views import (
    # Loan Views
    LoanListCreateView, LoanDetailView, LoanDetailWithEMIsView,
    
    # Loan EMI Views
    LoanEMIListView, LoanEMICreateView, LoanEMIDetailView, MarkLoanEMIPaidView,
    
    # Payment Views
    LoanPaymentListCreateView, LoanPaymentDetailView,
    
    # Summary and utility Views
    loan_summary, loan_emi_summary, enhanced_loan_emi_list, 
    generate_loan_emi_schedule
)

app_name = 'loans'

urlpatterns = [
    # Loan URLs
    path('', LoanListCreateView.as_view(), name='loan_list_create'),
    path('<int:pk>/', LoanDetailView.as_view(), name='loan_detail'),
    path('<int:pk>/details/', LoanDetailWithEMIsView.as_view(), name='loan_detail_with_emis'),
    
    # Loan EMI URLs
    path('<int:loan_id>/emis/', LoanEMIListView.as_view(), name='loan_emi_list'),
    path('<int:loan_id>/emis/enhanced/', enhanced_loan_emi_list, name='enhanced_loan_emi_list'),
    path('<int:loan_id>/emis/create/', LoanEMICreateView.as_view(), name='loan_emi_create'),
    path('<int:loan_id>/emis/generate-schedule/', generate_loan_emi_schedule, name='loan_emi_schedule'),
    path('<int:loan_id>/emis/summary/', loan_emi_summary, name='loan_emi_summary'),
    path('emis/<int:pk>/', LoanEMIDetailView.as_view(), name='loan_emi_detail'),
    path('emis/<int:emi_id>/mark-paid/', MarkLoanEMIPaidView.as_view(), name='mark_loan_emi_paid'),
    path('emis/enhanced/', enhanced_loan_emi_list, name='enhanced_all_loan_emis'),
    
    # Payment URLs
    path('payments/', LoanPaymentListCreateView.as_view(), name='loan_payment_list_create'),
    path('payments/<int:pk>/', LoanPaymentDetailView.as_view(), name='loan_payment_detail'),
    
    # Summary URLs
    path('summary/', loan_summary, name='loan_summary'),
] 