import uuid
from django.db import models
from django.conf import settings
from Creation.models import School, Department, Degree,Regulation,Semester

'''
----------------------------------------------------------------------------------------------------------------------------
                                    Faculty creation
----------------------------------------------------------------------------------------------------------------------------
'''



import uuid

class Faculty(models.Model):
    GENDER_CHOICES = [
        ('MALE', 'Male'),
        ('FEMALE', 'Female'),
        ('OTHER', 'Other'),
    ]
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='faculty_profile'
    )

    employee_id = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique Employee ID"
    )

    faculty_name = models.CharField(max_length=255)
    faculty_email = models.EmailField(unique=True)
    faculty_mobile_no = models.CharField(max_length=15, blank=True, null=True)
    faculty_date_of_birth = models.DateField(blank=True, null=True)
    faculty_gender = models.CharField(max_length=10, choices=GENDER_CHOICES)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)



class FacultyMapping(models.Model):
    mapping_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    faculty = models.ForeignKey(Faculty, on_delete=models.CASCADE, related_name='mappings')
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        unique_together = ['faculty', 'school', 'department']

    def __str__(self):
        return f"{self.faculty.faculty_name} -> {self.school.school_name}" + (
            f" ({self.department.dept_name})" if self.department else ""
        )



'''
--------------------------------------------------------------------------------------------------------------------------------
                                                Student creation
--------------------------------------------------------------------------------------------------------------------------------
'''



from django.db import models
from Creation.models import Degree, Department, Regulation, Semester


class Student(models.Model):
    # Django will automatically create: id = AutoField(primary_key=True)
    student_id = models.UUIDField(
            primary_key=True,
            default=uuid.uuid4,
            editable=False
        )
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='student_profile',
        null=True,
        blank=True
    )
    roll_no = models.CharField(max_length=30)

    # ===== Student details (matches serializer & Excel) =====
    student_name = models.CharField(max_length=255)
    student_email = models.EmailField()
    student_gender = models.CharField(max_length=10)
    student_date_of_birth = models.DateField()

    student_phone_number = models.CharField(max_length=15)

    # ===== Parent details =====
    parent_name = models.CharField(max_length=255)
    parent_phone_number = models.CharField(max_length=15)

    # ===== Academic details =====
    batch = models.CharField(max_length=20)

    degree = models.ForeignKey(
        Degree, on_delete=models.PROTECT, related_name="students"
    )
    department = models.ForeignKey(
        Department, on_delete=models.PROTECT, related_name="students"
    )
    regulation = models.ForeignKey(
        Regulation, on_delete=models.PROTECT, related_name="students"
    )
    semester = models.ForeignKey(
        Semester, on_delete=models.PROTECT, related_name="students"
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [
            ("department", "roll_no")  # dept-wise isolation
        ]
        ordering = ["roll_no"]

    def __str__(self):
        return f"{self.roll_no} - {self.student_name}"




# ==================================================================================
# DEPARTMENT ADMIN ASSIGNMENT MODEL
# ==================================================================================
# This model manages the assignment of faculty members as Department Admins.
# 
# Purpose:
# - Campus Admins can promote faculty members to Department Admin role
# - Each assignment links a faculty to specific School/Degree/Department
# - Supports multiple departments per faculty (one assignment per department)
#
# Key Features:
# - Cascading hierarchy validation (School -> Degree -> Department)
# - Prevents duplicate assignments (unique constraint on faculty + department)
# - Tracks who assigned and when for audit purposes
# - Active/inactive status for temporary admin privileges
#
# Usage Flow:
# 1. Campus Admin selects School -> filters Degrees -> filters Departments
# 2. Campus Admin searches and selects faculty member(s)
# 3. Assignment triggers MFA verification
# 4. On success, faculty's User role is updated to include DEPARTMENT_ADMIN
# 5. Department Admin can now access department-specific dashboard
# ==================================================================================

class DepartmentAdminAssignment(models.Model):
    """
    Represents the assignment of a faculty member as a Department Administrator.
    
    A Department Admin has elevated privileges to manage their assigned department,
    including viewing students, managing courses, and accessing department analytics.
    """
    
    # Primary identifier for this assignment
    assignment_id = models.UUIDField(
        primary_key=True, 
        default=uuid.uuid4, 
        editable=False,
        help_text="Unique identifier for this department admin assignment"
    )
    
    # The faculty member being assigned as Department Admin
    # This creates a link to the Faculty model
    faculty = models.ForeignKey(
        Faculty, 
        on_delete=models.CASCADE, 
        related_name='dept_admin_assignments',
        help_text="Faculty member assigned as department admin"
    )
    
    # Hierarchy: School -> Degree -> Department
    # These fields enforce the academic structure hierarchy
    # When selecting a department, we validate that it belongs to the selected degree,
    # and that the degree belongs to the selected school
    
    school = models.ForeignKey(
        School, 
        on_delete=models.CASCADE,
        help_text="School to which this department belongs"
    )
    
    degree = models.ForeignKey(
        'Creation.Degree',
        on_delete=models.CASCADE,
        help_text="Degree to which this department belongs (must be under selected school)"
    )
    
    department = models.ForeignKey(
        Department, 
        on_delete=models.CASCADE,
        help_text="Department being managed by this admin (must be under selected degree)"
    )
    
    # Audit trail: who made this assignment and when
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='dept_admin_assignments_made',
        help_text="Campus admin who created this assignment"
    )
    
    assigned_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when this assignment was created"
    )
    
    # Status flag: allows temporary deactivation without deletion
    # Useful for sabbaticals, leaves, or role changes
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this assignment is currently active"
    )

    class Meta:
        # Prevent duplicate assignments: one faculty can only be admin of a department once
        unique_together = ['faculty', 'department']
        ordering = ['-assigned_at']
        verbose_name = "Department Admin Assignment"
        verbose_name_plural = "Department Admin Assignments"

    def __str__(self):
        """String representation showing faculty name and assigned department"""
        return f"{self.faculty.full_name} -> {self.department.dept_name} ({self.school.school_name})"
    
    def save(self, *args, **kwargs):
        """
        Override save to update the faculty's user role when assignment is created.
        
        When a faculty is assigned as Department Admin:
        1. Their associated User record gets the DEPARTMENT_ADMIN role
        2. This grants them access to department-specific features
        """
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # If this is a new assignment and it's active, update the user's role
        if is_new and self.is_active:
            user = self.faculty.user
            # Only update if not already a department admin
            if user.role != 'DEPARTMENT_ADMIN':
                user.role = 'DEPARTMENT_ADMIN'
                user.save()