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
    BulkImportTemplateView,
    BulkImportUploadView,
    AcademicClassListAPIView,
    VirtualSectionCreateAPIView,
    VirtualSectionListAPIView,
)

urlpatterns = [
    # Course Registration Management for Academic Coordinators
    path('registration/summary/', DeptAdminRegistrationSummaryAPIView.as_view(), name='registration-summary'),
    path('registration/unregistered/', DeptAdminUnregisteredStudentsAPIView.as_view(), name='unregistered-students'),
    path('registration/assign/', DeptAdminAssignCoursesAPIView.as_view(), name='assign-courses'),
    path('academic/class-allocation/', AcademicClassAllocationAPIView.as_view(),name='academic-class-allocation'),
    path('academic/class-allocation/list/', AcademicClassListAPIView.as_view(), name='academic-class-list'),
    path('academic/class-allocation/preview/', AcademicClassAllocationPreviewAPIView.as_view(), name='academic-class-allocation-preview'),
    path('academic/virtual-section/create/', VirtualSectionCreateAPIView.as_view(), name='virtual-section-create'),
    path('academic/virtual-section/list/', VirtualSectionListAPIView.as_view(), name='virtual-section-list'),
    path('academic/faculty-allocation/', FacultyAllocationAPIView.as_view(),name='faculty-allocation'),
    path('academic/faculty-allocation/list/', FacultyAllocationListAPIView.as_view(),name='faculty-allocation-list'),
    path('academic/timetable/create/', TimetableCreateAPIView.as_view(),name='timetable-create'),
    path('academic/timetable/list/', TimetableListAPIView.as_view(), name='timetable-list'),
    
    # Bulk Import (Course Only)
    path('import/template/<str:entity_type>/', BulkImportTemplateView.as_view(), name='bulk-import-template'),
    path('import/upload/<str:entity_type>/', BulkImportUploadView.as_view(), name='bulk-import-upload'),
]
