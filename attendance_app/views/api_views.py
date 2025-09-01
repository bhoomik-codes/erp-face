# attendance_app/views/api_views.py
import json
import math
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db.utils import IntegrityError
from django.db import connection
from django.views.decorators.cache import never_cache
from django.conf import settings
import logging

# Assuming models.py is at the app root
from ..models import LocationSetting, Employee

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def save_location_settings(request):
    """
    API endpoint to save office location settings.
    """
    try:
        data = json.loads(request.body)
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        radius_meters = data.get('radius_meters')

        logger.debug(f"Received latitude: {latitude}, longitude: {longitude}, radius_meters: {radius_meters}")

        if not all([latitude is not None, longitude is not None, radius_meters is not None]):
            logger.warning("Missing location data in save_location_settings request.")
            return JsonResponse({'status': 'error', 'message': 'Missing location data. All fields are required.'},
                                status=400)

        try:
            latitude = float(latitude)
            longitude = float(longitude)
            radius_meters = int(radius_meters)
        except ValueError:
            logger.error(
                f"Invalid numeric data for location settings: latitude={latitude}, longitude={longitude}, radius_meters={radius_meters}")
            return JsonResponse(
                {'status': 'error', 'message': 'Invalid numeric data for latitude, longitude, or radius.'}, status=400)

        if not math.isfinite(latitude) or not math.isfinite(longitude) or radius_meters <= 0:
            logger.warning(
                f"Invalid range for location settings: latitude={latitude}, longitude={longitude}, radius_meters={radius_meters}")
            return JsonResponse({'status': 'error',
                                 'message': 'Latitude and longitude must be valid finite numbers, and radius must be a positive integer.'},
                                status=400)

        settings_obj, created = LocationSetting.objects.get_or_create(pk=1)

        logger.debug(f"Latitude type: {type(latitude)}, value: {latitude}")
        logger.debug(f"Longitude type: {type(longitude)}, value: {longitude}")
        logger.debug(f"Radius type: {type(radius_meters)}, value: {radius_meters}")

        settings_obj.latitude = latitude
        settings_obj.longitude = longitude
        settings_obj.radius_meters = radius_meters
        settings_obj.save()

        logger.info("Location settings saved successfully.")
        return JsonResponse({'status': 'success', 'message': 'Location settings saved successfully.'})
    except json.JSONDecodeError:
        logger.error("Invalid JSON data received in save_location_settings.")
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON data.'}, status=400)
    except IntegrityError as e:
        logger.exception("Database integrity error in save_location_settings:")
        return JsonResponse({'status': 'error',
                             'message': f'Database integrity error: {str(e)}. This often means a NOT NULL constraint was violated.'},
                            status=500)
    except Exception as e:
        logger.exception("An unexpected internal server error occurred in save_location_settings:")
        return JsonResponse({'status': 'error', 'message': f'An internal server error occurred: {str(e)}'}, status=500)


@login_required
def get_location_settings(request):
    """
    API endpoint to retrieve office location settings.
    """
    try:
        settings_obj = LocationSetting.objects.first()
        if settings_obj:
            logger.debug("Location settings retrieved successfully.")
            return JsonResponse({
                'status': 'success',
                'latitude': float(settings_obj.latitude),
                'longitude': float(settings_obj.longitude),
                'radius_meters': settings_obj.radius_meters
            })
        else:
            logger.info("Location settings not found.")
            return JsonResponse({'status': 'error', 'message': 'Location settings not found.'}, status=404)
    except Exception as e:
        logger.exception("Failed to retrieve location settings:")
        return JsonResponse({'status': 'error', 'message': f'Failed to retrieve location settings: {str(e)}'},
                            status=500)


@never_cache
def health_check(request):
    """
    API endpoint for health checks.
    Checks database connection.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

        status_info = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "Attendance System",
            "database": "connected",
            "debug_mode": settings.DEBUG
        }
        logger.info("Health check: Database connected.")
        return JsonResponse(status_info)

    except Exception as e:
        error_info = {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "service": "Attendance System",
            "database": "disconnected"
        }
        logger.error(f"Health check failed: {e}")
        return JsonResponse(error_info, status=500)


# Removed check_face_position as it was a placeholder and not used server-side based on JS analysis.
# If it's intended for a future server-side face position validation, uncomment and implement properly.
@require_http_methods(["GET"])
def check_face_position(request):
    """
    Placeholder endpoint. If client-side only, this can be removed.
    If intended for server-side validation, implement logic here.
    """
    logger.warning("check_face_position endpoint called, but it's a placeholder.")
    return JsonResponse({"status": "ok", "message": "Face position check endpoint (placeholder)"})

@require_http_methods(["GET"])
@login_required # Ensure only logged-in users can access this
def get_eligible_employees(request):
    """
    API endpoint to return a list of employees eligible to be team members.
    (Trainee, Junior Developer, Senior Developer)
    """
    try:
        eligible_employees = Employee.objects.filter(
            role__in=['TRAINEE', 'JUNIOR_DEVELOPER', 'SENIOR_DEVELOPER']
        ).values('id', 'name').order_by('name') # Get ID and Name, order by name

        employees_list = list(eligible_employees) # Convert QuerySet to a list of dicts

        logger.debug(f"Fetched {len(employees_list)} eligible employees for team members.")
        return JsonResponse({'status': 'success', 'employees': employees_list})
    except Exception as e:
        logger.exception("Error fetching eligible employees for team members:")
        return JsonResponse({'status': 'error', 'message': f'Failed to fetch eligible employees: {str(e)}'}, status=500)
