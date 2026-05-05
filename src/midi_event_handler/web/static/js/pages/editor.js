/**
 * Editor page module.
 */

import { escapeHtml, noteToName } from '../modules/utils.js';

// Event filtering
function filterEvents(query) {
  const q = query.toLowerCase().trim();
  const items = document.querySelectorAll('.event-item:not(.empty)');
  
  items.forEach(item => {
    const text = item.textContent.toLowerCase();
    item.style.display = text.includes(q) ? '' : 'none';
  });
}

function clearFilter() {
  const input = document.getElementById('events-filter');
  if (input) {
    input.value = '';
    filterEvents('');
    input.focus();
  }
}

// Dirty state tracking
function isDirty() {
  const container = document.querySelector('.editor-container');
  return container && container.dataset.dirty === 'true';
}

function updateDirtyIndicator() {
  const indicator = document.getElementById('dirty-indicator');
  if (indicator) {
    indicator.classList.toggle('hidden', !isDirty());
  }
}

// =============================================================================
// Notes Editor (Modal Form)
// =============================================================================

function syncNotesInput() {
  const badges = document.getElementById('notes-badges');
  const hiddenInput = document.getElementById('trigger-notes');
  if (!badges || !hiddenInput) return;
  
  const notes = Array.from(badges.querySelectorAll('.note-badge-edit'))
    .map(b => b.dataset.note)
    .filter(n => n);
  hiddenInput.value = notes.join(', ');
}

function createNoteBadge(noteNum, noteName) {
  const badge = document.createElement('span');
  badge.className = 'note-badge-edit';
  badge.dataset.note = noteNum;
  badge.innerHTML = `
    <span class="note-num">${noteNum}</span>
    <span class="note-name">${noteName}</span>
    <button type="button" class="note-delete" data-action="delete-note">&times;</button>
  `;
  return badge;
}

function startEditNote(badge) {
  const noteNum = badge.dataset.note;
  const input = document.createElement('input');
  input.type = 'text';
  input.className = 'note-input';
  input.value = noteNum;
  input.dataset.originalNote = noteNum;
  
  badge.replaceWith(input);
  input.focus();
  input.select();
  
  const finishEdit = async () => {
    const val = input.value.trim();
    if (!val) {
      input.remove();
      syncNotesInput();
      return;
    }
    
    const resolved = await resolveNote(val);
    if (resolved) {
      const newBadge = createNoteBadge(resolved.num, resolved.name);
      input.replaceWith(newBadge);
    } else {
      input.classList.add('error');
      input.focus();
      return;
    }
    syncNotesInput();
  };
  
  input.addEventListener('blur', finishEdit);
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      input.blur();
    } else if (e.key === 'Escape') {
      const original = input.dataset.originalNote;
      if (original) {
        resolveNote(original).then(resolved => {
          if (resolved) {
            input.replaceWith(createNoteBadge(resolved.num, resolved.name));
          }
        });
      } else {
        input.remove();
      }
      syncNotesInput();
    }
  });
}

function addNewNote() {
  const badges = document.getElementById('notes-badges');
  if (!badges) return;
  
  const input = document.createElement('input');
  input.type = 'text';
  input.className = 'note-input';
  input.placeholder = 'C4';
  
  badges.appendChild(input);
  input.focus();
  
  const finishAdd = async () => {
    const val = input.value.trim();
    if (!val) {
      input.remove();
      return;
    }
    
    const resolved = await resolveNote(val);
    if (resolved) {
      const newBadge = createNoteBadge(resolved.num, resolved.name);
      input.replaceWith(newBadge);
      syncNotesInput();
    } else {
      input.classList.add('error');
      input.focus();
    }
  };
  
  input.addEventListener('blur', finishAdd);
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      input.blur();
    } else if (e.key === 'Escape') {
      input.remove();
    }
  });
}

function deleteNote(deleteBtn) {
  const badge = deleteBtn.closest('.note-badge-edit');
  if (badge) {
    badge.remove();
    syncNotesInput();
  }
}

