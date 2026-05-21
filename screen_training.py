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

        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.pose = self.mp_pose.Pose(model_complexity=1)

        self._current_letter = "?"
        self.buffer_size = 15
        self.last_letters_queue = []

    @Property(str, notify=frameUpdated)
    def currentLetter(self):
        return self._current_letter

    @Slot()
    def rotateCamera(self):
        self._rotation_state = (self._rotation_state + 1) % 4

    def calculate_angle(self, a, b, c):
        ang = math.degrees(math.atan2(c.y - b.y, c.x - b.x) - math.atan2(a.y - b.y, a.x - b.x))
        return abs(ang) if abs(ang) <= 180 else 360 - abs(ang)

    def detect_letter(self, lm):
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

        is_downdog = (l_hip_ang < 120 and r_hip_ang < 120) and \
                     (l_knee_ang > 140 and r_knee_ang > 140) and \
                     (l_elbow_ang > 140 and r_elbow_ang > 140) and \
                     (mean_hip_y < mean_sh_y) and \
                     (mean_wrist_y > mean_sh_y)

        hip_ank_dist = abs(mean_hip_y - mean_ank_y)
        butt_on_heels = hip_ank_dist < 0.08
        arms_stretched = (l_sh_ang > 145 and r_sh_ang > 145) and (l_elbow_ang > 130 and r_elbow_ang > 130)
        torso_low = (mean_sh_y > mean_hip_y - 0.05)

        is_childs = (l_knee_ang < 80 and r_knee_ang < 80) and butt_on_heels and arms_stretched and torso_low

        tree_l = (l_knee_ang < 110 and r_knee_ang > 150) and (lm[self.L_ANKLE].y < lm[self.R_KNEE].y + 0.05)
        tree_r = (r_knee_ang < 110 and l_knee_ang > 150) and (lm[self.R_ANKLE].y < lm[self.L_KNEE].y + 0.05)

        hands_above_tree = (mean_wrist_y < nose_y)
        wrists_together_tree = abs(lm[self.L_WRIST].x - lm[self.R_WRIST].x) < 0.15
        elbows_bent = (l_elbow_ang < 155 and r_elbow_ang < 155)
        elbows_wide = abs(lm[self.L_ELBOW].x - lm[self.R_ELBOW].x) > abs(lm[self.L_SHOULDER].x - lm[self.R_SHOULDER].x)

        is_tree = (tree_l or tree_r) and hands_above_tree and wrists_together_tree and elbows_bent and elbows_wide

        legs_straight = (l_knee_ang > 145 and r_knee_ang > 145) and (l_hip_ang > 140 and r_hip_ang > 140)
        feet_together = abs(lm[self.L_ANKLE].x - lm[self.R_ANKLE].x) < 0.18
        hands_above_head = (mean_wrist_y < nose_y)

        arms_behind_head = abs(mean_wrist_x - nose_x) > 0.08
        torso_arched = abs(mean_sh_x - mean_hip_x) > 0.05

        is_mountain = legs_straight and feet_together and hands_above_head and arms_behind_head and torso_arched

        if is_downdog: return "Pies z glowa w dol"
        if is_childs: return "Pozycja dziecka"
        if is_tree: return "Pozycja drzewa"
        if is_mountain: return "Pozycja gory"

        return "?"

    @Slot()
    def startTraining(self):
        if not self.is_running:
            self.cap = cv2.VideoCapture(0)
            self.is_running = True
            self.last_letters_queue = []
            self.timer.start(15)

    @Slot()
    def stopTraining(self):
        if self.is_running:
            self.is_running = False
            self.timer.stop()
            if self.cap:
                self.cap.release()
                self.cap = None

    def process_frame(self):
        if not self.cap: return
        ret, frame = self.cap.read()
        if ret:
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

            if results.pose_landmarks:
                self.mp_drawing.draw_landmarks(rgb, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS)
                detected = self.detect_letter(results.pose_landmarks.landmark)

            self.last_letters_queue.append(detected)
            if len(self.last_letters_queue) > self.buffer_size:
                self.last_letters_queue.pop(0)

            if self.last_letters_queue:
                self._current_letter = max(set(self.last_letters_queue), key=self.last_letters_queue.count)

            h, w, ch = rgb.shape
            self.video_provider.image = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888).copy()
            self.frameUpdated.emit()