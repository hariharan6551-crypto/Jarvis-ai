"""
J.A.R.V.I.S Intent Classification Engine
Classifies user speech into actionable intents for command execution.
Features: confidence scoring, 12+ intent categories, activate/deactivate detection.
"""

import re
from typing import Tuple, Optional, Dict, List
from core.logger import get_logger

log = get_logger("intent")

# ─── Intent Categories ───────────────────────────────────────────────

INTENT_OPEN_APP = "open_app"
INTENT_CLOSE_APP = "close_app"
INTENT_SEARCH_WEB = "search_web"
INTENT_SEARCH_YOUTUBE = "search_youtube"
INTENT_SET_REMINDER = "set_reminder"
INTENT_SYSTEM_CONTROL = "system_control"
INTENT_PLAY_MEDIA = "play_media"
INTENT_GET_WEATHER = "get_weather"
INTENT_TYPE_TEXT = "type_text"
INTENT_WINDOW_CONTROL = "window_control"
INTENT_VOLUME_UP = "volume_up"
INTENT_VOLUME_DOWN = "volume_down"
INTENT_VOLUME_MUTE = "volume_mute"
INTENT_VOLUME_SET = "volume_set"
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
INTENT_SYSTEM_INFO = "system_info"
INTENT_CLIPBOARD_READ = "clipboard_read"
INTENT_PRESS_KEY = "press_key"
INTENT_TIME = "get_time"
INTENT_DATE = "get_date"
INTENT_ACTIVATE = "activate"
INTENT_DEACTIVATE = "deactivate"
INTENT_GENERAL_CONVERSATION = "general_conversation"
INTENT_UNKNOWN = "unknown"

# ─── Application name mappings ───────────────────────────────────────

