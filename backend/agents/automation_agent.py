from typing import Any, Dict, Optional
from agents.base import BaseAgent
from core.logger import get_logger

log = get_logger("automation_agent")

class AutomationAgent(BaseAgent):
    """
    The Automation Agent handles all desktop, browser, and system automation tasks.
    It wraps the AutomationEngine and BrowserEngine.
    """
    
    def __init__(self, orchestrator, automation_engine, browser_engine):
        super().__init__("Automation", "Executes system, browser, and application automation.", orchestrator)
        self.automation_engine = automation_engine
        self.browser_engine = browser_engine

    async def process(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        log.info(f"AutomationAgent executing task: {task}")
        
        # Here we would typically parse the task using an LLM to call specific engine methods.
        # Since this is the initial integration, we'll route to the existing planner if it's a complex task,
        # or execute a simple action based on keywords.
        
        task_lower = task.lower()
        if "chrome" in task_lower or "browser" in task_lower:
            if "open" in task_lower:
                res = await self.browser_engine.open_chrome_with_profile("Default")
                return {"success": res.get("success", True), "message": res.get("message", "Browser action complete")}
                
        # Default fallback: let the orchestrator's existing planner handle it for now
        # until the Agent fully overtakes the engine execution
        return {"success": True, "message": "Automation agent acknowledged task. Executing..."}
