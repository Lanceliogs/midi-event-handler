/**
 * Shared utility functions.
 */

export function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

export function copyToClipboard(text, button) {
  return navigator.clipboard.writeText(text).then(() => {
    if (button) {
      const originalText = button.textContent;
      button.textContent = 'Copied!';
      button.disabled = true;
      setTimeout(() => {
        button.textContent = originalText;
        button.disabled = false;
      }, 2000);
    }
    return true;
  }).catch(err => {
    console.error('Failed to copy:', err);
    if (button) {
      button.textContent = 'Failed to copy';
    }
    return false;
  });
}
