// attendance_app/static/js/common_utils.js
// --------------------------------------------------
// Shared utilities used across the admin interface.
// --------------------------------------------------

/**
 * Displays a message using the global toast system.
 * Maintains backward compatibility with the old `messagesDiv` signature.
 *
 * @param {HTMLElement|null} messagesDiv - Legacy parameter (ignored; kept for compat).
 * @param {string}  message - Text to display.
 * @param {string}  type    - 'success' | 'error' | 'warning' | 'info'
 */
function displayMessage(messagesDiv, message, type) {
    const toastType = type === 'success' ? 'success'
                    : type === 'error'   ? 'error'
                    : type === 'warning' ? 'warning'
                    : 'info';

    if (typeof window.showToast === 'function') {
        window.showToast(message, toastType);
    } else {
        // Fallback: console log if toast.js hasn't loaded yet
        console.info(`[${toastType.toUpperCase()}] ${message}`);
        // Try a simple alert for critical errors only
        if (toastType === 'error') {
            // Silently fail — don't disrupt UX with alert()
        }
    }
}

// Make globally accessible (legacy usage)
window.displayMessage = displayMessage;


/**
 * Initialises the delete-confirmation modal for employee deletion via AJAX.
 *
 * Requires in DOM:
 *   - Buttons with class 'delete-btn' and data-employee-id / data-employee-name
 *   - #deleteModal, #modalEmployeeName, #modalEmployeeId
 *   - #confirmDeleteBtn, #cancelDeleteBtn
 *
 * @param {string} csrfToken - Django CSRF token.
 */
function initializeDeleteModal(csrfToken) {
    window.initializeDeleteModal = initializeDeleteModal;
    const deleteButtons     = document.querySelectorAll('.delete-btn');
    const deleteModal       = document.getElementById('deleteModal');
    const modalEmployeeName = document.getElementById('modalEmployeeName');
    const modalEmployeeId   = document.getElementById('modalEmployeeId');
    const confirmDeleteBtn  = document.getElementById('confirmDeleteBtn');
    const cancelDeleteBtn   = document.getElementById('cancelDeleteBtn');

    let employeeIdToDelete = null;

    // ── Open modal on delete button click ──────────────
    deleteButtons.forEach(button => {
        button.addEventListener('click', function () {
            employeeIdToDelete = this.dataset.employeeId;
            const employeeName = this.dataset.employeeName;

            if (modalEmployeeName) modalEmployeeName.textContent = employeeName;
            if (modalEmployeeId)   modalEmployeeId.textContent   = employeeIdToDelete;
            if (deleteModal)       deleteModal.style.display = 'flex';
        });
    });

    // ── Confirm delete ─────────────────────────────────
    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener('click', async function () {
            if (!employeeIdToDelete) {
                window.showToast?.('No employee selected for deletion.', 'error');
                return;
            }

            // Button loading state
            const originalHTML = confirmDeleteBtn.innerHTML;
            confirmDeleteBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Deleting…';
            confirmDeleteBtn.disabled  = true;

            try {
                const response = await fetch(`/attendance/employee/delete/${employeeIdToDelete}/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken':  csrfToken,
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({}),
                });

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({ message: 'Unknown error' }));
                    throw new Error(errorData.message || `HTTP ${response.status}`);
                }

                const data = await response.json();

                if (data.status === 'success') {
                    window.showToast?.(
                        data.message || 'Employee deleted successfully.',
                        'success'
                    );

                    // Remove the table row
                    const row = document.querySelector(`button[data-employee-id="${employeeIdToDelete}"]`)?.closest('tr');
                    if (row) {
                        row.style.transition = 'opacity 0.3s, transform 0.3s';
                        row.style.opacity    = '0';
                        row.style.transform  = 'translateX(-12px)';
                        setTimeout(() => row.remove(), 300);
                    }

                    // Empty-state row if table is now empty
                    setTimeout(() => {
                        const tbody = document.querySelector('#employeeTableBody') || document.querySelector('.employee-table tbody');
                        if (tbody) {
                            const visibleRows = tbody.querySelectorAll('tr:not([style*="opacity: 0"])');
                            if (visibleRows.length === 0) {
                                tbody.innerHTML = `
                                    <tr id="emptyRow">
                                        <td colspan="5" class="text-center py-12" style="color:var(--clr-text-muted);">
                                            <i class="fa-solid fa-users-slash text-3xl mb-3 block" style="opacity:.35;"></i>
                                            No employees registered.
                                        </td>
                                    </tr>`;
                            }
                        }
                    }, 350);

                } else {
                    window.showToast?.(data.message || 'Deletion failed.', 'error');
                }

            } catch (error) {
                console.error('Delete error:', error);
                window.showToast?.(`Deletion failed: ${error.message}`, 'error');
            } finally {
                if (deleteModal) deleteModal.style.display = 'none';
                confirmDeleteBtn.innerHTML = originalHTML;
                confirmDeleteBtn.disabled  = false;
                employeeIdToDelete         = null;
            }
        });
    }

    // ── Cancel ─────────────────────────────────────────
    if (cancelDeleteBtn) {
        cancelDeleteBtn.addEventListener('click', () => {
            if (deleteModal) deleteModal.style.display = 'none';
            employeeIdToDelete = null;
        });
    }

    // ── Click-outside to close ─────────────────────────
    if (deleteModal) {
        deleteModal.addEventListener('click', (e) => {
            if (e.target === deleteModal) {
                deleteModal.style.display = 'none';
                employeeIdToDelete = null;
            }
        });
    }
}
