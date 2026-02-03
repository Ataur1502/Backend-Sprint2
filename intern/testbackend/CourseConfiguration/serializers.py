from rest_framework import serializers
from .models import Course
from Creation.models import School, Degree, Department, Regulation

class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = '__all__'
        read_only_fields = ['course_id']

    def validate(self, data):
        # 1. Check if Regulation is active
        regulation = data.get('regulation')
        if regulation and not regulation.is_active:
            raise serializers.ValidationError({"regulation": "Selected regulation is not active."})

        # 2. Check for Duplicate Course Code (though model unique=True handles it, we can be explicit)
        course_code = data.get('course_code')
        if not self.instance and Course.objects.filter(course_code=course_code).exists():
            raise serializers.ValidationError({"course_code": "Duplicate Course Code detected."})

        return data

from .models import RegistrationWindow, StudentSelection

class RegistrationWindowSerializer(serializers.ModelSerializer):
    school_name = serializers.ReadOnlyField(source='school.school_name')
    dept_name = serializers.ReadOnlyField(source='department.dept_name')
    sem_name = serializers.ReadOnlyField(source='semester.sem_name')
    regulation_code = serializers.ReadOnlyField(source='regulation.regulation_code')
    
    class Meta:
        model = RegistrationWindow
        fields = '__all__'
        read_only_fields = ['window_id', 'created_at', 'updated_at']

class StudentSelectionSerializer(serializers.ModelSerializer):
    student_name = serializers.ReadOnlyField(source='student.student_name')
    roll_no = serializers.ReadOnlyField(source='student.roll_no')
    
    class Meta:
        model = StudentSelection
        fields = '__all__'
        read_only_fields = ['selection_id', 'submitted_at']
