from django.urls import path
from .views import dashboard, enhanced_dashboard

app_name = 'dashboard'
 
urlpatterns = [
    path('', dashboard, name='dashboard'),
    path('enhanced/', enhanced_dashboard, name='enhanced_dashboard'),
] 