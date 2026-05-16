"""
J.A.R.V.I.S Desktop Automation Engine
Full Windows PC control: apps, system, media, volume, brightness, files.
Every action logged with duration. No silent failures.
"""

import asyncio
import os
import subprocess
import time
import base64
from pathlib import Path
from typing import Optional
from core.logger import get_logger
from config.settings import settings

log = get_logger("automation")


class AutomationEngine:
    """Desktop automation via pyautogui, pygetwindow, subprocess, and Win32 API."""

    def __init__(self):
        self.pyautogui = None
        self.pygetwindow = None
        self._init_libs()
        log.info("Automation engine initialized")

    def _init_libs(self):
        """Initialize automation libraries with proper error handling."""
        try:
            import pyautogui
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.05
            self.pyautogui = pyautogui
            log.debug("pyautogui loaded")
        except ImportError:
            log.error("pyautogui not installed — desktop automation unavailable")

        try:
            import pygetwindow as gw
            self.pygetwindow = gw
            log.debug("pygetwindow loaded")
        except ImportError:
            log.warning("pygetwindow not installed — window management limited")

    def _check_pyautogui(self) -> dict:
        """Check if pyautogui is available, return error dict if not."""
        if self.pyautogui is None:
            return {"success": False, "message": "pyautogui not available — please install it"}
        return None

    def _timed_action(self, action_name: str):
        """Context manager for timing and logging actions."""
        class Timer:
            def __init__(self):
                self.start = time.time()
                self.name = action_name

            def __enter__(self):
                log.debug(f"Starting: {self.name}")
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                elapsed = (time.time() - self.start) * 1000
                if exc_type:
                    log.error(f"FAILED: {self.name} ({elapsed:.0f}ms) — {exc_val}")
                else:
                    log.info(f"Completed: {self.name} ({elapsed:.0f}ms)")
                return False
        return Timer()

    # ─── Application Management ───────────────────────────────────────

    APP_PATHS = {
        # Browsers
        "chrome": "chrome", "firefox": "firefox", "msedge": "msedge",
        "brave": "brave", "opera": "opera", "arc": "arc",
        # Editors
        "code": "code", "devenv": "devenv", "sublime_text": "sublime_text",
        "cursor": "cursor", "studio64": "studio64",
        # Office
        "notepad": "notepad", "notepad++": "notepad++",
        "calc": "calc", "mspaint": "mspaint",
        "winword": "winword", "excel": "excel", "powerpnt": "powerpnt",
        "outlook": "outlook", "onenote": "onenote", "msaccess": "msaccess",
        # File Explorer
        "explorer": "explorer",
        "explorer_downloads": "explorer shell:Downloads",
        "explorer_documents": "explorer shell:Documents",
        "explorer_desktop": "explorer shell:Desktop",
        "explorer_recycle": "explorer shell:RecycleBinFolder",
        # Terminal
        "cmd": "cmd", "powershell": "powershell", "wt": "wt",
        # System tools
        "taskmgr": "taskmgr", "control": "control",
        "regedit": "regedit", "resmon": "resmon",
        "msinfo32": "msinfo32", "charmap": "charmap",
        "snippingtool": "snippingtool",
        # MMC snap-ins
        "devmgmt.msc": "devmgmt.msc",
        "diskmgmt.msc": "diskmgmt.msc",
        "eventvwr.msc": "eventvwr.msc",
    }

    # UWP app search keywords → what to search in PackageFamilyName
    UWP_SEARCH_KEYS = {
        "whatsapp": "WhatsApp",
        "instagram": "Instagram",
        "spotify": "Spotify",
        "telegram": "Telegram",
        "discord": "Discord",
        "canva": "Canva",
        "teams": "MicrosoftTeams",
        "xbox": "XboxApp",
        "netflix": "Netflix",
        "prime video": "AmazonVideo",
        "twitter": "Twitter",
        "tiktok": "TikTok",
        "messenger": "Messenger",
    }

    # Cache for discovered UWP apps
    _uwp_cache: dict = {}

    def _discover_uwp_app(self, search_key: str) -> str:
        """Dynamically discover a UWP app's launch ID via PowerShell."""
        if search_key in self._uwp_cache:
            return self._uwp_cache[search_key]
        try:
            # Get PackageFamilyName
            ps_cmd = f'Get-AppxPackage *{search_key}* | Select-Object -First 1 -ExpandProperty PackageFamilyName'
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True, text=True, timeout=5
            )
            pfn = result.stdout.strip()
            if pfn:
                # UWP apps use PackageFamilyName!App as the launch ID
                launch_id = f"{pfn}!App"
                self._uwp_cache[search_key] = launch_id
                log.info(f"Discovered UWP app: {search_key} → {launch_id}")
                return launch_id
        except Exception as e:
            log.debug(f"UWP discovery failed for {search_key}: {e}")
        return ""

    async def open_application(self, app_name: str) -> dict:
        """Open any application — supports win32 apps, UWP/Store apps, ms-settings, .msc, and URLs."""
        with self._timed_action(f"open_app({app_name})"):
            try:
                app_lower = app_name.lower().strip()

                # 1. Windows Settings (ms-settings: URI)
                if app_lower.startswith("ms-settings"):
                    subprocess.Popen(["start", app_lower], shell=True)
                    label = app_lower.replace("ms-settings:", "").replace("-", " ").title() or "Settings"
                    return {"success": True, "message": f"Opened {label} settings, Sir"}

                # 2. MMC snap-ins (.msc files)
                if app_lower.endswith(".msc"):
                    subprocess.Popen(["mmc", app_lower], shell=True)
                    return {"success": True, "message": f"Opened {app_lower}, Sir"}

                # 3. Explorer special folders
                cmd = self.APP_PATHS.get(app_lower, None)
                if cmd and cmd.startswith("explorer shell:"):
                    subprocess.Popen(cmd, shell=True)
                    return {"success": True, "message": f"Opened {app_name}, Sir"}

                # 4. UWP / Store apps (dynamic discovery)
                uwp_key = self.UWP_SEARCH_KEYS.get(app_lower, None)
                if uwp_key:
                    launch_id = self._discover_uwp_app(uwp_key)
                    if launch_id:
                        subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{launch_id}"])
                        return {"success": True, "message": f"Opened {app_name}, Sir"}

                # 5. Known win32 apps
                if cmd:
                    if app_lower in ("chrome", "firefox", "msedge", "brave", "opera"):
                        subprocess.Popen(["start", cmd], shell=True)
                    else:
                        subprocess.Popen(["start", "", cmd], shell=True)
                    return {"success": True, "message": f"Opened {app_name}, Sir"}

                # 6. Try as a UWP app by name (even if not in our search keys)
                launch_id = self._discover_uwp_app(app_lower)
                if launch_id:
                    subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{launch_id}"])
                    return {"success": True, "message": f"Opened {app_name}, Sir"}

                # 7. Ultimate fallback: try 'start' command (Windows will search PATH)
                subprocess.Popen(["start", "", app_lower], shell=True)
                return {"success": True, "message": f"Opened {app_name}, Sir"}

            except FileNotFoundError:
                log.error(f"Application not found: {app_name}")
                return {"success": False, "message": f"Application '{app_name}' not found on this system, Sir"}
            except Exception as e:
                log.error(f"Failed to open {app_name}: {e}")
                return {"success": False, "message": f"Failed to open {app_name}: {str(e)}"}

    async def close_application(self, app_name: str) -> dict:
        """Close an application by name."""
        with self._timed_action(f"close_app({app_name})"):
            try:
                app_lower = app_name.lower().strip()

                # Try using pygetwindow first
                if self.pygetwindow:
                    windows = self.pygetwindow.getWindowsWithTitle(app_name)
                    if windows:
                        for w in windows:
                            try:
                                w.close()
                            except Exception:
                                pass
                        return {"success": True, "message": f"Closed {app_name}"}

                # Fallback to taskkill
                process_name = self.APP_PATHS.get(app_lower, app_lower)
                if not process_name.endswith(".exe"):
                    process_name += ".exe"

                result = subprocess.run(
                    ["taskkill", "/F", "/IM", process_name],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    return {"success": True, "message": f"Closed {app_name}"}
                else:
                    return {"success": False, "message": f"Could not close {app_name}: {result.stderr.strip()}"}

            except subprocess.TimeoutExpired:
                return {"success": False, "message": f"Timeout closing {app_name}"}
            except Exception as e:
                log.error(f"Failed to close {app_name}: {e}")
                return {"success": False, "message": f"Failed to close {app_name}: {str(e)}"}

    # ─── URL & Search ─────────────────────────────────────────────────

    async def go_to_url(self, url: str) -> dict:
        """Navigate to a URL in the default browser."""
        with self._timed_action(f"go_to_url({url})"):
            try:
                import webbrowser
                if not url.startswith(("http://", "https://")):
                    url = "https://" + url
                webbrowser.open(url)
                return {"success": True, "message": f"Navigated to {url}"}
            except Exception as e:
                return {"success": False, "message": f"Failed to open URL: {str(e)}"}

    async def search_web(self, query: str) -> dict:
        """Search Google in the default browser."""
        with self._timed_action(f"search_web({query})"):
            try:
                import webbrowser
                import urllib.parse
                url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
                webbrowser.open(url)
                return {"success": True, "message": f"Searching Google for: {query}"}
            except Exception as e:
                return {"success": False, "message": f"Search failed: {str(e)}"}

    async def search_youtube(self, query: str) -> dict:
        """Search YouTube in the default browser."""
        with self._timed_action(f"search_youtube({query})"):
            try:
                import webbrowser
                import urllib.parse
                url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
                webbrowser.open(url)
                return {"success": True, "message": f"Searching YouTube for: {query}"}
            except Exception as e:
                return {"success": False, "message": f"YouTube search failed: {str(e)}"}

    # ─── Volume Control ───────────────────────────────────────────────

    async def volume_up(self) -> dict:
        """Increase volume by one step."""
        err = self._check_pyautogui()
        if err:
            return err
        with self._timed_action("volume_up"):
            try:
                self.pyautogui.press("volumeup")
                self.pyautogui.press("volumeup")
                return {"success": True, "message": "Volume increased"}
            except Exception as e:
                return {"success": False, "message": f"Volume up failed: {str(e)}"}

    async def volume_down(self) -> dict:
        """Decrease volume by one step."""
        err = self._check_pyautogui()
        if err:
            return err
        with self._timed_action("volume_down"):
            try:
                self.pyautogui.press("volumedown")
                self.pyautogui.press("volumedown")
                return {"success": True, "message": "Volume decreased"}
            except Exception as e:
                return {"success": False, "message": f"Volume down failed: {str(e)}"}

    async def volume_mute(self) -> dict:
        """Toggle mute."""
        err = self._check_pyautogui()
        if err:
            return err
        with self._timed_action("volume_mute"):
            try:
                self.pyautogui.press("volumemute")
                return {"success": True, "message": "Volume mute toggled"}
            except Exception as e:
                return {"success": False, "message": f"Mute toggle failed: {str(e)}"}

    async def set_volume(self, level: int) -> dict:
        """Set volume to a specific level (0-100)."""
        with self._timed_action(f"set_volume({level})"):
            try:
                from ctypes import cast, POINTER
                from comtypes import CLSCTX_ALL
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = cast(interface, POINTER(IAudioEndpointVolume))
                volume.SetMasterVolumeLevelScalar(level / 100.0, None)
                return {"success": True, "message": f"Volume set to {level}%"}
            except ImportError:
                # Fallback: use nircmd or key presses
                return {"success": False, "message": "pycaw not installed for precise volume control"}
            except Exception as e:
                return {"success": False, "message": f"Set volume failed: {str(e)}"}

    # ─── Brightness Control ───────────────────────────────────────────

    async def brightness_up(self) -> dict:
        """Increase brightness."""
        with self._timed_action("brightness_up"):
            try:
                import screen_brightness_control as sbc
                current = sbc.get_brightness(display=0)
                if isinstance(current, list):
                    current = current[0]
                new_val = min(100, current + 10)
                sbc.set_brightness(new_val, display=0)
                return {"success": True, "message": f"Brightness increased to {new_val}%"}
            except ImportError:
                return {"success": False, "message": "screen_brightness_control not installed"}
            except Exception as e:
                return {"success": False, "message": f"Brightness up failed: {str(e)}"}

    async def brightness_down(self) -> dict:
        """Decrease brightness."""
        with self._timed_action("brightness_down"):
            try:
                import screen_brightness_control as sbc
                current = sbc.get_brightness(display=0)
                if isinstance(current, list):
                    current = current[0]
                new_val = max(0, current - 10)
                sbc.set_brightness(new_val, display=0)
                return {"success": True, "message": f"Brightness decreased to {new_val}%"}
            except ImportError:
                return {"success": False, "message": "screen_brightness_control not installed"}
            except Exception as e:
                return {"success": False, "message": f"Brightness down failed: {str(e)}"}

    # ─── Media Controls ───────────────────────────────────────────────

    async def media_play_pause(self) -> dict:
        err = self._check_pyautogui()
        if err:
            return err
        with self._timed_action("media_play_pause"):
            try:
                self.pyautogui.press("playpause")
                return {"success": True, "message": "Play/Pause toggled"}
            except Exception as e:
                return {"success": False, "message": f"Media play/pause failed: {str(e)}"}

    async def media_next(self) -> dict:
        err = self._check_pyautogui()
        if err:
            return err
        with self._timed_action("media_next"):
            try:
                self.pyautogui.press("nexttrack")
                return {"success": True, "message": "Skipped to next track"}
            except Exception as e:
                return {"success": False, "message": f"Media next failed: {str(e)}"}

    async def media_prev(self) -> dict:
        err = self._check_pyautogui()
        if err:
            return err
        with self._timed_action("media_prev"):
            try:
                self.pyautogui.press("prevtrack")
                return {"success": True, "message": "Skipped to previous track"}
            except Exception as e:
                return {"success": False, "message": f"Media prev failed: {str(e)}"}

    # ─── Keyboard & Text ──────────────────────────────────────────────

    async def type_text(self, text: str) -> dict:
        """Type text at the current cursor position."""
        err = self._check_pyautogui()
        if err:
            return err
        with self._timed_action(f"type_text({text[:30]}...)"):
            try:
                self.pyautogui.typewrite(text, interval=0.02) if text.isascii() else self.pyautogui.write(text)
                return {"success": True, "message": f"Typed: {text[:50]}"}
            except Exception as e:
                return {"success": False, "message": f"Type text failed: {str(e)}"}

    async def press_key(self, key_combo: str) -> dict:
        """Press a keyboard shortcut (e.g., 'ctrl+c', 'alt+tab', 'enter')."""
        err = self._check_pyautogui()
        if err:
            return err
        with self._timed_action(f"press_key({key_combo})"):
            try:
                keys = [k.strip() for k in key_combo.lower().replace("+", " ").split()]
                if len(keys) > 1:
                    self.pyautogui.hotkey(*keys)
                else:
                    self.pyautogui.press(keys[0])
                return {"success": True, "message": f"Pressed: {key_combo}"}
            except Exception as e:
                return {"success": False, "message": f"Press key failed: {str(e)}"}

    # ─── Screenshot ───────────────────────────────────────────────────

    async def take_screenshot(self, filename: str = None) -> dict:
        """Take a screenshot and return as base64."""
        err = self._check_pyautogui()
        if err:
            return err
        with self._timed_action("screenshot"):
            try:
                import io
                screenshot = self.pyautogui.screenshot()

                if filename:
                    screenshots_dir = Path(settings.SQLITE_DB_PATH).parent / "screenshots"
                    screenshots_dir.mkdir(exist_ok=True)
                    filepath = screenshots_dir / filename
                    screenshot.save(str(filepath))

                buffer = io.BytesIO()
                screenshot.save(buffer, format="PNG")
                img_base64 = base64.b64encode(buffer.getvalue()).decode()

                return {
                    "success": True,
                    "message": "Screenshot captured",
                    "image": img_base64,
                    "filename": filename,
                }
            except Exception as e:
                return {"success": False, "message": f"Screenshot failed: {str(e)}"}

    # ─── System Control ───────────────────────────────────────────────

    async def get_system_info(self) -> dict:
        """Get comprehensive system information."""
        with self._timed_action("get_system_info"):
            try:
                import psutil

                cpu_freq = psutil.cpu_freq()
                mem = psutil.virtual_memory()
                disk = psutil.disk_usage("C:\\")
                net = psutil.net_io_counters()

                battery = None
                try:
                    bat = psutil.sensors_battery()
                    if bat:
                        battery = {
                            "percent": bat.percent,
                            "plugged_in": bat.power_plugged,
                            "time_left": str(bat.secsleft // 60) + " min" if bat.secsleft > 0 else "N/A",
                        }
                except Exception:
                    pass

                # Top processes
                procs = []
                try:
                    for p in psutil.process_iter(["name", "cpu_percent"]):
                        try:
                            info = p.info
                            if info["cpu_percent"] and info["cpu_percent"] > 0:
                                procs.append({"name": info["name"], "cpu_percent": info["cpu_percent"]})
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                    procs = sorted(procs, key=lambda x: x["cpu_percent"], reverse=True)[:5]
                except Exception:
                    pass

                data = {
                    "cpu": {
                        "usage_percent": psutil.cpu_percent(interval=0.5),
                        "cores": psutil.cpu_count(),
                        "frequency_mhz": round(cpu_freq.current) if cpu_freq else 0,
                    },
                    "memory": {
                        "total_gb": round(mem.total / (1024**3), 1),
                        "used_gb": round(mem.used / (1024**3), 1),
                        "usage_percent": mem.percent,
                    },
                    "disk": {
                        "total_gb": round(disk.total / (1024**3), 1),
                        "used_gb": round(disk.used / (1024**3), 1),
                        "free_gb": round(disk.free / (1024**3), 1),
                        "usage_percent": round(disk.percent, 1),
                    },
                    "battery": battery or {"percent": None, "plugged_in": False},
                    "network": {
                        "bytes_sent_mb": round(net.bytes_sent / (1024**2), 1),
                        "bytes_recv_mb": round(net.bytes_recv / (1024**2), 1),
                    },
                    "top_processes": procs,
                }
                return {"success": True, "data": data, "message": "System info retrieved"}
            except ImportError:
                return {"success": False, "message": "psutil not installed"}
            except Exception as e:
                return {"success": False, "message": f"System info failed: {str(e)}"}

    async def shutdown_pc(self) -> dict:
        """Shutdown the PC (with 30s delay for safety)."""
        with self._timed_action("shutdown_pc"):
            try:
                subprocess.Popen(["shutdown", "/s", "/t", "30"])
                return {"success": True, "message": "Shutting down in 30 seconds. Say 'cancel shutdown' to abort."}
            except Exception as e:
                return {"success": False, "message": f"Shutdown failed: {str(e)}"}

    async def restart_pc(self) -> dict:
        """Restart the PC (with 30s delay for safety)."""
        with self._timed_action("restart_pc"):
            try:
                subprocess.Popen(["shutdown", "/r", "/t", "30"])
                return {"success": True, "message": "Restarting in 30 seconds. Say 'cancel restart' to abort."}
            except Exception as e:
                return {"success": False, "message": f"Restart failed: {str(e)}"}

    async def lock_pc(self) -> dict:
        """Lock the PC."""
        with self._timed_action("lock_pc"):
            try:
                import ctypes
                ctypes.windll.user32.LockWorkStation()
                return {"success": True, "message": "PC locked"}
            except Exception as e:
                return {"success": False, "message": f"Lock failed: {str(e)}"}

    async def sleep_pc(self) -> dict:
        """Put PC to sleep."""
        with self._timed_action("sleep_pc"):
            try:
                subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0", "1", "0"])
                return {"success": True, "message": "PC going to sleep"}
            except Exception as e:
                return {"success": False, "message": f"Sleep failed: {str(e)}"}

    # ─── Window Management ────────────────────────────────────────────

    async def switch_window(self, title: str) -> dict:
        """Switch to a window by title."""
        with self._timed_action(f"switch_window({title})"):
            try:
                if not self.pygetwindow:
                    return {"success": False, "message": "pygetwindow not available"}

                windows = self.pygetwindow.getWindowsWithTitle(title)
                if windows:
                    win = windows[0]
                    if win.isMinimized:
                        win.restore()
                    win.activate()
                    return {"success": True, "message": f"Switched to: {win.title}"}
                return {"success": False, "message": f"Window '{title}' not found"}
            except Exception as e:
                return {"success": False, "message": f"Switch window failed: {str(e)}"}

    async def maximize_window(self) -> dict:
        """Maximize the current window."""
        err = self._check_pyautogui()
        if err:
            return err
        with self._timed_action("maximize_window"):
            try:
                if self.pygetwindow:
                    win = self.pygetwindow.getActiveWindow()
                    if win:
                        win.maximize()
                        return {"success": True, "message": "Window maximized"}
                # Fallback
                self.pyautogui.hotkey("win", "up")
                return {"success": True, "message": "Window maximized"}
            except Exception as e:
                return {"success": False, "message": f"Maximize failed: {str(e)}"}

    async def minimize_window(self) -> dict:
        """Minimize the current window."""
        err = self._check_pyautogui()
        if err:
            return err
        with self._timed_action("minimize_window"):
            try:
                if self.pygetwindow:
                    win = self.pygetwindow.getActiveWindow()
                    if win:
                        win.minimize()
                        return {"success": True, "message": "Window minimized"}
                self.pyautogui.hotkey("win", "down")
                return {"success": True, "message": "Window minimized"}
            except Exception as e:
                return {"success": False, "message": f"Minimize failed: {str(e)}"}

    # ─── File Operations ──────────────────────────────────────────────

    async def open_file(self, path: str) -> dict:
        """Open a file or folder."""
        with self._timed_action(f"open_file({path})"):
            try:
                os.startfile(path)
                return {"success": True, "message": f"Opened: {path}"}
            except FileNotFoundError:
                return {"success": False, "message": f"File not found: {path}"}
            except Exception as e:
                return {"success": False, "message": f"Open file failed: {str(e)}"}

    async def create_folder(self, path: str) -> dict:
        """Create a new folder."""
        with self._timed_action(f"create_folder({path})"):
            try:
                Path(path).mkdir(parents=True, exist_ok=True)
                return {"success": True, "message": f"Created folder: {path}"}
            except Exception as e:
                return {"success": False, "message": f"Create folder failed: {str(e)}"}

    # ─── Clipboard ────────────────────────────────────────────────────

    async def read_clipboard(self) -> dict:
        """Read text from the clipboard."""
        with self._timed_action("read_clipboard"):
            try:
                import win32clipboard
                win32clipboard.OpenClipboard()
                try:
                    data = win32clipboard.GetClipboardData()
                    return {"success": True, "message": f"Clipboard: {data[:200]}", "text": data}
                finally:
                    win32clipboard.CloseClipboard()
            except ImportError:
                # Fallback using pyperclip or tkinter
                try:
                    import tkinter as tk
                    root = tk.Tk()
                    root.withdraw()
                    data = root.clipboard_get()
                    root.destroy()
                    return {"success": True, "message": f"Clipboard: {data[:200]}", "text": data}
                except Exception:
                    return {"success": False, "message": "Could not read clipboard"}
            except Exception as e:
                return {"success": False, "message": f"Clipboard read failed: {str(e)}"}

    # ─── Status ───────────────────────────────────────────────────────

    def get_status(self) -> dict:
        """Get automation engine status."""
        return {
            "pyautogui_available": self.pyautogui is not None,
            "pygetwindow_available": self.pygetwindow is not None,
        }
