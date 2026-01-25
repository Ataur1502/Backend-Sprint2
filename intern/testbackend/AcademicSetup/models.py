import uuid
from django.db import models
from Creation.models import School, Degree, Department, Regulation, Semester

class AcademicCalendar(models.Model):
    calendar_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="calendars")
    degree = models.ForeignKey(Degree, on_delete=models.CASCADE, related_name="calendars")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="calendars")
    regulation = models.ForeignKey(Regulation, on_delete=models.CASCADE, related_name="calendars")
    batch = models.CharField(max_length=50) # e.g., 2025-2026
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name="calendars")
    
    excel_file = models.FileField(upload_to='academic_calendars/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['regulation', 'batch', 'semester'], 
                condition=models.Q(is_active=True),
                name='unique_active_calendar'
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.batch} - {self.semester.sem_name})"

class CalendarEvent(models.Model):
    EVENT_TYPES = [
        ('INSTRUCTION', 'Instruction Period'),
        ('HOLIDAY', 'Holiday'),
        ('EXAM', 'Examination'),
        ('OTHER', 'Other'),
    ]
    
    event_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    calendar = models.ForeignKey(AcademicCalendar, on_delete=models.CASCADE, related_name='events')
    
    type = models.CharField(max_length=20, choices=EVENT_TYPES)
    name = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    description = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['start_date']

    def __str__(self):
        return f"{self.type}: {self.name} ({self.start_date} - {self.end_date})"
