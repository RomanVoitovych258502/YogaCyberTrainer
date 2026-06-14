import warnings
import cv2
import time
import math
import os
import random
import threading
import mediapipe as mp
from PySide6.QtCore import QObject, Signal, Slot, Property, QTimer
from PySide6.QtGui import QImage
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtMultimedia import QMediaDevices

HOLD_REQUIRED = 1.0
HOLD_TOLERANCE = 0.2

# Hint cycle interval in seconds — how often the TTS reads out the next hint
HINT_CYCLE_INTERVAL = 1.0

AVAILABLE_POSES = [
    "pies_z_glowa_w_dol",
    "pozycja_dziecka",
    "pozycja_drzewa",
    "pozycja_gory"
]

# Human-readable Polish names for TTS announcements
POSE_NAMES_PL = {
    "pies_z_glowa_w_dol": "Pies z głową w dół",
    "pozycja_dziecka":    "Pozycja dziecka",
    "pozycja_drzewa":     "Pozycja drzewa",
    "pozycja_gory":       "Pozycja góry",
}


class VideoProvider(QQuickImageProvider):
    def __init__(self):
        super().__init__(QQuickImageProvider.Image)
        self.image = QImage()

    def requestImage(self, id, size, requestedSize):
        return self.image


class TrainingController(QObject):
    frameUpdated   = Signal()
    poseCompleted  = Signal(str)
    # Emitted when the training should stop (e.g. voice command "stop")
    stopRequested  = Signal()

    NOSE = 0
    L_SHOULDER, R_SHOULDER = 11, 12
    L_ELBOW,    R_ELBOW    = 13, 14
    L_WRIST,    R_WRIST    = 15, 16
    L_HIP,      R_HIP      = 23, 24
    L_KNEE,     R_KNEE     = 25, 26
    L_ANKLE,    R_ANKLE    = 27, 28

    def __init__(self, app_core, video_provider):
        super().__init__()
        self.app            = app_core
        self.video_provider = video_provider
        self.timer          = QTimer()
        self.timer.timeout.connect(self.process_frame)
        self.cap            = None
        self.is_running     = False
        self._rotation_state = 0
        self._camera_index  = 0

        # Will be set by main.py after VoiceAssistant is created
        self._voice_assistant = None

        self.mp_pose    = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.pose       = self.mp_pose.Pose(model_complexity=1)

        self._current_letter   = "?"
        self.buffer_size       = 15
        self.last_letters_queue = []

        # Gamification / hold logic
        self._target_pose    = random.choice(AVAILABLE_POSES)
        self._super_end_time = 0.0
        self._hold_start     = None
        self._lost_start     = None
        self._hold_progress  = 0.0

        # ── Audio hint cycle ─────────────────────────────────────────────────
        # Keep track of which hint index to read next, and when it was last spoken
        self._last_hints:       list  = []
        self._hint_index:       int   = 0
        self._last_hint_time:   float = 0.0
        self._hint_thread:      threading.Thread | None = None
        self._tts_busy:         bool  = False   # prevent overlapping TTS calls

        # Load reference images
        self._pose_images = {}
        for p in AVAILABLE_POSES:
            if os.path.exists(f"{p}.jpg"):
                self._pose_images[p] = cv2.imread(f"{p}.jpg")
            elif os.path.exists(f"{p}.png"):
                self._pose_images[p] = cv2.imread(f"{p}.png")
            else:
                self._pose_images[p] = None

    # ── Public API ────────────────────────────────────────────────────────────

    def set_voice_assistant(self, va):
        """Called by main.py to give training controller a reference to TTS."""
        self._voice_assistant = va

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

    # ── Voice-command entry point ─────────────────────────────────────────────

    def voice_stop_training(self):
        """Called by VoiceAssistant when the stop-word is detected."""
        if self.is_running:
            self.stopTraining()
            # Emit on the Qt thread via a zero-delay timer
            QTimer.singleShot(0, self.stopRequested.emit)

    # ── Geometry helpers ──────────────────────────────────────────────────────

    def calculate_angle(self, a, b, c):
        ang = math.degrees(
            math.atan2(c.y - b.y, c.x - b.x) -
            math.atan2(a.y - b.y, a.x - b.x)
        )
        return abs(ang) if abs(ang) <= 180 else 360 - abs(ang)

    def detect_letter(self, lm, target_pose):
        l_hip_ang   = self.calculate_angle(lm[self.L_SHOULDER], lm[self.L_HIP],   lm[self.L_KNEE])
        r_hip_ang   = self.calculate_angle(lm[self.R_SHOULDER], lm[self.R_HIP],   lm[self.R_KNEE])
        l_knee_ang  = self.calculate_angle(lm[self.L_HIP],      lm[self.L_KNEE],  lm[self.L_ANKLE])
        r_knee_ang  = self.calculate_angle(lm[self.R_HIP],      lm[self.R_KNEE],  lm[self.R_ANKLE])
        l_elbow_ang = self.calculate_angle(lm[self.L_SHOULDER], lm[self.L_ELBOW], lm[self.L_WRIST])
        r_elbow_ang = self.calculate_angle(lm[self.R_SHOULDER], lm[self.R_ELBOW], lm[self.R_WRIST])
        l_sh_ang    = self.calculate_angle(lm[self.L_HIP],      lm[self.L_SHOULDER], lm[self.L_WRIST])
        r_sh_ang    = self.calculate_angle(lm[self.R_HIP],      lm[self.R_SHOULDER], lm[self.R_WRIST])

        mean_hip_y   = (lm[self.L_HIP].y    + lm[self.R_HIP].y)    / 2
        mean_sh_y    = (lm[self.L_SHOULDER].y + lm[self.R_SHOULDER].y) / 2
        mean_ank_y   = (lm[self.L_ANKLE].y   + lm[self.R_ANKLE].y)   / 2
        mean_wrist_y = (lm[self.L_WRIST].y   + lm[self.R_WRIST].y)   / 2
        mean_wrist_x = (lm[self.L_WRIST].x   + lm[self.R_WRIST].x)   / 2
        mean_sh_x    = (lm[self.L_SHOULDER].x + lm[self.R_SHOULDER].x) / 2
        mean_hip_x   = (lm[self.L_HIP].x     + lm[self.R_HIP].x)     / 2
        nose_y       = lm[self.NOSE].y
        nose_x       = lm[self.NOSE].x

        # 1. PIES Z GŁOWĄ W DÓŁ
        hints_downdog = []

        if not (l_hip_ang < 120 and r_hip_ang < 120):
            hints_downdog.append(["Ugnij mocniej biodra", "Ugnij mocniej biodra"])

        if not (l_knee_ang > 140 and r_knee_ang > 140):
            hints_downdog.append(["Wyprostuj kolana", "Wyprostuj kolana"])

        if not (l_elbow_ang > 140 and r_elbow_ang > 140):
            hints_downdog.append(["Wyprostuj łokcie", "Wyprostuj lokcie"])

        if not (mean_hip_y < mean_sh_y):
            hints_downdog.append(["Unieś biodra wyżej", "Unies biodra wyzej"])

        if not (mean_wrist_y > mean_sh_y):
            hints_downdog.append(["Oprzyj dłonie", "Oprzyj dlonie"])

        # 2. POZYCJA DZIECKA
        hints_childs = []

        if not (l_knee_ang < 80 and r_knee_ang < 80):
            hints_childs.append(["Ugnij kolana bardziej", "Ugnij kolana bardziej"])

        if not (abs(mean_hip_y - mean_ank_y) < 0.10):
            hints_childs.append(["Oprzyj biodra na piętach", "Oprzyj biodra na pietach"])

        if not ((l_sh_ang > 145 and r_sh_ang > 145) and (l_elbow_ang > 130 and r_elbow_ang > 130)):
            hints_childs.append(["Wyciągnij ręce do przodu", "Wyciagnij rece do przodu"])

        if not (mean_sh_y > mean_hip_y - 0.05):
            hints_childs.append(["Opuść tors niżej", "Opusc tors nizej"])

        # 3. POZYCJA DRZEWA
        hints_tree = []

        tree_l = (l_knee_ang < 110 and r_knee_ang > 150) and (lm[self.L_ANKLE].y < lm[self.R_KNEE].y + 0.05)
        tree_r = (r_knee_ang < 110 and l_knee_ang > 150) and (lm[self.R_ANKLE].y < lm[self.L_KNEE].y + 0.05)

        if not (tree_l or tree_r):
            hints_tree.append(["Postaw stopę na łydce", "Postaw stope na lydce"])

        if not (mean_wrist_y < nose_y):
            hints_tree.append(["Unieś dłonie nad głowę", "Unies dlonie nad glowe"])

        if not (abs(lm[self.L_WRIST].x - lm[self.R_WRIST].x) < 0.15):
            hints_tree.append(["Złącz dłonie razem", "Zlacz dlonie razem"])

        if not (l_elbow_ang < 155 and r_elbow_ang < 155):
            hints_tree.append(["Ugnij lekko łokcie", "Ugnij lekko lokcie"])

        if not (abs(lm[self.L_ELBOW].x - lm[self.R_ELBOW].x) > abs(lm[self.L_SHOULDER].x - lm[self.R_SHOULDER].x)):
            hints_tree.append(["Rozstaw łokcie szerzej", "Rozstaw lokcie szerzej"])

        # 4. POZYCJA GÓRY
        hints_mountain = []

        if not ((l_knee_ang > 145 and r_knee_ang > 145) and (l_hip_ang > 140 and r_hip_ang > 140)):
            hints_mountain.append(["Wyprostuj nogi i biodra", "Wyprostuj nogi i biodra"])

        if not (abs(lm[self.L_ANKLE].x - lm[self.R_ANKLE].x) < 0.18):
            hints_mountain.append(["Złącz stopy razem", "Zlacz stopy razem"])

        if not (mean_wrist_y < nose_y):
            hints_mountain.append(["Unieś ręce", "Unies rece"])

        if not (abs(mean_wrist_x - nose_x) > 0.08):
            hints_mountain.append(["Odchyl ręce do tyłu", "Odchyl rece do tylu"])

        if not (abs(mean_sh_x - mean_hip_x) > 0.05):
            hints_mountain.append(["Wygnij lekko plecy", "Wygnij lekko plecy"])

        all_hints = {
            "pies_z_glowa_w_dol": hints_downdog,
            "pozycja_dziecka":    hints_childs,
            "pozycja_drzewa":     hints_tree,
            "pozycja_gory":       hints_mountain,
        }

        target_hints = all_hints.get(target_pose, [])
        if len(target_hints) == 0:
            return target_pose, []
        return "?", target_hints

    # ── Audio hint cycle ──────────────────────────────────────────────────────

    def _speak_async(self, text: str):
        """Speak text in a background thread so the frame loop never blocks."""
        if self._voice_assistant is None or self._tts_busy:
            return

        def _run():
            self._tts_busy = True
            try:
                self._voice_assistant.speak(text, "pl")
            finally:
                self._tts_busy = False

        t = threading.Thread(target=_run, daemon=True)
        t.start()

    def _maybe_speak_hint(self, hints: list, now: float):
        """
        Called every frame.  Every HINT_CYCLE_INTERVAL seconds it picks the
        next hint (round-robin) and reads it aloud.  When hints change
        completely (new pose or new set) the index resets.
        """
        if not hints:
            # No hints means pose is correct — reset cycle
            self._last_hints   = []
            self._hint_index   = 0
            self._last_hint_time = now
            return

        # If the hint list changed, restart from beginning
        if hints != self._last_hints:
            self._last_hints = hints
            self._hint_index = 0
            self._last_hint_time = now  # don't speak immediately on first frame
            return

        if now - self._last_hint_time >= HINT_CYCLE_INTERVAL and not self._tts_busy:
            hint_text = hints[self._hint_index % len(hints)][0]
            self._speak_async(hint_text)
            self._hint_index     = (self._hint_index + 1) % len(hints)
            self._last_hint_time = now

    # ── Hold-timer logic ──────────────────────────────────────────────────────

    def _update_hold_timer(self, smoothed_pose: str, now: float):
        if smoothed_pose != self._target_pose:
            if self._lost_start is None:
                self._lost_start = now
            elif now - self._lost_start > HOLD_TOLERANCE:
                self._hold_start    = None
                self._lost_start    = None
                self._hold_progress = 0.0
            return self._hold_progress

        self._lost_start = None

        if self._hold_start is None:
            self._hold_start    = now
            self._hold_progress = 0.0
            return 0.0

        elapsed             = now - self._hold_start
        self._hold_progress = min(elapsed / HOLD_REQUIRED, 1.0)

        if self._hold_progress >= 1.0:
            completed_pose = self._target_pose
            self.poseCompleted.emit(completed_pose)
            self._super_end_time = now + 2.0

            # Announce success
            name = POSE_NAMES_PL.get(completed_pose, completed_pose)
            self._speak_async(f"Super! {name} zaliczona!")

            options            = [p for p in AVAILABLE_POSES if p != self._target_pose]
            self._target_pose  = random.choice(options)

            # Announce new target after a short delay (happens via next hint cycle)
            self._last_hints      = []
            self._hint_index      = 0
            self._last_hint_time  = now + 2.5  # give 2.5 s before first hint

            self._hold_start    = None
            self._hold_progress = 0.0

        return self._hold_progress

    # ── Overlay drawing ───────────────────────────────────────────────────────

    def _draw_overlay(self, rgb, hints: list, progress: float, now: float):
        h, w = rgb.shape[:2]

        img_size = 120
        margin   = 15

        target_img = self._pose_images.get(self._target_pose)
        if target_img is not None:
            resized_img = cv2.resize(target_img, (img_size, img_size))
            resized_rgb = cv2.cvtColor(resized_img, cv2.COLOR_BGR2RGB)
            rgb[margin:margin + img_size, margin:margin + img_size] = resized_rgb
            cv2.rectangle(rgb, (margin, margin), (margin + img_size, margin + img_size), (0, 255, 0), 2)
        else:
            cv2.rectangle(rgb, (margin, margin), (margin + img_size, margin + img_size), (30, 30, 30), -1)
            cv2.rectangle(rgb, (margin, margin), (margin + img_size, margin + img_size), (255, 255, 255), 1)
            cv2.putText(rgb, "BRAK ZDJ", (margin + 15, margin + 65),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        hints_start_y = margin + img_size + 30
        for i, hint in enumerate(hints):
            y = hints_start_y + i * 35
            cv2.putText(rgb, f"! {hint[1]}", (margin + 2, y + 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(rgb, f"! {hint[1]}", (margin, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2, cv2.LINE_AA)

        bar_h      = 18
        bar_margin = 20
        bar_y      = h - bar_margin - bar_h
        bar_w      = w - 2 * bar_margin

        cv2.rectangle(rgb, (bar_margin, bar_y), (bar_margin + bar_w, bar_y + bar_h), (50, 50, 50), -1)
        if progress > 0:
            fill_color = (80, 200, 80) if progress < 1.0 else (50, 220, 50)
            cv2.rectangle(rgb, (bar_margin, bar_y),
                          (bar_margin + int(bar_w * progress), bar_y + bar_h), fill_color, -1)
        cv2.rectangle(rgb, (bar_margin, bar_y), (bar_margin + bar_w, bar_y + bar_h), (180, 180, 180), 1)

        label = f"Trzymaj: {min(int(progress * HOLD_REQUIRED) + 1, int(HOLD_REQUIRED))}/{int(HOLD_REQUIRED)}s"
        cv2.putText(rgb, label, (bar_margin + 6, bar_y + bar_h - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

        if now < self._super_end_time:
            text        = "SUPER!"
            font        = cv2.FONT_HERSHEY_DUPLEX
            font_scale  = 3.0
            thickness   = 6
            text_size   = cv2.getTextSize(text, font, font_scale, thickness)[0]
            text_x      = (w - text_size[0]) // 2
            text_y      = (h + text_size[1]) // 2
            cv2.putText(rgb, text, (text_x + 5, text_y + 5), font, font_scale, (0, 0, 0),    thickness + 3, cv2.LINE_AA)
            cv2.putText(rgb, text, (text_x,     text_y),     font, font_scale, (50, 255, 50), thickness,     cv2.LINE_AA)

    # ── Qt slots ──────────────────────────────────────────────────────────────

    @Slot()
    def startTraining(self):
        if not self.is_running:
            print("[Voice] START")
            self.cap = cv2.VideoCapture(self._camera_index, cv2.CAP_DSHOW)
            if not self.cap or not self.cap.isOpened():
                self.cap = cv2.VideoCapture(self._camera_index)

            self.is_running          = True
            self.last_letters_queue  = []
            self._hold_start         = None
            self._lost_start         = None
            self._hold_progress      = 0.0
            self._last_hints         = []
            self._hint_index         = 0
            self._last_hint_time     = time.time() + 3.0  # 3 s grace before first hint

            # Announce the first target pose
            name = POSE_NAMES_PL.get(self._target_pose, self._target_pose)
            self._speak_async(f"Trening rozpoczęty! Wykonaj: {name}")

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
        if not self.cap:
            return
        ret, frame = self.cap.read()
        if not ret:
            return

        frame = cv2.resize(frame, (640, 480))
        frame = cv2.flip(frame, 1)

        if self._rotation_state == 1:
            frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
        elif self._rotation_state == 2:
            frame = cv2.rotate(frame, cv2.ROTATE_180)
        elif self._rotation_state == 3:
            frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)

        rgb     = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(rgb)

        detected = "?"
        hints    = []

        if results.pose_landmarks:
            self.mp_drawing.draw_landmarks(rgb, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS)
            detected, hints = self.detect_letter(results.pose_landmarks.landmark, self._target_pose)

        self.last_letters_queue.append(detected)
        if len(self.last_letters_queue) > self.buffer_size:
            self.last_letters_queue.pop(0)
        smoothed          = max(set(self.last_letters_queue), key=self.last_letters_queue.count)
        self._current_letter = smoothed

        now      = time.time()
        progress = self._update_hold_timer(smoothed, now)
        self._maybe_speak_hint(hints, now)
        self._draw_overlay(rgb, hints, progress, now)

        h, w, ch = rgb.shape
        self.video_provider.image = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888).copy()
        self.frameUpdated.emit()