from django.urls import path, include
from .views import (
    CourseListCreateAPIView,
    CourseRetrieveUpdateDestroyAPIView,
    CourseBulkUploadAPIView,
    RegistrationWindowViewSet,
    RegistrationMonitoringAPIView,
    StudentCourseRegistrationAPIView
)
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'windows', RegistrationWindowViewSet, basename='registration-window')

urlpatterns = [
    path('courses/', CourseListCreateAPIView.as_view(), name='course-list-create'),
    path('courses/<uuid:course_id>/', CourseRetrieveUpdateDestroyAPIView.as_view(), name='course-detail'),
    path('courses/upload/', CourseBulkUploadAPIView.as_view(), name='course-bulk-upload'),
    
    # Registration Windows
    path('', include(router.urls)),
    path('windows/<uuid:window_id>/monitor/', RegistrationMonitoringAPIView.as_view(), name='registration-monitor'),
    
    # Student specific
    path('student/registration/', StudentCourseRegistrationAPIView.as_view(), name='student-registration'),
]