async function resolveNote(input) {
  try {
    const resp = await fetch(`/meh/ui/editor/resolve-note?note=${encodeURIComponent(input)}`);
    if (resp.ok) {
      return await resp.json();
    }
  } catch (err) {
    console.error('[ResolveNote] Error:', err);
  }
  return null;
}

// =============================================================================
// Inline MIDI Recording (Modal Form)
// =============================================================================

let isRecording = false;
let recordingPort = null;

async function abortRecording(port) {
  try {
    await fetch('/meh/ui/editor/record/abort', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ port })
    });
  } catch (err) {
    console.error('[Record] Abort error:', err);
  }
}

async function startRecording() {
  const portSelect = document.getElementById('trigger-port');
  const port = portSelect?.value;
  const recButton = document.querySelector('[data-action="record-notes"]');
  const modalFooter = recButton?.closest('.modal')?.querySelector('.modal-footer');
  const modalButtons = modalFooter?.querySelectorAll('button');
  const badges = document.getElementById('notes-badges');
  
  if (!port) {
    alert('Please select a trigger port first');
    return;
  }
  
  if (isRecording) return;
  isRecording = true;
  recordingPort = port;
  
  // Save original badges to restore on timeout/cancel
  const originalBadgesHtml = badges ? badges.innerHTML : '';
  
  const handleEsc = (e) => {
    if (e.key === 'Escape' && isRecording && recordingPort) {
      e.preventDefault();
      e.stopPropagation();
      abortRecording(recordingPort);
    }
  };
  document.addEventListener('keydown', handleEsc, true);
  
  recButton.classList.add('recording');
  modalButtons?.forEach(btn => btn.disabled = true);
  
  // Show recording indicator in badges area
  if (badges) {
    badges.innerHTML = '<span class="record-status-text">Recording... (ESC to cancel)</span>';
  }
  
  try {
    const resp = await fetch('/meh/ui/editor/record', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ port })
    });
    
    const data = await resp.json();
    
    if (data.notes && data.notes.length > 0) {
      // Resolve notes and create badges
      badges.innerHTML = '';
      for (const note of data.notes) {
        const resolved = await resolveNote(note);
        if (resolved) {
          badges.appendChild(createNoteBadge(resolved.num, resolved.name));
        }
      }
      syncNotesInput();
    } else if (data.timeout || data.aborted) {
      // Timeout or aborted: restore original notes
      badges.innerHTML = originalBadgesHtml;
    } else if (data.error) {
      badges.innerHTML = `<span class="record-status-text text-error">${data.error}</span>`;
      setTimeout(() => {
        if (badges.querySelector('.record-status-text')) {
          badges.innerHTML = originalBadgesHtml;
        }
      }, 3000);
    }
  } catch (err) {
    console.error('[Record] Error:', err);
    if (badges) {
      badges.innerHTML = '<span class="record-status-text text-error">Recording failed</span>';
      setTimeout(() => {
        if (badges.querySelector('.record-status-text')) {
          badges.innerHTML = originalBadgesHtml;
        }
      }, 3000);
    }
  } finally {
    document.removeEventListener('keydown', handleEsc, true);
    recButton.classList.remove('recording');
    modalButtons?.forEach(btn => btn.disabled = false);
    isRecording = false;
    recordingPort = null;
  }
}

// =============================================================================
// Quick Record (Event List)
// =============================================================================

let quickRecordingEvent = null;
let quickRecordingPort = null;

