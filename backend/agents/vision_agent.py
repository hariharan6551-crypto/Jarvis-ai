from typing import Any, Dict, Optional
from agents.base import BaseAgent
from core.logger import get_logger

log = get_logger("vision_agent")

class VisionAgent(BaseAgent):
    """
    The Vision Agent handles screen reading, OCR, and visual context understanding.
    """
    
    def __init__(self, orchestrator, vision_engine):
        super().__init__("Vision", "Handles screen reading, OCR, and visual understanding.", orchestrator)
        self.vision_engine = vision_engine

    async def process(self, task: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        log.info(f"VisionAgent processing task: {task}")
        
        task_lower = task.lower()
        if "read" in task_lower or "what's on screen" in task_lower:
            result = await self.vision_engine.read_screen_text()
            return {
                "success": result.get("success", False),
                "data": result.get("text", ""),
                "message": "Screen read complete" if result.get("success") else "Failed to read screen"
            }
            
        return {"success": True, "message": "Vision task processed"}
