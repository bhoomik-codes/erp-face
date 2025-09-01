document.addEventListener('DOMContentLoaded', function () {
    const latitudeInput = document.getElementById('latitude');
    const longitudeInput = document.getElementById('longitude');
    const radiusInput = document.getElementById('radius');
    const locationSettingsForm = document.getElementById('locationSettingsForm');
    const messagesDiv = document.getElementById('messages');
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    let map = null;
    let officeMarker = null;
    let radiusCircle = null;

    // displayMessage is now global (defined in common_utils.js without 'export')
    // and should be called via window.displayMessage.
    function displayMessage(message, type) {
        if (messagesDiv && typeof window.displayMessage === 'function') {
            window.displayMessage(messagesDiv, message, type);
        } else if (messagesDiv) {
            // Fallback if global displayMessage isn't loaded yet
            messagesDiv.innerHTML = `<div class="message ${type}">${message}</div>`;
            setTimeout(() => {
                messagesDiv.innerHTML = '';
            }, 5000); // Message disappears after 5 seconds
        } else {
            console.warn("Messages div not found or global displayMessage not available. Message: ", message);
        }
    }

    /**
     * Initializes the Leaflet map.
     * @param {number} lat - Initial latitude for the map center.
     * @param {number} lng - Initial longitude for the map center.
     * @param {number} zoom - Initial zoom level for the map.
     */
    function initializeMap(lat, lng, zoom = 13) {
        if (map) {
            map.remove(); // Remove existing map if it was already initialized
        }
        map = L.map('map').setView([lat, lng], zoom);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);

        map.on('click', function (e) {
            latitudeInput.value = e.latlng.lat.toFixed(6);
            longitudeInput.value = e.latlng.lng.toFixed(6);
            updateMapMarkerAndCircle(e.latlng.lat, e.latlng.lng, parseFloat(radiusInput.value || 0));
        });

        // IMPORTANT: Invalidate map size after initialization to ensure tiles load correctly
        // This is crucial if the map container is initially hidden or its dimensions are not fully calculated
        // when the map is first created.
        map.invalidateSize();
    }

    /**
     * Updates the marker and circle on the map.
     * @param {number} lat - Latitude of the office location.
     * @param {number} lng - Longitude of the office location.
     * @param {number} radius - Radius in meters.
     */
    function updateMapMarkerAndCircle(lat, lng, radius) {
        if (!map) return;

        const latLng = L.latLng(lat, lng);

        if (officeMarker) {
            officeMarker.setLatLng(latLng);
        } else {
            officeMarker = L.marker(latLng).addTo(map)
                .bindPopup("Office Location").openPopup();
        }

        if (radiusCircle) {
            radiusCircle.setLatLng(latLng).setRadius(radius);
        } else {
            radiusCircle = L.circle(latLng, {
                color: 'blue',
                fillColor: '#30a0e0',
                fillOpacity: 0.2,
                radius: radius
            }).addTo(map);
        }
        map.setView(latLng, map.getZoom()); // Center map on the updated location
        map.invalidateSize(); // Also invalidate size on updates, just in case
    }

    /**
     * Fetches current location settings from the backend.
     */
    async function fetchLocationSettings() {
        try {
            const response = await fetch('/attendance/api/get-location-settings/');
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(`HTTP error! status: ${response.status}. Server message: ${errorData.message || JSON.stringify(errorData)}`);
            }
            const data = await response.json();
            if (data.status === 'success' && data.latitude !== undefined && data.longitude !== undefined && data.radius_meters !== undefined) {
                latitudeInput.value = data.latitude;
                longitudeInput.value = data.longitude;
                radiusInput.value = data.radius_meters; // Use radius_meters from backend

                initializeMap(data.latitude, data.longitude);
                updateMapMarkerAndCircle(data.latitude, data.longitude, data.radius_meters);
            } else {
                initializeMap(26.9124, 75.7873); // Default to Jaipur, India
                displayMessage('No location settings found. Please set them.', 'info');
            }
        } catch (error) {
            console.error('Error fetching location settings:', error);
            initializeMap(26.9124, 75.7873); // Default to Jaipur if fetch fails
            displayMessage('Failed to load existing settings. ' + error.message, 'error');
        }
    }

    /**
     * Validates the input fields for location settings.
     * @returns {boolean} True if inputs are valid, false otherwise.
     */
    function validateInputs() {
        const latitude = parseFloat(latitudeInput.value);
        const longitude = parseFloat(longitudeInput.value);
        const radius = parseFloat(radiusInput.value);

        if (isNaN(latitude) || latitude < -90 || latitude > 90) {
            displayMessage('Please enter a valid latitude between -90 and 90.', 'error');
            return false;
        }
        if (isNaN(longitude) || longitude < -180 || longitude > 180) {
            displayMessage('Please enter a valid longitude between -180 and 180.', 'error');
            return false;
        }
        if (isNaN(radius) || radius <= 0) {
            displayMessage('Please enter a valid positive radius.', 'error');
            return false;
        }
        return true;
    }


    /**
     * Handles saving location settings.
     * @param {Event} event - The form submission event.
     */
    locationSettingsForm.addEventListener('submit', async function (event) {
        event.preventDefault();

        if (!validateInputs()) {
            return; // Stop submission if validation fails
        }

        const latitude = parseFloat(latitudeInput.value);
        const longitude = parseFloat(longitudeInput.value);
        const radius = parseFloat(radiusInput.value);

        try {
            const response = await fetch('/attendance/api/save-location-settings/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    latitude: latitude,
                    longitude: longitude,
                    radius_meters: radius
                })
            });
            console.log(response);
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({message: 'Failed to parse error response.'}));
                throw new Error(`HTTP error! status: ${response.status}. Server message: ${errorData.message || JSON.stringify(errorData)}`);
            }

            const data = await response.json();
            if (data.status === 'success') {
                displayMessage('Location settings saved successfully!', 'success');
                updateMapMarkerAndCircle(latitude, longitude, radius);
            } else {
                displayMessage('Failed to save settings: ' + data.message, 'error');
            }
        } catch (error) {
            console.error('Error saving location settings:', error);
            displayMessage('An error occurred while saving settings: ' + error.message, 'error');
        }
    });

    // Event listeners for input changes to update map dynamically
    latitudeInput.addEventListener('input', () => {
        const lat = parseFloat(latitudeInput.value);
        const lng = parseFloat(longitudeInput.value);
        const rad = parseFloat(radiusInput.value);
        if (!isNaN(lat) && !isNaN(lng) && !isNaN(rad)) {
            updateMapMarkerAndCircle(lat, lng, rad);
        }
    });

    longitudeInput.addEventListener('input', () => {
        const lat = parseFloat(latitudeInput.value);
        const lng = parseFloat(longitudeInput.value);
        const rad = parseFloat(radiusInput.value);
        if (!isNaN(lat) && !isNaN(lng) && !isNaN(rad)) {
            updateMapMarkerAndCircle(lat, lng, rad);
        }
    });

    radiusInput.addEventListener('input', () => {
        const lat = parseFloat(latitudeInput.value);
        const lng = parseFloat(longitudeInput.value);
        const rad = parseFloat(radiusInput.value);
        if (!isNaN(lat) && !isNaN(lng) && !isNaN(rad) && rad > 0) {
            updateMapMarkerAndCircle(lat, lng, rad);
        }
    });

    // Initial fetch of settings when the page loads
    fetchLocationSettings();
});
