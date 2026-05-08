"""
J.A.R.V.I.S Backend Entry Point v2.5
Strict startup order: Config → Logging → Memory → Services → Voice → AI → WebSocket → Watchdog
Global exception handler, graceful shutdown, health endpoint.
"""

import asyncio
import json
import sys
import os
import time
import signal
import base64

# Ensure backend dir is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# ── Phase 1: Config + Logging ────────────────────────────────────────
from config.settings import settings
from core.logger import get_logger

log = get_logger("main")

# ── Phase 2: Global Exception Handler ────────────────────────────────
def global_exception_handler(exc_type, exc_value, exc_tb):
    """Catch all unhandled exceptions and log them."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return
    log.critical(f"Unhandled exception: {exc_type.__name__}: {exc_value}")

sys.excepthook = global_exception_handler

# ── Phase 3: FastAPI App ──────────────────────────────────────────────
app = FastAPI(
    title="J.A.R.V.I.S API",
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.DEBUG else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Globals (initialized in startup) ─────────────────────────────────
orchestrator = None
voice_engine = None
watchdog = None
health_monitor = None
system_monitor = None
connected_clients: list[WebSocket] = []


# ── Request Models ────────────────────────────────────────────────────
class CommandRequest(BaseModel):
    text: str

class TTSRequest(BaseModel):
    text: str

class ProfileRequest(BaseModel):
    profile_name: str


# ═══════════════════════════════════════════════════════════════════════
#  STARTUP / SHUTDOWN
# ═══════════════════════════════════════════════════════════════════════

@app.on_event("startup")
async def startup():
    """Strict startup sequence with error isolation per module."""
    global orchestrator, voice_engine, watchdog, health_monitor, system_monitor

    log.info("=" * 60)
    log.info("J.A.R.V.I.S BACKEND STARTING")
    log.info(f"Version: {settings.APP_VERSION}")
    log.info(f"Host: {settings.HOST}:{settings.PORT}")
    log.info(f"AI Provider: {settings.DEFAULT_AI_PROVIDER}")
    log.info("=" * 60)

    # Step 1: Health Monitor
    try:
        from core.health import HealthMonitor
        health_monitor = HealthMonitor()
        log.info("✓ Health monitor initialized")
    except Exception as e:
        log.error(f"✗ Health monitor failed: {e}")

    # Step 2: Voice Engine
    try:
        from voice.engine import VoiceEngine
        voice_engine = VoiceEngine()
        if health_monitor:
            health_monitor.register_engine("voice", voice_engine)
        log.info("✓ Voice engine initialized")
    except Exception as e:
        log.error(f"✗ Voice engine failed: {e}")

    # Step 3: Orchestrator (includes AI, automation, memory, browser, vision)
    try:
        from services.orchestrator import Orchestrator
        orchestrator = Orchestrator()
        await orchestrator.start_services()
        if health_monitor:
            health_monitor.register_engine("ai", orchestrator.ai_provider)
            health_monitor.register_engine("automation", orchestrator.automation)
            health_monitor.register_engine("memory", orchestrator.memory)
        log.info("✓ Orchestrator initialized (AI + automation + memory + services)")
    except Exception as e:
        log.error(f"✗ Orchestrator failed: {e}")

    # Step 4: System Monitor (background stats broadcaster)
    try:
        from services.system_monitor import SystemMonitorService
        system_monitor = SystemMonitorService(interval=5)
        system_monitor.on_stats_update = broadcast_stats
        await system_monitor.start()
        log.info("✓ System monitor started")
    except Exception as e:
        log.error(f"✗ System monitor failed: {e}")

    # Step 5: Watchdog
    try:
        from core.watchdog import Watchdog
        watchdog = Watchdog(check_interval=5)

        if orchestrator:
            watchdog.register(
                "orchestrator",
                lambda: orchestrator is not None,
            )
        if voice_engine:
            watchdog.register(
                "voice",
                lambda: voice_engine is not None,
            )
        if system_monitor:
            watchdog.register(
                "system_monitor",
                lambda: system_monitor._running,
                restart_fn=system_monitor.start,
            )

        await watchdog.start()
        log.info("✓ Watchdog started")
    except Exception as e:
        log.error(f"✗ Watchdog failed: {e}")

    # Step 6: AI Provider health check background task
    try:
        if orchestrator and orchestrator.ai_provider:
            asyncio.create_task(orchestrator.ai_provider.health_check())
            log.info("✓ AI health check loop started")
    except Exception as e:
        log.error(f"✗ AI health check failed: {e}")

    # Step 7: Mic retry loop (if mic not found)
    try:
        if voice_engine and not voice_engine._mic_available:
            asyncio.create_task(voice_engine.start_mic_retry_loop())
            log.info("✓ Mic retry loop started")
    except Exception as e:
        log.error(f"✗ Mic retry failed: {e}")

    log.info("=" * 60)
    log.info("J.A.R.V.I.S BACKEND ONLINE")
    log.info(f"API: http://{settings.HOST}:{settings.PORT}")
    log.info(f"WS:  ws://{settings.HOST}:{settings.PORT}/ws")
    log.info(f"Docs: http://{settings.HOST}:{settings.PORT}/docs")
    log.info("=" * 60)


@app.on_event("shutdown")
async def shutdown():
    """Graceful shutdown of all services."""
    log.info("J.A.R.V.I.S shutting down...")

    if watchdog:
        await watchdog.stop()
    if system_monitor:
        await system_monitor.stop()
    if orchestrator:
        await orchestrator.stop_services()
    if voice_engine:
        await voice_engine.shutdown()

    # Close all WebSocket connections
    for ws in connected_clients[:]:
        try:
            await ws.close()
        except Exception:
            pass
    connected_clients.clear()

    log.info("J.A.R.V.I.S shutdown complete")


# ═══════════════════════════════════════════════════════════════════════
#  WEBSOCKET
# ═══════════════════════════════════════════════════════════════════════

async def broadcast_stats(stats: dict):
    """Broadcast system stats to all connected WebSocket clients."""
    if not connected_clients:
        return
    message = json.dumps({"type": "status", "data": {"system": stats}})
    stale = []
    for ws in connected_clients:
        try:
            await ws.send_text(message)
        except Exception:
            stale.append(ws)
    for ws in stale:
        try:
            connected_clients.remove(ws)
        except ValueError:
            pass


async def send_ws(ws: WebSocket, msg_type: str, data: dict):
    """Send a typed JSON message to a WebSocket client."""
    try:
        await ws.send_json({"type": msg_type, "data": data, "timestamp": time.time()})
    except Exception:
        pass


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connected_clients.append(ws)
    log.info(f"WebSocket client connected ({len(connected_clients)} total)")

    await send_ws(ws, "connected", {
        "message": f"Hello {settings.USER_NAME}, J.A.R.V.I.S is online.",
        "version": settings.APP_VERSION,
    })

    # Send initial status
    if orchestrator:
        try:
            status = await orchestrator.get_system_status()
            await send_ws(ws, "status", status)
        except Exception:
            pass

    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await send_ws(ws, "error", {"message": "Invalid JSON"})
                continue

            msg_type = data.get("type", "")

            if msg_type == "command" and orchestrator:
                text = data.get("text", "").strip()
                if not text:
                    continue

                await send_ws(ws, "state_change", {"state": "thinking"})
                await send_ws(ws, "transcription", {"text": text})

                try:
                    result = await orchestrator.process_command(text)

                    response_text = result.get("ai_response", result.get("message", ""))

                    # Generate TTS audio
                    audio_b64 = None
                    if voice_engine and response_text:
                        try:
                            await send_ws(ws, "state_change", {"state": "speaking"})
                            audio_bytes = await voice_engine.speak(response_text)
                            if audio_bytes:
                                audio_b64 = base64.b64encode(audio_bytes).decode()
                        except Exception as e:
                            log.error(f"TTS failed: {e}")

                    await send_ws(ws, "response", {
                        "success": result.get("success", True),
                        "response_text": response_text,
                        "message": response_text,
                        "intent": result.get("intent", ""),
                        "duration_ms": result.get("duration_ms", 0),
                        "plan_steps": result.get("plan_steps", 1),
                        "audio": audio_b64,
                    })

                except Exception as e:
                    log.error(f"Command execution error: {e}")
                    await send_ws(ws, "response", {
                        "success": False,
                        "response_text": f"Error: {str(e)}",
                        "message": f"Error: {str(e)}",
                    })

                await send_ws(ws, "state_change", {"state": "idle"})

            elif msg_type == "ping":
                await send_ws(ws, "pong", {"time": time.time()})

            elif msg_type == "get_status" and orchestrator:
                status = await orchestrator.get_system_status()
                await send_ws(ws, "status", status)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        log.error(f"WebSocket error: {e}")
    finally:
        if ws in connected_clients:
            connected_clients.remove(ws)
        log.info(f"WebSocket client disconnected ({len(connected_clients)} remaining)")


# ═══════════════════════════════════════════════════════════════════════
#  REST API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════

@app.post("/api/command")
async def api_command(req: CommandRequest):
    """Execute a text command."""
    if not orchestrator:
        raise HTTPException(503, "Orchestrator not initialized")
    result = await orchestrator.process_command(req.text)
    return result


@app.post("/api/tts")
async def api_tts(req: TTSRequest):
    """Generate TTS audio from text."""
    if not voice_engine:
        raise HTTPException(503, "Voice engine not initialized")
    audio_bytes = await voice_engine.speak(req.text)
    if audio_bytes:
        return {"audio": base64.b64encode(audio_bytes).decode(), "format": "mp3"}
    return {"audio": None, "error": "TTS generation failed"}


@app.get("/api/status")
async def api_status():
    """Get system status."""
    if orchestrator:
        return await orchestrator.get_system_status()
    return {"status": "starting", "version": settings.APP_VERSION}


@app.get("/api/health")
async def api_health():
    """Health check endpoint."""
    if health_monitor:
        return health_monitor.get_health()
    return {"status": "ok", "version": settings.APP_VERSION}


@app.get("/api/health/quick")
async def api_health_quick():
    """Quick health check (for load balancers)."""
    if health_monitor:
        return health_monitor.get_quick_health()
    return {"status": "ok"}


@app.get("/api/browser/profiles")
async def api_browser_profiles():
    """Get detected Chrome profiles."""
    if orchestrator:
        profiles = orchestrator.browser.detect_chrome_profiles()
        return {"profiles": profiles, "count": len(profiles)}
    return {"profiles": [], "count": 0}


@app.post("/api/browser/open-profile")
async def api_open_profile(req: ProfileRequest):
    """Open Chrome with a specific profile."""
    if not orchestrator:
        raise HTTPException(503, "Orchestrator not initialized")
    result = await orchestrator.browser.open_chrome_with_profile(req.profile_name)
    return result


@app.get("/api/vision/screen-text")
async def api_screen_text():
    """Read screen text via OCR."""
    if not orchestrator:
        raise HTTPException(503, "Orchestrator not initialized")
    result = await orchestrator.vision.read_screen_text()
    return result


@app.get("/api/vision/active-window")
async def api_active_window():
    """Get info about the active window."""
    if orchestrator and orchestrator.automation.pygetwindow:
        try:
            win = orchestrator.automation.pygetwindow.getActiveWindow()
            if win:
                return {"title": win.title, "position": {"x": win.left, "y": win.top, "w": win.width, "h": win.height}}
        except Exception:
            pass
    return {"title": "Unknown", "position": {}}


@app.get("/api/reminders")
async def api_reminders():
    """Get pending reminders."""
    if orchestrator:
        return {"reminders": orchestrator.reminder_service.get_pending()}
    return {"reminders": []}


@app.get("/api/watchdog")
async def api_watchdog():
    """Get watchdog status."""
    if watchdog:
        return watchdog.get_status()
    return {"watchdog_running": False}


# ═══════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    log.info("Starting J.A.R.V.I.S backend server...")
    try:
        uvicorn.run(
            "main:app",
            host=settings.HOST,
            port=settings.PORT,
            reload=settings.DEBUG,
            log_level="info",
            ws_ping_interval=30,     # Server-side WS ping every 30s
            ws_ping_timeout=10,
        )
    except KeyboardInterrupt:
        log.info("Server stopped by user")
    except Exception as e:
        log.critical(f"Server crash: {e}")
        sys.exit(1)
