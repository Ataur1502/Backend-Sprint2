import uuid
from django.db import models
from Creation.models import Degree, Department

class Calendar(models.Model):
    calendar_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    name = models.CharField(max_length=100)
    academic_year = models.CharField(max_length=20)

    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [
            ('name', 'academic_year')
        ]

    def __str__(self):
        return f"{self.name} ({self.academic_year})"


class Holiday(models.Model):
    holiday_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    calendar = models.ForeignKey(
        Calendar,
        on_delete=models.CASCADE,
        related_name="holidays"
    )

    date = models.DateField()

    scope = models.CharField(
        max_length=20,
        choices=[
            ('CAMPUS', 'Campus Wide'),
            ('DEGREE', 'Degree Specific'),
            ('DEPARTMENT', 'Department Specific'),
        ]
    )

    degree = models.ForeignKey(
        Degree,
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )

    department = models.ForeignKey(
        Department,
        null=True,
        blank=True,
        on_delete=models.CASCADE
    )

    reason = models.CharField(max_length=255)

    class Meta:
        unique_together = [
            ('calendar', 'date', 'scope', 'degree', 'department')
        ]

    def __str__(self):
        return f"{self.date} - {self.reason}"
