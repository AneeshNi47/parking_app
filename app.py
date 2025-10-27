from flask import Flask, render_template_string
import threading
from car_counter import car_counter_bp, start_car_counter_camera
from parking_app import parking_bp
from picamera2 import Picamera2

# ================================
# Flask App Initialization
# ================================
app = Flask(__name__)

# Register Blueprints
app.register_blueprint(car_counter_bp)
app.register_blueprint(parking_bp)


# ================================
# Routes
# ================================
@app.route("/")
def index():
    """Home screen with 2 cards: Parking App and Car Counter"""
    return render_template_string(open("templates/home.html").read())


# ================================
# Camera Setup (Shared)
# ================================
picam2 = Picamera2()
picam2.configure(picam2.create_video_configuration(main={"size": (1280, 720)}))
picam2.start()


# ================================
# Background Threads
# ================================
# 1️⃣ Start the Car Counter YOLOv8 + SORT detection thread
threading.Thread(target=start_car_counter_camera, args=(picam2,), daemon=True).start()

# 2️⃣ Start Parking App’s frame capture thread
from parking_app import capture_frames
threading.Thread(target=capture_frames, daemon=True).start()


# ================================
# Run the Flask Server
# ================================
if __name__ == "__main__":
    print("🚀 Flask Smart Camera System running...")
    print("👉 Access the dashboard at: http://<raspberry-pi-ip>:5000/")
    print("   • Parking App: http://<ip>:5000/dashboard")
    print("   • Car Counter: http://<ip>:5000/car_counter\n")
    app.run(host="0.0.0.0", port=5000)