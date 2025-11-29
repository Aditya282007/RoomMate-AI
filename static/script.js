// Real-time status update
let updateInterval;
let camera = null;
let hands = null;
let lastGestureSent = null;
let gestureDebounce = null;

function updateStatus() {
    fetch('/api/status')
        .then(response => response.json())
        .then(data => {
            // Update connection status
            const statusDot = document.getElementById('statusDot');
            const statusText = document.getElementById('statusText');
            
            if (data.esp_connected) {
                statusDot.classList.add('connected');
                statusText.textContent = 'Connected';
            } else {
                statusDot.classList.remove('connected');
                statusText.textContent = 'Disconnected';
            }

            // Update device states
            updateDeviceStatus('light', data.light);
            updateDeviceStatus('fan', data.fan);

            // Update gas value
            const gasValue = document.getElementById('gasValue');
            const gasFill = document.getElementById('gasFill');
            gasValue.textContent = data.gas_value;
            
            // Update gas bar (scale 0-1000)
            const gasPercent = Math.min((data.gas_value / 1000) * 100, 100);
            gasFill.style.width = gasPercent + '%';

            // Change color based on gas level
            if (data.gas_value > 300) {
                gasValue.style.color = '#ff4444';
            } else if (data.gas_value > 150) {
                gasValue.style.color = '#ffaa00';
            } else {
                gasValue.style.color = '#44ff44';
            }

            // Update motion detection
            const motionValue = document.getElementById('motionValue');
            if (data.motion) {
                motionValue.textContent = 'Motion Detected';
                motionValue.style.color = '#ff4444';
            } else {
                motionValue.textContent = 'No Motion';
                motionValue.style.color = '#44ff44';
            }

            // Update gesture
            const gestureValue = document.getElementById('gestureValue');
            if (data.last_gesture) {
                gestureValue.textContent = formatGesture(data.last_gesture);
                gestureValue.style.color = '#667eea';
            } else {
                gestureValue.textContent = 'None';
                gestureValue.style.color = '#999';
            }
        })
        .catch(error => {
            console.error('Error fetching status:', error);
            const statusDot = document.getElementById('statusDot');
            const statusText = document.getElementById('statusText');
            statusDot.classList.remove('connected');
            statusText.textContent = 'Error';
        });
}

function updateDeviceStatus(device, state) {
    const statusElement = document.getElementById(device + 'Status');
    statusElement.textContent = state;
    
    if (state === 'ON') {
        statusElement.style.color = '#44ff44';
        statusElement.classList.add('on');
        statusElement.classList.remove('off');
    } else {
        statusElement.style.color = '#ff4444';
        statusElement.classList.add('off');
        statusElement.classList.remove('on');
    }
}

function formatGesture(gesture) {
    const gestureMap = {
        'fan_on': '👍 Fan ON',
        'fan_off': '🖐 Fan OFF',
        'light_on': '✌ Light ON',
        'light_off': '✊ Light OFF'
    };
    return gestureMap[gesture] || gesture;
}

