/**
 * RoadSense Fleet — Dashboard Controller
 * Fetches stats, manages real-time event WebSocket, updates KPIs.
 */

const API_BASE = window.location.protocol + '//' + window.location.hostname + ':8000';
const WS_BASE = 'ws://' + window.location.hostname + ':8000';

let eventSocket = null;
let deviceRefreshTimer = null;

// ─── Initialization ───────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    updateClock();
    setInterval(updateClock, 1000);

    fetchStats();
    fetchDevices();
    connectEventSocket();

    // Auto-refresh devices every 10s
    deviceRefreshTimer = setInterval(fetchDevices, 10000);
    // Auto-refresh stats every 15s
    setInterval(fetchStats, 15000);
});


// ─── Fetch Stats ──────────────────────────────
async function fetchStats() {
    try {
        const res = await fetch(`${API_BASE}/events/stats`);
        if (!res.ok) throw new Error('Stats fetch failed');
        const data = await res.json();

        // Update KPI cards
        document.getElementById('kpiTotal').textContent = data.total_events || 0;
        document.getElementById('kpiPotholes').textContent = data.by_type?.pothole || 0;
        document.getElementById('kpiDamage').textContent =
            (data.by_type?.road_damage || 0) +
            (data.by_type?.crack || 0) +
            (data.by_type?.longitudinal_crack || 0) +
            (data.by_type?.transverse_crack || 0) +
            (data.by_type?.alligator_crack || 0);
        document.getElementById('kpiVehicles').textContent =
            (data.by_type?.car || 0) + (data.by_type?.bus || 0) +
            (data.by_type?.truck || 0) + (data.by_type?.motorcycle || 0);
        document.getElementById('kpiWaterlogging').textContent = data.by_type?.waterlogging || 0;

        // Update event badge in nav
        document.getElementById('navEventCount').textContent = data.total_events || 0;

        // Update recent events
        renderRecentEvents(data.recent_events || []);

        // Update map markers
        if (typeof updateMapMarkers === 'function') {
            updateMapMarkers(data.recent_events || []);
        }

        // Update charts
        if (typeof updateCharts === 'function') {
            updateCharts(data);
        }

        updateServerStatus('online');
    } catch (err) {
        console.error('Stats error:', err);
        updateServerStatus('offline');
    }
}


// ─── Fetch Devices ────────────────────────────
async function fetchDevices() {
    try {
        const res = await fetch(`${API_BASE}/devices`);
        if (!res.ok) return;
        const data = await res.json();

        const onlineCount = data.devices?.filter(d => d.status === 'online').length || 0;
        document.getElementById('activeDeviceCount').textContent = onlineCount;
        document.getElementById('kpiDevices').textContent = onlineCount;

        const dot = document.querySelector('#deviceIndicator .status-dot');
        dot.className = 'status-dot ' + (onlineCount > 0 ? 'online' : 'offline');
    } catch (err) {
        console.error('Devices error:', err);
    }
}


// ─── Real-Time Event WebSocket ────────────────
function connectEventSocket() {
    eventSocket = new WebSocket(`${WS_BASE}/ws/events`);

    eventSocket.onopen = () => {
        console.log('Event WebSocket connected');
        updateServerStatus('online');
    };

    eventSocket.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);
            if (msg.type === 'new_event') {
                handleNewEvent(msg.data);
            }
        } catch (e) {
            console.error('Event parse error:', e);
        }
    };

    eventSocket.onclose = () => {
        updateServerStatus('offline');
        setTimeout(connectEventSocket, 5000);
    };

    eventSocket.onerror = () => {
        updateServerStatus('offline');
    };

    // Keep-alive ping every 30s
    setInterval(() => {
        if (eventSocket && eventSocket.readyState === WebSocket.OPEN) {
            eventSocket.send(JSON.stringify({ type: 'ping' }));
        }
    }, 30000);
}


function handleNewEvent(eventData) {
    // Show toast notification
    showEventToast(eventData);

    // Refresh stats
    fetchStats();

    // Add marker to map
    if (typeof addMapMarker === 'function' && eventData.latitude && eventData.longitude) {
        addMapMarker(eventData);
    }
}


