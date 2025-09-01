// This section should be uncommented and configured if you are using MediaPipe libraries
// for Gesture Recognition. Ensure you have the MediaPipe Tasks Vision library accessible.
import {
    GestureRecognizer,
    FilesetResolver,
    DrawingUtils
} from "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.3";

// Face-API.js is now loaded globally via CDN in mark_attendance.html
// Accessing it via window.faceapi to ensure it's defined within the module scope.

const demosSection = document.getElementById("demos");
const loadingDiv = document.getElementById("loading");
let gestureRecognizer; // Variable to hold the gesture recognizer instance
let runningMode = "VIDEO"; // Set to VIDEO mode for live stream
let webcamRunning = false;
const videoHeight = "480px"; // These are hints, canvas will adapt to video dimensions
const videoWidth = "640px"; // These are hints, canvas will adapt to video dimensions

// Correctly identify elements from mark_attendance.html
const video = document.getElementById("webcam");
const canvasElement = document.getElementById("output_canvas");
const canvasCtx = canvasElement.getContext("2d");
const gestureOutput = document.getElementById("gesture_output"); // Used for console debugging, hidden from UI
const statusMessage = document.getElementById("status_message"); // Main status message area
const employeeIdDisplay = document.getElementById('employeeIdDisplay'); // Display for recognized employee ID
const recentRecordsScrollContainer = document.getElementById('recentRecordsScrollContainer'); // Container for recent records
const noRecentRecordsMessage = document.getElementById('noRecentRecordsMessage'); // Message for no recent records
const currentDateTimeElement = document.getElementById('currentDateTime'); // Element for current date/time in header
const cameraButton = document.getElementById('cameraButton'); // New camera button

// Global variables for Face-API.js and emotion
let currentEmotion = null; // Stores the detected emotion, for backend only

// --- State Management ---
// Define possible states for the attendance system
const SYSTEM_STATE = {
    INITIAL: 'INITIAL', // Initial state, waiting for models/webcam
    FACE_RECOGNIZING: 'FACE_RECOGNIZING', // Actively trying to recognize a face
    MULTIPLE_FACES_DETECTED: 'MULTIPLE_FACES_DETECTED', // New state for multiple faces
    FACE_RECOGNIZED_PROMPT_GESTURE: 'FACE_RECOGNIZED_PROMPT_GESTURE', // Face recognized, waiting for gesture
    ATTENDANCE_PROCESSING: 'ATTENDANCE_PROCESSING' // Marking attendance, waiting for backend response
};
let currentSystemState = SYSTEM_STATE.INITIAL;
let recognizedEmployeeName = null; // Stores the name of the last recognized
let recognizedPopupShown = false;
let lastFaceRecognitionTime = 0; // Timestamp for last face recognition attempt (for cooldown)
const FACE_RECOGNITION_COOLDOWN_SECONDS = 5; // Cooldown period for initiating face recognition

// Define the gestures that trigger attendance marking and breaks
const ATTENDANCE_TRIGGER_GESTURE = "Thumb_Up";
const BREAK_TRIGGER_GESTURE = "Fist";
let lastAttendanceMarkedTime = 0; // Timestamp for the last successful attendance mark (for cooldown)
const ATTENDANCE_COOLDOWN_SECONDS = 10; // Cooldown period after marking attendance for the same person

let isScanningAllowed = false;
let noFaceDetectedAttempts = 0;

let lastSpeechPromptTime = 0;
const SPEECH_PROMPT_INTERVAL_SECONDS = 60;

function setSystemState(newState) {
    if (currentSystemState !== newState) {
        console.log(`➡️ SYSTEM STATE CHANGE: ${currentSystemState} -> ${newState}`);
        currentSystemState = newState;
    }
}


function speak(text) {
    console.log(`🗣️ Speech requested: "${text}"`);
    return new Promise(resolve => {
        if ('speechSynthesis' in window) {
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.onend = () => {
                console.log("🗣️ Speech finished.");
                resolve();
            };
            utterance.onerror = (event) => {
                console.error("❌ Speech synthesis error:", event);
                resolve();
            };
            speechSynthesis.speak(utterance);
        } else {
            console.warn("Speech synthesis not supported in this browser.");
            resolve();
        }
    });
}

