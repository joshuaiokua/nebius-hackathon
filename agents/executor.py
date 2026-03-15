"""Executor agent — maps high-level actions to G1 joint control targets.

Stephen: fill in real joint target arrays from G1 PD controller specs.
Joint groups (29 DOF):
  Legs 0-11, Waist 12-14, Arms 15-28
"""

from __future__ import annotations

import numpy as np

from agents.sim_interface import SimInterface

# 29 DOF — all zeros is the neutral standing pose
_ZEROS = [0.0] * 29

# Placeholder joint targets — Stephen fills these with real PD targets.
# Each entry: list of 29 floats (one per actuator).
ACTION_TARGETS: dict[str, list[float]] = {
    "walk_forward": [
        # Legs: hip pitch forward bias, knee flex, ankle push
        0.3, 0.0, -0.6, 0.3, 0.0, -0.6,   # L/R hip pitch/roll/yaw
        0.8, 0.8,                             # L/R knee
        -0.4, 0.0, -0.4, 0.0,               # L/R ankle pitch/roll
        # Waist neutral
        0.0, 0.0, 0.0,
        # Arms: slight swing
        0.2, 0.0, 0.0, -0.3, 0.0, 0.0, 0.0,   # L arm (7 joints)
        -0.2, 0.0, 0.0, -0.3, 0.0, 0.0, 0.0,  # R arm (7 joints)
    ],
    "walk_backward": [
        -0.3, 0.0, 0.6, -0.3, 0.0, 0.6,
        0.4, 0.4,
        0.2, 0.0, 0.2, 0.0,
        0.0, 0.0, 0.0,
        -0.1, 0.0, 0.0, -0.2, 0.0, 0.0, 0.0,
        0.1, 0.0, 0.0, -0.2, 0.0, 0.0, 0.0,
    ],
    "turn_left": [
        0.1, 0.2, -0.3, 0.1, -0.2, 0.3,
        0.3, 0.3,
        -0.1, 0.0, -0.1, 0.0,
        0.0, 0.0, -0.3,
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    ],
    "turn_right": [
        0.1, -0.2, 0.3, 0.1, 0.2, -0.3,
        0.3, 0.3,
        -0.1, 0.0, -0.1, 0.0,
        0.0, 0.0, 0.3,
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    ],
    "stop": list(_ZEROS),
    "stand": list(_ZEROS),
    "wave": [
        # Legs/waist neutral
        *_ZEROS[:15],
        # Left arm neutral
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
        # Right arm: shoulder up, elbow extended
        0.0, -1.2, 0.5, 0.3, 0.0, 0.0, 0.0,
    ],
    "reach_left": [
        *_ZEROS[:15],
        # Left arm extended forward
        0.8, 0.3, 0.0, -0.4, 0.0, 0.0, 0.0,
        # Right arm neutral
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    ],
    "reach_right": [
        *_ZEROS[:15],
        # Left arm neutral
        0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
        # Right arm extended forward
        0.8, -0.3, 0.0, -0.4, 0.0, 0.0, 0.0,
    ],
}


class ExecutorAgent:
    """Maps action names to G1 joint control targets and sends them to the sim."""

    def __init__(self, sim: SimInterface) -> None:
        self.sim = sim

    async def execute(self, action_name: str, sim_state: dict) -> dict:
        """Execute an action by sending joint targets to the simulation.

        Args:
            action_name: One of the keys in ACTION_TARGETS (e.g. 'walk_forward').
            sim_state: Current simulation state (used for context/logging).

        Returns:
            Dict with 'action', 'targets', and sim 'result'.
        """
        targets = ACTION_TARGETS.get(action_name)
        if targets is None:
            return {
                "action": action_name,
                "error": f"Unknown action: {action_name}. "
                         f"Available: {list(ACTION_TARGETS.keys())}",
            }

        result = await self.sim.send_command(action_name, {
            "targets": targets,
            "duration_steps": 100,
        })

        return {
            "action": action_name,
            "targets": targets,
            "result": result,
        }
