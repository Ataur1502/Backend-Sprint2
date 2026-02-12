from rest_framework import serializers
from UserDataManagement.models import Student
from CourseConfiguration.models import Course


class DeptAdminStudentSerializer(serializers.ModelSerializer):
    """Lightweight student serializer for coordinator dashboard."""
    
    class Meta:
        model = Student
        fields = [
            'student_id',
            'roll_no',
            'student_name',
            'student_email',
            'batch'
        ]


class DeptAdminAssignCoursesSerializer(serializers.Serializer):
    """Validates course assignment payloads from coordinators."""
    
    student_id = serializers.UUIDField()
    course_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False
    )
