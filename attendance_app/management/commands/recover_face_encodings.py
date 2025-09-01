# attendance_app/management/commands/recover_face_encodings.py
import pickle
import numpy as np  # <-- ADD THIS LINE
from django.core.management.base import BaseCommand, CommandError
from attendance_app.models import Employee
from attendance_app.face_recognizer import get_face_recognition_system


class Command(BaseCommand):
    help = 'Recovers face encodings from the database and saves them to the .pkl file for FaceRecognitionSystem.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Attempting to recover face encodings from database...'))

        face_recognition_system = get_face_recognition_system()

        # Clear current in-memory known faces before reloading from DB
        # This is important to prevent duplicates if the system already loaded some.
        face_recognition_system._known_face_encodings = []
        face_recognition_system._known_face_names = []
        face_recognition_system._known_employee_ids = []

        employees_with_encodings = Employee.objects.filter(face_encoding__isnull=False)
        recovered_count = 0

        if not employees_with_encodings.exists():
            self.stdout.write(self.style.WARNING('No employees with face encodings found in the database.'))
            return

        for employee in employees_with_encodings:
            try:
                # Load the pickled encoding from the database field
                loaded_encoding = pickle.loads(employee.face_encoding)

                # Ensure it's a valid face encoding format (numpy array of 128 floats)
                if isinstance(loaded_encoding, (list, tuple)):  # Handle legacy list/tuple format if any
                    loaded_encoding = np.array(loaded_encoding)

                if isinstance(loaded_encoding, np.ndarray) and loaded_encoding.shape == (128,):
                    face_recognition_system._known_face_encodings.append(loaded_encoding)
                    face_recognition_system._known_face_names.append(employee.name)
                    face_recognition_system._known_employee_ids.append(employee.employee_id)
                    recovered_count += 1
                    self.stdout.write(f'  - Recovered encoding for: {employee.name} (ID: {employee.employee_id})')
                else:
                    self.stdout.write(self.style.WARNING(
                        f'  - Skipping {employee.name} (ID: {employee.employee_id}): Invalid encoding format in database.'))
            except (pickle.UnpicklingError, ValueError, TypeError) as e:
                self.stdout.write(self.style.ERROR(
                    f'  - Error unpickling encoding for {employee.name} (ID: {employee.employee_id}): {e}'))
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  - Unexpected error for {employee.name} (ID: {employee.employee_id}): {e}'))

        # Save the combined in-memory data to the .pkl file
        face_recognition_system._save_encodings()

        self.stdout.write(
            self.style.SUCCESS(f'Successfully recovered {recovered_count} face encodings from the database.'))
        self.stdout.write(self.style.WARNING(
            'Remember to restart your Django development server after running this command for changes to take full effect in running processes.'))
