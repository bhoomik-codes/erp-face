import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "erp_face.settings")
django.setup()

from attendance_app.forms import EmployeeForm
from django.core.files.uploadedfile import SimpleUploadedFile

data = {'name': 'Test User', 'employee_id': 'TEST-001', 'role': 'TRAINEE'}
file_data = {'photo': SimpleUploadedFile("file.jpg", b"file_content", content_type="image/jpeg")}
form = EmployeeForm(data, file_data)
print(form.is_valid())
print(form.errors)