function updateStatusMessage(type, message = "No message provided.") {
    if (statusMessage) {
        statusMessage.textContent = message;
        statusMessage.classList.remove('status-info', 'status-success', 'status-warning', 'status-error', 'status-no-face');
        switch (type) {
            case 'info':
                statusMessage.classList.add('status-info');
                break;
            case 'success':
                statusMessage.classList.add('status-success');
                break;
            case 'warning':
                statusMessage.classList.add('status-warning');
                break;
            case 'error':
                statusMessage.classList.add('status-error');
                break;
            case 'no_face':
                statusMessage.classList.add('status-no-face');
                break;
            default:
                statusMessage.classList.add('status-info');
                break;
        }
    }
}

function checkFacePosition(detection) {
    if (!detection || !video) {
        return {status: 'no_face', message: 'No face detected.'};
    }

    const videoWidth = video.videoWidth;
    const videoHeight = video.videoHeight;
    const box = detection.box;

    const centralRegionXStart = videoWidth * 0.25;
    const centralRegionXEnd = videoWidth * 0.75;
    const centralRegionYStart = videoHeight * 0.20;
    const centralRegionYEnd = videoHeight * 0.80;

    const faceCenterX = box.x + box.width / 2;
    const faceCenterY = box.y + box.height / 2;

    const isCentered = (faceCenterX > centralRegionXStart && faceCenterX < centralRegionXEnd) &&
        (faceCenterY > centralRegionYStart && faceCenterY < centralRegionYEnd);

    const minFaceSize = Math.min(videoWidth, videoHeight) * 0.20;
    const maxFaceSize = Math.min(videoWidth, videoHeight) * 0.70;

    const faceSize = Math.max(box.width, box.height);

    let message = "Please position your face within the frame.";
    let status = 'info';

    if (faceSize < minFaceSize) {
        message = "Move closer to the camera.";
        status = 'warning';
    } else if (faceSize > maxFaceSize) {
        message = "Move further from the camera.";
        status = 'warning';
    } else if (!isCentered) {
        let horizontalMsg = "";
        let verticalMsg = "";
        if (faceCenterX < centralRegionXStart) horizontalMsg = "Move right. ";
        else if (faceCenterX > centralRegionXEnd) horizontalMsg = "Move left. ";

        if (faceCenterY < centralRegionYStart) verticalMsg = "Move down.";
        else if (faceCenterY > centralRegionYEnd) verticalMsg = "Move up.";

        if (horizontalMsg || verticalMsg) {
            message = `Center your face. ${horizontalMsg}${verticalMsg}`;
            status = 'warning';
        } else {
            message = "Adjust your position slightly.";
            status = 'warning';
        }
    } else {
        message = "Face is positioned correctly.";
        status = 'centered';
    }
    return {status, message};
}


async function loadFaceApiModels() {
    loadingDiv.classList.remove("hidden");
    updateStatusMessage('info', "Loading AI models...");
    try {
        while (typeof window.faceapi === 'undefined') {
            console.log("Waiting for window.faceapi to load...");
            await new Promise(resolve => setTimeout(resolve, 100));
        }

        const MODEL_URL = '/static/models';
        await window.faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL);
        await window.faceapi.nets.faceLandmark68Net.loadFromUri(MODEL_URL);
        await window.faceapi.nets.faceRecognitionNet.loadFromUri(MODEL_URL);
        await window.faceapi.nets.faceExpressionNet.loadFromUri(MODEL_URL);

        console.log("✅ Face-API.js models loaded successfully.");
        updateStatusMessage('info', "Models loaded. Starting webcam...");
        loadingDiv.classList.add("hidden");
    } catch (error) {
        console.error("❌ Error loading Face-API.js models:", error);
        updateStatusMessage('error', "Error loading face recognition models. Please check your internet connection and ensure models are in '/static/models'.");
        loadingDiv.classList.add("hidden");
        webcamRunning = false;
        setSystemState(SYSTEM_STATE.INITIAL);
    }
}


