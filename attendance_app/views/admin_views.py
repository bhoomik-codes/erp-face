# attendance_app/views/admin_views.py
import json
import random
from datetime import date, timedelta, datetime, time
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone
from django.db.models import Max, Sum, DurationField, F
from django.template.loader import render_to_string
from django.http import JsonResponse, HttpResponse
import logging
import csv
from io import StringIO, BytesIO
import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

from ..models import Employee, AttendanceRecord, LocationSetting, Break
from ..services.attendance_manager import AttendanceManager

logger = logging.getLogger(__name__)


def _process_attendance_record_for_report(record, today_date):
    """
    Helper function to process a single attendance record for reports.
    This centralizes the logic for calculating working hours, overtime,
    and handling the "IN but no OUT" scenario.
    """
    standard_work_hours = 8.0

    employee_obj = record.get('employee')
    record_date_obj = datetime.strptime(record.get('date'), '%Y-%m-%d').date()
    # The 'breaks' list comes from the record dictionary created in AttendanceManager.get_filtered_attendance_summary.
    # It is a list of Break instances.
    record_breaks = record.get('breaks', [])
    if record_breaks is None:
        record_breaks = []

    (
        calculated_total_working_hours,
        lunch_duration_hours,
        other_break_duration_hours,
        has_out_record
    ) = AttendanceManager.calculate_working_hours(
        employee=employee_obj,
        target_date=record_date_obj,
    )

    lunch_breaks = [b for b in record_breaks if b.break_type == 'LUNCH']
    lunch_in_time = min(b.break_in for b in lunch_breaks if b.break_in) if lunch_breaks else None
    lunch_out_time = max(b.break_out for b in lunch_breaks if b.break_out) if any(
        b.break_out for b in lunch_breaks) else None

    total_break_hours = lunch_duration_hours + other_break_duration_hours

    overtime_hours = max(0.0, calculated_total_working_hours - standard_work_hours)

    out_time_str = record.get('out_record')
    if out_time_str:
        out_time_str = out_time_str.time.strftime('%I:%M %p')
    elif not has_out_record and record_date_obj < today_date:
        out_time_str = AttendanceManager.OUT_TIME_DEFAULT.strftime('%I:%M %p')
    elif not has_out_record:
        out_time_str = 'In progress...'
    else:
        out_time_str = '-'

    in_time_str = record.get('in_time', '-')

    return {
        'employee_name': record.get('employee_name', '-'),
        'employee_id': record.get('employee_id', '-'),
        'date': record.get('date', '-'),
        'in_time': in_time_str,
        'out_time': out_time_str,
        'lunch_in_time': lunch_in_time.strftime('%I:%M %p') if lunch_in_time else '-',
        'lunch_out_time': lunch_out_time.strftime('%I:%M %p') if lunch_out_time else '-',
        'total_break_duration': f"{total_break_hours:.2f} hours" if total_break_hours > 0 else '-',
        'total_working_hours': f"{calculated_total_working_hours:.2f} hours",
        'overtime_hours': f"{overtime_hours:.2f} hours",
    }


