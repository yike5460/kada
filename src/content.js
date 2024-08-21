let sidebar;

function createSidebar() {
  sidebar = document.createElement('iframe');
  sidebar.id = 'video-summarizer-sidebar';
  sidebar.src = chrome.runtime.getURL('sidebar.html');
  sidebar.style.cssText = `
    position: fixed;
    top: 0;
    right: 0;
    width: 300px;
    height: 100%;
    border: none;
    z-index: 9999;
    display: none;
  `;
  document.body.appendChild(sidebar);
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