const createGestureRecognizer = async () => {
    console.log("🛠️ Initializing Gesture Recognizer...");
    updateStatusMessage('info', "Initializing gesture recognition...");
    try {
        const vision = await FilesetResolver.forVisionTasks(
            "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.3/wasm"
        );
        console.log("Fetched MediaPipe WASM files.");
        gestureRecognizer = await GestureRecognizer.createFromOptions(vision, {
            baseOptions: {
                modelAssetPath:
                    "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task",
                delegate: "GPU"
            },
            runningMode: runningMode,
            numHands: 1,
            minDetectionConfidence: 0.7,
            minTrackingConfidence: 0.7,
            minResultConfidence: 0.1
        });
        console.log("Gesture Recognizer initialized.");
        if (loadingDiv) loadingDiv.classList.add("hidden");
        if (demosSection) demosSection.classList.remove("invisible");
        updateStatusMessage('info', "Gesture recognizer ready. Starting webcam...");
        console.log("✅ Gesture Recognizer loaded successfully.");
        await enableCam();

    } catch (error) {
        console.error("❌ Failed to load Gesture Recognizer:", error);
        updateStatusMessage('error', "Error loading gesture recognition model. Please refresh the page.");
        webcamRunning = false;
        setSystemState(SYSTEM_STATE.INITIAL);
    }
};

function hasGetUserMedia() {
    return !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
}

async function enableCam() {
    console.log(`🎥 enableCam called. Current webcamRunning: ${webcamRunning}`);
    if (!gestureRecognizer || typeof window.faceapi === 'undefined' || loadingDiv && !loadingDiv.classList.contains("hidden")) {
        updateStatusMessage('info', "Please wait for all system components to initialize.");
        console.log("ℹ️ Gesture Recognizer or Face-API.js models not fully ready, waiting.");
        return;
    }

    if (webcamRunning === true) {
        console.log("Stopping webcam...");
        webcamRunning = false;
        if (video.srcObject) {
            video.srcObject.getTracks().forEach(track => {
                console.log(`Stopping track: ${track.kind}`);
                track.stop();
            });
        }
        video.srcObject = null;
        canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);
        if (gestureOutput) gestureOutput.style.display = "none";
        if (employeeIdDisplay) employeeIdDisplay.textContent = 'Waiting for scan...';
        updateStatusMessage('info', "Webcam stopped. Refresh page to restart.");
        setSystemState(SYSTEM_STATE.INITIAL);
        recognizedEmployeeName = null;
        currentEmotion = null;
        console.log("🚫 Webcam stopped. System state reset to INITIAL.");
    } else {
        webcamRunning = true;
        updateStatusMessage('info', "Requesting camera access...");
        if (employeeIdDisplay) employeeIdDisplay.textContent = 'Scanning...';
        console.log("🚀 Starting webcam and requesting camera access...");

        const constraints = {video: true};
        try {
            const stream = await navigator.mediaDevices.getUserMedia(constraints);
            video.srcObject = stream;
            video.onloadedmetadata = () => {
                video.play();
                predictWebcam();
            };
            updateStatusMessage('info', "Webcam enabled. Press Spacebar or Camera button to start scanning for faces.");
            setSystemState(SYSTEM_STATE.FACE_RECOGNIZING);
            recognizedPopupShown = false;
            isScanningAllowed = false;
            console.log("✅ Webcam access granted. System state set to FACE_RECOGNIZING. Scanning paused, press Spacebar or Camera button to start.");
        } catch (err) {
            console.error("❌ Error accessing webcam: ", err);
            updateStatusMessage('error', "Error: Could not access webcam. Please allow camera access and refresh.");
            webcamRunning = false;
            setSystemState(SYSTEM_STATE.INITIAL);
            console.log("🚫 Webcam access denied. System state reset to INITIAL.");
        }
    }
}

let lastVideoTime = -1;
let gestureResults = undefined;

