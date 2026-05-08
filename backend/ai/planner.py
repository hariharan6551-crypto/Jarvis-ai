"""
J.A.R.V.I.S AI Task Planner
Decomposes complex natural language commands into executable multi-step plans.
Uses Gemini/OpenAI to reason about multi-step tasks.
"""

import asyncio
import json
import re
from typing import Optional
from core.logger import get_logger
from config.settings import settings

log = get_logger("planner")


# Step types the planner can produce
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
STEP_MEDIA = "media_control"
STEP_SWITCH_WINDOW = "switch_window"
STEP_FILE_OP = "file_operation"
STEP_SPEAK = "speak"
STEP_CONVERSATION = "conversation"

PLANNER_SYSTEM_PROMPT = """You are J.A.R.V.I.S, an AI task planner for a Windows desktop automation system.
Your job is to decompose user commands into executable steps.

AVAILABLE STEP TYPES:
- open_app: Open an application. param = app name (chrome, notepad, vscode, excel, explorer, etc.)
- close_app: Close an application. param = app name
- browser_profile: Open Chrome with specific profile. param = profile name
- navigate_url: Navigate browser to URL. param = URL
- search_web: Search Google. param = search query
- search_youtube: Search YouTube. param = search query
- click_text: Click on text visible on screen (OCR). param = text to click
- type_text: Type text at current cursor. param = text to type
- press_key: Press keyboard shortcut. param = key combo (e.g., "ctrl+c", "enter", "alt+tab")
- wait: Wait for seconds. param = seconds (e.g., "2")
- screenshot: Take screenshot. param = null
- read_screen: Read text from screen via OCR. param = null
- system_cmd: Run system command. param = command string
- volume: Volume control. param = "up", "down", or "mute"
- brightness: Brightness control. param = "up" or "down"
- media_control: Media control. param = "play", "pause", "next", "prev"
- switch_window: Switch to a window. param = window title keyword
- file_operation: File operation. param = JSON {"action": "open|create|delete", "path": "..."}
- speak: Speak a message. param = message text
- conversation: AI conversation response. param = original user message

RULES:
1. Return a JSON array of steps, each with "type" and "param"
2. Keep plans minimal — fewest steps needed
3. For simple single-action commands, return just one step
4. For "open Chrome with profile X" → use browser_profile step
5. Add wait steps between UI actions that need loading time
6. Always end multi-step plans with a speak step confirming completion
7. For conversational messages (greetings, questions), use conversation type

EXAMPLES:

User: "Open Chrome and select Mersal Hariharan Google account"
[{"type": "browser_profile", "param": "Mersal Hariharan"}, {"type": "wait", "param": "2"}, {"type": "speak", "param": "Chrome is now open with Mersal Hariharan's profile."}]

User: "Open notepad and type hello world"
[{"type": "open_app", "param": "notepad"}, {"type": "wait", "param": "1"}, {"type": "type_text", "param": "hello world"}, {"type": "speak", "param": "Done. I've typed hello world in Notepad."}]

User: "Search YouTube for Python tutorials"
[{"type": "search_youtube", "param": "Python tutorials"}]

User: "What time is it?"
[{"type": "conversation", "param": "What time is it?"}]

User: "Increase volume and open Spotify"
[{"type": "volume", "param": "up"}, {"type": "open_app", "param": "spotify"}, {"type": "speak", "param": "Volume increased and Spotify is opening."}]

User: "Take a screenshot and save it"
[{"type": "screenshot", "param": null}]

Return ONLY the JSON array. No explanation, no markdown."""


