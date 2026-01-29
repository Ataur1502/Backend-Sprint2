from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import transaction
from .models import Faculty, FacultyMapping, DepartmentAdminAssignment
from Creation.models import School, Department, Degree

User = get_user_model()

class FacultyMappingSerializer(serializers.ModelSerializer):
    school_id = serializers.PrimaryKeyRelatedField(
        queryset=School.objects.all(), source='school'
    )
    department_id = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(), source='department', 
        required=False, allow_null=True
    )

    class Meta:
        model = FacultyMapping
        fields = ['school_id', 'department_id']

class FacultySerializer(serializers.ModelSerializer):
    mappings = FacultyMappingSerializer(many=True)

    class Meta:
        model = Faculty
        fields = [
            'faculty_id', 'employee_id', 'full_name', 'email', 'mobile_no', 
            'dob', 'gender', 'mappings', 'is_active', 'created_at'
        ]
        read_only_fields = ['faculty_id', 'created_at']

    def validate_employee_id(self, value):
        instance = self.instance
        if Faculty.objects.filter(employee_id=value).exclude(pk=getattr(instance, 'pk', None)).exists():
            raise serializers.ValidationError("A faculty with this Employee ID already exists.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        mappings_data = validated_data.pop('mappings', [])
        employee_id = validated_data.get('employee_id')
        email = validated_data.get('email')

        # Create or Get User (Username & Password = Employee ID)
        user, created = User.objects.get_or_create(
            username=employee_id,
            defaults={
                'email': email,
                'role': 'FACULTY'
            }
        )
        if created:
            user.set_password(employee_id)
            user.save()
        else:
            # If user already exists, update email and role just in case
            user.email = email
            user.role = 'FACULTY'
            user.save()

        faculty = Faculty.objects.create(user=user, **validated_data)

        for mapping in mappings_data:
            FacultyMapping.objects.create(faculty=faculty, **mapping)

        return faculty

    @transaction.atomic
    def update(self, instance, validated_data):
        mappings_data = validated_data.pop('mappings', None)
        employee_id = validated_data.get('employee_id', instance.employee_id)
        email = validated_data.get('email', instance.email)

        # Update associated User
        user = instance.user
        user.username = employee_id
        user.email = email
        user.set_password(employee_id)
        user.save()

        # Update Faculty
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update Mappings if provided
        if mappings_data is not None:
            instance.mappings.all().delete()
            for mapping in mappings_data:
                FacultyMapping.objects.create(faculty=instance, **mapping)

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
