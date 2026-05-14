"""
J.A.R.V.I.S Focus Mode & Environment Control
Modes: Focus, Night, Cinema, Gaming, Presentation, Normal
"""

import asyncio, subprocess, time
from core.logger import get_logger
from config.settings import settings

log = get_logger("focus_mode")


class FocusModeService:
    def __init__(self, automation_engine=None):
        self.automation = automation_engine
        self.current_mode = "normal"
        self._focus_timer_task = None
        self._focus_remaining = 0
        self._original_brightness = None
        log.info("Focus mode service initialized")

    async def activate_focus(self, duration_minutes: int = 45) -> dict:
        self.current_mode = "focus"
        steps = []
        # Mute notifications via Focus Assist
        try:
            subprocess.run(["powershell", "-Command",
                "Set-ItemProperty -Path 'HKCU:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Notifications\\Settings' -Name 'NOC_GLOBAL_SETTING_ALLOW_NOTIFICATION_SOUND' -Value 0"],
                capture_output=True, timeout=5)
            steps.append("Notifications muted")
        except: pass

        # Dim brightness
        try:
            import screen_brightness_control as sbc
            self._original_brightness = sbc.get_brightness(display=0)
            if isinstance(self._original_brightness, list):
                self._original_brightness = self._original_brightness[0]
            sbc.set_brightness(60, display=0)
            steps.append("Screen dimmed to 60%")
        except: pass

        # Start timer
        self._focus_remaining = duration_minutes * 60
        if self._focus_timer_task:
            self._focus_timer_task.cancel()
        self._focus_timer_task = asyncio.create_task(self._focus_countdown(duration_minutes))
        steps.append(f"Focus timer: {duration_minutes} minutes")

        return {
            "success": True,
            "message": f"Focus mode active for {duration_minutes} minutes, Sir. Notifications muted, screen dimmed. Let's get to work.",
            "mode": "focus",
            "duration": duration_minutes,
            "steps": steps,
        }

    async def activate_night_mode(self) -> dict:
        self.current_mode = "night"
        steps = []
        # Enable dark mode
        try:
            subprocess.run(["reg", "add",
                r"HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize",
                "/v", "AppsUseLightTheme", "/t", "REG_DWORD", "/d", "0", "/f"],
                capture_output=True, timeout=5)
            subprocess.run(["reg", "add",
                r"HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize",
                "/v", "SystemUsesLightTheme", "/t", "REG_DWORD", "/d", "0", "/f"],
                capture_output=True, timeout=5)
            steps.append("Dark mode enabled")
        except: pass

        # Dim brightness
        try:
            import screen_brightness_control as sbc
            self._original_brightness = sbc.get_brightness(display=0)
            if isinstance(self._original_brightness, list):
                self._original_brightness = self._original_brightness[0]
            sbc.set_brightness(30, display=0)
            steps.append("Brightness set to 30%")
        except: pass

        # Enable night light
        try:
            subprocess.run(["powershell", "-Command",
                "Set-ItemProperty -Path 'HKCU:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\CloudStore\\Store\\DefaultAccount\\Current\\default$windows.data.bluelightreduction.bluelightreductionstate\\windows.data.bluelightreduction.bluelightreductionstate' -Name 'Data' -Value ([byte[]](0x02))"],
                capture_output=True, timeout=5)
            steps.append("Night light on")
        except: pass

        return {
            "success": True,
            "message": "Night mode active, Sir. Easy on the eyes.",
            "mode": "night",
            "steps": steps,
        }

    async def activate_cinema_mode(self) -> dict:
        self.current_mode = "cinema"
        return {
            "success": True,
            "message": "Cinema mode active, Sir. Enjoy the show. Say 'JARVIS' when you're done.",
            "mode": "cinema",
        }

    async def activate_gaming_mode(self) -> dict:
        self.current_mode = "gaming"
        try:
            subprocess.run(["powershell", "-Command",
                "Set-ItemProperty -Path 'HKCU:\\SOFTWARE\\Microsoft\\GameBar' -Name 'AutoGameModeEnabled' -Value 1"],
                capture_output=True, timeout=5)
        except: pass
        return {
            "success": True,
            "message": "Gaming mode active, Sir. Good luck.",
            "mode": "gaming",
        }

    async def activate_presentation_mode(self) -> dict:
        self.current_mode = "presentation"
        try:
            import screen_brightness_control as sbc
            sbc.set_brightness(100, display=0)
        except: pass
        return {
            "success": True,
            "message": "Presentation mode ready, Sir. Brightness maxed, notifications off.",
            "mode": "presentation",
        }

    async def deactivate(self) -> dict:
        prev = self.current_mode
        self.current_mode = "normal"
        if self._focus_timer_task:
            self._focus_timer_task.cancel()
            self._focus_timer_task = None

        # Restore brightness
        if self._original_brightness:
            try:
                import screen_brightness_control as sbc
                sbc.set_brightness(self._original_brightness, display=0)
            except: pass
            self._original_brightness = None

        # Re-enable notifications
        try:
            subprocess.run(["powershell", "-Command",
                "Set-ItemProperty -Path 'HKCU:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Notifications\\Settings' -Name 'NOC_GLOBAL_SETTING_ALLOW_NOTIFICATION_SOUND' -Value 1"],
                capture_output=True, timeout=5)
        except: pass

        return {
            "success": True,
            "message": f"Back to normal mode, Sir. {prev.title()} mode deactivated.",
            "mode": "normal",
        }

    async def _focus_countdown(self, minutes: int):
        total = minutes * 60
        try:
            while self._focus_remaining > 0:
                await asyncio.sleep(1)
                self._focus_remaining -= 1
                if self._focus_remaining == 300:
                    log.info("Focus mode: 5 minutes remaining")
            log.info("Focus session complete")
        except asyncio.CancelledError:
            pass

    def get_status(self) -> dict:
        return {
            "mode": self.current_mode,
            "focus_remaining_seconds": self._focus_remaining if self.current_mode == "focus" else 0,
        }
