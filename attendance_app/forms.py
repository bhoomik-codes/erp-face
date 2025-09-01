# attendance_app/forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import Employee, LocationSetting, CustomUser


class EmployeeForm(forms.ModelForm):
    """
    Form for creating and updating Employee records.
    Handles 'name', 'employee_id', 'photo', 'role', and 'team_members'.
    The 'photo' field is now a regular FileInput that we'll handle manually in the view.
    """
    # Override the photo field to handle it as a regular file upload
    photo = forms.FileField(
        required=True,
        widget=forms.FileInput(attrs={
            'class': 'block w-full text-sm text-gray-700 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100',
        }),
        help_text="A clear photo of the employee's face for recognition."
    )

    class Meta:
        model = Employee
        # We will not include 'photo' in the fields because we will handle its saving manually in the view
        fields = ['name', 'employee_id', 'role', 'team_members']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline',
                'placeholder': 'Employee Full Name'
            }),
            'employee_id': forms.TextInput(attrs={
                'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline',
                'placeholder': 'Unique Employee ID'
            }),
            'role': forms.Select(attrs={
                'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline',
            }),
            # IMPORTANT CHANGE: Always render team_members as SelectMultiple, but make it hidden
            'team_members': forms.SelectMultiple(attrs={
                'class': 'hidden'  # This class will hide the default Django widget
            }),
        }
        labels = {
            'name': 'Full Name',
            'employee_id': 'Employee ID',
            'photo': 'Profile Photo',
            'role': 'Role',
            'team_members': 'Team Members',
        }
        help_texts = {
            'photo': 'Upload a clear photo of the employee\'s face for recognition.',
            'role': 'Select the employee\'s role within the company.',
            'team_members': 'Select developers who work under this Team Leader. (Only applicable for Team Leaders)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dynamically set the queryset for team_members
        self.fields['team_members'].queryset = Employee.objects.filter(
            role__in=['TRAINEE', 'JUNIOR_DEVELOPER', 'SENIOR_DEVELOPER']
        ).order_by('name')

        self.fields['team_members'].required = False  # Make it not required as it's optional

        # New logic to make the photo optional during an update
        # `self.instance` will be set if this is an update form
        if self.instance and self.instance.pk and self.instance.photo:
            self.fields['photo'].required = False

    def clean_employee_id(self):
        # Custom validation for employee_id to handle updates
        employee_id = self.cleaned_data.get('employee_id')
        if not self.instance:  # If creating a new employee
            if Employee.objects.filter(employee_id=employee_id).exists():
                raise forms.ValidationError("An employee with this ID already exists.")
        else:  # If updating an existing employee
            if Employee.objects.filter(employee_id=employee_id).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError("An employee with this ID already exists.")
        return employee_id


class AdminLoginForm(AuthenticationForm):
    """
    Custom login form for admin users.
    Inherits from Django's built-in AuthenticationForm.
    """
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline',
            'placeholder': 'Username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-shadow-outline',
            'placeholder': 'Password'
        })
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'password']


class LocationSettingForm(forms.ModelForm):
    """
    Form for managing the single LocationSetting record.
    Used in admin settings to set geofencing parameters.
    """

    class Meta:
        model = LocationSetting
        fields = ['latitude', 'longitude', 'radius_meters']
        widgets = {
            'latitude': forms.NumberInput(attrs={
                'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline',
                'step': 'any',
                'placeholder': 'e.g., 26.9124'
            }),
            'longitude': forms.NumberInput(attrs={
                'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline',
                'step': 'any',
                'placeholder': 'e.g., 75.7873'
            }),
            'radius_meters': forms.NumberInput(attrs={
                'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline',
                'min': '1',
                'placeholder': 'e.g., 500'
            }),
        }
        labels = {
            'latitude': 'Latitude',
            'longitude': 'Longitude',
            'radius_meters': 'Radius (meters)',
        }
