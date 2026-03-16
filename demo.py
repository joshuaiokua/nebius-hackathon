#!/usr/bin/env python3
"""RoboStore Demo — starts with no legs, web app triggers upgrade to walking G1.

Run with:  mjpython demo.py

Phase 1: Shows G1 torso with no legs on a stand (waiting for hardware)
Phase 2: After web app purchases legs, switches to full RL walking model
Phase 3: Accepts walk/turn commands from web app and CLI

The web app communicates via HTTP on port 8765:
  POST /cmd   {"cmd": [vx,vy,yr], "duration_s": N}
  POST /legs  {} — triggers the model swap to walking G1
"""

import json
import re
import threading
import time
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler

import mujoco
import mujoco.viewer
import numpy as np
import torch
from dotenv import load_dotenv

load_dotenv()

NOLEGS_PATH = "mujoco_sims/unitree_ros/robots/g1_description/scene_nolegs.xml"
WALKING_PATH = "mujoco_sims/unitree_ros/robots/g1_description/scene_rl.xml"
POLICY_PATH = "deploy/g1_policy.pt"

KPS = np.array([100,100,100,150,40,40, 100,100,100,150,40,40], dtype=np.float32)
KDS = np.array([2,2,2,4,2,2, 2,2,2,4,2,2], dtype=np.float32)
DEFAULT_ANGLES = np.array([-0.1,0,0,0.3,-0.2,0, -0.1,0,0,0.3,-0.2,0], dtype=np.float32)
CMD_SCALE = np.array([2.0, 2.0, 0.25], dtype=np.float32)
DT = 0.002
DECIMATION = 10
ACTION_SCALE = 0.25

C = "\033[96m"; G = "\033[92m"; Y = "\033[93m"; M = "\033[95m"
R = "\033[91m"; B = "\033[1m"; D = "\033[2m"; X = "\033[0m"

VELOCITY_PROMPT = """\
You are a G1 robot controller. Convert the movement command to a velocity.
Output ONLY JSON: {"cmd": [vx, vy, yaw_rate], "duration_s": float}
vx: -0.5 to 1.0. vy: -0.3 to 0.3. yaw_rate: -0.8 to 0.8.
duration_s: 0.5 to 6.0. No explanation. Just JSON."""


class Demo:
    def __init__(self):
        self.has_legs = False
        self.model = mujoco.MjModel.from_xml_path(NOLEGS_PATH)
        self.data = mujoco.MjData(self.model)
        self.model.opt.timestep = DT

        self.policy = torch.jit.load(POLICY_PATH, map_location="cpu")
        self.policy.eval()

        self.action = np.zeros(12, dtype=np.float32)
        self.target_dof = DEFAULT_ANGLES.copy()
        self.obs = np.zeros(47, dtype=np.float32)
        self.step_count = 0
        self.cmd = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        self.cmd_steps = 0

        self.swap_to_legs = False  # signal from HTTP handler

    def install_legs(self):
        """Swap to the full walking model."""
        print(f"\n  {G}[UPGRADE]{X} Installing legs... loading RL walking model")
        self.model = mujoco.MjModel.from_xml_path(WALKING_PATH)
        self.data = mujoco.MjData(self.model)
        self.model.opt.timestep = DT
        self.has_legs = True
        self.step_count = 0
        self.action[:] = 0
        self.target_dof[:] = DEFAULT_ANGLES
        self.cmd[:] = 0
        self.cmd_steps = 0
        print(f"  {G}[UPGRADE]{X} Legs installed! G1 is now bipedal.\n")

    def physics_step(self):
        if not self.has_legs:
            # No-legs mode: just step physics (torso sits on stand)
            mujoco.mj_step(self.model, self.data)
            return

        tau = (self.target_dof - self.data.qpos[7:]) * KPS + (0 - self.data.qvel[6:]) * KDS
        self.data.ctrl[:] = tau
        mujoco.mj_step(self.model, self.data)
        self.step_count += 1

        if self.step_count % DECIMATION == 0:
            qj = (self.data.qpos[7:] - DEFAULT_ANGLES) * 1.0
            dqj = self.data.qvel[6:] * 0.05
            qw, qx, qy, qz = self.data.qpos[3:7]
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

    def set_velocity(self, vx, vy, yr, duration_s):
        if not self.has_legs:
            print(f"  {R}No legs installed — can't walk{X}")
            return
        self.cmd[:] = [vx, vy, yr]
        self.cmd_steps = int(duration_s / DT)
        print(f"  {G}[EXEC]{X} cmd=[{vx:.1f}, {vy:.1f}, {yr:.1f}] for {duration_s:.1f}s")


