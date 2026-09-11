# 🛣️ RoadSense Fleet

**Intelligent Road Monitoring System for Chennai's Public Transport**

Transform mobile phone cameras on urban buses into intelligent road-monitoring sensors. The system streams live video, runs AI detection (potholes, road damage, vehicles, waterlogging), auto-captures evidence with GPS/timestamp, and displays everything in a real-time admin dashboard.

---

## 🏗️ Architecture

```
Mobile Camera → WebSocket → FastAPI Backend → YOLO AI Detection → Annotated Snapshot
                                                                    ↓
                                            SQLite Event Store ← Evidence Image + GPS
                                                   ↓
                                         Admin Dashboard (Real-time WebSocket push)
```

## ✨ Features

### Streaming Platform (Mobile)
- Live camera preview with rear-camera default
- GPS tracking via browser Geolocation API
- WebSocket video streaming with JPEG compression
- Device/Bus ID configuration
- Demo mode (load video file as camera source)
- Connection status & reconnection handling

### AI Detection
| Detector | Method | Model |
|----------|--------|-------|
| 🕳️ Pothole | YOLOv8 | `pothole_yolov8.pt` |
| ⚠️ Road Damage / Cracks | YOLOv8 (RDD) | `road_damage.pt` |
| 🚗 Vehicle / Traffic | YOLOv8n (COCO) | `yolov8n.pt` |
| 🌊 Waterlogging | OpenCV Heuristic | No model needed |

### Admin Dashboard
- KPI cards (events, potholes, damage, vehicles, devices)
- Leaflet.js map with Chennai-centered event markers
- Chart.js analytics (by type, severity)
- Real-time event notifications (WebSocket push)
- Live video monitoring (select a device, watch its stream)
- Event gallery with evidence images
- Filters: type, severity, device, status

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python, FastAPI, Uvicorn |
| AI | Ultralytics YOLO, OpenCV |
| Database | SQLite + SQLAlchemy |
| Frontend | HTML, CSS, Vanilla JavaScript |
| Maps | Leaflet.js |
| Charts | Chart.js |
| Communication | WebSockets |

---

## 📦 Installation

### 1. Clone the repository

```bash
cd "d:\SIH 2026 - Antigravity\roadsense-fleet-demo"
```

### 2. Create Python virtual environment

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
# Copy the example env (already done if .env exists)
copy ..\.env.example ..\.env
```

---

## 🤖 Model Setup

### YOLOv8n (Vehicle Detection — auto-downloads)
The vehicle detector will auto-download `yolov8n.pt` from Ultralytics on first use.

### Pothole Detection Model
Download a pretrained pothole YOLOv8 model:
- [HuggingFace: keremberke/yolov8m-pothole-segmentation](https://huggingface.co/keremberke/yolov8m-pothole-segmentation)
- [HuggingFace: peterhdd/pothole-detection-yolov8](https://huggingface.co/peterhdd/pothole-detection-yolov8)

Place the `.pt` file at: `backend/models/pothole_yolov8.pt`

### Road Damage Detection Model
Download from:
- [HuggingFace: RDD2022 models](https://huggingface.co/models?search=road+damage+detection)
- [Roboflow Universe](https://universe.roboflow.com/search?q=road+damage+detection)

Place the `.pt` file at: `backend/models/road_damage.pt`

> **Note:** The system works without pothole/road damage models — those detectors simply return empty results and the vehicle detector + waterlogging heuristic still function.

---

## 🚀 Running

### Start Backend

```bash
cd roadsense-fleet
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### Open Streaming Platform (Mobile)
Navigate to: **http://\<your-ip\>:8000/stream/**

1. Enter server URL (auto-detected)
2. Enter a Device ID (e.g., `MTC-001`)
3. Enter Device Name (e.g., `Route 21G Anna Nagar`)
4. Select camera (rear for road-facing)
5. Click **Start Streaming**

### Open Admin Dashboard
Navigate to: **http://\<your-ip\>:8000/admin/**

---

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | System health check |
| GET | `/devices` | List all devices |
| GET | `/events` | List events (with filters) |
| GET | `/events/stats` | Aggregated statistics |
| GET | `/events/{id}` | Single event detail |
| GET | `/snapshots/{filename}` | Evidence image |

### Filters for `/events`
```
?device_id=MTC-001
?detection_type=pothole
?severity=high
?status=new
```

## 🔌 WebSocket Endpoints

| Endpoint | Direction | Purpose |
|----------|-----------|---------|
| `/ws/stream/{device_id}` | Device → Backend | Send video frames + GPS |
| `/ws/watch/{device_id}` | Backend → Admin | Relay live video to admin |
| `/ws/events` | Backend → Admin | Push real-time event notifications |

---

## 🔍 How Detection Works

1. Mobile camera captures frames at ~8 FPS
2. Frames are JPEG-compressed and sent via WebSocket
3. Backend receives frames, relays to admin viewers
4. Every 5th frame (configurable) is processed by AI
5. All detectors run: pothole, road damage, vehicle, waterlogging
6. Valid detections trigger:
   - Bounding box annotation on the frame
   - JPEG snapshot saved to `backend/uploads/snapshots/`
   - Event record created in SQLite
   - Real-time push to admin dashboard via WebSocket
7. De-duplication prevents duplicate events (5s cooldown per type/device)

---

## ⚠️ Known Limitations

- **Prototype-level** — designed for hackathon demonstration
- No authentication (add for production)
- SQLite for single-server use (PostgreSQL for scale)
- Waterlogging detection is heuristic-based, not ML
- Model accuracy depends on training data quality
- GPS accuracy depends on mobile browser/device

---

## 🗺️ Future Roadmap

- Missing road divider detection
- Missing zebra crossing detection
- Missing signboard detection
- Pedestrian danger-zone alerts
- Hit-and-run ANPR (requires privacy review)
- Fleet GPS triangulation
- Multi-device mesh alerts
- Mobile app (React Native)
- Cloud deployment with PostgreSQL
