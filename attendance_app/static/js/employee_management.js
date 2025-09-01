// attendance_app/static/js/employee_management.js
// This file is now intentionally minimal as the core logic for
// initializing the delete modal has been moved to be called directly
// from employee_list.html, importing from common_utils.js.

// The CSRF token is now retrieved in employee_list.html's inline script
// and passed to initializeDeleteModal.

// You can use this file for any other employee-management specific logic
// that is NOT related to the delete modal, e.g., form validation for
// adding/editing employees, or client-side filtering/sorting of the table
// if not handled by backend AJAX calls.

document.addEventListener('DOMContentLoaded', function () {
    console.log("employee_management.js loaded. Delete modal logic is now handled via direct import in employee_list.html.");
});

