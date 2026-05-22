import jwt
import datetime
from django.conf import settings
from django.contrib.auth import authenticate
from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import User
from .serializers import (
    RegisterSerializer,
    RegisterVerifySerializer,
    RegisterResendSerializer,
    PasswordResetRequestSerializer,
    PasswordResetResendSerializer,
    PasswordResetConfirmSerializer,
    LoginSerializer,
    UserProfileSerializer,
)
from .password_reset import (
    PasswordResetError,
    confirm_password_reset,
    request_password_reset,
    resend_password_reset_otp,
)
from .signup_otp import SignupOtpError, request_signup_otp, resend_signup_otp, verify_signup_otp


def generate_token(user):
    payload = {
        'user_id': user.id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=settings.JWT_EXPIRY_HOURS),
        'iat': datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm='HS256')


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    return Response({'status': 'ok'})


def home(request):
    return render(request, 'home.html')


def _flow_error_response(exc):
    return Response(
        {'error': exc.message, 'code': exc.code},
        status=exc.http_status,
    )


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def register(request):
    """
    Legacy endpoint — signup requires email OTP verification first.
    Use register_request_otp and register_verify instead.
    """
    return Response(
        {
            'error': 'Email verification required before account creation.',
            'code': 'otp_required',
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def register_request_otp(request):
    """Step 1: validate signup details and send OTP to email."""
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        result = request_signup_otp(serializer.validated_data)
    except SignupOtpError as exc:
        return _flow_error_response(exc)

    return Response(result, status=status.HTTP_200_OK)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def register_verify(request):
    """Step 2: verify OTP and create the account."""
    serializer = RegisterVerifySerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        user = verify_signup_otp(
            serializer.validated_data['email'],
            serializer.validated_data['otp'],
        )
    except SignupOtpError as exc:
        return _flow_error_response(exc)

    token = generate_token(user)
    return Response({
        'token': token,
        'user': UserProfileSerializer(user).data,
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def register_resend_otp(request):
    """Resend OTP for a pending signup (cooldown applies)."""
    serializer = RegisterResendSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        result = resend_signup_otp(serializer.validated_data['email'])
    except SignupOtpError as exc:
        return _flow_error_response(exc)

    return Response(result, status=status.HTTP_200_OK)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def forgot_password_request(request):
    """Step 1: send password reset OTP (generic response if email unknown)."""
    serializer = PasswordResetRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        result = request_password_reset(serializer.validated_data['email'])
    except PasswordResetError as exc:
        return _flow_error_response(exc)

    return Response(result, status=status.HTTP_200_OK)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def forgot_password_resend(request):
    """Resend password reset OTP (cooldown applies)."""
    serializer = PasswordResetResendSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        result = resend_password_reset_otp(serializer.validated_data['email'])
    except PasswordResetError as exc:
        return _flow_error_response(exc)

    return Response(result, status=status.HTTP_200_OK)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def forgot_password_confirm(request):
    """Step 2: verify OTP and set new password."""
    serializer = PasswordResetConfirmSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    try:
        result = confirm_password_reset(
            serializer.validated_data['email'],
            serializer.validated_data['otp'],
            serializer.validated_data['password'],
        )
    except PasswordResetError as exc:
        return _flow_error_response(exc)

    return Response(result, status=status.HTTP_200_OK)


@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def login(request):
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    email = serializer.validated_data['username']
    password = serializer.validated_data['password']

    user = authenticate(request, email=email, password=password)
    if not user:
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

    if user.is_banned:
        return Response({'error': 'Account is banned'}, status=status.HTTP_403_FORBIDDEN)

    token = generate_token(user)
    return Response({
        'token': token,
        'user': UserProfileSerializer(user).data,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    return Response({'message': 'Logged out successfully'})


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def profile(request):
    if request.method == 'GET':
        return Response(UserProfileSerializer(request.user).data)

    serializer_data = {}
    if 'full_name' in request.data:
        serializer_data['full_name'] = request.data['full_name']
    if 'wallet_address' in request.data:
        serializer_data['wallet_address'] = request.data['wallet_address']

    for key, value in serializer_data.items():
        setattr(request.user, key, value)
    request.user.save()

    return Response(UserProfileSerializer(request.user).data)
