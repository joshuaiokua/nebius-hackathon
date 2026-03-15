"""Multi-agent orchestrator — runs SCOUT, PLANNER, SAFETY in parallel loops."""

import asyncio
import base64
import json
import random

from agents.scout import ScoutAgent
from agents.planner import PlannerAgent
from agents.safety import SafetyAgent

# ANSI colors for demo output
C_SCOUT = "\033[96m"   # cyan
C_PLAN = "\033[93m"    # yellow
C_SAFE = "\033[92m"    # green
C_ORCH = "\033[95m"    # magenta
C_ERR = "\033[91m"     # red
C_RST = "\033[0m"      # reset


def _label(color: str, name: str, msg: str) -> None:
    print(f"{color}[{name}]{C_RST} {msg}")


class AsyncOrchestrator:
    """Runs SCOUT → PLANNER → SAFETY in an async loop with re-planning on veto."""

    def __init__(self) -> None:
        self.scout = ScoutAgent()
        self.planner = PlannerAgent()
        self.safety = SafetyAgent()

    # ------------------------------------------------------------------
    # Mock simulation state
    # ------------------------------------------------------------------
    @staticmethod
    def mock_sim_state() -> dict:
        """Return fake robot state JSON simulating a Unitree G1 in MuJoCo."""
        return {
            "time": round(random.uniform(0, 120), 2),
            "position": [round(random.uniform(-2, 2), 3) for _ in range(3)],
            "orientation": [round(random.uniform(-1, 1), 3) for _ in range(4)],
            "velocity": [round(random.uniform(-0.5, 0.5), 3) for _ in range(3)],
            "angular_vel": [round(random.uniform(-0.2, 0.2), 3) for _ in range(3)],
            "stability": round(random.uniform(0.7, 1.0), 2),
            "battery": round(random.uniform(60, 100), 1),
            "joint_positions": [round(random.uniform(-1, 1), 2) for _ in range(29)],
            "camera_frame": base64.b64encode(b"MOCK_FRAME_DATA").decode(),
        }

    # ------------------------------------------------------------------
    # Single iteration
    # ------------------------------------------------------------------
    async def run_loop(self, task: str, iteration: int = 0) -> dict:
        """Run one SCOUT → PLANNER → SAFETY iteration.

        Returns a result dict with keys: action, status, scout/planner/safety outputs.
        """
        state = self.mock_sim_state()
        camera_b64 = state.pop("camera_frame")

        # --- SCOUT (analyze frame) ---
        _label(C_SCOUT, "SCOUT", "Analyzing camera frame...")
        scene_description = await self.scout.analyze_frame(camera_b64)
        _label(C_SCOUT, "SCOUT", f"Scene: {scene_description[:120]}...")

        # --- PLANNER (generate plan from scene + state + task) ---
        _label(C_PLAN, "PLANNER", "Generating action plan...")
        plan = await self.planner.plan(scene_description, state, task)
        _label(C_PLAN, "PLANNER", f"Plan: {json.dumps(plan, indent=2)[:200]}...")

        # --- SAFETY (evaluate proposed plan) ---
        _label(C_SAFE, "SAFETY", "Evaluating plan for risks...")
        # Run safety evaluation concurrently with a fresh scout pre-fetch for next iter
        safety_result = await self.safety.evaluate(plan, state)
        _label(C_SAFE, "SAFETY", f"Risk: {safety_result.get('risk_level', '?')} | Approved: {safety_result.get('approved', '?')}")

        risk = safety_result.get("risk_level", "low").lower()

        # --- DECISION ---
        if risk in ("low", "medium") and safety_result.get("approved", False):
            _label(C_ORCH, "ORCHESTRATOR", "Action APPROVED — executing plan")
            return {
                "status": "execute",
                "iteration": iteration,
                "scene": scene_description,
                "plan": plan,
                "safety": safety_result,
            }

        # Safety vetoed — re-plan with feedback
        _label(C_ERR, "ORCHESTRATOR", f"Action VETOED (risk={risk}). Re-planning with safety feedback...")
        concerns = safety_result.get("concerns", [])
        feedback_task = (
            f"{task}\n\nSAFETY FEEDBACK — previous plan was rejected.\n"
            f"Concerns: {json.dumps(concerns)}\n"
            f"Mitigations suggested: {json.dumps(safety_result.get('mitigations', []))}\n"
            f"Revise the plan to address these concerns."
        )
        revised_plan = await self.planner.plan(scene_description, state, feedback_task)
        _label(C_PLAN, "PLANNER", f"Revised plan: {json.dumps(revised_plan, indent=2)[:200]}...")

        return {
            "status": "revised",
            "iteration": iteration,
            "scene": scene_description,
            "original_plan": plan,
            "revised_plan": revised_plan,
            "safety": safety_result,
        }

    # ------------------------------------------------------------------
    # Demo runner
    # ------------------------------------------------------------------
    async def run_demo(self, task: str, iterations: int = 5) -> list[dict]:
        """Run multiple iterations of the orchestration loop."""
        _label(C_ORCH, "ORCHESTRATOR", f"Starting demo — task: {task!r}")
        _label(C_ORCH, "ORCHESTRATOR", f"Running {iterations} iterations\n")

        results = []
        for i in range(iterations):
            _label(C_ORCH, "ORCHESTRATOR", f"{'='*60}")
            _label(C_ORCH, "ORCHESTRATOR", f"Iteration {i + 1}/{iterations}")
            _label(C_ORCH, "ORCHESTRATOR", f"{'='*60}")

            result = await self.run_loop(task, iteration=i)
            results.append(result)

            _label(C_ORCH, "ORCHESTRATOR", f"Result: {result['status']}\n")

        # Summary
        executed = sum(1 for r in results if r["status"] == "execute")
        revised = sum(1 for r in results if r["status"] == "revised")
        _label(C_ORCH, "ORCHESTRATOR", f"Demo complete — {executed} executed, {revised} revised")

        return results


if __name__ == "__main__":

    async def main() -> None:
        orch = AsyncOrchestrator()
        await orch.run_demo("Walk to the red box and inspect it")

    asyncio.run(main())