class TaskPlanner:
    """Decomposes complex commands into sequential executable steps using AI."""

    def __init__(self, ai_provider=None):
        self.ai_provider = ai_provider
        log.info("Task Planner initialized")

    def set_ai_provider(self, provider):
        """Set the AI provider (called after orchestrator init)."""
        self.ai_provider = provider

    async def plan(self, user_command: str) -> list[dict]:
        """
        Generate an execution plan from a natural language command.
        Returns a list of steps: [{"type": "...", "param": "..."}, ...]
        """
        # Try quick pattern matching first for simple commands
        quick_plan = self._quick_classify(user_command)
        if quick_plan:
            log.info(f"Quick plan for '{user_command}': {len(quick_plan)} steps")
            return quick_plan

        # Fall back to AI planning for complex commands
        if self.ai_provider:
            return await self._ai_plan(user_command)

        # Absolute fallback: treat as conversation
        return [{"type": STEP_CONVERSATION, "param": user_command}]

    def _quick_classify(self, text: str) -> Optional[list[dict]]:
        """Fast regex-based classification for simple commands."""
        t = text.lower().strip()

        # Remove wake word
        for prefix in ["jarvis", "hey jarvis", "ok jarvis", "j.a.r.v.i.s"]:
            if t.startswith(prefix):
                t = t[len(prefix):].strip().lstrip(",.!? ")
                break

        if not t:
            return [{"type": STEP_CONVERSATION, "param": "hello"}]

        # Compound commands with "and" → let AI handle (except chrome profile commands)
        if " and " in t and not re.search(r"chrome.*and\s+(?:select|choose|use|open)", t):
            parts = t.split(" and ")
            if len(parts) > 1 and all(len(p.strip()) > 2 for p in parts):
                return None  # Route to AI planner for multi-step decomposition

        # Chrome with profile
        chrome_profile = re.search(
            r"(?:open|launch|start)\s+(?:google\s+)?chrome\s+(?:with|using|and\s+(?:select|choose|use|open))\s+(.+?)(?:\s+(?:account|profile|google\s+account))?$",
            t, re.IGNORECASE
        )
        if chrome_profile:
            profile_name = chrome_profile.group(1).strip()
            # Clean up common suffixes
            for suffix in ["account", "profile", "google account", "google"]:
                if profile_name.lower().endswith(suffix):
                    profile_name = profile_name[:-(len(suffix))].strip()
            return [
                {"type": STEP_BROWSER_PROFILE, "param": profile_name},
                {"type": STEP_WAIT, "param": "2"},
                {"type": STEP_SPEAK, "param": f"Chrome is now open with {profile_name}'s profile."},
            ]

        # Simple app open
        app_match = re.match(r"(?:open|launch|start|run)\s+(.+)", t)
        if app_match:
            app = app_match.group(1).strip()
            # Check if there's a compound command (open X and do Y)
            if " and " in app:
                return None  # Let AI handle compound commands
            return [{"type": STEP_OPEN_APP, "param": app}]

        # Close app
        close_match = re.match(r"(?:close|quit|exit|kill)\s+(.+)", t)
        if close_match:
            return [{"type": STEP_CLOSE_APP, "param": close_match.group(1).strip()}]

        # YouTube search
        yt_match = re.search(r"(?:search\s+)?youtube\s+(?:for\s+)?(.+)", t)
        if yt_match:
            return [{"type": STEP_SEARCH_YOUTUBE, "param": yt_match.group(1).strip()}]

        # Web search
        search_match = re.search(r"(?:search|google)\s+(?:for\s+)?(.+)", t)
        if search_match:
            return [{"type": STEP_SEARCH_WEB, "param": search_match.group(1).strip()}]

        # Volume
        if re.search(r"(?:increase|raise|turn\s+up|up)\s+(?:the\s+)?volume", t):
            return [{"type": STEP_VOLUME, "param": "up"}]
        if re.search(r"(?:decrease|lower|turn\s+down|down)\s+(?:the\s+)?volume", t):
            return [{"type": STEP_VOLUME, "param": "down"}]
        if re.search(r"mute|unmute", t):
            return [{"type": STEP_VOLUME, "param": "mute"}]

        # Brightness
        if re.search(r"(?:increase|raise|up)\s+(?:the\s+)?brightness", t):
            return [{"type": STEP_BRIGHTNESS, "param": "up"}]
        if re.search(r"(?:decrease|lower|down)\s+(?:the\s+)?brightness", t):
            return [{"type": STEP_BRIGHTNESS, "param": "down"}]

        # Screenshot
        if re.search(r"screenshot|capture\s+screen", t):
            return [{"type": STEP_SCREENSHOT, "param": None}]

        # Media controls
        if re.search(r"(?:play|resume)\s+(?:music|media|song)", t):
            return [{"type": STEP_MEDIA, "param": "play"}]
        if re.search(r"(?:pause|stop)\s+(?:music|media|song|playback)", t):
            return [{"type": STEP_MEDIA, "param": "pause"}]
        if re.search(r"(?:next|skip)\s+(?:song|track)", t):
            return [{"type": STEP_MEDIA, "param": "next"}]
        if re.search(r"(?:previous|back)\s+(?:song|track)", t):
            return [{"type": STEP_MEDIA, "param": "prev"}]

        # System commands
        if re.search(r"(?:system|pc|computer)\s+(?:info|status|stats)", t):
            return [{"type": STEP_SYSTEM_CMD, "param": "info"}]
        if re.search(r"shutdown|shut\s+down|power\s+off", t):
            return [{"type": STEP_SYSTEM_CMD, "param": "shutdown"}]
        if re.search(r"restart|reboot", t):
            return [{"type": STEP_SYSTEM_CMD, "param": "restart"}]
        if re.search(r"lock\s+(?:the\s+)?(?:pc|computer|screen)", t):
            return [{"type": STEP_SYSTEM_CMD, "param": "lock"}]
        if re.search(r"sleep", t):
            return [{"type": STEP_SYSTEM_CMD, "param": "sleep"}]

        # Type text
        type_match = re.match(r"(?:type|write)\s+(.+)", t)
        if type_match:
            return [{"type": STEP_TYPE_TEXT, "param": type_match.group(1).strip()}]

        # Read screen
        if re.search(r"read\s+(?:the\s+)?screen|what(?:'s|\s+is)\s+on\s+(?:the\s+)?screen", t):
            return [{"type": STEP_READ_SCREEN, "param": None}]

        # If contains "and" — likely multi-step, let AI handle
        if " and " in t and len(t.split(" and ")) > 1:
            return None

        # Default: no quick match — return None to trigger AI planner
        return None

    async def _ai_plan(self, user_command: str) -> list[dict]:
        """Use AI to generate a multi-step execution plan."""
        try:
            response = await self.ai_provider.chat(
                message=f"User command: \"{user_command}\"\n\nGenerate the execution plan as a JSON array.",
                system_prompt=PLANNER_SYSTEM_PROMPT,
            )

            # Extract JSON from response
            plan = self._parse_plan_json(response)
            if plan:
                log.info(f"AI plan for '{user_command}': {len(plan)} steps")
                return plan

            log.warning(f"AI planner returned invalid response: {response[:200]}")
            return [{"type": STEP_CONVERSATION, "param": user_command}]

        except Exception as e:
            log.error(f"AI planning failed: {e}")
            return [{"type": STEP_CONVERSATION, "param": user_command}]

    def _parse_plan_json(self, response: str) -> Optional[list[dict]]:
        """Parse the AI response to extract the JSON plan."""
        # Try direct parse
        try:
            plan = json.loads(response.strip())
            if isinstance(plan, list):
                return self._validate_plan(plan)
        except json.JSONDecodeError:
            pass

        # Try to extract JSON from markdown code block
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", response, re.DOTALL)
        if json_match:
            try:
                plan = json.loads(json_match.group(1).strip())
                if isinstance(plan, list):
                    return self._validate_plan(plan)
            except json.JSONDecodeError:
                pass

        # Try to find array in response
        array_match = re.search(r"\[.*\]", response, re.DOTALL)
        if array_match:
            try:
                plan = json.loads(array_match.group(0))
                if isinstance(plan, list):
                    return self._validate_plan(plan)
            except json.JSONDecodeError:
                pass

        return None

    def _validate_plan(self, plan: list) -> list[dict]:
        """Validate and clean a parsed plan."""
        valid_types = {
            STEP_OPEN_APP, STEP_CLOSE_APP, STEP_BROWSER_PROFILE,
            STEP_NAVIGATE_URL, STEP_SEARCH_WEB, STEP_SEARCH_YOUTUBE,
            STEP_CLICK_TEXT, STEP_TYPE_TEXT, STEP_PRESS_KEY,
            STEP_WAIT, STEP_SCREENSHOT, STEP_READ_SCREEN,
            STEP_SYSTEM_CMD, STEP_VOLUME, STEP_BRIGHTNESS,
            STEP_MEDIA, STEP_SWITCH_WINDOW, STEP_FILE_OP,
            STEP_SPEAK, STEP_CONVERSATION,
        }

        validated = []
        for step in plan:
            if isinstance(step, dict) and "type" in step:
                if step["type"] in valid_types:
                    validated.append({
                        "type": step["type"],
                        "param": step.get("param"),
                    })
                else:
                    log.warning(f"Unknown step type: {step['type']}")
        return validated if validated else None
