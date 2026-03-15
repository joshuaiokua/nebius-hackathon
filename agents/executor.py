"""Executor agent — maps high-level actions to G1 joint control targets.

Uses LLM (Nebius) to translate arbitrary natural language commands into
23-DOF joint targets. Falls back to hardcoded presets for common actions.

Joint order (23 DOF):
  0-5:   left leg  (hip yaw/roll/pitch, knee, ankle pitch/roll)
  6-11:  right leg (hip yaw/roll/pitch, knee, ankle pitch/roll)
  12:    waist yaw
  13-17: left arm  (shoulder pitch/roll/yaw, elbow, hand)
  18-22: right arm (shoulder pitch/roll/yaw, elbow, hand)
"""

from __future__ import annotations

import json

from agents.sim_interface import SimInterface
from agent.planner import llm_call as nebius_llm_call

# 23 DOF — all zeros is the neutral standing pose
_ZEROS = [0.0] * 23

JOINT_NAMES = [
    "left_hip_yaw", "left_hip_roll", "left_hip_pitch",
    "left_knee", "left_ankle_pitch", "left_ankle_roll",
    "right_hip_yaw", "right_hip_roll", "right_hip_pitch",
    "right_knee", "right_ankle_pitch", "right_ankle_roll",
    "waist_yaw",
    "left_shoulder_pitch", "left_shoulder_roll", "left_shoulder_yaw",
    "left_elbow", "left_hand",
    "right_shoulder_pitch", "right_shoulder_roll", "right_shoulder_yaw",
    "right_elbow", "right_hand",
]

# Multi-phase gait sequences: list of (targets, duration_steps) per phase.
# Walking alternates left-swing/right-stance ↔ right-swing/left-stance.
# Each "step" is 2 phases (left step + right step).

def _walk_gait(direction: float = -1.0, num_steps: int = 4) -> list[dict]:
    """Generate a walking gait: alternating left/right steps.

    direction: -1.0 = forward (hip pitch negative), +1.0 = backward
    """
    swing_hip = 0.4 * direction   # swing leg hip pitch
    stance_hip = 0.15 * direction  # stance leg hip pitch (slight lean)
    swing_knee = 0.5
    stance_knee = 0.2
    swing_ankle = -0.25
    stance_ankle = -0.1
    arm_swing = 0.2

    phases = []
    for i in range(num_steps):
        if i % 2 == 0:
            # Left leg swings, right leg stance
            phases.append({
                "targets": [
                    swing_hip, 0.0, 0.0, swing_knee, swing_ankle, 0.0,
                    stance_hip, 0.0, 0.0, stance_knee, stance_ankle, 0.0,
                    0.0,
                    -arm_swing, 0.0, 0.0, -0.15, 0.0,
                    arm_swing, 0.0, 0.0, -0.15, 0.0,
                ],
                "duration_steps": 250,
            })
        else:
            # Right leg swings, left leg stance
            phases.append({
                "targets": [
                    stance_hip, 0.0, 0.0, stance_knee, stance_ankle, 0.0,
                    swing_hip, 0.0, 0.0, swing_knee, swing_ankle, 0.0,
                    0.0,
                    arm_swing, 0.0, 0.0, -0.15, 0.0,
                    -arm_swing, 0.0, 0.0, -0.15, 0.0,
                ],
                "duration_steps": 250,
            })

    # End with standing
    phases.append({"targets": list(_ZEROS), "duration_steps": 200})
    return phases


def _turn_gait(direction: float = -1.0, num_steps: int = 3) -> list[dict]:
    """Generate a turning gait. direction: -1.0 = left, +1.0 = right."""
    waist = 0.3 * direction
    phases = []
    for i in range(num_steps):
        yaw_l = 0.1 * direction if i % 2 == 0 else -0.05 * direction
        yaw_r = -0.1 * direction if i % 2 == 0 else 0.05 * direction
        phases.append({
            "targets": [
                -0.15, 0.0, yaw_l, 0.3, -0.1, 0.0,
                -0.15, 0.0, yaw_r, 0.3, -0.1, 0.0,
                waist,
                0.0, 0.0, 0.0, 0.0, 0.0,
                0.0, 0.0, 0.0, 0.0, 0.0,
            ],
            "duration_steps": 200,
        })
    phases.append({"targets": list(_ZEROS), "duration_steps": 200})
    return phases