@login_required
def admin_dashboard_view(request):
    """
    Renders the admin dashboard with summary statistics and charts, now with period filters.
    """
    filter_period = request.GET.get('period', 'month')
    today = timezone.localdate()
    start_date, end_date = AttendanceManager.get_period_dates(today, filter_period)

    total_employees = Employee.objects.count()

    # Get all employees and their records for the period to calculate hours
    employees = Employee.objects.all().prefetch_related(
        'attendance_records'
    ).order_by('name')

    total_attendance_hours_all = 0
    total_overtime_all = 0
    present_employee_ids = set()

    for employee in employees:
        records_in_period = employee.attendance_records.filter(
            date__gte=start_date,
            date__lte=end_date,
            attendance_type='IN'
        ).values_list('date', flat=True).distinct()

        for record_date in records_in_period:
            total_hours_for_day, _, _, has_out = AttendanceManager.calculate_working_hours(
                employee=employee,
                target_date=record_date
            )
            if has_out or (record_date < today):
                total_hours_for_day = total_hours_for_day
            else:
                total_hours_for_day = max(0, total_hours_for_day - (AttendanceManager.LUNCH_TIME_END.hour - AttendanceManager.LUNCH_TIME_START.hour))

            total_attendance_hours_all += total_hours_for_day
            overtime_for_day = max(0.0, total_hours_for_day - AttendanceManager.STANDARD_WORK_HOURS)
            total_overtime_all += overtime_for_day

            present_employee_ids.add(employee.id)

    all_employee_ids = set(employees.values_list('id', flat=True))
    absent_employee_ids = all_employee_ids - present_employee_ids
    total_absentees_count = len(absent_employee_ids)

    # Fetch data for top lists (already handled in get_dashboard_data)
    # The current implementation in admin_dashboard_view uses placeholders,
    # so we'll just keep the existing logic and let the AJAX call handle the actual data.
    top_5_absentees = Employee.objects.filter(id__in=absent_employee_ids)[:5]
    top_5_max_attendance = Employee.objects.order_by('-last_seen')[:5]
    top_5_overtime = Employee.objects.all()[:5]  # Placeholder

    top_5_absentees_html = render_to_string(
        'attendance_app/partials/top_absentees_list.html',
        {'employees': top_5_absentees, 'period': filter_period}
    )
    top_5_max_attendance_html = render_to_string(
        'attendance_app/partials/top_max_attendance_list.html',
        {'employees': top_5_max_attendance, 'period': filter_period}
    )
    top_5_overtime_html = render_to_string(
        'attendance_app/partials/top_overtime_list.html',
        {'employees': top_5_overtime, 'period': filter_period}
    )

    # Fetch data for charts
    emotion_trends_data = {
        'weekly': AttendanceManager.get_emotion_trends(today - timedelta(days=6), today, 'daily'),
        'monthly': AttendanceManager.get_emotion_trends(today.replace(day=1), today, 'daily'),
        'yearly': AttendanceManager.get_emotion_trends(today.replace(month=1, day=1), today, 'monthly'),
    }
    late_on_time_trends_data = {
        'weekly': AttendanceManager.get_late_on_time_trends(today - timedelta(days=6), today, 'daily'),
        'monthly': AttendanceManager.get_late_on_time_trends(today.replace(day=1), today, 'daily'),
        'yearly': AttendanceManager.get_late_on_time_trends(today.replace(month=1, day=1), today, 'monthly'),
    }
    attendance_percentage_trends_data = {
        'weekly': AttendanceManager.get_attendance_percentage_trends(today - timedelta(days=6), today, 'daily'),
        'monthly': AttendanceManager.get_attendance_percentage_trends(today.replace(day=1), today, 'daily'),
        'yearly': AttendanceManager.get_attendance_percentage_trends(today.replace(month=1, day=1), today, 'monthly'),
    }
    leave_data = AttendanceManager.get_leave_distribution()

    context = {
        'report_data': json.dumps({
            'emotionTrends': emotion_trends_data,
            'leaveDistribution': leave_data,
            'arrivalStats': late_on_time_trends_data,
            'attendanceTrends': attendance_percentage_trends_data,
        }),
        'total_employees': total_employees,
        'total_attendance_hours_all': f'{total_attendance_hours_all:.2f}',
        'total_overtime_all': f'{total_overtime_all:.2f}',
        'total_absentees_count': total_absentees_count,
        'top_5_absentees_html': top_5_absentees_html,
        'top_5_max_attendance_html': top_5_max_attendance_html,
        'top_5_overtime_html': top_5_overtime_html,
        'filter_period': filter_period,
    }
    return render(request, 'attendance_app/admin_dashboard.html', context)


