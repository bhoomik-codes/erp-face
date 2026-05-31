# attendance_app/views/attendance_views.py
import base64
import json
import numpy as np
import cv2
import os
import pytz
from datetime import datetime, date, timedelta, time
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from geopy.distance import geodesic
import logging
from django.template.loader import render_to_string
from django.templatetags.static import static

from ..services.attendance_manager import AttendanceManager
from ..face_recognizer import get_face_recognition_system
from ..forms import EmployeeForm
from ..models import Employee, AttendanceRecord, LocationSetting, LeaveHistory
import boto3

logger = logging.getLogger(__name__)


from django.core.files.storage import default_storage

def upload_photo_to_cloud_storage(photo_file):
    """
    Uploads a photo to Amazon S3.
    If AWS credentials are not set in the environment, falls back to local storage.
    """
    aws_access_key = os.environ.get('AWS_ACCESS_KEY_ID')
    
    if not aws_access_key:
        # Fall back to local storage
        logger.info("AWS_ACCESS_KEY_ID not set. Saving photo locally.")
        try:
            filename, file_extension = os.path.splitext(photo_file.name)
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            local_filename = f"employee_photos/{filename}_{timestamp}{file_extension}"
            
            saved_path = default_storage.save(local_filename, photo_file)
            return default_storage.url(saved_path)
        except Exception as e:
            logger.error(f"Failed to save photo locally: {e}")
            return None

    try:
        s3 = boto3.client(
            's3',
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
            region_name=os.environ.get('AWS_S3_REGION_NAME')
        )

        # Define a unique filename for the S3 object
        filename, file_extension = os.path.splitext(photo_file.name)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        s3_filename = f"employee_photos/{filename}_{timestamp}{file_extension}"

        # Upload the file to S3
        s3.upload_fileobj(photo_file, 'chaturvedi-v2', s3_filename)

        # Construct the URL for the uploaded file
        # The URL format may vary depending on your S3 bucket configuration
        file_url = f"https://chaturvedi-v2.s3.{os.environ.get('AWS_S3_REGION_NAME')}.amazonaws.com/{s3_filename}"

        return file_url
    except Exception as e:
        logger.error(f"Failed to upload photo to S3: {e}")
        return None


@require_http_methods(["GET", "POST"])
@login_required
def register_employee(request):
    """
    Handles the registration of a new employee.

    This view processes both GET and POST requests. On a GET request, it
    displays the employee registration form. On a POST request, it validates
    the form data, uploads the employee's photo to Amazon S3, and saves the
    employee record along with the S3 photo URL to MongoDB. If the photo
    upload or face encoding fails, the entire transaction is rolled back.

    Args:
        request (HttpRequest): The incoming request.

    Returns:
        HttpResponse: Renders the form on GET or redirects to the employee
                      list on successful POST.
    """
    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES)
        if form.is_valid():
            photo_file = request.FILES.get('photo')
            photo_url = None
            if photo_file:
                photo_url = upload_photo_to_cloud_storage(photo_file)
                if not photo_url:
                    form.add_error('photo', "Failed to upload photo. Please try again.")
                    return render(request, 'attendance_app/register_employee.html',
                                  {'form': form, 'current_page': 'register_employee'})

            if photo_url:
                form.instance.photo = photo_url

            face_error = False
            try:
                with transaction.atomic():
                    employee = form.save()

                    face_recognition_system = get_face_recognition_system()
                    if photo_url:
                        if not face_recognition_system.register_employee(employee.employee_id):
                            logger.warning(
                                f"Failed to generate face encoding for employee {employee.name}. Rolling back transaction.")
                            form.add_error('photo',
                                           "Failed to generate face encoding from the photo. Please try a different one.")
                            face_error = True
                            raise ValueError("Face encoding failed")
                    else:
                        logger.warning(f"Attempted to register employee {employee.name} without a photo.")
                        form.add_error('photo', "A profile photo is required for face recognition registration.")
                        face_error = True
                        raise ValueError("Photo required")
            except Exception as e:
                if not face_error:
                    logger.exception(
                        f"Error during face registration for employee {form.instance.name}. Rolling back transaction.")
                    form.add_error('photo', "An error occurred during face encoding. Please try again.")
                return render(request, 'attendance_app/register_employee.html', {'form': form, 'current_page': 'register_employee'})

            logger.info(
                f"Employee {employee.name} ({employee.employee_id}) registered successfully with role {employee.role}.")
            messages.success(request, f"Employee '{employee.name}' registered successfully!")
            return redirect('attendance_app:employee_list')
    else:
        form = EmployeeForm()

    return render(request, 'attendance_app/register_employee.html', {'form': form, 'current_page': 'register_employee'})


