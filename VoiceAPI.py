import json
import tempfile
import threading
import wave
import asyncio
import time

import numpy as np
import sounddevice as sd
import edge_tts

from faster_whisper import WhisperModel

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication
from PySide6.QtMultimedia import QSoundEffect


class VoiceAssistant:

    def __init__(self, commands, language="pl", texts_file="texts.json"):
        self.commands = commands
        self.language = language
        self.running = False

        # Whisper
        self.model = WhisperModel("base",device="cpu",compute_type="int8")

        # Texts
        self.texts = self.load_texts(texts_file)
        self.voice = ("pl-PL-MarekNeural" if language == "pl" else "en-US-GuyNeural")

        # Qt app
        self.app = QApplication.instance()

        if self.app is None:
            self.app = QApplication([])

        # Audio player
        self.player = QSoundEffect()
        self.player.setVolume(1.0)

    def load_texts(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_text(self, key):
        return self.texts[self.language].get(key, key)

    async def speak_async(self, text):

        output = "voice.wav"
        await edge_tts.Communicate(text=text,voice=self.voice).save(output)
        self.player.setSource(QUrl.fromLocalFile(output))
        self.player.play()
        while self.player.isPlaying():
            self.app.processEvents()
            time.sleep(0.01)

    def speak(self, key):

        text = self.get_text(key)
        try:
            loop = asyncio.get_running_loop()
            asyncio.create_task(self.speak_async(text))

        except RuntimeError:
            asyncio.run(self.speak_async(text))

    def start(self):
        if self.running:
            return
        self.running = True
        threading.Thread(target=self.loop,daemon=True).start()

    def stop(self):
        self.running = False

    def record_audio(self,seconds=3,samplerate=16000):
        audio = sd.rec(int(seconds * samplerate),samplerate=samplerate,channels=1,dtype=np.int16)
        sd.wait()
        temp = tempfile.NamedTemporaryFile(delete=False,suffix=".wav")
        with wave.open(temp.name, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(samplerate)
            wf.writeframes(audio.tobytes())
        return temp.name

    def transcribe(self, path):
        segments, _ = self.model.transcribe(path,language=self.language)
        return " ".join(seg.text for seg in segments).lower()

    def handle(self, text):
        for command, func in self.commands.items():
            if command.lower() in text:
                func()
                return

    def loop(self):
        while self.running:
            try:
                wav = self.record_audio()
                text = self.transcribe(wav)
                if not text:
                    continue
                print("HEARD:", text)
                self.handle(text)
            except Exception as e:
                print("ERROR:", e)
