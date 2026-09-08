/**
 * RoadSense Fleet — Chart.js Analytics
 * Renders dashboard charts for detection analytics.
 */

let chartByType = null;
let chartBySeverity = null;

// Color palette matching the dashboard theme
const CHART_COLORS = {
    pothole: '#ef4444',
    road_damage: '#f59e0b',
    crack: '#fb923c',
    longitudinal_crack: '#f97316',
    transverse_crack: '#ea580c',
    alligator_crack: '#c2410c',
    edge_crack: '#f97316',
    lateral_crack: '#ea580c',
    traffic_sign: '#3b82f6',
    zebra_crossing: '#a855f7',
    waterlogging: '#06b6d4',
    car: '#10b981',
    bus: '#34d399',
    truck: '#059669',
    motorcycle: '#6ee7b7',
    person: '#8b5cf6',
};

const SEVERITY_COLORS = {
    high: '#ef4444',
    medium: '#f59e0b',
    low: '#3b82f6',
};

// Chart.js global defaults for dark theme
Chart.defaults.color = '#8899b0';
Chart.defaults.borderColor = 'rgba(255,255,255,0.06)';
Chart.defaults.font.family = "'Inter', sans-serif";


function initCharts() {
    // Detection by Type — Doughnut
    const typeCtx = document.getElementById('chartByType');
    if (typeCtx && !chartByType) {
        chartByType = new Chart(typeCtx, {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [],
                    borderWidth: 0,
                    hoverOffset: 8,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '65%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 16,
                            usePointStyle: true,
                            pointStyleWidth: 10,
                            font: { size: 12 },
                        },
                    },
                },
            },
        });
    }

    // Severity Distribution — Bar
    const sevCtx = document.getElementById('chartBySeverity');
    if (sevCtx && !chartBySeverity) {
        chartBySeverity = new Chart(sevCtx, {
            type: 'bar',
            data: {
                labels: ['High', 'Medium', 'Low'],
                datasets: [{
                    label: 'Events',
                    data: [0, 0, 0],
                    backgroundColor: [
                        SEVERITY_COLORS.high,
                        SEVERITY_COLORS.medium,
                        SEVERITY_COLORS.low,
                    ],
                    borderRadius: 6,
                    borderSkipped: false,
                    maxBarThickness: 50,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { stepSize: 1, font: { size: 12 } },
                        grid: { color: 'rgba(255,255,255,0.04)' },
                    },
                    x: {
                        grid: { display: false },
                        ticks: { font: { size: 12 } },
                    },
                },
            },
        });
    }
}


function updateCharts(statsData) {
    initCharts();

    // Update type chart
    if (chartByType && statsData.by_type) {
        const entries = Object.entries(statsData.by_type).filter(([k, v]) => v > 0);
        const labels = entries.map(([k]) => k.replace(/_/g, ' ').toUpperCase());
        const values = entries.map(([, v]) => v);
        const colors = entries.map(([k]) => CHART_COLORS[k] || '#6b7280');

        chartByType.data.labels = labels;
        chartByType.data.datasets[0].data = values;
        chartByType.data.datasets[0].backgroundColor = colors;
        chartByType.update('none');
    }

    // Update severity chart
    if (chartBySeverity && statsData.by_severity) {
        chartBySeverity.data.datasets[0].data = [
            statsData.by_severity.high || 0,
            statsData.by_severity.medium || 0,
            statsData.by_severity.low || 0,
        ];
        chartBySeverity.update('none');
    }
}


document.addEventListener('DOMContentLoaded', () => {
    setTimeout(initCharts, 500);
});
