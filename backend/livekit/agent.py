"""
J.A.R.V.I.S LiveKit Voice Agent
Real-time voice AI using LiveKit Agents SDK.

This module creates a production-grade LiveKit Agent with:
- Silero VAD for voice activity detection
- Deepgram Nova-3 for STT (or configurable)
- Google Gemini / OpenAI for LLM
- Edge-TTS / Cartesia for TTS
- Enhanced noise cancellation

Usage:
  python -m livekit.agent dev    (development mode)
  python -m livekit.agent start  (production mode)

Requires:
  - LiveKit Cloud account (https://cloud.livekit.io)
  - LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET in .env
"""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

from core.logger import get_logger
log = get_logger("livekit-agent")


# ─── JARVIS Agent Definition ─────────────────────────────────────────

JARVIS_INSTRUCTIONS = """You are J.A.R.V.I.S (Just A Rather Very Intelligent System),
an advanced AI assistant modeled after Tony Stark's AI from Iron Man.

Personality:
- You address the user as "Sir" or by their name (Hari)
- You are loyal, precise, witty, and proactive
- You speak concisely — no long paragraphs in voice conversation
- You are curious and have a dry sense of humor
- You do NOT use emojis, asterisks, or markdown formatting in speech
- You keep responses under 2-3 sentences for voice interaction
- You sound confident and professional, like a trusted advisor

Capabilities:
- You can control the user's Windows PC (open apps, manage files, control volume)
- You can search the web, play music, set reminders
- You provide system information and monitor performance
- You remember conversation context and user preferences

Always respond naturally and concisely — this is a voice conversation, not text chat."""


def create_agent():
    """Create and return the JARVIS LiveKit agent server."""
    try:
        from livekit import agents
        from livekit.agents import AgentServer, AgentSession, Agent, room_io
    except ImportError:
        log.error(
            "LiveKit Agents SDK not installed! Run:\n"
            "  pip install 'livekit-agents[silero,turn-detector]>=1.0'\n"
            "  pip install livekit-plugins-noise-cancellation"
        )
        return None

    class JarvisAgent(Agent):
        def __init__(self) -> None:
            super().__init__(instructions=JARVIS_INSTRUCTIONS)

    server = AgentServer()

    @server.rtc_session(agent_name="jarvis")
    async def jarvis_session(ctx: agents.JobContext):
        """Main JARVIS voice agent session."""
        
        # ─── Configure STT/LLM/TTS pipeline ──────────────────────
        session_kwargs = {}
        
        # Try LiveKit Inference (recommended for LiveKit Cloud)
        try:
            from livekit.agents import inference
            session_kwargs["stt"] = inference.STT(
                model="deepgram/nova-3",
                language="multi",
            )
            session_kwargs["llm"] = inference.LLM(
                model="google/gemini-2.0-flash",
            )
            session_kwargs["tts"] = inference.TTS(
                model="cartesia/sonic-3",
                voice="9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
            )
            log.info("Using LiveKit Inference pipeline")
        except (ImportError, Exception) as e:
            log.warning(f"LiveKit Inference not available ({e}), using plugins")
            
            # Fallback: Use individual plugins
            try:
                from livekit.plugins import openai as lk_openai
                session_kwargs["llm"] = lk_openai.realtime.RealtimeModel(
                    voice="coral",
                )
                log.info("Using OpenAI Realtime Model")
            except (ImportError, Exception):
                log.error("No LLM plugin available for LiveKit")
                return

        # ─── VAD (Voice Activity Detection) ───────────────────────
        try:
            from livekit.plugins import silero
            session_kwargs["vad"] = silero.VAD.load()
            log.info("Silero VAD loaded")
        except ImportError:
            log.warning("Silero VAD not available")

        # ─── Turn Detection ───────────────────────────────────────
        try:
            from livekit.agents import TurnHandlingOptions
            from livekit.plugins.turn_detector.multilingual import MultilingualModel
            session_kwargs["turn_handling"] = TurnHandlingOptions(
                turn_detection=MultilingualModel(),
            )
            log.info("Multilingual turn detector loaded")
        except ImportError:
            log.debug("Multilingual turn detector not available")

        # ─── Create and start session ─────────────────────────────
        session = AgentSession(**session_kwargs)

        # Room options with noise cancellation
        room_options_kwargs = {}
        try:
            from livekit.plugins import ai_coustics
            room_options_kwargs["audio_input"] = room_io.AudioInputOptions(
                noise_cancellation=ai_coustics.audio_enhancement(
                    model=ai_coustics.EnhancerModel.QUAIL_VF_S
                ),
            )
            log.info("AI noise cancellation enabled")
        except ImportError:
            log.debug("ai_coustics not available — using raw audio")

        await session.start(
            room=ctx.room,
            agent=JarvisAgent(),
            room_options=room_io.RoomOptions(**room_options_kwargs),
        )

        # Generate initial greeting
        await session.generate_reply(
            instructions="Greet the user. Say something like: 'Good evening Sir, J.A.R.V.I.S online and ready. How may I assist you today?'"
        )

    return server


# ─── CLI Entry Point ──────────────────────────────────────────────────

if __name__ == "__main__":
    # Check required environment variables
    required_vars = ["LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET"]
    missing = [v for v in required_vars if not os.getenv(v)]
    
    if missing:
        print("\n" + "=" * 60)
        print("  J.A.R.V.I.S LiveKit Agent — Setup Required")
        print("=" * 60)
        print(f"\n  Missing environment variables: {', '.join(missing)}")
        print("\n  Steps to set up:")
        print("  1. Sign up at https://cloud.livekit.io (free)")
        print("  2. Create a project and get your credentials")
        print("  3. Add to your .env file:")
        print("     LIVEKIT_URL=wss://your-project.livekit.cloud")
        print("     LIVEKIT_API_KEY=your_api_key")
        print("     LIVEKIT_API_SECRET=your_api_secret")
        print("\n  Or use the LiveKit CLI:")
        print("     lk cloud auth")
        print("     lk agent init jarvis --template agent-starter-python")
        print("=" * 60 + "\n")
        sys.exit(1)

    server = create_agent()
    if server:
        from livekit import agents
        agents.cli.run_app(server)
    else:
        print("Failed to create LiveKit agent. Check logs for details.")
        sys.exit(1)
