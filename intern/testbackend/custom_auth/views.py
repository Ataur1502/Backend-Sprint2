from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from django.utils import timezone
from django.db.models import Q
from django.conf import settings

from .serializers import (
    LoginSerializer, 
    MFAVerifySerializer,
    ForgotPasswordSerializer,
    ForgotPasswordOTPVerifySerializer,
    ForgotPasswordResetSerializer,
    ResetPasswordRequestSerializer
)
from .utils import send_duo_push, send_otp_email
from .models import User, MFASession

from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView

class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    callback_url = "http://localhost:3000/login" 
    client_class = OAuth2Client
    authentication_classes = []  # Ensure this endpoint is public and ignores old tokens

    def post(self, request, *args, **kwargs):
        self.request = request
        self.serializer = self.get_serializer(data=self.request.data)
        try:
            self.serializer.is_valid(raise_exception=True)
        except Exception as e:
            # Check if this is a "not registered" error
            detail = str(e)
            if "already registered" in detail:
                 # This usually happens if allauth finds the email but it's not linked, 
                 # and auto-signup is off.
                 return Response({'detail': 'Email is already registered. Please login with password or link your Google account.'}, status=status.HTTP_400_BAD_REQUEST)
            return Response({'detail': 'Unauthorized: Your email is not registered in our system.'}, status=status.HTTP_401_UNAUTHORIZED)

        self.login()
        
        # After successful social login, allauth has linked/found the user
        user = self.user
        
        if user.role in MFA_ALLOWED_ROLES:
            # Trigger Duo MFA
            success, msg, mfa_id = send_duo_push(user.email)
            if not mfa_id:
                return Response({'detail': msg}, status=status.HTTP_429_TOO_MANY_REQUESTS)
            
            return Response({
                'mfa_required': True,
                'role': user.role,
                'email': user.email,
                'mfa_id': mfa_id,
                'push_success': success,
                'message': msg if not success else 'Approve the Duo push in your Duo Mobile app.'
            })

        # Manual token return for consistency across all login methods
        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'role': user.role,
            'email': user.email
        })

# Roles that require Multi-Factor Authentication
MFA_ALLOWED_ROLES = ["COLLEGE_ADMIN", "ACADEMIC_COORDINATOR", "college_admin", "accedemic_coordinator"]

