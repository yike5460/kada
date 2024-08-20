let sidebar;

function createSidebar() {
  sidebar = document.createElement('div');
  sidebar.id = 'video-summarizer-sidebar';
  sidebar.innerHTML = `
    <h2>Video Summarizer</h2>
    <button id="summarize-btn">Summarize Video</button>
    <div id="summary-output"></div>
    <div id="edit-controls"></div>
  `;
  document.body.appendChild(sidebar);
  
  document.getElementById('summarize-btn').addEventListener('click', summarizeVideo);
}

function toggleSidebar(open) {
  if (!sidebar) {
    createSidebar();
  }
  sidebar.style.display = open ? 'block' : 'none';
}

function summarizeVideo() {
  // Implement video summarization logic here
  // This should interact with your backend APIs
}

// Add functions for video editing capabilities

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "toggleSidebar") {
    toggleSidebar(request.open);
  }
});

// Check sidebar state on page load
chrome.runtime.sendMessage({ action: "getSidebarState" }, (response) => {
  toggleSidebar(response.open);
});