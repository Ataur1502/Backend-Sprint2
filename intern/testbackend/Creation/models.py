import uuid
from django.db import models
from django.core.validators import MinValueValidator


# ------------------------------------------
# SCHOOL 
# ------------------------------------------
class School(models.Model):
    # ... (existing fields)
    school_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    school_name = models.CharField(
        max_length=255
    )

    school_code = models.CharField(
        max_length=50,
        unique=True
    )

    school_short_name = models.CharField(
        max_length=50
    )

    def __str__(self):
        return f"{self.school_name} ({self.school_code})"


# ------------------------------------------
# DEGREE 
# ------------------------------------------
class Degree(models.Model):
    degree_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    degree_name = models.CharField(
        max_length=255
    )

    degree_code = models.CharField(
        max_length=50,
        unique=True
    )

    degree_duration = models.PositiveIntegerField(
        help_text="Duration in years"
    )

    number_of_semesters = models.PositiveIntegerField()

    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name="degrees"
    )

    def __str__(self):
        return f"{self.degree_name} ({self.degree_code})"


#Department admin


class Department(models.Model):
    dept_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    degree = models.ForeignKey(
        'Degree',
        on_delete=models.CASCADE,
        related_name='departments'
    )

    dept_code = models.CharField(max_length=20)
    dept_name = models.CharField(max_length=100)

    class Meta:
        unique_together = [
            ('degree', 'dept_code'),
            ('degree', 'dept_name')
        ]

    def __str__(self):
        return f"{self.dept_name} ({self.dept_code})"


# ------------------------------------------
# SEMESTER
# ------------------------------------------
class Semester(models.Model):
    sem_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    degree = models.ForeignKey(
        Degree,
        on_delete=models.CASCADE,
        related_name="semesters"
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="semesters"
    )

    sem_number = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )

    sem_name = models.CharField(max_length=50)
    sem_short_name = models.CharField(max_length=10)  # I-I, I-II
    year = models.PositiveIntegerField()               # Academic year
    annual_exam = models.BooleanField(default=False)

    class Meta:
        unique_together = [
            ('degree', 'department', 'sem_number'),
            ('degree', 'department', 'sem_name')
        ]

    def __str__(self):
        return f"{self.sem_name} ({self.department.dept_code})"
# ------------------------------------------
# REGULATION
# ------------------------------------------
class Regulation(models.Model):
    regulation_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    # Pre-conditions: Degree and Department must exist 
    # For now we'll map to Degree as per 'Degree Mapping' input requirement
    degree = models.ForeignKey(
        Degree,
        on_delete=models.CASCADE,
        related_name="regulations"
    )
    
    # Input: Regulation ID (e.g., MR25)
    regulation_code = models.CharField(
        max_length=50,
        unique=True,
        help_text="e.g. MR25"
    )
    
    # Input: Batch (e.g. 2025-2026)
    batch = models.CharField(
        max_length=50,
        help_text="e.g. 2025-2026"
    )
    
    # Status (Active/Inactive)
    is_active = models.BooleanField(
        default=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Requirements: Validate uniqueness of Regulation ID (code) for redundancy.
        # We also ensure a degree/batch/code combo is unique if needed, 
        # but code itself is already unique.
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.regulation_code} ({self.batch})"
