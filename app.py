from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import requests
import threading
import time
from datetime import datetime
import json
import os

app = Flask(__name__)
CORS(app)

# ---- ESP32 Config ----
ESP_IP = "http://192.168.29.226"

# ---- Global State ----
system_state = {
    "light": "OFF",
    "fan": "OFF",
    "gas_value": 0,
    "motion": False,
    "last_gesture": None,
    "last_updated": None,
    "esp_connected": False
}

event_log = []
MAX_LOG_SIZE = 50

def add_log(message):
    """Add event to log with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    event_log.insert(0, {"time": timestamp, "message": message})
    if len(event_log) > MAX_LOG_SIZE:
        event_log.pop()


# ---- Behaviour learning config ----
BEHAVIOR_DATA_FILE = "behavior_data.json"

AUTO_LIGHT_ENABLED = True
AUTO_LIGHT_DAYS_WINDOW = 7
AUTO_LIGHT_TRIGGER_TOLERANCE_MIN = 5  # minutes window around learned time

# Auto-off when no motion for some time (seconds)
NO_MOTION_AUTO_OFF_SECONDS = 300  # 5 minutes

behavior_data = {
    "light_on_minutes": [],       # list of minutes-of-day (0-1439)
    "last_auto_light_date": None  # ISO date string when auto-light last triggered
}

last_motion_time = None


def load_behavior_data():
    """Load learned behaviour from disk if available"""
    global behavior_data
    if not os.path.exists(BEHAVIOR_DATA_FILE):
        return
    try:
        with open(BEHAVIOR_DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            behavior_data["light_on_minutes"] = data.get("light_on_minutes", [])
            behavior_data["last_auto_light_date"] = data.get("last_auto_light_date")
    except Exception as e:
        add_log(f"Failed to load behaviour data: {e}")


def save_behavior_data():
    """Persist learned behaviour to disk"""
    try:
        with open(BEHAVIOR_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(behavior_data, f)
    except Exception as e:
        add_log(f"Failed to save behaviour data: {e}")


def minute_of_day(dt: datetime) -> int:
    return dt.hour * 60 + dt.minute


def record_light_on_event(now: datetime):
    """Record a manual light-ON event for behaviour learning"""
    minutes = minute_of_day(now)
    behavior_data["light_on_minutes"].append(minutes)
    # keep only last AUTO_LIGHT_DAYS_WINDOW events
    if len(behavior_data["light_on_minutes"]) > AUTO_LIGHT_DAYS_WINDOW:
        behavior_data["light_on_minutes"] = behavior_data["light_on_minutes"][-AUTO_LIGHT_DAYS_WINDOW:]
    save_behavior_data()


def get_learned_light_on_minute():
    """Return the learned minute-of-day when the user usually turns the light ON"""
    data = behavior_data.get("light_on_minutes") or []
    if not data:
        return None
    return int(sum(data) / len(data))  # simple average


def maybe_auto_light_on(now_dt: datetime):
    """Automatically turn light ON around the learned time"""
    if not AUTO_LIGHT_ENABLED:
        return
    if not system_state["esp_connected"]:
        return
    if system_state["light"] == "ON":
        return

    learned_minute = get_learned_light_on_minute()
    if learned_minute is None:
        return

    now_min = minute_of_day(now_dt)
    if abs(now_min - learned_minute) > AUTO_LIGHT_TRIGGER_TOLERANCE_MIN:
        return

    today_str = now_dt.date().isoformat()
    if behavior_data.get("last_auto_light_date") == today_str:
        return

    try:
        res = requests.get(f"{ESP_IP}/light/on", timeout=2)
        if res.status_code == 200:
            system_state["light"] = "ON"
            behavior_data["last_auto_light_date"] = today_str
            save_behavior_data()
            add_log("Auto-light: turned ON based on learned behaviour")
    except requests.exceptions.RequestException as e:
        add_log(f"Auto-light ON failed: {e}")


def maybe_auto_light_off(now_ts: float):
    """Turn light OFF if there has been no motion for a while"""
    global last_motion_time
    if NO_MOTION_AUTO_OFF_SECONDS <= 0:
        return
    if last_motion_time is None:
        return
    if not system_state["esp_connected"]:
        return
    if system_state["light"] != "ON":
        return
    if system_state["motion"]:
        return
    if now_ts - last_motion_time < NO_MOTION_AUTO_OFF_SECONDS:
        return

    try:
        res = requests.get(f"{ESP_IP}/light/off", timeout=2)
        if res.status_code == 200:
            system_state["light"] = "OFF"
            add_log("Auto-light: turned OFF due to no motion")
    except requests.exceptions.RequestException as e:
        add_log(f"Auto-light OFF failed: {e}")

def poll_esp32():
    """Background thread to poll ESP32 status and drive automations"""
    global last_motion_time
    while True:
        now_ts = time.time()
        now_dt = datetime.now()
        try:
            res = requests.get(f"{ESP_IP}/status", timeout=2)
            if res.status_code == 200:
                status = res.text
                if not system_state["esp_connected"]:
                    add_log("ESP32 connected successfully.")
                system_state["esp_connected"] = True
                
                # Parse status: "Gas:123|Motion:Detected|Light:ON|Fan:OFF"
                if "Gas:" in status:
                    parts = status.split("|")
                    for part in parts:
                        if "Gas:" in part:
                            system_state["gas_value"] = int(part.split(":")[1])
                        elif "Motion:" in part:
                            system_state["motion"] = "Detected" in part
                        elif "Light:" in part:
                            system_state["light"] = part.split(":")[1]
                        elif "Fan:" in part:
                            system_state["fan"] = part.split(":")[1]

                # Track last time motion was detected
                if system_state["motion"]:
                    last_motion_time = now_ts
                
                system_state["last_updated"] = now_dt.isoformat()

                # Run behaviour-based automations
                maybe_auto_light_on(now_dt)
                maybe_auto_light_off(now_ts)
            else:
                if system_state["esp_connected"]:
                    add_log(f"ESP32 returned non-200 status: {res.status_code}")
                system_state["esp_connected"] = False
        except requests.exceptions.RequestException as e:
            if system_state["esp_connected"]:
                add_log(f"ESP32 connection lost: {e}")
            system_state["esp_connected"] = False
        except Exception as e:
            add_log(f"An unexpected error occurred in poll_esp32: {e}")
            system_state["esp_connected"] = False
        
        time.sleep(1)

# Start background polling
load_behavior_data()
threading.Thread(target=poll_esp32, daemon=True).start()

# ---- Routes ----

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    """Get current system status"""
    return jsonify(system_state)

@app.route('/api/control/<device>/<state>')
def control_device(device, state):
    """Control light or fan"""
    if device not in ['light', 'fan'] or state not in ['on', 'off']:
        return jsonify({"success": False, "error": "Invalid parameters"}), 400
    
    if not system_state["esp_connected"]:
        return jsonify({"success": False, "error": "ESP32 is not connected"}), 503
    
    try:
        url = f"{ESP_IP}/{device}/{state}"
        res = requests.get(url, timeout=2)
        
        if res.status_code == 200:
            system_state[device] = state.upper()
            # Record behaviour only for light turning ON
            if device == 'light' and state == 'on':
                record_light_on_event(datetime.now())
            add_log(f"{device.capitalize()} turned {state.upper()}")
            return jsonify({"success": True, "device": device, "state": state})
        else:
            add_log(f"Failed to control {device}: ESP32 returned status {res.status_code}")
            return jsonify({"success": False, "error": f"ESP32 request failed with status {res.status_code}"}), 500
    except requests.exceptions.RequestException as e:
        add_log(f"Failed to control {device}: {e}")
        return jsonify({"success": False, "error": f"Failed to communicate with ESP32: {e}"}), 500

@app.route('/api/logs')
def get_logs():
    """Get event logs"""
    return jsonify(event_log)

@app.route('/api/gesture', methods=['POST'])
def update_gesture():
    """Update last detected gesture from Python script"""
    data = request.json
    if data and 'gesture' in data:
        system_state['last_gesture'] = data['gesture']
        add_log(f"Gesture detected: {data['gesture']}")
        return jsonify({"success": True})
    return jsonify({"success": False}), 400

@app.route('/api/process_gesture', methods=['POST'])
def process_gesture():
    """Process gesture detected from web camera and control devices"""
    data = request.json
    if not data or 'gesture' not in data:
        return jsonify({"success": False, "error": "No gesture provided"}), 400
    
    gesture = data['gesture']
    system_state['last_gesture'] = gesture
    
    try:
        # Map gesture to device control
        if gesture == 'fan_on':
            url = f"{ESP_IP}/fan/on"
            res = requests.get(url, timeout=2)
            if res.status_code == 200:
                system_state['fan'] = 'ON'
                add_log("🖐 Gesture: Fan turned ON")
                return jsonify({"success": True, "action": "Fan ON"})
        
        elif gesture == 'light_on':
            url = f"{ESP_IP}/light/on"
            res = requests.get(url, timeout=2)
            if res.status_code == 200:
                system_state['light'] = 'ON'
                record_light_on_event(datetime.now())
                add_log("🖐 Gesture: Light turned ON")
                return jsonify({"success": True, "action": "Light ON"})
        
        elif gesture == 'fan_off':
            url = f"{ESP_IP}/fan/off"
            res = requests.get(url, timeout=2)
            if res.status_code == 200:
                system_state['fan'] = 'OFF'
                add_log("🖐 Gesture: Fan turned OFF")
                return jsonify({"success": True, "action": "Fan OFF"})
        
        elif gesture == 'light_off':
            url = f"{ESP_IP}/light/off"
            res = requests.get(url, timeout=2)
            if res.status_code == 200:
                system_state['light'] = 'OFF'
                add_log("🖐 Gesture: Light turned OFF")
                return jsonify({"success": True, "action": "Light OFF"})
        
        return jsonify({"success": False, "error": "Unknown gesture"}), 400
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    add_log("RoomMate.AI Web Server Started")
    app.run(host='0.0.0.0', port=5000, debug=True)
