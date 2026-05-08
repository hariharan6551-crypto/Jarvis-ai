"""
J.A.R.V.I.S Voice Engine
Complete voice pipeline: STT (Whisper), TTS (pyttsx3/Edge-TTS/ElevenLabs),
clap detection, offline wake word ("Hey JARVIS"), and mic auto-detection.

Latency targets:
  - STT: under 500ms
  - TTS: under 1 second
  - Full round-trip: under 2 seconds
"""

import asyncio
import io
import os
import sys
import tempfile
import threading
import time
import wave
import struct
import base64
import math
from pathlib import Path
from typing import Optional, Callable
from core.logger import get_logger
from config.settings import settings

log = get_logger("voice")


# ═══════════════════════════════════════════════════════════════════════
#  VOICE ENGINE
# ═══════════════════════════════════════════════════════════════════════

class VoiceEngine:
    """Handles speech-to-text, text-to-speech, clap detection, and wake word."""

    def __init__(self):
        self.whisper_model = None
        self.tts_engine = None
        self._tts_lock = threading.Lock()
        self._tts_thread = None
        self._mic_available = False
        self._mic_device_index = None
        self._mic_retry_task = None
        self._clap_listener_task = None
        self._wake_word_task = None
        self._is_listening = False
        self._shutdown = False

        # JARVIS active state
        self.jarvis_active = False

        # Callbacks
        self.on_clap: Optional[Callable] = None          # single clap
        self.on_double_clap: Optional[Callable] = None    # double clap
        self.on_triple_clap: Optional[Callable] = None    # triple clap
        self.on_wake_word: Optional[Callable] = None      # "Hey JARVIS"
        self.on_voice_activity: Optional[Callable] = None  # voice detected

        # WebSocket broadcast function (set by main.py)
        self.broadcast_fn: Optional[Callable] = None

        # Detect mic on init
        self._detect_mic()
        self._init_tts()
        log.info("Voice engine initialized")

    # ─── Microphone Detection ─────────────────────────────────────────

    def _detect_mic(self) -> bool:
        """Detect and select the best microphone device."""
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            default_input = sd.default.device[0]

            # Try default input first
            if default_input is not None and default_input >= 0:
                dev = devices[default_input]
                if dev.get("max_input_channels", 0) > 0:
                    self._mic_device_index = int(default_input)
                    self._mic_available = True
                    log.info(f"Microphone detected: {dev['name']} (index {default_input})")
                    return True

            # Scan for any input device
            for i, dev in enumerate(devices):
                try:
                    if dev.get("max_input_channels", 0) > 0:
                        self._mic_device_index = i
                        self._mic_available = True
                        log.info(f"Microphone found: {dev['name']} (index {i})")
                        return True
                except Exception:
                    continue

            log.warning("No microphone device detected")
            self._mic_available = False
            return False

        except ImportError:
            log.warning("sounddevice not installed — mic detection unavailable")
            self._mic_available = False
            return False
        except Exception as e:
            log.error(f"Mic detection failed: {e}")
            self._mic_available = False
            return False

    async def start_mic_retry_loop(self):
        """Retry mic detection every 10 seconds if not found."""
        while not self._shutdown:
            if not self._mic_available:
                log.info("Retrying microphone detection...")
                found = self._detect_mic()
                if found:
                    log.info("Microphone detected on retry!")
                    # Start listeners that need mic
                    asyncio.create_task(self.start_clap_detector())
                    break
            else:
                break
            await asyncio.sleep(10)

    def get_mic_status(self) -> dict:
        """Get current microphone status."""
        try:
            import sounddevice as sd
            if self._mic_available and self._mic_device_index is not None:
                dev = sd.query_devices(self._mic_device_index)
                return {
                    "available": True,
                    "device_name": dev.get("name", "Unknown"),
                    "device_index": self._mic_device_index,
                    "sample_rate": int(dev.get("default_samplerate", 16000)),
                }
            return {"available": False, "device_name": None, "device_index": None}
        except Exception:
            return {"available": False, "device_name": None, "device_index": None}

    # ─── TTS Initialization ───────────────────────────────────────────

    def _init_tts(self):
        """Initialize TTS engine (pyttsx3 in daemon thread for safety)."""
        if settings.TTS_PROVIDER == "pyttsx3":
            self._start_pyttsx3_thread()
        log.info(f"TTS provider: {settings.TTS_PROVIDER}")

    def _start_pyttsx3_thread(self):
        """Initialize pyttsx3 in a separate daemon thread to avoid COM issues."""
        def _init_worker():
            try:
                import pyttsx3
                engine = pyttsx3.init()
                engine.setProperty("rate", 175)
                engine.setProperty("volume", 0.9)
                voices = engine.getProperty("voices")
                for voice in voices:
                    if "male" in voice.name.lower() or "david" in voice.name.lower():
                        engine.setProperty("voice", voice.id)
                        break
                self.tts_engine = engine
                log.info("pyttsx3 TTS initialized in daemon thread")
            except Exception as e:
                log.warning(f"pyttsx3 init failed: {e}")
                self.tts_engine = None

        self._tts_thread = threading.Thread(target=_init_worker, daemon=True)
        self._tts_thread.start()
        self._tts_thread.join(timeout=5)

    def _reinit_tts(self):
        """Auto-reinitialize TTS engine on crash."""
        log.warning("Re-initializing TTS engine after crash...")
        self.tts_engine = None
        try:
            if settings.TTS_PROVIDER == "pyttsx3":
                self._start_pyttsx3_thread()
            log.info("TTS engine re-initialized successfully")
        except Exception as e:
            log.error(f"TTS re-initialization failed: {e}")

    # ─── Whisper STT ──────────────────────────────────────────────────

    async def load_whisper(self):
        """Lazy load Whisper model in background thread (non-blocking)."""
        if self.whisper_model is None:
            try:
                import whisper
                log.info(f"Loading Whisper model: {settings.WHISPER_MODEL}")
                self.whisper_model = await asyncio.to_thread(
                    whisper.load_model, settings.WHISPER_MODEL
                )
                log.info("Whisper model loaded successfully")
            except ImportError:
                log.warning("openai-whisper not installed — local STT unavailable")
            except Exception as e:
                log.error(f"Failed to load Whisper: {e}")

    async def transcribe(self, audio_data: bytes, sample_rate: int = 16000) -> str:
        """Transcribe audio bytes to text using Whisper (with API fallback)."""
        start = time.time()
        try:
            # Try local Whisper first
            if self.whisper_model is None:
                await self.load_whisper()

            if self.whisper_model:
                text = await self._transcribe_whisper(audio_data, sample_rate)
                elapsed = (time.time() - start) * 1000
                log.info(f"Transcribed in {elapsed:.0f}ms: {text}")
                return text

            # Fallback to OpenAI API
            if settings.OPENAI_API_KEY:
                text = await self._transcribe_openai_api(audio_data, sample_rate)
                elapsed = (time.time() - start) * 1000
                log.info(f"Transcribed (API) in {elapsed:.0f}ms: {text}")
                return text

            log.warning("No STT engine available")
            return ""
        except Exception as e:
            log.error(f"Transcription failed: {e}")
            return ""

    async def _transcribe_whisper(self, audio_data: bytes, sample_rate: int) -> str:
        """Transcribe using local Whisper model."""
        try:
            import numpy as np
            audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0

            result = await asyncio.to_thread(
                self.whisper_model.transcribe,
                audio_array,
                language="en",
                fp16=False,
            )
            return result.get("text", "").strip()
        except Exception as e:
            log.error(f"Whisper transcription error: {e}")
            return ""

    async def _transcribe_openai_api(self, audio_data: bytes, sample_rate: int) -> str:
        """Transcribe using OpenAI Whisper API."""
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_data)
            wav_buffer.seek(0)
            wav_buffer.name = "audio.wav"

            response = await client.audio.transcriptions.create(
                model="whisper-1",
                file=wav_buffer,
                language="en",
            )
            return response.text.strip()
        except Exception as e:
            log.error(f"OpenAI API transcription error: {e}")
            return ""

    # ─── TTS (Text-to-Speech) ─────────────────────────────────────────

    async def speak(self, text: str) -> Optional[bytes]:
        """Convert text to speech audio bytes. Auto-reinit on crash."""
        if not text or not text.strip():
            return None
        start = time.time()
        try:
            if settings.TTS_PROVIDER == "edge":
                audio = await self._speak_edge_tts(text)
            elif settings.TTS_PROVIDER == "elevenlabs" and settings.ELEVENLABS_API_KEY:
                audio = await self._speak_elevenlabs(text)
            elif settings.TTS_PROVIDER == "pyttsx3" and self.tts_engine:
                audio = await self._speak_pyttsx3(text)
            else:
                # Default to edge-tts
                audio = await self._speak_edge_tts(text)

            elapsed = (time.time() - start) * 1000
            if audio:
                log.debug(f"TTS generated {len(audio)} bytes in {elapsed:.0f}ms")
            return audio
        except Exception as e:
            log.error(f"TTS failed: {e}")
            # Auto-reinitialize on crash
            self._reinit_tts()
            # Try one more time with edge-tts as fallback
            try:
                return await self._speak_edge_tts(text)
            except Exception as e2:
                log.error(f"TTS fallback also failed: {e2}")
                return None

    async def _speak_edge_tts(self, text: str) -> bytes:
        """Generate speech using Edge TTS (free, high quality)."""
        try:
            import edge_tts
            communicate = edge_tts.Communicate(text, settings.EDGE_TTS_VOICE)
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            return audio_data
        except Exception as e:
            log.error(f"Edge TTS error: {e}")
            raise

    async def _speak_elevenlabs(self, text: str) -> bytes:
        """Generate speech using ElevenLabs API."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{settings.ELEVENLABS_VOICE_ID}",
                    headers={
                        "xi-api-key": settings.ELEVENLABS_API_KEY,
                        "Content-Type": "application/json",
                    },
                    json={
                        "text": text,
                        "model_id": "eleven_monolingual_v1",
                        "voice_settings": {
                            "stability": 0.5,
                            "similarity_boost": 0.75,
                        },
                    },
                )
                if response.status_code == 200:
                    return response.content
                log.error(f"ElevenLabs API error: {response.status_code}")
                raise Exception(f"ElevenLabs HTTP {response.status_code}")
        except Exception as e:
            log.error(f"ElevenLabs TTS error: {e}")
            raise

    async def _speak_pyttsx3(self, text: str) -> Optional[bytes]:
        """Generate speech using pyttsx3 (offline, in daemon thread)."""
        if not self.tts_engine:
            self._reinit_tts()
            if not self.tts_engine:
                return None

        temp_file = tempfile.mktemp(suffix=".wav")
        try:
            def _save_and_run():
                with self._tts_lock:
                    try:
                        self.tts_engine.save_to_file(text, temp_file)
                        self.tts_engine.runAndWait()
                    except Exception as e:
                        log.error(f"pyttsx3 engine error: {e}")
                        raise

            await asyncio.to_thread(_save_and_run)

            if os.path.exists(temp_file):
                with open(temp_file, "rb") as f:
                    return f.read()
            return None
        except Exception as e:
            log.error(f"pyttsx3 TTS error: {e}")
            self._reinit_tts()
            return None
        finally:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception:
                pass

    # ─── Clap Detection ───────────────────────────────────────────────

    async def start_clap_detector(self):
        """
        Background clap detection using audio amplitude spikes.
        Single clap  → activate JARVIS (say "Hey Hari, how can I help you?")
        Double clap  → deactivate JARVIS (turn off)
        """
        if not self._mic_available:
            log.warning("Clap detection unavailable — no microphone")
            return

        log.info("🎤 Starting clap detector (single=ON, double=OFF)...")

        try:
            import sounddevice as sd
            import numpy as np

            sample_rate = 44100
            block_size = 2048
            # Adaptive threshold - will be calibrated
            clap_threshold = 0.35
            clap_cooldown = 0.25       # Min time between claps (seconds)
            multi_clap_window = 0.65   # Window to detect multiple claps

            clap_times = []
            # Track ambient noise for adaptive threshold
            noise_samples = []
            noise_floor = 0.05

            def _audio_callback(indata, frames, time_info, status):
                nonlocal noise_floor
                if status:
                    return
                try:
                    amplitude = np.abs(indata).max()

                    # Update noise floor (rolling average of quiet samples)
                    if amplitude < 0.15:
                        noise_samples.append(amplitude)
                        if len(noise_samples) > 200:
                            noise_samples.pop(0)
                        if len(noise_samples) > 20:
                            noise_floor = np.mean(noise_samples) * 1.5

                    # Adaptive threshold: must be well above noise floor
                    adaptive_thresh = max(clap_threshold, noise_floor * 4)

                    if amplitude > adaptive_thresh:
                        now = time.time()
                        # Cooldown check
                        if clap_times and (now - clap_times[-1]) < clap_cooldown:
                            return
                        clap_times.append(now)
                        log.debug(f"Clap spike detected: amplitude={amplitude:.3f} threshold={adaptive_thresh:.3f}")
                except Exception:
                    pass

            stream = sd.InputStream(
                samplerate=sample_rate,
                channels=1,
                blocksize=block_size,
                device=self._mic_device_index,
                callback=_audio_callback,
            )

            with stream:
                log.info("✓ Clap detector active and listening")
                while not self._shutdown:
                    await asyncio.sleep(0.1)

                    if not clap_times:
                        continue

                    now = time.time()
                    # Check if multi-clap window has passed
                    if (now - clap_times[-1]) > multi_clap_window:
                        recent = [t for t in clap_times if (now - t) < (multi_clap_window + 0.5)]
                        clap_count = len(recent)
                        clap_times.clear()

                        if clap_count >= 2:
                            log.info("👏👏 Double clap → Deactivate JARVIS")
                            self.jarvis_active = False
                            await self._broadcast_clap_event("double_clap", "off")
                        elif clap_count == 1:
                            log.info("👏 Single clap → Activate JARVIS")
                            self.jarvis_active = True
                            await self._broadcast_clap_event("single_clap", "on")

        except ImportError:
            log.warning("sounddevice not available for clap detection")
        except Exception as e:
            log.error(f"Clap detector error: {e}")
            # Auto-restart after 3 seconds
            if not self._shutdown:
                log.info("Restarting clap detector in 3s...")
                await asyncio.sleep(3)
                asyncio.create_task(self.start_clap_detector())

    async def _broadcast_clap_event(self, event_type: str, jarvis_state: str):
        """Broadcast clap event to all connected WebSocket clients."""
        log.info(f"Attempting to broadcast clap event: {event_type}. broadcast_fn is set: {self.broadcast_fn is not None}")
        if self.broadcast_fn:
            try:
                payload = {
                    "type": "clap_event",
                    "data": {
                        "event": event_type,
                        "jarvis_active": jarvis_state == "on",
                        "message": (
                            f"Hey {settings.USER_NAME}, how can I help you?"
                            if jarvis_state == "on"
                            else f"Going offline {settings.USER_NAME}. Call me anytime."
                        ),
                    },
                }
                log.info(f"Sending payload: {payload}")
                await self.broadcast_fn(payload)
                log.info("Successfully executed broadcast_fn for clap event")
            except Exception as e:
                log.error(f"Broadcast clap event failed: {e}")
        else:
            log.warning("Cannot broadcast clap event: broadcast_fn is None")

    # ─── Wake Word Detection ──────────────────────────────────────────

    async def start_wake_word_listener(self):
        """
        Offline wake word detection using Vosk (lightweight).
        Listens for "Hey JARVIS" / "JARVIS" continuously.
        Falls back to keyword spotting if Vosk unavailable.
        """
        if not self._mic_available:
            log.warning("Wake word listener unavailable — no microphone")
            return

        # Try Vosk first (offline, lightweight)
        try:
            await self._wake_word_vosk()
            return
        except ImportError:
            log.info("Vosk not installed, wake word detection will use frontend Web Speech API")
        except Exception as e:
            log.warning(f"Vosk wake word failed: {e}")

        log.info("Wake word detection delegated to frontend (Web Speech API)")

    async def _wake_word_vosk(self):
        """Wake word detection using Vosk (offline)."""
        import vosk
        import sounddevice as sd
        import json as _json
        import queue

        model_path = Path(__file__).parent.parent / "data" / "vosk-model-small-en-us"
        if not model_path.exists():
            log.warning(f"Vosk model not found at {model_path}. Download from https://alphacephei.com/vosk/models")
            raise FileNotFoundError(f"Vosk model not at {model_path}")

        model = vosk.Model(str(model_path))
        recognizer = vosk.KaldiRecognizer(model, 16000)

        audio_queue = queue.Queue()

        def _callback(indata, frames, time_info, status):
            if status:
                return
            audio_queue.put(bytes(indata))

        log.info("Starting Vosk wake word listener...")

        stream = sd.RawInputStream(
            samplerate=16000,
            blocksize=4000,
            dtype="int16",
            channels=1,
            device=self._mic_device_index,
            callback=_callback,
        )

        wake_words = ["jarvis", "hey jarvis", "j.a.r.v.i.s"]

        with stream:
            while not self._shutdown:
                try:
                    data = await asyncio.to_thread(audio_queue.get, timeout=1)
                except Exception:
                    continue

                if recognizer.AcceptWaveform(data):
                    result = _json.loads(recognizer.Result())
                    text = result.get("text", "").lower().strip()
                    if text and any(w in text for w in wake_words):
                        log.info(f"Wake word detected: '{text}'")
                        self.jarvis_active = True
                        # Broadcast wake word event
                        if self.broadcast_fn:
                            try:
                                await self.broadcast_fn({
                                    "type": "wake_word",
                                    "data": {
                                        "text": text,
                                        "jarvis_active": True,
                                        "message": f"Hey {settings.USER_NAME}, how can I help you?",
                                    },
                                })
                            except Exception as e:
                                log.error(f"Broadcast wake word failed: {e}")
                        if self.on_wake_word:
                            try:
                                if asyncio.iscoroutinefunction(self.on_wake_word):
                                    await self.on_wake_word(text)
                                else:
                                    self.on_wake_word(text)
                            except Exception as e:
                                log.error(f"Wake word handler error: {e}")

    # ─── Record Audio ─────────────────────────────────────────────────

    async def record_audio(self, duration: float = 5.0, sample_rate: int = 16000) -> Optional[bytes]:
        """Record audio from microphone for a fixed duration."""
        if not self._mic_available:
            log.warning("Cannot record — no microphone available")
            return None

        try:
            import sounddevice as sd
            import numpy as np

            log.debug(f"Recording {duration}s of audio...")
            audio = await asyncio.to_thread(
                sd.rec,
                int(duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                dtype="int16",
                device=self._mic_device_index,
            )
            await asyncio.to_thread(sd.wait)

            audio_bytes = audio.tobytes()
            log.debug(f"Recorded {len(audio_bytes)} bytes")
            return audio_bytes

        except Exception as e:
            log.error(f"Audio recording failed: {e}")
            return None

    async def record_until_silence(
        self,
        sample_rate: int = 16000,
        silence_threshold: float = 0.01,
        silence_duration: float = 1.5,
        max_duration: float = 15.0,
    ) -> Optional[bytes]:
        """Record audio until silence is detected or max duration reached."""
        if not self._mic_available:
            return None

        try:
            import sounddevice as sd
            import numpy as np

            chunk_duration = 0.1
            chunk_samples = int(sample_rate * chunk_duration)
            all_audio = []
            silence_time = 0.0
            total_time = 0.0

            stream = sd.InputStream(
                samplerate=sample_rate,
                channels=1,
                dtype="int16",
                blocksize=chunk_samples,
                device=self._mic_device_index,
            )

            with stream:
                while total_time < max_duration:
                    data, _ = stream.read(chunk_samples)
                    all_audio.append(data.copy())

                    amplitude = np.abs(data.astype(np.float32) / 32768.0).mean()
                    if amplitude < silence_threshold:
                        silence_time += chunk_duration
                    else:
                        silence_time = 0.0

                    total_time += chunk_duration

                    if silence_time >= silence_duration and total_time > 0.5:
                        break

                    await asyncio.sleep(0)

            if all_audio:
                combined = np.concatenate(all_audio)
                return combined.tobytes()
            return None

        except Exception as e:
            log.error(f"Record-until-silence failed: {e}")
            return None

    # ─── Greeting ─────────────────────────────────────────────────────

    async def greet(self, user_name: str = "Hari") -> Optional[bytes]:
        """Generate time-of-day greeting for the user."""
        hour = time.localtime().tm_hour
        if hour < 12:
            greeting = f"Good morning {user_name}"
        elif hour < 17:
            greeting = f"Good afternoon {user_name}"
        elif hour < 21:
            greeting = f"Good evening {user_name}"
        else:
            greeting = f"Good evening {user_name}"

        text = f"{greeting}. All systems are online and ready. How can I help you?"
        log.info(f"Greeting: {text}")
        return await self.speak(text)

    async def activation_greeting(self) -> Optional[bytes]:
        """Say activation greeting."""
        text = f"Hey {settings.USER_NAME}, how can I help you?"
        return await self.speak(text)

    async def deactivation_message(self) -> Optional[bytes]:
        """Say deactivation message."""
        text = f"Going offline {settings.USER_NAME}. Call me anytime."
        return await self.speak(text)

    # ─── Shutdown ─────────────────────────────────────────────────────

    async def shutdown(self):
        """Clean shutdown of all voice resources."""
        log.info("Voice engine shutting down...")
        self._shutdown = True

        # Stop pyttsx3 engine
        if self.tts_engine:
            try:
                with self._tts_lock:
                    self.tts_engine.stop()
            except Exception:
                pass
            self.tts_engine = None

        # Unload Whisper model
        self.whisper_model = None

        log.info("Voice engine shutdown complete")

    # ─── Status ───────────────────────────────────────────────────────

    def get_status(self) -> dict:
        """Get voice engine status."""
        return {
            "mic_available": self._mic_available,
            "mic_device": self._mic_device_index,
            "whisper_loaded": self.whisper_model is not None,
            "tts_engine": settings.TTS_PROVIDER,
            "tts_ready": (
                self.tts_engine is not None
                if settings.TTS_PROVIDER == "pyttsx3"
                else True
            ),
            "wake_word": settings.WAKE_WORD,
            "jarvis_active": self.jarvis_active,
        }
