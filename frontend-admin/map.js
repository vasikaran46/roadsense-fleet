/**
 * RoadSense Fleet — Leaflet.js Map Integration
 * Displays detection event markers on a Chennai-centered map.
 */

let dashMap = null;
let mapMarkers = [];
let markerLayer = null;

// Chennai center coordinates
const CHENNAI_CENTER = [13.0827, 80.2707];
const MAP_ZOOM = 12;

// Detection type marker colors
const MARKER_COLORS = {
    pothole: '#ef4444',
    road_damage: '#f59e0b',
    crack: '#f59e0b',
    longitudinal_crack: '#f59e0b',
    transverse_crack: '#f59e0b',
    lateral_crack: '#f59e0b',
    alligator_crack: '#f59e0b',
    edge_crack: '#f59e0b',
    traffic_sign: '#3b82f6',
    zebra_crossing: '#8b5cf6',
    waterlogging: '#06b6d4',
    car: '#10b981',
    bus: '#10b981',
    truck: '#10b981',
};

const MARKER_ICONS = {
    pothole: '🕳️',
    road_damage: '⚠️',
    crack: '⚠️',
    longitudinal_crack: '⚡',
    transverse_crack: '⚡',
    lateral_crack: '⚡',
    alligator_crack: '🐊',
    edge_crack: '⚠️',
    traffic_sign: '🛑',
    zebra_crossing: '🚶',
    waterlogging: '🌊',
};


function initDashboardMap() {
    const mapEl = document.getElementById('dashboardMap');
    if (!mapEl || dashMap) return;

    dashMap = L.map('dashboardMap', {
        zoomControl: true,
        scrollWheelZoom: true,
    }).setView(CHENNAI_CENTER, MAP_ZOOM);

    // OpenStreetMap tile layer
    L.tileLayer(
        "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        {
            attribution: "&copy; OpenStreetMap contributors",
            maxZoom: 19
        }
    ).addTo(dashMap);

    markerLayer = L.layerGroup().addTo(dashMap);

    // Fix map rendering issues
    setTimeout(() => dashMap.invalidateSize(), 200);
}


function createCustomIcon(color, label) {
    return L.divIcon({
        className: 'custom-marker',
        html: `<div style="
            width: 28px; height: 28px;
            background: ${color};
            border: 3px solid rgba(255,255,255,0.8);
            border-radius: 50% 50% 50% 0;
            transform: rotate(-45deg);
            box-shadow: 0 2px 10px rgba(0,0,0,0.5);
            display: flex; align-items: center; justify-content: center;
        "><span style="transform: rotate(45deg); font-size: 12px;">${label}</span></div>`,
        iconSize: [28, 28],
        iconAnchor: [14, 28],
        popupAnchor: [0, -28],
    });
}


function updateMapMarkers(events) {
    if (!dashMap) initDashboardMap();
    if (!markerLayer) return;

    markerLayer.clearLayers();
    let markerCount = 0;

    events.forEach(e => {
        if (!e.latitude || !e.longitude) return;

        const color = MARKER_COLORS[e.detection_type] || '#3b82f6';
        const icon = createCustomIcon(color, MARKER_ICONS[e.detection_type] || '📋');
        const typeName = (e.detection_type || '').replace(/_/g, ' ').toUpperCase();
        const time = e.timestamp ? new Date(e.timestamp).toLocaleString('en-IN') : '';
        const confidence = (e.confidence * 100).toFixed(0);

        const snapshotHtml = e.snapshot_path
            ? `<img src="${API_BASE}/snapshots/${e.snapshot_path}" style="width:100%;max-width:200px;border-radius:6px;margin-top:8px;" onerror="this.style.display='none'">`
            : '';

        const marker = L.marker([e.latitude, e.longitude], { icon })
            .bindPopup(`
                <div style="font-family: Inter, sans-serif; min-width: 180px;">
                    <strong style="font-size:14px;">${typeName}</strong><br>
                    <span style="color:#888;">Confidence:</span> ${confidence}%<br>
                    <span style="color:#888;">Device:</span> ${e.device_id}<br>
                    <span style="color:#888;">Severity:</span> <strong>${e.severity}</strong><br>
                    <span style="color:#888;">Time:</span> ${time}<br>
                    ${snapshotHtml}
                </div>
            `, { maxWidth: 250 });

        markerLayer.addLayer(marker);
        markerCount++;
    });

    const badge = document.getElementById('mapEventCount');
    if (badge) badge.textContent = `${markerCount} markers`;
}


function addMapMarker(eventData) {
    if (!dashMap) initDashboardMap();
    if (!markerLayer || !eventData.latitude || !eventData.longitude) return;

    const color = MARKER_COLORS[eventData.detection_type] || '#3b82f6';
    const icon = createCustomIcon(color, MARKER_ICONS[eventData.detection_type] || '📋');
    const typeName = (eventData.detection_type || '').replace(/_/g, ' ').toUpperCase();

    const marker = L.marker([eventData.latitude, eventData.longitude], { icon })
        .bindPopup(`<strong>${typeName}</strong><br>${eventData.device_id}<br>${(eventData.confidence * 100).toFixed(0)}%`);

    markerLayer.addLayer(marker);
}


// Initialize map when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(initDashboardMap, 300);
});
