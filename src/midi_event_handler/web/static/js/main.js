const socket = new WebSocket(`ws://${location.host}/events`);

socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log(data)
    if (data.notify) {
        console.log("Dispatching update event to trigger HTMX");
        console.log(document.getElementById("status-area"));
        document.body.dispatchEvent(new CustomEvent("update"));
    }
};

document.addEventListener("DOMContentLoaded", () => {
  const dropZone = document.getElementById("drop-zone");

  if (!dropZone) return;

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
  });

  dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("dragover");
  });

  dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");

    const files = e.dataTransfer.files;
    if (!files || files.length === 0) return;

    const file = files[0];

    if (!file.name.endsWith(".yaml")) {
      alert("Only .yaml files are supported.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    const uploadUrl = dropZone.dataset.uploadUrl || "/upload-mapping";

    fetch(uploadUrl, {
      method: "POST",
      body: formData,
    })
    .then((res) => res.text())
    .then((html) => {
      const feedback = document.getElementById("hx-feedback");
      if (feedback) {
        feedback.innerHTML = html;
      }
    })
    .catch((err) => {
      console.error("Upload failed", err);
    });
  });
});

document.addEventListener("htmx:afterSwap", function (event) {
  if (!event.detail.target || event.detail.target.id !== "hx-feedback") return;

  const timestampEl = document.getElementById("hx-feedback-timestamp");
  if (!timestampEl) return;

  const now = new Date();
  const formatted = now.toLocaleString(); // or use toISOString() if preferred
  timestampEl.textContent = `Updated: ${formatted}`;
});


