import uuid
from django.db import models
from django.conf import settings
from Creation.models import Regulation, Semester, Department
from CourseConfiguration.models import Course
from AcademicSetup.models import Section
from CourseManagement.models import AcademicClass

# Document Request remains here
class DocumentRequest(models.Model):
    STATUS_CHOICES = [
        ('SUBMITTED', 'Submitted'),
        ('UNDER_REVIEW', 'Under Review'),
        ('ON_HOLD', 'On Hold'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('READY', 'Ready/Issued'),
    ]

    request_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    student = models.ForeignKey(
        'UserDataManagement.Student',
        on_delete=models.CASCADE,
        related_name='document_requests'
    )

    document_type = models.CharField(
        max_length=100,
        help_text="Bona fide / Memo / Certificate / TC etc"
    )

    purpose = models.TextField(
        help_text="Reason for requesting the document"
    )

    supporting_doc = models.FileField(
        upload_to='student_service_requests/',
        null=True,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='SUBMITTED'
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.document_type} - {self.student.roll_no}"


class DocumentRequestHistory(models.Model):
    history_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    request = models.ForeignKey(
        DocumentRequest,
        on_delete=models.CASCADE,
        related_name='history'
    )

    status = models.CharField(max_length=20)
    remark = models.TextField(blank=True, null=True)

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )

    updated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.request.request_id} → {self.status}"


# ============================================================
# IMPORTED FROM FACULTY APP (Consolidated Models)
# ============================================================
from faculty.models import (
    Assignment, 
    StudentSubmission, 
    Quiz, 
    Question, 
    Option, 
    StudentQuizAttempt, 
    StudentAnswer, 
    Resource
)
