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

def update_slot_status(slots, frame_gray, threshold=120):
    new_status = []
    for slot in slots:
        pts = slot.get("points", [])
        if not pts or len(pts) < 3:
            continue  # Skip invalid polygon

        # Convert list of points to integer coordinates
        polygon = np.array([[p['x'], p['y']] for p in pts], np.int32)
        polygon = polygon.reshape((-1, 1, 2))

        # Create a mask for the polygon
        mask = np.zeros(frame_gray.shape, dtype=np.uint8)
        cv2.fillPoly(mask, [polygon], 255)

        # Apply mask to gray image
        roi = cv2.bitwise_and(frame_gray, frame_gray, mask=mask)
        mean_val = cv2.mean(roi, mask=mask)[0]

        status = "used" if mean_val < threshold else "vacant"
        slot["status"] = status
        new_status.append(slot)
    return new_status
