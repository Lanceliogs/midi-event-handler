/**
 * Toast notification module.
 */

import { escapeHtml } from './utils.js';

const TOAST_DURATIONS = {
  success: 3000,
  info: 3000,
  warning: 5000,
  error: 10000,
};

function createToastContainer() {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    
    const header = document.createElement('div');
    header.className = 'toast-header hidden';
    header.innerHTML = `
      <span class="toast-count"></span>
      <button class="toast-dismiss-all">Dismiss All</button>
    `;
    header.querySelector('.toast-dismiss-all').addEventListener('click', dismissAll);
    container.appendChild(header);
    
    const list = document.createElement('div');
    list.className = 'toast-list';
    container.appendChild(list);
    
    document.body.appendChild(container);
  }
  return container;
}

function getToastList() {
  const container = createToastContainer();
  return container.querySelector('.toast-list');
}

function updateToastHeader() {
  const container = document.getElementById('toast-container');
  if (!container) return;
  
  const header = container.querySelector('.toast-header');
  const list = container.querySelector('.toast-list');
  const count = list ? list.children.length : 0;
  
  if (count > 1) {
    header.classList.remove('hidden');
    header.querySelector('.toast-count').textContent = `${count} notifications`;
  } else {
    header.classList.add('hidden');
  }
}

export function dismissAll() {
  const list = document.querySelector('.toast-list');
  if (!list) return;
  
  const toasts = list.querySelectorAll('.toast');
  toasts.forEach(toast => {
    if (toast.dataset.timeoutId) {
      clearTimeout(parseInt(toast.dataset.timeoutId));
    }
    toast.remove();
  });
  
  updateToastHeader();
}

export function dismiss(toastOrButton) {
  const toast = toastOrButton.closest ? toastOrButton.closest('.toast') : toastOrButton;
  if (!toast) return;
  
  if (toast.dataset.timeoutId) {
    clearTimeout(parseInt(toast.dataset.timeoutId));
  }
  
  toast.classList.remove('toast-show');
  toast.classList.add('toast-hide');
  setTimeout(() => {
    toast.remove();
    updateToastHeader();
  }, 300);
}

export function showErrorDetail(detail, errors = null) {
  if (!detail && !errors) return;
  
  let bodyContent;
  if (errors && errors.length > 0) {
    // Format errors with bold short message
    bodyContent = errors.map(err => {
      const short = err.short || '';
      const full = err.detail || err.short || '';
      return `<div class="error-item"><h4>${escapeHtml(short)}</h4><pre class="error-detail">${escapeHtml(full)}</pre></div>`;
    }).join('<hr>');
  } else {
    bodyContent = `<pre class="error-detail">${escapeHtml(detail)}</pre>`;
  }
  
  const modal = document.createElement('div');
  modal.className = 'modal-overlay';
  modal.innerHTML = `
    <div class="modal">
      <div class="modal-header">
        <h3>Error Details</h3>
        <button class="modal-close">&times;</button>
      </div>
      <div class="modal-body">
        ${bodyContent}
      </div>
      <div class="modal-footer">
        <button class="btn btn-secondary copy-btn">Copy to Clipboard</button>
        <button class="btn btn-primary close-btn">Close</button>
      </div>
    </div>
  `;
  
  const plainText = errors ? errors.map(e => e.detail || e.short).join('\n\n---\n\n') : detail;
  
  modal.querySelector('.modal-close').addEventListener('click', () => modal.remove());
  modal.querySelector('.close-btn').addEventListener('click', () => modal.remove());
  modal.querySelector('.copy-btn').addEventListener('click', (e) => {
    const btn = e.target;
    navigator.clipboard.writeText(plainText).then(() => {
      const originalText = btn.textContent;
      btn.textContent = 'Copied!';
      btn.disabled = true;
      setTimeout(() => {
        btn.textContent = originalText;
        btn.disabled = false;
      }, 2000);
    }).catch(err => {
      console.error('Failed to copy:', err);
      btn.textContent = 'Failed to copy';
    });
  });
  
  document.body.appendChild(modal);
}

/**
 * Show a toast notification.
 */
export function show(message, type = 'info', options = {}) {
  createToastContainer();
  const list = getToastList();
  const duration = options.persist ? 0 : (options.duration || TOAST_DURATIONS[type] || 3000);
  
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  
  const msgSpan = document.createElement('span');
  msgSpan.className = 'toast-message';
  msgSpan.textContent = message;
  toast.appendChild(msgSpan);
  
  if ((options.detail || options.errors) && type === 'error') {
    const detailBtn = document.createElement('button');
    detailBtn.className = 'toast-details';
    detailBtn.textContent = 'Details';
    detailBtn.addEventListener('click', () => showErrorDetail(options.detail, options.errors));
    toast.appendChild(detailBtn);
  }
  
  const closeBtn = document.createElement('button');
  closeBtn.className = 'toast-close';
  closeBtn.innerHTML = '&times;';
  closeBtn.addEventListener('click', () => dismiss(toast));
  toast.appendChild(closeBtn);
  
  list.appendChild(toast);
  updateToastHeader();
  
  requestAnimationFrame(() => {
    toast.classList.add('toast-show');
  });
  
  if (duration > 0) {
    toast.dataset.timeoutId = setTimeout(() => dismiss(toast), duration);
  }
  
  return toast;
}

export function success(message) {
  return show(message, 'success');
}

export function error(message, detail = null) {
  return show(message, 'error', { detail });
}

export function warning(message) {
  return show(message, 'warning');
}

export function info(message) {
  return show(message, 'info');
}

/**
 * Handle toast from WebSocket message.
 */
export function handleWebSocket(data) {
  if (data.toast) {
    show(data.toast, data.toast_type || 'error', { 
      detail: data.toast_detail 
    });
  }
}

/**
 * Initialize HTMX integration for toasts.
 */
export function initHtmxIntegration() {
  document.body.addEventListener('htmx:afterRequest', (e) => {
    const xhr = e.detail.xhr;
    if (!xhr) return;
    
    const toastMessage = xhr.getResponseHeader('X-Toast');
    const toastType = xhr.getResponseHeader('X-Toast-Type') || 'info';
    
    let toastErrors = null;
    if (toastType === 'error' && xhr.responseText) {
      try {
        const data = JSON.parse(xhr.responseText);
        if (data.errors && data.errors.length > 0) {
          toastErrors = data.errors;
        }
      } catch (e) {
        // Not JSON, ignore
      }
    }
    
    if (toastMessage) {
      show(toastMessage, toastType, { errors: toastErrors });
    }
    
    if (!toastMessage && !e.detail.successful && xhr.status >= 400) {
      const errorMsg = xhr.responseText || `Request failed (${xhr.status})`;
      error(errorMsg);
    }
  });
}
