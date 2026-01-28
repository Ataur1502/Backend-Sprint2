from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import transaction
from .models import Faculty, FacultyMapping
from Creation.models import School, Department

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
