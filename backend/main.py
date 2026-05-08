"""
J.A.R.V.I.S FastAPI Backend Server v2.0
REST API + WebSocket with browser automation, vision, and multi-step planning.
"""

import asyncio
import json
import sys
import os
import base64
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from core.logger import get_logger
from config.settings import settings
from services.orchestrator import Orchestrator
from voice.engine import VoiceEngine

log = get_logger("server")

# ─── FastAPI App ──────────────────────────────────────────────────────

app = FastAPI(
    title="J.A.R.V.I.S API",
    description="Advanced AI Desktop Assistant Backend v2.0",
    version=settings.APP_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Global State ────────────────────────────────────────────────────

orchestrator: Optional[Orchestrator] = None
voice_engine: Optional[VoiceEngine] = None
connected_clients: list[WebSocket] = []


# ─── Startup / Shutdown ─────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    global orchestrator, voice_engine
    log.info("=" * 60)
    log.info("  J.A.R.V.I.S v2.0 SYSTEM INITIALIZING")
    log.info("=" * 60)

    orchestrator = Orchestrator()
    voice_engine = VoiceEngine()

    log.info(f"Server ready on {settings.HOST}:{settings.PORT}")
    log.info(f"AI Provider: {settings.DEFAULT_AI_PROVIDER}")
    log.info(f"TTS Provider: {settings.TTS_PROVIDER}")
    log.info(f"Browser profiles: {len(orchestrator.browser.detect_chrome_profiles())}")
    log.info("=" * 60)
    log.info("  J.A.R.V.I.S v2.0 SYSTEM ONLINE")
    log.info("=" * 60)


@app.on_event("shutdown")
async def shutdown():
    log.info("J.A.R.V.I.S shutting down...")
    for client in connected_clients:
        try:
            await client.close()
        except Exception:
            pass


# ─── Models ──────────────────────────────────────────────────────────

class CommandRequest(BaseModel):
    text: str
    provider: Optional[str] = None
    model: Optional[str] = None

class TTSRequest(BaseModel):
    text: str

class ProfileRequest(BaseModel):
    profile_name: str


# ─── REST Endpoints ─────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"status": "online", "name": "J.A.R.V.I.S", "version": settings.APP_VERSION}

@app.get("/api/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/status")
async def system_status():
    if orchestrator:
        status = await orchestrator.get_system_status()
        return status
    return {"error": "System not initialized"}

@app.post("/api/command")
async def execute_command(request: CommandRequest):
    """Execute a text command through the v2.0 pipeline."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")

    result = await orchestrator.process_command(request.text)

    await broadcast({
        "type": "command_result",
        "data": result,
    })

    return result

@app.post("/api/tts")
async def text_to_speech(request: TTSRequest):
    """Generate speech audio from text."""
    if not voice_engine:
        raise HTTPException(status_code=503, detail="Voice engine not ready")

    audio_data = await voice_engine.speak(request.text)
    if audio_data:
        audio_b64 = base64.b64encode(audio_data).decode("utf-8")
        return {"audio": audio_b64, "format": "mp3"}
    return {"error": "TTS generation failed"}

@app.post("/api/transcribe")
async def transcribe_audio(request: dict):
    """Transcribe audio data to text."""
    if not voice_engine:
        raise HTTPException(status_code=503, detail="Voice engine not ready")

    audio_b64 = request.get("audio", "")
    sample_rate = request.get("sample_rate", 16000)
    audio_bytes = base64.b64decode(audio_b64)
    text = await voice_engine.transcribe(audio_bytes, sample_rate)
    return {"text": text}

@app.get("/api/providers")
async def get_providers():
    """Get available AI providers."""
    if orchestrator:
        return {
            "providers": orchestrator.ai_provider.get_available_providers(),
            "default": settings.DEFAULT_AI_PROVIDER,
        }
    return {"providers": [], "default": None}

@app.get("/api/history")
async def get_history():
    """Get conversation history."""
    if orchestrator:
        messages = orchestrator.memory.get_recent_messages(limit=50)
        return {"messages": messages}
    return {"messages": []}

# ─── Browser Profile Endpoints (NEW v2.0) ────────────────────────────

@app.get("/api/browser/profiles")
async def get_browser_profiles():
    """Get all detected Chrome profiles."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    return await orchestrator.browser.list_profiles()

@app.post("/api/browser/open-profile")
async def open_browser_profile(request: ProfileRequest):
    """Open Chrome with a specific profile."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    return await orchestrator.browser.open_chrome_with_profile(request.profile_name)

# ─── Vision Endpoints (NEW v2.0) ─────────────────────────────────────

@app.get("/api/vision/screen-text")
async def read_screen():
    """Read text from the current screen via OCR."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    return await orchestrator.vision.read_screen_text()

@app.get("/api/vision/active-window")
async def active_window_info():
    """Get active window information."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    return await orchestrator.vision.get_active_window_info()

@app.get("/api/vision/windows")
async def list_windows():
    """List all open windows."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    return await orchestrator.vision.list_all_windows()

@app.post("/api/vision/find-text")
async def find_text_on_screen(request: dict):
    """Find text on screen using OCR."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    text = request.get("text", "")
    return await orchestrator.vision.find_text_on_screen(text)

# ─── Preferences Endpoints (NEW v2.0) ────────────────────────────────

@app.get("/api/preferences/frequent-apps")
async def frequent_apps():
    """Get most frequently used apps."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    return {"apps": orchestrator.preferences.get_frequent_apps(10)}

@app.get("/api/preferences/context")
async def user_context():
    """Get user context for personalization."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="System not initialized")
    return orchestrator.preferences.get_user_context()


# ─── WebSocket ───────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """Real-time WebSocket communication channel."""
    await ws.accept()
    connected_clients.append(ws)
    log.info(f"Client connected. Total: {len(connected_clients)}")

    await ws.send_json({
        "type": "connected",
        "data": {
            "message": "J.A.R.V.I.S v2.0 WebSocket connected",
            "version": settings.APP_VERSION,
            "user": settings.USER_NAME,
        },
    })

    try:
        while True:
            data = await ws.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "command":
                text = data.get("text", "")
                if text:
                    await ws.send_json({"type": "state_change", "data": {"state": "thinking"}})

                    result = await orchestrator.process_command(text)

                    response_text = result.get("ai_response", result.get("message", ""))
                    audio_b64 = None

                    if response_text:
                        await ws.send_json({"type": "state_change", "data": {"state": "speaking"}})
                        audio_data = await voice_engine.speak(response_text)
                        if audio_data:
                            audio_b64 = base64.b64encode(audio_data).decode("utf-8")

                    await ws.send_json({
                        "type": "response",
                        "data": {
                            **result,
                            "response_text": response_text,
                            "audio": audio_b64,
                        },
                    })

                    await ws.send_json({"type": "state_change", "data": {"state": "idle"}})

            elif msg_type == "audio":
                audio_b64 = data.get("audio", "")
                if audio_b64:
                    await ws.send_json({"type": "state_change", "data": {"state": "listening"}})

                    audio_bytes = base64.b64decode(audio_b64)
                    text = await voice_engine.transcribe(audio_bytes)

                    if text:
                        await ws.send_json({
                            "type": "transcription",
                            "data": {"text": text},
                        })

                        await ws.send_json({"type": "state_change", "data": {"state": "thinking"}})
                        result = await orchestrator.process_command(text)

                        response_text = result.get("ai_response", result.get("message", ""))
                        audio_b64 = None

                        if response_text:
                            await ws.send_json({"type": "state_change", "data": {"state": "speaking"}})
                            audio_data = await voice_engine.speak(response_text)
                            if audio_data:
                                audio_b64 = base64.b64encode(audio_data).decode("utf-8")

                        await ws.send_json({
                            "type": "response",
                            "data": {
                                **result,
                                "response_text": response_text,
                                "audio": audio_b64,
                            },
                        })

                    await ws.send_json({"type": "state_change", "data": {"state": "idle"}})

            elif msg_type == "status":
                status = await orchestrator.get_system_status()
                await ws.send_json({"type": "status", "data": status})

            elif msg_type == "get_profiles":
                profiles = orchestrator.browser.detect_chrome_profiles()
                await ws.send_json({"type": "profiles", "data": {"profiles": profiles}})

            elif msg_type == "ping":
                await ws.send_json({"type": "pong", "data": {"timestamp": time.time()}})

    except WebSocketDisconnect:
        log.info("Client disconnected")
    except Exception as e:
        log.error(f"WebSocket error: {e}")
    finally:
        if ws in connected_clients:
            connected_clients.remove(ws)


async def broadcast(message: dict):
    """Broadcast message to all connected WebSocket clients."""
    disconnected = []
    for client in connected_clients:
        try:
            await client.send_json(message)
        except Exception:
            disconnected.append(client)
    for client in disconnected:
        connected_clients.remove(client)


# ─── Entry Point ─────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
    )
