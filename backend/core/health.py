"""
J.A.R.V.I.S Health Monitor
Provides system-wide health data for the /health API endpoint.
Aggregates status from all engines: voice, AI, automation, memory.
"""

import time
import platform
from typing import Optional
from core.logger import get_logger

log = get_logger("health")


class HealthMonitor:
    """Aggregates health status from all JARVIS subsystems."""

    def __init__(self):
        self._start_time = time.time()
        self._engines = {}
        self._last_check_time = 0
        self._cached_status = None
        self._cache_ttl = 2  # seconds
        log.info("Health monitor initialized")

    def register_engine(self, name: str, engine):
        """Register an engine for health monitoring."""
        self._engines[name] = engine
        log.debug(f"Registered engine for health monitoring: {name}")

    def unregister_engine(self, name: str):
        """Unregister an engine."""
        if name in self._engines:
            del self._engines[name]

    def get_health(self) -> dict:
        """
        Get comprehensive health status.
        Cached for 2 seconds to avoid excessive polling.
        """
        now = time.time()
        if self._cached_status and (now - self._last_check_time) < self._cache_ttl:
            return self._cached_status

        status = {
            "status": "healthy",
            "uptime_seconds": round(now - self._start_time, 1),
            "uptime_human": self._format_uptime(now - self._start_time),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "platform": {
                "system": platform.system(),
                "release": platform.release(),
                "version": platform.version(),
                "machine": platform.machine(),
                "python": platform.python_version(),
            },
            "engines": {},
        }

        # Check each registered engine
        degraded = False
        failed = False

        for name, engine in self._engines.items():
            try:
                if hasattr(engine, "get_status"):
                    engine_status = engine.get_status()
                    status["engines"][name] = {
                        "status": "running",
                        "details": engine_status,
                    }
                elif hasattr(engine, "get_health_status"):
                    engine_status = engine.get_health_status()
                    status["engines"][name] = {
                        "status": "running",
                        "details": engine_status,
                    }
                else:
                    status["engines"][name] = {
                        "status": "running" if engine is not None else "stopped",
                        "details": {},
                    }
            except Exception as e:
                status["engines"][name] = {
                    "status": "error",
                    "error": str(e),
                }
                degraded = True
                log.warning(f"Engine '{name}' health check failed: {e}")

        # Overall status
        if failed:
            status["status"] = "unhealthy"
        elif degraded:
            status["status"] = "degraded"

        self._cached_status = status
        self._last_check_time = now
        return status

    def get_quick_health(self) -> dict:
        """Quick health check (for load balancers / monitors)."""
        return {
            "status": "ok",
            "uptime": round(time.time() - self._start_time, 1),
        }

    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human-readable form."""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{secs}s")
        return " ".join(parts)

    @property
    def uptime(self) -> float:
        return time.time() - self._start_time
