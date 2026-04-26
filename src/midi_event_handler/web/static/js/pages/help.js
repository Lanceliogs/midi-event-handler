/**
 * Help page module.
 */

import { escapeHtml, copyToClipboard } from '../modules/utils.js';

async function viewLogs() {
  try {
    const resp = await fetch('/meh/api/logs?lines=500');
    const data = await resp.json();
    
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.innerHTML = `
      <div class="modal logs-modal">
        <div class="modal-header">
          <h3>Application Logs (last ${data.lines} of ${data.total_lines || data.lines} lines)</h3>
          <button class="modal-close">&times;</button>
        </div>
        <div class="modal-body">
          <pre class="logs-content">${escapeHtml(data.logs || 'No logs available')}</pre>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary copy-btn">Copy to Clipboard</button>
          <button class="btn btn-secondary download-btn">Download</button>
          <button class="btn btn-primary close-btn">Close</button>
        </div>
      </div>
    `;
    
    // Event listeners
    modal.querySelector('.modal-close').addEventListener('click', () => modal.remove());
    modal.querySelector('.close-btn').addEventListener('click', () => modal.remove());
    modal.querySelector('.download-btn').addEventListener('click', () => {
      window.location.href = '/meh/api/logs/download';
    });
    modal.querySelector('.copy-btn').addEventListener('click', (e) => {
      const logs = modal.querySelector('.logs-content').textContent;
      copyToClipboard(logs, e.target);
    });
    
    document.body.appendChild(modal);
  } catch (err) {
    alert('Failed to load logs: ' + err.message);
  }
}

// Initialize
const viewLogsBtn = document.getElementById('view-logs-btn');
if (viewLogsBtn) {
  viewLogsBtn.addEventListener('click', viewLogs);
}
