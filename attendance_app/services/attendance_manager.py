# attendance_app/services/attendance_manager.py
import logging
from datetime import datetime, date, timedelta, time
from collections import defaultdict
import calendar
from django.conf import settings
from django.db.models import Max, Q, Count, Sum
from django.utils import timezone
from geopy.distance import geodesic

from ..models import AttendanceRecord, Employee, LocationSetting, LeaveHistory, Break

logger = logging.getLogger(__name__)


class AttendanceManager:
    """
    Manages all core business logic related to employee attendance.

    This class handles time-based calculations, attendance marking logic,
    and data retrieval for reports and dashboards.
    """
    IN_TIME_START = time(10, 0)
    IN_TIME_END = time(11, 0)
    LUNCH_TIME_START = time(13, 30)
    LUNCH_TIME_END = time(14, 30)
    MAX_LUNCH_DURATION = timedelta(hours=1, minutes=30)
    OUT_TIME_MIN = time(19, 0)
    OFFICE_CLOSE = time(23, 59)
    STANDARD_WORK_HOURS = 9
    OUT_TIME_DEFAULT = time(19, 15)  # Auto OUT time at 7:15 PM

    @staticmethod
    def get_period_dates(today, period):
        """
        Calculates the start and end dates for a given period.
        """
        if period == 'week':
            start_date = today - timedelta(days=today.weekday())
            end_date = start_date + timedelta(days=6)
        elif period == 'month':
            start_date = today.replace(day=1)
            next_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
            end_date = next_month - timedelta(days=1)
        elif period == 'year':
            start_date = today.replace(month=1, day=1)
            end_date = today.replace(month=12, day=31)
        else:  # 'day' or invalid period
            start_date = today
            end_date = today
        return start_date, end_date

    @staticmethod
    def create_attendance_record(employee, attendance_type, remarks="", emotional_state=None):
        """
        Creates a new attendance record for the employee.
        This function is simplified as break logic is handled elsewhere.
        """
        record_kwargs = {
            'employee': employee,
            'date': timezone.localdate(),
            'time': timezone.localtime().time(),
            'attendance_type': attendance_type,
            'remarks': remarks
        }
        if attendance_type == 'IN' and emotional_state:
            record_kwargs['emotional_state'] = emotional_state
        AttendanceRecord.objects.create(**record_kwargs)
        employee.last_seen = timezone.now()
        employee.save()
        logger.info(f"Attendance recorded for {employee.name} as {attendance_type}")
        if emotional_state and attendance_type == 'IN':
            logger.info(f"Emotional state recorded: {emotional_state}")

    @staticmethod
    def calculate_working_hours(employee, target_date):
        """
        Calculates total working hours, lunch duration, and break duration for an employee on a given date.
        It handles different attendance types and calculates hours up to the current time for active sessions.
        """
        # Fetch the main IN and OUT records for the day
        in_record = AttendanceRecord.objects.filter(
            employee=employee,
            date=target_date,
            attendance_type='IN'
        ).first()

        out_record = AttendanceRecord.objects.filter(
            employee=employee,
            date=target_date,
            attendance_type='OUT'
        ).first()

        total_working_seconds = 0
        lunch_duration_seconds = 0
        other_break_duration_seconds = 0
        has_out = False

        if in_record:
            # Calculate total break duration from the breaks array
            if in_record.breaks:
                for b in in_record.breaks:
                    if b.break_in and b.break_out:
                        # Ensure breaks are handled as timedeltas
                        break_duration = datetime.combine(target_date, b.break_out) - datetime.combine(target_date,
                                                                                                       b.break_in)
                        if b.break_type == 'LUNCH':
                            lunch_duration_seconds += break_duration.total_seconds()
                        else:
                            other_break_duration_seconds += break_duration.total_seconds()

            # Fix: Ensure all datetime objects are timezone-aware for comparison
            # The database stores naive datetimes by default, so we need to make them aware.
            # `timezone.localtime()` handles converting a naive datetime to the correct timezone.
            start_dt_naive = datetime.combine(target_date, in_record.time)
            start_dt = timezone.make_aware(start_dt_naive)

            end_dt = None
            if out_record:
                end_dt_naive = datetime.combine(target_date, out_record.time)
                end_dt = timezone.make_aware(end_dt_naive)
                has_out = True
            elif target_date < timezone.localdate():
                # For a past date with no explicit OUT, use the default auto-out time
                end_dt_naive = datetime.combine(target_date, AttendanceManager.OUT_TIME_DEFAULT)
                end_dt = timezone.make_aware(end_dt_naive)
            else:
                # For the current day, use the current timezone-aware time
                end_dt = timezone.now()

            # Ensure start is before end to avoid negative time
            if start_dt < end_dt:
                total_working_seconds = (end_dt - start_dt).total_seconds()
                total_working_seconds -= (lunch_duration_seconds + other_break_duration_seconds)
            else:
                total_working_seconds = 0

        total_hours = total_working_seconds / 3600.0
        lunch_duration_hours = lunch_duration_seconds / 3600.0
        other_break_duration_hours = other_break_duration_seconds / 3600.0

        return total_hours, lunch_duration_hours, other_break_duration_hours, has_out

    @staticmethod
    def get_filtered_attendance_summary(filter_start_date_str, filter_end_date_str, employee_ids_list, total_hours_lt):
        """
        Fetches attendance records and creates a summary for a given date range and filters.
        The function now retrieves the employee object to be passed to the helper function.
        It also handles the 'total_hours_lt' filter.
        """
        try:
            start_date = datetime.strptime(filter_start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(filter_end_date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            logger.error("Invalid date format in get_filtered_attendance_summary.")
            return []

        # Start with all 'IN' records in the date range
        base_query = AttendanceRecord.objects.filter(
            date__gte=start_date,
            date__lte=end_date,
            attendance_type='IN'
        )

        if employee_ids_list:
            base_query = base_query.filter(employee__employee_id__in=employee_ids_list)

        # Retrieve the records, including related employee data
        records_with_employees = base_query.select_related('employee').order_by('date', 'employee__name')

        summary = []
        today_date = timezone.localdate()

        # We need to manually process each record to calculate hours for filtering
        for record in records_with_employees:
            total_hours, _, _, has_out = AttendanceManager.calculate_working_hours(record.employee, record.date)

            # Apply the total hours filter if it exists
            if total_hours_lt and total_hours >= float(total_hours_lt):
                continue

            # Create a simplified dictionary to be used by the report view
            summary.append({
                'employee': record.employee,
                'employee_name': record.employee.name,
                'employee_id': record.employee.employee_id,
                'date': record.date.strftime('%Y-%m-%d'),
                'in_time': record.time.strftime('%I:%M %p'),
                'breaks': record.breaks,
                'out_record': AttendanceRecord.objects.filter(employee=record.employee, date=record.date,
                                                              attendance_type='OUT').first(),
                'has_out': has_out,
            })

        return summary

    @staticmethod
    def get_emotion_trends(start_date, end_date, interval):
        """
        Calculates emotion trends over a given period.
        """
        # This is an example implementation. You might need to adapt it.
        trends_data = defaultdict(lambda: {'happy': 0, 'sad': 0, 'neutral': 0, 'total': 0})

        records = AttendanceRecord.objects.filter(
            date__gte=start_date,
            date__lte=end_date,
            emotional_state__isnull=False
        )

        for record in records:
            if interval == 'daily':
                key = record.date.strftime('%Y-%m-%d')
            elif interval == 'monthly':
                key = record.date.strftime('%Y-%m')
            else:  # yearly
                key = record.date.strftime('%Y')

            emotion = record.emotional_state.lower()
            if emotion in trends_data[key]:
                trends_data[key][emotion] += 1
            trends_data[key]['total'] += 1

        labels = sorted(trends_data.keys())
        return {
            'labels': labels,
            'happy': [trends_data[label]['happy'] for label in labels],
            'sad': [trends_data[label]['sad'] for label in labels],
            'neutral': [trends_data[label]['neutral'] for label in labels],
        }

    @staticmethod
    def get_late_on_time_trends(start_date, end_date, interval):
        """
        Calculates trends for late vs. on-time arrivals.
        """
        # Example implementation
        trends_data = defaultdict(lambda: {'late': 0, 'on_time': 0})
        records = AttendanceRecord.objects.filter(
            date__gte=start_date,
            date__lte=end_date,
            attendance_type='IN'
        )

        for record in records:
            if interval == 'daily':
                key = record.date.strftime('%Y-%m-%d')
            elif interval == 'monthly':
                key = record.date.strftime('%Y-%m')
            else:  # yearly
                key = record.date.strftime('%Y')

            # Fix: Ensure `record.time` is a time object and can be compared with other time objects.
            # The database returns a time object, which is timezone-naive.
            # This comparison is safe as both are naive time objects.
            if record.time > AttendanceManager.IN_TIME_END:
                trends_data[key]['late'] += 1
            else:
                trends_data[key]['on_time'] += 1

        labels = sorted(trends_data.keys())
        return {
            'labels': labels,
            'on_time': [trends_data[label]['on_time'] for label in labels],
            'late': [trends_data[label]['late'] for label in labels],
        }

    @staticmethod
    def get_attendance_percentage_trends(start_date, end_date, interval):
        """
        Calculates attendance trends: number of present and absent employees per interval.
        """
        trends_data = defaultdict(lambda: {'present': 0, 'absent': 0})
        total_employees = Employee.objects.count()

        if total_employees == 0:
            return []

        # Iterate over each day, month, or year in the range
        current_date = start_date
        while current_date <= end_date:
            if interval == 'daily':
                key = current_date.strftime('%Y-%m-%d')
                days_to_check = [current_date]
                next_date = current_date + timedelta(days=1)
            elif interval == 'monthly':
                key = current_date.strftime('%Y-%m')
                _, num_days = calendar.monthrange(current_date.year, current_date.month)
                days_to_check = [current_date + timedelta(days=d) for d in range(num_days) if
                                 (current_date + timedelta(days=d)) <= end_date]
                next_date = (current_date.replace(day=28) + timedelta(days=4)).replace(day=1)
            else:  # yearly
                key = current_date.strftime('%Y')
                num_days = 365 + (1 if calendar.isleap(current_date.year) else 0)
                days_to_check = [current_date + timedelta(days=d) for d in range(num_days) if
                                 (current_date + timedelta(days=d)) <= end_date]
                next_date = current_date.replace(year=current_date.year + 1)

            present_employees_on_interval = set(
                AttendanceRecord.objects.filter(
                    date__in=days_to_check,
                    attendance_type='IN'
                ).values_list('employee', flat=True)
            )

            present_count = len(present_employees_on_interval)
            absent_count = total_employees - present_count

            trends_data[key]['present'] += present_count
            trends_data[key]['absent'] += absent_count
            current_date = next_date

        labels = sorted(trends_data.keys())
        return {
            'labels': labels,
            'present': [trends_data[label]['present'] for label in labels],
            'absent': [trends_data[label]['absent'] for label in labels],
        }

    @staticmethod
    def get_leave_distribution():
        """
        Fetches and aggregates leave data from LeaveHistory to provide distribution.
        This is a placeholder for dynamic data. You might need to adjust
        based on how leave types are managed in your system.
        """
        total_leaves_taken_all_time = LeaveHistory.objects.aggregate(Sum('leaves_taken'))['leaves_taken__sum'] or 0

        if total_leaves_taken_all_time > 0:
            sick = round(total_leaves_taken_all_time * 0.30)
            vacation = round(total_leaves_taken_all_time * 0.45)
            casual = round(total_leaves_taken_all_time * 0.20)
            other = total_leaves_taken_all_time - (sick + vacation + casual)
        else:
            sick, vacation, casual, other = 0, 0, 0, 0

        return {
            'labels': ['Sick Leave', 'Vacation Leave', 'Casual Leave', 'Other'],
            'data': [sick, vacation, casual, other]
        }