@login_required
def employee_list(request):
    """
    Displays a list of all registered employees.
    The photo URL will be used to display the image.
    """
    employees = Employee.objects.all().order_by('name')
    context = {
        'employees': employees,
        'current_page': 'employee_list'
    }
    return render(request, 'attendance_app/employee_list.html', context)


@require_http_methods(["GET", "POST"])
@login_required
def employee_update(request, employee_id):
    """
    Handles updating an existing employee's details.

    This view allows an administrator to modify an employee's information. It
    handles form submission, including the re-uploading of a new profile photo.
    If a new photo is provided, it is uploaded to S3 and the old photo URL is
    replaced in the database.

    Args:
        request (HttpRequest): The incoming request.
        employee_id (str): The unique identifier for the employee.

    Returns:
        HttpResponse: Renders the update form on GET or redirects on successful POST.
    """
    employee = get_object_or_404(Employee, employee_id=employee_id)

    if request.method == 'POST':
        form = EmployeeForm(request.POST, request.FILES, instance=employee)
        if form.is_valid():
            photo_file = request.FILES.get('photo')
            photo_url = None

            if photo_file:
                photo_url = upload_photo_to_cloud_storage(photo_file)
                if not photo_url:
                    form.add_error('photo', "Failed to upload new photo. Please try a different one.")
                    return render(request, 'attendance_app/employee_update.html', {'form': form, 'employee': employee})

            if photo_url:
                form.instance.photo = photo_url

            face_error = False
            try:
                with transaction.atomic():
                    employee = form.save()

                    # Only attempt to register face encoding if a new photo was uploaded
                    if photo_url:
                        face_recognition_system = get_face_recognition_system()
                        if not face_recognition_system.register_employee(employee.employee_id):
                            form.add_error('photo',
                                           "Failed to generate face encoding from the new photo. Please try a different one.")
                            face_error = True
                            raise ValueError("Face encoding failed")
            except Exception as e:
                if not face_error:
                    logger.exception(
                        f"Error during face registration for employee {form.instance.name}. Rolling back transaction.")
                    form.add_error('photo', "An error occurred during face encoding. Please try again.")
                return render(request, 'attendance_app/employee_update.html', {'form': form, 'employee': form.instance, 'current_page': 'employee_update'})

            logger.info(f"Employee {employee.name} updated successfully.")
            messages.success(request, f"Employee '{employee.name}' updated successfully!")
            return redirect('attendance_app:employee_list')
    else:
        form = EmployeeForm(instance=employee)

    context = {
        'form': form,
        'employee': employee,
        'current_page': 'employee_update'
    }
    return render(request, 'attendance_app/employee_update.html', context)


