"""
J.A.R.V.I.S. Phase 1 - Minimal Working Voice Assistant
=======================================================
Architecture:
    MICROPHONE -> Wake Word -> STT -> Command Router -> LLM Brain -> Action Executor -> TTS -> SPEAKER

This is the REAL minimum JARVIS. Nothing else until this works perfectly.

Author: Hari
"""

import sys
import io
# Fix Windows console encoding for special characters
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import os
import time
import json
import subprocess
import webbrowser
import datetime
import threading
import re

import pyttsx3
import speech_recognition as sr
import psutil
import pyautogui

# Optional: OpenAI for smart responses
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
except ImportError:
    pass


# =====================================================================
# CONFIGURATION
# =====================================================================

WAKE_WORD = "jarvis"
USER_NAME = os.getenv("USER_NAME", "Hari")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LISTENING_TIMEOUT = 5        # seconds to wait for command after wake word
PHRASE_TIME_LIMIT = 10       # max seconds for a single phrase
ENERGY_THRESHOLD = 300       # microphone sensitivity (lower = more sensitive)


# =====================================================================
# TEXT-TO-SPEECH ENGINE
# =====================================================================

class Speaker:
    """Handles all text-to-speech output."""

    def __init__(self):
        self.engine = pyttsx3.init()
        # Configure voice
        voices = self.engine.getProperty('voices')
        # Try to find a male English voice (JARVIS-like)
        for voice in voices:
            if 'david' in voice.name.lower() or 'male' in voice.name.lower():
                self.engine.setProperty('voice', voice.id)
                break
        self.engine.setProperty('rate', 175)    # Speaking speed
        self.engine.setProperty('volume', 1.0)  # Volume
        self._lock = threading.Lock()

    def say(self, text: str):
        """Speak the given text."""
        print(f"\n[JARVIS] {text}")
        with self._lock:
            self.engine.say(text)
            self.engine.runAndWait()


# =====================================================================
# SPEECH-TO-TEXT ENGINE
# =====================================================================

class Listener:
    """Handles microphone input and speech recognition."""

    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = ENERGY_THRESHOLD
        self.recognizer.dynamic_energy_threshold = True
        self.microphone = None
        self._init_microphone()

    def _init_microphone(self):
        """Initialize the microphone with error handling."""
        try:
            self.microphone = sr.Microphone()
            # Calibrate for ambient noise
            with self.microphone as source:
                print("[MIC] Calibrating microphone for ambient noise...")
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
            print(f"[MIC] Microphone ready (energy threshold: {self.recognizer.energy_threshold:.0f})")
        except Exception as e:
            print(f"[ERROR] Microphone error: {e}")
            print("   Make sure a microphone is connected and permissions are granted.")
            sys.exit(1)

    def listen_for_wake_word(self) -> bool:
        """Continuously listen for the wake word 'Jarvis'."""
        try:
            with self.microphone as source:
                audio = self.recognizer.listen(source, timeout=None, phrase_time_limit=3)

            text = self._recognize(audio)
            if text and WAKE_WORD in text.lower():
                print(f"\n[WAKE] Wake word detected: '{text}'")
                return True
        except sr.WaitTimeoutError:
            pass
        except Exception as e:
            if "connection" not in str(e).lower():
                print(f"[WARN] Listen error: {e}")
        return False

    def listen_for_command(self) -> str | None:
        """Listen for a command after wake word is detected."""
        try:
            with self.microphone as source:
                print("[LISTEN] Listening for command...")
                audio = self.recognizer.listen(
                    source,
                    timeout=LISTENING_TIMEOUT,
                    phrase_time_limit=PHRASE_TIME_LIMIT
                )

            text = self._recognize(audio)
            if text:
                print(f"[HEARD] '{text}'")
                return text
        except sr.WaitTimeoutError:
            print("[TIMEOUT] No command heard")
        except Exception as e:
            print(f"[WARN] Command listen error: {e}")
        return None

    def _recognize(self, audio) -> str | None:
        """Convert audio to text using Google Speech Recognition (free)."""
        try:
            text = self.recognizer.recognize_google(audio)
            return text
        except sr.UnknownValueError:
            return None
        except sr.RequestError as e:
            print(f"[WARN] Speech recognition service error: {e}")
            return None


