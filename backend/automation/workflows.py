"""
J.A.R.V.I.S Smart Workflow Engine
Multi-step automated workflows with error recovery and retry logic.
"""

import asyncio
import time
from typing import Callable, Optional
from core.logger import get_logger

log = get_logger("workflow")


class WorkflowStep:
    """A single step in a workflow."""
    def __init__(self, name: str, action: Callable, params: dict = None,
                 retry_count: int = 2, wait_before: float = 0,
                 wait_after: float = 0, critical: bool = True):
        self.name = name
        self.action = action
        self.params = params or {}
        self.retry_count = retry_count
        self.wait_before = wait_before
        self.wait_after = wait_after
        self.critical = critical
        self.result = None
        self.status = "pending"
        self.error = None
        self.attempts = 0
        self.duration_ms = 0


class Workflow:
    """A sequence of steps to execute."""
    def __init__(self, name: str):
        self.name = name
        self.steps: list[WorkflowStep] = []
        self.status = "pending"
        self.current_step = 0

    def add_step(self, step: WorkflowStep):
        self.steps.append(step)


class WorkflowEngine:
    """Executes multi-step workflows with retry and error recovery."""

    def __init__(self):
        self.workflow_history: list[dict] = []
        log.info("Workflow engine initialized")

    async def execute(self, workflow: Workflow, progress_cb=None) -> dict:
        workflow.status = "running"
        start = time.time()
        results = []
        all_ok = True

        for i, step in enumerate(workflow.steps):
            workflow.current_step = i
            step.status = "running"

            if progress_cb:
                try:
                    await progress_cb({"step": i+1, "total": len(workflow.steps), "name": step.name})
                except Exception:
                    pass

            if step.wait_before > 0:
                await asyncio.sleep(step.wait_before)

            result = await self._execute_step(step)

            if step.wait_after > 0:
                await asyncio.sleep(step.wait_after)

            results.append({"step": step.name, "status": step.status, "result": result, "attempts": step.attempts})

            if step.status == "failed":
                all_ok = False
                if step.critical:
                    workflow.status = "failed"
                    break

        total_ms = (time.time() - start) * 1000
        if workflow.status != "failed":
            workflow.status = "completed" if all_ok else "partial"

        summary = {
            "name": workflow.name, "status": workflow.status,
            "steps_total": len(workflow.steps),
            "steps_ok": sum(1 for s in workflow.steps if s.status == "success"),
            "duration_ms": round(total_ms, 2), "results": results,
        }
        self.workflow_history.append(summary)
        log.info(f"Workflow '{workflow.name}' {workflow.status} in {total_ms:.0f}ms")
        return summary

    async def _execute_step(self, step: WorkflowStep) -> dict:
        last_err = None
        for attempt in range(step.retry_count + 1):
            step.attempts = attempt + 1
            t0 = time.time()
            try:
                if asyncio.iscoroutinefunction(step.action):
                    result = await step.action(**step.params)
                else:
                    result = await asyncio.to_thread(step.action, **step.params)
                step.duration_ms = (time.time() - t0) * 1000
                step.result = result
                ok = result.get("success", True) if isinstance(result, dict) else (result is not None)
                if ok:
                    step.status = "success"
                    return result
                last_err = result.get("message", "Failed") if isinstance(result, dict) else "Failed"
            except Exception as e:
                step.duration_ms = (time.time() - t0) * 1000
                last_err = str(e)
            if attempt < step.retry_count:
                await asyncio.sleep(0.5 * (attempt + 1))

        step.status = "failed"
        step.error = last_err
        return {"success": False, "message": last_err}
