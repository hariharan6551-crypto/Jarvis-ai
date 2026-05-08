"""
J.A.R.V.I.S System Monitor Service
Periodically collects CPU, RAM, disk, battery, and network stats.
Broadcasts to connected WebSocket clients for real-time dashboard updates.
"""

import asyncio
import time
from typing import Optional, Callable
from core.logger import get_logger

log = get_logger("sysmon")


class SystemMonitorService:
    """Background service that broadcasts system stats periodically."""

    def __init__(self, interval: int = 5):
        self._interval = interval
        self._running = False
        self._task = None
        self._latest_stats = {}
        self._last_update = 0
        self.on_stats_update: Optional[Callable] = None  # async callback(stats_dict)
        log.info(f"System monitor initialized (interval: {interval}s)")

    async def start(self):
        """Start the monitor loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop())
        log.info("System monitor started")

    async def stop(self):
        """Stop the monitor."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        log.info("System monitor stopped")

    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self._running:
            try:
                stats = await self._collect_stats()
                self._latest_stats = stats
                self._last_update = time.time()

                if self.on_stats_update:
                    try:
                        if asyncio.iscoroutinefunction(self.on_stats_update):
                            await self.on_stats_update(stats)
                        else:
                            self.on_stats_update(stats)
                    except Exception as e:
                        log.debug(f"Stats callback error: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"System monitor error: {e}")

            await asyncio.sleep(self._interval)

    async def _collect_stats(self) -> dict:
        """Collect all system statistics."""
        try:
            import psutil

            cpu_freq = psutil.cpu_freq()
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("C:\\")
            net = psutil.net_io_counters()

            battery = {"percent": None, "plugged_in": False, "time_left": "N/A"}
            try:
                bat = psutil.sensors_battery()
                if bat:
                    battery = {
                        "percent": bat.percent,
                        "plugged_in": bat.power_plugged,
                        "time_left": f"{bat.secsleft // 60} min" if bat.secsleft > 0 else "N/A",
                    }
            except Exception:
                pass

            # Top 5 CPU-consuming processes
            procs = []
            try:
                for p in psutil.process_iter(["name", "cpu_percent", "memory_percent"]):
                    try:
                        info = p.info
                        if info.get("cpu_percent", 0) > 0:
                            procs.append({
                                "name": info["name"],
                                "cpu_percent": round(info["cpu_percent"], 1),
                                "memory_percent": round(info.get("memory_percent", 0), 1),
                            })
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                procs = sorted(procs, key=lambda x: x["cpu_percent"], reverse=True)[:5]
            except Exception:
                pass

            return {
                "cpu": {
                    "usage_percent": psutil.cpu_percent(interval=0.3),
                    "cores": psutil.cpu_count(),
                    "physical_cores": psutil.cpu_count(logical=False),
                    "frequency_mhz": round(cpu_freq.current) if cpu_freq else 0,
                },
                "memory": {
                    "total_gb": round(mem.total / (1024**3), 1),
                    "used_gb": round(mem.used / (1024**3), 1),
                    "available_gb": round(mem.available / (1024**3), 1),
                    "usage_percent": mem.percent,
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 1),
                    "used_gb": round(disk.used / (1024**3), 1),
                    "free_gb": round(disk.free / (1024**3), 1),
                    "usage_percent": round(disk.percent, 1),
                },
                "battery": battery,
                "network": {
                    "bytes_sent_mb": round(net.bytes_sent / (1024**2), 1),
                    "bytes_recv_mb": round(net.bytes_recv / (1024**2), 1),
                },
                "top_processes": procs,
                "timestamp": time.strftime("%H:%M:%S"),
            }
        except ImportError:
            log.warning("psutil not installed")
            return {"error": "psutil not installed"}
        except Exception as e:
            log.error(f"Stats collection failed: {e}")
            return {"error": str(e)}

    def get_latest_stats(self) -> dict:
        """Get the most recently collected stats."""
        return self._latest_stats

    def get_status(self) -> dict:
        return {
            "running": self._running,
            "interval": self._interval,
            "last_update": time.strftime("%H:%M:%S", time.localtime(self._last_update)) if self._last_update else None,
        }
