"""
J.A.R.V.I.S Command Execution Orchestrator
Routes classified intents to the appropriate automation actions.
"""

import asyncio
import time
from typing import Optional
from core.logger import get_logger
from ai.intent import (
    IntentClassifier,
    INTENT_OPEN_APP, INTENT_CLOSE_APP, INTENT_SEARCH_WEB,
    INTENT_SEARCH_YOUTUBE, INTENT_VOLUME_UP, INTENT_VOLUME_DOWN,
    INTENT_VOLUME_MUTE, INTENT_BRIGHTNESS_UP, INTENT_BRIGHTNESS_DOWN,
    INTENT_SCREENSHOT, INTENT_SHUTDOWN, INTENT_RESTART, INTENT_LOCK,
    INTENT_SLEEP, INTENT_MEDIA_PLAY, INTENT_MEDIA_PAUSE,
    INTENT_MEDIA_NEXT, INTENT_MEDIA_PREV, INTENT_TYPE_TEXT,
    INTENT_SYSTEM_INFO, INTENT_CONVERSATION, INTENT_UNKNOWN,
)
from automation.engine import AutomationEngine
from ai.provider import AIProvider
from memory.engine import MemoryEngine
from config.settings import settings

log = get_logger("orchestrator")

JARVIS_SYSTEM_PROMPT = """You are J.A.R.V.I.S (Just A Rather Very Intelligent System), an advanced AI assistant created for {user}.
You speak in a sophisticated, articulate manner — confident yet warm, like a trusted advisor.
You are witty, efficient, and always professional. You address the user by name.
Keep responses concise and natural for voice output (2-3 sentences max unless asked for detail).
You are running on their Windows PC and can control their system.
Current time context will be provided when available."""


class Orchestrator:
    """Central command orchestrator connecting all engines."""

    def __init__(self):
        self.intent_classifier = IntentClassifier()
        self.automation = AutomationEngine()
        self.ai_provider = AIProvider()
        self.memory = MemoryEngine()
        self.conversation_id = self.memory.create_conversation("Main Session")
        self.pending_confirmations = {}
        log.info("Orchestrator initialized")

    async def process_command(self, text: str) -> dict:
        """Process a user command through the full pipeline."""
        start_time = time.time()

        # Classify intent
        intent, param = self.intent_classifier.classify(text)
        log.info(f"Processing: '{text}' -> intent={intent}, param={param}")

        # Store user message
        self.memory.add_message(self.conversation_id, "user", text, {"intent": intent})

        # Execute based on intent
        result = await self._execute_intent(intent, param, text)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        self.memory.log_command(text, intent, result.get("status", "success"), str(result), duration_ms)

        # Generate AI response if needed
        if result.get("needs_ai_response", False) or intent == INTENT_CONVERSATION:
            ai_response = await self._generate_ai_response(text, result)
            result["ai_response"] = ai_response
            self.memory.add_message(self.conversation_id, "assistant", ai_response)
        elif result.get("message"):
            self.memory.add_message(self.conversation_id, "assistant", result["message"])

        result["intent"] = intent
        result["duration_ms"] = round(duration_ms, 2)
        return result

    async def _execute_intent(self, intent: str, param: Optional[str], original_text: str) -> dict:
        """Execute the classified intent."""
        try:
            if intent == INTENT_OPEN_APP:
                return await self.automation.open_application(param or "")
            elif intent == INTENT_CLOSE_APP:
                return await self.automation.close_application(param or "")
            elif intent == INTENT_SEARCH_WEB:
                return await self.automation.search_web(param or "")
            elif intent == INTENT_SEARCH_YOUTUBE:
                return await self.automation.search_youtube(param or "")
            elif intent == INTENT_VOLUME_UP:
                return await self.automation.volume_up()
            elif intent == INTENT_VOLUME_DOWN:
                return await self.automation.volume_down()
            elif intent == INTENT_VOLUME_MUTE:
                return await self.automation.volume_mute()
            elif intent == INTENT_BRIGHTNESS_UP:
                return await self.automation.brightness_up()
            elif intent == INTENT_BRIGHTNESS_DOWN:
                return await self.automation.brightness_down()
            elif intent == INTENT_SCREENSHOT:
                return await self.automation.take_screenshot()
            elif intent == INTENT_SHUTDOWN:
                return await self.automation.shutdown_pc()
            elif intent == INTENT_RESTART:
                return await self.automation.restart_pc()
            elif intent == INTENT_LOCK:
                return await self.automation.lock_pc()
            elif intent == INTENT_SLEEP:
                return await self.automation.sleep_pc()
            elif intent in (INTENT_MEDIA_PLAY, INTENT_MEDIA_PAUSE):
                return await self.automation.media_play_pause()
            elif intent == INTENT_MEDIA_NEXT:
                return await self.automation.media_next()
            elif intent == INTENT_MEDIA_PREV:
                return await self.automation.media_prev()
            elif intent == INTENT_TYPE_TEXT:
                return await self.automation.type_text(param or "")
            elif intent == INTENT_SYSTEM_INFO:
                info = await self.automation.get_system_info()
                info["needs_ai_response"] = True
                return info
            elif intent == INTENT_CONVERSATION:
                return {"success": True, "needs_ai_response": True, "message": ""}
            else:
                return {"success": True, "needs_ai_response": True, "message": ""}
        except Exception as e:
            log.error(f"Intent execution failed: {e}")
            return {"success": False, "message": f"Command failed: {str(e)}"}

    async def _generate_ai_response(self, user_message: str, context: dict) -> str:
        """Generate an AI response for conversation or context-aware replies."""
        system_prompt = JARVIS_SYSTEM_PROMPT.format(user=settings.USER_NAME)

        # Add context about executed actions
        if context.get("data"):
            context_str = f"\n\nSystem information data: {context['data']}"
            user_message = f"{user_message}\n{context_str}"

        history = self.memory.get_recent_messages(limit=10)
        formatted_history = [
            {"role": m["role"], "content": m["content"]}
            for m in history
            if m["role"] in ("user", "assistant")
        ]

        response = await self.ai_provider.chat(
            message=user_message,
            system_prompt=system_prompt,
            history=formatted_history,
        )
        return response

    async def get_system_status(self) -> dict:
        """Get full system status for dashboard."""
        sys_info = await self.automation.get_system_info()
        memory_stats = self.memory.get_stats()
        providers = self.ai_provider.get_available_providers()

        return {
            "system": sys_info.get("data", {}),
            "memory": memory_stats,
            "ai_providers": providers,
            "default_provider": settings.DEFAULT_AI_PROVIDER,
            "user": settings.USER_NAME,
            "version": settings.APP_VERSION,
        }