async function predictWebcam() {
    canvasElement.width = video.videoWidth;
    canvasElement.height = video.videoHeight;

    let nowInMs = Date.now();

    if (video.currentTime !== lastVideoTime) {
        lastVideoTime = video.currentTime;
        if (gestureRecognizer) {
            gestureResults = gestureRecognizer.recognizeForVideo(video, nowInMs);
        }
    }

    canvasCtx.save();
    canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);
    canvasCtx.drawImage(video, 0, 0, canvasElement.width, canvasElement.height);
    canvasCtx.translate(canvasElement.width, 0);
    canvasCtx.scale(-1, 1);

    if (webcamRunning && gestureResults && gestureResults.landmarks && gestureResults.landmarks.length > 0) {
        const drawingUtils = new DrawingUtils(canvasCtx);
        // for (const handLandmarks of gestureResults.landmarks) {
        //     drawingUtils.drawConnectors(
        //         handLandmarks,
        //         GestureRecognizer.HAND_CONNECTIONS,
        //         { color: "#00FF00", lineWidth: 5 }
        //     );
        //     drawingUtils.drawLandmarks(handLandmarks, {
        //         color: "#FF0000",
        //         lineWidth: 2
        //     });
        // }
    }

    let detections = [];
    if (webcamRunning && typeof window.faceapi !== 'undefined' && isScanningAllowed) {
        try {
            detections = await window.faceapi.detectAllFaces(video, new window.faceapi.TinyFaceDetectorOptions())
                .withFaceLandmarks()
                .withFaceExpressions();

            if (detections.length > 1) {
                setSystemState(SYSTEM_STATE.MULTIPLE_FACES_DETECTED);
                updateStatusMessage('warning', 'Multiple faces detected! Please ensure only one person is in front of the camera.');
                employeeIdDisplay.textContent = 'Multiple Faces';
                currentEmotion = null;
                window.faceapi.draw.drawDetections(canvasElement, window.faceapi.resizeResults(detections, {
                    width: canvasElement.width,
                    height: canvasElement.height
                }));
                isScanningAllowed = false;
                recognizedEmployeeName = null;
                recognizedPopupShown = false;
            } else if (detections.length === 1) {
                setSystemState(SYSTEM_STATE.FACE_RECOGNIZING);
                noFaceDetectedAttempts = 0;
                const resizedDetections = window.faceapi.resizeResults(detections[0], {
                    width: canvasElement.width,
                    height: canvasElement.height
                });

                window.faceapi.draw.drawDetections(canvasElement, resizedDetections);

                const expressions = resizedDetections.expressions;
                if (expressions) {
                    const sortedExpressions = Object.keys(expressions).sort((a, b) => expressions[b] - expressions[a]);
                    currentEmotion = sortedExpressions[0];
                    console.log("📊 Detected Emotion:", currentEmotion);
                }

                const facePositionStatus = checkFacePosition(resizedDetections.detection);
                if (currentSystemState !== SYSTEM_STATE.MULTIPLE_FACES_DETECTED) {
                    updateStatusMessage(facePositionStatus.status, facePositionStatus.message);
                }

            } else {
                if (currentSystemState !== SYSTEM_STATE.MULTIPLE_FACES_DETECTED) {
                    noFaceDetectedAttempts++;
                    if (noFaceDetectedAttempts >= 2) {
                        updateStatusMessage('no_face', 'No face detected. Press Spacebar or Camera button to re-scan.');
                        employeeIdDisplay.textContent = 'Waiting for scan...';
                    }
                }
                currentEmotion = null;
            }
        } catch (faceApiError) {
            console.error("❌ Error during Face-API.js detection:", faceApiError);
            updateStatusMessage('error', 'Error during face detection. Models might not be fully ready or a webcam issue occurred.');
        }
    } else if (!isScanningAllowed) {
        if (currentSystemState === SYSTEM_STATE.FACE_RECOGNIZING) {
            employeeIdDisplay.textContent = 'Waiting for scan...';
            updateStatusMessage("info", "Scanning... Please wait a few seconds. If it takes longer than 10 seconds, please press spacebar again.");
        }
        if (currentSystemState === SYSTEM_STATE.FACE_RECOGNIZED_PROMPT_GESTURE) {
            console.log("Prompt...")
            employeeIdDisplay.textContent = 'Waiting for scan...';
        }
        if (currentSystemState === SYSTEM_STATE.ATTENDANCE_PROCESSING) {
            console.log("Processing...")
        }
        if (currentSystemState !== SYSTEM_STATE.MULTIPLE_FACES_DETECTED) {
            employeeIdDisplay.textContent = 'Ready to scan.';
        }
        currentEmotion = null;
    }


    canvasCtx.restore();
    canvasElement.style.display = "block";

    let currentGesture = null;
    if (webcamRunning && gestureResults && gestureResults.gestures && gestureResults.gestures.length > 0
        &&
        gestureResults.gestures[0] && gestureResults.gestures[0][0].score >= 0.5) {
        currentGesture = gestureResults.gestures[0][0].categoryName;
    }

    const currentTime = Date.now();

    if (currentSystemState === SYSTEM_STATE.FACE_RECOGNIZING && !isScanningAllowed && (currentTime - lastSpeechPromptTime) > (SPEECH_PROMPT_INTERVAL_SECONDS * 1000)) {
        speak("Press spacebar or camera button to initiate face scan for attendance.");
        lastSpeechPromptTime = currentTime;
    }


    switch (currentSystemState) {
        case SYSTEM_STATE.FACE_RECOGNIZING:
            if (isScanningAllowed && detections.length === 1) {
                const facePosStatus = (detections[0] && detections[0].detection) ? checkFacePosition(detections[0].detection).status : 'no_face';
                const cooldownPassed = (currentTime - lastFaceRecognitionTime) > (FACE_RECOGNITION_COOLDOWN_SECONDS * 1000);

                console.log(`[STATE: FACE_RECOGNIZING] Face Pos: ${facePosStatus}, Emotion: ${currentEmotion}, Cooldown Passed: ${cooldownPassed}, Scanning Allowed: ${isScanningAllowed}`);

                if (currentEmotion !== null && facePosStatus === 'centered' && cooldownPassed) {
                    console.log(`[ACTION] Triggering backend face recognition.`);
                    lastFaceRecognitionTime = currentTime;
                    const imageDataUrl = captureFrame(video);
                    recognizeFaceOnBackend(imageDataUrl);
                    isScanningAllowed = false;
                } else if (currentEmotion === null) {
                } else if (!cooldownPassed) {
                    const timeLeft = FACE_RECOGNITION_COOLDOWN_SECONDS - Math.floor((currentTime - lastFaceRecognitionTime) / 1000);
                    updateStatusMessage('info', `Scanning... Please wait ${timeLeft} seconds.`);
                }
            } else if (!isScanningAllowed && detections.length === 0) {
                employeeIdDisplay.textContent = 'Ready to scan.';
            }
            break;

        case SYSTEM_STATE.MULTIPLE_FACES_DETECTED:
            updateStatusMessage('error', 'Multiple faces detected! Please ensure only one person is in front of the camera.');
            employeeIdDisplay.textContent = 'Multiple Faces';
            if (!recognizedPopupShown) {
                speak("Multiple faces detected. Please ensure only one person is in front of the camera.");
                recognizedPopupShown = true;
                setTimeout(() => recognizedPopupShown = false, 5000);
            }
            break;

        case SYSTEM_STATE.FACE_RECOGNIZED_PROMPT_GESTURE:
            console.log(`[STATE: FACE_RECOGNIZED_PROMPT_GESTURE] Recognized: ${recognizedEmployeeName}. Waiting for gesture.`);
            const displayEmployeeName = recognizedEmployeeName.replace("_spoken_prompt", "");
            employeeIdDisplay.textContent = `Recognized: ${displayEmployeeName}`;
            updateStatusMessage('success', `Welcome ${displayEmployeeName}! Please perform the attendance gesture.`);

            if (!recognizedPopupShown) {
                recognizedFacePopup(displayEmployeeName);
                recognizedPopupShown = true;
            }

            if (!recognizedEmployeeName.includes("_spoken_prompt") && (currentTime - lastSpeechPromptTime) > (SPEECH_PROMPT_INTERVAL_SECONDS * 1000 / 2)) {
                speak(`Welcome ${displayEmployeeName}! Please show your attendance gesture.`);
                lastSpeechPromptTime = currentTime;
                recognizedEmployeeName += "_spoken_prompt";
            }

            // New logic to handle both attendance and break gestures
            if (currentGesture === ATTENDANCE_TRIGGER_GESTURE || currentGesture === BREAK_TRIGGER_GESTURE) {
                if ((currentTime - lastAttendanceMarkedTime) > (ATTENDANCE_COOLDOWN_SECONDS * 1000)) {
                     console.log(`[ACTION] Gesture '${currentGesture}' detected. Marking attendance/break.`);
                     setSystemState(SYSTEM_STATE.ATTENDANCE_PROCESSING);
                     updateStatusMessage('info', `Marking attendance/break...`);
                     navigator.geolocation.getCurrentPosition(position => {
                        const userLatitude = position.coords.latitude;
                        const userLongitude = position.coords.longitude;
                        markAttendanceOnBackend(displayEmployeeName, currentGesture, userLatitude, userLongitude);
                    }, error => {
                        console.warn("Geolocation error:", error);
                        updateStatusMessage('warning', "Couldn't get your location. Marking attendance without location check.");
                        markAttendanceOnBackend(displayEmployeeName, currentGesture, null, null);
                    }, {enableHighAccuracy: true, timeout: 5000, maximumAge: 0});
                } else {
                    const timeLeft = ATTENDANCE_COOLDOWN_SECONDS - Math.floor((currentTime - lastAttendanceMarkedTime) / 1000);
                    console.log(`[INFO] Attendance cooldown active for ${displayEmployeeName}. Time left: ${timeLeft}s`);
                    updateStatusMessage('info', `Attendance for ${displayEmployeeName} recently marked. Please wait.`);
                }
            }
            break;

        case SYSTEM_STATE.ATTENDANCE_PROCESSING:
            console.log("[STATE: ATTENDANCE_PROCESSING] Waiting for backend response.");
            updateStatusMessage('info', "Processing attendance, please wait...");
            break;

        case SYSTEM_STATE.INITIAL:
        default:
            updateStatusMessage('info', "System initializing. Please wait...");
            if (employeeIdDisplay) employeeIdDisplay.textContent = 'Waiting for scan...';
            console.log("[STATE: INITIAL] Awaiting webcam start/model load.");
            break;
    }

    if (webcamRunning === true) {
        window.requestAnimationFrame(predictWebcam);
    }
}

