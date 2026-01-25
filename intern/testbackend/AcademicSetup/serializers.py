from rest_framework import serializers
from .models import AcademicCalendar, CalendarEvent
import openpyxl
from datetime import datetime, date

class CalendarEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarEvent
        fields = '__all__'

class AcademicCalendarSerializer(serializers.ModelSerializer):
    events = CalendarEventSerializer(many=True, read_only=True)
    
    class Meta:
        model = AcademicCalendar
        fields = [
            'calendar_id', 'name', 'school', 'degree', 'department', 
            'regulation', 'batch', 'semester', 'excel_file', 
            'is_active', 'created_at', 'events'
        ]
        read_only_fields = ['calendar_id', 'created_at']

    def validate(self, data):
        # 1. Duplicate Check: Regulation + Batch + Semester + Active
        regulation = data.get('regulation')
        batch = data.get('batch')
        semester = data.get('semester')
        
        # Only check uniqueness for active calendars
        if data.get('is_active', True):
            existing = AcademicCalendar.objects.filter(
                regulation=regulation,
                batch=batch,
                semester=semester,
                is_active=True
            )
            if self.instance:
                existing = existing.exclude(calendar_id=self.instance.calendar_id)
                
            if existing.exists():
                raise serializers.ValidationError({
                    "non_field_errors": ["An active calendar already exists for this Regulation, Batch, and Semester."]
                })
            
        return data

    def create(self, validated_data):
        excel_file = validated_data.get('excel_file')
        calendar = super().create(validated_data)
        
        if excel_file:
            self.parse_excel(calendar, excel_file)
            
        return calendar

    def parse_excel(self, calendar, file):
        try:
            wb = openpyxl.load_workbook(file)
            sheet = wb.active
            
            events = []
            # Type labels to match choices
            type_map = {
                'instruction': 'INSTRUCTION',
                'spell': 'INSTRUCTION',
                'holiday': 'HOLIDAY',
                'exam': 'EXAM',
                'examination': 'EXAM',
            }

            for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
                if not any(row): continue
                
                # Check for minimum number of columns
                if len(row) < 4:
                    raise serializers.ValidationError(f"Row {row_idx}: Missing required columns. Expected: Type, Name, Start Date, End Date.")

                e_type_raw, e_name, e_start, e_end = row[0:4]
                e_desc = row[4] if len(row) > 4 else ""

                if not all([e_type_raw, e_name, e_start, e_end]):
                    raise serializers.ValidationError(f"Row {row_idx}: All fields (Type, Name, Start Date, End Date) are mandatory.")

                # Normalize type
                final_type = type_map.get(str(e_type_raw).lower(), 'OTHER')
                
                # Date parsing/validation
                def ensure_date(val, name):
                    if isinstance(val, date):
                        return val
                    if isinstance(val, str):
                        try:
                            return datetime.strptime(val, '%Y-%m-%d').date()
                        except ValueError:
                            raise serializers.ValidationError(f"Row {row_idx}: {name} must be in YYYY-MM-DD format.")
                    if isinstance(val, datetime):
                        return val.date()
                    raise serializers.ValidationError(f"Row {row_idx}: {name} has invalid date format.")

                start_date = ensure_date(e_start, "Start Date")
                end_date = ensure_date(e_end, "End Date")

                if start_date > end_date:
                    raise serializers.ValidationError(f"Row {row_idx}: Start date ({start_date}) cannot be after end date ({end_date}).")

                # TODO: Date conflict logic (e.g. overlapping instructions)
                # For simplified logic, we just collect them for now.
                
                events.append(CalendarEvent(
                    calendar=calendar,
                    type=final_type,
                    name=e_name,
                    start_date=start_date,
                    end_date=end_date,
                    description=e_desc
                ))
            
            if not events:
                raise serializers.ValidationError("The Excel file contains no valid events.")

            CalendarEvent.objects.bulk_create(events)
            
        except serializers.ValidationError:
            calendar.delete()
            raise
        except Exception as e:
            calendar.delete()
            raise serializers.ValidationError(f"Error processing Excel: {str(e)}")
