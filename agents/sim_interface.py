"""Simulation interface — real MuJoCo G1 with position-controlled actuators."""

import base64
import io
import os
import threading

import mujoco
import numpy as np
from PIL import Image

_MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "mujoco_sims", "unitree_ros", "robots", "g1_description", "g1_23dof.xml",
)


class SimInterface:
    """Real MuJoCo interface to the Unitree G1 23-DOF simulation.

    The MJCF model uses position actuators with high kp + joint damping,
    so ctrl[i] = target position in radians. The robot stands at ctrl=0.
    """

    def __init__(self, model_path: str = _MODEL_PATH) -> None:
        self.model_path = model_path
        self.model = mujoco.MjModel.from_xml_path(model_path)
        self.data = mujoco.MjData(self.model)
        self.renderer = mujoco.Renderer(self.model, height=480, width=640)
        self._lock = threading.Lock()

        # Frame cache to avoid re-rendering on every poll
        self._frame_cache: bytes = b""
        self._frame_dirty = True

        # Stabilize at standing pose
        self.data.ctrl[:] = 0
        for _ in range(1000):
            mujoco.mj_step(self.model, self.data)

    async def get_state(self) -> dict:
        with self._lock:
            return {
                "time": float(self.data.time),
                "qpos": self.data.qpos.tolist(),
                "qvel": self.data.qvel.tolist(),
                "position": self.data.qpos[:3].tolist(),
                "orientation": self.data.qpos[3:7].tolist(),
                "velocity": self.data.qvel[:3].tolist(),
                "angular_vel": self.data.qvel[3:6].tolist(),
                "stability": float(np.clip(
                    1.0 - np.abs(self.data.qvel[3:6]).mean() * 0.5, 0, 1
                )),
                "battery": 85.0,
                "joint_positions": self.data.qpos[7:7 + self.model.nu].tolist(),
                "joint_targets": self.data.ctrl[:self.model.nu].tolist(),
            }

    def _render_jpeg(self) -> bytes:
        self.renderer.update_scene(self.data)
        frame = self.renderer.render()
        img = Image.fromarray(frame)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=75)
        return buf.getvalue()

    async def get_camera_frame(self) -> str:
        with self._lock:
            if self._frame_dirty:
                self._frame_cache = self._render_jpeg()
                self._frame_dirty = False
            return base64.b64encode(self._frame_cache).decode()

    async def get_camera_frame_bytes(self) -> bytes:
        with self._lock:
            if self._frame_dirty:
                self._frame_cache = self._render_jpeg()
                self._frame_dirty = False
            return self._frame_cache

    async def send_command(self, action: str, params: dict) -> dict:
        if action == "inject_scene":
            mjcf_xml = params.get("mjcf_xml", "")
            if not mjcf_xml:
                return {"status": "error", "message": "No mjcf_xml provided"}
            return await self.inject_scene_xml(mjcf_xml)

        targets = params.get("targets", [0.0] * self.model.nu)
        duration_steps = params.get("duration_steps", 200)
        target_arr = np.array(targets[:self.model.nu], dtype=np.float64)

        with self._lock:
            # Interpolate to target
            start = self.data.ctrl[:self.model.nu].copy()
            for i in range(duration_steps):
                alpha = (i + 1) / duration_steps
                self.data.ctrl[:self.model.nu] = start + alpha * (target_arr - start)
                mujoco.mj_step(self.model, self.data)

            # Hold at target briefly to let physics settle
            for _ in range(100):
                mujoco.mj_step(self.model, self.data)

            # If robot fell (height < 0.4m), recover to standing
            if self.data.qpos[2] < 0.4:
                mujoco.mj_resetData(self.model, self.data)
                self.data.ctrl[:] = 0
                for _ in range(1000):
                    mujoco.mj_step(self.model, self.data)

            self._frame_dirty = True

        return {
            "status": "ok",
            "action": action,
            "steps_executed": duration_steps,
            "new_state": await self.get_state(),
        }

    async def inject_scene_xml(self, mjcf_xml: str) -> dict:
        import xml.etree.ElementTree as ET

        tree = ET.parse(self.model_path)
        root = tree.getroot()
        worldbody = root.find("worldbody")

        new_elements = ET.fromstring(f"<wrapper>{mjcf_xml}</wrapper>")
        for elem in new_elements:
            worldbody.append(elem)

        model_dir = os.path.dirname(os.path.abspath(self.model_path))
        temp_path = os.path.join(model_dir, "_scene_tmp.xml")
        tree.write(temp_path)

        try:
            with self._lock:
                old_ctrl = self.data.ctrl[:self.model.nu].copy()
                self.model = mujoco.MjModel.from_xml_path(temp_path)
                self.data = mujoco.MjData(self.model)
                self.renderer = mujoco.Renderer(self.model, height=480, width=640)
                self.data.ctrl[:len(old_ctrl)] = old_ctrl
                for _ in range(500):
                    mujoco.mj_step(self.model, self.data)
                self._frame_dirty = True
        finally:
            os.unlink(temp_path)

        return {"status": "ok", "message": "Scene updated with new elements"}
