from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    FacultyViewSet, 
    FacultyMappingOptionsView,
    DepartmentAdminAssignmentViewSet,
    DegreesForSchoolView,
    DepartmentsForDegreeView,
    FacultySearchView
)

router = DefaultRouter()
router.register(r'faculty', FacultyViewSet, basename='faculty')

# Department Admin Assignment routes
router.register(r'dept-admin', DepartmentAdminAssignmentViewSet, basename='dept-admin-assignment')

urlpatterns = [
    # Faculty mapping options for multi-select dropdown
    path('faculty/mapping-options/', FacultyMappingOptionsView.as_view(), name='faculty-mapping-options'),
    
    # Department Admin Assignment - Cascading filter endpoints
    # These endpoints enable the School -> Degree -> Department cascading selection
    path('dept-admin/degrees-for-school/', DegreesForSchoolView.as_view(), name='degrees-for-school'),
    path('dept-admin/departments-for-degree/', DepartmentsForDegreeView.as_view(), name='departments-for-degree'),
    path('dept-admin/search-faculty/', FacultySearchView.as_view(), name='search-faculty'),
    
    # Include router URLs (includes CRUD for faculty and dept-admin)
    path('', include(router.urls)),
]
