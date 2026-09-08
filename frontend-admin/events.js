/**
 * RoadSense Fleet — Events Page Controller
 * Fetches, filters, and displays detection events with evidence images.
 */

const API_BASE = window.location.origin;
const WS_BASE = (window.location.protocol === 'https:' ? 'wss:' : 'ws:') + '//' + window.location.host;

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
        longitudinal_crack: '⚡', transverse_crack: '⚡',
        lateral_crack: '⚡', alligator_crack: '🐊', edge_crack: '⚠️',
        traffic_sign: '🛑', zebra_crossing: '🚶',
        waterlogging: '🌊', car: '🚗', bus: '🚌', truck: '🚛',
    };

    grid.innerHTML = events.map(e => {
        let typeName = (e.detection_type || '').replace(/_/g, ' ').toUpperCase();
        if (e.subtype) {
            typeName += ` · ${e.subtype.replace(/_/g, ' ').toUpperCase()}`;
        }
        const icon = iconMap[e.detection_type] || '📋';
        const confidence = e.confidence ? (e.confidence * 100).toFixed(0) : '?';
        const time = e.timestamp ? new Date(e.timestamp).toLocaleString('en-IN') : '';
        const lat = e.latitude ? e.latitude.toFixed(4) : 'N/A';
        const lon = e.longitude ? e.longitude.toFixed(4) : 'N/A';
        const snapshotUrl = e.snapshot_path ? `${API_BASE}/snapshots/${e.snapshot_path}` : '';

        return `
        <div class="event-card" data-event-id="${e.id}" onclick="showEventDetail(${e.id})">
            ${snapshotUrl
                ? `<img src="${snapshotUrl}" class="event-card-image" alt="Evidence" loading="lazy" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 320 200%22><rect fill=%22%23111a2e%22 width=%22320%22 height=%22200%22/><text x=%22160%22 y=%22100%22 fill=%22%234e5d73%22 font-size=%2216%22 text-anchor=%22middle%22>No Image</text></svg>'">`
                : `<div class="event-card-image" style="display:flex;align-items:center;justify-content:center;font-size:48px;background:var(--bg-secondary);">${icon}</div>`
            }
            <div class="event-card-body">
                <div class="event-card-type">
                    <span>${icon} ${typeName}</span>
                    <div style="display:flex;align-items:center;gap:8px;">
                        <span class="severity-badge severity-${e.severity}">${e.severity}</span>
                        <button class="event-card-delete-btn" type="button" title="Delete Event" onclick="handleCardDelete(event, ${e.id})">🗑️</button>
                    </div>
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
        </div>
        <div class="modal-footer">
            <button class="btn-delete" type="button" onclick="handleCardDelete(event, ${e.id})">🗑️ Delete Event</button>
            <button class="btn-secondary" type="button" onclick="closeModal()">Close</button>
        </div>`;

        modal.classList.add('active');
        modal.onclick = (ev) => { if (ev.target === modal) closeModal(); };
    } catch (err) {
        console.error('Event detail error:', err);
    }
}

function closeModal() {
    const modal = document.getElementById('eventModal');
    if (modal) modal.classList.remove('active');
}


// ─── Delete Operations & Custom Modal ─────────
function handleCardDelete(event, eventId) {
    if (event) {
        event.stopPropagation();
        event.preventDefault();
    }
    showConfirmDelete(eventId);
}

function showConfirmDelete(eventId) {
    const modal = document.getElementById('confirmDeleteModal');
    const title = document.getElementById('confirmDeleteTitle');
    const message = document.getElementById('confirmDeleteMessage');
    const btn = document.getElementById('confirmActionBtn');

    title.textContent = `Delete Event #${eventId}?`;
    message.textContent = `Are you sure you want to delete Event #${eventId}? This will permanently remove its evidence snapshot from disk.`;
    
    btn.onclick = () => deleteEventConfirmed(eventId);
    btn.textContent = 'Yes, Delete';

    modal.classList.add('active');
    modal.onclick = (ev) => { if (ev.target === modal) closeConfirmModal(); };
}

function showConfirmClearAll() {
    if (!allEvents.length) {
        showToast('No events to delete', 'warning');
        return;
    }

    const modal = document.getElementById('confirmDeleteModal');
    const title = document.getElementById('confirmDeleteTitle');
    const message = document.getElementById('confirmDeleteMessage');
    const btn = document.getElementById('confirmActionBtn');

    title.textContent = `Clear All Events?`;
    message.textContent = `Are you sure you want to permanently delete all ${allEvents.length} recorded events? This cannot be undone.`;
    
    btn.onclick = () => clearAllEventsConfirmed();
    btn.textContent = `Clear All (${allEvents.length})`;

    modal.classList.add('active');
    modal.onclick = (ev) => { if (ev.target === modal) closeConfirmModal(); };
}

function closeConfirmModal() {
    const modal = document.getElementById('confirmDeleteModal');
    if (modal) modal.classList.remove('active');
}

async function deleteEventConfirmed(eventId) {
    closeConfirmModal();
    closeModal();

    // Optimistic / Instant DOM update with smooth fade-out
    const cardEl = document.querySelector(`.event-card[data-event-id="${eventId}"]`);
    if (cardEl) {
        cardEl.style.transition = 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
        cardEl.style.opacity = '0';
        cardEl.style.transform = 'scale(0.92)';
        setTimeout(() => {
            if (cardEl && cardEl.parentNode) cardEl.remove();
        }, 300);
    }

    // Update in-memory list
    allEvents = allEvents.filter(ev => ev.id !== eventId);
    const totalEl = document.getElementById('eventTotal');
    if (totalEl) totalEl.textContent = `${allEvents.length} events`;

    if (allEvents.length === 0) {
        setTimeout(() => renderEvents([]), 350);
    }

    try {
        const res = await fetch(`${API_BASE}/events/${eventId}`, { method: 'DELETE' });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        showToast(`Event #${eventId} deleted successfully`, 'success');
    } catch (err) {
        console.error('Delete event error:', err);
        showToast(`Failed to delete Event #${eventId}: ${err.message}`, 'danger');
        // Rollback by re-fetching
        fetchEvents();
    }
}

async function clearAllEventsConfirmed() {
    closeConfirmModal();

    const grid = document.getElementById('eventsGrid');
    if (grid) {
        grid.style.transition = 'opacity 0.3s ease';
        grid.style.opacity = '0';
        setTimeout(() => {
            renderEvents([]);
            grid.style.opacity = '1';
        }, 300);
    }

    const totalEl = document.getElementById('eventTotal');
    if (totalEl) totalEl.textContent = `0 events`;
    allEvents = [];

    try {
        const res = await fetch(`${API_BASE}/events`, { method: 'DELETE' });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        showToast(`Cleared ${data.deleted_count || 0} events successfully`, 'success');
    } catch (err) {
        console.error('Clear events error:', err);
        showToast('Failed to clear events from server', 'danger');
        fetchEvents();
    }
}


function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast-item ${type}`;
    const title = type === 'danger' ? '⚠️ Error' : (type === 'warning' ? '⚠️ Warning' : '✅ Notice');
    toast.innerHTML = `
        <div class="toast-title">${title}</div>
        <div class="toast-message">${message}</div>
    `;
    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('removing');
        setTimeout(() => toast.remove(), 300);
    }, 3200);
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
