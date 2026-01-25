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

class TimeTableTemplate(models.Model):
    template_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name="timetable_templates")
    degree = models.ForeignKey(Degree, on_delete=models.CASCADE, related_name="timetable_templates")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name="timetable_templates")
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name="timetable_templates")
    
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class TimeSlot(models.Model):
    DAYS_OF_WEEK = [
        ('MONDAY', 'Monday'),
        ('TUESDAY', 'Tuesday'),
        ('WEDNESDAY', 'Wednesday'),
        ('THURSDAY', 'Thursday'),
        ('FRIDAY', 'Friday'),
        ('SATURDAY', 'Saturday'),
        ('SUNDAY', 'Sunday'),
    ]
    
    slot_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(TimeTableTemplate, on_delete=models.CASCADE, related_name='slots')
    
    day = models.CharField(max_length=10, choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_order = models.PositiveIntegerField()
    slot_type = models.CharField(max_length=50, blank=True, null=True, help_text="e.g. Theory, Lab, Break")

    class Meta:
        ordering = ['day', 'slot_order']
        constraints = [
            models.UniqueConstraint(
                fields=['template', 'day', 'slot_order'], 
                name='unique_template_day_slot_order'
            )
        ]

    def __str__(self):
        return f"{self.day} - Slot {self.slot_order} ({self.start_time} - {self.end_time})"
