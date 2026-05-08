"""
J.A.R.V.I.S Voice Engine
Speech recognition using Whisper + TTS using Edge-TTS / pyttsx3.
"""

import asyncio
import io
import os
import tempfile
import wave
import struct
import base64
from pathlib import Path
from typing import Optional
from core.logger import get_logger
from config.settings import settings

log = get_logger("voice")


class VoiceEngine:
    """Handles speech-to-text and text-to-speech."""

    def __init__(self):
        self.whisper_model = None
        self.tts_engine = None
        self._init_tts()
        log.info("Voice engine initialized")

    def _init_tts(self):
        """Initialize TTS engine."""
        if settings.TTS_PROVIDER == "pyttsx3":
            try:
                import pyttsx3
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty("rate", 175)
                self.tts_engine.setProperty("volume", 0.9)
                voices = self.tts_engine.getProperty("voices")
                # Try to find a male voice
                for voice in voices:
                    if "male" in voice.name.lower() or "david" in voice.name.lower():
                        self.tts_engine.setProperty("voice", voice.id)
                        break
                log.info("pyttsx3 TTS initialized")
            except Exception as e:
                log.warning(f"pyttsx3 init failed: {e}")

    async def load_whisper(self):
        """Lazy load Whisper model."""
        if self.whisper_model is None:
            try:
                import whisper
                log.info(f"Loading Whisper model: {settings.WHISPER_MODEL}")
                self.whisper_model = await asyncio.to_thread(
                    whisper.load_model, settings.WHISPER_MODEL
                )
                log.info("Whisper model loaded successfully")
            except Exception as e:
                log.error(f"Failed to load Whisper: {e}")

    async def transcribe(self, audio_data: bytes, sample_rate: int = 16000) -> str:
        """Transcribe audio bytes to text using Whisper."""
        try:
            # Try Whisper first
            if self.whisper_model is None:
                await self.load_whisper()

            if self.whisper_model:
                return await self._transcribe_whisper(audio_data, sample_rate)

            # Fallback to OpenAI API
            if settings.OPENAI_API_KEY:
                return await self._transcribe_openai_api(audio_data, sample_rate)

            return ""
        except Exception as e:
            log.error(f"Transcription failed: {e}")
            return ""

    async def _transcribe_whisper(self, audio_data: bytes, sample_rate: int) -> str:
        """Transcribe using local Whisper model."""
        import numpy as np

        # Convert bytes to float32 numpy array
        audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0

        result = await asyncio.to_thread(
            self.whisper_model.transcribe,
            audio_array,
            language="en",
            fp16=False,
        )
        text = result.get("text", "").strip()
        log.info(f"Transcribed: {text}")
        return text

    async def _transcribe_openai_api(self, audio_data: bytes, sample_rate: int) -> str:
        """Transcribe using OpenAI Whisper API."""
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        # Create WAV file in memory
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
        text = response.text.strip()
        log.info(f"Transcribed (API): {text}")
        return text

    async def speak(self, text: str) -> Optional[bytes]:
        """Convert text to speech audio bytes."""
        try:
            if settings.TTS_PROVIDER == "edge":
                return await self._speak_edge_tts(text)
            elif settings.TTS_PROVIDER == "elevenlabs" and settings.ELEVENLABS_API_KEY:
                return await self._speak_elevenlabs(text)
            elif settings.TTS_PROVIDER == "pyttsx3" and self.tts_engine:
                return await self._speak_pyttsx3(text)
            else:
                # Default to edge-tts
                return await self._speak_edge_tts(text)
        except Exception as e:
            log.error(f"TTS failed: {e}")
            return None

    async def _speak_edge_tts(self, text: str) -> bytes:
        """Generate speech using Edge TTS (free, high quality)."""
        import edge_tts

        communicate = edge_tts.Communicate(text, settings.EDGE_TTS_VOICE)
        audio_data = b""

        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]

        log.debug(f"Edge TTS generated {len(audio_data)} bytes")
        return audio_data

    async def _speak_elevenlabs(self, text: str) -> bytes:
        """Generate speech using ElevenLabs API."""
        import httpx

        async with httpx.AsyncClient() as client:
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
            return response.content

    async def _speak_pyttsx3(self, text: str) -> Optional[bytes]:
        """Generate speech using pyttsx3 (offline)."""
        if not self.tts_engine:
            return None

        temp_file = tempfile.mktemp(suffix=".wav")
        try:
            await asyncio.to_thread(self.tts_engine.save_to_file, text, temp_file)
            await asyncio.to_thread(self.tts_engine.runAndWait)

            with open(temp_file, "rb") as f:
                return f.read()
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
