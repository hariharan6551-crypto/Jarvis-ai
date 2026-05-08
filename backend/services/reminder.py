"""
J.A.R.V.I.S Reminder Service
Schedule time-based reminders that fire as voice + toast notifications.
"""

import asyncio
import json
import time
import uuid
from typing import Optional, Callable
from core.logger import get_logger

log = get_logger("reminder")


class Reminder:
    """A single scheduled reminder."""

    def __init__(self, task: str, delay_seconds: float, reminder_id: str = None):
        self.id = reminder_id or str(uuid.uuid4())[:8]
        self.task = task
        self.delay_seconds = delay_seconds
        self.created_at = time.time()
        self.fire_at = self.created_at + delay_seconds
        self.fired = False
        self.cancelled = False

    def to_dict(self) -> dict:
        remaining = max(0, self.fire_at - time.time())
        return {
            "id": self.id,
            "task": self.task,
            "delay_seconds": self.delay_seconds,
            "remaining_seconds": round(remaining, 1),
            "fired": self.fired,
            "cancelled": self.cancelled,
            "created_at": time.strftime("%H:%M:%S", time.localtime(self.created_at)),
            "fire_at": time.strftime("%H:%M:%S", time.localtime(self.fire_at)),
        }


class ReminderService:
    """Manages scheduled reminders with voice and toast notification callbacks."""

    def __init__(self):
        self._reminders: list[Reminder] = []
        self._running = False
        self._task = None
        self.on_reminder_fire: Optional[Callable] = None  # async callback(task_text)
        self.on_notify: Optional[Callable] = None          # async callback(title, message)
        log.info("Reminder service initialized")

    async def start(self):
        """Start the reminder check loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._check_loop())
        log.info("Reminder service started")

    async def stop(self):
        """Stop the reminder service."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        log.info("Reminder service stopped")

    async def add_reminder(self, task: str, delay_seconds: float) -> dict:
        """Add a new reminder."""
        reminder = Reminder(task, delay_seconds)
        self._reminders.append(reminder)

        # Human-readable time
        if delay_seconds >= 3600:
            time_str = f"{int(delay_seconds // 3600)} hour(s)"
        elif delay_seconds >= 60:
            time_str = f"{int(delay_seconds // 60)} minute(s)"
        else:
            time_str = f"{int(delay_seconds)} second(s)"

        log.info(f"Reminder set: '{task}' in {time_str} (id: {reminder.id})")
        return {
            "success": True,
            "message": f"I'll remind you to {task} in {time_str}.",
            "reminder": reminder.to_dict(),
        }

    async def cancel_reminder(self, reminder_id: str) -> dict:
        """Cancel a specific reminder."""
        for r in self._reminders:
            if r.id == reminder_id and not r.fired:
                r.cancelled = True
                log.info(f"Reminder cancelled: {r.task} (id: {r.id})")
                return {"success": True, "message": f"Reminder '{r.task}' cancelled."}
        return {"success": False, "message": f"Reminder {reminder_id} not found."}

    async def cancel_all(self) -> dict:
        """Cancel all pending reminders."""
        count = 0
        for r in self._reminders:
            if not r.fired and not r.cancelled:
                r.cancelled = True
                count += 1
        log.info(f"Cancelled {count} reminder(s)")
        return {"success": True, "message": f"Cancelled {count} reminder(s)."}

    def get_pending(self) -> list:
        """Get all pending (unfired, uncancelled) reminders."""
        return [
            r.to_dict() for r in self._reminders
            if not r.fired and not r.cancelled
        ]

    def get_all(self) -> list:
        """Get all reminders."""
        return [r.to_dict() for r in self._reminders]

    async def _check_loop(self):
        """Check reminders every second."""
        while self._running:
            try:
                now = time.time()
                for reminder in self._reminders:
                    if reminder.cancelled or reminder.fired:
                        continue
                    if now >= reminder.fire_at:
                        reminder.fired = True
                        log.info(f"Reminder fired: '{reminder.task}'")
                        await self._fire_reminder(reminder)

                # Cleanup old reminders (keep last 100)
                if len(self._reminders) > 100:
                    self._reminders = self._reminders[-100:]

            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Reminder check error: {e}")

            await asyncio.sleep(1)

    async def _fire_reminder(self, reminder: Reminder):
        """Fire a reminder — invoke voice + notification callbacks."""
        try:
            if self.on_reminder_fire:
                if asyncio.iscoroutinefunction(self.on_reminder_fire):
                    await self.on_reminder_fire(reminder.task)
                else:
                    self.on_reminder_fire(reminder.task)

            if self.on_notify:
                if asyncio.iscoroutinefunction(self.on_notify):
                    await self.on_notify("⏰ Reminder", reminder.task)
                else:
                    self.on_notify("⏰ Reminder", reminder.task)

        except Exception as e:
            log.error(f"Error firing reminder: {e}")

    def get_status(self) -> dict:
        return {
            "running": self._running,
            "pending_count": len(self.get_pending()),
            "total_count": len(self._reminders),
        }
