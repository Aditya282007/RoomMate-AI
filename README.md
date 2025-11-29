# 🏠 RoomMate.AI - Smart Home Gesture Control System

A comprehensive smart home automation system that uses hand gesture recognition to control home appliances like lights and fans. The system includes real-time monitoring of gas levels and motion detection with an intuitive web dashboard.

## 🎯 Features

- **Gesture Control**: Control devices using hand gestures detected via webcam
  - 👍 Thumbs Up → Fan ON
  - ✌ Victory Sign → Light ON
  - 🖐 Palm Open → Fan OFF
  - ✊ Fist → Light OFF

- **Real-time Monitoring**:
  - Gas level detection with email alerts
  - Motion detection for automatic lighting
  - Live device status updates

- **Web Dashboard**:
  - Modern, responsive UI
  - Manual device control
  - **Browser-based gesture control** (use any device's camera!)
  - Real-time sensor readings
  - Event logging
  - ESP32 connection status

## 📋 Prerequisites

- Python 3.8 or higher
- Webcam
- ESP32 with configured devices (Light, Fan, Gas sensor, Motion sensor)
- Internet connection for email alerts

## 🚀 Installation

1. **Clone or navigate to the project directory**:
   ```bash
   cd "C:\Users\Aditya\Documents\Final year"
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure ESP32 IP**:
   - Update the `ESP_IP` variable in both `gesture.py` and `app.py` with your ESP32's IP address
   - Default: `http://192.168.29.226`

4. **Configure Email Alerts** (in `gesture.py`):
   - Set `EMAIL_SENDER` to your Gmail address
   - Set `EMAIL_PASSWORD` to your app-specific password
   - Set `EMAIL_RECEIVER` to the recipient email

## 🎮 Usage

### Running the Web Dashboard

1. **Start the Flask web server**:
   ```bash
   python app.py
   ```

2. **Access the dashboard**:
   - Open your browser and go to: `http://localhost:5000`
   - Or from another device on the same network: `http://YOUR_IP:5000`

### Running Gesture Control

1. **Start the gesture recognition system**:
   ```bash
   python gesture.py
   ```

2. **Perform gestures** in front of your webcam to control devices

3. **Press ESC** to exit the application

### Running Both Together

For full functionality, run both the web server and gesture control:

**Terminal 1:**
```bash
python app.py
```

**Terminal 2:**
```bash
python gesture.py
```

### Using Camera Gesture Control (Browser-Based)

1. **Access the web dashboard** (the Flask server must be running)
2. **Scroll to the "Camera Gesture Control" section**
3. **Click "Start Camera"** and allow camera permissions
4. **Perform gestures** in front of your device's camera:
   - 👍 Thumbs Up → Fan ON
   - ✌ Victory Sign → Light ON
   - 🖐 Palm Open → Fan OFF
   - ✊ Fist → Light OFF
5. The system will automatically detect and execute gestures
6. Works on **any device** with a camera (phone, tablet, laptop)!

**Note**: Camera gesture control works entirely in the browser using MediaPipe.js - no Python gesture script needed!

## 📱 Web Dashboard Features

- **Device Controls**: Manual ON/OFF buttons for Light and Fan
- **Camera Gesture Control**: 
  - Use your device's camera (phone, tablet, laptop) directly in the browser
  - Real-time hand gesture recognition using MediaPipe
  - Works on any device with a camera - no Python installation needed!
  - Click "Start Camera" and perform gestures to control devices
- **Sensor Readings**: Real-time display of:
  - Gas levels with visual indicator
  - Motion detection status
  - Last detected gesture
- **Event Log**: Chronological list of system events
- **Connection Status**: ESP32 connectivity indicator

## 🔧 ESP32 API Endpoints

The system expects the following endpoints from your ESP32:

- `GET /status` - Returns: `Gas:XXX|Motion:Detected|Light:ON|Fan:OFF`
- `GET /light/on` - Turn light ON
- `GET /light/off` - Turn light OFF
- `GET /fan/on` - Turn fan ON
- `GET /fan/off` - Turn fan OFF

## 🛡️ Safety Features

- **Gas Leak Detection**: Automatic email alerts when gas level exceeds 300
- **Alert Throttling**: Prevents spam by limiting alerts to once every 30 seconds
- **Voice Alerts**: Audio notifications for critical events (if available)
- **Automatic Lighting**: Motion-triggered light control

## 📁 Project Structure

```
Final year/
├── gesture.py           # Gesture recognition & control logic
├── app.py              # Flask web server
├── requirements.txt    # Python dependencies
├── README.md          # Documentation
├── templates/
│   └── index.html     # Web dashboard HTML
└── static/
    ├── style.css      # Dashboard styling
    └── script.js      # Frontend JavaScript
```

## 🐛 Troubleshooting

**Web dashboard not loading:**
- Ensure Flask is running without errors
- Check firewall settings
- Verify the port 5000 is not in use

**Gesture recognition not working:**
- Check webcam permissions
- Ensure proper lighting conditions
- Verify MediaPipe installation

**ESP32 connection issues:**
- Verify ESP32 is powered and connected to WiFi
- Check if the IP address is correct
- Test endpoints using a browser or curl

**Email alerts not sending:**
- Enable "Less secure app access" or use App Password for Gmail
- Check internet connection
- Verify email credentials

## 🎨 Customization

### Changing Gesture Mappings
Edit the `detect_gesture()` function in `gesture.py`

### Adjusting Gas Alert Threshold
Modify the condition in `gesture.py`:
```python
if gas_value > 300:  # Change 300 to your desired threshold
```

### Modifying UI Colors
Edit `static/style.css` to change the color scheme

## 📄 License

This project is for educational purposes as part of a final year project.

## 👨‍💻 Author

Aditya Chavda

---

**Note**: Make sure your ESP32 firmware is properly configured to respond to the expected API endpoints before running the system.