@login_required
def get_dashboard_data(request):
    """
    AJAX endpoint to fetch filtered dashboard data.
    This logic mirrors admin_dashboard_view but returns JSON.
    """
    filter_period = request.GET.get('period', 'month')
    today = timezone.localdate()
    start_date, end_date = AttendanceManager.get_period_dates(today, filter_period)

    all_employees_queryset = Employee.objects.all()

    # Optimized fetching of attendance data for the period
    all_attendance_records = AttendanceRecord.objects.filter(
        date__range=[start_date, end_date],
        attendance_type__in=['IN', 'OUT']
    ).select_related('employee').order_by('employee', 'date', 'time')

    # Calculate daily summaries efficiently
    employee_daily_records = defaultdict(list)
    for record in all_attendance_records:
        employee_daily_records[(record.employee, record.date)].append(record)

    employee_period_hours = defaultdict(lambda: {'employee': None, 'total_hours': 0, 'days_present': 0})
    present_employee_ids_in_period = set()

    for (employee_obj, record_date), records_list in employee_daily_records.items():
        # Using the refactored calculate_working_hours from the manager
        total_hours_for_day, _, _, _ = AttendanceManager.calculate_working_hours(employee_obj, record_date)

        present_employee_ids_in_period.add(employee_obj.id)

        employee_period_hours[employee_obj.id]['employee'] = employee_obj
        employee_period_hours[employee_obj.id]['total_hours'] += total_hours_for_day
        if total_hours_for_day > 0:
            employee_period_hours[employee_obj.id]['days_present'] += 1

    total_attendance_hours_all = sum(data['total_hours'] for data in employee_period_hours.values())

    # Calculate overtime for each employee over the period
    total_overtime_all = 0
    overtime_employees_list = []
    STANDARD_WORK_HOURS_PER_DAY = 8

    for emp_data in employee_period_hours.values():
        if emp_data['days_present'] > 0:
            expected_hours_for_period = STANDARD_WORK_HOURS_PER_DAY * emp_data['days_present']
            overtime_for_employee = max(0, emp_data['total_hours'] - expected_hours_for_period)
            total_overtime_all += overtime_for_employee
            if overtime_for_employee > 0:
                emp_data['overtime_hours'] = overtime_for_employee
                overtime_employees_list.append(emp_data)

    total_absentees_count = all_employees_queryset.exclude(
        id__in=list(present_employee_ids_in_period)
    ).count()

    absent_employees_in_period = all_employees_queryset.exclude(
        id__in=list(present_employee_ids_in_period)
    ).order_by('name')[:5]

    top_5_max_attendance = sorted(
        [data for data in employee_period_hours.values() if data['total_hours'] > 0],
        key=lambda x: x['total_hours'],
        reverse=True
    )[:5]

    top_5_overtime = sorted(
        overtime_employees_list,
        key=lambda x: x['overtime_hours'],
        reverse=True
    )[:5]

    data = {
        'total_attendance_hours_all': f"{total_attendance_hours_all:.1f}" if total_attendance_hours_all else "N/A",
        'total_overtime_all': f"{total_overtime_all:.1f}" if total_overtime_all else "N/A",
        'total_absentees_count': total_absentees_count,
        'top_5_absentees_html': render_to_string(
            'attendance_app/partials/top_absentees_list.html',
            {'top_5_absentees': absent_employees_in_period, 'filter_period': filter_period}
        ),
        'top_5_max_attendance_html': render_to_string(
            'attendance_app/partials/top_max_attendance_list.html',
            {'top_5_max_attendance': top_5_max_attendance, 'filter_period': filter_period}
        ),
        'top_5_overtime_html': render_to_string(
            'attendance_app/partials/top_overtime_list.html',
            {'top_5_overtime': top_5_overtime, 'filter_period': filter_period}
        ),
    }
    return JsonResponse(data)


@login_required(login_url="admin_login")
def admin_settings_view(request):
    """
    Admin settings page to configure office location for geofencing.
    """
    settings_obj = LocationSetting.objects.first()
    context = {
        'latitude': settings_obj.latitude if settings_obj else None,
        'longitude': settings_obj.longitude if settings_obj else None,
        'radius_meters': settings_obj.radius_meters if settings_obj else 500,
        'current_page': 'settings'
    }
    return render(request, 'attendance_app/admin_settings.html', context)


