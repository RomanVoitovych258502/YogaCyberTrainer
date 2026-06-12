import cv2
import time
import os
import random
import mediapipe as mp
from PySide6.QtCore import QObject, Signal, Slot, Property, QTimer
from PySide6.QtGui import QImage
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtMultimedia import QMediaDevices

# Import z wydzielonego modułu reguł
from pose_rules import AVAILABLE_POSES, check_pose_rules, check_cam2_rules

HOLD_REQUIRED = 3.0
HOLD_TOLERANCE = 0.5


class VideoProvider(QQuickImageProvider):
    def __init__(self):
        super().__init__(QQuickImageProvider.Image)
        self.image = QImage()

    def requestImage(self, id, size, requestedSize):
        return self.image


class VideoProvider2(QQuickImageProvider):
    def __init__(self):
        super().__init__(QQuickImageProvider.Image)
        self.image = QImage()

    def requestImage(self, id, size, requestedSize):
        return self.image


class TrainingController(QObject):
    frameUpdated = Signal()
    poseCompleted = Signal(str)

    def __init__(self, app_core, video_provider, video_provider2):
        super().__init__()
        self.app = app_core
        self.video_provider = video_provider
        self.video_provider2 = video_provider2
        self.timer = QTimer()
        self.timer.timeout.connect(self.process_frame)
        self.cap = None
        self.cap2 = None
        self.is_running = False

        # --- Niezależny stan obrotu dla obu kamer ---
        self._rotation_state_1 = 0
        self._rotation_state_2 = 0

        self._camera_index = 0
        self._camera_index_2 = -1
        self._dual_camera_enabled = False

        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.pose = self.mp_pose.Pose(model_complexity=1)
        self.pose2 = self.mp_pose.Pose(model_complexity=0)

        self._current_letter = "?"
        self.buffer_size = 15
        self.last_letters_queue = []

        self._target_pose = random.choice(AVAILABLE_POSES)
        self._super_end_time = 0.0
        self._hold_start = None
        self._lost_start = None
        self._hold_progress = 0.0

        # --- MECHANIZM DELAYU ---
        self._hint_timer_start = None

        self._pose_images = {}
        for p in AVAILABLE_POSES:
            if os.path.exists(f"{p}.jpg"):
                self._pose_images[p] = cv2.imread(f"{p}.jpg")
            elif os.path.exists(f"{p}.png"):
                self._pose_images[p] = cv2.imread(f"{p}.png")
            else:
                self._pose_images[p] = None

    @Property(str, notify=frameUpdated)
    def currentLetter(self):
        return self._target_pose

    @Property(list, notify=frameUpdated)
    def cameraNames(self):
        devices = QMediaDevices.videoInputs()
        if not devices: return ["Brak dostępnych kamer"]
        return [dev.description() for dev in devices]

    @Property(bool, notify=frameUpdated)
    def isRunning(self):
        return self.is_running

    @Property(bool, notify=frameUpdated)
    def dualCameraEnabled(self):
        return self._dual_camera_enabled

    @Property(int, notify=frameUpdated)
    def cameraIndex2(self):
        return self._camera_index_2

    @Slot(int)
    def setCameraIndex(self, index):
        if self._camera_index != index:
            self._camera_index = index
            if self.is_running:
                self.stopTraining()
                self.startTraining()

    @Slot(int)
    def setCameraIndex2(self, index):
        if self._camera_index_2 != index:
            self._camera_index_2 = index
            self._dual_camera_enabled = (index >= 0)
            if self.is_running:
                if self.cap2:
                    self.cap2.release()
                    self.cap2 = None
                if self._dual_camera_enabled:
                    self.cap2 = cv2.VideoCapture(self._camera_index_2, cv2.CAP_DSHOW)
                    if not self.cap2 or not self.cap2.isOpened():
                        self.cap2 = cv2.VideoCapture(self._camera_index_2)
            self.frameUpdated.emit()

    @Slot(bool)
    def setDualCameraEnabled(self, enabled):
        if self._dual_camera_enabled != enabled:
            self._dual_camera_enabled = enabled
            if self.is_running:
                if enabled and self._camera_index_2 >= 0:
                    if self.cap2 is None:
                        self.cap2 = cv2.VideoCapture(self._camera_index_2, cv2.CAP_DSHOW)
                        if not self.cap2 or not self.cap2.isOpened():
                            self.cap2 = cv2.VideoCapture(self._camera_index_2)
                else:
                    if self.cap2:
                        self.cap2.release()
                        self.cap2 = None
            self.frameUpdated.emit()

    @Slot(int)
    def rotateCamera(self, cam_id):
        """Obraca wybraną kamerę (1 lub 2)"""
        if cam_id == 1:
            self._rotation_state_1 = (self._rotation_state_1 + 1) % 4
        elif cam_id == 2:
            self._rotation_state_2 = (self._rotation_state_2 + 1) % 4

    def is_whole_body_visible(self, lm, target_pose):
        """
        Sprawdza widoczność sylwetki uwzględniając, czy pozycja jest wykonywana
        przodem (wymaga obu stron ciała) czy bokiem (wymaga tylko jednego profilu).
        """
        if target_pose == "pozycja_drzewa":
            # PRZODEM: Wymagamy widoczności lewej i prawej strony ciała
            critical_landmarks = [0, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28]
            for idx in critical_landmarks:
                if lm[idx].visibility < 0.5:
                    return False
            return True
        else:
            # BOKIEM (Góra, Pies, Dziecko): Jedna strona zasłania drugą.
            # Wystarczy, że widzimy wyraźnie przynajmniej jeden cały profil (lewy ALBO prawy).
            left_profile = [11, 13, 15, 23, 25, 27]  # Bark, łokieć, nadgarstek, biodro, kolano, kostka lewa
            right_profile = [12, 14, 16, 24, 26, 28]  # Bark, łokieć, nadgarstek, biodro, kolano, kostka prawa

            left_ok = all(lm[idx].visibility > 0.4 for idx in left_profile)
            right_ok = all(lm[idx].visibility > 0.4 for idx in right_profile)

            return left_ok or right_ok

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
            self._target_pose = random.choice(options)
            self._hold_start = None
            self._hold_progress = 0.0

        return self._hold_progress

    def _draw_overlay(self, rgb, hints: list, progress: float, now: float):
        h, w = rgb.shape[:2]
        img_size = 120
        margin = 15

        target_img = self._pose_images.get(self._target_pose)
        if target_img is not None:
            resized_img = cv2.resize(target_img, (img_size, img_size))
            resized_rgb = cv2.cvtColor(resized_img, cv2.COLOR_BGR2RGB)
            rgb[margin:margin + img_size, margin:margin + img_size] = resized_rgb
            cv2.rectangle(rgb, (margin, margin), (margin + img_size, margin + img_size), (0, 255, 0), 2)
        else:
            cv2.rectangle(rgb, (margin, margin), (margin + img_size, margin + img_size), (30, 30, 30), -1)
            cv2.rectangle(rgb, (margin, margin), (margin + img_size, margin + img_size), (255, 255, 255), 1)

        hints_start_y = margin + img_size + 30
        for i, hint in enumerate(hints):
            y = hints_start_y + i * 35
            text_color = (255, 50, 50) if "Pokaz cale cialo" in hint else (0, 255, 0)
            cv2.putText(rgb, f"! {hint}", (margin + 2, y + 2), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(rgb, f"! {hint}", (margin, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, text_color, 2, cv2.LINE_AA)

        bar_h = 18
        bar_margin = 20
        bar_y = h - bar_margin - bar_h
        bar_w = w - 2 * bar_margin

        cv2.rectangle(rgb, (bar_margin, bar_y), (bar_margin + bar_w, bar_y + bar_h), (50, 50, 50), -1)
        if progress > 0:
            fill_color = (80, 200, 80) if progress < 1.0 else (50, 220, 50)
            cv2.rectangle(rgb, (bar_margin, bar_y), (bar_margin + int(bar_w * progress), bar_y + bar_h), fill_color, -1)
        cv2.rectangle(rgb, (bar_margin, bar_y), (bar_margin + bar_w, bar_y + bar_h), (180, 180, 180), 1)

        label = f"Trzymaj: {min(int(progress * HOLD_REQUIRED) + 1, int(HOLD_REQUIRED))}/{int(HOLD_REQUIRED)}s"
        cv2.putText(rgb, label, (bar_margin + 6, bar_y + bar_h - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1,
                    cv2.LINE_AA)

        if now < self._super_end_time:
            text = "SUPER!"
            font = cv2.FONT_HERSHEY_DUPLEX
            text_size = cv2.getTextSize(text, font, 3.0, 6)[0]
            cv2.putText(rgb, text, ((w - text_size[0]) // 2 + 5, (h + text_size[1]) // 2 + 5), font, 3.0, (0, 0, 0), 9,
                        cv2.LINE_AA)
            cv2.putText(rgb, text, ((w - text_size[0]) // 2, (h + text_size[1]) // 2), font, 3.0, (50, 255, 50), 6,
                        cv2.LINE_AA)

    def _detect_cam2(self, lm, target_pose):
        """Wrapper na potrzeby overlay'u kamery 2."""
        plain_hints = check_cam2_rules(target_pose, lm)
        color_map = {
            "Zlacz stopy": (255, 80, 80),
            "Zlacz kolana": (255, 80, 80),
            "Wyprostuj plecy": (255, 160, 40),
            "Wyprostuj glowe": (255, 160, 40),
        }
        return [(msg, color_map.get(msg, (255, 160, 40))) for msg in plain_hints]

    def _draw_overlay_cam2(self, rgb, issues: list, target_pose: str):
        h, w = rgb.shape[:2]
        margin = 8
        check_label = {"pozycja_gory": "SPRAWDZA: NOGI", "pozycja_drzewa": "SPRAWDZA: PLECY"}.get(target_pose,
                                                                                                  "KAMERA 2")
        cv2.putText(rgb, check_label, (margin, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (140, 140, 255), 1, cv2.LINE_AA)

        if not issues:
            cv2.putText(rgb, "OK", (w // 2 - 20, h // 2), cv2.FONT_HERSHEY_DUPLEX, 1.6, (50, 230, 80), 3, cv2.LINE_AA)
        else:
            for i, (msg, color) in enumerate(issues):
                cv2.putText(rgb, f"! {msg}", (margin, 50 + i * 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2,
                            cv2.LINE_AA)

    @Slot()
    def startTraining(self):
        if not self.is_running:
            self.cap = cv2.VideoCapture(self._camera_index, cv2.CAP_DSHOW)
            if not self.cap or not self.cap.isOpened(): self.cap = cv2.VideoCapture(self._camera_index)
            if self._dual_camera_enabled and self._camera_index_2 >= 0:
                self.cap2 = cv2.VideoCapture(self._camera_index_2, cv2.CAP_DSHOW)
                if not self.cap2 or not self.cap2.isOpened(): self.cap2 = cv2.VideoCapture(self._camera_index_2)

            self.is_running = True
            self.last_letters_queue = []
            self._hold_start = None
            self._lost_start = None
            self._hold_progress = 0.0
            self._hint_timer_start = None
            self.timer.start(15)

    @Slot()
    def stopTraining(self):
        if self.is_running:
            self.is_running = False
            self.timer.stop()
            if self.cap: self.cap.release(); self.cap = None
            if self.cap2: self.cap2.release(); self.cap2 = None
            self._hint_timer_start = None
            self.frameUpdated.emit()

    def process_frame(self):
        if not self.cap: return
        ret, frame = self.cap.read()
        if not ret: return

        frame = cv2.resize(frame, (640, 480))
        frame = cv2.flip(frame, 1)

        # Obracanie kamery głównej
        if self._rotation_state_1 == 1:
            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        elif self._rotation_state_1 == 2:
            frame = cv2.rotate(frame, cv2.ROTATE_180)
        elif self._rotation_state_1 == 3:
            frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb)

        lm1 = results.pose_landmarks.landmark if results.pose_landmarks else None
        lm2 = None

        if self._dual_camera_enabled and self.cap2 and self.cap2.isOpened():
            ret2, frame2 = self.cap2.read()
            if ret2:
                frame2 = cv2.resize(frame2, (640, 480))
                frame2 = cv2.flip(frame2, 1)

                # Obracanie kamery bocznej
                if self._rotation_state_2 == 1:
                    frame2 = cv2.rotate(frame2, cv2.ROTATE_90_CLOCKWISE)
                elif self._rotation_state_2 == 2:
                    frame2 = cv2.rotate(frame2, cv2.ROTATE_180)
                elif self._rotation_state_2 == 3:
                    frame2 = cv2.rotate(frame2, cv2.ROTATE_90_COUNTERCLOCKWISE)

                rgb2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2RGB)
                results2 = self.pose2.process(rgb2)
                if results2.pose_landmarks:
                    lm2 = results2.pose_landmarks.landmark
                    self.mp_drawing.draw_landmarks(rgb2, results2.pose_landmarks, self.mp_pose.POSE_CONNECTIONS)
                    issues = self._detect_cam2(lm2, self._target_pose)
                    self._draw_overlay_cam2(rgb2, issues, self._target_pose)
                else:
                    self._draw_overlay_cam2(rgb2, [], self._target_pose)
                h2, w2, ch2 = rgb2.shape
                self.video_provider2.image = QImage(rgb2.data, w2, h2, ch2 * w2, QImage.Format_RGB888).copy()

        detected = "?"
        hints = []
        now = time.time()

        if lm1:
            self.mp_drawing.draw_landmarks(rgb, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS)

            # SPRAWDZENIE CZY CIAŁO JEST W KADRZE (Z UWZGLĘDNIENIEM POZYCJI)
            if self.is_whole_body_visible(lm1, self._target_pose):

                # Przekazujemy do pose_rules
                actual_detected, actual_hints = check_pose_rules(
                    self._target_pose,
                    lm1,
                    lm2,
                    self._dual_camera_enabled
                )
                detected = actual_detected

                if detected == self._target_pose:
                    self._hint_timer_start = None
                    hints = []
                else:
                    # DELAY 1 SEKUNDY
                    if self._hint_timer_start is None:
                        self._hint_timer_start = now

                    if now - self._hint_timer_start >= 1.0:
                        hints = actual_hints
                    else:
                        hints = []
            else:
                # CIAŁO NIE W KADRZE - NATYCHMIASTOWY KOMUNIKAT
                detected = "?"
                hints = ["Pokaz cale cialo w kadrze"]
                self._hint_timer_start = None
        else:
            self._hint_timer_start = None

        self.last_letters_queue.append(detected)
        if len(self.last_letters_queue) > self.buffer_size: self.last_letters_queue.pop(0)
        smoothed = max(set(self.last_letters_queue), key=self.last_letters_queue.count)
        self._current_letter = smoothed

        progress = self._update_hold_timer(smoothed, now)
        self._draw_overlay(rgb, hints, progress, now)

        h, w, ch = rgb.shape
        self.video_provider.image = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888).copy()
        self.frameUpdated.emit()