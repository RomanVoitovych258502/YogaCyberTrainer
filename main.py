import sys

from PySide6.QtCore import QObject
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle


class AppCore(QObject):
    def __init__(self):
        super().__init__()

if __name__ == "__main__":
    # Fixes white background when hovering over buttons in Windows 11
    QQuickStyle.setStyle("Basic")

    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()

    app_core = AppCore()

    ctx = engine.rootContext()

    engine.load("main.qml")
    if not engine.rootObjects():
        sys.exit(-1)
    sys.exit(app.exec())