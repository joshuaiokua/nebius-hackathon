"""Simulation interface — MuJoCo G1 with Unitree RL locomotion policy.

Uses the pre-trained G1 walking policy from unitree_rl_gym. The policy
takes velocity commands [vx, vy, yaw_rate] and outputs torques for
12 leg joints at 50Hz. Arms are not actuated in this model.
"""

import base64
import io
import os
import threading

import mujoco
import numpy as np
import torch
from PIL import Image

_BASE = os.path.dirname(os.path.dirname(__file__))
_MODEL_PATH = os.path.join(_BASE, "mujoco_sims", "unitree_ros", "robots", "g1_description", "scene_rl.xml")
_POLICY_PATH = os.path.join(_BASE, "deploy", "g1_policy.pt")

# Config from unitree_rl_gym/deploy/deploy_mujoco/configs/g1.yaml
_KPS = np.array([100, 100, 100, 150, 40, 40, 100, 100, 100, 150, 40, 40], dtype=np.float32)
_KDS = np.array([2, 2, 2, 4, 2, 2, 2, 2, 2, 4, 2, 2], dtype=np.float32)
_DEFAULT_ANGLES = np.array([-0.1, 0.0, 0.0, 0.3, -0.2, 0.0,
                             -0.1, 0.0, 0.0, 0.3, -0.2, 0.0], dtype=np.float32)
_CMD_SCALE = np.array([2.0, 2.0, 0.25], dtype=np.float32)
_ANG_VEL_SCALE = 0.25
_DOF_POS_SCALE = 1.0
_DOF_VEL_SCALE = 0.05
_ACTION_SCALE = 0.25
_NUM_ACTIONS = 12
_NUM_OBS = 47
_SIM_DT = 0.002
_CONTROL_DECIMATION = 10


def _gravity_orientation(quat: np.ndarray) -> np.ndarray:
    qw, qx, qy, qz = quat
    return np.array([
        2 * (-qz * qx + qw * qy),
        -2 * (qz * qy + qw * qx),
        1 - 2 * (qw * qw + qz * qz),
    ])


class SimInterface:
    """MuJoCo G1 simulation driven by a pre-trained RL locomotion policy.

    Commands are velocity-based: [forward_speed, lateral_speed, yaw_rate].
    The policy runs at 50Hz, physics at 500Hz.
    """

    def __init__(self, model_path: str = _MODEL_PATH, policy_path: str = _POLICY_PATH) -> None:
        self.model_path = model_path
        self.model = mujoco.MjModel.from_xml_path(model_path)
        self.data = mujoco.MjData(self.model)
        self.model.opt.timestep = _SIM_DT
        self.renderer = mujoco.Renderer(self.model, height=480, width=640)

        self.policy = torch.jit.load(policy_path, map_location="cpu")
        self.policy.eval()

        self._lock = threading.Lock()
        self._action = np.zeros(_NUM_ACTIONS, dtype=np.float32)
        self._target_dof_pos = _DEFAULT_ANGLES.copy()
        self._obs = np.zeros(_NUM_OBS, dtype=np.float32)
        self._step_count = 0
        self._cmd = np.array([0.0, 0.0, 0.0], dtype=np.float32)  # standing still

        self._frame_cache: bytes = b""
        self._frame_dirty = True

        # Stabilize at default standing pose
        self._run_policy_steps(1000)

    def _policy_step(self) -> None:
        """One physics step with PD control, policy inference at decimation."""
        tau = (self._target_dof_pos - self.data.qpos[7:]) * _KPS + (0 - self.data.qvel[6:]) * _KDS
        self.data.ctrl[:] = tau
        mujoco.mj_step(self.model, self.data)
        self._step_count += 1

        if self._step_count % _CONTROL_DECIMATION == 0:
            qj = (self.data.qpos[7:] - _DEFAULT_ANGLES) * _DOF_POS_SCALE
            dqj = self.data.qvel[6:] * _DOF_VEL_SCALE
            grav = _gravity_orientation(self.data.qpos[3:7])
            omega = self.data.qvel[3:6] * _ANG_VEL_SCALE

            phase = (self._step_count * _SIM_DT) % 0.8 / 0.8
            sin_p, cos_p = np.sin(2 * np.pi * phase), np.cos(2 * np.pi * phase)

            obs = self._obs
            obs[:3] = omega
            obs[3:6] = grav
            obs[6:9] = self._cmd * _CMD_SCALE
            obs[9:9 + _NUM_ACTIONS] = qj
            obs[9 + _NUM_ACTIONS:9 + 2 * _NUM_ACTIONS] = dqj
            obs[9 + 2 * _NUM_ACTIONS:9 + 3 * _NUM_ACTIONS] = self._action
            obs[9 + 3 * _NUM_ACTIONS:9 + 3 * _NUM_ACTIONS + 2] = [sin_p, cos_p]

            with torch.no_grad():
                self._action = self.policy(
                    torch.from_numpy(obs).unsqueeze(0)
                ).numpy().squeeze()

            self._target_dof_pos = self._action * _ACTION_SCALE + _DEFAULT_ANGLES

    def _run_policy_steps(self, n: int) -> None:
        for _ in range(n):
            self._policy_step()
        self._frame_dirty = True

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
                "joint_positions": self.data.qpos[7:].tolist(),
                "cmd": self._cmd.tolist(),
            }

    def _render_jpeg(self) -> bytes:
        cam = mujoco.MjvCamera()
        cam.type = mujoco.mjtCamera.mjCAMERA_TRACKING
        cam.trackbodyid = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "pelvis")
        cam.distance = 3.0
        cam.azimuth = -135
        cam.elevation = -20
        cam.lookat[:] = [0, 0, 0.8]
        self.renderer.update_scene(self.data, cam)
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

        # Velocity command: [vx, vy, yaw_rate]
        cmd = params.get("cmd", None)
        duration_s = params.get("duration_s", 2.0)

        if cmd is not None:
            self._cmd = np.array(cmd[:3], dtype=np.float32)
        else:
            # Legacy: treat targets as ignored, use cmd from params or default
            self._cmd = np.array(params.get("velocity", [0.0, 0.0, 0.0])[:3], dtype=np.float32)

        steps = int(duration_s / _SIM_DT)

        with self._lock:
            self._run_policy_steps(steps)

        # Stop after command
        self._cmd = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        # Let it settle
        with self._lock:
            self._run_policy_steps(250)

        return {
            "status": "ok",
            "action": action,
            "duration_s": duration_s,
            "steps_executed": steps,
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
                self.model = mujoco.MjModel.from_xml_path(temp_path)
                self.data = mujoco.MjData(self.model)
                self.model.opt.timestep = _SIM_DT
                self.renderer = mujoco.Renderer(self.model, height=480, width=640)
                self._action = np.zeros(_NUM_ACTIONS, dtype=np.float32)
                self._target_dof_pos = _DEFAULT_ANGLES.copy()
                self._step_count = 0
                self._run_policy_steps(500)
        finally:
            os.unlink(temp_path)

        return {"status": "ok", "message": "Scene updated with new elements"}
