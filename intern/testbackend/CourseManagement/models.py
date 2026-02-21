import uuid
from django.db import models

''' ---------------------------------------------------------------------------------
    |    Course Management Models are derieved from the Course Configuration Models |
    ---------------------------------------------------------------------------------  '''

# =====================================================
# ACADEMIC CLASS MODELS (Base Classes)
# =====================================================

class AcademicClass(models.Model):
    class_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    school = models.ForeignKey('Creation.School', on_delete=models.CASCADE)
    degree = models.ForeignKey('Creation.Degree', on_delete=models.CASCADE)
    department = models.ForeignKey('Creation.Department', on_delete=models.CASCADE)

    semester = models.ForeignKey('Creation.Semester', on_delete=models.CASCADE)
    regulation = models.ForeignKey('Creation.Regulation', on_delete=models.CASCADE)

    batch = models.CharField(max_length=20)  # e.g. 2025-2026
    academic_year = models.CharField(max_length=20)  # e.g. AY 2025-26

    section = models.ForeignKey('AcademicSetup.Section', on_delete=models.CASCADE)

    strength = models.PositiveIntegerField()

    status = models.CharField(
        max_length=10,
        choices=[('ACTIVE', 'Active'), ('INACTIVE', 'Inactive')],
        default='ACTIVE'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('department', 'semester', 'section', 'academic_year')

    def __str__(self):
        return f"{self.department.name} - {self.section.name} ({self.academic_year})"



class AcademicClassStudent(models.Model):
    mapping_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    academic_class = models.ForeignKey(
        AcademicClass,
        on_delete=models.CASCADE,
        related_name='students'
    )

    student = models.ForeignKey(
        'UserDataManagement.Student',
        on_delete=models.CASCADE
    )

    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('academic_class', 'student')

    def __str__(self):
        return f"{self.student.student_name} -> {self.academic_class}"

# =====================================================
# VIRTUAL SECTION MODELS (CBCS / Elective Groups)
# =====================================================

class VirtualSection(models.Model):
    """
    Logical grouping of students for attendance and faculty view.
    Used for both Core (1:1 with AcademicClass) and Electives (Cross-section grouping).
    Does NOT change the student's physical 'Home Section'.
    """
    virtual_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    name = models.CharField(
        max_length=100,
        help_text="e.g. CSE-A-Java or Elective-Cyber-G1"
    )
    
    course = models.ForeignKey(
        'CourseConfiguration.Course',
        on_delete=models.CASCADE,
        related_name='virtual_sections'
    )
    
    # Context
    school = models.ForeignKey('Creation.School', on_delete=models.CASCADE)
    degree = models.ForeignKey('Creation.Degree', on_delete=models.CASCADE)
    department = models.ForeignKey('Creation.Department', on_delete=models.CASCADE)
    semester = models.ForeignKey('Creation.Semester', on_delete=models.CASCADE)
    regulation = models.ForeignKey('Creation.Regulation', on_delete=models.CASCADE)
    
    academic_year = models.CharField(max_length=20)
    batch = models.CharField(max_length=20)

    # The actual members
    students = models.ManyToManyField(
        'UserDataManagement.Student',
        related_name='virtual_sections'
    )

    status = models.CharField(
        max_length=10,
        choices=[('ACTIVE', 'Active'), ('INACTIVE', 'Inactive')],
        default='ACTIVE'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Virtual Section"
        verbose_name_plural = "Virtual Sections"

    def __str__(self):
        return f"{self.name} ({self.course.course_code})"


# =====================================================
# FACULTY ALLOCATION MODELS
# =====================================================

class FacultyAllocation(models.Model):
    allocation_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    faculty = models.ForeignKey(
        'UserDataManagement.Faculty',
        on_delete=models.CASCADE,
        related_name='faculty_allocations'
    )

    course = models.ForeignKey(
        'CourseConfiguration.Course',
        on_delete=models.CASCADE,
        related_name='course_allocations'
    )

    # Standard roll-number based class (Home Section)
    academic_class = models.ForeignKey(
        'AcademicClass',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='class_allocations'
    )

    # Logical course-based grouping (CBCS / Virtual Group)
    virtual_section = models.ForeignKey(
        'VirtualSection',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='virtual_allocations'
    )

    semester = models.ForeignKey(
        'Creation.Semester',
        on_delete=models.CASCADE
    )

    academic_year = models.CharField(max_length=20)

    status = models.CharField(
        max_length=10,
        choices=[('ACTIVE', 'Active'), ('INACTIVE', 'Inactive')],
        default='ACTIVE'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Note: We now allow allocation to either academic_class OR virtual_section
        unique_together = (
            'faculty',
            'course',
            'academic_class',
            'virtual_section',
            'semester',
            'academic_year'
        )

    def __str__(self):
        return f"{self.faculty} - {self.course}"

# =====================================================
# TIMETABLE MODELS
# =====================================================

class Timetable(models.Model):
    timetable_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    academic_class = models.ForeignKey(
        'AcademicClass',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='timetables'
    )

    virtual_section = models.ForeignKey(
        'VirtualSection',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='virtual_timetables'
    )

    faculty_allocation = models.ForeignKey(
        'FacultyAllocation',
        on_delete=models.CASCADE,
        related_name='timetables'
    )

    day_of_week = models.CharField(
        max_length=10,
        choices=[
            ('MONDAY', 'Monday'),
            ('TUESDAY', 'Tuesday'),
            ('WEDNESDAY', 'Wednesday'),
            ('THURSDAY', 'Thursday'),
            ('FRIDAY', 'Friday'),
            ('SATURDAY', 'Saturday'),
        ]
    )

    start_time = models.TimeField()
    end_time = models.TimeField()

    academic_year = models.CharField(max_length=20)

    status = models.CharField(
        max_length=10,
        choices=[('ACTIVE', 'Active'), ('INACTIVE', 'Inactive')],
        default='ACTIVE'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (
            'academic_class',
            'virtual_section',
            'day_of_week',
            'start_time',
            'academic_year'
        )

    def __str__(self):
        return f"{self.academic_class} - {self.day_of_week} {self.start_time}"
