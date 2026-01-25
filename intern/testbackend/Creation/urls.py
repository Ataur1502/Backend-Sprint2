from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SchoolViewSet, DegreeView, DepartmentAPIView, SemesterAPIView, RegulationAPIView

# ----------------------------
# Router for ViewSets
# ----------------------------
router = DefaultRouter()
router.register(r'schools', SchoolViewSet, basename='school')

# ----------------------------
# URL patterns
# ----------------------------
urlpatterns = [
    # School CRUD (ViewSet)
    path('', include(router.urls)),

    # Degree APIs (APIView)
    path('degrees/', DegreeView.as_view(), name='degree-standalone'), # Added for direct access
    path('degrees/<uuid:degree_id>/', DegreeView.as_view(), name='degree-put-standalone'), # Added for direct access
    path('schools/<uuid:school_id>/degrees/', DegreeView.as_view(), name='degree-get-post'),
    path('schools/<uuid:school_id>/degrees/<uuid:degree_id>/', DegreeView.as_view(), name='degree-put'),

    # Dept creation API's
    path('departments/', DepartmentAPIView.as_view()),               # GET, POST
    path('departments/<uuid:dept_id>/', DepartmentAPIView.as_view()), # PUT

    # Semester creation API's
    path('semesters/', SemesterAPIView.as_view()),               # GET, POST
    path('semesters/<uuid:sem_id>/', SemesterAPIView.as_view()), # PUT

    # Regulation creation API's
    path('regulations/', RegulationAPIView.as_view(), name='regulation-list-create'),
    path('regulations/<uuid:regulation_id>/', RegulationAPIView.as_view(), name='regulation-detail'),
]
