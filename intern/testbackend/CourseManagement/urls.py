from django.urls import path
from .views import (
    DeptAdminRegistrationSummaryAPIView,
    DeptAdminUnregisteredStudentsAPIView,
    DeptAdminAssignCoursesAPIView
)

urlpatterns = [
    # Course Registration Management for Academic Coordinators
    path('registration/summary/', DeptAdminRegistrationSummaryAPIView.as_view(), name='registration-summary'),
    path('registration/unregistered/', DeptAdminUnregisteredStudentsAPIView.as_view(), name='unregistered-students'),
    path('registration/assign/', DeptAdminAssignCoursesAPIView.as_view(), name='assign-courses'),
]
