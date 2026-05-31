# attendance_app/forms.py
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import Employee, LocationSetting, CustomUser


class EmployeeForm(forms.ModelForm):
    """
    Form for creating and updating Employee records.
    Handles 'name', 'employee_id', 'photo', 'role', and other profile fields.
    The 'photo' field is handled as a regular file upload in the view.
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
        # 'photo' is handled manually in the view; 'face_encoding' is set programmatically
        fields = ['name', 'employee_id', 'email', 'phone', 'role', 'department', 'shift', 'joining_date', 'status']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline',
                'placeholder': 'Employee Full Name'
            }),
            'employee_id': forms.TextInput(attrs={
                'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline',
                'placeholder': 'Unique Employee ID'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline',
                'placeholder': 'employee@example.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline',
                'placeholder': '+91 9876543210'
            }),
            'role': forms.Select(attrs={
                'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline',
            }),
            'department': forms.Select(attrs={
                'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline',
            }),
            'shift': forms.Select(attrs={
                'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline',
            }),
            'joining_date': forms.DateInput(attrs={
                'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline',
                'type': 'date'
            }),
            'status': forms.Select(attrs={
                'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline',
            }),
        }

    team_members = forms.ModelMultipleChoiceField(
        queryset=Employee.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={'id': 'id_team_members', 'style': 'display:none;'})
    )

    def save(self, commit=True):
        employee = super().save(commit=False)
        if commit:
            employee.save()
            if 'team_members' in self.cleaned_data:
                if employee.pk:
                    Employee.objects.filter(manager=employee).update(manager=None)
                for member in self.cleaned_data['team_members']:
                    member.manager = employee
                    member.save()
        return employee

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # New logic to make the photo optional during an update
        # `self.instance` will be set if this is an update form
        if self.instance and self.instance.pk and self.instance.photo:
            self.fields['photo'].required = False

    def clean_employee_id(self):
        # Custom validation for employee_id to handle updates
        employee_id = self.cleaned_data.get('employee_id')
        if not self.instance or not self.instance.pk:  # If creating a new employee
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
