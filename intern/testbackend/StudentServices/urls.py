from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DocumentRequestHistoryView,
    StudentDocumentRequestView,
    AdminDocumentRequestListView,
    AdminDocumentRequestUpdateView,
    CourseRegistrationViewSet,
    StudentDashboardSummaryView,
    StudentAssignmentViewSet,
    StudentQuizViewSet,
    StudentResourceViewSet
)

router = DefaultRouter()
router.register(r'registration', CourseRegistrationViewSet, basename='student-registration')
router.register(r'assignments', StudentAssignmentViewSet, basename='student-assignments')
router.register(r'quizzes', StudentQuizViewSet, basename='student-quizzes')
router.register(r'resources', StudentResourceViewSet, basename='student-resources')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', StudentDashboardSummaryView.as_view(), name='student-dashboard'),
    path('requests/', StudentDocumentRequestView.as_view()),
    path('admin/requests/', AdminDocumentRequestListView.as_view()),
    path('admin/requests/<uuid:request_id>/', AdminDocumentRequestUpdateView.as_view()),
    path('requests/<uuid:request_id>/history/', DocumentRequestHistoryView.as_view()),
]
