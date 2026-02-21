from django.shortcuts import render
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from faculty.models import LecturePlan, LectureSession, Attendance, StudentAttendance, Assignment, Quiz
from .serializers import (
    LecturePlanCreateSerializer,
    LecturePlanDetailSerializer,
    LectureSessionSerializer,
    AttendanceCreateSerializer,
    StudentAttendanceSerializer,

    LecturePlanBulkUploadSerializer
)
from Creation.permissions import IsFaculty, IsActiveFaculty
from CourseManagement.models import FacultyAllocation
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from io import BytesIO
from django.http import HttpResponse
import openpyxl

from datetime import timedelta
from AcademicSetup.models import AcademicCalendar, CalendarEvent
from CourseManagement.models import Timetable


def generate_sessions(allocation):

    academic_class = allocation.academic_class
    course = allocation.course
    section = allocation.section

    # 🔹 Get active calendar for this semester
    try:
        calendar = AcademicCalendar.objects.get(
            semester=academic_class.semester,
            is_active=True
        )
    except AcademicCalendar.DoesNotExist:
        raise Exception("Active Academic Calendar not found for this semester")

    # 🔹 Semester start = first INSTRUCTION event
    instruction_event = CalendarEvent.objects.filter(
        calendar=calendar,
        type="INSTRUCTION"
    ).order_by("start_date").first()

    if not instruction_event:
        raise Exception("INSTRUCTION event not found in calendar")

    start_date = instruction_event.start_date

    # 🔹 Semester end = first EXAM event
    exam_event = CalendarEvent.objects.filter(
        calendar=calendar,
        type="EXAM"
    ).order_by("start_date").first()

    if not exam_event:
        raise Exception("EXAM event not found in calendar")

    end_date = exam_event.end_date

    # 🔹 Blocked dates (HOLIDAY, EXAM, OTHER)
    blocked_events = CalendarEvent.objects.filter(
        calendar=calendar,
        type__in=["HOLIDAY", "EXAM", "OTHER"]
    )

    blocked_dates = set()

    for event in blocked_events:
        current = event.start_date
        while current <= event.end_date:
            blocked_dates.add(current)
            current += timedelta(days=1)

    # 🔹 Get timetable working days
    timetable_days = Timetable.objects.filter(
    faculty_allocation=allocation
).values_list("day_of_week", flat=True)


    # 🔹 Generate sessions
    current = start_date
    session_no = 1

    while current <= end_date:

        if (
            current.strftime("%A").upper() in timetable_days
            and current not in blocked_dates
        ):
            LectureSession.objects.create(
                allocation=allocation,
                session_no=session_no,
                session_date=current
            )
            session_no += 1

        current += timedelta(days=1)
        print("Timetable Days:", timetable_days)
        print("Start:", start_date)
        print("End:", end_date)


from rest_framework.exceptions import PermissionDenied

def get_faculty_profile(user):
    try:
        return user.faculty_profile
    except:
        raise PermissionDenied("Faculty profile not found")

'''
------------------------------------------------------------------------------------------------------------------------------
                                        Lecture plan views
------------------------------------------------------------------------------------------------------------------------------
'''


class LecturePlanViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsFaculty, IsActiveFaculty]
    lookup_field = "lecture_plan_id"
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        faculty = get_faculty_profile(self.request.user)
        return LecturePlan.objects.filter(
            session__allocation__faculty=faculty
        )

    def get_serializer_class(self):
        if self.action == "bulk_upload":
            return LecturePlanBulkUploadSerializer
        if self.action == "create":
            return LecturePlanCreateSerializer
        return LecturePlanDetailSerializer

    @action(detail=False, methods=["post"], url_path="bulk-upload")
    def bulk_upload(self, request):
        serializer = self.get_serializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"message": "Lecture plan uploaded successfully."},
            status=status.HTTP_201_CREATED
        )


