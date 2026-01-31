import csv
import io
import random
import string
from datetime import datetime
from openpyxl import load_workbook
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import transaction
from .models import Faculty, FacultyMapping, Student,DepartmentAdminAssignment
from Creation.models import School, Department,Degree, Department, Regulation, Semester

User = get_user_model()

'''
---------------------------------------------------------------------------------------------------------------------------------
                                            Faculty creation
---------------------------------------------------------------------------------------------------------------------------------
'''

class FacultyMappingCreateSerializer(serializers.Serializer):
    school_code = serializers.CharField()
    dept_code = serializers.CharField()

class FacultyMappingReadSerializer(serializers.ModelSerializer):
    school_code = serializers.CharField(
        source="school.school_code",
        read_only=True
    )
    department_id = serializers.UUIDField(
        source="department.id",
        read_only=True
    )

    class Meta:
        model = FacultyMapping
        fields = ["school_code", "department_id"]

class FacultySerializer(serializers.ModelSerializer):
    class Meta:
        model = Faculty
        fields = [
            "id",
            "employee_id",
            "faculty_name",
            "faculty_email",
            "faculty_mobile_no",
            "faculty_date_of_birth",
            "faculty_gender",
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_employee_id(self, value):
        instance = self.instance
        qs = Faculty.objects.filter(employee_id=value)
        if instance:
            qs = qs.exclude(pk=instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "A faculty with this employee_id already exists."
            )
        return value

    @transaction.atomic
    def create(self, validated_data):
        mappings_data = validated_data.pop("mappings", [])
        employee_id = validated_data["employee_id"]
        email = validated_data.get("faculty_email")

        # --- USER ---
        user, created = User.objects.get_or_create(
            username=employee_id,
            defaults={"email": email}
        )

        if created:
            user.set_password(employee_id)  # password = employee_id
        user.email = email
        user.save()

        # --- FACULTY ---
        faculty = Faculty.objects.create(
            user=user,
            **validated_data
        )

        # --- MAPPINGS ---
        for mapping in mappings_data:
            school_code = mapping["school_code"]
            dept_code = mapping["dept_code"]

            school = School.objects.filter(
                school_code__iexact=school_code
            ).first()
            if not school:
                raise serializers.ValidationError(
                    {"school_code": f"Invalid school_code '{school_code}'"}
                )

            department = Department.objects.filter(
                dept_code__iexact=dept_code,
                degree__school=school
            ).first()
            if not department:
                raise serializers.ValidationError(
                    {
                        "dept_code": f"Invalid dept_code '{dept_code}' "
                                     f"for school '{school_code}'"
                    }
                )

            FacultyMapping.objects.create(
                faculty=faculty,
                school=school,
                department=department
            )

        return faculty


    


'''
--------------------------------------------------------------------------------------------------------------------------------
                                                Student creation
--------------------------------------------------------------------------------------------------------------------------------
'''


"""
creates Students using .Xlsx file 
"""


User = get_user_model()

class UserRoleSerializer(serializers.ModelSerializer):
    """
    Serializer for the Roles Dashboard list.
    Unified view for all user roles with their associated profiles.
    """
    profile_details = serializers.SerializerMethodField(read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'role_display', 'profile_details']

    def get_profile_details(self, obj):
        # Faculty Profile
        if obj.role == 'FACULTY':
            faculty = getattr(obj, 'faculty_profile', None)
            if faculty:
                return {
                    'name': faculty.faculty_name,
                    'id': faculty.employee_id,
                    'details': f"Faculty ({faculty.faculty_gender})"
                }
        
        # Student Profile
        if obj.role == 'STUDENT':
            student = getattr(obj, 'student_profile', None)
            if student:
                return {
                    'name': student.student_name,
                    'id': student.roll_no,
                    'details': f"Batch: {student.batch}, Dept: {student.department.dept_code if student.department else 'N/A'}",
                    # Academic hierarchy for filtering support in frontend
                    'school_id': str(student.degree.school.id) if student.degree and student.degree.school else None,
                    'degree_id': str(student.degree.id) if student.degree else None,
                    'department_id': str(student.department.id) if student.department else None,
                    'batch_name': student.batch
                }
        
        return {
            'name': obj.get_full_name() or obj.username,
            'id': obj.username,
            'details': 'Administrator'
        }


class StudentExcelUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    @transaction.atomic
    def save(self, **kwargs):
        workbook = load_workbook(self.validated_data["file"])
        sheet = workbook.active

        created = 0
        skipped = []
        errors = []

        for row_no, row in enumerate(
            sheet.iter_rows(min_row=2, values_only=True), start=2
        ):
            try:
                if len(row) < 10:
                    errors.append(
                        {"row": row_no, "error": "Insufficient columns in Excel row"}
                    )
                    continue

                (
                    roll_no,
                    student_name,
                    student_email,
                    student_gender,
                    student_date_of_birth,
                    student_phone_number,
                    parent_name,
                    parent_phone_number,
                    regulation_code,
                    dept_code,
                ) = row[:10]

                if not roll_no:
                    continue

                if Student.objects.filter(roll_no=roll_no).exists():
                    skipped.append(
                        {"row": row_no, "roll_no": roll_no, "error": "Already exists"}
                    )
                    continue

                department = Department.objects.filter(
                    dept_code__iexact=dept_code
                ).first()
                if not department:
                    errors.append(
                        {"row": row_no, "roll_no": roll_no, "error": "Invalid department"}
                    )
                    continue

                regulation = Regulation.objects.filter(
                    regulation_code__iexact=regulation_code
                ).first()
                if not regulation:
                    errors.append(
                        {"row": row_no, "roll_no": roll_no, "error": "Invalid regulation"}
                    )
                    continue

                semester = Semester.objects.filter(
                    degree=department.degree
                ).order_by("sem_number").first()
                if not semester:
                    errors.append(
                        {"row": row_no, "roll_no": roll_no, "error": "Semester not found"}
                    )
                    continue

                # =============================
                # AUTH USER CREATION (THIS NOW RUNS)
                # =============================
                user, created_user = User.objects.get_or_create(
                    username=roll_no,
                    defaults={"email": student_email}
                )

                user.role = "STUDENT"
                user.is_active = True

                if created_user:
                    user.set_password(roll_no)

                user.save()

                # =============================
                # STUDENT CREATION
                # =============================
                Student.objects.create(
                    user=user,
                    roll_no=roll_no,
                    student_name=student_name,
                    student_email=student_email,
                    student_gender=student_gender,
                    student_date_of_birth=student_date_of_birth,
                    student_phone_number=str(student_phone_number),
                    parent_name=parent_name,
                    parent_phone_number=str(parent_phone_number),
                    batch=regulation.batch,
                    degree=department.degree,
                    department=department,
                    regulation=regulation,
                    semester=semester,
                    is_active=True,
                )

                created += 1

            except Exception as e:
                errors.append(
                    {
                        "row": row_no,
                        "roll_no": roll_no if row else None,
                        "error": str(e),
                    }
                )

        return {
            "created": created,
            "skipped": skipped,
            "errors": errors,
        }


class StudentPatchSerializer(serializers.Serializer):
    student_name = serializers.CharField(required=False)
    student_email = serializers.EmailField(required=False)
    student_gender = serializers.CharField(required=False)
    student_date_of_birth = serializers.DateField(required=False)
    student_phone_number = serializers.CharField(required=False)
    parent_name = serializers.CharField(required=False)
    parent_phone_number = serializers.CharField(required=False)
    batch = serializers.CharField(required=False)

    def update(self, instance, validated_data):
        field_mapping = {
            "student_name": "name",
            "student_email": "email",
            "student_gender": "gender",
            "student_date_of_birth": "dob",
            "student_phone_number": "student_mobile",
            "parent_phone_number": "parent_mobile",
        }

        for field, value in validated_data.items():
            model_field = field_mapping.get(field, field)
            setattr(instance, model_field, value)

        instance.save()
        return instance



# ==================================================================================
# DEPARTMENT ADMIN ASSIGNMENT SERIALIZER
# ==================================================================================
# This serializer handles the assignment of faculty members as Department Admins.
#
# Key Responsibilities:
# 1. Validate cascading hierarchy (School -> Degree -> Department)
# 2. Ensure selected department actually belongs to selected degree
# 3. Ensure selected degree actually belongs to selected school
# 4. Prevent duplicate assignments (handled by model unique_together)
# 5. Automatically set assigned_by to the requesting user
#
# Cascading Validation Flow:
# - Frontend sends: school_id, degree_id, department_id, faculty_id
# - Backend validates:
#   a) Does the degree belong to the selected school?
#   b) Does the department belong to the selected degree?
# - If valid, create assignment
# - Model's save() method automatically updates faculty user's role
# ==================================================================================

class DepartmentAdminAssignmentSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and managing Department Admin assignments.
    
    Enforces the academic hierarchy: School -> Degree -> Department
    """
    
    # Use PrimaryKeyRelatedField for cleaner input/output
    # Frontend sends UUIDs, backend validates they exist
    faculty_id = serializers.PrimaryKeyRelatedField(
        queryset=Faculty.objects.filter(is_active=True),
        source='faculty',
        help_text="Faculty member to assign (must be active)"
    )
    
    school_id = serializers.PrimaryKeyRelatedField(
        queryset=School.objects.all(),
        source='school',
        help_text="School in the hierarchy"
    )
    
    degree_id = serializers.PrimaryKeyRelatedField(
        queryset=Degree.objects.all(),  # Will be filtered in validation
        source='degree',
        help_text="Degree under the selected school"
    )
    
    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(),
        source='department',
        help_text="Department under the selected degree"
    )
    
    # Read-only fields for output
    assigned_by_email = serializers.EmailField(
        source='assigned_by.email',
        read_only=True,
        help_text="Email of admin who made this assignment"
    )
    
    faculty_name = serializers.CharField(
        source='faculty.full_name',
        read_only=True,
        help_text="Full name of assigned faculty"
    )

    class Meta:
        model = DepartmentAdminAssignment
        fields = [
            'assignment_id', 'faculty_id', 'faculty_name', 'school_id', 
            'degree_id', 'department_id', 'assigned_by', 'assigned_by_email',
            'assigned_at', 'is_active'
        ]
        read_only_fields = ['assignment_id', 'assigned_by', 'assigned_at']

    def validate(self, data):
        """
        Validate the cascading hierarchy: School -> Degree -> Department
        
        This ensures:
        1. The selected degree belongs to the selected school
        2. The selected department belongs to the selected degree
        
        If either validation fails, raise a clear error message.
        """
        school = data.get('school')
        degree = data.get('degree')
        department = data.get('department')
        
        # Validation 1: Does the degree belong to the selected school?
        if degree and school:
            if degree.school != school:
                raise serializers.ValidationError({
                    'degree_id': f"Selected degree '{degree.degree_name}' does not belong to school '{school.school_name}'"
                })
        
        # Validation 2: Does the department belong to the selected degree?
        if department and degree:
            if department.degree != degree:
                raise serializers.ValidationError({
                    'department_id': f"Selected department '{department.dept_name}' does not belong to degree '{degree.degree_name}'"
                })
        
        return data

    @transaction.atomic
    def create(self, validated_data):
        """
        Create a new Department Admin assignment.
        
        The model's save() method will automatically update the faculty's
        user role to DEPARTMENT_ADMIN.
        """
        # The assigned_by field should be set by the view from request.user
        # If not already set, we'll handle it in the view
        return DepartmentAdminAssignment.objects.create(**validated_data)