@login_required(login_url='admin_login')
def attendance_report(request):
    """
    Renders the attendance report page with initial data based on filters.
    By default, shows records for today in ascending order of time.
    """
    employees = Employee.objects.all().order_by('name')

    filter_start_date_str = request.GET.get('start_date')
    filter_end_date_str = request.GET.get('end_date')
    filter_employee_ids_list = request.GET.getlist('employee_ids[]')
    filter_total_hours_lt = request.GET.get('total_hours_lt')

    # If no dates are provided, default to today's date
    today_iso = timezone.localdate().isoformat()
    if not filter_start_date_str:
        filter_start_date_str = today_iso
    if not filter_end_date_str:
        filter_end_date_str = today_iso

    context = {
        'employees': employees,
        'filter_start_date': filter_start_date_str,
        'filter_end_date': filter_end_date_str,
        'filter_employee_ids': filter_employee_ids_list,
        'filter_total_hours_lt': filter_total_hours_lt,
        'current_page': 'view_attendance'
    }

    return render(request, 'attendance_app/view_attendance_records.html', context)


@login_required(login_url='admin_login')
def get_attendance_table(request):
    """
    AJAX endpoint to fetch and return the rendered attendance table body based on filters.
    This is called by attendance_report_scripts.js.
    """
    filter_start_date_str = request.GET.get('start_date')
    filter_end_date_str = request.GET.get('end_date')
    filter_employee_ids_list = request.GET.getlist('employee_ids[]')
    filter_total_hours_lt_str = request.GET.get('total_hours_lt')

    today_iso = timezone.localdate().isoformat()
    if not filter_start_date_str:
        filter_start_date_str = today_iso
    if not filter_end_date_str:
        filter_end_date_str = today_iso

    filter_total_hours_lt = None
    if filter_total_hours_lt_str:
        try:
            filter_total_hours_lt = float(filter_total_hours_lt_str)
        except (ValueError, TypeError):
            logger.warning(f"Invalid total_hours_lt filter value: {filter_total_hours_lt_str}. Ignoring.")

    attendance_summary = AttendanceManager.get_filtered_attendance_summary(
        filter_start_date_str, filter_end_date_str, filter_employee_ids_list,
        filter_total_hours_lt
    )

    today_date = timezone.localdate()
    processed_records = [_process_attendance_record_for_report(record, today_date) for record in attendance_summary]

    def dynamic_sort_key(item):
        sort_by = request.GET.get('sort_by', 'date')
        sort_by_map = {
            'employee_name': item.get('employee_name', ''),
            'employee_id': item.get('employee_id', ''),
            'date': item.get('date', ''),
            'in_time': item.get('in_time', ''),
            'out_time': item.get('out_time', ''),
            'total_working_hours': item.get('total_working_hours', ''),
            'overtime_hours': item.get('overtime_hours', ''),
        }
        value = sort_by_map.get(sort_by, '')

        if 'time' in sort_by:
            return datetime.strptime(value, '%I:%M %p').time() if value and value != '-' else time.min
        elif 'hours' in sort_by:
            try:
                return float(value.replace(' hours', '')) if value and value != '-' else 0.0
            except ValueError:
                return 0.0
        return value

    sort_order = request.GET.get('sort_order', 'asc')
    sorted_records = sorted(processed_records, key=dynamic_sort_key, reverse=(sort_order == 'desc'))

    html = render_to_string(
        'attendance_app/partials/attendance_table_body.html',
        {'attendance_records': sorted_records},
        request=request
    )
    return JsonResponse({'html': html})


