"""
J.A.R.V.I.S Intent Classification Engine
Classifies user speech into actionable intents for command execution.
"""

import re
from typing import Tuple, Optional
from core.logger import get_logger

log = get_logger("intent")

# Intent categories
INTENT_OPEN_APP = "open_app"
INTENT_CLOSE_APP = "close_app"
INTENT_SEARCH_WEB = "search_web"
INTENT_SEARCH_YOUTUBE = "search_youtube"
INTENT_VOLUME_UP = "volume_up"
INTENT_VOLUME_DOWN = "volume_down"
INTENT_VOLUME_MUTE = "volume_mute"
INTENT_BRIGHTNESS_UP = "brightness_up"
INTENT_BRIGHTNESS_DOWN = "brightness_down"
INTENT_SCREENSHOT = "screenshot"
INTENT_SHUTDOWN = "shutdown"
INTENT_RESTART = "restart"
INTENT_LOCK = "lock_pc"
INTENT_SLEEP = "sleep_pc"
INTENT_MEDIA_PLAY = "media_play"
INTENT_MEDIA_PAUSE = "media_pause"
INTENT_MEDIA_NEXT = "media_next"
INTENT_MEDIA_PREV = "media_prev"
INTENT_TYPE_TEXT = "type_text"
INTENT_SYSTEM_INFO = "system_info"
INTENT_CONVERSATION = "conversation"
INTENT_UNKNOWN = "unknown"

# Application name mappings
APP_ALIASES = {
    "chrome": "chrome",
    "google chrome": "chrome",
    "browser": "chrome",
    "firefox": "firefox",
    "edge": "msedge",
    "microsoft edge": "msedge",
    "vs code": "code",
    "vscode": "code",
    "visual studio code": "code",
    "visual studio": "devenv",
    "notepad": "notepad",
    "calculator": "calc",
    "calc": "calc",
    "paint": "mspaint",
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
    "outlook": "outlook",
    "teams": "teams",
    "discord": "discord",
    "spotify": "spotify",
    "whatsapp": "whatsapp",
    "telegram": "telegram",
    "slack": "slack",
    "file explorer": "explorer",
    "explorer": "explorer",
    "files": "explorer",
    "downloads": "explorer_downloads",
    "documents": "explorer_documents",
    "desktop": "explorer_desktop",
    "task manager": "taskmgr",
    "settings": "ms-settings:",
    "control panel": "control",
    "command prompt": "cmd",
    "cmd": "cmd",
    "terminal": "wt",
    "powershell": "powershell",
    "snipping tool": "snippingtool",
    "zoom": "zoom",
    "obs": "obs64",
    "steam": "steam",
    "blender": "blender",
    "photoshop": "photoshop",
    "premiere": "premiere",
    "after effects": "afterfx",
    "figma": "figma",
}

