from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db import transaction

from CourseConfiguration.models import (
    RegistrationWindow,
    StudentSelection,
    Course
)
from UserDataManagement.models import (
    Student,
    DepartmentAdminAssignment
)
from .serializers import (
    DeptAdminStudentSerializer,
    DeptAdminAssignCoursesSerializer
)


# =====================================================
# 🔒 COMMON ROLE CHECK
# =====================================================
def ensure_department_admin(request):
    """
    Validates that the user is an authenticated Academic Coordinator
    with an active department assignment.
    
    Returns: (success: bool, error_response: Response or None)
    """
    if not request.user.is_authenticated:
        return False, Response(
            {"detail": "Authentication required"},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if request.user.role != 'ACADEMIC_COORDINATOR':
        return False, Response(
            {"detail": "Access denied. Academic Coordinator role required."},
            status=status.HTTP_403_FORBIDDEN
        )

    return True, None


# =====================================================
# 1️⃣ REGISTRATION SUMMARY
# =====================================================
class DeptAdminRegistrationSummaryAPIView(APIView):
    """
    Returns a summary of course registration statistics for the 
    Academic Coordinator's assigned department.
    
    Response:
        - window_id: Active registration window UUID
        - total_students: Total students in dept/regulation/semester
        - registered_students: Students who have completed registration
        - unregistered_students: Students who haven't registered yet
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        allowed, error = ensure_department_admin(request)
        if not allowed:
            return error

        faculty = getattr(request.user, 'faculty_profile', None)

        if not faculty:
            return Response(
                {"error": "Faculty profile not found for this user"},
                status=status.HTTP_400_BAD_REQUEST
            )

        assignment = DepartmentAdminAssignment.objects.filter(
            faculty=faculty,
            is_active=True
        ).first()

        if not assignment:
            return Response(
                {"error": "No department assigned"},
                status=status.HTTP_403_FORBIDDEN
            )

        window = RegistrationWindow.objects.filter(
            department=assignment.department,
            status='ACTIVE',
            is_active=True
        ).first()

        if not window:
            return Response(
                {"error": "Course Registration window closed"},
                status=status.HTTP_400_BAD_REQUEST
            )

        total_students_qs = Student.objects.filter(
            department=assignment.department,
            regulation=window.regulation,
            semester=window.semester,
            is_active=True
        )

        registered_students_qs = Student.objects.filter(
            course_selections__window=window
        ).distinct()

        return Response({
            "window_id": str(window.window_id),
            "total_students": total_students_qs.count(),
            "registered_students": registered_students_qs.count(),
            "unregistered_students": (
                total_students_qs.count() - registered_students_qs.count()
            )
        })


# =====================================================
# 2️⃣ UNREGISTERED STUDENTS
# =====================================================
class DeptAdminUnregisteredStudentsAPIView(APIView):
    """
    Returns a list of students who have not yet completed course 
    registration for the active window.
    
    Response: List of student objects with basic information.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        allowed, error = ensure_department_admin(request)
        if not allowed:
            return error

        faculty = getattr(request.user, 'faculty_profile', None)

        if not faculty:
            return Response(
                {"error": "Faculty profile not found for this user"},
                status=status.HTTP_400_BAD_REQUEST
            )

        assignment = DepartmentAdminAssignment.objects.filter(
            faculty=faculty,
            is_active=True
        ).first()

        if not assignment:
            return Response(
                {"error": "No department assigned"},
                status=status.HTTP_403_FORBIDDEN
            )

        window = RegistrationWindow.objects.filter(
            department=assignment.department,
            status='ACTIVE',
            is_active=True
        ).first()

        if not window:
            return Response(
                {"error": "Course Registration window closed"},
                status=status.HTTP_400_BAD_REQUEST
            )

        registered_ids = StudentSelection.objects.filter(
            window=window
        ).values_list('student_id', flat=True)

        students = Student.objects.filter(
            department=assignment.department,
            regulation=window.regulation,
            semester=window.semester,
            is_active=True
        ).exclude(student_id__in=registered_ids)

        serializer = DeptAdminStudentSerializer(students, many=True)
        return Response(serializer.data)


# =====================================================
# 3️⃣ MANUAL REGISTER / MODIFY COURSES
# =====================================================
class DeptAdminAssignCoursesAPIView(APIView):
    """
    Allows Academic Coordinators to manually register or modify 
    course selections for students in their department.
    
    Payload:
        - student_id: UUID of the student
        - course_ids: List of course UUIDs to assign
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        allowed, error = ensure_department_admin(request)
        if not allowed:
            return error

        serializer = DeptAdminAssignCoursesSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        faculty = getattr(request.user, 'faculty_profile', None)

        if not faculty:
            return Response(
                {"error": "Faculty profile not found for this user"},
                status=status.HTTP_400_BAD_REQUEST
            )

        assignment = DepartmentAdminAssignment.objects.filter(
            faculty=faculty,
            is_active=True
        ).first()

        if not assignment:
            return Response(
                {"error": "No department assigned"},
                status=status.HTTP_403_FORBIDDEN
            )

        window = RegistrationWindow.objects.filter(
            department=assignment.department,
            status='ACTIVE',
            is_active=True
        ).first()

        if not window:
            return Response(
                {"error": "Course Registration window closed"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            student = Student.objects.get(
                student_id=serializer.validated_data['student_id'],
                department=assignment.department
            )
        except Student.DoesNotExist:
            return Response(
                {"error": "Student not found in your department"},
                status=status.HTTP_404_NOT_FOUND
            )

        selection, _ = StudentSelection.objects.get_or_create(
            student=student,
            window=window
        )

        courses = Course.objects.filter(
            course_id__in=serializer.validated_data['course_ids']
        )

        selection.courses.set(courses)
        selection.save()

        return Response(
            {"message": "Student course registration updated successfully"},
            status=status.HTTP_200_OK
        )
