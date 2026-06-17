
import cv2
import time
import random
import threading
import mediapipe as mp
from PySide6.QtCore import QObject, Signal, Slot, Property, QTimer
from PySide6.QtGui import QImage
from PySide6.QtQuick import QQuickImageProvider
from PySide6.QtMultimedia import QMediaDevices

from pose_rules import AVAILABLE_POSES, check_pose_rules, check_cam2_rules

HOLD_REQUIRED = 3.0
HOLD_TOLERANCE = 0.5
HINT_CYCLE_INTERVAL = 3.0
SUCCESS_ANNOUNCE_DELAY_MS = 1800

POSE_NAMES_PL = {
    "pies_z_glowa_w_dol": "Pies z głową w dół",
    "pozycja_dziecka": "Pozycja dziecka",
    "pozycja_drzewa": "Pozycja drzewa",
    "pozycja_gory": "Pozycja góry",
}


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
    stopRequested = Signal()

    def __init__(self, app_core, video_provider, video_provider2=None):
        super().__init__()
        self.app = app_core
        self.video_provider = video_provider
        self.video_provider2 = video_provider2

        self.timer = QTimer()
        self.timer.timeout.connect(self.process_frame)

        self.cap = None
        self.cap2 = None
        self.is_running = False

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

        self._current_hints = []
        self._voice_hints = []
        self._hint_timer_start = None

        self._voice_assistant = None
        self._last_hints = []
        self._hint_index = 0
        self._last_hint_time = 0.0
        self._tts_busy = False
        self._tts_lock = threading.Lock()

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

    @Property(bool, notify=frameUpdated)
    def dualCameraEnabled(self):
        return self._dual_camera_enabled

    @Property(int, notify=frameUpdated)
    def cameraIndex2(self):
        return self._camera_index_2

    @Property(list, notify=frameUpdated)
    def poseHints(self):
        return self._current_hints

    @Property(float, notify=frameUpdated)
    def holdProgress(self):
        return self._hold_progress

    @Property(bool, notify=frameUpdated)
    def isSuper(self):
        return time.time() < self._super_end_time

    @Slot(object)
    def setVoiceAssistant(self, assistant):
        self._voice_assistant = assistant

    @Slot(object)
    def set_voice_assistant(self, assistant):
        self.setVoiceAssistant(assistant)

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
        if cam_id == 1:
            self._rotation_state_1 = (self._rotation_state_1 + 1) % 4
        elif cam_id == 2:
            self._rotation_state_2 = (self._rotation_state_2 + 1) % 4

    @Slot()
    def nextPose(self):
        options = [p for p in AVAILABLE_POSES if p != self._target_pose]
        if options:
            self._target_pose = random.choice(options)

        self._hold_start = None
        self._lost_start = None
        self._hold_progress = 0.0
        self._current_hints = []
        self._voice_hints = []
        self._hint_timer_start = None
        self._last_hints = []
        self._hint_index = 0
        self._last_hint_time = time.time()
        self.frameUpdated.emit()

        if self._voice_assistant is not None:
            name = POSE_NAMES_PL.get(self._target_pose, self._target_pose)
            self._speak_async(f"Teraz wykonaj: {name}")

    @Slot()
    def voice_stop_training(self):
        if self.is_running:
            self.stopTraining()
            QTimer.singleShot(0, self.stopRequested.emit)

    def _pretty_pose_name(self, pose_key: str) -> str:
        return POSE_NAMES_PL.get(pose_key, pose_key)

    def _split_hint_list(self, hints):
        gui_hints = []
        voice_hints = []

        for item in hints or []:
            if isinstance(item, dict):
                voice = item.get("voice", "")
                gui = item.get("gui", voice)

            elif isinstance(item, (list, tuple)) and item:
                # Format: [voice, gui]
                voice = str(item[0])
                gui = str(item[1]) if len(item) > 1 and item[1] else voice

            else:
                voice = str(item)
                gui = str(item)

            if voice:
                voice_hints.append(voice)
            if gui:
                gui_hints.append(gui)

        return gui_hints, voice_hints

    def is_whole_body_visible(self, lm, target_pose):
        if target_pose == "pozycja_drzewa":
            critical_landmarks = [0, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28]
            for idx in critical_landmarks:
                if lm[idx].visibility < 0.5:
                    return False
            return True

        left_profile = [11, 13, 15, 23, 25, 27]
        right_profile = [12, 14, 16, 24, 26, 28]
        left_ok = all(lm[idx].visibility > 0.4 for idx in left_profile)
        right_ok = all(lm[idx].visibility > 0.4 for idx in right_profile)
        return left_ok or right_ok

    def _speak_async(self, text: str):
        if self._voice_assistant is None or not text:
            return

        with self._tts_lock:
            if self._tts_busy:
                return
            self._tts_busy = True

        def _run():
            try:
                self._voice_assistant.speak(text, "pl")
            except Exception as e:
                print("[TTS] Błąd:", e)
            finally:
                with self._tts_lock:
                    self._tts_busy = False

        threading.Thread(target=_run, daemon=True).start()

    def _maybe_speak_hint(self, voice_hints: list, now: float):
        if not voice_hints:
            self._last_hints = []
            self._hint_index = 0
            self._last_hint_time = now
            return

        if voice_hints != self._last_hints:
            self._last_hints = list(voice_hints)
            self._hint_index = 0
            self._last_hint_time = now
            return

        if now - self._last_hint_time < HINT_CYCLE_INTERVAL:
            return

        if self._tts_busy:
            return

        hint = voice_hints[self._hint_index % len(voice_hints)]
        self._speak_async(hint)
        self._hint_index = (self._hint_index + 1) % len(voice_hints)
        self._last_hint_time = now

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
            completed_pose = self._target_pose
            self.poseCompleted.emit(completed_pose)
            self._super_end_time = now + 2.0

            name = self._pretty_pose_name(completed_pose)
            self._speak_async(f"Super! {name} zaliczona!")

            options = [p for p in AVAILABLE_POSES if p != self._target_pose]
            if options:
                self._target_pose = random.choice(options)

            self._last_hints = []
            self._hint_index = 0
            self._last_hint_time = now + 2.5

            self._hold_start = None
            self._hold_progress = 0.0
            self._current_hints = []
            self._voice_hints = []
            self._hint_timer_start = None
            self.frameUpdated.emit()

            next_pose_name = self._pretty_pose_name(self._target_pose)
            QTimer.singleShot(
                SUCCESS_ANNOUNCE_DELAY_MS,
                lambda name=next_pose_name: self._speak_async(f"Teraz wykonaj: {name}")
            )

        return self._hold_progress

    def _detect_cam2(self, lm, target_pose):
        plain_hints = check_cam2_rules(target_pose, lm)
        return self._split_hint_list(plain_hints)

    def _draw_overlay_cam2(self, rgb, issues: list, target_pose: str):
        h, w = rgb.shape[:2]
        margin = 8
        check_label = {
            "pozycja_gory": "SPRAWDZA: NOGI",
            "pozycja_drzewa": "SPRAWDZA: PLECY",
        }.get(target_pose, "KAMERA 2")
        cv2.putText(rgb, check_label, (margin, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (140, 140, 255), 1, cv2.LINE_AA)

        if not issues:
            cv2.putText(rgb, "OK", (w // 2 - 20, h // 2), cv2.FONT_HERSHEY_DUPLEX, 1.6, (50, 230, 80), 3, cv2.LINE_AA)
        else:
            for i, msg in enumerate(issues):
                cv2.putText(rgb, f"! {msg}", (margin, 50 + i * 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 160, 40), 2, cv2.LINE_AA)

    @Slot()
    def startTraining(self):
        if self.is_running:
            return

        self.cap = cv2.VideoCapture(self._camera_index, cv2.CAP_DSHOW)
        if not self.cap or not self.cap.isOpened():
            self.cap = cv2.VideoCapture(self._camera_index)

        if self._dual_camera_enabled and self._camera_index_2 >= 0:
            self.cap2 = cv2.VideoCapture(self._camera_index_2, cv2.CAP_DSHOW)
            if not self.cap2 or not self.cap2.isOpened():
                self.cap2 = cv2.VideoCapture(self._camera_index_2)
        else:
            self.cap2 = None

        self.is_running = True
        self.last_letters_queue = []
        self._hold_start = None
        self._lost_start = None
        self._hold_progress = 0.0
        self._hint_timer_start = None
        self._current_hints = []
        self._voice_hints = []
        self._last_hints = []
        self._hint_index = 0
        self._last_hint_time = time.time() + 3.0
        self.timer.start(15)

        if self._voice_assistant is not None:
            name = POSE_NAMES_PL.get(self._target_pose, self._target_pose)
            self._speak_async(f"Trening rozpoczęty! Wykonaj: {name}")

        self.frameUpdated.emit()

    @Slot()
    def stopTraining(self):
        if not self.is_running:
            return

        self.is_running = False
        self.timer.stop()

        if self.cap:
            self.cap.release()
            self.cap = None

        if self.cap2:
            self.cap2.release()
            self.cap2 = None

        self._hint_timer_start = None
        self._current_hints = []
        self._voice_hints = []
        self.frameUpdated.emit()

    def process_frame(self):
        if not self.cap:
            return

        ret, frame = self.cap.read()
        if not ret:
            return

        frame = cv2.resize(frame, (640, 480))
        frame = cv2.flip(frame, 1)

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
        gui_cam2_hints = []
        voice_cam2_hints = []

        if self._dual_camera_enabled and self.cap2 and self.cap2.isOpened():
            ret2, frame2 = self.cap2.read()
            if ret2:
                frame2 = cv2.resize(frame2, (640, 480))
                frame2 = cv2.flip(frame2, 1)

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
                    gui_cam2_hints, voice_cam2_hints = self._detect_cam2(lm2, self._target_pose)
                    self._draw_overlay_cam2(rgb2, gui_cam2_hints, self._target_pose)
                else:
                    self._draw_overlay_cam2(rgb2, [], self._target_pose)

                if self.video_provider2 is not None:
                    h2, w2, ch2 = rgb2.shape
                    self.video_provider2.image = QImage(rgb2.data, w2, h2, ch2 * w2, QImage.Format_RGB888).copy()

        detected = "?"
        gui_hints = []
        voice_hints = []
        now = time.time()

        if lm1:
            self.mp_drawing.draw_landmarks(rgb, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS)

            if self.is_whole_body_visible(lm1, self._target_pose):
                actual_detected, actual_hints = check_pose_rules(
                    self._target_pose,
                    lm1,
                    lm2,
                    self._dual_camera_enabled
                )
                detected = actual_detected
                gui_actual_hints, voice_actual_hints = self._split_hint_list(actual_hints)

                if detected == self._target_pose:
                    self._hint_timer_start = None
                    gui_hints = []
                    voice_hints = []
                else:
                    if self._hint_timer_start is None:
                        self._hint_timer_start = now

                    if now - self._hint_timer_start >= 1.0:
                        gui_hints = gui_actual_hints
                        voice_hints = voice_actual_hints
                    else:
                        gui_hints = []
                        voice_hints = []
            else:
                detected = "?"
                gui_hints = ["Pokaz cale cialo w kadrze"]
                voice_hints = ["Pokaż całe ciało w kadrze"]
                self._hint_timer_start = None
        else:
            self._hint_timer_start = None

        self.last_letters_queue.append(detected)
        if len(self.last_letters_queue) > self.buffer_size:
            self.last_letters_queue.pop(0)

        smoothed = max(set(self.last_letters_queue), key=self.last_letters_queue.count)
        self._current_letter = smoothed

        # GUI should show the main pose hints; if there are no main hints,
        # allow camera-2-only hints to surface in the UI and TTS.
        if gui_hints:
            self._current_hints = gui_hints
            self._voice_hints = voice_hints
        elif gui_cam2_hints:
            self._current_hints = gui_cam2_hints
            self._voice_hints = voice_cam2_hints
        else:
            self._current_hints = []
            self._voice_hints = []

        self._update_hold_timer(smoothed, now)
        self._maybe_speak_hint(self._voice_hints, now)

        h, w, ch = rgb.shape
        self.video_provider.image = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888).copy()
        self.frameUpdated.emit()
