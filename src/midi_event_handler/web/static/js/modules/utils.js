/**
 * Shared utility functions.
 */

export function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

export function noteToName(noteNum) {
  const notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
  const octave = Math.floor(noteNum / 12) - 1;
  const note = notes[noteNum % 12];
  return `${note}${octave}`;
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
