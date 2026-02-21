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


# =====================================================
# ACADEMIC CLASS SERIALIZERS
# =====================================================

from rest_framework import serializers
from .models import AcademicClass


class AcademicClassCreateSerializer(serializers.Serializer):
    school_id = serializers.UUIDField()
    degree_id = serializers.UUIDField()
    department_id = serializers.UUIDField()
    semester_id = serializers.UUIDField()
    regulation_id = serializers.UUIDField()

    batch = serializers.CharField(max_length=20)
    academic_year = serializers.CharField(max_length=20)

    strength = serializers.IntegerField(min_value=1)

    def validate(self, data):
        """
        Prevent duplicate class creation for same
        Department + Semester + Academic Year
        """

        department_id = data.get("department_id")
        semester_id = data.get("semester_id")
        academic_year = data.get("academic_year")

        existing = AcademicClass.objects.filter(
            department_id=department_id,
            semester_id=semester_id,
            academic_year=academic_year
        )

        if existing.exists():
            raise serializers.ValidationError(
                "Classes already created for this Department + Semester + Academic Year."
            )

        return data

class AcademicClassViewSerializer(serializers.ModelSerializer):
    section_name = serializers.CharField(source="section.name", read_only=True)
    department_name = serializers.CharField(source="department.dept_name", read_only=True)
    degree_name = serializers.CharField(source="degree.degree_name", read_only=True)

    class Meta:
        model = AcademicClass
        fields = [
            'class_id',
            'school',
            'degree',
            'degree_name',
            'department',
            'department_name',
            'semester',
            'regulation',
            'batch',
            'academic_year',
            'section',
            'section_name',
            'strength',
            'status'
        ]

from rest_framework import serializers
from .models import FacultyAllocation, VirtualSection
from CourseConfiguration.models import Course
from UserDataManagement.models import Faculty
from .models import AcademicClass


class VirtualSectionSerializer(serializers.ModelSerializer):
    course_name = serializers.CharField(source="course.course_name", read_only=True)
    course_code = serializers.CharField(source="course.course_code", read_only=True)
    student_count = serializers.IntegerField(source="students.count", read_only=True)

    class Meta:
        model = VirtualSection
        fields = [
            'virtual_id',
            'name',
            'course',
            'course_name',
            'course_code',
            'school',
            'degree',
            'department',
            'semester',
            'regulation',
            'batch',
            'academic_year',
            'student_count',
            'status'
        ]


class FacultyAllocationCreateSerializer(serializers.Serializer):
    faculty_id = serializers.UUIDField()
    course_id = serializers.UUIDField()

    academic_class_id = serializers.UUIDField(required=False, allow_null=True)
    virtual_section_id = serializers.UUIDField(required=False, allow_null=True)

    semester_id = serializers.UUIDField()
    academic_year = serializers.CharField(max_length=20)

    def validate(self, data):
        faculty_id = data.get("faculty_id")
        course_id = data.get("course_id")
        academic_class_id = data.get("academic_class_id")
        virtual_section_id = data.get("virtual_section_id")
        semester_id = data.get("semester_id")
        academic_year = data.get("academic_year")

        # 🔒 Must provide either academic_class OR virtual_section
        if not academic_class_id and not virtual_section_id:
            raise serializers.ValidationError(
                "Either academic class or virtual section must be provided."
            )

        # 🔎 Validate faculty exists
        if not Faculty.objects.filter(pk=faculty_id, is_active=True).exists():
            raise serializers.ValidationError(
                "Invalid or inactive faculty."
            )

        # 🔎 Validate course exists
        if not Course.objects.filter(pk=course_id, is_active=True).exists():
            raise serializers.ValidationError(
                "Invalid or inactive course."
            )

        # 🔎 Validate academic class if provided
        if academic_class_id:
            try:
                academic_class = AcademicClass.objects.get(pk=academic_class_id)
                if str(academic_class.semester_id) != str(semester_id):
                    raise serializers.ValidationError(
                        "Course semester mismatch with academic class."
                    )
            except AcademicClass.DoesNotExist:
                raise serializers.ValidationError(
                    "Academic class not found."
                )

        # 🔎 Validate virtual section if provided
        if virtual_section_id:
            try:
                virtual_section = VirtualSection.objects.get(pk=virtual_section_id)
                if str(virtual_section.semester_id) != str(semester_id):
                    raise serializers.ValidationError(
                        "Course semester mismatch with virtual section."
                    )
            except VirtualSection.DoesNotExist:
                raise serializers.ValidationError(
                    "Virtual section not found."
                )

        # 🔎 Prevent duplicate allocation
        if FacultyAllocation.objects.filter(
            faculty_id=faculty_id,
            course_id=course_id,
            academic_class_id=academic_class_id,
            virtual_section_id=virtual_section_id,
            semester_id=semester_id,
            academic_year=academic_year
        ).exists():
            raise serializers.ValidationError(
                "Faculty already allocated for this course and class/section."
            )

        return data