async function startQuickRecord(eventName, port) {
  if (quickRecordingEvent) return;
  quickRecordingEvent = eventName;
  quickRecordingPort = port;
  
  const recButton = document.querySelector(`[data-action="quick-record"][data-event="${eventName}"]`);
  const triggerNotes = document.querySelector(`.event-trigger-notes[data-event="${eventName}"]`);
  
  if (!recButton || !triggerNotes) return;
  
  const originalContent = triggerNotes.innerHTML;
  
  const handleEsc = (e) => {
    if (e.key === 'Escape' && quickRecordingEvent && quickRecordingPort) {
      e.preventDefault();
      e.stopPropagation();
      abortRecording(quickRecordingPort);
    }
  };
  document.addEventListener('keydown', handleEsc, true);
  
  recButton.classList.add('recording');
  triggerNotes.classList.add('recording');
  triggerNotes.innerHTML = '<span class="record-status-text">Recording... (ESC to cancel)</span>';
  
  try {
    const resp = await fetch('/meh/ui/editor/record', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ port })
    });
    
    const data = await resp.json();
    
    if (data.notes && data.notes.length > 0) {
      triggerNotes.innerHTML = '<span class="record-status-text">Saving...</span>';
      await saveQuickRecord(eventName, data.notes.join(','));
    } else if (data.timeout || data.aborted) {
      // Timeout or aborted: restore original notes
      triggerNotes.innerHTML = originalContent;
      triggerNotes.classList.remove('recording');
    } else if (data.error) {
      triggerNotes.innerHTML = `<span class="record-status-text text-error">${data.error}</span>`;
      setTimeout(() => {
        triggerNotes.innerHTML = originalContent;
        triggerNotes.classList.remove('recording');
      }, 3000);
    }
  } catch (err) {
    console.error('[QuickRecord] Error:', err);
    triggerNotes.innerHTML = '<span class="record-status-text text-error">Recording failed</span>';
    setTimeout(() => {
      triggerNotes.innerHTML = originalContent;
      triggerNotes.classList.remove('recording');
    }, 2000);
  } finally {
    document.removeEventListener('keydown', handleEsc, true);
    recButton.classList.remove('recording');
    quickRecordingEvent = null;
    quickRecordingPort = null;
  }
}

async function saveQuickRecord(eventName, notes) {
  const formData = new FormData();
  formData.append('notes', notes);
  
  try {
    const resp = await fetch(`/meh/ui/editor/event/${encodeURIComponent(eventName)}/trigger`, {
      method: 'POST',
      body: formData
    });
    
    if (resp.ok) {
      const html = await resp.text();
      document.getElementById('main-content').innerHTML = html;
      htmx.process(document.getElementById('main-content'));
      updateDirtyIndicator();
    }
  } catch (err) {
    console.error('[SaveQuickRecord] Error:', err);
  }
}

// =============================================================================
// Event Testing (PAD)
// =============================================================================

async function playEvent(eventName) {
  try {
    const resp = await fetch(`/meh/ui/editor/event/${encodeURIComponent(eventName)}/play`, {
      method: 'POST'
    });
    
    if (resp.ok) {
      const html = await resp.text();
      document.getElementById('main-content').innerHTML = html;
      htmx.process(document.getElementById('main-content'));
    } else {
      const data = await resp.json();
      console.error('[PlayEvent] Error:', data.error);
    }
  } catch (err) {
    console.error('[PlayEvent] Error:', err);
  }
}

async function stopEvent(eventName) {
  try {
    const resp = await fetch(`/meh/ui/editor/event/${encodeURIComponent(eventName)}/stop`, {
      method: 'POST'
    });
    
    if (resp.ok) {
      const html = await resp.text();
      document.getElementById('main-content').innerHTML = html;
      htmx.process(document.getElementById('main-content'));
    } else {
      const data = await resp.json();
      console.error('[StopEvent] Error:', data.error);
    }
  } catch (err) {
    console.error('[StopEvent] Error:', err);
  }
}

// =============================================================================
// Message CRUD
// =============================================================================

function getMessagesFromEditor(editorId) {
  const editor = document.getElementById(editorId);
  if (!editor) return [];
  
  const hiddenInput = document.getElementById(editor.dataset.target);
  if (!hiddenInput || !hiddenInput.value) return [];
  
  try {
    return JSON.parse(hiddenInput.value);
  } catch (e) {
    return [];
  }
}

function saveMessagesToEditor(editorId, messages) {
  const editor = document.getElementById(editorId);
  if (!editor) return;
  
  const hiddenInput = document.getElementById(editor.dataset.target);
  if (hiddenInput) {
    hiddenInput.value = JSON.stringify(messages);
  }
  
  // Re-render the messages list
  renderMessagesList(editor, messages);
}

