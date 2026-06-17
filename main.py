
import os
import sys
from PySide6.QtCore import QObject, Signal, Property, Slot, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from screen_training import TrainingController, VideoProvider, VideoProvider2
from VoiceAPI import VoiceAssistant

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


class AppCore(QObject):
    navRequested = Signal(str)
    videoSourceChanged = Signal()
    pageChangeRequested = Signal(str)
    startTrainingRequested = Signal()
    stopTrainingRequested = Signal()

    def __init__(self):
        super().__init__()
        self._video_source = "0"

    @Property(str, notify=videoSourceChanged)
    def video_source(self):
        return self._video_source

    @video_source.setter
    def video_source(self, value):
        if self._video_source != str(value):
            self._video_source = str(value)
            self.videoSourceChanged.emit()

    @Slot(int, list)
    def update_stats(self, duration, session_letters):
        print(f"[AppCore] Trening zakończony. Czas: {duration}s, Wykryte litery: {session_letters}")


if __name__ == "__main__":
    QQuickStyle.setStyle("Basic")

    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()

    app_core = AppCore()

    video_provider = VideoProvider()
    engine.addImageProvider("video", video_provider)

    video_provider2 = VideoProvider2()
    engine.addImageProvider("video2", video_provider2)

    training_ctrl = TrainingController(app_core, video_provider, video_provider2)

    app_core.startTrainingRequested.connect(training_ctrl.startTraining)
    app_core.stopTrainingRequested.connect(training_ctrl.stopTraining)

    def _start_training():
        print("[Voice] START")
        app_core.startTrainingRequested.emit()
        app_core.pageChangeRequested.emit("TrainingScreen.qml")

    def _stop_training():
        print("[Voice] STOP")
        app_core.stopTrainingRequested.emit()
        app_core.pageChangeRequested.emit("MainMenu.qml")


    def _next_pose():
        print("[Voice] NEXT POSE")
        if training_ctrl.isRunning:
            training_ctrl.nextPose()


    def _swap_cameras():
        print("[Voice] SWAP CAMERAS")

        cam1 = training_ctrl._camera_index
        cam2 = training_ctrl._camera_index_2

        if cam2 >= 0:
            training_ctrl.setCameraIndex(cam2)
            training_ctrl.setCameraIndex2(cam1)

    voice_commands = {
        "zacznij trening": _start_training,
        "rozpocznij trening": _start_training,
        "start": _start_training,
        "trenuj": _start_training,
        "zatrzymaj trening": _stop_training,
        "stop": _stop_training,
        "koniec": _stop_training,
        "zakoncz trening": _stop_training,
        "zakończ trening": _stop_training,
        "wróc": _stop_training,
        "wroc": _stop_training,
        "wróć": _stop_training,
        "następna pozycja": _next_pose,
        "nastepna pozycja": _next_pose,
        "zmień pozycję": _next_pose,
        "zmien pozycje": _next_pose,
        "kolejna pozycja": _next_pose,
        "dalej": _next_pose,
        "zamień kamery": _swap_cameras,
        "zamien kamery": _swap_cameras,
        "zamień kamerki": _swap_cameras,
        "zamien kamerki": _swap_cameras,
        "zmień kamery": _swap_cameras,
        "zmien kamery": _swap_cameras,
    }

    voice_assistant = VoiceAssistant(
        commands=voice_commands,
        model_pl_path=os.path.join(SCRIPT_DIR, "models", "pl"),
        model_en_path=os.path.join(SCRIPT_DIR, "models", "en"),
        preferred_language="pl",
    )

    training_ctrl.setVoiceAssistant(voice_assistant)
    voice_assistant.start()

    ctx = engine.rootContext()
    ctx.setContextProperty("App", app_core)
    ctx.setContextProperty("TrainingCtrl", training_ctrl)

    engine.addImportPath(SCRIPT_DIR)

    qml_file = os.path.join(SCRIPT_DIR, "main.qml")
    engine.load(QUrl.fromLocalFile(qml_file))

    if not engine.rootObjects():
        print(f"[ERROR] QML engine failed to load: {qml_file}", file=sys.stderr)
        sys.exit(-1)

    exit_code = app.exec()
    voice_assistant.stop()
    sys.exit(exit_code)
