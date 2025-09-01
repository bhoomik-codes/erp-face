from django.urls import path
from .views import admin_views, attendance_views, api_views

urlpatterns = [
    # These paths are now relative to the '/api/' prefix from my_project/urls.py
    # NOTE: The following lines are commented out or modified because their
    # logic is now handled in other files for better organization.
    # path('get_employee_leaves/<str:employee_id>/', views.get_employee_leaves, name='api_get_employee_leaves'),
    # path('get-current-working-hours/<str:employee_id>/<str:date_str>/', views.get_current_working_hours, name='get_current_working_hours'),
    # path('check-face-position/', views.check_face_position, name='check_face_position'),
    # path('health/', views.health_check, name='health_check'),

    # API endpoints that are still needed and are now correctly linked
    path('save-location-settings/', api_views.save_location_settings, name='save_location_settings_api'),
    path('get-location-settings/', api_views.get_location_settings, name='get_location_settings_api'),
    path('get-attendance-table/', admin_views.get_attendance_table, name='get_attendance_table'),
]
