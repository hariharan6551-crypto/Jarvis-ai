"""
J.A.R.V.I.S Desktop Automation Engine
Complete Windows PC control: apps, files, system, media, browser.
"""

import asyncio
import os
import subprocess
import time
import json
from pathlib import Path
from typing import Optional
from core.logger import get_logger
from config.settings import settings

log = get_logger("automation")


class AutomationEngine:
    """Full desktop automation controller for Windows."""

    def __init__(self):
        self._import_modules()
        log.info("Automation engine initialized")

    def _import_modules(self):
        """Lazy import automation modules."""
        try:
            import pyautogui
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.1
            self.pyautogui = pyautogui
        except ImportError:
            self.pyautogui = None
            log.warning("pyautogui not available")

        try:
            import psutil
            self.psutil = psutil
        except ImportError:
            self.psutil = None
            log.warning("psutil not available")

    # ─── Application Management ───────────────────────────────────────

    async def open_application(self, app: str) -> dict:
        """Open an application by name or path."""
        log.info(f"Opening application: {app}")

        special_folders = {
            "explorer_downloads": os.path.expanduser("~\\Downloads"),
            "explorer_documents": os.path.expanduser("~\\Documents"),
            "explorer_desktop": os.path.expanduser("~\\Desktop"),
        }

        try:
            if app in special_folders:
                os.startfile(special_folders[app])
                folder_name = app.replace("explorer_", "").title()
                return {"success": True, "message": f"Opened {folder_name} folder"}

            if app.startswith("ms-settings"):
                os.startfile(app)
                return {"success": True, "message": "Opened Windows Settings"}

            # Try common app locations
            app_commands = {
                "chrome": "start chrome",
                "firefox": "start firefox",
                "msedge": "start msedge",
                "code": "code",
                "notepad": "notepad",
                "calc": "calc",
                "mspaint": "mspaint",
                "explorer": "explorer",
                "cmd": "start cmd",
                "wt": "wt",
                "powershell": "start powershell",
                "taskmgr": "taskmgr",
                "snippingtool": "snippingtool",
                "control": "control",
                "spotify": "start spotify:",
                "discord": "start discord:",
                "slack": "start slack:",
                "teams": "start msteams:",
                "whatsapp": "start whatsapp:",
                "telegram": "start telegram:",
                "zoom": "start zoommtg:",
            }

            cmd = app_commands.get(app, f"start {app}")
            await asyncio.to_thread(
                subprocess.Popen, cmd, shell=True,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )

            app_display = app.replace("ms-settings:", "Settings").title()
            return {"success": True, "message": f"Opening {app_display}"}

        except Exception as e:
            log.error(f"Failed to open {app}: {e}")
            return {"success": False, "message": f"Failed to open {app}: {str(e)}"}

    async def close_application(self, app: str) -> dict:
        """Close an application by name."""
        log.info(f"Closing application: {app}")

        process_map = {
            "chrome": "chrome.exe",
            "firefox": "firefox.exe",
            "msedge": "msedge.exe",
            "code": "Code.exe",
            "notepad": "notepad.exe",
            "spotify": "Spotify.exe",
            "discord": "Discord.exe",
            "slack": "slack.exe",
            "teams": "Teams.exe",
            "whatsapp": "WhatsApp.exe",
        }

        process_name = process_map.get(app, f"{app}.exe")

        try:
            result = await asyncio.to_thread(
                subprocess.run,
                f"taskkill /IM {process_name} /F",
                shell=True, capture_output=True, text=True
            )
            if result.returncode == 0:
                return {"success": True, "message": f"Closed {app}"}
            else:
                return {"success": False, "message": f"Could not find {app} running"}
        except Exception as e:
            log.error(f"Failed to close {app}: {e}")
            return {"success": False, "message": f"Failed to close {app}: {str(e)}"}

    # ─── Web Search ───────────────────────────────────────────────────

    async def search_web(self, query: str) -> dict:
        """Search Google in default browser."""
        import urllib.parse
        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        try:
            os.startfile(url)
            return {"success": True, "message": f"Searching Google for: {query}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def search_youtube(self, query: str) -> dict:
        """Search YouTube in default browser."""
        import urllib.parse
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
        try:
            os.startfile(url)
            return {"success": True, "message": f"Searching YouTube for: {query}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # ─── Volume Control ───────────────────────────────────────────────

    async def volume_up(self, amount: int = 10) -> dict:
        """Increase system volume."""
        try:
            if self.pyautogui:
                for _ in range(amount // 2):
                    self.pyautogui.press("volumeup")
            return {"success": True, "message": f"Volume increased by {amount}%"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def volume_down(self, amount: int = 10) -> dict:
        """Decrease system volume."""
        try:
            if self.pyautogui:
                for _ in range(amount // 2):
                    self.pyautogui.press("volumedown")
            return {"success": True, "message": f"Volume decreased by {amount}%"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def volume_mute(self) -> dict:
        """Toggle mute."""
        try:
            if self.pyautogui:
                self.pyautogui.press("volumemute")
            return {"success": True, "message": "Volume muted/unmuted"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # ─── Brightness Control ───────────────────────────────────────────

    async def brightness_up(self, amount: int = 20) -> dict:
        """Increase screen brightness."""
        try:
            import screen_brightness_control as sbc
            current = sbc.get_brightness()[0]
            new_val = min(100, current + amount)
            sbc.set_brightness(new_val)
            return {"success": True, "message": f"Brightness set to {new_val}%"}
        except Exception as e:
            log.warning(f"Brightness control failed: {e}")
            return {"success": False, "message": "Brightness control not available on this device"}

    async def brightness_down(self, amount: int = 20) -> dict:
        """Decrease screen brightness."""
        try:
            import screen_brightness_control as sbc
            current = sbc.get_brightness()[0]
            new_val = max(0, current - amount)
            sbc.set_brightness(new_val)
            return {"success": True, "message": f"Brightness set to {new_val}%"}
        except Exception as e:
            return {"success": False, "message": "Brightness control not available on this device"}

    # ─── Screenshot ───────────────────────────────────────────────────

    async def take_screenshot(self) -> dict:
        """Capture screen screenshot."""
        try:
            if self.pyautogui:
                screenshots_dir = Path.home() / "Pictures" / "JARVIS_Screenshots"
                screenshots_dir.mkdir(parents=True, exist_ok=True)
                filename = f"screenshot_{int(time.time())}.png"
                filepath = screenshots_dir / filename
                screenshot = self.pyautogui.screenshot()
                screenshot.save(str(filepath))
                return {
                    "success": True,
                    "message": f"Screenshot saved to {filepath}",
                    "path": str(filepath),
                }
            return {"success": False, "message": "Screenshot module not available"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # ─── System Commands ──────────────────────────────────────────────

    async def shutdown_pc(self, confirm: bool = True) -> dict:
        """Shutdown the PC."""
        if confirm:
            return {
                "success": True,
                "message": "Are you sure you want to shut down? Say 'confirm shutdown' to proceed.",
                "requires_confirmation": True,
                "action": "shutdown",
            }
        try:
            os.system("shutdown /s /t 5")
            return {"success": True, "message": "Shutting down in 5 seconds..."}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def restart_pc(self, confirm: bool = True) -> dict:
        """Restart the PC."""
        if confirm:
            return {
                "success": True,
                "message": "Are you sure you want to restart? Say 'confirm restart' to proceed.",
                "requires_confirmation": True,
                "action": "restart",
            }
        try:
            os.system("shutdown /r /t 5")
            return {"success": True, "message": "Restarting in 5 seconds..."}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def lock_pc(self) -> dict:
        """Lock the PC."""
        try:
            import ctypes
            ctypes.windll.user32.LockWorkStation()
            return {"success": True, "message": "PC locked"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def sleep_pc(self) -> dict:
        """Put PC to sleep."""
        try:
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            return {"success": True, "message": "PC going to sleep..."}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # ─── Media Controls ───────────────────────────────────────────────

    async def media_play_pause(self) -> dict:
        if self.pyautogui:
            self.pyautogui.press("playpause")
        return {"success": True, "message": "Toggled play/pause"}

    async def media_next(self) -> dict:
        if self.pyautogui:
            self.pyautogui.press("nexttrack")
        return {"success": True, "message": "Next track"}

    async def media_prev(self) -> dict:
        if self.pyautogui:
            self.pyautogui.press("prevtrack")
        return {"success": True, "message": "Previous track"}

    # ─── Keyboard Actions ─────────────────────────────────────────────

    async def type_text(self, text: str) -> dict:
        """Type text using keyboard."""
        try:
            if self.pyautogui:
                await asyncio.sleep(0.5)
                self.pyautogui.typewrite(text, interval=0.02)
            return {"success": True, "message": f"Typed: {text}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # ─── System Information ───────────────────────────────────────────

    async def get_system_info(self) -> dict:
        """Get comprehensive system information."""
        info = {}

        if self.psutil:
            try:
                # CPU
                info["cpu"] = {
                    "usage_percent": self.psutil.cpu_percent(interval=0.5),
                    "cores_physical": self.psutil.cpu_count(logical=False),
                    "cores_logical": self.psutil.cpu_count(logical=True),
                    "frequency_mhz": round(self.psutil.cpu_freq().current) if self.psutil.cpu_freq() else 0,
                }

                # Memory
                mem = self.psutil.virtual_memory()
                info["memory"] = {
                    "total_gb": round(mem.total / (1024**3), 2),
                    "used_gb": round(mem.used / (1024**3), 2),
                    "available_gb": round(mem.available / (1024**3), 2),
                    "usage_percent": mem.percent,
                }

                # Disk
                disk = self.psutil.disk_usage("/")
                info["disk"] = {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "usage_percent": round(disk.percent, 1),
                }

                # Battery
                battery = self.psutil.sensors_battery()
                if battery:
                    info["battery"] = {
                        "percent": battery.percent,
                        "plugged_in": battery.power_plugged,
                        "time_remaining_min": round(battery.secsleft / 60) if battery.secsleft > 0 else None,
                    }

                # Network
                net = self.psutil.net_io_counters()
                info["network"] = {
                    "bytes_sent_mb": round(net.bytes_sent / (1024**2), 2),
                    "bytes_recv_mb": round(net.bytes_recv / (1024**2), 2),
                }

                # Top processes
                processes = []
                for proc in self.psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
                    try:
                        pinfo = proc.info
                        if pinfo["cpu_percent"] and pinfo["cpu_percent"] > 0:
                            processes.append(pinfo)
                    except (self.psutil.NoSuchProcess, self.psutil.AccessDenied):
                        pass
                processes.sort(key=lambda x: x.get("cpu_percent", 0), reverse=True)
                info["top_processes"] = processes[:5]

            except Exception as e:
                log.error(f"System info error: {e}")

        return {"success": True, "data": info}
