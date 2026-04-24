import sys

from PySide6.QtCore import QObject
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine


class AppCore(QObject):
    def __init__(self):
        super().__init__()

if __name__ == "__main__":
    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()

    app_core = AppCore()

    ctx = engine.rootContext()

    engine.load("main.qml")
    if not engine.rootObjects():
        sys.exit(-1)
    sys.exit(app.exec())