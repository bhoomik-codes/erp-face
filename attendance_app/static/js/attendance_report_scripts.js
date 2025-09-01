// Ensure jQuery is loaded before this script
$(document).ready(function () {
    // Initialize Select2 for the employee dropdown with full previous functionality
    $('.employee-select').select2({
        placeholder: "Search and select employees",
        allowClear: true,
        width: '100%',
        theme: 'default',
        matcher: function (params, data) {
            if ($.trim(params.term) === '') {
                return data;
            }
            if (typeof data.text === 'undefined') {
                return null;
            }
            const searchTerm = params.term.toLowerCase();
            const text = data.text.toLowerCase();
            const id = $(data.element).val().toLowerCase();

            if (text.includes(searchTerm) || id.includes(searchTerm)) {
                return data;
            }
            return null;
        }
    });

    /**
     * Function to fetch and update the attendance table body using AJAX.
     */
    async function updateAttendanceTable() {
        console.log("🔄 Fetching updated attendance table HTML from backend...");
        const tableBody = document.getElementById('attendanceTableBody');
        const loadingOverlay = document.getElementById('attendanceTableLoadingOverlay');
        const messagesDiv = document.getElementById('messages');

        if (!tableBody) {
            console.error("Error: tbody element with ID 'attendanceTableBody' not found.");
            return;
        }

        // Show loading indicator
        if (loadingOverlay) {
            loadingOverlay.style.display = 'flex';
        } else {
            tableBody.classList.add('opacity-50', 'pointer-events-none');
        }

        const form = document.getElementById('attendanceFilterForm');
        const formData = new FormData(form);
        const params = new URLSearchParams();
        const sortButton = document.querySelector('.sort-btn.active');
        const sort_by = sortButton ? sortButton.dataset.sort : 'date';
        const sort_order = sortButton ? sortButton.dataset.order : 'asc';

        for (const [key, value] of formData.entries()) {
            if (value !== '') {
                params.append(key, value);
            }
        }
        params.append('sort_by', sort_by);
        params.append('sort_order', sort_order);

        const url = `/attendance/get-attendance-table/?${params.toString()}`;

        try {
            const response = await fetch(url);
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
            }
            const data = await response.json();

            if (data.html) {
                $('#attendanceTableBody').html(data.html);
                console.log("✅ Attendance table updated successfully.");
            } else {
                console.warn("Received empty HTML from backend for attendance table.");
                $('#attendanceTableBody').html('<tr><td colspan="10" class="px-6 py-4 text-center text-gray-500">No records found.</td></tr>');
            }
        } catch (error) {
            console.error('❌ Error fetching updated attendance table:', error);
            $('#attendanceTableBody').html('<tr><td colspan="10" class="px-6 py-4 text-center text-red-500">Failed to load attendance data. Please try again.</td></tr>');
            if (messagesDiv && typeof window.displayMessage === 'function') {
                window.displayMessage(messagesDiv, "Failed to load attendance records. Please try again.", 'error');
            } else {
                console.warn('displayMessage function not found or messages div not present. Cannot show user-friendly error message.');
            }
        } finally {
            if (loadingOverlay) {
                loadingOverlay.style.display = 'none';
            } else {
                tableBody.classList.remove('opacity-50', 'pointer-events-none');
            }
        }
    }

    // Attach event listener to the form's submit event
    $('#attendanceFilterForm').on('submit', function (e) {
        e.preventDefault();
        updateAttendanceTable();
    });

    /**
     * Attaches click listeners to table headers for sorting.
     */
    function setupSorting() {
        $('th[data-sort]').on('click', function () {
            const currentOrder = $(this).data('order') || 'asc';
            const newOrder = currentOrder === 'asc' ? 'desc' : 'asc';

            // Remove 'active' and 'order' from all headers
            $('th[data-sort]').removeClass('active').data('order', null);

            // Add 'active' and 'order' to the clicked header
            $(this).addClass('active').data('order', newOrder);

            // Update the display of sort arrows
            $('th[data-sort]').find('.sort-icon').removeClass('fa-sort-up fa-sort-down').addClass('fa-sort');
            if (newOrder === 'asc') {
                $(this).find('.sort-icon').removeClass('fa-sort').addClass('fa-sort-up');
            } else {
                $(this).find('.sort-icon').removeClass('fa-sort').addClass('fa-sort-down');
            }

            updateAttendanceTable();
        });
    }

    /**
     * Global function to clear all filter fields and refresh the table.
     */
    window.clearFilters = function () {
        $('#start_date').val('');
        $('#end_date').val('');
        $('.employee-select').val(null).trigger('change');
        $('#attendance_type').val('');
        $('#total_hours_lt').val('');
        // Reset sorting
        $('th[data-sort]').removeClass('active').data('order', null);
        $('th[data-sort]').find('.sort-icon').removeClass('fa-sort-up fa-sort-down').addClass('fa-sort');
        updateAttendanceTable();
    };

    /**
     * Function to trigger attendance report download.
     * @param {string} format - The desired export format ('csv', 'xlsx', 'pdf').
     */
    function downloadReport(format) {
        const form = document.getElementById('attendanceFilterForm');
        const formData = new FormData(form);
        const params = new URLSearchParams();

        for (const [key, value] of formData.entries()) {
            if (value !== '') {
                params.append(key, value);
            }
        }

        let url = '';
        if (format === 'csv') {
            url = `/attendance/export-attendance-csv/?${params.toString()}`;
        } else if (format === 'xlsx') {
            url = `/attendance/export-attendance-xlsx/?${params.toString()}`;
        } else if (format === 'pdf') {
            url = `/attendance/export-attendance-pdf/?${params.toString()}`;
        } else {
            console.error('Invalid export format:', format);
            return;
        }

        window.open(url, '_blank');
    }

    // Attach click listeners to export buttons
    $('#exportCsv').on('click', function () {
        downloadReport('csv');
    });

    $('#exportXlsx').on('click', function () {
        downloadReport('xlsx');
    });

    $('#exportPdf').on('click', function () {
        downloadReport('pdf');
    });


    // Initial calls on page load
    updateAttendanceTable();
    setupSorting();

    // Set intervals to periodically update the entire attendance table
    setInterval(updateAttendanceTable, 30000);
});