function renderMessagesList(editor, messages) {
  const list = editor.querySelector('.messages-list');
  if (!list) return;
  
  const isStart = editor.id.includes('start');
  const defaultHint = isStart ? '(note_on, vel 127)' : '(note_off, vel 0)';
  
  if (messages.length === 0) {
    list.innerHTML = `<span class="messages-placeholder">Click + to add ${defaultHint}</span>`;
    return;
  }
  
  list.innerHTML = messages.map((msg, idx) => `
    <span class="message-badge" data-index="${idx}" data-port="${escapeHtml(msg.port)}" data-type="${escapeHtml(msg.type)}" data-note="${msg.note}" data-velocity="${msg.velocity}">
      <span class="msg-port">${escapeHtml(msg.port)}</span>
      <span class="msg-note">${msg.note}</span>
      <span class="msg-name">${noteToName(msg.note)}</span>
      <span class="msg-vel">${msg.velocity}</span>
      <button type="button" class="msg-delete" data-action="delete-message" title="Delete">&times;</button>
    </span>
  `).join('');
}

function getOutputsList(editorId) {
  // Get outputs from a data attribute on the messages editor
  const editor = document.getElementById(editorId);
  if (editor && editor.dataset.outputs) {
    try {
      return JSON.parse(editor.dataset.outputs);
    } catch (e) {
      console.error('[getOutputsList] Failed to parse outputs:', editor.dataset.outputs, e);
    }
  }
  return [];
}

function showMessageForm(editorId, existingMsg = null, editIndex = null, defaults = 'start', targetBadge = null) {
  const editor = document.getElementById(editorId);
  if (!editor) return;
  
  // Remove any existing form and restore any hidden badges
  const existingForm = editor.querySelector('.message-form');
  if (existingForm) {
    const hiddenBadge = editor.querySelector('.message-badge.editing-hidden');
    if (hiddenBadge) hiddenBadge.classList.remove('editing-hidden');
    existingForm.remove();
  }
  
  // Defaults based on start/end
  const defaultType = defaults === 'end' ? 'note_off' : 'note_on';
  const defaultVel = defaults === 'end' ? 0 : 127;
  
  // Get available outputs from the editor's data attribute
  const outputs = getOutputsList(editorId);
  const firstOutput = outputs.length > 0 ? outputs[0] : '';
  
  let outputOptions = '';
  if (outputs.length === 0) {
    outputOptions = '<option value="">No outputs defined</option>';
  } else {
    outputOptions = outputs.map(o => {
      const selected = existingMsg ? (existingMsg.port === o ? 'selected' : '') : (o === firstOutput ? 'selected' : '');
      return `<option value="${escapeHtml(o)}" ${selected}>${escapeHtml(o)}</option>`;
    }).join('');
  }
  
  const typeValue = existingMsg ? existingMsg.type : defaultType;
  const typeOptions = ['note_on', 'note_off'].map(t =>
    `<option value="${t}" ${t === typeValue ? 'selected' : ''}>${t}</option>`
  ).join('');
  
  const velocityValue = existingMsg ? existingMsg.velocity : defaultVel;
  
  const form = document.createElement('div');
  form.className = 'message-form';
  form.dataset.editor = editorId;
  if (editIndex !== null) form.dataset.editIndex = editIndex;
  
  form.innerHTML = `
    <select name="port" required>${outputOptions}</select>
    <input type="text" name="note" placeholder="C4" value="${existingMsg ? existingMsg.note : ''}" required>
    <input type="number" name="velocity" placeholder="Vel" min="0" max="127" value="${velocityValue}" required>
    <select name="type" required>${typeOptions}</select>
    <button type="button" class="btn-icon btn-icon-sm" data-action="save-message" title="Save">
      <img src="/static/assets/icons/check.svg" class="icon" alt="">
    </button>
    <button type="button" class="btn-icon btn-icon-sm" data-action="cancel-message" title="Cancel">
      <img src="/static/assets/icons/x-mark.svg" class="icon" alt="">
    </button>
  `;
  
  // If editing, hide the badge and insert form in its place
  if (targetBadge) {
    targetBadge.classList.add('editing-hidden');
    targetBadge.insertAdjacentElement('afterend', form);
  } else {
    // New message: insert before the add button
    const addBtn = editor.querySelector('[data-action="add-message"]');
    editor.insertBefore(form, addBtn);
  }
  
  form.querySelector('input[name="note"]').focus();
}

