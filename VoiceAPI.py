import json, tempfile, threading, wave, asyncio
import numpy as np
import sounddevice as sd
import edge_tts
from playsound import playsound
from faster_whisper import WhisperModel


class VoiceAssistant:

    def __init__(self, commands, language="pl", texts_file="texts.json"):
        self.commands = commands
        self.language = language
        self.running = False
        self.model = WhisperModel("base", device="cpu", compute_type="int8")
        self.texts = self.load_texts(texts_file)
        self.voice = "pl-PL-MarekNeural" if language == "pl" else "en-US-GuyNeural"

    def load_texts(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_text(self, key):
        return self.texts[self.language].get(key, key)

    async def speak_async(self, text):
        output = "voice.mp3"
        await edge_tts.Communicate(text=text, voice=self.voice).save(output)
        playsound(output)

    def speak(self, key):
        asyncio.run(self.speak_async(self.get_text(key)))

    def start(self):
        if self.running: return
        self.running = True
        threading.Thread(target=self.loop, daemon=True).start()

    def stop(self):
        self.running = False

    def record_audio(self, seconds=3, samplerate=16000):
        audio = sd.rec(int(seconds * samplerate), samplerate=samplerate, channels=1, dtype=np.int16)
        sd.wait()
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")

        with wave.open(temp.name, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(samplerate)
            wf.writeframes(audio.tobytes())
        return temp.name

    def transcribe(self, path):
        segments, _ = self.model.transcribe(path, language=self.language)
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
                if not text: continue
                print("HEARD:", text)
                self.handle(text)
            except Exception as e:
                print("ERROR:", e)