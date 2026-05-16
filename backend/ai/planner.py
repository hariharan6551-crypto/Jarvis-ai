"""
J.A.R.V.I.S Task Planner
Decomposes complex natural language commands into executable step sequences.
Features: asyncio.Queue execution, 10s timeout per step, task status tracking.
"""

import asyncio
import json
import re
import time
from typing import Optional
from core.logger import get_logger
from config.settings import settings

log = get_logger("planner")

# ─── Step Type Constants ──────────────────────────────────────────────

STEP_OPEN_APP = "open_app"
STEP_CLOSE_APP = "close_app"
STEP_BROWSER_PROFILE = "browser_profile"
STEP_NAVIGATE_URL = "navigate_url"
STEP_SEARCH_WEB = "search_web"
STEP_SEARCH_YOUTUBE = "search_youtube"
STEP_CLICK_TEXT = "click_text"
STEP_TYPE_TEXT = "type_text"
STEP_PRESS_KEY = "press_key"
STEP_WAIT = "wait"
STEP_SCREENSHOT = "screenshot"
STEP_READ_SCREEN = "read_screen"
STEP_SYSTEM_CMD = "system_cmd"
STEP_VOLUME = "volume"
STEP_BRIGHTNESS = "brightness"
STEP_MEDIA = "media"
STEP_SWITCH_WINDOW = "switch_window"
STEP_FILE_OP = "file_op"
STEP_SPEAK = "speak"
STEP_CONVERSATION = "conversation"
STEP_SET_REMINDER = "set_reminder"
STEP_CLIPBOARD = "clipboard"
STEP_WINDOW_CTRL = "window_control"
STEP_WEATHER = "weather"
STEP_FOCUS_MODE = "focus_mode"
STEP_FILE_FIND = "file_find"
STEP_FILE_CREATE = "file_create"


# ─── Task Status Tracking ────────────────────────────────────────────

class TaskStatus:
    """Track the status of a single task."""

    def __init__(self, task_id: str, command: str, plan: list):
        self.task_id = task_id
        self.command = command
        self.plan = plan
        self.status = "pending"  # pending, running, success, partial, failed
        self.current_step = 0
        self.total_steps = len(plan)
        self.step_results = []
        self.start_time = time.time()
        self.end_time = None
        self.error = None

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "command": self.command,
            "status": self.status,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "elapsed_ms": round((time.time() - self.start_time) * 1000, 2),
            "error": self.error,
        }


# ─── Task Planner ─────────────────────────────────────────────────────

