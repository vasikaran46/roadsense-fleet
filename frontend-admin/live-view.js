/**
 * RoadSense Fleet — Live Monitoring Controller
 * Manages device selection, live video stream, and detection display.
 */

const API_BASE = window.location.origin;
const WS_BASE = (window.location.protocol === 'https:' ? 'wss:' : 'ws:') + '//' + window.location.host;

let watchSocket = null;
let selectedDeviceId = null;
let liveCanvas = null;
let liveCtx = null;
let detectionsList = [];
let deviceRefreshTimer = null;

// ─── Initialize ───────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    liveCanvas = document.getElementById('liveCanvas');
    liveCtx = liveCanvas.getContext('2d');

    updateClock();
    setInterval(updateClock, 1000);

    fetchDevices();
    deviceRefreshTimer = setInterval(fetchDevices, 5000);
});


// ─── Fetch Devices ────────────────────────────
async function fetchDevices() {
    try {
        const res = await fetch(`${API_BASE}/devices`);
        if (!res.ok) throw new Error('Failed to fetch devices');
        const data = await res.json();

        renderDeviceList(data.devices || []);
        updateServerStatus('online');
    } catch (err) {
        console.error('Devices error:', err);
        updateServerStatus('offline');
    }
}


function renderDeviceList(devices) {
    const list = document.getElementById('deviceList');
    const onlineDevices = devices.filter(d => d.status === 'online');
    const offlineDevices = devices.filter(d => d.status !== 'online');
    const allDevices = [...onlineDevices, ...offlineDevices];

    document.getElementById('deviceCountLabel').textContent = `${onlineDevices.length} online`;

    if (!allDevices.length) {
        list.innerHTML = `
            <div class="empty-state" style="padding:30px 16px;">
                <span class="empty-icon" style="font-size:32px;">📡</span>
                <p>No devices connected</p>
                <p class="empty-sub">Start streaming from a mobile device</p>
            </div>`;
        return;
    }

    list.innerHTML = allDevices.map(d => {
        const isOnline = d.status === 'online';
        const isActive = d.device_id === selectedDeviceId;
        const gps = d.latitude
            ? `📍 ${d.latitude.toFixed(4)}, ${d.longitude.toFixed(4)}`
            : '📍 No GPS';

        return `
        <div class="device-item ${isActive ? 'active' : ''}"
             onclick="selectDevice('${d.device_id}')"
             style="${!isOnline ? 'opacity:0.5;' : ''}">
            <span class="status-dot ${isOnline ? 'online' : 'offline'}"></span>
            <div class="device-item-info">
                <div class="device-item-name">${d.device_id}</div>
                <div class="device-item-meta">${d.name || d.device_id} · ${gps}</div>
            </div>
        </div>`;
    }).join('');
}


// ─── Select & Watch Device ────────────────────
function selectDevice(deviceId) {
    if (selectedDeviceId === deviceId) return;

    // Disconnect previous
    if (watchSocket) {
        watchSocket.close();
        watchSocket = null;
    }

    selectedDeviceId = deviceId;
    detectionsList = [];
    renderDetections();

    // Update device list selection
    document.querySelectorAll('.device-item').forEach(el => el.classList.remove('active'));
    const items = document.querySelectorAll('.device-item');
    items.forEach(el => {
        if (el.querySelector('.device-item-name')?.textContent === deviceId) {
            el.classList.add('active');
        }
    });

    // Connect to watch WebSocket
    connectWatch(deviceId);
}


function connectWatch(deviceId) {
    const placeholder = document.getElementById('videoPlaceholder');
    const canvas = document.getElementById('liveCanvas');

    placeholder.innerHTML = '<p>Connecting to ' + deviceId + '...</p>';

    const url = `${WS_BASE}/ws/watch/${encodeURIComponent(deviceId)}`;
    watchSocket = new WebSocket(url);

    watchSocket.binaryType = 'arraybuffer';

    watchSocket.onopen = () => {
        console.log(`Watching ${deviceId}`);
        placeholder.style.display = 'none';
        canvas.style.display = 'block';
    };

    watchSocket.onmessage = (event) => {
        if (event.data instanceof ArrayBuffer) {
            // Binary frame — render on canvas
            renderFrame(event.data);
        } else {
            // Text — JSON detection/event
            try {
                const msg = JSON.parse(event.data);
                handleWatchMessage(msg);
            } catch (e) {
                console.error('Parse error:', e);
            }
        }
    };

    watchSocket.onclose = () => {
        console.log(`Watch disconnected: ${deviceId}`);
        if (selectedDeviceId === deviceId) {
            canvas.style.display = 'none';
            placeholder.style.display = 'flex';
            placeholder.innerHTML = `
                <span style="font-size:48px;">📡</span>
                <p>Stream ended for ${deviceId}</p>
                <p class="empty-sub">The device may have disconnected</p>`;
        }
    };

    watchSocket.onerror = (err) => {
        console.error('Watch error:', err);
    };
}


