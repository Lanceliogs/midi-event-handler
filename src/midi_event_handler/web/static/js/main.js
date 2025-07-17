const socket = new WebSocket(`ws://${location.host}/events`);

socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === "update") {
        // Trigger HTMX to re-fetch status
        const el = document.getElementById("status-area");
        if (el) el.dispatchEvent(new Event("htmx:trigger"));
    }
};
