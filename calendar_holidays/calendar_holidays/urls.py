from django.urls import path
from .views import CalendarAPIView, HolidayAPIView

urlpatterns = [
    path('calendars/', CalendarAPIView.as_view()),
    path('holidays/', HolidayAPIView.as_view()),
]
