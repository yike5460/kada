document.addEventListener('DOMContentLoaded', () => {
    console.log('Sidebar DOM loaded');
    const detectVideoBtn = document.getElementById('detect-video-btn');
    const summarizeBtn = document.getElementById('summarize-btn');
    const exportBtn = document.getElementById('export-btn');
    const videoUrlInput = document.getElementById('video-url');
    const summaryOutput = document.getElementById('summary-output');
    const progressBarFill = document.getElementById('progress-bar-fill');
    const statusMessage = document.getElementById('status-message');

    let detectedVideoUrl = '';
    let processedVideoUrl = '';

    detectVideoBtn.addEventListener('click', () => {
        console.log('Detect video button clicked');
        chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
            if (!tabs[0]) {
                console.error('No active tab found');
                statusMessage.textContent = "Error: Cannot detect video on this page.";
                return;
            }
            chrome.tabs.sendMessage(tabs[0].id, {action: "detectVideo"}, (response) => {
                if (chrome.runtime.lastError) {
                    console.error('Error sending message:', chrome.runtime.lastError);
                    statusMessage.textContent = "Error detecting video. Please try again.";
                    return;
                }
                if (response && response.videoUrl) {
                    detectedVideoUrl = response.videoUrl;
                    videoUrlInput.value = detectedVideoUrl;
                    statusMessage.textContent = "Video detected successfully!";
                } else {
                    statusMessage.textContent = "No video detected on the page.";
                }
            });
        });
    });

    summarizeBtn.addEventListener('click', () => {
        console.log('Summarize button clicked');
        const videoUrl = videoUrlInput.value || detectedVideoUrl;
        if (!videoUrl) {
            statusMessage.textContent = "Please enter a video URL or detect a video first.";
            return;
        }

        statusMessage.textContent = "Processing video...";
        progressBarFill.style.width = "0%";

        chrome.runtime.sendMessage({ action: "summarizeVideo", videoUrl: videoUrl }, (response) => {
            if (response.success) {
                processedVideoUrl = response.processedVideoUrl;
                statusMessage.textContent = "Video summarized successfully!";
                summaryOutput.textContent = `Original video: ${videoUrl}\nSummarized video: ${processedVideoUrl}`;
            } else {
                statusMessage.textContent = "Error summarizing video. Please try again.";
            }
        });
    });

    exportBtn.addEventListener('click', () => {
        console.log('Export button clicked');
        if (processedVideoUrl) {
            navigator.clipboard.writeText(processedVideoUrl).then(() => {
                statusMessage.textContent = "Processed video URL copied to clipboard!";
                // Provide visual feedback
                exportBtn.textContent = "Copied!";
                setTimeout(() => {
                    exportBtn.textContent = "Export Short Video";
                }, 2000);
            }).catch(err => {
                console.error('Failed to copy:', err);
                statusMessage.textContent = "Failed to copy URL. Please try again.";
            });
        } else {
            statusMessage.textContent = "Please summarize a video first.";
            // Provide visual feedback
            exportBtn.disabled = true;
            setTimeout(() => {
                exportBtn.disabled = false;
            }, 2000);
        }
    });

    // Listen for progress updates from the background script
    chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
        if (request.action === "updateProgress") {
            progressBarFill.style.width = `${request.progress}%`;
        }
    });
});