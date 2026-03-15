"""Simulation interface — abstract boundary between orchestrator and MuJoCo.

Stephen: Replace the mock implementations with real MuJoCo calls.
See CLAUDE.md for G1 state extraction patterns and rendering setup.
"""

import base64
import random


class SimInterface:
    """Interface to the MuJoCo G1 simulation.

    Every method returns mock data. Stephen replaces internals with real
    mujoco calls — the orchestrator never imports mujoco directly.
    """

    def __init__(self, model_path: str = "mujoco_sims/unitree_ros/robots/g1_description/g1_23dof.xml") -> None:
        self.model_path = model_path
        # Stephen: load model/data here
        # self.model = mujoco.MjModel.from_xml_path(model_path)
        # self.data = mujoco.MjData(self.model)

    async def get_state(self) -> dict:
        """Return current robot state from the simulation.

        Returns dict with: time, qpos, qvel, position, orientation,
        velocity, angular_vel, stability, battery, joint_positions.
        """
        return {
            "time": round(random.uniform(0, 120), 2),
            "position": [round(random.uniform(-2, 2), 3) for _ in range(3)],
            "orientation": [round(random.uniform(-1, 1), 3) for _ in range(4)],
            "velocity": [round(random.uniform(-0.5, 0.5), 3) for _ in range(3)],
            "angular_vel": [round(random.uniform(-0.2, 0.2), 3) for _ in range(3)],
            "stability": round(random.uniform(0.7, 1.0), 2),
            "battery": round(random.uniform(60, 100), 1),
            "joint_positions": [round(random.uniform(-1, 1), 2) for _ in range(23)],
        }

    async def get_camera_frame(self) -> str:
        """Return a base64-encoded camera frame from the simulation.

        Stephen: use mujoco.Renderer for offscreen rendering.
        """
        # Mock: return a tiny placeholder
        return base64.b64encode(b"MOCK_FRAME_DATA").decode()

    async def send_command(self, action: str, params: dict) -> dict:
        """Send a control command to the simulation.

        Args:
            action: Action name (e.g. 'walk_forward', 'stop', 'wave').
            params: Action parameters (e.g. joint targets, duration).

        Returns:
            Result dict with status and new state snapshot.
        """
        # Stephen: set data.ctrl[indices] = params["targets"], step sim
        return {
            "status": "ok",
            "action": action,
            "steps_executed": params.get("duration_steps", 100),
            "new_state": await self.get_state(),
        }
