document.addEventListener('DOMContentLoaded', () => {
  const summarizeBtn = document.getElementById('summarize-btn');
  const editBtn = document.getElementById('edit-btn');
  const exportBtn = document.getElementById('export-btn');
  const customPrompt = document.getElementById('custom-prompt');
  const summaryOutput = document.getElementById('summary-output');

  summarizeBtn.addEventListener('click', () => {
    const prompt = customPrompt.value;
    // TODO: Implement actual summarization logic
    summaryOutput.textContent = `Summary generated with prompt: ${prompt || 'Default prompt'}`;
  });

  editBtn.addEventListener('click', () => {
    summaryOutput.contentEditable = true;
    summaryOutput.focus();
  });

  exportBtn.addEventListener('click', () => {
    // TODO: Implement export functionality
    alert('Summary exported!');
  });
});