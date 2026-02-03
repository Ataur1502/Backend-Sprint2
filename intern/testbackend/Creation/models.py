import uuid
from django.db import models

# ------------------------------------------
# SCHOOL 
# ------------------------------------------
class School(models.Model):
    school_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    school_name = models.CharField(max_length=255)
    school_code = models.CharField(max_length=50, unique=True)
    
    # Existing fields in DB
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
    degree_name = models.CharField(max_length=255)
    degree_code = models.CharField(max_length=50, unique=True)
    degree_duration = models.PositiveIntegerField(help_text="Duration in years")
    number_of_semesters = models.PositiveIntegerField()
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name="degrees"
    )

    # Existing fields in DB
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.degree_name} ({self.degree_code})"


# ------------------------------------------
# Department creation
# ------------------------------------------
class Department(models.Model):
    dept_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    degree = models.ForeignKey(
        Degree,
        on_delete=models.CASCADE,
        related_name='departments'
    )
    dept_code = models.CharField(max_length=20)
    dept_name = models.CharField(max_length=100)

    # Existing fields in DB
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
    sem_number = models.PositiveIntegerField()
    sem_name = models.CharField(max_length=50)
    degree = models.ForeignKey(
        Degree,
        on_delete=models.CASCADE,
        related_name="semesters"
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="semesters"
    )
    year = models.PositiveIntegerField()
  
    # Existing fields in DB
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('degree', 'sem_number')
        ordering = ['sem_number']

    def __str__(self):
        return f"{self.degree.degree_name} - Semester {self.sem_number}"


# ------------------------------------------
# REGULATION
# ------------------------------------------
class Regulation(models.Model):
    regulation_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    degree = models.ForeignKey(
        Degree,
        on_delete=models.CASCADE,
        related_name="regulations"
    )
    regulation_code = models.CharField(max_length=50, help_text="e.g. R20")
    batch = models.CharField(max_length=20, help_text="e.g. 2020-2024")

    # fields in DB (Regulation does NOT have updated_at according to PRAGMA)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [
            ('degree', 'regulation_code', 'batch')
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.regulation_code} ({self.batch})"
