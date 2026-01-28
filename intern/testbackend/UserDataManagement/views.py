from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .models import Faculty, FacultyMapping
from .serializers import FacultySerializer
from AcademicSetup.permissions import IsCampusAdmin
import openpyxl
from io import BytesIO
from django.contrib.auth import get_user_model
from Creation.models import School, Department
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
