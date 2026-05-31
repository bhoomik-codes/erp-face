// attendance_app/static/js/admin_settings.js
// Location settings form + Leaflet map integration

document.addEventListener('DOMContentLoaded', function () {

    const latitudeInput       = document.getElementById('latitude');
    const longitudeInput      = document.getElementById('longitude');
    const radiusInput         = document.getElementById('radius');
    const locationSettingsForm = document.getElementById('locationSettingsForm');
    const saveBtn             = document.getElementById('btn-save-settings');
    const csrfToken           = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';

    let map          = null;
    let officeMarker = null;
    let radiusCircle = null;

    // ── Map initialisation ─────────────────────────────
    function initializeMap(lat, lng, zoom = 14) {
        if (map) { map.remove(); }

        map = L.map('map').setView([lat, lng], zoom);

        L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
            maxZoom: 19,
        }).addTo(map);

        map.on('click', function (e) {
            latitudeInput.value  = e.latlng.lat.toFixed(6);
            longitudeInput.value = e.latlng.lng.toFixed(6);
            updateMapMarkerAndCircle(e.latlng.lat, e.latlng.lng, parseFloat(radiusInput.value || 0));
        });

        setTimeout(() => map.invalidateSize(), 200);
    }

    // ── Map marker & radius circle ─────────────────────
    function updateMapMarkerAndCircle(lat, lng, radius) {
        if (!map) return;
        const latLng = L.latLng(lat, lng);

        if (officeMarker) {
            officeMarker.setLatLng(latLng);
        } else {
            officeMarker = L.marker(latLng)
                .addTo(map)
                .bindPopup('<strong>Office Location</strong>');
            officeMarker.openPopup();
        }

        if (radiusCircle) {
            radiusCircle.setLatLng(latLng).setRadius(radius);
        } else {
            radiusCircle = L.circle(latLng, {
                color:       '#4F46E5',
                fillColor:   '#4F46E5',
                fillOpacity: 0.12,
                radius:      radius,
                weight:      2,
            }).addTo(map);
        }

        map.setView(latLng, map.getZoom());
        map.invalidateSize();
    }

    // ── Fetch existing settings from backend ───────────
    async function fetchLocationSettings() {
        try {
            const response = await fetch('/attendance/api/get-location-settings/');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const data = await response.json();

            if (data.status === 'success'
                && data.latitude  !== undefined
                && data.longitude !== undefined
                && data.radius_meters !== undefined)
            {
                latitudeInput.value  = data.latitude;
                longitudeInput.value = data.longitude;
                radiusInput.value    = data.radius_meters;

                initializeMap(data.latitude, data.longitude);
                updateMapMarkerAndCircle(data.latitude, data.longitude, data.radius_meters);
            } else {
                // Default to Jaipur
                initializeMap(26.9124, 75.7873);
                window.showToast?.('No saved location found — please configure one.', 'info');
            }
        } catch (error) {
            console.error('Error fetching location settings:', error);
            initializeMap(26.9124, 75.7873);
            window.showToast?.(`Could not load saved settings: ${error.message}`, 'warning');
        }
    }

    // ── Validation ─────────────────────────────────────
    function validateInputs() {
        const lat    = parseFloat(latitudeInput.value);
        const lng    = parseFloat(longitudeInput.value);
        const radius = parseFloat(radiusInput.value);

        if (isNaN(lat) || lat < -90 || lat > 90) {
            window.showToast?.('Enter a valid latitude (−90 to 90).', 'error');
            latitudeInput.focus();
            return false;
        }
        if (isNaN(lng) || lng < -180 || lng > 180) {
            window.showToast?.('Enter a valid longitude (−180 to 180).', 'error');
            longitudeInput.focus();
            return false;
        }
        if (isNaN(radius) || radius <= 0) {
            window.showToast?.('Enter a positive radius value in metres.', 'error');
            radiusInput.focus();
            return false;
        }
        return true;
    }

    // ── Form submit ────────────────────────────────────
    if (locationSettingsForm) {
        locationSettingsForm.addEventListener('submit', async function (event) {
            event.preventDefault();

            if (!validateInputs()) return;

            const lat    = parseFloat(latitudeInput.value);
            const lng    = parseFloat(longitudeInput.value);
            const radius = parseFloat(radiusInput.value);

            // Loading state
            const originalHTML    = saveBtn.innerHTML;
            saveBtn.innerHTML     = '<i class="fa-solid fa-spinner fa-spin"></i> Saving…';
            saveBtn.disabled      = true;

            try {
                const response = await fetch('/attendance/api/save-location-settings/', {
                    method:  'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken':  csrfToken,
                    },
                    body: JSON.stringify({ latitude: lat, longitude: lng, radius_meters: radius }),
                });

                if (!response.ok) {
                    const errData = await response.json().catch(() => ({ message: 'Unknown error' }));
                    throw new Error(errData.message || `HTTP ${response.status}`);
                }

                const data = await response.json();

                if (data.status === 'success') {
                    window.showToast?.('Location settings saved successfully!', 'success');
                    updateMapMarkerAndCircle(lat, lng, radius);
                } else {
                    window.showToast?.(`Save failed: ${data.message || 'Unknown error'}`, 'error');
                }

            } catch (error) {
                console.error('Error saving settings:', error);
                window.showToast?.(`Could not save settings: ${error.message}`, 'error');
            } finally {
                saveBtn.innerHTML = originalHTML;
                saveBtn.disabled  = false;
            }
        });
    }

    // ── Live map preview as user types ─────────────────
    function tryUpdateMap() {
        const lat    = parseFloat(latitudeInput.value);
        const lng    = parseFloat(longitudeInput.value);
        const radius = parseFloat(radiusInput.value);
        if (!isNaN(lat) && !isNaN(lng) && !isNaN(radius) && radius > 0) {
            updateMapMarkerAndCircle(lat, lng, radius);
        }
    }

    latitudeInput?.addEventListener('input',  tryUpdateMap);
    longitudeInput?.addEventListener('input', tryUpdateMap);
    radiusInput?.addEventListener('input',    tryUpdateMap);

    // ── Boot ───────────────────────────────────────────
    fetchLocationSettings();
});
