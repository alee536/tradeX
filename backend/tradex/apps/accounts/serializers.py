from rest_framework import serializers
from .models import User


class UserProfileSerializer(serializers.ModelSerializer):
    sponsor_link = serializers.ReadOnlyField()
    is_admin = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'full_name', 'email',
            'sponsor_code', 'sponsor_link', 'is_admin',
            'is_active', 'date_joined', 'wallet_address',
        ]

    def get_is_admin(self, obj):
        return obj.is_staff or obj.is_superuser


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    full_name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    sponsor_code = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Email already registered')
        return value

    def create(self, validated_data):
        from apps.sponsor.access import resolve_active_sponsor_by_ref

        sponsor_code = validated_data.pop('sponsor_code', None)
        sponsored_by = None
        if sponsor_code:
            code = (sponsor_code or '').strip()
            # Only active, admin-approved sponsors count (/ref/SLUG or legacy code).
            sponsored_by = resolve_active_sponsor_by_ref(code)
            if sponsored_by is None:
                sponsored_by = User.objects.filter(
                    sponsor_code=code,
                    sponsor_access_status=User.SPONSOR_ACCESS_ACTIVE,
                ).first()

        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            full_name=validated_data['full_name'],
            sponsored_by=sponsored_by,
        )
        return user


class RegisterVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(min_length=6, max_length=6)

    def validate_otp(self, value):
        code = (value or '').strip()
        if not code.isdigit() or len(code) != 6:
            raise serializers.ValidationError('Enter the 6-digit code from your email.')
        return code


class RegisterResendSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetResendSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(min_length=6, max_length=6)
    password = serializers.CharField(min_length=8, write_only=True)

    def validate_otp(self, value):
        code = (value or '').strip()
        if not code.isdigit() or len(code) != 6:
            raise serializers.ValidationError('Enter the 6-digit code from your email.')
        return code


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()
