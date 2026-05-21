import sys
from PySide6.QtCore import QObject, Signal, Property, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from screen_training import TrainingController, VideoProvider


class AppCore(QObject):
    navRequested = Signal(str)
    videoSourceChanged = Signal()

    def __init__(self):
        super().__init__()
        # Domyślne źródło wideo: "0" oznacza pierwszą dostępną kamerę internetową
        self._video_source = "0"

    # Właściwość (Property) dostępna zarówno dla Pythona, jak i dla widoku QML
    @Property(str, notify=videoSourceChanged)
    def video_source(self):
        return self._video_source

    @video_source.setter
    def video_source(self, value):
        if self._video_source != str(value):
            self._video_source = str(value)
            self.videoSourceChanged.emit()

    # Metoda wywoływana automatycznie przy zatrzymaniu treningu w screen_training.py
    @Slot(int, list)
    def update_stats(self, duration, session_letters):
        print(f"[AppCore] Trening zakończony. Czas: {duration}s, Wykryte litery: {session_letters}")
        # Tutaj możesz w przyszłości dodać logikę przekazywania statystyk do ResultsScreen.qml


if __name__ == "__main__":
    # Fixes white background when hovering over buttons in Windows 11
    QQuickStyle.setStyle("Basic")

    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()

    app_core = AppCore()

    video_provider = VideoProvider()
    engine.addImageProvider("video", video_provider)

    training_ctrl = TrainingController(app_core, video_provider)

    ctx = engine.rootContext()
    ctx.setContextProperty("App", app_core)
    ctx.setContextProperty("TrainingCtrl", training_ctrl)

    engine.load("main.qml")

    if not engine.rootObjects():
        sys.exit(-1)
    sys.exit(app.exec())