function renderFrame(arrayBuffer) {
    const blob = new Blob([arrayBuffer], { type: 'image/jpeg' });
    const url = URL.createObjectURL(blob);
    const img = new Image();

    img.onload = () => {
        liveCanvas.width = img.width;
        liveCanvas.height = img.height;
        liveCtx.drawImage(img, 0, 0);
        URL.revokeObjectURL(url);
    };

    img.src = url;
}


function handleWatchMessage(msg) {
    if (msg.type === 'detection' || msg.type === 'new_event') {
        const data = msg.data || msg;
        addDetection(data);
    } else if (msg.type === 'device_info') {
        console.log('Device info:', msg.data);
    }
}


// ─── Live Detections ──────────────────────────
function addDetection(data) {
    detectionsList.unshift({
        ...data,
        received_at: new Date().toLocaleTimeString('en-IN'),
    });

    // Keep last 50
    if (detectionsList.length > 50) detectionsList.pop();

    renderDetections();
    showDetectionToast(data);

    document.getElementById('detectionCount').textContent = detectionsList.length;
}


function renderDetections() {
    const container = document.getElementById('liveDetectionsList');

    if (!detectionsList.length) {
        container.innerHTML = `
            <div class="empty-state" style="padding:20px;">
                <p class="empty-sub">Detections will appear here in real-time</p>
            </div>`;
        return;
    }

    const iconMap = {
        pothole: '🕳️', road_damage: '⚠️', crack: '⚠️',
        longitudinal_crack: '⚡', transverse_crack: '⚡',
        lateral_crack: '⚡', alligator_crack: '🐊', edge_crack: '⚠️',
        traffic_sign: '🛑', zebra_crossing: '🚶',
        waterlogging: '🌊', car: '🚗', bus: '🚌',
        truck: '🚛', motorcycle: '🏍️', person: '🚶',
    };

    container.innerHTML = detectionsList.map(d => {
        const icon = iconMap[d.detection_type] || '📋';
        const typeName = (d.detection_type || '').replace(/_/g, ' ').toUpperCase();
        const confidence = d.confidence ? (d.confidence * 100).toFixed(0) : '?';
        const snapshotUrl = d.snapshot_path ? `${API_BASE}/snapshots/${d.snapshot_path}` : '';

        return `
        <div class="live-detection-item">
            <span class="live-detection-icon">${icon}</span>
            <div class="live-detection-info">
                <div class="live-detection-type">${typeName}</div>
                <div class="live-detection-meta">
                    ${confidence}% · ${d.severity || 'N/A'} · ${d.received_at || ''}
                </div>
            </div>
            ${snapshotUrl ? `<img src="${snapshotUrl}" class="live-detection-snapshot" onerror="this.style.display='none'" title="Evidence">` : ''}
        </div>`;
    }).join('');
}


function showDetectionToast(data) {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const typeName = (data.detection_type || '').replace(/_/g, ' ').toUpperCase();
    const severity = data.severity || 'N/A';
    const severityClass = { high: 'danger', medium: 'warning' }[severity] || '';

    const el = document.createElement('div');
    el.className = `toast-item ${severityClass}`;
    el.innerHTML = `
        <div class="toast-title">🔔 ${typeName}</div>
        <div class="toast-message">${data.device_id || ''} · ${severity} severity</div>`;
    container.appendChild(el);

    setTimeout(() => {
        el.classList.add('removing');
        setTimeout(() => el.remove(), 300);
    }, 4000);
}


// ─── Helpers ──────────────────────────────────
function updateClock() {
    const el = document.getElementById('topbarTime');
    if (el) el.textContent = new Date().toLocaleTimeString('en-IN', { hour12: true });
}

function updateServerStatus(status) {
    const el = document.getElementById('serverStatus');
    if (!el) return;
    const dot = el.querySelector('.status-dot');
    const text = el.querySelector('span:last-child');
    dot.className = 'status-dot ' + status;
    text.textContent = status === 'online' ? 'Server connected' : 'Server offline';
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    sidebar.classList.toggle('open');
    if (overlay) overlay.classList.toggle('active');
}

function closeSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    if (sidebar) sidebar.classList.remove('open');
    if (overlay) overlay.classList.remove('active');
}
