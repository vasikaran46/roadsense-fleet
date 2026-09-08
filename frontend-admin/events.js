/**
 * RoadSense Fleet — Events Page Controller
 * Fetches, filters, and displays detection events with evidence images.
 */

const API_BASE = window.location.protocol + '//' + window.location.hostname + ':8000';
const WS_BASE = 'ws://' + window.location.hostname + ':8000';

let allEvents = [];
let eventSocket = null;

// ─── Initialize ───────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    updateClock();
    setInterval(updateClock, 1000);

    fetchEvents();
    fetchDevicesForFilter();
    connectEventSocket();

    // Auto-refresh
    setInterval(fetchEvents, 20000);
});


// ─── Fetch Events ─────────────────────────────
async function fetchEvents() {
    try {
        const type = document.getElementById('filterType').value;
        const severity = document.getElementById('filterSeverity').value;
        const device = document.getElementById('filterDevice').value;
        const status = document.getElementById('filterStatus').value;

        let url = `${API_BASE}/events?limit=200`;
        if (type) url += `&detection_type=${type}`;
        if (severity) url += `&severity=${severity}`;
        if (device) url += `&device_id=${device}`;
        if (status) url += `&status=${status}`;

        const res = await fetch(url);
        if (!res.ok) throw new Error('Failed');
        const data = await res.json();

        allEvents = data.events || [];
        document.getElementById('eventTotal').textContent = `${data.total} events`;

        renderEvents(allEvents);
        updateServerStatus('online');
    } catch (err) {
        console.error('Events error:', err);
        updateServerStatus('offline');
    }
}

function applyFilters() {
    fetchEvents();
}


// ─── Fetch Devices for Filter ─────────────────
async function fetchDevicesForFilter() {
    try {
        const res = await fetch(`${API_BASE}/devices`);
        if (!res.ok) return;
        const data = await res.json();

        const select = document.getElementById('filterDevice');
        (data.devices || []).forEach(d => {
            const opt = document.createElement('option');
            opt.value = d.device_id;
            opt.textContent = d.device_id;
            select.appendChild(opt);
        });
    } catch (e) {}
}


