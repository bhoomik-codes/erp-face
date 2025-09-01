from django.contrib import admin
from .models import Employee, AttendanceRecord


# Register your models here so they appear in the Django admin interface.

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    """
    Customizes the display of the Employee model in the Django admin.
    """
    list_display = ('name', 'employee_id', 'photo', 'has_face_encoding')
    search_fields = ('name', 'employee_id')
    list_filter = ('name',)  # Example filter

    def has_face_encoding(self, obj):
        """
        Custom method to display a boolean indicating if an employee has a face encoding.
        """
        return bool(obj.face_encoding)

    has_face_encoding.boolean = True  # Displays a checkmark icon in admin
    has_face_encoding.short_description = 'Face Encoding'  # Column header


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    """
    Customizes the display of the AttendanceRecord model in the Django admin.
    """
    list_display = ('employee', 'date', 'time')
    list_filter = ('date', 'employee')
    search_fields = ('employee__name', 'employee__employee_id')  # Search by related employee's name or ID
    date_hierarchy = 'date'  # Adds a date drill-down navigation
