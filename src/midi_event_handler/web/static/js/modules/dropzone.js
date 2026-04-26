/**
 * File dropzone module for YAML uploads.
 */

import * as toast from './toast.js';

export function init() {
  const dropZone = document.getElementById("drop-zone");
  if (!dropZone) return;

  dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
  });

  dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("dragover");
  });

  dropZone.addEventListener("drop", async (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");

    const files = e.dataTransfer.files;
    if (!files || files.length === 0) return;

    const file = files[0];

    if (!file.name.endsWith(".yaml") && !file.name.endsWith(".yml")) {
      toast.error("Only .yaml/.yml files are supported.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    const uploadUrl = dropZone.dataset.uploadUrl || "/meh/api/upload-mapping";

    try {
      const res = await fetch(uploadUrl, {
        method: "POST",
        body: formData,
      });
      
      const toastMsg = res.headers.get("X-Toast");
      const toastType = res.headers.get("X-Toast-Type") || "info";
      
      if (toastMsg) {
        toast.show(toastMsg, toastType);
      }
      
      document.body.dispatchEvent(new CustomEvent("update"));
      document.body.dispatchEvent(new CustomEvent("ports-refresh"));
    } catch (err) {
      console.error("Upload failed", err);
      toast.error("Upload failed");
    }
  });
}
