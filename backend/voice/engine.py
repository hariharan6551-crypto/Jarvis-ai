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
        self._is_speaking = False
        self._wake_cooldown_until = 0

        # JARVIS active state
        self.jarvis_active = False

        # Callbacks
        self.on_clap: Optional[Callable] = None          # single clap
        self.on_double_clap: Optional[Callable] = None    # double clap
        self.on_triple_clap: Optional[Callable] = None    # triple clap
        self.on_wake_word: Optional[Callable] = None      # "Hey JARVIS"
        self.on_voice_activity: Optional[Callable] = None  # voice detected
        self.on_command: Optional[Callable] = None        # full voice command heard

        # WebSocket broadcast function (set by main.py)
        self.broadcast_fn: Optional[Callable] = None
        
        self._sr_listener_active = False

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
        self._is_speaking = True
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
            # Keep _is_speaking=True for a bit so mic doesn't pick up tail-end
            asyncio.get_event_loop().call_later(2.0, self._clear_speaking)
            return audio
        except Exception as e:
            log.error(f"TTS failed: {e}")
            self._is_speaking = False
            # Auto-reinitialize on crash
            self._reinit_tts()
            # Try one more time with edge-tts as fallback
            try:
                result = await self._speak_edge_tts(text)
                asyncio.get_event_loop().call_later(2.0, self._clear_speaking)
                return result
            except Exception as e2:
                log.error(f"TTS fallback also failed: {e2}")
                self._is_speaking = False
                return None

    def _clear_speaking(self):
        """Clear the speaking flag after TTS finishes (with delay for mic)."""
        self._is_speaking = False

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
        Single clap  → activate JARVIS
        Double clap  → deactivate JARVIS
        Triple clap  → emergency stop all tasks
        """
        if not self._mic_available:
            log.warning("Clap detection unavailable — no microphone")
            return

        log.info("🎤 Starting clap detector (single=ON, double=OFF, triple=EMERGENCY)...")

        try:
            import sounddevice as sd
            import numpy as np

            sample_rate = 44100
            block_size = 2048
            clap_threshold = 0.25      # Raised: prevents false triggers from typing/ambient noise
            clap_cooldown = 0.30       # Min time between claps (seconds)
            multi_clap_window = 0.80   # Window to detect multiple claps

            clap_times = []
            noise_samples = []
            noise_floor = 0.03
            calibrating = True
            calibration_start = time.time()

            def _audio_callback(indata, frames, time_info, status):
                nonlocal noise_floor, calibrating
                if status:
                    return
                try:
                    amplitude = np.abs(indata).max()

                    # Update noise floor (rolling average of quiet samples)
                    if amplitude < 0.08:
                        noise_samples.append(amplitude)
                        if len(noise_samples) > 300:
                            noise_samples.pop(0)
                        if len(noise_samples) > 10:
                            noise_floor = np.mean(noise_samples)

                    # Skip during calibration period
                    if calibrating:
                        return

                    # Adaptive threshold: must be well above noise floor (5x = very strict)
                    adaptive_thresh = max(clap_threshold, noise_floor * 5.0)

                    if amplitude > adaptive_thresh:
                        now = time.time()
                        if clap_times and (now - clap_times[-1]) < clap_cooldown:
                            return
                        clap_times.append(now)
                        log.debug(f"Clap spike: amp={amplitude:.3f} thresh={adaptive_thresh:.3f} floor={noise_floor:.3f}")
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
                # Calibrate noise floor for 2 seconds
                log.info("Calibrating ambient noise level...")
                await asyncio.sleep(2)
                calibrating = False
                log.info(f"✓ Clap detector active (noise_floor={noise_floor:.3f}, threshold={max(clap_threshold, noise_floor * 3.5):.3f})")

                while not self._shutdown:
                    await asyncio.sleep(0.08)

                    if not clap_times:
                        continue

                    now = time.time()
                    if (now - clap_times[-1]) > multi_clap_window:
                        recent = [t for t in clap_times if (now - t) < (multi_clap_window + 0.5)]
                        clap_count = len(recent)
                        clap_times.clear()

                        if clap_count >= 3:
                            log.info("👏👏👏 Triple clap → EMERGENCY STOP")
                            self.jarvis_active = False
                            await self._broadcast_clap_event("triple_clap", "emergency")
                        elif clap_count == 2:
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
            if not self._shutdown:
                log.info("Restarting clap detector in 3s...")
                await asyncio.sleep(3)
                asyncio.create_task(self.start_clap_detector())

    async def _broadcast_clap_event(self, event_type: str, jarvis_state: str):
        """Broadcast clap event to all connected WebSocket clients."""
        if self.broadcast_fn:
            try:
                if jarvis_state == "on":
                    message = f"Hey {settings.USER_NAME}, how can I help you?"
                elif jarvis_state == "emergency":
                    message = f"Emergency stop activated. All tasks halted, {settings.USER_NAME}."
                else:
                    message = f"Going offline {settings.USER_NAME}. Call me anytime."

                payload = {
                    "type": "clap_event",
                    "data": {
                        "event": event_type,
                        "jarvis_active": jarvis_state == "on",
                        "message": message,
                    },
                }
                await self.broadcast_fn(payload)
                log.info(f"Broadcast clap event: {event_type} → {jarvis_state}")
            except Exception as e:
                log.error(f"Broadcast clap event failed: {e}")
        else:
            log.warning("Cannot broadcast clap event: no WebSocket clients")

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

    # ─── Robust Speech Recognition Fallback ───────────────────────────

    async def start_speech_recognition_loop(self):
        """
        Background listener using SpeechRecognition library (like Phase 1).
        This is a robust fallback when Vosk is missing or Electron blocks mic.
        
        RELIABILITY FEATURES:
        - Auto-restarts on any crash (with exponential backoff)
        - Heartbeat watchdog detects frozen threads
        - Mic reconnection on device errors
        - Consecutive failure tracking with pause before retry
        """
        if not self._mic_available:
            log.warning("Speech recognition loop unavailable — no microphone")
            return

        if self._sr_listener_active:
            return

        self._sr_listener_active = True
        self._sr_restart_count = 0
        self._sr_last_heartbeat = time.time()
        log.info("Starting robust backend speech recognition loop (Phase 1 style)...")

        # ━━━ CRITICAL: Capture the MAIN event loop BEFORE launching the thread ━━━
        main_loop = asyncio.get_running_loop()

        def _listen_loop():
            consecutive_errors = 0
            max_consecutive_errors = 10  # Pause after this many errors in a row

            try:
                import speech_recognition as sr
            except ImportError:
                log.error("SpeechRecognition not installed! Run: pip install SpeechRecognition")
                self._sr_listener_active = False
                return

            while not self._shutdown:
                recognizer = sr.Recognizer()
                recognizer.energy_threshold = 300
                recognizer.dynamic_energy_threshold = True
                recognizer.pause_threshold = 0.8

                try:
                    mic = sr.Microphone(device_index=self._mic_device_index)
                    with mic as source:
                        log.info("Calibrating mic for ambient noise...")
                        recognizer.adjust_for_ambient_noise(source, duration=2)
                    
                    log.info("🎤 Backend listener ready. Say 'JARVIS' to activate.")
                    consecutive_errors = 0  # Reset on successful mic init

                    while not self._shutdown:
                        try:
                            # Update heartbeat so watchdog knows we're alive
                            self._sr_last_heartbeat = time.time()

                            # ANTI-FEEDBACK: Skip listening while TTS is playing
                            if self._is_speaking:
                                time.sleep(0.5)
                                continue

                            with mic as source:
                                audio = recognizer.listen(source, timeout=3, phrase_time_limit=10)
                            
                            # Double-check speaking flag after recording
                            if self._is_speaking:
                                continue

                            # Use Google STT (free, internet required)
                            text = recognizer.recognize_google(audio).lower().strip()
                            if not text:
                                continue

                            # Reset error count on successful recognition
                            consecutive_errors = 0

                            # Filter out TTS echo (common JARVIS response fragments)
                            echo_phrases = [
                                "yes sir", "i'm listening", "how can i help",
                                "going offline", "call me anytime", "all systems",
                                "hey hari", "welcome back",
                            ]
                            if any(ep in text for ep in echo_phrases) and not any(w in text for w in ["jarvis"]):
                                log.debug(f"Filtered echo: '{text}'")
                                continue

                            log.info(f"🎤 Heard: '{text}'")
                            
                            # Check for wake word
                            if not self.jarvis_active:
                                wake_words = ["jarvis", "hey jarvis", "j.a.r.v.i.s"]
                                if any(w in text for w in wake_words):
                                    # Cooldown check: don't re-trigger within 5 seconds
                                    now = time.time()
                                    if now < self._wake_cooldown_until:
                                        log.debug(f"Wake word cooldown active, skipping")
                                        continue
                                    self._wake_cooldown_until = now + 5.0

                                    self.jarvis_active = True
                                    log.info("🟢 Wake word detected via SR!")
                                    
                                    # If there's a command after the wake word, process it immediately
                                    cleaned = text.replace("hey jarvis", "").replace("jarvis", "").strip()
                                    if cleaned and len(cleaned) > 2:
                                        # Direct command — send transcription + process
                                        if self.broadcast_fn:
                                            asyncio.run_coroutine_threadsafe(
                                                self.broadcast_fn({
                                                    "type": "transcription",
                                                    "data": {"text": cleaned},
                                                }),
                                                main_loop,
                                            )
                                        if self.on_command:
                                            asyncio.run_coroutine_threadsafe(
                                                self.on_command(cleaned),
                                                main_loop,
                                            )
                                    else:
                                        # Wake word only — notify UI
                                        if self.broadcast_fn:
                                            asyncio.run_coroutine_threadsafe(
                                                self.broadcast_fn({
                                                    "type": "wake_word",
                                                    "data": {
                                                        "text": text,
                                                        "jarvis_active": True,
                                                        "message": f"Yes Sir? I'm listening.",
                                                    },
                                                }),
                                                main_loop,
                                            )
                                continue

                            # If JARVIS is already active, process as a command
                            if self.jarvis_active:
                                # Deactivation checks
                                if any(phrase in text for phrase in ["stop listening", "go to sleep", "turn off", "deactivate"]):
                                    self.jarvis_active = False
                                    self._wake_cooldown_until = time.time() + 5.0
                                    log.info("🔴 JARVIS deactivated via SR.")
                                    if self.broadcast_fn:
                                        asyncio.run_coroutine_threadsafe(
                                            self.broadcast_fn({
                                                "type": "clap_event",
                                                "data": {
                                                    "event": "double_clap",
                                                    "jarvis_active": False,
                                                    "message": "Going offline Sir. Call me anytime.",
                                                },
                                            }),
                                            main_loop,
                                        )
                                    continue
                                
                                # Send transcription to UI first
                                if self.broadcast_fn:
                                    asyncio.run_coroutine_threadsafe(
                                        self.broadcast_fn({
                                            "type": "transcription",
                                            "data": {"text": text},
                                        }),
                                        main_loop,
                                    )
                                
                                # Execute command — use captured main_loop
                                if self.on_command:
                                    asyncio.run_coroutine_threadsafe(
                                        self.on_command(text),
                                        main_loop,
                                    )

                        except sr.WaitTimeoutError:
                            continue
                        except sr.UnknownValueError:
                            continue
                        except sr.RequestError as e:
                            consecutive_errors += 1
                            log.warning(f"Google STT error ({consecutive_errors}x): {e}")
                            if consecutive_errors >= max_consecutive_errors:
                                log.warning(f"Too many STT errors ({consecutive_errors}), pausing 30s...")
                                time.sleep(30)
                                consecutive_errors = 0
                            else:
                                time.sleep(2)
                        except OSError as e:
                            # Microphone disconnected / device error
                            log.error(f"Microphone device error: {e}")
                            consecutive_errors += 1
                            break  # Break inner loop to re-init mic
                        except Exception as e:
                            consecutive_errors += 1
                            log.warning(f"SR Loop error ({consecutive_errors}x): {e}")
                            if consecutive_errors >= max_consecutive_errors:
                                log.warning(f"Too many SR errors, pausing 30s...")
                                time.sleep(30)
                                consecutive_errors = 0
                            else:
                                time.sleep(1)
                            
                except Exception as e:
                    log.error(f"SR loop mic init error: {e}")

                # ━━━ AUTO-RESTART with backoff ━━━
                if not self._shutdown:
                    self._sr_restart_count += 1
                    backoff = min(30, 2 ** min(self._sr_restart_count, 5))  # 2, 4, 8, 16, 30, 30...
                    log.warning(
                        f"SR loop crashed (restart #{self._sr_restart_count}). "
                        f"Re-detecting mic and restarting in {backoff}s..."
                    )
                    time.sleep(backoff)

                    # Re-detect microphone (may have been unplugged/replugged)
                    self._detect_mic()
                    if not self._mic_available:
                        log.warning("Mic not found on re-detect. Will retry in 10s...")
                        time.sleep(10)
                        self._detect_mic()
                        if not self._mic_available:
                            log.error("Mic still unavailable. SR loop stopping.")
                            break

            self._sr_listener_active = False
            log.info("SR loop thread exiting.")

        threading.Thread(target=_listen_loop, daemon=True, name="jarvis-sr-loop").start()

        # ━━━ Heartbeat Watchdog: restart SR loop if it freezes ━━━
        asyncio.create_task(self._sr_watchdog(main_loop))

    async def _sr_watchdog(self, main_loop):
        """
        Watchdog that monitors the SR listener thread.
        If the thread hasn't sent a heartbeat in 60s, force-restart it.
        """
        log.info("SR watchdog started — monitoring listener health every 30s")
        while not self._shutdown:
            await asyncio.sleep(30)

            if not self._sr_listener_active:
                # SR loop died and didn't restart itself
                log.warning("⚠ SR watchdog: listener is DEAD. Attempting restart...")
                self._detect_mic()
                if self._mic_available:
                    await self.start_speech_recognition_loop()
                else:
                    log.warning("SR watchdog: no mic available, will check again in 30s")
                continue

            # Check heartbeat freshness
            if hasattr(self, '_sr_last_heartbeat'):
                elapsed = time.time() - self._sr_last_heartbeat
                if elapsed > 60:
                    log.warning(
                        f"⚠ SR watchdog: no heartbeat for {elapsed:.0f}s — listener may be frozen. "
                        f"Forcing restart..."
                    )
                    # Mark as dead so next iteration restarts it
                    self._sr_listener_active = False

        log.info("SR watchdog stopped.")

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
