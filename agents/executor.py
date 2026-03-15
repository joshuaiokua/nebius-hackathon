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
from agent.planner import nebius_llm_call

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

# Fallback presets with approximate joint angles based on G1 joint ranges.
# Hip pitch ~0.5 rad for walking, knee ~0.8 rad bent, shoulder ~1.2 rad raised.
ACTION_TARGETS: dict[str, dict] = {
    "walk_forward": {
        "targets": [
            # Left leg: hip yaw, roll, pitch, knee, ankle pitch, roll
            0.0, 0.0, -0.5, 0.8, -0.4, 0.0,
            # Right leg
            0.0, 0.0, -0.5, 0.8, -0.4, 0.0,
            # Waist
            0.0,
            # Left arm (natural swing)
            0.3, 0.0, 0.0, -0.3, 0.0,
            # Right arm
            -0.3, 0.0, 0.0, -0.3, 0.0,
        ],
        "duration_steps": 150,
    },
    "walk_backward": {
        "targets": [
            0.0, 0.0, 0.4, 0.5, -0.2, 0.0,
            0.0, 0.0, 0.4, 0.5, -0.2, 0.0,
            0.0,
            -0.2, 0.0, 0.0, -0.2, 0.0,
            0.2, 0.0, 0.0, -0.2, 0.0,
        ],
        "duration_steps": 150,
    },
    "turn_left": {
        "targets": [
            0.15, 0.1, -0.3, 0.4, -0.15, 0.0,
            -0.15, -0.1, -0.3, 0.4, -0.15, 0.0,
            -0.4,
            0.0, 0.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 0.0, 0.0, 0.0,
        ],
        "duration_steps": 100,
    },
    "turn_right": {
        "targets": [
            -0.15, -0.1, -0.3, 0.4, -0.15, 0.0,
            0.15, 0.1, -0.3, 0.4, -0.15, 0.0,
            0.4,
            0.0, 0.0, 0.0, 0.0, 0.0,
            0.0, 0.0, 0.0, 0.0, 0.0,
        ],
        "duration_steps": 100,
    },
    "stop": {
        "targets": list(_ZEROS),
        "duration_steps": 50,
    },
    "stand": {
        "targets": list(_ZEROS),
        "duration_steps": 50,
    },
    "wave": {
        "targets": [
            *_ZEROS[:13],
            # Left arm neutral
            0.0, 0.0, 0.0, 0.0, 0.0,
            # Right arm: shoulder up and out, elbow bent for waving
            -1.2, -0.5, 0.3, 0.8, 0.0,
        ],
        "duration_steps": 120,
    },
    "reach_left": {
        "targets": [
            *_ZEROS[:13],
            # Left arm extended forward
            0.8, 0.3, 0.0, -0.4, 0.0,
            # Right arm neutral
            0.0, 0.0, 0.0, 0.0, 0.0,
        ],
        "duration_steps": 100,
    },
    "reach_right": {
        "targets": [
            *_ZEROS[:13],
            # Left arm neutral
            0.0, 0.0, 0.0, 0.0, 0.0,
            # Right arm extended forward
            0.8, -0.3, 0.0, -0.4, 0.0,
        ],
        "duration_steps": 100,
    },
}

_NL_SYSTEM_PROMPT = """\
You are a G1 humanoid robot controller. Given a movement command and the robot's \
current joint state, output the target joint positions as a JSON object.

Joint order (23 DOF):
[left_hip_yaw, left_hip_roll, left_hip_pitch, left_knee, left_ankle_pitch, \
left_ankle_roll, right_hip_yaw, right_hip_roll, right_hip_pitch, right_knee, \
right_ankle_pitch, right_ankle_roll, waist_yaw, left_shoulder_pitch, \
left_shoulder_roll, left_shoulder_yaw, left_elbow, left_hand, \
right_shoulder_pitch, right_shoulder_roll, right_shoulder_yaw, right_elbow, \
right_hand]

Joint ranges (radians, approximate):
- Hip yaw: -0.5 to 0.5
- Hip roll: -0.5 to 0.5
- Hip pitch: -1.5 to 1.0
- Knee: 0.0 to 2.0
- Ankle pitch: -0.8 to 0.5
- Ankle roll: -0.3 to 0.3
- Waist yaw: -1.0 to 1.0
- Shoulder pitch: -2.0 to 2.0
- Shoulder roll: -1.5 to 1.5
- Shoulder yaw: -1.0 to 1.0
- Elbow: -2.0 to 0.0
- Hand: -0.5 to 0.5

Guidelines:
- Walking: hip pitch ~-0.5, knee ~0.8, ankle pitch ~-0.4
- Arm raise: shoulder pitch ~ -1.5 (up)
- Keep the robot balanced: leg joints should be symmetric unless intentionally asymmetric
- Smooth motions: don't exceed 1.5 rad change from current position

Output ONLY a JSON object with:
- "targets": array of 23 floats (target joint positions in radians)
- "duration_steps": integer (simulation steps, typically 50-200)

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

    async def execute(self, action_name: str, sim_state: dict) -> dict:
        """Execute an action by sending joint targets to the simulation.

        If action_name matches a preset, use it directly. Otherwise, treat it
        as a natural language command and use the LLM to generate targets.

        Args:
            action_name: Preset key (e.g. 'walk_forward') or natural language.
            sim_state: Current simulation state.

        Returns:
            Dict with 'action', 'targets', 'source', and sim 'result'.
        """
        preset = ACTION_TARGETS.get(action_name)
        if preset is not None:
            targets = preset["targets"]
            duration = preset["duration_steps"]
            source = "preset"
        else:
            # LLM-based translation for arbitrary commands
            try:
                llm_result = await nl_to_joint_targets(action_name, sim_state)
                targets = llm_result["targets"]
                duration = llm_result["duration_steps"]
                source = "llm"
            except Exception as e:
                return {
                    "action": action_name,
                    "error": f"LLM joint target generation failed: {e}",
                    "available_presets": list(ACTION_TARGETS.keys()),
                }

        result = await self.sim.send_command(action_name, {
            "targets": targets,
            "duration_steps": duration,
        })

        return {
            "action": action_name,
            "targets": targets,
            "duration_steps": duration,
            "source": source,
            "result": result,
        }
