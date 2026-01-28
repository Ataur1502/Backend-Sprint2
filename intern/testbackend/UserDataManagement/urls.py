from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FacultyViewSet, FacultyMappingOptionsView

router = DefaultRouter()
router.register(r'faculty', FacultyViewSet, basename='faculty')

urlpatterns = [
    path('faculty/mapping-options/', FacultyMappingOptionsView.as_view(), name='faculty-mapping-options'),
    path('', include(router.urls)),
]
