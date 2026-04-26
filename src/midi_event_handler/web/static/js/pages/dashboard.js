/**
 * Dashboard page - real-time show monitoring
 */

import { getSocket } from '../modules/websocket.js';
import { noteToName } from '../modules/utils.js';

let timerInterval = null;
let reconcileInterval = null;
let startedAt = null;
let handlerStartTimes = {};  // Track when each handler's event started
const MAX_MIDI_ENTRIES = 10;
const MAX_LOG_ENTRIES = 20;
const RECONCILE_INTERVAL_MS = 5000;  // Refresh from server every 5s

// =============================================================================
// Timers (Show + Handler countdowns)
// =============================================================================

function formatDuration(seconds) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

function formatTimeOfDay(timestamp) {
  const date = new Date(timestamp * 1000);
  return `${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}:${date.getSeconds().toString().padStart(2, '0')}`;
}

function updateTimerNumerics() {
  const now = Date.now() / 1000;
  
  // Update show timer
  const showTimerEl = document.getElementById('show-timer');
  if (showTimerEl && startedAt) {
    const elapsed = now - startedAt;
    showTimerEl.textContent = formatDuration(elapsed);
  }
  
  // Update handler timers (elapsed + remaining text only)
  document.querySelectorAll('.handler-card.active').forEach(card => {
    const eventType = card.dataset.eventType;
    const startTime = handlerStartTimes[eventType];
    if (!startTime) return;
    
    const elapsed = now - startTime;
    const durationMax = parseFloat(card.dataset.durationMax) || 0;
    
    // Update elapsed text
    const elapsedEl = card.querySelector('.elapsed');
    if (elapsedEl) {
      elapsedEl.textContent = `${Math.floor(elapsed)}s`;
    }
    
    // Update remaining text (bar is CSS animated)
    if (durationMax > 0) {
      const remaining = Math.max(0, durationMax - elapsed);
      const remainingEl = card.querySelector('.remaining');
      if (remainingEl) {
        remainingEl.textContent = `${Math.floor(remaining)}s left`;
      }
    }
  });
}

function initProgressBarAnimations() {
  // Set up CSS animations for progress bars based on remaining time
  document.querySelectorAll('.handler-card.active').forEach(card => {
    const eventType = card.dataset.eventType;
    const startTime = handlerStartTimes[eventType];
    const durationMax = parseFloat(card.dataset.durationMax) || 0;
    
    if (!startTime || !durationMax) return;
    
    const now = Date.now() / 1000;
    const elapsed = now - startTime;
    const remaining = Math.max(0, durationMax - elapsed);
    const currentProgress = (remaining / durationMax) * 100;
    
    const progressBar = card.querySelector('.countdown-progress');
    if (progressBar) {
      // Reset any existing transition
      progressBar.style.transition = 'none';
      progressBar.style.width = `${currentProgress}%`;
      
      // Force reflow to apply initial state
      progressBar.offsetHeight;
      
      // Now set transition and animate to 0
      progressBar.style.transition = `width ${remaining}s linear`;
      progressBar.style.width = '0%';
    }
  });
}

function initTimers() {
  // Get show start time
  const container = document.getElementById('dashboard-container');
  if (container && container.dataset.startedAt) {
    startedAt = parseFloat(container.dataset.startedAt);
  } else {
    startedAt = null;
  }
  
  // Get handler start times from data attributes
  handlerStartTimes = {};
  document.querySelectorAll('.handler-card.active').forEach(card => {
    const eventType = card.dataset.eventType;
    const eventStartedAt = card.dataset.eventStartedAt;
    if (eventType && eventStartedAt) {
      handlerStartTimes[eventType] = parseFloat(eventStartedAt);
    }
  });
  
  // Start CSS animations for progress bars
  initProgressBarAnimations();
  
  // Update numeric values every second (light on client)
  if (!timerInterval) {
    timerInterval = setInterval(updateTimerNumerics, 1000);
  }
  
  // Initial update
  updateTimerNumerics();
}

function stopTimers() {
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
  if (reconcileInterval) {
    clearInterval(reconcileInterval);
    reconcileInterval = null;
  }
  startedAt = null;
  handlerStartTimes = {};
}

// =============================================================================
// MIDI Input Display
// =============================================================================

