let sidebarOpen = false;

chrome.action.onClicked.addListener((tab) => {
  if (tab.url.includes("youtube.com")) {
    sidebarOpen = !sidebarOpen;
    chrome.tabs.sendMessage(tab.id, { action: "toggleSidebar", open: sidebarOpen });
  }
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "getSidebarState") {
    sendResponse({ open: sidebarOpen });
  }
});

// Add functionality to interact with backend APIs for video processing
// This is where you'd implement the calls to your AWS services