APP_ALIASES = {
    # Browsers
    "chrome": "chrome", "google chrome": "chrome", "browser": "chrome",
    "firefox": "firefox", "mozilla": "firefox",
    "edge": "msedge", "microsoft edge": "msedge",
    "brave": "brave", "opera": "opera", "arc": "arc",

    # Code Editors
    "vs code": "code", "vscode": "code", "visual studio code": "code",
    "visual studio": "devenv", "sublime": "sublime_text", "atom": "atom",
    "cursor": "cursor", "android studio": "studio64",

    # Microsoft Office
    "word": "winword", "microsoft word": "winword", "ms word": "winword",
    "excel": "excel", "microsoft excel": "excel", "ms excel": "excel",
    "powerpoint": "powerpnt", "ppt": "powerpnt", "ms powerpoint": "powerpnt",
    "outlook": "outlook", "microsoft outlook": "outlook", "ms outlook": "outlook",
    "onenote": "onenote", "access": "msaccess", "ms access": "msaccess",

    # Communication & Social
    "whatsapp": "whatsapp", "whats app": "whatsapp",
    "telegram": "telegram",
    "discord": "discord",
    "teams": "teams", "microsoft teams": "teams",
    "slack": "slack",
    "zoom": "zoom", "zoom meeting": "zoom",
    "skype": "skype",
    "instagram": "instagram",
    "messenger": "messenger",

    # Media & Entertainment
    "spotify": "spotify", "music": "spotify",
    "vlc": "vlc", "media player": "vlc",
    "youtube music": "youtube_music",
    "itunes": "itunes",

    # Design & Creative
    "photoshop": "photoshop", "adobe photoshop": "photoshop",
    "premiere": "premiere", "premiere pro": "premiere",
    "after effects": "afterfx",
    "illustrator": "illustrator",
    "figma": "figma",
    "canva": "canva",
    "blender": "blender",

    # Gaming
    "steam": "steam",
    "epic games": "epicgameslauncher",
    "minecraft": "minecraft",

    # System Tools
    "notepad": "notepad", "notepad++": "notepad++",
    "calculator": "calc", "calc": "calc",
    "paint": "mspaint",
    "file explorer": "explorer", "explorer": "explorer", "files": "explorer", "my computer": "explorer",
    "this pc": "explorer",
    "downloads": "explorer_downloads", "download folder": "explorer_downloads",
    "documents": "explorer_documents", "my documents": "explorer_documents",
    "desktop": "explorer_desktop",
    "recycle bin": "explorer_recycle",
    "task manager": "taskmgr", "taskmanager": "taskmgr",
    "command prompt": "cmd", "cmd": "cmd",
    "terminal": "wt", "windows terminal": "wt",
    "powershell": "powershell",
    "snipping tool": "snippingtool", "snip": "snippingtool",
    "screen recorder": "snippingtool",
    "obs": "obs64", "obs studio": "obs64",
    "control panel": "control",
    "device manager": "devmgmt.msc",
    "disk management": "diskmgmt.msc",
    "event viewer": "eventvwr.msc",
    "registry editor": "regedit",
    "resource monitor": "resmon",
    "system information": "msinfo32",
    "character map": "charmap",

    # Windows Settings (ms-settings: URIs)
    "settings": "ms-settings:",
    "wifi": "ms-settings:network-wifi", "wi-fi": "ms-settings:network-wifi",
    "wifi settings": "ms-settings:network-wifi",
    "bluetooth": "ms-settings:bluetooth", "bluetooth settings": "ms-settings:bluetooth",
    "bluetooth devices": "ms-settings:connecteddevices",
    "network": "ms-settings:network", "internet": "ms-settings:network",
    "network settings": "ms-settings:network",
    "airplane mode": "ms-settings:network-airplanemode",
    "vpn": "ms-settings:network-vpn", "vpn settings": "ms-settings:network-vpn",
    "display": "ms-settings:display", "display settings": "ms-settings:display",
    "resolution": "ms-settings:display",
    "night light": "ms-settings:nightlight",
    "sound": "ms-settings:sound", "sound settings": "ms-settings:sound",
    "audio settings": "ms-settings:sound",
    "notifications": "ms-settings:notifications",
    "focus assist": "ms-settings:quiethours",
    "power": "ms-settings:powersleep", "power settings": "ms-settings:powersleep",
    "battery": "ms-settings:batterysaver", "battery settings": "ms-settings:batterysaver",
    "storage": "ms-settings:storagesense", "storage settings": "ms-settings:storagesense",
    "multitasking": "ms-settings:multitasking",
    "apps": "ms-settings:appsfeatures", "installed apps": "ms-settings:appsfeatures",
    "default apps": "ms-settings:defaultapps",
    "startup apps": "ms-settings:startupapps",
    "accounts": "ms-settings:accounts", "account settings": "ms-settings:accounts",
    "personalization": "ms-settings:personalization",
    "themes": "ms-settings:themes", "theme settings": "ms-settings:themes",
    "background": "ms-settings:personalization-background",
    "wallpaper": "ms-settings:personalization-background",
    "colors": "ms-settings:colors", "color settings": "ms-settings:colors",
    "lock screen": "ms-settings:lockscreen",
    "taskbar settings": "ms-settings:taskbar",
    "start menu": "ms-settings:personalization-start",
    "time": "ms-settings:dateandtime", "time settings": "ms-settings:dateandtime",
    "date and time": "ms-settings:dateandtime",
    "language": "ms-settings:regionlanguage", "language settings": "ms-settings:regionlanguage",
    "keyboard settings": "ms-settings:keyboard",
    "mouse": "ms-settings:mousetouchpad", "mouse settings": "ms-settings:mousetouchpad",
    "touchpad": "ms-settings:devices-touchpad",
    "printers": "ms-settings:printers", "printer": "ms-settings:printers",
    "camera": "ms-settings:privacy-webcam", "camera settings": "ms-settings:privacy-webcam",
    "microphone settings": "ms-settings:privacy-microphone",
    "privacy": "ms-settings:privacy", "privacy settings": "ms-settings:privacy",
    "security": "ms-settings:windowsdefender",
    "windows security": "ms-settings:windowsdefender",
    "windows update": "ms-settings:windowsupdate", "update": "ms-settings:windowsupdate",
    "check for updates": "ms-settings:windowsupdate",
    "about": "ms-settings:about", "about pc": "ms-settings:about",
    "gaming settings": "ms-settings:gaming-gamebar",
    "game bar": "ms-settings:gaming-gamebar",
    "accessibility": "ms-settings:easeofaccess",
    "ease of access": "ms-settings:easeofaccess",

    # Tanglish aliases
    "chrome open pannu": "chrome",
    "browser open pannu": "chrome",
    "file manager": "explorer",
}

