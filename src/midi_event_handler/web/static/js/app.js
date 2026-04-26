/**
 * Main application entry point.
 * Imports and initializes all modules.
 */

import * as toast from './modules/toast.js';
import * as modal from './modules/modal.js';
import * as websocket from './modules/websocket.js';
import * as dropzone from './modules/dropzone.js';

// Export to window for HTMX hx-on handlers that need to call JS
// (hx-on::after-request="closeModal()" etc.)
window.closeModal = modal.close;
window.openModal = modal.open;

// Toast functions (for programmatic use from other scripts)
window.showToast = toast.show;
window.toastSuccess = toast.success;
window.toastError = toast.error;
window.toastWarning = toast.warning;
window.toastInfo = toast.info;

// Initialize on DOM ready
document.addEventListener("DOMContentLoaded", () => {
  // Initialize integrations
  toast.initHtmxIntegration();
  modal.initHtmxIntegration();
  
  // Connect WebSocket
  websocket.connect();
  
  // Initialize dropzone if present
  dropzone.init();
});

console.log("[App] Modules loaded");