# =====================================================
# FACULTY ALLOCATION VIEW SERIALIZER
# =====================================================

class FacultyAllocationViewSerializer(serializers.ModelSerializer):

    faculty_name = serializers.CharField(source="faculty.faculty_name", read_only=True)
    course_name = serializers.CharField(source="course.course_name", read_only=True)
    class_section = serializers.CharField(source="academic_class.section.name", read_only=True)
    virtual_section_name = serializers.CharField(source="virtual_section.name", read_only=True)

    class Meta:
        model = FacultyAllocation
        fields = [
            "allocation_id",
            "faculty_id",
            "faculty_name",
            "course_id",
            "course_name",
            "academic_class",
            "class_section",
            "virtual_section",
            "virtual_section_name",
            "semester",
            "academic_year",
            "status"
        ]


# =====================================================
# TIMETABLE CREATE SERIALIZER
# =====================================================

from .models import Timetable, FacultyAllocation


class TimetableCreateSerializer(serializers.Serializer):

    academic_class_id = serializers.UUIDField()
    faculty_allocation_id = serializers.UUIDField()

    day_of_week = serializers.ChoiceField(choices=[
        'MONDAY', 'TUESDAY', 'WEDNESDAY',
        'THURSDAY', 'FRIDAY', 'SATURDAY'
    ])

    start_time = serializers.TimeField()
    end_time = serializers.TimeField()

    academic_year = serializers.CharField(max_length=20)

    def validate(self, data):

        academic_class_id = data.get("academic_class_id")
        faculty_allocation_id = data.get("faculty_allocation_id")
        day_of_week = data.get("day_of_week")
        start_time = data.get("start_time")
        end_time = data.get("end_time")
        academic_year = data.get("academic_year")

        # 1️⃣ Validate Faculty Allocation exists
        try:
            allocation = FacultyAllocation.objects.get(
                pk=faculty_allocation_id,
                status="ACTIVE"
            )
        except FacultyAllocation.DoesNotExist:
            raise serializers.ValidationError(
                "Invalid or inactive faculty allocation."
            )

        # 2️⃣ Ensure allocation belongs to this academic class
        if str(allocation.academic_class_id) != str(academic_class_id):
            raise serializers.ValidationError(
                "Faculty allocation does not belong to this class."
            )

        # 3️⃣ Prevent Class Slot Overlap
        if Timetable.objects.filter(
            academic_class_id=academic_class_id,
            day_of_week=day_of_week,
            start_time=start_time,
            academic_year=academic_year,
            status="ACTIVE"
        ).exists():
            raise serializers.ValidationError(
                "This class already has a subject at this time."
            )

        # 4️⃣ Prevent Faculty Double Booking
        if Timetable.objects.filter(
            faculty_allocation__faculty=allocation.faculty,
            day_of_week=day_of_week,
            start_time=start_time,
            academic_year=academic_year,
            status="ACTIVE"
        ).exists():
            raise serializers.ValidationError(
                "Faculty already assigned to another class at this time."
            )

        # 5️⃣ Basic time validation
        if start_time >= end_time:
            raise serializers.ValidationError(
                "End time must be after start time."
            )

        return data

# =====================================================
# TIMETABLE VIEW SERIALIZER
# =====================================================

class TimetableViewSerializer(serializers.ModelSerializer):

    course_name = serializers.CharField(
        source="faculty_allocation.course.course_name",
        read_only=True
    )

    faculty_name = serializers.CharField(
        source="faculty_allocation.faculty.faculty_name",
        read_only=True
    )

    section_name = serializers.CharField(
        source="academic_class.section.name",
        read_only=True
    )

    class Meta:
        model = Timetable
        fields = [
            "timetable_id",
            "academic_class",
            "section_name",
            "day_of_week",
            "start_time",
            "end_time",
            "course_name",
            "faculty_name",
            "academic_year",
            "status"
        ]