class LoginView(APIView):
    """Unified login endpoint supporting username or email.
    
    - For non-MFA roles (STUDENT, FACULTY): returns access & refresh tokens immediately.
    - For MFA roles: initiates Duo Push and returns mfa_id/mfa_required.
    """
    authentication_classes = []
    permission_classes = []
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def post(self, request):
        username = request.data.get('username') or request.data.get('email')
        password = request.data.get('password')

        if not username or not password:
            return Response({'detail': 'Username/email and password are required.'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(Q(username=username) | Q(email=username)).first()
        if not user or not user.check_password(password):
            return Response({'detail': 'Invalid username/email or password.'}, status=status.HTTP_401_UNAUTHORIZED)

        if user.role in MFA_ALLOWED_ROLES:
            # Try Duo Push
            success, msg, mfa_id = send_duo_push(user.email)
            
            if not mfa_id:
                return Response({'detail': msg}, status=status.HTTP_429_TOO_MANY_REQUESTS)

            # We always return the mfa_id if it exists, allowing passcode fallback
            return Response({
                'mfa_required': True, 
                'role': user.role, 
                'email': user.email, 
                'mfa_id': mfa_id, 
                'push_success': success,
                'message': msg if not success else 'Approve the Duo push in your Duo Mobile app.'
            })

        refresh = RefreshToken.for_user(user)
        return Response({'access': str(refresh.access_token), 'refresh': str(refresh), 'role': user.role})


class MFAVerifyView(APIView):
    """Unified verification endpoint for both Duo Push and legacy OTP.
    Polled by the client or called once the Duo Push is approved.
    """
    authentication_classes = []
    permission_classes = []
    def post(self, request):
        serializer = MFAVerifySerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            mfa_session = serializer.validated_data['mfa_session']
            
            # Ensure session is marked as verified
            mfa_session.is_verified = True
            mfa_session.save()

            refresh = RefreshToken.for_user(user)
            return Response({
                'mfa_verified': True,
                'mfa_id': str(mfa_session.id),
                'role': user.role,
                'email': user.email,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# =====================================================
# FORGOT PASSWORD FLOW
# =====================================================

class ForgotPasswordView(APIView):
    """Initiates the forgot password flow by sending an OTP to the admin's email."""
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]

            if user.role not in MFA_ALLOWED_ROLES:
                return Response(
                    {"detail": "Access denied. Restricted to admin roles."},
                    status=status.HTTP_403_FORBIDDEN
                )

            success, msg, _ = send_otp_email(user.email)
            if not success:
                return Response({"detail": msg}, status=status.HTTP_400_BAD_REQUEST)

            return Response({"otp_sent": True, "message": "OTP sent to email"})

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ForgotPasswordOTPVerifyView(APIView):
    """Verifies the OTP sent for the forgot password flow."""
    def post(self, request):
        serializer = ForgotPasswordOTPVerifySerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]

            if user.role not in MFA_ALLOWED_ROLES:
                return Response(
                    {"detail": "Access denied. Restricted to admin roles."},
                    status=status.HTTP_403_FORBIDDEN
                )

            mfa = serializer.validated_data["mfa_session"]
            mfa.is_verified = True
            mfa.save()

            return Response({"otp_verified": True})

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ForgotPasswordResetView(APIView):
    """Sets the new password after the OTP has been verified."""
    def post(self, request):
        serializer = ForgotPasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            # Get the latest verified session for recovery
            try:
                mfa = MFASession.objects.filter(is_verified=True).latest("created_at")
            except MFASession.DoesNotExist:
                return Response({"detail": "No verified session found."}, status=status.HTTP_400_BAD_REQUEST)

            user = mfa.user
            if user.role not in MFA_ALLOWED_ROLES:
                return Response(
                    {"detail": "Access denied. Restricted to admin roles."},
                    status=status.HTTP_403_FORBIDDEN
                )

            user.set_password(serializer.validated_data["new_password"])
            user.password_last_changed_at = timezone.now()
            user.save()

            mfa.delete()  # Cleanup session after use
            return Response({"password_reset": True, "message": "Password reset successfully."})

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# =====================================================
# RESET PASSWORD (LOGGED IN)
# =====================================================

class ResetPasswordRequestView(APIView):
    """Allows a logged-in admin to change their password once."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if user.is_password_reset_done:
            return Response(
                {"detail": "Password reset is allowed only once."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ResetPasswordRequestSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            user.set_password(serializer.validated_data["new_password"])
            user.is_password_reset_done = True
            user.password_last_changed_at = timezone.now()
            user.save()

            # Blacklist the current session to force re-login
            refresh_token = serializer.validated_data.get("refresh")
            try:
                RefreshToken(refresh_token).blacklist()
            except Exception:
                pass 

            return Response({
                "password_changed": True,
                "message": "Password updated successfully. Please log in again."
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# =====================================================
# SYSTEM WEBHOOKS
# =====================================================

class DuoWebhookView(APIView):
    """Receiver for async callbacks from Duo security service."""
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        import hmac, hashlib, logging
        logger = logging.getLogger(__name__)

        secret = getattr(settings, 'DUO_WEBHOOK_SECRET', None)
        body = request.body or b''

        if secret:
            signature = request.headers.get('X-Duo-Signature')
            if not signature:
                return Response({'detail': 'missing signature'}, status=status.HTTP_403_FORBIDDEN)

            sig_hex = signature.split('=')[-1]
            expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(sig_hex, expected):
                return Response({'detail': 'invalid signature'}, status=status.HTTP_403_FORBIDDEN)

        payload = request.data
        txid = payload.get('txid') or payload.get('txId') or payload.get('tx_id')
        result = payload.get('result') or payload.get('status')

        if not txid or not result:
            return Response({'detail': 'invalid payload'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            mfa = MFASession.objects.get(duo_txid=txid)
        except MFASession.DoesNotExist:
            return Response({'detail': 'session not found'}, status=status.HTTP_404_NOT_FOUND)

        if result in ('allow', 'approved'):
            mfa.duo_status = 'allow'
            mfa.is_verified = True
        elif result in ('deny', 'denied'):
            mfa.duo_status = 'deny'
        else:
            mfa.duo_status = str(result)

        mfa.save()
        return Response({'ok': True})
