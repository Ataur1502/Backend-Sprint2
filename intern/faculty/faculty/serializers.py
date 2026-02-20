from rest_framework import serializers
from faculty.models import LecturePlan, LectureSession,Attendance, StudentAttendance
from CourseManagement.models import FacultyAllocation

from rest_framework import serializers
import openpyxl
from django.db import transaction


'''
------------------------------------------------------------------------------------------------------------------------------
                                        Lecture Plan Serializers(individual)
------------------------------------------------------------------------------------------------------------------------------
'''

class LecturePlanCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = LecturePlan
        fields = [
            "session",
            "unit_name",
            "topic_name",
            "subtopic_name",
        ]

    def validate(self, data):
        session = data["session"]
        request = self.context["request"]

        if session.allocation.faculty != request.user:
            raise serializers.ValidationError("Not authorized.")

        if session.is_completed:
            raise serializers.ValidationError("Session already completed.")

        return data

    def create(self, validated_data):
        session = validated_data["session"]

        lecture_plan = super().create(validated_data)

        session.is_completed = True
        session.save()

        return lecture_plan



'''
------------------------------------------------------------------------------------------------------------------------------
                                        Lecture Session Serializers
------------------------------------------------------------------------------------------------------------------------------
'''
#Bulk

class LecturePlanBulkUploadSerializer(serializers.ModelSerializer):

    class Meta:
        model = LecturePlan
        fields = [
            "lecture_plan_id",
            "faculty_allocation",
            "uploaded_file",
        ]
        read_only_fields = ["lecture_plan_id"]

    def validate(self, data):
        request = self.context.get("request")
        allocation = data.get("faculty_allocation")

        if allocation.faculty != request.user:
            raise serializers.ValidationError(
                "Not authorized for this allocation."
            )

        if allocation.status != "ACTIVE":
            raise serializers.ValidationError(
                "Allocation is inactive."
            )

        if not data.get("uploaded_file"):
            raise serializers.ValidationError(
                "Excel file is required."
            )

        return data

    @transaction.atomic
    def create(self, validated_data):
        file = validated_data.get("uploaded_file")
        allocation = validated_data.get("faculty_allocation")

        wb = openpyxl.load_workbook(file)
        sheet = wb.active

        lecture_plans_to_create = []
        sessions_to_update = []

        for row_idx, row in enumerate(
            sheet.iter_rows(min_row=2, values_only=True), start=2
        ):

            if not any(row):
                continue

            if len(row) < 5:
                raise serializers.ValidationError(
                    f"Row {row_idx}: Required columns missing."
                )

            session_no, excel_date, unit_name, topic_name, subtopic_name = row[:5]

            if not all([session_no, excel_date, unit_name, topic_name, subtopic_name]):
                raise serializers.ValidationError(
                    f"Row {row_idx}: All fields are required."
                )

            # Fetch stored session
            try:
                session = LectureSession.objects.get(
                    allocation=allocation,
                    session_no=session_no
                )
            except LectureSession.DoesNotExist:
                raise serializers.ValidationError(
                    f"Row {row_idx}: Invalid session number."
                )

            # Convert Excel date properly
            if hasattr(excel_date, "strftime"):
                excel_date_str = excel_date.strftime("%Y-%m-%d")
            else:
                excel_date_str = str(excel_date)

            stored_date_str = session.session_date.strftime("%Y-%m-%d")

            if excel_date_str != stored_date_str:
                raise serializers.ValidationError(
                    f"Row {row_idx}: Date mismatch detected."
                )

            if session.is_completed:
                raise serializers.ValidationError(
                    f"Row {row_idx}: Session already completed."
                )

            lecture_plans_to_create.append(
                LecturePlan(
                    session=session,
                    unit_name=unit_name,
                    topic_name=topic_name,
                    subtopic_name=subtopic_name,
                )
            )

            session.is_completed = True
            sessions_to_update.append(session)

        if not lecture_plans_to_create:
            raise serializers.ValidationError(
                "Excel contains no valid data."
            )

        LecturePlan.objects.bulk_create(lecture_plans_to_create)
        LectureSession.objects.bulk_update(sessions_to_update, ["is_completed"])

        return {"message": "Lecture plan uploaded successfully."}



class LectureSessionSerializer(serializers.ModelSerializer):

    class Meta:
        model = LectureSession
        fields = [
            "session_id",
            "allocation",
            "session_no",
            "session_date",
            "is_completed",
        ]
        read_only_fields = ["session_id"]



'''
------------------------------------------------------------------------------------------------------------------------------
                                        Lecture Plan Detail Serializers
------------------------------------------------------------------------------------------------------------------------------
'''

class LecturePlanDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = LecturePlan
        fields = [
            "lecture_plan_id",
            "session",
            "unit_name",
            "topic_name",
            "subtopic_name",
            "created_at",
        ]



