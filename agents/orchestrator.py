"""Multi-agent orchestrator — event-driven parallel pipeline.

SCOUT runs on a timer. When it detects a scene change, PLANNER fires.
SAFETY evaluates concurrently with the next SCOUT frame analysis.
If approved, EXECUTOR sends joint commands to the sim.
"""

import asyncio
import json
import re
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

from agents.scout import ScoutAgent
from agents.planner import PlannerAgent
from agents.safety import SafetyAgent
from agents.executor import ExecutorAgent
from agents.sim_interface import SimInterface
from agents.scene_builder import SceneBuilder

# Self-expanding loop imports
from agent.planner import detect_gaps, generate_skill_file, ingest_skill
from agent.catalog import search_and_select_module
from schemas import CapabilityGap, RobotProfile

SKILLS_DIR = Path("skills")

# Type for event callbacks: async (agent_name, message, metadata) -> None
EventCallback = Callable[[str, str, dict[str, Any]], Coroutine[Any, Any, None]]

# ANSI colors for demo output
C_SCOUT = "\033[96m"   # cyan
C_PLAN = "\033[93m"    # yellow
C_SAFE = "\033[92m"    # green
C_EXEC = "\033[94m"    # blue
C_ORCH = "\033[95m"    # magenta
C_ERR = "\033[91m"     # red
C_CMD = "\033[97m"     # white (user command)
C_EXPAND = "\033[33m"  # orange/dark yellow — self-expanding loop
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
        self.profile = RobotProfile()

        # Shared state
        self._last_scene: str | None = None
        self._iteration = 0
        self._results: list[dict] = []
        self._task_complete = False

        # Event callback — set per-command via command(..., on_event=...)
        self._on_event: EventCallback | None = None

    async def _emit(self, agent: str, message: str, metadata: dict | None = None) -> None:
        """Log to console AND fire the event callback if set."""
        color_map = {
            "SCOUT": C_SCOUT, "PLANNER": C_PLAN, "SAFETY": C_SAFE,
            "EXECUTOR": C_EXEC, "ORCHESTRATOR": C_ORCH, "SCENE": C_ORCH,
            "COMMAND": C_CMD, "ERROR": C_ERR, "EXPAND": C_EXPAND,
        }
        _label(color_map.get(agent, C_RST), agent, message)
        if self._on_event:
            await self._on_event(agent, message, metadata or {})

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
        await self._emit("SCOUT", "Analyzing camera frame...")
        scene = await self.scout.analyze_frame(camera_b64)
        await self._emit("SCOUT", f"Scene: {scene[:120]}...")
        return scene, state

    async def _plan_and_evaluate(
        self, scene: str, state: dict, task: str
    ) -> tuple[dict, dict]:
        """Run PLANNER then SAFETY+next-SCOUT concurrently (pipeline parallel)."""
        # PLANNER generates action plan
        await self._emit("PLANNER", "Generating action plan...")
        plan = await self.planner.plan(scene, state, task)
        await self._emit("PLANNER", f"Plan: {json.dumps(plan, indent=2)[:200]}...", {"plan": plan})

        # SAFETY evaluates concurrently with a pre-fetch of next SCOUT frame
        await self._emit("SAFETY", "Evaluating plan for risks...")
        safety_task = self.safety.evaluate(plan, state)
        prefetch_task = self.sim.get_camera_frame()  # warm up next frame
        safety_result, _ = await asyncio.gather(safety_task, prefetch_task)

        await self._emit(
            "SAFETY",
            f"Risk: {safety_result.get('risk_level', '?')} | "
            f"Approved: {safety_result.get('approved', '?')}",
            {"safety": safety_result},
        )
        return plan, safety_result

    async def _execute_action(self, plan: dict, state: dict) -> dict | None:
        """Extract first action from plan and send to EXECUTOR."""
        steps = plan.get("steps", [])
        if not steps:
            await self._emit("ERROR", "No steps in plan")
            return None

        action_name = steps[0].get("action", "stop")
        await self._emit("EXECUTOR", f"Executing: {action_name}")
        result = await self.executor.execute(action_name, state)

        if "error" in result:
            await self._emit("ERROR", f"Execution error: {result['error']}")
        else:
            await self._emit("EXECUTOR", f"Action '{action_name}' sent to sim")

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
        await self._emit("PLANNER", "Re-planning with safety feedback...")
        revised = await self.planner.plan(scene, state, feedback_task)
        await self._emit("PLANNER", f"Revised: {json.dumps(revised, indent=2)[:200]}...", {"plan": revised})
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
        await self._emit("SCENE", f"Building: {prompt}")
        mjcf_xml = await self.scene_builder.build_from_prompt(prompt)
        await self._emit("SCENE", f"Generated {len(mjcf_xml)} chars of MJCF")

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
    async def command(
        self, nl_input: str, on_event: EventCallback | None = None
    ) -> dict:
        """Execute a natural language command end-to-end.

        This is the MAIN ENTRY POINT. Routes to scene building or movement.

        Args:
            nl_input: Raw user input, e.g. 'walk forward 2 meters',
                      'build a wall and walk around it', 'wave at me'.
            on_event: Optional async callback (agent_name, message, metadata)
                      called each time an agent produces output. Useful for
                      streaming updates to SSE clients.

        Returns:
            Dict with command type, agent outputs, and results.
        """
        self._on_event = on_event
        try:
            await self._emit("COMMAND", nl_input)

            # Check if this is a scene modification
            if _SCENE_KEYWORDS.search(nl_input):
                return await self._handle_scene_and_move(nl_input)

            # It's a movement command — run through the pipeline
            return await self._handle_movement(nl_input)
        finally:
            self._on_event = None

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
        await self._emit("ORCHESTRATOR", "Scene modification detected")
        scene_result = await self.scene_command(scene_part)
        results["steps"].append({"agent": "SCENE_BUILDER", "result": scene_result})

        # If there's a movement part, execute it
        if move_part:
            await self._emit("ORCHESTRATOR", f"Follow-up movement: {move_part}")
            move_result = await self._handle_movement(move_part)
            results["steps"].append({"agent": "MOVEMENT", "result": move_result})

        return results

    # ------------------------------------------------------------------
    # Self-expanding loop — detect gaps, buy hardware, generate skills
    # ------------------------------------------------------------------
    def _plan_has_capability_gap(self, plan: dict) -> bool:
        """Check if a PLANNER response indicates missing capabilities."""
        confidence = plan.get("confidence", 1.0)
        capabilities_needed = plan.get("capabilities_needed", [])
        return confidence < 0.3 or bool(capabilities_needed)

    async def _handle_capability_gap(self, plan: dict) -> dict:
        """Run the self-expanding loop: detect gaps → search → buy → generate → install.

        Returns:
            Dict with expansion results including filled gaps and updated capabilities.
        """
        SKILLS_DIR.mkdir(exist_ok=True)
        capabilities_needed = plan.get("capabilities_needed", [])
        confidence = plan.get("confidence", 1.0)

        await self._emit("EXPAND", f"Capability gap detected! confidence={confidence:.1f}, "
                         f"needed={capabilities_needed}")
        await self._emit("EXPAND", "Starting self-expanding loop...")

        # Step 1: Detect gaps via the planner LLM
        await self._emit("EXPAND", "Analyzing capability gaps...")
        # Build a pseudo-task from the capabilities_needed list
        gap_description = ", ".join(capabilities_needed) if capabilities_needed else "unknown"
        try:
            result = await detect_gaps(
                f"Robot needs these capabilities: {gap_description}",
                self.profile,
            )
        except Exception as e:
            await self._emit("ERROR", f"Gap detection failed: {e}")
            return {"status": "gap_detection_failed", "error": str(e)}

        if result["status"] == "executable":
            await self._emit("EXPAND", "Robot already has the needed capabilities!")
            return {"status": "already_capable", "result": result}

        gaps: list[CapabilityGap] = result["gaps"]
        await self._emit("EXPAND", f"Found {len(gaps)} gap(s): "
                         f"{[g.need for g in gaps]}")

        # Step 2-4: For each gap — search catalog, select module, generate skill, install
        filled = []
        for i, gap in enumerate(gaps, 1):
            await self._emit("EXPAND", f"--- Gap {i}/{len(gaps)}: {gap.need} ({gap.priority}) ---")
            await self._emit("EXPAND", f"Reason: {gap.reason}")

            # Search & select hardware
            await self._emit("EXPAND", f"Searching catalogs for '{gap.hardware_category}'...")
            try:
                module = await search_and_select_module(gap, self.profile)
            except Exception as e:
                await self._emit("ERROR", f"Catalog search failed for {gap.need}: {e}")
                continue
            await self._emit("EXPAND", f"Selected: {module.name} (${module.price:.2f})")
            await self._emit("EXPAND", f"Rationale: {module.rationale}")

            # Generate skill YAML
            await self._emit("EXPAND", "Generating integration skill...")
            try:
                skill_yaml = await generate_skill_file(module, self.profile, gap)
            except Exception as e:
                await self._emit("ERROR", f"Skill generation failed for {gap.need}: {e}")
                continue

            skill_path = SKILLS_DIR / f"{gap.need}.yaml"
            skill_path.write_text(skill_yaml)
            await self._emit("EXPAND", f"Saved skill → {skill_path}")

            # Ingest skill into profile
            try:
                skill = ingest_skill(skill_yaml, self.profile)
            except Exception as e:
                await self._emit("ERROR", f"Skill ingestion failed for {gap.need}: {e}")
                continue

            tool_names = [t["name"] for t in skill.get("agent_tools", [])]
            await self._emit("EXPAND", f"Installed: {skill['skill_id']} → tools: {tool_names}")
            filled.append({"gap": gap.need, "module": module.name, "skill": skill["skill_id"]})

        caps = [c["id"] for c in self.profile.capabilities]
        await self._emit("EXPAND", f"Self-expansion complete! Capabilities: {caps}")

        return {
            "status": "expanded",
            "filled": filled,
            "total_gaps": len(gaps),
            "capabilities": caps,
        }

    async def _handle_movement(self, nl_input: str) -> dict:
        """Handle a movement command through PLANNER → SAFETY → EXECUTOR."""
        state = await self.sim.get_state()

        # Get scene context from SCOUT
        await self._emit("SCOUT", "Getting scene context...")
        camera_b64 = await self.sim.get_camera_frame()
        scene = await self.scout.analyze_frame(camera_b64)
        await self._emit("SCOUT", f"Scene: {scene[:100]}...")

        # PLANNER generates a plan from the NL input
        await self._emit("PLANNER", "Planning...")
        plan = await self.planner.plan(scene, state, nl_input)
        await self._emit("PLANNER", f"Plan: {json.dumps(plan, indent=2)[:200]}...", {"plan": plan})

        # Check for capability gaps — trigger self-expanding loop if needed
        if self._plan_has_capability_gap(plan):
            expand_result = await self._handle_capability_gap(plan)
            if expand_result["status"] == "expanded" and expand_result["filled"]:
                # Retry: re-plan with updated capabilities
                await self._emit("ORCHESTRATOR", "Retrying command with new capabilities...")
                plan = await self.planner.plan(scene, state, nl_input)
                await self._emit("PLANNER", f"Retry plan: {json.dumps(plan, indent=2)[:200]}...", {"plan": plan})

                # If still a gap after expansion, give up
                if self._plan_has_capability_gap(plan):
                    return {
                        "type": "movement",
                        "input": nl_input,
                        "status": "capability_gap",
                        "plan": plan,
                        "expansion": expand_result,
                    }
            elif expand_result["status"] != "already_capable":
                return {
                    "type": "movement",
                    "input": nl_input,
                    "status": "capability_gap",
                    "plan": plan,
                    "expansion": expand_result,
                }

        # SAFETY checks the plan
        await self._emit("SAFETY", "Evaluating...")
        safety_result = await self.safety.evaluate(plan, state)
        risk = safety_result.get("risk_level", "low").lower()
        approved = safety_result.get("approved", False)
        await self._emit("SAFETY", f"Risk: {risk} | Approved: {approved}", {"safety": safety_result})

        if risk not in ("low", "medium") or not approved:
            await self._emit("ERROR", f"VETOED — {safety_result.get('concerns', [])}")
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
        await self._emit("ORCHESTRATOR", "APPROVED — executing")
        exec_results = []
        for step in plan.get("steps", []):
            action = step.get("action", nl_input)
            await self._emit("EXECUTOR", f"Executing: {action}")
            result = await self.executor.execute(action, state)
            exec_results.append(result)
            if "error" in result:
                await self._emit("ERROR", f"Execution error: {result['error']}")
            else:
                source = result.get("source", "?")
                await self._emit("EXECUTOR", f"Done ({source})")
            # Update state after each step
            state = await self.sim.get_state()

        await self._emit("ORCHESTRATOR", "Command complete")
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
        await self._emit("ORCHESTRATOR", f"Starting — task: {task!r}")
        await self._emit("ORCHESTRATOR", f"Max iterations: {max_iterations}, "
               f"SCOUT interval: {SCOUT_INTERVAL_S}s")

        self._iteration = 0
        self._results = []
        self._task_complete = False

        while self._iteration < max_iterations and not self._task_complete:
            self._iteration += 1
            await self._emit("ORCHESTRATOR", f"{'='*50}")
            await self._emit("ORCHESTRATOR", f"Tick {self._iteration}/{max_iterations}")

            # --- SCOUT (continuous) ---
            scene, state = await self._scout_analyze()

            if not self._scene_changed(self._last_scene, scene):
                await self._emit("SCOUT", "No significant scene change — waiting...")
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
                await self._emit("ORCHESTRATOR", "Action APPROVED")
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
                await self._emit("ERROR",
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

            await self._emit("ORCHESTRATOR",
                   f"Result: {self._results[-1]['status']}")

            # Pace the loop
            await asyncio.sleep(SCOUT_INTERVAL_S)

        # --- Summary ---
        executed = sum(1 for r in self._results if r["status"] == "executed")
        revised = sum(1 for r in self._results if r["status"] == "revised")
        await self._emit("ORCHESTRATOR",
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
