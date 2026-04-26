/**
 * WebSocket connection module.
 */

import * as toast from './toast.js';

let socket = null;

function updateStatus(connected) {
  const led = document.getElementById("ws-led");
  const label = document.getElementById("ws-label");

  if (!led || !label) return;

  if (connected) {
    led.classList.add("up");
    led.classList.remove("down");
    label.innerText = "UP";
  } else {
    led.classList.add("down");
    led.classList.remove("up");
    label.innerText = "DOWN";
  }
}

export function connect() {
  if (socket && socket.readyState === WebSocket.OPEN) {
    console.log("[WS] Already connected. Skipping.");
    return;
  }
  
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  socket = new WebSocket(`${protocol}//${location.host}/meh/ws/events`);

  socket.onopen = () => {
    console.log("[WS] Connected to server");
    updateStatus(true);
  };

  socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log("[WS] Message:", data);
    
    // Handle state change notifications
    if (data.notify) {
      document.body.dispatchEvent(new CustomEvent("update"));
    }
    
    // Handle toast notifications from server
    if (data.toast) {
      toast.handleWebSocket(data);
    }
    
    // Handle error notifications
    if (data.error) {
      toast.show(data.short, 'error', { 
        detail: data.detail,
        persist: true 
      });
    }
  };

  socket.onclose = () => {
    console.warn("[WS] Disconnected. Reconnecting in 1s...");
    updateStatus(false);
    setTimeout(connect, 1000);
  };

  socket.onerror = (err) => {
    console.error("[WS] Error:", err);
    socket.close();
  };
}

export function getSocket() {
  return socket;
}