# Intent patterns
PATTERNS = {
    INTENT_OPEN_APP: [
        r"open\s+(.+)",
        r"launch\s+(.+)",
        r"start\s+(.+)",
        r"run\s+(.+)",
    ],
    INTENT_CLOSE_APP: [
        r"close\s+(.+)",
        r"quit\s+(.+)",
        r"exit\s+(.+)",
        r"kill\s+(.+)",
        r"terminate\s+(.+)",
    ],
    INTENT_SEARCH_WEB: [
        r"search\s+(?:google\s+)?(?:for\s+)?(.+)",
        r"google\s+(.+)",
        r"look\s+up\s+(.+)",
    ],
    INTENT_SEARCH_YOUTUBE: [
        r"(?:search\s+)?youtube\s+(?:for\s+)?(.+)",
        r"play\s+(?:on\s+)?youtube\s+(.+)",
        r"find\s+(?:on\s+)?youtube\s+(.+)",
    ],
    INTENT_VOLUME_UP: [r"(?:increase|raise|up|turn\s+up)\s+(?:the\s+)?volume"],
    INTENT_VOLUME_DOWN: [r"(?:decrease|lower|down|turn\s+down)\s+(?:the\s+)?volume"],
    INTENT_VOLUME_MUTE: [r"mute\s+(?:the\s+)?(?:volume|sound|audio)", r"unmute"],
    INTENT_BRIGHTNESS_UP: [r"(?:increase|raise|up)\s+(?:the\s+)?brightness"],
    INTENT_BRIGHTNESS_DOWN: [r"(?:decrease|lower|down)\s+(?:the\s+)?brightness"],
    INTENT_SCREENSHOT: [r"(?:take\s+(?:a\s+)?)?screenshot", r"capture\s+screen"],
    INTENT_SHUTDOWN: [r"shutdown", r"shut\s+down", r"power\s+off", r"turn\s+off\s+(?:the\s+)?(?:pc|computer)"],
    INTENT_RESTART: [r"restart", r"reboot", r"restart\s+(?:the\s+)?(?:pc|computer|system)"],
    INTENT_LOCK: [r"lock\s+(?:the\s+)?(?:pc|computer|screen)"],
    INTENT_SLEEP: [r"sleep\s+(?:the\s+)?(?:pc|computer)", r"put\s+(?:the\s+)?(?:pc|computer)\s+to\s+sleep"],
    INTENT_MEDIA_PLAY: [r"play\s+(?:music|media|song)", r"resume\s+(?:music|media|playback)"],
    INTENT_MEDIA_PAUSE: [r"pause\s+(?:music|media|song|playback)", r"stop\s+(?:music|media|playback)"],
    INTENT_MEDIA_NEXT: [r"next\s+(?:song|track)", r"skip\s+(?:song|track)"],
    INTENT_MEDIA_PREV: [r"previous\s+(?:song|track)", r"(?:go\s+)?back\s+(?:song|track)"],
    INTENT_SYSTEM_INFO: [
        r"system\s+(?:info|information|status|stats)",
        r"(?:how\s+(?:is\s+)?(?:the\s+)?)?(?:cpu|ram|memory|disk|battery)\s+(?:usage|status)?",
        r"(?:what(?:'s|\s+is)\s+(?:the\s+)?)?(?:cpu|ram|memory|disk|battery)",
    ],
    INTENT_TYPE_TEXT: [r"type\s+(.+)", r"write\s+(.+)"],
}


class IntentClassifier:
    """Classifies user input into actionable intents."""

    def classify(self, text: str) -> Tuple[str, Optional[str]]:
        """
        Classify text into intent and extract parameters.
        Returns (intent, parameter) tuple.
        """
        if not text:
            return INTENT_UNKNOWN, None

        text_lower = text.lower().strip()

        # Remove wake word
        for prefix in ["jarvis", "hey jarvis", "ok jarvis", "j.a.r.v.i.s"]:
            if text_lower.startswith(prefix):
                text_lower = text_lower[len(prefix):].strip()
                # Remove leading comma or period
                text_lower = text_lower.lstrip(",.!? ")
                break

        if not text_lower:
            return INTENT_CONVERSATION, None

        # Check YouTube search first (before generic search)
        for pattern in PATTERNS[INTENT_SEARCH_YOUTUBE]:
            match = re.search(pattern, text_lower)
            if match:
                query = match.group(1).strip() if match.lastindex else ""
                log.info(f"Intent: search_youtube, query: {query}")
                return INTENT_SEARCH_YOUTUBE, query

        # Check all other patterns
        for intent, patterns in PATTERNS.items():
            if intent == INTENT_SEARCH_YOUTUBE:
                continue
            for pattern in patterns:
                match = re.search(pattern, text_lower)
                if match:
                    param = match.group(1).strip() if match.lastindex and match.lastindex >= 1 else None

                    # Resolve app names for open/close intents
                    if intent in (INTENT_OPEN_APP, INTENT_CLOSE_APP) and param:
                        param = self._resolve_app(param)

                    log.info(f"Intent: {intent}, param: {param}")
                    return intent, param

        # Default to conversation
        log.info(f"Intent: conversation (no pattern matched)")
        return INTENT_CONVERSATION, text_lower

    def _resolve_app(self, app_name: str) -> str:
        """Resolve app alias to executable name."""
        app_lower = app_name.lower().strip()
        return APP_ALIASES.get(app_lower, app_lower)
