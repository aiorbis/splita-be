from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    UserRegistrationView, UserLoginView, UserLogoutView, UserProfileView,
    ChangePasswordView, UserSessionsView, DeactivateSessionView,
    UpdateFCMTokenView, user_dashboard
)

app_name = 'accounts'

urlpatterns = [
    # Authentication
    path('register/', UserRegistrationView.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Profile Management
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    
    # Session Management
    path('sessions/', UserSessionsView.as_view(), name='sessions'),
    path('sessions/<int:session_id>/deactivate/', DeactivateSessionView.as_view(), name='deactivate_session'),
    
    # FCM Token
    path('fcm-token/', UpdateFCMTokenView.as_view(), name='update_fcm_token'),
    
    # Dashboard
    path('dashboard/', user_dashboard, name='dashboard'),
] 