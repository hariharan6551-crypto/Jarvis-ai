"""
J.A.R.V.I.S AI Provider Manager
Supports Google Gemini (new SDK), OpenAI, Anthropic Claude, and Ollama.
Features: retry with exponential backoff, auto-fallback, health pings.
"""

import asyncio
import re as _re
import time
import warnings
from typing import AsyncGenerator, Optional
from core.logger import get_logger
from config.settings import settings

log = get_logger("ai")


class AIProvider:
    """Manages multiple AI providers with fallback support and retry logic."""

    # Placeholder values that indicate an unconfigured key
    _PLACEHOLDER_KEYS = {"your_key_here", "your-key-here", "changeme", "xxx", "todo", "sk-xxx", ""}

    def __init__(self):
        self.providers = {}
        self._consecutive_failures = {}
        self._last_health_check = {}
        self._health_status = {}
        self._fallback_active = False
        self._primary_provider = settings.DEFAULT_AI_PROVIDER
        self._health_check_interval = 60  # seconds
        self._max_consecutive_failures = 3
        self._gemini_client = None  # google-genai Client
        self._last_gemini_request = 0.0  # Rate limiter timestamp
        self._gemini_min_interval = 3.5  # Min seconds between Gemini requests (free tier: ~20/min)
        self._init_providers()
        log.info(f"AI Provider initialized with default: {settings.DEFAULT_AI_PROVIDER}")

    def _is_valid_key(self, key: str) -> bool:
        """Check if an API key is valid (not a placeholder)."""
        if not key:
            return False
        return key.strip().lower() not in self._PLACEHOLDER_KEYS

    def _init_providers(self):
        """Initialize available AI providers."""
        # ─── Gemini (Primary — free tier available) ───────────────────
        if settings.GEMINI_API_KEY and self._is_valid_key(settings.GEMINI_API_KEY):
            try:
                from google import genai
                self._gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
                self.providers["gemini"] = "genai"
                self._consecutive_failures["gemini"] = 0
                self._health_status["gemini"] = "ok"
                log.info("✓ Gemini provider ready (google-genai SDK)")
            except ImportError:
                # Fall back to deprecated google-generativeai
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", FutureWarning)
                        import google.generativeai as genai_legacy
                    genai_legacy.configure(api_key=settings.GEMINI_API_KEY)
                    self.providers["gemini"] = genai_legacy
                    self._consecutive_failures["gemini"] = 0
                    self._health_status["gemini"] = "ok"
                    log.info("✓ Gemini provider ready (legacy SDK)")
                except Exception as e:
                    log.warning(f"Gemini init failed: {e}")
                    self._health_status["gemini"] = "failed"
            except Exception as e:
                log.warning(f"Gemini init failed: {e}")
                self._health_status["gemini"] = "failed"
        else:
            if settings.GEMINI_API_KEY:
                log.warning("Gemini API key is a placeholder — skipping")
            else:
                log.warning("No GEMINI_API_KEY set in .env — Gemini unavailable")

        # ─── OpenAI ───────────────────────────────────────────────────
        if settings.OPENAI_API_KEY and self._is_valid_key(settings.OPENAI_API_KEY):
            try:
                from openai import AsyncOpenAI
                self.providers["openai"] = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                self._consecutive_failures["openai"] = 0
                self._health_status["openai"] = "ok"
                log.info("✓ OpenAI provider ready")
            except Exception as e:
                log.warning(f"OpenAI init failed: {e}")
                self._health_status["openai"] = "failed"

        # ─── Anthropic ────────────────────────────────────────────────
        if settings.ANTHROPIC_API_KEY and self._is_valid_key(settings.ANTHROPIC_API_KEY):
            try:
                from anthropic import AsyncAnthropic
                self.providers["anthropic"] = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
                self._consecutive_failures["anthropic"] = 0
                self._health_status["anthropic"] = "ok"
                log.info("✓ Anthropic provider ready")
            except Exception as e:
                log.warning(f"Anthropic init failed: {e}")
                self._health_status["anthropic"] = "failed"

        # ─── Ollama (local, free, no API key needed) ──────────────────
        try:
            import httpx
            # Quick check if Ollama is running
            try:
                resp = httpx.get(f"{settings.OLLAMA_HOST}/api/tags", timeout=2)
                if resp.status_code == 200:
                    import ollama
                    self.providers["ollama"] = ollama
                    self._consecutive_failures["ollama"] = 0
                    self._health_status["ollama"] = "ok"
                    log.info("✓ Ollama provider ready (local)")
            except (httpx.ConnectError, httpx.TimeoutException):
                log.debug("Ollama not running locally")
        except ImportError:
            log.debug("httpx/ollama not installed")

    def get_available_providers(self) -> list:
        """Return list of available provider names."""
        return list(self.providers.keys())

    def get_health_status(self) -> dict:
        """Return health status of all providers."""
        return {
            name: {
                "status": self._health_status.get(name, "unknown"),
                "failures": self._consecutive_failures.get(name, 0),
                "available": name in self.providers,
            }
            for name in ["gemini", "openai", "anthropic", "ollama"]
        }

    # ─── Retry Logic ──────────────────────────────────────────────────

    async def _retry_with_backoff(self, provider: str, func, *args, **kwargs):
        """
        Retry logic with smart 429 rate-limit detection.
        For 429 errors: extracts the retry delay from the error message and waits.
        For other errors: 3 attempts with exponential backoff (1s → 2s → 4s).
        """
        max_retries = 4
        base_delay = 1.0

        for attempt in range(1, max_retries + 1):
            try:
                # Rate limiter: space out Gemini requests (free tier = 20/min)
                if provider == "gemini":
                    now = time.time()
                    elapsed = now - self._last_gemini_request
                    if elapsed < self._gemini_min_interval:
                        wait_time = self._gemini_min_interval - elapsed
                        log.debug(f"Rate limiting: waiting {wait_time:.1f}s before Gemini request")
                        await asyncio.sleep(wait_time)
                    self._last_gemini_request = time.time()

                result = await func(*args, **kwargs)
                # Reset failure counter on success
                self._consecutive_failures[provider] = 0
                self._health_status[provider] = "ok"
                return result
            except Exception as e:
                error_str = str(e)
                is_rate_limit = "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower()

                # Extract retry delay from error message if available
                if is_rate_limit:
                    retry_match = _re.search(r"retry\s+in\s+([\d.]+)s", error_str, _re.IGNORECASE)
                    if retry_match:
                        delay = float(retry_match.group(1)) + 1.0  # Add 1s buffer
                    else:
                        delay = 8.0 * attempt  # 8s, 16s, 24s, 32s for rate limits
                    log.warning(
                        f"Rate limit hit on '{provider}' (attempt {attempt}/{max_retries}). "
                        f"Waiting {delay:.1f}s before retry..."
                    )
                else:
                    delay = base_delay * (2 ** (attempt - 1))  # 1s, 2s, 4s, 8s
                    log.error(
                        f"AI provider '{provider}' attempt {attempt}/{max_retries} failed: {e} "
                        f"(timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')})"
                    )

                self._consecutive_failures[provider] = self._consecutive_failures.get(provider, 0) + 1

                if attempt < max_retries:
                    log.info(f"Retrying in {delay:.1f}s...")
                    await asyncio.sleep(delay)
                else:
                    # All retries exhausted
                    self._health_status[provider] = "degraded"

                    # Check if we should auto-switch to fallback
                    if self._consecutive_failures.get(provider, 0) >= self._max_consecutive_failures:
                        self._health_status[provider] = "failed"
                        log.warning(
                            f"Provider '{provider}' failed {self._max_consecutive_failures} "
                            f"consecutive times — switching to fallback"
                        )
                    raise

    # ─── Auto-Fallback ────────────────────────────────────────────────

    def _get_fallback_provider(self, failed_provider: str) -> Optional[str]:
        """Get the next available fallback provider."""
        # Priority order for fallback
        fallback_order = ["gemini", "openai", "anthropic", "ollama"]

        for name in fallback_order:
            if (
                name != failed_provider
                and name in self.providers
                and self._health_status.get(name) != "failed"
            ):
                log.info(f"Falling back to provider: {name}")
                return name
        return None

    # ─── Health Check ─────────────────────────────────────────────────

    async def health_check(self):
        """Ping all providers to check health. Run every 60 seconds."""
        while True:
            for name in list(self.providers.keys()):
                try:
                    now = time.time()
                    last_check = self._last_health_check.get(name, 0)
                    if now - last_check < self._health_check_interval:
                        continue

                    self._last_health_check[name] = now

                    if name == "openai":
                        client = self.providers["openai"]
                        await asyncio.wait_for(
                            client.models.list(),
                            timeout=10
                        )
                        self._health_status[name] = "ok"
                        self._consecutive_failures[name] = 0

                    elif name == "gemini":
                        # Quick health check for Gemini
                        if self._gemini_client:
                            await asyncio.to_thread(
                                lambda: self._gemini_client.models.list()
                            )
                        self._health_status[name] = "ok"
                        self._consecutive_failures[name] = 0

                    elif name == "ollama":
                        import ollama as ollama_lib
                        await asyncio.to_thread(ollama_lib.list)
                        self._health_status[name] = "ok"
                        self._consecutive_failures[name] = 0

                    elif name == "anthropic":
                        # Anthropic doesn't have a simple list endpoint,
                        # just mark as ok if init succeeded
                        if name in self.providers:
                            self._health_status[name] = "ok"

                    log.debug(f"Health check passed: {name}")

                except asyncio.TimeoutError:
                    self._health_status[name] = "degraded"
                    log.warning(f"Health check timeout: {name}")
                except Exception as e:
                    self._health_status[name] = "degraded"
                    log.warning(f"Health check failed for {name}: {e}")

            await asyncio.sleep(self._health_check_interval)

    # ─── Chat (with retry + fallback) ─────────────────────────────────

    async def chat(
        self,
        message: str,
        system_prompt: str = None,
        provider: str = None,
        model: str = None,
        history: list = None,
    ) -> str:
        """Send a chat message and get a complete response. Includes retry + auto-fallback."""
        provider = provider or settings.DEFAULT_AI_PROVIDER
        model = model or settings.DEFAULT_AI_MODEL

        # If requested provider unavailable or failed, find fallback
        if provider not in self.providers or self._health_status.get(provider) == "failed":
            fallback = self._get_fallback_provider(provider)
            if fallback:
                log.warning(f"Provider '{provider}' unavailable, using fallback: {fallback}")
                provider = fallback
            elif self.providers:
                provider = list(self.providers.keys())[0]
                log.warning(f"Using first available provider: {provider}")
            else:
                log.error("No AI providers configured!")
                return (
                    "Sir, I don't have an AI brain configured yet. "
                    "Please add your GEMINI_API_KEY to the .env file. "
                    "Get a free key at https://aistudio.google.com/apikey — "
                    "Basic commands like 'open chrome', 'volume up', 'take screenshot' still work."
                )

        try:
            async def _do_chat():
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

            return await self._retry_with_backoff(provider, _do_chat)

        except Exception as e:
            log.error(f"All retries failed for {provider}: {e}")

            # Try fallback provider
            fallback = self._get_fallback_provider(provider)
            if fallback:
                log.info(f"Attempting fallback to {fallback}")
                try:
                    if fallback == "openai":
                        return await self._chat_openai(message, system_prompt, None, history)
                    elif fallback == "anthropic":
                        return await self._chat_anthropic(message, system_prompt, None, history)
                    elif fallback == "gemini":
                        return await self._chat_gemini(message, system_prompt, None, history)
                    elif fallback == "ollama":
                        return await self._chat_ollama(message, system_prompt, None, history)
                except Exception as e2:
                    log.error(f"Fallback provider {fallback} also failed: {e2}")

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
            self._consecutive_failures[provider] = self._consecutive_failures.get(provider, 0) + 1
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

    # ─── Gemini (New google-genai SDK) ────────────────────────────────

    async def _chat_gemini(self, message, system_prompt, model, history):
        model_name = model or "gemini-2.5-flash"

        # New google-genai Client API (preferred)
        if self._gemini_client:
            from google.genai import types
            contents = []
            if history:
                for h in history[-10:]:
                    role = "user" if h["role"] == "user" else "model"
                    contents.append(types.Content(role=role, parts=[types.Part(text=h["content"])]))
            contents.append(types.Content(role="user", parts=[types.Part(text=message)]))

            config = types.GenerateContentConfig(
                system_instruction=system_prompt or "You are J.A.R.V.I.S, an advanced AI assistant.",
                max_output_tokens=2048,
            )
            response = await asyncio.to_thread(
                self._gemini_client.models.generate_content,
                model=model_name,
                contents=contents,
                config=config,
            )
            return response.text

        # Legacy google.generativeai API
        genai = self.providers["gemini"]
        gen_model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system_prompt or "You are J.A.R.V.I.S, an advanced AI assistant.",
        )
        chat = gen_model.start_chat(history=self._build_gemini_history(history))
        response = await asyncio.to_thread(chat.send_message, message)
        return response.text

    async def _stream_gemini(self, message, system_prompt, model, history):
        model_name = model or "gemini-2.5-flash"

        # New google-genai Client API
        if self._gemini_client:
            from google.genai import types
            contents = []
            if history:
                for h in history[-10:]:
                    role = "user" if h["role"] == "user" else "model"
                    contents.append(types.Content(role=role, parts=[types.Part(text=h["content"])]))
            contents.append(types.Content(role="user", parts=[types.Part(text=message)]))

            config = types.GenerateContentConfig(
                system_instruction=system_prompt or "You are J.A.R.V.I.S, an advanced AI assistant.",
                max_output_tokens=2048,
            )
            response = await asyncio.to_thread(
                self._gemini_client.models.generate_content,
                model=model_name,
                contents=contents,
                config=config,
            )
            yield response.text
            return

        # Legacy google.generativeai API
        genai = self.providers["gemini"]
        gen_model = genai.GenerativeModel(
            model_name=model_name,
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