# =====================================================================
# COMMAND ROUTER - Maps voice commands to actions
# =====================================================================

class CommandRouter:
    """Routes recognized speech to appropriate actions."""

    def __init__(self, speaker: Speaker):
        self.speaker = speaker
        self.openai_client = None
        if HAS_OPENAI and OPENAI_API_KEY:
            self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
            print("[BRAIN] OpenAI connected - smart responses enabled")
        else:
            print("[BRAIN] Running in offline mode (no OpenAI key)")

    def process(self, command: str) -> bool:
        """
        Process a voice command. Returns True to continue, False to exit.
        """
        cmd = command.lower().strip()

        # -- Exit commands --
        if any(phrase in cmd for phrase in ["shutdown", "shut down", "goodbye", "go to sleep", "exit", "quit"]):
            self.speaker.say(f"Goodbye {USER_NAME}. Shutting down.")
            return False

        # -- Chrome profiles listing --
        if any(phrase in cmd for phrase in ["list profiles", "show profiles", "chrome profiles", "which profiles", "available profiles"]):
            profiles = self._detect_chrome_profiles()
            if profiles:
                names = [p["name"] for p in profiles]
                self.speaker.say(f"You have {len(names)} Chrome profiles: {', '.join(names[:8])}. Say open chrome with any profile name.")
            else:
                self.speaker.say("I couldn't find any Chrome profiles.")
            return True

        # -- App launching --
        if "open" in cmd:
            return self._handle_open(cmd)

        # -- System info --
        if any(phrase in cmd for phrase in ["time", "what time"]):
            return self._tell_time()

        if any(phrase in cmd for phrase in ["date", "what date", "today"]):
            return self._tell_date()

        if any(phrase in cmd for phrase in ["battery", "power", "charge"]):
            return self._tell_battery()

        if any(phrase in cmd for phrase in ["cpu", "processor", "usage"]):
            return self._tell_cpu()

        if any(phrase in cmd for phrase in ["memory", "ram"]):
            return self._tell_memory()

        # -- Web search --
        if any(phrase in cmd for phrase in ["search for", "google", "look up", "search"]):
            return self._handle_search(cmd)

        # -- YouTube --
        if "youtube" in cmd:
            return self._handle_youtube(cmd)

        # -- Screenshot --
        if any(phrase in cmd for phrase in ["screenshot", "screen shot", "capture screen"]):
            return self._take_screenshot()

        # -- Volume control --
        if "volume" in cmd or "mute" in cmd:
            return self._handle_volume(cmd)

        # -- Notepad / typing --
        if any(phrase in cmd for phrase in ["type", "write", "note"]):
            return self._handle_type(cmd)

        # -- System commands --
        if any(phrase in cmd for phrase in ["lock", "lock screen", "lock computer"]):
            self.speaker.say("Locking the computer.")
            os.system("rundll32.exe user32.dll,LockWorkStation")
            return True

        if "restart" in cmd and "computer" in cmd:
            self.speaker.say("Restarting the computer in 10 seconds. Say cancel to abort.")
            os.system("shutdown /r /t 10")
            return True

        # -- Fall through to AI --
        return self._ask_ai(command)

    # -- Action Handlers --

    def _handle_open(self, cmd: str) -> bool:
        """Open applications or websites."""

        # ── Chrome with profile detection ──
        profile_match = re.search(
            r"open\s+(?:google\s+)?chrome\s+(?:and\s+)?(?:select|use|with|click|load|switch\s+to|go\s+to|choose|pick)\s+(.+?)(?:\s+account|\s+profile)?$",
            cmd,
        )
        if not profile_match:
            profile_match = re.search(
                r"open\s+(?:google\s+)?chrome\s+(.+?)\s+(?:profile|account)$",
                cmd,
            )
        if not profile_match:
            profile_match = re.search(
                r"open\s+(?:google\s+)?chrome\s+(?:in|on|for)\s+(.+?)(?:\s+account|\s+profile)?$",
                cmd,
            )
        if not profile_match:
            # "open chrome [name]" — check if name is a known profile
            simple_match = re.search(r"open\s+(?:google\s+)?chrome\s+(.+)$", cmd)
            if simple_match:
                candidate = simple_match.group(1).strip()
                candidate = re.sub(r"\s+(?:please|for me|for|now)$", "", candidate)
                # Check against detected profiles
                detected = self._detect_chrome_profiles()
                for p in detected:
                    if candidate.lower() in p["name"].lower() or p["name"].lower().startswith(candidate.lower()):
                        profile_match = simple_match
                        break

        if profile_match:
            profile_name = profile_match.group(1).strip()
            profile_name = re.sub(r"\s+(?:please|for me|bro|sir|da|di|now)$", "", profile_name)
            return self._open_chrome_profile(profile_name)

        app_map = {
            "chrome": "chrome",
            "browser": "chrome",
            "google chrome": "chrome",
            "firefox": "firefox",
            "edge": "msedge",
            "notepad": "notepad",
            "calculator": "calc",
            "calc": "calc",
            "paint": "mspaint",
            "word": "winword",
            "excel": "excel",
            "powerpoint": "powerpnt",
            "task manager": "taskmgr",
            "file explorer": "explorer",
            "explorer": "explorer",
            "files": "explorer",
            "terminal": "wt",
            "command prompt": "cmd",
            "cmd": "cmd",
            "powershell": "powershell",
            "settings": "ms-settings:",
            "spotify": "spotify",
            "discord": "discord",
            "vscode": "code",
            "vs code": "code",
            "visual studio code": "code",
            "code": "code",
        }

        # Website shortcuts
        web_map = {
            "youtube": "https://www.youtube.com",
            "google": "https://www.google.com",
            "github": "https://github.com",
            "gmail": "https://mail.google.com",
            "whatsapp": "https://web.whatsapp.com",
            "instagram": "https://www.instagram.com",
            "twitter": "https://twitter.com",
            "reddit": "https://www.reddit.com",
            "chatgpt": "https://chat.openai.com",
            "netflix": "https://www.netflix.com",
        }

        # Check websites first
        for name, url in web_map.items():
            if name in cmd:
                self.speaker.say(f"Opening {name}.")
                webbrowser.open(url)
                return True

        # Check applications
        for name, exe in app_map.items():
            if name in cmd:
                self.speaker.say(f"Opening {name}.")
                try:
                    if exe.startswith("ms-"):
                        os.system(f"start {exe}")
                    else:
                        subprocess.Popen(exe, shell=True)
                except Exception as e:
                    self.speaker.say(f"Sorry, I couldn't open {name}. {e}")
                return True

        # Generic: try to open whatever was said after "open"
        target = cmd.split("open", 1)[-1].strip()
        if target:
            self.speaker.say(f"Trying to open {target}.")
            try:
                os.system(f"start {target}")
            except Exception:
                self.speaker.say(f"Sorry, I couldn't open {target}.")
        else:
            self.speaker.say("What would you like me to open?")
        return True

    def _detect_chrome_profiles(self) -> list:
        """Detect Chrome profiles from Local State file."""
        profiles = []
        try:
            local_state = os.path.expandvars(
                r"%LOCALAPPDATA%\Google\Chrome\User Data\Local State"
            )
            if not os.path.exists(local_state):
                return profiles
            with open(local_state, "r", encoding="utf-8") as f:
                state = json.load(f)
            info_cache = state.get("profile", {}).get("info_cache", {})
            for dir_name, data in info_cache.items():
                name = data.get("gaia_name", "") or data.get("name", dir_name)
                profiles.append({"name": name, "dir": dir_name})
        except Exception as e:
            print(f"[WARN] Chrome profile detection failed: {e}")
        return profiles

    def _open_chrome_profile(self, target_name: str) -> bool:
        """Open Chrome with a specific profile."""
        profiles = self._detect_chrome_profiles()

        # Find matching profile
        matched = None
        target_lower = target_name.lower().strip()

        # Exact match
        for p in profiles:
            if p["name"].lower() == target_lower:
                matched = p
                break

        # Partial match
        if not matched:
            for p in profiles:
                if target_lower in p["name"].lower() or p["name"].lower().startswith(target_lower):
                    matched = p
                    break

        # Word-level match
        if not matched:
            target_words = set(target_lower.split())
            for p in profiles:
                name_words = set(p["name"].lower().split())
                if target_words & name_words:
                    matched = p
                    break

        if not matched:
            available = [p["name"] for p in profiles]
            self.speaker.say(
                f"Profile {target_name} not found. Available profiles are: "
                + ", ".join(available[:5])
            )
            return True

        # Find Chrome executable
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ]
        chrome_exe = None
        for p in chrome_paths:
            if os.path.exists(p):
                chrome_exe = p
                break

        try:
            if chrome_exe:
                cmd = f'"{chrome_exe}" --profile-directory="{matched["dir"]}"'
            else:
                cmd = f'chrome --profile-directory="{matched["dir"]}"'
            subprocess.Popen(cmd, shell=True)
            self.speaker.say(f"Opening Chrome with {matched['name']} profile.")
        except Exception as e:
            self.speaker.say(f"Failed to open Chrome profile: {e}")
        return True

    def _handle_search(self, cmd: str) -> bool:
        """Search the web."""
        # Extract search query
        for prefix in ["search for", "search", "google", "look up"]:
            if prefix in cmd:
                query = cmd.split(prefix, 1)[-1].strip()
                break
        else:
            query = cmd

        if query:
            self.speaker.say(f"Searching for {query}.")
            webbrowser.open(f"https://www.google.com/search?q={query}")
        else:
            self.speaker.say("What should I search for?")
        return True

    def _handle_youtube(self, cmd: str) -> bool:
        """Search or open YouTube."""
        for prefix in ["search youtube for", "youtube search", "play on youtube", "search on youtube", "youtube"]:
            if prefix in cmd:
                query = cmd.split(prefix, 1)[-1].strip()
                break
        else:
            query = ""

        if query:
            self.speaker.say(f"Searching YouTube for {query}.")
            webbrowser.open(f"https://www.youtube.com/results?search_query={query}")
        else:
            self.speaker.say("Opening YouTube.")
            webbrowser.open("https://www.youtube.com")
        return True

    def _tell_time(self) -> bool:
        now = datetime.datetime.now()
        time_str = now.strftime("%I:%M %p")
        self.speaker.say(f"It's {time_str}.")
        return True

    def _tell_date(self) -> bool:
        now = datetime.datetime.now()
        date_str = now.strftime("%A, %B %d, %Y")
        self.speaker.say(f"Today is {date_str}.")
        return True

    def _tell_battery(self) -> bool:
        battery = psutil.sensors_battery()
        if battery:
            percent = battery.percent
            plugged = "plugged in" if battery.power_plugged else "on battery"
            self.speaker.say(f"Battery is at {percent}%, {plugged}.")
        else:
            self.speaker.say("I couldn't read the battery status.")
        return True

    def _tell_cpu(self) -> bool:
        cpu = psutil.cpu_percent(interval=1)
        self.speaker.say(f"CPU usage is at {cpu}%.")
        return True

    def _tell_memory(self) -> bool:
        mem = psutil.virtual_memory()
        used_gb = mem.used / (1024 ** 3)
        total_gb = mem.total / (1024 ** 3)
        self.speaker.say(f"Memory usage: {used_gb:.1f} GB used out of {total_gb:.1f} GB total. That's {mem.percent}%.")
        return True

    def _take_screenshot(self) -> bool:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshots_dir = os.path.join(os.path.dirname(__file__), '..', 'screenshots')
        os.makedirs(screenshots_dir, exist_ok=True)
        filepath = os.path.join(screenshots_dir, f"screenshot_{timestamp}.png")
        pyautogui.screenshot(filepath)
        self.speaker.say(f"Screenshot saved.")
        return True

    def _handle_volume(self, cmd: str) -> bool:
        """Control system volume."""
        if "mute" in cmd:
            pyautogui.press('volumemute')
            self.speaker.say("Volume muted.")
        elif "up" in cmd or "increase" in cmd:
            for _ in range(5):
                pyautogui.press('volumeup')
            self.speaker.say("Volume increased.")
        elif "down" in cmd or "decrease" in cmd:
            for _ in range(5):
                pyautogui.press('volumedown')
            self.speaker.say("Volume decreased.")
        elif "max" in cmd or "full" in cmd:
            for _ in range(50):
                pyautogui.press('volumeup')
            self.speaker.say("Volume set to maximum.")
        return True

    def _handle_type(self, cmd: str) -> bool:
        """Type text (useful for quick notes)."""
        for prefix in ["type", "write", "note"]:
            if prefix in cmd:
                text = cmd.split(prefix, 1)[-1].strip()
                break
        else:
            text = cmd

        if text:
            self.speaker.say("Typing now.")
            time.sleep(0.5)
            pyautogui.typewrite(text, interval=0.03)
        else:
            self.speaker.say("What should I type?")
        return True

    def _ask_ai(self, command: str) -> bool:
        """Fall through to AI for general questions."""
        if self.openai_client:
            try:
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                f"You are JARVIS, a highly intelligent AI assistant for {USER_NAME}. "
                                "You are concise, witty, and helpful - like the AI from Iron Man. "
                                "Keep responses SHORT (1-3 sentences max). "
                                "You are running on a Windows PC as a voice assistant."
                            )
                        },
                        {"role": "user", "content": command}
                    ],
                    max_tokens=150,
                    temperature=0.7
                )
                answer = response.choices[0].message.content
                self.speaker.say(answer)
            except Exception as e:
                self.speaker.say(f"I had trouble thinking about that. Error: {e}")
        else:
            self.speaker.say(
                f"I'm not sure how to handle that, {USER_NAME}. "
                "I can open apps, search the web, tell you system info, and more. "
                "Try saying open chrome or what time is it."
            )
        return True