class TaskPlanner:
    """AI-powered task planner that decomposes commands into executable steps."""

    def __init__(self, ai_provider=None):
        self.ai_provider = ai_provider
        self._task_queue = asyncio.Queue()
        self._task_history = []  # Recent task statuses
        self._max_history = 50
        self._step_timeout = 10  # seconds per step
        self._is_processing = False

        # Chrome profile aliases (resolved during planning)
        self._profile_patterns = {
            "mersal hariharan": "Mersal Hariharan",
            "hariharan": "Mersal Hariharan",
            "mersal": "Mersal Hariharan",
            "personal": "Personal",
            "work": "Work",
            "school": "School",
            "college": "College",
        }

        log.info("Task planner initialized")

    # ─── Quick Classification (no AI needed) ──────────────────────────

    def _quick_classify(self, text: str) -> Optional[list]:
        """
        Fast local classification for common commands.
        Returns a plan (list of steps) or None if AI is needed.
        """
        text_lower = text.lower().strip()

        # Remove wake word prefix
        for prefix in ["jarvis", "hey jarvis", "ok jarvis"]:
            if text_lower.startswith(prefix):
                text_lower = text_lower[len(prefix):].strip()
                text_lower = text_lower.lstrip(",.!? ")
                break

        if not text_lower:
            return [{"type": STEP_CONVERSATION, "param": "hello"}]

        # ── Chrome with profile ──
        profile_match = re.search(
            r"open\s+chrome\s+(?:and\s+)?(?:select|use|with|load|switch\s+to)\s+(.+?)(?:\s+account|\s+profile)?$",
            text_lower,
        )
        if profile_match:
            profile_name = profile_match.group(1).strip()
            resolved = self._resolve_profile(profile_name)
            return [
                {"type": STEP_OPEN_APP, "param": "chrome"},
                {"type": STEP_WAIT, "param": "1"},
                {"type": STEP_BROWSER_PROFILE, "param": resolved},
            ]

        # ══════════════════════════════════════════════════════════════
        # TANGLISH COMMANDS (Tamil + English)
        # ══════════════════════════════════════════════════════════════

        # Tanglish open: "chrome open pannu", "notepad thuru"
        tanglish_open = re.match(r"(.+?)\s+(?:open\s+pannu|thuru|open\s+pannuda|open\s+podu)", text_lower)
        if tanglish_open:
            return [{"type": STEP_OPEN_APP, "param": tanglish_open.group(1).strip()}]

        # Tanglish close: "chrome close pannu", "chrome ah moodu"
        tanglish_close = re.match(r"(.+?)\s+(?:close\s+pannu|moodu|close\s+pannuda|ah\s+moodu)", text_lower)
        if tanglish_close:
            return [{"type": STEP_CLOSE_APP, "param": tanglish_close.group(1).strip()}]

        # Tanglish screenshot: "screenshot edu", "screen capture pannu"
        if re.search(r"screenshot\s+edu|screen\s+capture\s+pannu|screen\s+edu", text_lower):
            return [{"type": STEP_SCREENSHOT, "param": None}]

        # Tanglish time: "time sollu", "neram enna", "mani enna"
        if re.search(r"time\s+sollu|neram\s+enna|mani\s+enna|time\s+enna", text_lower):
            from datetime import datetime
            now = datetime.now().strftime("%I:%M %p")
            return [{"type": STEP_SPEAK, "param": f"Sir, ippo time {now}"}]

        # Tanglish date: "date sollu", "enna date"
        if re.search(r"date\s+sollu|enna\s+date|inaikku\s+enna", text_lower):
            from datetime import datetime
            today = datetime.now().strftime("%A, %B %d, %Y")
            return [{"type": STEP_SPEAK, "param": f"Sir, inaikku {today}"}]

        # Tanglish volume: "volume uyarthu/kuraithu"
        if re.search(r"volume\s+(?:uyarthu|ethu|athigam|high)", text_lower):
            return [{"type": STEP_VOLUME, "param": "up"}]
        if re.search(r"volume\s+(?:kuraithu|thazhthu|kammi|low)", text_lower):
            return [{"type": STEP_VOLUME, "param": "down"}]

        # Tanglish music: "music podu", "paattu podu"
        if re.search(r"music\s+podu|paattu\s+podu|song\s+podu|play\s+pannu", text_lower):
            return [{"type": STEP_MEDIA, "param": "play"}]
        if re.search(r"music\s+niruthu|paattu\s+niruthu|stop\s+pannu|pause\s+pannu", text_lower):
            return [{"type": STEP_MEDIA, "param": "pause"}]

        # Tanglish search: "google la search pannu", "youtube la search pannu"
        tanglish_yt = re.match(r"youtube\s+(?:la|ula)\s+(?:search\s+pannu|thedi)\s+(.+)", text_lower)
        if tanglish_yt:
            return [{"type": STEP_SEARCH_YOUTUBE, "param": tanglish_yt.group(1).strip()}]
        tanglish_search = re.match(r"(?:google\s+(?:la|ula)\s+(?:search\s+pannu|thedi)|thedi)\s+(.+)", text_lower)
        if tanglish_search:
            return [{"type": STEP_SEARCH_WEB, "param": tanglish_search.group(1).strip()}]

        # Tanglish weather: "weather sollu", "weather eppadi"
        if re.search(r"weather\s+(?:sollu|eppadi|enna)|vaanilai\s+(?:sollu|enna)", text_lower):
            return [{"type": STEP_WEATHER, "param": "current"}]

        # Tanglish shutdown/lock/sleep
        if re.search(r"pc\s+(?:ah\s+)?(?:off\s+pannu|anaippu|shut\s+pannu)", text_lower):
            return [{"type": STEP_SYSTEM_CMD, "param": "shutdown"}]
        if re.search(r"pc\s+(?:ah\s+)?(?:lock\s+pannu|pootu)", text_lower):
            return [{"type": STEP_SYSTEM_CMD, "param": "lock"}]

        # ══════════════════════════════════════════════════════════════
        # ENGLISH COMMANDS
        # ══════════════════════════════════════════════════════════════

        # ── Open app ──
        open_match = re.match(r"(?:please\s+)?(?:open|launch|start|run)\s+(?:the\s+|my\s+|a\s+)?(.+)", text_lower)
        if open_match:
            app = open_match.group(1).strip()
            # Remove trailing words like "app", "application", "please"
            app = re.sub(r"\s+(?:app|application|please|for me)$", "", app)
            return [{"type": STEP_OPEN_APP, "param": app}]

        # ── Close app ──
        close_match = re.match(r"(?:please\s+)?(?:close|quit|exit|kill|terminate)\s+(?:the\s+|my\s+)?(.+)", text_lower)
        if close_match:
            app = close_match.group(1).strip()
            app = re.sub(r"\s+(?:app|application|please|for me)$", "", app)
            return [{"type": STEP_CLOSE_APP, "param": app}]

        # ── YouTube search ──
        yt_match = re.match(
            r"(?:search\s+youtube\s+for|youtube\s+search|play\s+on\s+youtube|find\s+on\s+youtube)\s+(.+)",
            text_lower,
        )
        if yt_match:
            query = yt_match.group(1).strip()
            return [{"type": STEP_SEARCH_YOUTUBE, "param": query}]

        # ── Web search ──
        search_match = re.match(
            r"(?:search|google|look\s+up)\s+(?:for\s+)?(.+)",
            text_lower,
        )
        if search_match and "youtube" not in text_lower:
            query = search_match.group(1).strip()
            return [{"type": STEP_SEARCH_WEB, "param": query}]

        # ── Weather ──
        if re.search(r"(?:what(?:'s|\s+is)\s+(?:the\s+)?)?weather|how(?:'s|\s+is)\s+(?:the\s+)?weather|will\s+it\s+rain|temperature", text_lower):
            if re.search(r"rain", text_lower):
                return [{"type": STEP_WEATHER, "param": "rain"}]
            if re.search(r"forecast", text_lower):
                return [{"type": STEP_WEATHER, "param": "forecast"}]
            return [{"type": STEP_WEATHER, "param": "current"}]

        # ── Focus / Night / Cinema / Gaming modes ──
        if re.search(r"(?:activate|start|enable)\s+focus\s+(?:mode)?|focus\s+mode", text_lower):
            return [{"type": STEP_FOCUS_MODE, "param": "focus"}]
        if re.search(r"(?:activate|start|enable)\s+night\s+(?:mode)?|night\s+mode", text_lower):
            return [{"type": STEP_FOCUS_MODE, "param": "night"}]
        if re.search(r"(?:activate|start|enable)\s+cinema\s+(?:mode)?|cinema\s+mode|movie\s+mode", text_lower):
            return [{"type": STEP_FOCUS_MODE, "param": "cinema"}]
        if re.search(r"(?:activate|start|enable)\s+gaming\s+(?:mode)?|gaming\s+mode|game\s+mode", text_lower):
            return [{"type": STEP_FOCUS_MODE, "param": "gaming"}]
        if re.search(r"(?:activate|start|enable)\s+presentation\s+(?:mode)?|presentation\s+mode", text_lower):
            return [{"type": STEP_FOCUS_MODE, "param": "presentation"}]
        if re.search(r"(?:deactivate|stop|disable|exit)\s+(?:focus|night|cinema|gaming|presentation)\s+(?:mode)?|normal\s+mode", text_lower):
            return [{"type": STEP_FOCUS_MODE, "param": "normal"}]

        # ── File operations ──
        file_find = re.match(r"(?:find|locate|search\s+for)\s+(?:file\s+)?(.+?)(?:\s+(?:file|on\s+my\s+pc))?$", text_lower)
        if file_find and not re.search(r"youtube|google|web", text_lower):
            return [{"type": STEP_FILE_FIND, "param": file_find.group(1).strip()}]

        # ── Volume ──
        if re.search(r"(?:increase|raise|turn\s+up)\s+(?:the\s+)?volume|volume\s+up|louder", text_lower):
            return [{"type": STEP_VOLUME, "param": "up"}]
        if re.search(r"(?:decrease|lower|turn\s+down)\s+(?:the\s+)?volume|volume\s+down|quieter", text_lower):
            return [{"type": STEP_VOLUME, "param": "down"}]
        if re.search(r"mute|unmute", text_lower):
            return [{"type": STEP_VOLUME, "param": "mute"}]

        vol_match = re.search(r"(?:set\s+)?volume\s+(?:to\s+)?(\d+)", text_lower)
        if vol_match:
            return [{"type": STEP_VOLUME, "param": f"set:{vol_match.group(1)}"}]

        # ── Brightness ──
        if re.search(r"(?:increase|raise)\s+(?:the\s+)?brightness|brighter", text_lower):
            return [{"type": STEP_BRIGHTNESS, "param": "up"}]
        if re.search(r"(?:decrease|lower)\s+(?:the\s+)?brightness|dimmer", text_lower):
            return [{"type": STEP_BRIGHTNESS, "param": "down"}]

        # ── Screenshot ──
        if re.search(r"(?:take\s+(?:a\s+)?)?screenshot|capture\s+(?:the\s+)?screen", text_lower):
            return [{"type": STEP_SCREENSHOT, "param": None}]

        # ── System ──
        if re.search(r"shutdown|shut\s+down|power\s+off", text_lower):
            return [{"type": STEP_SYSTEM_CMD, "param": "shutdown"}]
        if re.search(r"restart|reboot", text_lower):
            return [{"type": STEP_SYSTEM_CMD, "param": "restart"}]
        if re.search(r"lock\s+(?:the\s+)?(?:pc|computer|screen)", text_lower):
            return [{"type": STEP_SYSTEM_CMD, "param": "lock"}]
        if re.search(r"sleep\s+(?:the\s+)?(?:pc|computer|mode)", text_lower):
            return [{"type": STEP_SYSTEM_CMD, "param": "sleep"}]
        if re.search(r"(?:system|pc|computer)\s+(?:info|status|stats)|(?:cpu|ram|memory|battery)\s*(?:usage)?", text_lower):
            return [{"type": STEP_SYSTEM_CMD, "param": "info"}]

        # ── Media ──
        if re.search(r"(?:play|resume)\s+(?:music|media|song|playback)|^play$", text_lower):
            return [{"type": STEP_MEDIA, "param": "play"}]
        if re.search(r"(?:pause|stop)\s+(?:music|media|song|playback)|^pause$", text_lower):
            return [{"type": STEP_MEDIA, "param": "pause"}]
        if re.search(r"(?:next|skip)\s+(?:song|track)|^next$|^skip$", text_lower):
            return [{"type": STEP_MEDIA, "param": "next"}]
        if re.search(r"(?:previous|back|last)\s+(?:song|track)|^previous$", text_lower):
            return [{"type": STEP_MEDIA, "param": "prev"}]

        # ── Type text ──
        type_match = re.match(r"(?:type|write)\s+(.+)", text_lower)
        if type_match:
            return [{"type": STEP_TYPE_TEXT, "param": type_match.group(1)}]

        # ── Press key ──
        key_match = re.match(r"(?:press|hit)\s+(.+)", text_lower)
        if key_match:
            return [{"type": STEP_PRESS_KEY, "param": key_match.group(1)}]

        # ── Reminders ──
        reminder_match = re.match(
            r"remind\s+me\s+(?:in\s+)?(\d+)\s*(minutes?|mins?|hours?|hrs?|seconds?|secs?)\s+(?:to\s+)?(.+)",
            text_lower,
        )
        if reminder_match:
            amount = int(reminder_match.group(1))
            unit = reminder_match.group(2).lower()
            task = reminder_match.group(3).strip()
            if unit.startswith("h"):
                seconds = amount * 3600
            elif unit.startswith("m"):
                seconds = amount * 60
            else:
                seconds = amount
            return [{"type": STEP_SET_REMINDER, "param": json.dumps({"seconds": seconds, "task": task})}]

        # ── Window control ──
        if re.search(r"(?:maximize|max)\s+(?:the\s+)?window", text_lower):
            return [{"type": STEP_WINDOW_CTRL, "param": "maximize"}]
        if re.search(r"(?:minimize|min)\s+(?:the\s+)?window|minimize\s+everything|show\s+desktop", text_lower):
            return [{"type": STEP_WINDOW_CTRL, "param": "minimize"}]
        if re.search(r"alt\s+tab", text_lower):
            return [{"type": STEP_PRESS_KEY, "param": "alt+tab"}]

        # ── Time / Date ──
        if re.search(r"what\s*(?:'s|\s+is)\s+(?:the\s+)?time|what\s+time|current\s+time", text_lower):
            from datetime import datetime
            now = datetime.now().strftime("%I:%M %p")
            return [{"type": STEP_SPEAK, "param": f"The current time is {now}"}]
        if re.search(r"what\s*(?:'s|\s+is)\s+(?:the\s+)?(?:date|day)|today(?:'s)?\s+date|what\s+day", text_lower):
            from datetime import datetime
            today = datetime.now().strftime("%A, %B %d, %Y")
            return [{"type": STEP_SPEAK, "param": f"Today is {today}"}]

        # ── Clipboard ──
        if re.search(r"read\s+(?:the\s+)?clipboard|what(?:'s|\s+is)\s+(?:in\s+)?(?:the\s+)?clipboard", text_lower):
            return [{"type": STEP_CLIPBOARD, "param": "read"}]

        # ── Simple greetings (English + Tanglish) ──
        greetings = ["hello", "hi", "hey", "good morning", "good afternoon", "good evening",
                     "howdy", "how are you", "vanakkam", "vaanga", "eppadi irukeenga",
                     "nandri", "thanks", "thank you"]
        if text_lower in greetings or any(text_lower.startswith(g) for g in greetings):
            return [{"type": STEP_CONVERSATION, "param": text_lower}]

        # Not a simple command — needs AI planning
        return None

    # ─── AI-Powered Planning ──────────────────────────────────────────

    PLANNING_PROMPT = """Decompose the user command into a JSON array of steps. Output ONLY valid JSON, nothing else.

Step types: open_app, close_app, browser_profile, navigate_url, search_web, search_youtube,
click_text, type_text, press_key, wait, screenshot, read_screen, system_cmd, volume,
brightness, media, switch_window, speak, conversation

Examples:
"open chrome and search for AI" → [{"type":"open_app","param":"chrome"},{"type":"wait","param":"2"},{"type":"search_web","param":"AI"}]
"take a screenshot" → [{"type":"screenshot","param":null}]
"tell me about Mars" → [{"type":"conversation","param":"tell me about Mars"}]

User command: {command}
JSON:"""

    async def plan(self, command: str) -> list:
        """Generate an execution plan for a command."""
        # Try quick classification first (fast, no AI call)
        quick_plan = self._quick_classify(command)
        if quick_plan is not None:
            log.info(f"Quick plan for '{command}': {[s['type'] for s in quick_plan]}")
            return quick_plan

        # Fall back to AI planning
        if self.ai_provider and settings.USE_AI_PLANNER:
            try:
                plan = await self._ai_plan(command)
                if plan:
                    log.info(f"AI plan for '{command}': {[s['type'] for s in plan]}")
                    return plan
            except Exception as e:
                log.error(f"AI planning failed: {e}")

        # Ultimate fallback: treat as conversation
        log.info(f"Fallback to conversation for: '{command}'")
        return [{"type": STEP_CONVERSATION, "param": command}]

    async def _ai_plan(self, command: str) -> Optional[list]:
        """Use AI to decompose a complex command into steps."""
        if not self.ai_provider:
            return None

        try:
            prompt = self.PLANNING_PROMPT.format(command=command)
            response = await self.ai_provider.chat(
                message=prompt,
                system_prompt="Output ONLY a valid JSON array. No text, no explanation, no markdown.",
            )

            # Robust JSON extraction
            response = response.strip()
            # Remove markdown code blocks if present
            response = re.sub(r"```(?:json)?\s*", "", response)
            response = re.sub(r"\s*```", "", response)
            response = response.strip()

            # Find the JSON array in the response (it might have extra text)
            bracket_start = response.find('[')
            bracket_end = response.rfind(']')
            if bracket_start != -1 and bracket_end != -1 and bracket_end > bracket_start:
                response = response[bracket_start:bracket_end + 1]

            plan = json.loads(response)
            if isinstance(plan, list) and all(isinstance(s, dict) and "type" in s for s in plan):
                return plan

            log.warning(f"Invalid AI plan format: {response[:200]}")
            return None
        except json.JSONDecodeError as e:
            log.error(f"AI plan JSON parse error: {e} — raw: {response[:100]}")
            return None
        except Exception as e:
            log.error(f"AI plan generation failed: {e}")
            return None

    # ─── Profile Resolution ───────────────────────────────────────────

    def _resolve_profile(self, name: str) -> str:
        """Resolve a spoken profile name to actual Chrome profile name."""
        name_lower = name.lower().strip()
        return self._profile_patterns.get(name_lower, name.title())

    # ─── Task Queue ───────────────────────────────────────────────────

    async def enqueue_task(self, command: str) -> str:
        """Add a task to the async queue. Returns task ID."""
        import uuid
        task_id = str(uuid.uuid4())[:8]
        plan = await self.plan(command)
        status = TaskStatus(task_id, command, plan)
        await self._task_queue.put((task_id, command, plan, status))
        self._task_history.append(status)
        if len(self._task_history) > self._max_history:
            self._task_history = self._task_history[-self._max_history:]
        log.info(f"Task {task_id} queued: '{command}' ({len(plan)} steps)")
        return task_id

    def get_task_status(self, task_id: str) -> Optional[dict]:
        """Get status of a queued task."""
        for status in self._task_history:
            if status.task_id == task_id:
                return status.to_dict()
        return None

    def get_recent_tasks(self, limit: int = 10) -> list:
        """Get recent task statuses."""
        return [t.to_dict() for t in self._task_history[-limit:]]

    @property
    def step_timeout(self) -> int:
        """Get step timeout in seconds."""
        return self._step_timeout

    @step_timeout.setter
    def step_timeout(self, value: int):
        """Set step timeout in seconds."""
        self._step_timeout = max(5, min(60, value))
