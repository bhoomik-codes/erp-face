/**
 * VIDHEMA ERP — Toast Notification System
 * Global `window.showToast(message, type, duration, title)` API
 *
 * Types:  'success' | 'error' | 'warning' | 'info'
 * Duration: milliseconds (default 3500)
 */
(function () {
  'use strict';

  const ICONS = {
    success: 'fa-solid fa-circle-check',
    error:   'fa-solid fa-circle-xmark',
    warning: 'fa-solid fa-triangle-exclamation',
    info:    'fa-solid fa-circle-info',
  };

  const TITLES = {
    success: 'Success',
    error:   'Error',
    warning: 'Warning',
    info:    'Info',
  };

  /**
   * Ensures the toast container exists in the DOM.
   * @returns {HTMLElement}
   */
  function getContainer() {
    let container = document.getElementById('toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toast-container';
      document.body.appendChild(container);
    }
    return container;
  }

  /**
   * Removes a toast element with an exit animation.
   * @param {HTMLElement} toastEl
   */
  function removeToast(toastEl) {
    if (!toastEl || toastEl._removing) return;
    toastEl._removing = true;
    toastEl.classList.add('toast-exit');
    toastEl.addEventListener('animationend', () => {
      if (toastEl.parentNode) {
        toastEl.parentNode.removeChild(toastEl);
      }
    }, { once: true });
  }

  /**
   * Shows a toast notification.
   * @param {string}  message  - Body text shown to the user.
   * @param {string}  type     - 'success' | 'error' | 'warning' | 'info'
   * @param {number}  duration - Auto-dismiss delay in ms (0 = no auto-dismiss).
   * @param {string}  [title]  - Optional override for the bold title line.
   */
  function showToast(message, type = 'info', duration = 3500, title = null) {
    const validTypes = ['success', 'error', 'warning', 'info'];
    if (!validTypes.includes(type)) type = 'info';

    const container = getContainer();

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'polite');

    const iconClass  = ICONS[type];
    const toastTitle = title || TITLES[type];

    toast.innerHTML = `
      <span class="toast-icon"><i class="${iconClass}"></i></span>
      <div class="toast-body">
        <div class="toast-title">${escapeHtml(toastTitle)}</div>
        <div class="toast-msg">${escapeHtml(message)}</div>
      </div>
      <button class="toast-close" aria-label="Dismiss notification">
        <i class="fa-solid fa-xmark"></i>
      </button>
    `;

    // Close button
    toast.querySelector('.toast-close').addEventListener('click', () => {
      removeToast(toast);
    });

    container.appendChild(toast);

    // Auto-dismiss
    if (duration > 0) {
      setTimeout(() => removeToast(toast), duration);
    }

    return toast;
  }

  /**
   * Basic HTML escaper to prevent XSS from toast messages.
   * @param {string} str
   * @returns {string}
   */
  function escapeHtml(str) {
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return String(str).replace(/[&<>"']/g, m => map[m]);
  }

  // -------------------------------------------------------
  // Legacy compatibility shim:
  // The old code uses `window.displayMessage(messagesDiv, message, type)`.
  // This shim routes those calls to showToast transparently.
  // -------------------------------------------------------
  function displayMessage(messagesDiv, message, type) {
    const toastType = type === 'success' ? 'success' : type === 'error' ? 'error' : 'info';
    showToast(message, toastType);

    // Also update the legacy div if it exists (for Django form error rendering compatibility)
    if (messagesDiv) {
      const el = document.createElement('div');
      el.style.cssText = 'display:none';
      messagesDiv.appendChild(el);
      setTimeout(() => { if (el.parentNode) el.parentNode.removeChild(el); }, 100);
    }
  }

  // Expose globally
  window.showToast    = showToast;
  window.displayMessage = displayMessage;

})();
