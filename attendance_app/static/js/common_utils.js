// attendance_app/static/js/common_utils.js

/**
 * Displays a message to the user in a specified messages div.
 * @param {HTMLElement} messagesDiv - The div element to display messages in.
 * @param {string} message - The message to display.
 * @param {string} type - 'success' or 'error'.
 */
function displayMessage(messagesDiv, message, type) {
    if (messagesDiv) {
        // Create a new div element for the message to avoid XSS if message contains HTML
        const messageElement = document.createElement('div');
        messageElement.classList.add('p-3', 'rounded-md', 'mb-4', 'text-center');
        if (type === 'success') {
            messageElement.classList.add('bg-green-100', 'text-green-700');
        } else {
            messageElement.classList.add('bg-red-100', 'text-red-700');
        }
        messageElement.textContent = message; // Use textContent to prevent XSS

        // Clear any existing messages before adding the new one
        messagesDiv.innerHTML = '';
        messagesDiv.appendChild(messageElement);

        setTimeout(() => {
            if (messagesDiv.contains(messageElement)) {
                messagesDiv.removeChild(messageElement);
            }
        }, 5000); // Message disappears after 5 seconds
    } else {
        console.warn("Messages div not found for general messages. Message: ", message);
    }
}

// Make displayMessage globally accessible
window.displayMessage = displayMessage;

/**
 * Initializes generic delete confirmation modal logic for employee deletion.
 * Assumes certain DOM elements exist with specific IDs/data attributes:
 * - Elements with class 'delete-btn'
 * - Element with ID 'deleteModal'
 * - Element with ID 'modalEmployeeName'
 * - Element with ID 'modalEmployeeId'
 * - Element with ID 'confirmDeleteBtn'
 * - Element with ID 'cancelDeleteBtn'
 * - Element with ID 'messages' (for displaying messages)
 * - Element with class 'employee-table tbody' (for checking empty table)
 * @param {string} csrfToken - The CSRF token for AJAX requests.
 */
export function initializeDeleteModal(csrfToken) {
    const deleteButtons = document.querySelectorAll('.delete-btn');
    const deleteModal = document.getElementById('deleteModal');
    const modalEmployeeName = document.getElementById('modalEmployeeName');
    const modalEmployeeId = document.getElementById('modalEmployeeId');
    const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
    const cancelDeleteBtn = document.getElementById('cancelDeleteBtn');
    const messagesDiv = document.getElementById('messages'); // Main messages div

    let employeeIdToDelete = null;

    // Add click listeners to all delete buttons
    deleteButtons.forEach(button => {
        button.addEventListener('click', function () {
            employeeIdToDelete = this.dataset.employeeId;
            const employeeName = this.dataset.employeeName;

            if (modalEmployeeName && modalEmployeeId) {
                modalEmployeeName.textContent = employeeName;
                modalEmployeeId.textContent = employeeIdToDelete;
            }
            if (deleteModal) {
                deleteModal.style.display = 'flex'; // Show modal
            }
        });
    });

    // Handle confirm delete button click
    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener('click', async function () {
            if (!employeeIdToDelete) {
                displayMessage(messagesDiv, 'Error: No employee selected for deletion.', 'error');
                return;
            }

            try {
                const response = await fetch(`/attendance/employee/delete/${employeeIdToDelete}/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrfToken,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({}) // Send an empty JSON body
                });

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({message: 'Failed to parse error response.'}));
                    throw new Error(`HTTP error! status: ${response.status}, message: ${errorData.message || 'Unknown error'}`);
                }

                const data = await response.json();
                if (data.status === 'success') {
                    displayMessage(messagesDiv, data.message, 'success');
                    // Remove the row from the table
                    const row = document.querySelector(`button[data-employee-id="${employeeIdToDelete}"]`).closest('tr');
                    if (row) {
                        row.remove();
                    }
                    // If the table becomes empty, display the "No employees" message
                    const tbody = document.querySelector('.employee-table tbody');
                    if (tbody && tbody.children.length === 0) {
                        const noRecordsRow = document.createElement('tr');
                        noRecordsRow.innerHTML = '<td colspan="4" class="text-center py-4 text-gray-500">No employees registered yet.</td>';
                        tbody.appendChild(noRecordsRow);
                    }
                } else {
                    displayMessage(messagesDiv, data.message, 'error');
                }
            } catch (error) {
                console.error('Error deleting employee:', error);
                displayMessage(messagesDiv, 'An error occurred during deletion: ' + error.message, 'error');
            } finally {
                if (deleteModal) {
                    deleteModal.style.display = 'none'; // Hide modal
                }
                employeeIdToDelete = null; // Clear selected employee
            }
        });
    }

    // Handle cancel delete button click
    if (cancelDeleteBtn) {
        cancelDeleteBtn.addEventListener('click', function () {
            if (deleteModal) {
                deleteModal.style.display = 'none'; // Hide modal
            }
            employeeIdToDelete = null; // Clear selected employee
        });
    }

    // Close modal if the user clicks outside of it
    if (deleteModal) {
        window.addEventListener('click', function (event) {
            if (event.target === deleteModal) {
                deleteModal.style.display = 'none';
                employeeIdToDelete = null;
            }
        });
    }
}

