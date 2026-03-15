"""Simulation interface — abstract boundary between orchestrator and MuJoCo.

Real MuJoCo implementation for Unitree G1 humanoid robot.
"""

import asyncio
import base64
import io
import mujoco
import numpy as np
from PIL import Image


class SimInterface:
    """Interface to the MuJoCo G1 simulation.

    Provides state extraction, camera rendering, command execution,
    and scene XML injection for the Unitree G1 23-DOF humanoid.
    """

    def __init__(self, model_path: str = "mujoco_sims/unitree_ros/robots/g1_description/g1_23dof.xml") -> None:
        self.model_path = model_path
        self.model = mujoco.MjModel.from_xml_path(model_path)
        self.data = mujoco.MjData(self.model)
        self.renderer = mujoco.Renderer(self.model, height=480, width=640)
        # Step to initial state
        mujoco.mj_step(self.model, self.data)

    async def get_state(self) -> dict:
        """Return current robot state from the simulation.

        Returns dict with: time, qpos, qvel, position, orientation,
        velocity, angular_vel, stability, battery, joint_positions.
        """
        return {
            "time": float(self.data.time),
            "qpos": self.data.qpos.tolist(),
            "qvel": self.data.qvel.tolist(),
            "position": self.data.qpos[:3].tolist(),
            "orientation": self.data.qpos[3:7].tolist(),
            "velocity": self.data.qvel[:3].tolist(),
            "angular_vel": self.data.qvel[3:6].tolist(),
            "stability": float(np.clip(1.0 - np.abs(self.data.qvel[3:6]).mean(), 0, 1)),
            "battery": 85.0,
            "joint_positions": self.data.qpos[7:].tolist(),
        }

    async def get_camera_frame(self) -> str:
        """Return a base64-encoded camera frame from the simulation.

        Uses offscreen rendering for headless operation.
        """
        self.renderer.update_scene(self.data)
        frame = self.renderer.render()
        img = Image.fromarray(frame)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=70)
        return base64.b64encode(buf.getvalue()).decode()

    async def send_command(self, action: str, params: dict) -> dict:
        """Send a control command to the simulation.

        Args:
            action: Action name (e.g. 'walk_forward', 'stop', 'wave').
            params: Action parameters (e.g. joint targets, duration).

        Returns:
            Result dict with status and new state snapshot.
        """
        targets = params.get("targets", [0.0] * self.model.nu)
        steps = params.get("duration_steps", 100)
        for _ in range(steps):
            self.data.ctrl[:len(targets)] = targets
            mujoco.mj_step(self.model, self.data)
        return {
            "status": "ok",
            "action": action,
            "steps_executed": steps,
            "new_state": await self.get_state(),
        }

    async def inject_scene_xml(self, mjcf_xml: str) -> dict:
        """Inject new bodies/geoms into the running scene from MJCF XML string.

        This is how SceneBuilder output gets into the sim.

        Rebuilds the entire model with new XML appended to worldbody.
        """
        import xml.etree.ElementTree as ET
        import tempfile

        # Load original scene XML
        tree = ET.parse(self.model_path)
        root = tree.getroot()
        worldbody = root.find('worldbody')

        # Parse the new elements and append them
        # Wrap in a root tag so ET can parse multiple top-level elements
        new_elements = ET.fromstring(f"<wrapper>{mjcf_xml}</wrapper>")
        for elem in new_elements:
            worldbody.append(elem)

        # Write to temp file and reload
        with tempfile.NamedTemporaryFile(suffix='.xml', mode='w', delete=False) as f:
            tree.write(f, encoding='unicode')
            temp_path = f.name

        # Reload model with new scene
        self.model = mujoco.MjModel.from_xml_path(temp_path)
        self.data = mujoco.MjData(self.model)
        self.renderer = mujoco.Renderer(self.model, height=480, width=640)
        mujoco.mj_step(self.model, self.data)

        return {"status": "ok", "message": f"Scene updated with new elements"}