# ─── Intent Patterns with Confidence Weights ─────────────────────────

PATTERNS: Dict[str, List[Tuple[str, float]]] = {
    # Activation / Deactivation
    INTENT_ACTIVATE: [
        (r"^(?:hey\s+)?jarvis$", 0.95),
        (r"^wake\s+up", 0.90),
        (r"^activate", 0.85),
        (r"^turn\s+on\s+(?:jarvis|assistant)", 0.90),
    ],
    INTENT_DEACTIVATE: [
        (r"^(?:turn\s+off|go\s+to\s+sleep|jarvis\s+stop|stop\s+listening|deactivate|good\s*night)", 0.95),
        (r"^(?:shut\s+up|be\s+quiet|silence)", 0.80),
    ],

    # App Control
    INTENT_OPEN_APP: [
        (r"open\s+(.+)", 0.85),
        (r"launch\s+(.+)", 0.85),
        (r"start\s+(.+)", 0.80),
        (r"run\s+(.+)", 0.75),
    ],
    INTENT_CLOSE_APP: [
        (r"close\s+(?:this\s+)?(?:window|app)?(.+)?", 0.85),
        (r"quit\s+(.+)", 0.85),
        (r"exit\s+(.+)", 0.80),
        (r"kill\s+(.+)", 0.80),
        (r"terminate\s+(.+)", 0.80),
    ],

    # Web & Search
    INTENT_SEARCH_WEB: [
        (r"search\s+(?:google\s+)?(?:for\s+)?(.+)", 0.85),
        (r"google\s+(.+)", 0.85),
        (r"look\s+up\s+(.+)", 0.80),
    ],
    INTENT_SEARCH_YOUTUBE: [
        (r"(?:search\s+)?youtube\s+(?:for\s+)?(.+)", 0.90),
        (r"play\s+(?:on\s+)?youtube\s+(.+)", 0.90),
        (r"find\s+(?:on\s+)?youtube\s+(.+)", 0.85),
        (r"play\s+(.+)\s+on\s+youtube", 0.90),
    ],

    # Volume
    INTENT_VOLUME_UP: [
        (r"(?:increase|raise|up|turn\s+up)\s+(?:the\s+)?volume", 0.90),
        (r"volume\s+up", 0.90),
        (r"louder", 0.85),
    ],
    INTENT_VOLUME_DOWN: [
        (r"(?:decrease|lower|down|turn\s+down)\s+(?:the\s+)?volume", 0.90),
        (r"volume\s+down", 0.90),
        (r"quieter", 0.85),
    ],
    INTENT_VOLUME_MUTE: [
        (r"mute\s+(?:the\s+)?(?:volume|sound|audio)", 0.90),
        (r"unmute", 0.90),
        (r"toggle\s+mute", 0.85),
    ],
    INTENT_VOLUME_SET: [
        (r"set\s+(?:the\s+)?volume\s+(?:to\s+)?(\d+)\s*%?", 0.95),
        (r"volume\s+(?:to\s+)?(\d+)\s*%?", 0.85),
    ],

    # Brightness
    INTENT_BRIGHTNESS_UP: [
        (r"(?:increase|raise|up)\s+(?:the\s+)?brightness", 0.90),
        (r"brighter", 0.85),
    ],
    INTENT_BRIGHTNESS_DOWN: [
        (r"(?:decrease|lower|down)\s+(?:the\s+)?brightness", 0.90),
        (r"dimmer", 0.85),
    ],

    # Screenshot
    INTENT_SCREENSHOT: [
        (r"(?:take\s+(?:a\s+)?)?screenshot", 0.90),
        (r"capture\s+(?:the\s+)?screen", 0.90),
        (r"screen\s*(?:shot|cap)", 0.85),
    ],

    # System Control
    INTENT_SHUTDOWN: [
        (r"shutdown\s*(?:the\s+)?(?:pc|computer)?", 0.90),
        (r"shut\s+down", 0.90),
        (r"power\s+off", 0.90),
        (r"turn\s+off\s+(?:the\s+)?(?:pc|computer)", 0.90),
    ],
    INTENT_RESTART: [
        (r"restart\s*(?:the\s+)?(?:pc|computer|system)?", 0.90),
        (r"reboot", 0.90),
    ],
    INTENT_LOCK: [
        (r"lock\s+(?:the\s+)?(?:pc|computer|screen)", 0.90),
        (r"lock\s+screen", 0.90),
    ],
    INTENT_SLEEP: [
        (r"(?:put\s+(?:the\s+)?(?:pc|computer)\s+to\s+)?sleep", 0.80),
        (r"sleep\s+(?:the\s+)?(?:pc|computer|mode)", 0.85),
    ],

    # Media Controls
    INTENT_MEDIA_PLAY: [
        (r"(?:play|resume)\s+(?:music|media|song|playback)", 0.90),
        (r"^play$", 0.75),
    ],
    INTENT_MEDIA_PAUSE: [
        (r"(?:pause|stop)\s+(?:music|media|song|playback)", 0.90),
        (r"^pause$", 0.80),
    ],
    INTENT_MEDIA_NEXT: [
        (r"(?:next|skip)\s+(?:song|track)", 0.90),
        (r"^next$", 0.75),
        (r"^skip$", 0.75),
    ],
    INTENT_MEDIA_PREV: [
        (r"(?:previous|back|last)\s+(?:song|track)", 0.90),
        (r"^previous$", 0.80),
    ],

    # System Info
    INTENT_SYSTEM_INFO: [
        (r"(?:system|pc|computer)\s+(?:info|information|status|stats)", 0.90),
        (r"(?:how\s+(?:is\s+)?(?:the\s+)?)?(?:cpu|ram|memory|disk|battery)\s*(?:usage|status)?", 0.85),
        (r"(?:what(?:'s|\s+is)\s+(?:the\s+)?)?(?:cpu|ram|memory|disk|battery)", 0.85),
    ],

    # Time & Date
    INTENT_TIME: [
        (r"what\s*(?:'s|\s+is)\s+(?:the\s+)?time", 0.95),
        (r"tell\s+(?:me\s+)?(?:the\s+)?time", 0.90),
        (r"what\s+time\s+is\s+it", 0.95),
        (r"current\s+time", 0.90),
    ],
    INTENT_DATE: [
        (r"what\s*(?:'s|\s+is)\s+(?:the\s+)?(?:date|day)", 0.95),
        (r"what\s+day\s+is\s+it", 0.95),
        (r"today(?:'s)?\s+date", 0.90),
    ],

    # Typing & Keyboard
    INTENT_TYPE_TEXT: [
        (r"type\s+(.+)", 0.90),
        (r"write\s+(.+)", 0.80),
    ],
    INTENT_PRESS_KEY: [
        (r"press\s+(.+)", 0.90),
        (r"hit\s+(.+)", 0.80),
    ],
    INTENT_CLIPBOARD_READ: [
        (r"read\s+(?:the\s+)?clipboard", 0.90),
        (r"what(?:'s|\s+is)\s+(?:in\s+)?(?:the\s+)?clipboard", 0.90),
        (r"paste\s+(?:the\s+)?clipboard", 0.80),
    ],

    # Window Management
    INTENT_WINDOW_CONTROL: [
        (r"(?:maximize|max)\s+(?:the\s+)?window", 0.90),
        (r"(?:minimize|min)\s+(?:the\s+)?window", 0.90),
        (r"minimize\s+everything", 0.90),
        (r"show\s+desktop", 0.90),
        (r"snap\s+(?:to\s+)?(?:the\s+)?(?:left|right)", 0.90),
        (r"move\s+(?:to\s+)?(?:second|other)\s+monitor", 0.85),
        (r"switch\s+(?:to\s+)?(.+)", 0.80),
        (r"alt\s+tab", 0.85),
    ],

    # Reminders
    INTENT_SET_REMINDER: [
        (r"remind\s+me\s+(?:in\s+)?(\d+)\s*(?:minutes?|mins?|hours?|hrs?|seconds?|secs?)\s+(?:to\s+)?(.+)", 0.95),
        (r"set\s+(?:a\s+)?reminder\s+(.+)", 0.90),
        (r"(?:what\s+are\s+)?(?:my\s+)?reminders", 0.85),
        (r"cancel\s+(?:all\s+)?reminders?", 0.90),
    ],

    # Weather
    INTENT_GET_WEATHER: [
        (r"(?:what(?:'s|\s+is)\s+)?(?:the\s+)?weather", 0.90),
        (r"(?:how(?:'s|\s+is)\s+)?(?:the\s+)?weather", 0.90),
        (r"temperature\s+(?:outside|today)?", 0.85),
        (r"(?:is\s+it\s+)?(?:raining|sunny|cloudy|cold|hot)", 0.75),
    ],
}

