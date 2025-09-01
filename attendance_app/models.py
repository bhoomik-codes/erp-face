from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractUser

# We need to import djongo's models to handle the MongoDB specific features
from djongo import models as djongo_models


class CustomUser(AbstractUser):
    # You can add custom fields here if needed in the future
    # For now, we'll just use the default fields provided by AbstractUser
    pass


class Employee(djongo_models.Model):
    # This class inherits from djongo_models.Model for MongoDB compatibility
    ROLE_CHOICES = [
        ('TRAINEE', 'Trainee'),
        ('JUNIOR_DEVELOPER', 'Junior Developer'),
        ('SENIOR_DEVELOPER', 'Senior Developer'),
        ('TEAM_LEADER', 'Team Leader'),
        ('HR', 'HR'),
        ('CEO', 'CEO'),
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
    # The 'photo' field is now a URLField to store the link from a cloud storage service
    # This replaces the ImageField
    photo = models.URLField(
        max_length=200,
        blank=False,
        null=False,
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
    # team_members will now be a ManyToMany field that references itself
    # This will be handled by Djongo
    team_members = models.ManyToManyField(
        'self',
        symmetrical=False,
        blank=True,
        related_name='team_leaders',
        limit_choices_to={'role__in': ['JUNIOR_DEVELOPER', 'SENIOR_DEVELOPER', 'TRAINEE']},
        help_text="For Team Leaders, select the developers working under them."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_seen = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time the employee was recognized by the system."
    )

    def __str__(self):
        return f"{self.name} ({self.employee_id})"

    class Meta:
        # Use Djongo's specific meta options if needed.
        # Djongo handles collection names automatically based on the model name.
        app_label = 'attendance_app'
        verbose_name = "Employee"
        verbose_name_plural = "Employees"
        ordering = ['name']


# An embedded model to store break-in and break-out times, and a break type
class Break(djongo_models.Model):
    BREAK_TYPES = [
        ('LUNCH', 'Lunch Break'),
        ('OTHER', 'Other Break'),
    ]
    break_type = models.CharField(
        max_length=10,
        choices=BREAK_TYPES,
        default='OTHER'
    )
    break_in = models.TimeField(null=True, blank=True)
    break_out = models.TimeField(null=True, blank=True)

    class Meta:
        abstract = True


class AttendanceRecord(djongo_models.Model):
    ATTENDANCE_TYPES = [
        ('IN', 'In Time'),
        ('OUT', 'Out Time'),
    ]

    employee = models.ForeignKey(
        Employee,
        on_delete=models.CASCADE,
        related_name='attendance_records',
        help_text="The employee associated with this attendance record."
    )
    date = models.DateField(
        default=timezone.now,
        help_text="The date when attendance was marked."
    )
    time = models.TimeField(
        default=timezone.now,
        help_text="The time when attendance was marked."
    )
    attendance_type = models.CharField(
        max_length=10,
        choices=ATTENDANCE_TYPES,
        default='IN'
    )
    remarks = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Additional remarks (e.g., late entry, extended lunch)"
    )
    emotional_state = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Detected emotional state during attendance marking (e.g., happy, neutral, sad)."
    )

    # New field to store a list of breaks
    breaks = djongo_models.ArrayField(
        model_container=Break,
        null=True,
        blank=True,
    )

    class Meta:
        app_label = 'attendance_app'
        verbose_name = "Attendance Record"
        verbose_name_plural = "Attendance Records"
        ordering = ['-date', '-time']
        # The unique_together constraint is simplified to just 'IN' and 'OUT'
        # to avoid conflicts with multiple breaks.
        unique_together = ['employee', 'date', 'attendance_type']

    def __str__(self):
        return f"{self.employee.name} - {self.date} {self.time} ({self.attendance_type})"


class LocationSetting(djongo_models.Model):
    """
    Model to store the single office location for geofencing.
    Using pk=1 to ensure only one record exists.
    """
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

    def __str__(self):
        return f"Office Location: {self.latitude}, {self.longitude} (Radius: {self.radius_meters}m)"


class LeaveHistory(djongo_models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    month = models.CharField(max_length=7)  # Format: YYYY-MM (e.g., "2025-06")
    leaves_taken = models.IntegerField(default=0)

    class Meta:
        unique_together = ('employee', 'month')

