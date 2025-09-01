# migrate_employees.py
import os
import django
from django.conf import settings
import sys
import shutil  # For copying photo files

# Add your project's base directory to the Python path
# Adjust 'erp-face-gesture-enabled' if your project root has a different name
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE',
                      'vidAttendence2.settings')  # Replace 'your_project_name' with your actual project name (e.g., 'erp_face_gesture_enabled.settings')
django.setup()

from attendance_app.models import Employee  # Import your Employee model

print("Starting Employee data migration...")

# --- Temporary SQLite settings for reading ---
# Make sure this matches your original SQLite settings
SQLITE_DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(settings.BASE_DIR, 'db.sqlite3'),
    }
}

# --- PostgreSQL settings for writing (should be in your main settings.py) ---
# We'll use the default settings configured in settings.py for writing.

# Get the media root for photo files
MEDIA_ROOT = settings.MEDIA_ROOT

try:
    # 1. Connect to SQLite to read data
    # Temporarily override Django's database connection to read from SQLite
    original_default_db = settings.DATABASES['default']
    settings.DATABASES['default'] = SQLITE_DATABASES['default']
    django.db.connections.close_all()
    from django.db import connections

    sqlite_conn = connections['default']
    sqlite_conn.ensure_connection()

    # Fetch employees from SQLite
    print("Fetching employees from SQLite database...")
    sqlite_employees = Employee.objects.all()
    print(f"Found {sqlite_employees.count()} employees in SQLite.")

    # 2. Switch to PostgreSQL to write data
    settings.DATABASES['default'] = original_default_db
    django.db.connections.close_all()
    pg_conn = connections['default']
    pg_conn.ensure_connection()

    print("Migrating employee data to PostgreSQL...")
    migrated_count = 0
    for sqlite_employee in sqlite_employees:
        try:
            # --- IMPORTANT CHANGE: Preserve original PK ---
            # Use the original PK from SQLite when creating/updating in PostgreSQL
            # This ensures foreign key relationships in other fixtures remain valid.
            pg_employee, created = Employee.objects.update_or_create(
                pk=sqlite_employee.pk,  # Use the original primary key
                defaults={
                    'name': sqlite_employee.name,
                    'employee_id': sqlite_employee.employee_id,  # Ensure employee_id is also set/updated
                    'face_encoding': sqlite_employee.face_encoding,
                    'created_at': sqlite_employee.created_at,
                    'updated_at': sqlite_employee.updated_at,
                    'last_seen': sqlite_employee.last_seen,
                    # photo field will be handled separately below
                }
            )

            if not created:
                print(
                    f"Updated existing employee (PK: {pg_employee.pk}, ID: {pg_employee.employee_id}): {pg_employee.name}")
            else:
                print(f"Created new employee (PK: {pg_employee.pk}, ID: {pg_employee.employee_id}): {pg_employee.name}")

            # Handle photo file migration
            if sqlite_employee.photo:
                source_photo_path = sqlite_employee.photo.path
                relative_photo_path = os.path.join('employee_photos', os.path.basename(source_photo_path))
                destination_photo_path = os.path.join(MEDIA_ROOT, relative_photo_path)

                os.makedirs(os.path.dirname(destination_photo_path), exist_ok=True)

                if os.path.exists(source_photo_path):
                    if not os.path.exists(destination_photo_path) or \
                            not os.path.samefile(source_photo_path, destination_photo_path):
                        try:
                            shutil.copyfile(source_photo_path, destination_photo_path)
                            print(f"Copied photo for {pg_employee.name} to {destination_photo_path}")
                        except shutil.SameFileError:
                            print(
                                f"Skipping photo copy for {pg_employee.name}: Source and destination are the same file (SameFileError).")
                        except Exception as copy_e:
                            print(f"Error copying photo for {pg_employee.name}: {copy_e}")
                    else:
                        print(
                            f"Skipping photo copy for {pg_employee.name}: Photo already exists at destination and is the same file.")

                    pg_employee.photo.name = relative_photo_path
                    pg_employee.save(update_fields=['photo'])
                else:
                    print(f"Warning: Photo file not found for {sqlite_employee.name} at {source_photo_path}")

            migrated_count += 1

        except Exception as e:
            print(f"Error migrating employee (PK: {sqlite_employee.pk}, ID: {sqlite_employee.employee_id}): {e}")
            # Continue to next employee even if one fails

    print(f"\nSuccessfully migrated {migrated_count} employees to PostgreSQL.")

except Exception as e:
    print(f"An error occurred during the migration process: {e}")
finally:
    django.db.connections.close_all()
    print("Database connections closed.")