'''
------------------------------------------------------------------------------------------------------------------------------
                                        Attendance create Serializers
------------------------------------------------------------------------------------------------------------------------------
'''

class AttendanceCreateSerializer(serializers.ModelSerializer):

    date = serializers.DateField(write_only=True)

    class Meta:
        model = Attendance
        fields = [
            "attendance_id",
            "faculty_allocation",
            "date",
            "is_submitted",
        ]
        read_only_fields = ["attendance_id", "is_submitted"]

    def validate(self, data):
        request = self.context.get("request")
        allocation = data.get("faculty_allocation")
        date = data.get("date")

        # Ownership check
        if allocation.faculty != request.user:
            raise serializers.ValidationError(
                "Not authorized for this allocation."
            )

        # Find lecture session using date
        try:
            session = LectureSession.objects.get(
                allocation=allocation,
                session_date=date
            )
        except LectureSession.DoesNotExist:
            raise serializers.ValidationError(
                "No lecture session found for selected date."
            )

        # Session must be completed
        if not session.is_completed:
            raise serializers.ValidationError(
                "Lecture not completed for this session."
            )

        # Prevent duplicate attendance
        if Attendance.objects.filter(
            lecture_session=session
        ).exists():
            raise serializers.ValidationError(
                "Attendance already created for this session."
            )

        # Store session internally
        data["lecture_session"] = session

        return data




'''
------------------------------------------------------------------------------------------------------------------------------
                                        Student Attendance Serializers
------------------------------------------------------------------------------------------------------------------------------
'''
class StudentAttendanceSerializer(serializers.ModelSerializer):

    class Meta:
        model = StudentAttendance
        fields = [
            "attendance",
            "student",
            "status",
        ]

    def validate_status(self, value):
        allowed = ["PRESENT", "ABSENT"]
        if value not in allowed:
            raise serializers.ValidationError("Invalid status.")
        return value

    def validate(self, data):
        attendance = data.get("attendance")
        student = data.get("student")

        # Lock after submission
        if attendance.is_submitted:
            raise serializers.ValidationError(
                "Attendance already submitted and locked."
            )

        # Prevent duplicate marking
        if StudentAttendance.objects.filter(
            attendance=attendance,
            student=student
        ).exists():
            raise serializers.ValidationError(
                "Attendance already marked."
            )

        # Ensure student belongs to section
        if student.section != attendance.faculty_allocation.section:
            raise serializers.ValidationError(
                "Student does not belong to this section."
            )

        return data




'''
-------------------------------------------------------------------------------------------------------------------------------
                                            Assignment
-------------------------------------------------------------------------------------------------------------------------------
'''

from rest_framework import serializers
from .models import Assignment
from CourseManagement.models import FacultyAllocation
from django.utils import timezone

class AssignmentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Assignment
        fields = "__all__"
        read_only_fields = ["faculty"]

    def validate(self, data):
        request = self.context["request"]
        faculty = request.user

        academic_class = data.get("academic_class")
        section = data.get("section")
        start = data.get("start_datetime")
        end = data.get("end_datetime")

        # ✅ Validate faculty allocation
        if not FacultyAllocation.objects.filter(
            faculty=faculty,
            academic_class=academic_class,
            section=section
        ).exists():
            raise serializers.ValidationError(
                "You are not allocated to this class and section."
            )

        # ✅ Validate time
        if end <= start:
            raise serializers.ValidationError(
                "End time must be greater than start time."
            )

        if start < timezone.now():
            raise serializers.ValidationError(
                "Start time cannot be in the past."
            )

        return data
#After student submits the assignment
from rest_framework import serializers
from .models import StudentSubmission
from django.utils import timezone

class FacultySubmissionViewSerializer(serializers.ModelSerializer):

    student_name = serializers.CharField(source="student.username", read_only=True)
    status = serializers.SerializerMethodField()

    class Meta:
        model = StudentSubmission
        fields = [
            "id",
            "student_name",
            "file",
            "submitted_at",
            "status",
            "marks_obtained",
            "feedback"
        ]

    def get_status(self, obj):
        if obj.submitted_at <= obj.assignment.end_datetime:
            return "On Time"
        return "Late"


#Student submission serializers(POV: Faculty)
from django.utils import timezone
from rest_framework import serializers
from .models import StudentSubmission

class StudentSubmissionSerializer(serializers.ModelSerializer):

    class Meta:
        model = StudentSubmission
        fields = "__all__"

    def validate(self, data):
        assignment = data.get("assignment")

        # 🚫 Auto Lock Check
        if timezone.now() > assignment.end_datetime:
            raise serializers.ValidationError(
                "Submission closed. Assignment deadline has passed."
            )

        return data

'''
-----------------------------------------------------------------------------------------------------------------------------
                                        Quiz
-----------------------------------------------------------------------------------------------------------------------------
'''
from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta

from .models import (
    Quiz,
    Question,
    Option,
    StudentQuizAttempt,
    StudentAnswer
)
from CourseManagement.models import FacultyAllocation