@require_http_methods(["POST"])
@login_required
@transaction.atomic
def employee_delete(request, employee_id):
    """
    Deletes an employee record.

    This function handles the deletion of an employee and their associated data.
    The employee's record is removed from the database, and any face encodings
    are also cleared from the face recognition system.

    Args:
        request (HttpRequest): The incoming request.
        employee_id (str): The unique identifier for the employee to be deleted.

    Returns:
        JsonResponse: A success or error message.
    """
    logger.info(f"Attempting to delete employee with ID: {employee_id}")
    try:
        employee = get_object_or_404(Employee, employee_id=employee_id)

        face_recognition_system = get_face_recognition_system()
        # Remove the encoding from the in-memory cache
        face_recognition_system.delete_employee_encoding(employee_id)

        # Delete the employee from the database
        employee.delete()

        logger.info(f"Employee {employee.name} (ID: {employee.employee_id}) deleted from database and cache.")

        return JsonResponse({'status': 'success', 'message': f"Employee '{employee.name}' has been deleted successfully."}, status=200)
    except Exception as e:
        logger.exception(f"Error deleting employee {employee_id}:")
        return JsonResponse({'status': 'error', 'message': f'An error occurred during deletion: {str(e)}'}, status=500)



def mark_attendance(request):
    """
    Renders the main attendance marking page.
    """
    return render(request, 'attendance_app/mark_attendance.html')


