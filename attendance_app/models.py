from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import datetime


class CustomUser(AbstractUser):
    """Extended user model with additional profile fields"""
    ROLE_CHOICES = [
        ('ADMIN', 'Administrator'),
        ('MANAGER', 'Manager'),
        ('EMPLOYEE', 'Employee'),
        ('HR', 'HR'),
    ]
    
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='EMPLOYEE',
        help_text="Role of the user in the system."
    )
    phone = models.CharField(max_length=20, blank=True, null=True)
    is_active_employee = models.BooleanField(default=True)
    profile_picture = models.URLField(max_length=500, blank=True, null=True)


class Department(models.Model):
    """Department/Office Locations"""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Departments"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"


class Shift(models.Model):
    """Work Shift Configuration"""
    SHIFT_TYPES = [
        ('MORNING', 'Morning Shift'),
        ('AFTERNOON', 'Afternoon Shift'),
        ('NIGHT', 'Night Shift'),
        ('FLEXIBLE', 'Flexible Hours'),
    ]
    
    name = models.CharField(max_length=100)
    shift_type = models.CharField(max_length=20, choices=SHIFT_TYPES)
    start_time = models.TimeField(help_text="Shift start time")
    end_time = models.TimeField(help_text="Shift end time")
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['start_time']

    def __str__(self):
        return f"{self.name} ({self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')})"


class GeofenceZone(models.Model):
    """Geofencing zones for office locations"""
    name = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='geofence_zones')
    latitude = models.FloatField(validators=[MinValueValidator(-90), MaxValueValidator(90)])
    longitude = models.FloatField(validators=[MinValueValidator(-180), MaxValueValidator(180)])
    radius_meters = models.IntegerField(
        default=500,
        validators=[MinValueValidator(50), MaxValueValidator(5000)],
        help_text="Radius in meters for geofencing"
    )
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Geofence Zones"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.department.name})"


class Employee(models.Model):
    """Employee Information with enhanced fields"""
    ROLE_CHOICES = [
        ('TRAINEE', 'Trainee'),
        ('JUNIOR_DEVELOPER', 'Junior Developer'),
        ('SENIOR_DEVELOPER', 'Senior Developer'),
        ('TEAM_LEADER', 'Team Leader'),
        ('HR', 'HR'),
        ('CEO', 'CEO'),
    ]
    
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('INACTIVE', 'Inactive'),
        ('LEAVE', 'On Leave'),
        ('RESIGNED', 'Resigned'),
    ]

    name = models.CharField(
        max_length=100,
        help_text="Full name of the employee."
    )
    employee_id = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique identifier for the employee (e.g., staff ID)."
    )
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    photo = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        help_text="URL of the employee's photo for recognition."
    )
    face_encoding = models.BinaryField(
        blank=True,
        null=True,
        help_text="Serialized face encoding derived from the employee's photo."
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='TRAINEE',
        help_text="The role of the employee within the company."
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name='employees',
        null=True,
        blank=True
    )
    shift = models.ForeignKey(
        Shift,
        on_delete=models.SET_NULL,
        related_name='employees',
        null=True,
        blank=True
    )
    manager = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='team_members'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='ACTIVE'
    )
    geofence_zone = models.ForeignKey(
        GeofenceZone,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees'
    )
    joining_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_seen = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time the employee was recognized by the system."
    )

    class Meta:
        app_label = 'attendance_app'
        verbose_name = "Employee"
        verbose_name_plural = "Employees"
        ordering = ['name']
        indexes = [
            models.Index(fields=['employee_id']),
            models.Index(fields=['department', 'status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.name} ({self.employee_id})"


# An embedded model to store break-in and break-out times, and a break type
class AttendanceRecord(models.Model):
    """Attendance record with geofence validation"""
    ATTENDANCE_TYPES = [
        ('IN', 'Check In'),
        ('OUT', 'Check Out'),
    ]
    
    STATUS_CHOICES = [
        ('APPROVED', 'Approved'),
        ('PENDING', 'Pending'),
        ('REJECTED', 'Rejected'),
    ]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='attendance_records',
        help_text="The employee associated with this attendance record."
    )
    date = models.DateField(
        auto_now_add=False,
        help_text="The date when attendance was marked."
    )
    check_in_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Time of check in."
    )
    check_out_time = models.TimeField(
        null=True,
        blank=True,
        help_text="Time of check out."
    )
    attendance_type = models.CharField(
        max_length=10,
        choices=ATTENDANCE_TYPES,
        default='IN'
    )
    latitude = models.FloatField(
        null=True,
        blank=True,
        help_text="Latitude of attendance marking location."
    )
    longitude = models.FloatField(
        null=True,
        blank=True,
        help_text="Longitude of attendance marking location."
    )
    is_geofence_valid = models.BooleanField(
        default=True,
        help_text="Whether the attendance was marked within geofence."
    )
    emotional_state = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Detected emotional state during attendance marking."
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='APPROVED'
    )
    remarks = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="Additional remarks."
    )
    working_hours = models.FloatField(
        null=True,
        blank=True,
        help_text="Total working hours for the day."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'attendance_app'
        verbose_name = "Attendance Record"
        verbose_name_plural = "Attendance Records"
        ordering = ['-date', '-check_in_time']
        indexes = [
            models.Index(fields=['employee', 'date']),
            models.Index(fields=['date']),
            models.Index(fields=['status']),
        ]
        unique_together = ['employee', 'date', 'attendance_type']

    def __str__(self):
        return f"{self.employee.name} - {self.date} ({self.attendance_type})"


class Leave(models.Model):
    """Leave management system"""
    LEAVE_TYPES = [
        ('SICK', 'Sick Leave'),
        ('CASUAL', 'Casual Leave'),
        ('EARNED', 'Earned Leave'),
        ('UNPAID', 'Unpaid Leave'),
        ('MATERNITY', 'Maternity Leave'),
        ('PATERNITY', 'Paternity Leave'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled'),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leaves')
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    reason = models.TextField()
    approved_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_leaves'
    )
    approval_date = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'attendance_app'
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['employee', 'start_date']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.employee.name} - {self.leave_type} ({self.start_date} to {self.end_date})"

    @property
    def duration_days(self):
        return (self.end_date - self.start_date).days + 1


