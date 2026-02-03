from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .models import Faculty, FacultyMapping,Student,DepartmentAdminAssignment
from .serializers import FacultySerializer,StudentPatchSerializer, DepartmentAdminAssignmentSerializer
from Creation.permissions import IsCollegeAdmin
from AcademicSetup.permissions import IsCampusAdmin
import openpyxl
from io import BytesIO
from django.contrib.auth import get_user_model
from Creation.models import School, Department,Degree
from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q, F
from .serializers import (
    FacultySerializer, 
    StudentPatchSerializer, 
    DepartmentAdminAssignmentSerializer,
    UserRoleSerializer
)


'''
-------------------------------------------------------------------------------------------------------------------------------
                                                Faculty creation
-------------------------------------------------------------------------------------------------------------------------------
'''


User = get_user_model()

REQUIRED_HEADERS = [
    "employee_id",
    "faculty_name",
    "faculty_email",
    "faculty_mobile_no",
    "faculty_date_of_birth",
    "faculty_gender",
    "dept_code",
    "school_code",
]

ALLOWED_GENDERS = ["MALE", "FEMALE", "OTHER"]


#Faculty Individual upload

class FacultyViewSet(viewsets.ModelViewSet):
    queryset = Faculty.objects.all()
    serializer_class = FacultySerializer
    lookup_field = "employee_id"   # 🔑 IMPORTANT

    def create(self, request, *args, **kwargs):
        mappings = request.data.pop("mappings", [])

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        faculty = serializer.save()

        self._save_mappings(faculty, mappings)

        return Response(
            FacultySerializer(faculty).data,
            status=status.HTTP_201_CREATED
        )

    def partial_update(self, request, *args, **kwargs):
        faculty = get_object_or_404(
            Faculty,
            employee_id=kwargs["employee_id"]
        )

        mappings = request.data.pop("mappings", None)

        serializer = self.get_serializer(
            faculty,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        faculty = serializer.save()

        if mappings is not None:
            FacultyMapping.objects.filter(faculty=faculty).delete()
            self._save_mappings(faculty, mappings)

        return Response(
            FacultySerializer(faculty).data,
            status=status.HTTP_200_OK
        )

    # 🔁 shared helper (clean + DRY)
    def _save_mappings(self, faculty, mappings):
        for mapping in mappings:
            school_code = mapping.get("school_code")
            dept_code = mapping.get("dept_code")

            school = School.objects.filter(
                school_code__iexact=school_code
            ).first()
            if not school:
                raise ValueError(f"Invalid school_code '{school_code}'")

            department = Department.objects.filter(
                dept_code__iexact=dept_code,
                degree__school=school
            ).first()
            if not department:
                raise ValueError(
                    f"Invalid dept_code '{dept_code}' for school '{school_code}'"
                )

            FacultyMapping.objects.create(
                faculty=faculty,
                school=school,
                department=department
            )

class FacultyMappingOptionsView(APIView):
    permission_classes = [IsCampusAdmin]

    def get(self, request):
        schools = School.objects.all().prefetch_related('degrees__departments')
        options = []

        for school in schools:
            options.append({
                "label": f"{school.school_name} (Full School)",
                "school_id": str(school.school_id),
                "department_id": None
            })

            for degree in school.degrees.all():
                for dept in degree.departments.all():
                    options.append({
                        "label": f"{school.school_name} - {dept.dept_name}",
                        "school_id": str(school.school_id),
                        "department_id": str(dept.dept_id)
                    })

        return Response(options)


#Faculty Bulk upload
class FacultyBulkUploadAPIView(APIView):
    permission_classes = [IsCampusAdmin]
    parser_classes = [MultiPartParser]

    def post(self, request):
        excel_file = request.FILES.get("file")

        if not excel_file:
            return Response(
                {"error": "Excel file is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            wb = openpyxl.load_workbook(excel_file)
            sheet = wb.active   # sheet name is now irrelevant

            summary = {
                "total_rows": 0,
                "created_faculty": 0,
                "skipped_rows": 0,
            }

            row_errors = []

            headers = [cell.value for cell in sheet[1] if cell.value]

            missing_headers = [h for h in REQUIRED_HEADERS if h not in headers]
            if missing_headers:
                return Response(
                    {
                        "error": "Missing required columns",
                        "missing_columns": missing_headers
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            header_index = {h: headers.index(h) for h in REQUIRED_HEADERS}

            for row_no, row in enumerate(sheet.iter_rows(min_row=2), start=2):
                if not any(cell.value for cell in row):
                    continue

                summary["total_rows"] += 1

                try:
                    data = {
                        h: row[header_index[h]].value
                        for h in REQUIRED_HEADERS
                    }

                    # --- BASIC VALIDATIONS ---
                    if not data["employee_id"]:
                        raise ValueError("employee_id is required")

                    gender = str(data["faculty_gender"]).upper()
                    if gender not in ALLOWED_GENDERS:
                        raise ValueError(
                            f"Invalid gender '{data['faculty_gender']}'. "
                            f"Allowed: {ALLOWED_GENDERS}"
                        )

                    # --- SCHOOL FROM EXCEL ---
                    school_code = str(data["school_code"]).strip()
                    school = School.objects.filter(
                        school_code__iexact=school_code
                    ).first()

                    if not school:
                        raise ValueError(f"Invalid school_code '{school_code}'")

                    # --- DEPARTMENT FROM EXCEL ---
                    dept_code = str(data["dept_code"]).strip()

                    department = Department.objects.filter(
                        dept_code__iexact=dept_code,
                        degree__school=school
                    ).first()

                    if not department:
                        raise ValueError(
                            f"Invalid dept_code '{dept_code}' for school '{school_code}'"
                        )

                    # --- USER ---
                    user, _ = User.objects.get_or_create(
                        username=data["employee_id"],
                        defaults={"email": data["faculty_email"]}
                    )

                    # --- FACULTY ---
                    faculty, created = Faculty.objects.get_or_create(
                        employee_id=data["employee_id"],
                        defaults={
                            "user": user,
                            "faculty_name": data["faculty_name"],
                            "faculty_email": data["faculty_email"],
                            "faculty_mobile_no": data["faculty_mobile_no"],
                            "faculty_date_of_birth": data["faculty_date_of_birth"],
                            "faculty_gender": gender,
                        }
                    )

                    # --- MAPPING ---
                    FacultyMapping.objects.get_or_create(
                        faculty=faculty,
                        school=school,
                        department=department
                    )

                    if created:
                        summary["created_faculty"] += 1

                except Exception as e:
                    summary["skipped_rows"] += 1
                    row_errors.append({
                        "row": row_no,
                        "error": str(e)
                    })

            return Response(
                {
                    "status": "PARTIAL_SUCCESS" if row_errors else "SUCCESS",
                    "summary": summary,
                    "row_errors": row_errors
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {"error": f"Error processing Excel file: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )



'''
--------------------------------------------------------------------------------------------------------------------------------
                                                Student creation
--------------------------------------------------------------------------------------------------------------------------------
'''


# ------------------------------------------
# STUDENTS
# ------------------------------------------

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from Creation.permissions import IsCollegeAdmin
from .models import Student
from .serializers import (
    StudentExcelUploadSerializer,
    StudentPatchSerializer,
)


# ======================================================
# BULK POST – EXCEL UPLOAD
# ======================================================

from django.contrib.auth import get_user_model
User = get_user_model()

import openpyxl
from django.contrib.auth import get_user_model

User = get_user_model()

class StudentExcelUploadAPIView(APIView):
    permission_classes = [IsAuthenticated, IsCollegeAdmin]

    def post(self, request):
        serializer = StudentExcelUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = serializer.save()

        return Response(
            {
                "status": "SUCCESS" if not result["errors"] else "PARTIAL_SUCCESS",
                **result
            },
            status=status.HTTP_201_CREATED
        )


# ======================================================
# BULK GET – ALL STUDENTS
# ======================================================
class StudentListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsCollegeAdmin]

    def get(self, request):
        students = Student.objects.select_related(
            "department", "degree", "regulation", "semester"
        ).all()

        data = [
            {
                "roll_no": s.roll_no,
                "student_name": s.student_name,
                "student_email": s.student_email,
                "student_gender": s.student_gender,
                "student_date_of_birth": s.student_date_of_birth,
                "student_phone_number": s.student_phone_number,
                "department": s.department.dept_code,
                "regulation": s.regulation.regulation_code,
                "semester": s.semester.sem_number,
                "is_active": s.is_active,
            }
            for s in students
        ]

        return Response(
            {
                "count": len(data),
                "results": data,
            },
            status=status.HTTP_200_OK,
        )


# ======================================================
# GET + PATCH – INDIVIDUAL STUDENT
# ======================================================
class StudentDetailAPIView(APIView):
    permission_classes = [IsAuthenticated, IsCollegeAdmin]

    def get(self, request, roll_no):
        student = Student.objects.filter(roll_no=roll_no).first()
        if not student:
            return Response(
                {"error": "Student not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "roll_no": student.roll_no,
                "student_name": student.student_name,
                "student_email": student.student_email,
                "student_gender": student.student_gender,
                "student_date_of_birth": student.student_date_of_birth,
                "student_phone_number": student.student_phone_number,
                "parent_name": student.parent_name,
                "parent_phone_number": student.parent_phone_number,
                "batch": student.batch,
                "department": student.department.dept_code,
                "regulation": student.regulation.regulation_code,
                "semester": student.semester.sem_number,
                "is_active": student.is_active,
            },
            status=status.HTTP_200_OK,
        )

    def patch(self, request, roll_no):
        student = Student.objects.filter(roll_no=roll_no).first()
        if not student:
            return Response(
                {"error": "Student not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = StudentPatchSerializer(
            instance=student,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"message": "Student updated successfully"},
            status=status.HTTP_200_OK,
        )



# ==================================================================================
# DEPARTMENT ADMIN ASSIGNMENT VIEWS
# ==================================================================================
# These views handle the Department Admin assignment feature.
#
# Key Components:
# 1. DepartmentAdminAssignmentViewSet: CRUD operations for assignments
# 2. DegreesForSchoolView: Cascading filter - get degrees for a school
# 3. DepartmentsForDegreeView: Cascading filter - get departments for a degree
# 4. FacultySearchView: Search faculty by name or employee_id
#
# Cascading Selection Flow:
# Step 1: User selects School -> Frontend calls DegreesForSchoolView
# Step 2: User selects Degree -> Frontend calls DepartmentsForDegreeView
# Step 3: User selects Department(s) and Faculty
# Step 4: User clicks "Assign" -> Triggers MFA (handled in frontend)
# Step 5: After MFA success -> POST to DepartmentAdminAssignmentViewSet
# ==================================================================================

class DepartmentAdminAssignmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Department Admin assignments.
    
    Only Campus Admins can create, view, update, or delete assignments.
    When a new assignment is created, the faculty member's user role is
    automatically updated to DEPARTMENT_ADMIN (handled in model.save()).
    """
    queryset = DepartmentAdminAssignment.objects.all().select_related(
        'faculty', 'school', 'degree', 'department', 'assigned_by'
    )
    serializer_class = DepartmentAdminAssignmentSerializer
    permission_classes = [IsCampusAdmin]
    lookup_field = 'assignment_id'
    
    def perform_create(self, serializer):
        """
        Override perform_create to automatically set assigned_by to current user.
        
        This ensures we always know which campus admin made each assignment.
        """
        serializer.save(assigned_by=self.request.user)


class DegreesForSchoolView(APIView):
    """
    Cascading filter endpoint: Get all degrees for a selected school.
    
    Usage: GET /users/dept-admin/degrees-for-school/?school_id=<uuid>
    
    This is used in the frontend to populate the Degree dropdown after
    a School is selected, ensuring only relevant degrees are shown.
    """
    permission_classes = [IsCampusAdmin]
    
    def get(self, request):
        school_id = request.query_params.get('school_id')
        
        if not school_id:
            return Response(
                {"detail": "school_id query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get all degrees for this school
        degrees = Degree.objects.filter(school_id=school_id).values(
            'degree_id', 'degree_name', 'degree_code'
        )
        
        return Response(list(degrees))


class DepartmentsForDegreeView(APIView):
    """
    Cascading filter endpoint: Get all departments for a selected degree.
    
    Usage: GET /users/dept-admin/departments-for-degree/?degree_id=<uuid>
    
    This is used in the frontend to populate the Department dropdown after
    a Degree is selected, ensuring only relevant departments are shown.
    """
    permission_classes = [IsCampusAdmin]
    
    def get(self, request):
        degree_id = request.query_params.get('degree_id')
        
        if not degree_id:
            return Response(
                {"detail": "degree_id query parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get all departments for this degree
        departments = Department.objects.filter(degree_id=degree_id).values(
            'dept_id', 'dept_name', 'dept_code'
        )
        
        return Response(list(departments))


class FacultySearchView(APIView):
    """
    Search endpoint: Find faculty by name or employee ID.
    
    Usage: GET /users/dept-admin/search-faculty/?q=<search_term>
    
    This powers the faculty search functionality in the assignment form.
    Supports partial matching on both full_name and employee_id.
    Only returns active faculty members.
    """
    permission_classes = [IsCampusAdmin]
    
    def get(self, request):
        search_query = request.query_params.get('q', '').strip()
        
        if len(search_query) < 2:
            return Response(
                {"detail": "Search query must be at least 2 characters"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Search by faculty_name or employee_id (case-insensitive)
        faculty = Faculty.objects.filter(
            is_active=True
        ).filter(
            Q(faculty_name__icontains=search_query) |
            Q(employee_id__icontains=search_query)
        ).values(
            'id', 'faculty_name', 'employee_id', 'faculty_email'
        )[:20]  # Limit to 20 results
        
        return Response(list(faculty))

# ==================================================================================
# ROLES DASHBOARD VIEWS (FEATURE 4)
# ==================================================================================

class RolesSummaryView(APIView):
    """
    API for the Roles Dashboard Summary.
    Returns counts for Faculty, Campus Admins (CA), and Students.
    """
    permission_classes = [IsAuthenticated, IsCollegeAdmin]

    def get(self, request):
        counts = User.objects.aggregate(
            total_students=Count('id', filter=Q(role='STUDENT')),
            total_faculty=Count('id', filter=Q(role='FACULTY')),
            total_ca=Count('id', filter=Q(role__in=['COLLEGE_ADMIN', 'ACADEMIC_COORDINATOR']))
        )
        return Response(counts)

class RolesListView(APIView):
    """
    API for the Roles Dashboard Detail List.
    Supports filtering by role and academic hierarchy (for students).
    """
    permission_classes = [IsAuthenticated, IsCollegeAdmin]

    def get(self, request):
        role_filter = request.query_params.get('role')
        school_id = request.query_params.get('school_id')
        degree_id = request.query_params.get('degree_id')
        dept_id = request.query_params.get('department_id')
        batch = request.query_params.get('batch')
        search = request.query_params.get('search')

        queryset = User.objects.all().select_related(
            'faculty_profile', 
            'student_profile', 
            'student_profile__department', 
            'student_profile__degree', 
            'student_profile__degree__school'
        )

        # Role Filter
        if role_filter and role_filter != 'ALL':
            if role_filter == 'CA':
                queryset = queryset.filter(role__in=['COLLEGE_ADMIN', 'ACADEMIC_COORDINATOR'])
            else:
                queryset = queryset.filter(role=role_filter)

        # Academic Filters (Only for Students or if role filter is broad)
        is_student_view = role_filter == 'STUDENT'
        is_broad_view = not role_filter or role_filter == 'ALL'

        if is_student_view or is_broad_view:
            # We apply student-specific filters if they are provided
            if school_id:
                queryset = queryset.filter(Q(student_profile__degree__school_id=school_id) | ~Q(role='STUDENT'))
            if degree_id:
                queryset = queryset.filter(Q(student_profile__degree_id=degree_id) | ~Q(role='STUDENT'))
            if dept_id:
                queryset = queryset.filter(Q(student_profile__department_id=dept_id) | ~Q(role='STUDENT'))
            if batch:
                queryset = queryset.filter(Q(student_profile__batch=batch) | ~Q(role='STUDENT'))
            
            # If we are specifically filtering for students, ensure we only get students
            if is_student_view:
                queryset = queryset.filter(role='STUDENT')

        # Search
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(faculty_profile__faculty_name__icontains=search) |
                Q(student_profile__student_name__icontains=search)
            )

        serializer = UserRoleSerializer(queryset[:100], many=True) # Limit to 100 for performance
        return Response(serializer.data)
