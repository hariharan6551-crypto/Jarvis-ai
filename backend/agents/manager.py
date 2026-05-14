from typing import Any, Dict, Optional
from agents.base import BaseAgent
from core.logger import get_logger

log = get_logger("agent_manager")

class AgentManager:
    """
    Manages the lifecycle and communication of all J.A.R.V.I.S agents.
    """
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.agents = {}
        log.info("AgentManager initialized")
        
    def register_agent(self, agent: BaseAgent):
        """Register an agent with the manager."""
        self.agents[agent.name] = agent
        log.debug(f"Registered agent: {agent.name}")
        
    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Retrieve an agent by name."""
        return self.agents.get(name)
        
    async def route_message(self, source: str, target: str, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Route a message from one agent to another."""
        target_agent = self.get_agent(target)
        if not target_agent:
            log.error(f"Routing failed: Agent '{target}' not found (from '{source}')")
            return {"success": False, "message": f"Agent {target} not found"}
            
        log.info(f"Routing task from {source} -> {target}")
        try:
            return await target_agent.process(message, context)
        except Exception as e:
            log.error(f"Agent {target} failed to process message: {e}")
            return {"success": False, "message": f"Agent execution error: {str(e)}"}

    async def execute_task(self, command: str) -> Dict[str, Any]:
        """Entry point for executing a task via the Multi-Agent system."""
        commander = self.get_agent("Commander")
        if commander:
            return await commander.process(command)
        return {"success": False, "message": "Commander agent not available"}