function captureFrame(videoElement) {
    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = videoElement.videoWidth;
    tempCanvas.height = videoElement.videoHeight;
    const tempCtx = tempCanvas.getContext('2d');
    tempCtx.translate(tempCanvas.width, 0);
    tempCtx.scale(-1, 1);
    tempCtx.drawImage(videoElement, 0, 0, tempCanvas.width, tempCanvas.height);
    const imageDataUrl = tempCanvas.toDataURL('image/jpeg', 0.8);
    console.log("🖼️ Frame captured for face recognition.");
    return imageDataUrl;
}

function showLatePopup(employeeName) {
    const popup = document.createElement('div');
    popup.className = 'popup popup--late';
    popup.textContent = `You are late, ${employeeName}!`;
    document.body.appendChild(popup);

    setTimeout(() => popup.remove(), 4000);
    console.log(`🔔 "You are Late" popup shown for ${employeeName}.`);
}

function showAttendanceSuccessPopup(message, employeeName) {
    const popup = document.createElement('div');
    popup.className = 'popup popup--success';
    popup.innerHTML = `✅ Attendance marked for <strong>${employeeName}</strong><br/>${message}`;
    document.body.appendChild(popup);

    setTimeout(() => popup.remove(), 4000);
    console.log(`🎉 "Attendance Marked" popup shown for ${employeeName}.`);

    updateRecentRecords();
}

