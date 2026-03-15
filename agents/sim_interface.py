"""Simulation interface — real MuJoCo G1 implementation."""

import asyncio
import base64
import io
import os

import mujoco
import numpy as np
from PIL import Image

_MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "mujoco_sims", "unitree_ros", "robots", "g1_description", "g1_23dof.xml",
)


class SimInterface:
    """Real MuJoCo interface to the Unitree G1 23-DOF simulation."""

    def __init__(self, model_path: str = _MODEL_PATH) -> None:
        self.model_path = model_path
        self.model = mujoco.MjModel.from_xml_path(model_path)
        self.data = mujoco.MjData(self.model)
        self.renderer = mujoco.Renderer(self.model, height=480, width=640)
        # Step to initial state
        mujoco.mj_step(self.model, self.data)

    async def get_state(self) -> dict:
        """Return current robot state from the real simulation."""
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
        """Render the scene offscreen and return as base64 JPEG."""
        self.renderer.update_scene(self.data)
        frame = self.renderer.render()
        img = Image.fromarray(frame)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=70)
        return base64.b64encode(buf.getvalue()).decode()

    async def send_command(self, action: str, params: dict) -> dict:
        """Route commands to the appropriate handler.

        - 'inject_scene': delegates to inject_scene_xml()
        - Everything else: joint control targets → step sim
        """
        if action == "inject_scene":
            mjcf_xml = params.get("mjcf_xml", "")
            if not mjcf_xml:
                return {"status": "error", "message": "No mjcf_xml provided"}
            return await self.inject_scene_xml(mjcf_xml)

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
        """Inject new bodies/geoms into the scene from MJCF XML string."""
        import xml.etree.ElementTree as ET
        import tempfile

        tree = ET.parse(self.model_path)
        root = tree.getroot()
        worldbody = root.find("worldbody")

        new_elements = ET.fromstring(f"<wrapper>{mjcf_xml}</wrapper>")
        for elem in new_elements:
            worldbody.append(elem)

        with tempfile.NamedTemporaryFile(suffix=".xml", mode="wb", delete=False) as f:
            tree.write(f)
            temp_path = f.name

        self.model = mujoco.MjModel.from_xml_path(temp_path)
        self.data = mujoco.MjData(self.model)
        self.renderer = mujoco.Renderer(self.model, height=480, width=640)
        mujoco.mj_step(self.model, self.data)

        os.unlink(temp_path)
        return {"status": "ok", "message": "Scene updated with new elements"}
