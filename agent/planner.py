"""
RutinitasKu - Task Planner
Decomposes complex tasks into actionable steps.
"""

import json
import logging
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TaskStep:
    """A single step in a task plan."""
    id: int
    description: str
    tool: Optional[str] = None
    args: dict = field(default_factory=dict)
    status: str = "pending"  # pending, in_progress, done, failed
    result: Optional[str] = None


@dataclass
class TaskPlan:
    """A complete task execution plan."""
    goal: str
    steps: list[TaskStep]
    current_step: int = 0

    @property
    def is_complete(self) -> bool:
        return all(s.status in ("done", "failed") for s in self.steps)

    @property
    def current(self) -> Optional[TaskStep]:
        if self.current_step < len(self.steps):
            return self.steps[self.current_step]
        return None

    @property
    def progress(self) -> str:
        done = sum(1 for s in self.steps if s.status == "done")
        return f"{done}/{len(self.steps)}"

    def to_context(self) -> str:
        """Convert plan to context string for LLM."""
        lines = [f"📋 Rencana: {self.goal}", f"Progress: {self.progress}", ""]

        for step in self.steps:
            status_icon = {
                "pending": "⬜",
                "in_progress": "🔄",
                "done": "✅",
                "failed": "❌"
            }.get(step.status, "⬜")

            lines.append(f"{status_icon} {step.id}. {step.description}")
            if step.tool:
                lines.append(f"   Tool: {step.tool}")
            if step.result:
                lines.append(f"   Hasil: {step.result[:100]}...")

        return "\n".join(lines)


class TaskPlanner:
    """
    Plans and tracks multi-step task execution.
    Helps the agent break down complex requests.
    """

    def __init__(self):
        self._plans: dict[str, TaskPlan] = {}

    def create_plan(
        self,
        session_id: str,
        goal: str,
        steps: list[dict]
    ) -> TaskPlan:
        """
        Create a new task plan.

        Args:
            session_id: Current session ID
            goal: High-level goal description
            steps: List of step dicts with 'description' and optional 'tool', 'args'

        Returns:
            Created TaskPlan
        """
        task_steps = [
            TaskStep(
                id=i + 1,
                description=step.get("description", ""),
                tool=step.get("tool"),
                args=step.get("args", {})
            )
            for i, step in enumerate(steps)
        ]

        plan = TaskPlan(goal=goal, steps=task_steps)
        self._plans[session_id] = plan

        logger.info(f"Created plan for session {session_id}: {goal} ({len(steps)} steps)")
        return plan

    def get_plan(self, session_id: str) -> Optional[TaskPlan]:
        """Get current plan for a session."""
        return self._plans.get(session_id)

    def mark_step_done(self, session_id: str, step_id: int, result: str = None):
        """Mark a step as completed."""
        plan = self._plans.get(session_id)
        if not plan:
            return

        for step in plan.steps:
            if step.id == step_id:
                step.status = "done"
                step.result = result
                if plan.current_step == step_id - 1:
                    plan.current_step = step_id
                break

    def mark_step_failed(self, session_id: str, step_id: int, error: str = None):
        """Mark a step as failed."""
        plan = self._plans.get(session_id)
        if not plan:
            return

        for step in plan.steps:
            if step.id == step_id:
                step.status = "failed"
                step.result = error
                break

    def mark_step_in_progress(self, session_id: str, step_id: int):
        """Mark a step as in progress."""
        plan = self._plans.get(session_id)
        if not plan:
            return

        for step in plan.steps:
            if step.id == step_id:
                step.status = "in_progress"
                break

    def clear_plan(self, session_id: str):
        """Remove plan for a session."""
        self._plans.pop(session_id, None)

    def get_plan_context(self, session_id: str) -> Optional[str]:
        """Get plan as context string for LLM injection."""
        plan = self._plans.get(session_id)
        if not plan:
            return None
        return plan.to_context()


# Global planner instance
planner = TaskPlanner()