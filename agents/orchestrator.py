"""Multi-agent orchestrator — event-driven parallel pipeline.

SCOUT runs on a timer. When it detects a scene change, PLANNER fires.
SAFETY evaluates concurrently with the next SCOUT frame analysis.
If approved, EXECUTOR sends joint commands to the sim.
"""

import asyncio
import json
import re

from agents.scout import ScoutAgent
from agents.planner import PlannerAgent
from agents.safety import SafetyAgent
from agents.executor import ExecutorAgent
from agents.sim_interface import SimInterface
from agents.scene_builder import SceneBuilder

# ANSI colors for demo output
C_SCOUT = "\033[96m"   # cyan
C_PLAN = "\033[93m"    # yellow
C_SAFE = "\033[92m"    # green
C_EXEC = "\033[94m"    # blue
C_ORCH = "\033[95m"    # magenta
C_ERR = "\033[91m"     # red
C_CMD = "\033[97m"     # white (user command)
C_RST = "\033[0m"      # reset

# Words that indicate a scene modification vs a movement command
_SCENE_KEYWORDS = re.compile(
    r"\b(build|add|place|create|scatter|put|spawn|remove|delete|insert|construct|make a wall|make a box|make a ramp|make stairs)\b",
    re.IGNORECASE,
)

SCOUT_INTERVAL_S = 0.5  # 500ms
MAX_ITERATIONS = 50


def _label(color: str, name: str, msg: str) -> None:
    print(f"{color}[{name}]{C_RST} {msg}")


