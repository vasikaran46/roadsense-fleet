# RoadSense Fleet — Architecture

## System Overview

```
┌─────────────────────┐     WebSocket        ┌──────────────────────────────────┐
│  Mobile Phone       │  /ws/stream/{id}     │  FastAPI Backend                 │
│  (frontend-stream)  │ ──────────────────── │                                  │
│                     │  Binary: JPEG frames  │  ┌───────────┐                  │
│  • Camera capture   │  JSON: GPS updates    │  │  Stream    │                  │
│  • GPS tracking     │                       │  │  Manager   │                  │
│  • JPEG compression │                       │  └─────┬─────┘                  │
│  • WS client        │                       │        │                        │
└─────────────────────┘                       │  ┌─────▼─────────┐              │
                                              │  │ Frame          │              │
                                              │  │ Processor      │              │
                                              │  │ (every Nth)    │              │
                                              │  └─────┬─────────┘              │
                                              │        │                        │
                                              │  ┌─────▼─────────────────────┐  │
                                              │  │  AI Detectors              │  │
                                              │  │  ├── Pothole (YOLO)       │  │
                                              │  │  ├── Road Damage (YOLO)   │  │
                                              │  │  ├── Vehicle (YOLO COCO)  │  │
                                              │  │  └── Waterlogging (OpenCV)│  │
                                              │  └─────┬─────────────────────┘  │
                                              │        │ detections             │
                                              │  ┌─────▼──────┐                 │
                                              │  │  Snapshot   │─► uploads/     │
                                              │  │  Service    │   snapshots/   │
                                              │  └─────┬──────┘                 │
                                              │        │                        │
                                              │  ┌─────▼──────┐                 │
                                              │  │  Event      │─► SQLite DB    │
                                              │  │  Service    │                │
                                              │  └─────┬──────┘                 │
                                              │        │                        │
                                              │  ┌─────▼──────┐                 │
                                              │  │  WebSocket  │                │
                                              │  │  Broadcast  │                │
                                              │  └─────┬──────┘                 │
                                              └────────┼────────────────────────┘
                                                       │
                              ┌─────────────────────────┼──────────────────┐
                              │                         │                  │
                              ▼                         ▼                  ▼
                     /ws/watch/{id}            /ws/events          REST API
                     (live video)            (event push)        /events, etc.
                              │                         │                  │
                              └──────────┬──────────────┘──────────────────┘
                                         │
                              ┌──────────▼──────────────────────┐
                              │  Admin Dashboard                 │
                              │  (frontend-admin)                │
                              │                                  │
                              │  • KPI Cards                     │
                              │  • Leaflet.js Map (Chennai)      │
                              │  • Chart.js Analytics            │
                              │  • Live Video Viewer             │
                              │  • Event Gallery                 │
                              │  • Real-time Notifications       │
                              └──────────────────────────────────┘
```

## Data Flow

1. **Frame Ingestion**: Mobile → Binary WebSocket → Backend receives JPEG bytes
2. **Relay**: Backend stores latest frame, relays to admin viewers
3. **AI Processing**: Every Nth frame → all detectors run in thread pool
4. **Snapshot**: Detection found → annotate frame → save JPEG
5. **Event**: Create DB record with GPS/timestamp → de-duplicate
6. **Push**: Broadcast event JSON to admin WebSocket subscribers
7. **Display**: Admin dashboard renders notification, updates charts/map
