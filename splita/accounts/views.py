from django.shortcuts import render
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import UserSession
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserProfileSerializer,
    ChangePasswordSerializer, UserSessionSerializer, FCMTokenSerializer
)

User = get_user_model()


class UserRegistrationView(generics.CreateAPIView):
    """
    API view for user registration
    """
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    @swagger_auto_schema(
        operation_summary="Register a new user",
        operation_description="Create a new user account and return JWT tokens",
        request_body=UserRegistrationSerializer,
        responses={
            201: openapi.Response(
                description="User registered successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'user': openapi.Schema(type=openapi.TYPE_OBJECT),
                        'tokens': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'access': openapi.Schema(type=openapi.TYPE_STRING),
                                'refresh': openapi.Schema(type=openapi.TYPE_STRING)
                            }
                        )
                    }
                )
            ),
            400: openapi.Response(description="Bad request")
        }
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        # Create user session
        session = UserSession.objects.create(
            user=user,
            session_key=str(refresh.access_token)[:40],
            device_info=request.META.get('HTTP_USER_AGENT', ''),
            ip_address=self.get_client_ip(request)
        )
        
        return Response({
            'message': 'User registered successfully',
            'user': UserProfileSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class UserLoginView(APIView):
    """
    API view for user login
    """
    permission_classes = [permissions.AllowAny]
    
    @swagger_auto_schema(
        operation_summary="User login",
        operation_description="Authenticate user and return JWT tokens",
        request_body=UserLoginSerializer,
        responses={
            200: openapi.Response(
                description="Login successful",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'user': openapi.Schema(type=openapi.TYPE_OBJECT),
                        'tokens': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'access': openapi.Schema(type=openapi.TYPE_STRING),
                                'refresh': openapi.Schema(type=openapi.TYPE_STRING)
                            }
                        )
                    }
                )
            ),
            400: openapi.Response(description="Invalid credentials")
        }
    )
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        # Create or update user session
        session, created = UserSession.objects.get_or_create(
            user=user,
            session_key=str(refresh.access_token)[:40],
            defaults={
                'device_info': request.META.get('HTTP_USER_AGENT', ''),
                'ip_address': self.get_client_ip(request)
            }
        )
        
        if not created:
            session.last_activity = timezone.now()
            session.is_active = True
            session.save()
        
        return Response({
            'message': 'Login successful',
            'user': UserProfileSerializer(user).data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_200_OK)
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class UserLogoutView(APIView):
    """
    API view for user logout
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh_token')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            # Deactivate user session
            UserSession.objects.filter(user=request.user, is_active=True).update(is_active=False)
            
            return Response({
                'message': 'Logout successful'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': 'Invalid token'
            }, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    API view for user profile
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    """
    API view for changing password
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        # Deactivate all user sessions
        UserSession.objects.filter(user=user).update(is_active=False)
        
        return Response({
            'message': 'Password changed successfully'
        }, status=status.HTTP_200_OK)


class UserSessionsView(generics.ListAPIView):
    """
    API view to list user sessions
    """
    serializer_class = UserSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return UserSession.objects.filter(user=self.request.user, is_active=True)


class DeactivateSessionView(APIView):
    """
    API view to deactivate a specific session
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, session_id):
        try:
            session = UserSession.objects.get(id=session_id, user=request.user)
            session.is_active = False
            session.save()
            
            return Response({
                'message': 'Session deactivated successfully'
            }, status=status.HTTP_200_OK)
        except UserSession.DoesNotExist:
            return Response({
                'error': 'Session not found'
            }, status=status.HTTP_404_NOT_FOUND)


class UpdateFCMTokenView(APIView):
    """
    API view to update FCM token for push notifications
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = FCMTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        user.fcm_token = serializer.validated_data['fcm_token']
        user.save()
        
        return Response({
            'message': 'FCM token updated successfully'
        }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
@swagger_auto_schema(
    operation_summary="User dashboard data",
    operation_description="Get user profile and statistics for dashboard",
    security=[{'Bearer': []}],
    responses={
        200: openapi.Response(
            description="User dashboard data",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'user': openapi.Schema(type=openapi.TYPE_OBJECT),
                    'stats': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'credit_cards_count': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'loans_count': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'pending_emis_count': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'overdue_emis_count': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'total_monthly_payment': openapi.Schema(type=openapi.TYPE_NUMBER),
                        }
                    )
                }
            )
        )
    }
)
def user_dashboard(request):
    """
    API view for user dashboard data
    """
    user = request.user
    
    # Get user's credit cards and loans count
    credit_cards_count = user.credit_cards.filter(is_active=True).count()
    loans_count = user.loans.filter(is_active=True).count()
    
    # Get pending EMIs count
    pending_emis_count = user.emis.filter(status='PENDING').count()
    overdue_emis_count = user.emis.filter(status='OVERDUE').count()
    
    # Get total monthly payment
    from django.db.models import Sum
    total_monthly_payment = user.emis.filter(
        status__in=['PENDING', 'OVERDUE']
    ).aggregate(total=Sum('emi_amount'))['total'] or 0
    
    return Response({
        'user': UserProfileSerializer(user).data,
        'stats': {
            'credit_cards_count': credit_cards_count,
            'loans_count': loans_count,
            'pending_emis_count': pending_emis_count,
            'overdue_emis_count': overdue_emis_count,
            'total_monthly_payment': total_monthly_payment,
        }
    }, status=status.HTTP_200_OK)