def _wave_sequence() -> list[dict]:
    """Wave: arm up → wave back and forth → arm down."""
    base_legs = [0.0] * 13
    return [
        {"targets": [*base_legs, 0.0,0.0,0.0,0.0,0.0, -1.0,-0.3,0.0,0.6,0.0], "duration_steps": 250},
        {"targets": [*base_legs, 0.0,0.0,0.0,0.0,0.0, -1.0,-0.5,0.3,0.8,0.0], "duration_steps": 150},
        {"targets": [*base_legs, 0.0,0.0,0.0,0.0,0.0, -1.0,-0.1,-0.2,0.4,0.0], "duration_steps": 150},
        {"targets": [*base_legs, 0.0,0.0,0.0,0.0,0.0, -1.0,-0.5,0.3,0.8,0.0], "duration_steps": 150},
        {"targets": [*base_legs, 0.0,0.0,0.0,0.0,0.0, -1.0,-0.1,-0.2,0.4,0.0], "duration_steps": 150},
        {"targets": list(_ZEROS), "duration_steps": 250},
    ]


# Single-pose presets (actions that don't need multi-phase)
ACTION_TARGETS: dict[str, dict] = {
    "stop":  {"targets": list(_ZEROS), "duration_steps": 200},
    "stand": {"targets": list(_ZEROS), "duration_steps": 200},
    "reach_left": {
        "targets": [*_ZEROS[:13], 0.6, 0.2, 0.0, -0.3, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        "duration_steps": 300,
    },
    "reach_right": {
        "targets": [*_ZEROS[:13], 0.0, 0.0, 0.0, 0.0, 0.0, 0.6, -0.2, 0.0, -0.3, 0.0],
        "duration_steps": 300,
    },
}

# Multi-phase sequence presets
SEQUENCE_ACTIONS: dict[str, list[dict]] = {
    "walk_forward": _walk_gait(direction=-1.0, num_steps=6),
    "walk_backward": _walk_gait(direction=1.0, num_steps=4),
    "turn_left": _turn_gait(direction=-1.0, num_steps=4),
    "turn_right": _turn_gait(direction=1.0, num_steps=4),
    "wave": _wave_sequence(),
}

_NL_SYSTEM_PROMPT = """\
You are a G1 humanoid robot controller. A PD position controller smoothly \
interpolates from the current pose to your target pose, so the robot won't \
collapse. Output conservative target joint positions.

Joint order (23 DOF):
[left_hip_pitch, left_hip_roll, left_hip_yaw, left_knee, left_ankle_pitch, \
left_ankle_roll, right_hip_pitch, right_hip_roll, right_hip_yaw, right_knee, \
right_ankle_pitch, right_ankle_roll, waist_yaw, left_shoulder_pitch, \
left_shoulder_roll, left_shoulder_yaw, left_elbow, left_wrist, \
right_shoulder_pitch, right_shoulder_roll, right_shoulder_yaw, right_elbow, \
right_wrist]

CRITICAL RULES:
- Standing pose is all zeros. ALWAYS keep legs near zero unless actively walking.
- Leg joints must be symmetric (left = right) to stay balanced.
- Walking: hip pitch -0.3, knee 0.6, ankle pitch -0.3 (both legs same).
- Turning: waist yaw ±0.3, small hip adjustments only.
- Arms only: leave legs at 0. Shoulder pitch -1.0 = arm up, elbow 0.6 = bent.
- Max change from current: 0.5 rad per joint. Be conservative.
- duration_steps: 200-500 (more steps = smoother). Use 300 as default.

Output ONLY a JSON object with:
- "targets": array of 23 floats
- "duration_steps": integer (200-500)

No explanation, no markdown fences. Just the JSON object."""


async def nl_to_joint_targets(command: str, robot_state: dict) -> dict:
    """Use LLM to translate a natural language command into joint targets.

    Args:
        command: Natural language movement command (e.g. 'raise both arms').
        robot_state: Current robot state including joint_positions.

    Returns:
        Dict with 'targets' (list of 23 floats) and 'duration_steps' (int).
    """
    current_joints = robot_state.get("joint_positions", _ZEROS)
    joint_state_str = ", ".join(
        f"{name}={val:.2f}" for name, val in zip(JOINT_NAMES, current_joints)
    )

    user_msg = (
        f"Command: {command}\n\n"
        f"Current joint positions:\n{joint_state_str}"
    )

    raw = await nebius_llm_call(_NL_SYSTEM_PROMPT, user_msg, max_tokens=512)
    # Strip markdown fences if any
    cleaned = raw.strip()
    for fence in ("```json", "```"):
        cleaned = cleaned.removeprefix(fence).removesuffix(fence).strip()

    result = json.loads(cleaned)
    targets = result["targets"]
    if len(targets) != 23:
        raise ValueError(f"Expected 23 joint targets, got {len(targets)}")

    return {
        "targets": [float(t) for t in targets],
        "duration_steps": int(result.get("duration_steps", 100)),
    }


class ExecutorAgent:
    """Maps action names or natural language to G1 joint targets and sends to sim."""

    def __init__(self, sim: SimInterface) -> None:
        self.sim = sim

    @staticmethod
    def _clamp_targets(targets: list[float]) -> list[float]:
        """Safety clamp: keep all joint targets within conservative ranges."""
        clamped = list(targets[:23]) + [0.0] * max(0, 23 - len(targets))
        # Leg joints (0-11): clamp to ±0.8 rad max
        for i in range(12):
            clamped[i] = max(-0.8, min(0.8, clamped[i]))
        # Waist (12): clamp to ±0.5
        clamped[12] = max(-0.5, min(0.5, clamped[12]))
        # Arm joints (13-22): clamp to ±1.5
        for i in range(13, 23):
            clamped[i] = max(-1.5, min(1.5, clamped[i]))
        return clamped

    async def execute(self, action_name: str, sim_state: dict) -> dict:
        """Execute an action by sending joint targets to the simulation.

        Checks multi-phase sequences first, then single-pose presets,
        then falls back to LLM for arbitrary commands.
        """
        # Multi-phase sequence (walk, turn, wave)
        sequence = SEQUENCE_ACTIONS.get(action_name)
        if sequence is not None:
            results = []
            for phase in sequence:
                targets = self._clamp_targets(phase["targets"])
                r = await self.sim.send_command(action_name, {
                    "targets": targets,
                    "duration_steps": phase["duration_steps"],
                })
                results.append(r)
            return {
                "action": action_name,
                "phases": len(sequence),
                "source": "sequence",
                "result": results[-1],
            }

        # Single-pose preset
        preset = ACTION_TARGETS.get(action_name)
        if preset is not None:
            targets = self._clamp_targets(preset["targets"])
            duration = preset["duration_steps"]
            result = await self.sim.send_command(action_name, {
                "targets": targets,
                "duration_steps": duration,
            })
            return {
                "action": action_name,
                "targets": targets,
                "duration_steps": duration,
                "source": "preset",
                "result": result,
            }

        # LLM fallback for arbitrary commands
        try:
            llm_result = await nl_to_joint_targets(action_name, sim_state)
            targets = self._clamp_targets(llm_result["targets"])
            duration = max(200, min(500, llm_result["duration_steps"]))
        except Exception as e:
            return {
                "action": action_name,
                "error": f"LLM joint target generation failed: {e}",
                "available_presets": list(ACTION_TARGETS.keys()) + list(SEQUENCE_ACTIONS.keys()),
            }

        result = await self.sim.send_command(action_name, {
            "targets": targets,
            "duration_steps": duration,
        })
        return {
            "action": action_name,
            "targets": targets,
            "duration_steps": duration,
            "source": "llm",
            "result": result,
        }