// ─── Render Events Grid ───────────────────────
function renderEvents(events) {
    const grid = document.getElementById('eventsGrid');

    if (!events.length) {
        grid.innerHTML = `
            <div class="empty-state" style="grid-column: 1/-1;">
                <span class="empty-icon">📭</span>
                <p>No events found</p>
                <p class="empty-sub">Try adjusting your filters or start streaming</p>
            </div>`;
        return;
    }

    const iconMap = {
        pothole: '🕳️', road_damage: '⚠️', crack: '⚠️',
        longitudinal_crack: '⚠️', transverse_crack: '⚠️',
        waterlogging: '🌊', car: '🚗', bus: '🚌', truck: '🚛',
    };

    grid.innerHTML = events.map(e => {
        const typeName = (e.detection_type || '').replace(/_/g, ' ').toUpperCase();
        const icon = iconMap[e.detection_type] || '📋';
        const confidence = e.confidence ? (e.confidence * 100).toFixed(0) : '?';
        const time = e.timestamp ? new Date(e.timestamp).toLocaleString('en-IN') : '';
        const lat = e.latitude ? e.latitude.toFixed(4) : 'N/A';
        const lon = e.longitude ? e.longitude.toFixed(4) : 'N/A';
        const snapshotUrl = e.snapshot_path ? `${API_BASE}/snapshots/${e.snapshot_path}` : '';

        return `
        <div class="event-card" onclick="showEventDetail(${e.id})">
            ${snapshotUrl
                ? `<img src="${snapshotUrl}" class="event-card-image" alt="Evidence" loading="lazy" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 320 200%22><rect fill=%22%23111a2e%22 width=%22320%22 height=%22200%22/><text x=%22160%22 y=%22100%22 fill=%22%234e5d73%22 font-size=%2216%22 text-anchor=%22middle%22>No Image</text></svg>'">`
                : `<div class="event-card-image" style="display:flex;align-items:center;justify-content:center;font-size:48px;background:var(--bg-secondary);">${icon}</div>`
            }
            <div class="event-card-body">
                <div class="event-card-type">
                    <span>${icon} ${typeName}</span>
                    <span class="severity-badge severity-${e.severity}">${e.severity}</span>
                </div>
                <div class="event-card-details">
                    <div><span class="event-detail-label">Confidence</span><br>${confidence}%</div>
                    <div><span class="event-detail-label">Device</span><br>${e.device_id}</div>
                    <div><span class="event-detail-label">GPS</span><br>${lat}, ${lon}</div>
                    <div><span class="event-detail-label">Time</span><br>${time}</div>
                </div>
            </div>
        </div>`;
    }).join('');
}


// ─── Event Detail Modal ───────────────────────
async function showEventDetail(eventId) {
    try {
        const res = await fetch(`${API_BASE}/events/${eventId}`);
        if (!res.ok) return;
        const e = await res.json();

        const modal = document.getElementById('eventModal');
        const content = document.getElementById('eventModalContent');
        const typeName = (e.detection_type || '').replace(/_/g, ' ').toUpperCase();
        const snapshotUrl = e.snapshot_path ? `${API_BASE}/snapshots/${e.snapshot_path}` : '';
        const time = e.timestamp ? new Date(e.timestamp).toLocaleString('en-IN') : 'N/A';
        const lat = e.latitude ? e.latitude.toFixed(5) : 'N/A';
        const lon = e.longitude ? e.longitude.toFixed(5) : 'N/A';

        content.innerHTML = `
        <div class="modal-header">
            <h3>📸 Event #${e.id} — ${typeName}</h3>
            <button class="modal-close" onclick="closeModal()">&times;</button>
        </div>
        <div class="modal-body">
            ${snapshotUrl ? `<img src="${snapshotUrl}" class="modal-image" alt="Evidence">` : ''}
            <div class="modal-details">
                <div class="modal-detail">
                    <div class="modal-detail-label">Type</div>
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
                    <div class="modal-detail-label">Status</div>
                    <div class="modal-detail-value">${e.status || 'new'}</div>
                </div>
                <div class="modal-detail">
                    <div class="modal-detail-label">Device</div>
                    <div class="modal-detail-value">${e.device_id}</div>
                </div>
                <div class="modal-detail">
                    <div class="modal-detail-label">Timestamp</div>
                    <div class="modal-detail-value">${time}</div>
                </div>
                <div class="modal-detail" style="grid-column:1/-1;">
                    <div class="modal-detail-label">GPS Coordinates</div>
                    <div class="modal-detail-value">${lat}, ${lon}</div>
                </div>
            </div>
        </div>`;

        modal.classList.add('active');
        modal.onclick = (ev) => { if (ev.target === modal) closeModal(); };
    } catch (err) {
        console.error('Event detail error:', err);
    }
}

function closeModal() {
    document.getElementById('eventModal').classList.remove('active');
}


// ─── Real-Time Event WebSocket ────────────────
function connectEventSocket() {
    eventSocket = new WebSocket(`${WS_BASE}/ws/events`);

    eventSocket.onopen = () => updateServerStatus('online');

    eventSocket.onmessage = (e) => {
        try {
            const msg = JSON.parse(e.data);
            if (msg.type === 'new_event') {
                // Prepend to list
                allEvents.unshift(msg.data);
                renderEvents(allEvents);
                document.getElementById('eventTotal').textContent = `${allEvents.length} events`;
            }
        } catch (err) {}
    };

    eventSocket.onclose = () => {
        updateServerStatus('offline');
        setTimeout(connectEventSocket, 5000);
    };

    setInterval(() => {
        if (eventSocket?.readyState === WebSocket.OPEN) {
            eventSocket.send(JSON.stringify({ type: 'ping' }));
        }
    }, 30000);
}


// ─── Helpers ──────────────────────────────────
function updateClock() {
    const el = document.getElementById('topbarTime');
    if (el) el.textContent = new Date().toLocaleTimeString('en-IN', { hour12: true });
}

function updateServerStatus(status) {
    const el = document.getElementById('serverStatus');
    if (!el) return;
    el.querySelector('.status-dot').className = 'status-dot ' + status;
    el.querySelector('span:last-child').textContent = status === 'online' ? 'Server connected' : 'Server offline';
}

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('open');
}
