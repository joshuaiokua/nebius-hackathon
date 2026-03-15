"""Executor agent — maps high-level actions to G1 velocity commands.

The G1 sim uses a pre-trained RL locomotion policy that accepts velocity
commands [vx, vy, yaw_rate]. The executor translates action names and
natural language into these velocity commands.
"""

from __future__ import annotations

import json

from agents.sim_interface import SimInterface
from agent.planner import llm_call as nebius_llm_call

# Velocity presets: [vx (m/s), vy (m/s), yaw_rate (rad/s)], duration (seconds)
VELOCITY_PRESETS: dict[str, dict] = {
    "walk_forward":  {"cmd": [0.5,  0.0,  0.0], "duration_s": 3.0},
    "walk_backward": {"cmd": [-0.3, 0.0,  0.0], "duration_s": 2.5},
    "turn_left":     {"cmd": [0.0,  0.0,  0.5], "duration_s": 2.0},
    "turn_right":    {"cmd": [0.0,  0.0, -0.5], "duration_s": 2.0},
    "strafe_left":   {"cmd": [0.0,  0.3,  0.0], "duration_s": 2.0},
    "strafe_right":  {"cmd": [0.0, -0.3,  0.0], "duration_s": 2.0},
    "run_forward":   {"cmd": [1.0,  0.0,  0.0], "duration_s": 3.0},
    "stop":          {"cmd": [0.0,  0.0,  0.0], "duration_s": 1.0},
    "stand":         {"cmd": [0.0,  0.0,  0.0], "duration_s": 1.0},
    "wave":          {"cmd": [0.0,  0.0,  0.0], "duration_s": 0.5},
    "reach_left":    {"cmd": [0.0,  0.0,  0.0], "duration_s": 0.5},
    "reach_right":   {"cmd": [0.0,  0.0,  0.0], "duration_s": 0.5},
}

_NL_SYSTEM_PROMPT = """\
You are a G1 humanoid robot controller. The robot uses an RL locomotion policy \
that takes velocity commands. Given a movement command, output the velocity.

Commands are: [vx, vy, yaw_rate]
- vx: forward/backward speed in m/s. Positive = forward. Range: -0.5 to 1.0
- vy: lateral speed in m/s. Positive = left. Range: -0.3 to 0.3
- yaw_rate: turning rate in rad/s. Positive = turn left. Range: -0.8 to 0.8
- duration_s: how long to execute in seconds. Range: 0.5 to 5.0

Examples:
- "walk forward slowly" → {"cmd": [0.3, 0, 0], "duration_s": 3.0}
- "turn left 90 degrees" → {"cmd": [0, 0, 0.5], "duration_s": 3.14}
- "walk forward and turn right" → {"cmd": [0.4, 0, -0.3], "duration_s": 3.0}
- "stop" → {"cmd": [0, 0, 0], "duration_s": 1.0}
- "run forward" → {"cmd": [0.8, 0, 0], "duration_s": 3.0}
- "back up a little" → {"cmd": [-0.3, 0, 0], "duration_s": 1.5}

Output ONLY a JSON object with "cmd" (3 floats) and "duration_s" (float).
No explanation, no markdown. Just the JSON."""


async def nl_to_velocity(command: str) -> dict:
    """Use LLM to translate natural language to velocity command."""
    raw = await nebius_llm_call(_NL_SYSTEM_PROMPT, f"Command: {command}", max_tokens=128)
    cleaned = raw.strip()
    for fence in ("```json", "```"):
        cleaned = cleaned.removeprefix(fence).removesuffix(fence).strip()
    result = json.loads(cleaned)
    cmd = [float(x) for x in result["cmd"][:3]]
    cmd[0] = max(-0.5, min(1.0, cmd[0]))
    cmd[1] = max(-0.3, min(0.3, cmd[1]))
    cmd[2] = max(-0.8, min(0.8, cmd[2]))
    return {
        "cmd": cmd,
        "duration_s": max(0.5, min(5.0, float(result.get("duration_s", 2.0)))),
    }


class ExecutorAgent:
    """Maps action names or natural language to G1 velocity commands."""

    def __init__(self, sim: SimInterface) -> None:
        self.sim = sim

    async def execute(self, action_name: str, sim_state: dict) -> dict:
        preset = VELOCITY_PRESETS.get(action_name)
        if preset is not None:
            cmd = preset["cmd"]
            duration = preset["duration_s"]
            source = "preset"
        else:
            try:
                result = await nl_to_velocity(action_name)
                cmd = result["cmd"]
                duration = result["duration_s"]
                source = "llm"
            except Exception as e:
                return {
                    "action": action_name,
                    "error": f"LLM velocity command failed: {e}",
                    "available_presets": list(VELOCITY_PRESETS.keys()),
                }

        result = await self.sim.send_command(action_name, {
            "cmd": cmd,
            "duration_s": duration,
        })

        return {
            "action": action_name,
            "cmd": cmd,
            "duration_s": duration,
            "source": source,
            "result": result,
        }
