from AcademicSetup.models import AcademicCalendar, CalendarEvent
from django.db.models import Q
from datetime import timedelta
from faculty.models import LectureSession
from CourseManagement.models import FacultyAllocation

from CourseManagement.models import Timetable


def generate_sessions(allocation: FacultyAllocation):

    academic_class = allocation.academic_class
    subject = allocation.subject
    section = allocation.section

    start_date = academic_class.start_date
    end_date = academic_class.end_date

    # Get excluded dates
    holiday_dates = set(
        CalendarEvent.objects.filter(event_type="HOLIDAY")
        .values_list("date", flat=True)
    )

    exam_dates = set(
        CalendarEvent.objects.filter(event_type="EXAM")
        .values_list("date", flat=True)
    )


    # Get valid timetable days (e.g., Monday, Wednesday)
    timetable_days = Timetable.objects.filter(
        subject=subject,
        section=section,
        academic_class=academic_class
    ).values_list("day", flat=True)

    current = start_date
    session_no = 1

    while current <= end_date:

        if (
            current not in holiday_dates and
            current not in exam_dates and
            current.strftime("%A") in timetable_days
        ):
            LectureSession.objects.create(
                allocation=allocation,
                session_no=session_no,
                session_date=current
            )
            session_no += 1

        current += timedelta(days=1)