function showBreakSuccessPopup(message, employeeName) {
    const popup = document.createElement('div');
    popup.className = 'popup popup--success';
    popup.innerHTML = `⏳ Break marked for <strong>${employeeName}</strong><br/>${message}`;
    document.body.appendChild(popup);

    setTimeout(() => popup.remove(), 4000);
    console.log(`🎉 "Break Marked" popup shown for ${employeeName}.`);

    updateRecentRecords();
}


function pressCameraButtonPopup() {
    const existingPopup = document.querySelector('.popup--camera');
    if (existingPopup) {
        existingPopup.remove();
    }

    const popup = document.createElement('div');
    popup.className = 'popup popup--camera';
    popup.textContent = 'Press the camera button or space bar to scan your face.';
    document.body.appendChild(popup);

    setTimeout(() => {
        if (popup.parentNode) {
            popup.remove();
        }
    }, 4000);
    console.log('📸 "Press Camera Button" popup shown.');
}

function recognizedFacePopup(employeeName) {
    const existingPopup = document.querySelector('.popup--recognized-face');
    if (existingPopup) {
        existingPopup.remove();
    }

    const popup = document.createElement('div');
    popup.className = 'popup popup--recognized-face';
    popup.innerHTML = `👋 Welcome, <strong>${employeeName}</strong>! Please perform the attendance gesture.`;
    document.body.appendChild(popup);

    setTimeout(() => {
        if (popup.parentNode) {
            popup.remove();
        }
    }, 5000);
    console.log(`👤 "Recognized Face" popup shown for ${employeeName}.`);
}


function updateRecentRecords() {
    fetch('/attendance/recent-attendance-records/')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                recentRecordsScrollContainer.innerHTML = data.records_html;
                if (data.records_html.trim() !== '') {
                    noRecentRecordsMessage.style.display = 'none';
                } else {
                    noRecentRecordsMessage.style.display = 'block';
                }
                const scrollArrows = document.querySelector('.scroll-arrows');
                if (recentRecordsScrollContainer.scrollWidth > recentRecordsScrollContainer.clientWidth) {
                    if (scrollArrows) scrollArrows.style.display = 'flex';
                } else {
                    if (scrollArrows) scrollArrows.style.display = 'none';
                }
                console.log("✅ Recent records updated successfully.");
            } else {
                console.error("⚠️ Failed to update recent records:", data.message);
            }
        })
        .catch(error => {
            console.error("❌ Error updating recent attendance records:", error);
            if (recentRecordsScrollContainer) {
                recentRecordsScrollContainer.innerHTML = '<div class="no-recent-records text-red-500">Failed to load records. Check connection.</div>';
            }
            if (noRecentRecordsMessage) {
                noRecentRecordsMessage.style.display = 'none';
            }
        });
}


