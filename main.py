import os
import sys
from PySide6.QtCore import QObject, Signal, Property, Slot, QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from screen_training import TrainingController, VideoProvider
from VoiceAPI import VoiceAssistant

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


class AppCore(QObject):
    navRequested = Signal(str)
    videoSourceChanged = Signal()
    pageChangeRequested = Signal(str)

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

    training_ctrl = TrainingController(app_core, video_provider)


    # ── Voice commands ────────────────────────────────────────────────────────
    def _start_training():
        print("--- PRÓBA STARTU TRENINGU ---")
        app_core.pageChangeRequested.emit("TrainingScreen.qml")


    def _stop_training():
        print("[Voice] STOP")
        app_core.pageChangeRequested.emit("MainMenu.qml")


    voice_commands = {
        # Start variants
        "zacznij trening": _start_training,
        "rozpocznij trening": _start_training,
        "start": _start_training,
        "trenuj": _start_training,
        # Stop variants
        "zatrzymaj trening": _stop_training,
        "stop": _stop_training,
        "koniec": _stop_training,
        "zakończ trening": _stop_training,
        "wróć": _stop_training,
    }

    voice_assistant = VoiceAssistant(
        commands=voice_commands,
        model_pl_path=os.path.join(SCRIPT_DIR, "models", "pl"),
        model_en_path=os.path.join(SCRIPT_DIR, "models", "en"),
        preferred_language="pl",
    )

    training_ctrl.set_voice_assistant(voice_assistant)
    voice_assistant.start()

    # ── QML context ───────────────────────────────────────────────────────────
    ctx = engine.rootContext()
    ctx.setContextProperty("App", app_core)
    ctx.setContextProperty("TrainingCtrl", training_ctrl)

    engine.addImportPath(SCRIPT_DIR)

    qml_file = os.path.join(SCRIPT_DIR, "main.qml")
    engine.load(QUrl.fromLocalFile(qml_file))

    if not engine.rootObjects():
        print(f"[ERROR] QML engine failed to load: {qml_file}", file=sys.stderr)
        sys.exit(-1)

    sys.exit(app.exec())