class AttendanceMarkedLog(models.Model):
    """Log for tracking attendance marking activities"""
    attendance = models.ForeignKey(
        AttendanceRecord,
        on_delete=models.CASCADE,
        related_name='marking_logs'
    )
    method = models.CharField(
        max_length=50,
        choices=[
            ('FACE', 'Face Recognition'),
            ('QR', 'QR Code'),
            ('MANUAL', 'Manual Entry'),
            ('BIOMETRIC', 'Biometric'),
            ('RFID', 'RFID Card'),
        ]
    )
    device_info = models.CharField(max_length=200, blank=True, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'attendance_app'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['attendance']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.attendance} - {self.method}"


class EmployeeLeaveBalance(models.Model):
    """Track annual leave balance for each employee"""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_balances')
    year = models.IntegerField()
    leave_type = models.CharField(max_length=20, choices=Leave.LEAVE_TYPES)
    total_leaves = models.IntegerField(default=0)
    used_leaves = models.IntegerField(default=0)
    pending_leaves = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'attendance_app'
        unique_together = ['employee', 'year', 'leave_type']
        indexes = [
            models.Index(fields=['employee', 'year']),
        ]

    def __str__(self):
        return f"{self.employee.name} - {self.leave_type} ({self.year})"

    @property
    def available_leaves(self):
        return self.total_leaves - self.used_leaves - self.pending_leaves


class LocationSetting(models.Model):
    """Deprecated - Use GeofenceZone instead"""
    latitude = models.FloatField(
        null=False,
        default=0.0,
        help_text="Latitude of the office location."
    )
    longitude = models.FloatField(
        null=False,
        default=0.0,
        help_text="Longitude of the office location."
    )
    radius_meters = models.IntegerField(
        default=500,
        help_text="Radius in meters within which attendance can be marked."
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'attendance_app'

    def __str__(self):
        return f"Office Location: {self.latitude}, {self.longitude} (Radius: {self.radius_meters}m)"


class LeaveHistory(models.Model):
    """Historical record of monthly leaves"""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='leave_history')
    month = models.CharField(max_length=7)  # Format: YYYY-MM
    leaves_taken = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'attendance_app'
        unique_together = ('employee', 'month')
        indexes = [
            models.Index(fields=['employee', 'month']),
        ]

    def __str__(self):
        return f"{self.employee.name} - {self.month}"

