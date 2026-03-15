#!/usr/bin/env python3
"""RoboStore Demo — NL commands → LLM → RL locomotion + scene building in MuJoCo.

Run with:  mjpython demo.py

Type natural language commands and watch the G1 execute them in real-time:
  "walk forward"
  "place a red ball 2 meters ahead"
  "walk around the ball"
  "build a wall and walk to it"
  "turn left then run forward"
  "put stairs in front and walk up to them"
"""

import asyncio
import json
import re
import sys
import threading
import time
import xml.etree.ElementTree as ET

import mujoco
import mujoco.viewer
import numpy as np
import torch
from dotenv import load_dotenv

load_dotenv()

from agent.planner import llm_call
from agents.scene_builder import SceneBuilder

# --- Config ---
MODEL_PATH = "mujoco_sims/unitree_ros/robots/g1_description/scene_rl.xml"
POLICY_PATH = "deploy/g1_policy.pt"

KPS = np.array([100,100,100,150,40,40, 100,100,100,150,40,40], dtype=np.float32)
KDS = np.array([2,2,2,4,2,2, 2,2,2,4,2,2], dtype=np.float32)
DEFAULT_ANGLES = np.array([-0.1,0,0,0.3,-0.2,0, -0.1,0,0,0.3,-0.2,0], dtype=np.float32)
CMD_SCALE = np.array([2.0, 2.0, 0.25], dtype=np.float32)
DT = 0.002
DECIMATION = 10
ACTION_SCALE = 0.25

SCENE_WORDS = re.compile(
    r"\b(place|add|put|build|create|spawn|insert|scatter|make)\b", re.IGNORECASE
)

VELOCITY_PROMPT = """\
You are a G1 robot controller. Convert the movement command to a velocity.
Output ONLY a JSON object: {"cmd": [vx, vy, yaw_rate], "duration_s": float}
- vx: forward speed (-0.5 to 1.0 m/s). Positive = forward.
- vy: lateral speed (-0.3 to 0.3). Positive = left.
- yaw_rate: turn rate (-0.8 to 0.8 rad/s). Positive = left.
- duration_s: 0.5 to 6.0 seconds.
No explanation. Just JSON."""

# --- Colors ---
C = "\033[96m"   # cyan
G = "\033[92m"   # green
Y = "\033[93m"   # yellow
M = "\033[95m"   # magenta
R = "\033[91m"   # red
B = "\033[1m"    # bold
D = "\033[2m"    # dim
X = "\033[0m"    # reset


