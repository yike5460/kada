document.addEventListener('DOMContentLoaded', () => {
  console.log('Sidebar DOM loaded');
  const summarizeBtn = document.getElementById('summarize-btn');
  const editBtn = document.getElementById('edit-btn');
  const exportBtn = document.getElementById('export-btn');
  const customPrompt = document.getElementById('custom-prompt');
  const summaryOutput = document.getElementById('summary-output');

  summarizeBtn.addEventListener('click', () => {
    console.log('Summarize button clicked');
    const prompt = customPrompt.value;
    console.log('Custom prompt:', prompt);
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