import uuid
from django.db import models
from Creation.models import School, Degree, Department, Regulation, Semester

class Course(models.Model):
    COURSE_TYPE_CHOICES = [
        ('CORE', 'Core'),
        ('ELECTIVE', 'Elective'),
        ('OPEN_ELECTIVE', 'Open Elective'),
        ('LAB', 'Lab'),
    ]
    
    COURSE_CATEGORY_CHOICES = [
        ('THEORY', 'Theory'),
        ('PRACTICAL', 'Practical'),
        ('PROJECT', 'Project'),
    ]

    course_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course_name = models.CharField(max_length=255)
    course_short_name = models.CharField(max_length=50, blank=True, null=True, help_text="Abbreviated course name")
    course_code = models.CharField(max_length=50, unique=True)
    course_type = models.CharField(max_length=20, choices=COURSE_TYPE_CHOICES)
    
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='courses')
    degree = models.ForeignKey(Degree, on_delete=models.CASCADE, related_name='courses')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='courses')
    regulation = models.ForeignKey(Regulation, on_delete=models.CASCADE, related_name='courses')
    
    credit_value = models.DecimalField(max_digits=5, decimal_places=2)
    
    lecture_hours = models.PositiveIntegerField(default=0)
    tutorial_hours = models.PositiveIntegerField(default=0)
    practical_hours = models.PositiveIntegerField(default=0)
    
    course_category = models.CharField(max_length=20, choices=COURSE_CATEGORY_CHOICES)
    status = models.BooleanField(default=True) # Active/Inactive

    class Meta:
        unique_together = ('course_code', 'regulation')

    @property
    def batch(self):
        """Backward compatibility property - returns batch from regulation."""
        return self.regulation.batch if self.regulation else None
    
    def __str__(self):
        return f"{self.course_name} ({self.course_code})"

class RegistrationWindow(models.Model):
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('COMPLETED', 'Completed'),
    ]

    window_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='registration_windows')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='registration_windows')
    batch = models.CharField(max_length=50)
    semester = models.ForeignKey(Semester, on_delete=models.CASCADE, related_name='registration_windows')
    regulation = models.ForeignKey(Regulation, on_delete=models.CASCADE, related_name='registration_windows')
    
    major_subjects = models.ManyToManyField(Course, related_name='major_in_windows')
    elective_subjects = models.ManyToManyField(Course, related_name='elective_in_windows')
    
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    
    is_active = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_datetime']

    def __str__(self):
        dept_name = self.department.dept_name if self.department else "N/A"
        sem_name = self.semester.sem_name if self.semester else "N/A"
        return f"Registration: {dept_name} - {self.batch} ({sem_name})"

    def clean(self):
        from django.core.exceptions import ValidationError
        # Check for overlapping active windows for same Dept + Batch + Sem
        if self.status == 'ACTIVE' and self.is_active:
            overlaps = RegistrationWindow.objects.filter(
                department=self.department,
                batch=self.batch,
                semester=self.semester,
                is_active=True,
                status='ACTIVE'
            ).exclude(pk=self.pk)
            if overlaps.exists():
                raise ValidationError("Only one Active Course Registration allowed per Department + Batch + Semester.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

from UserDataManagement.models import Student

class StudentSelection(models.Model):
    selection_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='course_selections')
    window = models.ForeignKey(RegistrationWindow, on_delete=models.CASCADE, related_name='student_selections')
    courses = models.ManyToManyField(Course, related_name='selected_by_students')
    
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'window')

    def __str__(self):
        return f"Selection: {self.student.roll_no} for {self.window}"
