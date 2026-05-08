"""
J.A.R.V.I.S Notification Service
Windows toast notifications via win10toast or plyer.
"""

import asyncio
import threading
from typing import Optional
from core.logger import get_logger

log = get_logger("notification")


class NotificationService:
    """Sends Windows toast notifications."""

    def __init__(self):
        self._notifier = None
        self._init_notifier()
        log.info("Notification service initialized")

    def _init_notifier(self):
        """Initialize the toast notification library."""
        try:
            from win10toast import ToastNotifier
            self._notifier = ToastNotifier()
            self._backend = "win10toast"
            log.debug("Using win10toast for notifications")
            return
        except ImportError:
            pass

        try:
            from plyer import notification
            self._notifier = notification
            self._backend = "plyer"
            log.debug("Using plyer for notifications")
            return
        except ImportError:
            pass

        self._backend = "powershell"
        log.debug("Using PowerShell fallback for notifications")

    async def notify(
        self,
        title: str = "J.A.R.V.I.S",
        message: str = "",
        duration: int = 5,
        icon_path: Optional[str] = None,
    ) -> dict:
        """Send a Windows toast notification."""
        try:
            if self._backend == "win10toast" and self._notifier:
                def _show():
                    try:
                        self._notifier.show_toast(
                            title, message,
                            duration=duration,
                            threaded=True,
                            icon_path=icon_path,
                        )
                    except Exception as e:
                        log.debug(f"win10toast error: {e}")
                await asyncio.to_thread(_show)

            elif self._backend == "plyer" and self._notifier:
                await asyncio.to_thread(
                    self._notifier.notify,
                    title=title,
                    message=message,
                    timeout=duration,
                    app_name="J.A.R.V.I.S",
                )

            else:
                # PowerShell fallback
                import subprocess
                ps_cmd = (
                    f'[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, '
                    f'ContentType = WindowsRuntime] > $null; '
                    f'$xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent(0); '
                    f'$text = $xml.GetElementsByTagName("text"); '
                    f'$text[0].AppendChild($xml.CreateTextNode("{title}")) > $null; '
                    f'$text[1].AppendChild($xml.CreateTextNode("{message}")) > $null; '
                    f'$toast = [Windows.UI.Notifications.ToastNotification]::new($xml); '
                    f'[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("JARVIS").Show($toast)'
                )
                await asyncio.to_thread(
                    subprocess.run,
                    ["powershell", "-Command", ps_cmd],
                    capture_output=True, timeout=10
                )

            log.info(f"Notification sent: {title} — {message[:50]}")
            return {"success": True, "message": f"Notification sent: {title}"}

        except Exception as e:
            log.error(f"Notification failed: {e}")
            return {"success": False, "message": f"Notification failed: {str(e)}"}

    async def notify_command_complete(self, command: str, result: str):
        """Notify when a command completes."""
        await self.notify(
            title="Command Complete",
            message=f"{command}: {result[:100]}",
            duration=3,
        )

    async def notify_reminder(self, task: str):
        """Notify for a reminder."""
        await self.notify(
            title="⏰ Reminder — J.A.R.V.I.S",
            message=task,
            duration=10,
        )

    async def notify_error(self, error: str):
        """Notify about an error."""
        await self.notify(
            title="⚠️ J.A.R.V.I.S Error",
            message=error[:200],
            duration=5,
        )

    def get_status(self) -> dict:
        return {
            "available": True,
            "backend": self._backend,
        }
