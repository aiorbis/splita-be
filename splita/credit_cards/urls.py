from django.urls import path
from .views import (
    # Credit Card Views
    CreditCardListCreateView, CreditCardDetailView, CreditCardDetailWithEMIsView,
    
    # Credit Card EMI Views
    CreditCardEMIListView, CreditCardEMICreateView, CreditCardEMIDetailView, MarkCreditCardEMIPaidView,
    
    # Payment Views
    CreditCardPaymentListCreateView, CreditCardPaymentDetailView,
    
    # Summary and utility Views
    credit_card_summary, credit_card_emi_summary, enhanced_credit_card_emi_list, 
    generate_credit_card_emi_schedule
)

app_name = 'credit_cards'

urlpatterns = [
    # Credit Card URLs
    path('', CreditCardListCreateView.as_view(), name='credit_card_list_create'),
    path('<int:pk>/', CreditCardDetailView.as_view(), name='credit_card_detail'),
    path('<int:pk>/details/', CreditCardDetailWithEMIsView.as_view(), name='credit_card_detail_with_emis'),
    
    # Credit Card EMI URLs
    path('<int:credit_card_id>/emis/', CreditCardEMIListView.as_view(), name='credit_card_emi_list'),
    path('<int:credit_card_id>/emis/enhanced/', enhanced_credit_card_emi_list, name='enhanced_credit_card_emi_list'),
    path('<int:credit_card_id>/emis/create/', CreditCardEMICreateView.as_view(), name='credit_card_emi_create'),
    path('<int:credit_card_id>/emis/generate-schedule/', generate_credit_card_emi_schedule, name='credit_card_emi_schedule'),
    path('<int:credit_card_id>/emis/summary/', credit_card_emi_summary, name='credit_card_emi_summary'),
    path('emis/<int:pk>/', CreditCardEMIDetailView.as_view(), name='credit_card_emi_detail'),
    path('emis/<int:emi_id>/mark-paid/', MarkCreditCardEMIPaidView.as_view(), name='mark_credit_card_emi_paid'),
    path('emis/enhanced/', enhanced_credit_card_emi_list, name='enhanced_all_credit_card_emis'),
    
    # Payment URLs
    path('payments/', CreditCardPaymentListCreateView.as_view(), name='credit_card_payment_list_create'),
    path('payments/<int:pk>/', CreditCardPaymentDetailView.as_view(), name='credit_card_payment_detail'),
    
    # Summary URLs
    path('summary/', credit_card_summary, name='credit_card_summary'),
] 