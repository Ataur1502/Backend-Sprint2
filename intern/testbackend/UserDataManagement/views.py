from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .models import Faculty, FacultyMapping, DepartmentAdminAssignment
from .serializers import FacultySerializer, DepartmentAdminAssignmentSerializer
from AcademicSetup.permissions import IsCampusAdmin
import openpyxl
from io import BytesIO
from django.contrib.auth import get_user_model
from Creation.models import School, Department, Degree
from django.db import transaction
from django.db.models import Q
from django.db import transaction

User = get_user_model()

class FacultyViewSet(viewsets.ModelViewSet):
    queryset = Faculty.objects.all()
    serializer_class = FacultySerializer
    permission_classes = [IsCampusAdmin]
    lookup_field = 'faculty_id'
    parser_classes = (MultiPartParser, FormParser, JSONParser)

    @action(detail=False, methods=['post'], url_path='upload-bulk')
    @transaction.atomic
    def upload_bulk(self, request):
        excel_file = request.FILES.get('file')
        if not excel_file:
            return Response({"detail": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            wb = openpyxl.load_workbook(excel_file)
            sheet = wb.active
            
            # Expected headers: Name, EmployeeID, Email, Mobile, DOB(YYYY-MM-DD), Gender, Mappings
            # Mappings format: "SchoolID:DeptID|SchoolID|SchoolID:DeptID"
            results = {"created": 0, "errors": []}
            
            for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
                if not any(row): continue
                
                try:
                    name, emp_id, email, mobile, dob, gender, mappings_raw = row[0:7]
                    
                    # Parse mappings
                    mappings = []
                    if mappings_raw:
                        parts = str(mappings_raw).split('|')
                        for part in parts:
                            if ':' in part:
                                s_id, d_id = part.split(':')
                                mappings.append({"school_id": s_id.strip(), "department_id": d_id.strip()})
                            else:
                                mappings.append({"school_id": part.strip(), "department_id": None})
                    
                    data = {
                        "full_name": name,
                        "employee_id": emp_id,
                        "email": email,
                        "mobile_no": mobile,
                        "dob": dob,
                        "gender": str(gender).upper(),
                        "mappings": mappings
                    }
                    
                    serializer = self.get_serializer(data=data)
                    if serializer.is_valid(raise_exception=True):
                        serializer.save()
                        results["created"] += 1
                except Exception as e:
                    results["errors"].append(f"Row {row_idx}: {str(e)}")
            
            return Response(results, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({"detail": f"Error processing file: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

class FacultyMappingOptionsView(APIView):
    permission_classes = [IsCampusAdmin]

    def get(self, request):
        schools = School.objects.all().prefetch_related('degrees__departments')
        options = []
        
        for school in schools:
            # Option for School only
            options.append({
                "label": f"{school.school_name} (Full School)",
                "value": f"{school.school_id}:none",
                "school_id": str(school.school_id),
                "department_id": None
            })
            # Options for each Department (through Degrees)
            for degree in school.degrees.all():
                for dept in degree.departments.all():
                    options.append({
                        "label": f"{school.school_name} - {dept.dept_name}",
                        "value": f"{school.school_id}:{dept.dept_id}",
                        "school_id": str(school.school_id),
                        "department_id": str(dept.dept_id)
                    })
        
        return Response(options)

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
        
        # Search by full_name or employee_id (case-insensitive)
        faculty = Faculty.objects.filter(
            is_active=True
        ).filter(
            Q(full_name__icontains=search_query) |
            Q(employee_id__icontains=search_query)
        ).values(
            'faculty_id', 'full_name', 'employee_id', 'email'
        )[:20]  # Limit to 20 results
        
        return Response(list(faculty))
