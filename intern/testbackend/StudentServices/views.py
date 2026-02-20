from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status, viewsets
from django.utils import timezone
from django.db import transaction

from .models import (
    DocumentRequest, DocumentRequestHistory,
    CourseRegistrationWindow, CourseRegistration, CourseRegistrationItem,
    Assignment, StudentSubmission, Quiz, Question, Option, 
    StudentQuizAttempt, StudentAnswer, Resource
)
from .serializers import (
    DocumentRequestSerializer,
    DocumentStatusUpdateSerializer,
    DocumentRequestHistorySerializer,
    CourseRegistrationWindowSerializer,
    CourseRegistrationSerializer,
    AssignmentSerializer,
    StudentSubmissionSerializer,
    QuizSerializer,
    QuestionSerializer,
    StudentQuizAttemptSerializer,
    StudentAnswerSerializer,
    ResourceSerializer
)
from Creation.permissions import IsCollegeAdmin, IsAcademicCoordinator

# =====================================================
# STUDENT DOCUMENT REQUEST VIEWS
# =====================================================

class StudentDocumentRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DocumentRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Ensure student profile exists
        if not hasattr(request.user, 'student_profile'):
            return Response({"detail": "Only students can request documents"}, status=403)

        doc_request = serializer.save(student=request.user.student_profile)

        DocumentRequestHistory.objects.create(
            request=doc_request,
            status='SUBMITTED',
            updated_by=request.user
        )

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def get(self, request):
        if not hasattr(request.user, 'student_profile'):
            return Response({"detail": "Only students can view their requests"}, status=403)
            
        qs = DocumentRequest.objects.filter(student=request.user.student_profile)
        serializer = DocumentRequestSerializer(qs, many=True)
        return Response(serializer.data)

class AdminDocumentRequestListView(APIView):
    permission_classes = [IsAuthenticated, IsCollegeAdmin]

    def get(self, request):
        qs = DocumentRequest.objects.all().order_by('-created_at')
        serializer = DocumentRequestSerializer(qs, many=True)
        return Response(serializer.data)

class AdminDocumentRequestUpdateView(APIView):
    permission_classes = [IsAuthenticated, IsCollegeAdmin]

    def patch(self, request, request_id):
        try:
            doc_request = DocumentRequest.objects.get(request_id=request_id)
        except DocumentRequest.DoesNotExist:
            return Response({"detail": "Request not found"}, status=404)

        serializer = DocumentStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        doc_request.status = serializer.validated_data['status']
        doc_request.save()

        DocumentRequestHistory.objects.create(
            request=doc_request,
            status=doc_request.status,
            remark=serializer.validated_data.get('remark'),
            updated_by=request.user
        )

        return Response(
            {"message": "Request status updated"},
            status=status.HTTP_200_OK
        )

class DocumentRequestHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, request_id):
        try:
            doc_request = DocumentRequest.objects.get(request_id=request_id)
        except DocumentRequest.DoesNotExist:
            return Response({"detail": "Request not found"}, status=404)

        # Students can only see their own requests
        if request.user.role == 'STUDENT':
            if not hasattr(request.user, 'student_profile') or doc_request.student != request.user.student_profile:
                return Response({"detail": "Not authorized"}, status=403)

        history = doc_request.history.order_by('updated_at')
        serializer = DocumentRequestHistorySerializer(history, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


from rest_framework.decorators import action
from CourseConfiguration.models import Course, RegistrationWindow
from CourseConfiguration.serializers import CourseSerializer

# =====================================================
# COURSE REGISTRATION VIEWS
# =====================================================

class CourseRegistrationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CourseRegistrationSerializer

    def get_queryset(self):
        if hasattr(self.request.user, 'student_profile'):
            return CourseRegistration.objects.filter(student=self.request.user.student_profile)
        return CourseRegistration.objects.none()

    @action(detail=False, methods=['get'])
    def available_courses(self, request):
        """
        Returns courses available for registration in the active window.
        - Mandatory courses from the student's regulation/semester.
        - Electives defined in the active RegistrationWindow.
        """
        if not hasattr(request.user, 'student_profile'):
            return Response({"detail": "Only students can access registration"}, status=403)
        
        student = request.user.student_profile
        
        # 1. Find active window
        window = CourseRegistrationWindow.objects.filter(
            regulation=student.regulation,
            semester=student.semester,
            is_active=True,
            start_datetime__lte=timezone.now(),
            end_datetime__gte=timezone.now()
        ).first()
        
        if not window:
            return Response({"detail": "No active registration window found for your semester/regulation."}, status=404)
        
        # 2. Fetch Mandatory Courses for this semester/regulation
        mandatory_courses = Course.objects.filter(
            regulation=student.regulation,
            semester=student.semester, # This assumes Semester is linked to Course or we filter by regulation
            course_type='CORE'
        )
        
        # 3. Fetch Electives (from the Window or general pool)
        # Note: If CourseConfiguration.RegistrationWindow is used, we might need to sync or cross-reference.
        # For now, we'll fetch based on Course model.
        elective_courses = Course.objects.filter(
            regulation=student.regulation,
            course_type__in=['ELECTIVE', 'OPEN_ELECTIVE']
        )

        return Response({
            "window": CourseRegistrationWindowSerializer(window).data,
            "mandatory_courses": CourseSerializer(mandatory_courses, many=True).data,
            "elective_courses": CourseSerializer(elective_courses, many=True).data,
        })

    def create(self, request, *args, **kwargs):
        """
        Submit course registration.
        Expects: { "semester": uuid, "academic_year": "2025-26", "course_ids": [uuid, ...] }
        """
        if not hasattr(request.user, 'student_profile'):
            return Response({"detail": "Not authorized"}, status=403)
            
        student = request.user.student_profile
        course_ids = request.data.get('course_ids', [])
        
        # Check if already registered/locked
        existing = CourseRegistration.objects.filter(
            student=student, 
            semester_id=request.data.get('semester'), 
            academic_year=request.data.get('academic_year')
        ).first()
        
        if existing and existing.is_locked:
            return Response({"detail": "Registration is already locked and cannot be modified."}, status=400)

        with transaction.atomic():
            registration, created = CourseRegistration.objects.get_or_create(
                student=student,
                semester_id=request.data.get('semester'),
                academic_year=request.data.get('academic_year'),
                defaults={'status': 'DRAFT'}
            )
            
            # Clear existing items if updating
            registration.items.all().delete()
            
            total_credits = 0
            for cid in course_ids:
                course = Course.objects.get(course_id=cid)
                CourseRegistrationItem.objects.create(
                    registration=registration,
                    course=course,
                    is_mandatory=(course.course_type == 'CORE')
                )
                total_credits += course.credit_value
                
            registration.total_credits = total_credits
            registration.save()
            
        return Response(CourseRegistrationSerializer(registration).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def lock(self, request, pk=None):
        registration = self.get_object()
        registration.is_locked = True
        registration.status = 'REGISTERED'
        registration.submitted_at = timezone.now()
        registration.save()
        return Response({"status": "locked"})

# =====================================================
# STUDENT PORTAL / DASHBOARD VIEWS
# =====================================================

class StudentDashboardSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not hasattr(request.user, 'student_profile'):
            return Response({"detail": "Not a student"}, status=403)
            
        student = request.user.student_profile
        
        # 1. Registration Status
        current_reg = CourseRegistration.objects.filter(student=student).order_by('-created_at').first()
        
        # 2. Document Requests (Recent 3)
        recent_docs = DocumentRequest.objects.filter(student=student).order_by('-created_at')[:3]
        
        # 3. Attendance Summary (Aggregated from CourseManagement - PLACEHOLDER)
        # In a real scenario, we'd query Attendace records per course
        attendance_summary = {
            "overall_percentage": 85.5,
            "classes_attended": 120,
            "total_classes": 140
        }
        
        # 4. Academic Info
        academic_info = {
            "regulation": student.regulation.regulation_code,
            "semester": student.semester.sem_number,
            "department": student.department.dept_name,
            "section": student.section if hasattr(student, 'section') else "A"
        }

        # 5. External Integration Placeholders (Quiz/Assignments)
        # These will be populated once the Faculty app code is integrated.
        upcoming_tasks = [
            {"type": "Quiz", "title": "Data Structures - Mid Quiz", "date": "2025-03-10", "status": "PENDING"},
            {"type": "Assignment", "title": "Python Basics - HW1", "date": "2025-03-05", "status": "SUBMITTED"}
        ]

        return Response({
            "student_name": student.student_name,
            "roll_no": student.roll_no,
            "academic_info": academic_info,
            "registration": CourseRegistrationSerializer(current_reg).data if current_reg else None,
            "recent_document_requests": DocumentRequestSerializer(recent_docs, many=True).data,
            "attendance": attendance_summary,
            "upcoming_tasks": upcoming_tasks
        })


# =====================================================
# ASSIGNMENT VIEWS
# =====================================================

class StudentAssignmentViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = AssignmentSerializer

    def get_queryset(self):
        if hasattr(self.request.user, 'student_profile'):
            student = self.request.user.student_profile
            from CourseManagement.models import AcademicClassStudent
            class_ids = AcademicClassStudent.objects.filter(student=student).values_list('academic_class_id', flat=True)
            return Assignment.objects.filter(academic_class_id__in=class_ids)
        return Assignment.objects.none()

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        assignment = self.get_object()
        student = request.user.student_profile
        
        file = request.FILES.get('file')
        if not file:
            return Response({"detail": "File is required"}, status=400)
            
        submission, created = StudentSubmission.objects.get_or_create(
            assignment=assignment,
            student=student,
            defaults={'file': file}
        )
        if not created:
            submission.file = file
            submission.submitted_at = timezone.now()
            submission.save()
            
        return Response(StudentSubmissionSerializer(submission).data)


# =====================================================
# QUIZ VIEWS
# =====================================================

class StudentQuizViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = QuizSerializer

    def get_queryset(self):
        if hasattr(self.request.user, 'student_profile'):
            student = self.request.user.student_profile
            from CourseManagement.models import AcademicClassStudent
            class_ids = AcademicClassStudent.objects.filter(student=student).values_list('academic_class_id', flat=True)
            return Quiz.objects.filter(academic_class_id__in=class_ids, is_published=True)
        return Quiz.objects.none()

    @action(detail=True, methods=['get'])
    def questions(self, request, pk=None):
        quiz = self.get_object()
        student = request.user.student_profile
        
        attempt = StudentQuizAttempt.objects.filter(quiz=quiz, student=student).first()
        if not attempt:
            return Response({"detail": "You must start the attempt first."}, status=400)
            
        if attempt.is_submitted:
            return Response({"detail": "Quiz already submitted."}, status=400)
            
        questions = quiz.questions.all().order_by('order')
        return Response(QuestionSerializer(questions, many=True).data)

    @action(detail=True, methods=['post'])
    def start_attempt(self, request, pk=None):
        quiz = self.get_object()
        student = request.user.student_profile
        
        now = timezone.now()
        if now < quiz.access_start_datetime or now > quiz.access_end_datetime:
            return Response({"detail": "Quiz is not accessible at this time."}, status=400)
            
        attempt, created = StudentQuizAttempt.objects.get_or_create(
            quiz=quiz,
            student=student,
            defaults={
                'calculated_end_time': now + timezone.timedelta(minutes=quiz.quiz_time)
            }
        )
        return Response(StudentQuizAttemptSerializer(attempt).data)

    @action(detail=True, methods=['post'])
    def submit_answer(self, request, pk=None):
        quiz = self.get_object()
        student = request.user.student_profile
        attempt = StudentQuizAttempt.objects.get(quiz=quiz, student=student)
        
        if attempt.is_submitted:
            return Response({"detail": "Already submitted"}, status=400)
            
        question_id = request.data.get('question_id')
        option_ids = request.data.get('option_ids', [])
        text_answer = request.data.get('text_answer', '')
        
        answer, created = StudentAnswer.objects.get_or_create(
            attempt=attempt,
            question_id=question_id
        )
        if option_ids:
            answer.selected_options.set(option_ids)
        if text_answer:
            answer.text_answer = text_answer
        answer.save()
        
        return Response({"status": "answer saved"})

    @action(detail=True, methods=['post'])
    def finalize(self, request, pk=None):
        quiz = self.get_object()
        student = request.user.student_profile
        attempt = StudentQuizAttempt.objects.get(quiz=quiz, student=student)
        
        if attempt.is_submitted:
            return Response({"detail": "Already submitted"}, status=400)
            
        attempt.is_submitted = True
        attempt.submitted_at = timezone.now()
        attempt.save()
        return Response({"status": "quiz submitted"})


# =====================================================
# RESOURCE VIEWS
# =====================================================

class StudentResourceViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ResourceSerializer

    def get_queryset(self):
        if hasattr(self.request.user, 'student_profile'):
            student = self.request.user.student_profile
            from CourseManagement.models import AcademicClassStudent
            class_ids = AcademicClassStudent.objects.filter(student=student).values_list('academic_class_id', flat=True)
            return Resource.objects.filter(academic_class_id__in=class_ids, is_active=True)
        return Resource.objects.none()
