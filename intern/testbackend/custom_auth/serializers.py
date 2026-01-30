from rest_framework import serializers
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import User, MFASession

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        # Lookup user by email and verify password (supports email-based login)
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError('Invalid credentials.')

        if not user.check_password(password):
            raise serializers.ValidationError('Invalid credentials.')

        # Use hardcoded role values as the canonical reference for MFA-allowed roles
        allowed_roles = ['COLLEGE_ADMIN', 'ACADEMIC_COORDINATOR', 'college_admin', 'accedemic_coordinator']
        if user.role not in allowed_roles:
            raise serializers.ValidationError('Role not authorized for MFA.') 

        attrs['user'] = user
        return attrs

class MFAVerifySerializer(serializers.Serializer):
    mfa_id = serializers.UUIDField(required=True)
    otp = serializers.CharField(max_length=6, required=False, allow_blank=True)

    def validate(self, attrs):
        mfa_id = attrs.get('mfa_id')
        otp = attrs.get('otp')

        try:
            mfa_session = MFASession.objects.get(id=mfa_id)
        except MFASession.DoesNotExist:
            raise serializers.ValidationError('MFA session not found.')

        # Check if already verified (e.g. immediate push approval)
        if mfa_session.is_verified:
            attrs['user'] = mfa_session.user
            attrs['mfa_session'] = mfa_session
            return attrs

        # Try Duo Passcode verification first if provided
        if otp:
            from .utils import verify_duo_passcode
            success, message = verify_duo_passcode(mfa_session.user.email, otp)
            if success:
                attrs['user'] = mfa_session.user
                attrs['mfa_session'] = mfa_session
                return attrs
            else:
                raise serializers.ValidationError(message)

        # If no (valid) passcode provided, check Duo Push status if applicable
        if mfa_session.duo_txid:
            from .utils import check_duo_status
            status, message, session = check_duo_status(mfa_id)
            if status == 'allow':
                attrs['user'] = mfa_session.user
                attrs['mfa_session'] = session
                return attrs
            if status == 'deny':
                raise serializers.ValidationError(f'MFA denied: {message}')
            # still pending
            raise serializers.ValidationError('MFA pending approval in your Duo app.')

        raise serializers.ValidationError('Verification required. Please enter a Duo Passcode.')


# =====================================================
# FORGOT PASSWORD SERIALIZERS
# =====================================================


User = get_user_model()


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate(self, attrs):
        user = User.objects.filter(email=attrs["email"]).first()
        if not user:
            raise serializers.ValidationError("User not found.")
        attrs["user"] = user
        return attrs


class ForgotPasswordOTPVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

    def validate(self, attrs):
        email = attrs["email"]
        otp = attrs["otp"]

        user = User.objects.filter(email=email).first()
        if not user:
            raise serializers.ValidationError("User not found.")

        # 🔑 Always check latest unverified OTP
        mfa = MFASession.objects.filter(
            user=user,
            is_verified=False
        ).order_by("-created_at").first()

        if not mfa:
            raise serializers.ValidationError("No active OTP found.")

        if mfa.expires_at < timezone.now():
            raise serializers.ValidationError("OTP expired.")

        if mfa.otp != otp:
            raise serializers.ValidationError("Invalid OTP.")

        attrs["user"] = user
        attrs["mfa_session"] = mfa
        return attrs


class ForgotPasswordResetSerializer(serializers.Serializer):
    mfa_id = serializers.UUIDField()
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError("Passwords do not match.")
        return attrs

# =====================================================
# RESET PASSWORD (LOGGED-IN, ONE TIME)
# =====================================================

class ResetPasswordRequestSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)  # existing password
    new_password = serializers.CharField(min_length=8, write_only=True)
    confirm_password = serializers.CharField(min_length=8, write_only=True)
    refresh = serializers.CharField(write_only=True)  # refresh token for de-tokenisation

    def validate(self, attrs):
        user = self.context["request"].user

        if not user.check_password(attrs["password"]):
            raise serializers.ValidationError("Existing password is incorrect.")

        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError("New passwords do not match.")

        return attrs