async function recognizeFaceOnBackend(imageDataUrl) {
    console.log(`📡 Sending image to backend for face recognition.`);
    updateStatusMessage('info', "Scanning for face...");
    if (employeeIdDisplay) employeeIdDisplay.textContent = "Recognizing...";

    try {
        const response = await fetch('/attendance/recognize-face-for-prompt/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                image: imageDataUrl
            })
        });

        const data = await response.json();
        console.log("✅ Face Recognition Response from Backend:", data);

        if (response.ok) {
            if (data.status === 'success' && data.recognized_name !== 'Unknown') {
                recognizedEmployeeName = data.recognized_name;
                setSystemState(SYSTEM_STATE.FACE_RECOGNIZED_PROMPT_GESTURE);
                console.log(`🥳 Face recognized: ${recognizedEmployeeName}. Ready for gesture.`);
            } else {
                recognizedEmployeeName = null;
                employeeIdDisplay.textContent = 'Unknown Face';
                updateStatusMessage('warning', data.message || 'No recognizable face detected. Press Spacebar or Camera button to re-scan.');
                setSystemState(SYSTEM_STATE.FACE_RECOGNIZING);
                recognizedPopupShown = false;
                isScanningAllowed = false;
                console.log(`⚠️ Face recognition: ${data.message || 'Unknown face detected'}. Paused scanning.`);
            }
        } else {
            recognizedEmployeeName = null;
            employeeIdDisplay.textContent = 'Error';
            updateStatusMessage('error', `Error during recognition. Please try again or contact support.`);
            setSystemState(SYSTEM_STATE.FACE_RECOGNIZING);
            recognizedPopupShown = false;
            isScanningAllowed = false;
            console.error(`❌ Server error (${response.status}) during face recognition: ${data.message}`);
        }
    } catch (error) {
        console.error("❌ Network error during face recognition:", error);
        recognizedEmployeeName = null;
        employeeIdDisplay.textContent = 'Network Error';
        updateStatusMessage('error', "Network error. Please check your internet connection.");
        setSystemState(SYSTEM_STATE.FACE_RECOGNIZING);
        recognizedPopupShown = false;
        isScanningAllowed = false;
    }
}

async function markAttendanceOnBackend(name, gesture, latitude, longitude) {
    console.log(`📡 Sending attendance request for ${name} with gesture ${gesture}. Current Emotion: ${currentEmotion}. Lat: ${latitude}, Lng: ${longitude}`);
    updateStatusMessage('info', `Marking attendance for ${name}...`);
    if (employeeIdDisplay) employeeIdDisplay.textContent = "Marking...";

    try {
        const response = await fetch('/attendance/mark-attendance-with-gesture/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                recognized_name: name,
                gesture: gesture,
                emotional_state: currentEmotion,
                latitude: latitude,
                longitude: longitude
            })
        });

        const data = await response.json();
        console.log("✅ Attendance Marking Response from Backend:", data);

        if (response.ok) {
            updateStatusMessage('success', data.message);
            speak(data.message);

            // Use different popup for breaks
            if (data.attendance_type === "BREAK_IN" || data.attendance_type === "BREAK_OUT") {
                showBreakSuccessPopup(data.message, name);
            } else if (data.is_late) {
                showLatePopup(name);
            } else {
                showAttendanceSuccessPopup(data.message, name);
            }

            lastAttendanceMarkedTime = Date.now();
            updateRecentRecords();

        } else if (data.status === 'info') {
            updateStatusMessage('info', data.message);
            speak(data.message);
            console.log(`ℹ️ Attendance info: ${data.message}`);

        } else {
            updateStatusMessage('error', data.message || 'Failed to mark attendance. Please try again.');
            speak(data.message || 'Failed to mark attendance.');
            console.warn(`⚠️ Attendance warning/failure: ${data.message}`);
        }

    } catch (error) {
        console.error("❌ Network error during attendance marking:", error);
        updateStatusMessage('error', "Network error. Unable to connect to server.");

    } finally {
        setSystemState(SYSTEM_STATE.FACE_RECOGNIZING);
        recognizedPopupShown = false;
        recognizedEmployeeName = null;
        currentEmotion = null;
        isScanningAllowed = false;
        console.log("🔄 Reverting to FACE_RECOGNIZING state after attendance attempt. Scanning paused.");

        setTimeout(() => {
            if (currentSystemState === SYSTEM_STATE.FACE_RECOGNIZING) {
                if (employeeIdDisplay) employeeIdDisplay.textContent = 'Press Spacebar or Camera button to scan.';
                updateStatusMessage('info', "Scan complete. Press Spacebar or Camera button for next scan.");
                console.log("⏱️ Display reverted to scanning message.");
                pressCameraButtonPopup();
            }
        }, 3000);
    }
}


