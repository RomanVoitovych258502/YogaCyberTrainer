import sys, os, json, asyncio, threading, random
import numpy as np
import sounddevice as sd
from PySide6.QtCore import QObject, Signal, Property, Slot, QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaDevices

from screen_training import TrainingController
from video_providers import VideoProvider, VideoProvider2
from VoiceAPI import VoiceAssistant


class AppCore(QObject):
    navRequested = Signal(str)
    videoSourceChanged = Signal()
    i18nChanged = Signal()
    audioOutputsChanged = Signal()
    audioInputsChanged = Signal()
    audioLevelChanged = Signal()
    playTtsRequested = Signal(str)

    def __init__(self):
        super().__init__()
        self._video_source = "0"
        self._i18n_dict = {}

        # Audio & TTS setup
        self.tts_player = QMediaPlayer()
        self.tts_audio_output = QAudioOutput()
        self.tts_player.setAudioOutput(self.tts_audio_output)
        self.playTtsRequested.connect(self._do_play_tts)

        self.setup_audio_devices()

        # Initialize voice API
        self.voice_api = VoiceAssistant(commands={}, language="pl", play_callback=self.play_tts_file)
        self.voice_api.input_device = self._current_input_idx

        # Audio level monitoring
        self._audio_level = 0.0
        self._raw_level = 0.0
        self.level_timer = QTimer()
        self.level_timer.timeout.connect(self.update_audio_level)
        self.level_timer.start(50)
        self.stream = None
        self.start_input_stream()

        # Load initial language
        self.load_language("pl")

    # --- Language / i18n ---
    def load_language(self, lang_code):
        path = os.path.join("lang", f"{lang_code}.json")
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
        self.voice_api.language = lang_code
        self.voice_api.voice = "pl-PL-MarekNeural" if lang_code == "pl" else "en-US-GuyNeural"

    # --- Audio Logic ---
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
            self.voice_api.input_device = self._current_input_idx
            self.start_input_stream()

    def start_input_stream(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
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
            text = self.voice_api.get_text("test_audio")
            asyncio.run(self.voice_api.speak_async(text))

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

    ctx = engine.rootContext()
    ctx.setContextProperty("App", app_core)
    ctx.setContextProperty("TrainingCtrl", training_ctrl)

    engine.load("main.qml")

    if not engine.rootObjects():
        sys.exit(-1)
    sys.exit(app.exec())