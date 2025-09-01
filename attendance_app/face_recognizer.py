# attendance_app/face_recognizer.py
import face_recognition
import os
import pickle
import numpy as np
from django.conf import settings
import requests
import io
import cv2
import logging

logger = logging.getLogger(__name__)

class FaceRecognitionSystem:
    _instance = None
    _known_face_encodings = []
    _known_face_names = []
    _known_employee_ids = []

    def __new__(cls, *args, **kwargs):
        """
        Ensures a single instance of FaceRecognitionSystem exists.
        Initializes the instance and loads encodings if not already done.
        """
        if cls._instance is None:
            cls._instance = super(FaceRecognitionSystem, cls).__new__(cls)
            cls._instance.tolerance = kwargs.get('tolerance', 0.6)
            cls._instance._load_encodings()
        return cls._instance

    def _load_encodings(self):
        """
        Loads known face encodings from the database.

        This function retrieves all employees from the database and loads their
        face encodings into a set of in-memory lists. This is done once when
        the application starts to optimize for real-time face recognition.
        """
        from .models import Employee
        try:
            employees = Employee.objects.all().only('employee_id', 'name', 'face_encoding')
            self._known_face_encodings = []
            self._known_face_names = []
            self._known_employee_ids = []
            for emp in employees:
                if emp.face_encoding:
                    # Check if the encoding is a bytes-like object before loading
                    if isinstance(emp.face_encoding, bytes):
                        self._known_face_encodings.append(pickle.loads(emp.face_encoding))
                        self._known_face_names.append(emp.name)
                        self._known_employee_ids.append(emp.employee_id)
                    else:
                        logger.warning(f"Skipping invalid encoding for employee ID: {emp.employee_id}. Data type is {type(emp.face_encoding)}, expected 'bytes'.")
            logger.info(f"Loaded {len(self._known_face_encodings)} face encodings from database.")
        except Exception as e:
            logger.error(f"Error loading encodings from database: {e}")
            self._known_face_encodings = []
            self._known_face_names = []
            self._known_employee_ids = []

    def register_employee(self, employee_id):
        """
        Registers a new employee's face encoding.

        This method downloads the employee's photo from the stored URL,
        generates a face encoding from the image, and saves it to the
        database. It also updates the in-memory cache to ensure the
        system is ready for immediate recognition.

        Args:
            employee_id (str): The unique ID of the employee to register.

        Returns:
            bool: True if registration is successful, False otherwise.
        """
        from .models import Employee

        try:
            employee = Employee.objects.get(employee_id=employee_id)
            if not employee.photo:
                logger.warning(f"Employee {employee.name} (ID: {employee.employee_id}) has no photo URL to encode.")
                return False

            # Use a robust image download function
            image_data = self._download_image_from_url(employee.photo)
            if image_data is None:
                return False

            face_encodings = face_recognition.face_encodings(image_data)

            if face_encodings:
                new_encoding = face_encodings[0]

                # Update the database record with the new encoding
                employee.face_encoding = pickle.dumps(new_encoding)
                employee.save(update_fields=['face_encoding', 'updated_at'])

                # Update the in-memory cache
                self._load_encodings()

                logger.info(f"Registered new face encoding for: {employee.name} (ID: {employee_id})")
                return True
            else:
                logger.warning(f"No face found in the photo for employee: {employee.name} (ID: {employee_id})")
                return False
        except Employee.DoesNotExist:
            logger.warning(f"Employee with ID {employee_id} not found during registration.")
            return False
        except Exception as e:
            logger.exception(f"Error during face registration for employee {employee_id}:")
            return False

    def _download_image_from_url(self, image_url):
        """
        Helper function to download an image from a URL and return it as a numpy array.
        This is a robust version of the code we developed previously.
        """
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(image_url, headers=headers, timeout=10)
            response.raise_for_status()

            if not response.content:
                logger.error("Downloaded content is empty.")
                return None

            image_data = face_recognition.load_image_file(io.BytesIO(response.content))
            return image_data

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download image from URL {image_url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing image from URL {image_url}: {e}")
            return None

    def delete_employee_encoding(self, employee_id):
        """
        Removes an employee's face encoding from the in-memory cache.
        """
        if employee_id in self._known_employee_ids:
            index_to_delete = self._known_employee_ids.index(employee_id)
            self._known_employee_ids.pop(index_to_delete)
            self._known_face_encodings.pop(index_to_delete)
            self._known_face_names.pop(index_to_delete)
            logger.info(f"Successfully deleted encoding for employee ID: {employee_id} from cache.")
            return True
        return False

    def recognize_face(self, frame):
        """
        Recognizes faces in a given image frame.

        This function takes a NumPy array representing an image frame and
        compares any detected faces to the known face encodings loaded into
        the system. It returns a list of recognized names.

        Args:
            frame (np.array): A NumPy array representing the image in RGB format.

        Returns:
            list: A list of names of the recognized employees.
        """
        # The frame received from the view is already correctly formatted as rgb_frame.
        face_locations = face_recognition.face_locations(frame)
        face_encodings = face_recognition.face_encodings(frame, face_locations)

        recognized_names = []
        for face_encoding in face_encodings:
            if not self._known_face_encodings:
                logger.warning("No known faces loaded for recognition.")
                return recognized_names

            matches = face_recognition.compare_faces(self._known_face_encodings, face_encoding, self.tolerance)
            name = "Unknown"

            face_distances = face_recognition.face_distance(self._known_face_encodings, face_encoding)
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                name = self._known_face_names[best_match_index]

            recognized_names.append(name)
        return recognized_names


def get_face_recognition_system():
    """
    Returns the singleton instance of FaceRecognitionSystem.

    This ensures that all parts of the application use the same instance,
    maintaining a consistent cache of face encodings.
    """
    return FaceRecognitionSystem()
