from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import(
    LecturePlanViewSet,
    LectureSessionViewSet,
    LecturePlanTemplateView,
    AttendanceViewSet,
    StudentAttendanceViewSet,
    SubmitAttendanceAPIView,
    OverrideAttendanceAPIView,
    GrantOverrideAPIView,
    GenerateLectureSessionsAPIView,
    LecturePlanReportAPIView,
    LecturePlanProgressAPIView,
    AssignmentAPIView,
    FacultySubmissionAPIView,
    QuizCreateAPIView,
    QuizUpdateAPIView,
    PublishQuizAPIView,
    QuizDetailAPIView,
    AddQuestionAPIView,
    AddOptionAPIView,
    ResourceCreateAPIView,
    ResourceUpdateAPIView,
    ResourceDeleteAPIView,
    ResourceListAPIView
)

router = DefaultRouter()

# Lecture Plan
router.register(r'lecture-plans', LecturePlanViewSet, basename='lecture-plan')
router.register(r'lecture-sessions', LectureSessionViewSet, basename='lecture-session')


# Attendance
router.register(r'attendance', AttendanceViewSet, basename='attendance')
router.register(r'student-attendance', StudentAttendanceViewSet, basename='student-attendance')


urlpatterns = [
    #Lecture plan
    path("lecture-plans/template/", LecturePlanTemplateView.as_view(), name="lecture-plan-template"),
    path("lecture-plans/progress/", LecturePlanProgressAPIView.as_view()),
    path("lecture-plans/report/", LecturePlanReportAPIView.as_view()),
    path("generate-sessions/", GenerateLectureSessionsAPIView.as_view()),
    #Attendance
    path("attendance/submit/", SubmitAttendanceAPIView.as_view()),
    path("attendance/override/", OverrideAttendanceAPIView.as_view()),
    path("attendance/grant-override/", GrantOverrideAPIView.as_view()),
    path("assignments/", AssignmentAPIView.as_view()),
    path("assignments/<uuid:pk>/", AssignmentAPIView.as_view()),
    path("assignments/<uuid:assignment_id>/submissions/",FacultySubmissionAPIView.as_view()),
    #Quiz
    path("create/", QuizCreateAPIView.as_view()),
    path("<uuid:quiz_id>/update/", QuizUpdateAPIView.as_view()),
    path("<uuid:quiz_id>/publish/", PublishQuizAPIView.as_view()),
    path("<uuid:quiz_id>/detail/", QuizDetailAPIView.as_view()),
    path("add-question/", AddQuestionAPIView.as_view()),
    path("add-option/", AddOptionAPIView.as_view()),
    #Resources
    path("create/", ResourceCreateAPIView.as_view()),
    path("<uuid:resource_id>/update/", ResourceUpdateAPIView.as_view()),
    path("<uuid:resource_id>/delete/", ResourceDeleteAPIView.as_view()),
    path("list/", ResourceListAPIView.as_view()),

    path('', include(router.urls)),
]