# Confidence threshold — reject below this
CONFIDENCE_THRESHOLD = 0.4


class IntentClassifier:
    """Classifies user input into actionable intents with confidence scoring."""

    def classify(self, text: str) -> Tuple[str, Optional[str], float]:
        """
        Classify text into intent and extract parameters.
        Returns (intent, parameter, confidence) tuple.
        """
        if not text:
            log.info("Intent: unknown (empty input), confidence: 0.0")
            return INTENT_UNKNOWN, None, 0.0

        text_lower = text.lower().strip()

        # Remove wake word prefix
        for prefix in ["jarvis", "hey jarvis", "ok jarvis", "j.a.r.v.i.s"]:
            if text_lower.startswith(prefix):
                text_lower = text_lower[len(prefix):].strip()
                text_lower = text_lower.lstrip(",.!? ")
                break

        if not text_lower:
            log.info("Intent: activate (wake word only), confidence: 0.95")
            return INTENT_ACTIVATE, None, 0.95

        # Check YouTube search first (before generic search captures it)
        best_intent = None
        best_param = None
        best_confidence = 0.0

        for intent, patterns in PATTERNS.items():
            for pattern, weight in patterns:
                try:
                    match = re.search(pattern, text_lower)
                    if match:
                        # Calculate confidence
                        confidence = weight

                        # Boost for exact/full match
                        if match.group(0) == text_lower:
                            confidence = min(1.0, confidence + 0.05)

                        if confidence > best_confidence:
                            best_confidence = confidence
                            best_intent = intent

                            # Extract parameter
                            if match.lastindex and match.lastindex >= 1:
                                param = match.group(1).strip()
                                # Resolve app names for open/close intents
                                if intent in (INTENT_OPEN_APP, INTENT_CLOSE_APP) and param:
                                    param = self._resolve_app(param)
                                best_param = param
                            else:
                                best_param = None
                except re.error:
                    continue

        # Apply confidence threshold
        if best_intent and best_confidence >= CONFIDENCE_THRESHOLD:
            log.info(
                f"Intent: {best_intent}, param: {best_param}, "
                f"confidence: {best_confidence:.2f}, input: '{text_lower}'"
            )
            return best_intent, best_param, best_confidence

        # Default fallback: general_conversation
        log.info(
            f"Intent: general_conversation (no pattern matched above threshold), "
            f"best was: {best_intent} @ {best_confidence:.2f}, input: '{text_lower}'"
        )
        return INTENT_GENERAL_CONVERSATION, text_lower, 0.5

    def _resolve_app(self, app_name: str) -> str:
        """Resolve app alias to executable name."""
        app_lower = app_name.lower().strip()
        return APP_ALIASES.get(app_lower, app_lower)

    def get_all_intents(self) -> list:
        """Return list of all supported intent names."""
        return list(PATTERNS.keys()) + [INTENT_GENERAL_CONVERSATION, INTENT_UNKNOWN]