function addMidiInput(port, notes, timestamp) {
  const display = document.getElementById('midi-input-display');
  if (!display) return;
  
  // Remove empty message
  const empty = display.querySelector('.midi-empty');
  if (empty) empty.remove();
  
  // Create entry
  const entry = document.createElement('div');
  entry.className = 'midi-entry new';
  
  const timeStr = formatTimeOfDay(timestamp);
  const noteNames = notes.map(n => `${n} (${noteToName(n)})`).join(', ');
  
  entry.innerHTML = `
    <span class="midi-time">${timeStr}</span>
    <span class="midi-port">${port}</span>
    <span class="midi-notes">${noteNames}</span>
  `;
  
  // Add to top
  display.insertBefore(entry, display.firstChild);
  
  // Trigger animation
  requestAnimationFrame(() => entry.classList.remove('new'));
  
  // Limit entries
  while (display.children.length > MAX_MIDI_ENTRIES) {
    display.lastChild.remove();
  }
}

// =============================================================================
// Event Log
// =============================================================================

function addLogEntry(eventName, action, timestamp) {
  const log = document.getElementById('event-log');
  if (!log) return;
  
  // Remove empty message
  const empty = log.querySelector('.log-empty');
  if (empty) empty.remove();
  
  // Create entry
  const entry = document.createElement('div');
  entry.className = `log-entry ${action} new`;
  
  const timeStr = formatTimeOfDay(timestamp);
  
  entry.innerHTML = `
    <span class="log-time">${timeStr}</span>
    <span class="log-action ${action}">${action.toUpperCase()}</span>
    <span class="log-event">${eventName}</span>
  `;
  
  // Add to top
  log.insertBefore(entry, log.firstChild);
  
  // Trigger animation
  requestAnimationFrame(() => entry.classList.remove('new'));
  
  // Limit entries
  while (log.children.length > MAX_LOG_ENTRIES) {
    log.lastChild.remove();
  }
}

// =============================================================================
// WebSocket Handlers
// =============================================================================

function handleWebSocketMessage(data) {
  // MIDI input
  if (data.midi_input) {
    addMidiInput(data.port, data.notes, data.timestamp);
  }
  
  // Event changes
  if (data.notify === 'event' && data.event_name) {
    addLogEntry(data.event_name, data.action, data.timestamp);
    
    // Refresh dashboard for active events display
    refreshDashboard();
  }
  
  // State changes (start/stop)
  if (data.notify === 'state') {
    refreshDashboard();
  }
}

async function refreshDashboard() {
  const container = document.getElementById('dashboard-area');
  if (!container) return;
  
  try {
    const resp = await fetch('/meh/ui/dashboard/status');
    if (resp.ok) {
      const html = await resp.text();
      container.innerHTML = html;
      
      // Reinitialize timers with new data
      initTimers();
    }
  } catch (err) {
    console.error('[Dashboard] Refresh failed:', err);
  }
}

// =============================================================================
// Initialize
// =============================================================================

function onDashboardLoaded() {
  console.log('[Dashboard] Content loaded, initializing timers...');
  initTimers();
}

function waitForDashboard() {
  const container = document.getElementById('dashboard-container');
  if (container) {
    console.log('[Dashboard] Content found, initializing...');
    onDashboardLoaded();
  } else {
    // Not loaded yet, wait and retry
    setTimeout(waitForDashboard, 50);
  }
}

function init() {
  console.log('[Dashboard] Initializing...');
  
  // Wait for dashboard content to be loaded
  waitForDashboard();
  
  // Listen for HTMX swaps (for refreshes)
  document.body.addEventListener('htmx:afterSwap', (e) => {
    if (e.detail.target.id === 'dashboard-area') {
      onDashboardLoaded();
    }
  });
  
  // Start periodic reconciliation (refresh from server)
  if (!reconcileInterval) {
    reconcileInterval = setInterval(() => {
      refreshDashboard();
    }, RECONCILE_INTERVAL_MS);
  }
  
  // Listen for WebSocket messages
  const checkSocket = setInterval(() => {
    const socket = getSocket();
    if (socket && socket.readyState === WebSocket.OPEN) {
      const currentHandler = socket.onmessage;
      socket.onmessage = (event) => {
        // Call original handler
        if (currentHandler) currentHandler(event);
        
        // Process for dashboard
        try {
          const data = JSON.parse(event.data);
          handleWebSocketMessage(data);
        } catch (e) {}
      };
      clearInterval(checkSocket);
    }
  }, 100);
  
  // Listen for state updates (from controls)
  document.body.addEventListener('update', refreshDashboard);
}

// Run on DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
