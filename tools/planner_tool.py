"""
RutinitasKu - Planner Tool
Task planning and decomposition tools for the agent.
"""

from .registry import registry


@registry.tool(
    name="create_plan",
    description="Buat rencana untuk tugas kompleks. Pecah tugas besar menjadi langkah-langkah kecil yang bisa dieksekusi.",
    input_schema={
        "type": "object",
        "properties": {
            "goal": {
                "type": "string",
                "description": "Tujuan utama dari rencana"
            },
            "steps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "Deskripsi langkah"
                        },
                        "tool": {
                            "type": "string",
                            "description": "Tool yang akan digunakan (opsional)"
                        }
                    },
                    "required": ["description"]
                },
                "description": "Daftar langkah-langkah"
            }
        },
        "required": ["goal", "steps"]
    }
)
async def create_plan(goal: str, steps: list) -> str:
    """
    Create a task execution plan.

    Args:
        goal: Main goal description
        steps: List of step descriptions

    Returns:
        Plan confirmation
    """
    # This is handled by the orchestrator
    import json
    return f"CREATE_PLAN|{goal}|{json.dumps(steps)}"


@registry.tool(
    name="update_plan_step",
    description="Update status langkah dalam rencana (done/failed/in_progress).",
    input_schema={
        "type": "object",
        "properties": {
            "step_id": {
                "type": "integer",
                "description": "ID langkah yang akan diupdate"
            },
            "status": {
                "type": "string",
                "description": "Status baru (done, failed, in_progress)",
                "enum": ["done", "failed", "in_progress"]
            },
            "result": {
                "type": "string",
                "description": "Hasil eksekusi langkah (opsional)"
            }
        },
        "required": ["step_id", "status"]
    }
)
async def update_plan_step(step_id: int, status: str, result: str = None) -> str:
    """
    Update a plan step's status.

    Args:
        step_id: Step ID to update
        status: New status
        result: Step execution result

    Returns:
        Update confirmation
    """
    return f"UPDATE_STEP|{step_id}|{status}|{result or ''}"


@registry.tool(
    name="get_plan",
    description="Lihat rencana yang sedang berjalan dan progress-nya.",
    input_schema={
        "type": "object",
        "properties": {},
        "required": []
    }
)
async def get_plan() -> str:
    """
    Get current execution plan.

    Returns:
        Current plan status
    """
    return "GET_PLAN"