# =========================================
# QUIZ CREATE SERIALIZER (FACULTY)
# =========================================

class QuizCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Quiz
        fields = "__all__"
        read_only_fields = ["faculty", "is_published", "total_marks"]

    def validate(self, data):
        request = self.context["request"]
        faculty = request.user

        start = data.get("access_start_datetime")
        end = data.get("access_end_datetime")
        quiz_time = data.get("quiz_time")
        academic_class = data.get("academic_class")
        section = data.get("section")

        # Access time validation
        if end <= start:
            raise serializers.ValidationError(
                "Access end time must be greater than start time."
            )

        if quiz_time <= 0:
            raise serializers.ValidationError(
                "Quiz time must be greater than 0."
            )

        # Faculty allocation validation
        if not FacultyAllocation.objects.filter(
            faculty=faculty,
            academic_class=academic_class,
            section=section
        ).exists():
            raise serializers.ValidationError(
                "You are not allocated to this class and section."
            )

        return data


# =========================================
# QUIZ UPDATE SERIALIZER (PUT)
# =========================================

class QuizUpdateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Quiz
        fields = [
            "title",
            "description",
            "access_start_datetime",
            "access_end_datetime",
            "quiz_time",
        ]

    def validate(self, data):

        instance = self.instance

        if instance.is_published:
            raise serializers.ValidationError(
                "Cannot edit a published quiz."
            )

        return data


# =========================================
# OPTION SERIALIZER
# =========================================

class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = "__all__"


# =========================================
# QUESTION SERIALIZER
# =========================================

class QuestionSerializer(serializers.ModelSerializer):
    options = OptionSerializer(many=True, read_only=True)

    class Meta:
        model = Question
        fields = [
            "id",
            "quiz",
            "question_text",
            "question_type",
            "marks",
            "order",
            "options",
        ]

    def validate(self, data):
        marks = data.get("marks")

        if marks <= 0:
            raise serializers.ValidationError(
                "Marks must be greater than 0."
            )

        return data


# =========================================
# QUIZ DETAIL SERIALIZER (FACULTY VIEW)
# =========================================

class QuizDetailSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = [
            "id",
            "title",
            "description",
            "access_start_datetime",
            "access_end_datetime",
            "quiz_time",
            "total_marks",
            "is_published",
            "questions",
        ]


# =========================================
# START QUIZ SERIALIZER (STUDENT)
# =========================================

class StartQuizSerializer(serializers.Serializer):
    message = serializers.CharField()
    calculated_end_time = serializers.DateTimeField()


# =========================================
# STUDENT ANSWER SERIALIZER
# =========================================

class StudentAnswerSerializer(serializers.ModelSerializer):

    class Meta:
        model = StudentAnswer
        fields = "__all__"


# =========================================
# STUDENT QUIZ ATTEMPT SERIALIZER
# =========================================

class StudentQuizAttemptSerializer(serializers.ModelSerializer):
    answers = StudentAnswerSerializer(many=True, read_only=True)

    class Meta:
        model = StudentQuizAttempt
        fields = [
            "id",
            "quiz",
            "student",
            "started_at",
            "calculated_end_time",
            "submitted_at",
            "total_score",
            "is_submitted",
            "answers",
        ]




'''
-----------------------------------------------------------------------------------------------------------------------------
                                                Resources
-----------------------------------------------------------------------------------------------------------------------------
'''
from rest_framework import serializers
from .models import Resource
from CourseManagement.models import FacultyAllocation
import os


ALLOWED_FILE_EXTENSIONS = [
    ".pdf",
    ".ppt",
    ".pptx",
    ".doc",
    ".docx",
    ".jpg",
    ".jpeg",
    ".png",
    ".mp4",
    ".avi",
    ".mov",
]


class ResourceSerializer(serializers.ModelSerializer):

    class Meta:
        model = Resource
        fields = "__all__"
        read_only_fields = ["faculty"]

    def validate(self, data):

        request = self.context["request"]
        faculty = request.user

        academic_class = data.get("academic_class")
        section = data.get("section")
        file = data.get("file")
        link = data.get("link")
        resource_type = data.get("resource_type")

        # Allocation validation
        if not FacultyAllocation.objects.filter(
            faculty=faculty,
            academic_class=academic_class,
            section=section
        ).exists():
            raise serializers.ValidationError(
                "You are not allocated to this class and section."
            )

        # Must provide either file or link
        if not file and not link:
            raise serializers.ValidationError(
                "Provide either a file or a link."
            )

        # If file provided, validate extension
        if file:
            ext = os.path.splitext(file.name)[1].lower()

            if ext not in ALLOWED_FILE_EXTENSIONS:
                raise serializers.ValidationError(
                    "Unsupported file type."
                )

        # If type is LINK, link must exist
        if resource_type == "LINK" and not link:
            raise serializers.ValidationError(
                "Link is required for LINK type."
            )

        return data