// Control device
function controlDevice(device, state) {
    fetch(`/api/control/${device}/${state}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateDeviceStatus(device, state.toUpperCase());
                addLogToUI(`${device.charAt(0).toUpperCase() + device.slice(1)} turned ${state.toUpperCase()}`);
            } else {
                alert('Failed to control device: ' + (data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Error controlling device:', error);
            alert('Failed to control device. Check connection.');
        });
}

// Update event log
function updateLog() {
    fetch('/api/logs')
        .then(response => response.json())
        .then(logs => {
            const logContainer = document.getElementById('logContainer');
            
            if (logs.length === 0) {
                logContainer.innerHTML = '<p class="log-empty">No events yet...</p>';
                return;
            }

            logContainer.innerHTML = '';
            logs.forEach(log => {
                const logItem = document.createElement('div');
                logItem.className = 'log-item';
                logItem.innerHTML = `
                    <span class="log-message">${log.message}</span>
                    <span class="log-time">${log.time}</span>
                `;
                logContainer.appendChild(logItem);
            });
        })
        .catch(error => {
            console.error('Error fetching logs:', error);
        });
}

function addLogToUI(message) {
    const logContainer = document.getElementById('logContainer');
    const timestamp = new Date().toLocaleString();
    
    // Remove empty message if exists
    const emptyMsg = logContainer.querySelector('.log-empty');
    if (emptyMsg) {
        logContainer.innerHTML = '';
    }

    const logItem = document.createElement('div');
    logItem.className = 'log-item';
    logItem.innerHTML = `
        <span class="log-message">${message}</span>
        <span class="log-time">${timestamp}</span>
    `;
    logContainer.insertBefore(logItem, logContainer.firstChild);

    // Limit log items
    while (logContainer.children.length > 50) {
        logContainer.removeChild(logContainer.lastChild);
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    // Initial update
    updateStatus();
    updateLog();

    // Set up periodic updates
    updateInterval = setInterval(() => {
        updateStatus();
        updateLog();
    }, 1000); // Update every second
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (updateInterval) {
        clearInterval(updateInterval);
    }
    if (camera) {
        camera.stop();
    }
});

// ===== CAMERA GESTURE CONTROL =====

function startCamera() {
    const video = document.getElementById('webcam');
    const startBtn = document.getElementById('startCamera');
    const stopBtn = document.getElementById('stopCamera');
    
    // Request camera permission
    navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } })
        .then(stream => {
            video.srcObject = stream;
            startBtn.style.display = 'none';
            stopBtn.style.display = 'inline-block';
            
            // Initialize MediaPipe Hands
            initializeHandDetection();
            
            addLogToUI('Camera started for gesture control');
        })
        .catch(err => {
            console.error('Camera error:', err);
            alert('Could not access camera. Please check permissions.');
        });
}

function stopCamera() {
    const video = document.getElementById('webcam');
    const startBtn = document.getElementById('startCamera');
    const stopBtn = document.getElementById('stopCamera');
    
    // Stop video stream
    if (video.srcObject) {
        video.srcObject.getTracks().forEach(track => track.stop());
        video.srcObject = null;
    }
    
    // Stop MediaPipe
    if (camera) {
        camera.stop();
        camera = null;
    }
    
    startBtn.style.display = 'inline-block';
    stopBtn.style.display = 'none';
    
    document.getElementById('detectedGesture').textContent = 'Camera stopped';
    addLogToUI('Camera stopped');
}

function initializeHandDetection() {
    const video = document.getElementById('webcam');
    
    // Initialize MediaPipe Hands
    hands = new Hands({
        locateFile: (file) => {
            return `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`;
        }
    });
    
    hands.setOptions({
        maxNumHands: 1,
        modelComplexity: 1,
        minDetectionConfidence: 0.7,
        minTrackingConfidence: 0.5
    });
    
    hands.onResults(onHandResults);
    
    // Start camera
    camera = new Camera(video, {
        onFrame: async () => {
            await hands.send({ image: video });
        },
        width: 640,
        height: 480
    });
    
    camera.start();
}

function onHandResults(results) {
    if (results.multiHandLandmarks && results.multiHandLandmarks.length > 0) {
        const landmarks = results.multiHandLandmarks[0];
        const gesture = detectGestureFromLandmarks(landmarks);
        
        if (gesture) {
            document.getElementById('detectedGesture').textContent = formatGesture(gesture);
            
            // Send gesture to server with debouncing
            if (gesture !== lastGestureSent) {
                clearTimeout(gestureDebounce);
                gestureDebounce = setTimeout(() => {
                    sendGestureToServer(gesture);
                    lastGestureSent = gesture;
                }, 1000); // 1 second debounce
            }
        } else {
            document.getElementById('detectedGesture').textContent = 'No gesture detected';
        }
    } else {
        document.getElementById('detectedGesture').textContent = 'No hand detected';
    }
}

function detectGestureFromLandmarks(landmarks) {
    // Get key landmark points
    const thumbTip = landmarks[4].y;
    const thumbIp = landmarks[3].y;
    const indexTip = landmarks[8].y;
    const indexMcp = landmarks[5].y;
    const middleTip = landmarks[12].y;
    const middleMcp = landmarks[9].y;
    const ringTip = landmarks[16].y;
    const ringMcp = landmarks[13].y;
    const pinkyTip = landmarks[20].y;
    const pinkyMcp = landmarks[17].y;
    
    // Thumbs up = Fan ON
    if (thumbTip < thumbIp && indexTip > indexMcp && middleTip > middleMcp) {
        return 'fan_on';
    }
    
    // Victory = Light ON
    else if (indexTip < indexMcp && middleTip < middleMcp && ringTip > ringMcp && pinkyTip > pinkyMcp) {
        return 'light_on';
    }
    
    // Palm = Fan OFF (all fingers up)
    else if (indexTip < indexMcp && middleTip < middleMcp && ringTip < ringMcp && pinkyTip < pinkyMcp) {
        return 'fan_off';
    }
    
    // Fist = Light OFF
    else if (indexTip > indexMcp && middleTip > middleMcp && ringTip > ringMcp && pinkyTip > pinkyMcp) {
        return 'light_off';
    }
    
    return null;
}

function sendGestureToServer(gesture) {
    fetch('/api/process_gesture', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ gesture: gesture })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('Gesture processed:', data.action);
        } else {
            console.error('Gesture processing failed:', data.error);
        }
    })
    .catch(error => {
        console.error('Error sending gesture:', error);
    });
}