function editMessage(badge) {
  const editor = badge.closest('.messages-editor');
  const editorId = editor.id;
  const index = parseInt(badge.dataset.index);
  const defaults = editor.id.includes('start') ? 'start' : 'end';
  
  // Read message data from badge data attributes
  const msg = {
    port: badge.dataset.port,
    type: badge.dataset.type,
    note: parseInt(badge.dataset.note),
    velocity: parseInt(badge.dataset.velocity)
  };
  
  showMessageForm(editorId, msg, index, defaults, badge);
}

async function saveMessage(form) {
  const editorId = form.dataset.editor;
  const editIndex = form.dataset.editIndex !== undefined ? parseInt(form.dataset.editIndex) : null;
  
  const port = form.querySelector('select[name="port"]').value;
  const type = form.querySelector('select[name="type"]').value;
  const noteInput = form.querySelector('input[name="note"]').value;
  const velocity = parseInt(form.querySelector('input[name="velocity"]').value);
  
  if (!port || !type || !noteInput || isNaN(velocity)) {
    alert('Please fill all fields');
    return;
  }
  
  // Resolve note (could be "C4" or "60")
  let noteNum;
  const resolved = await resolveNote(noteInput);
  if (resolved) {
    noteNum = resolved.num;
  } else {
    alert('Invalid note');
    return;
  }
  
  const messages = getMessagesFromEditor(editorId);
  const newMsg = { port, type, note: noteNum, velocity };
  
  if (editIndex !== null) {
    messages[editIndex] = newMsg;
  } else {
    messages.push(newMsg);
  }
  
  saveMessagesToEditor(editorId, messages);
  form.remove();
}

function cancelMessageForm(form) {
  // Restore any hidden badge before removing form
  const editor = document.getElementById(form.dataset.editor);
  if (editor) {
    const hiddenBadge = editor.querySelector('.message-badge.editing-hidden');
    if (hiddenBadge) hiddenBadge.classList.remove('editing-hidden');
  }
  form.remove();
}

function deleteMessage(badge) {
  const editor = badge.closest('.messages-editor');
  const editorId = editor.id;
  const index = parseInt(badge.dataset.index);
  const messages = getMessagesFromEditor(editorId);
  
  messages.splice(index, 1);
  saveMessagesToEditor(editorId, messages);
}

// =============================================================================
// Download with Save As dialog
// =============================================================================

async function downloadMapping() {
  try {
    const resp = await fetch('/meh/ui/editor/api/mapping/download');
    if (!resp.ok) throw new Error('Download failed');
    
    const content = await resp.text();
    const blob = new Blob([content], { type: 'application/x-yaml' });
    
    // Try File System Access API for native Save As dialog (Chrome/Edge)
    if ('showSaveFilePicker' in window) {
      try {
        const handle = await window.showSaveFilePicker({
          suggestedName: 'mapping.yml',
          types: [{
            description: 'YAML files',
            accept: { 'application/x-yaml': ['.yml', '.yaml'] }
          }]
        });
        const writable = await handle.createWritable();
        await writable.write(blob);
        await writable.close();
        return;
      } catch (err) {
        if (err.name === 'AbortError') return; // User cancelled
        // Fall through to legacy download
      }
    }
    
    // Fallback: trigger browser download
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'mapping.yml';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
  } catch (err) {
    console.error('[Download] Error:', err);
    alert('Download failed');
  }
}

// =============================================================================
// Initialize
// =============================================================================

