from rest_framework import serializers
from .models import School, Degree, Department, Semester


# ------------------------------------------
# School Serializer
# ------------------------------------------
# ... (existing)
class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = [
            'school_id',
            'school_name',
            'school_code',
            'school_short_name'
        ]
        read_only_fields = ['school_id']


# ------------------------------------------
# Degree Serializer
# ------------------------------------------
# serializers.py
from rest_framework import serializers
from .models import Degree

class DegreeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Degree
        fields = [
            'degree_id',
            'degree_code',
            'degree_name',
            'degree_duration',
            'number_of_semesters',
            'school'
        ]
        read_only_fields = ['degree_id', 'school']


#Dept Admin


from rest_framework import serializers
from .models import Department
from rest_framework import serializers
from .models import Department

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = [
            'dept_id',
            'dept_code',
            'dept_name',
            'degree'
        ]

    def validate(self, data):
        degree = data.get('degree')
        dept_code = data.get('dept_code')
        dept_name = data.get('dept_name')

        queryset = Department.objects.filter(degree=degree)

        if self.instance:
            queryset = queryset.exclude(dept_id=self.instance.dept_id)

        if queryset.filter(dept_code=dept_code).exists():
            raise serializers.ValidationError(
                "Department code already exists under this degree."
            )

        if queryset.filter(dept_name=dept_name).exists():
            raise serializers.ValidationError(
                "Department name already exists under this degree."
            )

        return data

# ------------------------------------------
# SEMESTER SERIALIZER 
# ------------------------------------------
class SemesterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Semester
        fields = [
            'sem_id',
            'sem_number',
            'sem_name',
            'sem_short_name',
            'year',
            'annual_exam',
            'degree',
            'department'
        ]

    def validate(self, data):
        degree = data.get('degree')
        department = data.get('department')
        sem_number = data.get('sem_number')

        # Department must belong to Degree
        if department.degree_id != degree.degree_id:
            raise serializers.ValidationError(
                "Selected department does not belong to the selected degree."
            )

        # Semester number must not exceed degree config
        if sem_number > degree.number_of_semesters:
            raise serializers.ValidationError(
                "Semester number exceeds total semesters for this degree."
            )

        return data
# ------------------------------------------
# REGULATION SERIALIZER
# ------------------------------------------
from .models import Regulation

class RegulationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Regulation
        fields = [
            'regulation_id',
            'regulation_code',
            'batch',
            'degree',
            'is_active',
            'created_at'
        ]
        read_only_fields = ['regulation_id', 'created_at']

    def validate_regulation_code(self, value):
        if Regulation.objects.filter(regulation_code__iexact=value).exists():
            raise serializers.ValidationError("A regulation with this ID already exists.")
        return value
