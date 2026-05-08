"""
J.A.R.V.I.S Command Execution Orchestrator v2.0
Central brain connecting AI planning, automation, browser control, vision, and memory.
Routes commands through the AI task planner for multi-step execution.
"""

import asyncio
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
    STEP_SPEAK, STEP_CONVERSATION,
)
from automation.engine import AutomationEngine
from automation.browser import BrowserEngine
from automation.vision import VisionEngine
from automation.workflows import WorkflowEngine, Workflow, WorkflowStep
from ai.provider import AIProvider
from memory.engine import MemoryEngine
from memory.preferences import PreferenceEngine
from config.settings import settings

log = get_logger("orchestrator")

JARVIS_SYSTEM_PROMPT = """You are J.A.R.V.I.S (Just A Rather Very Intelligent System), an advanced AI assistant created for {user}.
You speak in a sophisticated, articulate manner — confident yet warm, like a trusted advisor.
You are witty, efficient, and always professional. You address the user by name.
Keep responses concise and natural for voice output (2-3 sentences max unless asked for detail).
You are running on their Windows PC and can control their system.
Current time: {time}

You can:
- Open/close any application
- Control Chrome with specific Google account profiles
- Search the web and YouTube
- Control volume, brightness, media playback
- Take screenshots, read screen content via OCR
- Type text, press keyboard shortcuts
- Navigate files and folders
- Provide system information (CPU, RAM, disk, battery)
- Remember user preferences and habits
- Execute multi-step automated workflows"""


class Orchestrator:
    """Central command orchestrator v2.0 — connects all engines."""

    def __init__(self):
        self.ai_provider = AIProvider()
        self.automation = AutomationEngine()
        self.browser = BrowserEngine()
        self.vision = VisionEngine()
        self.workflow_engine = WorkflowEngine()
        self.memory = MemoryEngine()
        self.preferences = PreferenceEngine()
        self.planner = TaskPlanner(ai_provider=self.ai_provider)
        self.conversation_id = self.memory.create_conversation("Main Session")
        log.info("Orchestrator v2.0 initialized — all engines online")

    async def process_command(self, text: str) -> dict:
        """Process a user command through the full v2.0 pipeline."""
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
        self.memory.log_command(text, intent, result.get("status", "success"), str(result.get("message", "")), duration_ms)
        self.preferences.track_command(intent, duration_ms)

        # Store assistant response
        ai_resp = result.get("ai_response", result.get("message", ""))
        if ai_resp:
            self.memory.add_message(self.conversation_id, "assistant", ai_resp)

        result["intent"] = intent
        result["duration_ms"] = round(duration_ms, 2)
        result["plan_steps"] = len(plan)
        return result

    async def _execute_plan(self, plan: list[dict], original_text: str) -> dict:
        """Execute a sequence of planned steps."""
        if not plan:
            return {"success": True, "needs_ai_response": True, "message": ""}

        # Single conversation step — just get AI response
        if len(plan) == 1 and plan[0]["type"] == STEP_CONVERSATION:
            ai_response = await self._generate_ai_response(original_text, {})
            return {"success": True, "message": ai_response, "ai_response": ai_response, "status": "success"}

        # Multi-step execution
        messages = []
        last_result = {}
        all_success = True

        for i, step in enumerate(plan):
            step_type = step["type"]
            param = step.get("param")

            log.info(f"Executing step {i+1}/{len(plan)}: {step_type} -> {param}")

            try:
                result = await self._execute_step(step_type, param, original_text)
                if isinstance(result, dict):
                    if not result.get("success", True):
                        all_success = False
                    msg = result.get("message", "")
                    if msg:
                        messages.append(msg)
                    last_result = result
                else:
                    last_result = {"success": True}
            except Exception as e:
                log.error(f"Step {step_type} failed: {e}")
                all_success = False
                messages.append(f"Step {step_type} failed: {str(e)}")

        # Build final response
        final_message = messages[-1] if messages else "Done."

        # If we need an AI-crafted response
        if last_result.get("needs_ai_response"):
            ai_response = await self._generate_ai_response(original_text, last_result)
            return {"success": all_success, "message": ai_response, "ai_response": ai_response, "status": "success" if all_success else "partial"}

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
            if param == "up":
                return await self.automation.volume_up()
            elif param == "down":
                return await self.automation.volume_down()
            else:
                return await self.automation.volume_mute()

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

        else:
            return {"success": True, "needs_ai_response": True, "message": ""}

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

    async def _handle_file_op(self, param) -> dict:
        import json as _json
        try:
            if isinstance(param, str):
                data = _json.loads(param)
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

    def _resolve_app(self, app_name: str) -> str:
        """Resolve app name using the intent classifier's alias map."""
        from ai.intent import APP_ALIASES
        return APP_ALIASES.get(app_name.lower().strip(), app_name.lower().strip())

    async def _generate_ai_response(self, user_message: str, context: dict) -> str:
        """Generate an AI response for conversation or context-aware replies."""
        from datetime import datetime
        system_prompt = JARVIS_SYSTEM_PROMPT.format(
            user=settings.USER_NAME,
            time=datetime.now().strftime("%A, %B %d, %Y %I:%M %p"),
        )

        # Add context data
        if context.get("data"):
            user_message = f"{user_message}\n\nSystem data: {context['data']}"
        if context.get("text"):
            user_message = f"{user_message}\n\nScreen text (OCR): {context['text'][:2000]}"

        # Add user preferences context
        user_ctx = self.preferences.get_user_context()
        if user_ctx.get("frequent_apps"):
            apps = [a["app_name"] for a in user_ctx["frequent_apps"][:3]]
            system_prompt += f"\nUser's frequent apps: {', '.join(apps)}"

        history = self.memory.get_recent_messages(limit=10)
        formatted = [{"role": m["role"], "content": m["content"]} for m in history if m["role"] in ("user", "assistant")]

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

        return {
            "system": sys_info.get("data", {}),
            "memory": memory_stats,
            "ai_providers": providers,
            "default_provider": settings.DEFAULT_AI_PROVIDER,
            "user": settings.USER_NAME,
            "version": settings.APP_VERSION,
            "chrome_profiles": [{"name": p["name"], "email": p.get("email", "")} for p in chrome_profiles],
            "frequent_apps": self.preferences.get_frequent_apps(5),
        }