function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    console.log(`🍪 CSRF Token: ${cookieValue ? 'Found' : 'Not Found'}`);
    return cookieValue;
}

function updateCurrentDateTime() {
    const now = new Date();
    const optionsDate = {weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'};
    const optionsTime = {hour: 'numeric', minute: 'numeric', hour12: true};
    const dateString = now.toLocaleDateString('en-US', optionsDate);
    const timeString = now.toLocaleTimeString('en-US', optionsTime);
    if (currentDateTimeElement) {
        currentDateTimeElement.textContent = `${dateString} | ${timeString}`;
    }
}

document.addEventListener('keydown', (event) => {
    if (event.code === 'Space') {
        event.preventDefault();
        console.log("Spacebar pressed. isScanningAllowed set to true.");
        recognizedEmployeeName = null;
        currentEmotion = null;
        recognizedPopupShown = false;

        if (currentSystemState === SYSTEM_STATE.FACE_RECOGNIZING ||
            currentSystemState === SYSTEM_STATE.FACE_RECOGNIZED_PROMPT_GESTURE ||
            currentSystemState === SYSTEM_STATE.MULTIPLE_FACES_DETECTED) {
            isScanningAllowed = true;
            noFaceDetectedAttempts = 0;
            updateStatusMessage('info', 'Scanning for face...');
            employeeIdDisplay.textContent = 'Scanning...';
            lastFaceRecognitionTime = 0;
            setSystemState(SYSTEM_STATE.FACE_RECOGNIZING);
        } else if (currentSystemState === SYSTEM_STATE.ATTENDANCE_PROCESSING) {
            console.log("Spacebar pressed while processing attendance, ignoring.");
        }
    }
});

if (cameraButton) {
    cameraButton.addEventListener('click', () => {
        console.log("Camera button pressed. isScanningAllowed set to true.");
        recognizedEmployeeName = null;
        currentEmotion = null;
        recognizedPopupShown = false;

        if (currentSystemState === SYSTEM_STATE.FACE_RECOGNIZING ||
            currentSystemState === SYSTEM_STATE.FACE_RECOGNIZED_PROMPT_GESTURE ||
            currentSystemState === SYSTEM_STATE.MULTIPLE_FACES_DETECTED) {
            isScanningAllowed = true;
            noFaceDetectedAttempts = 0;
            updateStatusMessage('info', 'Scanning for face...');
            employeeIdDisplay.textContent = 'Scanning...';
            lastFaceRecognitionTime = 0;
            setSystemState(SYSTEM_STATE.FACE_RECOGNIZING);
        } else if (currentSystemState === SYSTEM_STATE.ATTENDANCE_PROCESSING) {
            console.log("Camera button pressed while processing attendance, ignoring.");
        }
    });
}


window.onload = async () => {
    console.log("🚀 Window loaded. Initializing application...");
    await loadFaceApiModels();
    await createGestureRecognizer();

    updateCurrentDateTime();
    setInterval(updateCurrentDateTime, 1000);

    updateRecentRecords();
    pressCameraButtonPopup();
};

window.onbeforeunload = () => {
    console.log("👋 Window is about to unload. Stopping webcam and speech.");
    if (video && video.srcObject) {
        video.srcObject.getTracks().forEach(track => track.stop());
        console.log("📸 Webcam tracks stopped.");
    }
    if ('speechSynthesis' in window) {
        speechSynthesis.cancel();
        console.log("🗣️ Speech synthesis cancelled.");
    }
};
