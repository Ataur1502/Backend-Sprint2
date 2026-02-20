from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .models import AcademicCalendar
from .serializers import AcademicCalendarSerializer
from Creation.permissions import IsCollegeAdmin

class AcademicCalendarViewSet(viewsets.ModelViewSet):
    """
    Handles the Academic Calendar operations:
    - List available calendars with optional school filtering
    - Create a new calendar from an Excel upload
    - Remove calendars and their associated events
    """
    queryset = AcademicCalendar.objects.all().order_by('-created_at')
    serializer_class = AcademicCalendarSerializer
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    permission_classes = [IsCollegeAdmin]
    lookup_field = 'calendar_id'

    def get_queryset(self):
        # Optional filtering by school/degree/regulation
        queryset = super().get_queryset()
        school_id = self.request.query_params.get('school_id')
        if school_id:
            queryset = queryset.filter(school_id=school_id)
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return Response({
                "message": "Academic Calendar created successfully",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

from django.http import HttpResponse
from rest_framework.views import APIView
from io import BytesIO
import openpyxl

class CalendarTemplateView(APIView):
    """
    Returns a standard Excel template for Academic Calendar creation.
    """
    authentication_classes = []
    permission_classes = []
    
    def get(self, request):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Calendar Template"
        
        # Headers
        headers = ['Type (Instruction/Holiday/Exam)', 'Name', 'Start Date (YYYY-MM-DD)', 'End Date (YYYY-MM-DD)', 'Description']
        ws.append(headers)
        
        # Sample data
        ws.append(['Instruction', 'Odd Semester Classes', '2025-08-01', '2025-11-30', 'Regular instruction period'])
        ws.append(['Holiday', 'Independence Day', '2025-08-15', '2025-08-15', 'National holiday'])
        ws.append(['Exam', 'End Semester Exams', '2025-12-05', '2025-12-25', 'Final examinations'])
        
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        
        response = HttpResponse(
            buffer.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename=Academic_Calendar_Template.xlsx'
        return response

from .models import TimeTableTemplate
from .serializers import TimeTableTemplateSerializer

class TimeTableTemplateViewSet(viewsets.ModelViewSet):
    """
    Manages reusable Time Table Templates which act as blueprints for actual schedules.
    """
    queryset = TimeTableTemplate.objects.all().order_by('-created_at')
    serializer_class = TimeTableTemplateSerializer
    permission_classes = [IsCollegeAdmin]
    lookup_field = 'template_id'

    def get_queryset(self):
        queryset = super().get_queryset()
        department_id = self.request.query_params.get('department_id')
        if department_id:
            queryset = queryset.filter(department_id=department_id)
        return queryset

from .models import Section
from .serializers import SectionSerializer

class SectionViewSet(viewsets.ModelViewSet):
    """
    Manages user-created sections (e.g. A, B, Section 1).
    Ensures uniqueness per academic context via serializer validation.
    """
    queryset = Section.objects.all().order_by('name')
    serializer_class = SectionSerializer
    permission_classes = [IsCollegeAdmin]
    lookup_field = 'section_id'

    def get_queryset(self):
        queryset = super().get_queryset()
        # Optional filters for dropdowns/management
        department_id = self.request.query_params.get('department_id')
        semester_id = self.request.query_params.get('semester_id')
        batch = self.request.query_params.get('batch')

        if department_id:
            queryset = queryset.filter(department_id=department_id)
        if semester_id:
            queryset = queryset.filter(semester_id=semester_id)
        if batch:
            queryset = queryset.filter(batch=batch)
            
        return queryset

from .models import CalendarEvent
from .serializers import CalendarEventSerializer

class CalendarEventViewSet(viewsets.ModelViewSet):
    """
    Manages individual calendar events (Holidays, Exams, Instructions).
    Used for the interactive "Holidays" tab.
    """
    queryset = CalendarEvent.objects.all().order_by('start_date')
    serializer_class = CalendarEventSerializer
    permission_classes = [IsCollegeAdmin]
    lookup_field = 'event_id'

    def get_queryset(self):
        queryset = super().get_queryset()
        calendar_id = self.request.query_params.get('calendar_id')
        if calendar_id:
            queryset = queryset.filter(calendar_id=calendar_id)
        return queryset
