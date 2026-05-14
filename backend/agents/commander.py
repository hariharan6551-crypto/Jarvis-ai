import json
from typing import Any, Dict, Optional
from agents.base import BaseAgent
from core.logger import get_logger

log = get_logger("commander_agent")

class CommanderAgent(BaseAgent):
    """
    The Commander Agent is the primary brain of the Multi-Agent System.
    It receives the high-level user command, breaks it down into sub-tasks,
    and delegates them to the specialized agents.
    """
    
    def __init__(self, orchestrator, ai_provider):
        super().__init__("Commander", "Breaks down goals and routes tasks to specialized agents.", orchestrator)
        self.ai_provider = ai_provider
        self.system_prompt = """You are the Commander Agent of J.A.R.V.I.S.
Your job is to analyze the user's request and determine which specialized agent should handle it.
Available Agents:
- Automation: System, browser, file, and app control.
- Vision: Screen reading (OCR) and visual understanding.
- Memory: Remembering user details, preferences, and context.
- Voice: TTS and Voice related adjustments.
- Coding: Writing, executing, or debugging code.
- Research: Searching the web and summarizing information.
- Security: Permission checks and secure operations.

Reply with a JSON object containing:
- "target_agent": The name of the agent to route to.
- "task_payload": The specific instruction for that agent.
- "requires_multiple": boolean, if true, break into a list of tasks.
"""

    async def process(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        log.info(f"Commander analyzing task: {task}")
        
        # In a full implementation, we'd use the AI provider to intelligently route.
        # For now, we'll implement a basic heuristic routing to demonstrate the architecture.
        task_lower = task.lower()
        
        target_agent = "Automation"
        if "remember" in task_lower or "what did I say" in task_lower:
            target_agent = "Memory"
        elif "read screen" in task_lower or "what do you see" in task_lower or "screenshot" in task_lower:
            target_agent = "Vision"
        elif "code" in task_lower or "script" in task_lower or "python" in task_lower:
            target_agent = "Coding"
        elif "search" in task_lower or "research" in task_lower or "look up" in task_lower:
            target_agent = "Research"
        elif "voice" in task_lower or "speak" in task_lower:
            target_agent = "Voice"

        log.info(f"Commander delegating to {target_agent} Agent")
        
        # Communicate with the target agent
        result = await self.communicate(target_agent, task, context)
        
        return {
            "success": result.get("success", True),
            "delegated_to": target_agent,
            "result": result,
            "message": result.get("message", f"Task delegated to {target_agent} agent.")
        }
