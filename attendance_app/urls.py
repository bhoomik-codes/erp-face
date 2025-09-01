# attendance_app/urls.py
from django.urls import path
from .views import admin_views
from .views import attendance_views
from .views import api_views
from .views import auth_views

app_name = 'attendance_app'

urlpatterns = [
    # Authentication URLs
    path('admin-login/', auth_views.admin_login_view, name='admin_login'),
    path('admin-logout/', auth_views.admin_logout_view, name='admin_logout'),

    # Admin Dashboard URLs
    path('admin_dashboard/', admin_views.admin_dashboard_view, name='admin_dashboard'),
    path('get-dashboard-data/', admin_views.get_dashboard_data, name='get_dashboard_data'),

    # Admin Settings
    path('admin-settings/', admin_views.admin_settings_view, name='admin_settings'),

    # Attendance Report URLs
    path('attendance-report/', admin_views.attendance_report, name='attendance_report'),
    path('get-attendance-table/', admin_views.get_attendance_table, name='get_attendance_table'),
    path('export-attendance-csv/', admin_views.export_attendance_csv, name='export_attendance_csv'),
    path('export-attendance-xlsx/', admin_views.export_attendance_xlsx, name='export_attendance_xlsx'),
    path('export-attendance-pdf/', admin_views.export_attendance_pdf, name='export_attendance_pdf'),

    # Employee Management URLs
    path('register-employee/', attendance_views.register_employee, name='register_employee'),
    path('employees/', attendance_views.employee_list, name='employee_list'),
    path('employee/delete/<str:employee_id>/', attendance_views.employee_delete, name='employee_delete'),
    path('employee/<str:employee_id>/update/', attendance_views.employee_update, name='employee_update'),

    # Mark Attendance URLs
    path('mark-attendance/', attendance_views.mark_attendance, name='mark_attendance'),
    path('recognize-face-for-prompt/', attendance_views.recognize_face_for_prompt, name='recognize_face_for_prompt'),
    path('mark-attendance-with-gesture/', attendance_views.mark_attendance_with_gesture,
         name='mark_attendance_with_gesture'),
    path('recent-attendance-records/', attendance_views.recent_attendance_records, name='recent_attendance_records'),
    path('get-current-working-hours/<str:employee_id>/<str:date_str>/', attendance_views.get_current_working_hours,
         name='get_current_working_hours'),
    path('get-employee-leaves/<str:employee_id>/', attendance_views.get_employee_leaves, name='get_employee_leaves'),

    # Reports
    path('reports/', admin_views.reports_view, name='reports'),

    # API URLs
    path('api/save-location-settings/', api_views.save_location_settings, name='save_location_settings'),
    path('api/get-location-settings/', api_views.get_location_settings, name='get_location_settings'),
    path('api/health-check/', api_views.health_check, name='health_check'),
    path('api/eligible-employees/', api_views.get_eligible_employees, name='api_get_eligible_employees'),
]
