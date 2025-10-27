from flask import Blueprint, request, jsonify, render_template_string
from picamera2 import Picamera2
import cv2
import threading
import time
import base64
import numpy as np
from utils import save_layout, load_layout, list_layouts
from car_counter import log_vehicle_to_csv, is_car_counter_enabled

parking_bp = Blueprint("parking", __name__)

picam2 = Picamera2()
picam2.configure(picam2.create_video_configuration(main={"size": (1280, 720)}))
picam2.start()

current_mode = "detection"
current_layout_name = None
saved_slots = []
latest_frame = None
frame_lock = threading.Lock()

@parking_bp.route("/dashboard")
def dashboard():
    layouts = list_layouts()
    return render_template_string(open("templates/dashboard.html").read(), mode=current_mode, layouts=layouts)

@parking_bp.route("/frame")
def frame():
    global latest_frame
    with frame_lock:
        if latest_frame is None:
            return "", 204
        _, buffer = cv2.imencode('.jpg', latest_frame)
        jpg_as_text = base64.b64encode(buffer).decode('utf-8')
        return jsonify({"frame": jpg_as_text})

@parking_bp.route("/set_mode", methods=["POST"])
def set_mode():
    global current_mode
    current_mode = request.json.get("mode", "detection")
    return jsonify({"success": True})

@parking_bp.route("/save_layout", methods=["POST"])
def save_layout_route():
    data = request.json
    name = data.get("layout_name")
    slots = data.get("slots")
    save_layout(name, slots)
    return jsonify({"success": True})

@parking_bp.route("/load_layout", methods=["POST"])
def load_layout_route():
    global saved_slots, current_layout_name
    layout_name = request.json.get("layout_name")
    saved_slots = load_layout(layout_name)
    current_layout_name = layout_name
    return jsonify({"success": True, "slots": saved_slots})

@parking_bp.route("/detect", methods=["GET"])
def detect():
    global saved_slots, latest_frame
    if not saved_slots or latest_frame is None:
        return jsonify({"slots": []})

    with frame_lock:
        gray = cv2.cvtColor(latest_frame, cv2.COLOR_BGR2GRAY)
        updated_slots = []
        used_count = 0
        vacant_count = 0

        for slot in saved_slots:
            if "points" not in slot:
                continue
            pts = np.array([[p['x'], p['y']] for p in slot["points"]], np.int32)
            mask = np.zeros(gray.shape, dtype=np.uint8)
            cv2.fillPoly(mask, [pts], 255)
            mean_val = cv2.mean(gray, mask=mask)[0]
            status = "used" if mean_val < 60 else "vacant"
            if status == "used":
                used_count += 1
            else:
                vacant_count += 1
            updated_slots.append({"points": slot["points"], "status": status})

    return jsonify({"slots": updated_slots, "summary": {"used": used_count, "vacant": vacant_count}})


# Background frame capture
def capture_frames():
    global latest_frame
    while True:
        with frame_lock:
            latest_frame = picam2.capture_array()
        time.sleep(0.1)


threading.Thread(target=capture_frames, daemon=True).start()