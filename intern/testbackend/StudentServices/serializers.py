from rest_framework import serializers
from .models import (
    DocumentRequest, DocumentRequestHistory, 
    CourseRegistrationWindow, CourseRegistration, CourseRegistrationItem,
    Assignment, StudentSubmission, Quiz, Question, Option, 
    StudentQuizAttempt, StudentAnswer, Resource
)
from CourseConfiguration.models import Course

# =====================================================
# COURSE REGISTRATION SERIALIZERS
# =====================================================

class CourseRegistrationWindowSerializer(serializers.ModelSerializer):
    regulation_code = serializers.CharField(source='regulation.regulation_code', read_only=True)
    semester_name = serializers.CharField(source='semester.sem_name', read_only=True)

    class Meta:
        model = CourseRegistrationWindow
        fields = '__all__'


class CourseRegistrationItemSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source='course.course_name', read_only=True)
    course_code = serializers.CharField(source='course.course_code', read_only=True)
    credit_value = serializers.DecimalField(source='course.credit_value', max_digits=5, decimal_places=2, read_only=True)

    class Meta:
        model = CourseRegistrationItem
        fields = [
            'id', 'course', 'course_name', 'course_code', 
            'credit_value', 'is_mandatory'
        ]


class CourseRegistrationSerializer(serializers.ModelSerializer):
    items = CourseRegistrationItemSerializer(many=True, read_only=True)
    semester_name = serializers.CharField(source='semester.sem_name', read_only=True)

    class Meta:
        model = CourseRegistration
        fields = [
            'id', 'student', 'semester', 'semester_name', 
            'academic_year', 'status', 'total_credits', 
            'is_locked', 'submitted_at', 'items', 'created_at'
        ]
        read_only_fields = ['id', 'status', 'total_credits', 'is_locked', 'submitted_at', 'created_at']


# =====================================================
# DOCUMENT REQUEST SERIALIZERS
# =====================================================

class DocumentRequestSerializer(serializers.ModelSerializer):
    latest_remark = serializers.SerializerMethodField()

    class Meta:
        model = DocumentRequest
        fields = [
            'request_id',
            'document_type',
            'purpose',
            'supporting_doc',
            'status',
            'latest_remark',
            'created_at'
        ]
        read_only_fields = ['request_id', 'status', 'created_at']

    def get_latest_remark(self, obj):
        last_history = obj.history.order_by('-updated_at').first()
        return last_history.remark if last_history else None

class DocumentStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[
        ('SUBMITTED', 'Submitted'),
        ('UNDER_REVIEW', 'Under Review'),
        ('ON_HOLD', 'On Hold'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('READY', 'Ready/Issued'),
    ])
    remark = serializers.CharField(required=False, allow_blank=True)

class DocumentRequestHistorySerializer(serializers.ModelSerializer):
    updated_by_email = serializers.EmailField(
        source='updated_by.email',
        read_only=True
    )

    class Meta:
        model = DocumentRequestHistory
        fields = [
            'history_id',
            'status',
            'remark',
            'updated_by_email',
            'updated_at'
        ]


# =====================================================
# ASSIGNMENT SERIALIZERS
# =====================================================

class AssignmentSerializer(serializers.ModelSerializer):
    faculty_name = serializers.CharField(source='faculty.user.first_name', read_only=True)
    class_name = serializers.CharField(source='academic_class.department.dept_name', read_only=True)

    class Meta:
        model = Assignment
        fields = '__all__'


class StudentSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentSubmission
        fields = '__all__'
        read_only_fields = ['student', 'submitted_at', 'marks_obtained', 'feedback']

    def validate(self, data):
        assignment = data.get('assignment')
        from django.utils import timezone
        if timezone.now() > assignment.end_datetime:
            raise serializers.ValidationError("Submission deadline has passed.")
        return data


# =====================================================
# QUIZ SERIALIZERS
# =====================================================

class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ['id', 'option_text']


class QuestionSerializer(serializers.ModelSerializer):
    options = OptionSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = ['id', 'question_text', 'question_type', 'marks', 'order', 'options']


class QuizSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quiz
        fields = '__all__'


class StudentAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentAnswer
        fields = '__all__'


class StudentQuizAttemptSerializer(serializers.ModelSerializer):
    answers = StudentAnswerSerializer(many=True, read_only=True)

    class Meta:
        model = StudentQuizAttempt
        fields = '__all__'
        read_only_fields = ['student', 'started_at', 'calculated_end_time', 'submitted_at', 'total_score', 'is_submitted']


# =====================================================
# RESOURCE SERIALIZERS
# =====================================================

class ResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resource
        fields = '__all__'
