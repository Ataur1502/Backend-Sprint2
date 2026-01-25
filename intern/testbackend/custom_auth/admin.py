from django.contrib import admin
from .models import User, MFASession

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'role', 'is_active', 'date_joined']
    list_filter = ['role', 'is_active', 'is_staff']
    search_fields = ['username', 'email']

@admin.register(MFASession)
class MFASessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'otp', 'expires_at', 'is_verified', 'created_at']
    list_filter = ['is_verified', 'expires_at']
