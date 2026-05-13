import cv2
import mediapipe as mp
from PySide6.QtCore import QObject, Signal, Slot, QTimer
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

    def __init__(self, video_provider):
        super().__init__()
        self.video_provider = video_provider
        self.timer = QTimer()
        self.timer.timeout.connect(self.process_frame)
        self.cap = None
        self.is_running = False

        self.mp_pose = mp.solutions.pose
        self.mp_drawing = mp.solutions.drawing_utils
        self.pose = self.mp_pose.Pose(model_complexity=0)

    @Slot()
    def startTraining(self):
        if not self.is_running:
            self.cap = cv2.VideoCapture(0)
            self.is_running = True
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
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            results = self.pose.process(rgb)

            if results.pose_landmarks:
                self.mp_drawing.draw_landmarks(rgb, results.pose_landmarks, self.mp_pose.POSE_CONNECTIONS)

            h, w, ch = rgb.shape
            self.video_provider.image = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888).copy()
            self.frameUpdated.emit()