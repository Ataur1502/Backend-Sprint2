from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status, viewsets
from django.utils import timezone
from django.db import transaction

from .models import (
    DocumentRequest, DocumentRequestHistory
)
from faculty.models import (
    Assignment, StudentSubmission, Quiz, Question, Option, 
    StudentQuizAttempt, StudentAnswer, Resource, StudentAttendance
)
from CourseManagement.models import AcademicClassStudent, FacultyAllocation
from CourseConfiguration.models import Course, RegistrationWindow, StudentSelection
from CourseConfiguration.serializers import RegistrationWindowSerializer, StudentSelectionSerializer

from .serializers import (
    DocumentRequestSerializer,
    DocumentStatusUpdateSerializer,
    DocumentRequestHistorySerializer,
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

class CourseRegistrationViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = StudentSelectionSerializer

    def get_queryset(self):
        if hasattr(self.request.user, 'student_profile'):
            return StudentSelection.objects.filter(student=self.request.user.student_profile)
        return StudentSelection.objects.none()

    @action(detail=False, methods=['get'])
    def available_courses(self, request):
        """
        Redirects to the improved StudentCourseRegistrationAPIView in CourseConfiguration
        or replicates logic here using RegistrationWindow.
        """
        if not hasattr(request.user, 'student_profile'):
            return Response({"detail": "Only students can access registration"}, status=403)
        
        student = request.user.student_profile
        
        # 1. Find active window for this student
        window = RegistrationWindow.objects.filter(
            department=student.department,
            batch=student.batch,
            is_active=True,
            status='ACTIVE',
            start_datetime__lte=timezone.now(),
            end_datetime__gte=timezone.now()
        ).first()
        
        if not window:
            return Response({"detail": "No active registration window found for your semester/regulation."}, status=404)
        
        # 2. Fetch courses from the window
        return Response({
            "window": RegistrationWindowSerializer(window).data,
            "major_subjects": CourseSerializer(window.major_subjects.all(), many=True).data,
            "elective_subjects": CourseSerializer(window.elective_subjects.all(), many=True).data,
        })

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
        current_reg = StudentSelection.objects.filter(student=student).order_by('-submitted_at').first()
        
        # 2. Document Requests (Recent 3)
        recent_docs = DocumentRequest.objects.filter(student=student).order_by('-created_at')[:3]
        
        # 3. Attendance Summary
        attendance_records = StudentAttendance.objects.filter(student=student)
        total_sessions = attendance_records.count()
        attended_sessions = attendance_records.filter(status='PRESENT').count()
        overall_percentage = (attended_sessions / total_sessions * 100) if total_sessions > 0 else 0
        
        attendance_summary = {
            "overall_percentage": round(overall_percentage, 2),
            "classes_attended": attended_sessions,
            "total_classes": total_sessions
        }
        
        # 4. Academic Info
        academic_info = {
            "regulation": student.regulation.regulation_code,
            "semester": student.semester.sem_number,
            "department": student.department.dept_name,
            "section": student.section.name if hasattr(student, 'section') and student.section else "A"
        }

        # 5. Upcoming Tasks (Quiz/Assignments)
        class_ids = AcademicClassStudent.objects.filter(student=student).values_list('academic_class_id', flat=True)
        
        # Get pending assignments
        pending_assignments = Assignment.objects.filter(
            academic_class_id__in=class_ids,
            end_datetime__gt=timezone.now()
        ).order_by('end_datetime')[:5]
        
        # Get active quizzes
        active_quizzes = Quiz.objects.filter(
            academic_class_id__in=class_ids,
            is_published=True,
            access_end_datetime__gt=timezone.now()
        ).order_by('access_end_datetime')[:5]

        upcoming_tasks = []
        for a in pending_assignments:
            upcoming_tasks.append({
                "type": "Assignment",
                "title": a.title,
                "date": a.end_datetime.strftime("%Y-%m-%d"),
                "status": "PENDING"
            })
        for q in active_quizzes:
            upcoming_tasks.append({
                "type": "Quiz",
                "title": q.title,
                "date": q.access_end_datetime.strftime("%Y-%m-%d"),
                "status": "AVAILABLE"
            })

        return Response({
            "student_name": student.student_name,
            "roll_no": student.roll_no,
            "academic_info": academic_info,
            "registration": StudentSelectionSerializer(current_reg).data if current_reg else None,
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
            student=request.user,
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
            student=request.user,
            defaults={
                'calculated_end_time': now + timezone.timedelta(minutes=quiz.quiz_time)
            }
        )
        return Response(StudentQuizAttemptSerializer(attempt).data)

    @action(detail=True, methods=['post'])
    def submit_answer(self, request, pk=None):
        quiz = self.get_object()
        attempt = StudentQuizAttempt.objects.get(quiz=quiz, student=request.user)
        
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
        attempt = StudentQuizAttempt.objects.get(quiz=quiz, student=request.user)
        
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
