import cv2
import mediapipe as mp
import requests
import smtplib
from email.mime.text import MIMEText
import time
import datetime
import pyttsx3
import threading
import queue
import os

# ---- ESP32 Config (Fixed IP) ----
ESP_IP = "http://192.168.29.226"  # Your ESP32 IP

# ---- Email Alert Config ----
# IMPORTANT: Do NOT hardcode real passwords in this file.
# Configure these via environment variables before running:
#   EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECEIVER
EMAIL_SENDER = os.getenv("EMAIL_SENDER", "your_email@example.com")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER", "receiver@example.com")

# ---- Voice engine setup ----
try:
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)
    engine.setProperty('volume', 0.8)
    VOICE_AVAILABLE = True
except:
    print("⚠ Voice engine failed. Voice alerts disabled.")
    VOICE_AVAILABLE = False

voice_queue = queue.Queue()

def voice_worker():
    while True:
        msg = voice_queue.get()
        if msg is None:
            break
        if VOICE_AVAILABLE:
            engine.say(msg)
            engine.runAndWait()
        voice_queue.task_done()

if VOICE_AVAILABLE:
    threading.Thread(target=voice_worker, daemon=True).start()

def voice_alert(msg):
    if VOICE_AVAILABLE:
        voice_queue.put(msg)

def log_event(msg):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"{timestamp} - {msg}")

# ---- ESP32 Controller ----
class ESP32Controller:
    def control_device(self, device, state):
        url = f"{ESP_IP}/{device}/{state}"
        try:
            res = requests.get(url, timeout=2)
            if res.status_code == 200:
                log_event(f"✅ {device.upper()} {state.upper()}")
                return True
        except:
            log_event(f"⚠ Could not connect to ESP32 for {device}")
        return False

    def get_status(self):
        try:
            res = requests.get(f"{ESP_IP}/status", timeout=2)
            if res.status_code == 200:
                return res.text
        except:
            log_event(".")
        return None

esp_controller = ESP32Controller()

# ---- Email Alert ----
def send_email_alert(gas_value):
    if not EMAIL_PASSWORD:
        log_event("❌ EMAIL_PASSWORD not set; skipping email alert")
        return

    subject = "⚠ Gas Leak Alert - RoomMate AI"
    body = f"Gas leak detected!\n\nGas Sensor Value: {gas_value}\nTime: {datetime.datetime.now()}\n"
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        server.quit()
        log_event("✅ Email alert sent")
        voice_alert("Warning! Gas leak detected. Email alert sent.")
    except Exception as e:
        log_event(f"❌ Email failed: {e}")

# ---- Mediapipe Setup ----
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.7)

# ---- Gesture Detection ----

def detect_gesture(landmarks):
    thumb_tip = landmarks[4].y
    thumb_ip  = landmarks[3].y
    index_tip = landmarks[8].y
    index_mcp = landmarks[5].y
    middle_tip = landmarks[12].y
    middle_mcp = landmarks[9].y
    ring_tip = landmarks[16].y
    ring_mcp = landmarks[13].y
    pinky_tip = landmarks[20].y
    pinky_mcp = landmarks[17].y

    # 👍 Thumbs up = Fan ON
    if thumb_tip < thumb_ip and index_tip > index_mcp and middle_tip > middle_mcp:
        return "fan_on"

    # ✌ Victory = Light ON
    elif index_tip < index_mcp and middle_tip < middle_mcp and ring_tip > ring_mcp and pinky_tip > pinky_mcp:
        return "light_on"

    # 🖐 Palm = Fan OFF (all fingers up)
    elif index_tip < index_mcp and middle_tip < middle_mcp and ring_tip < ring_mcp and pinky_tip < pinky_mcp:
        return "fan_off"

    # ✊ Fist = Light OFF
    elif index_tip > index_mcp and middle_tip > middle_mcp and ring_tip > ring_mcp and pinky_tip > pinky_mcp:
        return "light_off"

    return None

def main():
    cap = cv2.VideoCapture(0)
    last_alert_time = 0
    light_on_by_motion = False
    last_gesture = None
    light_state = "OFF"
    fan_state = "OFF"
    gas_value = 0
    motion = False

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = hands.process(img_rgb)

        # ---- Gesture Control ----
        if result.multi_hand_landmarks:
            for hand_landmarks in result.multi_hand_landmarks:
                mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                gesture = detect_gesture(hand_landmarks.landmark)

                if gesture and gesture != last_gesture:
                    if gesture == "light_on":
                        if esp_controller.control_device("light", "on"):
                            light_state = "ON"
                    elif gesture == "light_off":
                        if esp_controller.control_device("light", "off"):
                            light_state = "OFF"
                        light_on_by_motion = False
                    elif gesture == "fan_on":
                        if esp_controller.control_device("fan", "on"):
                            fan_state = "ON"
                    elif gesture == "fan_off":
                        if esp_controller.control_device("fan", "off"):
                            fan_state = "OFF"

                    log_event(f"🖐 Gesture detected: {gesture}")
                    last_gesture = gesture

        # ---- ESP32 Status ----
        status = esp_controller.get_status()
        if status and "Gas:" in status:
            try:
                gas_value = int(status.split("|")[0].split(":")[1])
                motion = "Detected" in status

                # Gas alert
                if gas_value > 300 and time.time() - last_alert_time > 30:
                    send_email_alert(gas_value)
                    last_alert_time = time.time()

                # Motion control for light
                if motion:
                    if not light_on_by_motion:
                        if esp_controller.control_device("light", "on"):
                            light_on_by_motion = True
                            light_state = "ON"
                else:
                    if light_on_by_motion and time.time() - last_alert_time > 60:
                        if esp_controller.control_device("light", "off"):
                            light_on_by_motion = False
                            light_state = "OFF"

            except Exception as e:
                log_event(f"Status parse error: {e}")

        # ---- Debug Overlay ----
        cv2.putText(frame, f"Gesture: {last_gesture}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,255), 2)
        cv2.putText(frame, f"Light: {light_state}", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
        cv2.putText(frame, f"Fan: {fan_state}", (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,0,0), 2)
        cv2.putText(frame, f"Gas: {gas_value}", (20, 160), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
        cv2.putText(frame, f"Motion: {'Yes' if motion else 'No'}", (20, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (255,255,255), 2)

        cv2.imshow("RoomMate.AI Debug", frame)
        if cv2.waitKey(1) & 0xFF == 27:  # ESC to quit
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()