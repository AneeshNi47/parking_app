from flask import Blueprint, request, jsonify, render_template_string
from datetime import datetime
import csv
import os
import threading
import time
import cv2
import numpy as np
from ultralytics import YOLO
from sort import Sort  # ensure sort.py is in your root folder
from google_sheet_handler import sync_csv_to_sheet

# Flask Blueprint
car_counter_bp = Blueprint("car_counter", __name__)

# Global States
car_counter_enabled = False
vehicle_log_memory = []   # in-memory vehicle list for UI
line_definitions = []     # user-defined direction lines
frame_lock = threading.Lock()
latest_frame = None

# YOLOv8 + SORT setup
model = YOLO("yolov8n.pt")   # Automatically downloads if not present
tracker = Sort()
track_history = {}  # {id: [(x,y), ...]}

# =============================
# Flask Routes
# =============================

@car_counter_bp.route("/car_counter")
def car_counter_dashboard():
    return render_template_string(open("templates/car_counter.html").read())


@car_counter_bp.route("/toggle_car_counter", methods=["POST"])
def toggle_car_counter():
    global car_counter_enabled
    car_counter_enabled = request.json.get("enabled", False)
    return jsonify({"enabled": car_counter_enabled})


@car_counter_bp.route("/sync_sheet", methods=["POST"])
def sync_to_sheet():
    synced = sync_csv_to_sheet("car_counter_log.csv")
    return jsonify({"success": True, "synced": synced})


@car_counter_bp.route("/set_lines", methods=["POST"])
def set_lines():
    """Receive two direction lines from frontend."""
    global line_definitions
    line_definitions = request.json.get("lines", [])
    return jsonify({"success": True})


@car_counter_bp.route("/vehicle_feed")
def vehicle_feed():
    """Return live table + count."""
    d1 = sum(1 for v in vehicle_log_memory if v[1] == "Direction 1")
    d2 = sum(1 for v in vehicle_log_memory if v[1] == "Direction 2")
    return jsonify({
        "vehicles": vehicle_log_memory[-50:],  # latest 50 entries
        "counts": {"d1": d1, "d2": d2, "total": d1 + d2}
    })


# =============================
# Helper Functions
# =============================

def log_vehicle_to_csv(track_id, direction, vehicle_type, color, speed):
    """Append a new detected vehicle to CSV + memory list."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = [track_id, direction, vehicle_type, color, speed, timestamp, "No"]
    new_file = not os.path.exists("car_counter_log.csv")

    with open("car_counter_log.csv", "a", newline="") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(["track_id", "direction", "vehicle_type", "color", "speed", "timestamp", "synced"])
        writer.writerow(row)

    vehicle_log_memory.append(row[:6])  # store recent entry


def is_car_counter_enabled():
    return car_counter_enabled


# =============================
# Detection Thread
# =============================

def start_car_counter_camera(picam2):
    """Capture loop with YOLOv8 + SORT tracking and direction detection."""
    global latest_frame
    print("🚦 Car Counter thread started...")

    while True:
        frame = picam2.capture_array()
        latest_frame = frame.copy()

        if not car_counter_enabled:
            time.sleep(0.1)
            continue

        # YOLO detection
        results = model(frame, verbose=False)[0]
        detections = []
        for r in results.boxes:
            cls = int(r.cls)
            if cls in [2, 3, 5, 7]:  # car, motorcycle, bus, truck
                x1, y1, x2, y2 = map(int, r.xyxy[0])
                conf = float(r.conf[0])
                detections.append([x1, y1, x2, y2, conf])

        # SORT tracking
        if len(detections) > 0:
            tracked = tracker.update(np.array(detections))
        else:
            tracked = []

        # Draw lines if defined
        for line in line_definitions:
            cv2.line(frame, (int(line["x1"]), int(line["y1"])),
                     (int(line["x2"]), int(line["y2"])), (255, 0, 0), 2)

        # Process each tracked vehicle
        for track in tracked:
            x1, y1, x2, y2, track_id = map(int, track)
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

            # Track position history
            if track_id not in track_history:
                track_history[track_id] = []
            track_history[track_id].append((cx, cy))

            # Check direction if enough history
            if len(track_history[track_id]) > 10 and len(line_definitions) == 2:
                y_positions = [p[1] for p in track_history[track_id][-10:]]
                direction = None
                l1_y = np.mean([line_definitions[0]["y1"], line_definitions[0]["y2"]])
                l2_y = np.mean([line_definitions[1]["y1"], line_definitions[1]["y2"]])

                if y_positions[0] < l1_y and y_positions[-1] > l2_y:
                    direction = "Direction 2"
                elif y_positions[0] > l2_y and y_positions[-1] < l1_y:
                    direction = "Direction 1"

                if direction:
                    vehicle_type = results.names[cls]
                    log_vehicle_to_csv(f"ID-{track_id}", direction, vehicle_type, "unknown", "unknown")
                    print(f"✅ Logged {track_id} → {direction}")
                    del track_history[track_id]  # prevent duplicate logging

            # Draw bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"ID:{track_id}", (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        latest_frame = frame.copy()
        time.sleep(0.1)