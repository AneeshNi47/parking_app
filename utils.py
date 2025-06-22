import os
import json

LAYOUT_DIR = "layouts"

def save_layout(name, slots):
    if not os.path.exists(LAYOUT_DIR):
        os.makedirs(LAYOUT_DIR)
    with open(os.path.join(LAYOUT_DIR, f"{name}.json"), "w") as f:
        json.dump({"layout_name": name, "slots": slots}, f)

def load_layout(name):
    try:
        with open(os.path.join(LAYOUT_DIR, f"{name}.json"), "r") as f:
            data = json.load(f)
            return data.get("slots", [])
    except FileNotFoundError:
        return []

def list_layouts():
    if not os.path.exists(LAYOUT_DIR):
        return []
    return [f.replace(".json", "") for f in os.listdir(LAYOUT_DIR) if f.endswith(".json")]

def update_slot_status(slots, frame_gray, threshold=30):
    new_status = []
    for slot in slots:
        roi = frame_gray[slot["y1"]:slot["y2"], slot["x1"]:slot["x2"]]
        mean_val = roi.mean()
        status = "used" if mean_val < threshold else "vacant"
        slot["status"] = status
        new_status.append(slot)
    return new_status
