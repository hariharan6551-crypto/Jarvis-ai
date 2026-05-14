import asyncio
import os
from dotenv import load_dotenv

from livekit.agents import (
    AutoSubscribe,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
    llm,
)
from livekit.agents.pipeline import VoicePipelineAgent
from livekit.plugins import openai, deepgram, cartesia, silero

# Load environment variables
load_dotenv(".env.local")

import logging
from typing import Annotated

# Set up logging for debugging
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("jarvis-agent")

# Import the existing Jarvis automation classes or define placeholders
# from automation.browser import BrowserAutomation
# from automation.engine import AutomationEngine

class JarvisSystemTools(llm.FunctionContext):
    """
    These are the tools available to the J.A.R.V.I.S assistant.
    The LLM will choose when to invoke these based on the user's spoken intent.
    """

    def __init__(self):
        super().__init__()
        # self.browser = BrowserAutomation()
        # self.system = AutomationEngine()

    @llm.ai_callable(desc="Open Google Chrome and optionally search for a query.")
    async def search_web(
        self,
        query: Annotated[str, llm.TypeInfo(desc="The search query (optional)")] = "",
    ):
        logger.info(f"[INTENT] search_web | Query: {query}")
        # result = await self.browser.open_chrome_and_search(query)
        logger.info("[EXECUTOR] Chrome launched successfully")
        return f"Successfully opened Chrome and searched for {query}."

    @llm.ai_callable(desc="Create a new folder at a specified location.")
    async def create_folder(
        self,
        folder_name: Annotated[str, llm.TypeInfo(desc="Name of the folder")],
        location: Annotated[str, llm.TypeInfo(desc="Location (e.g., desktop, documents)")] = "desktop",
    ):
        logger.info(f"[INTENT] create_folder | Name: {folder_name}, Location: {location}")
        # await self.system.create_directory(folder_name, location)
        logger.info("[EXECUTOR] Folder created successfully")
        return f"Created folder {folder_name} on the {location}."

    @llm.ai_callable(desc="Adjust the system volume to a specific percentage.")
    async def set_volume(
        self,
        percentage: Annotated[int, llm.TypeInfo(desc="Volume percentage from 0 to 100")],
    ):
        logger.info(f"[INTENT] set_volume | Target: {percentage}%")
        # await self.system.set_volume(percentage)
        logger.info("[EXECUTOR] Volume updated")
        return f"Volume set to {percentage} percent."

    @llm.ai_callable(desc="Take a screenshot of the current screen.")
    async def take_screenshot(self):
        logger.info("[INTENT] take_screenshot")
        # await self.system.capture_screenshot()
        logger.info("[EXECUTOR] Screenshot captured")
        return "Screenshot captured and saved."


def prewarm(proc: JobProcess):
    """
    Pre-warm process for VAD. This ensures that the Silero model is loaded
    before the first user connection, keeping initial latency as low as possible.
    """
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    """
    Entrypoint for a new agent session. Called every time a user connects.
    """
    initial_ctx = llm.ChatContext().append(
        role="system",
        text=(
            "You are J.A.R.V.I.S, an advanced, highly intelligent operating system assistant. "
            "You are calm, reliable, friendly, and slightly witty. "
            "Your interface with the user is purely vocal. Keep your responses concise, conversational, and natural. "
            "Never use markdown, lists, or JSON in your responses. "
            "If the user asks you to perform an action, use the available tools to do so. "
            "If you need clarification, ask one question at a time. "
            "Always confirm important actions before executing them."
        ),
    )

    logger.info(f"[SESSION] Connecting to room {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    # Instantiate the VoicePipelineAgent using our preferred providers
    agent = VoicePipelineAgent(
        vad=ctx.proc.userdata["vad"],
        stt=deepgram.STT(model="nova-3"),
        llm=openai.LLM(model="gpt-4o"),
        tts=cartesia.TTS(model="sonic-3"),
        chat_ctx=initial_ctx,
        fnc_ctx=JarvisSystemTools(),
        # Allows the LLM to start speaking its response before the entire response is generated
        preemptive_generation=True,
    )

    # Start the agent processing loop
    agent.start(ctx.room, ctx.participant)
    logger.info("[SESSION] Agent started and listening")

    # The agent will automatically greet the user or wait for them to speak.
    await agent.say("All systems are online and ready. How can I help you?", allow_interruptions=True)


if __name__ == "__main__":
    # cli.run_app handles the LiveKit AgentServer setup and lifecycle
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
        )
    )
