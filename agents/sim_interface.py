"""Simulation interface — MuJoCo G1 with Unitree RL locomotion policy.

The sim runs in a background thread. Commands set velocity targets;
the camera feed updates in real-time during execution.
"""

import asyncio
import base64
import io
import os
import threading
import time

import mujoco
import numpy as np
import torch
from PIL import Image

_BASE = os.path.dirname(os.path.dirname(__file__))
_MODEL_PATH = os.path.join(_BASE, "mujoco_sims", "unitree_ros", "robots", "g1_description", "scene_rl.xml")
_POLICY_PATH = os.path.join(_BASE, "deploy", "g1_policy.pt")

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
_RENDER_INTERVAL = 50
_MAX_CMD_STEPS = 5000  # safety cap: 10 seconds max


def _gravity_orientation(quat):
    qw, qx, qy, qz = quat
    return np.array([2*(-qz*qx+qw*qy), -2*(qz*qy+qw*qx), 1-2*(qw*qw+qz*qz)])


class SimInterface:
    def __init__(self, model_path=_MODEL_PATH, policy_path=_POLICY_PATH):
        self.model_path = model_path
        self.model = mujoco.MjModel.from_xml_path(model_path)
        self.data = mujoco.MjData(self.model)
        self.model.opt.timestep = _SIM_DT
        self.renderer = mujoco.Renderer(self.model, height=480, width=640)

        self.policy = torch.jit.load(policy_path, map_location="cpu")
        self.policy.eval()

        self._action = np.zeros(_NUM_ACTIONS, dtype=np.float32)
        self._target_dof_pos = _DEFAULT_ANGLES.copy()
        self._obs = np.zeros(_NUM_OBS, dtype=np.float32)
        self._step_count = 0
        self._cmd = np.array([0.0, 0.0, 0.0], dtype=np.float32)

        # Frame cache: sim thread writes, HTTP handlers read
        self._frame_bytes = b""
        self._frame_lock = threading.Lock()

        # Command lifecycle
        self._cmd_steps_left = 0
        self._cmd_done = threading.Event()
        self._cmd_done.set()  # starts idle

        # Camera
        self._cam = mujoco.MjvCamera()
        self._cam.type = mujoco.mjtCamera.mjCAMERA_TRACKING
        self._cam.trackbodyid = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "pelvis")
        self._cam.distance = 3.0
        self._cam.azimuth = -135
        self._cam.elevation = -20
        self._cam.lookat[:] = [0, 0, 0.8]

        # Stabilize standing
        for _ in range(1000):
            self._step_physics()
        self._do_render()

        # Start background sim
        self._alive = True
        threading.Thread(target=self._loop, daemon=True).start()

    def _step_physics(self):
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
            o = self._obs
            o[:3] = omega
            o[3:6] = grav
            o[6:9] = self._cmd * _CMD_SCALE
            o[9:21] = qj
            o[21:33] = dqj
            o[33:45] = self._action
            o[45:47] = [np.sin(2*np.pi*phase), np.cos(2*np.pi*phase)]
            with torch.no_grad():
                self._action = self.policy(torch.from_numpy(o).unsqueeze(0)).numpy().squeeze()
            self._target_dof_pos = self._action * _ACTION_SCALE + _DEFAULT_ANGLES

    def _do_render(self):
        self.renderer.update_scene(self.data, self._cam)
        frame = self.renderer.render()
        buf = io.BytesIO()
        Image.fromarray(frame).save(buf, format="JPEG", quality=75)
        with self._frame_lock:
            self._frame_bytes = buf.getvalue()

    def _loop(self):
        rc = 0
        while self._alive:
            self._step_physics()
            rc += 1

            # Render periodically
            if rc >= _RENDER_INTERVAL:
                self._do_render()
                rc = 0

            # Command countdown
            if self._cmd_steps_left > 0:
                self._cmd_steps_left -= 1
                if self._cmd_steps_left <= 0:
                    self._cmd[:] = 0.0
                    self._do_render()
                    self._cmd_done.set()
            else:
                # Idle: don't burn 100% CPU
                time.sleep(0.002)

    # --- Public API (called from async FastAPI handlers) ---

    async def get_state(self):
        return {
            "time": float(self.data.time),
            "position": self.data.qpos[:3].tolist(),
            "orientation": self.data.qpos[3:7].tolist(),
            "velocity": self.data.qvel[:3].tolist(),
            "angular_vel": self.data.qvel[3:6].tolist(),
            "stability": float(np.clip(1.0 - np.abs(self.data.qvel[3:6]).mean() * 0.5, 0, 1)),
            "battery": 85.0,
            "joint_positions": self.data.qpos[7:].tolist(),
            "cmd": self._cmd.tolist(),
            "qpos": self.data.qpos.tolist(),
            "qvel": self.data.qvel.tolist(),
        }

    async def get_camera_frame(self):
        with self._frame_lock:
            return base64.b64encode(self._frame_bytes).decode()

    async def get_camera_frame_bytes(self):
        with self._frame_lock:
            return self._frame_bytes

    async def send_command(self, action, params):
        if action == "inject_scene":
            mjcf_xml = params.get("mjcf_xml", "")
            if not mjcf_xml:
                return {"status": "error", "message": "No mjcf_xml provided"}
            return await self.inject_scene_xml(mjcf_xml)

        cmd = params.get("cmd", params.get("velocity", [0.0, 0.0, 0.0]))
        duration_s = params.get("duration_s", 2.0)
        steps = min(int(duration_s / _SIM_DT), _MAX_CMD_STEPS)

        self._cmd[:] = np.array(cmd[:3], dtype=np.float32)
        self._cmd_done.clear()
        self._cmd_steps_left = steps

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: self._cmd_done.wait(timeout=15.0))

        # Force stop if timed out
        self._cmd[:] = 0.0
        self._cmd_steps_left = 0

        return {
            "status": "ok",
            "action": action,
            "duration_s": duration_s,
            "steps_executed": steps,
            "new_state": await self.get_state(),
        }

    async def inject_scene_xml(self, mjcf_xml):
        import xml.etree.ElementTree as ET

        tree = ET.parse(self.model_path)
        worldbody = tree.getroot().find("worldbody")
        for elem in ET.fromstring(f"<w>{mjcf_xml}</w>"):
            worldbody.append(elem)

        model_dir = os.path.dirname(os.path.abspath(self.model_path))
        temp_path = os.path.join(model_dir, "_scene_tmp.xml")
        tree.write(temp_path)

        try:
            self.model = mujoco.MjModel.from_xml_path(temp_path)
            self.data = mujoco.MjData(self.model)
            self.model.opt.timestep = _SIM_DT
            self.renderer = mujoco.Renderer(self.model, height=480, width=640)
            self._cam.trackbodyid = mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_BODY, "pelvis")
            self._action[:] = 0
            self._target_dof_pos[:] = _DEFAULT_ANGLES
            self._step_count = 0
            for _ in range(500):
                self._step_physics()
            self._do_render()
        finally:
            os.unlink(temp_path)

        return {"status": "ok", "message": "Scene updated"}
