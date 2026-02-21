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
            
            # Match headers from user image
            required_headers = [
                'Course Name', 'Course Short Name', 'Course Code', 'Course Type', 
                'School Code', 'Degree Code', 'Department Code', 'Regulation Code', 
                'Credit Value', 'L', 'T', 'P', 'Category'
            ]
            
            courses_to_create = []
            errors = []

            with transaction.atomic():
                for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
                    if not any(row): continue # Skip empty rows
                    
                    try:
                        # Unpack according to image attributes:
                        # 1.Name, 2.ShortName, 3.Code, 4.Type, 5.School, 6.Degree, 7.Dept, 8.Reg, 9.Credits, 10.L, 11.T, 12.P, 13.Cat
                        (name, short_name, code, c_type, s_code, d_code, dept_code, r_code, credit, l, t, p, cat) = row
                        
                        # Lookups
                        school = School.objects.get(school_code=s_code)
                        degree = Degree.objects.get(degree_code=d_code, school=school)
                        department = Department.objects.get(dept_code=dept_code, degree=degree)
                        
                        # Regulation lookup (since Batch is missing, find active regulation by code)
                        regulations = Regulation.objects.filter(regulation_code=r_code, degree=degree)
                        if regulations.filter(is_active=True).exists():
                             regulation = regulations.filter(is_active=True).first()
                        else:
                             regulation = regulations.first()

                        if not regulation:
                             errors.append(f"Row {row_idx}: Regulation {r_code} not found for degree {d_code}")
                             continue

                        course_data = {
                            'course_name': name,
                            'course_short_name': short_name,
                            'course_code': code,
                            'course_type': c_type.upper() if c_type else 'CORE',
                            'school': school,
                            'degree': degree,
                            'department': department,
                            'regulation': regulation,
                            'credit_value': credit,
                            'lecture_hours': l if l is not None else 0,
                            'tutorial_hours': t if t is not None else 0,
                            'practical_hours': p if p is not None else 0,
                            'course_category': cat.upper() if cat else 'THEORY',
                            'status': True
                        }
                        
                        if Course.objects.filter(course_code=code).exists():
                            errors.append(f"Row {row_idx}: Duplicate course code {code}")
                            continue

                        courses_to_create.append(Course(**course_data))
                    
                    except School.DoesNotExist: errors.append(f"Row {row_idx}: School {s_code} not found")
                    except Degree.DoesNotExist: errors.append(f"Row {row_idx}: Degree {d_code} not found")
                    except Department.DoesNotExist: errors.append(f"Row {row_idx}: Department {dept_code} not found")
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

from Creation.permissions import IsCollegeAdmin, IsAcademicCoordinator, IsCampusAdmin
from rest_framework.permissions import IsAuthenticated

class RegistrationWindowViewSet(viewsets.ModelViewSet):
    queryset = RegistrationWindow.objects.all()
    serializer_class = RegistrationWindowSerializer
    permission_classes = [IsAuthenticated, IsCampusAdmin] # Admin or Coordinator
    lookup_field = 'window_id'

class RegistrationMonitoringAPIView(APIView):
    permission_classes = [IsAuthenticated, IsCampusAdmin]

    def get(self, request, window_id):
        window = generics.get_object_or_404(RegistrationWindow, window_id=window_id)
        
        # 1. Total students in that Dept + Batch + Sem + Regulation
        all_students = Student.objects.filter(
            department=window.department,
            batch=window.batch,
            regulation=window.regulation,
            semester=window.semester,
            is_active=True
        )
        
        # 2. Registered students
        registered_selections = StudentSelection.objects.filter(window=window)
        registered_student_ids = registered_selections.values_list('student_id', flat=True)
        
        # 3. Categorization
        registered_students_list = all_students.filter(student_id__in=registered_student_ids)
        pending_students_list = all_students.exclude(student_id__in=registered_student_ids)
        
        # 4. Subject-wise counts
        subject_counts = []
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
                "total_students": all_students.count(),
                "registered_count": registered_students_list.count(),
                "pending_count": pending_students_list.count(),
                "subject_wise_counts": subject_counts
            },
            "registered_students": [
                {"id": s.student_id, "name": s.student_name, "roll_no": s.roll_no} for s in registered_students_list
            ],
            "pending_students": [
                {"id": s.student_id, "name": s.student_name, "roll_no": s.roll_no} for s in pending_students_list
            ]
        })

class ManualRegistrationAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAcademicCoordinator]

    def post(self, request):
        window_id = request.data.get('window_id')
        student_id = request.data.get('student_id')
        course_ids = request.data.get('course_ids', [])

        window = generics.get_object_or_404(RegistrationWindow, window_id=window_id)
        student = generics.get_object_or_404(Student, student_id=student_id)

        with transaction.atomic():
            selection, created = StudentSelection.objects.get_or_create(
                student=student,
                window=window
            )
            selection.courses.set(course_ids)
            selection.save()

        return Response({
            "message": f"Manual registration successful for {student.roll_no}",
            "selection_id": selection.selection_id
        }, status=status.HTTP_201_CREATED)

class ExtendRegistrationAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAcademicCoordinator]

    def post(self, request, window_id):
        new_end_date = request.data.get('end_datetime')
        if not new_end_date:
            return Response({"error": "end_datetime is required"}, status=400)

        window = generics.get_object_or_404(RegistrationWindow, window_id=window_id)
        window.end_datetime = new_end_date
        window.save()

        return Response({
            "message": "Registration window extended successfully",
            "new_end_datetime": window.end_datetime
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
