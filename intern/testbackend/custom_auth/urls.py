from django.urls import path
from .views import (
    LoginView, MFAVerifyView, DuoWebhookView,
    ForgotPasswordView, ForgotPasswordOTPVerifyView,
    ForgotPasswordResetView, ResetPasswordRequestView,
    GoogleLogin, ActionMFAInitiateView, ActionMFACheckView
)
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    # Unified Login and Multi-Factor Verification
    path('login/', LoginView.as_view(), name='login'),
    path('mfa-verify/', MFAVerifyView.as_view(), name='mfa-verify'),
    
    # Action-Specific MFA for Logged-in Users
    path('action-mfa/initiate/', ActionMFAInitiateView.as_view(), name='action-mfa-initiate'),
    path('action-mfa/check/<str:mfa_id>/', ActionMFACheckView.as_view(), name='action-mfa-check'),
    
    # Social Login
    path('google/', GoogleLogin.as_view(), name='google_login'),

    # Forgot Password Flow (Email OTP based)
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('forgot-password/verify-otp/', ForgotPasswordOTPVerifyView.as_view(), name='forgot-password-verify'),
    path('forgot-password/reset/', ForgotPasswordResetView.as_view(), name='forgot-password-reset'),

    # Logged-in One-time Reset
    path('reset-password/', ResetPasswordRequestView.as_view(), name='reset-password'),

    # Duo webhook for async auth callbacks
    path('duo/webhook/', DuoWebhookView.as_view(), name='duo-webhook'),

    # Token management
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Backward compatibility for old client endpoints
    path('admin-login/', LoginView.as_view()),
    path('admin-verify-otp/', MFAVerifyView.as_view()),
]
