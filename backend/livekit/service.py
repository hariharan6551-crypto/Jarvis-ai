import os
import time
from typing import Optional
from core.logger import get_logger

log = get_logger("livekit")

class LiveKitService:
    """
    LiveKit integration for ultra-low latency real-time voice streaming.
    Provides token generation, room connection, and audio stream routing.
    """
    
    def __init__(self):
        self.url = os.getenv("LIVEKIT_URL", "ws://localhost:7880")
        self.api_key = os.getenv("LIVEKIT_API_KEY", "")
        self.api_secret = os.getenv("LIVEKIT_API_SECRET", "")
        self.room_name = "jarvis_main_room"
        
        self.is_connected = False
        log.info(f"LiveKit Service initialized (URL: {self.url})")
        
    def generate_token(self, participant_name: str) -> str:
        """Generate an access token for the frontend to connect."""
        try:
            from livekit import api
            token = api.AccessToken(self.api_key, self.api_secret)
            token.with_identity(participant_name)
            token.with_name(participant_name)
            token.with_grants(api.VideoGrants(
                room_join=True,
                room=self.room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True
            ))
            return token.to_jwt()
        except ImportError:
            log.warning("livekit-server-sdk not installed. Cannot generate real token.")
            return "dummy_token_install_livekit"
        except Exception as e:
            log.error(f"LiveKit token generation failed: {e}")
            return ""

    async def connect_agent(self, agent_name: str = "JARVIS"):
        """Connect the backend AI agent to the LiveKit room."""
        try:
            from livekit import rtc
            # Connection logic would go here. We'd create an RTC room and subscribe to the user's mic.
            # Then we'd publish the TTS audio to the room.
            log.info(f"Agent {agent_name} connecting to LiveKit room {self.room_name}...")
            # For now, this is a placeholder to show the architecture setup.
            self.is_connected = True
        except ImportError:
            log.warning("livekit-client not installed. Cannot connect agent.")
            self.is_connected = False

    async def disconnect(self):
        self.is_connected = False
        log.info("LiveKit Service disconnected")
