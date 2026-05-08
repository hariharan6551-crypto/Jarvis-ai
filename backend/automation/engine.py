"""
J.A.R.V.I.S Desktop Automation Engine
Full Windows PC control: apps, files, system, media, browser, windows, advanced actions.
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
        try:
            import pyautogui
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.1
            self.pyautogui = pyautogui
        except ImportError:
            self.pyautogui = None

        try:
            import psutil
            self.psutil = psutil
        except ImportError:
            self.psutil = None

    # ─── Application Management ───────────────────────────────────────

    async def open_application(self, app: str) -> dict:
        log.info(f"Opening application: {app}")

        special_folders = {
            "explorer_downloads": os.path.expanduser("~\\Downloads"),
            "explorer_documents": os.path.expanduser("~\\Documents"),
            "explorer_desktop": os.path.expanduser("~\\Desktop"),
            "explorer_pictures": os.path.expanduser("~\\Pictures"),
            "explorer_videos": os.path.expanduser("~\\Videos"),
            "explorer_music": os.path.expanduser("~\\Music"),
        }

        try:
            if app in special_folders:
                os.startfile(special_folders[app])
                return {"success": True, "message": f"Opened {app.replace('explorer_', '').title()} folder"}

            if app.startswith("ms-settings"):
                os.startfile(app)
                return {"success": True, "message": "Opened Windows Settings"}

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
            return {"success": True, "message": f"Opening {app.title()}"}
        except Exception as e:
            log.error(f"Failed to open {app}: {e}")
            return {"success": False, "message": f"Failed to open {app}: {str(e)}"}

    async def close_application(self, app: str) -> dict:
        log.info(f"Closing application: {app}")
        process_map = {
            "chrome": "chrome.exe", "firefox": "firefox.exe", "msedge": "msedge.exe",
            "code": "Code.exe", "notepad": "notepad.exe", "spotify": "Spotify.exe",
            "discord": "Discord.exe", "slack": "slack.exe", "teams": "Teams.exe",
            "whatsapp": "WhatsApp.exe", "explorer": "explorer.exe",
        }
        process_name = process_map.get(app, f"{app}.exe")
        try:
            result = await asyncio.to_thread(
                subprocess.run, f"taskkill /IM {process_name} /F",
                shell=True, capture_output=True, text=True
            )
            if result.returncode == 0:
                return {"success": True, "message": f"Closed {app}"}
            return {"success": False, "message": f"Could not find {app} running"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # ─── Window Management ────────────────────────────────────────────

    async def switch_window(self, app_name: str) -> dict:
        """Switch to a running application window."""
        try:
            import pygetwindow as gw
            windows = gw.getWindowsWithTitle(app_name)
            if windows:
                win = windows[0]
                if win.isMinimized:
                    win.restore()
                win.activate()
                return {"success": True, "message": f"Switched to {app_name}"}
            return {"success": False, "message": f"No window found for {app_name}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def minimize_window(self) -> dict:
        if self.pyautogui:
            self.pyautogui.hotkey('win', 'down')
        return {"success": True, "message": "Window minimized"}

    async def maximize_window(self) -> dict:
        if self.pyautogui:
            self.pyautogui.hotkey('win', 'up')
        return {"success": True, "message": "Window maximized"}

    async def close_window(self) -> dict:
        if self.pyautogui:
            self.pyautogui.hotkey('alt', 'F4')
        return {"success": True, "message": "Window closed"}

    async def switch_tab(self) -> dict:
        if self.pyautogui:
            self.pyautogui.hotkey('alt', 'tab')
        return {"success": True, "message": "Switched tab"}

    async def new_tab(self) -> dict:
        if self.pyautogui:
            self.pyautogui.hotkey('ctrl', 't')
        return {"success": True, "message": "New tab opened"}

    async def close_tab(self) -> dict:
        if self.pyautogui:
            self.pyautogui.hotkey('ctrl', 'w')
        return {"success": True, "message": "Tab closed"}

    # ─── Browser Navigation ──────────────────────────────────────────

    async def go_to_url(self, url: str) -> dict:
        """Navigate to a URL in the current browser."""
        if self.pyautogui:
            self.pyautogui.hotkey('ctrl', 'l')
            await asyncio.sleep(0.3)
            self.pyautogui.typewrite(url, interval=0.02)
            self.pyautogui.press('enter')
        return {"success": True, "message": f"Navigating to {url}"}

    async def go_back(self) -> dict:
        if self.pyautogui:
            self.pyautogui.hotkey('alt', 'left')
        return {"success": True, "message": "Going back"}

    async def go_forward(self) -> dict:
        if self.pyautogui:
            self.pyautogui.hotkey('alt', 'right')
        return {"success": True, "message": "Going forward"}

    async def refresh_page(self) -> dict:
        if self.pyautogui:
            self.pyautogui.press('f5')
        return {"success": True, "message": "Page refreshed"}

    async def scroll_down(self) -> dict:
        if self.pyautogui:
            self.pyautogui.scroll(-5)
        return {"success": True, "message": "Scrolled down"}

    async def scroll_up(self) -> dict:
        if self.pyautogui:
            self.pyautogui.scroll(5)
        return {"success": True, "message": "Scrolled up"}

    # ─── Web Search ───────────────────────────────────────────────────

    async def search_web(self, query: str) -> dict:
        import urllib.parse
        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        try:
            os.startfile(url)
            return {"success": True, "message": f"Searching Google for: {query}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def search_youtube(self, query: str) -> dict:
        import urllib.parse
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
        try:
            os.startfile(url)
            return {"success": True, "message": f"Searching YouTube for: {query}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def open_website(self, site: str) -> dict:
        """Open a website by name."""
        sites = {
            "google": "https://www.google.com",
            "youtube": "https://www.youtube.com",
            "gmail": "https://mail.google.com",
            "github": "https://github.com",
            "chatgpt": "https://chat.openai.com",
            "whatsapp web": "https://web.whatsapp.com",
            "twitter": "https://twitter.com",
            "instagram": "https://instagram.com",
            "facebook": "https://facebook.com",
            "linkedin": "https://linkedin.com",
            "reddit": "https://reddit.com",
            "netflix": "https://netflix.com",
            "amazon": "https://amazon.in",
        }
        url = sites.get(site.lower(), f"https://{site}")
        os.startfile(url)
        return {"success": True, "message": f"Opening {site}"}

    # ─── Volume Control ───────────────────────────────────────────────

    async def volume_up(self, amount: int = 10) -> dict:
        if self.pyautogui:
            for _ in range(amount // 2):
                self.pyautogui.press("volumeup")
        return {"success": True, "message": f"Volume increased"}

    async def volume_down(self, amount: int = 10) -> dict:
        if self.pyautogui:
            for _ in range(amount // 2):
                self.pyautogui.press("volumedown")
        return {"success": True, "message": f"Volume decreased"}

    async def volume_mute(self) -> dict:
        if self.pyautogui:
            self.pyautogui.press("volumemute")
        return {"success": True, "message": "Volume toggled"}

    # ─── Brightness Control ───────────────────────────────────────────

    async def brightness_up(self, amount: int = 20) -> dict:
        try:
            import screen_brightness_control as sbc
            current = sbc.get_brightness()[0]
            sbc.set_brightness(min(100, current + amount))
            return {"success": True, "message": f"Brightness increased"}
        except:
            return {"success": False, "message": "Brightness control not available"}

    async def brightness_down(self, amount: int = 20) -> dict:
        try:
            import screen_brightness_control as sbc
            current = sbc.get_brightness()[0]
            sbc.set_brightness(max(0, current - amount))
            return {"success": True, "message": f"Brightness decreased"}
        except:
            return {"success": False, "message": "Brightness control not available"}

    # ─── Screenshot ───────────────────────────────────────────────────

    async def take_screenshot(self) -> dict:
        try:
            if self.pyautogui:
                d = Path.home() / "Pictures" / "JARVIS_Screenshots"
                d.mkdir(parents=True, exist_ok=True)
                f = d / f"screenshot_{int(time.time())}.png"
                self.pyautogui.screenshot().save(str(f))
                return {"success": True, "message": f"Screenshot saved", "path": str(f)}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # ─── System Commands ──────────────────────────────────────────────

    async def shutdown_pc(self, confirm: bool = True) -> dict:
        if confirm:
            return {"success": True, "message": "Say 'confirm shutdown' to proceed", "requires_confirmation": True}
        os.system("shutdown /s /t 5")
        return {"success": True, "message": "Shutting down in 5 seconds"}

    async def restart_pc(self, confirm: bool = True) -> dict:
        if confirm:
            return {"success": True, "message": "Say 'confirm restart' to proceed", "requires_confirmation": True}
        os.system("shutdown /r /t 5")
        return {"success": True, "message": "Restarting in 5 seconds"}

    async def lock_pc(self) -> dict:
        import ctypes
        ctypes.windll.user32.LockWorkStation()
        return {"success": True, "message": "PC locked"}

    async def sleep_pc(self) -> dict:
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        return {"success": True, "message": "Going to sleep"}

    # ─── Media Controls ───────────────────────────────────────────────

    async def media_play_pause(self) -> dict:
        if self.pyautogui: self.pyautogui.press("playpause")
        return {"success": True, "message": "Play/Pause toggled"}

    async def media_next(self) -> dict:
        if self.pyautogui: self.pyautogui.press("nexttrack")
        return {"success": True, "message": "Next track"}

    async def media_prev(self) -> dict:
        if self.pyautogui: self.pyautogui.press("prevtrack")
        return {"success": True, "message": "Previous track"}

    # ─── Keyboard Actions ─────────────────────────────────────────────

    async def type_text(self, text: str) -> dict:
        if self.pyautogui:
            await asyncio.sleep(0.5)
            self.pyautogui.typewrite(text, interval=0.02)
        return {"success": True, "message": f"Typed: {text}"}

    async def press_key(self, key: str) -> dict:
        """Press a keyboard key or shortcut."""
        if self.pyautogui:
            keys = key.lower().replace('+', ' ').split()
            if len(keys) > 1:
                self.pyautogui.hotkey(*keys)
            else:
                self.pyautogui.press(keys[0])
        return {"success": True, "message": f"Pressed {key}"}

    async def copy(self) -> dict:
        if self.pyautogui: self.pyautogui.hotkey('ctrl', 'c')
        return {"success": True, "message": "Copied"}

    async def paste(self) -> dict:
        if self.pyautogui: self.pyautogui.hotkey('ctrl', 'v')
        return {"success": True, "message": "Pasted"}

    async def undo(self) -> dict:
        if self.pyautogui: self.pyautogui.hotkey('ctrl', 'z')
        return {"success": True, "message": "Undone"}

    async def select_all(self) -> dict:
        if self.pyautogui: self.pyautogui.hotkey('ctrl', 'a')
        return {"success": True, "message": "Selected all"}

    async def save(self) -> dict:
        if self.pyautogui: self.pyautogui.hotkey('ctrl', 's')
        return {"success": True, "message": "Saved"}

    async def find(self, text: str = None) -> dict:
        if self.pyautogui:
            self.pyautogui.hotkey('ctrl', 'f')
            if text:
                await asyncio.sleep(0.3)
                self.pyautogui.typewrite(text, interval=0.02)
        return {"success": True, "message": f"Find opened{' for: ' + text if text else ''}"}

    # ─── Mouse Actions ────────────────────────────────────────────────

    async def click(self, x: int = None, y: int = None) -> dict:
        if self.pyautogui:
            if x and y:
                self.pyautogui.click(x, y)
            else:
                self.pyautogui.click()
        return {"success": True, "message": "Clicked"}

    async def right_click(self) -> dict:
        if self.pyautogui:
            self.pyautogui.rightClick()
        return {"success": True, "message": "Right clicked"}

    async def double_click(self) -> dict:
        if self.pyautogui:
            self.pyautogui.doubleClick()
        return {"success": True, "message": "Double clicked"}

    # ─── File Operations ──────────────────────────────────────────────

    async def open_file(self, path: str) -> dict:
        """Open a file with its default application."""
        try:
            full_path = os.path.expanduser(path)
            if os.path.exists(full_path):
                os.startfile(full_path)
                return {"success": True, "message": f"Opened {os.path.basename(full_path)}"}
            return {"success": False, "message": f"File not found: {path}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def create_folder(self, name: str) -> dict:
        """Create a folder on the Desktop."""
        try:
            path = Path.home() / "Desktop" / name
            path.mkdir(parents=True, exist_ok=True)
            return {"success": True, "message": f"Created folder: {name}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    # ─── Windows Shortcuts ────────────────────────────────────────────

    async def show_desktop(self) -> dict:
        if self.pyautogui: self.pyautogui.hotkey('win', 'd')
        return {"success": True, "message": "Desktop shown"}

    async def open_task_view(self) -> dict:
        if self.pyautogui: self.pyautogui.hotkey('win', 'tab')
        return {"success": True, "message": "Task view opened"}

    async def open_action_center(self) -> dict:
        if self.pyautogui: self.pyautogui.hotkey('win', 'a')
        return {"success": True, "message": "Action center opened"}

    async def open_start_menu(self) -> dict:
        if self.pyautogui: self.pyautogui.press('win')
        return {"success": True, "message": "Start menu opened"}

    async def open_run(self) -> dict:
        if self.pyautogui: self.pyautogui.hotkey('win', 'r')
        return {"success": True, "message": "Run dialog opened"}

    async def open_emoji(self) -> dict:
        if self.pyautogui: self.pyautogui.hotkey('win', '.')
        return {"success": True, "message": "Emoji picker opened"}

    async def snap_left(self) -> dict:
        if self.pyautogui: self.pyautogui.hotkey('win', 'left')
        return {"success": True, "message": "Window snapped left"}

    async def snap_right(self) -> dict:
        if self.pyautogui: self.pyautogui.hotkey('win', 'right')
        return {"success": True, "message": "Window snapped right"}

    # ─── System Information ───────────────────────────────────────────

    async def get_system_info(self) -> dict:
        info = {}
        if self.psutil:
            try:
                info["cpu"] = {
                    "usage_percent": self.psutil.cpu_percent(interval=0.5),
                    "cores_physical": self.psutil.cpu_count(logical=False),
                    "cores_logical": self.psutil.cpu_count(logical=True),
                    "frequency_mhz": round(self.psutil.cpu_freq().current) if self.psutil.cpu_freq() else 0,
                }
                mem = self.psutil.virtual_memory()
                info["memory"] = {
                    "total_gb": round(mem.total / (1024**3), 2),
                    "used_gb": round(mem.used / (1024**3), 2),
                    "available_gb": round(mem.available / (1024**3), 2),
                    "usage_percent": mem.percent,
                }
                disk = self.psutil.disk_usage("/")
                info["disk"] = {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "usage_percent": round(disk.percent, 1),
                }
                battery = self.psutil.sensors_battery()
                if battery:
                    info["battery"] = {
                        "percent": battery.percent,
                        "plugged_in": battery.power_plugged,
                    }
                net = self.psutil.net_io_counters()
                info["network"] = {
                    "bytes_sent_mb": round(net.bytes_sent / (1024**2), 2),
                    "bytes_recv_mb": round(net.bytes_recv / (1024**2), 2),
                }
                processes = []
                for proc in self.psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
                    try:
                        pinfo = proc.info
                        if pinfo["cpu_percent"] and pinfo["cpu_percent"] > 0:
                            processes.append(pinfo)
                    except:
                        pass
                processes.sort(key=lambda x: x.get("cpu_percent", 0), reverse=True)
                info["top_processes"] = processes[:5]
            except Exception as e:
                log.error(f"System info error: {e}")
        return {"success": True, "data": info}