@login_required(login_url='admin_login')
def export_attendance_csv(request):
    """
    Exports attendance data to CSV format, now using the centralized processing logic.
    """
    filter_start_date_str = request.GET.get('start_date')
    filter_end_date_str = request.GET.get('end_date')
    filter_employee_ids_list = request.GET.getlist('employee_ids[]')
    filter_total_hours_lt_str = request.GET.get('total_hours_lt')

    today_iso = timezone.localdate().isoformat()
    if not filter_start_date_str:
        filter_start_date_str = today_iso
    if not filter_end_date_str:
        filter_end_date_str = today_iso

    filter_total_hours_lt = None
    if filter_total_hours_lt_str:
        try:
            filter_total_hours_lt = float(filter_total_hours_lt_str)
        except (ValueError, TypeError):
            pass

    attendance_summary = AttendanceManager.get_filtered_attendance_summary(
        filter_start_date_str, filter_end_date_str, filter_employee_ids_list,
        filter_total_hours_lt
    )

    today_date = timezone.localdate()
    processed_records = [_process_attendance_record_for_report(record, today_date) for record in attendance_summary]

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="attendance_report.csv"'

    writer = csv.writer(response)
    headers = [
        'Employee Name', 'Employee ID', 'Date', 'In Time', 'Out Time',
        'Lunch In', 'Lunch Out', 'Total Break Duration', 'Total Working Hours', 'Overtime'
    ]
    writer.writerow(headers)

    for record in processed_records:
        writer.writerow([
            record['employee_name'],
            record['employee_id'],
            record['date'],
            record['in_time'],
            record['out_time'],
            record['lunch_in_time'],
            record['lunch_out_time'],
            record['total_break_duration'],
            record['total_working_hours'],
            record['overtime_hours'],
        ])
    return response


@login_required(login_url='admin_login')
def export_attendance_xlsx(request):
    """
    Exports attendance data to XLSX format, now using the centralized processing logic.
    """
    filter_start_date_str = request.GET.get('start_date')
    filter_end_date_str = request.GET.get('end_date')
    filter_employee_ids_list = request.GET.getlist('employee_ids[]')
    filter_total_hours_lt_str = request.GET.get('total_hours_lt')

    today_iso = timezone.localdate().isoformat()
    if not filter_start_date_str:
        filter_start_date_str = today_iso
    if not filter_end_date_str:
        filter_end_date_str = today_iso

    filter_total_hours_lt = None
    if filter_total_hours_lt_str:
        try:
            filter_total_hours_lt = float(filter_total_hours_lt_str)
        except (ValueError, TypeError):
            pass

    attendance_summary = AttendanceManager.get_filtered_attendance_summary(
        filter_start_date_str, filter_end_date_str, filter_employee_ids_list,
        filter_total_hours_lt
    )

    today_date = timezone.localdate()
    processed_records = [_process_attendance_record_for_report(record, today_date) for record in attendance_summary]

    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = "Attendance Report"

    headers = [
        'Employee Name', 'Employee ID', 'Date', 'In Time', 'Out Time',
        'Lunch In', 'Lunch Out', 'Total Break Duration', 'Total Working Hours', 'Overtime'
    ]
    sheet.append(headers)

    header_font = Font(bold=True)
    for cell in sheet[1]:
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'),
                             bottom=Side(style='thin'))

    for record in processed_records:
        row_data = [
            record['employee_name'],
            record['employee_id'],
            record['date'],
            record['in_time'],
            record['out_time'],
            record['lunch_in_time'],
            record['lunch_out_time'],
            record['total_break_duration'],
            record['total_working_hours'],
            record['overtime_hours'],
        ]
        sheet.append(row_data)

    for col in sheet.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        sheet.column_dimensions[column].width = adjusted_width

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="attendance_report.xlsx"'
    workbook.save(response)
    return response


