import uuid
from django.db import models
from django.conf import settings
from Creation.models import School, Department

class Faculty(models.Model):
    GENDER_CHOICES = [
        ('MALE', 'Male'),
        ('FEMALE', 'Female'),
        ('OTHER', 'Other'),
    ]

    faculty_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='faculty_profile')
    
    employee_id = models.CharField(max_length=50, unique=True, help_text="Unique Employee ID")
    full_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    mobile_no = models.CharField(max_length=15, blank=True, null=True)
    dob = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Faculties"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} ({self.employee_id})"

class FacultyMapping(models.Model):
    mapping_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name='mappings')
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        unique_together = ['faculty', 'school', 'department']

    def __str__(self):
        return f"{self.faculty.full_name} -> {self.school.school_name}" + (f" ({self.department.dept_name})" if self.department else "")
