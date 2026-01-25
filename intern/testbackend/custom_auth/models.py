from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import uuid

# User Role Definitions
ROLE_CHOICES = (
    ("COLLEGE_ADMIN", "college admin"),
    ("ACADEMIC_COORDINATOR", "accedemic coordinator"),
    ("FACULTY", "Faculty"),
    ("STUDENT", "Student"),
)

class User(AbstractUser):
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, default="STUDENT")

    # Optional Duo username for users provisioned in Duo (use this for Duo Push lookups)
    duo_username = models.CharField(max_length=150, null=True, blank=True, help_text="Duo username or user_id for Duo API calls")
    
    # Password policy flags for one-time reset feature
    is_password_reset_done = models.BooleanField(default=False)
    password_last_changed_at = models.DateTimeField(null=True, blank=True)
    
    @property
    def is_campus_admin(self):
        return self.role == "ACADEMIC_COORDINATOR"
    
    @property
    def is_academic_admin(self):
        return self.role == "COLLEGE_ADMIN"

    def __str__(self):
        return f"{self.username} ({self.role})"

# MFA session tracking for Duo and OTP
class MFASession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6, null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    otp_attempts = models.IntegerField(default=0)

    # Duo integration fields
    duo_txid = models.CharField(max_length=200, null=True, blank=True)
    duo_status = models.CharField(max_length=30, default='pending')  # pending, allow, deny

    resend_count = models.IntegerField(default=0)
    last_resend_at = models.DateTimeField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"MFA Session for {self.user.username}"
