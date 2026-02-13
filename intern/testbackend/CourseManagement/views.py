from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from AcademicSetup.models import Section 
from .models import (
    AcademicClass, 
    AcademicClassStudent, 
    FacultyAllocation,
    Timetable,
)
from math import ceil

from CourseConfiguration.models import (
    RegistrationWindow,
    StudentSelection,
    Course
)
from UserDataManagement.models import (
    Student,
    DepartmentAdminAssignment,
    Faculty
)

from .serializers import (
    DeptAdminStudentSerializer,
    DeptAdminAssignCoursesSerializer,
    AcademicClassCreateSerializer,
    FacultyAllocationCreateSerializer,
    FacultyAllocationViewSerializer,
    TimetableCreateSerializer,
    TimetableViewSerializer
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

        registered_students_qs =  total_students_qs.filter(
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
            course_id__in=serializer.validated_data['course_ids'],
            department=assignment.department,
            regulation=window.regulation,
            semester=window.semester,
            is_active=True
        )
        
        if courses.count() != len(serializer.validated_data['course_ids']):
            return Response(
                {"error": "Invalid course selection"},
                status=status.HTTP_400_BAD_REQUEST
                )
            
        selection.courses.set(courses)
        selection.save()

        return Response(
            {"message": "Student course registration updated successfully"},
            status=status.HTTP_200_OK
        )
    
# =====================================================
# CLASS ALLOCATION (AUTO ROLL SPLIT)
# =====================================================

class AcademicClassAllocationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):

        # 🔒 Ensure Department Admin
        if request.user.role != 'ACADEMIC_COORDINATOR':
            return Response(
                {"error": "Access denied"},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = AcademicClassCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        department_id = data["department_id"]
        semester_id = data["semester_id"]
        regulation_id = data["regulation_id"]
        batch = data["batch"]
        academic_year = data["academic_year"]
        strength = data["strength"]

        # 1️⃣ Fetch eligible students ordered by roll_no
        students = Student.objects.filter(
            department_id=department_id,
            regulation_id=regulation_id,
            semester_id=semester_id,
            batch=batch,
            is_active=True
        ).order_by("roll_no")

        total_students = students.count()

        if total_students == 0:
            return Response(
                {"error": "No students found for allocation"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2️⃣ Calculate required number of classes
        number_of_classes = ceil(total_students / strength)

        # 3️⃣ Fetch sections
        sections = Section.objects.filter(
            status='ACTIVE'
        ).order_by("id")

        if sections.count() < number_of_classes:
            return Response(
                {"error": "Not enough active sections available"},
                status=status.HTTP_400_BAD_REQUEST
            )

        created_classes = []

        # 4️⃣ Create classes and assign students
        for i in range(number_of_classes):

            section = sections[i]

            academic_class = AcademicClass.objects.create(
                school_id=data["school_id"],
                degree_id=data["degree_id"],
                department_id=department_id,
                semester_id=semester_id,
                regulation_id=regulation_id,
                batch=batch,
                academic_year=academic_year,
                section=section,
                strength=strength,
                status="ACTIVE"
            )

            chunk_students = students[i * strength:(i + 1) * strength]

            for student in chunk_students:
                AcademicClassStudent.objects.create(
                    academic_class=academic_class,
                    student=student
                )
                student.section = section.name  
                student.save(update_fields=["section"])

            created_classes.append({
                "class_id": str(academic_class.class_id),
                "section": section.id,
                "student_count": chunk_students.count()
            })

        return Response(
            {
                "message": "Classes created successfully",
                "total_students": total_students,
                "total_classes_created": number_of_classes,
                "details": created_classes
            },
            status=status.HTTP_201_CREATED
        )

# =====================================================
# CLASS ALLOCATION PREVIEW (NO DB WRITE)
# =====================================================

class AcademicClassAllocationPreviewAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        # 🔒 Ensure Department Admin
        if request.user.role != 'ACADEMIC_COORDINATOR':
            return Response(
                {"error": "Access denied"},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = AcademicClassCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        department_id = data["department_id"]
        semester_id = data["semester_id"]
        regulation_id = data["regulation_id"]
        batch = data["batch"]
        strength = data["strength"]

        # Fetch students
        students = Student.objects.filter(
            department_id=department_id,
            regulation_id=regulation_id,
            semester_id=semester_id,
            batch=batch,
            is_active=True
        ).order_by("roll_no")

        total_students = students.count()

        if total_students == 0:
            return Response(
                {"error": "No students found"},
                status=status.HTTP_400_BAD_REQUEST
            )

        from math import ceil
        number_of_classes = ceil(total_students / strength)

        sections = Section.objects.filter(
            status="ACTIVE"
        ).order_by("id")

        if sections.count() < number_of_classes:
            return Response(
                {"error": "Not enough active sections available"},
                status=status.HTTP_400_BAD_REQUEST
            )

        preview_data = []

        for i in range(number_of_classes):
            section = sections[i]
            chunk_students = students[i * strength:(i + 1) * strength]

            preview_data.append({
                "section_id": section.id,
                "student_count": chunk_students.count(),
                "roll_range": {
                    "from": chunk_students.first().roll_no if chunk_students else None,
                    "to": chunk_students.last().roll_no if chunk_students else None
                }
            })

        return Response({
            "total_students": total_students,
            "strength_per_class": strength,
            "total_classes_to_be_created": number_of_classes,
            "distribution": preview_data
        })

# =====================================================
# FACULTY ALLOCATION API
# =====================================================

class FacultyAllocationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        # 🔒 Ensure Department Admin role
        if request.user.role != 'ACADEMIC_COORDINATOR':
            return Response(
                {"error": "Access denied"},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = FacultyAllocationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        allocation = FacultyAllocation.objects.create(
            faculty_id=data["faculty_id"],
            course_id=data["course_id"],
            academic_class_id=data["academic_class_id"],
            semester_id=data["semester_id"],
            academic_year=data["academic_year"],
            status="ACTIVE"
        )

        return Response(
            {
                "message": "Faculty allocated successfully",
                "allocation_id": str(allocation.allocation_id)
            },
            status=status.HTTP_201_CREATED
        )

# =====================================================
# FACULTY ALLOCATION LIST API
# =====================================================

class FacultyAllocationListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        if request.user.role != 'ACADEMIC_COORDINATOR':
            return Response(
                {"error": "Access denied"},
                status=status.HTTP_403_FORBIDDEN
            )

        academic_class_id = request.query_params.get("academic_class_id")
        semester_id = request.query_params.get("semester_id")
        academic_year = request.query_params.get("academic_year")

        allocations = FacultyAllocation.objects.all()

        if academic_class_id:
            allocations = allocations.filter(academic_class_id=academic_class_id)

        if semester_id:
            allocations = allocations.filter(semester_id=semester_id)

        if academic_year:
            allocations = allocations.filter(academic_year=academic_year)

        serializer = FacultyAllocationViewSerializer(allocations, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


# =====================================================
# TIMETABLE CREATE API
# =====================================================

class TimetableCreateAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        # 🔒 Ensure Department Admin
        if request.user.role != 'ACADEMIC_COORDINATOR':
            return Response(
                {"error": "Access denied"},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = TimetableCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        timetable = Timetable.objects.create(
            academic_class_id=data["academic_class_id"],
            faculty_allocation_id=data["faculty_allocation_id"],
            day_of_week=data["day_of_week"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            academic_year=data["academic_year"],
            status="ACTIVE"
        )

        return Response(
            {
                "message": "Timetable created successfully",
                "timetable_id": str(timetable.timetable_id)
            },
            status=status.HTTP_201_CREATED
        )

# =====================================================
# TIMETABLE LIST API
# =====================================================

class TimetableListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):

        if request.user.role != 'ACADEMIC_COORDINATOR':
            return Response(
                {"error": "Access denied"},
                status=status.HTTP_403_FORBIDDEN
            )

        academic_class_id = request.query_params.get("academic_class_id")
        academic_year = request.query_params.get("academic_year")

        timetables = Timetable.objects.filter(status="ACTIVE")

        if academic_class_id:
            timetables = timetables.filter(academic_class_id=academic_class_id)

        if academic_year:
            timetables = timetables.filter(academic_year=academic_year)

        timetables = timetables.order_by("day_of_week", "start_time")

        serializer = TimetableViewSerializer(timetables, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)
