from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AcademicCalendarViewSet, CalendarTemplateView, TimeTableTemplateViewSet, SectionViewSet, CalendarEventViewSet

router = DefaultRouter()
router.register(r'calendars', AcademicCalendarViewSet, basename='academic-calendar')
router.register(r'timetable-templates', TimeTableTemplateViewSet, basename='timetable-template')
router.register(r'sections', SectionViewSet, basename='academic-section')
router.register(r'events', CalendarEventViewSet, basename='calendar-event')

urlpatterns = [
    path('template/', CalendarTemplateView.as_view(), name='calendar-template'),
    path('', include(router.urls)),
]
