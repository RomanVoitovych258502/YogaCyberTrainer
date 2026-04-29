import sys
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from screen_training import TrainingController, VideoProvider


class AppCore(QObject):
    navRequested = Signal(str)

    def __init__(self):
        super().__init__()


if __name__ == "__main__":
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()

    app_core = AppCore()

    video_provider = VideoProvider()
    engine.addImageProvider("video", video_provider)

    training_ctrl = TrainingController(video_provider)

    ctx = engine.rootContext()
    ctx.setContextProperty("App", app_core)
    ctx.setContextProperty("TrainingCtrl", training_ctrl)

    engine.load("main.qml")

    if not engine.rootObjects():
        sys.exit(-1)
    sys.exit(app.exec())