// Configuration
const API_BASE_URL = 'http://localhost:5000/api';
const ORIGINAL_VIDEO = 'footages.mp4';
const TITLE_VIDEO = 'title.mp4';

// DOM elements
const queryInput = document.getElementById('queryInput');
const submitBtn = document.getElementById('submitBtn');
const statusMessage = document.getElementById('status');
const videoPlayer = document.getElementById('videoPlayer');
const bgMusic = document.getElementById('bgMusic');
// Results UI was removed from the page; keep references null-safe
const resultsContainer = document.getElementById('resultsContainer');
const resultsList = document.getElementById('resultsList');

// State
let isProcessing = false;

// Event listeners
submitBtn.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    handleSubmit();
});
queryInput.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === 'Enter') {
        e.preventDefault();
        handleSubmit();
    }
});

// Additional safety: prevent any form submission
document.addEventListener('submit', function(e) {
    e.preventDefault();
    return false;
});

/**
 * Main submit handler
 */
async function handleSubmit() {
    const input = queryInput.value.trim();
    
    if (!input) {
        showStatus('Please enter at least one query', 'error');
        return;
    }

    isProcessing = true;
    submitBtn.disabled = true;
    showStatus('Processing query...', 'loading');
    if (resultsList) resultsList.innerHTML = '';
    if (resultsContainer) resultsContainer.style.display = 'none';

    try {
        // Send raw input text to backend - let backend handle the split
        const results = await fetchQueryFromBackend(input);

        // Display results
        displayResults(results);

        // Start looping playback over the matched intervals
        startSegmentLoopFromResults(results);

        const numQueries = Array.isArray(results) ? results.length : 1;
        showStatus(`✓ Successfully processed ${numQueries} queries and generated video`, 'success');
    } catch (error) {
        console.error('Error:', error);
        showStatus(`Error: ${error.message}`, 'error');
    } finally {
        isProcessing = false;
        submitBtn.disabled = false;
    }
}

/**
 * Fetch query results from backend API
 */
