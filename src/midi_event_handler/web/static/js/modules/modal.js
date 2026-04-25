/**
 * Modal management module.
 */

export function open() {
  const backdrop = document.getElementById("modal-backdrop");
  if (backdrop) {
    backdrop.classList.remove("hidden");
  }
}

export function close() {
  const backdrop = document.getElementById("modal-backdrop");
  const container = document.getElementById("modal-container");
  if (backdrop) {
    backdrop.classList.add("hidden");
  }
  if (container) {
    container.innerHTML = "";
  }
}

/**
 * Initialize modal system with event delegation and HTMX integration.
 */
export function init() {
  // Event delegation for close buttons
  document.addEventListener('click', (e) => {
    const action = e.target.closest('[data-action="close-modal"]');
    if (action) {
      close();
    }
  });
  
  // Auto-open modal when content is loaded into modal-container
  document.addEventListener("htmx:afterSwap", function (event) {
    const target = event.detail.target;
    if (!target) return;
    
    if (target.id === "modal-container" && target.innerHTML.trim()) {
      open();
    }
  });
}

// Backwards compatibility alias
export const initHtmxIntegration = init;
