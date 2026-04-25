# Editor Page Plan

## Overview

The editor page allows users to visually edit the mapping configuration (inputs, outputs, event_types, events) with a similar layout to the dashboard: main content area + right sidebar.

## Design Philosophy: HTMX-First, Minimal JS

This is an **experiment** in building a rich interactive UI with minimal JavaScript.

**Goals:**
- Push HTMX + Jinja2 as far as possible
- JS only where HTML/HTTP literally cannot do the job
- Server renders all UI state — no client-side state management
- Learn what works and what doesn't for future projects

**JS is allowed only for:**
1. WebSocket (no HTTP equivalent)
2. Drag & drop file upload (HTML5 API)
3. `beforeunload` guard (browser API)
4. Modal backdrop click handling (CSS can't detect "outside" clicks)
5. MIDI recording state (WebSocket-driven)

**Everything else via HTMX:**
- All CRUD operations
- Form validation feedback
- Loading states
- UI updates after actions

## Reference

See `docs/dashboard.png` for the current dashboard UI.

## Reusable Components from Dashboard

| Component              | Dashboard Location       | Editor Usage                     |
|------------------------|--------------------------|----------------------------------|
| Sidebar layout         | Right side               | Same structure                   |
| START/STOP buttons     | Sidebar                  | Same (test after save)           |
| UPLOAD MAPPING button  | Sidebar                  | Rename to "LOAD MAPPING"         |
| Dropzone               | Sidebar                  | Same, for loading mapping        |
| MIDI Ports panel       | Main content             | **Move to sidebar** (both pages) |
| WS status (LED + UP)   | Sidebar bottom           | Same                             |
| Card styling           | MIDI Ports section       | For config/events cards          |
| Button styling (`.btn`)| All buttons              | Same                             |

## Sidebar Consistency

MIDI ports should be visible in the sidebar on **both** Dashboard and Editor pages.

**Updated Sidebar Layout (both pages):**
```
┌─────────────────────┐
│ [START] [STOP]      │
│ ─────────────────── │
│ [LOAD/UPLOAD]       │
│ [dropzone]          │
│ [DOWNLOAD] (editor) │
│ [SAVE] (editor)     │
│ ─────────────────── │
│ [RESTART]           │
│ ─────────────────── │
│ MIDI PORTS    [↻]   │
│ ▼ Inputs            │
│   • loopIN0 → ...   │
│ ▼ Outputs           │
│   • loopOU0 → ...   │
│ ─────────────────── │
│ ● UP                │
└─────────────────────┘
```

**Dashboard main area:** Status + Active Events only (MIDI ports moved to sidebar)
**Editor main area:** Config card + Events card

---

## UI Structure

```
┌─────────────────────────────────────────────────────────────┐
│  TOPBAR:  [HOME] [EDITOR] [HELP]                            │
├─────────────────────────────────────────────────┬───────────┤
│                                                 │ SIDEBAR   │
│  ┌─────────────────────────────────────────┐    │           │
│  │ CONFIGURATION CARD                      │    │ [LOAD]    │
│  │ ┌─────────┬─────────┬─────────────────┐ │    │ [drop]    │
│  │ │ INPUTS  │ OUTPUTS │ EVENT TYPES     │ │    │ [DOWNLOAD]│
│  │ │ + edit  │ + edit  │ + edit          │ │    │ ───────── │
│  │ └─────────┴─────────┴─────────────────┘ │    │ [SAVE]    │
│  └─────────────────────────────────────────┘    │           │
│                                                 │ ───────── │
│  ┌─────────────────────────────────────────┐    │ MIDI PORTS│
│  │ EVENTS CARD (scrollable)                │    │ ▼ Inputs  │
│  │ ┌─────────────────────────────────────┐ │    │  • port1  │
│  │ │ Event 1        [🎹REC] [✏️] [🗑️]    │ │    │ ▼ Outputs │
│  │ │ Event 2        [🎹REC] [✏️] [🗑️]    │ │    │  • port2  │
│  │ │ ...                                 │ │    │ [REFRESH] │
│  │ │ [+ ADD EVENT]                       │ │    │           │
│  │ └─────────────────────────────────────┘ │    │ WS: [●]   │
│  └─────────────────────────────────────────┘    │           │
└─────────────────────────────────────────────────┴───────────┘
```

---

## Backend

### API Endpoints (JSON)

| Method   | Route                       | Description                          |
|----------|-----------------------------|--------------------------------------|
| `GET`    | `/meh.api/mapping`          | Return current editor mapping as JSON |
| `GET`    | `/meh.api/mapping/download` | Download mapping as YAML file        |
| `POST`   | `/meh.api/mapping/save`     | Save editor mapping to runtime file  |
| `GET`    | `/meh.api/ports`            | Get available MIDI ports (live)      |
| `GET`    | `/healthz`                  | Health check (alive, version, pid)   |

### UI Endpoints (HTML - HTMX partials)

| Method   | Route                                   | Description                          |
|----------|-----------------------------------------|--------------------------------------|
| `GET`    | `/meh.ui/editor`                        | Editor page (full template)          |
| `GET`    | `/meh.ui/editor/config`                 | Config card partial (inputs/outputs/types) |
| `GET`    | `/meh.ui/editor/events`                 | Events list partial                  |
| `GET`    | `/meh.ui/editor/ports`                  | MIDI ports sidebar partial           |
| `GET`    | `/meh.ui/editor/input/new`              | Modal: new input form                |
| `GET`    | `/meh.ui/editor/input/<name>`           | Modal: edit input form               |
| `POST`   | `/meh.ui/editor/input`                  | Create/update input → return config partial |
| `DELETE` | `/meh.ui/editor/input/<name>`           | Delete input → return config partial |
| `GET`    | `/meh.ui/editor/output/new`             | Modal: new output form               |
| `GET`    | `/meh.ui/editor/output/<name>`          | Modal: edit output form              |
| `POST`   | `/meh.ui/editor/output`                 | Create/update output → return config partial |
| `DELETE` | `/meh.ui/editor/output/<name>`          | Delete output → return config partial |
| `GET`    | `/meh.ui/editor/event-type/new`         | Modal: new event type form           |
| `GET`    | `/meh.ui/editor/event-type/<name>`      | Modal: edit event type form          |
| `POST`   | `/meh.ui/editor/event-type`             | Create/update type → return config partial |
| `DELETE` | `/meh.ui/editor/event-type/<name>`      | Delete type (+ cascade) → return config+events |
| `GET`    | `/meh.ui/editor/event/new`              | Modal: new event form                |
| `GET`    | `/meh.ui/editor/event/<name>`           | Modal: edit event form               |
| `POST`   | `/meh.ui/editor/event`                  | Create/update event → return events partial |
| `DELETE` | `/meh.ui/editor/event/<name>`           | Delete event → return events partial |
| `GET`    | `/meh.ui/editor/confirm-delete/<type>/<name>` | Confirmation modal partial     |

### Editor State (Server-Side)

```python
class EditorState:
    """In-memory working copy of mapping for editor."""
    
    def __init__(self):
        self.mapping: dict = {}       # Working copy
        self.original: dict = {}      # Snapshot for dirty check
    
    def load(self, mapping: dict):
        self.mapping = copy.deepcopy(mapping)
        self.original = copy.deepcopy(mapping)
    
    @property
    def dirty(self) -> bool:
        return self.mapping != self.original
    
    def save(self):
        # Write self.mapping to .runtime/mapping.yaml
        self.original = copy.deepcopy(self.mapping)
```

### WebSocket Endpoint for Recording

| Route              | Description                                    |
|--------------------|------------------------------------------------|
| `/meh.ws/record`   | Record MIDI chord from a specific input port   |

**Recording Flow:**

```
Client                          Server                          MIDI
  |                               |                               |
  |-- { start, port } ----------->|                               |
  |                               |-- open port ----------------->|
  |                               |                               |
  |                               |<-- note_on 65 ----------------|
  |<-- { note: 65 } --------------|                               |
  |   (UI shows: [65])            |                               |
  |                               |<-- note_on 67 ----------------|
  |<-- { note: 67 } --------------|                               |
  |   (UI shows: [65, 67])        |                               |
  |                               |<-- note_off ------------------|
  |<-- { chord: [65, 67] } -------|                               |
  |   (UI shows final chord)      |-- close port ---------------->|
  |                               |                               |
```

**Messages:**
- `{ "action": "start", "port": "loopIN0" }` — Start recording
- `{ "action": "note", "note": 65 }` — Note pressed (real-time feedback)
- `{ "action": "chord", "notes": [65, 67] }` — Chord complete
- `{ "action": "stop" }` — Cancel recording (client-initiated)
- `{ "action": "error", "message": "..." }` — Port unavailable, app running, etc.

**Guard: App must be STOPPED to record!**
- Recording opens a MIDI port exclusively
- If MidiApp is running, it already owns the ports
- Server returns `{ "action": "error", "message": "Cannot record while app is running" }`
- UI should disable Record buttons when app is running (check via status)

**UI Updates via HTMX:**
The WebSocket events can trigger HTMX swaps using `htmx:trigger` custom events:

```javascript
// On WS message, dispatch event that HTMX listens to
socket.onmessage = (e) => {
  const data = JSON.parse(e.data);
  if (data.action === 'note' || data.action === 'chord') {
    // Store notes in a data attribute, trigger HTMX refresh
    document.getElementById('record-display').dataset.notes = JSON.stringify(data.notes || [data.note]);
    document.body.dispatchEvent(new CustomEvent('recording-update'));
  }
};
```

```html
<!-- Display updates via HTMX trigger -->
<span id="record-display" 
      hx-get="/meh.ui/editor/record-display"
      hx-trigger="recording-update from:body"
      hx-swap="innerHTML">
  Press keys...
</span>
```

Or simpler: just update innerHTML directly with JS for the note display (it's just a list of numbers).

**Reusability:** Create a `MidiRecorder` class reusing chord-building logic from `MidiListener`.

---

## Frontend Architecture

### Current State

```
templates/
├── base.html              # Base layout (topbar, content block, footer)
├── dashboard.html         # Sidebar is inline here
├── help.html              # No sidebar, just content
├── whatsnew.html          # No sidebar, just content
└── partials/
    └── status_fragment.html   # HTMX partial

static/
├── css/
│   └── style.css          # All styles in one file
└── js/
    ├── main.js            # WebSocket, dropzone, htmx handlers (all mixed)
    └── htmx.min.js        # HTMX library
```

**Problems:**
- Sidebar is hardcoded in `dashboard.html`, can't reuse
- `main.js` mixes unrelated concerns (WS, dropzone, htmx)
- No module structure for JS

### Proposed Structure

```
templates/
├── base.html              # Base layout (unchanged)
├── base_with_sidebar.html # NEW: extends base, adds sidebar slot
├── dashboard.html         # extends base_with_sidebar
├── editor.html            # extends base_with_sidebar
├── help.html              # extends base (no sidebar)
├── whatsnew.html          # extends base (no sidebar)
└── partials/
    ├── status_fragment.html
    └── sidebar/
        ├── ws_status.html      # WebSocket LED indicator
        ├── controls.html       # START/STOP buttons
        ├── mapping_loader.html # LOAD/UPLOAD button + dropzone
        ├── midi_ports.html     # MIDI ports panel (BOTH pages)
        └── editor_actions.html # SAVE + DOWNLOAD (editor only)

static/
├── css/
│   └── style.css          # Keep single file (add editor/modal styles)
└── js/
    ├── htmx.min.js        # HTMX library
    ├── main.js            # Shared init, loads modules
    ├── websocket.js       # NEW: WebSocket connection module
    ├── dropzone.js        # NEW: Drag & drop module
    ├── modal.js           # NEW: Modal component
    └── editor.js          # NEW: Editor-specific logic
```

### Template Inheritance

```
base.html
├── base_with_sidebar.html (extends base)
│   ├── dashboard.html (extends base_with_sidebar)
│   └── editor.html (extends base_with_sidebar)
├── help.html (extends base)
└── whatsnew.html (extends base)
```

### base_with_sidebar.html Concept

```html
{% extends "base.html" %}

{% block content %}
<div id="main-content">
  {% block main %}{% endblock %}
</div>

<aside class="sidebar-right">
  {% block sidebar %}{% endblock %}

  <!-- Always show WS status at bottom -->
  {% include "partials/sidebar/ws_status.html" %}
</aside>
{% endblock %}
```

### HTMX-First Approach

Prioritize server-rendered HTML with HTMX over client-side JS.

**Use HTMX for:**
- Loading/refreshing data (mapping, ports)
- CRUD operations (add/edit/delete) via form submissions
- Swapping UI fragments after actions
- Modal content loading

**Use JS only for:**
- WebSocket connection (required)
- Dropzone drag & drop (HTML5 API)
- Modal open/close mechanics
- Dirty state tracking + beforeunload guard
- MIDI recording UI state

### HTMX Patterns for Editor

#### Loading Mapping Data
```html
<!-- Editor page loads config card via HTMX on page load -->
<div id="config-card"
     hx-get="/meh.ui/editor/config"
     hx-trigger="load"
     hx-swap="innerHTML">
  Loading...
</div>
```

#### Add/Edit with Modal
```html
<!-- Button triggers modal load -->
<button hx-get="/meh.ui/editor/event/new"
        hx-target="#modal-container"
        hx-swap="innerHTML">
  + Add Event
</button>

<!-- Edit existing -->
<button hx-get="/meh.ui/editor/event/{{ event.name }}"
        hx-target="#modal-container"
        hx-swap="innerHTML">
  Edit
</button>
```

#### Form Submission
```html
<!-- Modal form submits via HTMX -->
<form hx-post="/meh.api/editor/event"
      hx-target="#events-list"
      hx-swap="outerHTML"
      hx-on::after-request="closeModal()">
  <!-- fields -->
  <button type="button" onclick="closeModal()">Cancel</button>
  <button type="submit">OK</button>
</form>
```

#### Delete with Confirmation
```html
<!-- Delete button loads confirmation modal -->
<button hx-get="/meh.ui/editor/confirm-delete/event/{{ event.name }}"
        hx-target="#modal-container"
        hx-swap="innerHTML">
  Delete
</button>

<!-- Confirmation modal -->
<form hx-delete="/meh.api/editor/event/{{ event.name }}"
      hx-target="#events-list"
      hx-swap="outerHTML"
      hx-on::after-request="closeModal()">
  <p>Delete event "{{ event.name }}"?</p>
  <button type="button" onclick="closeModal()">Cancel</button>
  <button type="submit">Delete</button>
</form>
```

### Server-Side State Management

Instead of keeping mapping state in JS, we keep it server-side in a session/memory object:

```python
# Editor session state (in-memory, per-session or global for single-user)
editor_state = {
    "mapping": { ... },      # Working copy of mapping
    "dirty": False,          # Has unsaved changes
    "original": { ... }      # Original mapping for dirty comparison
}
```

**Benefits:**
- Jinja2 templates render current state directly
- HTMX swaps bring fresh server-rendered HTML
- No complex JS state management
- Dirty state tracked server-side (or hybrid with JS)

**Trade-off:**
- More HTTP requests, but keeps architecture simple
- Single-user app, so no concurrency issues

### Minimal JS Requirements

| Feature              | Why JS is Required                          | Location    |
|----------------------|---------------------------------------------|-------------|
| WebSocket            | No HTTP equivalent for persistent connection | `main.js`   |
| Dropzone             | HTML5 drag & drop API requires JS           | `main.js`   |
| Modal open/close     | CSS can't detect backdrop clicks            | `main.js`   |
| `beforeunload`       | Browser API, no HTMX equivalent             | `editor.js` |
| Dirty state flag     | Track unsaved changes (simple bool)         | `editor.js` |
| Record WS messages   | Send start/stop, receive notes, update display | `editor.js` |

**Recording JS is minimal:**
- Send `{ action: start, port }` on button click
- Update note display on each `{ action: note }` message (direct innerHTML, ~3 lines)
- On `{ action: chord }`, populate form field and stop

**Total JS estimate:** ~100-150 lines across both files.

### Modal Mechanics (JS)

Simple modal open/close, content loaded via HTMX:

```javascript
// Modal container in base template
// <div id="modal-container" class="modal-backdrop hidden"></div>

function openModal() {
  document.getElementById('modal-container').classList.remove('hidden');
}

function closeModal() {
  document.getElementById('modal-container').classList.add('hidden');
  document.getElementById('modal-container').innerHTML = '';
}

// HTMX hook: open modal when content is swapped in
document.body.addEventListener('htmx:afterSwap', (e) => {
  if (e.detail.target.id === 'modal-container' && e.detail.target.innerHTML.trim()) {
    openModal();
  }
});
```

### Migration Steps

1. Create `base_with_sidebar.html` template
2. Extract sidebar partials (`ws_status.html`, `mapping_loader.html`)
3. Add modal container to `base.html`
4. Update `dashboard.html` to extend `base_with_sidebar`
5. Refactor `main.js` (keep WS, dropzone, add modal mechanics)
6. Create `editor.js` (dirty state, beforeunload)

---

## Frontend

### Files

| File                          | Action   | Description                        |
|-------------------------------|----------|------------------------------------|
| `templates/base.html`         | Modify   | Add EDITOR nav link                |
| `templates/editor.html`       | **New**  | Editor page template               |
| `static/js/modal.js`          | **New**  | Reusable modal component           |
| `static/js/editor.js`         | **New**  | Editor-specific logic              |
| `static/js/main.js`           | Keep     | Shared code (WS, dropzone)         |
| `static/css/style.css`        | Modify   | Add editor + modal styles          |

### Modal Component

Reusable modal with OK/Cancel buttons. Does NOT close on outside click.

```javascript
// Edit modal
Modal.open({
  title: "Edit Event",
  content: htmlOrElement,
  onOk: () => { /* save */ },
  onCancel: () => { /* discard */ },
  closeOnOutsideClick: false
});

// Confirmation modal
Modal.confirm({
  title: "Delete Event Type?",
  message: "This will delete 3 events of type 'light'. Continue?",
  onConfirm: () => { /* delete */ },
  danger: true
});
```

---

## Component Details

### Config Card (Inputs / Outputs / Event Types)

Three columns, each with:
- List of items with edit/delete buttons
- Add button at bottom

```
┌─────────────────────────────────────────────────────┐
│ CONFIGURATION                                       │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐ │
│ │ Inputs      │ │ Outputs     │ │ Event Types     │ │
│ │ ──────────  │ │ ──────────  │ │ ──────────────  │ │
│ │ • loopIN0 ✏️🗑️│ │ • loopOU0 ✏️🗑️│ │ • light    ✏️🗑️ │ │
│ │             │ │             │ │ • music    ✏️🗑️ │ │
│ │ [+ Add]     │ │ [+ Add]     │ │ [+ Add]         │ │
│ └─────────────┘ └─────────────┘ └─────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### Port Input with Live Resolution

Autocomplete dropdown from available ports, but text is editable (mido adds indices).
Shows live resolution status below input.

```
┌───────────────────────────────────────────┐
│ Port Name: [loopIN0          ▼]           │
│            ↳ Resolves to: loopIN0 0       │
│              or: ⚠️ No matching port      │
└───────────────────────────────────────────┘
```

### Events Card

Scrollable list of events with inline Record button and edit/delete actions.

```
┌──────────────────────────────────────────────────────────┐
│ EVENTS                                        [+ Add]    │
│ ─────────────────────────────────────────────────────────│
│ ┌──────────────────────────────────────────────────────┐ │
│ │ event_key_107 (music)                                │ │
│ │ Trigger: loopIN0 → [107]  [🎹 Record]                │ │
│ │ Start: 1 msg  |  End: 1 msg                          │ │
│ │ Duration: 0-10s  |  Fallback: event_key_128          │ │
│ │                                      [✏️ Edit] [🗑️]   │ │
│ └──────────────────────────────────────────────────────┘ │
│ ... (scrollable)                                         │
└──────────────────────────────────────────────────────────┘
```

### Event Editor Modal

Full form for editing an event. Opens via Edit button or Add button.

```
┌────────────────────────────────────────────────────┐
│ Edit Event: event_key_107                     [X]  │
├────────────────────────────────────────────────────┤
│ Name:    [event_key_107        ]                   │
│ Type:    [music          ▼]  (from event_types)    │
│                                                    │
│ Trigger Port: [loopIN0 ▼]                          │
│ Trigger Notes: [107] [🎹 Record]                   │
│                                                    │
│ Start Messages:                         [+ Add]    │
│ ┌────────────────────────────────────────────────┐ │
│ │ note_on, note=106, vel=127, port=loopOU0 [🗑️]  │ │
│ └────────────────────────────────────────────────┘ │
│                                                    │
│ End Messages:                           [+ Add]    │
│ ┌────────────────────────────────────────────────┐ │
│ │ note_off, note=106, vel=0, port=loopOU0  [🗑️]  │ │
│ └────────────────────────────────────────────────┘ │
│                                                    │
│ Duration Min: [0   ]s   Duration Max: [10  ]s      │
│ Fallback Event: [event_key_128 ▼]                  │
│                                                    │
│              [Cancel]              [OK]            │
└────────────────────────────────────────────────────┘
```

### Delete Confirmation Modals

#### Delete Event
Simple confirmation.

#### Delete Event Type (CRITICAL)
Shows warning about cascading deletion of events.

```
┌────────────────────────────────────────────┐
│ ⚠️ Delete Event Type "light"?              │
├────────────────────────────────────────────┤
│ WARNING: This will also delete 2 events:   │
│   • event_key_107                          │
│   • event_key_108                          │
│                                            │
│ This action cannot be undone.              │
│                                            │
│         [Cancel]        [Delete]           │
└────────────────────────────────────────────┘
```

### Sidebar MIDI Ports

Always visible, scrollable container, collapsible per category.

```
┌─────────────────────┐
│ MIDI PORTS    [↻]   │
│ ─────────────────── │
│ ▼ Inputs            │
│ ┌─────────────────┐ │
│ │ • loopIN0       │ │
│ │   → loopIN0 0   │ │
│ │ • loopIN1       │ │
│ │   → ⚠️ N/A      │ │
│ └─────────────────┘ │  ← scrollable
│ ▶ Outputs (2)       │  ← collapsed
└─────────────────────┘
```

---

## Validation Rules

| Field            | Rule                                              | Severity |
|------------------|---------------------------------------------------|----------|
| Port names       | Autocomplete + editable, show live resolution     | Warning  |
| Event names      | Must be unique                                    | Error    |
| Event types      | Must exist in `event_types` list                  | Error    |
| Delete event type| Cascades to delete all events of that type        | Confirm  |
| Fallback event   | Should reference existing event                   | Warning  |

---

## Data Flow

```
1. Page Load
   GET /meh.api/mapping → populate JS state → render UI
   GET /meh.api/ports → populate available ports

2. Edit Operations
   User action → update JS state → mark dirty → re-render UI

3. Record Chord
   Click Record → WS /meh.ws/record { action: start, port: X }
   WS receives { action: recorded, notes: [...] }
   Update trigger notes in JS state

4. Save
   Click Save → POST /meh.api/mapping/save (JSON body)
   Server writes to .runtime/mapping.yaml
   Clear dirty state

5. Download
   Click Download → GET /meh.api/mapping/download
   Browser downloads file

6. Load New Mapping (LOAD button or dropzone)
   If dirty → show confirmation modal:
     "You have unsaved changes. Loading a new mapping will discard them. Continue?"
     [Cancel] [Load Anyway]
   If confirmed or not dirty → POST /meh.api/upload-mapping
   On success → GET /meh.api/mapping → repopulate JS state → clear dirty

7. Navigation Guard
   beforeunload event → if dirty, show browser warning
```

---

## Implementation Phases

| Phase | Tasks                                                            |
|-------|------------------------------------------------------------------|
| **0** | Frontend refactor: Extract sidebar templates, add modal container |
| **1** | Backend: API endpoints (`/mapping`, `/save`, `/download`, `/ports`) |
| **2** | Backend: Editor route + EditorState + basic template             |
| **3** | Backend: Note conversion helpers (`note_to_name`, `name_to_note`) |
| **4** | Frontend: Config card - inputs/outputs (with middle_c) /event_types |
| **5** | Frontend: Events card - list display with note badges            |
| **6** | Frontend: Event editor modal (full form with note input parsing) |
| **7** | Backend: WebSocket recorder endpoint                             |
| **8** | Frontend: Record button + real-time note badge display           |
| **9** | Frontend: Save/Load/Download + dirty state + beforeunload        |
| **10**| Polish: validation messages, CSS, error handling                 |

---

## Files to Create/Modify

### Phase 0: Frontend Refactor

| File                                                  | Action   |
|-------------------------------------------------------|----------|
| `web/templates/base.html`                             | Modify (add modal container, scripts block) |
| `web/templates/base_with_sidebar.html`                | **New**  |
| `web/templates/dashboard.html`                        | Modify (use base_with_sidebar) |
| `web/templates/partials/sidebar/ws_status.html`       | **New**  |
| `web/templates/partials/sidebar/mapping_loader.html`  | **New**  |
| `web/static/js/main.js`                               | Refactor (WS, dropzone, modal mechanics) |

### Phase 1-10: Editor Implementation

| File                                                  | Action   |
|-------------------------------------------------------|----------|
| `web/app.py`                                          | Modify (or split to `web/editor.py` router) |
| `web/editor.py`                                       | **New** (optional: editor routes as separate router) |
| `web/editor_state.py`                                 | **New** (EditorState class) |
| `web/templates/editor.html`                           | **New**  |
| `web/templates/partials/editor/config_card.html`      | **New**  |
| `web/templates/partials/editor/events_card.html`      | **New**  |
| `web/templates/partials/editor/event_row.html`        | **New**  |
| `web/templates/partials/editor/modals/input_form.html`| **New**  |
| `web/templates/partials/editor/modals/output_form.html`| **New** |
| `web/templates/partials/editor/modals/event_type_form.html`| **New** |
| `web/templates/partials/editor/modals/event_form.html`| **New**  |
| `web/templates/partials/editor/modals/confirm_delete.html`| **New** |
| `web/templates/partials/sidebar/midi_ports.html`      | **New**  |
| `web/static/js/editor.js`                             | **New** (dirty state, beforeunload, record) |
| `web/static/css/style.css`                            | Modify (modal + editor styles) |
| `core/midi/recorder.py`                               | **New**  |
| `core/midi/notes.py`                                  | **New** (note conversion helpers) |

---

## Note Display & Conversion

### Note Badges (Cool Factor!)

Display notes as fancy badges showing both number and note name:

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  60 │ C4    │  │  65 │ F4    │  │  67 │ G4    │
└─────────────┘  └─────────────┘  └─────────────┘
```

CSS styling for badges:
```css
.note-badge {
  display: inline-flex;
  border: 1px solid #888;
  border-radius: 4px;
  overflow: hidden;
  font-family: monospace;
  font-size: 0.9rem;
}
.note-badge .note-num {
  background: #333;
  color: #fff;
  padding: 0.2rem 0.4rem;
}
.note-badge .note-name {
  background: #f0f0f0;
  padding: 0.2rem 0.4rem;
  font-weight: bold;
}
```

### Note Conversion

Standard MIDI: middle C (C4) = 60

**Conversion formula:**
```
note_name = NOTE_NAMES[note % 12] + str(note // 12 - 1)
# where NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
```

**But some devices differ!** Common variations:
- Yamaha: C3 = 60
- Roland: C4 = 60 (standard)
- Some: C5 = 60

### Configurable Middle C Offset

Add optional `middle_c` parameter to inputs/outputs:

```yaml
inputs:
  # Simple string (default: middle_c = 60)
  - "loopIN0"
  
  # Or object with config
  - name: "loopIN1"
    middle_c: 48  # C4 = 48 on this device (Yamaha style)

outputs:
  - name: "loopOU0"
    middle_c: 72  # C4 = 72 on this device
```

**Backward compatible:** If input/output is a string, treat as `{ name: "...", middle_c: 60 }`

### Note Entry in Forms

When user types notes in the modal, accept either format:

```
┌─────────────────────────────────────────────────┐
│ Trigger Notes: [C4, F4, G4    ] [🎹 Record]     │
│                ↳ Parsed: 60, 65, 67             │
└─────────────────────────────────────────────────┘
```

**Parsing rules:**
- Numbers: use directly (`60` → `60`)
- Note strings: convert using port's middle_c offset (`C4` → `60` if middle_c=60)
- Comma or space separated
- Show live preview of parsed numbers below input

**Always save as numbers** in the YAML.

### Server-Side Helpers

```python
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

def note_to_name(note: int, middle_c: int = 60) -> str:
    """Convert MIDI note number to name (e.g., 60 -> 'C4')"""
    # Adjust octave based on middle_c offset
    octave_offset = (middle_c - 60) // 12
    octave = (note // 12) - 1 - octave_offset
    return f"{NOTE_NAMES[note % 12]}{octave}"

def name_to_note(name: str, middle_c: int = 60) -> int:
    """Convert note name to MIDI number (e.g., 'C4' -> 60)"""
    # Parse "C#4" or "D2" etc.
    match = re.match(r'([A-G]#?)(-?\d+)', name.upper())
    if not match:
        raise ValueError(f"Invalid note: {name}")
    note_name, octave = match.groups()
    octave_offset = (middle_c - 60) // 12
    base = NOTE_NAMES.index(note_name)
    return base + (int(octave) + 1 + octave_offset) * 12
```

### Updated Mapping Structure

```yaml
inputs:
  - name: "loopIN0"
    middle_c: 60  # optional

outputs:
  - name: "loopOU0"
    middle_c: 60  # optional

event_types:
  - light
  - music

events:
  - name: event_key_107
    # ... (unchanged)
```

**Migration:** On load, normalize string inputs/outputs to objects with default middle_c.

---

## Open Questions

1. **Message editor in event modal**: How to add/edit MIDI messages? Inline form or nested modal?
2. **Bulk operations**: Need multi-select for events? (Probably not for v1)
3. **Undo/Redo**: Worth implementing? (Probably not for v1)
