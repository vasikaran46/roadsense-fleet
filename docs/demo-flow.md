# 🎬 RoadSense Fleet — Demo Flow

Step-by-step guide for demonstrating the RoadSense Fleet system.

---

## Prerequisites

1. Backend running on laptop: `python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000`
2. Both laptop and mobile phone on the **same WiFi network**
3. Know your laptop's local IP (e.g., `192.168.1.100`)

---

## Demo Script

### Step 1 — Start the Backend
```bash
cd roadsense-fleet-demo
backend\venv\Scripts\activate
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
You should see: `RoadSense Fleet — Starting Up` in the terminal.

### Step 2 — Open Admin Dashboard
On your laptop browser, go to:
```
http://localhost:8000/admin/
```
You'll see the dashboard with empty KPI cards and a Chennai-centered map.

### Step 3 — Open Streaming App on Mobile
On your mobile phone browser, go to:
```
http://<laptop-ip>:8000/stream/
```
For example: `http://192.168.1.100:8000/stream/`

### Step 4 — Configure the Device
- **Server URL**: `ws://<laptop-ip>:8000` (should auto-detect)
- **Device ID**: `MTC-001`
- **Device Name**: `Route 21G Anna Nagar`
- **Camera**: Rear Camera (Road-facing)

### Step 5 — Start Streaming
- Tap **Start Streaming**
- Allow camera and GPS permissions when prompted
- You should see:
  - ✅ Camera preview
  - ✅ GPS coordinates
  - ✅ "Connected" status
  - ✅ Frame counter increasing

### Step 6 — Check Admin Dashboard
Go back to the admin dashboard:
- **Dashboard**: `MTC-001` should show as online in the device count
- **Live Monitoring**: Click to see the live page
  - Select `MTC-001` from the device list
  - You should see the live video stream from the mobile phone

### Step 7 — Trigger Detection
- Point the mobile phone camera at a road with potholes/damage
- Or use **Demo Mode**: check "Demo Mode" in the streaming app and load a dashcam video file showing road issues
- The AI will detect potholes/road damage and automatically:
  - Draw bounding boxes
  - Capture evidence snapshots
  - Create events in the database
  - Push notifications to the admin dashboard

### Step 8 — View Results
On the admin dashboard:
- **Dashboard**: KPI cards update, recent events appear, map markers show
- **Live Monitoring**: Detection notifications appear below the video
- **Events**: Browse all detected events with evidence images

---

## Demo Tips

1. **For best pothole detection**: Use a dashcam video of Indian roads with visible potholes
2. **Vehicle detection works immediately** with the COCO model (auto-downloads)
3. **Multiple devices**: Open the streaming page on multiple phones with different Device IDs
4. **Show the map**: Events with GPS coordinates appear as colored markers on the Chennai map
5. **Show evidence**: Click any event to see the annotated snapshot with bounding boxes

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Camera not working | Check browser permissions, try Chrome |
| GPS shows "unavailable" | Enable location services, may need HTTPS for some browsers |
| WebSocket won't connect | Check both devices are on same network, check firewall |
| No detections | Ensure model files are in `backend/models/`, check backend logs |
| Stream is slow | Reduce JPEG_QUALITY in .env, check WiFi bandwidth |