async function fetchQueryFromBackend(queryText) {
    try {
        console.log('Sending query to backend:', queryText);
        console.log('Backend URL:', `${API_BASE_URL}/query`);
        
        const response = await fetch(`${API_BASE_URL}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ query: queryText })
        });

        console.log('Response status:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error('API error response:', errorText);
            throw new Error(`API error: ${response.statusText}`);
        }

        const data = await response.json();
        console.log('Query results received:', data);
        // Ensure we always return an array
        return Array.isArray(data) ? data : [data];
    } catch (error) {
        console.error('Error processing query:', error);
        throw new Error(`Failed to process query: ${error.message}`);
    }
}

/**
 * Display results in the UI
 */
function displayResults(results) {
    if (!resultsContainer || !resultsList) {
        // Results panel removed in current UI; nothing to render
        return;
    }

    resultsContainer.style.display = 'block';
    resultsList.innerHTML = '';

    // Results should be an array from backend
    const resultsArray = Array.isArray(results) ? results : [results];

    resultsArray.forEach((result, index) => {
        const resultDiv = document.createElement('div');
        resultDiv.className = 'result-item';
        resultDiv.innerHTML = `
            <div style="margin-bottom: 8px;">
                <span style="font-weight: bold; color: #4caf50;">Result #${index + 1}</span>
            </div>
            <div class="result-item query" style="border: none; background: none; border-left: 3px solid #4caf50;">
                <div class="result-label">Query</div>
                <div class="result-value">${escapeHtml(result.query)}</div>
            </div>
            <div class="result-item interval" style="border: none; background: none; border-left: 3px solid #2196f3; margin-top: 8px;">
                <div class="result-label">Interval</div>
                <div class="result-value">${escapeHtml(result.interval)}</div>
            </div>
            <div class="result-item highlight" style="border: none; background: none; border-left: 3px solid #ff9800; margin-top: 8px; margin-bottom: 15px;">
                <div class="result-label">Highlight</div>
                <div class="result-value">${escapeHtml(result.highlight)}</div>
            </div>
        `;
        resultsList.appendChild(resultDiv);
    });
}

/**
 * Start looping playback over intervals from backend results
 */
function startSegmentLoopFromResults(results) {
    // Extract time intervals from results
    const intervals = results.map(r => r.interval);
	
    console.log('=== INTERVALS ===');
    console.log('Number of intervals:', intervals.length);
    intervals.forEach((interval, index) => {
        console.log(`Interval ${index + 1}: ${interval}`);
    });
    console.log('==================');

    // Convert interval strings ("HH:MM:SS - HH:MM:SS") to [startSeconds, endSeconds]
    const segments = intervals
        .map(interval => {
            const { start, end } = parseInterval(interval);
            return [start, end];
        })
        .filter(([start, end]) => !Number.isNaN(start) && !Number.isNaN(end) && end > start);

    if (segments.length === 0) {
        console.warn('No valid segments found in results. Playing full video.');
        playFullVideo();
        return;
    }

    setupSegmentPlayback(segments);
}

/**
 * Parse interval string "HH:MM:SS - HH:MM:SS" to start and end times in seconds
 */
function parseInterval(intervalStr) {
    const [startStr, endStr] = intervalStr.split(' - ').map(s => s.trim());
    return {
        start: timeToSeconds(startStr),
        end: timeToSeconds(endStr)
    };
}

/**
 * Convert "HH:MM:SS" to seconds
 */
function timeToSeconds(timeStr) {
    const parts = timeStr.split(':');
    return parseInt(parts[0]) * 3600 + parseInt(parts[1]) * 60 + parseInt(parts[2]);
}

// Segment-looping playback state
let currentSegments = [];
let currentSegmentIndex = 0;
let segmentTimeUpdateHandler = null;

/**
 * Set up looping playback over a list of [start, end] segments (in seconds).
 */
function setupSegmentPlayback(segments) {
    // Clear any existing handler
    if (segmentTimeUpdateHandler) {
        videoPlayer.removeEventListener('timeupdate', segmentTimeUpdateHandler);
        segmentTimeUpdateHandler = null;
    }

    currentSegments = segments;
    currentSegmentIndex = 0;

    if (!currentSegments.length) {
        playFullVideo();
        return;
    }

    // Always use the original footage for segment playback, muted and without controls
    videoPlayer.src = ORIGINAL_VIDEO;
    videoPlayer.muted = true;
    videoPlayer.controls = false;
    videoPlayer.load();

    startBackgroundMusic();

    if (videoPlayer.readyState >= 1) {
        playCurrentSegment();
    } else {
        videoPlayer.onloadedmetadata = () => {
            playCurrentSegment();
        };
    }
}

/**
 * Play the current segment and set up timeupdate listener to loop through segments.
 */
function playCurrentSegment() {
    if (!currentSegments.length) {
        return;
    }

    const [start, end] = currentSegments[currentSegmentIndex];
    videoPlayer.currentTime = start;
    videoPlayer.play();

    segmentTimeUpdateHandler = () => {
        if (videoPlayer.currentTime >= end) {
            videoPlayer.removeEventListener('timeupdate', segmentTimeUpdateHandler);
            segmentTimeUpdateHandler = null;
            currentSegmentIndex = (currentSegmentIndex + 1) % currentSegments.length;
            playCurrentSegment();
        }
    };

    videoPlayer.addEventListener('timeupdate', segmentTimeUpdateHandler);
}

/**
 * Play the full original video without segment looping.
 */
function playFullVideo() {
    videoPlayer.src = ORIGINAL_VIDEO;
    videoPlayer.muted = true;
    videoPlayer.controls = false;
    videoPlayer.load();
    videoPlayer.play();
    startBackgroundMusic();
}

function startBackgroundMusic() {
    if (!bgMusic) return;
    try {
        bgMusic.loop = true;
        bgMusic.play();
    } catch (err) {
        console.warn('Unable to start background music:', err);
    }
}

function stopBackgroundMusic() {
    if (!bgMusic) return;
    bgMusic.pause();
    bgMusic.currentTime = 0;
}

/**
 * Show status message
 */
function showStatus(message, type = 'info') {
    statusMessage.textContent = message;
    statusMessage.className = 'status-message ' + type;
    
    // Auto-clear info messages after 5 seconds
    if (type === 'info') {
        setTimeout(() => {
            if (statusMessage.textContent === message) {
                statusMessage.textContent = '';
                statusMessage.className = 'status-message';
            }
        }, 5000);
    }
}

/**
 * Escape HTML special characters
 */
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

/**
 * Initialize on page load
 */
window.addEventListener('load', () => {
    console.log('Page loaded. Ready for video queries.');
    // Ensure title.mp4 plays with sound and controls until we switch to footages.mp4
    videoPlayer.muted = false;
    videoPlayer.controls = true;
    stopBackgroundMusic();
    showStatus('Ready. Enter queries to get started.', 'info');
});
