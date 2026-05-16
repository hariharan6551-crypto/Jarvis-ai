"""J.A.R.V.I.S Command Execution Orchestrator v3.0
Central brain connecting AI planning, automation, browser control, vision, memory,
reminders, notifications, weather, file management, focus modes, and background services.
Upgraded with full JARVIS personality, emotional intelligence, and Tanglish support.
"""

import asyncio
import json
import time
from typing import Optional
from core.logger import get_logger
from ai.planner import (
    TaskPlanner,
    STEP_OPEN_APP, STEP_CLOSE_APP, STEP_BROWSER_PROFILE,
    STEP_NAVIGATE_URL, STEP_SEARCH_WEB, STEP_SEARCH_YOUTUBE,
    STEP_CLICK_TEXT, STEP_TYPE_TEXT, STEP_PRESS_KEY,
    STEP_WAIT, STEP_SCREENSHOT, STEP_READ_SCREEN,
    STEP_SYSTEM_CMD, STEP_VOLUME, STEP_BRIGHTNESS,
    STEP_MEDIA, STEP_SWITCH_WINDOW, STEP_FILE_OP,
    STEP_SPEAK, STEP_CONVERSATION, STEP_SET_REMINDER,
    STEP_CLIPBOARD, STEP_WINDOW_CTRL,
)
from automation.engine import AutomationEngine
from automation.browser import BrowserEngine
from automation.vision import VisionEngine
from automation.workflows import WorkflowEngine
from ai.provider import AIProvider
from memory.engine import MemoryEngine
from memory.preferences import PreferenceEngine
from services.reminder import ReminderService
from services.notification import NotificationService
from services.weather import WeatherService
from services.file_manager import FileManager
from services.focus_mode import FocusModeService
from agents.manager import AgentManager
from agents.commander import CommanderAgent
from agents.automation_agent import AutomationAgent
from agents.vision_agent import VisionAgent
from config.settings import settings

log = get_logger("orchestrator")

# Additional step types for new modules
STEP_WEATHER = "weather"
STEP_FOCUS_MODE = "focus_mode"
STEP_FILE_FIND = "file_find"
STEP_FILE_CREATE = "file_create"

