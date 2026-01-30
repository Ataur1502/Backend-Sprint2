from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    FacultyViewSet,
    FacultyMappingOptionsView,
    FacultyBulkUploadAPIView,
    StudentExcelUploadAPIView,
    StudentListAPIView,
    StudentDetailAPIView,
    DegreesForSchoolView,
    DepartmentsForDegreeView,
    FacultySearchView


)

router = DefaultRouter()
router.register(r'faculty', FacultyViewSet, basename='faculty')

urlpatterns = [

    #Student creation
    path(
        "students/",
        StudentListAPIView.as_view(),
        name="student-list",
    ),

    #  Bulk upload via Excel
    path(
        "students/upload-excel/",
        StudentExcelUploadAPIView.as_view(),
        name="student-excel-upload",
    ),

    #  Individual GET / PATCH
    path(
        "students/<str:roll_no>/",
        StudentDetailAPIView.as_view(),
        name="student-detail",
    ),

                                #Faculty creation
    #  BULK UPLOAD (MUST COME FIRST)
    path(
        'faculty/upload-bulk/',
        FacultyBulkUploadAPIView.as_view(),
        name='faculty-upload-bulk'
    ),

    #  FACULTY MAPPING OPTIONS
    path(
        'faculty/mapping-options/',
        FacultyMappingOptionsView.as_view(),
        name='faculty-mapping-options'
    ),



     # Department Admin Assignment - Cascading filter endpoints
    # These endpoints enable the School -> Degree -> Department cascading selection
    path('dept-admin/degrees-for-school/', DegreesForSchoolView.as_view(), name='degrees-for-school'),
    path('dept-admin/departments-for-degree/', DepartmentsForDegreeView.as_view(), name='departments-for-degree'),
    path('dept-admin/search-faculty/', FacultySearchView.as_view(), name='search-faculty'),
    
    # ROUTER (KEEP THIS LAST)
    path('', include(router.urls)),

]

    


    