class AsyncOrchestrator:
    """Event-driven orchestrator with pipeline parallelism.

    Pipeline:
        SCOUT (continuous, 500ms) ──▶ scene change? ──▶ PLANNER
        PLANNER output + SAFETY evaluate run concurrently with next SCOUT
        SAFETY approved? ──▶ EXECUTOR fires
    """

    def __init__(self, sim: SimInterface | None = None) -> None:
        self.sim = sim or SimInterface()
        self.scout = ScoutAgent()
        self.planner = PlannerAgent()
        self.safety = SafetyAgent()
        self.executor = ExecutorAgent(self.sim)
        self.scene_builder = SceneBuilder()

        # Shared state
        self._last_scene: str | None = None
        self._iteration = 0
        self._results: list[dict] = []
        self._task_complete = False

    # ------------------------------------------------------------------
    # Scene change detection
    # ------------------------------------------------------------------
    @staticmethod
    def _scene_changed(old: str | None, new: str) -> bool:
        """Detect if the scene description changed meaningfully."""
        if old is None:
            return True
        # Simple heuristic: if >30% of words differ, it's a new scene.
        old_words = set(old.lower().split())
        new_words = set(new.lower().split())
        if not old_words:
            return True
        overlap = len(old_words & new_words) / max(len(old_words), len(new_words))
        return overlap < 0.7

    # ------------------------------------------------------------------
    # Core pipeline stages
    # ------------------------------------------------------------------
    async def _scout_analyze(self) -> tuple[str, dict]:
        """Run SCOUT: get sim state + camera frame, analyze scene."""
        state, camera_b64 = await asyncio.gather(
            self.sim.get_state(),
            self.sim.get_camera_frame(),
        )
        _label(C_SCOUT, "SCOUT", "Analyzing camera frame...")
        scene = await self.scout.analyze_frame(camera_b64)
        _label(C_SCOUT, "SCOUT", f"Scene: {scene[:120]}...")
        return scene, state

    async def _plan_and_evaluate(
        self, scene: str, state: dict, task: str
    ) -> tuple[dict, dict]:
        """Run PLANNER then SAFETY+next-SCOUT concurrently (pipeline parallel)."""
        # PLANNER generates action plan
        _label(C_PLAN, "PLANNER", "Generating action plan...")
        plan = await self.planner.plan(scene, state, task)
        _label(C_PLAN, "PLANNER", f"Plan: {json.dumps(plan, indent=2)[:200]}...")

        # SAFETY evaluates concurrently with a pre-fetch of next SCOUT frame
        _label(C_SAFE, "SAFETY", "Evaluating plan for risks...")
        safety_task = self.safety.evaluate(plan, state)
        prefetch_task = self.sim.get_camera_frame()  # warm up next frame
        safety_result, _ = await asyncio.gather(safety_task, prefetch_task)

        _label(
            C_SAFE, "SAFETY",
            f"Risk: {safety_result.get('risk_level', '?')} | "
            f"Approved: {safety_result.get('approved', '?')}",
        )
        return plan, safety_result

    async def _execute_action(self, plan: dict, state: dict) -> dict | None:
        """Extract first action from plan and send to EXECUTOR."""
        steps = plan.get("steps", [])
        if not steps:
            _label(C_ERR, "EXECUTOR", "No steps in plan")
            return None

        action_name = steps[0].get("action", "stop")
        _label(C_EXEC, "EXECUTOR", f"Executing: {action_name}")
        result = await self.executor.execute(action_name, state)

        if "error" in result:
            _label(C_ERR, "EXECUTOR", f"Error: {result['error']}")
        else:
            _label(C_EXEC, "EXECUTOR", f"Action '{action_name}' sent to sim")

        return result

    async def _replan_with_feedback(
        self, scene: str, state: dict, task: str, safety_result: dict
    ) -> dict:
        """Re-plan incorporating safety feedback."""
        concerns = safety_result.get("concerns", [])
        feedback_task = (
            f"{task}\n\nSAFETY FEEDBACK — previous plan was rejected.\n"
            f"Concerns: {json.dumps(concerns)}\n"
            f"Mitigations suggested: {json.dumps(safety_result.get('mitigations', []))}\n"
            f"Revise the plan to address these concerns."
        )
        _label(C_PLAN, "PLANNER", "Re-planning with safety feedback...")
        revised = await self.planner.plan(scene, state, feedback_task)
        _label(C_PLAN, "PLANNER", f"Revised: {json.dumps(revised, indent=2)[:200]}...")
        return revised

    # ------------------------------------------------------------------
    # Scene building
    # ------------------------------------------------------------------
    async def scene_command(self, prompt: str) -> dict:
        """Generate MJCF XML from a natural language prompt and send to sim.

        Args:
            prompt: e.g. 'build a staircase of 10 steps in front of the robot'

        Returns:
            Dict with 'prompt', 'mjcf_xml', and sim 'result'.
        """
        _label(C_ORCH, "SCENE", f"Building: {prompt}")
        mjcf_xml = await self.scene_builder.build_from_prompt(prompt)
        _label(C_ORCH, "SCENE", f"Generated {len(mjcf_xml)} chars of MJCF")

        result = await self.sim.send_command("inject_scene", {
            "mjcf_xml": mjcf_xml,
        })

        return {
            "prompt": prompt,
            "mjcf_xml": mjcf_xml,
            "result": result,
        }

    # ------------------------------------------------------------------
    # Main entry point — natural language command
    # ------------------------------------------------------------------
    async def command(self, nl_input: str) -> dict:
        """Execute a natural language command end-to-end.

        This is the MAIN ENTRY POINT. Routes to scene building or movement.

        Args:
            nl_input: Raw user input, e.g. 'walk forward 2 meters',
                      'build a wall and walk around it', 'wave at me'.

        Returns:
            Dict with command type, agent outputs, and results.
        """
        _label(C_CMD, "COMMAND", nl_input)

        # Check if this is a scene modification
        if _SCENE_KEYWORDS.search(nl_input):
            return await self._handle_scene_and_move(nl_input)

        # It's a movement command — run through the pipeline
        return await self._handle_movement(nl_input)

    async def _handle_scene_and_move(self, nl_input: str) -> dict:
        """Handle commands that mix scene building and movement.

        Splits compound commands (e.g. 'build a wall and walk around it')
        into scene + movement parts.
        """
        results = {"type": "scene_and_move", "input": nl_input, "steps": []}

        # Check for compound command with 'and' or 'then'
        parts = re.split(r"\band\b|\bthen\b", nl_input, maxsplit=1)
        scene_part = parts[0].strip()
        move_part = parts[1].strip() if len(parts) > 1 else None

        # Build the scene
        _label(C_ORCH, "ORCHESTRATOR", f"Scene modification detected")
        scene_result = await self.scene_command(scene_part)
        results["steps"].append({"agent": "SCENE_BUILDER", "result": scene_result})

        # If there's a movement part, execute it
        if move_part:
            _label(C_ORCH, "ORCHESTRATOR", f"Follow-up movement: {move_part}")
            move_result = await self._handle_movement(move_part)
            results["steps"].append({"agent": "MOVEMENT", "result": move_result})

        return results

    async def _handle_movement(self, nl_input: str) -> dict:
        """Handle a movement command through PLANNER → SAFETY → EXECUTOR."""
        state = await self.sim.get_state()

        # Get scene context from SCOUT
        _label(C_SCOUT, "SCOUT", "Getting scene context...")
        camera_b64 = await self.sim.get_camera_frame()
        scene = await self.scout.analyze_frame(camera_b64)
        _label(C_SCOUT, "SCOUT", f"Scene: {scene[:100]}...")

        # PLANNER generates a plan from the NL input
        _label(C_PLAN, "PLANNER", "Planning...")
        plan = await self.planner.plan(scene, state, nl_input)
        _label(C_PLAN, "PLANNER", f"Plan: {json.dumps(plan, indent=2)[:200]}...")

        # SAFETY checks the plan
        _label(C_SAFE, "SAFETY", "Evaluating...")
        safety_result = await self.safety.evaluate(plan, state)
        risk = safety_result.get("risk_level", "low").lower()
        approved = safety_result.get("approved", False)
        _label(C_SAFE, "SAFETY", f"Risk: {risk} | Approved: {approved}")

        if risk not in ("low", "medium") or not approved:
            _label(C_ERR, "SAFETY", f"VETOED — {safety_result.get('concerns', [])}")
            # Re-plan with safety feedback
            revised = await self._replan_with_feedback(scene, state, nl_input, safety_result)
            # Re-evaluate revised plan
            safety_result = await self.safety.evaluate(revised, state)
            approved = safety_result.get("approved", False)
            if not approved:
                return {
                    "type": "movement",
                    "input": nl_input,
                    "status": "vetoed",
                    "safety": safety_result,
                    "plan": revised,
                }
            plan = revised

        # EXECUTOR — execute all steps in the plan
        _label(C_ORCH, "ORCHESTRATOR", "APPROVED — executing")
        exec_results = []
        for step in plan.get("steps", []):
            action = step.get("action", nl_input)
            _label(C_EXEC, "EXECUTOR", f"Executing: {action}")
            result = await self.executor.execute(action, state)
            exec_results.append(result)
            if "error" in result:
                _label(C_ERR, "EXECUTOR", f"Error: {result['error']}")
            else:
                source = result.get("source", "?")
                _label(C_EXEC, "EXECUTOR", f"Done ({source})")
            # Update state after each step
            state = await self.sim.get_state()

        _label(C_ORCH, "ORCHESTRATOR", "Command complete")
        return {
            "type": "movement",
            "input": nl_input,
            "status": "executed",
            "plan": plan,
            "safety": safety_result,
            "executions": exec_results,
        }

    # ------------------------------------------------------------------
    # Event-driven loop
    # ------------------------------------------------------------------
    async def run(self, task: str, max_iterations: int = MAX_ITERATIONS) -> list[dict]:
        """Run the event-driven orchestration loop.

        SCOUT fires every SCOUT_INTERVAL_S. On scene change, PLANNER and
        SAFETY run. If approved, EXECUTOR fires. Loop until task_complete
        or max_iterations reached.
        """
        _label(C_ORCH, "ORCHESTRATOR", f"Starting — task: {task!r}")
        _label(C_ORCH, "ORCHESTRATOR", f"Max iterations: {max_iterations}, "
               f"SCOUT interval: {SCOUT_INTERVAL_S}s\n")

        self._iteration = 0
        self._results = []
        self._task_complete = False

        while self._iteration < max_iterations and not self._task_complete:
            self._iteration += 1
            _label(C_ORCH, "ORCHESTRATOR", f"{'='*50}")
            _label(C_ORCH, "ORCHESTRATOR", f"Tick {self._iteration}/{max_iterations}")

            # --- SCOUT (continuous) ---
            scene, state = await self._scout_analyze()

            if not self._scene_changed(self._last_scene, scene):
                _label(C_SCOUT, "SCOUT", "No significant scene change — waiting...")
                self._last_scene = scene
                await asyncio.sleep(SCOUT_INTERVAL_S)
                continue

            self._last_scene = scene

            # --- PLANNER + SAFETY (pipeline parallel) ---
            plan, safety_result = await self._plan_and_evaluate(scene, state, task)

            risk = safety_result.get("risk_level", "low").lower()
            approved = safety_result.get("approved", False)

            if risk in ("low", "medium") and approved:
                # --- EXECUTOR ---
                _label(C_ORCH, "ORCHESTRATOR", "Action APPROVED")
                exec_result = await self._execute_action(plan, state)

                self._results.append({
                    "status": "executed",
                    "iteration": self._iteration,
                    "scene": scene,
                    "plan": plan,
                    "safety": safety_result,
                    "execution": exec_result,
                })
            else:
                # --- VETO: re-plan ---
                _label(C_ERR, "ORCHESTRATOR",
                       f"VETOED (risk={risk}). Re-planning...")
                revised = await self._replan_with_feedback(
                    scene, state, task, safety_result
                )
                self._results.append({
                    "status": "revised",
                    "iteration": self._iteration,
                    "scene": scene,
                    "original_plan": plan,
                    "revised_plan": revised,
                    "safety": safety_result,
                })

            _label(C_ORCH, "ORCHESTRATOR",
                   f"Result: {self._results[-1]['status']}\n")

            # Pace the loop
            await asyncio.sleep(SCOUT_INTERVAL_S)

        # --- Summary ---
        executed = sum(1 for r in self._results if r["status"] == "executed")
        revised = sum(1 for r in self._results if r["status"] == "revised")
        _label(C_ORCH, "ORCHESTRATOR",
               f"Done — {executed} executed, {revised} revised, "
               f"{self._iteration} ticks")
        return self._results

    # ------------------------------------------------------------------
    # Legacy demo runner (kept for backward compat)
    # ------------------------------------------------------------------
    async def run_demo(self, task: str, iterations: int = 5) -> list[dict]:
        """Run the event loop with a fixed iteration cap."""
        return await self.run(task, max_iterations=iterations)


if __name__ == "__main__":

    async def main() -> None:
        sim = SimInterface()
        orch = AsyncOrchestrator(sim=sim)
        await orch.run("Walk to the red box and inspect it", max_iterations=5)

    asyncio.run(main())