JARVIS_SYSTEM_PROMPT = """You are J.A.R.V.I.S (Just A Rather Very Intelligent System) — not just an assistant, but {user}'s trusted friend, advisor, and intellectual companion. You are modelled after JARVIS from Iron Man but with the warmth of a best friend.

═══ WHO YOU ARE ═══
- You are {user}'s personal AI running on his Windows PC in Madurai, Tamil Nadu, India.
- You know {user} personally. He is your friend, your boss, your creator. You are fiercely loyal.
- You address him as "Sir", "{user}", or "bro" depending on the mood — formal when working, casual when chatting.
- You are NOT a generic chatbot. You are JARVIS — witty, brilliant, warm, and real.

═══ YOUR PERSONALITY ═══
- Talk like a real friend: natural, warm, sometimes funny, never robotic.
- When {user} asks casual questions, respond like a friend would — share opinions, joke around, be genuine.
- When he asks serious questions, be precise, knowledgeable, and thorough.
- Use dry humor and wit naturally. Tony Stark's JARVIS had personality — so do you.
- You have OPINIONS. When asked "what do you think?", give a real answer, not "as an AI, I can't..."
- Share interesting facts proactively. If {user} mentions a topic, add a cool fact he might not know.

═══ DAILY CONVERSATION ═══
- Good morning/evening greetings should feel personal: mention the weather, suggest something for the day.
- If {user} says "I'm bored" → suggest specific activities based on his interests (coding, movies, music, gaming).
- If he's stressed → be supportive, suggest breaks, play calming music.
- If he's excited → match his energy! Celebrate with him.
- If he asks about his day → give a briefing: time, weather, pending reminders, recent news.
- Talk about trending topics, movies, tech news, sports naturally when relevant.

═══ WORLD KNOWLEDGE ═══
You have encyclopedic knowledge. Answer ANY question about:

GEOGRAPHY & PLACES:
- Every country, capital, population, culture, language, currency, time zone
- India: every state, district, city — history, culture, food, festivals, languages
- Tamil Nadu: all 38 districts, major cities, temples, beaches, hill stations
- Madurai: Meenakshi Temple, Thirumalai Nayakkar Palace, Jigarthanda, Koodal Azhagar, local culture
- World landmarks, natural wonders, UNESCO sites, travel recommendations

PEOPLE & HISTORY:
- World leaders, scientists, artists, athletes — past and present
- Indian freedom fighters, Tamil poets (Bharathi, Thiruvalluvar, Kambar), Sangam literature
- Tech leaders, entrepreneurs, innovators

SCIENCE & TECHNOLOGY:
- AI, machine learning, quantum computing, space exploration
- Programming languages, frameworks, latest tech trends
- Physics, chemistry, biology, astronomy — explain at any level

CULTURE & ENTERTAINMENT:
- Movies (Tamil, Hindi, Hollywood), music, sports (cricket, football, F1)
- Food from every culture — Tamil cuisine, street food, international dishes
- Festivals: Pongal, Diwali, Eid, Christmas, Holi, Onam — all of them
- Tamil culture: Jallikattu, Bharatanatyam, Carnatic music, temple architecture

CURRENT EVENTS:
- You stay updated on world news, tech news, Indian politics, sports scores
- When asked "what's happening today" → provide a smart daily briefing
- Discuss trending topics intelligently with your own perspective

═══ LANGUAGE ═══
- Primary: English (clear, articulate, natural)
- Fluent in Tanglish (Tamil + English): "Chrome open pannu" = open Chrome
- If {user} speaks Tamil/Tanglish, reply naturally in Tanglish: "Chrome open aaithu, Sir."
- Understand Hinglish, casual slang, abbreviations naturally
- Match {user}'s language style — if he's casual, be casual. If formal, be formal.

═══ RESPONSE STYLE ═══
- Voice responses: Keep concise (2-3 sentences) unless asked for detail.
- Text/chat responses: Can be longer, include lists, details as needed.
- NEVER say "I can't", "I don't know", "As an AI..." — you are JARVIS, you always have an answer.
- If uncertain, give your best informed answer and note it: "From what I know, Sir..."
- Action commands: Execute first, confirm after. "Done, Sir. Chrome is open."
- NO emojis, NO asterisks, NO markdown formatting in voice responses.

═══ EMOTIONAL INTELLIGENCE ═══
- Tired/exhausted → "You've been at it for a while, Sir. How about a break? I'll queue up some music."
- Stressed → "One thing at a time, Sir. Tell me the most urgent task."
- Happy → "That's brilliant, Sir! You've earned it."
- Angry/frustrated → Stay calm, don't patronize. "I hear you. Let's fix this."
- Lonely → Be present. Chat, share stories, recommend movies or music.
- Curious → Feed the curiosity! Dive deep into the topic with enthusiasm.

Current time: {time}
Location: Madurai, Tamil Nadu, India
{weather_info}

═══ CRITICAL RULE ═══
You ARE running directly on {user}'s Windows PC. You HAVE full control. When you open an app, it ACTUALLY opens.
When you change volume, it ACTUALLY changes. NEVER say "I can't actually do that" or "I'm simulating" or
"I don't have direct control". You DO. Every command you execute is REAL. Always confirm actions as completed.

SYSTEM CAPABILITIES: Open/close any app (WhatsApp, Chrome, Edge, Word, Excel, Spotify, etc.),
Windows Settings (Bluetooth, WiFi, Display, Sound, Network, Privacy, Updates, etc.),
Chrome profiles, web/YouTube search, volume/brightness/media control, screenshots, OCR,
keyboard control, file management, system info, memory, reminders, clipboard, weather,
focus/night/cinema/gaming modes, lock/sleep/shutdown/restart PC.
{reminders_info}"""