#Bulk upload template
class LecturePlanTemplateView(APIView):
    permission_classes = [IsAuthenticated, IsFaculty, IsActiveFaculty]

    def get(self, request):
        subject_id = request.query_params.get("subject_id")

        if not subject_id:
            return Response({"error": "subject_id is required"}, status=400)

        try:
            faculty = request.user.faculty_profile

            allocation = FacultyAllocation.objects.get(
                faculty=request.user.faculty_profile,
                course_id=subject_id

            )
        except FacultyAllocation.DoesNotExist:
            return Response({"error": "Invalid subject"}, status=400)

        # 🔥 Auto generate sessions if not exist
        if not LectureSession.objects.filter(allocation=allocation).exists():
            generate_sessions(allocation)

        sessions = LectureSession.objects.filter(
            allocation=allocation
        ).order_by("session_no")

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Lecture Plan"

        # Final Headers
        headers = [
            "Session No",
            "Date",
            "Unit Name",
            "Topic Name",
            "Sub Topic Name"
        ]
        ws.append(headers)

        for session in sessions:
            ws.append([
                session.session_no,
                session.session_date.strftime("%Y-%m-%d"),
                "",
                "",
                ""
            ])

        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        response = HttpResponse(
            buffer.read(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        response["Content-Disposition"] = "attachment; filename=Lecture_Plan.xlsx"

        return response


'''
------------------------------------------------------------------------------------------------------------------------------
                                        Lecture plan seesion views
------------------------------------------------------------------------------------------------------------------------------
'''

class LectureSessionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsFaculty, IsActiveFaculty]
    lookup_field = "session_id"
    serializer_class = LectureSessionSerializer

    def get_queryset(self):
        faculty = get_faculty_profile(self.request.user)
        return LectureSession.objects.filter(
            allocation__faculty=faculty
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_completed:
            return Response({"error": "Completed session cannot be modified."}, status=400)
        return super().update(request, *args, **kwargs)

#Report

class LecturePlanProgressAPIView(APIView):
    permission_classes = [IsAuthenticated, IsFaculty, IsActiveFaculty]

    def get(self, request):
        subject_id = request.query_params.get("subject_id")

        if not subject_id:
            return Response({"error": "subject_id is required"}, status=400)

        faculty = get_faculty_profile(request.user)

        try:
            allocation = FacultyAllocation.objects.get(
                faculty=faculty,
                course_id=subject_id
            )
        except FacultyAllocation.DoesNotExist:
            return Response({"error": "Invalid subject"}, status=400)

        total = LectureSession.objects.filter(allocation=allocation).count()
        completed = LectureSession.objects.filter(
            allocation=allocation,
            is_completed=True
        ).count()

        percentage = (completed / total * 100) if total > 0 else 0

        return Response({
            "total_sessions": total,
            "completed_sessions": completed,
            "completion_percentage": round(percentage, 2)
        })




#Generates the lecture plan
class GenerateLectureSessionsAPIView(APIView):
    permission_classes = [IsAuthenticated, IsFaculty, IsActiveFaculty]

    def post(self, request):
        course_id = request.data.get("course_id")
        section_id = request.data.get("section_id")

        if not course_id:
            return Response(
                {"error": "course_id is required"},
                status=400
            )

        if not section_id:
            return Response(
                {"error": "section_id is required"},
                status=400
            )

        faculty = get_faculty_profile(request.user)

        try:
            allocation = FacultyAllocation.objects.get(
                faculty=faculty,
                course_id=course_id,
                section_id=section_id,
                status="ACTIVE"
            )
        except FacultyAllocation.DoesNotExist:
            return Response(
                {"error": "Invalid subject or section"},
                status=400
            )

        except FacultyAllocation.MultipleObjectsReturned:
            return Response(
                {"error": "Multiple allocations found. Contact admin."},
                status=400
            )

        if LectureSession.objects.filter(allocation=allocation).exists():
            return Response(
                {"message": "Sessions already generated."}
            )

        generate_sessions(allocation)

        return Response(
            {"message": "Lecture sessions generated successfully."},
            status=201
        )


#Lecture plan progress
class LecturePlanReportAPIView(APIView):
    permission_classes = [IsAuthenticated, IsFaculty, IsActiveFaculty]

    def get(self, request):
        subject_id = request.query_params.get("subject_id")
        section_id = request.query_params.get("section_id")

        if not subject_id:
            return Response(
                {"error": "subject_id is required"},
                status=400
            )

        if not section_id:
            return Response(
                {"error": "section_id is required"},
                status=400
            )

        try:
            faculty = request.user.faculty_profile

            allocation = FacultyAllocation.objects.get(
                faculty=faculty,
                course_id=subject_id,
                section_id=section_id,
                status="ACTIVE"
            )

        except FacultyAllocation.DoesNotExist:
            return Response(
                {"error": "Invalid subject or section"},
                status=400
            )

        except FacultyAllocation.MultipleObjectsReturned:
            return Response(
                {"error": "Multiple allocations found. Contact admin."},
                status=400
            )

        total_sessions = LectureSession.objects.filter(
            allocation=allocation
        ).count()

        completed_sessions = LectureSession.objects.filter(
            allocation=allocation,
            is_completed=True
        ).count()

        percentage = (
            (completed_sessions / total_sessions) * 100
            if total_sessions > 0 else 0
        )

        return Response({
            "total_sessions": total_sessions,
            "completed_sessions": completed_sessions,
            "completion_percentage": round(percentage, 2)
        })




'''
------------------------------------------------------------------------------------------------------------------------------
                                        Attendance views
------------------------------------------------------------------------------------------------------------------------------
'''
from django.utils import timezone
from datetime import timedelta
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from .models import Attendance, StudentAttendance
from .serializers import AttendanceCreateSerializer, StudentAttendanceSerializer
from Creation.permissions import IsFaculty, IsActiveFaculty, IsAcademicCoordinator
from CourseManagement.models import FacultyAllocation


class AttendanceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsFaculty, IsActiveFaculty]
    lookup_field = "attendance_id"
    serializer_class = AttendanceCreateSerializer

    def get_queryset(self):
        faculty = get_faculty_profile(self.request.user)
        return Attendance.objects.filter(
            faculty_allocation__faculty=faculty
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.is_submitted:
            return Response(
                {"error": "Attendance already submitted and locked."},
                status=400
            )

        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.is_submitted:
            return Response(
                {"error": "Submitted attendance cannot be deleted."},
                status=400
            )

        return super().destroy(request, *args, **kwargs)


class StudentAttendanceViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsFaculty, IsActiveFaculty]
    serializer_class = StudentAttendanceSerializer

    def get_queryset(self):
        return StudentAttendance.objects.filter(
            attendance__faculty_allocation__faculty=self.request.user
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.attendance.is_submitted:
            now = timezone.now()

            # Allow override if within coordinator window
            if instance.attendance.override_until and now <= instance.attendance.override_until:
                return super().update(request, *args, **kwargs)

            return Response(
                {"error": "Attendance is locked."},
                status=400
            )

        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.attendance.is_submitted:
            return Response(
                {"error": "Attendance is locked."},
                status=400
            )

        return super().destroy(request, *args, **kwargs)


class SubmitAttendanceAPIView(APIView):
    permission_classes = [IsAuthenticated, IsFaculty, IsActiveFaculty]

    def post(self, request):
        attendance_id = request.data.get("attendance_id")

        if not attendance_id:
            return Response({"error": "attendance_id required"}, status=400)

        faculty = get_faculty_profile(request.user)

        try:
            attendance = Attendance.objects.get(
                attendance_id=attendance_id,
                faculty_allocation__faculty=faculty
            )
        except Attendance.DoesNotExist:
            return Response({"error": "Attendance not found"}, status=404)

        attendance.is_submitted = True
        attendance.save()

        return Response({"message": "Attendance submitted successfully."})



class OverrideAttendanceAPIView(APIView):
    permission_classes = [IsAuthenticated, IsFaculty, IsActiveFaculty]

    def post(self, request):
        attendance_id = request.data.get("attendance_id")

        if not attendance_id:
            return Response({"error": "attendance_id required"}, status=400)

        try:
            attendance = Attendance.objects.get(
                attendance_id=attendance_id,
                faculty_allocation__faculty=request.user.faculty_profile

            )
        except Attendance.DoesNotExist:
            return Response(
                {"error": "Attendance not found or unauthorized."},
                status=404
            )

        now = timezone.now()

        # Auto override within 7 days
        if attendance.submitted_at and now <= attendance.submitted_at + timedelta(days=7):
            attendance.is_submitted = False
            attendance.save()
            return Response({"message": "Attendance unlocked (within 7-day window)."})

        # Coordinator override window
        if attendance.override_until and now <= attendance.override_until:
            attendance.is_submitted = False
            attendance.save()
            return Response({"message": "Attendance unlocked (coordinator approval)."})

        return Response(
            {"error": "Override period expired. Contact Academic Coordinator."},
            status=403
        )


class GrantOverrideAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAcademicCoordinator]

    def post(self, request):
        attendance_id = request.data.get("attendance_id")

        if not attendance_id:
            return Response({"error": "attendance_id required"}, status=400)

        try:
            attendance = Attendance.objects.get(attendance_id=attendance_id)
        except Attendance.DoesNotExist:
            return Response({"error": "Attendance not found"}, status=404)

        attendance.override_until = timezone.now() + timedelta(hours=1)
        attendance.save()

        return Response({
            "message": "Override granted for 1 hour.",
            "override_until": attendance.override_until
        })



'''
-------------------------------------------------------------------------------------------------------------------------------
                                            Assignment
-------------------------------------------------------------------------------------------------------------------------------
'''

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Assignment, StudentSubmission
from .serializers import AssignmentSerializer, FacultySubmissionViewSerializer, StudentSubmissionSerializer, AssignmentSerializer
from rest_framework.permissions import IsAuthenticated
from Creation.permissions import IsFaculty

class AssignmentAPIView(APIView):

    permission_classes = [IsAuthenticated, IsFaculty]

    # ✅ List Assignments for Faculty
    def get(self, request):
        assignments = Assignment.objects.filter(faculty=request.user)
        serializer = AssignmentSerializer(assignments, many=True)
        return Response(serializer.data)

    # ✅ Create Assignment
    def post(self, request):
        serializer = AssignmentSerializer(
            data=request.data,
            context={"request": request}
        )

        if serializer.is_valid():
            serializer.save(faculty=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        try:
            assignment = Assignment.objects.get(pk=pk, faculty=request.user)
            assignment.delete()
            return Response({"message": "Assignment deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except Assignment.DoesNotExist:
            return Response({"error": "Assignment not found"}, status=status.HTTP_404_NOT_FOUND)

    # ✅ Edit Assignment (PUT)
    def put(self, request, pk):
        try:
            assignment = Assignment.objects.get(pk=pk, faculty=request.user)
        except Assignment.DoesNotExist:
            return Response(
                {"error": "Assignment not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = AssignmentSerializer(
            assignment,
            data=request.data,
            context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


#After submitting the assignment
from django.utils import timezone
from django.db.models import Count


class FacultySubmissionAPIView(APIView):

    permission_classes = [IsAuthenticated, IsFaculty]

    def get(self, request, assignment_id):

        try:
            assignment = Assignment.objects.get(
                id=assignment_id,
                faculty=request.user
            )
        except Assignment.DoesNotExist:
            return Response(
                {"error": "Assignment not found"},
                status=404
            )

        submissions = StudentSubmission.objects.filter(
            assignment=assignment
        )

        # 🔎 FILTER
        status_filter = request.query_params.get("status")

        if status_filter == "late":
            submissions = submissions.filter(
                submitted_at__gt=assignment.end_datetime
            )

        elif status_filter == "on_time":
            submissions = submissions.filter(
                submitted_at__lte=assignment.end_datetime
            )

        serializer = FacultySubmissionViewSerializer(submissions, many=True)

        # 📊 COUNTS
        from UserDataManagement.models import Student

        section_name = assignment.section.name

        total_students = Student.objects.filter(
            academicclassstudent__academic_class=assignment.academic_class,
            section=section_name
        ).distinct().count()


        submitted_count = StudentSubmission.objects.filter(
            assignment=assignment
        ).count()

        not_submitted = total_students - submitted_count

        late_count = StudentSubmission.objects.filter(
            assignment=assignment,
            submitted_at__gt=assignment.end_datetime
        ).count()

        on_time_count = submitted_count - late_count

        return Response({
            "assignment_title": assignment.title,
            "total_students": total_students,
            "submitted_count": submitted_count,
            "not_submitted_count": not_submitted,
            "on_time_count": on_time_count,
            "late_count": late_count,
            "submissions": serializer.data
        })



'''
-------------------------------------------------------------------------------------------------------------------------------
                                                Quiz
-------------------------------------------------------------------------------------------------------------------------------
'''

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .models import Quiz, Question, Option
from .serializers import (
    QuizCreateSerializer,
    QuizUpdateSerializer,
    QuizDetailSerializer,
    QuestionSerializer,
    OptionSerializer
)

from Creation.permissions import IsFaculty


# =========================================
# CREATE QUIZ
# =========================================

class QuizCreateAPIView(APIView):
    permission_classes = [IsAuthenticated, IsFaculty]

    def get(self, request):
        quizzes = Quiz.objects.filter(faculty=request.user)
        serializer = QuizDetailSerializer(quizzes, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = QuizCreateSerializer(
            data=request.data,
            context={"request": request}
        )

        if serializer.is_valid():
            serializer.save(faculty=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# =========================================
# UPDATE QUIZ (PUT)
# =========================================

class QuizUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated, IsFaculty]

    def put(self, request, quiz_id):
        try:
            quiz = Quiz.objects.get(id=quiz_id, faculty=request.user)
        except Quiz.DoesNotExist:
            return Response({"error": "Quiz not found"}, status=404)

        serializer = QuizUpdateSerializer(quiz, data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=400)

    def delete(self, request, quiz_id):
        try:
            quiz = Quiz.objects.get(id=quiz_id, faculty=request.user)
            quiz.delete()
            return Response({"message": "Quiz deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
        except Quiz.DoesNotExist:
            return Response({"error": "Quiz not found"}, status=status.HTTP_404_NOT_FOUND)


# =========================================
# PUBLISH QUIZ
# =========================================

class PublishQuizAPIView(APIView):
    permission_classes = [IsAuthenticated, IsFaculty]

    def put(self, request, quiz_id):
        try:
            quiz = Quiz.objects.get(id=quiz_id, faculty=request.user)
        except Quiz.DoesNotExist:
            return Response({"error": "Quiz not found"}, status=404)

        if quiz.questions.count() == 0:
            return Response(
                {"error": "Cannot publish quiz without questions."},
                status=400
            )

        quiz.is_published = True
        quiz.save(update_fields=["is_published"])

        return Response({"message": "Quiz published successfully."})


# =========================================
# QUIZ DETAIL (FACULTY VIEW)
# =========================================

class QuizDetailAPIView(APIView):
    permission_classes = [IsAuthenticated, IsFaculty]

    def get(self, request, quiz_id):
        try:
            quiz = Quiz.objects.get(id=quiz_id, faculty=request.user)
        except Quiz.DoesNotExist:
            return Response({"error": "Quiz not found"}, status=404)

        serializer = QuizDetailSerializer(quiz)
        return Response(serializer.data)


# =========================================
# ADD QUESTION
# =========================================

class AddQuestionAPIView(APIView):
    permission_classes = [IsAuthenticated, IsFaculty]

    def post(self, request):
        serializer = QuestionSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)

        return Response(serializer.errors, status=400)


# =========================================
# ADD OPTION
# =========================================

class AddOptionAPIView(APIView):
    permission_classes = [IsAuthenticated, IsFaculty]

    def post(self, request):
        serializer = OptionSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)

        return Response(serializer.errors, status=400)



'''
--------------------------------------------------------------------------------------------------------------------------------
                                        Resources
--------------------------------------------------------------------------------------------------------------------------------
'''


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .models import Resource
from .serializers import ResourceSerializer
from Creation.permissions import IsFaculty


# =========================================
# CREATE RESOURCE
# =========================================

class ResourceCreateAPIView(APIView):
    permission_classes = [IsAuthenticated, IsFaculty]

    def post(self, request):

        serializer = ResourceSerializer(
            data=request.data,
            context={"request": request}
        )

        if serializer.is_valid():
            serializer.save(faculty=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# =========================================
# UPDATE RESOURCE
# =========================================

class ResourceUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated, IsFaculty]

    def put(self, request, resource_id):

        try:
            resource = Resource.objects.get(
                id=resource_id,
                faculty=request.user,
                is_active=True
            )
        except Resource.DoesNotExist:
            return Response(
                {"error": "Resource not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = ResourceSerializer(
            resource,
            data=request.data,
            context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# =========================================
# DELETE RESOURCE (Soft Delete)
# =========================================

class ResourceDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated, IsFaculty]

    def delete(self, request, resource_id):

        try:
            resource = Resource.objects.get(
                id=resource_id,
                faculty=request.user,
                is_active=True
            )
        except Resource.DoesNotExist:
            return Response(
                {"error": "Resource not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Soft delete instead of permanent delete
        resource.is_active = False
        resource.save(update_fields=["is_active"])

        return Response(
            {"message": "Resource deleted successfully."},
            status=status.HTTP_200_OK
        )


# =========================================
# LIST RESOURCES
# =========================================

class ResourceListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsFaculty]

    def get(self, request):

        academic_class = request.query_params.get("academic_class")
        section = request.query_params.get("section")
        resource_type = request.query_params.get("resource_type")

        resources = Resource.objects.filter(
            faculty=request.user,
            is_active=True
        )

        if academic_class:
            resources = resources.filter(academic_class=academic_class)

        if section:
            resources = resources.filter(section=section)

        if resource_type:
            resources = resources.filter(resource_type=resource_type)

        serializer = ResourceSerializer(resources, many=True)

        return Response(serializer.data)


# =========================================
# FACULTY DASHBOARD SUMMARY
# =========================================

class FacultyDashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated, IsFaculty]

    def get(self, request):
        faculty_profile = getattr(request.user, 'faculty_profile', None)
        if not faculty_profile:
            return Response({"error": "Faculty profile not found"}, status=403)

        # 1. Allocated Classes
        allocations = FacultyAllocation.objects.filter(faculty=faculty_profile)
        
        class_data = []
        total_students_count = 0
        
        for alloc in allocations:
        # Count students in this class / virtual section
            if alloc.academic_class:
                student_count = alloc.academic_class.students.count()
                class_name = str(alloc.academic_class)
                class_id = alloc.academic_class.class_id
            else:
                student_count = alloc.virtual_section.students.count()
                class_name = f"Virtual: {alloc.virtual_section.name}"
                class_id = str(alloc.virtual_section.virtual_id)

            total_students_count += student_count
            
            class_data.append({
                "allocation_id": str(alloc.allocation_id),
                "class_id": class_id,
                "section_id": alloc.section.id if alloc.section else (str(alloc.virtual_section.virtual_id) if alloc.virtual_section else None),
                "class_name": class_name,
                "course_name": alloc.course.course_name,
                "student_count": student_count,
                "is_virtual": alloc.virtual_section is not None
            })

        # 2. Assignment Summary
        assignments = Assignment.objects.filter(faculty=request.user)
        pending_assignments_count = assignments.filter(end_datetime__gt=timezone.now()).count()

        # 3. Quiz Summary
        quizzes = Quiz.objects.filter(faculty=request.user)
        unpublished_quizzes_count = quizzes.filter(is_published=False).count()

        # 4. Recent Activities (Attendance markers)
        # Fetching last 5 attendance records
        recent_attendance = Attendance.objects.filter(faculty_allocation__faculty=faculty_profile).select_related('faculty_allocation__academic_class', 'faculty_allocation__virtual_section').order_by('-date')[:5]
        attendance_activities = []
        for att in recent_attendance:
            alloc = att.faculty_allocation
            if alloc.academic_class:
                class_label = str(alloc.academic_class)
            elif alloc.virtual_section:
                class_label = f"Virtual: {alloc.virtual_section.name}"
            else:
                class_label = "Unknown"

            attendance_activities.append({
                "date": att.date,
                "class": class_label,
                "status": "Submitted" if att.is_submitted else "Pending"
            })

        return Response({
            "faculty_name": request.user.get_full_name(),
            "employee_id": faculty_profile.employee_id,
            "total_classes": allocations.count(),
            "total_students": total_students_count,
            "allocated_classes": class_data,
            "tasks": {
                "active_assignments": pending_assignments_count,
                "unpublished_quizzes": unpublished_quizzes_count,
            },
            "recent_attendance": attendance_activities
        })


class StudentsForAllocationAPIView(APIView):
    permission_classes = [IsAuthenticated, IsFaculty, IsActiveFaculty]

    def get(self, request):
        allocation_id = request.query_params.get("allocation_id")
        if not allocation_id:
            return Response({"error": "allocation_id is required"}, status=400)

        try:
            faculty = request.user.faculty_profile
            allocation = FacultyAllocation.objects.get(
                allocation_id=allocation_id,
                faculty=faculty
            )
        except FacultyAllocation.DoesNotExist:
            return Response({"error": "Allocation not found or unauthorized"}, status=404)

        student_data = []
        if allocation.academic_class:
            from CourseManagement.models import AcademicClassStudent
            students_mappings = AcademicClassStudent.objects.filter(
                academic_class=allocation.academic_class
            ).select_related('student')
            
            for mapping in students_mappings:
                student_data.append({
                    "student_id": mapping.student.student_id,
                    "roll_no": mapping.student.roll_no,
                    "student_name": mapping.student.student_name,
                })
        elif allocation.virtual_section:
            students = allocation.virtual_section.students.all()
            for student in students:
                student_data.append({
                    "student_id": student.student_id,
                    "roll_no": student.roll_no,
                    "student_name": student.student_name,
                })
        else:
            return Response({"error": "No academic class or virtual section associated"}, status=400)

        return Response(student_data)
