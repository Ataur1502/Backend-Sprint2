from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AcademicCalendarViewSet, CalendarTemplateView, TimeTableTemplateViewSet

router = DefaultRouter()
router.register(r'calendars', AcademicCalendarViewSet, basename='academic-calendar')
router.register(r'timetable-templates', TimeTableTemplateViewSet, basename='timetable-template')

urlpatterns = [
    path('template/', CalendarTemplateView.as_view(), name='calendar-template'),
    path('', include(router.urls)),
]
