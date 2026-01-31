import uuid
from django.db import models
from django.conf import settings

class DocumentRequest(models.Model):
    STATUS_CHOICES = [
        ('UNDER_REVIEW', 'Under Review'),
        ('IN_HOLD', 'In Hold (Need Details)'),
        ('APPROVED', 'Approved'),
        ('ISSUED', 'Issued'),
        ('REJECTED', 'Rejected'),
    ]

    request_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='document_requests'
    )

    document_type = models.CharField(
        max_length=100,
        help_text="Bonafide / Memo / TC / etc"
    )

    message = models.TextField(
        blank=True,
        null=True,
        help_text="Optional message from student"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='UNDER_REVIEW'
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.document_type} - {self.student.email}"


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
