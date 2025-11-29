# 🚀 Quick Start Guide - RoomMate.AI Web App

## Option 1: Web Dashboard Only (Recommended for Remote Control)

### Step 1: Install Dependencies
```bash
pip install flask flask-cors requests
```

### Step 2: Start the Web Server
```bash
python app.py
```

### Step 3: Access from Any Device
- **On the same computer**: Open browser → `http://localhost:5000`
- **From phone/tablet**: Open browser → `http://YOUR_COMPUTER_IP:5000`
  - Find your IP: `ipconfig` (Windows) or `ifconfig` (Mac/Linux)

### Step 4: Control Your Devices

#### Manual Control:
- Click ON/OFF buttons for Light and Fan

#### Camera Gesture Control (Works on ANY device!):
1. Click **"Start Camera"** button
2. Allow camera permissions when prompted
3. Show your hand to the camera and perform gestures:
   - 👍 **Thumbs Up** → Fan ON
   - ✌ **Victory** → Light ON  
   - 🖐 **Palm Open** → Fan OFF
   - ✊ **Fist** → Light OFF

**✨ Pro Tip**: Use your phone's camera while lying in bed to control devices!

---

## Option 2: Full System (Desktop Gesture + Web)

### Terminal 1 - Web Server:
```bash
python app.py
```

### Terminal 2 - Desktop Gesture Recognition:
```bash
python gesture.py
```

This runs gesture detection on your desktop webcam AND provides the web interface.

---

## 📱 Mobile Usage

1. Make sure your phone is on the **same WiFi** as your computer
2. On your computer, find your IP address:
   ```bash
   ipconfig
   ```
   Look for "IPv4 Address" (e.g., 192.168.1.100)

3. On your phone's browser, go to:
   ```
   http://192.168.1.100:5000
   ```
   (Replace with your actual IP)

4. Tap "Start Camera" and use hand gestures!

---

## 🔧 Troubleshooting

**Camera not working?**
- Allow camera permissions in your browser
- Use HTTPS or localhost (browsers require secure context)
- Try Chrome/Edge (better WebRTC support)

**Can't access from phone?**
- Check firewall settings
- Ensure both devices are on the same network
- Verify the IP address is correct

**ESP32 not responding?**
- Check ESP32 is powered on
- Verify WiFi connection
- Update ESP_IP in `app.py` if IP changed

---

## 🎯 Features Summary

✅ Manual ON/OFF control  
✅ Browser-based gesture control  
✅ Real-time sensor monitoring  
✅ Gas leak alerts  
✅ Motion detection  
✅ Event logging  
✅ Multi-device access  
✅ Mobile-friendly interface  

---

Enjoy your smart home! 🏠✨