demo = Demo()


class CmdHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}

        if self.path == "/cmd":
            cmd = body.get("cmd", [0, 0, 0])
            dur = body.get("duration_s", 2.0)
            demo.set_velocity(float(cmd[0]), float(cmd[1]), float(cmd[2]), float(dur))
            self._respond({"status": "ok"})

        elif self.path == "/legs":
            demo.swap_to_legs = True
            self._respond({"status": "ok", "message": "legs install triggered"})

        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _respond(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())


def run_cmd_server():
    server = HTTPServer(("127.0.0.1", 8765), CmdHandler)
    print(f"  {D}Command server on http://127.0.0.1:8765{X}")
    server.serve_forever()


def input_thread():
    print(f"\n{B}{C}{'='*50}{X}")
    print(f"{B}{C}  RoboStore Demo{X}")
    print(f"{B}{C}{'='*50}{X}")
    print(f"  {Y}G1 has no legs. Use the web app to purchase them.{X}")
    print(f"  {D}Or type 'legs' to install manually.{X}")
    print(f"  {D}After legs: w/b/l/r/run/stop or natural language{X}\n")

    PRESETS = {
        "w": ([0.5,0,0], 4.0), "walk": ([0.5,0,0], 4.0),
        "b": ([-0.3,0,0], 3.0), "back": ([-0.3,0,0], 3.0),
        "l": ([0,0,0.5], 3.0), "left": ([0,0,0.5], 3.0),
        "r": ([0,0,-0.5], 3.0), "right": ([0,0,-0.5], 3.0),
        "s": ([0,0,0], 0.5), "stop": ([0,0,0], 0.5),
        "run": ([1.0,0,0], 4.0),
    }

    while True:
        try:
            text = input(f"{B}{C}demo>{X} ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not text:
            continue
        if text.lower() in ("q", "quit", "exit"):
            import os; os._exit(0)
        if text.lower() == "legs":
            demo.swap_to_legs = True
            continue

        if not demo.has_legs:
            print(f"  {Y}No legs yet — purchase them from the web app or type 'legs'{X}")
            continue

        key = text.lower()
        if key in PRESETS:
            vel, dur = PRESETS[key]
            demo.set_velocity(*vel, dur)
            continue

        try:
            from agent.planner import llm_call
            print(f"  {Y}[LLM]{X} Translating...")
            loop = asyncio.new_event_loop()
            raw = loop.run_until_complete(llm_call(VELOCITY_PROMPT, f"Command: {text}", max_tokens=128))
            cleaned = raw.strip()
            for fence in ("```json", "```"):
                cleaned = cleaned.removeprefix(fence).removesuffix(fence).strip()
            match = re.search(r'\{[^}]+\}', cleaned)
            result = json.loads(match.group() if match else cleaned)
            cmd = result["cmd"]
            dur = max(0.5, min(6.0, float(result.get("duration_s", 3.0))))
            demo.set_velocity(
                max(-0.5, min(1.0, float(cmd[0]))),
                max(-0.3, min(0.3, float(cmd[1]))),
                max(-0.8, min(0.8, float(cmd[2]))),
                dur,
            )
        except Exception as e:
            print(f"  {R}Error: {e}{X}")


def main():
    threading.Thread(target=run_cmd_server, daemon=True).start()
    threading.Thread(target=input_thread, daemon=True).start()

    while True:
        with mujoco.viewer.launch_passive(demo.model, demo.data) as viewer:
            while viewer.is_running():
                t0 = time.time()

                # Check if we need to swap models
                if demo.swap_to_legs:
                    demo.swap_to_legs = False
                    demo.install_legs()
                    break  # break to restart viewer with new model

                demo.physics_step()
                viewer.sync()
                sleep = DT - (time.time() - t0)
                if sleep > 0:
                    time.sleep(sleep)
            else:
                break  # viewer closed by user


if __name__ == "__main__":
    main()
