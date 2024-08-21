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
        // TODO: Implement video detection logic
        chrome.tabs.query({active: true, currentWindow: true}, (tabs) => {
            chrome.tabs.sendMessage(tabs[0].id, {action: "detectVideo"}, (response) => {
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

        // TODO: Implement actual summarization logic
        statusMessage.textContent = "Processing video...";
        progressBarFill.style.width = "0%";

        // Simulating video processing with a timer
        let progress = 0;
        const interval = setInterval(() => {
            progress += 10;
            progressBarFill.style.width = `${progress}%`;
            if (progress >= 100) {
                clearInterval(interval);
                processedVideoUrl = "https://example.com/processed-video.mp4"; // Replace with actual processed video URL
                statusMessage.textContent = "Video summarized successfully!";
                summaryOutput.textContent = `Original video: ${videoUrl}\nSummarized video: ${processedVideoUrl}`;
            }
        }, 500);

        // In a real implementation, you would call your backend API here
        // and update the progress bar and status message based on the response
    });

    exportBtn.addEventListener('click', () => {
        console.log('Export button clicked');
        if (processedVideoUrl) {
            // TODO: Implement export functionality (e.g., copy to clipboard or download)
            navigator.clipboard.writeText(processedVideoUrl).then(() => {
                statusMessage.textContent = "Processed video URL copied to clipboard!";
            }).catch(err => {
                console.error('Failed to copy: ', err);
                statusMessage.textContent = "Failed to copy URL. Please try again.";
            });
        } else {
            statusMessage.textContent = "Please summarize a video first.";
        }
    });
});