function init() {
  // Event delegation for editor actions
  document.addEventListener('click', (e) => {
    // Handle note badge click (for editing)
    const noteBadge = e.target.closest('.note-badge-edit');
    if (noteBadge && !e.target.closest('.note-delete')) {
      startEditNote(noteBadge);
      return;
    }
    
    // Handle message badge click (for editing)
    const msgBadge = e.target.closest('.message-badge');
    if (msgBadge && !e.target.closest('.msg-delete')) {
      editMessage(msgBadge);
      return;
    }
    
    const action = e.target.closest('[data-action]');
    if (!action) return;
    
    switch (action.dataset.action) {
      case 'clear-filter':
        clearFilter();
        break;
      case 'clear-input': {
        const input = action.previousElementSibling;
        if (input && input.tagName === 'INPUT') {
          input.value = '';
          input.dispatchEvent(new Event('input'));
        }
        break;
      }
      case 'record-notes':
        startRecording();
        break;
      case 'add-note':
        addNewNote();
        break;
      case 'delete-note':
        deleteNote(action);
        break;
      case 'quick-record':
        startQuickRecord(action.dataset.event, action.dataset.port);
        break;
      case 'play-event':
        playEvent(action.dataset.event);
        break;
      case 'stop-event':
        stopEvent(action.dataset.event);
        break;
      case 'add-message': {
        const defaults = action.dataset.defaults || 'start';
        showMessageForm(action.dataset.editor, null, null, defaults);
        break;
      }
      case 'delete-message':
        deleteMessage(action.closest('.message-badge'));
        break;
      case 'save-message':
        saveMessage(action.closest('.message-form'));
        break;
      case 'cancel-message':
        cancelMessageForm(action.closest('.message-form'));
        break;
      case 'toggle-card': {
        const card = document.getElementById(action.dataset.target);
        if (card) card.classList.toggle('collapsed');
        break;
      }
    }
  });
  
  // Event delegation for input events
  document.addEventListener('input', (e) => {
    if (e.target.dataset.action === 'filter-events') {
      filterEvents(e.target.value);
    }
  });
  
  // Beforeunload guard for dirty state
  window.addEventListener('beforeunload', (e) => {
    if (isDirty()) {
      e.preventDefault();
      e.returnValue = '';
    }
  });
  
  // Update dirty indicator on HTMX swap
  document.body.addEventListener('htmx:afterSwap', (e) => {
    if (e.detail.target.id === 'main-content') {
      updateDirtyIndicator();
    }
  });

  // Disable submit button when a resolution-error is present in a modal form
  document.body.addEventListener('htmx:afterSettle', (e) => {
    const target = e.detail.target;
    if (target.id === 'port-resolution' || target.id === 'type-resolution') {
      const modal = target.closest('.modal');
      if (!modal) return;
      const submitBtn = modal.querySelector('button[type="submit"]');
      if (!submitBtn) return;
      const hasError = target.querySelector('.resolution-error');
      submitBtn.disabled = !!hasError;
    }
  });
  
  // Download button with Save As dialog
  const downloadBtn = document.getElementById('download-btn');
  if (downloadBtn) {
    downloadBtn.addEventListener('click', downloadMapping);
  }
  
  // Listen for WebSocket state/event updates
  document.body.addEventListener('update', () => {
    refreshEditorContent();
  });
}

// Refresh editor content when app state changes
async function refreshEditorContent() {
  const mainContent = document.getElementById('main-content');
  if (!mainContent) return;
  
  // Only refresh if we're on the editor page
  const editorContainer = document.querySelector('.editor-container');
  if (!editorContainer) return;
  
  try {
    const resp = await fetch('/meh/ui/editor/partials/content');
    if (resp.ok) {
      const html = await resp.text();
      mainContent.innerHTML = html;
      htmx.process(mainContent);
      updateDirtyIndicator();
    }
  } catch (err) {
    console.error('[RefreshEditor] Error:', err);
  }
}

// Export for use by save_confirm modal (still uses inline hx-on)
window.updateDirtyIndicator = updateDirtyIndicator;

// Initialize
init();