// ─── Render Recent Events ─────────────────────
function renderRecentEvents(events) {
    const list = document.getElementById('recentList');
    if (!events.length) {
        list.innerHTML = `
            <div class="empty-state">
                <span class="empty-icon">📭</span>
                <p>No incidents detected yet</p>
                <p class="empty-sub">Start streaming from a device to see detections here</p>
            </div>`;
        return;
    }

    const iconMap = {
        pothole: '🕳️',
        road_damage: '⚠️',
        crack: '⚠️',
        longitudinal_crack: '⚠️',
        transverse_crack: '⚠️',
        alligator_crack: '⚠️',
        waterlogging: '🌊',
        car: '🚗',
        bus: '🚌',
        truck: '🚛',
        motorcycle: '🏍️',
        person: '🚶',
    };

    list.innerHTML = events.map(e => {
        const icon = iconMap[e.detection_type] || '📋';
        const time = e.timestamp ? new Date(e.timestamp).toLocaleTimeString('en-IN') : '';
        const typeName = (e.detection_type || '').replace(/_/g, ' ');

        return `
        <div class="recent-item" onclick="showEventModal(${e.id})">
            <div class="recent-item-icon ${e.detection_type}">${icon}</div>
            <div class="recent-item-info">
                <div class="recent-item-title">${typeName.toUpperCase()}</div>
                <div class="recent-item-meta">
                    <span>${e.device_id || ''}</span>
                    <span>${(e.confidence * 100).toFixed(0)}%</span>
                    <span>${time}</span>
                </div>
            </div>
            <span class="severity-badge severity-${e.severity}">${e.severity}</span>
        </div>`;
    }).join('');
}


// ─── Event Modal ──────────────────────────────
async function showEventModal(eventId) {
    try {
        const res = await fetch(`${API_BASE}/events/${eventId}`);
        if (!res.ok) return;
        const e = await res.json();

        const snapshotUrl = e.snapshot_path ? `${API_BASE}/snapshots/${e.snapshot_path}` : '';
        const time = e.timestamp ? new Date(e.timestamp).toLocaleString('en-IN') : 'N/A';
        const lat = e.latitude ? e.latitude.toFixed(5) : 'N/A';
        const lon = e.longitude ? e.longitude.toFixed(5) : 'N/A';
        const typeName = (e.detection_type || '').replace(/_/g, ' ').toUpperCase();

        // Create modal
        let overlay = document.getElementById('eventModal');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'eventModal';
            overlay.className = 'modal-overlay';
            document.body.appendChild(overlay);
        }

        overlay.innerHTML = `
        <div class="modal">
            <div class="modal-header">
                <h3>📸 ${typeName}</h3>
                <button class="modal-close" onclick="closeModal()">&times;</button>
            </div>
            <div class="modal-body">
                ${snapshotUrl ? `<img src="${snapshotUrl}" class="modal-image" alt="Evidence" onerror="this.style.display='none'">` : ''}
                <div class="modal-details">
                    <div class="modal-detail">
                        <div class="modal-detail-label">Detection Type</div>
                        <div class="modal-detail-value">${typeName}</div>
                    </div>
                    <div class="modal-detail">
                        <div class="modal-detail-label">Confidence</div>
                        <div class="modal-detail-value">${(e.confidence * 100).toFixed(1)}%</div>
                    </div>
                    <div class="modal-detail">
                        <div class="modal-detail-label">Severity</div>
                        <div class="modal-detail-value"><span class="severity-badge severity-${e.severity}">${e.severity}</span></div>
                    </div>
                    <div class="modal-detail">
                        <div class="modal-detail-label">Device</div>
                        <div class="modal-detail-value">${e.device_id}</div>
                    </div>
                    <div class="modal-detail">
                        <div class="modal-detail-label">Time</div>
                        <div class="modal-detail-value">${time}</div>
                    </div>
                    <div class="modal-detail">
                        <div class="modal-detail-label">GPS</div>
                        <div class="modal-detail-value">${lat}, ${lon}</div>
                    </div>
                </div>
            </div>
        </div>`;
        overlay.classList.add('active');
        overlay.onclick = (ev) => { if (ev.target === overlay) closeModal(); };
    } catch (err) {
        console.error('Modal error:', err);
    }
}

function closeModal() {
    const overlay = document.getElementById('eventModal');
    if (overlay) overlay.classList.remove('active');
}


// ─── Toast Notifications ──────────────────────
function showEventToast(eventData) {
    const container = document.getElementById('toastContainer');
    const typeName = (eventData.detection_type || '').replace(/_/g, ' ').toUpperCase();
    const confidence = (eventData.confidence * 100).toFixed(0);

    const severityClass = {
        high: 'danger',
        medium: 'warning',
        low: '',
    }[eventData.severity] || '';

    const toastEl = document.createElement('div');
    toastEl.className = `toast-item ${severityClass}`;
    toastEl.innerHTML = `
        <div class="toast-title">🔔 ${typeName} Detected</div>
        <div class="toast-message">
            ${confidence}% confidence · ${eventData.device_id} · ${eventData.severity} severity
        </div>`;
    container.appendChild(toastEl);

    // Auto-remove after 6s
    setTimeout(() => {
        toastEl.classList.add('removing');
        setTimeout(() => toastEl.remove(), 300);
    }, 6000);
}


// ─── UI Helpers ───────────────────────────────
function updateClock() {
    const now = new Date();
    const el = document.getElementById('topbarTime');
    if (el) el.textContent = now.toLocaleTimeString('en-IN', { hour12: true });
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
    document.getElementById('sidebar').classList.toggle('open');
}
