from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    SchoolViewSet,
    DegreeView,
    DepartmentAPIView,
    SemesterAPIView,
    RegulationAPIView
)

# -------------------------------------------------
# Router for ViewSets (School)
# -------------------------------------------------
router = DefaultRouter()
router.register(r'schools', SchoolViewSet, basename='school')

# -------------------------------------------------
# URL Patterns
# -------------------------------------------------
urlpatterns = [
    # ---------------------------------------------
    # School APIs (ViewSet)
    # ---------------------------------------------
    path('', include(router.urls)),

    # ---------------------------------------------
    # Degree APIs (STRICTLY UNDER SCHOOL)
    # ---------------------------------------------
    path(
        'schools/<uuid:school_id>/degrees/',
        DegreeView.as_view(),                               #GET & POST
        name='degree-list-create'
    ),
    path(
        'schools/<uuid:school_id>/degrees/<uuid:degree_id>/',
        DegreeView.as_view(),                                       #PUT
        name='degree-update'
    ),

    # ---------------------------------------------
    # Department APIs
    # ---------------------------------------------
    path(
        'departments/',
        DepartmentAPIView.as_view(),
        name='department-list-create'
    ),
    path(
        'departments/<uuid:dept_id>/',
        DepartmentAPIView.as_view(),
        name='department-update'
    ),

    # ---------------------------------------------
    # Semester APIs (READ-ONLY ENTITY)
    # ---------------------------------------------
    path(
        'semesters/',
        SemesterAPIView.as_view(),
        name='semester-list'
    ),
    path(
        'semesters/<uuid:sem_id>/',
        SemesterAPIView.as_view(),
        name='semester-update'
    ),

    # ---------------------------------------------
    # Regulation APIs
    # ---------------------------------------------
    path(
        'regulations/',
        RegulationAPIView.as_view(),
        name='regulation-list-create'
    ),
    path(
        'regulations/<uuid:regulation_id>/',
        RegulationAPIView.as_view(),
        name='regulation-update'
    ),
]