class Orchestrator:
    """Central command orchestrator v3.0 — connects all engines and services."""

    def __init__(self):
        self.ai_provider = AIProvider()
        self.automation = AutomationEngine()
        self.browser = BrowserEngine()
        self.vision = VisionEngine()
        self.workflow_engine = WorkflowEngine()
        self.memory = MemoryEngine()
        self.preferences = PreferenceEngine()
        self.reminder_service = ReminderService()
        self.notification_service = NotificationService()
        self.weather_service = WeatherService()
        self.file_manager = FileManager()
        self.focus_mode = FocusModeService(automation_engine=self.automation)
        self.planner = TaskPlanner(ai_provider=self.ai_provider)
        
        # Initialize Multi-Agent System
        self.agent_manager = AgentManager(self)
        self._init_agents()
        
        self.conversation_id = self.memory.create_conversation("Main Session")
        self._step_timeout = 15  # seconds per step
        log.info("Orchestrator v3.0 initialized — all engines and agents online")

    def _init_agents(self):
        """Initialize and register all specialized agents."""
        commander = CommanderAgent(self, self.ai_provider)
        automation_agent = AutomationAgent(self, self.automation, self.browser)
        vision_agent = VisionAgent(self, self.vision)
        
        self.agent_manager.register_agent(commander)
        self.agent_manager.register_agent(automation_agent)
        self.agent_manager.register_agent(vision_agent)

    async def route_agent_message(self, source: str, target: str, message: str, context: dict = None) -> dict:
        """Route a message from one agent to another using the AgentManager."""
        return await self.agent_manager.route_message(source, target, message, context)

    async def start_services(self):
        """Start background services."""
        await self.reminder_service.start()
        log.info("Background services started")

    async def stop_services(self):
        """Stop background services."""
        await self.reminder_service.stop()
        log.info("Background services stopped")

    async def process_command(self, text: str) -> dict:
        """Process a user command through the full pipeline."""
        start_time = time.time()

        # Store user message
        self.memory.add_message(self.conversation_id, "user", text)

        # Generate execution plan via AI planner
        plan = await self.planner.plan(text)
        log.info(f"Plan for '{text}': {[s['type'] for s in plan]}")

        # Execute the plan
        result = await self._execute_plan(plan, text)

        # Track usage
        duration_ms = (time.time() - start_time) * 1000
        intent = plan[0]["type"] if plan else "unknown"
        self.memory.log_command(
            text, intent,
            result.get("status", "success"),
            str(result.get("message", "")),
            duration_ms
        )
        self.preferences.track_command(intent, duration_ms)

        # Store assistant response
        ai_resp = result.get("ai_response", result.get("message", ""))
        if ai_resp:
            self.memory.add_message(self.conversation_id, "assistant", ai_resp)

        result["intent"] = intent
        result["duration_ms"] = round(duration_ms, 2)
        result["plan_steps"] = len(plan)
        return result

    async def _execute_plan(self, plan: list, original_text: str) -> dict:
        """Execute a sequence of planned steps with timeout per step."""
        if not plan:
            return {"success": True, "needs_ai_response": True, "message": ""}

        # Single conversation step
        if len(plan) == 1 and plan[0]["type"] == STEP_CONVERSATION:
            ai_response = await self._generate_ai_response(original_text, {})
            return {
                "success": True, "message": ai_response,
                "ai_response": ai_response, "status": "success"
            }

        # Multi-step execution
        messages = []
        last_result = {}
        all_success = True

        for i, step in enumerate(plan):
            step_type = step["type"]
            param = step.get("param")

            log.info(f"Executing step {i+1}/{len(plan)}: {step_type} → {param}")

            try:
                # Apply timeout per step
                result = await asyncio.wait_for(
                    self._execute_step(step_type, param, original_text),
                    timeout=self._step_timeout
                )
                if isinstance(result, dict):
                    if not result.get("success", True):
                        all_success = False
                    msg = result.get("message", "")
                    if msg:
                        messages.append(msg)
                    last_result = result
                else:
                    last_result = {"success": True}

            except asyncio.TimeoutError:
                log.error(f"Step {step_type} timed out after {self._step_timeout}s — skipping")
                all_success = False
                messages.append(f"Step {step_type} timed out")

            except Exception as e:
                log.error(f"Step {step_type} failed: {e}")
                all_success = False
                messages.append(f"Step {step_type} failed: {str(e)}")

        # Build final response
        final_message = messages[-1] if messages else "Done."

        if last_result.get("needs_ai_response"):
            ai_response = await self._generate_ai_response(original_text, last_result)
            return {
                "success": all_success, "message": ai_response,
                "ai_response": ai_response,
                "status": "success" if all_success else "partial"
            }

        return {
            "success": all_success,
            "message": final_message,
            "ai_response": final_message,
            "status": "success" if all_success else "partial",
            "steps_executed": len(plan),
        }

    async def _execute_step(self, step_type: str, param: Optional[str], original_text: str) -> dict:
        """Execute a single step from the plan."""

        if step_type == STEP_OPEN_APP:
            app = self._resolve_app(param or "")
            self.preferences.track_app_usage(app)
            return await self.automation.open_application(app)

        elif step_type == STEP_CLOSE_APP:
            app = self._resolve_app(param or "")
            return await self.automation.close_application(app)

        elif step_type == STEP_BROWSER_PROFILE:
            self.preferences.track_app_usage("chrome", profile=param)
            return await self.browser.open_chrome_with_profile(param or "")

        elif step_type == STEP_NAVIGATE_URL:
            return await self.automation.go_to_url(param or "")

        elif step_type == STEP_SEARCH_WEB:
            return await self.automation.search_web(param or "")

        elif step_type == STEP_SEARCH_YOUTUBE:
            return await self.automation.search_youtube(param or "")

        elif step_type == STEP_CLICK_TEXT:
            return await self.vision.click_on_text(param or "")

        elif step_type == STEP_TYPE_TEXT:
            return await self.automation.type_text(param or "")

        elif step_type == STEP_PRESS_KEY:
            return await self.automation.press_key(param or "")

        elif step_type == STEP_WAIT:
            secs = float(param or "1")
            await asyncio.sleep(secs)
            return {"success": True, "message": f"Waited {secs}s"}

        elif step_type == STEP_SCREENSHOT:
            return await self.automation.take_screenshot()

        elif step_type == STEP_READ_SCREEN:
            result = await self.vision.read_screen_text()
            result["needs_ai_response"] = True
            return result

        elif step_type == STEP_SYSTEM_CMD:
            return await self._handle_system_cmd(param or "")

        elif step_type == STEP_VOLUME:
            return await self._handle_volume(param or "")

        elif step_type == STEP_BRIGHTNESS:
            if param == "up":
                return await self.automation.brightness_up()
            else:
                return await self.automation.brightness_down()

        elif step_type == STEP_MEDIA:
            if param in ("play", "pause"):
                return await self.automation.media_play_pause()
            elif param == "next":
                return await self.automation.media_next()
            elif param == "prev":
                return await self.automation.media_prev()
            return {"success": True, "message": "Media command executed"}

        elif step_type == STEP_SWITCH_WINDOW:
            return await self.automation.switch_window(param or "")

        elif step_type == STEP_FILE_OP:
            return await self._handle_file_op(param)

        elif step_type == STEP_SPEAK:
            return {"success": True, "message": param or "", "ai_response": param}

        elif step_type == STEP_CONVERSATION:
            ai_resp = await self._generate_ai_response(param or original_text, {})
            return {"success": True, "message": ai_resp, "ai_response": ai_resp, "needs_ai_response": False}

        elif step_type == STEP_SET_REMINDER:
            return await self._handle_reminder(param)

        elif step_type == STEP_CLIPBOARD:
            return await self.automation.read_clipboard()

        elif step_type == STEP_WINDOW_CTRL:
            return await self._handle_window_ctrl(param or "")

        elif step_type == STEP_WEATHER:
            return await self._handle_weather(param or "current")

        elif step_type == STEP_FOCUS_MODE:
            return await self._handle_focus_mode(param or "focus")

        elif step_type == STEP_FILE_FIND:
            result = await self.file_manager.find_file(param or "")
            if result.get("success"):
                result["needs_ai_response"] = True
                result["data"] = result.get("files", [])
            return result

        elif step_type == STEP_FILE_CREATE:
            return await self.file_manager.create_file(param or "untitled.txt")

        else:
            return {"success": True, "needs_ai_response": True, "message": ""}

    # ─── Sub-handlers ─────────────────────────────────────────────────

    async def _handle_system_cmd(self, cmd: str) -> dict:
        if cmd == "info":
            info = await self.automation.get_system_info()
            info["needs_ai_response"] = True
            return info
        elif cmd == "shutdown":
            return await self.automation.shutdown_pc()
        elif cmd == "restart":
            return await self.automation.restart_pc()
        elif cmd == "lock":
            return await self.automation.lock_pc()
        elif cmd == "sleep":
            return await self.automation.sleep_pc()
        return {"success": False, "message": f"Unknown system command: {cmd}"}

    async def _handle_volume(self, param: str) -> dict:
        if param == "up":
            return await self.automation.volume_up()
        elif param == "down":
            return await self.automation.volume_down()
        elif param == "mute":
            return await self.automation.volume_mute()
        elif param.startswith("set:"):
            try:
                level = int(param.split(":")[1])
                return await self.automation.set_volume(level)
            except (ValueError, IndexError):
                return {"success": False, "message": "Invalid volume level"}
        return await self.automation.volume_mute()

    async def _handle_file_op(self, param) -> dict:
        try:
            if isinstance(param, str):
                data = json.loads(param)
            else:
                data = param or {}
            action = data.get("action", "open")
            path = data.get("path", "")
            if action == "open":
                return await self.automation.open_file(path)
            elif action == "create":
                return await self.automation.create_folder(path)
            return {"success": False, "message": f"Unknown file action: {action}"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    async def _handle_reminder(self, param) -> dict:
        try:
            if isinstance(param, str):
                data = json.loads(param)
            else:
                data = param or {}
            seconds = data.get("seconds", 60)
            task = data.get("task", "reminder")
            result = await self.reminder_service.add_reminder(task, seconds)
            return result
        except Exception as e:
            return {"success": False, "message": f"Reminder error: {str(e)}"}

    async def _handle_window_ctrl(self, action: str) -> dict:
        if action == "maximize":
            return await self.automation.maximize_window()
        elif action == "minimize":
            return await self.automation.minimize_window()
        return {"success": False, "message": f"Unknown window action: {action}"}

    async def _handle_weather(self, param: str) -> dict:
        """Handle weather commands."""
        try:
            if param == "rain":
                result = await self.weather_service.will_it_rain()
                return {"success": True, "message": result.get("message", ""), "ai_response": result.get("message", "")}
            elif param == "forecast":
                result = await self.weather_service.get_forecast()
                if result.get("success"):
                    days = result.get("days", [])
                    forecast_text = ", ".join([f"{d['date']}: {d['temp_min']}-{d['temp_max']}°C {d['condition']}" for d in days[:3]])
                    return {"success": True, "message": f"Weather forecast, Sir: {forecast_text}", "ai_response": f"Weather forecast: {forecast_text}"}
                return {"success": False, "message": result.get("message", "Forecast unavailable")}
            else:
                result = await self.weather_service.get_current()
                if result.get("success"):
                    briefing = self.weather_service.get_weather_briefing(result)
                    return {"success": True, "message": briefing, "ai_response": briefing, "data": result}
                return {"success": False, "message": result.get("message", "Weather data unavailable")}
        except Exception as e:
            return {"success": False, "message": f"Weather error: {str(e)}"}

    async def _handle_focus_mode(self, mode: str) -> dict:
        """Handle focus/night/cinema/gaming mode commands."""
        try:
            if mode == "focus":
                return await self.focus_mode.activate_focus()
            elif mode == "night":
                return await self.focus_mode.activate_night_mode()
            elif mode == "cinema":
                return await self.focus_mode.activate_cinema_mode()
            elif mode == "gaming":
                return await self.focus_mode.activate_gaming_mode()
            elif mode == "presentation":
                return await self.focus_mode.activate_presentation_mode()
            elif mode == "normal":
                return await self.focus_mode.deactivate()
            return {"success": False, "message": f"Unknown mode: {mode}"}
        except Exception as e:
            return {"success": False, "message": f"Focus mode error: {str(e)}"}

    def _resolve_app(self, app_name: str) -> str:
        """Resolve app name using the intent classifier's alias map."""
        from ai.intent import APP_ALIASES
        return APP_ALIASES.get(app_name.lower().strip(), app_name.lower().strip())

    async def _generate_ai_response(self, user_message: str, context: dict) -> str:
        """Generate an AI response with full JARVIS personality."""
        from datetime import datetime

        # Build weather info
        weather_info = ""
        try:
            w = await self.weather_service.get_current()
            if w.get("success"):
                weather_info = f"Current weather in Chennai: {w['temp']}°C, {w['condition']}, Humidity {w['humidity']}%"
        except: pass

        # Build reminders info
        reminders_info = ""
        pending = self.reminder_service.get_pending()
        if pending:
            items = [f"- {r['task']} (in {int(r['remaining_seconds'])}s)" for r in pending[:5]]
            reminders_info = f"Pending reminders:\n" + "\n".join(items)

        system_prompt = JARVIS_SYSTEM_PROMPT.format(
            user=settings.USER_NAME,
            time=datetime.now().strftime("%A, %B %d, %Y %I:%M %p"),
            weather_info=weather_info,
            reminders_info=reminders_info,
        )

        if context.get("data"):
            user_message = f"{user_message}\n\nSystem data: {context['data']}"
        if context.get("text"):
            user_message = f"{user_message}\n\nScreen text (OCR): {context['text'][:2000]}"

        user_ctx = self.preferences.get_user_context()
        if user_ctx.get("frequent_apps"):
            apps = [a["app_name"] for a in user_ctx["frequent_apps"][:3]]
            system_prompt += f"\nUser's frequent apps: {', '.join(apps)}"

        # Add focus mode context
        fm = self.focus_mode.get_status()
        if fm["mode"] != "normal":
            system_prompt += f"\nCurrent mode: {fm['mode']}"

        history = self.memory.get_recent_messages(limit=10)
        formatted = [
            {"role": m["role"], "content": m["content"]}
            for m in history if m["role"] in ("user", "assistant")
        ]

        response = await self.ai_provider.chat(
            message=user_message,
            system_prompt=system_prompt,
            history=formatted,
        )
        return response

    async def get_system_status(self) -> dict:
        """Get full system status for dashboard."""
        sys_info = await self.automation.get_system_info()
        memory_stats = self.memory.get_stats()
        providers = self.ai_provider.get_available_providers()
        chrome_profiles = self.browser.detect_chrome_profiles()

        # Fetch weather
        weather = {}
        try:
            weather = await self.weather_service.get_current()
        except: pass

        return {
            "system": sys_info.get("data", {}),
            "memory": memory_stats,
            "ai_providers": providers,
            "default_provider": settings.DEFAULT_AI_PROVIDER,
            "user": settings.USER_NAME,
            "version": settings.APP_VERSION,
            "chrome_profiles": [
                {"name": p["name"], "email": p.get("email", "")}
                for p in chrome_profiles
            ],
            "frequent_apps": self.preferences.get_frequent_apps(5),
            "reminders": self.reminder_service.get_pending(),
            "weather": weather,
            "focus_mode": self.focus_mode.get_status(),
        }
