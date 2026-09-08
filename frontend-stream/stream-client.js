/**
 * RoadSense Fleet — Mobile Streaming Client
 * Captures camera/video frames and streams them to the backend via WebSocket.
 */

// State
let ws = null;
let mediaStream = null;
let videoElement = null;
let captureCanvas = null;
let captureCtx = null;
let captureInterval = null;
let gpsWatchId = null;
let frameCount = 0;
let startTime = null;
let isStreaming = false;
let currentGps = { latitude: null, longitude: null };
let demoVideoFile = null;

// Config
const FPS = 8;
const JPEG_QUALITY = 0.7;
const GPS_SEND_INTERVAL = 3000; // Send GPS every 3 seconds
let gpsSendTimer = null;

// DOM Elements
const setupPanel = document.getElementById('setupPanel');
const streamPanel = document.getElementById('streamPanel');
const connectionBadge = document.getElementById('connectionBadge');
const connectionText = document.getElementById('connectionText');
const toast = document.getElementById('toast');

// Demo mode toggle
document.getElementById('demoMode').addEventListener('change', function() {
    document.getElementById('demoVideo').style.display = this.checked ? 'block' : 'none';
});

document.getElementById('demoVideo').addEventListener('change', function(e) {
    if (e.target.files.length > 0) {
        demoVideoFile = e.target.files[0];
    }
});

// Auto-detect server URL
(function autoDetectServer() {
    const host = window.location.hostname || 'localhost';
    const port = '8000';
    document.getElementById('serverUrl').value = `ws://${host}:${port}`;
})();


async function startStreaming() {
    const serverUrl = document.getElementById('serverUrl').value.trim();
    const deviceId = document.getElementById('deviceId').value.trim();
    const deviceName = document.getElementById('deviceName').value.trim();
    const isDemoMode = document.getElementById('demoMode').checked;
    const cameraFacing = document.getElementById('cameraSelect').value;

    if (!serverUrl) { showToast('Enter a server URL', 'error'); return; }
    if (!deviceId) { showToast('Enter a Device ID', 'error'); return; }

    try {
        // Initialize video source
        videoElement = document.getElementById('videoPreview');
        captureCanvas = document.getElementById('captureCanvas');
        captureCtx = captureCanvas.getContext('2d');

        if (isDemoMode && demoVideoFile) {
            // Demo mode: use video file
            const url = URL.createObjectURL(demoVideoFile);
            videoElement.src = url;
            videoElement.loop = true;
            videoElement.muted = true;
            await videoElement.play();
            showToast('Demo mode: using video file', 'success');
        } else {
            // Live camera mode
            const constraints = {
                video: {
                    facingMode: cameraFacing,
                    width: { ideal: 640 },
                    height: { ideal: 480 },
                },
                audio: false,
            };

            try {
                mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
                videoElement.srcObject = mediaStream;
                await videoElement.play();
            } catch (camErr) {
                showToast('Camera access denied: ' + camErr.message, 'error');
                return;
            }
        }

        // Set canvas size
        captureCanvas.width = 640;
        captureCanvas.height = 480;

        // Connect WebSocket
        const wsUrl = `${serverUrl}/ws/stream/${encodeURIComponent(deviceId)}`;
        connectWebSocket(wsUrl, deviceId, deviceName);

        // Start GPS
        startGps();

        // Switch UI
        setupPanel.style.display = 'none';
        streamPanel.style.display = 'block';
        document.getElementById('overlayDeviceId').textContent = deviceId;

        isStreaming = true;
        startTime = Date.now();
        frameCount = 0;

        // Start duration timer
        setInterval(updateDuration, 1000);

    } catch (err) {
        showToast('Failed to start: ' + err.message, 'error');
        console.error(err);
    }
}


function connectWebSocket(url, deviceId, deviceName) {
    updateConnectionStatus('connecting');

    ws = new WebSocket(url);

    ws.onopen = () => {
        updateConnectionStatus('online');
        showToast('Connected to server!', 'success');

        // Send device info
        ws.send(JSON.stringify({
            type: 'info',
            name: deviceName,
            device_id: deviceId,
        }));

        // Start frame capture
        captureInterval = setInterval(captureAndSend, 1000 / FPS);

        // Start periodic GPS send
        gpsSendTimer = setInterval(sendGps, GPS_SEND_INTERVAL);
    };

    ws.onclose = (event) => {
        updateConnectionStatus('offline');
        if (isStreaming) {
            showToast('Connection lost. Reconnecting...', 'error');
            setTimeout(() => {
                if (isStreaming) connectWebSocket(url, deviceId, deviceName);
            }, 3000);
        }
    };

    ws.onerror = (err) => {
        console.error('WebSocket error:', err);
        updateConnectionStatus('offline');
    };

    ws.onmessage = (event) => {
        // Handle detection notifications from backend
        try {
            const data = JSON.parse(event.data);
            if (data.type === 'detection') {
                showDetection(data.data);
            }
        } catch (e) { /* binary or non-JSON */ }
    };
}


