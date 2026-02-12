from rest_framework import serializers
from .models import School, Degree, Department, Semester,Regulation


# ------------------------------------------
# School Serializer
# ------------------------------------------

class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = [
            'school_id',
            'school_name',
            'school_code',
            
        ]
        read_only_fields = ['school_id']


# ------------------------------------------
# Degree Serializer
# ------------------------------------------



class DegreeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Degree
        fields = [
            'degree_id',
            'degree_code',
            'degree_name',
            'degree_duration',
            'number_of_semesters',
            'is_active',
            'school'
        ]
        read_only_fields = [
    'degree_id',
    'school',
    'number_of_semesters',
]

    def create(self, validated_data):
        years = validated_data['degree_duration']
        validated_data['number_of_semesters'] = years * 2
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'degree_duration' in validated_data:
            years = validated_data['degree_duration']
            instance.number_of_semesters = years * 2

        instance.degree_name = validated_data.get(
            'degree_name', instance.degree_name
        )
        instance.degree_code = validated_data.get(
            'degree_code', instance.degree_code
        )
        instance.degree_duration = validated_data.get(
            'degree_duration', instance.degree_duration
        )

        instance.save()
        return instance



#Dept Creation


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = [
            'dept_id',
            'dept_code',
            'dept_name',
            'degree',
            'is_active'
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
    department_codes = serializers.SerializerMethodField()

    class Meta:
        model = Semester
        fields = [
            'sem_id',
            'sem_number',
            'sem_name',
            'year',
            'degree',
            'department_codes',
        ]
        read_only_fields = fields

    def get_department_codes(self, obj):
        return list(
            obj.degree.departments.values_list('dept_code', flat=True)
        )


# ------------------------------------------
# REGULATION SERIALIZER
# ------------------------------------------





class RegulationSerializer(serializers.ModelSerializer):
    start_year = serializers.IntegerField(write_only=True)
    end_year = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Regulation
        fields = [
            'regulation_id',
            'regulation_code',
            'start_year',
            'end_year',
            'batch',
            'degree',
            'created_at'
        ]
        read_only_fields = [
            'regulation_id',
            'batch',
            'created_at'
        ]

    def create(self, validated_data):
        start_year = validated_data.pop('start_year')
        degree = validated_data['degree']

        end_year = start_year + degree.degree_duration
        validated_data['batch'] = f"{start_year}-{end_year}"

        return super().create(validated_data)

    def get_end_year(self, obj):
        return int(obj.batch.split('-')[1])
