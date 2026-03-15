import json

from agent.planner import nebius_llm_call


class SafetyAgent:
    """SAFETY agent — evaluates proposed actions for risk before execution."""

    async def evaluate(self, proposed_action: dict, robot_state: dict) -> dict:
        """Evaluate a proposed action for safety risks.

        Args:
            proposed_action: The action the planner wants to execute.
            robot_state: Current robot state (joint positions, battery, etc.).

        Returns:
            Risk assessment JSON with risk_level, concerns, and approved flag.
        """
        system = (
            "You are a robot safety agent. Evaluate the proposed action for risks "
            "including collisions, joint limit violations, balance loss, excessive "
            "force, and energy constraints.\n\n"
            "Output ONLY valid JSON with this schema:\n"
            '{"approved": <bool>, "risk_level": "low"|"medium"|"high"|"critical", '
            '"concerns": ["..."], "mitigations": ["..."]}'
        )
        user = (
            f"Proposed action: {json.dumps(proposed_action)}\n\n"
            f"Robot state: {json.dumps(robot_state)}"
        )
        raw = await nebius_llm_call(system, user)
        return json.loads(raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip())
