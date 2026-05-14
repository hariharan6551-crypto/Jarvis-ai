import asyncio
from typing import Any, Dict, Optional
from core.logger import get_logger

log = get_logger("agents")

class BaseAgent:
    """Base class for all J.A.R.V.I.S specialized agents."""
    
    def __init__(self, name: str, description: str, orchestrator=None):
        self.name = name
        self.description = description
        self.orchestrator = orchestrator

    async def process(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a specific task. Must be implemented by subclasses."""
        raise NotImplementedError(f"Agent {self.name} must implement process()")

    async def communicate(self, target_agent: str, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send a message/task to another agent via the orchestrator."""
        if self.orchestrator:
            log.debug(f"{self.name} communicating with {target_agent}: {message[:50]}...")
            return await self.orchestrator.route_agent_message(self.name, target_agent, message, context)
        return {"success": False, "message": "No orchestrator attached for inter-agent communication"}
