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
    FacultySearchView,
    RolesSummaryView,
    RolesListView,
    DepartmentAdminAssignmentViewSet,
    DashboardStatsView,
    FacultyTemplateDownloadAPIView,
    FacultyFilterAPIView,
    StudentExcelTemplateDownloadAPIView,
    StudentFilterAPIView
)

router = DefaultRouter()
router.register(r'faculty', FacultyViewSet, basename='faculty')
router.register(r'dept-admin', DepartmentAdminAssignmentViewSet, basename='dept-admin')

urlpatterns = [

    #Student creation
    path(
        "students/",
        StudentListAPIView.as_view(),
        name="student-list",
    ),
    #Download student template
    path(
        "students/template/download/",
        StudentExcelTemplateDownloadAPIView.as_view(),
        name="student-excel-template-download",
    ),

    #  Bulk upload via Excel
    path(
        "students/upload-excel/",
        StudentExcelUploadAPIView.as_view(),
        name="student-excel-upload",
    ),
    #filtering for students
    path(
        "students/filter/",
        StudentFilterAPIView.as_view(),
        name="student-filter",
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
    path(
        "faculty/template/",
        FacultyTemplateDownloadAPIView.as_view(),
        name="faculty-template-download",
    ),

    path(
        "faculty/filter/",
        FacultyFilterAPIView.as_view(),
        name="faculty-filter",
    ),



     # Department Admin Assignment - Cascading filter endpoints
    # These endpoints enable the School -> Degree -> Department cascading selection
    path('dept-admin/degrees-for-school/', DegreesForSchoolView.as_view(), name='degrees-for-school'),
    path('dept-admin/departments-for-degree/', DepartmentsForDegreeView.as_view(), name='departments-for-degree'),
    path('dept-admin/search-faculty/', FacultySearchView.as_view(), name='search-faculty'),
    
    # Roles Dashboard (Feature 4)
    path('roles/summary/', RolesSummaryView.as_view(), name='roles-summary'),
    path('roles/list/', RolesListView.as_view(), name='roles-list'),

    # Dashboard Stats
    path('dashboard/stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
    
    # ROUTER (KEEP THIS LAST)
    path('', include(router.urls)),

]