function captureAndSend() {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    if (!videoElement || videoElement.paused) return;

    try {
        captureCtx.drawImage(videoElement, 0, 0, captureCanvas.width, captureCanvas.height);
        captureCanvas.toBlob(
            (blob) => {
                if (blob && ws.readyState === WebSocket.OPEN) {
                    ws.send(blob);
                    frameCount++;
                    document.getElementById('statusFrames').textContent = frameCount.toLocaleString();

                    // Update FPS display
                    const elapsed = (Date.now() - startTime) / 1000;
                    const fps = Math.round(frameCount / elapsed);
                    document.getElementById('overlayFps').textContent = `${fps} FPS`;
                }
            },
            'image/jpeg',
            JPEG_QUALITY
        );
    } catch (e) {
        console.error('Frame capture error:', e);
    }
}


function startGps() {
    if (!navigator.geolocation) {
        document.getElementById('statusGps').textContent = '❌ Not supported';
        document.getElementById('overlayGps').textContent = '📍 GPS unavailable';
        return;
    }

    gpsWatchId = navigator.geolocation.watchPosition(
        (pos) => {
            currentGps.latitude = pos.coords.latitude;
            currentGps.longitude = pos.coords.longitude;

            const lat = pos.coords.latitude.toFixed(5);
            const lon = pos.coords.longitude.toFixed(5);
            document.getElementById('statusGps').textContent = `📍 ${lat}, ${lon}`;
            document.getElementById('overlayGps').textContent = `📍 ${lat}, ${lon}`;
        },
        (err) => {
            console.warn('GPS error:', err.message);
            document.getElementById('statusGps').textContent = '⚠️ ' + err.message;
            document.getElementById('overlayGps').textContent = '📍 GPS unavailable';
        },
        {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 5000,
        }
    );
}


function sendGps() {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    if (currentGps.latitude === null) return;

    ws.send(JSON.stringify({
        type: 'gps',
        latitude: currentGps.latitude,
        longitude: currentGps.longitude,
    }));
}


function stopStreaming() {
    isStreaming = false;

    // Stop frame capture
    if (captureInterval) { clearInterval(captureInterval); captureInterval = null; }
    if (gpsSendTimer) { clearInterval(gpsSendTimer); gpsSendTimer = null; }

    // Stop GPS
    if (gpsWatchId) { navigator.geolocation.clearWatch(gpsWatchId); gpsWatchId = null; }

    // Close WebSocket
    if (ws) { ws.close(); ws = null; }

    // Stop camera
    if (mediaStream) {
        mediaStream.getTracks().forEach(t => t.stop());
        mediaStream = null;
    }

    // Stop demo video
    if (videoElement) {
        videoElement.pause();
        videoElement.srcObject = null;
        videoElement.src = '';
    }

    // Switch UI
    streamPanel.style.display = 'none';
    setupPanel.style.display = 'block';
    updateConnectionStatus('offline');
    showToast('Streaming stopped', 'success');
}


function updateConnectionStatus(status) {
    const dot = connectionBadge.querySelector('.status-dot');
    dot.className = 'status-dot ' + status;

    const statusMap = { online: 'Connected', offline: 'Disconnected', connecting: 'Connecting...' };
    connectionText.textContent = statusMap[status] || status;

    const connCard = document.getElementById('statusConnection');
    connCard.innerHTML = `<span class="status-dot ${status}"></span> ${statusMap[status]}`;
}


function updateDuration() {
    if (!startTime || !isStreaming) return;
    const elapsed = Math.floor((Date.now() - startTime) / 1000);
    const mins = Math.floor(elapsed / 60).toString().padStart(2, '0');
    const secs = (elapsed % 60).toString().padStart(2, '0');
    document.getElementById('statusDuration').textContent = `${mins}:${secs}`;
}


function showDetection(data) {
    const card = document.getElementById('detectionCard');
    const info = document.getElementById('detectionInfo');
    card.style.display = 'block';
    info.innerHTML = `
        <div style="font-weight:600; color: var(--warning); font-size:16px;">${(data.detection_type || '').toUpperCase()}</div>
        <div style="color: var(--text-secondary); margin-top:4px;">
            Confidence: ${(data.confidence * 100).toFixed(0)}% · Severity: ${data.severity || 'N/A'}
        </div>
    `;
    // Auto-hide after 5 seconds
    setTimeout(() => { card.style.display = 'none'; }, 5000);
}


function showToast(message, type = '') {
    toast.textContent = message;
    toast.className = 'toast show ' + type;
    setTimeout(() => { toast.className = 'toast'; }, 3000);
}