@csrf_exempt
@require_http_methods(["POST"])
@transaction.atomic
def recognize_face_for_prompt(request):
    """
    Recognizes a face and returns a prompt for attendance marking.
    This function has been fixed to always return an HttpResponse object.
    """
    try:
        data = json.loads(request.body)
        frame_data = data.get('image') or data.get('frame')
        
        if not frame_data:
            return JsonResponse({'status': 'error', 'message': 'No frame provided.'}, status=400)

        # Parse the base64 image data
        if ',' in frame_data:
            imgstr = frame_data.split(',')[1]
        else:
            imgstr = frame_data
            
        img_bytes = base64.b64decode(imgstr)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return JsonResponse({'status': 'error', 'message': 'Invalid frame data.'}, status=400)
            
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        face_recognition_system = get_face_recognition_system()
        recognized_names = face_recognition_system.recognize_face(rgb_frame)
        
        recognized_name = recognized_names[0] if recognized_names else "Unknown"

        if recognized_name and recognized_name != "Unknown":
            # If a face is recognized, return a success message and prompt for action
            return JsonResponse({'status': 'success', 'recognized_name': recognized_name,
                                 'message': f'Face recognized as {recognized_name}. What action would you like to perform?'})
        else:
            # If no face is recognized or it's unknown, return an info message
            return JsonResponse({'status': 'info', 'recognized_name': 'Unknown', 'message': 'No known face detected.'})

    except json.JSONDecodeError:
        logger.error("Invalid JSON data received in recognize_face_for_prompt.")
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON data.'}, status=400)
    except Exception as e:
        logger.exception("An internal server error occurred in recognize_face_for_prompt:")
        return JsonResponse({'status': 'error', 'message': f'An internal server error occurred: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@transaction.atomic
def mark_attendance_with_gesture(request):
    """
    Marks employee attendance based on face recognition and gestures.

    This function has been refactored to use a clearer, mutually exclusive
    logic flow to determine the correct attendance action (IN, OUT, or BREAK)
    based on the current time and existing records. All breaks (including
    lunch) are now managed within the 'breaks' ArrayField of the 'IN' record.
    """
    try:
        data = json.loads(request.body)
        recognized_name = data.get('recognized_name')
        user_latitude = data.get('latitude')
        user_longitude = data.get('longitude')
        emotional_state = data.get('emotional_state')

        logger.info(
            f"Received attendance request for {recognized_name}. Emotion: {emotional_state}. Location: ({user_latitude}, {user_longitude})")

        if not recognized_name or recognized_name == "Unknown":
            logger.info("Unknown person detected or name missing.")
            return JsonResponse(
                {'status': 'info', 'message': 'Unknown person or name missing.', 'recognized_name': "Unknown"})

        try:
            employee = Employee.objects.get(name=recognized_name)
        except Employee.DoesNotExist:
            logger.warning(f'Employee "{recognized_name}" not found in database for attendance marking.')
            return JsonResponse({'status': 'failure', 'message': f'Employee "{recognized_name}" not found in database.',
                                 'recognized_name': recognized_name})

        # Geofencing logic
        office_setting = LocationSetting.objects.first()
        location_check_message_suffix = ""

        if office_setting and user_latitude is not None and user_longitude is not None:
            try:
                office_coords = (float(office_setting.latitude), float(office_setting.longitude))
                user_coords = (float(user_latitude), float(user_longitude))
                distance_meters = geodesic(office_coords, user_coords).meters
                if distance_meters > office_setting.radius_meters:
                    return JsonResponse({
                        'status': 'info',
                        'message': f'You are {int(distance_meters)}m away from the office. Attendance can only be marked within {office_setting.radius_meters}m.',
                        'recognized_name': employee.name,
                        'attendance_type': None
                    })
            except (ValueError, TypeError) as ve:
                logger.error(f"Invalid float conversion for location data during geofencing: {ve}")
                location_check_message_suffix = " (Location check skipped: Invalid coordinates provided or configured)."
            except Exception as geo_e:
                logger.exception(f"Error during geofencing check for {employee.name}:")
                location_check_message_suffix = f" (Location check failed due to an error: {str(geo_e)})."
        else:
            if not office_setting:
                location_check_message_suffix = " (No office location set by admin, location check skipped)."
            elif user_latitude is None or user_longitude is None:
                location_check_message_suffix = " (Your device location not available, location check skipped)."

        current_date = timezone.localdate()
        current_time = timezone.localtime(timezone.now()).time()

        # Find the main IN and OUT records for today.
        in_record = AttendanceRecord.objects.filter(employee=employee, date=current_date, attendance_type='IN').first()
        out_record = AttendanceRecord.objects.filter(employee=employee, date=current_date,
                                                     attendance_type='OUT').first()

        message = "No attendance action taken."
        attendance_type = None
        is_late = False

        if not in_record:
            # First action of the day: mark 'IN'
            is_late = current_time > AttendanceManager.IN_TIME_END
            remarks = "Late entry." if is_late else "On time."
            AttendanceManager.create_attendance_record(
                employee=employee,
                attendance_type='IN',
                remarks=remarks,
                emotional_state=emotional_state
            )
            attendance_type = 'IN'
            message = f"In Time. Welcome, {employee.name}!"
        elif in_record and not out_record:
            # Employee is in, check for OUT, LUNCH, or BREAK
            if current_time >= AttendanceManager.OUT_TIME_MIN:
                AttendanceManager.create_attendance_record(
                    employee=employee,
                    attendance_type='OUT',
                    remarks="Out Time."
                )
                attendance_type = 'OUT'
                message = f"Out Time. Goodbye, {employee.name}!"
            else:
                # For SQLite, we don't support break tracking
                # Just mark as out time
                AttendanceRecord.objects.create(
                    employee=employee,
                    date=current_date,
                    check_in_time=current_time,
                    attendance_type='OUT',
                    remarks="Out Time (break tracking not available)."
                )
                attendance_type = 'OUT'
                message = f"Out Time recorded. Goodbye, {employee.name}!"
        else:
            # Employee is already checked out for the day
            message = f"You have already checked out for today, {employee.name}."

        # Update the last_seen time for the employee
        employee.last_seen = timezone.now()
        employee.save(update_fields=['last_seen'])

        if attendance_type:
            logger.info(
                f"Attendance marked for {employee.name} as {attendance_type}. Message: {message}{location_check_message_suffix}")
            return JsonResponse({
                "status": "success",
                "message": message + location_check_message_suffix,
                "recognized_name": employee.name,
                "attendance_type": attendance_type,
                "is_late": is_late
            })
        else:
            return JsonResponse({
                'status': 'info',
                'message': message,
                'recognized_name': employee.name,
                'is_late': False
            })

    except json.JSONDecodeError:
        logger.error("Invalid JSON data received in mark_attendance_with_gesture.")
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON data.'}, status=400)
    except Exception as e:
        logger.exception("An internal server error occurred in mark_attendance_with_gesture:")
        return JsonResponse({'status': 'error', 'message': f'An internal server error occurred: {str(e)}'}, status=500)


@require_http_methods(["GET"])
def recent_attendance_records(request):
    """
    Fetches and displays recent attendance records as cards.
    This function has been updated to correctly handle the new `breaks` array.
    """
    try:
        cutoff_date = timezone.now() - timedelta(days=7)
        logger.debug(f"Cutoff date for recent records: {cutoff_date}")

        recent_employees_with_latest_activity = Employee.objects.filter(
            last_seen__gte=cutoff_date
        ).order_by('-last_seen')[:10]

        data = []
        for employee in recent_employees_with_latest_activity:
            employee_latest_record_overall = AttendanceRecord.objects.filter(
                employee=employee
            ).order_by('-date', '-created_at').first()

            if not employee_latest_record_overall:
                logger.warning(
                    f"No overall attendance record found for employee {employee.employee_id} after filtering by last_seen.")
                continue

            latest_date_for_employee = employee_latest_record_overall.date

            try:
                # Fetch only the IN record for the day to get breaks
                in_record = AttendanceRecord.objects.filter(
                    employee=employee,
                    date=latest_date_for_employee,
                    attendance_type='IN'
                ).first()

                # Fetch the OUT record
                out_record = AttendanceRecord.objects.filter(
                    employee=employee,
                    date=latest_date_for_employee,
                    attendance_type='OUT'
                ).first()

                # Use helper function to calculate everything
                (
                    total_hours_recent,
                    lunch_duration_hours,
                    other_break_duration_hours,
                    has_out_recent
                ) = AttendanceManager.calculate_working_hours(employee, latest_date_for_employee)

                # Format times and durations for display
                in_time_str = in_record.check_in_time.strftime('%I:%M %p') if in_record and in_record.check_in_time else '-'
                out_time_str = out_record.check_out_time.strftime('%I:%M %p') if out_record and out_record.check_out_time else '-'

                lunch_in_str, lunch_out_str = '-', '-'
                # Break tracking is not available in SQLite version

                total_break_duration_hours = lunch_duration_hours + other_break_duration_hours
                total_break_duration_str = f"{total_break_duration_hours:.2f} hours" if total_break_duration_hours > 0 else "-"

                remarks_list = [r.remarks for r in
                                AttendanceRecord.objects.filter(employee=employee, date=latest_date_for_employee) if
                                r.remarks]
                combined_remarks = "; ".join(remarks_list) if remarks_list else None

                is_late_for_record_display = False
                if in_record and in_record.check_in_time and in_record.check_in_time > AttendanceManager.IN_TIME_END:
                    is_late_for_record_display = True

                data.append({
                    'employee_name': employee.name,
                    'employee_id': employee.employee_id,
                    'photo_url': employee.photo if employee.photo else static('img/default_avatar.png'),
                    'date': latest_date_for_employee.strftime('%Y-%m-%d'),
                    'in_time': in_time_str,
                    'out_time': out_time_str,
                    'lunch_in_time': lunch_in_str,
                    'lunch_out_time': lunch_out_str,
                    'total_working_hours': f"{total_hours_recent:.2f} hours" if has_out_recent or (
                                latest_date_for_employee != date.today()) else 'In progress...',
                    'total_break_duration': total_break_duration_str,
                    'remarks': combined_remarks,
                    'is_late': is_late_for_record_display,
                    'emotional_state': in_record.emotional_state if in_record else None,
                })
            except Exception as e:
                logger.exception(
                    f"Error processing record for employee {employee.employee_id} on {latest_date_for_employee}: {e}")
                continue

        # Sort the data by date and then in_time (latest first)
        data.sort(key=lambda x: (
            datetime.strptime(x['date'], '%Y-%m-%d').date(),
            datetime.strptime(x['in_time'], '%I:%M %p').time() if x['in_time'] and x['in_time'] != '-' else time.max
        ), reverse=True)

        logger.info(f"Successfully fetched {len(data)} recent attendance records.")
        records_html = render_to_string(
            'attendance_app/partials/recent_records.html',
            {'records': data},
            request=request
        )
        return JsonResponse({'status': 'success', 'records_html': records_html})
    except Exception as e:
        logger.exception("Error fetching recent attendance records:")
        return JsonResponse({'status': 'error', 'message': f'Failed to fetch recent records: {str(e)}'}, status=500)


@require_http_methods(["GET"])
def get_current_working_hours(request, employee_id, date_str):
    """
    API endpoint to get real-time working hours for a single employee on a specific date.
    """
    try:
        employee = get_object_or_404(Employee, employee_id=employee_id)
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()

        total_hours, lunch_duration, break_duration, has_out = AttendanceManager.calculate_working_hours(employee,
                                                                                                         target_date)
        logger.debug(
            f"Working hours for {employee_id} on {date_str}: {total_hours} hrs, Lunch: {lunch_duration} hrs, Break: {break_duration} hrs, Has Out: {has_out}")
        return JsonResponse({
            'employee_id': employee_id,
            'date': date_str,
            'total_working_hours': total_hours,
            'lunch_duration': lunch_duration,
            'break_duration': break_duration,
            'has_out': has_out
        })
    except Employee.DoesNotExist:
        logger.warning(f"Employee {employee_id} not found when fetching working hours.")
        return JsonResponse({"status": "error", "message": "Employee not found."}, status=404)
    except ValueError:
        logger.error(f"Invalid date format received for working hours: {date_str}")
        return JsonResponse({"status": "error", "message": "Invalid date format."}, status=400)
    except Exception as e:
        logger.exception(f"Error getting current working hours for {employee_id} on {date_str}:")
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@require_http_methods(["GET"])
def get_employee_leaves(request, employee_id):
    """
    API endpoint to fetch leave information for a specific employee.
    """
    try:
        employee = get_object_or_404(Employee, employee_id=employee_id)
        logger.debug(f"Fetching leave info for Employee ID: {employee.employee_id}, Name: {employee.name}")
        current_date = date.today()
        current_year = current_date.year
        current_month_number = current_date.month

        total_leaves_accrued_this_year = current_month_number

        leaves_taken_this_year_query = LeaveHistory.objects.filter(
            employee=employee,
            month__startswith=str(current_year)
        ).aggregate(Sum('leaves_taken'))

        leaves_taken_this_year = leaves_taken_this_year_query['leaves_taken__sum'] or 0

        leaves_remaining = total_leaves_accrued_this_year - leaves_taken_this_year

        if leaves_remaining < 0:
            leaves_remaining = 0

        response_data = {
            'employeeId': employee.employee_id,
            'employeeName': employee.name,
            'totalLeavesAccruedThisYear': total_leaves_accrued_this_year,
            'leavesTakenThisYear': leaves_taken_this_year,
            'leavesRemaining': leaves_remaining,
            'currentMonth': f"{current_year}-{current_month_number:02d}"
        }
        logger.info(f"Leave info for {employee.name} ({employee.employee_id}): {response_data}")
        return JsonResponse(response_data)

    except Employee.DoesNotExist:
        logger.warning(f'Employee with ID "{employee_id}" not found for leave lookup.')
        return JsonResponse({'error': f'Employee with ID "{employee_id}" not found.'}, status=404)
    except Exception as e:
        logger.exception(f"An unexpected error occurred while fetching leave info for {employee_id}:")
        return JsonResponse({'error': f'An internal server error occurred: {str(e)}'}, status=500)
