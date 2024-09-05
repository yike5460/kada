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

function detectVideoOnPage() {
    const videoElements = document.querySelectorAll('video');
    if (videoElements.length > 0) {
        return videoElements[0].src || videoElements[0].currentSrc;
    }
    // Check for YouTube player
    const youtubePlayer = document.querySelector('#movie_player');
    if (youtubePlayer) {
        const videoId = new URLSearchParams(window.location.search).get('v');
        if (videoId) {
            return `https://www.youtube.com/watch?v=${videoId}`;
        }
    }
    return null;
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "toggleSidebar") {
        toggleSidebar(request.open);
    } else if (request.action === "detectVideo") {
        const videoUrl = detectVideoOnPage();
        console.log('Detected video URL:', videoUrl);
        sendResponse({videoUrl: videoUrl});
    }
});

// Check sidebar state on page load
chrome.runtime.sendMessage({ action: "getSidebarState" }, (response) => {
  toggleSidebar(response.open);
});