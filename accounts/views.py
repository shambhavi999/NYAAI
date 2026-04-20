"""
NYAAI - accounts/views.py
Handles all authentication — register, login, logout, profile
"""

from django.contrib.auth.models import User
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    UserProfileSerializer
)
import logging

logger = logging.getLogger(__name__)


def get_tokens_for_user(user):
    """
    Generate JWT access + refresh tokens for a user.
    Called after register and login.
    """
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access':  str(refresh.access_token),
    }


class RegisterView(APIView):
    """
    POST /api/auth/register/
    Creates a new user account and returns JWT tokens.
    No authentication required.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()
            tokens = get_tokens_for_user(user)

            logger.info(f"[NYAAI] New user registered: {user.email}")

            return Response({
                'success': True,
                'message': f'Welcome to NYAAI, {user.first_name or user.username}! '
                           f'Your account has been created.',
                'user': {
                    'id':       user.id,
                    'username': user.username,
                    'email':    user.email,
                    'name':     f"{user.first_name} {user.last_name}".strip(),
                },
                'tokens': tokens,
            }, status=status.HTTP_201_CREATED)

        # Return first error message cleanly
        errors = serializer.errors
        first_error = next(iter(errors.values()))[0]
        return Response({
            'success': False,
            'message': str(first_error),
            'errors':  errors,
        }, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """
    POST /api/auth/login/
    Authenticates user and returns JWT tokens.
    No authentication required.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)

        if serializer.is_valid():
            user   = serializer.validated_data['user']
            tokens = get_tokens_for_user(user)

            logger.info(f"[NYAAI] User logged in: {user.email}")

            return Response({
                'success': True,
                'message': f'Welcome back, {user.first_name or user.username}!',
                'user': {
                    'id':       user.id,
                    'username': user.username,
                    'email':    user.email,
                    'name':     f"{user.first_name} {user.last_name}".strip(),
                    'language': user.profile.preferred_language,
                    'state':    user.profile.get_state_display(),
                },
                'tokens': tokens,
            }, status=status.HTTP_200_OK)

        errors = serializer.errors
        first_error = next(iter(errors.values()))[0]
        return Response({
            'success': False,
            'message': str(first_error),
        }, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    """
    POST /api/auth/logout/
    Blacklists refresh token so it can't be reused.
    Requires authentication.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')

            if not refresh_token:
                return Response({
                    'success': False,
                    'message': 'Refresh token is required.',
                }, status=status.HTTP_400_BAD_REQUEST)

            # Blacklist the token
            token = RefreshToken(refresh_token)
            token.blacklist()

            logger.info(f"[NYAAI] User logged out: {request.user.email}")

            return Response({
                'success': True,
                'message': 'Logged out successfully.',
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False,
                'message': 'Invalid or expired token.',
            }, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(APIView):
    """
    GET  /api/auth/profile/  → returns user profile
    PUT  /api/auth/profile/  → updates user profile
    Requires authentication.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Return current user's profile."""
        try:
            profile    = request.user.profile
            serializer = UserProfileSerializer(profile)
            return Response({
                'success': True,
                'profile': serializer.data,
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': False,
                'message': 'Could not fetch profile.',
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def put(self, request):
        """Update current user's profile."""
        try:
            profile    = request.user.profile
            serializer = UserProfileSerializer(
                profile,
                data=request.data,
                partial=True      # allow partial updates
            )

            if serializer.is_valid():
                serializer.save()
                return Response({
                    'success': True,
                    'message': 'Profile updated successfully.',
                    'profile': serializer.data,
                }, status=status.HTTP_200_OK)

            return Response({
                'success': False,
                'message': 'Invalid data.',
                'errors':  serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                'success': False,
                'message': 'Could not update profile.',
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UserStatsView(APIView):
    """
    GET /api/auth/stats/
    Returns user dashboard statistics.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            cases = user.cases.all()

            stats = {
                'total_cases':    cases.count(),
                'active_cases':   cases.filter(status='active').count(),
                'resolved_cases': cases.filter(status='resolved').count(),
                'notices_sent':   cases.filter(notice_sent=True).count(),
            }

            return Response({
                'success': True,
                'stats':   stats,
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({
                'success': True,
                'stats': {
                    'total_cases':    0,
                    'active_cases':   0,
                    'resolved_cases': 0,
                    'notices_sent':   0,
                },
            }, status=status.HTTP_200_OK)
