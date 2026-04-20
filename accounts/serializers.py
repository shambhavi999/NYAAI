"""
NYAAI - accounts/serializers.py
Converts data between Python objects and JSON
"""

from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from rest_framework import serializers
from .models import UserProfile


class RegisterSerializer(serializers.ModelSerializer):
    """
    Handles new user registration.
    Validates all fields before creating user.
    """

    password = serializers.CharField(
        write_only=True,
        min_length=8,
        error_messages={
            'min_length': 'Password must be at least 8 characters.',
        }
    )
    confirm_password = serializers.CharField(write_only=True)
    phone = serializers.CharField(max_length=15, required=False, allow_blank=True)
    state = serializers.CharField(max_length=2, required=False, allow_blank=True)
    preferred_language = serializers.CharField(max_length=5, default='en')

    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'first_name',
            'last_name',
            'password',
            'confirm_password',
            'phone',
            'state',
            'preferred_language',
        ]

    def validate_email(self, value):
        """Make sure email is unique."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                'An account with this email already exists.'
            )
        return value

    def validate_username(self, value):
        """Make sure username is unique."""
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                'This username is already taken.'
            )
        return value

    def validate(self, data):
        """Make sure passwords match."""
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({
                'confirm_password': 'Passwords do not match.'
            })
        return data

    def create(self, validated_data):
        """Create user + automatically update their profile."""

        # Remove fields not in User model
        confirmed_password = validated_data.pop('confirm_password')
        phone = validated_data.pop('phone', '')
        state = validated_data.pop('state', '')
        preferred_language = validated_data.pop('preferred_language', 'en')
        password = validated_data.pop('password')

        # Create the User
        user = User.objects.create_user(
            password=password,
            **validated_data
        )

        # Update the auto-created profile
        user.profile.phone = phone
        user.profile.state = state
        user.profile.preferred_language = preferred_language
        user.profile.save()

        return user


class LoginSerializer(serializers.Serializer):
    """
    Handles user login.
    Accepts email + password.
    """

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')

        # Find user by email
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError(
                'No account found with this email address.'
            )

        # Check password
        user = authenticate(username=user.username, password=password)
        if not user:
            raise serializers.ValidationError(
                'Incorrect password. Please try again.'
            )

        if not user.is_active:
            raise serializers.ValidationError(
                'This account has been deactivated.'
            )

        data['user'] = user
        return data


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Returns full user profile data.
    Used for profile page and dashboard.
    """

    username    = serializers.CharField(source='user.username', read_only=True)
    email       = serializers.EmailField(source='user.email', read_only=True)
    first_name  = serializers.CharField(source='user.first_name')
    last_name   = serializers.CharField(source='user.last_name')
    full_name   = serializers.SerializerMethodField()
    total_cases = serializers.SerializerMethodField()
    state_name  = serializers.SerializerMethodField()
    joined      = serializers.DateTimeField(source='user.date_joined', read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            'username',
            'email',
            'first_name',
            'last_name',
            'full_name',
            'phone',
            'state',
            'state_name',
            'preferred_language',
            'avatar',
            'total_cases',
            'joined',
            'created_at',
        ]

    def get_full_name(self, obj):
        name = f"{obj.user.first_name} {obj.user.last_name}".strip()
        return name if name else obj.user.username

    def get_total_cases(self, obj):
        try:
            return obj.user.cases.count()
        except:
            return 0

    def get_state_name(self, obj):
        return obj.get_state_display() or 'Not set'

    def update(self, instance, validated_data):
        """Update both User and UserProfile fields."""

        # Extract user fields
        user_data = validated_data.pop('user', {})
        user = instance.user

        # Update User model fields
        if 'first_name' in user_data:
            user.first_name = user_data['first_name']
        if 'last_name' in user_data:
            user.last_name = user_data['last_name']
        user.save()

        # Update UserProfile fields
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        return instance