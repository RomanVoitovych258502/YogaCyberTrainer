import asyncio
import collections
import io
import json
import os
import queue
import tempfile
import threading
import time
import unicodedata
import wave
from typing import Callable, Dict, Optional

import numpy as np
import sounddevice as sd
import pygame
import edge_tts
from vosk import Model, KaldiRecognizer, SetLogLevel

SetLogLevel(-1)


def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return " ".join(text.split())


class VoiceAssistant:
    def __init__(
        self,
        commands: Dict[str, Callable[[], None]],
        model_pl_path: str = "models/pl",
        model_en_path: str = "models/en",
        preferred_language: str = "pl",
        sample_rate: int = 16000,
        chunk_ms: int = 100,
        energy_threshold: float = 450.0,
        silence_ms: int = 700,
        max_utterance_ms: int = 12000,
        texts_file: str = "texts.json",
        play_callback: Optional[Callable[[str], None]] = None,
    ):
        self.commands = commands
        self.preferred_language = preferred_language
        self.sample_rate = sample_rate
        self.chunk_ms = chunk_ms
        self.energy_threshold = energy_threshold
        self.silence_ms = silence_ms
        self.max_utterance_ms = max_utterance_ms
        self.play_callback = play_callback
        self.input_device: Optional[int] = None

        self.running = False
        self.audio_queue: "queue.Queue[bytes]" = queue.Queue()

        self.pre_speech_buffer = collections.deque(maxlen=5)
        self.texts = self._load_texts(texts_file)

        self.models = {
            "pl": Model(model_pl_path),
            "en": Model(model_en_path),
        }

        pygame.mixer.init()

        self.voices = {
            "pl": "pl-PL-MarekNeural",
            "en": "en-US-GuyNeural",
        }

    def _load_texts(self, path: str) -> dict:
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_text(self, key: str, language: Optional[str] = None) -> str:
        lang = language or self.preferred_language
        return self.texts.get(lang, {}).get(key, key)

    async def _speak_async(self, text: str, language: str = "pl") -> None:
        voice = self.voices.get(language, self.voices["pl"])

        fd, mp3_path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)

        try:
            communicate = edge_tts.Communicate(text=text, voice=voice, rate="+20%")
            await communicate.save(mp3_path)

            if self.play_callback:
                # Jeśli podano callback (np. QMediaPlayer z PySide6), przekieruj odtwarzanie tam
                self.play_callback(mp3_path)
                # Dajemy chwilę na załadowanie pliku zanim przejdziemy dalej
                await asyncio.sleep(1.5)
            else:
                pygame.mixer.music.load(mp3_path)
                pygame.mixer.music.play()

                while pygame.mixer.music.get_busy():
                    await asyncio.sleep(0.05)

                pygame.mixer.music.stop()
                try:
                    pygame.mixer.music.unload()
                except Exception:
                    pass
                await asyncio.sleep(0.2)

        finally:
            # Opóźnione usuwanie pliku tymczasowego (przydatne przy asynchronicznym QMediaPlayer)
            for _ in range(30):
                try:
                    if os.path.exists(mp3_path):
                        os.remove(mp3_path)
                    break
                except PermissionError:
                    await asyncio.sleep(0.2)

    def speak(self, text: str, language: str = "pl") -> None:
        asyncio.run(self._speak_async(text, language))

    def speak_key(self, key: str, language: Optional[str] = None) -> None:
        lang = language or self.preferred_language
        self.speak(self.get_text(key, lang), lang)

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        threading.Thread(target=self.loop, daemon=True).start()

    def stop(self) -> None:
        self.running = False

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            print("AUDIO STATUS:", status)
        self.audio_queue.put(bytes(indata))

    def _raw_to_wav_bytes(self, raw_bytes: bytes) -> bytes:
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(raw_bytes)
        return buffer.getvalue()

    def transcribe_with_model(self, raw_bytes: bytes, model: Model) -> str:
        wav_bytes = self._raw_to_wav_bytes(raw_bytes)
        wav_io = io.BytesIO(wav_bytes)

        with wave.open(wav_io, "rb") as wf:
            rec = KaldiRecognizer(model, wf.getframerate())
            rec.SetWords(False)

            parts = []
            while True:
                data = wf.readframes(4000)
                if not data:
                    break
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    text = result.get("text", "").strip()
                    if text:
                        parts.append(text)

            final_result = json.loads(rec.FinalResult())
            final_text = final_result.get("text", "").strip()
            if final_text:
                parts.append(final_text)

        return normalize_text(" ".join(parts))

    def handle(self, text: str) -> bool:
        normalized_text = normalize_text(text)
        for phrase, func in self.commands.items():
            if normalize_text(phrase) in normalized_text:
                func()
                return True
        return False

    def _process_utterance(self, raw_bytes: bytes) -> None:
        if not raw_bytes:
            return

        try:
            with open("debug_audio.wav", "wb") as f:
                f.write(self._raw_to_wav_bytes(raw_bytes))
        except Exception as e:
            print("BŁĄD ZAPISU DEBUG AUDIO:", e)

        order = [
            self.preferred_language,
            "en" if self.preferred_language == "pl" else "pl",
        ]

        for lang in order:
            model = self.models.get(lang)
            if model is None:
                continue

            text = self.transcribe_with_model(raw_bytes, model)
            if not text:
                continue

            print(f"HEARD [{lang}]:", text)
            if self.handle(text):
                return

    def loop(self) -> None:
        blocksize = int(self.sample_rate * self.chunk_ms / 1000)

        while self.running:
            speech_chunks = []
            in_speech = False
            silence_acc_ms = 0
            speech_acc_ms = 0
            current_device = self.input_device

            try:
                with sd.RawInputStream(
                    samplerate=self.sample_rate,
                    blocksize=blocksize,
                    dtype="int16",
                    channels=1,
                    device=current_device,
                    callback=self._audio_callback,
                ):
                    while self.running and current_device == self.input_device:
                        try:
                            data = self.audio_queue.get(timeout=0.5)
                        except queue.Empty:
                            continue

                        samples = np.frombuffer(data, dtype=np.int16).astype(np.float32)
                        rms = float(np.sqrt(np.mean(samples * samples))) if samples.size else 0.0

                        if rms >= self.energy_threshold:
                            if not in_speech:
                                in_speech = True
                                speech_chunks = list(self.pre_speech_buffer)
                                silence_acc_ms = 0
                                speech_acc_ms = len(speech_chunks) * self.chunk_ms

                            speech_chunks.append(data)
                            speech_acc_ms += self.chunk_ms
                            silence_acc_ms = 0

                        elif in_speech:
                            speech_chunks.append(data)
                            speech_acc_ms += self.chunk_ms
                            silence_acc_ms += self.chunk_ms

                            if silence_acc_ms >= self.silence_ms or speech_acc_ms >= self.max_utterance_ms:
                                self._process_utterance(b"".join(speech_chunks))
                                speech_chunks = []
                                in_speech = False
                                silence_acc_ms = 0
                                speech_acc_ms = 0
                        else:
                            self.pre_speech_buffer.append(data)

            except Exception as e:
                print("ERROR IN AUDIO STREAM LOOP:", e)
                time.sleep(1)  # Zapobiega zapętleniu błędu w nieskończoność