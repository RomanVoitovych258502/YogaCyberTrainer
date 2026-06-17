import warnings
import cv2
import time
import math
import os
import random
import mediapipe as mp
from PySide6.QtCore import QObject, Signal, Slot, Property, QTimer
from PySide6.QtGui import QImage
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtMultimedia import QMediaDevices

HOLD_REQUIRED = 3.0
HOLD_TOLERANCE = 0.5

AVAILABLE_POSES = [
    "pies_z_glowa_w_dol",
    "pozycja_dziecka",
    "pozycja_drzewa",
    "pozycja_gory"
]


class VideoProvider(QQuickImageProvider):
    def __init__(self):
        super().__init__(QQuickImageProvider.Image)
        self.image = QImage()

    def requestImage(self, id, size, requestedSize):
        return self.image


class TrainingController(QObject):
    frameUpdated = Signal()
    poseCompleted = Signal(str)

    NOSE = 0
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
        self.timer = QTimer()
        self.timer.timeout.connect(self.process_frame)
        self.cap = None
        self.is_running = False
        self._rotation_state = 0
        self._camera_index = 0

        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.pose = self.mp_pose.Pose(model_complexity=1)

        self._current_letter = "?"
        self.buffer_size = 15
        self.last_letters_queue = []

        # Logika grywalizacji i celów
        self._target_pose = random.choice(AVAILABLE_POSES)
        self._super_end_time = 0.0
        self._hold_start = None
        self._lost_start = None
        self._hold_progress = 0.0
        self._current_hints = []

    # --- WŁAŚCIWOŚCI DLA QML ---

    @Property(str, notify=frameUpdated)
    def currentLetter(self):
        return self._target_pose

    @Property(list, notify=frameUpdated)
    def cameraNames(self):
        devices = QMediaDevices.videoInputs()
        if not devices:
            return ["Brak dostępnych kamer"]
        return [dev.description() for dev in devices]

    @Property(bool, notify=frameUpdated)
    def isRunning(self):
        return self.is_running

    @Property(list, notify=frameUpdated)
    def poseHints(self):
        return self._current_hints

    @Property(float, notify=frameUpdated)
    def holdProgress(self):
        return self._hold_progress

    @Property(bool, notify=frameUpdated)
    def isSuper(self):
        return time.time() < self._super_end_time

    # --- SLOTY I LOGIKA ---

    @Slot(int)
    def setCameraIndex(self, index):
        if self._camera_index != index:
            self._camera_index = index
            if self.is_running:
                self.stopTraining()
                self.startTraining()

    @Slot()
    def rotateCamera(self):
        self._rotation_state = (self._rotation_state + 1) % 4

    @Slot()
    def nextPose(self):
        """Ręczna zmiana pozycji na inną losową (wywoływana z QML po kliknięciu)"""
        options = [p for p in AVAILABLE_POSES if p != self._target_pose]
        if options:
            self._target_pose = random.choice(options)

        # Resetowanie liczników trzymania pozycji
        self._hold_start = None
        self._lost_start = None
        self._hold_progress = 0.0
        self._current_hints = []
        self.frameUpdated.emit()

    def calculate_angle(self, a, b, c):
        ang = math.degrees(math.atan2(c.y - b.y, c.x - b.x) - math.atan2(a.y - b.y, a.x - b.x))
        return abs(ang) if abs(ang) <= 180 else 360 - abs(ang)

    def detect_letter(self, lm, target_pose):
        l_hip_ang = self.calculate_angle(lm[self.L_SHOULDER], lm[self.L_HIP], lm[self.L_KNEE])
        r_hip_ang = self.calculate_angle(lm[self.R_SHOULDER], lm[self.R_HIP], lm[self.R_KNEE])
        l_knee_ang = self.calculate_angle(lm[self.L_HIP], lm[self.L_KNEE], lm[self.L_ANKLE])
        r_knee_ang = self.calculate_angle(lm[self.R_HIP], lm[self.R_KNEE], lm[self.R_ANKLE])
        l_elbow_ang = self.calculate_angle(lm[self.L_SHOULDER], lm[self.L_ELBOW], lm[self.L_WRIST])
        r_elbow_ang = self.calculate_angle(lm[self.R_SHOULDER], lm[self.R_ELBOW], lm[self.R_WRIST])
        l_sh_ang = self.calculate_angle(lm[self.L_HIP], lm[self.L_SHOULDER], lm[self.L_WRIST])
        r_sh_ang = self.calculate_angle(lm[self.R_HIP], lm[self.R_SHOULDER], lm[self.R_WRIST])

        mean_hip_y = (lm[self.L_HIP].y + lm[self.R_HIP].y) / 2
        mean_sh_y = (lm[self.L_SHOULDER].y + lm[self.R_SHOULDER].y) / 2
        mean_ank_y = (lm[self.L_ANKLE].y + lm[self.R_ANKLE].y) / 2
        mean_wrist_y = (lm[self.L_WRIST].y + lm[self.R_WRIST].y) / 2
        mean_wrist_x = (lm[self.L_WRIST].x + lm[self.R_WRIST].x) / 2
        mean_sh_x = (lm[self.L_SHOULDER].x + lm[self.R_SHOULDER].x) / 2
        mean_hip_x = (lm[self.L_HIP].x + lm[self.R_HIP].x) / 2
        nose_y = lm[self.NOSE].y
        nose_x = lm[self.NOSE].x

        hints_downdog = []
        if not (l_hip_ang < 120 and r_hip_ang < 120): hints_downdog.append("Ugnij mocniej biodra")
        if not (l_knee_ang > 140 and r_knee_ang > 140): hints_downdog.append("Wyprostuj kolana")
        if not (l_elbow_ang > 140 and r_elbow_ang > 140): hints_downdog.append("Wyprostuj lokcie")
        if not (mean_hip_y < mean_sh_y): hints_downdog.append("Uniesc biodra wyzej")
        if not (mean_wrist_y > mean_sh_y): hints_downdog.append("Oprzyj dlonie")

        hints_childs = []
        if not (l_knee_ang < 80 and r_knee_ang < 80): hints_childs.append("Ugnij kolana bardziej")
        if not (abs(mean_hip_y - mean_ank_y) < 0.10): hints_childs.append("Oprzyj biodra na pietach")
        if not ((l_sh_ang > 145 and r_sh_ang > 145) and (l_elbow_ang > 130 and r_elbow_ang > 130)): hints_childs.append(
            "Wyciagnij rece do przodu")
        if not (mean_sh_y > mean_hip_y - 0.05): hints_childs.append("Opusc tors nizej")

        hints_tree = []
        tree_l = (l_knee_ang < 110 and r_knee_ang > 150) and (lm[self.L_ANKLE].y < lm[self.R_KNEE].y + 0.05)
        tree_r = (r_knee_ang < 110 and l_knee_ang > 150) and (lm[self.R_ANKLE].y < lm[self.L_KNEE].y + 0.05)
        if not (tree_l or tree_r): hints_tree.append("Postaw stope na lydce")
        if not (mean_wrist_y < nose_y): hints_tree.append("Uniesc dlonie nad glowe")
        if not (abs(lm[self.L_WRIST].x - lm[self.R_WRIST].x) < 0.15): hints_tree.append("Zlacz dlonie razem")
        if not (l_elbow_ang < 155 and r_elbow_ang < 155): hints_tree.append("Ugnij lekko lokcie")
        if not (abs(lm[self.L_ELBOW].x - lm[self.R_ELBOW].x) > abs(
            lm[self.L_SHOULDER].x - lm[self.R_SHOULDER].x)): hints_tree.append("Rozstaw lokcie szerzej")

        hints_mountain = []
        if not ((l_knee_ang > 145 and r_knee_ang > 145) and (
                l_hip_ang > 140 and r_hip_ang > 140)): hints_mountain.append("Wyprostuj nogi i biodra")
        if not (abs(lm[self.L_ANKLE].x - lm[self.R_ANKLE].x) < 0.18): hints_mountain.append("Zlacz stopy razem")
        if not (mean_wrist_y < nose_y): hints_mountain.append("Uniesc rece")
        if not (abs(mean_wrist_x - nose_x) > 0.08): hints_mountain.append("Odchyl rece do tylu")
        if not (abs(mean_sh_x - mean_hip_x) > 0.05): hints_mountain.append("Wygnij lekko plecy")

        all_hints = {
            "pies_z_glowa_w_dol": hints_downdog,
            "pozycja_dziecka": hints_childs,
            "pozycja_drzewa": hints_tree,
            "pozycja_gory": hints_mountain
        }

        target_hints = all_hints.get(target_pose, [])
        if len(target_hints) == 0:
            return target_pose, []
        return "?", target_hints

    def _update_hold_timer(self, smoothed_pose: str, now: float):
        if smoothed_pose != self._target_pose:
            if self._lost_start is None:
                self._lost_start = now
            elif now - self._lost_start > HOLD_TOLERANCE:
                self._hold_start = None
                self._lost_start = None
                self._hold_progress = 0.0
            return self._hold_progress

        self._lost_start = None

        if self._hold_start is None:
            self._hold_start = now
            self._hold_progress = 0.0
            return 0.0

        elapsed = now - self._hold_start
        self._hold_progress = min(elapsed / HOLD_REQUIRED, 1.0)

        if self._hold_progress >= 1.0:
            self.poseCompleted.emit(self._target_pose)
            self._super_end_time = now + 2.0

            options = [p for p in AVAILABLE_POSES if p != self._target_pose]
            if options:
                self._target_pose = random.choice(options)

            self._hold_start = None
            self._hold_progress = 0.0

        return self._hold_progress

    @Slot()
    def startTraining(self):
        if not self.is_running:
            self.cap = cv2.VideoCapture(self._camera_index, cv2.CAP_DSHOW)
            if not self.cap or not self.cap.isOpened():
                self.cap = cv2.VideoCapture(self._camera_index)

            self.is_running = True
            self.last_letters_queue = []
            self._hold_start = None
            self._lost_start = None
            self._hold_progress = 0.0
            self.timer.start(15)

    @Slot()
    def stopTraining(self):
        if self.is_running:
            self.is_running = False
            self.timer.stop()
            if self.cap:
                self.cap.release()
                self.cap = None
            self.frameUpdated.emit()

    def process_frame(self):
        if not self.cap: return
        ret, frame = self.cap.read()
        if not ret: return

        frame = cv2.resize(frame, (640, 480))
        frame = cv2.flip(frame, 1)

        if self._rotation_state == 1:
            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        elif self._rotation_state == 2:
            frame = cv2.rotate(frame, cv2.ROTATE_180)
        elif self._rotation_state == 3:
            frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb)

        detected = "?"
        hints = []

        if results.pose_landmarks:
            self.mp_drawing.draw_landmarks(rgb, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS)
            detected, hints = self.detect_letter(results.pose_landmarks.landmark, self._target_pose)

        self.last_letters_queue.append(detected)
        if len(self.last_letters_queue) > self.buffer_size:
            self.last_letters_queue.pop(0)

        smoothed = max(set(self.last_letters_queue), key=self.last_letters_queue.count)
        self._current_letter = smoothed

        now = time.time()
        self._current_hints = hints
        self._update_hold_timer(smoothed, now)

        h, w, ch = rgb.shape
        self.video_provider.image = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888).copy()
        self.frameUpdated.emit()