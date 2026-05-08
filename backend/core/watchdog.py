"""
J.A.R.V.I.S Watchdog Service
Monitors all background services every 5 seconds.
Auto-restarts crashed services and logs all events.
"""

import asyncio
import time
from typing import Dict, Callable, Optional
from core.logger import get_logger

log = get_logger("watchdog")


class ServiceInfo:
    """Tracks a single registered service."""

    def __init__(self, name: str, health_check: Callable, restart_fn: Optional[Callable] = None):
        self.name = name
        self.health_check = health_check
        self.restart_fn = restart_fn
        self.status = "starting"      # starting, running, degraded, crashed, stopped
        self.last_check = 0.0
        self.last_restart = 0.0
        self.restart_count = 0
        self.max_restarts = 5         # Max auto-restarts before giving up
        self.crash_count = 0
        self.uptime_start = time.time()

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "restart_count": self.restart_count,
            "crash_count": self.crash_count,
            "uptime_seconds": round(time.time() - self.uptime_start, 1),
            "last_check": self.last_check,
        }


class Watchdog:
    """Monitors and auto-restarts JARVIS services."""

    def __init__(self, check_interval: int = 5):
        self._services: Dict[str, ServiceInfo] = {}
        self._check_interval = check_interval
        self._running = False
        self._task = None
        log.info(f"Watchdog initialized (check interval: {check_interval}s)")

    def register(
        self,
        name: str,
        health_check: Callable,
        restart_fn: Optional[Callable] = None,
    ):
        """
        Register a service to be monitored.
        health_check: async or sync callable that returns True if healthy.
        restart_fn: async or sync callable to restart the service.
        """
        self._services[name] = ServiceInfo(name, health_check, restart_fn)
        log.info(f"Watchdog registered service: {name}")

    def unregister(self, name: str):
        """Unregister a service."""
        if name in self._services:
            del self._services[name]
            log.info(f"Watchdog unregistered service: {name}")

    async def start(self):
        """Start the watchdog monitoring loop."""
        if self._running:
            log.warning("Watchdog already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        log.info("Watchdog started")

    async def stop(self):
        """Stop the watchdog."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        log.info("Watchdog stopped")

    async def _monitor_loop(self):
        """Main monitoring loop — checks every service every N seconds."""
        while self._running:
            try:
                for name, service in list(self._services.items()):
                    try:
                        await self._check_service(service)
                    except Exception as e:
                        log.error(f"Watchdog check error for {name}: {e}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Watchdog loop error: {e}")

            await asyncio.sleep(self._check_interval)

    async def _check_service(self, service: ServiceInfo):
        """Check a single service's health."""
        service.last_check = time.time()

        try:
            # Call health check (supports both async and sync)
            if asyncio.iscoroutinefunction(service.health_check):
                healthy = await asyncio.wait_for(
                    service.health_check(),
                    timeout=5
                )
            else:
                healthy = await asyncio.to_thread(service.health_check)

            if healthy:
                if service.status != "running":
                    log.info(f"Service '{service.name}' is now running")
                service.status = "running"
            else:
                service.status = "degraded"
                service.crash_count += 1
                log.warning(f"Service '{service.name}' health check returned unhealthy")
                await self._try_restart(service)

        except asyncio.TimeoutError:
            service.status = "degraded"
            log.warning(f"Service '{service.name}' health check timed out")
            await self._try_restart(service)

        except Exception as e:
            service.status = "crashed"
            service.crash_count += 1
            log.error(f"Service '{service.name}' crashed: {e}")
            await self._try_restart(service)

    async def _try_restart(self, service: ServiceInfo):
        """Attempt to restart a crashed service."""
        if not service.restart_fn:
            log.warning(f"No restart function for service '{service.name}'")
            return

        if service.restart_count >= service.max_restarts:
            service.status = "stopped"
            log.error(
                f"Service '{service.name}' exceeded max restarts "
                f"({service.max_restarts}). Giving up."
            )
            return

        # Cooldown: don't restart more than once every 10 seconds
        if time.time() - service.last_restart < 10:
            return

        service.restart_count += 1
        service.last_restart = time.time()
        log.info(
            f"Restarting service '{service.name}' "
            f"(attempt {service.restart_count}/{service.max_restarts})"
        )

        try:
            if asyncio.iscoroutinefunction(service.restart_fn):
                await service.restart_fn()
            else:
                await asyncio.to_thread(service.restart_fn)

            service.status = "running"
            service.uptime_start = time.time()
            log.info(f"Service '{service.name}' restarted successfully")

        except Exception as e:
            service.status = "crashed"
            log.error(f"Failed to restart service '{service.name}': {e}")

    # ─── Status ───────────────────────────────────────────────────────

    def get_status(self) -> dict:
        """Get status of all monitored services."""
        return {
            "watchdog_running": self._running,
            "check_interval": self._check_interval,
            "services": {
                name: info.to_dict()
                for name, info in self._services.items()
            },
        }

    def get_service_status(self, name: str) -> Optional[dict]:
        """Get status of a specific service."""
        if name in self._services:
            return self._services[name].to_dict()
        return None

    def is_all_healthy(self) -> bool:
        """Check if all services are running."""
        return all(
            s.status in ("running", "starting")
            for s in self._services.values()
        )
