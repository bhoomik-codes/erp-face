document.addEventListener('DOMContentLoaded', function () {
    console.log("DOMContentLoaded fired. Initializing admin scripts...");

    const messagesDiv = document.getElementById('messages'); // Assuming admin_dashboard.html has a messages div

    // displayMessage is now global (defined in common_utils.js without 'export')
    // and can be called directly via window.displayMessage.
    // We define a local proxy function for convenience if the messagesDiv exists.
    function localDisplayMessage(message, type) {
        if (messagesDiv && typeof window.displayMessage === 'function') {
            window.displayMessage(messagesDiv, message, type); // Call the global utility
        } else if (messagesDiv) {
            // Fallback if global displayMessage isn't loaded yet
            messagesDiv.innerHTML = `<div class="p-3 rounded-md mb-4 text-center ${type === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}">
                ${message}
            </div>`;
            setTimeout(() => {
                messagesDiv.innerHTML = '';
            }, 5000);
        } else {
            console.warn("Messages div not found or global displayMessage not available. Message: ", message);
        }
    }


    // --- Dashboard Filtering Logic ---
    const filterButtons = document.querySelectorAll('.filter-button');
    const totalAttendanceHoursCard = document.getElementById('totalAttendanceHoursCard');
    const totalOvertimeHoursCard = document.getElementById('totalOvertimeHoursCard');
    const totalAbsenteesCard = document.getElementById('totalAbsenteesCard');
    const topAbsenteesList = document.getElementById('topAbsenteesList');
    const topMaxAttendanceList = document.getElementById('topMaxAttendanceList');
    const topOvertimeList = document.getElementById('topOvertimeList');
    const topAbsenteesPeriodDisplay = document.getElementById('topAbsenteesPeriodDisplay');
    const topMaxAttendancePeriodDisplay = document.getElementById('topMaxAttendancePeriodDisplay');
    const topOvertimePeriodDisplay = document.getElementById('topOvertimePeriodDisplay');

    async function updateDashboardData(period) {
        console.log(`Updating dashboard for period: ${period}`);

        // Update active state of buttons by directly manipulating Tailwind classes
        filterButtons.forEach(button => {
            if (button.dataset.period === period) {
                // Add active styles
                button.classList.add('bg-red-600', 'text-white');
                // Remove inactive styles
                button.classList.remove('bg-white', 'text-[#417893]', 'hover:bg-red-100', 'hover:text-red-600');
            } else {
                // Add inactive styles
                button.classList.add('bg-white', 'text-[#417893]', 'hover:bg-red-100', 'hover:text-red-600');
                // Remove active styles
                button.classList.remove('bg-red-600', 'text-white');
            }
        });

        try {
            // Show a loading indicator by dimming the lists
            if (topAbsenteesList) topAbsenteesList.classList.add('opacity-50', 'pointer-events-none');
            if (topMaxAttendanceList) topMaxAttendanceList.classList.add('opacity-50', 'pointer-events-none');
            if (topOvertimeList) topOvertimeList.classList.add('opacity-50', 'pointer-events-none');

            // Fetch data from the Django backend
            const response = await fetch(`/attendance/get-dashboard-data/?period=${period}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();

            // Update main cards
            if (totalAttendanceHoursCard) totalAttendanceHoursCard.querySelector('h3').textContent = data.total_attendance_hours_all + ' hrs';
            if (totalOvertimeHoursCard) totalOvertimeHoursCard.querySelector('h3').textContent = data.total_overtime_all + ' hrs';
            if (totalAbsenteesCard) totalAbsenteesCard.querySelector('h3').textContent = data.total_absentees_count;

            // Update lists HTML
            if (topAbsenteesList) topAbsenteesList.innerHTML = data.top_5_absentees_html;
            if (topMaxAttendanceList) topMaxAttendanceList.innerHTML = data.top_5_max_attendance_html;
            if (topOvertimeList) topOvertimeList.innerHTML = data.top_5_overtime_html;

            // Update period displays in titles
            const periodDisplayText = period.charAt(0).toUpperCase() + period.slice(1);
            if (topAbsenteesPeriodDisplay) topAbsenteesPeriodDisplay.textContent = `Current ${periodDisplayText}`;
            if (topMaxAttendancePeriodDisplay) topMaxAttendancePeriodDisplay.textContent = `Total Hours Current ${periodDisplayText}`;
            if (topOvertimePeriodDisplay) topOvertimePeriodDisplay.textContent = `Current ${periodDisplayText}`;

            console.log("Dashboard data updated successfully.");

        } catch (error) {
            console.error('Error fetching dashboard data:', error);
            localDisplayMessage('Failed to load dashboard data. Please try again.', 'error');
        } finally {
            // Hide loading indicator
            if (topAbsenteesList) topAbsenteesList.classList.remove('opacity-50', 'pointer-events-none');
            if (topMaxAttendanceList) topMaxAttendanceList.classList.remove('opacity-50', 'pointer-events-none');
            if (topOvertimeList) topOvertimeList.classList.remove('opacity-50', 'pointer-events-none');
        }
    }

    // Attach event listeners to filter buttons
    filterButtons.forEach(button => {
        button.addEventListener('click', function () {
            const period = this.dataset.period;
            updateDashboardData(period);
        });
    });

    // Initial load for the dashboard with the default period (e.g., 'month')
    // This assumes your Django view passes an initial 'filter_period' to set the active button on load.
    // If not, you might need to manually trigger it with a default:
    // updateDashboardData('month'); // You might uncomment this if your Django view doesn't set an initial filter_period
});