@login_required(login_url='admin_login')
def export_attendance_pdf(request):
    """
    Exports attendance data to PDF format, now using the centralized processing logic.
    """
    filter_start_date_str = request.GET.get('start_date')
    filter_end_date_str = request.GET.get('end_date')
    filter_employee_ids_list = request.GET.getlist('employee_ids[]')
    filter_total_hours_lt_str = request.GET.get('total_hours_lt')

    today_iso = timezone.localdate().isoformat()
    if not filter_start_date_str:
        filter_start_date_str = today_iso
    if not filter_end_date_str:
        filter_end_date_str = today_iso

    filter_total_hours_lt = None
    if filter_total_hours_lt_str:
        try:
            filter_total_hours_lt = float(filter_total_hours_lt_str)
        except (ValueError, TypeError):
            pass

    attendance_summary = AttendanceManager.get_filtered_attendance_summary(
        filter_start_date_str, filter_end_date_str, filter_employee_ids_list,
        filter_total_hours_lt
    )

    today_date = timezone.localdate()
    processed_records = [_process_attendance_record_for_report(record, today_date) for record in attendance_summary]

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
    styles = getSampleStyleSheet()

    elements = []

    title_style = styles['h1']
    title_style.alignment = 1
    elements.append(Paragraph("Attendance Report", title_style))
    elements.append(Spacer(1, 0.2 * inch))

    headers = [
        'Employee Name', 'Employee ID', 'Date', 'In Time', 'Out Time',
        'Lunch In', 'Lunch Out', 'Total Break Duration', 'Total Working Hours', 'Overtime'
    ]

    data = [headers]
    for record in processed_records:
        data.append([
            record['employee_name'],
            record['employee_id'],
            record['date'],
            record['in_time'],
            record['out_time'],
            record['lunch_in_time'],
            record['lunch_out_time'],
            record['total_break_duration'],
            record['total_working_hours'],
            record['overtime_hours'],
        ])

    num_columns = len(headers)
    table_width = landscape(letter)[0] - 2 * inch

    max_widths = [len(header) for header in headers]
    for row in data:
        for i, cell_value in enumerate(row):
            max_widths[i] = max(max_widths[i], len(str(cell_value)))

    CHAR_POINT_WIDTH = 6
    COLUMN_PADDING_POINTS = 10
    initial_col_widths = [(mw * CHAR_POINT_WIDTH) + COLUMN_PADDING_POINTS for mw in max_widths]
    total_initial_width = sum(initial_col_widths)

    col_widths = []
    if total_initial_width > table_width:
        scale_factor = table_width / total_initial_width
        col_widths = [w * scale_factor for w in initial_col_widths]
    else:
        remaining_space = table_width - total_initial_width
        space_per_column = remaining_space / num_columns
        col_widths = [w + space_per_column for w in initial_col_widths]

    table = Table(data, colWidths=col_widths)
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
    ])
    table.setStyle(table_style)
    elements.append(table)

    doc.build(elements)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="attendance_report.pdf"'
    response.write(buffer.getvalue())
    buffer.close()
    return response


@login_required(login_url='admin_login')
def reports_view(request):
    """
    Renders the reports page with dynamic data for various charts.
    """
    today = date.today()

    # Get filter period from request, default to 'weekly'
    filter_period = request.GET.get('period', 'weekly')

    start_date, end_date = AttendanceManager.get_period_dates(today, filter_period)

    emotion_trends_data = {
        'weekly': AttendanceManager.get_emotion_trends(today - timedelta(days=6), today, 'daily'),
        'monthly': AttendanceManager.get_emotion_trends(today.replace(day=1), today, 'daily'),
        'yearly': AttendanceManager.get_emotion_trends(today.replace(month=1, day=1), today, 'monthly'),
    }

    late_on_time_trends_data = {
        'weekly': AttendanceManager.get_late_on_time_trends(today - timedelta(days=6), today, 'daily'),
        'monthly': AttendanceManager.get_late_on_time_trends(today.replace(day=1), today, 'daily'),
        'yearly': AttendanceManager.get_late_on_time_trends(today.replace(month=1, day=1), today, 'monthly'),
    }

    attendance_percentage_trends_data = {
        'weekly': AttendanceManager.get_attendance_percentage_trends(today - timedelta(days=6), today, 'daily'),
        'monthly': AttendanceManager.get_attendance_percentage_trends(today.replace(day=1), today, 'daily'),
        'yearly': AttendanceManager.get_attendance_percentage_trends(today.replace(month=1, day=1), today, 'monthly'),
    }

    leave_data = AttendanceManager.get_leave_distribution()

    context = {
        'report_data': json.dumps({
            'emotionTrends': emotion_trends_data,
            'leaveDistribution': leave_data,
            'arrivalStats': late_on_time_trends_data,
            'attendanceTrends': attendance_percentage_trends_data,
        })
    }
    return render(request, 'attendance_app/reports.html', {**context, 'current_page': 'reports'})