class Demo:
    def __init__(self):
        self.model = mujoco.MjModel.from_xml_path(MODEL_PATH)
        self.data = mujoco.MjData(self.model)
        self.model.opt.timestep = DT
        self.policy = torch.jit.load(POLICY_PATH, map_location="cpu")
        self.policy.eval()
        self.scene_builder = SceneBuilder()

        self.action = np.zeros(12, dtype=np.float32)
        self.target_dof = DEFAULT_ANGLES.copy()
        self.obs = np.zeros(47, dtype=np.float32)
        self.step_count = 0
        self.cmd = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        self.cmd_steps = 0
        self.model_path = MODEL_PATH

    def physics_step(self):
        tau = (self.target_dof - self.data.qpos[7:]) * KPS + (0 - self.data.qvel[6:]) * KDS
        self.data.ctrl[:] = tau
        mujoco.mj_step(self.model, self.data)
        self.step_count += 1

        if self.step_count % DECIMATION == 0:
            qj = (self.data.qpos[7:] - DEFAULT_ANGLES) * 1.0
            dqj = self.data.qvel[6:] * 0.05
            grav_q = self.data.qpos[3:7]
            qw, qx, qy, qz = grav_q
            grav = np.array([2*(-qz*qx+qw*qy), -2*(qz*qy+qw*qx), 1-2*(qw*qw+qz*qz)])
            omega = self.data.qvel[3:6] * 0.25
            phase = (self.step_count * DT) % 0.8 / 0.8
            o = self.obs
            o[:3] = omega; o[3:6] = grav; o[6:9] = self.cmd * CMD_SCALE
            o[9:21] = qj; o[21:33] = dqj; o[33:45] = self.action
            o[45:47] = [np.sin(2*np.pi*phase), np.cos(2*np.pi*phase)]
            with torch.no_grad():
                self.action = self.policy(torch.from_numpy(o).unsqueeze(0)).numpy().squeeze()
            self.target_dof = self.action * ACTION_SCALE + DEFAULT_ANGLES

        if self.cmd_steps > 0:
            self.cmd_steps -= 1
            if self.cmd_steps <= 0:
                self.cmd[:] = 0.0

    def inject_scene(self, mjcf_xml: str):
        """Inject MJCF XML into the live scene."""
        tree = ET.parse(self.model_path)
        root = tree.getroot()
        worldbody = root.find("worldbody")

        for elem in ET.fromstring(f"<w>{mjcf_xml}</w>"):
            worldbody.append(elem)

        import os, tempfile
        model_dir = os.path.dirname(os.path.abspath(self.model_path))
        tmp = os.path.join(model_dir, "_demo_tmp.xml")
        tree.write(tmp)

        try:
            old_qpos = self.data.qpos.copy()
            old_qvel = self.data.qvel.copy()

            self.model = mujoco.MjModel.from_xml_path(tmp)
            self.data = mujoco.MjData(self.model)
            self.model.opt.timestep = DT

            # Restore robot state
            n = min(len(old_qpos), self.model.nq)
            self.data.qpos[:n] = old_qpos[:n]
            n = min(len(old_qvel), self.model.nv)
            self.data.qvel[:n] = old_qvel[:n]

            # Re-stabilize
            for _ in range(200):
                self.physics_step()

            self.model_path = tmp  # so next inject builds on top
            return True
        except Exception as e:
            print(f"  {R}Scene inject failed: {e}{X}")
            os.unlink(tmp)
            return False

    def set_velocity(self, vx, vy, yr, duration_s):
        self.cmd[:] = [vx, vy, yr]
        self.cmd_steps = int(duration_s / DT)

    async def handle_nl(self, text: str):
        """Route NL command to scene building and/or movement."""
        has_scene = bool(SCENE_WORDS.search(text))

        if has_scene:
            # Split compound: "place a ball and walk to it"
            parts = re.split(r"\b(?:and|then|,)\b", text, maxsplit=1)
            scene_part = parts[0].strip()
            move_part = parts[1].strip() if len(parts) > 1 else None

            print(f"  {M}[SCENE]{X} Generating: {scene_part}")
            try:
                mjcf = await self.scene_builder.build_from_prompt(scene_part)
                print(f"  {M}[SCENE]{X} XML: {mjcf[:100]}...")
                ok = self.inject_scene(mjcf)
                if ok:
                    print(f"  {G}[SCENE]{X} Injected into sim")
                else:
                    return
            except Exception as e:
                print(f"  {R}[SCENE] Error: {e}{X}")
                return

            if move_part:
                print(f"  {C}[MOVE]{X} Planning: {move_part}")
                await self._do_move(move_part)
        else:
            await self._do_move(text)

    async def _do_move(self, text: str):
        print(f"  {Y}[LLM]{X} Translating to velocity...")
        try:
            raw = await llm_call(VELOCITY_PROMPT, f"Command: {text}", max_tokens=128)
            cleaned = raw.strip()
            for fence in ("```json", "```"):
                cleaned = cleaned.removeprefix(fence).removesuffix(fence).strip()
            # Extract first JSON object
            match = re.search(r'\{[^}]+\}', cleaned)
            if match:
                result = json.loads(match.group())
            else:
                result = json.loads(cleaned)
            cmd = result["cmd"]
            dur = max(0.5, min(6.0, float(result.get("duration_s", 3.0))))
            vx = max(-0.5, min(1.0, float(cmd[0])))
            vy = max(-0.3, min(0.3, float(cmd[1])))
            yr = max(-0.8, min(0.8, float(cmd[2])))
            print(f"  {G}[EXEC]{X} cmd=[{vx:.1f}, {vy:.1f}, {yr:.1f}] for {dur:.1f}s")
            self.set_velocity(vx, vy, yr, dur)
        except Exception as e:
            print(f"  {R}[ERROR]{X} {e}")


def main():
    demo = Demo()
    loop = asyncio.new_event_loop()

    def input_thread():
        print(f"\n{B}{C}{'='*50}{X}")
        print(f"{B}{C}  RoboStore Demo — NL → LLM → G1 Simulation{X}")
        print(f"{B}{C}{'='*50}{X}")
        print(f"{D}Type natural language commands. Examples:{X}")
        print(f"  {G}walk forward{X}")
        print(f"  {G}place a red ball 2 meters ahead{X}")
        print(f"  {G}walk around the ball{X}")
        print(f"  {G}build stairs and walk to them{X}")
        print(f"  {G}turn left slowly{X}")
        print(f"  {D}quit / q to exit{X}\n")

        while True:
            try:
                text = input(f"{B}{C}demo>{X} ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not text:
                continue
            if text.lower() in ("q", "quit", "exit"):
                import os; os._exit(0)
            # Quick presets (no LLM needed)
            if text.lower() in ("w", "walk"):
                demo.set_velocity(0.5, 0, 0, 4.0)
                print(f"  {G}[EXEC]{X} walk forward 0.5m/s for 4s")
                continue
            if text.lower() in ("s", "stop"):
                demo.set_velocity(0, 0, 0, 0.5)
                print(f"  {G}[EXEC]{X} stop")
                continue

            loop.run_until_complete(demo.handle_nl(text))

    threading.Thread(target=input_thread, daemon=True).start()

    # MuJoCo viewer loop — restart viewer if model changes (scene inject)
    current_model_ptr = id(demo.model)
    while True:
        try:
            with mujoco.viewer.launch_passive(demo.model, demo.data) as viewer:
                while viewer.is_running():
                    t0 = time.time()
                    demo.physics_step()
                    viewer.sync()
                    sleep = DT - (time.time() - t0)
                    if sleep > 0:
                        time.sleep(sleep)
                    # If scene was injected, model changed — restart viewer
                    if id(demo.model) != current_model_ptr:
                        current_model_ptr = id(demo.model)
                        print(f"  {D}[VIEWER] Reloading scene...{X}")
                        break
                else:
                    break  # viewer closed by user
        except Exception as e:
            print(f"  {R}Viewer error: {e}{X}")
            break


if __name__ == "__main__":
    main()
