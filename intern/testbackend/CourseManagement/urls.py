from django.urls import path
from .views import (
    AcademicClassAllocationAPIView,
    AcademicClassAllocationPreviewAPIView,
    DeptAdminRegistrationSummaryAPIView,
    DeptAdminUnregisteredStudentsAPIView,
    DeptAdminAssignCoursesAPIView,
    FacultyAllocationAPIView,
    FacultyAllocationListAPIView,
    TimetableCreateAPIView,
    TimetableListAPIView,
    
)

urlpatterns = [
    # Course Registration Management for Academic Coordinators
    path('registration/summary/', DeptAdminRegistrationSummaryAPIView.as_view(), name='registration-summary'),
    path('registration/unregistered/', DeptAdminUnregisteredStudentsAPIView.as_view(), name='unregistered-students'),
    path('registration/assign/', DeptAdminAssignCoursesAPIView.as_view(), name='assign-courses'),
    path('academic/class-allocation/', AcademicClassAllocationAPIView.as_view(),name='academic-class-allocation'),
    path('academic/class-allocation/preview/', AcademicClassAllocationPreviewAPIView.as_view(), name='academic-class-allocation-preview'),
    path('academic/faculty-allocation/', FacultyAllocationAPIView.as_view(),name='faculty-allocation'),
    path('academic/faculty-allocation/list/', FacultyAllocationListAPIView.as_view(),name='faculty-allocation-list'),
    path('academic/timetable/create/', TimetableCreateAPIView.as_view(),name='timetable-create'),
    path('academic/timetable/list/', TimetableListAPIView.as_view(), name='timetable-list'),
]
