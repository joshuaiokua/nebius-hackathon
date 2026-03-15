import json

from agent.planner import nebius_llm_call


class PlannerAgent:
    """PLANNER agent — generates action plans from scene + robot state + task."""

    async def plan(self, scene_description: str, robot_state: dict, task: str) -> dict:
        """Generate an action plan for the robot.

        Args:
            scene_description: Natural language scene from SCOUT.
            robot_state: Current robot state (joint positions, battery, etc.).
            task: The high-level task to accomplish.

        Returns:
            Plan dict with steps, expected outcomes, and resource requirements.
        """
        system = (
            "You are a robot planner agent. Given a scene description, the robot's "
            "current state, and a task, produce a step-by-step action plan.\n\n"
            "Output ONLY valid JSON with this schema:\n"
            '{"steps": [{"action": "...", "params": {...}, "expected_outcome": "..."}], '
            '"estimated_duration_s": <number>, "confidence": <0.0-1.0>}'
        )
        user = (
            f"Task: {task}\n\n"
            f"Scene: {scene_description}\n\n"
            f"Robot state: {json.dumps(robot_state)}"
        )
        raw = await nebius_llm_call(system, user)
        return json.loads(raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip())
