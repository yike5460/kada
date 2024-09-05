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
  } else if (request.action === "summarizeVideo") {
    // TODO: Implement actual video summarization logic
    // This is where you'd call your AWS services
    // For now, we'll just simulate the process
    let progress = 0;
    const interval = setInterval(() => {
        progress += 10;
        chrome.tabs.sendMessage(sender.tab.id, {action: "updateProgress", progress: progress});
        if (progress >= 100) {
            clearInterval(interval);
            sendResponse({
                success: true,
                processedVideoUrl: "https://example.com/processed-video.mp4"
            });
        }
    }, 500);
    return true; // Indicates that the response will be sent asynchronously
  }
});

// Add functionality to interact with backend APIs for video processing
// This is where you'd implement the calls to your AWS services