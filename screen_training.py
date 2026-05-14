import cv2
import time
import math
import mediapipe as mp
from PySide6.QtCore import QObject, Signal, Slot, Property, QTimer
from PySide6.QtGui import QImage
from PySide6.QtQuick import QQuickImageProvider


class VideoProvider(QQuickImageProvider):
    def __init__(self):
        super().__init__(QQuickImageProvider.Image)
        self.image = QImage()

    def requestImage(self, id, size, requestedSize):
        return self.image


class TrainingController(QObject):
    frameUpdated = Signal()

    # Joint Constants for readability
    L_SHOULDER, R_SHOULDER = 11, 12
    L_ELBOW, R_ELBOW = 13, 14
    L_WRIST, R_WRIST = 15, 16
    L_HIP, R_HIP = 23, 24
    L_KNEE, R_KNEE = 25, 26
    L_ANKLE, R_ANKLE = 27, 28

    def __init__(self, app_core, video_provider):
        super().__init__()
        self.app = app_core
        self.video_provider = video_provider

        # MediaPipe Setup
        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.pose = self.mp_pose.Pose(model_complexity=0, min_detection_confidence=0.5)

        # State Management
        self.timer = QTimer()
        self.timer.timeout.connect(self.process_frame)
        self.cap = None
        self.is_running = False
        self._current_letter = "?"

        # Stats tracking
        self.start_time = 0
        self.session_letters = set()
        self.buffer_size = 10
        self.last_letters_queue = []

    @Property(str, notify=frameUpdated)
    def currentLetter(self):
        return self._current_letter

    def calculate_angle(self, a, b, c):
        """Calculates the angle at joint 'b' given points a, b, and c."""
        try:
            ang = math.degrees(
                math.atan2(c.y - b.y, c.x - b.x) - math.atan2(a.y - b.y, a.x - b.x)
            )
            ang = abs(ang)
            return ang if ang <= 180 else 360 - ang
        except Exception:
            return 0

    def detect_letter(self, lm):
        """Maps calculated angles to specific letter poses."""
        # Calculate key angles
        # Shoulder angles (Body-Shoulder-Wrist) to determine arm lift
        l_shoulder_ang = self.calculate_angle(lm[self.L_HIP], lm[self.L_SHOULDER], lm[self.L_WRIST])
        r_shoulder_ang = self.calculate_angle(lm[self.R_HIP], lm[self.R_SHOULDER], lm[self.R_WRIST])
        l_arm_ang = self.calculate_angle(lm[self.L_SHOULDER], lm[self.L_ELBOW], lm[self.L_WRIST])
        r_arm_ang = self.calculate_angle(lm[self.R_SHOULDER], lm[self.R_ELBOW], lm[self.R_WRIST])
        # Leg angle (Hip-Knee-Ankle) for the 'L' shape
        l_leg_ang = self.calculate_angle(lm[self.L_HIP], lm[self.L_KNEE], lm[self.L_ANKLE])
        r_leg_ang = self.calculate_angle(lm[self.R_HIP], lm[self.R_KNEE], lm[self.R_ANKLE])

        # Define Pose Requirements
        leg_is_tree = (l_leg_ang < 90 and r_leg_ang > 160) or (r_leg_ang < 90 and l_leg_ang > 160)


        poses = {
            "67": (135 < l_shoulder_ang <= 180) and (135 < r_shoulder_ang <= 180) and \
                  (90 < l_arm_ang < 140) and (90 < r_arm_ang < 140) and \
                  leg_is_tree,
            "T": (80 < l_shoulder_ang < 110) and (80 < r_shoulder_ang < 110),
            "Y": (130 < l_shoulder_ang < 160) and (130 < r_shoulder_ang < 160),
            "I": (165 < l_shoulder_ang <= 180) and (165 < r_shoulder_ang <= 180),
            "L": (l_shoulder_ang > 150) and (l_leg_ang < 150)  # Arm up, leg bent/out
        }

        for letter, active in poses.items():
            if active:
                return letter
        return "?"

    @Slot()
    def startTraining(self):
        if not self.is_running:
            src = int(self.app.video_source) if str(self.app.video_source).isdigit() else self.app.video_source
            self.cap = cv2.VideoCapture(src)
            if self.cap.isOpened():
                self.is_running = True
                self.start_time = time.time()
                self.session_letters = set()
                self.last_letters_queue = []
                self.timer.start(15)

    @Slot()
    def stopTraining(self):
        if self.is_running:
            self.is_running = False
            self.timer.stop()
            duration = int(time.time() - self.start_time)
            self.app.update_stats(duration, list(self.session_letters))
            if self.cap:
                self.cap.release()
                self.cap = None

    def process_frame(self):
        if not self.cap: return

        ret, frame = self.cap.read()
        if not ret:
            self.stop_and_nav_results()
            return

        # Prepare Image
        frame = cv2.flip(cv2.resize(frame, (640, 480)), 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb)

        detected_letter = "?"

        if results.pose_landmarks:
            lm = results.pose_landmarks.landmark
            detected_letter = self.detect_letter(lm)

            # Smooth detection using a moving average (mode)
            self.last_letters_queue.append(detected_letter)
            if len(self.last_letters_queue) > self.buffer_size:
                self.last_letters_queue.pop(0)

            # Determine most frequent letter in buffer
            self._current_letter = max(set(self.last_letters_queue), key=self.last_letters_queue.count)

            if self._current_letter != "?":
                self.session_letters.add(self._current_letter)

            # Draw skeleton
            self.mp_drawing.draw_landmarks(rgb, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS)

            print(self._current_letter)

        # Update UI Provider
        h, w, ch = rgb.shape
        self.video_provider.image = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888).copy()
        self.frameUpdated.emit()

    def stop_and_nav_results(self):
        self.stopTraining()
        self.app.navRequested.emit("ResultsScreen.qml")