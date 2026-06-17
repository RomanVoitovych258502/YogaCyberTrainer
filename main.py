import os
import sys
import json
import asyncio
import threading
import numpy as np
import sounddevice as sd
from PySide6.QtCore import QObject, Signal, Property, Slot, QUrl, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaDevices

from screen_training import TrainingController, VideoProvider, VideoProvider2
from VoiceAPI import VoiceAssistant

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


class AppCore(QObject):
    navRequested = Signal(str)
    videoSourceChanged = Signal()
    pageChangeRequested = Signal(str)
    startTrainingRequested = Signal()
    stopTrainingRequested = Signal()
    i18nChanged = Signal()
    audioOutputsChanged = Signal()
    audioInputsChanged = Signal()
    audioLevelChanged = Signal()
    playTtsRequested = Signal(str)

    def __init__(self):
        super().__init__()
        self._video_source = "0"
        self._i18n_dict = {}

        # Audio & TTS Setup
        self.tts_player = QMediaPlayer()
        self.tts_audio_output = QAudioOutput()
        self.tts_player.setAudioOutput(self.tts_audio_output)
        self.playTtsRequested.connect(self._do_play_tts)

        self.setup_audio_devices()

        # Audio level monitoring
        self._audio_level = 0.0
        self._raw_level = 0.0
        self.level_timer = QTimer()
        self.level_timer.timeout.connect(self.update_audio_level)
        self.level_timer.start(50)
        self.stream = None
        self.start_input_stream()

        # Load default interface language
        self.load_language("pl")

    # --- Language / i18n ---
    def load_language(self, lang_code):
        path = os.path.join(SCRIPT_DIR, "lang", f"{lang_code}.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                self._i18n_dict = json.load(f)
        except Exception as e:
            print(f"Error loading {path}:", e)
            self._i18n_dict = {}
        self.i18nChanged.emit()

    @Property(dict, notify=i18nChanged)
    def i18n(self):
        return self._i18n_dict

    @Slot(str)
    def setLanguage(self, lang_code):
        self.load_language(lang_code)
        if hasattr(self, 'voice_assistant'):
            self.voice_assistant.preferred_language = lang_code

    # --- Audio Device Logic & Levels ---
    def setup_audio_devices(self):
        self._audio_outputs = QMediaDevices.audioOutputs()
        self._output_names = [dev.description() for dev in self._audio_outputs]

        self._input_devices = []
        for i, dev in enumerate(sd.query_devices()):
            if dev['max_input_channels'] > 0:
                self._input_devices.append({'index': i, 'name': dev['name']})
        self._input_names = [d['name'] for d in self._input_devices]
        self._current_input_idx = self._input_devices[0]['index'] if self._input_devices else None

    @Property(list, notify=audioOutputsChanged)
    def audioOutputs(self):
        return self._output_names

    @Property(list, notify=audioInputsChanged)
    def audioInputs(self):
        return self._input_names

    @Property(float, notify=audioLevelChanged)
    def audioLevel(self):
        return self._audio_level

    @Slot(int)
    def setOutputDevice(self, index):
        if 0 <= index < len(self._audio_outputs):
            self.tts_audio_output.setDevice(self._audio_outputs[index])

    @Slot(int)
    def setInputDevice(self, index):
        if 0 <= index < len(self._input_devices):
            self._current_input_idx = self._input_devices[index]['index']
            if hasattr(self, 'voice_assistant'):
                self.voice_assistant.input_device = self._current_input_idx
            self.start_input_stream()

    def start_input_stream(self):
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
        if self._current_input_idx is not None:
            try:
                self.stream = sd.InputStream(device=self._current_input_idx, channels=1, callback=self.audio_callback)
                self.stream.start()
            except Exception as e:
                print("Could not start audio level stream:", e)

    def audio_callback(self, indata, frames, time, status):
        norm = np.linalg.norm(indata) * 10
        self._raw_level = norm

    def update_audio_level(self):
        target = min(1.0, self._raw_level / 100.0)
        self._audio_level = 0.8 * self._audio_level + 0.2 * target
        self.audioLevelChanged.emit()

    def play_tts_file(self, filepath):
        self.playTtsRequested.emit(filepath)

    @Slot(str)
    def _do_play_tts(self, filepath):
        self.tts_player.setSource(QUrl.fromLocalFile(os.path.abspath(filepath)))
        self.tts_player.play()

    @Slot()
    def testAudio(self):
        def worker():
            if hasattr(self, 'voice_assistant'):
                text = self.voice_assistant.get_text("test_audio")
                self.voice_assistant.speak(text, self.voice_assistant.preferred_language)
        threading.Thread(target=worker, daemon=True).start()

    # --- Video Config ---
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
        play_callback=app_core.play_tts_file
    )

    # Połącz wybrane urządzenie wejściowe z asystentem głosowym
    voice_assistant.input_device = app_core._current_input_idx
    app_core.voice_assistant = voice_assistant

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