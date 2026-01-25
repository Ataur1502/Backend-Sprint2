from rest_framework import serializers
from .models import Calendar, Holiday
from Creation.models import Degree, Department

class CalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Calendar
        fields = [
            'calendar_id',
            'name',
            'academic_year',
            'is_active'
        ]

    def validate(self, data):
        name = data.get('name')
        academic_year = data.get('academic_year')

        qs = Calendar.objects.filter(
            name=name,
            academic_year=academic_year
        )

        if self.instance:
            qs = qs.exclude(calendar_id=self.instance.calendar_id)

        if qs.exists():
            raise serializers.ValidationError(
                "Calendar with this name and academic year already exists."
            )

        return data


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = [
            'holiday_id',
            'calendar',
            'date',
            'scope',
            'degree',
            'department',
            'reason'
        ]

    def validate(self, data):
        scope = data.get('scope')
        degree = data.get('degree')
        department = data.get('department')

        # CAMPUS: no degree or department
        if scope == 'CAMPUS':
            if degree or department:
                raise serializers.ValidationError(
                    "Campus-wide holidays must not have degree or department."
                )

        # DEGREE: degree required, department not allowed
        elif scope == 'DEGREE':
            if not degree or department:
                raise serializers.ValidationError(
                    "Degree-specific holidays require a degree and no department."
                )

        # DEPARTMENT: both degree and department required
        elif scope == 'DEPARTMENT':
            if not degree or not department:
                raise serializers.ValidationError(
                    "Department-specific holidays require both degree and department."
                )

            if department.degree_id != degree.degree_id:
                raise serializers.ValidationError(
                    "Selected department does not belong to the selected degree."
                )

        else:
            raise serializers.ValidationError("Invalid holiday scope.")

        return data