# =====================================================================
# MAIN JARVIS LOOP
# =====================================================================

class Jarvis:
    """The main JARVIS orchestrator."""

    def __init__(self):
        print("=" * 60)
        print("  J.A.R.V.I.S. - Phase 1: Core Voice Assistant")
        print("=" * 60)
        print()

        self.speaker = Speaker()
        self.listener = Listener()
        self.router = CommandRouter(self.speaker)
        self.running = True

    def start(self):
        """Start the JARVIS main loop."""
        hour = datetime.datetime.now().hour
        if hour < 12:
            greeting = "morning"
        elif hour < 17:
            greeting = "afternoon"
        else:
            greeting = "evening"

        self.speaker.say(
            f"JARVIS online. Good {greeting}, {USER_NAME}. How can I help you?"
        )

        print(f"\n[INFO] Say '{WAKE_WORD}' to activate, then speak your command.")
        print("[INFO] Or say 'Jarvis shutdown' to exit.\n")

        while self.running:
            try:
                # Step 1: Listen for wake word
                if self.listener.listen_for_wake_word():
                    # Step 2: Acknowledge
                    self.speaker.say(f"Yes, {USER_NAME}?")

                    # Step 3: Listen for command
                    command = self.listener.listen_for_command()

                    if command:
                        # Step 4: Route and execute command
                        self.running = self.router.process(command)
                    else:
                        self.speaker.say("I didn't catch that. Try again.")

            except KeyboardInterrupt:
                print("\n\n[STOP] Keyboard interrupt received.")
                self.speaker.say(f"Goodbye, {USER_NAME}.")
                self.running = False

        print("\n[OFFLINE] JARVIS offline.")


# =====================================================================
# ENTRY POINT
# =====================================================================

if __name__ == "__main__":
    jarvis = Jarvis()
    jarvis.start()
