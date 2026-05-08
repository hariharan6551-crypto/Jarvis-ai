"""
J.A.R.V.I.S AI Provider Manager
Supports OpenAI, Anthropic Claude, Google Gemini, and Ollama.
"""

import asyncio
from typing import AsyncGenerator, Optional
from core.logger import get_logger
from config.settings import settings

log = get_logger("ai")


class AIProvider:
    """Manages multiple AI providers with fallback support."""

    def __init__(self):
        self.providers = {}
        self._init_providers()
        log.info(f"AI Provider initialized with default: {settings.DEFAULT_AI_PROVIDER}")

    def _init_providers(self):
        """Initialize available AI providers."""
        # OpenAI
        if settings.OPENAI_API_KEY:
            try:
                from openai import AsyncOpenAI
                self.providers["openai"] = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                log.info("OpenAI provider ready")
            except Exception as e:
                log.warning(f"OpenAI init failed: {e}")

        # Anthropic
        if settings.ANTHROPIC_API_KEY:
            try:
                from anthropic import AsyncAnthropic
                self.providers["anthropic"] = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
                log.info("Anthropic provider ready")
            except Exception as e:
                log.warning(f"Anthropic init failed: {e}")

        # Gemini
        if settings.GEMINI_API_KEY:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self.providers["gemini"] = genai
                log.info("Gemini provider ready")
            except Exception as e:
                log.warning(f"Gemini init failed: {e}")

        # Ollama (local, always available)
        try:
            import ollama
            self.providers["ollama"] = ollama
            log.info("Ollama provider ready")
        except Exception as e:
            log.debug(f"Ollama not available: {e}")

    def get_available_providers(self) -> list:
        """Return list of available provider names."""
        return list(self.providers.keys())

    async def chat(
        self,
        message: str,
        system_prompt: str = None,
        provider: str = None,
        model: str = None,
        history: list = None,
    ) -> str:
        """Send a chat message and get a complete response."""
        provider = provider or settings.DEFAULT_AI_PROVIDER
        model = model or settings.DEFAULT_AI_MODEL

        if provider not in self.providers:
            available = self.get_available_providers()
            if available:
                provider = available[0]
                log.warning(f"Requested provider unavailable, falling back to {provider}")
            else:
                return "I apologize, but no AI providers are currently configured. Please add an API key in the settings."

        try:
            if provider == "openai":
                return await self._chat_openai(message, system_prompt, model, history)
            elif provider == "anthropic":
                return await self._chat_anthropic(message, system_prompt, model, history)
            elif provider == "gemini":
                return await self._chat_gemini(message, system_prompt, model, history)
            elif provider == "ollama":
                return await self._chat_ollama(message, system_prompt, model, history)
            else:
                return f"Unknown provider: {provider}"
        except Exception as e:
            log.error(f"AI chat error ({provider}): {e}")
            return f"I encountered an error processing your request: {str(e)}"

    async def chat_stream(
        self,
        message: str,
        system_prompt: str = None,
        provider: str = None,
        model: str = None,
        history: list = None,
    ) -> AsyncGenerator[str, None]:
        """Stream a chat response token by token."""
        provider = provider or settings.DEFAULT_AI_PROVIDER
        model = model or settings.DEFAULT_AI_MODEL

        if provider not in self.providers:
            available = self.get_available_providers()
            if available:
                provider = available[0]
            else:
                yield "No AI providers configured."
                return

        try:
            if provider == "openai":
                async for token in self._stream_openai(message, system_prompt, model, history):
                    yield token
            elif provider == "anthropic":
                async for token in self._stream_anthropic(message, system_prompt, model, history):
                    yield token
            elif provider == "gemini":
                async for token in self._stream_gemini(message, system_prompt, model, history):
                    yield token
            elif provider == "ollama":
                async for token in self._stream_ollama(message, system_prompt, model, history):
                    yield token
        except Exception as e:
            log.error(f"AI stream error ({provider}): {e}")
            yield f"Error: {str(e)}"

    # ─── OpenAI ───────────────────────────────────────────────────────

    async def _chat_openai(self, message, system_prompt, model, history):
        client = self.providers["openai"]
        messages = self._build_messages(message, system_prompt, history)
        response = await client.chat.completions.create(
            model=model or "gpt-4o",
            messages=messages,
            max_tokens=2048,
        )
        return response.choices[0].message.content

    async def _stream_openai(self, message, system_prompt, model, history):
        client = self.providers["openai"]
        messages = self._build_messages(message, system_prompt, history)
        stream = await client.chat.completions.create(
            model=model or "gpt-4o",
            messages=messages,
            max_tokens=2048,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    # ─── Anthropic ────────────────────────────────────────────────────

    async def _chat_anthropic(self, message, system_prompt, model, history):
        client = self.providers["anthropic"]
        msgs = []
        if history:
            for h in history[-10:]:
                msgs.append({"role": h["role"], "content": h["content"]})
        msgs.append({"role": "user", "content": message})

        response = await client.messages.create(
            model=model or "claude-sonnet-4-20250514",
            max_tokens=2048,
            system=system_prompt or "You are J.A.R.V.I.S, an advanced AI assistant.",
            messages=msgs,
        )
        return response.content[0].text

    async def _stream_anthropic(self, message, system_prompt, model, history):
        client = self.providers["anthropic"]
        msgs = []
        if history:
            for h in history[-10:]:
                msgs.append({"role": h["role"], "content": h["content"]})
        msgs.append({"role": "user", "content": message})

        async with client.messages.stream(
            model=model or "claude-sonnet-4-20250514",
            max_tokens=2048,
            system=system_prompt or "You are J.A.R.V.I.S, an advanced AI assistant.",
            messages=msgs,
        ) as stream:
            async for text in stream.text_stream:
                yield text

    # ─── Gemini ───────────────────────────────────────────────────────

    async def _chat_gemini(self, message, system_prompt, model, history):
        genai = self.providers["gemini"]
        gen_model = genai.GenerativeModel(
            model_name=model or "gemini-1.5-flash",
            system_instruction=system_prompt or "You are J.A.R.V.I.S, an advanced AI assistant.",
        )
        chat = gen_model.start_chat(history=self._build_gemini_history(history))
        response = await asyncio.to_thread(chat.send_message, message)
        return response.text

    async def _stream_gemini(self, message, system_prompt, model, history):
        genai = self.providers["gemini"]
        gen_model = genai.GenerativeModel(
            model_name=model or "gemini-1.5-flash",
            system_instruction=system_prompt or "You are J.A.R.V.I.S, an advanced AI assistant.",
        )
        chat = gen_model.start_chat(history=self._build_gemini_history(history))
        response = await asyncio.to_thread(
            lambda: gen_model.generate_content(message, stream=True)
        )
        for chunk in response:
            if chunk.text:
                yield chunk.text

    def _build_gemini_history(self, history):
        if not history:
            return []
        gemini_history = []
        for h in history[-10:]:
            role = "user" if h["role"] == "user" else "model"
            gemini_history.append({"role": role, "parts": [h["content"]]})
        return gemini_history

    # ─── Ollama ───────────────────────────────────────────────────────

    async def _chat_ollama(self, message, system_prompt, model, history):
        import ollama as ollama_lib
        messages = self._build_messages(message, system_prompt, history)
        response = await asyncio.to_thread(
            ollama_lib.chat,
            model=model or "llama3.1",
            messages=messages,
        )
        return response["message"]["content"]

    async def _stream_ollama(self, message, system_prompt, model, history):
        import ollama as ollama_lib
        messages = self._build_messages(message, system_prompt, history)

        def _generate():
            return ollama_lib.chat(
                model=model or "llama3.1",
                messages=messages,
                stream=True,
            )

        stream = await asyncio.to_thread(_generate)
        for chunk in stream:
            if chunk["message"]["content"]:
                yield chunk["message"]["content"]

    # ─── Helpers ──────────────────────────────────────────────────────

    def _build_messages(self, message, system_prompt, history):
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if history:
            for h in history[-10:]:
                messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": message})
        return messages
