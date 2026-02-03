import openpyxl
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from rest_framework.parsers import MultiPartParser, FormParser
from django.db import transaction
from .models import Course
from .serializers import CourseSerializer
from Creation.models import School, Degree, Department, Regulation
from Creation.permissions import IsCollegeAdmin
from rest_framework.permissions import IsAuthenticated

class CourseListCreateAPIView(generics.ListCreateAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated, IsCollegeAdmin]
    filterset_fields = ['school', 'degree', 'department', 'regulation', 'batch']

    def get_queryset(self):
        queryset = super().get_queryset()
        school = self.request.query_params.get('school')
        degree = self.request.query_params.get('degree')
        department = self.request.query_params.get('department')
        regulation = self.request.query_params.get('regulation')
        batch = self.request.query_params.get('batch')

        if school: queryset = queryset.filter(school_id=school)
        if degree: queryset = queryset.filter(degree_id=degree)
        if department: queryset = queryset.filter(department_id=department)
        if regulation: queryset = queryset.filter(regulation_id=regulation)
        if batch: queryset = queryset.filter(batch=batch)
        
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return Response({"message": "Course created successfully", "data": serializer.data}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class CourseRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated, IsCollegeAdmin]
    lookup_field = 'course_id'

class CourseBulkUploadAPIView(APIView):
    permission_classes = [IsAuthenticated, IsCollegeAdmin]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({"error": "No file uploaded"}, status=status.HTTP_400_BAD_REQUEST)
        
        if not file_obj.name.endswith(('.xlsx', '.xls')):
            return Response({"error": "Invalid file format. Please upload an Excel file."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            wb = openpyxl.load_workbook(file_obj)
            sheet = wb.active
            
            # Assuming header row is at 1
            headers = [cell.value for cell in sheet[1]]
            required_headers = [
                'Course Name', 'Course Code', 'Course Type', 'School Code', 
                'Degree Code', 'Department Code', 'Regulation Code', 
                'Batch', 'Credit Value', 'L', 'T', 'P', 'Category'
            ]
            
            # Map headers to model fields or indices
            # For simplicity, let's assume a strict order or map them
            
            courses_to_create = []
            errors = []

            with transaction.atomic():
                for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
                    if not any(row): continue # Skip empty rows
                    
                    try:
                        (name, code, c_type, s_code, d_code, dept_code, r_code, batch, credit, l, t, p, cat) = row
                        
                        # Lookups
                        school = School.objects.get(school_code=s_code)
                        degree = Degree.objects.get(degree_code=d_code, school=school)
                        department = Department.objects.get(dept_code=dept_code, degree=degree)
                        regulation = Regulation.objects.get(regulation_code=r_code, degree=degree, batch=batch)
                        
                        if not regulation.is_active:
                            errors.append(f"Row {row_idx}: Regulation {r_code} is not active for batch {batch}")
                            continue

                        course_data = {
                            'course_name': name,
                            'course_code': code,
                            'course_type': c_type.upper(),
                            'school': school,
                            'degree': degree,
                            'department': department,
                            'regulation': regulation,
                            'batch': batch,
                            'credit_value': credit,
                            'lecture_hours': l,
                            'tutorial_hours': t,
                            'practical_hours': p,
                            'course_category': cat.upper(),
                            'status': True
                        }
                        
                        if Course.objects.filter(course_code=code).exists():
                            errors.append(f"Row {row_idx}: Duplicate course code {code}")
                            continue

                        courses_to_create.append(Course(**course_data))
                    
                    except School.DoesNotExist: errors.append(f"Row {row_idx}: School {s_code} not found")
                    except Degree.DoesNotExist: errors.append(f"Row {row_idx}: Degree {d_code} not found")
                    except Department.DoesNotExist: errors.append(f"Row {row_idx}: Department {dept_code} not found")
                    except Regulation.DoesNotExist: errors.append(f"Row {row_idx}: Regulation {r_code} not found for batch {batch}")
                    except Exception as e: errors.append(f"Row {row_idx}: {str(e)}")

                if errors:
                    transaction.set_rollback(True)
                    return Response({"error": "Bulk upload failed due to validation errors", "details": errors}, status=status.HTTP_400_BAD_REQUEST)
                
                Course.objects.bulk_create(courses_to_create)

            return Response({"message": f"Successfully uploaded {len(courses_to_create)} courses"}, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": f"An error occurred while processing the file: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

from rest_framework import viewsets
from .models import RegistrationWindow, StudentSelection
from .serializers import RegistrationWindowSerializer, StudentSelectionSerializer
from UserDataManagement.models import Student
from Creation.models import Semester
from django.db.models import Count

class RegistrationWindowViewSet(viewsets.ModelViewSet):
    queryset = RegistrationWindow.objects.all()
    serializer_class = RegistrationWindowSerializer
    permission_classes = [IsAuthenticated, IsCollegeAdmin]
    lookup_field = 'window_id'

class RegistrationMonitoringAPIView(APIView):
    permission_classes = [IsAuthenticated, IsCollegeAdmin]

    def get(self, request, window_id):
        window = generics.get_object_or_404(RegistrationWindow, window_id=window_id)
        
        # Total students in that Dept + Batch + Sem
        total_students = Student.objects.filter(
            department=window.department,
            batch=window.batch,
            semester=window.semester
        ).count()
        
        # Registered students
        registered_count = StudentSelection.objects.filter(window=window).count()
        
        # Subject-wise counts
        subject_counts = []
        # Combine major and elective for counting
        all_subjects = list(window.major_subjects.all()) + list(window.elective_subjects.all())
        
        for subject in all_subjects:
            count = StudentSelection.objects.filter(window=window, courses=subject).count()
            subject_counts.append({
                "course_name": subject.course_name,
                "course_code": subject.course_code,
                "count": count
            })

        return Response({
            "window_details": RegistrationWindowSerializer(window).data,
            "statistics": {
                "total_students": total_students,
                "registered_students": registered_count,
                "pending_students": total_students - registered_count,
                "subject_wise_counts": subject_counts
            }
        })

class StudentCourseRegistrationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Identify student profile
        student = generics.get_object_or_404(Student, user=request.user)
        
        # Find active window for this student
        window = RegistrationWindow.objects.filter(
            department=student.department,
            batch=student.batch,
            semester=student.semester,
            is_active=True,
            status='ACTIVE'
        ).first()
        
        if not window:
            return Response({"error": "No active registration window found for your semester."}, status=status.HTTP_404_NOT_FOUND)
            
        # Check if already registered
        existing = StudentSelection.objects.filter(student=student, window=window).first()
        
        return Response({
            "window": RegistrationWindowSerializer(window).data,
            "major_subjects": CourseSerializer(window.major_subjects.all(), many=True).data,
            "elective_subjects": CourseSerializer(window.elective_subjects.all(), many=True).data,
            "already_registered": existing is not None,
            "selection": StudentSelectionSerializer(existing).data if existing else None
        })

    def post(self, request):
        student = generics.get_object_or_404(Student, user=request.user)
        window_id = request.data.get('window_id')
        selected_course_ids = request.data.get('course_ids', [])
        
        window = generics.get_object_or_404(RegistrationWindow, window_id=window_id)
        
        # Validate window is still open
        from django.utils import timezone
        now = timezone.now()
        if now < window.start_datetime or now > window.end_datetime:
            return Response({"error": "Registration window is closed."}, status=status.HTTP_400_BAD_REQUEST)
        
        with transaction.atomic():
            selection, created = StudentSelection.objects.get_or_create(
                student=student,
                window=window
            )
            selection.courses.set(selected_course_ids)
            selection.save()
            
        return Response({"message": "Registration successful", "selection_id": selection.selection_id}, status=status.HTTP_201_CREATED)
